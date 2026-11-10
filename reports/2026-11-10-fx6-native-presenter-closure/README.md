# FX6 Ver. 6.01 Cold-Boot Lifecycle Completion & `FX6_NATIVE_FAITHFUL=1` Big6 Presenter Progression (2026-11-10)

## 1. Executive Summary

This report documents the Track 1B single-variable progression from the `work/fx6-worker-pool-restore-20261107` 129-TID `Application_System_Init` baseline (where `AppFw` stalled at `model_future::wait` `appFw.so +0x1acd874` / `+0xc09de4` while `SeqQueueCommon` waited on `0x032d` `init_hdmi`) to genuine native `ux::gfxeng::GraphicsEngine::drawFramebuffer()` execution and `FX6_OSD_FLUSH` output under strict **`FX6_NATIVE_FAITHFUL=1`** rules (`subst_color=0`, `subst_image=0`, `forced_render=0`, `skipped_node=0`, `lock_bypass=0`).

### Headline Milestones Achieved

1. **Q1 + Q2 Static & Runtime Closure (`Round 1`: `r1a` -> `r1b` -> `r1c`)**:
   - Disassembled FX6 `bin/im.elf` (`main` `0x401a88`) and `lib/libMWF.so` (`MWF_Init` `+0x27e74`, `MWF::RsrcRelation::Initialize` `+0x3a57c`, `MWF::ObjShLock::ObjShLock` `+0x3b300`, `MWF::MonDrv::Init` `+0x3f21c`).
   - Verified `MWF_Init(void)` requires the `MonDrv::Init` `/dev/mem` FixedArea backup keys `Backup_read_8Byte(0x00fa0028) = 0x429200000UL` and `Backup_read_8Byte(0x00fa005d) = 0x100000UL`.
   - Initialized real `MWF_Init()` in `appfw-launch` (`FX6_MWF_POST smp_monErr=0x1062c50 shLockMgr=0x1062f40 shLockAcsr=0x1063000 shLockGlobal=0x10630c0 lock_bypass=0`), removed all `pthread_mutex_*` low-address bypass masks, and un-NOPed `appFw.so +0x12d8254` (`bl 0x20ed13c`, all 70 `MWF` infra wrappers) — reaching **146 live threads** (`mwf_monitor_inp`, `IWrapperBB`, `IWrapperHDMI`, `IWrapperImaging`, `uipc_proxy_0..3`, etc.) with **zero crashes**.
2. **Unblocking `SeqQueueCommon` & Constructing Native Presenter (`Round 2`: `r2` -> `r2b` -> `r2c`)**:
   - Synthesized minimal ABI-compliant UIPC completions on `osal_snd_msg` for `init_hdmi` (`0x92840747 -> 0x81cf611b`, 12B `0x200d` / `0x132d`) and `get_rtc_status` (`0x92d2091c -> 0x81d705bd`, 2B `0x1700`).
   - `AppFw` (`tid=225`) naturally exited `model_future::wait` (`+0x1acd874` / `+0xc09de4`), executed `ScreenManager::initialize` (`+0xde31ac`, `sm_impl=0x7f7c01db00`, `sm_worker=0x7f7c012b90`, `gate_7d4=2`, `gate_7d0=3`), registered `GRM_fbrmRegisterTriggerFrameworkCb(cb=appFw+0xc091d0, user=App*)` at `+0xc09e4c`, entered `App::run` (`+0xc0a20c`), allocated all 9 `UX_ScreenArea` descriptors (`FX6_UX_SCREEN_AREA=9`), and constructed genuine native Presenter slot 0 (`+0xde10f4`, `vptr_off=0x2e8d950`, `screen!=NULL`) across **153 live threads** after fixing `R_AARCH64_TLSDESC` GOT corruption (`0x2ef29f0`, `0x2ef2a00`).
