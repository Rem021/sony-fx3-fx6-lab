# r50 design — offline candidate only

Status: **offline candidate / diagnosis preparation**, not runtime, not deployed, not
integrated into the default entry, and no new VM/browser/server/QMP/guest. r47/r48/r49
remain read-only. The failed r48 result and the absence of new runtime authorization
are unchanged.

## Target A — obs_v2 (implemented as an isolated PAGE candidate)

The candidate PAGE is built from the actual r47 canonical script by `make_candidate.py`.
Hashes are in `candidate/PAGE-IDENTITY-CANDIDATE.json`:

- baseline canonical `f9a428…`, full PAGE `551cbd…`;
- candidate canonical `70d08c…`, full PAGE `940694…`, served replay `75c1e9…`;
- diff `candidate/DIFF-obs-v2.patch`, SHA `7825a9…`; 52 added / 4 rewritten lines
  (the original condition/reason/function-call text is unchanged).

The insertion only records, in `window.__fx3FrameAdmissionObsV2`, when the original
combined freshness/identity rejection is taken:

- clicked, displayed, lastStatus and fresh preflight SHA/gen/seq;
- page performance-monotonic click/display/lastStatus, preflight request start/end,
  decision times;
- all predicate values in original source order, `first_true_term`, and the
  `evaluated_terms` prefix (short-circuit prefix);
- original `reason:'preflight_identity_or_lifecycle_changed'` remains the reason;
- sequence is explicitly `sequence_in_gate:false`; it is observation only;
- no `frameLoadedFor` call, no fetch/status/key request, no condition rewrite, no
  confirm/pin/ARM/recovery change. `frameLoadedFor`-equivalent values are computed
  from captured values only after the original decision.

This is not integrated. Future integration must patch the base PAGE source/assembly
(`trial_web_v22_navigation_review.py` / `trial_web_r24_review_snapshot.py`), rebind
canonical/full PAGE hashes, and re-approve any runtime use. No r47 source was changed.

## Target B — pre-click sync prototype (disabled, comparison failed to show benefit)

`prototype/preclick_sync.js` is a standalone, disabled-by-default function. It is not
imported by the PAGE/helper. It performs only bounded read-only status/load checks:

- defaults: `maxWaitMs=200`, `sampleIntervalMs=50`, `requiredStableSamples=2`,
  `maxAttempts=3`, `reserveMs=500`, all constrained by the existing 60 s arm
  (`deadline = min(now+maxWait, due-reserve)`); it never resets/rearms the arm;
- requires the page displayed frame to be loaded; fresh status must be ready and
  equal the displayed frame's SHA/generation for 2 stable samples; sequence is
  recorded only;
- if the fresh frame differs at any point: explicit `displayed_frame_superseded`
  refusal and re-view requirement; no auto-selection, no rebinding, no click;
- if not ready: bounded retry up to max attempts, then explicit refusal;
- if expiry/identity changes: refuse before click;
- returns `allow`; the caller may invoke the one original `b.click()` at most once.
  The function never clicks, confirms, pins, posts, or resets the arm; the original
  PAGE freshness/identity/confirm/unqueued gates remain in force after `allow`.

Comparison (`tests/preclick_compare.cjs`, fake DOM/fake clock, actual baseline PAGE +
helper; prototype invoked only on the allowed path):

| scenario | baseline | prototype | key POSTs | reads / waited | delta |
|---|---|---|---|---|---|
| same frame | accepted, key 1 | allowed then accepted, key 1 | 1 / 1 | 0 / 2 reads, 50.5 ms | no gain; +50.5 ms latency |
| r48 attempt 1 changed | not_posted, key 0 | pre-click refusal (no attempt), key 0 | 0 / 0 | 0 / 1 read, 0.25 ms | earlier refusal; no admission gain; attempt/recovery accounting changes |
| r48 attempt 2 changed | not_posted, key 0 | pre-click refusal (no attempt), key 0 | 0 / 0 | 0 / 1 read, 0.25 ms | same |
| prepared then changed | not_posted, key 0 | allowed; PAGE still not_posted, key 0 | 0 / 0 | 0 / 2 reads, 50.5 ms | no gain; added latency |
| never ready | not_posted, key 0 | pre-click refusal after 3 reads, key 0 | 0 / 0 | 0 / 3 reads, 100.75 ms | no gain; bounded cost |
| expired arm | no click, key 0 | pre-click refusal, key 0 | 0 / 0 | 0 / 0 | no gain |
| identity changed | no click, key 0 | pre-click refusal, key 0 | 0 / 0 | 0 / 0 | no gain |

Conclusions: no scenario gained acceptance of a changed frame; only the same-frame
case accepted, at extra latency. The changed-frame path converts a PAGE `not_posted`
attempt into a host pre-click refusal, which avoids an attempt/recovery but is a
policy/accounting change and is **not** a demonstrated menu/admission improvement.
The prototype therefore remains disabled and is **not integrated**; the comparison
is retained as failure evidence. Any future run/policy activation is a separate
decision, not authorized by this design.

## Preservation / constraints

- 60 s step arm, native 12 s, snapshot TTL 20 s, total 8 min, and original recovery
  counts are unchanged; the prototype does not reset the 60 s arm.
- No hash-stability visual confirmation, no frame/NO CARD whitelist, no automatic
  new-frame selection as reviewed, no automatic repeated click, no skip of human
  new-image review, no pin/confirm merge.
- B's pre-click refusal path has no PAGE attempt/key; the original PAGE attempt/
  recovery semantics are preserved for any click that is actually attempted.
- No new runtime authorization is implied; no deployment/default-entry change.

## Unknown / limitations

- Fake DOM/fake clock, not real browser/network timing; no actual visual confirm.
- Candidate obs_v2 is isolated PAGE script, not integrated/imported source.
- B latency is synthetic read count/interval, not measured network latency.
- No claim of menu, speed, FX6, CPU/FIFO, or guest success.
