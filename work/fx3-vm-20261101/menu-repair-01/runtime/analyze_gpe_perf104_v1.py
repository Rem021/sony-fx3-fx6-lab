"""Offline, end-to-endpoint envelopes only; never invent missing start/queue clocks."""
from pathlib import Path
import json,re,csv,hashlib,collections,argparse
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('prefix',type=Path);a=p.parse_args();assert not a.prefix.resolve().is_relative_to(a.run.resolve());paths=[Path(str(a.prefix)+x)for x in ['.json','.csv','.md']];assert not any(x.exists()for x in paths)
raw=(a.run/'serial.log').read_bytes();lines=raw.decode(errors='replace').splitlines();records=[]
for no,line in enumerate(lines,1):
 for m in re.finditer(r'(FX3_[A-Z0-9_]+)\s+',line):
  tail=line[m.end():];nextmark=re.search(r'FX3_[A-Z0-9_]+\s',tail)
  if nextmark:tail=tail[:nextmark.start()]
  fields=dict(re.findall(r'([A-Za-z_][A-Za-z0-9_]*)=(\S+)',tail));records.append({'kind':m[1],'line':no,'fields':fields,'raw':line})
def number(d,k):
 v=d.get(k)
 if v is not None and re.fullmatch(r'-?(?:0x[0-9a-fA-F]+|[0-9]+)',v):return int(v,0)if v.startswith(('0x','-0x'))else int(v)
 return None
def rs(kind):return[r for r in records if r['kind']==kind]
def byseq(kind):
 out={}
 for r in rs(kind):
  q=number(r['fields'],'seq')
  if q is not None:out[q]=r
 return out