3. **Q3 Trigger Pump & Genuine `FX6_NATIVE_FAITHFUL=1` Framebuffer Flush (`Round 3`: `r3` -> `r3b-grm-complete`)**:
   - Un-NOPed `appFw.so +0xc09e50` (`App::start_utimer`, 50 Hz `0x02010094 -> 0x5503e0`), pumped `cb=appFw+0xc091d0` at 25 Hz (`gate_7d4=0`, `gate_7d0=0`), supplied `CIFInfraIndctr` (`0x807e002f -> 0x807e0030`) completions, preserved the `bool` return value of `ux::gfxeng::GraphicsEngine::drawFramebuffer()` (`libuxengine.so +0x839c8`), stubbed `GRM_fbrmPrepareUpdate` / `GRM_fbrmPrepareFlip` (avoiding `ExternalOSDIF::waitUpdateComplete(NULL)`), and fixed `GRM_GPERMCmdCbParamRecord` (`user_data` at `+0x08`).
   - **`r3b-grm-complete` ran the full 52.45s window with 153 live threads and zero crashes**, executing genuine `ux::gfxeng::GraphicsEngine::drawFramebuffer()` (`FX6_MILESTONE_DRAW_FB #1 rc=1`, `#2 rc=0` from `appFw+0xc09a94`), issuing **2 real `FX6_GPE_FILLRECT` calls** (`1024x540` `0x00000000` + `1024x540` `0xff000000`) and **13 `FX6_OSD_FLUSH` updates** (`gpermDrawFlush #12`, `fbrmUpdate #13`), and committing **`552,960` real nonzero pixels (`2,211,840` bytes, `sha256=9c033ca44a46dc679cd2e625bd686e1de137c5dce019b9cf2500dc333ec5c00b`)** into physical GPE0 guest RAM (`0x41e001000`) with zero synthetic color/icon injection.
4. **Extended Screen-Open Probe & Exact Next Coordinate (`r3c-screen-open`)**:
   - Unblocking `0x909a015a` (`cmd=0x010a`) advanced `SeqQueueCommon` (`tid=250`) through **51 additional camera/codec setup RPCs** (`FX6_UIPC_SND=146`, `FX6_QUEUE_OBS_EXIT=79`, `FX6_UIPC_COMPLETION_=71`) into `mpr::SetMovieRecParam` -> `libXavcMxf::SetClipName` (`libmpr.so +0x54c184`), pinpointing the exact next cold-boot contract: `libXavcMxfGetSlotTypeFromMediaId(0)` (`libmpr.so +0x53c850`, `libXavcMxf.cpp:274`) asserts because `InfraMediaConfig_Init` (`libInfraMediaConfig.so +0x6750`) / `0x807b002b` (`libInfraAvbbc.so`) media-slot IDs (`0x1000` Slot A / `0x1010` Slot B) have not yet been initialized.

---

## 2. Deliverable Artifacts & Reproducible Harness

All created files reside strictly within the two authorized directories:

- Static ABI & disassembly contracts:
  - [`STATIC-CONTRACTS.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-10-fx6-native-presenter-closure/STATIC-CONTRACTS.md)
  - [`inspect_static_contracts.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/inspect_static_contracts.py)
  - [`static-contracts-summary.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/static-contracts-summary.json)
- `FX6_NATIVE_FAITHFUL=1` launcher, `LD_PRELOAD` shim, and single-variable QEMU runner:
  - [`appfw-launch.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/appfw-launch.c)
  - [`libgrm-fbinit9.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/libgrm-fbinit9.c)
  - [`got_table_fx6.inc`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/got_table_fx6.inc)
  - [`build_and_run_round.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/build_and_run_round.py)
- Experimental run logs & structured summaries (`serial.log`, `milestones.log`, `summary.json`):
  - [`work/fx6-native-presenter-closure-20261110/runs/`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs) (`r1a-mwf-init`, `r1b-mwf-fixedarea`, `r1c-mwf-infra70`, `r2-seqqueue-unblock`, `r2b-rtc-presenter`, `r2c-tlsdesc-fixed`, `r3-native-faithful`, `r3b-grm-complete`, `r3c-screen-open`)

### Reproducible Commands

