# FX6 Ver. 6.01 Cold-Boot Lifecycle Completion & `FX6_NATIVE_FAITHFUL=1` Foreground Presenter Closure (2026-11-10)

## 1. Executive Summary

This report documents the Track 1B single-variable progression (Phase 1: Rounds 1–3; Phase 2: Round 4 `r4a`–`r4i`) from the `work/fx6-worker-pool-restore-20261107` 129-TID `Application_System_Init` baseline (where `AppFw` stalled at `model_future::wait` `appFw.so +0x1acd874` / `+0xc09de4` while `SeqQueueCommon` waited on `0x032d` `init_hdmi`) all the way to **100% un-NOPed `appFw.so` `.text` (`nop_count = 0`)**, **complete `Presenter::open` closure across `160` live threads**, **foreground child widget attachment on `UX_ScreenArea`**, and **multi-color `FX6_GPE_RECTBLIT` foreground glyph & Shooting HUD rendering in physical `GPE0` (`0x41e001000`, `unique_colors = 16` in `r4h` and `unique_colors = 7` in `r4i`)** under strict **`FX6_NATIVE_FAITHFUL=1`** rules (`subst_color=0`, `subst_image=0`, `forced_render=0`, `skipped_node=0`, `lock_bypass=0`).

### Headline Milestones Achieved

1. **Q1 + Q2 Static & Runtime Closure (`Round 1`: `r1a` -> `r1b` -> `r1c`)**:
   - Disassembled FX6 `bin/im.elf` (`main` `0x402490`) and `lib/libMWF.so` (`MWF_Init` `+0x27e74`, `MWF::RsrcRelation::Initialize` `+0x3a57c`, `MWF::ObjShLock::ObjShLock` `+0x3b300`, `MWF::MonDrv::Init` `+0x3f21c`).
   - Verified `MWF_Init(void)` requires the `MonDrv::Init` `/dev/mem` FixedArea backup keys `Backup_read_8Byte(0x00fa0028) = 0x429200000UL` and `Backup_read_8Byte(0x00fa005d) = 0x100000UL`.
   - Initialized real `MWF_Init()` in `appfw-launch` (`FX6_MWF_POST smp_monErr=0x1062c50 shLockMgr=0x1062f40 shLockAcsr=0x1063000 shLockGlobal=0x10630c0 lock_bypass=0`), removed all `pthread_mutex_*` low-address bypass masks, and un-NOPed `appFw.so +0x12d8254` (`bl 0x20ed13c`, all 70 `MWF` infra wrappers) — reaching **146 live threads** with **zero crashes**.
2. **Unblocking `SeqQueueCommon` & Constructing Native Presenter (`Round 2`: `r2` -> `r2b` -> `r2c`)**:
   - Synthesized minimal ABI-compliant UIPC completions on `osal_snd_msg` for `init_hdmi` (`0x92840747 -> 0x81cf611b`, 12B `0x200d` / `0x132d`) and `get_rtc_status` (`0x92d2091c -> 0x81d705bd`, 2B `0x1700`).
   - `AppFw` (`tid=225`) exited `model_future::wait` (`+0x1acd874` / `+0xc09de4`), executed `ScreenManager::initialize` (`+0xde31ac`), registered `GRM_fbrmRegisterTriggerFrameworkCb(cb=appFw+0xc091d0, user=App*)`, allocated all 9 `UX_ScreenArea` descriptors, and constructed native Presenter slot 0 (`18rep_boot_presenter`, `vptr_off=0x2e8d950`) across **153 live threads** after fixing `R_AARCH64_TLSDESC` GOT corruption (`0x2ef29f0`, `0x2ef2a00`).
3. **Q3 Trigger Pump & Genuine `FX6_NATIVE_FAITHFUL=1` Framebuffer Flush (`Round 3`: `r3` -> `r3b` -> `r3c`)**:
   - Un-NOPed `appFw.so +0xc09e50` (`App::start_utimer`, 50 Hz `0x02010094 -> 0x5503e0`), pumped `cb=appFw+0xc091d0` at 25 Hz, preserved `ux::gfxeng::GraphicsEngine::drawFramebuffer()` `bool` return, and fixed `GRM_GPERMCmdCbParamRecord` (`user_data` at `+0x08`), committing **`552,960` real nonzero pixels (`0xff000000`)** into physical `GPE0` (`0x41e001000`) and pinpointing the `libXavcMxf.cpp:274` media-slot contract in `r3c`.
