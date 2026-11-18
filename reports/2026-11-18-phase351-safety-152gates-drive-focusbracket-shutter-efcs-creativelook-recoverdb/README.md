# Phase 351 工程结项报告：`152/152` 硬件安全门控（`verify-152-gates`，Wave 66 `G151` + `G152`）

- **日期**：`2026-11-18`
- **任务**：`H439` · **Phase 351（Wave 66 / 152/152 Hardware Safety Gates）**
- **目标基线**：`ILME-FX3 Ver. 7.02`（`ilc/2210`、`0x0502`、`PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6 Ver. 6.01`（`PRODUCT_MODEL_CHAPLIN`）
- **上游实证依据**：[Wave 66 情报报告](../2026-11-17-global-sony-wave66-drive-focusbracket-shutter-efcs-creativelook-recoverdb-intel/README.md)

---

## 一句话结论（结论先行）

**Phase 351 已在 `outputs/fx3-safety/` 端到端交付 `152/152` 硬件安全门控引擎（`G01..G152` / `verify-152-gates` / `verify_real_hardware_152gate_readiness`）**：严格基于 Wave 66 官方 UXC/ELF 实测依据完成 **`G151`**（静态 `[Drive Mode]` `10 fps Hi+` / `> F11` 首帧锁焦 / `Uncompressed RAW` 与闪光灯降速 + `0` 暴露休眠 `[Focus Bracket]` 辟谣 + 2 档 `[Shutter Type]` 零 `Auto` / `1/250 s` 单一闪光同步上限 / 抗 Reset `[e-Front Curtain Shut.]` `curtaion` 拼写 / `[Long Exposure NR]` `>= 1 s` / `[High ISO NR]` 与 `.ARW` 无损隔离）与 **`G152`**（`[Creative Look]` `10+6` 槽位 / `Fade`/`Sharpness`/`Clarity` `0..9` 非对称边界 / `PP`/`Log`/`HLG` `[-]` 锁定 + 双机 `0` 暴露休眠 `[Soft Skin Effect]` 辟谣 + 回放 `[Delete]`/`[Protect]`/`[Display Media Info.]`/`[Recover Image DB]` Tier-0 `Slot 1` `EROFS=30` 防火墙）；离线默认稳态 **`149/152`（`NO-GO` 待 Tier-0 物理备份）**，`--simulate-bench-dry-run` 与 `--force-clean-room` 下 **`152/152` 全通**，且所有只读红线（`emmc_writes_authorized=False`、`cross_model_flash_authorized=False`、`hardware_live_attachment_authorized=False`、`usb_packets_transmitted=0`、`raw_firmware_bytes_leaked=0`）全链锁死，`milestone324` 与 `milestone311` 均已自动发现 `152` 门控并双模式通过。

---

## 实测事实 vs 推断严格分层

### 1. 实测事实（可直接由代码、ELF/UXC 偏移、切片哈希与测试执行验证）

1. **核心交付模块与自动发现接入**：
   - 新增 [realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h439-phase351-safety-152gates-drive-focusbracket-shutter-efcs-creativelook-recoverdb/outputs/fx3-safety/fx3_safety/realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard.py)，向后委托 `evaluate_150gate_preflight()` 并叠加 `G151` + `G152` 生成 `Master152GateReport`（`schema_version = "realhw_152gate_preflight_v1"`），同时提供 `verify_real_hardware_152gate_readiness`、`evaluate_152_master_safety_gates` 与 `run_152_gate_preflight` 入口。
   - 已接入 [\_\_init\_\_.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h439-phase351-safety-152gates-drive-focusbracket-shutter-efcs-creativelook-recoverdb/outputs/fx3-safety/fx3_safety/__init__.py)（完整导出至 `__all__`）、[\_\_main\_\_.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h439-phase351-safety-152gates-drive-focusbracket-shutter-efcs-creativelook-recoverdb/outputs/fx3-safety/fx3_safety/__main__.py)（新增 `verify-drive-focusbracket-shutter-efcs-nr-guard` / `verify-g151`、`verify-creative-look-soft-skin-delete-protect-recoverdb-guard` / `verify-g152` 与 `verify-152-gates`，且 `help=` 百分号已转义为 `%%`）及 [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h439-phase351-safety-152gates-drive-focusbracket-shutter-efcs-creativelook-recoverdb/outputs/fx3-safety/README.md) 第 76 节。
   - 新增 100 项 4 模式单元测试 [test_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_152gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h439-phase351-safety-152gates-drive-focusbracket-shutter-efcs-creativelook-recoverdb/outputs/fx3-safety/tests/test_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_152gate_guard.py)，且动态发现断言严格使用 `assertIn(152, nums)` 与 `assertGreaterEqual(max(nums), 152)` 以保持前向兼容；上游 `150gate` 测试已自带 `>= 150` 前向兼容断言且实测无需修改。

