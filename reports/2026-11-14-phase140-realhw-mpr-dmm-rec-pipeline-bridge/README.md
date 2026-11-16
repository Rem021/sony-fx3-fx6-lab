# Phase 140 — 28th Unified `fx3-firmware-lab` Auditor: Real-Hardware Main Track Part 6 (`libMpr.so` / `osal_uipc` / `DmmCfg.bin` `MAIN` Card-Recording & Live-View Parameter-Binding ABI Bridge)
# 第 140 阶段 — 第 28 个统一 `fx3-firmware-lab` 审计器：真机主线第 6 部分（FX6 `appFw.so` -> 原厂 FX3 `libMpr.so` / `osal_uipc` / `DMM` `MAIN` 录卡与实时监看参数绑定 ABI 桥接）

- **Date / 日期**: 2026-11-14
- **Module / 模块**: [`outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_mpr_dmm_rec_pipeline_bridge_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_mpr_dmm_rec_pipeline_bridge_auditor.py)
- **CLI Subcommand / CLI 子命令**: `audit-realhw-mpr-dmm-bridge` (integrated as #28 in `audit-all`)
- **Tests / 单元测试**: [`outputs/fx3-firmware-lab/tests/test_realhw_mpr_dmm_rec_pipeline_bridge.py`](../../outputs/fx3-firmware-lab/tests/test_realhw_mpr_dmm_rec_pipeline_bridge.py) (**45/45** passing in both Local Donor & `FX3_FX6_FORCE_CLEAN_ROOM=1` modes)

---

## English Technical Summary

### 1. Verification Results & Deterministic Digests

| Verification Gate | Mode / Scope | Result | Runtime | Digest / Count |
| :--- | :--- | :--- | :--- | :--- |
| `analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=False)` | `LOCAL_DONOR_VERIFIED` (14 donor files `os.O_RDONLY` + `mmap.ACCESS_READ`) | `all_checks_passed = True` | `0.0480 s` (`< 0.25 s`) | `report_sha256 = a244dacfdc5d0191f636672b9a3b17834a64db993a15712cd8030d0d999e7f78` |
| `analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)` | `CLEAN_ROOM_SYNTHETIC` | `all_checks_passed = True` | `0.0032 s` (`< 0.02 s`) | `report_sha256 = ee7e9725e0f24cfa3c3cd74a4becbf8401ae6ec14d2df4f03dc241309294b534` |
| `audit-all --json` (Local Donor) | All 28 auditors | `all_checks_passed = True` (`28/28`) | `9.539 s` | `28/28` green (`525,233 B` JSON) |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... audit-all --json` | All 28 auditors (Clean-Room) | `all_checks_passed = True` (`28/28`) | `0.090 s` | `28/28` green (`483,521 B` JSON) |
| `unittest` Phase 140 suite | Local Donor / Forced Clean-Room | `OK` (`45/45` each) | `0.590 s` / `0.434 s` | `45` tests |
| `unittest discover` Full Lab Suite | Local Donor / Forced Clean-Room | `OK` (`880/880` each) | `28.677 s` / `15.721 s` | `880` tests (`28` auditors) |
| `scripts/run_all_lab_tests.py --clean-only` | Binary / `.pyc` / `git status` hygiene | `CLEAN` | `0.04 s` | `0` forbidden artifacts |

### 2. Verified Local Donor Artifacts (`os.O_RDONLY` + `mmap.ACCESS_READ`, Zero Mutations)

1. **FX3 `v7.02` (`PRODUCT_MODEL_ALCIN_UUD`)**:
   - `libmpr.so`: `3,517,008 B` (`3,541` exports, `356` imports, `9` `DT_NEEDED` including `libsecvlt.so`)
   - `appFw.so`: `79,015,712 B` · `DmmCfg.bin` (AP `/setting/DmmCfg.bin`): `66,796 B` (`603` units, `290` rules, version `for ilc32g12m-ipsxmp 2025/06/20 15:43:19`)
   - `osal_uipc.ko`: `76,168 B` · `libosal_uipc.so`: `43,752 B` · `libInfraAvbbc.so`: `1,734,632 B` (`738` `ParameterControl` exports) · `im.elf`: `40,920 B`
