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
  const fail = (reason, diagnostics = {}) => {const error=Error(reason);error.diagnostics=diagnostics;throw error;};
  const digest = async value => [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))].map(x=>x.toString(16).padStart(2,'0')).join('');
  function diagnostics() {
    const s=typeof lastStatus==='object' ? lastStatus : null;
    const h=helper && typeof helper.status==='function' ? helper.status() : null;
    return {phase:s?.phase, error:s?.error, steps:s?.steps, status_busy:s?.busy,
      host_busy:typeof busy==='boolean'?busy:null, awaiting_step:typeof awaitingStep==='undefined'?null:awaitingStep,
      delivery_unknown:typeof deliveryUnknown==='boolean'?deliveryUnknown:null,
      explicit_rejection:typeof explicitRejection==='undefined'?null:explicitRejection,
      review_required:s?.review_required, review_step:s?.review_step,
      input_received:s?.input_received, visual_state:s?.visual_state,
      render_valid:s?.render_valid,
      frame_sequence:s?.frame?.sequence, frame_generation:s?.frame?.content_generation,
      frame_sha:s?.frame?.PNG_sha256,
      displayed_sequence:typeof displayed==='number'?displayed:null,
      displayed_generation:typeof displayedGeneration==='number'?displayedGeneration:null,
      shown_sha:typeof shownSHA==='string'?shownSHA:null,
      alarm_state:h?.current?.state, alarm_nonce:h?.current?.nonce,
      remaining_ms:h?.current?.due_ms-performance.now()};
  }
  function identity() {
    if (window.top !== window || document !== doc || performance.timeOrigin !== origin)
      fail('document_changed', diagnostics());
    if (location.href !== c.url || document.title !== 'FX3 固件菜单试用')
      fail('url_or_title_changed', diagnostics());
    if (!lastStatus || lastStatus.launch_request_id !== c.launch_id)
      fail('launch_identity_changed', diagnostics());
    if (window.__fx3InteractionDeadlineV1 !== helper || !helper || typeof helper.status !== 'function')
      fail('deadline_helper_changed', diagnostics());
    const h = helper.status();
    if (h.version !== 1 || h.expectedURL !== c.url || h.expectedLaunchId !== c.launch_id ||
        h.documentTimeOrigin !== origin || h.deadline_ms !== DEADLINE_MS)
      fail('alarm_contract_changed', diagnostics());
    if (h.sealed || h.current?.nonce !== c.nonce || h.current?.state !== 'armed')
      fail('alarm_nonce_or_state_changed', diagnostics());
    if (!Number.isFinite(h.current.due_ms) || performance.now() >= h.current.due_ms)
      fail('alarm_due_expired', diagnostics());
    if (initial_due === null) initial_due = h.current.due_ms;
    if (h.current.due_ms !== initial_due) fail('alarm_due_changed', diagnostics());
    return h;
  }
  function state() {
    const h = identity(), s = lastStatus, img = document.querySelector('#frame');
    if (s.phase !== 'ready' || ending || finished) fail('phase_not_ready_or_terminal', diagnostics());
    if (s.error) fail('native_or_status_error', diagnostics());
    if (renderFault) fail('render_fault', diagnostics());
    if (deliveryUnknown || reviewUnknown || launchUnknown) fail('delivery_or_launch_unknown', diagnostics());
    if (explicitRejection?.kind==='key') fail('explicit_key_rejection', diagnostics());
    if (explicitRejection?.kind==='confirm' || reviewAwaiting || pendingConfirm !== null)
      fail('unexpected_confirmation_state', diagnostics());
    if (img !== image) fail('image_element_changed', diagnostics());
    if (!Number.isSafeInteger(s.steps) || s.steps < 0 || s.steps > 1 ||
        (awaitingStep !== null && awaitingStep !== 1)) fail('unexpected_step_or_awaiting_step', diagnostics());
    if (s.render_valid === false) fail('render_invalid', diagnostics());
    if (s.steps===0) {
      if (awaitingStep!==1 || s.review_required || s.input_received)
        fail('step_zero_without_expected_menu_pending', diagnostics());
      return {kind:'accepted_menu_waiting_for_status', diagnostics:diagnostics()};
    }
    if (!s.review_required) {
      if (!s.busy || s.review_step!==null)
        fail('step_one_without_expected_processing_or_review', diagnostics());
      if (s.visual_state==='input_pending' && s.input_received===false)
        return {kind:'step_one_input_pending', diagnostics:diagnostics()};
      if (s.visual_state==='visual_pending' && s.input_received===true)
        return {kind:'step_one_visual_pending_native_ack', diagnostics:diagnostics()};
      fail('step_one_unexpected_processing_state', diagnostics());
    }
    if (s.review_step!==1 || s.input_received!==true || s.busy)
      fail('step_one_review_identity_or_status_busy', diagnostics());
    if (s.visual_state!=='visual_changed' && s.visual_state!=='no_change_observed')
      fail('step_one_review_visual_state_unexpected', diagnostics());
    if (busy && awaitingStep===1)
      return {kind:'step_one_ack_handler_finishing', diagnostics:diagnostics()};
    if (busy) fail('unexpected_host_busy_after_review', diagnostics());
    if (awaitingStep!==null) return {kind:'step_one_page_awaiting_refresh', diagnostics:diagnostics()};
    const frame = s.frame;
    if (!frame || !Number.isSafeInteger(frame.content_generation) || frame.content_generation <= 0 ||
        !Number.isSafeInteger(frame.sequence) || frame.sequence <= 0)
      fail('frame_metadata_invalid', diagnostics());
    // A status update may lead image.onload. Wait for the original PAGE to load it.
    if (!img.complete || img.naturalWidth <= 0 || shownSHA !== frame.PNG_sha256 ||
        displayedGeneration !== frame.content_generation || displayed !== frame.sequence ||
        confirmButton.disabled)
      return {kind:'step_one_image_or_confirm_loading', diagnostics:diagnostics()};
    return {performance_ms:performance.now(), wall_UTC:new Date().toISOString(),
      kind:'ready_loaded_review',
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
    let last_kind=null;
    while (performance.now() < limit) {
      const s=state();
      if (s.kind !== last_kind) {
        stamp('state_transition', {state:s.kind, diagnostics:s.diagnostics || diagnostics()});
        last_kind=s.kind;
      }
      if (s.kind === 'ready_loaded_review' && s.png_sha256 === MENU_SHA) {
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
    const detail=error.diagnostics || diagnostics();
    stamp('refused',{reason:String(error), diagnostics:detail});
    return {status:'no_qualified_screenshot',reason:String(error),
      diagnostics:detail, waited_ms:performance.now()-started,events};
  }
})
