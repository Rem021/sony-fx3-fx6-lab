(async c => {
  const PLAN_SHA="4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f";
  const PLAN_KEYS=[427,3,504,427,428,427,427,427];
  'use strict';
  // Only document/script identity is sampled before await. It is not decision state.
  const docBefore = document, originBefore = performance.timeOrigin;
  const scriptsBefore = [...document.scripts], scriptBefore = scriptsBefore[0];
  const textBefore = scriptBefore?.textContent;
  const canonicalBefore = textBefore?.replace(/^const token=[^\r\n]*;$/m, 'const token=__TOKEN__;');
  const hash = canonicalBefore === undefined ? null :
    [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonicalBefore)))]
      .map(x => x.toString(16).padStart(2, '0')).join('');

  // No await from here through decision and the one original b.click().
  // This is one browser JS job, NOT an atomic server/guest admission.
  const scripts = [...document.scripts], s = lastStatus;
  const h = window.__fx3InteractionDeadlineV1?.status?.(), alarm = h?.current;
  const b = [...document.querySelectorAll('.key')].find(x => Number(x.dataset.key) === c.key);
  const now = performance.now();
  const finite = x => Number.isFinite(x) ? x : null;
  const id = x => typeof x === 'string' && /^[0-9a-f-]{36}$/.test(x) ? x : null;
  const sha = x => typeof x === 'string' && /^[0-9a-f]{64}$/.test(x) ? x : null;
  const identity = {
    document_unchanged: document === docBefore,
    time_origin_unchanged: performance.timeOrigin === originBefore,
    exact_url: location.href === c.url,
    top_level: window.top === window,
    one_inline_script: scripts.length === 1 && !scripts[0].src,
    script_unchanged_during_digest: scriptsBefore.length === 1 && scripts[0] === scriptBefore &&
      scriptBefore.textContent === textBefore,
    page_fingerprint: hash === c.page_sha,
    launch_identity: !!s && s.launch_request_id === c.launch,
    prerequisite_document: performance.timeOrigin === c.prerequisite.document_time_origin
  };
  const checks = {
    status_present: !!s,
    phase_ready: s?.phase === 'ready',
    server_ready: !!s?.ready,
    server_no_error: !s?.error,
    server_not_busy: !s?.busy,
    server_no_review: !s?.review_required,
    steps_under_eight: !!s && s.steps < 8,
    page_not_busy: !busy,
    page_not_ending: !ending,
    page_not_finished: !finished,
    delivery_known: !deliveryUnknown,
    review_known: !reviewUnknown,
    review_not_awaiting: !reviewAwaiting,
    no_awaiting_step: awaitingStep === null,
    no_render_fault: !renderFault,
    frame_loaded: !!s && frameLoadedFor(s),
    plan_matches: c.plan_sha === PLAN_SHA,
    plan_step_matches: Number.isInteger(c.step) && c.step >= 1 && c.step <= 8 && PLAN_KEYS[c.step-1] === c.key,
    server_step_matches: s?.steps === c.step-1,
    previous_confirm_matches: c.prerequisite.completed_step === c.step-1 &&
      (c.step === 1 ? c.prerequisite.previous_confirm === null :
        !!c.prerequisite.previous_confirm && confirmationMatches(s,c.prerequisite.previous_confirm.expected)),
    alarm_document_matches: h?.version === 1 && h.deadline_ms === 20000 && !h.sealed &&
      h.expectedURL === c.url && h.expectedLaunchId === c.launch && h.documentTimeOrigin === performance.timeOrigin,
    alarm_nonce_matches: alarm?.nonce === c.nonce,
    alarm_armed: alarm?.state === 'armed',
    // Explicit finite check fails closed on malformed due_ms (no change to 20 seconds).
    alarm_due_in_future: Number.isFinite(alarm?.due_ms) && now < alarm.due_ms,
    key_exists: !!b,
    key_enabled: !!b && !b.disabled
  };
  const identityFailures = Object.keys(identity).filter(k => !identity[k]);
  const failed = Object.keys(checks).filter(k => !checks[k]);
  const snapshot = {
    identity_trusted: identityFailures.length === 0, page: identity,
    document_time_origin: finite(performance.timeOrigin), digest_document_time_origin: finite(originBefore),
    script_count: scripts.length, canonical_sha256: hash,
    expected_page_sha256: c.page_sha, expected_launch: id(c.launch), launch: id(s?.launch_request_id),
    phase: ['starting','ready','stopping','finished','awaiting_launch'].includes(s?.phase) ? s.phase : null,
    ready: !!s?.ready, server_busy: !!s?.busy, review_required: !!s?.review_required,
    error_present: !!s?.error, steps: finite(s?.steps),
    page_busy: !!busy, ending: !!ending, finished: !!finished,
    delivery_unknown: !!deliveryUnknown, review_unknown: !!reviewUnknown, review_awaiting: !!reviewAwaiting,
    awaiting_step: finite(awaitingStep), render_fault_present: !!renderFault,
    frame_loaded: checks.frame_loaded, render_valid: !!s?.render_valid,
    loaded: {sha256: sha(shownSHA), generation: finite(displayedGeneration),
      displayed_sequence: finite(displayed), shown_sequence: finite(shown)},
    status_frame: {sha256: sha(s?.frame?.PNG_sha256), generation: finite(s?.frame?.content_generation),
      sequence: finite(s?.frame?.sequence)},
    scripted_navigation: true, visual_review_at_click: false,
    plan_sha: c.plan_sha, plan_step: c.step, previous_confirm: c.prerequisite.previous_confirm,
    prerequisite_sha256: c.prerequisite.prerequisite_sha256,
    click_time_frame: {PNG_sha256:sha(shownSHA),content_generation:finite(displayedGeneration),sequence:finite(displayed)},
    alarm: {expected_nonce: id(c.nonce), nonce: id(alarm?.nonce),
      state: ['armed','expired','cancelled'].includes(alarm?.state) ? alarm.state : null,
      armed_ms: finite(alarm?.armed_ms), due_ms: finite(alarm?.due_ms), now_ms: now},
    key: c.key, key_exists: checks.key_exists, key_enabled: checks.key_enabled
  };
  const result = {schema:'fx3-planned-navigation-v1',scripted_navigation:true,visual_review_at_click:false,plan_sha:c.plan_sha,plan_step:c.step, snapshot, checks,
    failed_checks:[...identityFailures.map(k => 'identity.' + k), ...failed],
    server_atomic_permission:false};
  // Identity failure never becomes a known no-click receipt, even if this code did not click.
  if (identityFailures.length) return {...result, status:'unknown', decision:'identity_untrusted'};
  if (failed.length) return {...result, status:'preflight_not_clicked',
    decision:'refuse_before_click', click_called:false};
  result.decision = 'invoke_original_button_once';
  b.click();
  // Any throw (including from here after click) loses the receipt and stays unknown in Python.
  const a = fx3KeyAttemptOutcome();
  if (!a || a.key !== c.key || a.alarm_nonce !== c.nonce) throw Error('attempt_not_created');
  return {...result, status:'click_invoked', click_called:true,
    attempt_id:a.attempt_id, step:a.expected_step, base_step:a.base_step,
    clicked_sha:a.frame.PNG_sha256, clicked_generation:a.frame.content_generation};
})
