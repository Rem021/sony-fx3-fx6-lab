import datetime,hashlib,json,os,subprocess,threading,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
CFG=json.loads((HERE/'config.json').read_text());FROZEN=Path(CFG['frozen_root']);OPS=FROZEN/'operator-helpers'
ENV={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','AGENT_BROWSER_NO_VERSION_CHECK':'1'}
def stamp():return {'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host_ns':time.monotonic_ns()}
def write(name,data):
 (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def read(name):return json.loads((HERE/name).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def event(stage,**kw):
 with (HERE/'tool-timeline.jsonl').open('a') as f:f.write(json.dumps({'stage':stage,**stamp(),**kw},ensure_ascii=False)+'\n')
def run(name,args,source=None,timeout=20,watch=False):
 start=stamp();event(name+'_enter',argv=args)
 stop=threading.Event()
 def observe():
  last=None
  while not stop.is_set():
   try:
    raw=(HERE/'ledger.json').read_text()
    if raw!=last:
     value=json.loads(raw)
     with (HERE/'ledger-observations.jsonl').open('a') as f:f.write(json.dumps({**stamp(),'during':name,'ledger':value})+'\n')
     last=raw
   except (FileNotFoundError,json.JSONDecodeError):pass
   stop.wait(.001)
 t=threading.Thread(target=observe)
 if watch:t.start()
 try:
  p=subprocess.run(args,input=source,text=True,capture_output=True,timeout=timeout,env=ENV)
  record={'argv':args,'start':start,'end':stamp(),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
  write(name+'-process.json',record)
 finally:
  stop.set()
  if watch:t.join()
 event(name+'_exit',returncode=p.returncode)
 if p.returncode:raise RuntimeError(name+' failed: '+p.stdout[-1000:]+p.stderr[-500:])
 return p.stdout

def browser(name,args,source=None,timeout=20):return run(name,['agent-browser','--session',CFG['session'],*args],source,timeout)
def ev(name,source):return json.loads(browser(name,['eval','--stdin'],source))
def helper(name,file,args,watch=False):return json.loads(run(name,['python3',str(OPS/file),*args],watch=watch))
def identity():return read('runtime.json')
def dl(name,action,nonce=None):
 c=identity();a=[action,'--session',CFG['session'],'--url',c['url'],'--launch-id',c['launch_id']]
 if nonce:a+=['--nonce',nonce]
 return helper(name,'deadline_cli.py',a)
def wait_readonly(name,expression):
 # Only polls readonly page state; no mutation or helper invocation here.
 source='(async()=>{const until=performance.now()+4000;while(performance.now()<until){const x=('+expression+');if(x)return x;await new Promise(r=>setTimeout(r,25));}throw Error("readonly condition timeout")})()'
 return ev(name,source)
def validated(name,process_name,result,folder,kind):
 process=read(process_name+'-process.json');assert process['returncode']==0
 mapping={'review':('qualified_review_screenshot','screenshot_path','screenshot_sha256','review-page.png'),'cancel':('cancelled_unqueued_alarm_only','current_screenshot_path','current_screenshot_sha256','current-after-cancel.png'),'menu':('qualified_screenshot_for_operator_review','screenshot_path','screenshot_file_sha256','menu-reference-page.png')}
 status,pathkey,hashkey,filename=mapping[kind];assert result.get('status')==status,result
 expected=HERE/folder;p=Path(result[pathkey]);assert p.is_absolute() and p==expected/filename
 assert expected.is_dir() and not expected.is_symlink() and p.is_file() and not p.is_symlink() and p.resolve().parent==expected.resolve()
 assert p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') and sha(p)==result[hashkey]
 # Folder nonexistence is enforced by caller and original helper's exclusive mkdir.
 assert p.stat().st_mtime_ns>=read('attempt-origin.json')['host_wall_ns']
 value={'status':status,'validated':True,'screenshot_path':str(p),'screenshot_sha256':sha(p),'validation_boundary':stamp(),'model_received_at':'unknown','model_review_completed_at':'unknown'}
 write(name,value);event(name,**value);return value
