(async function explicitRecoveryCancel(c){
 'use strict';
 const PAGE_SHA='852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b';
 const hash=async s=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)))].map(x=>x.toString(16).padStart(2,'0')).join('');
 let cancel_invoked=false;
 const fail=reason=>({status:'refused',reason,cancel_invoked,performance_ms:performance.now()});
 try{
  if(!c||location.href!==c.url||window.top!==window||document.title!=='FX3 固件菜单试用'||
     !c.review||!c.binding||typeof c.target!=='string'||!c.target.trim())return fail('config_or_document');
  const scripts=[...document.scripts];if(scripts.length!==1||scripts[0].src)return fail('script_shape');
  const canonical=scripts[0].textContent.replace(/^const token=[^\r\n]*;$/m,'const token=__TOKEN__;');
  if(await hash(canonical)!==PAGE_SHA)return fail('PAGE_fingerprint');
  const helper=window.__fx3InteractionDeadlineV1,desc=Object.getOwnPropertyDescriptor(window,'__fx3InteractionDeadlineV1');
  if(!helper||!desc||desc.configurable||desc.writable||desc.value!==helper||
     typeof helper.status!=='function'||typeof helper.cancel!=='function')return fail('deadline_identity');
  const review=c.review;
  if(review.status!=='qualified_review_screenshot'||review.attempt_id!==c.binding.attempt_id||
     review.nonce!==c.nonce||review.launch_id!==c.launch_id||
     !/^[0-9a-f]{64}$/.test(review.PNG_sha256)||
     !Number.isSafeInteger(review.content_generation)||review.content_generation<=0||
     !review.screenshot_sha256)return fail('review_receipt');
  const first=helper.status(),a=window.fx3KeyAttemptOutcome?.();
  if(!a||a.attempt_id!==c.binding.attempt_id||a.alarm_nonce!==c.nonce||
     !first.current||first.current.state!=='armed'||first.current.nonce!==c.nonce||
     first.expectedURL!==c.url||first.expectedLaunchId!==c.launch_id||
     first.documentTimeOrigin!==performance.timeOrigin||first.deadline_ms!==20000||
     !Number.isFinite(first.current.due_ms)||first.current.due_ms!==a.alarm_due_ms||
     performance.now()>=first.current.due_ms)return fail('attempt_alarm_binding');
  // Read-only server refresh. It is a snapshot, never an atomic key permission.
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),Math.min(2000,Math.max(1,first.current.due_ms-performance.now()-1000)));
  let fresh;
  try{const response=await fetch('/api/status',{cache:'no-store',signal:controller.signal});
      if(!response.ok)return fail('status_http');fresh=await response.json();}
  catch(_){return fail('status_unknown');}finally{clearTimeout(timer);}
  if(!fresh||fresh.phase!=='ready'||!fresh.ready||fresh.busy||fresh.review_required||fresh.error||
     fresh.steps!==a.base_step||fresh.launch_request_id!==c.launch_id||!fresh.frame||!fresh.render_valid||
     ending||finished||busy||deliveryUnknown||reviewUnknown||awaitingStep!==null||reviewAwaiting||renderFault)
     return fail('server_status_not_ready');
  // Ordinary page tick may still be loading. No key, confirm or alarm mutation while waiting.
  const limit=Math.min(performance.now()+2000,first.current.due_ms-1000);
  while(performance.now()<limit && (!lastStatus||!frameLoadedFor(lastStatus)||
        !image.complete||image.naturalWidth<=0||shownSHA!==fresh.frame.PNG_sha256||
        displayedGeneration!==fresh.frame.content_generation))
    await new Promise(resolve=>setTimeout(resolve,50));
  if(!lastStatus||!frameLoadedFor(lastStatus)||!image.complete||image.naturalWidth<=0||
     shownSHA!==fresh.frame.PNG_sha256||displayedGeneration!==fresh.frame.content_generation||
     lastStatus.steps!==a.base_step||lastStatus.launch_request_id!==c.launch_id)return fail('loaded_frame_not_current');
  const now=helper.status(),q=window.fx3KeyAttemptRecoveryEligibility?.(c.binding);
  if(!q?.eligible||window.fx3KeyAttemptOutcome?.().attempt_id!==a.attempt_id||
     now.current?.nonce!==c.nonce||now.current?.state!=='armed'||
     now.current.due_ms!==first.current.due_ms||performance.now()>=now.current.due_ms)return fail('last_identity_or_eligibility');
  // The only mutation: cancel this already proved unqueued test alarm.
  cancel_invoked=true;const receipt=helper.cancel(c.nonce);
  const event=receipt.events?.filter(e=>e.event==='cancelled'&&e.nonce===c.nonce).at(-1);
  const elapsed=receipt.current?.cancelled_ms-receipt.current?.armed_ms;
  if(receipt.current?.state!=='cancelled'||receipt.current.nonce!==c.nonce||
     receipt.current.due_ms!==first.current.due_ms||!event||
     !Number.isFinite(elapsed)||elapsed<0||elapsed>=20000||
     !Number.isFinite(event.elapsed_ms)||event.elapsed_ms<0||event.elapsed_ms>=20000)
    return {status:'unknown',reason:'cancel_receipt_mismatch',cancel_invoked,alarm_cancel_receipt:receipt};
  return {status:'cancelled_unqueued_alarm_only',cancel_invoked,attempt_id:a.attempt_id,
    nonce:c.nonce,alarm_cancel_receipt:receipt,
    old_review:{sha:review.PNG_sha256,generation:review.content_generation},
    current_frame:{sha:shownSHA,generation:displayedGeneration,sequence:displayed},
    historical_review_not_current:review.PNG_sha256!==shownSHA||review.content_generation!==displayedGeneration,
    no_visual_approval:true,no_guest_key:true,no_confirm_visual:true,server_atomic_permission:false,
    due_ms:receipt.current.due_ms,elapsed_ms:elapsed,performance_ms:performance.now()};
 }catch(e){return {status:cancel_invoked?'unknown':'refused',reason:String(e),cancel_invoked};}
})
