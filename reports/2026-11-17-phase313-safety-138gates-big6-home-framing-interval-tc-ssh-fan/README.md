# Phase 313（313th Phase Milestone）：Wave-59 实机硬件安全门禁 `G137` & `G138` 与统一 `138/138` 预检引擎交付报告

- **日期**：`2026-11-17`
- **任务**：Task H371 — Phase 313: Wave-59 Hardware Safety Gates `G137` & `G138` + Unified `verify-138-gates` (`138/138`)
- **交付范围（6 个 Phase 313 核心文件 + 协调器批准的 `test_85` 前向兼容修复第 7 文件）**：
  1. 新增核心守卫模块：[`realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/fx3_safety/realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard.py)
  2. 更新包导出与 Milestone 295 自动发现入口：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/fx3_safety/__init__.py)
  3. 注册 CLI 子命令（含 `--json`、`--summary`、`--clean-room` 与 `--simulate-bench-dry-run`）：[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/fx3_safety/__main__.py)
  4. 新增文档第 69 节：[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/README.md)
  5. 新增 88 项双模式/三环境变量单元测试：[`test_realhw_big6_home_framing_interval_tc_ssh_fan_138gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/tests/test_realhw_big6_home_framing_interval_tc_ssh_fan_138gate_guard.py)
  6. 协调器批准的前向兼容修复（`test_85` 使用 `assertGreaterEqual(highest[0], 136)`）：[`test_realhw_bright_mon_shotmark_usblan_bulb_dormant_136gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/tests/test_realhw_bright_mon_shotmark_usblan_bulb_dormant_136gate_guard.py)
  7. 本工程交付报告：`reports/2026-11-17-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/README.md`

---

## 核心结论（Executive Summary）

1. **已将实验室实机安全门禁总账从 `136/136` 推进并收口至 `138/138`（Phase 313 里程碑）**：
   - 离线默认模式（[`evaluate_138gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/fx3_safety/realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard.py) / `verify-138-gates`）：**`135/138` 门禁通过**（`VERIFIED_135_OF_138_AWAITING_PHYSICAL_TIER0`，仅物理 Tier-0 备份回执 `G10..G12` 待人工台架接入），在 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC`（`FX3_FX6_FORCE_CLEAN_ROOM=1`）下均实测通过。
   - 模拟演练模式（`--simulate-bench-dry-run`）：**`138/138` 门禁全绿通过**（`VERIFIED_ALL_138_GATES_DRY_RUN_SIMULATED_BACKUP`）。
   - **Milestone 295 动态自动发现实测确认**：`make verify-milestone-295` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` 自动发现最高入口 `evaluate_138gate_preflight`，动态输出 `gate124=135/138`、`pillars=6/6`、`recovery=54/54`、`auditors=45/45`、`vm_stages=63/63`、`qemu=35/35(105/105)`、`pngs=70/70`、`leaked=0`。
