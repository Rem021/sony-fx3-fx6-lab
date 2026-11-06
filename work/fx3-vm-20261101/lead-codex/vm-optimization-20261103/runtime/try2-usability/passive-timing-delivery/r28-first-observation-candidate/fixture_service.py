"""OFFLINE fixture only: actual candidate PAGE/server, fake native ACK and image animation. No guest."""
import hashlib,json,os,signal,struct,sys,threading,time,uuid,zlib
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import trial_web_r24_review_snapshot as web
ROOT=Path(__file__).resolve().parent;OUT=Path(sys.argv[1]);OUT.mkdir()
def save(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def stamp():return {'epoch_ns':time.time_ns(),'host_ns':time.monotonic_ns()}
def log(**v):
 with (OUT/'events.jsonl').open('a') as f:f.write(json.dumps({**stamp(),**v})+'\n')
def png():
 def ch(k,d):return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('!2I5B',2,2,8,2,0,0,0))+ch(b'IDAT',zlib.compress(b'\0'+bytes([20,80,180])*2+b'\0'+bytes([80,180,20])*2))+ch(b'IEND',b'')
INITIAL=png();MENU=(ROOT.parent/'r26-tool-return-preparation/samples/fixed.png').read_bytes()
state=web.TrialState('r28-FIXTURE',3600,32);sequence=0;mode='normal';delay=4.5;stop_animation=threading.Event();counts={}
def publish(data):
 global sequence
 with state.lock:
  sequence+=1;state.publish(data,{'sequence':sequence,'PNG_sha256':hashlib.sha256(data).hexdigest(),'all_zero_pixels':False,'nonuniform_pixels':True,'width':640 if data==MENU else 2,'height':480 if data==MENU else 2})
def reset(which):
 global sequence,mode,stop_animation,counts
 stop_animation.set();stop_animation=threading.Event();mode=which;counts={'keyPOST':0,'pinPOST':0,'confirmPOST':0,'nativeDown':0,'nativeUp':0};sequence=0
 fresh=web.TrialState('r28-FIXTURE-'+which,3600,32);fresh.url=state.url
 with state.lock:state.__dict__.update(fresh.__dict__)
 launch=str(uuid.uuid4());state.update(phase='ready',ready=True,launch_request_id=launch,launch_status='running');publish(INITIAL);log(reset=which,launch=launch)
 return {'fixture_only':True,'launch_id':launch,'url':state.url+'/','mode':mode}
def fake_native(item,cancel):
 time.sleep(.04)
 with state.lock:
  if cancel.is_set():return
  state.take();state.update(steps=item['step']);counts['nativeDown']+=1;counts['nativeUp']+=1;assert state.note_native_received(item['step'],item['request_id']);publish(INITIAL);state.require_visual_review(item['step'],'visual_changed',True)
 started=time.monotonic();log(mock_native_ACK=True,step=item['step'],attempt=item['request_id'])
 while not cancel.wait(.08):
  if time.monotonic()-started>=delay:publish(MENU);log(mock_menu_published=True,elapsed_after_native=time.monotonic()-started);break
  publish(INITIAL)
def submit(body):
 counts['keyPOST']+=1;code,v=web.TrialState.submit(state,body);log(keyPOST=True,status=code,request_id=body.get('request_id'))
 if code==202 and mode!='no-native':
  item={**state.pending[-1],'step':state.steps+1};threading.Thread(target=fake_native,args=(item,stop_animation),daemon=True).start()
 return code,v
state.submit=submit
def pin(body):
 counts['pinPOST']+=1;code,v=web.TrialState.pin_review(state,body);log(pinPOST=True,status=code,step=body.get('step'));return code,v
state.pin_review=pin
def confirm(body):
 counts['confirmPOST']+=1;code,v=web.TrialState.confirm_visual(state,body);log(confirmPOST=True,status=code,step=body.get('step'));return code,v
state.confirm_visual=confirm
server,thread=web.start_server(state,0);oldget=server.RequestHandlerClass.do_GET
reset('normal')
def get(self):
 u=urlsplit(self.path)
 if u.path=='/fixture/reset':return self.reply(200,reset(parse_qs(u.query).get('mode',['normal'])[0]))
 if u.path=='/fixture/metrics':return self.reply(200,{'fixture_only':True,'counts':counts,'snapshot':state.snapshot()})
 if u.path=='/fixture/preflight-change':publish(MENU);return self.reply(200,{'fixture_only':True})
 if u.path=='/fixture/change-launch':state.update(launch_request_id=str(uuid.uuid4()));return self.reply(200,{'fixture_only':True})
 return oldget(self)
server.RequestHandlerClass.do_GET=get
save('service.json',{'pid':os.getpid(),'port':server.server_address[1],'url':state.url+'/','fixture_only':True,'no_VM':True})
def finish(*_):threading.Thread(target=server.shutdown,daemon=True).start()
signal.signal(signal.SIGTERM,finish);signal.signal(signal.SIGINT,finish)
thread.join();stop_animation.set();server.server_close();save('service-exit.json',{'pid':os.getpid(),'closed':True,'fixture_only':True,**stamp()})
