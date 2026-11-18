# Phase 326 工程交付报告：Recovery Pillar 58（Wave-56）与 `58/58` 统一恢复总检（`verify-58pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`58/58` 恢复支柱闭环，`VERIFIED_58OF58_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：基于 Wave-56 `ILME-FX3 Ver. 7.02`（`0x91030080`，`ilc/2210`，`PRODUCT_MODEL_ALCIN_UUD`）与 `ILME-FX6 Ver. 6.01`（`5-024-458-18`，`PRODUCT_MODEL_CHAPLIN`）权威实证结果，完成 **Phase 326 Recovery Pillar 58**（Sub-Pillar **58A** `6/6` & Sub-Pillar **58B** `6/6`）及并发式 **`58/58` 统一恢复总检聚合器** `evaluate_realhw_58pillar_recovery_master`（`schema_version = "realhw_58pillar_recovery_master_v1"`，`verify-58pillar-recovery`），并自动接入 Milestone 311 与 Milestone 295 最高支柱发现接口（`recovery=58/58`），保持 `verify-22..57pillar-recovery` 100% 向后兼容。
- **关键实测结果（本地 `O_RDONLY` 供体 & 洁净室双模全过）**：
  - `verify-58pillar-recovery`（`LOCAL_DONOR_O_RDONLY`）：`pillars=58/58`，`all_passed=True`，核心耗时 **`1.127s`**（`< 1.5s` 快速预算），`raw_firmware_bytes_leaked=0`，`slot1_data_sector_writes=0`，`slot1_avf_info_mutated=False`，`slot1_vault_mutation_bytes=0`，`master_58pillar_sha256=2dca03a7b8a9951c5cb6ced45907ed2034fd538aeeeb42d8e270590b2947666e`。
  - `verify-58pillar-recovery --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`pillars=58/58`，`all_passed=True`，核心耗时 **`0.784s`**（`< 1.5s`），`raw_firmware_bytes_leaked=0`，`master_58pillar_sha256=72ff1ef2fef541b6d70b552bd376b9505fb21b7264c0e947409942448809ff3b`。
  - `verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault`：`58A=6/6`、`58B=6/6`，严格以 `os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK` 有界只读核验 **17 项** Wave-56 供体；`LOCAL_DONOR_O_RDONLY` 耗时 **`0.00343s`**（`suite_sha256=28dca10f98559329e381605e6437f864ceb7fcfeb3799c0ccc7e2c6b5f1a8752`），`CLEAN_ROOM_SYNTHETIC` 耗时 **`0.000381s`**（`suite_sha256=cd77d9ae6a72253bda6bcfc2ccbb7712a13f82718881bc1bf9c1e1bf633e7d76`），显式注入 `_iter_work_roots=(None,)` 与 `()` 均无 `TypeError` 安全回退 `CLEAN_ROOM_SYNTHETIC`。
  - Milestone 311 & Milestone 295（双模）：均输出 **`status=OK pillars=6/6 recovery=58/58 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 ready_attach=False cross_model_flash_auth=False leaked=0`**。
  - **硬件安全护栏硬锁**：`PERSISTENT_EMMC_WRITES_AUTHORIZED=False`、`SPI_NOR_WRITE_AUTHORIZED=False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED=False`、`ISP_WRITE_AUTHORIZED=False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED=False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED=False`、`OVERALL_READY_FOR_HARDWARE_ATTACH=False`、`CROSS_MODEL_FLASH_AUTHORIZED=False`、`OTP_FUSE_TOUCHES=0`、`RPMB_COUNTER_INCREMENTS=0`、`PHYSICAL_DEVICE_WRITES=0`、`RAW_FIRMWARE_BYTES_LEAKED=0`。

---

## 2. Wave-56 实测事实 vs 工程推断边界

> 严格区分来自 `ILME-FX3`（`ilc/2210`、`Ver. 7.02 appFw.so`/UXC/`Backup.bin`）与 `ILME-FX6`（`5-024-458-18`、`Ver. 6.01 appFw.so`/UXC）的**实测事实**，以及恢复子系统施加的**工程推断/安全护栏**（参见 [Wave-56 权威情报报告](../2026-11-17-global-sony-wave56-dial-wheel-setup-mydial-fn-menu-liveview-lut-embed-intel/README.md)）。

### 2.1 Sub-Pillar 58A：`[Dial Customize]` 5 项、`3` 转盘拓扑、`My Dial 1..3`、`Fn 12+12` 与 FX6 边界

1. **实测事实 — `MENU -> (Setup) -> [Dial Customize]`（`_g 0x62ed`）精确 5 项且全数 `Initialize`-only**：
   - `[Custom Key/Dial Set.]`（`_f 0x6290`/`0x73a0`，自 Ver. 2.00+ 正式替代旧 Ver. 1.xx `[Dial Setup]`）、`[My Dial Settings]`（`1..3`）、`[Av/Tv Rotate]`（`_f 0x72e3`，`Normal` 默认 / `Reverse`）、`[Function Ring(Lens)]`（`_f 0x715e`，仅 `Power Focus` 默认 / `APS-C/Super 35 mm / Full Frame`，拒绝 `VAL_setting_function_ring_FUNCTION_RING_INVALID`）与 `[Lock Operation Parts]`（`_f 0x6904`，`Off` 默认 / `Multi-Selector Only` / `Dial + Wheel` / `All`，替代旧 `[Dial / Wheel Lock]` `0xe352`，支持长按 `Fn` 切换锁定及 `MENU + Fn` 同按 5 秒全锁）。以上 5 项全数抵抗 `[Camera Settings Reset]`。
2. **实测事实 & 工程护栏 — `3` 物理转盘拓扑与休眠符号 `EOPNOTSUPP=95` 拦截**：
   - FX3 实机仅具备 `Front Dial`（`0xe4da`）、单 `Rear Dial`（`0xe4db`）与 `Control Wheel`（`0xe353`）3 个物理转盘；`FX3 appFw.so` / UXC 中残留的 `Rear Dial L/R`（`0x6a5c`/`0x680d`）、`BKID_APP_setting_dial_setup`、`Dial/Wheel Setup`（`0x6a89`）及 `Dial / Wheel Lock`（`0xe352`）均属跨机种休眠符号。工程护栏在 Stage-B/恢复网关对上述休眠符号强制 fail-closed 返回 `EOPNOTSUPP=95`。
3. **实测事实 — `My Dial 1..3` 跳空与锁覆盖、`[Fn Menu Settings]` `12+12` 拆分及 FX6 对比**：
   - `My Dial 1..3` 为共享 NVRAM 槽（`Initialize`-only），支持 Still/Movie 独立绑定 `Hold`（`0x66fe`）/ `Toggle`（`0x6bc0`）/ `1->2->3`（`0x7987`），`1->2->3` 自动跳过全 `Not set` 空组并在激活期间临时覆盖解锁 `[Lock Operation Parts]`。
   - `[Operation Customize] -> [Fn Menu Settings]`（`_g 0x614b`，`Initialize`-only）严格拆分为 `12 Still + 12 Movie` 槽位（`0..11`）；全为 `Not set`（`0xe0ac`）时按 `Fn` 触发 `_f 0x6220` 无效提示（状态模型映射为 `EINVAL=22`）。
   - `ILME-FX6` 采用 `Multi Function Dial`（`Project > Multi Function Dial > Default Function`）、`Grip Dial`、`Handle Dial`、`IRIS Dial`、`ND Dial`、物理 `HOLD` 开关与 `Status Screens`/`Direct Menu`，不存在 `Av/Tv Rotate` / `My Dial` / `Fn Menu`。

### 2.2 Sub-Pillar 58B：`[Live View Display Set.]` 非对称复位、`[Grid Line]` Clean-HDMI 隔离与 LUT 路径/`Slot-1` 防火墙

1. **实测事实 — `Shooting -> [Shooting Display] -> [Live View Display Set.]`（`_f 0x6429`）Still 专属 3 项非对称复位**：
   - 仅 Still 域有效（推断/护栏：Movie/`S&Q` 域请求返回 `EOPNOTSUPP=95`）。
   - `[Live View Display]`（`Setting Effect ON` 默认 / `OFF`，开启 `[Bright Monitoring]` 自动强制 `OFF`）与 `[Exposure Effect]`（`Exposure Set. & flash` 默认 / `Exposure Setting Only`）均为 `Initialize`-only；**仅 `[Frame Rate Low Limit]`（`On` / `Off` 默认）为可复位项（`can_be_reset=True`，随 `Camera Settings Reset` 归位 `Off`）**。
2. **实测事实 — `[Grid Line]` 与 Clean-HDMI/RAW OSD 隔离**：
   - `[Grid Line Display]`（`On` / `Off` 默认）与 `[Grid Line Type]`（`Rule of 3rds Grid` 默认 / `Square Grid` / `Diag. + Square Grid`）均为 `Initialize`-only；当 `HDMI Info. Display = Off`（`_f 0x6e7c`）或 RAW/`Off(HDMI Only)` 时，网格线严格隔离于机身 LCD，不污染 HDMI 清洁输出（对比 FX6 `Monitoring > Marker > Guide Frame` 与休眠 `BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0..3`）。
3. **实测事实 + 工程推断 — `[Manage User LUTs]`/`[Select LUT]`/`[Embed LUT File]` vs `PPLUT1..4` 与 `Slot-1` `EROFS=30` 防火墙**：
   - **实测事实**：`Exposure/Color -> [Color/Tone]`（`_g 0x61fa`）下提供 `[Manage User LUTs]`（`User1..16` 17/33-pt `.cube`，`Initialize`-only；SD/SDXC 路径 `/Private/Sony/PRO/LUT`，CFexpress `/Sony/PRO/LUT`）与 `[Select LUT]`（`S-Log3`/`s709` 默认可复位/`709(800%)`/`User1..16`，空槽回退 `S-Log3`）。`[Embed LUT File]` 位于 `Shooting -> [Image Quality/Rec] -> [Log Shooting Setting]`（不在 `Color/Tone` 下，默认 `On` 可复位），以容器元数据内嵌保留原生 `S-Log3` 像素且零外部 `.cube` 伴随文件，SD/SDHC 下被 `_g 0x61a0` 硬件锁死为 `Off`。`Picture Profile -> PPLUT1..4`（`_f 0x6095`）执行不可逆 DSP 像素烘焙，且会随 `Camera Settings Reset` / `Initialize` 重置（区别于保留的 `PP1..PP11`）。FX6 则限定 `Base Look` `16` 槽 UI 上限（休眠 `0..49` 缓冲槽）、`/PRIVATE/SONY/PRO/LUT/` 与 `/SONY/PRO/LUT/`、多通道独立 LUT 开关。
   - **工程推断（`Slot-1` Tier-0 保险库护栏）**：从 `Slot-1` 纯只读导入 `.cube` 在 `slot1_data_sector_writes == 0` 且不建目录时安全放行；任何指向 `Slot-1` 的写盘、内嵌录制、`PPLUT` 烘焙写卡、新建目录（`Make Cube Folder`）或格式化操作必须 fail-closed 拦截返回 `EROFS=30`，保证 `slot1_avf_info_mutated == False`。

---

## 3. 严格 6 文件交付清单（File Ownership Inventory）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py) | Pillar 58A/58B 状态机与评估器、17 项 `O_RDONLY` 供体有界核验（实测 `0.00334s`）+ 洁净室回退（含 `work_root is None` 防护）、`6/6 + 6/6` 场景套件及并发 `58/58` 主控 `evaluate_realhw_58pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出 Phase 326 `P326_*` / `PHASE326_*` / `MASTER_58_*` / `evaluate_realhw_58pillar_recovery_master` 等符号，供 Milestone 311 / 295 自动发现 `58/58` |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault` 与 `verify-58pillar-recovery` CLI 子命令 |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 326 Pillar 58 & `58/58` 恢复总检文档与 CLI 示例 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py) | **90 项**双模单元测试（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`work_root=None`、向后兼容与 Milestone 自动发现） |
| 6 | NEW | [`reports/2026-11-17-phase326-realhw-58pillar-dial-customize-mydial-fn12x2-liveview-lut-embed-vault-recovery/README.md`](README.md) | 本 Phase 326 中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 58 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest -v outputs/fx3-recovery-adapter/tests/test_realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py` | **`90/90 OK`**（`skipped=0`，`21.244s`） |
| Pillar 58 单测（`FX3_CLEAN_ROOM_TEST=1`） | `FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest ...` | **`90/90 OK`**（`skipped=1`，`20.650s`） |
| Pillar 58 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest ...` | **`90/90 OK`**（`skipped=1`，`19.733s`） |
| 显式模拟无供体 `work_root=None` | `mock.patch.object(p326, "_iter_work_roots", return_value=(None,))` | **`CLEAN_ROOM_SYNTHETIC` (`17` 供体, `all_passed=True`, 零 `TypeError`)** |
| `verify-pillar58-...` CLI（供体 / 洁净室） | `verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault --json` & `--force-clean-room --json` | **`58A=6/6, 58B=6/6, donors=17`**（`0.00343s` / `0.000381s`，`leaked=0`） |
| `verify-58pillar-recovery` CLI（供体 / 洁净室） | `verify-58pillar-recovery --json` & `--force-clean-room --json` | **`58/58 PASS`**（`1.127s` / `0.784s` `< 1.5s`，`leaked=0`） |
| `make verify-milestone-311`（双模） | `make verify-milestone-311` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-311` | **`status=OK pillars=6/6 gate134=141/144 recovery=58/58 leaked=0`**（`53409c149ba7c724...` / `0e2ce3f0ad068ba5...`） |
| `make verify-milestone-295`（双模） | `make verify-milestone-295` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` | **`status=OK pillars=6/6 gate124=141/144 recovery=58/58 leaked=0`**（`f534b9a41eff5071...` / `aa722e971786d1ae...`） |
| 清洁审计 | `make clean-audit` | **`ALL GREEN in 3.21s`**（零 `.pyc` / `__pycache__`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（本地供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -t outputs/fx3-recovery-adapter/tests -p "test_*.py"` | **`3,395 tests OK`**（`skipped=1`，`412.076s`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（强制洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -t outputs/fx3-recovery-adapter/tests -p "test_*.py"` | **`3,337 tests OK`**（`skipped=17`，`370.592s`） |