```sh
# Regenerate static disassembly summary JSON
/usr/bin/python3 work/fx6-native-presenter-closure-20261110/inspect_static_contracts.py

# Round 1: Real MWF_Init + ObjShLock + all 70 MWF infra wrappers (146 TIDs, 0 crashes)
/usr/bin/python3 work/fx6-native-presenter-closure-20261110/build_and_run_round.py \
  --round 1 --restore-infra70 1 --run-id repro-r1c --duration 40

# Round 2: SeqQueueCommon init_hdmi + RTC completions -> ScreenManager::initialize + Presenter slot 0 (153 TIDs, 0 crashes)
/usr/bin/python3 work/fx6-native-presenter-closure-20261110/build_and_run_round.py \
  --round 2 --restore-infra70 1 --run-id repro-r2c --duration 45

# Round 3 (Steady-State Milestone): App::start_utimer + 25Hz TriggerFrameworkCb pump -> drawFramebuffer + 552,960 GPE0 pixels (153 TIDs, 0 crashes)
/usr/bin/python3 work/fx6-native-presenter-closure-20261110/build_and_run_round.py \
  --round 3 --restore-infra70 1 --reply-all-200d 0 --run-id repro-r3b --duration 50

# Round 3 (Extended Screen-Open Probe): + 0x909a015a completion -> 146 UIPC sends -> libXavcMxf.cpp:274 media-slot assertion
/usr/bin/python3 work/fx6-native-presenter-closure-20261110/build_and_run_round.py \
  --round 3 --restore-infra70 1 --reply-all-200d 1 --run-id repro-r3c --duration 55
```

> [!NOTE]
> `build_and_run_round.py` compiles binaries into `/private/tmp/fx6-native-closure-build-<pid>-<run_id>`, repacks a temporary guest `.cpio` in `/private/tmp/fx6-native-closure-<pid>-<run_id>.cpio`, uses isolated `/private/tmp/fx6-native-<pid>-qmp.sock` sockets, terminates only its own `proc.pid` inside `finally:`, and deletes all `/private/tmp` build/cpio/socket artifacts on exit. No binary `.cpio`/`.so`/`.elf` files are written to `work/` or `reports/`.

---

## 3. Summary of Closed Static & Runtime ABI Contracts (Step A)