2. **FX6 `v6.01` (`PRODUCT_MODEL_CHAPLIN`)**:
   - `libmpr.so`: `28,921,824 B` (`4,271` exports, `497` imports, `8` `DT_NEEDED`, no `libsecvlt.so`)
   - `appFw.so`: `50,520,424 B` · `DmmCfg.bin` (AP `/setting/DmmCfg.bin`): `59,364 B` (`556` units, `259` rules, version `for ilc32g12m-ipsxmp 2025/10/02 12:16:04`)
   - `osal_uipc.ko`: `76,360 B` · `libosal_uipc.so`: `43,752 B` · `libInfraAvbbc.so`: `1,743,200 B` (`720` `ParameterControl` exports) · `im.elf`: `40,920 B`

### 3. Four Audited Route-1 AP -> CP Bridge Pillars

1. **Pillar 1 — `LIBMPR_EXPORT_AND_OPEN_START_CLOSE_ABI_DIFF`**:
   - FX3 `7.02` and FX6 `6.01` `libmpr.so` share **`3,102`** exports (`439` FX3-only, `1,169` FX6-only).
   - Of the **`89`** symbols FX6 `appFw.so` imports from `libmpr.so`, **`74` are pass-through compatible** in Stock FX3 `libmpr.so` (covering `PrepareRecStart`, `RecStart`, `RecStop`, `SetMovieRecParam`, `GetMovieRecParam`, `GetMovieRecStatus*`, `UnlockMovieRecStatus`, `ExecEncOpen/Start/Stop/Close`, `CallbackFromAvbbc`, `SendMsgToAvbbc`, `GetFixedArea`, `GetDmmModeId`, `GetDmmExtList`, `SetMemTbl`, `SetLutData`), while **`15` FX6-only symbols** (`RecClipClose`, `GetResumeInfo`, `GetMovieDetailInfo`, `ChangeMovieRecMedia`, `GetCacheRecBackTime`, `GetMediaTransferRateInh`, `file::GetTrimSupportFormatTable`, `file::Stat`, `ClipName::{C1,D1}Ev`, `RecPause`, `CheckCopy`, `GetLastTC`, `NextThumb`, `RecResume`) require `LD_PRELOAD` Stage-B shims.
   - `libosal_uipc.so` exports are **100% identical** (`87` exports); `im.elf` preserves identical `libosal_uipc.so`, `libbackup.so`, and `libIMDB.so` linkage.
   - Direct dereference of ABI-divergent global structs is explicitly blocked: `_ZN3mpr16g_videoParamCombE` (`312 B` FX3 vs `480 B` FX6) and `_ZN3mpr14s_movieRecInfoE` (`3,144 B` FX3 vs `5,248 B` FX6), whereas `_ZN3mpr16s_movieRecStatusE` (`136 B`), `_ZN3mpr13s_movieRWlockE` (`64 B`), `_ZN3mpr15s_recordCounterE` (`4 B`), and `_ZN3mpr6memory14s_mprFixedAreaE` (`160 B`) match across both bodies.
