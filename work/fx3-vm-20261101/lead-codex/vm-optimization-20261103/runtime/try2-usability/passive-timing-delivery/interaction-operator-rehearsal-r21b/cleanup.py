"""End first, final ACK, close only this browser and fixture, then verify exit/port."""
import signal,socket
from common import *
errors=[];c=identity();event('cleanup_entry')
try:
 write('cleanup-alarm-before-End.json',dl('cleanup-alarm-before-End','status'))
except Exception as e:errors.append('alarm status before End: '+repr(e))
try:
 result=ev('End-explicit-original-button','(()=>{if(!finished&&!endButton.disabled){endButton.click();return {End_invoked:true}}return {End_invoked:false,finished}})()')
 wait_readonly('wait-ended-status','finished&&lastStatus.phase==="finished"&&lastStatus')
 # The original PAGE issues final ACK after showing finished; no direct HTTP fallback.
 limit=time.monotonic()+4
 while time.monotonic()<limit:
  logs=(HERE/'fixture-events.jsonl').read_text().splitlines()
  if any('"path": "/api/final-ack"' in x and '"HTTP_status": 200' in x for x in logs):break
  time.sleep(.02)
 else:raise RuntimeError('missing final ACK')
 browser('ended-page',['screenshot',str(HERE/'ended-page.png')]);browser('ended-snapshot',['snapshot'])
 try:
  alarm=dl('cleanup-alarm-after-End','status');write('cleanup-alarm-after-End.json',alarm)
  if alarm.get('current',{}).get('state')=='armed':
   write('dispose-not-invoked.json',{'reason':'accepted/unknown alarm remains armed; do not force cancel to dispose','timer_termination':'owned document close below; not explicit cancellation',**stamp()})
  else:write('deadline-dispose.json',dl('deadline-dispose','dispose'))
 except Exception as e:errors.append('dispose/status: '+repr(e))
except Exception as e:errors.append('End/finalACK: '+repr(e))
try:
 # State-only command does not launch a replacement browser.
 browser('browser-before-close',['session','info','--json'])
 browser('browser-close',['close'])
 browser('browser-after-close',['session','info','--json'])
except Exception as e:errors.append('browser close: '+repr(e))
try:
 os.kill(c['pid'],signal.SIGTERM)
except ProcessLookupError:pass
limit=time.monotonic()+5
while time.monotonic()<limit:
 try:os.kill(c['pid'],0)
 except ProcessLookupError:break
 time.sleep(.03)
try:os.kill(c['pid'],0);alive=True
except ProcessLookupError:alive=False
from urllib.parse import urlsplit
port=urlsplit(c['url']).port;s=socket.socket();s.settimeout(.3);code=s.connect_ex(('127.0.0.1',port));s.close()
closed=read('fixture-closed.json') if (HERE/'fixture-closed.json').exists() else {}
write('CLEANUP.json',{'fixture_pid':c['pid'],'pid_alive':alive,'port':port,'connect_ex':code,'port_closed':code!=0,'fixture_closed':closed,'errors':errors,**stamp()})
print(json.dumps({'pid_alive':alive,'port_closed':code!=0,'errors':errors}))
