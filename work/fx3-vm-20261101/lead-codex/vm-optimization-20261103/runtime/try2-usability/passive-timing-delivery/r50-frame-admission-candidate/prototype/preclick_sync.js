/* fx3-preclick-frame-sync-v1 — disabled-by-default prototype, NOT integrated.
 * Read-only status checks only; no key/confirm/pin/ARM write.
 * Returns {allow:true} only if the fresh frame repeatedly equals the page's
 * currently displayed frame and all bounded/identity/readiness/ARM checks pass.
 * Content changes or identity changes are explicit refusals; no rebinding.
 */
async function fx3PreclickFrameSyncV1(c, rt) {
  'use strict';
  const cfg = {
    maxWaitMs: Number.isFinite(c.maxWaitMs) ? Math.max(0, c.maxWaitMs) : 200,
    sampleIntervalMs: Number.isFinite(c.sampleIntervalMs) ? Math.max(0, c.sampleIntervalMs) : 50,
    requiredStableSamples: Number.isInteger(c.requiredStableSamples) ? Math.max(1, c.requiredStableSamples) : 2,
    maxAttempts: Number.isInteger(c.maxAttempts) ? Math.max(1, c.maxAttempts) : 3,
    reserveMs: Number.isFinite(c.reserveMs) ? Math.max(0, c.reserveMs) : 500
  };
  const start = rt.now();
  const due = Number(c.dueMs);
  const deadline = Number.isFinite(due) ? Math.min(start + cfg.maxWaitMs, due - cfg.reserveMs) : start + cfg.maxWaitMs;
  const base = { schema: 'fx3-preclick-frame-sync-v1', version: 1, start_monotonic_ms: start,
    max_wait_ms: cfg.maxWaitMs, sample_interval_ms: cfg.sampleIntervalMs,
    required_stable_samples: cfg.requiredStableSamples, max_attempts: cfg.maxAttempts,
    due_ms: Number.isFinite(due) ? due : null, deadline_monotonic_ms: deadline,
    reserve_ms: cfg.reserveMs, arm_reset: false, key_calls: 0, confirm_calls: 0, pin_calls: 0,
    one_click_max: true, samples: [] };
  const fail = (reason, extra = {}) => ({ ...base, ...extra, allow: false, reason, ended_ms: rt.now() });
  if (!(deadline > start)) return fail('expired_or_no_window');
  let displayed;
  try { displayed = rt.displayed(); } catch (_) { return fail('displayed_read_failed'); }
  if (!displayed || displayed.loaded !== true || !displayed.frame || typeof displayed.frame.PNG_sha256 !== 'string' ||
      !Number.isFinite(displayed.frame.content_generation)) return fail('displayed_not_loaded');
  if (typeof rt.identity !== 'function' || rt.identity().same !== true) return fail('identity_changed');
  let prev = null, stableRun = 0;
  for (let attempt = 0; attempt < cfg.maxAttempts; attempt++) {
    const before = rt.now();
    if (before >= deadline) break;
    let s;
    try { s = await rt.readStatus(); } catch (_) { return fail('status_read_failed', { attempts: attempt + 1 }); }
    const at = rt.now();
    base.samples.push({ attempt: attempt + 1, at_monotonic_ms: at, phase: s && s.phase,
      ready: s && s.ready, busy: s && s.busy, review_required: s && s.review_required,
      error: s && s.error, frame: s && s.frame ? { ...s.frame } : null });
    if (!s || s.error || s.phase !== 'ready' || s.ready !== true || s.busy === true || s.review_required === true) {
      if (attempt + 1 < cfg.maxAttempts && rt.now() < deadline) {
        await rt.sleep(Math.min(cfg.sampleIntervalMs, deadline - rt.now()));
        continue;
      }
      return fail('status_not_ready', { attempts: attempt + 1, last_frame: s && s.frame ? { ...s.frame } : null });
    }
    if (rt.identity().same !== true) return fail('identity_changed', { attempts: attempt + 1 });
    if (!s.frame || s.frame.PNG_sha256 !== displayed.frame.PNG_sha256 ||
        s.frame.content_generation !== displayed.frame.content_generation) {
      return fail('displayed_frame_superseded', { attempts: attempt + 1,
        displayed: { ...displayed.frame }, observed: s.frame ? { ...s.frame } : null,
        note: 'fresh status no longer equals the displayed frame; refuse and require re-view; no rebind' });
    }
    if (prev && prev.PNG_sha256 === s.frame.PNG_sha256 && prev.content_generation === s.frame.content_generation) stableRun++;
    else stableRun = 0;
    prev = { ...s.frame };
    if (stableRun + 1 >= cfg.requiredStableSamples) {
      return { ...base, allow: true, reason: 'readonly_frame_matched', ended_ms: rt.now(), attempts: attempt + 1,
        stable_samples: stableRun + 1, matched_frame: { ...displayed.frame },
        note: 'admission precondition only; does not confirm/pin/review and does not select a new frame' };
    }
    if (attempt + 1 < cfg.maxAttempts) {
      const remaining = deadline - rt.now();
      if (remaining <= 0) break;
      await rt.sleep(Math.min(cfg.sampleIntervalMs, remaining));
    }
  }
  return fail(prev ? 'frame_not_stable' : 'no_sample', { attempts: base.samples.length });
}
if (typeof module !== 'undefined' && module.exports) module.exports = { fx3PreclickFrameSyncV1 };