2. **Gate `G151` 实测规则落地**：
   - **静态 `[Drive Mode]` 与 `10 fps` 门控**：`Shooting -> [Drive Mode]`（仅 `Still`，可被 `[Camera Settings Reset]` 重置）共 `8` 档（`Single Shooting` 默认、`Cont. Shooting` [`Hi+` `10 fps` / `Hi` `8 fps` / `Mid` `6 fps` / `Lo` `3 fps`]、`Self-timer(Single)` [`10/5/2 Sec`]、`Self-timer(Cont)` `6` 项 [拒绝休眠 `10SEC_10IMAGES`]、`Cont. Bracket`、`Single Bracket`、`WB bracket` [`Lo ±10 MK-1` / `Hi ±20 MK-1`]、`DRO Bracket` [在 `HLG Still Image = On` 时禁用]）；`Hi+/Hi/Mid` 在 `> F11` 时锁焦于首帧，`Uncompressed RAW` 或闪光触发时连拍降速。
   - **休眠 `[Focus Bracket]` 辟谣**：`BKID_APP_setting_focus_bracket_*` 与 `DRIVE_MODE_FOCUS_BRACKET` 虽存在于 `FX3 appFw.so`（以及 `FX6 appFw.so` 中的 `56` 个休眠符号），但在 `ilc/2210` 与 `5-024-458-18` UI 中均 **`0` 暴露**（`dormant_focus_bracket_exposed_events == 0`），任何伪造请求均以 `EOPNOTSUPP=95` 阻断。
   - **2 档 `[Shutter Type]`、`1/250 s` 上限、EFCS 与 NR**：`[Shutter Type]`（可 Reset）严格仅暴露 `Mechanical Shutter`（默认）与 `Electronic Shutter`（**无 `Auto` 选项**，`ELECTORONIC_SHUT` 仅存于休眠 `_anti_distortion_shutter` 系列；`[Shutter Type in Interval]` 独立默认 `Electronic Shutter`）；`Electronic Shutter` 或 `[Silent Mode] = On` 联锁禁用 5 项功能（`Flash`、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.`）；单档 `1/250 s` X-Sync 闪光同步上限（拒绝 `1/320 s` APS-C 档位）；`[e-Front Curtain Shut.]`（ELF 符号含索尼原生 `curtaion` 拼写：`BKID_APP_setting_front_curtaion_shutter`）默认 `On` 且 **抗 Reset（仅 `Initialize` 重置）**；`[Long Exposure NR]` 仅在 `>= 1 s` 执行暗帧减法且可 Reset；`[High ISO NR]`（`Normal/Low/Off`，无 `High` 档）不修改 `.ARW` 原始数据；对比 `ILME-FX6`（无机械快门、`Noise Suppression` 及 `Technical > APR`），跨机伪造以 `EOPNOTSUPP=95` 阻断。

3. **Gate `G152` 实测规则落地**：
   - **`[Creative Look]` `10+6` 槽位与非对称 `0..9` 参数**：`Exposure/Color -> [Color/Tone] -> [Creative Look]`（可 Reset）暴露 **10** 个预设（`ST` 默认/`PT`/`NT`/`VV`/`VV2`/`FL`/`IN`/`SH`/`BW`/`SE`）+ **6** 个 `Custom Look 1..6`（共 `16` 槽位，`look{0..15}`）；**8** 个调节参数中 `Contrast`/`Highlights`/`Shadows`/`Saturation` 范围为 `-9..+9`，而 **`Fade`/`Sharpness`/`Clarity` 严格为 `0..9` 非对称边界**（负值以 `EINVAL=22` 拒绝），`Sharpness Range` 范围为 `1..5`；`BW`/`SE` 锁定 `Saturation`，`Movie`/`S&Q` 锁定 `Sharpness Range`；当 `Picture Profile != Off`、`Log Shooting != Off`、`HLG Still Image = On` 或 `iAuto` 时强制显示为 `[-]`。
   - **休眠 `[Soft Skin Effect]` 双机辟谣**：`BKID_APP_setting_soft_skin_effect`（FX3）与 `FX6 ns1 0x2cce..0x32da` 在 `FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 上均为 **100% 休眠未暴露**（`0` UI 项暴露），任何启用请求均返回 `EOPNOTSUPP=95`。
   - **回放/介质操作与 Tier-0 `Slot 1` `EROFS=30` 防火墙**：`[Delete]` `5` 种批处理模式与代理文件协同删除、`[Delete confirm.]`（默认 `"Cancel" first`）及 `[Delete pressing twice]`（默认 `Off`）均 **抗 `[Camera Settings Reset]`**；`[Protect]` 仅 `7` 种模式（协同保护代理文件，**无 `"Cancel All Images"`**）；`[Display Media Info.]` 为纯只读查询（`40,000` 静态张数上限，允许对 `Slot 1` 执行且 `0` 写入）；`[Recover Image DB]` 重写 `AVF_INFO` 并清除 FTP 传输记录且同时免疫 `Camera Settings Reset` 与 `Initialize`；任何针对 `Slot 1` 的 `Delete`、`Protect`、`Recover Image DB` 或泛写操作均被 Tier-0 防火墙以 **`EROFS=30` 硬阻断**（`slot1_data_sector_writes == 0`、`emmc_nflasha_write_count == 0`），对比 `ILME-FX6` `Lock/Unlock Clip`、`Delete Clip` 与 `Restore Media(A)/(B)`。

