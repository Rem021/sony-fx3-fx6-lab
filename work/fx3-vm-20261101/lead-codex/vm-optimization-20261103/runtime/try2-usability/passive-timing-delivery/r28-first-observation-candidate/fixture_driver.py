"""Owned offline fixture setup/targeted checks only; actual wrapper is invoked as a subprocess."""
import hashlib,json,os,subprocess,sys,time,uuid,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SESSION='fx3-deadline-r28-44c77bd1a909'
def uid():return str(uuid.uuid4())
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def service():return json.loads((ROOT/'evidence/service/service.json').read_text())
def api(path):return json.load(urllib.request.urlopen(service()['url']+path))
def browser(*args,source=None):
 p=subprocess.run(['agent-browser','--session',SESSION,*args],input=source,text=True,capture_output=True,timeout=30)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout.strip()
def js(code):return json.loads(browser('eval','--stdin',source=code))
def wait(fn,limit=7):
 end=time.monotonic()+limit
 while time.monotonic()<end:
  v=fn()
  if v:return v
  time.sleep(.03)
 raise AssertionError('fixture readiness timeout')
def record_pids():
 info=json.loads(browser('session','info','--json'));owned={info['data']['pid']};rows=[x.split(None,2) for x in subprocess.check_output(['ps','-axo','pid=,ppid=,command='],text=True).splitlines()]
 while True:
  extra={int(x[0]) for x in rows if int(x[1]) in owned}-owned
  if not extra:break
  owned|=extra
 p=ROOT/'evidence/owned-browser-pids.json';old=json.loads(p.read_text()) if p.exists() else [];save(p,sorted(set(old)|owned))
def setup(name,mode='normal',review=True):
 browser('open','about:blank');runtime=api('fixture/reset?mode='+mode);browser('open',runtime['url']);browser('set','viewport','1280','1200');wait(lambda:js('!!lastStatus&&frameLoadedFor(lastStatus)&&!keys[0].disabled'));record_pids()
 js((ROOT/'operator-helpers/deadline.js').read_text()+'('+json.dumps({'expectedURL':runtime['url'],'expectedLaunchId':runtime['launch_id']})+')')
 run=ROOT/'evidence'/('run-'+name)
 p=subprocess.run(['python3','-B',str(ROOT/'prepare_run.py'),'--run-dir',str(run),'--task-id','task_'+name,'--dispatch-id','ctx_r28_fixture','--session',SESSION],capture_output=True,text=True);assert p.returncode==0,p.stderr
 fake=run/'fake-native-run';fake.mkdir();save(fake/'trial-web-final-receipt.json',{'MOCK':True,'not_real_QEMU_or_cleanup_proof':True})
 save(run/'runtime.json',{**runtime,'run':str(fake),'runner_pid':999999});env={**os.environ,'FX3_NAV_RUN_DIR':str(run),'PYTHONDONTWRITEBYTECODE':'1'}
 p=subprocess.run(['python3','-B','-c',"import sys;sys.path.insert(0,sys.argv[1]);from common import HERE;from untimed_image import snapshot;snapshot('fixture-initial',HERE/'initial-standby',0)",str(ROOT/'runtime-wrapper')],env=env,capture_output=True,text=True);assert p.returncode==0,p.stderr
 if review:operate(run,'standby_review','MOCK initial fixture image, no real camera/native standby proof')
 return run

def operate(run,*args,ok=True):
 start=time.monotonic_ns();p=subprocess.run(['python3','-B',str(ROOT/'runtime-wrapper/operate.py'),*args],env={**os.environ,'FX3_NAV_RUN_DIR':str(run),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=105)
 out=run/('driver-'+args[0]+'-'+str(start)+'.json');save(out,{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'start_host_ns':start,'end_host_ns':time.monotonic_ns(),'fixture_only':True})
 assert (p.returncode==0)==ok,(args,p.stdout[-1500:],p.stderr[-500:])
 return json.loads(p.stdout) if p.returncode==0 else None

def binding():
 return js('({url:location.href,launch_id:lastStatus.launch_request_id,run_incarnation:lastStatus.run_incarnation,document_id:reviewDocumentId,document_time_origin:performance.timeOrigin,step:currentKeyAttempt.expected_step,attempt_id:currentKeyAttempt.attempt_id,nonce:currentKeyAttempt.alarm_nonce})')
def direct_capture(run,name,n):
 b=binding();bp=run/(name+'-binding.json');reservation=run/(name+'-reservation.json');save(bp,b);save(reservation,{'status':'reserved_unknown','reservation_id':uid(),'observation_number':n,'binding':b});out=run/name
 p=subprocess.run(['python3','-B',str(ROOT/'operator-helpers/postkey_observation.py'),'--session',SESSION,'--binding',str(bp),'--reservation',str(reservation),'--out',str(out)],capture_output=True,text=True,timeout=25)
 save(run/(name+'-process.json'),{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});return json.loads(p.stdout)

if __name__=='__main__':
 if sys.argv[1]=='setup':print(json.dumps({'run_dir':str(setup(sys.argv[2],review=False)),'fixture_only':True}))