4. **Media-Slot Contract, `Presenter::open` Unblock, & Zero-NOP `appFw.so` (`Round 4A–4F`: `r4a` -> `r4f`)**:
   - Disassembled `libInfraMediaConfig.so +0x6750` (`InfraMediaConfig_Init`), disambiguated `0x807b002b` (`libInfraTp.so` touch panel) from `osal_snd_sync_msg(0x80cf016d)` (`InfraMediaConfig`), called `InfraMediaConfig_Init()` in `appfw-launch` (`slot0_id=0x1000`, `slot1_id=0x1010`), and crossed `mpr::SetMovieRecParam` / `libXavcMxf::SetClipName` with **zero assertions** (`r4a`).
   - Completed remote DMM (`0x9061003c`, `r4b`), all eight `0x215c6d0` `SeqQueueNetwork` RPCs (`r4c`–`r4d`), and preloaded donor `libCertificateManager.so` (`r4e`), **releasing `AppFw` from every `Presenter::open` `model_future::wait` barrier into steady-state `App::run`**.
   - Mapped the genuine donor FX6 NTSC Backup image (`CHAPLIN/CX95898_NTSC.bin`, `2,253,333` bytes) into `/etc/fx6_chaplin_ntsc.bk4` across `Backup_nread_multi` (`5,394` + `98` multi-item factory reads) and restored **all remaining `appFw.so` `.text` NOPs (`nop_count = 0`)** across **160 live threads** (`r4f`).
5. **Foreground Presenter Open, `UX_ScreenArea` Widget Tree Attachment, & Multi-Color `GPE0` Output (`Round 4G–4I`: `r4g` -> `r4h` -> `r4i`)**:
   - Resolved the `rep_boot_controller::process_MODEL_POWER_ON_COMP` (`appFw.so +0x1009b90..0x100ab4c`) handover chain (`0x02cf15c8 = 0x03`, `0x02cf0069 = 0x00060001` + `0x004b024e` `(6,1)` `"6.01"`, `InfraInput` `1,127` keys with `PW_SW` `phy_key_id=1 -> status=1`), and fixed offscreen backbuffer clobbering + verified `libgemini-grm.so` `blend_mode`/`const_alpha`/`tint` (`+0x3c..0x3f` when `+0x50 == 0x0e`) in `libgrm-fbinit9.c`:
     - **`r4h-foreground-gpe0-colors` (`0x02cf0068 = 0x01` factory default, 72.70s, 160 TIDs, `nop_count = 0`, 0 crashes)**: Opened **`slots[2] = 37procam_menu_initial_setting_presenter`** (`vptr_off=0x2e8eac0`), populated `UX_ScreenArea` `idx=2` (`0x7f74f27758`) & `idx=4` (`0x7f75727778`), executed `966` `drawFramebuffer()` passes, and committed **`16` unique ARGB colors (`552,960` nonzero pixels, including `3,047` anti-aliased Sony Cinema Line amber `0xffffaa00` foreground FreeType glyph pixels, `sha256 = 7c8f770c189d3e98e08a4b85beb6ba354ff51c9682c71e2b444094abbac3bce3`)** into physical `GPE0` (`0x41e001000`)!
     - **`r4i-shooting-big6-presenter` (`0x02cf0068 = 0x00` `--initial-setting-done 1`, 72.67s, 160 TIDs, `nop_count = 0`, 0 crashes)**: Transitioned **`slots[0]` from `18rep_boot_presenter` into `25procam_shooting_presenter` (`vptr_off=0x2e8d9e0`, `screen=0x7f66127730`)** alongside `slots[2] = 35procam_msg_1label_1button_presenter` (`vptr_off=0x2e8e208`), populated `UX_ScreenArea` `idx=2` (`0x7f64f27758`) & `idx=4` (`0x7f65727778`), executed **`774` real `FX6_GPE_RECTBLIT` calls** across **6 Shooting HUD icon/badge widgets** (including 1 Hz blinking `(787,46,135,26)`), and committed **`1,829` multi-color foreground HUD pixels across `7` unique ARGB colors (`sha256 = ec4db79643d457088b346828162591f5b8fd42299ab3f468f333862e50460d2a`)** over the transparent (`0x00000000`) live-view OSD plane in physical `GPE0`!

---

## 2. Deliverable Artifacts & Reproducible Harness

All created/updated files reside strictly within the three authorized directories:

