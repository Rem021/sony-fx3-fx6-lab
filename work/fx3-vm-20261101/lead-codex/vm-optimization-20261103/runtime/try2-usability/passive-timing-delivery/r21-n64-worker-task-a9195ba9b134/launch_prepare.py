from common import *
from preflight import verify
import fcntl,plistlib,re,shlex

def exclusive(name,allow_self=False):
 disk=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert disk['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 processes=[]
 for line in subprocess.check_output(['ps','-axo','pid=,args='],text=True).splitlines():
  x=line.strip().split(None,1)
  if len(x)!=2:continue
  pid=int(x[0]);args=x[1].split();exe=Path(args[0]).name if args else ''
  if exe.startswith('qemu-') or (exe.lower().startswith(('python','python3')) and any('run_trial_v25_diag_r3.py' in a for a in args[1:])):
   if not (allow_self and pid==identity()['runner_pid']):processes.append({'pid':pid,'argv':args})
 assert not processes,processes
 locks=[]
 for p in [Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/.run.lock'),Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/.run.lock')]:
  with p.open('rb') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
  locks.append({'path':str(p),'free_at_probe':True})
 write(name,{'volume_uuid':disk['VolumeUUID'],'conflicting_processes':processes,'locks':locks,**stamp()})

def main():
 assert read('PREFLIGHT-RESULT.json')['passed'];assert not (HERE/'runtime.json').exists();exclusive('EXCLUSIVE-BEFORE-SERVER.json')
 verify('INPUTS-SERVER-START.json')
 argv=['python3','-B',str(FROZEN/'run_trial_v25_diag_r3.py'),'--port','0','--max-minutes','8','--max-steps','32','--snapshot-tail','--gate-publish-interval','64','--pre-input-snapshot-step','2']
 p=subprocess.Popen(argv,stdout=(HERE/'runner-stdout.txt').open('x'),stderr=(HERE/'runner-stderr.txt').open('x'),env=ENV,start_new_session=True)
 write('RUNNER-LAUNCH.json',{'pid':p.pid,'argv':argv,**stamp()})
 limit=time.monotonic()+15
 while time.monotonic()<limit:
  text=(HERE/'runner-stdout.txt').read_text();m=re.search(r'http://127\.0\.0\.1:\d+/?',text)
  if m:break
  assert p.poll() is None,(HERE/'runner-stderr.txt').read_text();time.sleep(.05)
 else:raise RuntimeError('server URL missing')
 url=m.group(0).rstrip('/')+'/'
 candidates=[]
 for f in FROZEN.parent.parent.joinpath('runs').glob('*/command.json'):
  if f.stat().st_mtime_ns>=(HERE/'RUNNER-LAUNCH.json').stat().st_mtime_ns-1000000000:candidates.append(f)
 assert len(candidates)==1,candidates
 run=candidates[0].parent;cmd=json.loads(candidates[0].read_text());args=cmd['args'];q=Path(args[0]);assert sha(q)=='bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d'
 assert args[args.index('-cpu')+1]=='cortex-a35' and args[args.index('-smp')+1]=='4' and args[args.index('-m')+1]=='5120' and args[args.index('-accel')+1]=='tcg,thread=multi' and '-icount' not in args
 write('runtime.json',{'url':url,'run':str(run),'runner_pid':p.pid,'launch_id':None})
 write('ACTUAL-ARGV-PREPARED.json',{'qemu_sha256':sha(q),'command':cmd,**stamp()})
 browser('browser-open',['open',url]);browser('viewport',['set','viewport','1280','1200']);browser('HAR-start',['network','har','start'])
 browser('await-start-enabled',['wait','--fn','!!lastStatus&&lastStatus.browser_ready&&!startButton.disabled'])
 v=ev('PAGE-before-Start',r'''(async()=>{const s=[...document.scripts],d=async t=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(t)))].map(x=>x.toString(16).padStart(2,'0')).join('');return {canonical_sha:await d(s[0].textContent.replace(/^const token=[^\r\n]*;$/m,'const token=__TOKEN__;')),lastStatus,viewport:[innerWidth,innerHeight]};})()''')
 assert v['canonical_sha']=='f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab' and v['lastStatus']['phase']=='awaiting_launch' and v['viewport']==[1280,1200]
 tabs=json.loads(browser('owned-tab-prestart',['tab','--json']))['data']['tabs'];assert len(tabs)==1 and tabs[0]['url']==url
 browser('prestart-screenshot',['screenshot',str(HERE/'prestart.png')]);write('PRESTART-READY.json',{'passed':True,'actual_cli_steps':[{'step':x['step'],'click_command':['python3','-B',str(HERE/'operate.py'),'click',str(x['step']),x['target']],'confirm_command':['python3','-B',str(HERE/'operate.py'),'confirm','亲看并确认 '+x['target']]} for x in CFG['steps']],'bindings':'one exclusive step-N-attempt-N dir / new nonce generated before arm; helper CLI arguments fully wired from runtime.json','cancel_command':['python3','-B',str(HERE/'operate.py'),'recovery_cancel','仅取消同nonce未入队alarm'],'end_command':['python3','-B',str(HERE/'cleanup.py')],'tab':tabs[0],**stamp()})
 write('LOCAL-SOURCE-FREEZE.json',{p.name:sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.js')});print(json.dumps({'status':'web_prepared_guest_not_started','run':str(run),'url':url,'session':CFG['session']}))
if __name__=='__main__':main()
