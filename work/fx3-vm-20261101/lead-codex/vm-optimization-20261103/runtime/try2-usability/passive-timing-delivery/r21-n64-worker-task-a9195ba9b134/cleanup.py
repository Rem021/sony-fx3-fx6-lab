"""Original End first; allow original final ACK, reap, then close owned browser."""
import socket
from common import *
def cleanup():
 c=identity();errors=[];event('cleanup_entry_End_first')
 try:
  ev('End-original-button','(()=>{if(location.href!=='+json.dumps(c['url'])+'||lastStatus.launch_request_id!=='+json.dumps(c.get('launch_id'))+')throw Error("owned_page_identity");if(!finished&&!endButton.disabled){endButton.click();return {End_invoked:true}}return {End_invoked:false,finished,ending}})()')
 except Exception as e:errors.append('End: '+repr(e))
 limit=time.monotonic()+65
 while time.monotonic()<limit:
  if (Path(c['run'])/'trial-web-final-receipt.json').exists():break
  time.sleep(.2)
 try:
  ev('ended-state','({lastStatus,finished,ending,alarm:window.__fx3InteractionDeadlineV1?.status?.()})')
  browser('ended-page',['screenshot',str(HERE/'ended-page.png')],timeout=10)
  alarm=dl('deadline-after-End','status');write('deadline-after-End.json',alarm)
  if alarm.get('current',{}).get('state')!='armed':write('deadline-dispose.json',dl('deadline-dispose','dispose'))
  else:write('dispose-not-invoked.json',{'reason':'armed alarm cannot be force cancelled; owned document will close'})
 except Exception as e:errors.append('ended document: '+repr(e))
 try:browser('HAR-stop',['network','har','stop',str(HERE/'traffic.har')],timeout=15)
 except Exception as e:errors.append('HAR: '+repr(e))
 try:
  browser('browser-before-close',['session','info','--json']);browser('browser-close',['close']);browser('browser-after-close',['session','info','--json'])
 except Exception as e:errors.append('browser close: '+repr(e))
 def alive(pid):
  try:os.kill(pid,0);return True
  except ProcessLookupError:return False
 port=int(c['url'].split(':')[-1].strip('/'));s=socket.socket();s.settimeout(.3);closed=s.connect_ex(('127.0.0.1',port))!=0;s.close()
 value={'errors':errors,'runner_pid':c['runner_pid'],'runner_alive':alive(c['runner_pid']),'port_closed':closed,**stamp()};write('CLEANUP.json',value);print(json.dumps(value));return value
if __name__=='__main__':cleanup()
