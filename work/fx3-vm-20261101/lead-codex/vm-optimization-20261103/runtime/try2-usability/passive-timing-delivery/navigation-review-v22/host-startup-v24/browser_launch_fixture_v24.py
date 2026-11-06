"""Real browser preflight fixture. Never imports or executes the QEMU runner."""
import argparse,http.client,json,threading,time,signal,hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from trial_web_v22_navigation_review import TrialState,start_server,wait_for_final_receipt

HERE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--scenario',choices=['normal','start-ack-drop','start-ack-unmatched','terminal-apo'],required=True)
args=ap.parse_args();OUT=HERE/('browser-start-v24-'+args.scenario);OUT.mkdir(exist_ok=True)
state=TrialState('HOST_BROWSER_ONLY_NO_GUEST',90,4096)
if args.scenario=='terminal-apo':
 state.update(phase='finished',message='试用已结束：观察到原生关机；本轮健康未通过，资源已回收。',
  error='native_model_power_off_observed: FX3_BOOT_QUEUE_SEND source=0x830128',
  result={'health_pass':False,'qemu_exit':0,'API16_restored':True,'duration_seconds':340.857783})
else:
 state.update(phase='awaiting_launch',message='网页已连接；点击开始仅测试宿主握手，没有 guest。')
backend,bt=start_server(state,0);bp=backend.server_address[1]
rows=[];faulted=False;stop=threading.Event()
class Proxy(BaseHTTPRequestHandler):
 def log_message(self,*unused):pass
 def relay(self):
  global faulted
  data=self.rfile.read(int(self.headers.get('Content-Length','0')))
  row={'path':self.path,'method':self.command};rows.append(row)
  fault=(args.scenario in ('start-ack-drop','start-ack-unmatched') and self.path=='/api/start' and not faulted)
  if fault:faulted=True;row['fault']='drop-accepted-start-ack' if args.scenario=='start-ack-drop' else 'drop-start-before-backend'
  if fault and args.scenario=='start-ack-unmatched':
   self.close_connection=True;return
  c=http.client.HTTPConnection('127.0.0.1',bp,timeout=3)
  try:
   c.request(self.command,self.path,data,dict(self.headers));r=c.getresponse();body=r.read();row['backend_status']=r.status
   if fault:
    assert r.status==202;self.close_connection=True;return
   self.send_response(r.status)
   for k,v in r.getheaders():
    if k.lower() not in ('server','date','connection'):self.send_header(k,v)
   self.end_headers();self.wfile.write(body)
  except (BrokenPipeError,ConnectionResetError):pass
  finally:c.close()
 do_GET=relay;do_POST=relay
class Server(ThreadingHTTPServer):daemon_threads=True
proxy=Server(('127.0.0.1',0),Proxy);state.url='http://127.0.0.1:'+str(proxy.server_address[1]);pt=threading.Thread(target=proxy.serve_forever,daemon=True);pt.start()
def interrupted(*unused):stop.set();state.final_receipt_close.set()
signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
print(json.dumps({'url':state.url,'guest_started':False}),flush=True)
delivery=None;accepted_count=0
try:
 deadline=time.monotonic()+90
 while time.monotonic()<deadline and not stop.is_set():
  if args.scenario=='terminal-apo' and state.final_receipt_close.is_set():
   delivery=wait_for_final_receipt(state,timeout=0);break
  if state.launch_event.is_set() and not accepted_count:
   accepted_count=1;state.update(launch_status='running',phase='starting',message='仅宿主握手成功；fixture 没有启动 guest。')
  if state.stop.is_set():
   state.update(phase='finished',ready=False,busy=False,message='宿主 fixture 已结束；guest 从未启动。',result={'guest_started':False})
   delivery=wait_for_final_receipt(state);break
  stop.wait(.05)
finally:
 stop.set();proxy.shutdown();proxy.server_close();pt.join(timeout=2)
 backend.shutdown();backend.server_close();bt.join(timeout=2)
 (OUT/'receipt.json').write_text(json.dumps({'scenario':args.scenario,'web_sha256':hashlib.sha256((HERE/'trial_web_v22_navigation_review.py').read_bytes()).hexdigest(),
 'requests':rows,'accepted_count':accepted_count,'guest_started':False,'final_delivery':delivery,
 'threads_reaped':not pt.is_alive() and not bt.is_alive()},ensure_ascii=False,indent=2)+'\n')
