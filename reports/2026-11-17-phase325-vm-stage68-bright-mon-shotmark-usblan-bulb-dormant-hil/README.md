# Phase 325 Engineering Closure Report — VM HIL Stage 68 (`68/68` Milestone: Wave-58 自定义键 `[Bright Monitoring]` Ver. 7.00+ 放大共存 & `[Monitor Brightness]`、`[Shot Mark 1/2]` / `[Clip Flag]` vs 休眠 `[Divide]`/`[Extract]` & `Slot-1` `EROFS=30` Vault、零蓝牙 `[Timecode Link]` vs `VMC-BNCM1` & `WPA2/WPA3` / `USB-LAN` 互斥，以及 Still `[BULB]` 机械快门与休眠 `[Bulb Timer]` / `[Auto HDR]` HIL)

- **日期**：`2026-11-17`
- **任务 / 分支**：`H390`（`task_edd1fe46614f`） · `codex/h390-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil`
- **硬件安全红线**：`physical_device_writes = 0`、`persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`overall_ready_for_hardware_attach = False`、`rf_packets_transmitted = 0`、`slot1_data_sector_writes = 0`、`slot1_avf_info_mutated = False`、`raw_firmware_bytes_leaked = 0`

---

## 核心结论速览（Conclusion First）

1. **Stage 68（`68/68` 里程碑）已完成实现、全板接入与双模/三模校验**：
   - 新增 [`realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h390-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil/outputs/fx3-vm/realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py)（Schema `realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator_v1`）及其 `92` 项三模式单测 [`test_realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h390-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil/outputs/fx3-vm/tests/test_realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py)，并接入 [`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h390-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py) 作为 `stage68_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil`；
   - `make verify-milestone-311`（含 `FX3_FX6_FORCE_CLEAN_ROOM=1`）与 `make verify-milestone-295` 均自动发现 **`vm_stages=68/68`** 且 **`leaked=0`**，`make clean-audit` 报告 `ALL GREEN`。
2. **28 份真实供体 `os.O_RDONLY` 受界审计与 `work_root is None` 洁净室对等回退**：
   - **`实测事实`**：通过受界 `os.O_RDONLY`（`<= 4096 B` 窗口）完成对 Wave-58 全部 **28 份真实供体**（`14` 份 UXC 四语/英文包 + `7` 份网络/蓝牙/飞行模式 `.so` + `4` 份 `USB-LAN` 内核模块 `.ko` + `FX3 appFw.so` `79,015,712 B`、`FX3 BK4` `2,229,740 B`、`FX6 appFw.so` `50,520,424 B`）的精确字节与 SHA-256 锚定审计，并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 及无供体 CI（`work_root is None`）下对等切换至 `CLEAN_ROOM_SYNTHETIC`（`raw_firmware_bytes_leaked = 0`）。
