# FX6 66ed0f78 — evidence layer matrix

Run: `donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/runs/cp-bind-66ed0f78`
Exact candidate: `vm-candidate-upmcallsite180.json` (`d3181026…`)
Target serial: `377142e9dcee7f4f7728db6e9fcb822a9f3e501e61da7f719761d4d506f5050e`
Target CPIO: `3a08f89d…`; kernel `da4a66…`; DTB `b6f9f4…`.

## A. Layer / provenance

| ID | Object | Provenance / hashes | Evidence in this run | Classification | Status |
|---|---|---|---|---|---|
| L1 | FX6 donor `appFw.so` | donor `a1c58b69…`; target member `b1fe2274…` | target member is the modified version, not donor | FX6 original reference; target modified | original not run in target |
| L2 | FX6 donor `upm.ko` | donor `34d5bca7…`; CPIO baseline `ba0cca76…`; target `5be2aa0b…` | target hash matches `grm-fbinit/upm-callsite-skip.ko`; baseline not donor | modified (pre-existing baseline not donor) | not original |
| L3 | FX6 donor `backup.ko` | donor `0fe57e43…`; alternate `56193f9a…`; CPIO baseline `8a8d8c94…`; target `6ae178d5…` | target hash matches `backup-bug-skip.ko`; baseline not donor | modified (pre-existing baseline not donor) | not original |
| L4 | CP helper | `fx6-cp-backup-sync100-agnostic-g0.ko` `7e8d859e…` = target member | `FX6_SYNC100_AGNOSTIC_BIND`, INSmod rc, `synthetic_cp_backup_sync=1 original_CP=0` | FX3/FX6-agnostic simulation helper | emulation aid, not original FX6 CP |
| L5 | FX6 libs / peers | target CPIO `libgrm 0f9f…`, `libma 21de…`, `libgrm_bmp 4c83…`, `liblibra 3dff…`, `libstella d8d1…`, `libInfraAppRemoteBoard c7d6…`, `grm_ma 81e0…`, `libgrm-fbinit9 ca4d…` | appFw profile frames reference `/usr/lib/appFw.so`; libs mapped but not individually initialized/proven | FX6 original members present | loaded/mapped, function init unproven |
| L6 | FX3 kernel / DTB | kernel `da4a66fa…` (official FX3), DTB `b6f9f4…`, QEMU `bf4d4648…` | kernel boot lines; QEMU pre-cont PC/x0 and 4 CPUs; no FX6 kernel | fixed FX3 compatibility/platform | run constraint satisfied as input, not FX6 boot proof |
| L7 | FX3 rootfs / init / simulation modules | CPIO `/init`, FX3 userland, `simulation/fx3-*` | init/module markers; many simulation observers; `FX3_DATE99 … synthetic_cp_clock=1 original_CP=0` | FX3 compatibility + emulation | loaded/used; not original FX6 |
| L8 | appFw future::get change | target `0x2159c50` bytes `00008052c0035fd6` (`mov w0,#0; ret`) vs donor `fd7bbaa9…` | byte-level change verified; no direct future-return marker | diagnostic modification | return forced 0; no functional proof |
| L9 | upm callsite change | target member `5be2aa0b…` = `upm-callsite-skip.ko`; claim `upm_senser_dfs_measurement+0x4a0 blr x2 -> mov w0,#0` | hash/provenance matches; offset-level disassembly not performed | diagnostic modification | return forced 0; no sensor/DFS init proof |
| L10 | backup BUG skip | target `6ae178d5…`; source `8a8d8c94…`; claim `0x75c brk #0x3e8 -> b 0x700` | at claimed `0x75c` bytes are identical; actual first diff is `0x7c4`: target `e9ffff17` vs source `007d20d4` (`brk`) | diagnostic modification | **claim offset unsupported**; branch exists but no original path proof |
| L11 | target appFw identity | target member `b1fe2274…`, donor `a1c58b69…` | target is modified appFw; `FX3_PROFILE_FRAME` 294, `FX3_PROVIDER_CALLER` 7 | modified FX6 appFw | actual code execution markers, no menu |

## B. Stage / behavior

