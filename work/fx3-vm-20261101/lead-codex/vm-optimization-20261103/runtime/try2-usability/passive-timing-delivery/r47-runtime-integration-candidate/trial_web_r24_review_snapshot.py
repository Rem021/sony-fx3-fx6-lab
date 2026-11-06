"""r24 host candidate: one post-receive review object; original live key admission is inherited unchanged."""
import copy,hashlib,importlib.util,json,re,secrets,time,uuid
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
HERE=Path(__file__).resolve().parent
BASE=HERE
spec=importlib.util.spec_from_file_location('fx3_r24_original_web',BASE/'trial_web_v22_navigation_review.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
KEYS=base.KEYS;wait_for_final_receipt=base.wait_for_final_receipt
UUID=re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
MAX_SNAPSHOT_BYTES=4*1024*1024
SNAPSHOT_TTL=20.0
IDENTITY=('snapshot_id','run_incarnation','launch_id','document_id','step','attempt_id','pin_request_id','observed_sequence','content_generation','PNG_sha256')

class TrialState(base.TrialState):
 def __init__(self,*a,**k):
  super().__init__(*a,**k)
  self.run_incarnation=str(uuid.uuid4());self.owner_document_id=None;self.active_input=None
  self.review_object=None;self.publish_index=0;self.review_protocol_unknown=False;self.review_invalid_reason=None
 def _invalidate(self,reason,drop_input=False):
  self.review_object=None;self.review_invalid_reason=reason
  if self.active_input and self.active_input.get('review_state')=='issued':self.active_input['review_state']='revoked'
  if drop_input:self.active_input=None
 def _expire(self):
  if self.review_object and time.monotonic()>=self.review_object['expires']:
   self._invalidate('snapshot_expired')
 def update(self,**kw):
  with self.lock:
   if (kw.get('error') or kw.get('phase') in ('stopping','finished') or
       ('launch_request_id' in kw and kw['launch_request_id']!=self.launch_request_id)):
    self._invalidate('lifecycle_or_launch_changed',True)
   if self.review_object and (kw.get('review_required',self.review_required) is not True or kw.get('input_received',self.input_received) is not True or kw.get('review_step',self.review_step)!=self.review_object['meta']['step'] or kw.get('busy',self.busy) or kw.get('steps',self.steps)!=self.review_object['meta']['step']):
    self._invalidate('step_changed')
   if self.active_input and kw.get('steps',self.steps) not in (self.active_input['step']-1,self.active_input['step']):
    self._invalidate('input_step_changed',True)
   super().update(**kw)
 def publish(self,png,frame):
  with self.lock:
   super().publish(png,frame);self.publish_index+=1;self._expire()
 def snapshot(self):
  with self.lock:
   self._expire();s=super().snapshot()
   s.update(run_incarnation=self.run_incarnation,review_protocol_unknown=self.review_protocol_unknown,
            review_snapshot_present=self.review_object is not None)
   s['ready']=s['ready'] and not self.review_protocol_unknown
   return s
 def submit(self,body):
  with self.lock:
   doc=body.get('document_id');rid=body.get('request_id')
   if (self.review_protocol_unknown or not isinstance(doc,str) or not UUID.fullmatch(doc) or
       not isinstance(rid,str) or not UUID.fullmatch(rid) or
       (self.owner_document_id is not None and doc!=self.owner_document_id)):
    return 409,{'error':'r24 document/request/unknown identity refused','accepted':False,'enqueued':False,'request_id':rid if isinstance(rid,str) and UUID.fullmatch(rid) else None}
   # All original SHA/gen/cache/lifecycle/ready/busy/pending/review/key/limit branches run unchanged.
   code,value=super().submit(body)
   if code==202:
    self._invalidate('new_accepted_input',True);self.owner_document_id=doc
    self.active_input={'document_id':doc,'attempt_id':rid,'launch_id':self.launch_request_id,
      'step':self.steps+1,'observed_sequence':body['observed_sequence'],'native_received':False,'review_state':'unissued'}
    self.pending[-1].update(request_id=rid,document_id=doc)
   return code,value
 def note_native_received(self,step,attempt_id):
  """Called by the runner only after matching native down/up have been observed. Never writes guest."""
  with self.lock:
   a=self.active_input
   if (not a or a['step']!=step or a['attempt_id']!=attempt_id or self.stop.is_set() or self.error or
       self.phase!='ready' or self.review_protocol_unknown):return False
   if not a['native_received']:
    a.update(native_received=True,ack_publish_index=self.publish_index,
             ack_sequence=self.frame['sequence'] if self.frame else a['observed_sequence'],
             ack_observed_host_monotonic=time.monotonic())
   return True
 def require_visual_review(self,step,state,changed):
  with self.lock:
   if self.active_input and (step!=self.active_input['step'] or self.review_step not in (None,step)):self._invalidate('review_step_changed',True)
   super().require_visual_review(step,state,changed)
 def _review_ready(self,body):
  a=self.active_input
  return bool(a and not self.stop.is_set() and not self.error and self.phase=='ready' and
    not self.review_protocol_unknown and not self.busy and not self.pending and
    self.review_required and self.input_received and self.steps==self.review_step==a['step']==body.get('step') and
    a['native_received'] and body.get('attempt_id')==a['attempt_id'] and
    body.get('launch_id')==self.launch_request_id==a['launch_id'] and
    body.get('document_id')==self.owner_document_id==a['document_id'])
 def pin_review(self,body):
  with self.lock:
   self._expire()
   if not self._review_ready(body) or self.review_object is not None or self.active_input['review_state']!='unissued':
    return 409,{'error':'review identity/lifecycle or existing snapshot'}
   rid=body.get('pin_request_id');seq=body.get('observed_sequence');a=self.active_input
   f=self.frames.get(seq) if type(seq) is int else None
   if (not isinstance(rid,str) or not UUID.fullmatch(rid) or not f or not self.frame or not self.render_valid or
       self.publish_index<=a['ack_publish_index'] or seq<=a['ack_sequence'] or
       f['PNG_sha256']!=body.get('PNG_sha256') or f['content_generation']!=body.get('content_generation') or
       f['PNG_sha256']!=self.frame['PNG_sha256'] or f['content_generation']!=self.content_generation or
       f.get('all_zero_pixels') or f.get('nonuniform_pixels') is not True or
       not isinstance(self.png,(bytes,bytearray)) or not 0<len(self.png)<=MAX_SNAPSHOT_BYTES or
       not self.png.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(self.png).hexdigest()!=f['PNG_sha256']):
    return 409,{'error':'snapshot must be exact valid new post-receive observed PNG'}
   meta={'schema':'fx3-review-snapshot-v1','snapshot_id':str(uuid.uuid4()),'run_incarnation':self.run_incarnation,
     'launch_id':a['launch_id'],'document_id':a['document_id'],'step':a['step'],'attempt_id':a['attempt_id'],
     'pin_request_id':rid,'observed_sequence':seq,'content_generation':f['content_generation'],'PNG_sha256':f['PNG_sha256'],
     'byte_length':len(self.png),'native_receive_floor_sequence':a['ack_sequence'],
     'native_receive_observed_host_monotonic':a['ack_observed_host_monotonic'],
     'observation_scope':'new_host_observation_after_native_receive; no_pixel_causality_or_handler_completion_claim'}
   self.active_input['review_state']='issued'
   self.review_object={'meta':meta,'png':bytes(self.png),'expires':time.monotonic()+SNAPSHOT_TTL}
   return 201,copy.deepcopy(meta)
 def snapshot_png(self,sid,doc):
  with self.lock:
   self._expire();obj=self.review_object
   if not obj or obj['meta']['snapshot_id']!=sid or obj['meta']['document_id']!=doc:return 409,None
   if not self._review_ready(obj['meta']):self._invalidate('review_no_longer_ready');return 409,None
   if hashlib.sha256(obj['png']).hexdigest()!=obj['meta']['PNG_sha256']:self._invalidate('stored_bytes_invalid');return 409,None
   return 200,obj['png']
 def abort_review(self,body):
  with self.lock:
   a=self.active_input
   if not a or body.get('document_id')!=a['document_id'] or body.get('attempt_id')!=a['attempt_id']:return 409,{'error':'abort identity'}
   self.review_protocol_unknown=True;self.ready=False;self._invalidate('client_protocol_unknown')
   return 200,{'invalidated':True}
 def confirm_visual(self,body):
  with self.lock:
   self._expire();obj=self.review_object
   if (not obj or not self._review_ready(body) or body.get('schema')!='fx3-review-snapshot-v1' or
       any(body.get(k)!=obj['meta'][k] for k in IDENTITY) or
       not isinstance(body.get('request_id'),str) or not UUID.fullmatch(body['request_id']) or
       hashlib.sha256(obj['png']).hexdigest()!=obj['meta']['PNG_sha256']):
    return 409,{'error':'exact active review snapshot required; no replay'}
   historical={k:obj['meta'][k] for k in IDENTITY};historical.update(schema='fx3-review-snapshot-v1',request_id=body['request_id'],guest_input_written=False)
   self.active_input['review_state']='consumed'
   self.review_object=None # single-use, bytes released before returning any ACK
   self.review_required=False;self.review_step=None;self.visual_state='reviewed_historical_snapshot'
   self.review_confirmation=historical
   self.message='已确认本次按键后的指定快照；下一键仍独立检查实时画面。'
   return 200,{'confirmed':True,**copy.deepcopy(historical)}
 def request_stop(self):
  with self.lock:self._invalidate('stop',True);return super().request_stop()
 def fail(self,reason):
  with self.lock:self._invalidate('native_or_host_error',True);return super().fail(reason)

# Build a genuinely versioned PAGE from the original; no frozen source file is edited.
PAGE=base.PAGE
PAGE=PAGE.replace('<div class="layout"><div class="screen">','<p>当前实时画面（不是已审阅快照）</p><div class="layout"><div class="screen">')
PAGE=PAGE.replace('<button id="confirm" disabled>我已看清当前完整画面，继续</button>', '<button id="pin-review" disabled>保存本次按键后的审阅快照</button><button id="confirm" disabled>我已审阅下方指定快照，确认本步</button>')
PAGE=PAGE.replace('<details id="diagnostics"', '<section id="snapshot-review"><h2>本次按键后固定审阅副本</h2><p id="snapshot-label">尚未建立审阅对象；实时画面会继续更新。</p><img id="review-frame" style="position:static;width:640px;max-width:100%;height:auto" alt="指定的按键后审阅快照"></section><details id="diagnostics"')
PAGE=PAGE.replace("const keys=[...document.querySelectorAll('.key')];", "const keys=[...document.querySelectorAll('.key')];\n"+(HERE/'review_page_r24.js').read_text())
PAGE=PAGE.replace('!visual);\n confirmButton.disabled=', '!visual||reviewProtocolUnknown||reviewTerminated);\n confirmButton.disabled=')
start=PAGE.index(' confirmButton.disabled=!s.review_required');end=PAGE.index('\n}',start)
PAGE=PAGE[:start]+''' pinButton.disabled=!canPinReview(s);
 confirmButton.disabled=!canConfirmSnapshot(s);'''+PAGE[end:]
PAGE=PAGE.replace('function lockVisualControls(){keys.forEach(b=>b.disabled=true);confirmButton.disabled=true;}', 'function lockVisualControls(){keys.forEach(b=>b.disabled=true);pinButton.disabled=true;confirmButton.disabled=!canConfirmSnapshot(lastStatus);}')
PAGE=PAGE.replace("const c=s.review_confirmation;", "const c=s.review_confirmation;\n if(p?.schema!=='fx3-review-snapshot-v1'||!c||['snapshot_id','run_incarnation','launch_id','document_id','attempt_id','pin_request_id'].some(k=>c[k]!==p[k]))return false;")
PAGE=PAGE.replace("const s=(await request('/api/status')).body;lastStatus=s;", "const s=(await request('/api/status')).body;if(reviewTerminated&&!['stopping','finished'].includes(s.phase)){disableKeys();return;}lastStatus=s;\n   if(s.error||s.review_protocol_unknown)invalidateReview('server_error_or_unknown',true);\n   if(s.review_required&&reviewSnapshot&&s.review_step!==reviewSnapshot.step)invalidateReview('review_step_changed',true);")
PAGE=PAGE.replace("reviewEl.textContent=s.review_required?", "reviewEl.textContent=s.review_required?")
PAGE=PAGE.replace('原生按键已接收，效果待您看图确认。请只在当前画面完整且符合预期时点继续；无需再按一次固件键。', '原生按键已接收；请保存并实际审阅下方固定副本，再独立确认本步。实时画面继续更新。')
PAGE=PAGE.replace("finished=true;disableKeys();", "invalidateReview('finished');finished=true;disableKeys();")
PAGE=PAGE.replace("if(s.phase==='stopping'){ending=true;", "if(s.phase==='stopping'){invalidateReview('stopping');ending=true;")
PAGE=PAGE.replace("if((reviewAwaiting||reviewUnknown)&&confirmationMatches(s,pendingConfirm)){", "if(false){ // r24: only the explicit mutation response may complete this confirm; unknown stays sticky")
PAGE=PAGE.replace("renderFault=e.message;disableKeys();", "invalidateReview('read_or_render_unknown',true);renderFault=e.message;disableKeys();")
PAGE=PAGE.replace("Object.assign(currentKeyAttempt,{outcome,...extra,updated_monotonic_ms:performance.now()});return true;", "Object.assign(currentKeyAttempt,{outcome,...extra,updated_monotonic_ms:performance.now()});if(outcome==='delivery_unknown')invalidateReview('input_unknown',true);return true;")
PAGE=PAGE.replace("if(b.disabled||busy||ending||renderFault||awaitingStep!==null||!lastStatus)return;", "if(b.disabled||busy||ending||renderFault||awaitingStep!==null||!lastStatus||reviewProtocolUnknown||reviewTerminated)return;\n invalidateReview('new_input');")
PAGE=PAGE.replace("{key:a.key,observed_sequence:displayed,request_id:a.attempt_id}", "{key:a.key,observed_sequence:displayed,request_id:a.attempt_id,document_id:reviewDocumentId}")
start=PAGE.index('confirmButton.onclick=async()=>{');end=PAGE.index('\nendButton.onclick=',start)
PAGE=PAGE[:start]+(HERE/'confirm_page_r24.js').read_text()+PAGE[end:]
PAGE=PAGE.replace("ending=true;disableKeys();endButton.disabled=true;", "invalidateReview('End');ending=true;disableKeys();endButton.disabled=true;")
PAGE_SCRIPT_SHA=hashlib.sha256(PAGE.split('<script>')[1].split('</script>')[0].encode()).hexdigest()

def start_server(state,port):
 base.PAGE=PAGE
 server,thread=base.start_server(state,port);handler=server.RequestHandlerClass
 oldget,oldpost=handler.do_GET,handler.do_POST
 def do_get(self):
  u=urlsplit(self.path)
  if u.path!='/review-snapshot.png':return oldget(self)
  if not self.valid_host() or self.headers.get('X-Trial-Token')!=state.token:return self.reply(403,{'error':'snapshot session'})
  q=parse_qs(u.query);code,png=state.snapshot_png(q.get('snapshot_id',[''])[0],q.get('document_id',[''])[0])
  return self.reply(code,png if png is not None else {'error':'snapshot invalid'},'image/png' if png is not None else 'application/json')
 def do_post(self):
  if self.path not in ('/api/review-snapshot','/api/review-abort'):return oldpost(self)
  if (not self.valid_host() or self.headers.get('X-Trial-Token')!=state.token or
      (self.headers.get('Origin') and self.headers.get('Origin')!=state.url) or self.headers.get('Sec-Fetch-Site')=='cross-site'):
   return self.reply(403,{'error':'review session/origin'})
  try:
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=1024 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError()
   body=json.loads(self.rfile.read(n))
   if not isinstance(body,dict):raise ValueError()
  except (ValueError,UnicodeError):return self.reply(400,{'error':'review request format'})
  code,value=state.pin_review(body) if self.path=='/api/review-snapshot' else state.abort_review(body)
  return self.reply(code,value)
 handler.do_GET=do_get;handler.do_POST=do_post
 return server,thread