- Static ABI & disassembly contracts:
  - [`STATIC-CONTRACTS.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-10-fx6-native-presenter-closure/STATIC-CONTRACTS.md)
  - [`inspect_static_contracts.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/inspect_static_contracts.py)
  - [`static-contracts-summary.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/static-contracts-summary.json)
- `FX6_NATIVE_FAITHFUL=1` launcher, `LD_PRELOAD` shim, and single-variable QEMU runner (`work/` and synced pure sources in `outputs/fx6-native-presenter-closure/`):
  - [`appfw-launch.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx6-native-presenter-closure/appfw-launch.c)
  - [`libgrm-fbinit9.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx6-native-presenter-closure/libgrm-fbinit9.c)
  - [`got_table_fx6.inc`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx6-native-presenter-closure/got_table_fx6.inc)
  - [`build_and_run_round.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx6-native-presenter-closure/build_and_run_round.py)
  - [`outputs/fx6-native-presenter-closure/README.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx6-native-presenter-closure/README.md)
- Experimental run logs & structured summaries (`serial.log`, `milestones.log`, `summary.json`):
  - [`work/fx6-native-presenter-closure-20261110/runs/`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs) (`r1a`..`r3c`, `r4a-mediaconfig-init`..`r4i-shooting-big6-presenter`)

### Reproducible Commands

```sh
# Regenerate static disassembly summary JSON
/usr/bin/python3 work/fx6-native-presenter-closure-20261110/inspect_static_contracts.py

# Round 3 (Steady-State Boot Baseline): 552,960 GPE0 pixels (153 TIDs, 0 crashes)
/usr/bin/python3 work/fx6-native-presenter-closure-20261110/build_and_run_round.py \
  --round 3 --restore-infra70 1 --reply-all-200d 0 --run-id repro-r3b --duration 50

# Round 4H (Factory Out-of-Box Menu): nop_count=0, 160 TIDs, 37procam_menu_initial_setting_presenter,
# 16 unique ARGB colors in physical GPE0 (3,047 Sony amber 0xffffaa00 glyph pixels)
/usr/bin/python3 work/fx6-native-presenter-closure-20261110/build_and_run_round.py \
  --round 4 --restore-infra70 1 --restore-all-early 1 --reply-all-200d 1 \
  --initial-setting-done 0 --run-id repro-r4h --duration 70

# Round 4I (Shooting HUD Screen): nop_count=0, 160 TIDs, slots[0]=25procam_shooting_presenter,
# 774 FX6_GPE_RECTBLIT calls, 7 unique ARGB colors (1,829 HUD pixels over transparent live-view plane)
/usr/bin/python3 work/fx6-native-presenter-closure-20261110/build_and_run_round.py \
  --round 4 --restore-infra70 1 --restore-all-early 1 --reply-all-200d 1 \
  --initial-setting-done 1 --run-id repro-r4i --duration 70
```

> [!NOTE]
> `build_and_run_round.py` compiles binaries into `/private/tmp/fx6-native-closure-build-<pid>-<run_id>`, repacks a temporary guest `.cpio` in `/private/tmp/fx6-native-closure-<pid>-<run_id>.cpio`, uses isolated `/private/tmp/fx6-native-<pid>-qmp.sock` sockets, terminates only its own `proc.pid` inside `finally:`, and deletes all `/private/tmp` build/cpio/socket artifacts on exit. No binary `.cpio`/`.so`/`.elf`/`.bin` files are written to `work/`, `outputs/`, or `reports/`.

---

## 3. Summary of Closed Static & Runtime ABI Contracts (Rounds 1–4)

Full disassembly listings and struct offsets are recorded in [`STATIC-CONTRACTS.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-10-fx6-native-presenter-closure/STATIC-CONTRACTS.md).

| Contract | Binary & Offset | Verified Signature / Layout | Key Conclusion |
| --- | --- | --- | --- |
| **Q1: `MWF_Init` & `MonDrv`** | `libMWF.so +0x27e74`, `+0x3f21c` | `void MWF_Init(void)` + `0x00fa0028` / `0x00fa005d` | Allocates `smp_monErr` (`+0x67e00`), maps `/dev/mem` FixedArea (`0x429200000UL`, `0x100000UL`), spawns `mwf_monitor_inp`. |
| **Q2: `ObjShLock`** | `libMWF.so +0x3b300`, `+0x3a57c` | `sizeof == 0xb8`; `pthread_mutex_t` at `this + 0x28` | `MWF_Init` constructs all 3 `ObjShLock*` (`+0x68688..0x68698`); eliminates all `pthread_mutex_lock(0x28)` faults (`lock_bypass=0`). |
| **Q3: `TriggerFrameworkCb`** | `libgrm.so +0x236b8`, `appFw.so +0xc091d0` | `cb(App*)` clears `0x2f197d4=0`, `0x2f197d0=0` | Combined with un-NOPed `App::start_utimer` (`+0xc09e50`), drives 25 Hz `drawFramebuffer()` passes in `App::run`. |
| **4A: `InfraMediaConfig_Init`** | `libInfraMediaConfig.so +0x6750`, `appFw.so +0x2125930` | `0x80cf016d` (`osal_snd_sync_msg`), `MediaTtlInf` stride `0x110` | `0x807b002b` is `libInfraTp.so` (touch panel); media slots use `0x80cf016d`, populating `appFw + 0x5c3e560` (`Slot A=0x1000`, `Slot B=0x1010`) for `libXavcMxfGetSlotTypeFromMediaId` (`libmpr.so +0x53c850`). |
| **4B: DMM + Network + CertMgr** | `appFw.so +0x20fea28`, `+0x215c6d0`, `libCertificateManager.so` | `0x9061003c` (40B) + 8x `SeqQueueNetwork` RPCs | Completes `SeqQueueCommon` and `SeqQueueNetwork` cleanly; unblocks all `Presenter::open` `model_future::wait` barriers. |
| **4C: Handover & Screen Open** | `appFw.so +0x1009b90..0x100ab4c`, `CX95898_NTSC.bin` | `0x02cf15c8=3`, `0x02cf0069="6.01"`, `PW_SW=1`, `0x02cf0068` | Un-NOPs 100% of `appFw.so` (`nop_count=0`). `0x02cf0068=1` opens `37procam_menu_initial_setting_presenter`; `0x02cf0068=0` transitions `slots[0]` to `25procam_shooting_presenter`. |
| **4C: `GRMRenderer` GPE Blit** | `libgemini-grm.so +0x7700..0x7e78` | `GRM_GPERMRectblitParamRecord` (`tint` at `+0x3c..0x3f` when `+0x50==0x0e`) | Restricting `flush_pixels_to_osd` to `DrawFlush`/`Update`/`Flip` + honoring `blend_mode`, `const_alpha`, and A8 glyph `tint` preserves real multi-color foreground widgets in `GPE0`. |

