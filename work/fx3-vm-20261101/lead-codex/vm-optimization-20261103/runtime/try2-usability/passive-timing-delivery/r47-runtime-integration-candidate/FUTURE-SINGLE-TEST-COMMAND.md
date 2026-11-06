# Future single authorized run — command draft only

**STATUS: DRAFT. DO NOT RUN NOW.**
r45 already consumed its one VM run; no new VM authorization exists. This file is a
future command template, not an execution record. It must not be run until the
coordinator/user gives a fresh explicit authorization and a new Orca dispatch.

Profile: `r47-runtime-integration-60s`
Label: `v47runtime-n64-r47`
Candidate: this directory
Package: reused r42 package only (candidate `857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806`,
CPIO `59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63`); do not copy or rewrite it.
Fixed policy: whole-step 60s, native 12s, snapshot 20s, API16 restore 20s, startup 180s,
total 8min, 8 accepted / 10 attempts / 2 recoveries, 1 recovery per step. No auto retry,
no deadline extension, one Start only.

## 0. Preconditions (must be re-verified, not assumed)

```sh
VOL=$(diskutil info /Volumes/KAFU2T | awk -F': *' '/Volume UUID/{print $2}')
test "$VOL" = "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B" || { echo "wrong volume"; exit 1; }
cd /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r47-runtime-integration-candidate
shasum -a 256 -c SHA256SUMS
```

Operator must first read the current coordinator authorization and confirm: exactly one
future Start, no deployment, no FX6 implementation, no reuse of the r45 run directory.

## 1. Create a fresh future run directory (no process started)

Use a new `<task-id>` / `<dispatch-id>` / `<session>` from the future dispatch. The
`prepare_run.py` boundary requires `run-inputs/<task-suffix>`.

```sh
C="$(pwd)"
RUN="$C/run-inputs/<task-id-without-task_-prefix>"
python3 -B "$C/prepare_run.py" \
  --run-dir "$RUN" \
  --task-id "task_<id>" \
  --dispatch-id "ctx_<id>" \
  --session "fx3-deadline-<id>"
```

## 2. Offline preflight only (no browser/VM/QEMU)

```sh
FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/preflight.py"
```

This re-hashes the r42 package/CPIO, CORE/SOURCE, helper bindings, and performs an
import-only check. It does not start browser, server, QEMU or guest.

## 3. `launch_prepare.py` — web preparation only (no Start, no QEMU/guest)

```sh
FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/launch_prepare.py"
```

Actual source behavior: this starts the host runner process and the browser, opens the
loopback page, checks the canonical PAGE `f9a428…` / viewport 1280x1200 / HAR start /
`await-start-enabled`, and writes `PRESTART-READY.json`; it prints
`status=web_prepared_guest_not_started` and leaves the page `phase=awaiting_launch`.
Its `runtime.json` has `launch_id: null`. **It does not click the original Start button,
does not start QEMU, and does not start the guest.** Do not click `#start` manually and
do not start a second browser or runner.

## 4. `start_and_wait.py` — the one and only Start, 180s first-frame wait, initial standby

```sh
FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/start_and_wait.py"
```

Actual source behavior: it asserts `PRESTART-READY.json.passed`, requires that
`Start-once` does not exist, takes the exclusive lock, creates `Start-once`, clicks the
original `#start` exactly once, waits for `launch_request_id`, installs the 60s helper,
waits up to 180 host-monotonic seconds for the first loaded frame, then calls
`untimed_image.snapshot('initial-standby', HERE/'initial-standby', 0)`. It writes
`FIRST-FRAME-PASS.json`, `current-observation.json`, `ACTUAL-RUNNING-ARGV.json`, and
prints the snapshot image object. **This is the unique Start; never run it twice.** On
failure it writes `STARTUP-FAILURE.json` and invokes the original cleanup; do not
auto-retry or start another VM.

## 5. Operator human chain (human visual permission; no auto-retry)

Immediately after `start_and_wait.py`, **actually view** the initial standby image at
`$RUN/initial-standby/current.png` (receipt: `$RUN/initial-standby/capture-result.json`).
Only after that actual view:

```sh
FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/operate.py" standby_review "<operator actual view of initial-standby/current.png>"
```

Then use the exact commands in `$RUN/CLI-TEMPLATES.json`; examples:

```sh
FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/operate.py" click 1 "<target from NAVIGATION-PLAN>"
FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/operate.py" pin "<operator actual view of step-1 post-key image>"
FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/operate.py" confirm "<operator actual view of the pinned snapshot>"
# repeat click/pin/confirm for steps 2..8 only after each actual image view
```

If `click` returns `not_posted` / `preflight_identity_or_lifecycle_changed`:

1. The host has already recorded the read-only recovery observation; **actually view**
   `step-XX-attempt-YY/recovery-review/observation.png` and its receipt.
2. Only after that actual view:
   ```sh
   FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/operate.py" recovery_cancel "<explicit actual-view judgement>"
   ```
3. **Actually view** `step-XX-attempt-YY/recovery-cancel/observation/observation.png`.
4. Only after that actual view:
   ```sh
   FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/operate.py" recovery_review "<explicit actual-view judgement>"
   ```
5. The next `click` uses a new nonce. Do not auto-retry, auto-select an image, merge
   pin/confirm, or reuse the old frame/confirm.

## 6. End and cleanup

```sh
FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/cleanup.py"
```

`cleanup.py` invokes the original End, captures the ended page/HAR, checks the alarm,
closes the browser, and writes the strict cleanup evidence. Armed path must not
cancel/dispose; nonarmed path must have the original dispose receipt.

If cleanup is `unknown`, do not write a completed index or claim success; preserve the
unknown and the original failure, and report it to the coordinator. Do not start another
VM and do not retry.

## 7. `audit_after.py` — only if cleanup is actually completed

`audit_after.py` begins with `evidence.load(HERE/'CLEANUP-COMPLETED.json')`; a missing
or invalid completed index is a strict failure. Run it **only** when `cleanup.py`
returned `completed` and `CLEANUP-COMPLETED.json` exists and revalidates:

```sh
FX3_NAV_RUN_DIR="$RUN" python3 -B "$C/runtime-wrapper/audit_after.py"
```

If cleanup is `unknown`/missing, do **not** run `audit_after.py`; preserve the failure
and unknown evidence and report to the coordinator. Do not create a fake completed index,
do not start another VM, and do not auto-retry.

## 8. What this draft does not authorize

- No VM/browser/server/QMP/guest/deployment is authorized by this file.
- No second Start; r45's single run is spent.
- No fixed platform/firmware/CPIO/FX6 change.
- No automatic retry, no deadline extension, no synthetic visual pass.
- No claim that offline tests prove the real menu, recovery, cleanup or FX6 boot/speed.

Return the real receipts to the coordinator; coordinator decides acceptance.
