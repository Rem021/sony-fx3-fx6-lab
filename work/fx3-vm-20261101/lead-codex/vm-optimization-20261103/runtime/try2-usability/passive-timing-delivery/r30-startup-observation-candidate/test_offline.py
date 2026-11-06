#!/usr/bin/env python3
"""No browser/service/guest: actual reader, monitor, and extracted runner blocks.
Constructed headers/native pixels are fixtures; historical receive times are unrecoverable.
"""
import ast, collections, copy, hashlib, importlib.util, io, json, re, runpy, struct, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
R=Path(__file__).resolve().parent;D=R.parent;B=D/'r28-first-observation-candidate';F=D/'v25-r21-recovery-integration'
sys.dont_write_bytecode=True;sys.path[:0]=[str(R),str(F)]
from startup_observation import StartupObservation, MARKERS, PREDICATES, MAX_BYTES
from osd_ring93_v4 import MAGIC, BASE, HEADER, STRIDE, fnv

def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
old_ring=load('r30_old_reader',F/'trial_ring_cached.py');new_ring=load('r30_new_reader',R/'trial_ring_cached.py')
old_log=load('r30_old_log',F/'trial_log_v4_mss.py');new_log=load('r30_new_log',R/'trial_log_v4_mss.py')
RECEIPTS=[];INPUTS=[]
def old_input(p):
 b=p.read_bytes();INPUTS.append({'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)});return b

def header(seq=0,magic=MAGIC,version=2,fail=0):
 g=[magic,version,237,1,seq,seq,seq,0,0,fail,0,8,STRIDE,HEADER,0,0]
 return struct.pack('<16Q',*g)+b'\0'*128

def slot(seq=1,bad=False):
 v=[0]*36;raw=b'\x00\x00\xff\xff'
 for k,x in {0:seq,1:1,2:seq,3:0x1003,4:1,5:0x402,6:0x43feb5100,7:0,8:2,9:1,10:2,11:4,12:fnv(raw),13:0x7100,14:0x7200,15:0x7300,16:0x7400,17:0x402,18:1,19:0x2800001,20:0xabcd,21:1,22:0x7edf797100,23:0x7edf797000,24:0x7edf798000,25:0x43feb5000,26:1,27:1,29:2,31:0x43feb5000,32:0x140000,33:0x402,35:0x43feb5100}.items():v[k]=x
 if bad:v[12]^=1
 b=bytearray(STRIDE);struct.pack_into('<36Q',b,0,*v);b[0x200:0x204]=raw;return bytes(b)
class State:
 def __init__(self):self.published=[];self.black_after_ready=[];self.stops=[];self.updates=[];self.stop=SimpleNamespace(is_set=lambda:False)
 def publish(self,png,record):self.published.append((png,copy.deepcopy(record)))
 def update(self,**kw):self.updates.append(kw)
 def fail(self,reason):self.stops.append(reason)
class QMP:
 def __init__(self,run,heads,*,bad_slot=False):self.run=run;self.heads=iter(heads);self.calls=[];self.sequence=0;self.seq=1;self.bad_slot=bad_slot
 def __call__(self,command,arguments=None,**kw):
  self.sequence+=1;line=(arguments or {}).get('command-line','');self.calls.append((command,line.replace(str(self.run),'<RUN>'),kw))
  if 'pmemsave' in line:
   name=re.search(r'"([^"]+)"',line)[1];p=Path(name)
   if p.name=='osd-ring-header-live.bin':
    h=next(self.heads)
    if isinstance(h,BaseException):raise h
    if h=='error':return {'id':self.sequence,'error':{'class':'fixture'}}
    if h=='missing':return {'id':self.sequence,'return':''}
    if len(h)>=40:self.seq=struct.unpack_from('<Q',h,32)[0]
    p.write_bytes(h)
   else:p.write_bytes(slot(self.seq,bad=self.bad_slot))
  return {'id':self.sequence,'return':''}

def result(reader,state,exc):
 def cleanrec(rec):return {k:v for k,v in rec.items() if k!='host_monotonic'} if rec else None
 return {'last':reader.last,'seen':sorted(reader.seen),'rejects':[{k:v for k,v in x.items() if k!='host_monotonic'} for x in reader.rejects],
   'frame':cleanrec(reader.current_record),'published':[(hashlib.sha256(p).hexdigest(),cleanrec(r)) for p,r in state.published],
   'exception':None if exc is None else (type(exc).__name__,str(exc))}

def reader_cases(tmp):
 cases={'short_empty':[b''],'short_16Q':[header()[:128]],'oversize':[header()+b'x'],
  'bad_magic':[header(magic=0)],'bad_version':[header(version=3)],'seq0':[header()],
  'valid_and_repeat':[header(1),header(1)],'invalid_to_valid':[header(magic=0),header(),header(1)],
  'QMP_exception':[TimeoutError('fixture QMP timeout')],'QMP_exception_after_frame':[header(1),TimeoutError('fixture QMP timeout')],'diagnostic_prefix_exception':[header()[:128]],'QMP_error_response':['error'],'missing_export':['missing'],
  'consumer_failure':[header(1,fail=1)],'invalid_slot':[header(1)],'host_read_exception':[header()]}
 for name,heads in cases.items():
  pair=[];obs=None;traces=[]
  for label,mod in [('old',old_ring),('new',new_ring)]:
   run=tmp/(name+'-'+label);run.mkdir();q=QMP(run,heads,bad_slot=name=='invalid_slot');st=State();obs=StartupObservation(run) if label=='new' else None
   rr=mod.TrialRingReader(run,q,st,**({'startup_observation':obs,'request_sequence':lambda:q.sequence} if obs else {}));exc=None
   orig=Path.read_bytes
   def injected(p):
    if name=='host_read_exception' and p.name=='osd-ring-header-live.bin':raise OSError('fixture original read failed')
    return orig(p)
   oldopen=Path.open
   def injectedopen(p,*args,**kwargs):
    if name=='diagnostic_prefix_exception' and p.name=='osd-ring-header-live.bin' and args and args[0]=='rb':raise OSError('fixture diagnostic prefix unavailable')
    return oldopen(p,*args,**kwargs)
   with patch.object(Path,'read_bytes',injected),patch.object(Path,'open',injectedopen):
    try:
     for h in heads:rr.poll()
    except BaseException as e:exc=e
   pair.append(result(rr,st,exc));traces.append(q.calls)
  assert pair[0]==pair[1],(name,pair)
  assert traces[0]==traces[1],(name,traces)
  assert obs.header.count==len(heads)
  if name=='QMP_exception_after_frame':assert obs.header.last['raw_16Q'] is None
  if name=='diagnostic_prefix_exception':assert obs.header.last['words_source']=='diagnostic_prefix_unavailable'
  RECEIPTS.append({'scenario':'actual_reader_'+name,'equivalent':True,'same_QMP_sequence':traces[0],'outcome':pair[0],
    'observation':obs.header.data(),'header_counts':dict(obs.header_counts)})

class VirtualPath:
 def __init__(self,data):self.data=data;self.visible=0;self.reads=[]
 def exists(self):return True
 def open(self,mode):
  owner=self
  class Reader:
   pos=0
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def seek(self,pos):self.pos=pos
   def tell(self):return self.pos
   def read(self):
    a=self.pos;self.pos=owner.visible;owner.reads.append((a,self.pos));return owner.data[a:self.pos]
  return Reader()
 def read_bytes(self):return self.data[:self.visible]

def monitor_one(name,raw,splits,tmp,historical=False):
 vp=VirtualPath(raw);old=old_log.FullLogMonitor(vp,['FX3_SYNC100_BACKEND_BOUND','FX3_DATE99_CONSUMER_BOUND'])
 vp2=VirtualPath(raw);ob=StartupObservation(tmp/name,clock=lambda:vp2.visible);new=new_log.FullLogMonitor(vp2,['FX3_SYNC100_BACKEND_BOUND','FX3_DATE99_CONSUMER_BOUND'],startup_observation=ob)
 for end in splits:
  vp.visible=vp2.visible=end
  a=old.poll();b=new.poll();assert a==b,(name,end)
  da={k:v for k,v in old.__dict__.items() if k!='path'};db={k:v for k,v in new.__dict__.items() if k not in ('path','startup_observation')};assert da==db,(name,end)
 assert vp.reads==vp2.reads and sum(b-a for a,b in vp.reads)==len(raw)
 for token in MARKERS:
  expected=raw.find(token);found=ob.markers.get(token.decode())
  assert (found['byte_offset'] if found else -1)==expected,(name,token,expected,found)
 assert len(ob.carry)<=max(map(len,MARKERS))-1
 RECEIPTS.append({'scenario':'actual_monitor_'+name,'historical_replay':historical,'original_byte_length':len(raw),
  'poll_count':len(splits),'equivalent_selected_failure_markers_date99_state':True,'same_serial_read_ranges':True,
  'fixed_literal_first_offsets_match_raw_oracle':True,'markers':ob.markers,
  'receive_timestamps_scope':'fixture visibility offsets, NOT recovered historical host or guest times','carry_bound':len(ob.carry)})

def monitor_cases(tmp):
 raw=b'KEEP-excluded \xff\xfe utf8:'+ '中文'.encode()+b'\nFX3_SYNC100_BACKEND_BOUND\nFX3_TIMER_ENTRY '+'中文'.encode()+b'\xff\nFX3_OSD102_COMMIT no newline'
 monitor_one('arbitrary_byte_chunking',raw,list(range(1,len(raw)+1)),tmp)
 raw=b'x'*200000+b'FX3_UI_FILL_EXEC '+b'x'*200000+b'FX3_OSD102_COMMIT '
 monitor_one('long_unterminated_line',raw,list(range(4096,len(raw),4096))+[len(raw)],tmp)
 for rid in ['740bafa8','45304842','f7903939']:
  path=D.parent/'runs'/('v25gate-n64-r17-'+rid)/'serial.log';raw=old_input(path)
  monitor_one('historical_'+rid,raw,list(range(65536,len(raw),65536))+[len(raw)],tmp,True)

def main_node(path):return next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main')
def ready_nodes(path):
 tree=main_node(path);ifs=[n for n in ast.walk(tree) if isinstance(n,ast.If) and any(isinstance(x,ast.Name) and x.id=='replay_input_verified' for x in ast.walk(n.test))]
 target=next(n for n in ifs if any(isinstance(x,ast.Name) and x.id=='phaseA_capture' for x in ast.walk(n.test)))
 return target
OLD_READY=ready_nodes(B/'run_trial_r24_review_snapshot.py');NEW_READY=ready_nodes(R/'run_trial_r24_review_snapshot.py')
SERIAL='\n'.join(['FX3_AP89_SCREEN_OPEN_ENTER x id2=0x2dd',*['FX3_MEDIA_START_BRANCH x state=2']*2,
 'FX3_MEDIA_NOTIFY x mediaID=0x1000 x status=0','FX3_MEDIA_NOTIFY x mediaID=0x1010 x status=0',
 *['FX3_RM_NATIVE_FREE x bytes=%s x result=0 '%n for n in (136,28,7)],'FX3_KEY96_READY','FRONT_FULL_BODY','raw=02000007000000 '])
class FakeClock:
 def __init__(self):self.value=100;self.calls=[]
 def monotonic(self):self.calls.append('monotonic');return self.value
 def sleep(self,seconds):self.calls.append(('sleep',seconds));self.value+=seconds

def ready_eval(tmp,name,index=None,missing=False):
 pair=[];trace=[];newob=None
 for label,node in [('old',OLD_READY),('new',NEW_READY)]:
  path=tmp/(name+'-'+label);path.mkdir();ob=StartupObservation(path);clock=FakeClock();st=State()
  record={'sequence':1,'epoch':1,'PNG_sha256':'a'*64,'pixel_source_sequence':1,'nonuniform_pixels':True}
  serial=SERIAL;phase=None;replay=True;quiet=89
  if index==0:phase={'already':'ready'}
  if index==1:replay=False
  if index==2:serial=serial.replace('FX3_AP89_SCREEN_OPEN_ENTER','excluded')
  if index==3:record=None
  if index==4:quiet=95
  if index==5:serial=serial.replace('state=2','state=3',1)
  if index==6:serial=serial.replace('mediaID=0x1000','mediaID=0x1001')
  if index==7:serial=serial.replace('bytes=7 ','bytes=8 ')
  if index==8:serial=serial.replace('FX3_KEY96_READY','excluded')
  if index==9:serial=serial.replace('FRONT_FULL_BODY','excluded')
  if index==10:serial=serial.replace('raw=02000007000000 ','excluded')
  if index==11:serial=serial.replace('id2=0x2dd','id2=0x2ae')
  if index==12:record['nonuniform_pixels']=False
  if missing:record.pop('nonuniform_pixels')
  opens=list(re.finditer(r'FX3_AP89_SCREEN_OPEN_ENTER [^\n]*id2=(0x[0-9a-f]+)',serial))
  rr=SimpleNamespace(current_record=record,evidence=lambda *a:{'mock':'validated'})
  ns={'startup_observation':ob,'phaseA_capture':phase,'replay_input_verified':replay,'opens':opens,'ring_reader':rr,
      'time':clock,'last_screen_observed_at':quiet,'re':re,'serial_now':serial,'log_monitor':SimpleNamespace(native_shutdown_events=[],native_power_off_events=[]),
      'run':path,'json':json,'trial':st,'input_gate':SimpleNamespace(history=[])}
  if label=='new':ob.begin_ready()
  exc=None
  try:exec(compile(ast.Module(body=[copy.deepcopy(node)],type_ignores=[]),'actual-ready-fragment','exec'),ns)
  except BaseException as e:exc=(type(e).__name__,str(e))
  if label=='new' and exc is None:ob.end_ready(qualified=ns['phaseA_capture'] is not None,last_screen_observed_at=quiet,frame=record)
  pair.append((ns['phaseA_capture'],st.updates,exc));trace.append(clock.calls);newob=ob
 assert pair[0]==pair[1] and trace[0]==trace[1],(name,pair,trace)
 if index is not None:
  preds=newob.ready.last['predicates'];assert preds[PREDICATES[index]] is False,(name,preds)
  assert all(preds[x]=='not_evaluated' for x in PREDICATES[index+1:]),(name,preds)
 if index is None and not missing:assert all(v is True for v in newob.ready.last['predicates'].values())
 if missing:assert pair[1][2][0]=='KeyError' and newob.active_ready['evaluation_complete'] is False
 RECEIPTS.append({'scenario':'actual_ready_'+name,'equivalent_result_exit_exception':True,'original_clock_call_sequence':trace[0],
   'result':pair[0],'observation':newob.ready.data(),'incomplete':newob.active_ready})

def loop_fragment(path):
 n=next(n for n in ast.walk(main_node(path)) if isinstance(n,ast.While) and isinstance(n.test,ast.BoolOp) and any(isinstance(x,ast.Name) and x.id=='deadline' for x in ast.walk(n.test)) and any(isinstance(x,ast.Name) and x.id=='p' for x in ast.walk(n.test)))
 # Actual startup portion of original loop, ending before key processing. No surrogate predicates.
 stop=next(i for i,x in enumerate(n.body) if isinstance(x,ast.For) and isinstance(x.target,ast.Name) and x.target.id=='match')
 n=copy.deepcopy(n);n.body=n.body[:stop]+ast.parse('time.sleep(.05)').body
 return ast.fix_missing_locations(ast.Module(body=[n],type_ignores=[]))

def loop_case(tmp,name,late=False,qmp_error=False):
 outputs=[];obs=None;traces=[]
 for label,path,rm,lm in [('old',B,old_ring,old_log),('new',R,new_ring,new_log)]:
  run=tmp/('loop-'+name+'-'+label);run.mkdir();clock=FakeClock();st=State();ob=StartupObservation(run,clock=lambda:int(clock.value*1e9))
  heads=[header()] * (10 if not late else 100)+[TimeoutError('QMP fixture timeout') if qmp_error else header(1)]*100
  q=QMP(run,heads);rr=rm.TrialRingReader(run,q,st,**({'startup_observation':ob,'request_sequence':lambda:q.sequence} if label=='new' else {}))
  vp=VirtualPath(SERIAL.encode()+b'\n');vp.visible=len(vp.data);mon=lm.FullLogMonitor(vp,**({'startup_observation':ob} if label=='new' else {}))
  ns={'startup_observation':ob,'time':clock,'deadline':106 if late else 116,'p':SimpleNamespace(poll=lambda:None),'trial':st,
    'ns':SimpleNamespace(internal_hoststep=False,exit_at_phase=None),'current_command':None,'host_step':0,'log_monitor':mon,
    'ring_reader':rr,'run':run,'replay_input_verified':True,'phaseA_capture':None,'shutdown_count_at_ready':0,'power_off_count_at_ready':0,
    'last_screen_count':0,'last_screen_observed_at':100,'last_ring_poll':0,'last_nochange_frame':None,'last_nochange_key':None,
    'visual_records':[],'late_change':lambda *a:False,'next_native_file':999,'next_frame_wait':999,'re':re,'json':json,'qmp':q,
    'native_file_reads':[],'input_gate':SimpleNamespace(history=[]),'stop_cause':None,'early_stop_reason':None}
  exc=None
  try:exec(compile(loop_fragment(path/'run_trial_r24_review_snapshot.py'),'actual-startup-loop','exec'),ns)
  except BaseException as e:exc=(type(e).__name__,str(e))
  if late:
   # Explicit original finally-phase boundary, then final-only first frame.
   if label=='new':ob.phase('cleanup')
   q.heads=iter([header(1)]);rr.poll(final=True)
   assert not any(u.get('ready') for u in st.updates)
  outputs.append({'qualified':ns['phaseA_capture'] is not None,'updates':st.updates,'failure':st.stops,'exception':exc,
                 'stop_cause':ns['stop_cause'],'early_stop':ns['early_stop_reason'],'last':rr.last})
  traces.append((q.calls,clock.calls));obs=ob
 assert outputs[0]==outputs[1] and traces[0]==traces[1],(name,outputs)
 if late:assert obs.header.last['stage']=='cleanup' and obs.header.last['kind']=='valid_positive' and outputs[0]['qualified'] is False
 RECEIPTS.append({'scenario':'actual_runner_startup_loop_'+name,'same_QMP_call_sequence_and_original_clock_sleep_schedule':True,
  'QMP_calls':traces[0][0],'clock_schedule':traces[0][1],'result':outputs[0],'header_counts':dict(obs.header_counts),
  'last_header':obs.header.last,'last_ready':obs.ready.last})

def bounds_faults(tmp):
 p=tmp/'bounded';p.mkdir();o=StartupObservation(p)
 for i in range(3000):
  o.header_read(before_ns=i,after_ns=i+1,request_id_before=i,request_id_after=i+1,returned=header(i%2),file_length=256,prefix=header(i%2)[:128],source='fixture',outcome='returned')
 for bits in range(1024):
  o.begin_ready()
  for i,k in enumerate(PREDICATES):o.predicate(k,bool(bits&(1<<i)))
  o.end_ready(qualified=False,last_screen_observed_at=1,frame={'sequence':bits,'epoch':1,'PNG_sha256':'f'*64})
 assert o.ready.evicted>0 and o.ready.first_kind_omitted>0 and not o.path.exists()
 o.phase('cleanup');o.header_read(before_ns=3001,after_ns=3002,request_id_before=3001,request_id_after=3002,returned=header(1),file_length=256,prefix=header(1)[:128],source='fixture',outcome='returned')
 assert o.header.evicted>0 and o.header.initial['kind']=='valid_seq0' and o.header.last['stage']=='cleanup'
 with patch('os.fsync',side_effect=AssertionError('no diagnostic fsync permitted')):o.flush()
 assert o.saved and o.path.stat().st_size<=MAX_BYTES
 raw=o.path.read_bytes();o.flush();assert o.path.read_bytes()==raw
 bad=StartupObservation(tmp/'does-not-exist');bad.flush();assert bad.flush_attempted and not bad.saved and bad.errors['write']==1
 pred=StartupObservation(tmp);pred.begin_ready()
 with patch.object(pred,'clock',side_effect=OSError('fixture clock failure')):
  value=[];assert pred.predicate('screen_open_observed',value) is value
  pred.serial_chunk(0,b'FX3_TIMER_ENTRY ',16);pred.phase('cleanup');pred.end_ready(qualified=False,last_screen_observed_at=1,frame=None)
 assert pred.errors
 RECEIPTS.append({'scenario':'bounds_and_write_clock_faults','input_header_reads':3001,'retained_recent':len(o.header.recent),
   'evicted_transitions':o.header.evicted,'ready_evicted':o.ready.evicted,'ready_first_kind_omitted':o.ready.first_kind_omitted,'bytes':len(raw),'file_cap':MAX_BYTES,'no_per_poll_disk_write_or_fsync':True,
   'failed_write_contained':dict(bad.errors),'clock_failures_contained':dict(pred.errors)})

def guard_equivalence(tmp):
 for mode in ['success','exception','keyboard_interrupt']:
  pair=[]
  for label,path in [('old',B),('new',R)]:
   # actual module import only; its __main__ is never called
   env=tmp/('import-'+label);env.mkdir(exist_ok=True)
   import os
   os.environ['FX3_NAV_RUN_DIR']=str(env)
   g=runpy.run_path(str(path/'run_trial_r24_review_snapshot.py'),run_name='r30_test_import_only')
   trace=[]
   class Guard:
    closed=False;run=env
    def finalize(self,**kw):trace.append(('finalize',kw));self.closed=True
    def _safe_write(self,*a):trace.append(('guard_receipt',a[0]))
   fn=g['execute_runner'];fn.__globals__['ACTIVE_GUARD']=Guard();fn.__globals__['ACTIVE_HOST_JOURNAL']=None
   ob=StartupObservation(tmp/'absent-write-target')
   fn.__globals__['ACTIVE_STARTUP_OBSERVATION']=ob if label=='new' else None
   def fake_main():
    if mode=='exception':raise RuntimeError('fixture main exception')
    if mode=='keyboard_interrupt':raise KeyboardInterrupt()
    return 0
   try:code=fn(main_func=fake_main);out=('return',code)
   except BaseException as e:out=('raises',type(e).__name__)
   pair.append((out,trace))
   if label=='new':assert ob.flush_attempted and not ob.saved
  assert pair[0]==pair[1],(mode,pair)
  RECEIPTS.append({'scenario':'actual_execute_runner_'+mode,'same_original_exit_and_resource_guard_calls':True,'result':pair[0],
    'diagnostic_write_failure_did_not_skip_cleanup':True})

def main():
 with tempfile.TemporaryDirectory(prefix='r30-offline-',dir=R/'evidence') as t:
  tmp=Path(t)
  reader_cases(tmp);monitor_cases(tmp)
  ready_eval(tmp,'all_true')
  for i,k in enumerate(PREDICATES):ready_eval(tmp,k+'_false',i)
  ready_eval(tmp,'original_predicate_exception',missing=True)
  loop_case(tmp,'ready');loop_case(tmp,'cleanup_only_frame',late=True);loop_case(tmp,'QMP_exception',qmp_error=True)
  bounds_faults(tmp);guard_equivalence(tmp)
 out={'outcome':'offline_passed','scope':'actual host classes and source fragments with controlled QMP/pixels/time; no VM/browser/service or native visual validation',
      'case_count':len(RECEIPTS),'historical_inputs':INPUTS,'receipts':RECEIPTS}
 (R/'evidence/OFFLINE-RESULT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'outcome':out['outcome'],'case_count':len(RECEIPTS)}))
if __name__=='__main__':main()
