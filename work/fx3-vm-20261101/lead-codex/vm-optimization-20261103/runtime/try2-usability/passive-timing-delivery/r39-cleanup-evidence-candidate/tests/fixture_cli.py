"""OFFLINE ONLY: actual r39 CLI with browser/process/port/native mocks, real APFS evidence/flock."""
import errno,json,os,plistlib,runpy,subprocess,sys,time
from pathlib import Path
O=Path(__file__).resolve().parents[1];here=Path(os.environ['FX3_NAV_RUN_DIR']);scenario=sys.argv[1];mode=sys.argv[2] if len(sys.argv)>2 else 'cleanup'
sys.path.insert(0,str(O/'runtime-wrapper'));import common as C
E=C.evidence;E.RUNS=here/'native-runs';E.LOCKS=[here/'platform-lock-1',here/'platform-lock-2']
c=C.identity();calls=[];active=True;live=scenario in ('broken-index-live','cross-index-live','wrong-current-owner','wrong-current-page')
stats=here/('mock-calls-'+str(os.getpid())+'.json')
def record(kind,**kw):
 calls.append({'kind':kind,**kw});stats.write_text(json.dumps(calls,indent=2)+'\n')
def pid_probe(pid,sig):
 record('pid_probe',pid=pid)
 if live and pid in (52001,52002):return
 if scenario=='resource-fail':raise PermissionError('fixture resource check failed')
 if scenario=='runner-live' and pid==c['runner_pid']:return
 if scenario=='qemu-live' and pid==52002:return
 raise ProcessLookupError()
C.os.kill=pid_probe
class MockSocket:
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
 def settimeout(self,x):pass
 def connect_ex(self,address):
  record('port_probe',address=address)
  if scenario=='port-fail':return errno.ETIMEDOUT
  return 0 if live or scenario=='port-live' else errno.ECONNREFUSED
 def close(self):pass
