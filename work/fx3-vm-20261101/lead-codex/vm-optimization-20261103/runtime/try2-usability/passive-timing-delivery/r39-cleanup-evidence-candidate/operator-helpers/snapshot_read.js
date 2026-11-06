(async c=>{
 const doc=document,origin=performance.timeOrigin,scripts=[...document.scripts],script=scripts[0],text=script?.textContent;
 const hash=text===undefined?null:[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text.replace(/^const token=[^\r\n]*;$/m,'const token=__TOKEN__;'))))].map(x=>x.toString(16).padStart(2,'0')).join('');
 function guard(){
  const h=window.__fx3InteractionDeadlineV1?.status?.(),a=fx3KeyAttemptOutcome();
  if(document!==doc||performance.timeOrigin!==origin||location.href!==c.url||window.top!==window||scripts.length!==1||script.src||script.textContent!==text||hash!==c.page_sha||lastStatus?.launch_request_id!==c.launch||
    a?.attempt_id!==c.attempt_id||a.expected_step!==c.step||a.alarm_nonce!==c.nonce||a.outcome!=='accepted'||
    h?.version!==1||h.expectedURL!==c.url||h.expectedLaunchId!==c.launch||h.sealed||h.deadline_ms!==20000||h.documentTimeOrigin!==origin||h.current?.nonce!==c.nonce||h.current.state!=='armed'||performance.now()>=h.current.due_ms||
    reviewProtocolUnknown||reviewTerminated||ending||finished||lastStatus.error||deliveryUnknown||reviewUnknown||renderFault)throw Error('r24_snapshot_identity_or_unknown');
  return h;
 }
 const h=guard(),limit=Math.min(performance.now()+8000,h.current.due_ms-8000);
 if(c.action==='pin'){
  if(!canPinReview(lastStatus)||pinButton.disabled||(c.reference_sha&&shownSHA!==c.reference_sha))throw Error('r24_pin_not_ready');
  pinButton.click();return {pin_invoked:true,document_id:reviewDocumentId,origin};
 }
 if(c.action==='ready'){
  while(performance.now()<limit){guard();if(canPinReview(lastStatus)&&!pinButton.disabled&&(!c.reference_sha||shownSHA===c.reference_sha))return {ready:true};await new Promise(r=>setTimeout(r,25));}
  throw Error('r24_pin_readiness_bound');
 }
 while(performance.now()<limit){
  guard();const r=fx3ReviewSnapshotState(c.include_bytes===true);
  if(r.loaded&&r.snapshot){const snap=r.snapshot;
   if(snap.document_id!==reviewDocumentId||snap.attempt_id!==c.attempt_id||snap.step!==c.step||snap.launch_id!==c.launch)throw Error('r24_snapshot_binding');
   return {status:'qualified_review_snapshot',snapshot:snap,document_time_origin:origin,nonce:c.nonce,png_base64:r.png_base64};}
  await new Promise(r=>setTimeout(r,25));
 }
 throw Error('r24_snapshot_load_bound');
})
