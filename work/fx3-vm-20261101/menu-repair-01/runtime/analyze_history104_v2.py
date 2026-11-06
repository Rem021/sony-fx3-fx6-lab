from pathlib import Path
import re,json,csv,hashlib,collections
R=Path(__file__).resolve().parent;out=R/'ap104-historical-unfetched-inventory-v2.json';assert not out.exists();runs=['ap103r2ldec600-a7c9c32d','ap103v3ldec600-4ad191d2','ap103v4ldec600-71ce5752'];result=[]
def num(s):
 try:return int(s,0)
 except(ValueError,TypeError):return None
for name in runs:
 run=R/'runs'/name;raw=(run/'serial.log').read_bytes();lines=raw.decode(errors='replace').splitlines();commands=[];scopes={};locks=[]
 for no,line in enumerate(lines,1):
  if 'FX3_GPE_'not in line and 'FX3_GPE102_'not in line:continue
  d=dict(re.findall(r'([A-Za-z_][A-Za-z0-9_]*)=(\S+)',line))
  if 'FX3_GPE_CMD 'in line and num(d.get('seq'))is not None:d.update(line=no);commands.append(d)
  if 'FX3_GPE_SCOPE 'in line and num(d.get('seq'))is not None:scopes[num(d['seq'])]=d
  if 'FX3_GPE102_LOCK_WAIT 'in line:locks.append(dict(line=no,**d))
 failures=[x for x in commands if num(x.get('result'))not in [0,None]];entry={'run':name,'serial_SHA256':hashlib.sha256(raw).hexdigest(),'kernel_unfetched_lines':[{'line':i,'text':x}for i,x in enumerate(lines,1)if'unfetched dynamic queue'in x],'commands_parsed':len(commands),'failure_markers':failures,'per_command_return_ns_count':raw.count(b'FX3_GPE104_CMD_RETURN'),'start_enqueue_backend_queue_depth_available':False,'clock_note':'v24 command markers have no per-command monotonic timestamp. Kernel printk clock cannot substitute for user command clocks.'}
 if failures:
  f=failures[0];q=num(f['seq']);prev=max([num(x['seq'])for x in commands if num(x['seq'])<q and x.get('op')=='Flush'and num(x.get('result'))==0],default=-1);batch=[]
  for x in commands:
   seq=num(x['seq'])
   if not prev<seq<=q:continue
   sc=scopes.get(seq,{}).copy();x=x.copy();x['approx_tile']=next((v for v in ['repeat_mask_v1','none']if x.get('approx_tile','').startswith(v)),'unknown');sc['approx_stretch']=next((v for v in ['nearest_v1','nearest_v2','none']if sc.get('approx_stretch','').startswith(v)),'unknown');path=x.get('op','unknown');path+=('|tile'if x.get('approx_tile')not in [None,'none','unknown']else'')+('|stretch:'+sc['approx_stretch']if sc.get('approx_stretch')not in[None,'none','unknown']else'')+('|fmt2'if x.get('op')=='BitBlit'and num(x.get('src_fmt'))==2 else'')+('|Kblend:'+str(x.get('K'))if num(x.get('approx_blend'))==1 else'')
   batch.append({'seq':seq,'op':x.get('op'),'destination_format':num(x.get('fmt')),'source_format':num(x.get('src_fmt')),'marker_source_w':num(x.get('w')),'marker_source_h':num(x.get('h')),'path':path,'result':num(x.get('result')),'reason':num(x.get('reason')),'enqueue_ns':None,'start_ns':None,'end_ns':None,'completion_ns':None,'worker_queue_depth':None,'line':x['line']})
  path=R/(name+'-unfetched-batch-v2.csv');assert not path.exists()
  with path.open('w',newline='')as fp:w=csv.DictWriter(fp,fieldnames=list(batch[0]));w.writeheader();w.writerows(batch)
  entry.update(previous_successful_Flush_seq=prev,failed_seq=q,commands_in_partial_batch=len(batch),path_counts=dict(collections.Counter(x['path']for x in batch)),batch_csv=str(path),recorded_lock_waits=[x for x in locks if prev<num(x.get('seq'))<=q])
 result.append(entry)
out.write_text(json.dumps({'runs':result,'no_old_run_writes':True},indent=2)+'\n');print(json.dumps([{k:r.get(k)for k in ['run','commands_parsed','failed_seq','commands_in_partial_batch','per_command_return_ns_count']}for r in result]))