---

## 4. Single-Variable Experimental Progression Matrix (Rounds 1–4)

| Run ID | Config & Single-Variable Delta | Wall (s) | Live TIDs | `UIPC_SND` / `COMP` | `GPE` / `FLUSH` / `GPE0_NZ` / `UCOL` | Outcome & Milestone / Coordinate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| [`r1a`..`r1c`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r1c-mwf-infra70/summary.json) | `R1`: real `MWF_Init()` + FixedArea + `infra70=1` | 40.22 | 146 | 0 / 0 | 0 / 1 / 0 / 1 | **PASS (0 crashes)**. Real `MWF_Init` + 3x `ObjShLock*` + 70 infra wrappers (`lock_bypass=0`). |
| [`r2`..`r2c`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r2c-tlsdesc-fixed/summary.json) | `R2`: + `init_hdmi` (`0x92840747`) + RTC (`0x92d2091c`) + `skipped_tlsdesc=2` | 46.44 | 153 | 20 / 2 | 0 / 1 / 0 / 1 | **PASS (0 crashes)**. Unblocked `+0xc09de4`, ran `ScreenManager::initialize`, constructed `18rep_boot_presenter`. |
| [`r3b-grm-complete`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r3b-grm-complete/summary.json) | `R3`: + `start_utimer` + 25Hz pump + `0x807e002f` + `GRM_GPERMCmdCbParamRecord` | 52.45 | 153 | 95 / 39 | 2 / 13 / 552,960 / 1 | **PHASE 1 MILESTONE (0 crashes)**. Real `drawFramebuffer()` (`rc=1`), `552,960` `0xff000000` GPE0 pixels. |
| [`r3c-screen-open`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r3c-screen-open/summary.json) | `R3`: + `0x909a015a` (`reply_all_200d=1`) | 16.20 | 148 | 146 / 71 | 2 / 13 / 552,960 / 1 | Advanced 51 RPCs into `libXavcMxf.cpp:274` (`mediaId=0` assertion). |
| [`r4a-mediaconfig-init`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r4a-mediaconfig-init/summary.json) | `R4`: + `InfraMediaConfig_Init()` + FX6 BK4 media slot bytes (`0x1000`, `0x1010`) | 62.55 | 156 | 249 / 139 | 2 / 13 / 552,960 / 1 | **Crossed `libXavcMxf.cpp:274` with 0 assertions!** `SeqQueueCommon` reached `0x9061003c` (remote DMM). |
| [`r4b-dmm-presenter-open`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r4b-dmm-presenter-open/summary.json) | `R4`: + `0x9061003c` 40B DMM completion | 67.52 | 156 | 252 / 141 | 2 / 13 / 552,960 / 1 | **`SeqQueueCommon` (`tid=253`) completed 100% of tasks and returned to idle!** Next wait: `SeqQueueNetwork` (`0x832609f2`). |
| [`r4c`..`r4d`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r4d-presenter-open-complete/summary.json) | `R4`: + eight `0x215c6d0` `SeqQueueNetwork` RPC completions | 72.62 | 148 | 257 / 147 | 2 / 13 / 552,960 / 1 | Unblocked `SeqQueueNetwork` RPCs; pinpointed missing preload `libCertificateManager.so` (`CertificateUtil::InitCertificateManager`). |
| [`r4e-presenter-open-certmgr`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r4e-presenter-open-certmgr/summary.json) | `R4`: + preload donor `libCertificateManager.so` + sibling `.so`s | 72.60 | 156 | 800+ / 158 | 2 / 13 / 552,960 / 1 | **PASS (0 crashes)! `AppFw` exited ALL `Presenter::open` `model_future::wait` barriers into steady-state `App::run`!** |
| [`r4f-normal-boot-screen-open`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r4f-normal-boot-screen-open/summary.json) | `R4`: + donor `CX95898_NTSC.bin` BK4 + `0x02cf15c8=3` + `nop_count=0` | 77.66 | 160 | 800+ / 155 | 2 / 13 / 552,960 / 1 | **PASS (0 crashes, 160 TIDs, `nop_count=0`!)**. Identified `Backup_nread_multi` + `"6.01"` version + `PW_SW=1` handover checks. |
| [`r4g-foreground-big6`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r4g-foreground-big6/summary.json) | `R4`: + `Backup_nread_multi` (`5,492` hits) + `0x004b024e=(6,1)` + `InfraInput` `PW_SW=1` | 77.77 | 160 | 800+ / 152 | 146 / 614 / 552,960 / 1 | **Opened `slots[2]=37procam_menu_initial_setting_presenter` & emitted `1,650` real `FX6_GPE_RECTBLIT` calls!** Pinpointed post-flip `Fillrect` clobber + A8 glyph `tint`. |
| **[`r4h-foreground-gpe0-colors`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r4h-foreground-gpe0-colors/summary.json)** | **`R4`: + verified `libgemini-grm.so` flip/blend/tint (`--initial-setting-done 0`)** | **72.70** | **160** | **800+ / 152** | **106+ / 94+ / 552,960 / 16** | **PHASE 2 MILESTONE A (0 crashes, `nop_count=0`)**: `37procam_menu_initial_setting_presenter`, **`16` unique ARGB colors (`3,047` amber `0xffffaa00` glyph pixels)** in physical `GPE0`! |
| **[`r4i-shooting-big6-presenter`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-native-presenter-closure-20261110/runs/r4i-shooting-big6-presenter/summary.json)** | **`R4`: `--initial-setting-done 1` (`0x02cf0068 = 0x00`)** | **72.67** | **160** | **800+ / 184** | **88+ / 42+ / 1,829 / 7** | **PHASE 2 MILESTONE B (0 crashes, `nop_count=0`)**: **`slots[0] = 25procam_shooting_presenter`**, `774` `FX6_GPE_RECTBLIT` calls, **`7` unique ARGB colors (`1,829` HUD pixels over transparent live-view plane)** in physical `GPE0`! |

