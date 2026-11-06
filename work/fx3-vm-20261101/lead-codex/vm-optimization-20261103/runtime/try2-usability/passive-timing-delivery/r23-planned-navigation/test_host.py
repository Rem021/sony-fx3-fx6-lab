"""Actual runpy __main__ wrapper routes with strictly labelled external protocol doubles; no browser/VM/real visual approval."""
import base64,hashlib,json,os,runpy,subprocess,sys,time,types,uuid
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent;WRAPPER=ROOT/'runtime-wrapper';OUT=ROOT/'evidence'
if len(sys.argv)==1:
 results=[]
 for mode in ['step2_unconfirmed','confirm_exact_historical_image','cross_step_confirm_refused']:
  ident='host3_'+mode;d=OUT/('run-'+ident)
  prepare=['python3','-B',str(ROOT/'prepare_run.py'),'--run-dir',str(d),'--task-id','task_'+ident,'--dispatch-id','ctx_offline_fixture','--session','fx3-deadline-r23-host-fixture']
  p=subprocess.run(prepare,capture_output=True,text=True);assert p.returncode==0,p.stderr
  env={**os.environ,'FX3_NAV_RUN_DIR':str(d),'PYTHONDONTWRITEBYTECODE':'1'}
  p=subprocess.run(['python3','-B',str(__file__),mode],capture_output=True,text=True,env=env)
  (OUT/('host3-'+mode+'.process.json')).write_text(json.dumps({'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'fixture_only':True},indent=2)+'\n')
  assert p.returncode==0,p.stderr
  results.append(json.loads((d/'HOST-CASE-RESULT.json').read_text()))
 (OUT/'HOST-RESULT.json').write_text(json.dumps({'passed':True,'cases':results,'scope':__doc__},indent=2)+'\n')
 print(json.dumps({'passed':True,'cases':len(results)}));raise SystemExit()
mode=sys.argv[1];d=Path(os.environ['FX3_NAV_RUN_DIR']);sys.path.insert(0,str(WRAPPER));sys.path.insert(0,str(ROOT/'operator-helpers'))
import common
from capture_validation import validate_capture
assert 'sys' not in vars(common)
launch=str(uuid.uuid4());nonce=str(uuid.uuid4());aid=str(uuid.uuid4());trace=[]
c={'url':'http://127.0.0.1:32123/','launch_id':launch,'run':str(d/'fixture-run'),'runner_pid':999999};common.write('runtime.json',c)
folder=d/'step-01-attempt-01';folder.mkdir();image=folder/'capture';image.mkdir();shot=image/'menu-reference-page.png'
# Actual PNG bytes, but its semantic approval is a protocol oracle only.
shot.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5x8AAAAASUVORK5CYII='))
sha=hashlib.sha256(shot.read_bytes()).hexdigest();firmware_sha='a'*64
raw={'status':'qualified_screenshot_for_operator_review','screenshot_path':str(shot),'screenshot_file_sha256':sha,
     'before_eval':{'before':{'step':1,'content_generation':3,'sequence':40,'png_sha256':firmware_sha}},
     'after_eval':{'qualified':True,'step':1,'content_generation':3,'sequence':40,'png_sha256':firmware_sha}}
cap=validate_capture(0,json.dumps(raw),image);cap.update(step=1,attempt_number=1,attempt_id=aid,nonce=nonce)
common.write('current-attempt.json',{'step':1,'key':427,'path':str(folder),'nonce':nonce,'attempt_id':aid})
if mode=='cross_step_confirm_refused':cap['step']=2
(folder/'validated-image-return.json').write_text(json.dumps(cap)+'\n')
wrong={**raw,'after_eval':{**raw['after_eval'],'step':2}}
try:validate_capture(0,json.dumps(wrong),image)
except AssertionError:trace.append({'cross_step_capture_refused':True})
else:raise AssertionError('cross-step capture accepted')

def ev(name,code):
 trace.append({'readonly_eval_double':name,'code_sha256':hashlib.sha256(code.encode()).hexdigest()})
 return {'attempt_id':aid,'expected_step':1,'outcome':'accepted'}
def helper(name,file,args,**kw):
 trace.append({'helper_double':file,'argv':args})
 assert file=='explicit_confirm_cli.py'
 def opt(k):return args[args.index(k)+1]
 assert opt('--step')=='1' and opt('--png-sha')==firmware_sha and opt('--nonce')==nonce
 expected={'request_id':str(uuid.uuid4()),'step':1,'observed_sequence':40,'content_generation':3,'PNG_sha256':firmware_sha}
 value={'status':'confirmed_and_cancelled','step':1,'launch_id':launch,'alarm_nonce':nonce,'reviewed_png_sha256':firmware_sha,
        'browser_result':{'expected':expected,'cancelled':{'documentTimeOrigin':1.0,'current':{'nonce':nonce,'state':'cancelled'},'events':[{'elapsed_ms':1000}]},
                          'current_frame':{'PNG_sha256':'b'*64,'content_generation':999,'sequence':999}}}
 Path(opt('--receipt')).write_text(json.dumps(value)+'\n');return value
realrun=subprocess.run

def cleanup_only(args,**kw):
 assert args==['python3','-B',str(WRAPPER/'cleanup.py')],args
 trace.append({'cleanup_external_double':args});return types.SimpleNamespace(returncode=0,stdout='fixture-original-End-callback-only',stderr='')
sys.argv=[str(WRAPPER/'operate.py'), 'click','2','fixture missing previous confirmation'] if mode=='step2_unconfirmed' else [str(WRAPPER/'operate.py'),'confirm','fixture protocol oracle only; no real visual judgement']
error=None
with patch.object(common,'ev',ev),patch.object(common,'helper',helper),patch.object(subprocess,'run',cleanup_only):
 try:namespace=runpy.run_path(str(WRAPPER/'operate.py'),run_name='__main__')
 except (FileNotFoundError,ValueError,AssertionError) as exc:error=type(exc).__name__
if mode=='confirm_exact_historical_image':
 assert error is None
 v=json.loads((d/'step-01-prerequisite.json').read_text());actual=json.loads(Path(v['observation_path']).read_text())
 assert actual['firmware_generation']==3 and actual['firmware_png_sha256']==firmware_sha
 assert len([x for x in trace if 'helper_double' in x])==1
 assert namespace['sys'] is sys
else:
 assert error and not any('helper_double' in x for x in trace)
 assert len([x for x in trace if 'cleanup_external_double' in x])==1
result={'passed':True,'mode':mode,'scope':'host protocol doubles only; no real visual review, browser, HTTP, runner or guest started',
        'actual_runpy_name':'__main__','init_globals_supplied':False,'common_exports_sys':False,'error':error,'trace':trace}
common.write('HOST-CASE-RESULT.json',result);print(json.dumps({'passed':True,'mode':mode}))