3. **Wave-58 四大实机子系统工程闭环（严格区分 `实测事实` vs `推断`）**：
   - **68A 自定义键 `[Bright Monitoring]`（Ver. 7.00+ 对焦放大共存）& `[Monitor Brightness]` vs `FX6`**：
     - **`实测事实`**：FX3 `[Bright Monitoring]`（`_f 0x701f`，`BRIGHT_MONITORING_STATE_{ON,OFF}`）不在拍摄菜单暴露开关（仅由 `[Custom Key/Dial Set.]` 触发，来自拍摄菜单 fail-closed 返回 `EOPNOTSUPP=95`）；开启期间强制 `[Live View Display] -> [Setting Effect OFF]`，并在关机、切出 `P/A/S/M` 或从 `MF` 切回 `AF` 时自动取消；**`Ver. 7.00 / 7.02` 明确允许激活期间同时使用 `[Focus Magnifier]` 与 `[Auto Magnifier in MF]`**（`Ver. 6.01` 互斥拒绝）。`[Monitor Brightness]`（`base 0xe44b`，`Initialize`-only 抗 `[Camera Settings Reset]`）仅暴露 `Manual (-2..+2)` 与 `Sunny Weather`（`0xe1da`），对休眠 `Auto` / `LCD_BRIGHTNESS_AUTO` 返回 `EOPNOTSUPP=95`。对比 `ILME-FX6`（`Monitoring > VF Setting > Brightness 1..15` 默认 `8` + `Color/B&W`，`Shooting > Auto Exposure > Mode > Backlight` 为 AE 逆光补偿，而 `LCD/VF Backlight` 与 `NIGHTSHOT_*` 均休眠拒绝）。
     - **`推断`**：FX3 在 `4K` 录制下无消费级无风扇机型的强制降亮锁定，仅提示 `Sunny Weather` 高功耗与室内过亮；Clean-HDMI 输出流不随机背 Bright Monitoring 增益改变。
   - **68B `[Shot Mark 1/2]` / `[Clip Flag]` vs 零机内 `[Divide]`/`[Extract]` & `Slot-1` `EROFS=30` Vault 防火墙**：
     - **`实测事实`**：FX3 活跃支持录制 `[Add Shot Mark1/2]`（`_f 0x628b/0x628a`）、回放 `[Add/Delete Shot Mark1/2]`（`_f 0x6143/0x6142`）、12 项 `[Image Jump Setting]`、`[Clip Flag]`（`OK/NG/KEEP`）、`[Photo Capture]`（`JPEG/HEIF_420/HEIF_422`）及 `[Create Divider Frame]`；机内 `[Divide]` / `[Extract]` 在 `FX3/FX6 appFw.so` 与 `ilc/2210` 均 `0` 命中，`_f.uxc` 中 `Cut to 15/30/60 seconds`（`0x7005/0x6e38/0x6c2a`）无活跃状态机，一律 fail-closed 返回 `EOPNOTSUPP=95`；`FX6` 仅激活 `Thumbnail > Clip Flag`，CBM 退役遗留的 `Shot Mark 0..9` / `Essence Mark` 均按休眠拒绝。
     - **`推断`**：`Shot Mark 1/2` 增删与 `Clip Flag` 编辑均会就地重写 `M4ROOT/CLIP/*M01.XML` 侧车与 `AVF_INFO` 索引，`Photo Capture` / `Create Divider Frame` 会写入 `DCIM/` 与 `AVF_INFO`；因此台架 **`Slot-1` Tier-0 Vault 防火墙**对所有写卡类操作强制 fail-closed 拦截并返回 `EROFS=30`（忙碌时 `EBUSY=16`），确保 `slot1_data_sector_writes = 0` 且 `slot1_avf_info_mutated = False`。
   - **68C 零蓝牙 `[Timecode Link]` vs 有线 `VMC-BNCM1`、`WPA2/WPA3` Wi-Fi、`BT 5.0` & `USB-LAN` 互斥**：
     - **`实测事实`**：`FX3 appFw.so` 不含蓝牙 `[Timecode Link]` / `UltraSync BLUE`（`0` 命中，按 `EOPNOTSUPP=95` 拒绝），仅支持 Multi/Micro USB + `VMC-BNCM1` 有线外接 LTC（需 `Preset + Free Run` 方可锁定 `EXT-LK`）；Ver. 7.00+ 已彻底移除 `WEP` / `WPA-PSK` / `Security(IPsec)`，仅允许 `WPA2-PSK` / `WPA3-SAE`；`WW728473` 支持 `2.4/5GHz`（5GHz 限室内）而 `WW558244` 仅限 `2.4GHz`；`Bluetooth 5.0` 受限 `15` 配对 / `2` 并发 / `1` BT 遥控；`USB-LAN`（`cdc_ncm.ko` / `r8152.ko` / `ax88179_178a.ko` / `asix.ko` 与 `[USB-LAN Cnct. Launch]` 默认 `Off`）激活时禁用 Wi-Fi 且与 Multi/Micro USB（如 `VMC-BNCM1`）并发互斥返回 `EBUSY=16`；`FX6` 具备物理 `TC IN/OUT` BNC 拨动开关但无蓝牙硬件、无 `USB Timecode`。
     - **`推断`**：`[Airplane Mode]=On` 经实测在 `[Reset Network Set.]` 与 `[Initialize]` 后均持久保留 `On`；台架零射频防火墙据此锁死 `rf_packets_transmitted = 0`，仅允许有线 `USB-LAN eth0` 受控通信。
   - **68D Still `[BULB]` 机械快门约束 & `[DRO]` / `[DRO Bracket]` vs 休眠 `[Bulb Timer]` & `[Auto HDR]`**：
     - **`实测事实`**：尽管 `FX3 appFw.so` 与 `_f.uxc` 存在多机型共享沉底符号（`BKID_APP_setting_bulb_timer` / `0x630f` 与 `base 0xe49d` `Auto HDR`），但 `ilc/2210` 全站与 Ver. 7.00/7.02 说明 `0` 命中，且 `[Auto HDR]` 已被 `[HLG Still Image]` 替代，故两者均 fail-closed 返回 `EOPNOTSUPP=95`。Still `[BULB]` 要求 `Still + Manual Exposure (M) + Mechanical Shutter`，在 `Electronic Shutter`、`Cont. Shooting`、`Self-timer(Cont)`、`Cont. Bracket`、`Interval Shooting` 或非 `M` 模式下按 `EOPNOTSUPP=95` 拒绝并回退至 `30"`（`BULB` 下禁用 `[Anti-flicker Shoot.]`，`Long Exposure NR = On` 追加暗帧）。`[D-Range Optimizer]`（`Auto/Off/Lv1..Lv5`）在 `Picture Profile != Off` 或 `HLG Still Image = On` 时强制固定 `Off` 并禁用 `[DRO Bracket]`。
     - **`推断`**：`FX6 Ver. 6.01` 无机械快门与 Still `[BULB]`/`[DRO]` 流水线，相关请求统一按 `EOPNOTSUPP=95` 隔离，避免跨机模式混淆。