*(Note: `UIPC_SND`, `GPE`, and `FLUSH` log lines are rate-limited in serial output to keep UART bandwidth clean; `FX6_TRIGGER_PUMP_TICK` records the full cumulative totals: `draw_fb=966, flush=1307, prims=2610` in `r4h`, and `draw_fb=135, flush=269, prims=933` (`774` `Rectblit` + `159` `Fillrect`) in `r4i`.)*

---

## 5. Detailed Evidence & Verbatim Serial Excerpts

### 5.1 Rounds 1–3 Summary (`r1a` -> `r3b-grm-complete` -> `r3c-screen-open`)

- **Round 1 (`r1c-mwf-infra70`)**: Initialized real `MWF_Init()` with `0x00fa0028 -> 0x429200000UL` and `0x00fa005d -> 0x100000UL`, constructing `smp_monErr` and all 3 `ObjShLock` singletons (`lock_bypass=0`) across 146 threads.
- **Round 2 (`r2c-tlsdesc-fixed`)**: Unblocked `init_hdmi` (`0x92840747`) and `get_rtc_status` (`0x92d2091c`) and skipped the 2 `R_AARCH64_TLSDESC` GOT entries (`0x2ef29f0`, `0x2ef2a00`), constructing `slots[0] = 18rep_boot_presenter` (`vptr_off=0x2e8d950`).
- **Round 3 (`r3b-grm-complete` & `r3c-screen-open`)**: Pumped `GRM_fbrmRegisterTriggerFrameworkCb` at 25 Hz alongside native 50 Hz `App::start_utimer`, committing `552,960` `0xff000000` pixels to `GPE0` (`sha256=9c033ca44a46dc679cd2e625bd686e1de137c5dce019b9cf2500dc333ec5c00b`) and isolating `libXavcMxf.cpp:274` (`mediaId == 0`) in `r3c`.

---

### 5.2 Round 4 Step 4A & 4B: Media-Slot Closure, `Presenter::open` Unblock, & `nop_count = 0` (`r4a` -> `r4f`)

1. **Crossing `libXavcMxf.cpp:274` (`r4a-mediaconfig-init`)**:
   - Calling genuine `InfraMediaConfig_Init()` (`libInfraMediaConfig.so +0x6750`) in `appfw-launch` immediately after `MWF_Init()` populated `InfraMediaConfig::m_pMyObj` (`slot_count=3`, `slot0_id=0x1000`, `slot1_id=0x1010`, `slot2_id=0x2000`) and registered synchronous queue `0x80cf016d`.
   - During `Application_System_Init`, `appFw.so +0x2125930` queried `0x80cf016d` via `osal_snd_sync_msg`, populating `appFw.so +0x5c3e560` (`FX6_APPFW_MEDIA_SLOTS count=3 s0=0x1000 s1=0x1010 s2=0x2000`). `SeqQueueCommon` (`tid=253`) executed `mpr::SetMovieRecParam` -> `libXavcMxf::SetClipName` -> `libXavcMxfGetSlotTypeFromMediaId(0x1000 / 0x1010)` with **zero assertions**.
