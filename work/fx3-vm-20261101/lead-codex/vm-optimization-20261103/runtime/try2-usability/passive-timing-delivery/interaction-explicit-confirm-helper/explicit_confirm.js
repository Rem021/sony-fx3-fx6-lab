(async function explicitOperatorConfirm(c) {
  'use strict';
  const DEADLINE_MS = 20_000;
  const PAGE_SCRIPT_SHA = 'fe56b4846b9cb0c386216b38cc7e5b0707f616cab5ee6a526a217e68ce114478';
  const CONFIRM_HANDLER_SHA = 'f830416986fa93d865642fc00de7fc9963663dc87ba50d15939bf617e481fd5a';
  const events = [];
  const stamp = (event, extra = {}) => events.push({event, performance_ms: performance.now(), wall_UTC: new Date().toISOString(), ...extra});
  const result = (status, reason, extra = {}) => ({status, reason, click_invoked, events, ...extra});
  let click_invoked = false, expected = null, initial_due = null;
  const fail = why => { throw Error(why); };
  const digest = async text => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))].map(x => x.toString(16).padStart(2, '0')).join('');
  const helper = window.__fx3InteractionDeadlineV1;
  function alarm() {
    if (!helper || typeof helper.status !== 'function' || typeof helper.cancel !== 'function') fail('deadline_helper_missing');
    const h = helper.status();
    if (h.version !== 1 || h.expectedURL !== c.url || h.expectedLaunchId !== c.launch_id ||
        h.documentTimeOrigin !== performance.timeOrigin || h.deadline_ms !== DEADLINE_MS || h.sealed ||
        !h.current || h.current.nonce !== c.nonce || h.current.state !== 'armed' ||
        !Number.isFinite(h.current.due_ms) || performance.now() >= h.current.due_ms) fail('alarm_identity_or_due');
    if (initial_due !== null && h.current.due_ms !== initial_due) fail('alarm_due_changed');
    return h;
  }
  function pageIdentity() {
    const d = Object.getOwnPropertyDescriptor(window, '__fx3InteractionDeadlineV1');
    if (window.top !== window || location.href !== c.url || document.title !== 'FX3 固件菜单试用' ||
        !d || d.configurable || d.writable || d.value !== helper ||
        !lastStatus || lastStatus.launch_request_id !== c.launch_id ||
        document.querySelectorAll('#confirm').length !== 1 ||
        document.querySelector('#confirm').textContent !== '我已看清当前完整画面，继续') fail('page_or_document_identity');
  }
  function precondition() {
    pageIdentity();alarm();
    const s = lastStatus, b = document.querySelector('#confirm'), img = document.querySelector('#frame');
    if (s.phase !== 'ready' || s.error || s.busy || !s.render_valid || !s.frame ||
        !s.review_required || !s.input_received || s.review_step !== c.step || s.steps !== c.step ||
        s.frame.PNG_sha256 !== c.png_sha || shownSHA !== c.png_sha || displayed <= 0 ||
        displayedGeneration !== s.frame.content_generation || img !== image ||
        !img.complete || img.naturalWidth <= 0 || b !== confirmButton || b.disabled || b.hidden ||
        typeof b.onclick !== 'function' || busy || ending || finished || renderFault ||
        awaitingStep !== null || deliveryUnknown || reviewAwaiting || reviewUnknown ||
        pendingConfirm !== null || launchUnknown) fail('current_review_or_loaded_image_not_ready');
    const r = b.getBoundingClientRect(), style = getComputedStyle(b);
    if (style.display === 'none' || style.visibility !== 'visible' || Number(style.opacity) <= 0 ||
        r.width <= 0 || r.height <= 0 || r.top < 0 || r.left < 0 || r.bottom > innerHeight || r.right > innerWidth)
      fail('confirm_not_fully_visible');
    return {sequence: displayed, generation: displayedGeneration, sha: shownSHA};
  }
  function released() {
    pageIdentity();alarm();
    const s = lastStatus;
    const imageCurrent = !!s.frame && displayed > 0 && shownSHA === s.frame.PNG_sha256 &&
      displayedGeneration === s.frame.content_generation && image.complete && image.naturalWidth > 0;
    return confirmationMatches(s, expected) && s.phase === 'ready' && s.ready === true &&
      s.render_valid && !s.error && !s.busy && !s.review_required && imageCurrent &&
      !busy && !ending && !finished && !renderFault && !deliveryUnknown &&
      !reviewAwaiting && !reviewUnknown && pendingConfirm === null && awaitingStep === null &&
      !launchUnknown && keys.length === 7 && keys.every(b => !b.disabled);
  }
  try {
    stamp('invoked', {target: c.target, step: c.step, reviewed_png_sha256: c.png_sha});
    if (!c || typeof c.url !== 'string' || typeof c.launch_id !== 'string' ||
        typeof c.nonce !== 'string' || !Number.isSafeInteger(c.step) || c.step < 1 || c.step > 4096 ||
        !/^[0-9a-f]{64}$/.test(c.png_sha) || typeof c.target !== 'string' || !c.target.trim())
      fail('invalid_explicit_operator_arguments');
    pageIdentity();
    const scripts = [...document.scripts];
    if (scripts.length !== 1 || scripts[0].src) fail('PAGE_script_shape');
    const canonical = scripts[0].textContent.replace(/^const token=[^\r\n]*;$/m, 'const token=__TOKEN__;');
    if (await digest(canonical) !== PAGE_SCRIPT_SHA ||
        await digest(confirmButton.onclick.toString()) !== CONFIRM_HANDLER_SHA) fail('PAGE_or_original_confirm_handler_fingerprint');
    const h = alarm();initial_due = h.current.due_ms;
    const frame = precondition();
    stamp('precondition_passed', {due_ms: initial_due, sequence: frame.sequence,
      content_generation: frame.generation, png_sha256: frame.sha});
    // This is the only mutation. The original PAGE handler creates its own
    // request id and calls the original endpoint; this helper never POSTs.
    click_invoked = true;confirmButton.click();
    expected = pendingConfirm && {...pendingConfirm};
    stamp('confirm_click_invoked', {pending_confirm: expected});
    if (!expected || !/^[0-9a-f-]{36}$/.test(expected.request_id) ||
        expected.step !== c.step || expected.observed_sequence !== frame.sequence ||
        expected.content_generation !== frame.generation || expected.PNG_sha256 !== frame.sha)
      fail('synchronous_pending_confirm_identity_missing');
    const limit = Math.min(initial_due - 100, performance.now() + 10_000);
    while (performance.now() < limit) {
      if (released()) {
        stamp('matching_ack_and_current_frame_ready', {confirmation: {...lastStatus.review_confirmation},
          current_sequence: displayed, current_generation: displayedGeneration, current_png_sha256: shownSHA});
        const beforeCancel = performance.now();
        if (beforeCancel >= initial_due || beforeCancel - h.current.armed_ms >= DEADLINE_MS) fail('due_before_cancel');
        const cancelled = helper.cancel(c.nonce);
        const row = cancelled.events.findLast(e => e.event === 'cancelled' && e.nonce === c.nonce);
        stamp('cancel_returned', {state: cancelled.current?.state, due_ms: cancelled.current?.due_ms,
          elapsed_ms: row?.elapsed_ms});
        if (cancelled.current?.nonce !== c.nonce || cancelled.current?.state !== 'cancelled' ||
            cancelled.current?.due_ms !== initial_due || !row || !(row.elapsed_ms < DEADLINE_MS))
          return result('unknown', 'cancel_receipt_not_verified', {expected, cancelled});
        return result('confirmed_and_cancelled', 'matched_historical_receipt_and_current_input_gate',
          {expected, cancelled, current_frame: {sequence: displayed, content_generation: displayedGeneration,
            PNG_sha256: shownSHA}});
      }
      if (ending || finished || lastStatus?.error || renderFault || deliveryUnknown || reviewUnknown ||
          explicitRejection?.kind === 'confirm' ||
          (pendingConfirm && pendingConfirm.request_id !== expected.request_id))
        return result('unknown', 'terminal_error_rejection_or_request_replaced', {expected});
      await new Promise(resolve => setTimeout(resolve, Math.min(40, Math.max(1, limit - performance.now()))));
    }
    stamp('wait_ended', {due_ms: initial_due});
    return result('unknown', 'matching_ack_and_current_gate_not_proven_before_bound', {expected});
  } catch (error) {
    stamp('refused_or_unknown', {error: String(error)});
    return result(click_invoked ? 'unknown' : 'refused', String(error), {expected});
  }
})
