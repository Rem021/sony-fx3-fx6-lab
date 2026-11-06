# RUN-PLAN — FX3MS2 collector candidate (next review only)

Status: **NOT AUTHORIZED; NOT RUN; NOT DEPLOYED**

This is a proposed plan for a future review. It is not an authorization and must not be executed from this task.

## Preconditions

1. Direct user approval for one new observation, separate from the consumed `fx6-framed-map-20261106T083817Z` allowance.
2. Reviewer decision on the `ADMISSION.md` blocker: explicitly accept the residual non-atomic-map/permission risk, or add a permitted mechanism that establishes current executable mappings at the paused state.
3. Fresh private run root under `team/parallel-review-20261105/runs`; both fixed FX3 locks free; no preemption.
4. Candidate CPIO SHA `79a87f32059cd3fa7bd2b1fa6484559ce5b2b2cacdad1dba6c456e13a64cf92d`, 453,200,484 bytes; target ELF SHA `1286759f2662e0af43f054cce72b700b24588bdd96532a6ff5a910b4af341eb9`.
5. Fixed FX3 platform, zero keys, one start, observation <=150 s, launch-to-cleanup <=180 s, no automatic retry, guest restore not attempted, no deployment.

## Proposed argv (not executed)

```sh
python3 -B host/run_candidate_v2.py \
  --approved-token APPROVE_FX6_MAP_COLLECTOR_SHORTREAD_20261106 \
  --new-run-approval \
  --run-root <fresh private root under parallel-review-20261105/runs>
```

The entry is default-disabled and currently has no user approval. The token is a proposed new token; it must not be reused from the old framed-map allowance.

## Required runtime evidence (future)

- actual Python/QEMU PIDs, start/end, CLI wall, launch-to-reap bound;
- native receipt and `prearm-identity.json` showing the header/PHDR/four-code-word gate before arming;
- complete `FX3MS2` frame with `snapshot_atomic=0`, read_count/eintr_count/attempts, maps digest, appFw rows, bias;
- two-key entry/return values or precise failure;
- independent serial fault scan;
- before/after hashes of candidate CPIO, appFw, baseline/QEMU/kernel/DTB, and original diagnostic package;
- own QEMU reaped, own locks released, no residual breakpoints, no other run touched;
- `guest_restore_status=unknown_not_attempted`, `boot_menu_passed=false`.

## Boundaries

- No run in this task; no VM/QMP/RSP/guest; no target ELF execution.
- FX6 boot/menu remains **not passed**.
- If the locks are busy at a future launch, `starts_used=0`, report occupancy, do not preempt.