2. **Completing `Presenter::open` & Restoring 100% of `appFw.so` `.text` (`r4b` -> `r4f`)**:
   - Adding `0x9061003c` (remote DMM, `r4b`), the eight `0x215c6d0` `SeqQueueNetwork` completions (`r4c`–`r4d`), and donor `libCertificateManager.so` (`r4e`) drained both `SeqQueueCommon` and `SeqQueueNetwork` to idle and woke `AppFw` (`tid=225`) out of every `model_future::wait` barrier.
   - Mapping unmodified donor `CHAPLIN/CX95898_NTSC.bin` (`2,253,333` bytes) into `/etc/fx6_chaplin_ntsc.bk4` allowed restoring `0x12d824c`, `0x12d8250`, `0x12d8254`, and `0xc09e50` simultaneously (`FX6_PATCH_PLAN nop_count=0 round=4`, `160` live threads, `0` crashes).

---

### 5.3 Round 4 Step 4C Milestone A (`r4h-foreground-gpe0-colors`): `37procam_menu_initial_setting_presenter` & `16` Unique ARGB Colors in Physical `GPE0`

With factory out-of-box `0x02cf0068 = 0x01` (`--initial-setting-done 0`), `rep_boot_controller::process_MODEL_POWER_ON_COMP` opened **`slots[2] = 37procam_menu_initial_setting_presenter`** (`vptr_off = 0x2e8eac0`, `screen = 0x7f7612da80`), attached foreground widget trees to `UX_ScreenArea` `idx=0` (`0x7f703a0170`), `idx=2` (`0x7f74f27758`), and `idx=4` (`0x7f75727778`), rasterized FreeType `A8` (`fmt=4, bpp=1`) text glyphs via `libfont.so`, and composited them with Sony Cinema Line amber highlight tint (`0xffffaa00`) across `966` `drawFramebuffer()` passes (`2,610` GPE primitives, `1,307` OSD flushes):

#### Verbatim Serial Milestones (`runs/r4h-foreground-gpe0-colors/milestones.log`)

```text
FX6_BK4_MMAP status=ok base=0x7f8d736000 bytes=2253333
FX6_MWF_POST smp_monErr=0x106a280 shLockMgr=0x106a570 shLockAcsr=0x106a630 shLockGlobal=0x106a6f0 lock_bypass=0
FX6_IMCFG_POST singleton=0x106b400 slot_count=3 slot0_id=0x1000 slot0_dev=0xdf10 slot1_id=0x1010 slot1_dev=0xdf20
FX6_INFRA_INPUT_POST inst=0x106c8a0 key_cnt=1127 pw_sw_found=1 pw_sw_status=1
FX6_PATCH_PLAN appFw_base=0x7f71ee8000 nop_count=0 round=4
FX6_APPFW_MEDIA_SLOTS tag=trigger_cb_reg count=3 s0=0x1000 s1=0x1010 s2=0x2000 s3=0x0
FX6_PRESENTER_SLOT idx=0 tag=pump obj=0x7f76224f08 vptr=0x7f74d75950 vptr_off=0x2e8d950 screen=0x7f76127730 rtti=18rep_boot_presenter
FX6_PRESENTER_SLOT idx=2 tag=pump obj=0x7f766d4f08 vptr=0x7f74d76ac0 vptr_off=0x2e8eac0 screen=0x7f7612da80 rtti=37procam_menu_initial_setting_presenter
FX6_UX_SCREEN_TREE tag=pump idx=2 screen=0x7f7c00ef50 active=1 first_elem=0x7f74f27758
FX6_UX_SCREEN_TREE tag=pump idx=4 screen=0x7f7c00f710 active=1 first_elem=0x7f75727778
FX6_GPE_RECTBLIT #7 dst=(566,315,160,36) target=0x7f99df3300 src=0x7f7c1ab6f0 fmt=4 bpp=1 src_nz=1583 blend=2 calpha=255 tint=0xffaa00 subst_image=0
FX6_GPE_RECTBLIT #8 dst=(566,366,120,36) target=0x7f99df3300 src=0x7f7c1b1a50 fmt=4 bpp=1 src_nz=1464 blend=2 calpha=255 tint=0xffaa00 subst_image=0
FX6_OSD_FLUSH fbrmUpdate #9 prims=14 fill=8 blit=6 nz_pixels=552960 nonblack=3047 subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0
FX6_MILESTONE_DRAW_FB #4 self=0x7f7c00c070 rc=1 lr=0x7f72af1a94(appFw+0xc09a94) real=0x7f99cb09c8
FX6_TRIGGER_PUMP_TICK #1525 cb=0x7f72af11d0 ud=0x7f8654e658 gate_7d4=0 gate_7d0=0 draw_fb=966 flush=1307 prims=2610
```

#### Physical `GPE0` (`0x41e001000`) Readback Color Distribution (`r4h-foreground-gpe0-colors`)