2. **Pillar 2 — `DMM_CFG_NODE_TOPOLOGY_AND_UNSUPPORTED_SINK_MASK`**:
   - Decodes AP `DmmCfg.bin`: **`548` shared units**, **`55` FX3-only units**, **`8` FX6-only units** (`1204, 1205, 1615, 1620, 1621, 1622, 1867, 1868`).
   - All **`20` target `MAIN` recording unit IDs** (`700, 701, 822, 823, 922, 939, 962, 963, 966, 974, 975, 985, 986, 987, 991, 1243, 1244, 1245, 1246, 528413`) exist in both FX3 and FX6 AP `DmmCfg.bin` with **`1` extent each** (bounded within `GetDmmExtList`'s `0xa8` stack reply limit of `1..8` extents = `0x18 + 16*N`). DMM mode row counts `21/25/31/32 -> 7/10/13/19` are verified.
   - Enforces fail-safe stubbing of FX6-only hardware sinks (`12G_SDI_SERIALIZER`, `RAW_OVER_SDI`, `DARWIN_VARIABLE_ND`) so FX6 `appFw.so` never issues a DMM pool allocation request to Stock FX3 `cpapp-b.bin`.
3. **Pillar 3 — `MENU_EVENT_TO_CP_PARAMETER_BINDING_CONTRACT`**:
   - Verifies deterministic `FX6 Menu Event -> ParameterControl (56 B) -> Stock FX3 CP` translation across all 6 shooting domains: Base ISO (`800` / `12800`), Frame Rate / S&Q (`1..240 fps` IMX510 readout, clamping `4K` at `120p` and blocking `5K_OPEN_GATE`), Shutter Angle -> Speed (`180 deg @ 24p -> 1/48s`, zero mechanical shutter actuations), White Balance (`2000K..15000K`, Tint `-99..+99`, soft-mapped `WHT BAL` switch), Color/Look (`S-Log3 / S-Gamut3.Cine`, `S-Cinetone`, `.cube` MLUT staged in volatile RAM), and REC Start/Stop (`CFexpress Type A` / `SDXC` `Slot A & B`, enforcing `VPG200/400` / `V90` card gates).
4. **Pillar 4 — `UIPC_QUEUE_GUARD_AND_RECORD_LOCK_SAFETY`**:
   - Verifies `GetFixedArea(0..4)` (`0x8e00` total; `type 2 -> offset 0x0000, 512 B`), `PayloadMpr +0x28` virtual vs `+0x08` physical pointer domain isolation, `osal_valloc_msg_wait` `align64(align4(L)+24+4+40)` (`0x80c70047 -> 0x8055001f`), `Dataflow::ReceiveASync` `384 B` cap, `osal_uipc.ko` `ioctl` `op <= 16` & `ptr + 15 <= addr_limit`, `CallbackFromAvbbc` 48 B reply copy before `osal_free_msg` (`0x8000000b`), `s_movieRWlock` (`64 B`) pairing on `s_movieRecStatus` (`136 B`), and `ExecEncClose` `s_recordCounter` (`4 B`) gating to prevent `.RSV` unfinalized clips or IPC queue hangs.
   - `persistent_emmc_writes_authorized = False`, `emmc_mutation_bytes = 0`, `calibration_mutation_bytes = 0`, and `0` raw proprietary byte slices in JSON output.

### 4. Committed Files (6 Phase 140 Deliverables + 1 Coordinator-Authorized Forward-Compatibility Fix)

1. [`outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_mpr_dmm_rec_pipeline_bridge_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_mpr_dmm_rec_pipeline_bridge_auditor.py)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)
4. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md)
5. [`outputs/fx3-firmware-lab/tests/test_realhw_mpr_dmm_rec_pipeline_bridge.py`](../../outputs/fx3-firmware-lab/tests/test_realhw_mpr_dmm_rec_pipeline_bridge.py)
6. [`reports/2026-11-14-phase140-realhw-mpr-dmm-rec-pipeline-bridge/README.md`](./README.md)
7. [`outputs/fx3-firmware-lab/tests/test_realhw_cp_rtos_and_backup_bin.py`](../../outputs/fx3-firmware-lab/tests/test_realhw_cp_rtos_and_backup_bin.py) (relaxed lines 206 & 215 from `assertEqual(..., 27)` to `assertGreaterEqual(..., 27)`)

---

## 简体中文技术报告

### 一、 双模式实测验证结果

- **本地 Donor 模式**（严格 `os.O_RDONLY` + `mmap.ACCESS_READ` 只读扫描 14 份 FX3 `v7.02` 与 FX6 `v6.01` 二进制/配置）：单项审计耗时 **`0.0480 s`**（远低于 `0.25 s` 上限），`all_checks_passed = True`，`report_sha256 = a244dacfdc5d0191f636672b9a3b17834a64db993a15712cd8030d0d999e7f78`。
- **Clean-Room 合成模式**（`FX3_FX6_FORCE_CLEAN_ROOM=1`）：耗时 **`0.0032 s`**，`all_checks_passed = True`，`report_sha256 = ee7e9725e0f24cfa3c3cd74a4becbf8401ae6ec14d2df4f03dc241309294b534`。
- **`audit-all --json` 全量集成（28/28 全绿）**：本地 Donor 模式（`525,233 B` JSON）；Clean-Room 模式（`483,521 B` JSON）。
- **单元测试与仓库卫生**：Phase 140 专项 **`45/45`** 双模式全过（Donor `0.590 s` / Clean-Room `0.434 s`）；全量实验室套件 **`880/880`** 双模式全过（Donor `28.677 s` / Clean-Room `15.721 s`）；`scripts/run_all_lab_tests.py --clean-only` 返回 **`ALL GREEN in 0.04s`**。

### 二、 四大审计支柱核心实证结论

1. **支柱一 — `libmpr.so` 导出符号与结构体 ABI 隔离**：
   - FX3 `v7.02`（`3,541` 导出）与 FX6 `v6.01`（`4,271` 导出）共享 **`3,102`** 个 `libmpr.so` 导出符号。FX6 `appFw.so` 导入的 `89` 个 MPR 符号中，**`74` 个可直接透传原厂 FX3 `libmpr.so`**（含 `PrepareRecStart`/`RecStart`/`RecStop`/`SetMovieRecParam`/`GetMovieRecStatus`/`ExecEnc*`/`CallbackFromAvbbc`/`GetDmmExtList`/`SetLutData`），仅 **`15` 个 FX6 独占符号**需 `LD_PRELOAD` Stage-B 垫片拦截。
   - `libosal_uipc.so` 导出 100% 一致，`im.elf` 依赖一致；严格禁止直接解引用跨机身尺寸漂移结构体（`g_videoParamComb` `312 B` vs `480 B`、`s_movieRecInfo` `3,144 B` vs `5,248 B`），而共享状态锁/计数器（`s_movieRecStatus` `136 B`、`s_movieRWlock` `64 B`、`s_recordCounter` `4 B`、`s_mprFixedArea` `160 B`）尺寸完全一致。
2. **支柱二 — AP `DmmCfg.bin` 节点拓扑与 FX6 独占硬件掩码**：
   - 精确解码 FX3（`66,796 B`、`603` 单元、`290` 规则）与 FX6（`59,364 B`、`556` 单元、`259` 规则）AP `DmmCfg.bin`，跨机身 **`548` 共享单元 / `55` FX3 独占 / `8` FX6 独占**（`1204, 1205, 1615, 1620, 1621, 1622, 1867, 1868`）。
   - `MAIN` 录卡目标 **`20` 个关键单元**在双端均存在且均为 `1` 个 extent（远小于 `GetDmmExtList` `0xa8` 栈帧 `8` extent 上限），DMM 模式 `21/25/31/32` 行数（`7/10/13/19`）匹配；强制屏蔽/桩化 `12G_SDI_SERIALIZER`、`RAW_OVER_SDI` 与 `DARWIN_VARIABLE_ND`，杜绝 FX6 `appFw.so` 向原厂 FX3 `cpapp-b.bin` 请求不存在的内存池。
3. **支柱三 — 六大核心拍摄域菜单事件 -> `ParameterControl` -> FX3 CP 参数绑定**：
   - 验证 `Base ISO (800/12800)`、`Frame Rate & S&Q (1..240fps)`、`Shutter Angle->Speed (180°@24p -> 1/48s，零机械快门触发)`、`White Balance (2000K..15000K + Tint)`、`Color/Look (S-Log3 / S-Gamut3.Cine / S-Cinetone / .cube MLUT)` 与 `Slot A/B` 录卡启停契约，拦截 `5K Open Gate`、`X-OCN` 等 FX3 不支持模式及低速卡 `V30/V60` 录制 `XAVC S-I 4K`。
4. **支柱四 — `osal_uipc` 队列边界、回调释放顺序与防 `.RSV` 锁闭安全**：
   - 校验 `GetFixedArea(0..4)`（`0x8e00`）、`PayloadMpr +0x28` 虚拟指针域、`osal_valloc_msg_wait` `64B` 对齐公式、`Dataflow::ReceiveASync` `384 B` 上限、`CallbackFromAvbbc` 先拷贝 `48 B` 再 `osal_free_msg`、`s_movieRWlock` 配对及 `ExecEncClose` `s_recordCounter` 归零关断逻辑（防止未封口 `.RSV` 坏片或 IPC 队列挂死）；`persistent_emmc_writes_authorized = False`。
