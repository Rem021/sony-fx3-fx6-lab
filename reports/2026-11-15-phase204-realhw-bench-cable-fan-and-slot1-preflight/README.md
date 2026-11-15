# Phase 204（`preflight-bench-cable-fan-slot1`）— 真实物理 `ILME-FX3` 台架前供电/线束（`DC-C1` / `NP-FZ100` / `VMC-BNCM1`）、4 档风扇热控（`Always Off` 阻断）与卡槽 1 `CAMSET`/`.cube` 保险库就绪校验器交付报告

## 结论先行

已在 [`outputs/fx6-on-fx3-closure/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/README.md) 主干轨道完成 **Phase 204（[`realhw_bench_cable_fan_and_slot1_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_cable_fan_and_slot1_verifier.py) / CLI 子命令 `preflight-bench-cable-fan-slot1`）** 研发、双模式（`LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC`）验证与全套回归检查：

- **交付状态**：`54/54` 项双模式单元测试（`< 0.03s`，远低于 `6.0s` 上限）全部通过；既有 `preflight-card-insert`（Phase 186）、`verify-milestone-175`（Phase 175）与 `verify-milestone-193`（Phase 193）保持 100% 绿灯兼容；[`scripts/run_all_lab_tests.py --clean-only`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/scripts/run_all_lab_tests.py) 零 `.pyc` / 零专有固件泄漏通过。
- **硬锁安全不变量（实测硬编码）**：`hardware_live_attachment_authorized = False`（无条件恒为 `False`）、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。
- **离线与模拟双态门禁**：默认离线无双盘 `528 B FX3RCPT1` 凭证时严格阻断为 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`；开启 `--simulate-ready-bench` 时输出 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（且 `hardware_live_attachment_authorized == False` 保持不变）。

---

## 核心架构与三大台架前校验组（Waves 24–26 实机情报闭环）

参考情报基线：
- [Wave 25 报告（4 档风扇 PWM、`Off in Rec` 待机 `100% MAX PWM`、快门角度独立槽位、`6.01` vs `7.02` LUT 二进制代差）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/reports/2026-11-15-global-sony-wave25-fan-pwm-offinrec-shutter-angle-lut-601-vs-702-binary-split-intel/README.md)
- [Wave 26 报告（`BIG6` 零物理电子 ND、`CAMSET` 卡槽 1 路径不对称与跨机型防火墙、`VMC-BNCM1` 机身 `TC IN` 单向契约）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/reports/2026-11-15-global-sony-wave26-big6-home-aperture-nd-camset-slot1-path-vmcbncm1-tcin-only-intel/README.md)

### 1. [`evaluate_check_group_1_power_cable_harness`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_cable_fan_and_slot1_verifier.py#L973-L1228)（`B1_POWER_CABLE_AND_VMC_BNCM1_HARNESS`）
- **供电矩阵**：
  - `USB_PD_BODY`：强制机身插入原厂 `NP-FZ100` 且电量 `>= 51.0%`（电压 `7.20V..8.50V`），阻断无电池直插 USB-C PD、`< 51%` 欠电或 `> 8.50V` D-Tap 假电池过压风险。
  - `DC_C1_COUPLER`：强制 `>= 65.0W` USB-PD 电源与 `5.0A` e-Marked 线缆，严拒 `< 65W` 充电器及 `3A` 非 e-Marked 线缆；严拒 `Micro-USB` 主供电。
- **No-UVC 防火墙**：在 `ILME-FX3`（`0x91030080`，`Ver. 7.02`）上严拒 `[USB Streaming]` / `UVC` 模式预期，允许 `RTMP` / `RTMPS` / `SRT` 网络推流与 Type-A HDMI 采集。
- **`VMC-BNCM1`（`A-5051-506-A`）线束锁**：强制仅接机身 `Multi/Micro USB`（严拒插入 `XLR-H1` 手柄侧面 Micro-USB 口），强制单向 `TC_IN`（严拒反向 BNC `TC_OUT`，并在 `S&Q` 模式下阻断 HDMI `TC OUT`），校验 `Movie + Preset + Free Run`（`EXT-LK` 约 `10s` 锁定）及 Multi-USB `Pin 8/9/10` 与 `1.8V` 被动 UART RX 的互斥锁。

### 2. [`evaluate_check_group_2_fan_thermal_and_big6`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_cable_fan_and_slot1_verifier.py#L1233-L1442)（`B2_FOUR_MODE_FAN_THERMAL_AND_BIG6_NO_END_GATE`）
- **4 档 `[Fan Control]` 与冷备热阻断**：严格限定 `Auto` / `Minimum` / `Off in Rec` / `Always Off` 四档，显式拒绝虚构的广播机/Lumix `Auto1` / `Auto2` 档位；在执行 75 MiB `p3` `AdjustControl (0x40)` 冷备份或 Stage-B 预演前，若处于 `Always Off` 立即阻断并强制切回 `Auto`（同时校验 `[Auto Power OFF Temp.] = Standard / High` 且机身起始温度 `< 45.0°C`）。
- **`Off in Rec` PWM 物理模型**（[`model_fx3_702_fan_pwm_profile`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_cable_fan_and_slot1_verifier.py#L755-L785)）：建模待机非录制 `100% MAX PWM` 主动排热、常规录制（`< 78.0°C`）`0% PWM` 静音、以及 `>= 78.0°C` 紧急强制 `100% PWM` 保护。
- **`BIG6` 6 宫格与零物理 e-ND 校验**：校验 `[Mode Settings] = Fixed/Variable`、快门 `Speed`（`0x01120024`）与 `Angle`（`0x01120028`）双独立槽位（常规 `5.6°..64F` vs `119.88p/100p` 及 `S&Q` 下 `5.6°..360°` 上限）、`[Home (Lower Left)]`（`Aperture` / 纯软件 `ND Filter`），并硬锁 `e_nd_actuator_tx_count == 0`。

### 3. [`evaluate_check_group_3_slot1_lut_camset_vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_cable_fan_and_slot1_verifier.py#L1490-L1854)（`B3_SLOT1_CUBE_LUT_AND_CAMSET_VAULT_READINESS`）
- **卡槽 1 双介质路径不对称校验**：
  - `SDXC`：`/Private/Sony/PRO/LUT/` 与 `/PRIVATE/SONY/SETTING/FX3/CAMSET/`
  - `CFEXPRESS_A`（省略 `/Private`）：`/Sony/PRO/LUT/` 与 `/SONY/SETTING/FX3/CAMSET/`