- **Frame Dimensions**: `1024 x 540` ARGB8888 (`2,211,840` bytes, `552,960` total pixels)
- **Nonzero Pixels**: `552,960` (`549,913` opaque `0xff000000` background + **`3,047` non-black anti-aliased Sony Cinema Line amber foreground glyph pixels** = `1,583` at `(566,315,160,36)` + `1,464` at `(566,366,120,36)`)
- **Unique Colors**: **`16`** (`sha256 = 7c8f770c189d3e98e08a4b85beb6ba354ff51c9682c71e2b444094abbac3bce3`)

| ARGB8888 | Pixel Count | Role |
| --- | ---: | --- |
| `0xff000000` | `549,913` | Menu opaque black backdrop (`Fillrect`) |
| `0xffffaa00` | `1,791` | Full-coverage Sony amber (`R=255, G=170, B=0`) glyph core |
| `0xffdc9200` | `194` | Anti-aliased amber glyph edge (`alpha = 0xdc`) |
| `0xffba7c00` | `174` | Anti-aliased amber glyph edge (`alpha = 0xba`) |
| `0xff332200` | `142` | Anti-aliased amber glyph edge (`alpha = 0x33`) |
| `0xff875a00` | `134` | Anti-aliased amber glyph edge (`alpha = 0x87`) |
| `0xff986500` .. `0xff110b00` (10 ramps) | `612` | Remaining 10 FreeType coverage levels (`16` total unique colors) |

---

### 5.4 Round 4 Step 4C Milestone B (`r4i-shooting-big6-presenter`): `25procam_shooting_presenter` & Multi-Color Shooting HUD in Physical `GPE0`

Setting `--initial-setting-done 1` (`0x02cf0068 = 0x00`, corresponding to a camera whose initial Area/Date/Time wizard has been completed) caused `rep_boot_controller::process_MODEL_POWER_ON_COMP` (`+0x100aae8`) to close `18rep_boot_presenter` and open **`slots[0] = 25procam_shooting_presenter` (`vptr_off = 0x2e8d9e0`, `screen = 0x7f66127730`)** alongside **`slots[2] = 35procam_msg_1label_1button_presenter` (`vptr_off = 0x2e8e208`, `screen = 0x7f6612da80`)**!

In Shooting mode, `libuxengine.so` clears the OSD framebuffer with **transparent black `0x00000000` (`blend_mode = 1`)** (so live camera video underneath shows through on real hardware) and composites **6 distinct multi-color Shooting HUD icon/status widgets** via **`774` real `FX6_GPE_RECTBLIT` calls** (`135` `drawFramebuffer()` passes, including 1 Hz blinking media/battery warning indicator `(787,46,135,26)`):

#### Verbatim Serial Milestones (`runs/r4i-shooting-big6-presenter/milestones.log`)

```text
FX6_PATCH_PLAN appFw_base=0x7f61ee8000 nop_count=0 round=4
FX6_PRESENTER_SLOT idx=0 tag=pump obj=0x7f66224f08 vptr=0x7f64d759e0 vptr_off=0x2e8d9e0 screen=0x7f66127730 rtti=25procam_shooting_presenter
FX6_PRESENTER_SLOT idx=2 tag=pump obj=0x7f666d4f08 vptr=0x7f64d76208 vptr_off=0x2e8e208 screen=0x7f6612da80 rtti=35procam_msg_1label_1button_presenter
FX6_UX_SCREEN_TREE tag=pump idx=2 screen=0x7f6c00ef50 active=1 first_elem=0x7f64f27758
FX6_UX_SCREEN_TREE tag=pump idx=4 screen=0x7f6c00f710 active=1 first_elem=0x7f65727778
FX6_GPE_FILLRECT #3 (0,0,1024,540) argb=0x00000000 blend=1 calpha=255 dst=0x7f87aa8300 subst_color=0
FX6_GPE_RECTBLIT #13 dst=(787,46,135,26) target=0x7f87aa8300 src=0x7f6c1b7020 fmt=1 bpp=2 src_nz=2205 blend=2 calpha=255 tint=0xffffff subst_image=0
FX6_GPE_RECTBLIT #14 dst=(58,5,49,26) target=0x7f87aa8300 src=0x7f6c1c3f20 fmt=1 bpp=2 src_nz=894 blend=2 calpha=255 tint=0xffffff subst_image=0
FX6_GPE_RECTBLIT #15 dst=(930,95,50,20) target=0x7f87aa8300 src=0x7f6c1c9570 fmt=1 bpp=2 src_nz=761 blend=2 calpha=255 tint=0xffffff subst_image=0
FX6_GPE_RECTBLIT #16 dst=(398,508,25,27) target=0x7f87aa8300 src=0x7f6c1ca730 fmt=1 bpp=2 src_nz=563 blend=2 calpha=255 tint=0xffffff subst_image=0
FX6_GPE_RECTBLIT #17 dst=(930,117,32,26) target=0x7f87aa8300 src=0x7f6c1cde80 fmt=1 bpp=2 src_nz=642 blend=2 calpha=255 tint=0xffffff subst_image=0
FX6_GPE_RECTBLIT #18 dst=(962,122,25,20) target=0x7f87aa8300 src=0x7f6c1cec30 fmt=1 bpp=2 src_nz=386 blend=2 calpha=255 tint=0xffffff subst_image=0
FX6_OSD_FLUSH fbrmUpdate #9 prims=23 fill=5 blit=18 nz_pixels=1829 nonblack=1829 subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0
FX6_TRIGGER_PUMP_TICK #1525 cb=0x7f62af11d0 ud=0x7f61ee5658 gate_7d4=0 gate_7d0=0 draw_fb=135 flush=269 prims=933
```