| Stage | Observed | Evidence class | Status |
|---|---|---|---|
| CPIO/kernel/DTB loading | boot, FX3_DEVTMPFS_RC=0, module insmod lines, CP helper begin | load/mapping | observed |
| CP helper binding | `FX6_SYNC100_AGNOSTIC_BIND`, `FX3_SYNC100_BACKEND_BOUND`, `FX3_BACKUP_CP_PUBLIC_OWNER result=0`, `software_CP_executed=0` | actual helper execution / synthetic | observed, but emulation |
| FX6 appFw loading/execution | `FX3_PROFILE_FRAME` 294, `FX3_PROVIDER_CALLER` 7, appFw stacks | actual execution markers | observed |
| AP bootin | `FX3_AP_NATURAL_BOOTIN_BEGIN`, launch PID, IM/RM markers, `FX3_MEDIA_START_BRANCH` 2 | actual AP/media markers | observed |
| appFw future::get behavior | byte patch returns 0; no actual future result observed | patched return | no functional initialization proof |
| upm sensor/DFS behavior | `IWrapperUPM` threads present; callsite patched to return 0; no measurement/init result | thread/load marker, patched return | init unproven |
| Backup behavior | no BUG; branch at `0x7c4`; no original backup path/result proof | no-fault / patched branch | original function unproven |
| boot-screen model | `assert at model_api.cpp:3147` (line 11688), `:3176` (line 11738) | actual appFw thread assertion | failed |
| CAPID/media assert | `assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075` lines 14502 and 14734; `send_and_wait_cmp_i` stack | actual appFw/media thread assertion | known failure still present |
| screen creation | `FX3_AP89_SCREEN_CREATE` count 0 | missing | not achieved |
| UUD decision | `FX3_AP89_UUD_DECISION` 0 | missing | not achieved |
| menu | `FX3_MENU` 0 | missing | not achieved |
| render/visible pixels | no screen create; no framebuffer/visual proof | missing | unknown/not achieved |
| input/key path | `FX3_KEY` 1105 / `FX3_UI_GATE` 1 are not menu/key-event acceptance; no menu | missing semantic evidence | not achieved |
| cleanup | run dir only 5 files; serial tail cut mid-line at 179.53; reason `ap_guard_observed_continue`, elapsed 180.166; QMP quit/kill; no End marker/RESULT/RUN-SHA/cleanup receipt | timeout + self-report | cleanup not independently proven |

## C. Receipt caveats

- `serial_observation.fault_markers=[]` is narrow: it checks panic/Oops/Unable/Internal/SError, **not** `assert at`. The serial has four assert lines; target actually hit the known `1075` assert twice plus two `model_api` asserts.
- `cp_helper_rc_line=null` although serial contains the marker interleaved at line 1029; top-level `cp_helper_rc0=true` comes from substring search.
- `serial_observation.pre_ap_guard=false` vs top-level `pre_ap_guard=true`.
- `reason=ap_guard_observed_continue` while elapsed `180.166 > maximum 180`; final serial line is incomplete (`447 (SeqQueueInd`), consistent with timeout/QMP quit, not a clean guest End.
- No independent cleanup artifact; qemu_exit=0/reaped/locks are receipt self-report. File name `fx6kernel`/candidate name is not evidence by itself; actual kernel hash is fixed FX3 `da4a66…`.

## D. Baseline boundaries (2 rounds max)

| Baseline | Input difference | Known result | What it proves |
|---|---|---|---|
| `cp-bind-6e83a14a` | FX6 donor kernel `bc4925…`; CPIO `1cc4…`; appFw original `a1c58…`; upm `ba0c…`; backup `8a8d…`; no skip patches | known `assert at …:1075` line 10976; no screen/menu | The same CAPID assert exists without skips; target changed kernel and added skips, so differences cannot be attributed to skips alone. |
| `cp-bind-9d22099a` | FX6 donor kernel `bc4925…`; FX3 CPIO `11ad…`; FX3 appFw `545c…`; no FX6 appFw; no skip patches | `FX3_AP89_SCREEN_CREATE` 8, UUD 1; no menu | Screen marker is achievable in a different configuration; target with FX6 appFw/skip has screen 0; inputs differ, so not a causal fix/regression claim. |

## E. Missing evidence / next acceptance

Required before any FX6 boot/menu claim:

1. Original (not stub) appFw future::get, upm sensor/DFS, and backup path execute and return real results; no `mov w0,#0`/branch skip; function-level return/state observed.
2. No `assert at model_api.cpp:3147/3176` and no `assert at …:1075` (and no panic/Oops) in full serial.
3. At least `FX3_AP89_SCREEN_CREATE` and `FX3_AP89_UUD_DECISION` with real screen/presenter success, framebuffer/render evidence, and a menu marker; not just IM/poll/media markers.
4. Input path: menu open + key event/ack + visible UI response; not just `FX3_KEY` init or UI gate count.
5. Cleanup: guest End/stop marker, QMP/exit after guest stop, complete serial tail, run RESULT/SHA/cleanup artifact; not timeout/QMP-kill or self-report alone.
6. Receipt parser recognizes asserts/known faults; strict-line and nested/top-level fields consistent; no `fault_markers=[]` with assert lines present.
