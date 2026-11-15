# Phase 241 安全护栏里程碑报告：`92/92` Safety Gates G91 / G92 与统一 `verify-92-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-36 官方 `ILME-FX3 Ver. 7.02` 安全门禁 `G91`、`G92` 与统一 `92/92` 里程碑主预检引擎（`G01..G92`）闭环交付**：
   - 新增模块 [`realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py)（Schema `realhw_shoe_audio_wind_saveload_c3_and_92gate_guard_v1` `v1.0.0`，将 `G01..G90` 直接委托给 [`evaluate_90gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py#L2080-L2302)，`100%` 保留 `verify-58-gates` 至 `verify-90-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase241_shoe_audio_wind_saveload_c3_92gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/tests/test_phase241_shoe_audio_wind_saveload_c3_92gate_guard.py) 共 **66 项**双模式单元测试（要求 `>=62` 且 `<5s`），在 `LOCAL_DONOR_O_RDONLY`（`4.282s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`2.429s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`2063/2063` 全部通过（`129.986s`）**，Clean-Room 合成模式 **`2062` 项通过、`1` 项按设计跳过（`77.243s`）**；
   - CLI `verify-92-gates`：默认离线模式通过 **`89/92`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`92/92`**；
   - 跨模块里程碑与 BYOF 卫生审计：`make verify-milestone-221` 双模式 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN`（零 `.pyc`、零专有固件字节泄漏）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G91 与 Gate G92 技术建模要点（Wave-36 规范映射）

### 2.1 Gate G91：`G91_shoe_audio_4ch_meter_routing_and_wind_noise_builtin_only_guard`
- **`[Shoe Audio Set.]` `48kHz/24bit 4ch` 四声道电平路由与三大硬件互斥覆盖规则**：
  - [`resolve_fx3_shoe_audio_and_wind_noise_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py#L912-L1063) 与 [`verify_shoe_audio_4ch_and_wind_noise_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py#L1066-L1410) 精确建模 `MENU -> Shooting -> [Audio Recording] -> [Shoe Audio Set.]`：
    - 枚举与重置边界：`48kHz/16bit 2ch`（出厂默认）、`48kHz/24bit 2ch`、`48kHz/24bit 4ch`，且在 `[Camera Settings Reset]` 与 `[Initialize]` 时均恢复 `48kHz/16bit 2ch`（违例阻断为 `BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_MISMATCH`）；
    - 四声道激活与表头自动展开：当挂载数字 MI 热靴 4ch 声源（`XLR-H1` 拨于 `DIGITAL` 档或 `ECM-M1`）且 `[Shoe Audio Set.]=48kHz/24bit 4ch` 时，路由 `CH1..CH4` 四轨 LPCM 并自动将 `[Audio Level Display]` 从 `2ch` 展开至 `4ch`（违例阻断为 `BLOCKED_G91_SHOE_AUDIO_4CH_METER_EXPANSION_MISMATCH`）；
    - 三大硬件互斥与降级条件：(a) `[Audio Recording]=Off` 或 `S&Q Motion` 慢快动作（强制锁定 `0` 音轨，菜单灰显不可用）；(b) 机身侧面 `3.5mm` `MIC` 插孔插入外接麦（硬件插孔检测强制接管并降为机身模拟 ADC `2ch`）；(c) `XLR-H1` 手柄 `[DIGITAL/ANALOG]` 拨杆置于 `[ANALOG]`（硬件回退至模拟热靴 `48kHz/16bit 2ch`，忽略菜单 `24bit/4ch` 请求；违例阻断为 `BLOCKED_G91_SHOE_AUDIO_LOCKOUT_OR_OVERRIDE_VIOLATION`）。
- **`[Wind Noise Reduct.]` 仅限机内立体声麦克风生效边界与室内台架低频保护**：
  - 精确建模 `MENU -> Shooting -> [Audio Recording] -> [Wind Noise Reduct.]`（`Off` 出厂默认 / `On`，`[Camera Settings Reset]` 恢复 `Off`）：
    - 严格限定仅对机身内置立体声麦克风生效；当接入 `3.5mm` `MIC` 外接麦或 MI 热靴 `XLR-H1` 手柄时，DSP 高通降风噪对外接通道完全无效（`external_mic_wind_reduct_effective == False`，违例阻断为 `BLOCKED_G91_WIND_NOISE_EXTERNAL_MIC_INEFFECTIVE_BOUNDARY_VIOLATION`）；
    - 在室内无风测试台架下若内置麦开启 `[Wind Noise Reduct.]=On`，将不必要地衰减低频基频并扭曲台架声学参考，触发 `BLOCKED_G91_INDOOR_LOW_WIND_BENCH_ATTENUATION_ACTIVE` 阻断；在 `S&Q Motion` 或 `[Audio Recording]=Off` 下强制锁定不可用。
- **有界 `< 0.10s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底**：
  - [`audit_phase241_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py#L754-L903) 以 `os.O_RDONLY` 只读描述符校验 `cpapp-b.bin`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`（`raw_firmware_bytes_leaked == 0`），并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性合成模式。

### 2.2 Gate G92：`G92_saveload_camset_c3_excluded_items_and_slot1_tier0_vault_guard`
- **`[Save/Load Settings]` 跨存储卡 `CAMSET01..10.DAT` 同机型锁与 `C3 Portal` 云端目标建模**：
  - [`resolve_fx3_saveload_c3_and_slot1_vault_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py#L1564-L1630) 与 [`verify_saveload_camset_c3_exclusions_and_slot1_vault_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py#L1633-L1945) 覆盖 `MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]`：
    - 支持 `Media(Slot 1)`、`Media(Slot 2)`（单卡最多 `10` 组 `CAMSET01.DAT..CAMSET10.DAT`）及 `Cloud(Private)` / `Cloud(Share)`（`Creators' Cloud / C3 Portal`，需 `ILME-FX3 Ver. 4.00+` 且完成账号关联）；
    - 严格执行 `ILME-FX3` 同机型锁，拒绝跨机型导入 `ILME-FX6`、Alpha 或异构机型的 `.DAT` 配置文件（违例阻断为 `BLOCKED_G92_CROSS_MODEL_CAMSET_INCOMPATIBLE`）。
- **Sony Help Guide 五大类排除项隐私与标定防火墙（Excluded-Items Firewall）**：
  - [`classify_saveload_excluded_items()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py#L1538-L1561) 强制拦截任何企图通过 `CAMSET*.DAT` 或 `C3 Portal` 导出或覆盖以下 5 类排除项的负载（违例阻断为 `BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_NETWORK_LEAK`）：
    1. `[IPTC Information]` 新闻元数据；
    2. `[Copyright Info]` 摄影师/版权持有人信息；
    3. `[Custom White Balance]`（`Custom 1..3` 传感器个体实测色温标定值）；
    4. `[Face Memory]` 注册人脸生物特征库；
    5. 网络凭据与安全证书（`FTP` 账号密码、`RTMP/SRT Streaming` 推流密钥、`Wi-Fi` SSID/口令、静态 IP 与根/客户端 TLS 证书）。
- **Slot-1 Tier-0 法证冷备卡只读防火墙（Vault Write Firewall）**：
  - `[Load]` 操作对存储卡保持 `O_RDONLY` 零字节写入安全；而任何指向未验证或未开启物理 `WP` 写保护锁的 Slot 1 Tier-0 冷备卡（承载 `pnflasha` / `cnflasha` 分区回读或基线 `CAMSET01.DAT`）的 `[Save]` 操作均被硬性拦截（`slot1_unverified_camset_save_blocked == True`，违例阻断为 `BLOCKED_G92_SLOT1_UNVERIFIED_TIER0_VAULT_CAMSET_SAVE`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并零错误退出。
- **架构推断（Engineering Inference）**：物理真机 Slot 1 Tier-0 冷备回读（`G10..G12`）仍按设计处于离线待命阻断状态（`89/92`），唯有人工台架提供真机 SHA-256 回读收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 241 双模式定向单测（66 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase241_shoe_audio_wind_saveload_c3_92gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `66/66 OK`（`4.282s`）+ `66/66 OK`（`2.429s`），均 `< 5s` |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2063 tests in 129.986s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2063 tests in 77.243s — OK (skipped=1)` |
| CLI `verify-92-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-92-gates`（及 `--force-clean-room`） | `verified=89/92`（`VERIFIED_89_OF_92_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-92-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-92-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=92/92`（`VERIFIED_ALL_92_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 双模式 `status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase241_shoe_audio_wind_saveload_c3_92gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/outputs/fx3-safety/tests/test_phase241_shoe_audio_wind_saveload_c3_92gate_guard.py)
6. [`reports/2026-11-15-phase241-safety-92gates-shoe-audio-wind-saveload-c3/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h268-phase241-safety-92gates-shoe-audio-4ch-wind-saveload-c3/reports/2026-11-15-phase241-safety-92gates-shoe-audio-wind-saveload-c3/README.md)
