(async c=>{
 const doc=document,origin=performance.timeOrigin,scripts=[...document.scripts],script=scripts[0],text=script?.textContent;
 const hash=text===undefined?null:[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text.replace(/^const token=[^\r\n]*;$/m,'const token=__TOKEN__;'))))].map(x=>x.toString(16).padStart(2,'0')).join('');
 function local(){
  const h=window.__fx3InteractionDeadlineV1?.status?.(),a=fx3KeyAttemptOutcome(),s=lastStatus;
  if(document!==doc||performance.timeOrigin!==origin||origin!==c.document_time_origin||location.href!==c.url||window.top!==window||scripts.length!==1||script.src||document.scripts.length!==1||document.scripts[0]!==script||script.textContent!==text||hash!==c.page_sha||reviewDocumentId!==c.document_id||
   s?.launch_request_id!==c.launch_id||s.run_incarnation!==c.run_incarnation||(s.steps!==c.step&&!(s.steps===c.step-1&&awaitingStep===c.step))||s.phase!=='ready'||s.error||s.review_protocol_unknown||
   a?.attempt_id!==c.attempt_id||a.document_time_origin!==origin||a.launch_request_id!==c.launch_id||a.expected_step!==c.step||a.alarm_nonce!==c.nonce||a.outcome!=='accepted'||
   h?.version!==1||h.sealed||h.deadline_ms!==60000||h.expectedURL!==c.url||h.expectedLaunchId!==c.launch_id||h.documentTimeOrigin!==origin||h.current?.nonce!==c.nonce||h.current.state!=='armed'||h.current.due_ms!==a.alarm_due_ms||h.current.due_ms!==h.current.armed_ms+60000||performance.now()>=h.current.due_ms||
   reviewProtocolUnknown||reviewTerminated||reviewPinPending||reviewSnapshot||s.review_snapshot_present||reviewLastAck||ending||finished||deliveryUnknown||reviewUnknown||reviewAwaiting||renderFault)throw Error('r26_postkey_identity_lifecycle_or_existing_pin:'+JSON.stringify({step:s?.steps,expected_step:c.step,awaiting_step:awaitingStep,document_match:reviewDocumentId===c.document_id,origin_match:origin===c.document_time_origin,launch_match:s?.launch_request_id===c.launch_id,run_match:s?.run_incarnation===c.run_incarnation,attempt_match:a?.attempt_id===c.attempt_id,nonce_match:a?.alarm_nonce===c.nonce,alarm_state:h?.current?.state,alarm_due_exact:h?.current?.due_ms===h?.current?.armed_ms+60000,pinned:!!reviewSnapshot,last_ack:!!reviewLastAck,unknown:!!(deliveryUnknown||reviewUnknown||reviewProtocolUnknown),ending,finished}));
  return {h,a,s};
 }
 async function fresh(){
  local();const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),1000);let value;
  try{const response=await fetch('/api/status',{cache:'no-store',signal:controller.signal});if(!response.ok)throw Error('status_http');value=await response.json();}finally{clearTimeout(timer);}
  const {h,s}=local();
  if(value.launch_request_id!==c.launch_id||value.run_incarnation!==c.run_incarnation||(value.steps!==c.step&&!(value.steps===c.step-1&&value.busy&&!value.review_required))||value.phase!=='ready'||value.error||value.review_protocol_unknown||value.review_snapshot_present||!value.render_valid)throw Error('r26_fresh_identity_lifecycle');
  const ready=value.review_required&&value.input_received&&value.review_step===c.step&&!value.busy&&s.review_required&&s.input_received&&s.review_step===c.step&&!s.busy&&!busy&&awaitingStep===null&&s.render_valid&&frameLoadedFor(s)&&image.complete&&image.naturalWidth>0;
  return {h,ready,server:{run_incarnation:value.run_incarnation,launch_id:value.launch_request_id,step:value.steps,review_step:value.review_step,review_required:value.review_required,input_received:value.input_received,busy:value.busy,phase:value.phase,render_valid:value.render_valid},performance_ms:performance.now()};
 }
 const wait={schema:'fx3-first-observation-wait-r28-v1',first_observation:c.first_observation===true,applied:false,binding:{document_id:c.document_id,origin:c.document_time_origin,run_incarnation:c.run_incarnation,launch_id:c.launch_id,step:c.step,attempt_id:c.attempt_id,nonce:c.nonce},check_times_ms:[]};
 if(c.action==='observe'&&c.first_observation===true){
  let checked=await fresh();const h=checked.h;wait.arm_ms=h.current.armed_ms;wait.due_ms=h.current.due_ms;wait.not_before_ms=wait.arm_ms+5000;wait.entered_ms=performance.now();
  wait.applied=wait.entered_ms<wait.not_before_ms;let nextFresh=performance.now();
  while(performance.now()<wait.not_before_ms){
   local();await new Promise(resolve=>setTimeout(resolve,Math.min(25,Math.max(1,wait.not_before_ms-performance.now()))));local();
   if(performance.now()>=nextFresh||performance.now()>=wait.not_before_ms){checked=await fresh();wait.check_times_ms.push(performance.now());nextFresh=performance.now()+200;}
  }
  await fresh();wait.completed_ms=performance.now();wait.not_before_satisfied=wait.completed_ms>=wait.not_before_ms;
  if(!wait.not_before_satisfied)throw Error('r28_first_sample_before_arm_plus5000');
 }
 let before=await fresh();const until=Math.min(performance.now()+6000,before.h.current.due_ms);
 while(c.action!=='after'&&!before.ready&&performance.now()<until){await new Promise(r=>setTimeout(r,25));before=await fresh();}
 if(!before.ready)throw Error('r26_native_review_phase_not_ready');
 return {qualified:true,first_observation_wait:wait,document_id:reviewDocumentId,origin,run_incarnation:c.run_incarnation,binding:c,
  phase:before.server,displayed_frame:{sequence:displayed,content_generation:displayedGeneration,PNG_sha256:shownSHA},
  before,alarm_identity_json:JSON.stringify(before.h),performance_ms:performance.now()};
})
