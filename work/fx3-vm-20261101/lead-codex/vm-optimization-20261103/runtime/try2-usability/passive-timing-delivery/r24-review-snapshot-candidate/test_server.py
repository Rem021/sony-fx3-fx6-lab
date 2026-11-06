"""Pure host lifecycle/identity tests. No service, browser, native code or VM."""
import hashlib,json,struct,time,uuid,zlib
from pathlib import Path
import trial_web_r24_review_snapshot as web
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'evidence';RESULT={}
def uid():return str(uuid.uuid4())
def png(r,g,b):
 def ch(k,d):return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('!2I5B',2,2,8,2,0,0,0))+ch(b'IDAT',zlib.compress(b'\0'+bytes([r,g,b])*2+b'\0'+bytes([b,r,g])*2))+ch(b'IEND',b'')
A=png(80,40,20);B=png(20,100,200)
def publish(s,data,seq):s.publish(data,{'sequence':seq,'PNG_sha256':hashlib.sha256(data).hexdigest(),'all_zero_pixels':False,'nonuniform_pixels':True,'width':2,'height':2})
def fixture(native=True,new=True):
 s=web.TrialState('offline-server',3600,32);launch=uid();doc=uid();aid=uid()
 s.update(phase='ready',ready=True,launch_request_id=launch);publish(s,A,1)
 assert s.submit({'key':427,'observed_sequence':1,'request_id':aid,'document_id':doc})[0]==202
 assert s.take()['request_id']==aid;s.update(steps=1)
 if native:assert s.note_native_received(1,aid)
 if new:publish(s,A,2)
 s.require_visual_review(1,'visual_changed',True)
 body={'launch_id':launch,'document_id':doc,'attempt_id':aid,'step':1,'pin_request_id':uid(),
       'observed_sequence':s.frame['sequence'],'content_generation':s.content_generation,'PNG_sha256':s.frame['PNG_sha256']}
 return s,body

def pin(s,b):
 code,meta=s.pin_review(b);assert code==201,(code,meta)
 return meta,{'schema':'fx3-review-snapshot-v1','request_id':uid(),**{k:meta[k] for k in web.IDENTITY}}

s,b=fixture();meta,body=pin(s,b)
assert s.review_required and s.submit({'key':3,'observed_sequence':2,'request_id':uid(),'document_id':b['document_id']})[0]==409
for seq in range(3,100):publish(s,B if seq%2 else A,seq)
assert 2 not in s.frames and len(s.frames)==64
assert s.snapshot_png(meta['snapshot_id'],b['document_id'])==(200,A)
for key,value in [('run_incarnation',uid()),('launch_id',uid()),('document_id',uid()),('attempt_id',uid()),('step',2),('snapshot_id',uid()),('observed_sequence',1000),('content_generation',999),('PNG_sha256','0'*64)]:
 assert s.confirm_visual({**body,key:value})[0]==409,key
assert s.confirm_visual(body)[0]==200 and s.review_confirmation['content_generation']==meta['content_generation']
assert s.review_confirmation['observed_sequence']==2 and s.review_object is None
assert s.confirm_visual(body)[0]==409 and s.pin_review(b)[0]==409
RESULT['historical_bytes_survive_ring_and_identity_replay']={'passed':True,'negative_identities':9,'frames_bound':len(s.frames),'PNG_sha256':meta['PNG_sha256'],'receipt':s.review_confirmation}

for name,mutate in [('expiry',lambda s:setattr(s,'review_object',{**s.review_object,'expires':time.monotonic()-1})),
                    ('stored_bytes',lambda s:s.review_object.update(png=B)),
                    ('temporary_busy',lambda s:s.update(busy=True)),
                    ('temporary_review_removed',lambda s:s.update(review_required=False))]:
 s,b=fixture();meta,body=pin(s,b);mutate(s)
 assert s.snapshot_png(meta['snapshot_id'],b['document_id'])[0]==409
 s.update(busy=False,review_required=True,review_step=1,input_received=True)
 assert s.pin_review(b)[0]==409 and s.pin_review({**b,'pin_request_id':uid()})[0]==409
 assert s.confirm_visual(body)[0]==409
 RESULT[name+'_cannot_revive']={'passed':True,'state':s.active_input and s.active_input['review_state']}

for name,mutate in [('stop',lambda s,b:s.request_stop()),('native_error',lambda s,b:s.fail('fixture_native_assert')),
                    ('unknown',lambda s,b:s.abort_review(b)),('new_launch',lambda s,b:s.update(launch_request_id=uid())),
                    ('other_review_step',lambda s,b:s.require_visual_review(2,'visual_changed',True)),
                    ('other_input_step',lambda s,b:s.update(steps=2))]:
 s,b=fixture();meta,body=pin(s,b);mutate(s,b)
 assert s.confirm_visual(body)[0]==409 and s.review_object is None
 RESULT[name+'_invalidates']={'passed':True}

for name,native,new in [('before_native_receive',False,True),('no_new_frame_after_receive',True,False)]:
 s,b=fixture(native,new);assert s.pin_review(b)[0]==409 and s.review_object is None;RESULT[name]={'passed':True}
s,b=fixture();assert s.pin_review({**b,'observed_sequence':100000})[0]==409
s.png=B;assert s.pin_review(b)[0]==409
s.png=A*(web.MAX_SNAPSHOT_BYTES//len(A)+1);assert s.pin_review(b)[0]==409
RESULT['future_tampered_or_oversize_bytes_refused']={'passed':True,'MAX_SNAPSHOT_BYTES':web.MAX_SNAPSHOT_BYTES}
s,b=fixture();meta,body=pin(s,b);assert s.pin_review({**b,'pin_request_id':uid()})[0]==409
assert s.snapshot_png(meta['snapshot_id'],uid())[0]==409
assert s.confirm_visual(body)[0]==200
publish(s,B,3)
assert s.submit({'key':3,'observed_sequence':2,'request_id':uid(),'document_id':b['document_id']})[0]==409
assert s.submit({'key':3,'observed_sequence':3,'request_id':uid(),'document_id':b['document_id']})[0]==202
assert s.confirm_visual(body)[0]==409
RESULT['one_snapshot_and_fresh_input_gate']={'passed':True,'live_submit_calls':'stale 409; fresh 202','old_snapshot_replay':409}
(OUT/'SERVER-RESULT.json').write_text(json.dumps({'passed':True,'cases':RESULT,'scope':__doc__},indent=2)+'\n')
print(json.dumps({'passed':True,'groups':len(RESULT)}))