4. **本地只读取证账本与四模式 CI 验证**：
   - `audit_phase351_donor_contracts` 仅以 `os.open(..., os.O_RDONLY)` + 精确 `os.pread` 审计 `10` 个 Wave 66 donor 构件（`FX3 appFw.so` `79,015,712 B` 33 切片、`FX6 appFw.so` `50,520,424 B` 6 切片、`BK4` 及四语言 UXC 包，`raw_firmware_bytes_leaked == 0`），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 及 `work_root=None` / 不存在路径下无缝切换至 `CLEAN_ROOM_SYNTHETIC`。

### 2. 推断（物理硬件与台架边界推断）

1. **Tier-0 物理挂载前 `Slot 1` 零扇区写入语义（推断）**：在未接通真实相机与物理 SD 卡写保护拨片之前，软件层的 `EROFS=30` 防火墙与 `AVF_INFO`/FTP 元数据拦截属于基于固件行为与门控模型的只读安全护栏；接入物理相机台架时仍必须同步保持 `Slot 1` 物理写保护开关锁定 `LOCK`，才能实现软硬件双层防篡改。
2. **`verify-152-gates` 离线返回码与 NO-GO 语义说明**：实测 `fx3_safety/__main__.py` 全系列 `verify-<N>-gates` 子命令（`verify-58-gates` 至 `verify-152-gates`）在离线默认模式满足 `offline_149_gates_verified == True` 时返回进程退出码 `0` 并在输出中显式标注 `status=VERIFIED_149_OF_152_AWAITING_PHYSICAL_TIER0` 与 `overall_ready_for_hardware_attach=False`（NO-GO）；该设计保证 `fx3-safety` 上游 CLI 回归测试与 `verify-milestone-324` 链路的一致性。

---

## 验证汇总（实测执行结果）

| 验证门 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| 4 模式 Phase 351 专项测试 | `test_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_152gate_guard.py`（normal / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / `work_root=None`） | **`100/100` 全模式通过**（`Ran 100 tests ... OK` x 3 + mock `work_root=None`） |
| `verify-152-gates` & `G151`/`G152` CLI | `verify-152-gates`（离线、`--simulate-bench-dry-run`、`--force-clean-room --simulate-bench-dry-run`）+ `verify-g151` / `verify-g152` | 离线 **`149/152`**（`VERIFIED_149_OF_152_AWAITING_PHYSICAL_TIER0`, `overall_ready_for_hardware_attach=False`）/ 仿真与 Clean-Room **`152/152`**、`leaked=0` |
| `outputs/fx3-safety` 全量单测 | 正常模式 + `FX3_FX6_FORCE_CLEAN_ROOM=1`（`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests`） | 正常模式 **`4509/4509 OK`**；`FX3_FX6_FORCE_CLEAN_ROOM=1` **`4509` 项 `OK`**（`10 skipped` 为早期仅本地 donor 用例） |
| Milestone 324 双模式联调 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` | 自动发现 `152` 门控，双模式均 **`gate142=149/152`**、`leaked=0`、`ready_attach=False` |
| 产物卫生审计 | `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | **`ALL GREEN`**，零 `.pyc` 或二进制污染 |
