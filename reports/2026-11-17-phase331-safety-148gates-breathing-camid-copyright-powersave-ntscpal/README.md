# Phase 331（Task H400 / H426 里程碑）：Wave-64 安全门控 `G147` / `G148` 与统一 `148/148` 主安全预检交付报告

- **日期**：`2026-11-18`（初始草拟 `2026-11-17`）
- **任务**：Task H400（草拟）· Task H426（收尾校验并提交，`codex/h426-phase331-safety-148gates-breathing-camid-copyright-powersave-ntscpal-finish`）— Phase 331
- **模块**：[`realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard.py`](../../outputs/fx3-safety/fx3_safety/realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard.py)
- **前置实测输入**：[`2026-11-17-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/README.md`](../2026-11-17-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/README.md)

---

## 1. 核心结论

1. 在 `outputs/fx3-safety/` 完成 Wave-64 安全门控 **`G147`**、**`G148`** 与统一 **`148/148` 主安全预检引擎**（`evaluate_148gate_preflight` / `verify-148-gates`）：
   - 对 `G01..G146` 严格委托 [`evaluate_146gate_preflight()`](../../outputs/fx3-safety/fx3_safety/realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard.py)，`verify-58-gates` .. `verify-146-gates` 保持 `100%` 向后兼容；`148/148` 自动接入 `verify-milestone-324` 与 `verify-milestone-311` 最高门控发现钩子。
   - **离线默认模式**：`145/148` 通过（`VERIFIED_145_OF_148_AWAITING_PHYSICAL_TIER0`）；**`--simulate-bench-dry-run` 预演模式**：`148/148` 通过（`VERIFIED_ALL_148_GATES_DRY_RUN_SIMULATED_BACKUP`）。
   - 所有写入/刷写/实机挂载红线永久锁死为 `False` / `0`：`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`USB_PACKETS_TRANSMITTED = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`。

---

## 2. 实测事实 vs 推断边界

### 2.1 实测事实（本工作树本地 donor 只读核验 + 源码实证）

- **12 项 Wave-64 donor 制品只读审计（`os.open(..., os.O_RDONLY)` + 有界 `os.pread`，`< 0.20s`）**：
  - `FX3 appFw.so`（`79,015,712 B`，28 个切片 SHA-256 = `e466b63226e21591d34baeff1720ec0297873062d46c1f64dba0b428a04e9c39`）。
  - `FX3 libSaveLoadSettings.so`（`18,760 B`，SHA-256 = `07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7`，位于 `menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/`）。
  - `FX3` 4 套语言资源 `_f.uxc`（英文/简中/繁中/日文）、`string_english.uxc`、`string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`。
  - `FX6 appFw.so`（`50,520,424 B`，9 个切片 SHA-256 = `cccf1d05c2c3fc40729917f75928ff77987c3bbc35f93173119e3867cda6d068`）及 `FX6 string_english.uxc` / `string_english_2.uxc`。
- **Gate `G147` 实证行为**：
  - `[Breathing Comp.]`（`0x6F7E`，`Off`/`On`，可经 `[Camera Settings Reset]` 重置，区别于 `Initialize`-only 的 `Shading`/`Chromatic Aberration`/`Distortion Comp.`）；适用 Wave-41 勘误：**常规 Movie `119.88p / 100p` (`120p`)** 与 **`S&Q` `100/120/200/240fps`** 均不可用（FX3 `S&Q < 100fps` 可用，FX6 全 `S&Q=On` 锁 `Off`）；不兼容镜头 / `SEL100F28GM` `0.57-1.0m` 微距环 / `SEL14TC`/`SEL20TC` 增距镜返回 `EOPNOTSUPP=95`；外部 `4264x2408` 16-bit HDMI RAW 旁路；后期补偿仅支持付费 **`Catalyst Prepare` / `Catalyst Prepare Plugin`** + 机身 `[Distortion Comp.] = [Auto]`，拒绝免费 `Catalyst Browse`（`EOPNOTSUPP=95`）。
  - `[File Settings]`（`0x73CC`，全 `Initialize`-only）：`[File Number]`（`Series`/`Reset` + `max + 1`）、`[File Name Format]` 5 项（**`SDHC FAT32 <= 32 GB` 强锁 `Standard`、`4 GB` 切分，禁止与 `exFAT` 混用 `Simult. Recording`**）、`[Cam ID + Reel#]`（改 ID 重置 `Reel#`，`File Number = Reset` 保留 `Reel#`，`C999 -> D001` 仅滚动输出不改菜单，`Date+Title` 用 `6` 位 `YYMMDD`）、`37` 字符 `[Title Name Settings]`（默认 `"C"`）、固定 `PRIVATE/M4ROOT/CLIP`（对比 FX6 `4..46` 字符 `nnn_` + `/XDROOT/Clip/*.MXF`）与 `Slot-1` Tier-0 Vault `EROFS=30` 防火墙（`864` 态矩阵）。
- **Gate `G148` 实证行为**：
  - **Round-57 重置勘误**：`[Copyright Info]`（4 项，`<= 46` 可打印 ASCII，排除出 `CAMSET*.DAT` 防 PII 泄露）与现行 **Still + Movie `[Write Serial Number]`**（`BKID_APP_setting_write_serial_number_still_movie`）**全部 `Initialize`-only（`[Camera Settings Reset]` 不可重置）**，允许 `Write Serial Number` 布尔开关导出至 `CAMSET*.DAT`。
  - `Setup -> [Power Setting Option]` 精确 `2` 项 `Initialize`-only 菜单（`[Power Save Start Time]` `Off/30/5[def]/2/1 Min/10 Sec`，休眠值 `20SEC`/`NO_LIMIT`/`30 sec`/`60 min`/`240 min` 返回 `EOPNOTSUPP=95`，精确 `9` 项官方自动旁路条件；`[Auto Power OFF Temp.]` `Standard`/`High` 三脚架警示），拒绝无 EVF 休眠项 **`[Power Save by Monitor]`**（`BKID_APP_setting_monitor_power_linkage` -> `EOPNOTSUPP=95`）；`[NTSC/PAL Selector]` 强制重启、`Running on NTSC./PAL.`、跨制式回放拦截及 `base.uxc 0xe1e6..0xe9f6` 格式化提示下 **`Slot-1` Tier-0 Vault Format/SD-Erase/TRIM `EROFS=30` 防火墙**（`288` 态矩阵）。
- **无 donor CI 防护**：显式检查 `work_root is None`，避免无本地 `Mac/work` 时出现 `NoneType / str` 异常；并同步将 Phase 327 [`test_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_146gate_guard.py`](../../outputs/fx3-safety/tests/test_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_146gate_guard.py) 中 `test_88_highest_gate_discovery_hook_finds_146` 修复为前向兼容断言（`assertIn(146, nums)` + `assertGreaterEqual(max(nums), 146)`）。

### 2.2 推断（非真实硬件上电实测）

- 本次交付仅在主机 Python 仿真、四模式单元测试与只读 donor 切片范围内完成验证；真实 FX3 `Ver. 7.02` 机内 `NTSC/PAL` 实机重启及物理卡槽交互仍保留在离线 `3/148` 待物理确认门控中（`--simulate-bench-dry-run` 下可达 `148/148` 仿真通过，仍不授权实机挂载）。

---

## 3. 验证摘要（均以 `PYTHONDONTWRITEBYTECODE=1` + `/usr/bin/python3 -B` 运行）

- Phase 331 单元测试（[`test_realhw_breathing_camid_copyright_powersave_ntscpal_148gate_guard.py`](../../outputs/fx3-safety/tests/test_realhw_breathing_camid_copyright_powersave_ntscpal_148gate_guard.py)）：`96/96` 通过，覆盖四模式——正常 donor（`96` tests, `34.426s`）、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 及 `FX3_FX6_MAC_WORK_ROOT=__fx3_fx6_clean_room_donor_disabled__` 无 donor 回退（三组 clean-room 连续执行合计 `35.402s` 后单模式均为 `96` tests `OK`）。
- `outputs/fx3-safety` 全量单元测试发现：正常模式 `4311/4311 OK`（`513.062s`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `4311` 项通过、`OK (skipped=10)`（`369.127s`，`0` 失败/`0` 错误）。
- CLI `verify-148-gates`：离线默认 `145/148`（`VERIFIED_145_OF_148_AWAITING_PHYSICAL_TIER0`, `leaked=0`）、`--simulate-bench-dry-run` `148/148`（`VERIFIED_ALL_148_GATES_DRY_RUN_SIMULATED_BACKUP`, `leaked=0`）、`--force-clean-room --simulate-bench-dry-run` `148/148`（`CLEAN_ROOM_SYNTHETIC`, `leaked=0`）。
- 双模式 `make verify-milestone-324`（含 `FX3_FX6_FORCE_CLEAN_ROOM=1`）：`status=OK`、`pillars=6/6`、`gate142=145/148`、`recovery=61/61`、`auditors=45/45`、`vm_stages=74/74`、`leaked=0`；[`test_realhw_milestone324_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone324_master_gate.py) `84/84 OK`（`25.546s`）；`make clean-audit` `ALL GREEN` 且零 `.pyc` / `__pycache__`。

---

## 4. 文件变更清单（仅 `outputs/fx3-safety/` 与本报告共 7 个文件）

1. `outputs/fx3-safety/fx3_safety/realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard.py`（新增）
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`（追加 Section 74）
5. `outputs/fx3-safety/tests/test_realhw_breathing_camid_copyright_powersave_ntscpal_148gate_guard.py`（新增，`96` 项测试）
6. `outputs/fx3-safety/tests/test_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_146gate_guard.py`（授权修复第 `1543` 行 `test_88_highest_gate_discovery_hook_finds_146` 为前向兼容 `assertIn(146, nums)` + `assertGreaterEqual(max(nums), 146)`）
7. `reports/2026-11-17-phase331-safety-148gates-breathing-camid-copyright-powersave-ntscpal/README.md`（本报告）
