(async function captureMenuReference(c) {
  'use strict';
  const PAGE_SHA = 'fe56b4846b9cb0c386216b38cc7e5b0707f616cab5ee6a526a217e68ce114478';
  const MENU_SHA = '60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292';
  const MAX_WAIT_MS = 8000, CONFIRM_RESERVE_MS = 8000, DEADLINE_MS = 20000;
  const doc = document, origin = performance.timeOrigin;
  const helper = window.__fx3InteractionDeadlineV1;
  let initial_due = null;
  const started = performance.now();
  const events = [];
  const stamp = (kind, extra = {}) => events.push({kind, performance_ms:performance.now(), wall_UTC:new Date().toISOString(), ...extra});
  const fail = reason => {throw Error(reason);};
  const digest = async value => [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))].map(x=>x.toString(16).padStart(2,'0')).join('');
  function identity() {
    if (window.top !== window || document !== doc || performance.timeOrigin !== origin ||
        location.href !== c.url || !lastStatus || lastStatus.launch_request_id !== c.launch_id ||
        document.title !== 'FX3 固件菜单试用' ||
        window.__fx3InteractionDeadlineV1 !== helper ||
        !helper || typeof helper.status !== 'function') fail('page_or_document_identity');
    const h = helper.status();
    if (h.version !== 1 || h.expectedURL !== c.url || h.expectedLaunchId !== c.launch_id ||
        h.documentTimeOrigin !== origin || h.deadline_ms !== DEADLINE_MS || h.sealed ||
        h.current?.nonce !== c.nonce || h.current?.state !== 'armed' ||
        !Number.isFinite(h.current.due_ms) ||
        performance.now() >= h.current.due_ms) fail('alarm_identity_or_due');
    if (initial_due === null) initial_due = h.current.due_ms;
    if (h.current.due_ms !== initial_due) fail('alarm_due_changed');
    return h;
  }
  function state() {
    const h = identity(), s = lastStatus, img = document.querySelector('#frame');
    if (s.phase !== 'ready' || s.error || s.busy || !s.render_valid ||
        !s.review_required || !s.input_received || s.review_step !== 1 || s.steps !== 1 ||
        busy || ending || finished || renderFault || deliveryUnknown || reviewUnknown ||
        reviewAwaiting || pendingConfirm !== null ||
        launchUnknown || awaitingStep !== null || img !== image)
      fail('phase_or_input_gate_not_ready');
    const frame = s.frame;
    if (!frame || !Number.isSafeInteger(frame.content_generation) || frame.content_generation <= 0 ||
        !Number.isSafeInteger(frame.sequence) || frame.sequence <= 0)
      fail('frame_metadata_invalid');
    // A status update may lead image.onload. Wait for the original PAGE to load it.
    if (!img.complete || img.naturalWidth <= 0 || shownSHA !== frame.PNG_sha256 ||
        displayedGeneration !== frame.content_generation || displayed !== frame.sequence)
      return null;
    return {performance_ms:performance.now(), wall_UTC:new Date().toISOString(),
      launch_id:s.launch_request_id, step:s.steps, review_step:s.review_step,
      sequence:displayed, content_generation:displayedGeneration,
      png_sha256:shownSHA, frame_sequence:frame.sequence,
      frame_generation:frame.content_generation, frame_png_sha256:frame.PNG_sha256,
      due_ms:h.current.due_ms, due_token:h.current.due_ms.toPrecision(17),
      remaining_ms:h.current.due_ms-performance.now(),
      document_time_origin:origin, document_origin_token:origin.toPrecision(17)};
  }
  try {
    stamp('invoked');
    if (!c || typeof c.url !== 'string' || typeof c.launch_id !== 'string' ||
        typeof c.nonce !== 'string' || c.step !== 1 || c.reference_sha !== MENU_SHA)
      fail('arguments_or_menu_reference');
    identity();
    const scripts=[...document.scripts];
    if (scripts.length !== 1 || scripts[0].src) fail('PAGE_script_shape');
    const canonical=scripts[0].textContent.replace(/^const token=[^\r\n]*;$/m,'const token=__TOKEN__;');
    if (await digest(canonical) !== PAGE_SHA) fail('PAGE_fingerprint');
    const h=identity(), limit=Math.min(started+MAX_WAIT_MS,h.current.due_ms-CONFIRM_RESERVE_MS);
    if (limit <= performance.now()) fail('insufficient_confirm_reserve');
    while (performance.now() < limit) {
      const s=state();
      if (s && s.png_sha256 === MENU_SHA) {
        if (h.current.due_ms-performance.now() < CONFIRM_RESERVE_MS) fail('confirm_reserve_exhausted');
        stamp('reference_loaded', {sequence:s.sequence, generation:s.content_generation});
        return {status:'ready_for_screenshot', before:s, waited_ms:performance.now()-started,
          reference_sha:MENU_SHA, confirm_reserve_ms:CONFIRM_RESERVE_MS, events};
      }
      await new Promise(resolve=>setTimeout(resolve,Math.min(40,Math.max(1,limit-performance.now()))));
    }
    return {status:'no_qualified_screenshot',reason:'reference_not_loaded_before_bound',
      waited_ms:performance.now()-started,events};
  } catch (error) {
    stamp('refused',{reason:String(error)});
    return {status:'no_qualified_screenshot',reason:String(error),
      waited_ms:performance.now()-started,events};
  }
})