---

## 交付物与验证矩阵

| 交付文件（严格域隔离 5/5） | 职责与核心结果 |
| :--- | :--- |
| [`realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h390-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil/outputs/fx3-vm/realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py) | Stage 68（Phase 325）主协同仿真器 + 28 供体 `os.O_RDONLY`（`<=4096 B`）与 `work_root is None` 洁净室回退 |
| [`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h390-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 接入 `stage68_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil`（支持 `--include-stage68` / `--skip-stage68` / `--no-include-stage68` / `--skip-phase325`） |
| [`test_realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h390-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil/outputs/fx3-vm/tests/test_realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py) | 92 项三模式单测（覆盖 28 供体、`Bright Monitoring` 放大共存与自动取消、`Slot-1 EROFS=30`、零 BT `Timecode Link`、`USB-LAN` 互斥、`BULB` 机械快门与 Suite 篡改检测） |
| [`outputs/fx3-vm/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h390-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil/outputs/fx3-vm/README.md) | 追加 Stage 68（`68/68`）架构说明与三模式 CLI/测试命令 |
| [`reports/.../README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h390-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil/reports/2026-11-17-phase325-vm-stage68-bright-mon-shotmark-usblan-bulb-dormant-hil/README.md) | 本工程结案报告（结论先行，严格区分 `实测事实` 与 `推断`） |

### 实测验证记录

| 验证项 | 模式 / 命令 | 实测结果 |
| :--- | :--- | :--- |
| Stage 68 独立三模式自检 | `realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py --self-test`（默认 / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | 均通过（`donors=28`, `leak=0`, `rf=0`, `s1_wr=0`, `emmc_wr=0`） |
| Stage 68 单元测试 | `unittest test_realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py -v`（3 模式） | `92/92 OK`（3 模式全部 `0` 失败/`0` 错误） |
| 全板 68 阶段 Suite CLI | `fx3_vm_coemulation_suite.py --summary`（`LOCAL_DONOR_O_RDONLY` & `FX3_FX6_FORCE_CLEAN_ROOM=1`） | 均 `PASS`（`m68=68/68`, `bm_menu=0`, `div_byp=0`, `bt_tc=0`, `usblan=0`, `bulb=0`, `rf_tx=0`, `s1_wr=0`, `emmc_wr=0`） |
| `outputs/fx3-vm` 全量发现 | `unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'`（双模） | 默认供体模式 `3631/3631 OK`（`200.10s`，`0` 失败/`0` 错误）；`FX3_FX6_FORCE_CLEAN_ROOM=1` `3631` 项通过（`176.83s`，`skipped=5`，`0` 失败/`0` 错误） |
| Master Gate 里程碑校验 | `make verify-milestone-311`、`FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-311`、`make verify-milestone-295` | 全部 `status=OK`，`vm_stages=68/68`，`leaked=0` |
| 工作区卫生审计 | `make clean-audit` | `ALL GREEN`（`0.04s`） |
