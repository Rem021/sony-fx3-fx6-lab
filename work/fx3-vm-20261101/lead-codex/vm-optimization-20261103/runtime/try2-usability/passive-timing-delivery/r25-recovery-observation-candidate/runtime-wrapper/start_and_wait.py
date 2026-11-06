from common import *
from launch_prepare import exclusive
from untimed_image import snapshot
import signal

def main():
 assert read('PRESTART-READY.json')['passed'];assert not (HERE/'Start-once').exists()
 for f,h in read('LOCAL-SOURCE-FREEZE.json').items():assert sha(f)==h
 exclusive('EXCLUSIVE-BEFORE-Start.json',allow_self=True)
 (HERE/'Start-once').open('x').close();start_monotonic=time.monotonic();browser('Start-original-button',['click','#start'])
 c=identity();launch=wait_readonly('launch-identity','lastStatus?.launch_request_id&&({launch_id:lastStatus.launch_request_id})')['launch_id'];c['launch_id']=launch;write('runtime.json',c)
 write('deadline-install.json',dl('deadline-install','install'))
 # Bound first frame by host monotonic deadline, smaller polling calls allow status updates.
 deadline=start_monotonic+180
 write('FIRST-FRAME-CLOCK.json',{'limit_seconds':180,'start_monotonic':start_monotonic,**stamp()})
 while time.monotonic()<deadline:
  state=ev('first-frame-poll','({ready:!!lastStatus?.ready,loaded:!!lastStatus&&frameLoadedFor(lastStatus),phase:lastStatus?.phase,error:lastStatus?.error,finished})')
  if state['ready'] and state['loaded']:break
  if state['error'] or state['finished']:raise RuntimeError('startup failed: '+json.dumps(state))
  time.sleep(1)
 else:raise RuntimeError('first frame not ready by 180 seconds')
 image=snapshot('initial-standby',HERE/'initial-standby',0);write('current-observation.json',{**image['firmware'],'basis':'historical screenshot pending separate standby_review; no current-generation permission'});write('FIRST-FRAME-PASS.json',{'passed':True,**stamp()})
 cmd=json.loads((Path(c['run'])/'command.json').read_text());session=json.loads((Path(c['run'])/'trial-session.json').read_text());pid=session['qemu_pid'];actual=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip();assert str(cmd['args'][0]) in actual and sha(cmd['args'][0])=='bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d';write('ACTUAL-RUNNING-ARGV.json',{'pid':pid,'ps_command':actual,'command_json_args':cmd['args'],'qemu_sha256':sha(cmd['args'][0]),**stamp()});print(json.dumps(image))
if __name__=='__main__':
 try:main()
 except BaseException as e:
  write('STARTUP-FAILURE.json',{'error':repr(e),**stamp()})
  p=subprocess.run(['python3','-B',str(SOURCE/'cleanup.py')],capture_output=True,text=True,env=ENV,timeout=100);write('STARTUP-FAILURE-CLEANUP.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});raise
