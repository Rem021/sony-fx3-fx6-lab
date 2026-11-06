# Admission analysis — FX3MS2 bounded sequential read

Status: **DESIGN CANDIDATE; RUNTIME ADMISSION BLOCKED; NOT AUTHORIZED; NOT RUN**

## 1. What changed from FX3MS1

| | frozen FX3MS1 | candidate FX3MS2 |
|---|---|---|
| map capture | one bounded `read()` + one-byte EOF probe | repeated `read()` until EOF |
| short read with more data | emits `ERROR short_read_more_data` | continues under bounds |
| cap | 262,144 bytes | **unchanged** 262,144 bytes |
| bounds | cap + 3 EINTR retries per read | cap + max 64 data reads + 1,000 ms + 8 EINTR/read + 32 total |
| identity | pid/starttime before/after | same `/proc/<pid>` dir and pid/starttime before/after |
| atomicity | single read treated as one capture | explicitly `snapshot_atomic=0`; complete stream, not atomic |
| host fallback | none | none (FX3MS1 frames are rejected explicitly) |

The change is **not** "remove the cap" or "accept truncated maps". It is a narrow state-machine fix: a short read is normal `seq_file` behavior; read to EOF under the same cap, and refuse to claim atomicity.

## 2. Host pause / identity gate

The frozen r6 `HostRunner.start()` order is: mapping provider -> QMP `stop` -> RSP connect -> `Observer` construction/`arm()`. The candidate adapter (`host/live_runner_v2.py`) wraps the RSP factory and performs, **after the QMP stop and before the Observer is constructed/armed**:

1. full appFw ELF header (64 bytes) read back via RSP `m`;
2. full PHDR table read back;
3. all four thunk/return machine words read back;
4. byte-for-byte comparison with the pinned `appFw-future-skip.so` (SHA `b1fe2274...`);
5. on any mismatch: close RSP, raise, no `Z1` is sent, no breakpoint is armed.

The offline E2E injects a corrupt first header word and asserts that **no `Z1` command appears** and no pre-arm identity record is written. This proves the gate ordering, not target behavior.

## 3. Breakpoint placement contract — why admission is blocked

The mapping frame is used to derive the appFw bias. After the pause, the host verifies the pinned ELF bytes at that bias. That proves, at the paused state:

- the header/PHDR/code bytes are readable at the derived addresses;
- the four breakpoint words match the pinned ELF.

It does **not** prove:

- that the multi-read map was an atomic snapshot (it is explicitly not);
- that the appFw mapping did not change between the reads;
- that the code pages are **currently executable** at the paused state. RSP `m` returns memory bytes, not guest page-table permissions; the allowed RSP/QMP surface used by the frozen runner does not expose a per-page PTE permission query.

The old admission checked `x` permission from the map rows. A complete multi-read frame can mix mapping states, so a row's `x` permission is only historical. The post-pause byte check cannot restore that proof. Therefore the strict breakpoint contract (address + bytes **and current executable mapping**) is **not established** from a non-atomic maps stream plus RSP reads alone.

Because the task forbids `SIGSTOP`/`ptrace`/guest-application modification to freeze consistency, there is no permitted way in this candidate to make the map atomic. The correct outcome is a **design blocker**, not a silent relaxation:

- do not fall back to legacy raw maps;
- do not remove the `snapshot_atomic=0` requirement;
- do not admit the candidate to a runtime observation until a reviewer either:
  - accepts the residual permission/continuity risk explicitly, with a documented conditional contract, or
  - adds a permitted mechanism that establishes current executable mappings at the paused state.

This candidate is therefore delivered for offline review only. It is not a run authorization and must not be installed/deployed.

## 4. Semantics change (separate argument)

Changing from "one read + probe" to "read to EOF" changes the evidence from a single bounded read to a complete stream that may span multiple kernel `seq_read` calls. This is a **semantic change** even though the cap and guest path are unchanged. It is justified only by the reproduced short-read failure and is bounded by the explicit limits. It must be reviewed separately; host fixtures and the fake HostRunner E2E do not constitute target runtime evidence.

## 5. Prohibited shortcuts not used

- No `SIGSTOP`, `ptrace`, `process_vm_*`, or guest application modification to freeze the maps.
- No second guest read appended after a failed frame, and no fallback to the old parser.
- No change to the fixed FX3 platform, original diagnostic package, frozen r6, or run policy.
- No target execution, VM, QMP, RSP, guest, deployment, or runtime authorization in this task.
