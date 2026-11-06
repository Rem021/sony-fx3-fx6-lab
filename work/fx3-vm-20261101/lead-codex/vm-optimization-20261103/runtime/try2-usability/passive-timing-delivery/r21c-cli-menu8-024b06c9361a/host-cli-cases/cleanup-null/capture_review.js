(async function(c){
 const started=performance.now(),helper=window.__fx3InteractionDeadlineV1,doc=document,origin=performance.timeOrigin;
 let due=null;const events=[];
 const stamp=(event,extra={})=>events.push({event,performance_ms:performance.now(),UTC:new Date().toISOString(),...extra});
 function guard(){
  if(location.href!==c.url||document!==doc||performance.timeOrigin!==origin||lastStatus?.launch_request_id!==c.launch_id||window.__fx3InteractionDeadlineV1!==helper)throw Error('page_identity');
  const h=helper.status();
  if(h.sealed||h.deadline_ms!==20000||h.current?.nonce!==c.nonce||h.current?.state!=='armed'||performance.now()>=h.current.due_ms)throw Error('alarm_identity');
  if(due===null)due=h.current.due_ms;if(due!==h.current.due_ms)throw Error('due_changed');
  if(ending||finished||renderFault||deliveryUnknown||reviewUnknown||launchUnknown||explicitRejection||lastStatus.error||['stopping','finished'].includes(lastStatus.phase))throw Error('terminal_error_or_rejection');
  return h;
 }
 try{
  stamp('invoked');guard();const limit=Math.min(started+8000,due-8000);
  while(performance.now()<limit){
   guard();const s=lastStatus;
   if(s.steps>c.step||s.steps<c.step-1)throw Error('wrong_step');
   const ready=s.phase==='ready'&&s.steps===c.step&&s.review_required&&s.review_step===c.step&&s.input_received&&!s.busy&&!busy&&awaitingStep===null&&!reviewAwaiting&&pendingConfirm===null&&!confirmButton.disabled;
   const loaded=s.render_valid&&s.frame&&image.complete&&image.naturalWidth>0&&shownSHA===s.frame.PNG_sha256&&displayedGeneration===s.frame.content_generation&&displayed===s.frame.sequence;
   if(ready&&loaded){
    const before={step:c.step,sequence:displayed,content_generation:displayedGeneration,png_sha256:shownSHA,due_token:due.toPrecision(17),origin_token:origin.toPrecision(17),remaining_ms:due-performance.now(),performance_ms:performance.now(),UTC:new Date().toISOString(),frame:{...s.frame}};
    if(before.remaining_ms<8000)throw Error('insufficient_confirm_margin');stamp('current_loaded_review');return {status:'ready_for_screenshot',before,events};
   }
   await new Promise(r=>setTimeout(r,40));
  }
  throw Error('review_or_loaded_frame_not_ready_within_bound');
 }catch(e){stamp('refused',{reason:String(e)});return {status:'no_qualified_screenshot',reason:String(e),events};}
})
