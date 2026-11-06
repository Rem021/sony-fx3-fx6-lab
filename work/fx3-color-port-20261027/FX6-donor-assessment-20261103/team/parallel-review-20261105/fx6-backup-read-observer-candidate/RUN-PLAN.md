# RUN-PLAN — r5 stop-only / full-clean candidates

Status: host-only, **not authorized/run**. Preflight outside 180s; launch→own-child reap inside 150/180 budgets.

## Full clean candidate (blocked on inherited contract)

```sh
python3 observer/run_lifecycle.py --approved-token APPROVE_GRMREAL46_TWO_KEYS_0214_0218 --new-run-approval --run-root <new-private-root>
```
- Only after separate authorization and an established/cancellable inherited API16/unbind callback. Current 3a08 old restore contract is unestablished, so full clean is blocked. No actual launch this turn.

## HOST_STOP_ONLY_OBSERVATION candidate

```sh
python3 observer/run_stop_only.py --approved-token APPROVE_GRMREAL46_TWO_KEYS_STOP_ONLY --new-run-approval --run-root <new-private-root>
```
- One start, zero keys, <=150s observation/<=180s total; fixed baseline/3a08/b1fe; no guest control/code/data writes, no inherited callback.
- Two thunk entries/returns, RSP addressless c; cleanup pause/z1/close RSP/QMP quit→reap→locks. Outputs `two_keys_observed`, `host_cleanup_complete`, `guest_restore_status=unknown_not_attempted`, `boot_menu_passed=false`; exit 0 only observation+host cleanup.
- This is a candidate for future user acceptance of an observation termination mode; not authorization or policy change.

## Tests (offline only)

```sh
python3 tests/test_host.py
python3 tests/test_rsp_host.py
python3 tests/test_adapter.py
python3 tests/test_runner.py
python3 tests/test_stateful_transport.py
python3 tests/test_e2e_stateful.py
```
No QEMU start. Fixed manifest/entry paths are in `SHA256SUMS` and `RESULT.json`.

## r6 stop-only success gate

- rc0 requires `two_keys_observed && host_cleanup_complete && input_unchanged_after is True && postflight.error is None && verification_failed is False`; hash drift/error -> nonzero while preserving observation fields.
- UUID/preflight/run-root rejection never creates a directory or overwrites a receipt; only HostRunner-owned run root gets a receipt.
- cleanup switches RSP to cleanup phase before z1; observation expiry may use remaining total; total expiry performs no business IO and does not resume guest.
