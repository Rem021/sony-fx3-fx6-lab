(() => {
  'use strict';
  const c = CONFIG;
  const h = window.__fx3InteractionDeadlineV1?.status();
  const s = lastStatus, img = document.querySelector('#frame');
  const now = performance.now();
  const result = {wall_UTC:new Date().toISOString(), performance_ms:now,
    document_time_origin:performance.timeOrigin, location:location.href,
    launch_id:s?.launch_request_id, phase:s?.phase, error:s?.error,
    step:s?.steps, review_step:s?.review_step, review_required:s?.review_required,
    input_received:s?.input_received, render_valid:s?.render_valid,
    sequence:displayed, content_generation:displayedGeneration, png_sha256:shownSHA,
    frame_sequence:s?.frame?.sequence, frame_generation:s?.frame?.content_generation,
    frame_png_sha256:s?.frame?.PNG_sha256, image_complete:img?.complete,
    image_width:img?.naturalWidth, alarm_nonce:h?.current?.nonce,
    alarm_state:h?.current?.state, alarm_due_ms:h?.current?.due_ms,
    remaining_ms:h?.current?.due_ms-now};
  const checks = {
    top:window.top === window, url:result.location === c.url,
    document:result.document_time_origin?.toPrecision(17) === c.document_origin_token,
    launch:result.launch_id === c.launch_id, phase:result.phase === 'ready' && !result.error,
    step:result.step === 1 && result.review_step === 1,
    review:result.review_required === true && result.input_received === true,
    render:result.render_valid === true && result.image_complete === true && result.image_width > 0,
    sequence:result.sequence >= c.sequence && result.sequence === result.frame_sequence,
    generation:result.content_generation === c.content_generation &&
      result.frame_generation === c.content_generation,
    sha:result.png_sha256 === c.reference_sha && result.frame_png_sha256 === c.reference_sha,
    alarm_nonce:result.alarm_nonce === c.nonce,
    alarm_state:result.alarm_state === 'armed',
    alarm_due:result.alarm_due_ms?.toPrecision(17) === c.due_token,
    alarm_reserve:result.remaining_ms >= 8000,
    host_gate:!busy && !ending && !finished && !renderFault && !deliveryUnknown &&
      !reviewUnknown && !reviewAwaiting && pendingConfirm === null &&
      !launchUnknown && awaitingStep === null && !s?.busy
  };
  result.failed_checks = Object.entries(checks).filter(([,ok])=>!ok).map(([name])=>name);
  result.qualified = result.failed_checks.length === 0;
  return result;
})()
