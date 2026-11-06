(async c=>{
 let clicked=false,expected=null;const doc=document,origin=performance.timeOrigin,snap=reviewSnapshot,epoch=reviewEpoch;
 const digest=async text=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(x=>x.toString(16).padStart(2,'0')).join('');
 const alarm=()=>{const h=window.__fx3InteractionDeadlineV1?.status?.();if(!h||h.version!==1||h.expectedURL!==c.url||h.expectedLaunchId!==c.launch||h.sealed||h.deadline_ms!==60000||h.documentTimeOrigin!==origin||h.current?.nonce!==c.nonce||h.current.state!=='armed'||performance.now()>=h.current.due_ms)throw Error('r24_alarm');return h;};
 const identity=()=>{if(document!==doc||performance.timeOrigin!==origin||location.href!==c.url||window.top!==window||reviewEpoch!==epoch||reviewSnapshot!==snap||reviewProtocolUnknown||reviewTerminated||ending||finished||lastStatus?.error||lastStatus?.launch_request_id!==c.launch||deliveryUnknown||reviewUnknown||renderFault)throw Error('r24_confirm_identity_or_unknown');alarm();};
 try{
  const scripts=[...document.scripts],text=scripts[0]?.textContent;
  if(scripts.length!==1||scripts[0].src||await digest(text.replace(/^const token=[^\r\n]*;$/m,'const token=__TOKEN__;'))!==c.page_sha)throw Error('r24_PAGE_fingerprint');
  const byteHash=reviewBytes?[...new Uint8Array(await crypto.subtle.digest('SHA-256',reviewBytes))].map(x=>x.toString(16).padStart(2,'0')).join(''):null;
  // All decision state is checked again after the final await; no current-frame comparison.
  identity();if(scripts[0].textContent!==text||!snap||byteHash!==snap.PNG_sha256||!canConfirmSnapshot(lastStatus)||confirmButton.disabled||reviewIdentityKeys.some(k=>snap[k]!==c.snapshot[k]))throw Error('r24_exact_snapshot_not_ready');
  const h=alarm(),due=h.current.due_ms;clicked=true;confirmButton.click();expected=pendingConfirm&&{...pendingConfirm};
  if(!expected||reviewIdentityKeys.some(k=>expected[k]!==snap[k]))throw Error('r24_confirm_not_attributed');
  const limit=Math.min(due-100,performance.now()+10000);
  while(performance.now()<limit){
   identity();
   if(reviewLastAck?.request_id===expected.request_id&&confirmationMatches(lastStatus,expected)&&!reviewAwaiting&&!reviewUnknown&&pendingConfirm===null){
    const cancelled=window.__fx3InteractionDeadlineV1.cancel(c.nonce);
    if(cancelled.current?.state!=='cancelled'||cancelled.current.nonce!==c.nonce||cancelled.current.due_ms!==due)throw Error('r24_cancel_receipt');
    return {status:'confirmed_and_cancelled',receipt_schema:'fx3-r24-snapshot-confirm-v1',click_invoked:true,expected,cancelled,historical_snapshot:{...snap},guest_keys_sent:0};
   }
   await new Promise(r=>setTimeout(r,25));
  }
  throw Error('r24_confirm_receipt_bound');
 }catch(e){return {status:clicked?'unknown':'refused',receipt_schema:'fx3-r24-snapshot-confirm-v1',click_invoked:clicked,expected,reason:String(e),guest_keys_sent:0};}
})