import socket
socket.socket=lambda *a,**kw:MockSocket()
orig_run=subprocess.run
alarm={'version':1,'deadline_ms':20000,'expectedURL':c['url'],'expectedLaunchId':c['launch_id'],'sealed':True,'documentTimeOrigin':9000.5,'events':[{'event':'installed'}],'current':None}
if scenario=='armed':alarm['current']={'nonce':'22222222-3333-4444-5555-666666666666','state':'armed','armed_ms':100,'due_ms':20100,'deadline_ms':20000}
if scenario=='malformed-alarm':alarm.pop('documentTimeOrigin')
def fake_run(args,**kwargs):
 global active,live
 if args and args[0]=='ps':
  if args[-1]=='command=':
   argv=json.loads((here/'RUNNER-LAUNCH.json').read_text())['argv'];value=' '.join(argv) if scenario!='wrong-current-owner' else 'python3 -B unrelated.py'
  elif args[-1]=='ppid=':value='52001'
  elif args[-1]=='comm=':value='fixture-qemu-executable'
  else:raise RuntimeError('unexpected fixture ps')
  record('current_process_identity',field=args[-1]);return subprocess.CompletedProcess(args,0,value,'')
 if args[:3]==['diskutil','info','-plist']:
  return subprocess.CompletedProcess(args,0,plistlib.dumps({'VolumeUUID':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'}),b'')
 if args[0]=='agent-browser':
  op=args[3:];record('browser',argv=op)
  rc=0;value=''
  if op[:2]==['eval','--stdin']:
   src=kwargs['input']
   if 'End_invoked' in src:
    record('End')
    if scenario=='exclusive-stage-collision':(E.ACTIVE.get()['dir']/'End-original-button-process.json').write_bytes(b'fixture original sentinel')
    if scenario=='interrupt':os._exit(93)
    if scenario=='owner':
     (here/'owner-entered').write_text('held')
     limit=time.monotonic()+8
     while not (here/'release-owner').exists() and time.monotonic()<limit:time.sleep(.01)
     if not (here/'release-owner').exists():raise RuntimeError('fixture owner release timeout')
    if scenario=='transport':raise subprocess.TimeoutExpired(args,kwargs['timeout'],output='partial stdout',stderr='partial stderr')
    if scenario=='end-fail':return subprocess.CompletedProcess(args,1,'','fixture End error')
    live=False
    if (here/'pending-native').exists():
     native=Path(c['run'])
     for p in (here/'pending-native').iterdir():(native/p.name).write_bytes(p.read_bytes())
    value={'End_invoked':True}
   elif 'current_owned_lifecycle_unknown' in src:value={'url':c['url'],'launch_id':c['launch_id'] if scenario!='wrong-current-page' else 'different-launch','document_id':'fixture-document','document_time_origin':9000.5,'run_incarnation':'fixture-incarnation'}
   else:value={'lastStatus':{'phase':'finished','launch_request_id':c['launch_id'],'run_incarnation':'fixture-incarnation'},'finished':True,'ending':True,'url':c['url'],'document_time_origin':9000.5,'document_id':'fixture-document','alarm':alarm}
  elif op[0]=='screenshot':Path(op[1]).write_bytes(b'\x89PNG\r\n\x1a\nMOCK CLEANUP PNG');value='mock screenshot only'
  elif op[:3]==['network','har','stop']:
   record('HAR');Path(op[3]).write_text(json.dumps({'log':{'version':'1.2','entries':[{'fixture':True}]}}));value='mock har stopped'
  elif op[:2]==['session','info']:value={'success':True,'data':{'session':C.CFG['session'],'active':active,'pid':53003 if active else None}}
  elif op[0]=='close':record('close');active=False;value='mock closed'
  else:raise RuntimeError('unexpected browser mock argv:'+repr(args))
  return subprocess.CompletedProcess(args,rc,json.dumps(value) if isinstance(value,dict) else value,'')
 if Path(args[0]).name.startswith('python') and Path(args[1]).name=='deadline_cli.py':
  record('deadline',action=args[2]);return subprocess.CompletedProcess(args,0,json.dumps(alarm),'')
 # The only real child allowed here is the original operate failure dispatch to
 # this same fixture entry, whose __main__ executes the actual cleanup.py.
 if args[:2]==['python3','-B'] and Path(args[2]).name=='cleanup.py':
  record('failure_dispatch_once')
  return orig_run([sys.executable,'-B',str(Path(__file__).resolve()),'success','cleanup'],**kwargs)
 raise RuntimeError('FORBIDDEN unexpected process:'+repr(args))
subprocess.run=fake_run
# Only custom test locks are real; production locks/QMP/ports are never touched.
if scenario in ('stage-write-fail','invocation-write-fail'):
 original=E.put
 def bad_put(p,v):
  if Path(p).name==('invocation.json' if scenario=='invocation-write-fail' else 'End-original-button-process.json'):raise OSError('fixture receipt stage write failed')
  return original(p,v)
 E.put=bad_put
elif scenario in ('result-write-fail','index-write-fail'):
 original=E.put
 def bad_put(p,v):
  if Path(p).name==('result.json' if scenario=='result-write-fail' else 'CLEANUP-COMPLETED.json'):raise OSError('fixture receipt publication failed')
  return original(p,v)
 E.put=bad_put
try:
 if mode=='audit':runpy.run_path(str(O/'runtime-wrapper/audit_after.py'),run_name='__main__')
 elif mode=='operate-fail':
  # Actual entry/guard/failcleanup executes; a semantic action failure is
  # injected at its action boundary, never an input/VM call.
  g=runpy.run_path(str(O/'runtime-wrapper/operate.py'),run_name='fixture_operate_import_only')
  def fail(action):raise ValueError('fixture original action must stay failed')
  g['run_action'].__globals__['_run_action']=fail
  try:g['run_action']('pin')
  except ValueError:raise SystemExit(19)
  raise AssertionError('original action failure swallowed')
 else:runpy.run_path(str(O/'runtime-wrapper/cleanup.py'),run_name='__main__')
finally:
 stats.write_text(json.dumps(calls,indent=2)+'\n')
