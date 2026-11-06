"""Actual runpy __main__ paths with strict no-browser/process/network dependency doubles."""
import sys,types,runpy,json,hashlib,os,time,datetime,shutil,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
mode=sys.argv[1];CASE=ROOT/'host-cli-cases'/mode;CASE.mkdir(parents=True)
actual_cfg=json.loads((ROOT/'config.json').read_text());trace=[];c={'url':'http://127.0.0.1:32123/','run':str(CASE/'run'),'runner_pid':999999,'launch_id':'11111111-1111-4111-8111-111111111111'}
(CASE/'run').mkdir();(CASE/'run/trial-web-final-receipt.json').write_text('{"acknowledged":true}')
for f in ('capture_review.js','capture_after.js'):shutil.copyfile(ROOT/f,CASE/f)
PNG=b'\x89PNG\r\n\x1a\nhost-only-not-a-real-image';SHA='a'*64;aid='22222222-2222-4222-8222-222222222222';nonce='33333333-3333-4333-8333-333333333333';state={'step':1}
def record(kind,**kw):trace.append({'kind':kind,**kw})
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,v):(CASE/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def read(name):return json.loads((CASE/name).read_text())
def identity():return c
write('current-reviewed.json',{'step':0,'sha':SHA,'gen':3,'seq':40})
folder=CASE/'step-01-attempt-01'
a={'step':1,'key':427,'path':str(folder),'nonce':nonce,'attempt_id':aid};
if mode in ('operate-confirm','operate-recovery_cancel'):
 folder.mkdir();write('current-attempt.json',a)
 (folder/'validated-image-return.json').write_text(json.dumps({'validated_new_screenshot':True,'attempt_id':aid,'firmware_png_sha256':SHA,'firmware_generation':3,'firmware_sequence':40}))
if mode.startswith('operate-click-'):
 step=int(mode.rsplit('-',1)[1]);state['step']=step
 write('current-reviewed.json',{'step':step-1,'sha':SHA,'gen':3,'seq':40})
 if step>1:write('step-%02d-confirm.json'%(step-1),{'status':'confirmed_and_cancelled'})
def capture_result(out,step):
 out=Path(out);out.mkdir();shot=out/'menu-reference-page.png';shot.write_bytes(PNG)
 r={'status':'qualified_screenshot_for_operator_review','screenshot_path':str(shot),'screenshot_file_sha256':sha(shot),'before_eval':{'before':{'step':step,'content_generation':3,'sequence':40,'png_sha256':SHA}},'after_eval':{'qualified':True,'content_generation':3,'sequence':40,'png_sha256':SHA}};(out/'capture-result.json').write_text(json.dumps(r));return r

def ev(name,code):
 record('readonly_eval_double',name=name)
 if name.endswith('capture-before'):return {'status':'ready_for_screenshot','before':{'step':2,'content_generation':3,'sequence':40,'png_sha256':SHA}}
 if name.endswith('capture-after'):return {'qualified':True,'content_generation':3,'sequence':40,'shownSHA':SHA,'frame':{'content_generation':3,'PNG_sha256':SHA}}
 if name.endswith('-before') or name.endswith('-after'):return {'step':0,'sha':SHA,'gen':3,'seq':40,'origin':1.0}
 return {'End_invoked':True} if name=='End-original-button' else {'attempt_id':aid}
def browser(name,args,*a,**kw):
 record('browser_operation_double',name=name,args=args)
 if args[0]=='screenshot':Path(args[1]).write_bytes(PNG)
 return '{}'
def dl(name,action,nonce=None):
 record('deadline_operation_double',action=action)
 if action=='arm':return {'deadline_ms':20000,'current':{'state':'armed','nonce':nonce}}
 if action=='dispose':return {'disposed':True}
 if mode=='cleanup-exception':raise RuntimeError('intentional status fetch failure')
 if mode=='cleanup-malformed':return {'current':{}}
 h={'version':1,'deadline_ms':20000,'expectedURL':c['url'],'expectedLaunchId':c['launch_id'],'sealed':False,'documentTimeOrigin':1.0,'events':[{'event':'installed'}],'current':None}
 if mode in ('cleanup-armed','cleanup-nonarmed'):
  h['current']={'nonce':'33333333-3333-4333-8333-333333333333','armed_ms':1.0,'due_ms':20001.0,'deadline_ms':20000,'state':'armed' if mode=='cleanup-armed' else 'cancelled'}
 return h

def helper(name,file,args,**kw):
 record('helper_operation_double',file=file,args=args)
 if mode=='operate-failure':raise RuntimeError('intentional host helper failure')
 def opt(flag):return args[args.index(flag)+1]
 if file=='operator_click.py':
  write('ledger.json',{'attempts':[{'status':'click_invoked','attempt_id':aid,'step':state['step']}],'recoveries':[]})
  return {'status':'click_invoked','result':{'attempt_id':aid}}
 if file=='bounded_capture_cli.py':
  r=capture_result(opt('--evidence-dir'),state['step']);write(name+'-process.json',{'returncode':0,'stdout':json.dumps(r)});return r
 if file=='explicit_confirm_cli.py':return {'status':'confirmed_and_cancelled','browser_result':{'current_frame':{'PNG_sha256':'b'*64,'content_generation':999,'sequence':999},'cancelled':{'events':[{'elapsed_ms':1000}]}}}
 if file=='recovery_tools.py':
  out=Path(opt('--out'));out.mkdir();shot=out/'current-after-cancel.png';shot.write_bytes(PNG);return {'status':'cancelled_unqueued_alarm_only','current_screenshot_path':str(shot),'current_screenshot_sha256':sha(shot)}
 raise AssertionError(file)
def run(name,args,**kw):
 record('subprocess_operation_double',argv=args)
 r=capture_result(args[-1],state['step']);write(name+'-process.json',{'returncode':0,'stdout':json.dumps(r)});return json.dumps(r)
def fake_subprocess_run(argv,**kw):
 assert argv==['python3','-B',str(CASE/'cleanup.py')]
 record('failure_cleanup_subprocess_double',argv=argv);return types.SimpleNamespace(returncode=0,stdout='host-only-End-callback',stderr='')
def absent(pid,sig):record('pid_probe_double',pid=pid);raise ProcessLookupError()
class Socket:
 def settimeout(self,*a):pass
 def connect_ex(self,*a):record('port_probe_double');return 61
 def close(self):pass
fake=types.ModuleType('common')
exports={'HERE':CASE,'CFG':actual_cfg,'FROZEN':Path(actual_cfg['frozen_root']),'OPS':Path(actual_cfg['frozen_root'])/'operator-helpers','ENV':{},'Path':Path,'json':json,'hashlib':hashlib,'time':time,'datetime':datetime,'os':types.SimpleNamespace(kill=absent),'subprocess':types.SimpleNamespace(run=fake_subprocess_run),'sha':sha,'write':write,'read':read,'identity':identity,'event':lambda *a,**kw:record('event',name=a[0]),'stamp':lambda:{'UTC':'host-only','host_ns':time.monotonic_ns()},'ev':ev,'browser':browser,'dl':dl,'helper':helper,'run':run,'wait_readonly':lambda *a:{'attempt_id':aid,'outcome':'accepted'}}
for k,v in exports.items():setattr(fake,k,v)
assert 'sys' not in vars(fake);sys.modules['common']=fake
sys.path.insert(0,str(ROOT))
if mode.startswith('cleanup-'):
 sockmod=types.ModuleType('socket');sockmod.socket=Socket;sys.modules['socket']=sockmod;source=ROOT/'cleanup.py';argv=[str(source)]
elif mode=='later-capture':
 source=ROOT/'later_capture.py';cfg=CASE/'capture-config.json';cfg.write_text(json.dumps({'prefix':'host','step':2,'url':c['url'],'launch_id':c['launch_id'],'nonce':nonce,'attempt_id':aid}));argv=[str(source),str(cfg),str(CASE/'capture')]
else:
 source=ROOT/'operate.py'
 if mode.startswith('operate-click-') or mode=='operate-failure':argv=[str(source),'click',str(state['step']),actual_cfg['steps'][state['step']-1]['target']]
 else:argv=[str(source),mode.split('operate-')[1],'亲看完整图；仅执行本次明确操作']
sys.argv=argv
error=None
try:namespace=runpy.run_path(str(source),run_name='__main__')
except RuntimeError as e:
 if mode!='operate-failure':raise
 error=str(e)
assert sha(source)==hashlib.sha256(source.read_bytes()).hexdigest()
if mode.startswith('operate-click-'):
 assert len([x for x in trace if x.get('file')=='operator_click.py'])==1 and len([x for x in trace if x.get('action')=='arm'])==1
elif mode=='operate-confirm':
 assert len([x for x in trace if x.get('file')=='explicit_confirm_cli.py'])==1
 assert read('current-reviewed.json')['gen']==3 and read('current-reviewed.json')['sha']==SHA
elif mode=='operate-recovery_cancel':assert len([x for x in trace if x.get('file')=='recovery_tools.py'])==1 and not any(x.get('action')=='arm' for x in trace)
elif mode=='operate-failure':assert error and len([x for x in trace if x['kind']=='failure_cleanup_subprocess_double'])==1
elif mode=='later-capture':assert len([x for x in trace if x.get('args',[None])[0]=='screenshot'])==1
elif mode.startswith('cleanup-'):
 external=[x for x in trace if x['kind'] in ('readonly_eval_double','browser_operation_double','deadline_operation_double')]
 assert external[0]['name']=='End-original-button'
 assert any(x.get('name')=='HAR-stop' for x in external) and any(x.get('name')=='browser-close' for x in external)
 disposes=[x for x in external if x.get('action')=='dispose'];assert bool(disposes)==(mode in ('cleanup-null','cleanup-nonarmed'))
 assert not any(x.get('action')=='cancel' for x in external)
 assert read('CLEANUP.json')['runner_alive'] is False and read('CLEANUP.json')['port_closed'] is True
if mode!='operate-failure' and source.name in ('operate.py','later_capture.py'):assert namespace['sys'] is sys
result={'passed':True,'mode':mode,'source':str(source),'source_sha256':sha(source),'actual_runpy_name':'__main__','argv':argv,'init_globals_supplied':False,'dependency_common_exports_sys':False,'browser_HTTP_QEMU_processes_started':0,'strict_external_doubles':True,'trace':trace}
write('result.json',result)
print(json.dumps({'passed':True,'mode':mode,'source_sha256':sha(source)}))
