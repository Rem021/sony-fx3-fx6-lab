# r49 minimal improvement design — not implemented

This is a design record only. Nothing in this file was wired into r47/r48 source,
the PAGE, helpers, runtime policy, or any live run. r48's single Start is consumed;
no new VM/browser/server/QMP/guest is authorized by this task.

## Facts that constrain the design

- Both MENU clicks passed the host 26-check preflight and invoked the original
  button exactly once (`planned_navigation_click.js` lines 88/102/106).
- The PAGE's own click handler then fetched a fresh `/api/status`; the fresh frame
  was `gen20/seq128/SHA2914…` (attempt 1) and `gen44/seq235/SHA2914…` (attempt 2),
  while the click snapshot was `gen19/seq120/e014…` and `gen43/seq231/e014…`.
- PAGE canonical lines 304–305 (the freshness OR) rejected both:
  - `preflight.frame.PNG_sha256 !== clickedSHA`
  - `preflight.frame.content_generation !== clickedGeneration`
  - `!frameLoadedFor(preflight)`
  - Identity/lifecycle terms were false: same launch/run/document/timeOrigin,
    steps=0, phase=ready, ready=true, busy=false, review_required=false, error=null,
    render_valid=true.
- The page tick is 400 ms; the last tick was 264.5 ms (attempt 1) / 32.8 ms
  (attempt 2) before the click snapshot; the fresh preflight arrived ~1 ms after
  the click snapshot. The two observations therefore checked different frames.
- HAR has only `/api/start`, `/api/stop`, `/api/final-ack` POSTs; no `/api/key`.
- Actual image observation correction: recovery-before has no `NO CARD` text;
  initial-standby and recovery-after do. This is an observation, not proof that a
  native OSD flicker caused the frame change.

## Improvement 1 — observation v2 (no policy or semantic change)

Record in the click receipt, separately:

- `last_tick_frame` (gen/seq/SHA) and its age;
- `fresh_preflight_status_frame` (gen/seq/SHA) from the PAGE handler's request;
- `frame_loaded_for_preflight` and `lastStatus_loaded`;
- the exact predicate booleans for SHA/generation/sequence/lifecycle terms;
- the reason that actually fired, not only the combined
  `preflight_identity_or_lifecycle_changed` label.

Policy effect: none. Visual-confirmation/input-evidence semantics: unchanged.
Implementation: not done. It would make future attribution exact without allowing
any stale input.

## Improvement 2 — pre-click frame stabilization (policy/timing change)

Before the original `b.click()`:

1. Read a fresh `/api/status` (not only the page's last tick).
2. Require its frame identity (SHA/gen/seq) to equal the PAGE displayed/lastStatus
   frame; optionally require the same identity for one bounded hold (e.g. one
   400 ms tick or 100 ms).
3. Only then invoke the one original `b.click()`. The PAGE freshness gate remains
   unchanged; if the frame changes again after the click, the PAGE still refuses.
4. Bound the wait within the existing whole-step budget; no automatic re-click,
   no second recovery, no deadline extension. If the frame does not stabilize,
   return a precise refusal (not_posted) and let the operator decide.

Policy effect: yes — a new pre-click wait/observation step, within the 60 s
whole-step budget; operator timing changes. Visual confirmation/input evidence
semantics: unchanged (same freshness/identity/confirm/unqueued gates). This is
the **only** design that addresses the stale-snapshot race, and it does not claim
the r48 run would have passed. Implementation: not done, not authorized.

## Improvement 3 — explicit new-frame notice (UX only)

When the freshness gate refuses, display the new frame identity/time and require
the operator to re-click on the new view. This is already the effective behavior
(`not_posted` + "请看最新画面…"); making it explicit is UX only. No gate change;
implementation not done.

## Rejected shortcuts (not acceptable)

- Remove/reduce the freshness gate, or skip preflight frame equality.
- Whitelist `NO CARD`, e014/2914, known generations, or OSD-blink states.
- Auto-pass when a hash is "stable", or auto-select a newer frame.
- Infinite/automatic retry, second recovery per step, deadline extension.
- Merge pin/confirm or declare visual confirmation automatically.
- Change r47/r48 source or policy to fake authorization; no external FX6 contact.

## Unknowns still requiring evidence

- Exact native/OSD cause of `e014…`→`2914…`; whether NO CARD presence/absence is
  causal; raw frame-pixel comparison.
- Exact guest-entry timestamp and `phases.first_kinds` interaction cutoff.
- Whether a bounded pre-click stabilization would eliminate the false refusal in
  this workload, and what budget cost it implies.
- No claim that any improvement makes the menu pass; r48 remains failed.
