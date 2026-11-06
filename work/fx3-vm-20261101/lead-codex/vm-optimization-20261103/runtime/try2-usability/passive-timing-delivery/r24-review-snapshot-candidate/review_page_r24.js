// r24 explicitly separates one immutable review copy from the continuously published live image.
const reviewDocumentId=crypto.randomUUID().toLowerCase();
const pinButton=document.querySelector('#pin-review'),reviewImage=document.querySelector('#review-frame'),reviewLabel=document.querySelector('#snapshot-label');
let reviewSnapshot=null,reviewBytes=null,reviewImageURL=null,reviewSnapshotLoaded=false,reviewPinPending=false;
let reviewEpoch=0,reviewProtocolUnknown=false,reviewTerminated=false,reviewLastAck=null;
const reviewIdentityKeys=['snapshot_id','run_incarnation','launch_id','document_id','step','attempt_id','pin_request_id','observed_sequence','content_generation','PNG_sha256'];
function invalidateReview(reason,unknown=false){
 const a=currentKeyAttempt;
 reviewEpoch++;reviewSnapshot=null;reviewBytes=null;reviewSnapshotLoaded=false;reviewLastAck=null;
 if(reviewImageURL){URL.revokeObjectURL(reviewImageURL);reviewImageURL=null;}reviewImage.removeAttribute('src');
 reviewLabel.textContent='固定审阅对象已失效：'+reason;pinButton.disabled=confirmButton.disabled=true;
 if(unknown)reviewProtocolUnknown=true;
 if(['End','stopping','finished'].includes(reason))reviewTerminated=true;
 if(unknown&&a)void post('/api/review-abort',{document_id:reviewDocumentId,attempt_id:a.attempt_id}).catch(()=>{});
}
function canPinReview(s){
 const a=currentKeyAttempt;
 return !!s&&!!a&&a.outcome==='accepted'&&a.expected_step===s.steps&&s.review_step===s.steps&&
  s.phase==='ready'&&s.review_required&&s.input_received&&!s.error&&!s.busy&&!busy&&!ending&&!finished&&
  !reviewProtocolUnknown&&!reviewTerminated&&!reviewPinPending&&!reviewSnapshot&&
  !renderFault&&!deliveryUnknown&&!reviewUnknown&&!reviewAwaiting&&awaitingStep===null&&
  frameLoadedFor(s)&&image.complete&&image.naturalWidth>0;
}
function canConfirmSnapshot(s){
 const r=reviewSnapshot,a=currentKeyAttempt;
 return !!s&&!!r&&!!a&&reviewSnapshotLoaded&&reviewImage.complete&&reviewImage.naturalWidth>0&&
  s.phase==='ready'&&!s.error&&!s.busy&&s.review_required&&s.input_received&&s.steps===r.step&&s.review_step===r.step&&
  a.attempt_id===r.attempt_id&&a.expected_step===r.step&&a.outcome==='accepted'&&
  r.document_id===reviewDocumentId&&r.launch_id===s.launch_request_id&&
  !busy&&!ending&&!finished&&!renderFault&&!deliveryUnknown&&!reviewUnknown&&!reviewAwaiting&&
  !reviewProtocolUnknown&&!reviewTerminated&&awaitingStep===null&&pendingConfirm===null;
}
function reviewAsyncCurrent(epoch,attempt,step){
 return epoch===reviewEpoch&&!reviewProtocolUnknown&&!reviewTerminated&&!ending&&!finished&&
  !lastStatus?.error&&lastStatus?.phase==='ready'&&lastStatus.steps===step&&
  currentKeyAttempt?.attempt_id===attempt&&currentKeyAttempt.outcome==='accepted';
}
Object.defineProperty(window,'fx3ReviewSnapshotState',{value:(includeBytes=false)=>{
 let png_base64=null;
 if(includeBytes&&reviewBytes){let str='';for(const b of reviewBytes)str+=String.fromCharCode(b);png_base64=btoa(str);}
 return {schema:'fx3-review-page-state-v1',document_id:reviewDocumentId,epoch:reviewEpoch,
  protocol_unknown:reviewProtocolUnknown,terminated:reviewTerminated,pin_pending:reviewPinPending,
  loaded:reviewSnapshotLoaded,snapshot:reviewSnapshot&&structuredClone(reviewSnapshot),
  last_ack:reviewLastAck&&structuredClone(reviewLastAck),png_base64};
},writable:false,configurable:false});
pinButton.onclick=async()=>{
 if(!canPinReview(lastStatus))return;
 const a=currentKeyAttempt,epoch=reviewEpoch,step=a.expected_step;
 const expected={launch_id:lastStatus.launch_request_id,document_id:reviewDocumentId,step,
  attempt_id:a.attempt_id,pin_request_id:crypto.randomUUID().toLowerCase(),
  observed_sequence:displayed,content_generation:displayedGeneration,PNG_sha256:shownSHA};
 reviewPinPending=true;pinButton.disabled=true;
 try{
  const ack=await post('/api/review-snapshot',expected);
  if(!reviewAsyncCurrent(epoch,a.attempt_id,step))return;
  if(ack.schema!=='fx3-review-snapshot-v1'||!ack.snapshot_id||!ack.run_incarnation||
     Object.keys(expected).some(k=>ack[k]!==expected[k]))throw Error('snapshot_identity_mismatch');
  const u='/review-snapshot.png?snapshot_id='+encodeURIComponent(ack.snapshot_id)+'&document_id='+encodeURIComponent(reviewDocumentId);
  const {body}=await request(u,{headers:{'X-Trial-Token':token}},'arrayBuffer');
  const bytes=new Uint8Array(body);
  const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  if(bytes.byteLength!==ack.byte_length||hash!==ack.PNG_sha256)throw Error('snapshot_bytes_mismatch');
  if(!reviewAsyncCurrent(epoch,a.attempt_id,step))return;
  const objectURL=URL.createObjectURL(new Blob([bytes],{type:'image/png'}));
  await new Promise((resolve,reject)=>{let timer=setTimeout(()=>reject(Error('snapshot_image_timeout')),8000);
   reviewImage.onload=()=>{clearTimeout(timer);resolve();};reviewImage.onerror=()=>{clearTimeout(timer);reject(Error('snapshot_decode'));};reviewImage.src=objectURL;});
  if(!reviewAsyncCurrent(epoch,a.attempt_id,step)){URL.revokeObjectURL(objectURL);return;}
  reviewImageURL=objectURL;reviewBytes=bytes;reviewSnapshot=Object.freeze({...ack});reviewSnapshotLoaded=true;
  reviewLabel.textContent=`固定副本：第${step}步 · generation ${ack.content_generation} · sequence ${ack.observed_sequence}；确认仅针对本副本，实时画面继续更新。`;
 }catch(e){if(epoch===reviewEpoch)invalidateReview('snapshot_pin_or_load_unknown',true);}
 finally{reviewPinPending=false;enableKeys(lastStatus);}
};