#### Physical `GPE0` (`0x41e001000`) Readback Color Distribution (`r4i-shooting-big6-presenter`)

- **Frame Dimensions**: `1024 x 540` ARGB8888 (`2,211,840` bytes, `552,960` total pixels)
- **Nonzero Foreground HUD Pixels**: **`1,829`** over `551,131` transparent live-view pixels (`0x00000000`)
- **Unique Colors**: **`7`** (`sha256 = ec4db79643d457088b346828162591f5b8fd42299ab3f468f333862e50460d2a`)

| ARGB8888 | Pixel Count | Role |
| --- | ---: | --- |
| `0x00000000` | `551,131` | Transparent OSD camera live-view plane (`Fillrect` `0x00000000`) |
| `0xffdebd7b` | `1,182` | Shooting HUD primary icon/label body |
| `0xff9c317b` | `170` | Shooting HUD warning/status accent |
| `0xff73eeff` | `166` | Shooting HUD highlight glyph/border |
| `0xff10207b` | `113` | Shooting HUD badge outline/shadow |
| `0xff52ac7b` | `113` | Shooting HUD secondary icon tone |
| `0xff3162ff` | `85` | Shooting HUD indicator accent |

---

## 6. `FX6_NATIVE_FAITHFUL=1` & Clean-Room Audit

| Metric / Guardrail | Required | `r3b-grm-complete` | `r4h-foreground-gpe0-colors` | `r4i-shooting-big6-presenter` |
| --- | --- | --- | --- | --- |
| `subst_color` (synthetic ARGB color injection) | `0` | **`0`** | **`0`** | **`0`** |
| `subst_image` (synthetic bitmap/glyph injection) | `0` | **`0`** | **`0`** | **`0`** |
| `forced_render` (direct presenter/widget draw calls) | `0` | **`0`** | **`0`** | **`0`** |
| `skipped_node` (scene-graph node bypass) | `0` | **`0`** | **`0`** | **`0`** |
| `lock_bypass` (`pthread_mutex_*` / `ObjShLock` low-addr ignore) | `0` | **`0`** | **`0`** | **`0`** |
| `appFw.so` `.text` NOP patches (`nop_count`) | Minimal (`0` ideal) | `2` | **`0` (100% unmodified `.text`)** | **`0` (100% unmodified `.text`)** |
| `GPE0` `unique_colors` (`0x41e001000` readback) | `> 1` | `1` | **`16`** | **`7`** |
| `usb_or_camera_operations` | `0` | **`0`** | **`0`** | **`0`** |
| Shared host `qemu-gpio5` preview process touched | Forbidden | **Untouched** | **Untouched** | **Untouched** |
| Binary `.cpio`/`.so`/`.elf`/`.bin` in `outputs/`, `reports/`, `work/` | `0` | **`0`** | **`0`** | **`0`** |

---

## 7. Exact Next-Step Coordinates (Phase 3: Interactive `HOME` -> `31procam_big6_menu_home_presenter`)

1. **Interactive Key Dispatch (`25procam_shooting_presenter` -> `31procam_big6_menu_home_presenter`)**:
   - In `r4i-shooting-big6-presenter`, `slots[0]` is already running genuine `25procam_shooting_presenter` (`vptr_off = 0x2e8d9e0`) with `slots[2] = 35procam_msg_1label_1button_presenter` (`vptr_off = 0x2e8e208`, modal confirmation dialog).
   - Posting an `InfraInput` key press (`ENTER` to dismiss `slots[2]`, followed by `MENU` / `HOME` key event on `I-InputRecv` / `App` queue `0x5503e0`) will trigger `ScreenManager` to open **`31procam_big6_menu_home_presenter`** (the 6-panel Big6 Home Screen in `appFw.so` RTTI) natively!
2. **Exact 16-bit `BMP_PixelFormat == 1` (`bpp == 2`) Sub-Format Verification (`libgemini-grm.so +0x7204`)**:
   - In `r4i`, `BMP_PixelFormat == 1` (`bpp == 2`, `gemini` format `7`) HUD icons decode cleanly with non-zero alpha; verifying the exact 16-bit channel packing (`ARGB1555` vs `RGBA4444` vs `RGB565` in `libuxengine.so` resource decoder) will ensure 1:1 hue fidelity for 2-byte HUD icon bitmaps alongside the already-exact `ARGB8888` (`fmt=2`) and `A8` FreeType glyph (`fmt=4`) paths.