- **`CAMSET01..10.DAT` 与跨机型防火墙**：强制仅限 **Slot 1**（拒绝 Slot 2）、非 `MR`（`Recall Camera Setting`）曝光模式、单卡 `<= 10` 个唯一 `CAMSET01..10.DAT` 文件，并严拒 `ILME-FX3` / `ILME-FX3A` / `ILME-FX6` 跨机型 `.DAT` 混入。
- **`6.01` vs `7.02` User LUT 二进制代差沙箱**：校验 `.cube`（`17^3`/`33^3`、`<= 63B` ASCII、`User1..User16`、`0..+2.0EV`），强制 Stage-B LUT 与 CAMSET 隔离至易失性 `/tmp/fx6_lut_overlay` 与 `/tmp/fx6_camset_overlay`（`p2:/setting` 写入 `== 0`、`16/16` 存储面 `SHA256(H0) == SHA256(H3)`），并绑定双物理设备（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` Tier-0 凭证与 `slot1_dir` `O_RDONLY` 卫生扫描。

---

## 修改/新增文件清单（严格限定 6 个自有文件）

1. [realhw_bench_cable_fan_and_slot1_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_cable_fan_and_slot1_verifier.py)（新增：Phase 204 主校验器、`O_RDONLY` 有界 donor 探针、报告防篡改校验器与 Markdown 渲染器）
2. [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（更新：导出全部 Phase 204 常量、错误码、数据类与入口函数）
3. [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（更新：接入 `preflight-bench-cable-fan-slot1`，支持 `--force-clean-room`、`--simulate-ready-bench`、`--json` 等参数）
4. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/README.md)（更新：增补 Phase 204 模块说明与 CLI 命令 `# 37`）
5. [test_realhw_bench_cable_fan_and_slot1_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/outputs/fx6-on-fx3-closure/tests/test_realhw_bench_cable_fan_and_slot1_verifier.py)（新增：`54` 项双模式单元测试，含 `< 6.0s` 墙钟上限断言）
6. [README.md（本报告）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h224-phase204-preflight-bench-cable-fan-and-slot1/reports/2026-11-15-phase204-realhw-bench-cable-fan-and-slot1-preflight/README.md)

---

## 实测验证结果（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 执行命令 | 实测结果 |
|---|---|---|
| CLI 模拟就绪 JSON 输出 | `PYTHONPATH=... /usr/bin/python3 -B -m fx6_closure preflight-bench-cable-fan-slot1 --simulate-ready-bench --json \| head -n 35` | `go_no_go=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`, `groups=3/3`, `H0==H3=16/16`, `e_nd_tx=0`, `donor_elapsed=0.000575s (<0.15s)` |
| Phase 204 单元测试（本地 Donor `O_RDONLY`） | `PYTHONPATH=... /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_bench_cable_fan_and_slot1_verifier.py` | **54/54 PASS**（`0.028s`） |
| Phase 204 单元测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_bench_cable_fan_and_slot1_verifier.py` | **54/54 PASS**（`0.023s`） |
| 向后兼容性回归（Phases 175 / 186 / 193） | `preflight-card-insert --dry-run-simulated`、`verify-milestone-175`、`verify-milestone-193` | **100% GREEN**（SHA-256 与门禁计数零漂移） |
| 全仓洁净室与字节码卫生审计 | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | **ALL GREEN**（`0.05s`，零 `.pyc` / 零专有二进制污染） |
