"""Original End first; classify alarm explicitly, preserve HAR/close, await final exit."""
import socket, math, re
from common import *

def alarm_disposition(value,c):
 if not isinstance(value,dict):return 'unknown_malformed'
 if (value.get('version')!=1 or value.get('deadline_ms')!=20000 or
     value.get('expectedURL')!=c['url'] or value.get('expectedLaunchId')!=c['launch_id'] or
     type(value.get('sealed')) is not bool or type(value.get('documentTimeOrigin')) not in (int,float) or
     not math.isfinite(value['documentTimeOrigin']) or not isinstance(value.get('events'),list) or 'current' not in value):return 'unknown_malformed'
 current=value['current']
 if current is None:
  return 'valid_null_never_armed' if not any(isinstance(e,dict) and e.get('event') in ('armed','cancelled','expired') for e in value['events']) else 'unknown_malformed'
 if not isinstance(current,dict):return 'unknown_malformed'
 if (not isinstance(current.get('nonce'),str) or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',current['nonce']) or
     any(type(current.get(k)) not in (int,float) or not math.isfinite(current[k]) for k in ('armed_ms','due_ms')) or
     current['due_ms']-current['armed_ms']!=20000 or current.get('deadline_ms')!=20000):return 'unknown_malformed'
 if current.get('state')=='armed':return 'valid_armed_do_not_cancel_or_dispose'
 if current.get('state') in ('cancelled','expired'):return 'valid_nonarmed'
 return 'unknown_malformed'

def cleanup():
 c=identity();errors=[];event('cleanup_entry_End_first')
 try:
  ev('End-original-button','(()=>{if(location.href!=='+json.dumps(c['url'])+'||lastStatus.launch_request_id!=='+json.dumps(c.get('launch_id'))+')throw Error("owned_page_identity");if(!finished&&!endButton.disabled){endButton.click();return {End_invoked:true}}return {End_invoked:false,finished,ending}})()')
 except Exception as e:errors.append('End: '+repr(e))
 limit=time.monotonic()+65
 while time.monotonic()<limit:
  if (Path(c['run'])/'trial-web-final-receipt.json').exists():break
  time.sleep(.2)
 else:errors.append('final browser ACK receipt absent within cleanup wait')
 try:
  ev('ended-state','({lastStatus,finished,ending,alarm:window.__fx3InteractionDeadlineV1?.status?.()})')
  browser('ended-page',['screenshot',str(HERE/'ended-page.png')],timeout=10)
 except Exception as e:errors.append('ended document capture: '+repr(e))
 disposition='unknown_status_fetch_failed'
 try:
  alarm=dl('deadline-after-End','status');write('deadline-after-End.json',alarm);disposition=alarm_disposition(alarm,c)
  if disposition in ('valid_null_never_armed','valid_nonarmed'):
   write('deadline-dispose.json',dl('deadline-dispose','dispose'))
  else:write('dispose-not-invoked.json',{'reason':disposition,'alarm_cleanup':'no cancel/no dispose; owned document closes below'})
 except Exception as e:errors.append('alarm status/dispose: '+repr(e))
 write('ALARM-DISPOSITION.json',{'classification':disposition,'forced_cancel':False})
 try:browser('HAR-stop',['network','har','stop',str(HERE/'traffic.har')],timeout=15)
 except Exception as e:errors.append('HAR: '+repr(e))
 try:browser('browser-before-close',['session','info','--json'])
 except Exception as e:errors.append('browser before-close info: '+repr(e))
 try:browser('browser-close',['close'])
 except Exception as e:errors.append('browser close: '+repr(e))
 try:browser('browser-after-close',['session','info','--json'])
 except Exception as e:errors.append('browser after-close info: '+repr(e))
 def alive(pid):
  try:os.kill(pid,0);return True
  except ProcessLookupError:return False
 port=int(c['url'].split(':')[-1].strip('/'))
 def portclosed():
  s=socket.socket();s.settimeout(.3)
  try:return s.connect_ex(('127.0.0.1',port))!=0
  finally:s.close()
 limit=time.monotonic()+5
 while True:
  running=alive(c['runner_pid']);closed=portclosed()
  if (not running and closed) or time.monotonic()>=limit:break
  time.sleep(.05)
 if running or not closed:errors.append('final runner PID/port not closed within bounded wait')
 value={'errors':errors,'alarm_disposition':disposition,'runner_pid':c['runner_pid'],'runner_alive':running,'port_closed':closed,'bounded_final_recheck_seconds':5,**stamp()};write('CLEANUP.json',value);print(json.dumps(value));return value
if __name__=='__main__':cleanup()
