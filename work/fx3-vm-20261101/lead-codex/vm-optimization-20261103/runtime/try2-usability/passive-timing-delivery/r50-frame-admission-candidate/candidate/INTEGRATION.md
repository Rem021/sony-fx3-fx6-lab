# Integration differences (not integrated)

- Baseline actual PAGE is assembled by `trial_web_r24_review_snapshot.py` from
  `trial_web_v22_navigation_review.py` plus r24 review/confirm deltas. Its canonical
  script hash is `f9a428…`, full PAGE `551cbd…`.
- The r50 candidate is an **isolated final-script artifact** (`PAGE-script-obs-v2.*`)
  built by `make_candidate.py` from that assembled PAGE. `make_candidate.py` imports
  the actual r24 module read-only to extract/assemble, but no r47 source is edited.
- A future source integration would need to apply the same insertion to the base PAGE
  click handler (before r24 assembly), preserve all r24 replacements, regenerate the
  canonical/full PAGE, and rebind canonical/full PAGE hashes in the run identity and
  `planned_navigation_click.js` config. The helper itself is unchanged.
- r50 does **not** import the candidate into any server/runner/helper/default entry.
  The only runtime-adjacent artifact is a disabled-by-default prototype
  (`prototype/preclick_sync.js`) that is not imported anywhere.
- Future runtime/policy activation requires separate authorization; offline candidate
  preparation here does not create it.
