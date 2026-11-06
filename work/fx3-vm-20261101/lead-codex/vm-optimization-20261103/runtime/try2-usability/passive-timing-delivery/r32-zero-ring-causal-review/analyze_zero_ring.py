#!/usr/bin/env python3
"""Read-only r32: bytes-first parsing, sealed-source binding, bounded excerpts.
No runner import, VM, socket, HTTP, QMP execution or source mutation.
"""
import bisect,collections,datetime as dt,hashlib,json,re,struct,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent;D=R.parent;T=D.parent
PINS={}
for f in ['INPUTS-BEFORE.json','INPUT-SUPPLEMENT-BEFORE.json']:
 for x in json.loads((R/f).read_text())['files']:PINS[x['path']]=x

def read(p):
 p=Path(p).resolve();b=p.read_bytes();row=PINS[str(p)];assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],str(p);return b

def js(p):return json.loads(read(p))
def save(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def bounded_record(raw, lf, start, limit):
 e=raw.find(b'\n',start);partial=e<0 or e>=limit
 e=limit if partial else e
 b=raw[start:e].rstrip(b'\r')
 return {'byte_offset':start,'LF_line':bisect.bisect_left(lf,start)+1,'partial_record':partial,'window_end':limit,'text':b.decode(errors='replace'),'fields':fields(b)}

def fields(b):return {k.decode():v.decode(errors='replace') for k,v in re.findall(rb'\b(\w+)=([^\s\x00]+)',b)}
GATE=re.compile(rb'FX3_UI_GATE_SAMPLE id=(\d+) n=(\d+) tid=(\d+) pc=(0x[0-9a-f]+) object=(0x[0-9a-f]+) a18=(\d+) a12=(\d+) a13=(\d+) r0=(0x[0-9a-f]+|0) decision_a18=(\d+) elapsed=(\d+) old_time=(\d+) new_time=(\d+) message=(0x[0-9a-f]+|0) type=(0x[0-9a-f]+|0) source=(0x[0-9a-f]+|0) observed_only=1')
RUNS={'r31':('77e949cd','r31-vm-22ac221f3da6'),'r28':('f7903939','r28-vm-cb12b6256797'),'r26':('740bafa8','r26-vm-49f0c1c3663b'),'r26b':('45304842','r26b-vm-93b3e243da6f')}
TOKEN=[b'FX3_UI_GATE_BOUND ',b'FX3_TIMER_BOUND ',b'FX3_UI_CONFIG_DONE ',b'FX3_TIMER_ENTRY ',b'FX3_UI_FILL_EXEC ',b'FX3_OSD_HEADLESS_BOUND ',b'FX3_OSD_OWNER_START ',b'FX3_OSD102_COMMIT ',b'FX3_AP89_SCREEN_OPEN_ENTER ',b'FX3_BOOT_QUEUE_SEND ',b'FX3_UI_WIRE ',b'FX3_GPE_CMD ',b'FX3_KEY_INPUT_RECV ']

def run(label,rid,op):
 p=T/'runs'/('v25gate-n64-r17-'+rid);raw=read(p/'serial.log');lf=[m.start() for m in re.finditer(b'\n',raw)]
 def rec(m,limit=len(raw)):return bounded_record(raw,lf,m.start(),limit)
 def matches(token,cut=len(raw)):return [rec(m,cut) for m in re.finditer(re.escape(token),raw[:cut])]
 first_commit=raw.find(b'FX3_OSD102_COMMIT ');first_timer=raw.find(b'FX3_TIMER_ENTRY ')
 if label=='r31':
  obs=js(p/'startup-observation.json');cut=next(x['serial_offset'] for x in obs['phases']['recent'] if x['stage']=='cleanup');scope='exact last consumed serial prefix at host entry to original finally, before cleanup serial polling; not global guest event boundary'
 elif label in ['r26','r26b']:
  cut=first_commit;scope='code/serial prefix before first original OSD commit; native key receive excluded; precedes qualified ready; not matched-duration window'
 else:
  cut=first_timer;scope='pre-first-timer serial prefix only; exact pre-End byte boundary unavailable, so NOT asserted to be a strict host startup window'
 assert cut>0 and b'FX3_KEY_INPUT_RECV ' not in raw[:cut]
 windows={'comparison':{'cut':cut,'scope':scope}}
 if first_timer>=0:windows['pre_timer']={'cut':first_timer,'scope':'program/log order before first original timer; r28 host End relation uncertain'}
 if first_commit>=0:windows['pre_first_commit']={'cut':first_commit,'scope':'program/log order; r28 first commit observation straddles End; not retrospectively qualified'}
 result={'run':str(p),'serial_bytes':len(raw),'NUL_bytes_full':raw.count(b'\0'),'windows':{}}
 for w,v in windows.items():
  end=v['cut'];b=raw[:end];g=list(GATE.finditer(b));gs={}
  for id in [5,6,7,8,9,10,11]:
   rows=[m for m in g if int(m[1])==id and not rec(m,end)['partial_record']];rr=[rec(m,end) for m in rows]
   vals=[int(m[10]) for m in rows];signed=[x-(1<<32) if x&(1<<31) else x for x in vals]
   gs[str(id)]={'strict_records':len(rows),'excluded_fragment_or_partial_records':b.count(f'FX3_UI_GATE_SAMPLE id={id} '.encode())-len(rows),'raw_literal_count':b.count(f'FX3_UI_GATE_SAMPLE id={id} '.encode()),'first':rr[:2],'last':rr[-2:],
    'maximum_logged_n':max((int(m[2]) for m in rows),default=0),'roots':dict(collections.Counter(m[5].decode() for m in rows)),
    'tids':dict(collections.Counter(m[3].decode() for m in rows)),
    'signed_decision_min':min(signed) if signed else None,'signed_decision_max':max(signed) if signed else None,
    'a12_nonzero_samples':sum(int(m[7])!=0 for m in rows),
    'consumer_sample_source_type':dict(collections.Counter(m[16].decode()+':'+m[15].decode() for m in rows)) if id==11 else None}
  sends=matches(b'FX3_BOOT_QUEUE_SEND ',end);wires=matches(b'FX3_UI_WIRE ',end);receives=matches(b'FX3_UIPC_RECV_BEGIN ',end)
  unique=[z for z in matches(b'FX3_UIPC_SEND_UNIQUE ',end) if not z['partial_record'] and z['fields'].get('target')=='0x5503e0']
  groups=collections.Counter();sendbytes=0;complete=0
  for z in sends:
   if z['partial_record']:continue
   f=z['fields'];h=f.get('raw','');
   if re.fullmatch('[0-9a-f]+',h) and len(h)%2==0 and all(k in f for k in ['source','tid','bytes','caller_relative']):
    data=bytes.fromhex(h);complete+=1;sendbytes+=len(z['text'].encode())+1
    groups[(f['source'],hex(int.from_bytes(data[:4],'little')) if len(data)>=4 else 'short',f['caller_relative'],f['tid'],str(len(data)))]+=1
  wiregroups=collections.Counter()
  for z in wires:
   if z['partial_record']:continue
   f=z['fields']
   if all(k in f for k in ['target','tag1','result']):
    try:wiregroups[(f['target'],hex(int(f['tag1'],0)&0xffff),f['result'])]+=1
    except ValueError:pass
  # Diagnostic block coverage is bytes covered by matched BEGIN..END markers, NOT CPU/duration.
  block=[];opened={};unpaired=0
  for m in re.finditer(rb'FX3_TASK_SNAPSHOT_(\d+)_(BEGIN|END)',b):
   key=m[1]
   if m[2]==b'BEGIN':opened[key]=m.start()
   elif key in opened:block.append((opened.pop(key),m.end()))
   else:unpaired+=1
  cover=0;last=-1
  for a,e in sorted(block):cover+=max(0,e-max(a,last));last=max(last,e)
  result['windows'][w]={'cut':end,'scope':v['scope'],'NUL_bytes':b.count(b'\0'),'gate_samples':gs,
   'marker_counts':{x.decode().strip():b.count(x) for x in TOKEN},'marker_firsts':{x.decode().strip():matches(x,end)[:1] for x in TOKEN},
   'BOOT_QUEUE_SEND':{'literal_records':len(sends),'complete_field_records':complete,'record_byte_estimate':sendbytes,
      'grouping_columns':['source','body_low32_type','caller_relative','tid','body_bytes'],
      'groups':[{'key':list(k),'records':n} for k,n in groups.items()],
      'scope':'capid hook before underlying native send; no result or delivery proof, no complete production/consumption pairing'},
   'native_send_unique_5503e0':{'records':len(unique),'results':dict(collections.Counter(z['fields'].get('result','unknown') for z in unique)),'first_150000':[z for z in unique if z['fields'].get('tag1')=='0x150000'][:1],'scope':'original ioctl returned for selected unique bodies; dedup key omits result and tid, not every send status'},
   'UI_WIRE':[{'target_low16_result':list(k),'records':n} for k,n in wiregroups.items()],
   'recv_begin_queue_counts':dict(collections.Counter(z['fields'].get('queue','fragment') for z in receives if not z['partial_record'])),
   'task_snapshot_byte_coverage':{'matched_intervals':len(block),'union_bytes':cover,'unclosed':len(opened),'unpaired_ends':unpaired,
      'meaning':'diagnostic log volume/overlap only; neither write duration nor time spent blocked'},
   'last_original_screen':matches(b'FX3_AP89_SCREEN_OPEN_ENTER ',end)[-1:]}
 hraw=read(p/'ui-gate-counters.bin');h=struct.unpack_from('<8Q',hraw);v=struct.unpack_from('<98Q',hraw,0x100+h[2]*0x1000)
 result['post_End_published_bank_only']={'header':list(h),'counts0_11':list(v[:12]),'peak_gate':v[65],'hist0_1_2_3to10_11to100_gt100':list(v[73:79]),
  'backlog_skip':v[80],'time_pass':v[82],'last_a18':v[88],'producer9':v[9],'consumer10':v[10],'object_mismatch':v[96],'root_change':v[97],
  'scope':'paused original optional readback after End; N64 individually copied published fields can lag; controls contain a later key; not strict startup state or transaction snapshot'}
 cmd=js(p/'command.json');a=js(p/'cpio-audit.json')
 names=['usr/lib/appFw.so','simulation/fx3-osd-headless-v5.so','simulation/fx3-capid-v1.so','simulation/ioctl-trace.so','simulation/fx3-ui-gate-v1.so']
 result['actual_members']={n:next(x['sha256'] for x in a['members'] if x['path']==n) for n in names}
 result['fixed_argv']=[x.replace(str(p),'<RUN>') for x in cmd['args']];result['cpio_SHA']=a['candidate_cpio_sha256']
 result['queue_owner_guest_init']= 'FX3_OSD_QUEUE_OWNER=native-receiver-v1' in a['init_text'] and 'FX3_OSD_HEADLESS=software-ring-v1' in a['init_text']
 q=js(p/'qmp.json');dump=[{'journal_index':i,'id':x['request']['id'],'Popen_relative_s':x['elapsed_seconds'],'command_line':x['request']['arguments']['command-line']} for i,x in enumerate(q) if 'osd-ring-final.bin' in x.get('request',{}).get('arguments',{}).get('command-line','')]
 result['actual_QMP_ring_dump']=dump
 firststop=next(x for x in q if 'backup-native-load-before-AP.bin' in x.get('request',{}).get('arguments',{}).get('command-line',''))
 result['pre_AP_read_Popen_relative_s']=firststop['elapsed_seconds']
 tail=read(p/'snapshot-tail-slot-1.bin');tv=struct.unpack_from('<98Q',tail,0xc0)
 result['after_End_tail_checkpoint_NOT_startup_or_terminal']={'counts0_11':list(tv[:12]),'peak_gate':tv[65],'backlog_skip':tv[80],'time_pass':tv[82],
  'scope':'separate post-End nontransactional checkpoint, excluded from all startup window statistics'}
 if label=='r31':
  b=read(p/'osd-ring-final.bin');assert len(b)==1<<24 and b.count(0)==len(b)
  result['zero_ring']={'bytes':len(b),'all_zero':True,'sha256':hashlib.sha256(b).hexdigest(),'paused_readback':js(p/'osd-ring-final-readback-receipt.json')}
  result['r30_observation_summary']={k:obs[k] for k in ['header_counts','markers','serial','errors']};result['r30_observation_header_initial_last']={'initial':obs['headers']['initial'],'last':obs['headers']['last']}
  result['r30_ready_changes']=obs['ready']['recent']
 save(label+'-ANALYSIS.json',result);return result

def main():
 results={k:run(k,*v) for k,v in RUNS.items()}
 ref=results['r31'];assert all(x['fixed_argv']==ref['fixed_argv'] and x['cpio_SHA']==ref['cpio_SHA'] and x['actual_members']==ref['actual_members'] and x['queue_owner_guest_init'] for x in results.values())
 candidate=js(D/'r16-fixed-slot-guests/guest-N64/candidate.json');contract=candidate['v25_diagnostic_contract']
 manifest={line.split('  ',1)[1]:line.split('  ',1)[0] for line in read(D/'r16-r15-guest-SOURCE-SHA256SUMS').decode().splitlines()}
 assert hashlib.sha256(read(D/'v25-r15-snapshot-tail/fx3-ui-gate-v15.c')).hexdigest()==manifest['v25-r15-snapshot-tail/fx3-ui-gate-v15.c']
 assert js(D/'v25-r15-snapshot-tail/BUILD.json')['variants']['N64']['sha256']==candidate['fixed_layout_diagnostic_contract']['helper_raw_sha256']
 assert ref['actual_members']['simulation/fx3-ui-gate-v1.so']==candidate['fixed_layout_diagnostic_contract']['padded_slot_sha256']
 src=D/'v25-menu-osd-diagnostic-r3/src/fx3-osd-headless-v25-r3.c';so=D/'v25-menu-osd-diagnostic-r3/build/fx3-osd-headless-v25-r3.so'
 assert hashlib.sha256(read(src)).hexdigest()==contract['source_sha256']
 assert hashlib.sha256(read(so)).hexdigest()==contract['new_member_sha256']==ref['actual_members']['simulation/fx3-osd-headless-v5.so']
 cap=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-capid-v49-touch100.c');cb=js(cap.with_name('fx3-capid-v49-touch100-build.json'))
 assert hashlib.sha256(read(cap)).hexdigest()==cb['source_sha256'] and cb['output_sha256']==ref['actual_members']['simulation/fx3-capid-v1.so']
 # Byte-boundary regression: incomplete row must never borrow fields after cut.
 sample=b'prefix TOKEN value=1\n';cut=sample.index(b'=')
 z=bounded_record(sample,[len(sample)-1],7,cut)
 assert z['partial_record'] and '1' not in z['text'] and not z['fields']
 # Disassemble pinned files only; no code is loaded or executed.
 elf=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so')
 assert hashlib.sha256(read(elf)).hexdigest()==ref['actual_members']['usr/lib/appFw.so']
 dis=[]
 for name,path,a,b in [('app-producer-full.txt',elf,'0x16f1a48','0x16f1c18'),('app-consumer-full.txt',elf,'0x16f1d08','0x16f1db0'),('osd-bind-compiled.txt',so,'0x13f2c','0x14154')]:
  args=['/usr/bin/xcrun','llvm-objdump','--disassemble','--start-address='+a,'--stop-address='+b,str(path)]
  p=subprocess.run(args,capture_output=True);assert p.returncode==0;pout=R/name;pout.write_bytes(p.stdout);dis.append({'argv':args,'exit':p.returncode,'output':name,'sha256':hashlib.sha256(p.stdout).hexdigest()})
 # Pin-consumed code excerpts only, no entire source/log replication.
 ex=[]
 H=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/helpers')
 for path,ranges in [(src,[(26,37),(73,81),(111,121)]),(H/'fx3-osd-core-v4-frame.h',[(1,14)]),(H/'fx3-osd-owner-core-v1.h',[(1,12)]),
     (D/'v25-r15-snapshot-tail/fx3-ui-gate-v15.c',[(6,9),(19,23),(33,35),(134,146),(154,163)]),
     (cap,[(604,611),(680,683)]),(H/'ioctl-trace-v12.c',[(23,52),(188,196)])]:
  lines=read(path).decode(errors='replace').splitlines()
  for a,b in ranges:ex.append({'path':str(path),'first_line':a,'last_line':b,'lines':[f'{i}: {lines[i-1]}' for i in range(a,b+1)]})
 save('CODE-EVIDENCE.json',ex)
 # Independently recover the compiled vector literal used for magic/version.
 binary=read(so);phoff=struct.unpack_from('<Q',binary,32)[0];phents,phnum=struct.unpack_from('<HH',binary,54)
 def virtual_bytes(address,n):
  for i in range(phnum):
   h=struct.unpack_from('<II6Q',binary,phoff+i*phents);kind,flags,off,va,pa,filesz,memsz,align=h
   if kind==1 and va<=address and address+n<=va+filesz:return binary[off+address-va:off+address-va+n]
  raise ValueError('ELF literal outside file PT_LOAD')
 magic,version=struct.unpack('<2Q',virtual_bytes(0xac0,16));assert magic==0x32474e495244534f and version==2
 save('BINDING.json',{'compiled_magic_vector_at_0xac0':[hex(magic),version],'window_boundary_regression_passed':True,'UI_v15_source_build_fixed_slot_binding':True,'same_fixed_argv_cpio_and_actual_helpers_all4':True,'actual_members':ref['actual_members'],'cpio_SHA':ref['cpio_SHA'],'OSD_source_SHA':contract['source_sha256'],'capid_source_build_binary_binding':True,'disassembly':dis})
 summary={}
 for k,r in results.items():
  w=r['windows']['comparison'];summary[k]={'cut':w['cut'],'scope':w['scope'],'bytes':w['cut'],
   'gate':[w['gate_samples'][str(i)]['maximum_logged_n'] for i in [5,7,8,9,10,11]],
   'gate_order':'max logged n at id5,7,8,9,10,11 (sampled/lower bounds, never terminal counts)',
   'send_records':w['BOOT_QUEUE_SEND']['complete_field_records'],'timer150000_send_records':sum(x['records'] for x in w['BOOT_QUEUE_SEND']['groups'] if x['key'][1]=='0x150000'),'pre_AP_read_Popen_relative_s':r['pre_AP_read_Popen_relative_s'],'task_diag_bytes':w['task_snapshot_byte_coverage']['union_bytes'],'UI_WIRE':w['UI_WIRE'],
   'root_sets':{str(i):w['gate_samples'][str(i)]['roots'] for i in [5,9,10,11]}}
 save('COMPARISON.json',summary)
 after=[]
 for row in PINS.values():
  b=Path(row['path']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],row['path'];after.append(dict(row,unchanged=True))
 save('INPUTS-AFTER.json',{'checked_UTC':dt.datetime.now(dt.timezone.utc).isoformat(),'count':len(after),'files':after})
 print(json.dumps({'outcome':'readonly_analysis_complete_root_cause_unresolved','input_count':len(after),'all_hashes_unchanged':True,'summary':summary},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