ret=[r for r in rs('FX3_GPE104_CMD_RETURN')if all(number(r['fields'],k)is not None for k in ['ns','tid','seq','op','result'])];fail=next(r for r in ret if number(r['fields'],'op')==4 and number(r['fields'],'result')!=0);fseq=number(fail['fields'],'seq');tid=number(fail['fields'],'tid');fail_index=ret.index(fail);prior=next(r for r in reversed(ret[:fail_index])if number(r['fields'],'tid')==tid and number(r['fields'],'op')==4 and number(r['fields'],'result')==0);start=number(prior['fields'],'ns');end=number(fail['fields'],'ns');cstart=byseq('FX3_GPE104_COMPLETE_ENTER')[fseq];cend=byseq('FX3_GPE104_COMPLETE_RETURN')[fseq];attempt=number(cstart['fields'],'ns');qid=number(cstart['fields'],'completion_source')
dynamic=[r for r in rs('FX3_GPE104_DYNAMIC_RETURN')if number(r['fields'],'QID')==qid and number(r['fields'],'result')==0 and number(r['fields'],'ns')is not None and number(r['fields'],'ns')<attempt];claim=next(r for r in reversed(dynamic)if number(r['fields'],'flags')==0x2a);release=next(r for r in reversed(dynamic)if number(r['fields'],'flags')==0x4a);claim_ns=number(claim['fields'],'ns');release_ns=number(release['fields'],'ns');meta=byseq('FX3_GPE_CMD');scope=byseq('FX3_GPE_SCOPE');interval=byseq('FX3_GPE_DRAW_INTERVAL');params=byseq('FX3_GPE_RAW_PARAMS');texture=byseq('FX3_TEX102_BEFORE');locks=byseq('FX3_GPE102_LOCK_WAIT');comps=byseq('FX3_GPE104_COMPLETE_ENTER');compends=byseq('FX3_GPE104_COMPLETE_RETURN');rows=[];prev={}
for r in ret:
 d=r['fields'];n=number(d,'ns');t=number(d,'tid');seq=number(d,'seq');old=prev.get(t);prev[t]=r
 if t!=tid or not start<n<=end or old is None:continue
 oldn=number(old['fields'],'ns');oldseq=number(old['fields'],'seq');md=meta.get(seq,{}).get('fields',{});sc=scope.get(seq,{}).get('fields',{});iv=interval.get(seq,{}).get('fields',{});tx=texture.get(seq,{}).get('fields',{});pa=params.get(seq,{}).get('fields',{});blob=None
 try:
  h=pa.get('raw_hex','');b=bytes.fromhex(h)
  if len(b)in [56,144,24]:blob=b
 except ValueError:pass
 def u(off):return int.from_bytes(blob[off:off+4],'little')if blob is not None and off+4<=len(blob)else None
 op=number(d,'op');dw=u(16)if op in[0,1]else None;dh=u(20)if op in[0,1]else None;sw=u(72)if op==1 else None;sh=u(76)if op==1 else None
 fmt=number(md,'fmt');sf=number(md,'src_fmt');K=number(md,'K');blend=number(md,'approx_blend');tile=md.get('approx_tile','unknown');stretch=iv.get('approx_stretch',sc.get('approx_stretch','unknown'));path=('fill'if op==0 else'flush'if op==4 else'blit');path+=('|tile'if tile not in ['none','unknown']else'')+('|stretch:'+stretch if stretch not in ['none','unknown']else'')+('|fmt2'if sf==2 and op==1 else'')+('|Kblend:'+str(K)if blend==1 else'|replace'if op!=4 else'')
 sr=number(tx,'source_rows');sl=number(tx,'source_line_bytes');dr=number(tx,'destination_rows');dl=number(tx,'destination_line_bytes');observer_bytes=sr*sl+2*dr*dl if None not in[sr,sl,dr,dl]else None
 missing=max(0,seq-oldseq-1);late=max(0,min(n,attempt)-max(oldn,release_ns));full=max(0,min(n,end)-max(oldn,start));row={'seq':seq,'tid':t,'op':md.get('op',str(op)),'destination_format':fmt,'source_format':sf,'raw_destination_w':dw,'raw_destination_h':dh,'raw_source_crop_w':sw,'raw_source_crop_h':sh,'marker_w':number(md,'w'),'marker_h':number(md,'h'),'path':path,'K':K,'async':number(md,'async'),'enqueue_ns':None,'start_ns':None,'after_command_lock_acquire_ns':None,'backend_start_ns':None,'backend_end_ns':None,'end_after_observer_emit_ns':n,'previous_same_worker_end_ns':oldn,'previous_seq':oldseq,'unlogged_commands_in_envelope':missing,'endpoint_envelope_ns':n-oldn,'batch_endpoint_envelope_ns':full,'released_to_first_attempt_envelope_overlap_ns':late,'recorded_command_lock_wait_ns':number(locks.get(seq,{}).get('fields',{}),'wait_ns'),'life_lock_wait_ns':None,'worker_queue_depth':None,'completion_attempt_ns':number(comps.get(seq,{}).get('fields',{}),'ns'),'completion_attempt_return_ns':number(compends.get(seq,{}).get('fields',{}),'ns'),'completion_source':d.get('completion_source'),'result':number(d,'result'),'texture_observer_copied_and_SHA_bytes':observer_bytes,'texture_observer_histogram_bytes':sr*sl if sr is not None and sl is not None else None,'return_line':r['line'],'command_metadata_line':meta.get(seq,{}).get('line'),'raw_parameters_line':params.get(seq,{}).get('line')};rows.append(row)
summary=collections.defaultdict(lambda:{'commands':0,'batch_endpoint_envelope_ns':0,'late_window_envelope_ns':0,'texture_copied_and_SHA_bytes':0})
for r in rows:
 k=r['path']if not r['unlogged_commands_in_envelope']else'unknown_includes_missing_commands';z=summary[k];z['commands']+=1;z['batch_endpoint_envelope_ns']+=r['batch_endpoint_envelope_ns'];z['late_window_envelope_ns']+=r['released_to_first_attempt_envelope_overlap_ns'];z['texture_copied_and_SHA_bytes']+=r['texture_observer_copied_and_SHA_bytes']or 0