2. **所有硬核安全红线保持永久锁死**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`agent_auto_flash_blocked = True`、`human_hardware_attach_token = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`physical_flash_auto_exec_authorized = False`、`cross_model_flash_authorized = False`、`usb_packets_transmitted = 0`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。
3. **全量实测通过**：
   - Phase 313 新增 **88 项单元测试**（超过 `>= 84` 要求）在 **默认 (`LOCAL_DONOR_O_RDONLY`)**、**`FX3_CLEAN_ROOM_TEST=1`**、**`FX3_FX6_FORCE_CLEAN_ROOM=1`** 三种模式下全部 `88/88 OK`（分别耗时 `7.232s` / `5.444s` / `5.446s`）。
   - `outputs/fx3-safety` 全量单元测试发现共 **3,839 项测试**（含 Phase 313 `88/88 OK` 与 Phase 310 `86/86 OK`）全部 `OK`（`173.577s`）。
   - `make clean-audit`（`scripts/run_all_lab_tests.py --clean-only`）审计 **`ALL GREEN`**（`0.04s`）。

---

## 一、实测事实 vs 推断边界（Strict Fact / Inference Separation）

| 类别 | 具体内容 | 证据来源 |
| :--- | :--- | :--- |
| **实测事实（Donor 只读 `os.O_RDONLY` + `os.pread`）** | [`audit_phase313_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/fx3_safety/realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard.py) 在 `0.004491s`（`< 0.20s` 预算）内完成 11 项本地 donor 只读核验（`raw_firmware_bytes_leaked = 0`）：`FX3 appFw.so`（`79,015,712 B`，切片 SHA-256 `15f6ea2ca04673895bbcca9c2ef1502abc46c220122179b3cb2547372806a09e`）、`FX6 appFw.so`（`50,520,424 B`，切片 SHA-256 `5cc33db45343140b910c326e4505c9576b2bbcbfb21b26a79b5ccf78bac606b3`）、FX3 四语 `_f.uxc` / `.uxc` / `_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin` 与 FX6 `string_english.uxc` / `_2.uxc` 全数哈希一致。 | [Wave-59 情报报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/reports/2026-11-17-global-sony-wave59-big6-home-framing-interval-shoot-tc-make-run-auth-intel/README.md) & [`audit_phase313_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/fx3_safety/realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard.py) |
| **实测事实（FX3 Ver. 7.02 vs FX6 Ver. 6.01 ELF/UXC 契约）** | `FX3 appFw.so` 实含 `BKID_APP_setting_fps_fixed_variable_select`、`update_big6_item_iso_ei`、`BKID_APP_setting_movie_home_lower_left`、`TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`（`AUTO_FRAMING_AFR` / `PTZAUTOFRAMING` 均 `0` 命中）、`BKID_APP_setting_interval_shooting`、`VAL_setting_tc_make_TC_MAKE_REGENRATE`（无 `TC_MAKE_CLOCK`）、`MSGID_SSHD_START_CMD` / `sshd_start`（`HTTP_DIGEST` / `BASIC_AUTH` / `HTTPS` 均 `0` 命中）、`ROOT_CERTIFICATE_TYPE_{CLOUD,FTP,RTMP}`、`FAN_CONTROL_{AUTO,MINIMUM,OFF_IN_REC,ALWAYS_OFF}`（`FX3` 与 `FX6` 中 `FAN_CONTROL_MAX` 均为 `0` 命中）。 | `FX3 appFw.so` & `FX6 appFw.so` 实测符号审计 |
| **推断（工程化安全护栏与 Slot-1 Tier-0 防火墙）** | `Slot-1` Tier-0 恢复保险库 `EROFS=30` / `EBUSY=16` 写拦截防火墙（阻断会向 Slot 1 写入最多 9,999 张 / 19,998 个 `DCIM/` 文件及持续覆写 `AVF_INFO` 的 `[Interval Shoot Func.]` 以及 Slot 1 上的 `[Import Root Certificate]`、`slot1_data_sector_writes == 0`），并在状态机中对未公开/虚构符号（`Auto Framing`、FX3 `Clock` TC、HTTP Digest/HTTPS server auth、`FAN_CONTROL_MAX`、FX6 隐藏 `Always Off`）强制 fail-closed（`EOPNOTSUPP=95`）。 | [`verify_big6_home_framing_interval_vault_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/fx3_safety/realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard.py) & [`verify_tc_make_hdmi_rec_ssh_authen_fan_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h371-phase313-safety-138gates-big6-home-framing-interval-tc-ssh-fan/outputs/fx3-safety/fx3_safety/realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard.py) |

---

## 二、Gate `G137` & `G138` 核心门禁设计摘要

### 1. Gate `G137`（`[BIG6]` Home Fixed/Variable 前置条件与纯手动 ND 元数据真相、手动 `[Framing Settings]` vs 休眠 `[Auto Framing]`、`[Interval Shoot Func.]` 9,999 张连拍 Slot-1 保险库防火墙）
- **`[BIG6]` (`HOME`) 主屏幕与手动 ND 真相**：强制 `[Mode Settings] == Fixed/Variable`（`_f.uxc 0x7d0d`、`BKID_APP_setting_fps_fixed_variable_select`）及 `Movie`/`S&Q` 作为激活前置条件；支持 `[HOME]` 自定义键或 `[Touch Operation]` 开启下的 `[Swipe Down]` 进入；精确映射 6 格动态瓷砖（`FPS`、`ISO` vs `Base ISO + EI`、`Shutter Speed/Angle`、`Aperture` vs `Home (Lower Left)` `_f.uxc 0x7ce3` 手动 `ND Filter` 元数据、`Picture Profile` vs `Select LUT`、`White Balance`），严禁 `BIG6` 输出至 HDMI，且拦截一切宣称 FX3 存在物理 e-ND 硬件的执行器请求（对比 `ILME-FX6` 真实内置 `Clear` / `1/4..1/128` / `Auto` 无级电子 ND）。
- **手动 `[Framing Settings]` vs 休眠 `[Auto Framing]`**：放行 `_f.uxc 0x7d18` 手动取景裁剪配置（`Framing Off/On`、`Recording/Streaming Full/Crop`、`HDMI Crop/Full`），校验开启时自动关闭 `APS-C S35` 并在 `>=100p`、录制中、流传输中及 `Still` 模式下锁定不可变更；对跨机型休眠的 AI `[Auto Framing]`（`_f.uxc 0x6be6/0x79bc`、`AUTO_FRAMING_AFR`、`PTZAUTOFRAMING_*`）全部 fail-closed 返回 `EOPNOTSUPP=95`（锁死 `TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`）。
- **Critical Vault Firewall（`[Interval Shoot Func.]` 9,999 张写入爆发防护）**：完整校验 `_f.uxc 0x7027` 全部 7 项可随 `Camera Settings Reset` 重置的参数（`1..9999` 张、`RAW+JPEG/HEIF` 可达 `19,998` 个 `DCIM/` 文件并高频改写 `AVF_INFO`），自动退出 `BULB` 回退 `30"` 并在 `Intelligent Auto` 下禁用；严格区分 FX3 静态序列与 FX6 机内单 `XAVC MXF` `Project > Interval Rec`；凡写入目标路由至承载 Tier-0 只读保险库的 `Slot 1`（含 `Slot 1` 单卡或 `Simult. Recording`）一律 fail-closed 拦截返回 `EROFS=30` / `EBUSY=16`（`slot1_data_sector_writes == 0`）。
- **全量枚举矩阵 `compute_big6_home_framing_interval_matrix()`**：**256 状态**（`big6_active_count=64`、`nd_metadata_only_count=128`、`framing_apsc_disabled_count=128`、`slot1_firewall_blocked_count=32`）全部不变量成立。

### 2. Gate `G138`（`[Time Code Make]` Regenerate 强锁 `Rec Run` 与 HDMI `REC Control` 状态机、Ver. 7.00+ SSH `[Access Authen.]` vs 零 HTTPS/Digest、FX3 4 档 vs FX6 3 档 `[Fan Control]` 零 Max 真相）
- **`[Time Code Make]` / `[Time Code Run]` 与 HDMI `REC Control`**：校验 `_f.uxc 0x6b79`（`Preset`/`Regenerate`，仅 `[Initialize]` 重置；拒绝 FX6 专属 `Clock` 模式），强制 `Regenerate` 时无论设定如何均按 `Rec Run` 运行（在 `Simult. Recording` 下确定性继承 `Slot 1` 末段 TC），而 `VMC-BNCM1` `EXT-LK` 严格要求 `Preset + Free Run`；校验 HDMI `[REC Control]`（`_f.uxc 0x76e1`）前置依赖 `[Time Code Output] == On`（`_f.uxc 0x72af`），在 `[Rec. Media dur HDMI Output]` 为 `On` 与 `Off(HDMI Only)` 下均有效，但在 `Still`、`S&Q` 与流传输下受限；同步校验 `[4ch Audio Output]`（`_f.uxc 0x6aa0`: `CH1/CH2` vs `CH3/CH4`）与 FX6 `SDI/HDMI Remote I/F` / `Parallel Rec`（跟随 Slot A）。
- **Ver. 7.00+ SSH `[Access Authen.]` vs 零 HTTPS/Digest**：验证默认开启的 `[Access Authen. Settings]`（仅随 `Reset Network Set.` / `Initialize` 重置，不受 `Camera Settings Reset` 清除；强校验 `WPA2-PSK`/`WPA3-SAE`，拒绝 Ver. 7.00 已移除的 `IPsec`/`WEP`/`WPA-PSK`）走 **SSH（`MSGID_SSHD_START_CMD` / `sshd_start` / `_g.uxc 0x610b` Fingerprint）+ PTP-IP** 链路，拒绝一切不存在的 `HTTP_DIGEST` / `BASIC_AUTH` / `HTTPS` 服务端鉴权幻觉；校验 `[Import Root Certificate]`（`_f.uxc 0x7940`）仅用于 `Cloud` / `FTPS` / `RTMPS` 出站客户端 TLS 校验证书，且严禁向含 Tier-0 保险库的 Slot 1 执行写入性证书操作。
- **FX3 4 档 vs FX6 3 档 `[Fan Control]` 零 `Max` 纠偏**：强制校验 FX3 仅暴露 `Auto` / `Minimum` / `Off in Rec` / `Always Off`（4 档，仅 `Initialize` 重置，`Off in Rec` 过温自动恢复；联动 `[Auto Power OFF Temp.]` `Standard`/`High` 及低温烫伤/三脚架警示），FX6 `Technical > Fan Control` 仅暴露 `Auto` / `Minimum` / `Off in Rec`（3 档，`Always Off` 为休眠未暴露符号）；在两台机身上统一拦截不存在的 `FAN_CONTROL_MAX`（0 命中 -> `EOPNOTSUPP=95`）。
- **全量枚举矩阵 `compute_tc_make_ssh_authen_fan_matrix()`**：**256 状态**（`tc_regen_forced_rec_count=128`、`cardless_hdmi_rec_ctrl_count=64`、`sshd_active_count=128`、`fan_temp_override_count=32`）全部不变量成立。

---

## 三、端到端实测验证日志

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| **Phase 313 单元测试（Donor 只读模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_big6_home_framing_interval_tc_ssh_fan_138gate_guard.py` | **88/88 OK** (`7.232s`) |
| **Phase 313 单元测试（`FX3_CLEAN_ROOM_TEST=1`）** | `FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_big6_home_framing_interval_tc_ssh_fan_138gate_guard.py` | **88/88 OK** (`5.444s`) |
| **Phase 313 单元测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`）** | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_big6_home_framing_interval_tc_ssh_fan_138gate_guard.py` | **88/88 OK** (`5.446s`) |
| **Phase 310 兼容回归单元测试（`test_85` 前向兼容）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_bright_mon_shotmark_usblan_bulb_dormant_136gate_guard.py` | **86/86 OK** (`10.584s`) |
| **`verify-138-gates` 离线 & Dry-Run（Donor 模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-138-gates [--simulate-bench-dry-run] --summary --json` | 离线 **`135/138`**（`VERIFIED_135_OF_138_AWAITING_PHYSICAL_TIER0`）；Dry-Run **`138/138`**（`VERIFIED_ALL_138_GATES_DRY_RUN_SIMULATED_BACKUP`），`raw_firmware_bytes_leaked=0` |
| **`verify-138-gates` 离线 & Dry-Run（`FX3_FX6_FORCE_CLEAN_ROOM=1`）** | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-138-gates [--simulate-bench-dry-run] --summary --json` | 离线 **`135/138`**；Dry-Run **`138/138`**，`verification_mode=CLEAN_ROOM_SYNTHETIC`，`raw_firmware_bytes_leaked=0` |
| **`outputs/fx3-safety` 全量单元测试发现** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests` | **3,839/3,839 OK** (`173.577s`) |
| **Milestone 295 主控联合门禁（Donor + Clean-Room）** | `make verify-milestone-295` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` | **ALL OK**：动态自动发现 `evaluate_138gate_preflight`，`gate124=135/138`、`pillars=6/6`、`recovery=54/54`、`auditors=45/45`、`vm_stages=63/63`、`qemu=35/35(105/105)`、`pngs=70/70`、`leaked=0` |
| **Clean-Room 卫生审计** | `make clean-audit` (`scripts/run_all_lab_tests.py --clean-only`) | **`ALL GREEN`** (`0.04s`) |