Full disassembly listings and symbol offsets are recorded in [`STATIC-CONTRACTS.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-10-fx6-native-presenter-closure/STATIC-CONTRACTS.md). Key findings:

| Contract | Binary & Offset | Verified Signature / Layout | Key Conclusion |
| --- | --- | --- | --- |
| **Q1: `MWF_Init`** | `im.elf` `0x401cb4` -> `libMWF.so +0x27e74` | `void MWF_Init(void)` | Zero-arg `void`. Allocates `_ZN3MWF6RsrcDP10smp_monErrE` (`+0x67e00`, `0x18`B), runs `MWF::RsrcRelation::Initialize()`, and spawns `mwf_monitor_inp`. |
| **Q1b: `MonDrv::Init`** | `libMWF.so +0x3f21c` | `Backup_read_8Byte(0x00fa0028, &phys)` / `(0x00fa005d, &sz)` | Must return guest RAM carveout (`0x429200000UL`, `0x100000UL`) so `/dev/mem` `mmap` succeeds and `MonQueue` pointers are non-NULL. |
| **Q2: `ObjShLock`** | `libMWF.so +0x3b300`, `+0x3a57c` | `sizeof(MWF::ObjShLock) == 0xb8`; `pthread_mutex_t` at `this + 0x28` | `MWF_Init` initializes all 3 global `ObjShLock*` (`+0x68688`, `+0x68690`, `+0x68698`). `pthread_mutex_lock(0x28)` faults were caused solely by skipping `MWF_Init`. |
| **Q3: `TriggerFrameworkCb`** | `libgrm.so +0x236b8`, `appFw.so +0xc09e48` / `+0xc091d0` | `int GRM_fbrmRegisterTriggerFrameworkCb(void (*cb)(void *), void *ud)` | `appFw` registers `cb = appFw + 0xc091d0`, `ud = App*`. Callback clears `gate_7d4` (`App+0x7d4`) and `gate_7d0` (`App+0x7d0`) to `0` and wakes `App::run` (`+0xc0aca8 -> +0xc09a94`). |
| **Q3b: `App::start_utimer`** | `appFw.so +0xc09e50` -> `+0xc0a0e0` | `create_utimer(..., 20000000 ns)` (`0x02010094 -> 0x5503e0`) | Unconditional 50 Hz periodic timer started right after `TriggerFrameworkCb` registration; previously NOPed in `restore295`. |
| **GPERM Async Callback** | `libgrm.so` / `libuxengine.so +0x930e8` | `struct GRM_GPERMCmdCbParamRecord { uint64_t status; void *user_data; }` | `libuxengine.so` `thunk_gpeCallback` reads `param->user_data` at **`[x0, #8]`** (not `x0` directly) and calls `vtable[4]` (`onComplete`). |
| **`GRM_fbrmPrepare*`** | `libgrm.so +0x2352c` -> `+0x21f70` | `int GRM_fbrmPrepareUpdate(int plane)` / `GRM_fbrmPrepareFlip(int plane)` | Real `libgrm.so` dereferences `s_pExternalOSDIF[plane]` (`NULL` when `GRM_fbrmInitialize` is shimmed). Shimming both to return `0` prevents `NULL + 0` SEGV during `drawFramebuffer()`. |

---

## 4. Single-Variable Experimental Progression Matrix (Step B)

| Run ID | Config (`round`, `infra70`, delta) | Wall (s) | Live TIDs | `UIPC_SND` / `COMP` | `DRAW_FB` / `FLUSH` / `GPE0_NZ` | Outcome & Blocking / Fault Coordinate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| [`r1a-mwf-init`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r1a-mwf-init/summary.json) | `R1`, `infra70=0`, real `MWF_Init()`, `lock_bypass=0` | 8.93 | 1 | 0 / 0 | 0 / 0 / 0 | Caught `MonDrv::Init` `/dev/mem` contract (`ERROR : Failed to mmap!` -> `SIGSEGV` at `MonQueue::GetQueueRemain` `libMWF.so +0x409d0`). |
| [`r1b-mwf-fixedarea`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r1b-mwf-fixedarea/summary.json) | `R1`, `infra70=0`, + `0x00fa0028` / `0x00fa005d` carveout | 44.19 | 130 | 0 / 0 | 0 / 1 / 0 | **PASS (0 crashes)**. `FX6_MWF_POST` non-NULL (`smp_monErr=0x1062c50`, 3x `ObjShLock*` valid). Paused at baseline `model_future::wait` (`+0x1acd874`). |
| [`r1c-mwf-infra70`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r1c-mwf-infra70/summary.json) | `R1`, `infra70=1` (`0x12d8254` un-NOPed) | 40.22 | 146 | 0 / 0 | 0 / 1 / 0 | **PASS (0 crashes)**. All 70 `MWF` infra wrappers initialized (`IWrapperBB`, `IWrapperHDMI`, `uipc_proxy_0..3`, etc.) with `lock_bypass=0`. |
| [`r2-seqqueue-unblock`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r2-seqqueue-unblock/summary.json) | `R2`, `infra70=1`, + `0x92840747` (`init_hdmi` `0x132d`) completion | 44.22 | 152 | 400 / 1 | 0 / 1 / 0 | **PASS (`model_future::wait` `+0xc09de4` unblocked!)**. Completed `ScreenManager::initialize`, registered `TriggerFrameworkCb` (`+0xc09e4c`), entered `App::run` (`+0xc0a20c`); `SeqQueueCommon` waited on `0x92d2091c` (RTC). |
| [`r2b-rtc-presenter`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r2b-rtc-presenter/summary.json) | `R2`, `infra70=1`, + `0x92d2091c` (`0x1700`) RTC completion | 17.28 | 143 | 19 / 2 | 0 / 1 / 0 | Constructed native Presenter slot 0 (`vptr_off=0x2e8d950`, `screen!=NULL`)! Caught `R_AARCH64_TLSDESC` GOT overwrite (`0x2ef29f0` / `0x2ef2a00`) on `std::call_once`. |
| [`r2c-tlsdesc-fixed`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r2c-tlsdesc-fixed/summary.json) | `R2`, `infra70=1`, + `skipped_tlsdesc=2` | 46.44 | 153 | 20 / 2 | 0 / 1 / 0 | **PASS (0 crashes, 153 TIDs)**. Presenter slot 0 entered `open`/`activate` (`+0x13abb50 -> +0x13a9b40`); `SeqQueueCommon` waited on `0x807e002f` (`CIFInfraIndctr`). |
| [`r3-native-faithful`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r3-native-faithful/summary.json) | `R3`, `infra70=1`, un-NOP `0xc09e50` `start_utimer` + 25Hz pump + `0x807e002f` | 12.08 | 1 | 15 / 1 | 0 / 1 / 0 | Trigger pump reset `gate_7d4=0 gate_7d0=0` and drove `App::run` (`+0xc09a94`) into `GraphicsEngine::drawFramebuffer()`! Caught `GRM_fbrmPrepareUpdate` (`libgrm.so +0x21f70`) `NULL` deref. |
| **[`r3b-grm-complete`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r3b-grm-complete/summary.json)** | **`R3`, `infra70=1`, + `GRM_fbrmPrepare*` & `GRM_GPERMCmdCbParamRecord` fixes** | **52.45** | **153** | **95 / 39** | **2 / 13 / 552,960** | **MAIN ROUND 3 MILESTONE (0 crashes, 153 TIDs)**. Real `drawFramebuffer()` (`rc=1`), 2x `FX6_GPE_FILLRECT`, 13x `FX6_OSD_FLUSH`, **`552,960` GPE0 pixels** (`0xff000000`). Presenter `open` waits on `0x909a015a` (`seq=95`). |
| [`r3c-screen-open`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r3c-screen-open/summary.json) | `R3`, `infra70=1`, + `0x909a015a` (`reply_all_200d=1`) completion | 16.20 | 148 | 146 / 71 | 2 / 13 / 552,960 | Unblocked `0x909a015a`, advancing through 51 more camera/codec RPCs into `libXavcMxf.cpp:274` (`libXavcMxfGetSlotTypeFromMediaId(0)` `SIGABRT`). |

---

## 5. Detailed Round-by-Round Evidence & Verbatim Serial Excerpts

### 5.1 Round 1: Real `MWF_Init` & Removal of `ObjShLock` / `pthread_mutex_*` Bypass (`r1a` -> `r1b` -> `r1c`)

- **`r1a-mwf-init` Root Cause Captured**: Calling real `MWF_Init()` (`libMWF.so +0x27e74`) without FixedArea keys caused `MWF::MonDrv::Init` (`libMWF.so +0x3f21c`) to pass `offset=0, length=0` to `mmap("/dev/mem")`, printing `ERROR : Failed to mmap!` and faulting at `MWF::MonQueue::GetQueueRemain` (`libMWF.so +0x409d0`, `ldr w0, [x8, #0x14]` with `x8=0`).
- **`r1b-mwf-fixedarea` & `r1c-mwf-infra70` Resolution**: Providing `0x00fa0028 -> 0x429200000UL` and `0x00fa005d -> 0x100000UL` in `Backup_read_8Byte` satisfied `MonDrv::Init`, initialized `smp_monErr` and all three `ObjShLock` instances, spawned `mwf_monitor_inp`, and allowed un-NOPing `0x12d8254` (`bl 0x20ed13c`, all 70 `MWF` infra wrappers) with **zero `pthread_mutex_*` null/low-address guards** (`lock_bypass=0`):

```text
FX6_MWF_PRE fn=0x7f6ee77e74 smp_monErr=(nil) shLockMgr=(nil) shLockAcsr=(nil) shLockGlobal=(nil)
FX6_BACKUP_READ8 id=0x00fa0028 val=0x429200000 rc=0
FX6_BACKUP_READ8 id=0x00fa005d val=0x100000 rc=0
FX6_MWF_POST smp_monErr=0x1062c50 shLockMgr=0x1062f40 shLockAcsr=0x1063000 shLockGlobal=0x10630c0 lock_bypass=0
```

In `r1c-mwf-infra70`, `/proc/217/task` reached **146 live threads** (up from 129 in `restore295`), including `mwf_monitor_inp` (`tid=224`), `IWrapperBB` (`tid=228`), `IWrapperBBSub` (`tid=229`), `IWrapperHDMI` (`tid=230`), `IWrapperBizBBIn` (`tid=231..232`), `uipc_proxy_0..3` (`tid=233..235, 237`), `IWrapperImaging` (`tid=236`), `IWrapperMprNull` (`tid=238`), `IWrapperUPM` (`tid=239`), `IWrapperDataSer` (`tid=241`), `IWrapperMwfInh` (`tid=242`), `IWrapperLANC` (`tid=243`), `IWrapperHotshoe` (`tid=244`), and `IWrapperAccy` (`tid=245`), with zero low-address faults across 40.22s.

---

### 5.2 Round 2: Unblocking `SeqQueueCommon` `model_future::wait` & Constructing Native Presenter (`r2` -> `r2b` -> `r2c`)

1. **Unblocking `init_hdmi` (`r2-seqqueue-unblock`)**:
   When `SeqQueueCommon` sent `dest=0x92840747, src=0x81cf611b, w0=0x200d, cmd=0x032d` (`init_hdmi`), `libgrm-fbinit9.so` allocated a 12-byte UIPC pool block via `osal_get_mpf(0x837f0001)` and posted `[0x200d, 0x132d, 0x000c, 0x0001, 0, 0]` to `0x81cf611b`.
   - `AppFw` (`tid=225`) immediately exited `model_future::wait` (`+0x1acd874` / `+0xc09de4`), ran `ScreenManager::initialize` (`+0xde31ac`), registered `GRM_fbrmRegisterTriggerFrameworkCb` (`+0xc09e4c`), and entered `App::run` (`+0xc0a20c`).
2. **Unblocking `get_rtc_status` & Fixing `R_AARCH64_TLSDESC` GOT Entries (`r2b` -> `r2c-tlsdesc-fixed`)**:
   - Replying `[0x1700]` to `dest=0x92d2091c -> 0x81d705bd` (`get_rtc_status`) allowed `ScreenManager` worker threads to construct Presenter slot 0 (`+0xde10f4`, `vptr_off=0x2e8d950`, `screen=0x7f67d88730`).
   - `r2b-rtc-presenter` caught a subtle launcher bug inherited from `got_table_fx6.inc`: offsets `0x2ef29f0` and `0x2ef2a00` are 16-byte `R_AARCH64_TLSDESC` pairs (`resolver_fn_ptr`, `tls_offset`) used by `__once_callable` / `__once_call` inside `std::call_once`, which the static GOT binder had overwritten with symbol addresses, causing `SEGV_ACCERR` when jumping to data address `libstdc++.so.6 + 0x154168`.
   - Skipping `0x2ef29f0` and `0x2ef2a00` in [`appfw-launch.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/appfw-launch.c) (`skipped_tlsdesc=2`) resolved `std::call_once` cleanly in `r2c-tlsdesc-fixed` (**153 live threads, 46.44s, 0 crashes**).

---

### 5.3 Round 3: `FX6_NATIVE_FAITHFUL=1` Trigger Pump, Real `drawFramebuffer`, & `FX6_OSD_FLUSH` (`r3` -> `r3b-grm-complete`)

In Round 3 (`FX6_ROUND=3`), we:
1. Removed the NOP at `appFw.so +0xc09e50` so `App::start_utimer` (`+0xc0a0e0`) ran natively (`0x02010094 -> 0x5503e0`).
2. Spawned a dedicated 25 Hz (`40,000 us`) trigger pump thread inside `GRM_fbrmRegisterTriggerFrameworkCb` invoking Sony's registered callback `cb = appFw + 0xc091d0` with `ud = App*`.
3. Added UIPC completion for `libInfraIndctr.so` (`dest=0x807e002f -> reply_qid=0x807e0030`), stubbed `GRM_fbrmPrepareUpdate` / `GRM_fbrmPrepareFlip` (after `r3-native-faithful` caught `libgrm.so +0x21f70` `ExternalOSDIF::waitUpdateComplete(NULL)`), preserved the `bool` return value of `ux::gfxeng::GraphicsEngine::drawFramebuffer` (`libuxengine.so +0x839c8`), and passed `&GRM_GPERMCmdCbParamRecord` (`{0, user_data}`) to GPERM async callbacks.

#### Verbatim Serial Milestones from `r3b-grm-complete` (`runs/r3b-grm-complete/milestones.log`)

```text
FX6_MWF_PRE fn=0x7f6ee77e74 smp_monErr=(nil) shLockMgr=(nil) shLockAcsr=(nil) shLockGlobal=(nil)
FX6_MWF_POST smp_monErr=0x1062c50 shLockMgr=0x1062f40 shLockAcsr=0x1063000 shLockGlobal=0x10630c0 lock_bypass=0
FX6_MILESTONE_TRIGGER_CB_REG cb=0x7f656781d0(appFw+0xc091d0) user=0x7f64992658 lr=0x7f65678e4c(appFw+0xc09e4c)
FX6_SCREEN_MGR_STATE tag=trigger_cb_reg app=0x7f64992658 sm_impl=0x7f6001d2f0 sm_worker=0x7f60012b90 gate_7d4=2 gate_7d0=3
FX6_TRIGGER_PUMP_SPAWN rc=0 th=0x7ddddfe1e0
FX6_TRIGGER_PUMP_START tid=315 period_us=40000
FX6_TRIGGER_PUMP_TICK #1 cb=0x7f656781d0 ud=0x7f64992658 gate_7d4=0 gate_7d0=0 draw_fb=0 flush=1 prims=0
FX6_GPE_FILLRECT #1 (0,0,1024,540) argb=0x00000000 cb=(nil) ud=(nil) subst_color=0
FX6_OSD_FLUSH fillrect #3 prims=1 fill=1 blit=0 nz_pixels=0 subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0
FX6_GPE_FILLRECT #2 (0,0,1024,540) argb=0xff000000 cb=(nil) ud=(nil) subst_color=0
FX6_OSD_FLUSH fillrect #5 prims=2 fill=2 blit=0 nz_pixels=552960 subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0
FX6_OSD_FLUSH gpermDrawFlush #12 prims=2 fill=2 blit=0 nz_pixels=552960 subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0
FX6_OSD_FLUSH fbrmUpdate #13 prims=2 fill=2 blit=0 nz_pixels=552960 subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0
FX6_MILESTONE_DRAW_FB #1 self=0x7f6000c010 rc=1 lr=0x7f65678a94(appFw+0xc09a94) real=0x7f79d979c8
FX6_MILESTONE_DRAW_FB #2 self=0x7f6000c010 rc=0 lr=0x7f65678a94(appFw+0xc09a94) real=0x7f79d979c8
FX6_SCREEN_MGR_STATE tag=pump app=0x7f64992658 sm_impl=0x7f6001d2f0 sm_worker=0x7f60012b90 gate_7d4=0 gate_7d0=0
FX6_PRESENTER_SLOT idx=0 tag=pump obj=0x7f68dabf08 vptr=0x7f678fc950 vptr_off=0x2e8d950 screen=0x7f68cae730
```

- **Physical GPE0 Readback Verification (`0x41e001000`, `1024x540` ARGB8888)**:
  - `bytes = 2,211,840`, `total_pixels = 552,960`, **`nonzero_pixels = 552,960` (`100%` committed by `libuxengine.so` via `GRM_gpermFillRect` #2 -> `GRM_gpermDrawFlush` #12 -> `GRM_fbrmUpdate` #13)**, `sha256 = 9c033ca44a46dc679cd2e625bd686e1de137c5dce019b9cf2500dc333ec5c00b`.
- **Steady-State Thread Snapshot (`t = 20.28s` .. `52.45s`)**:
  - `FX6_WAIT_SNAPSHOT_ENUM pid=217 tids=153 overflow=0`: all 153 threads alive, zero crashes, `AppFw` (`tid=225`) waiting cleanly inside Presenter slot 0 `open` (`appFw.so +0x13abb50 -> +0x13a9b78 -> model_future::wait +0x1acd988`), while `SeqQueueCommon` (`tid=250`, `seq=95`) waited on `dest=0x909a015a` (`w0=0x2500 cmd=0x010a`, caller `appFw.so +0x20ef7a0`).

---

### 5.4 Extended Screen-Open Probe (`r3c-screen-open`): Exact Native Assertion & Call Stack

To determine what lies immediately beyond `0x909a015a` during Presenter slot 0 `open`, `r3c-screen-open` enabled `[0x2500, cmd | 0x1000, ...]` completion for `0x909a015a`.

- **Immediate Effect**: `SeqQueueCommon` (`tid=250`) surged from `seq=95` to **`seq=146`** (`FX6_QUEUE_OBS_ENTER=96`, `FX6_QUEUE_OBS_EXIT=79`, `FX6_UIPC_COMPLETION_=71`), advancing through 51 camera/codec setup RPCs into `libmpr.so` (`mpr::SetMovieRecParam` -> `libXavcMxf::SetClipName`).
- **Genuine Native Assertion Captured (`runs/r3c-screen-open/milestones.log`)**:

```text
appfw-launch: libXavcMxf.cpp:274: MEDIASLOTTYPE libXavcMxfGetSlotTypeFromMediaId(uint32_t): Assertion `0' failed.
APPFW_SEGV sig=6 code=-6 addr=0xd9 pc=0x7f9812107c lr=0x7f98121008 sp=0x7f37ff94c0
APPFW_PC_MODULE addr=0x7f9812107c module=/lib/libc.so.6+0x3107c base=0x7f980f0000 sym=gsignal
APPFW_FP_BT_0 addr=0x7f98122474 module=/lib/libc.so.6+0x32474 base=0x7f980f0000 sym=abort
APPFW_FP_BT_3 addr=0x7f989938c0 module=/usr/lib/libmpr.so+0x53c8c0 base=0x7f98457000 sym=?
APPFW_FP_BT_4 addr=0x7f989a3184 module=/usr/lib/libmpr.so+0x54c184 base=0x7f98457000 sym=_ZN10libXavcMxf11SetClipNameEjRA4_KN3mpr13ClipNameParamE
APPFW_FP_BT_5 addr=0x7f985c374c module=/usr/lib/libmpr.so+0x16c74c base=0x7f98457000 sym=_ZN3mpr16SetMovieRecParamERKNS_13movieRecParamE
APPFW_FP_BT_6 addr=0x7f8f750cf8 module=/usr/lib/appFw.so+0x213dcf8 base=0x7f8d613000 sym=?
APPFW_FP_BT_7 addr=0x7f8f6f1658 module=/usr/lib/appFw.so+0x20de658 base=0x7f8d613000 sym=?
```

- **Disassembly Root Cause (`libmpr.so +0x53c850`)**:
  `libXavcMxfGetSlotTypeFromMediaId(uint32_t mediaId)` checks `if (mediaId == 0x1000) return 0; else if (mediaId == 0x1010) return 1; else __assert_fail("0", "libXavcMxf.cpp", 274, ...)`. Immediately prior (`seq=145`), `libInfraAvbbc.so +0xdad8` queried `dest=0x807b002b` (`w0=0x0001 cmd=0x0000 len=0x0300`) while `InfraMediaConfig_Init` (`libInfraMediaConfig.so +0x6750`, called in `im.elf` `main` at `0x401d04`) had not yet populated media-slot IDs (`0x1000` CFexpress/SD Slot A, `0x1010` Slot B), leaving `mediaId == 0`.

---

## 6. `FX6_NATIVE_FAITHFUL=1` & Clean-Room Audit

| Metric / Guardrail | Required | Measured (`r3b-grm-complete`) |
| --- | --- | --- |
| `subst_color` (synthetic ARGB color injection) | `0` | **`0`** |
| `subst_image` (synthetic bitmap/glyph injection) | `0` | **`0`** |
| `forced_render` (direct presenter/widget draw calls) | `0` | **`0`** |
| `skipped_node` (scene-graph node bypass) | `0` | **`0`** |
| `lock_bypass` (`pthread_mutex_*` / `ObjShLock` low-addr ignore) | `0` | **`0`** |
| `usb_or_camera_operations` | `0` | **`0`** |
| Shared host `qemu-gpio5` preview process touched | Forbidden | **Untouched** |
| Binary `.cpio`/`.so`/`.elf`/`.bin`/`.dat` in `reports/` or `work/` | `0` | **`0`** |

---

## 7. Exact Next-Step Coordinates for Foreground Big6 Widget Population

1. **Initialize `InfraMediaConfig_Init` (`libInfraMediaConfig.so +0x6750`) & `0x807b002b` Media Slot Payload**:
   - Call `InfraMediaConfig_Init()` in `appfw-launch` (matching `im.elf` `0x401d04`, immediately after `MWF_Init`) or populate the `0x807b002b` (`libInfraAvbbc.so +0xdad8`) reply payload so active `movieRecParam` carries valid FX6 slot IDs (`0x1000` = Slot A, `0x1010` = Slot B) for `libXavcMxfGetSlotTypeFromMediaId` (`libmpr.so +0x53c850`).
2. **Complete Presenter Slot 0 `open` (`appFw.so +0x13abb50 -> +0x13a9b78`)**:
   - Once `mpr::SetMovieRecParam` returns cleanly on `SeqQueueCommon` (`tid=250`), the `model_future` awaited by `AppFw` (`tid=225` at `appFw.so +0x1acd988`) resolves, completing `Presenter::open` (`vptr_off=0x2e8d950`, `screen=0x7f68cae730`) and attaching child Big6 text/gauge widgets to `UX_ScreenArea` so subsequent 25 Hz `TriggerFrameworkCb` ticks emit `FX6_GPE_RECTBLIT` calls alongside `FX6_GPE_FILLRECT`.