v={'run':str(a.run.resolve()),'serial_SHA256':hashlib.sha256(raw).hexdigest(),'method':'Same-worker consecutive original adapter return timestamps provide wall-time envelopes; NOT command CPU/sole backend duration. All enqueue/start/backend clocks, life-lock waits and FIFO depth absent are null. Envelopes include producer/dequeue gaps, scheduling/QEMU pauses, validation/mmap, rendering, copies, hashes and text output.','failed_seq':fseq,'qid':hex(qid),'previous_successful_Flush':prior,'failed_Flush':fail,'claim':claim,'release':release,'first_zero_completion_attempt':cstart,'first_zero_completion_return':cend,'ns':{'last_success_Flush_return':start,'last_claim_return':claim_ns,'last_release_return':release_ns,'first_completion_attempt':attempt,'failed_Flush_return':end,'claim_to_release':release_ns-claim_ns,'release_to_first_completion_attempt':attempt-release_ns,'previous_Flush_to_failed_Flush':end-start},'recorded_command_lock_waits':[r for r in rs('FX3_GPE102_LOCK_WAIT')if number(r['fields'],'seq')in set(x['seq']for x in rows)],'queue_depth_observed':False,'start_or_enqueue_observed':False,'commands':rows,'summary':dict(summary),'native_PLT_records':rs('FX3_LIGHT104_SENDCOMP_ENTER')+rs('FX3_LIGHT104_SENDCOMP_RETURN'),'coverage':{'return_rows':len(rows),'expected_consecutive_seq_count':fseq-number(prior['fields'],'seq'),'missing_return_commands':sum(r['unlogged_commands_in_envelope']for r in rows),'command_metadata_missing':sum(r['command_metadata_line']is None for r in rows),'historical_v24_has_no_per_command_ns':True},'no_original_or_old_run_writes':True}
paths[0].write_text(json.dumps(v,indent=2)+'\n')
with paths[1].open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rank=sorted(rows,key=lambda r:r['endpoint_envelope_ns'],reverse=True);md=['# AP104 既有日志性能分解','',v['method'],'',f"失败序{fseq}，QID {hex(qid)}；last successful Flush返回至失败Flush返回 {(end-start)/1e9:.6f}s；领取到释放 {(release_ns-claim_ns)/1e9:.6f}s；释放返回至首次零完成投递 {(attempt-release_ns)/1e9:.6f}s。",'',f"逐条表：[{paths[1].name}]({paths[1].name})；完整字段/原行号：[{paths[0].name}]({paths[0].name})。入队、开始、backend分段、life锁等待和worker深度全部未记录，表中留空，不用终点间隔冒充这些值。",'','|路径|命令数|整批终点间隔(s)|释放后至首投递窗口占比(s)|纹理观察复制/三SHA字节|','|---|---:|---:|---:|---:|']
for k,z in sorted(summary.items(),key=lambda kv:kv[1]['late_window_envelope_ns'],reverse=True):md.append(f"|{k}|{z['commands']}|{z['batch_endpoint_envelope_ns']/1e9:.6f}|{z['late_window_envelope_ns']/1e9:.6f}|{z['texture_copied_and_SHA_bytes']}|")
md+=['','## 最大终点间隔（非实测backend耗时）','','|seq|op|src/dst fmt|raw dst尺寸|path|终点间隔(s)|释放后窗口交集(s)|','|---:|---|---|---|---|---:|---:|']
for r in rank[:20]:md.append(f"|{r['seq']}|{r['op']}|{r['source_format']}/{r['destination_format']}|{r['raw_destination_w']}×{r['raw_destination_h']}|{r['path']}|{r['endpoint_envelope_ns']/1e9:.6f}|{r['released_to_first_attempt_envelope_overlap_ns']/1e9:.6f}|")
md+=['','仅有显式command-lock竞争marker可计时；本批其他命令无marker不等于所有锁等待为零。命令返回标记位于tex102_emit之后，纹理复制/SHA/直方图和串口日志均包含在终点间隔；源代码表明这些工作可能占成本，但现有时钟不足以把其耗时与backend像素循环分离。历史v24轮无该逐命令ns，不能把printk时钟拼接成用户态命令耗时。',''];paths[2].write_text('\n'.join(md));print(json.dumps({'json':str(paths[0]),'csv':str(paths[1]),'summary':summary,'coverage':v['coverage'],'largest':[ {k:r[k]for k in ['seq','op','path','marker_w','marker_h','endpoint_envelope_ns']}for r in rank[:8]]}))
