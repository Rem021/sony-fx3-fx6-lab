# Phase 178（VM Stage 31 / `31/31`）：Sony SCEL `ssboot` / `WBI2` 引导防火墙、100 轮拔电池恢复与 Slot-1 `BODYDATA.DAT`（`>=2.04`）/ C2PA 100-License HIL 协同仿真报告

## 结论先行

在 `outputs/fx3-vm/` 中已落地并接通 **Stage 31（`31/31`）：[`realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py)**，并接入全板协同仿真总入口 [`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/fx3_vm_coemulation_suite.py)（含 `--skip-phase178` 开关）。

- **Stage 31 单阶段耗时与摘要**：
  - 本地只读供体模式（`LOCAL_DONOR_RDONLY`）：`wbi_wr=0 | cycles=100/100 | drift=0 | ufu_bypass_us=38.5 | emmc_wr=0 | digest=9e58d4324bfc`
  - 洁净室合成模式（`CLEAN_ROOM_SYNTHETIC`）：`wbi_wr=0 | cycles=100/100 | drift=0 | ufu_bypass_us=38.5 | emmc_wr=0 | digest=1d14c9e50f1f`
- **31/31 全板协同仿真总耗时**：进程内 Clean-Room **`0.457s`**（CLI `--json` `0.761s < 0.8s`）；进程内 Local-Donor **`1.991s`**（CLI `--json` `2.290s`，Stage 31 自身增量 `< 0.01s`）。
- **单测与全仓清洁校验**：
  - Stage 31 新增 [`test_realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/tests/test_realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py) 共 **48 项双模测试**（要求 `>= 46`）：本地模式 `5.397s` / 洁净室模式 `3.705s` 全部通过。
  - `outputs/fx3-vm/tests` 全量 **1,132 项单测**：本地模式 `79.417s` 全部通过（`OK`）；洁净室模式 `74.815s` 全部通过（`OK (skipped=3)`）。
  - 全仓干净态校验 `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`：`CLEAN (0.05s)`。

---

## 核心交付与技术闭环（Pillars A–D）

| 域 | 核心验证内容 | 实测结论 | 代码锚点 |
| :--- | :--- | :--- | :--- |
| **双模只读供体审计** | 严格 `os.O_RDONLY` 有界读取（`<= 4096 B` 读取 WBI2 与 `811 MiB` UFU 头）+ 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退 | `9` 份供体全过：`FX3 nflasha5` (`209,112,512 B`, `WBI2`, `1,399` 节) vs `FX6` (`202,677,056 B`, `1,197` 节)；`liro.ko` (`121,488 B` 体机专用哈希)；`vmlinux.bin` (`6,610,952 B`, `4.9.337-scel+`)；`FX3 7.02 BODYDATA.DAT` (`811,876,768 B`, `054c:0da1`) vs `FX6` (`847,081,840 B`, `054c:0d21`)；`im.elf` (`40,920 B`, `11/85` 零差异 ABI)；`raw_firmware_bytes_leaked == 0` | [`inspect_phase178_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py#L977-L1098) |
| **Pillar A: SCEL `ssboot` / `WBI2` 防火墙** | `WBI2\x00\x00\x00\x00` (`57 42 49 32`) LZO `prsv-img` 暖启动陷阱 vs Stage-A 冷启动 (`/sbin/init -> fx6-stage-a-verify`) | 未捕获 `WBI2` 陷阱在双启动激活前被拦截；Stage-B 锁定 `/dev/nflasha5` 与 `/dev/pnflasha5` `BLKROSET=1` 并屏蔽 `PM_SUSPEND_DISK` + `/proc/udm`（`wbi_persistent_writes == 0`）；`EH1` 拔卡旁路 `38.5 us < 50 us` 与干净卸载 `H2 -> H3` 保留 Stock FX3 `0.5s` 热启动及 `nflasha5` `H0 == H3` | [`evaluate_pillar_a_ssboot_wbi2_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py#L1239-L1300) |
| **Pillar B: 100 轮 `NP-FZ100` 骤断与跌压 HIL** | 100 轮 Stock <-> Stage-B 切换（菜单中拔电池、录制中 `6.3V` `EncWfiStop` exFAT `.RSV -> .MXF` 抢救、`EH2` `DISP+MENU+SHUTTER`、`EH3` 1 字节 `libJit.so` CRC32 fail-closed） | `100/100` 通过；`p1`、`p2:/setting`、`p5:/wbi`、`p12:/cert`、`p15:/usr`、`p18:/lens` 6 大受保护分区 `journal_metadata_drift_count == 0`、`rsv_orphan_count == 0`、`emmc_nflasha_write_count == 0` | [`run_100cycle_powerloss_and_brownout_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py#L1410-L1495) |
| **Pillar C: `Ver. 7.02` `BODYDATA.DAT` `>=2.04` & Slot-1 C2PA** | `<= Ver. 2.02` 拒绝（防 `7L+7S` LED 故障）、Slot-1 根目录唯一放置（禁 `BODYDATA (1).DAT` 与 Slot 2）、`\x89UFU` `<100 us` 旁路、Slot-1 `<=100` C2PA 许可 + `p12:/cert/RQ_LIC.DAT` `EROFS` 锁、`WPA2/WPA3`-only 门禁 | `7.02`/`2.04` 放行（`38.5 us < 100 us`）；`2.02` 触发 `BLOCKED_FX3_FW_BELOW_2_04_FLOOR_7L_7S`；`101` 许可、`WEP`/`WPA1`/`IPsec` 与任何 `RQ_LIC.DAT` 写请求 100% fail-closed 拦截 | [`evaluate_pillar_c_slot1_bodydata_c2pa_wifi`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py#L1727-L1783) |
| **Pillar D: 硬安全红线** | eMMC / SPI-NOR / EL3 / 物理 USB / OTP / RPMB 全维度探针 | `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0` | [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py#L1790-L1838) |

---

## 受控修改文件清单

1. [`outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py)（新增 Stage 31 核心模块）
2. [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/fx3_vm_coemulation_suite.py)（接入 `stage31_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil` 与 `--skip-phase178`）
3. [`outputs/fx3-vm/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/README.md)（补充 Phase 178 Stage 31 文档与 CLI 命令）
4. [`outputs/fx3-vm/tests/test_realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/tests/test_realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py)（新增 48 项双模单测）
5. [`outputs/fx3-vm/tests/test_realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/outputs/fx3-vm/tests/test_realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py)（仅放宽 Stage 30 总阶段数断言 `30 -> >=30`）
6. [`reports/2026-11-15-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu-hil/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h193-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu/reports/2026-11-15-phase178-vm-stage31-ssboot-wbi2-powerloss-slot1-ufu-hil/README.md)（本报告）

---

## 实测事实 vs 未执行物理真机实操边界

- **已验证事实（主机离线 HIL 与 `O_RDONLY` 供体校验）**：
  - 上述所有指标均来自主机 Python + Unicorn 协同仿真、`os.O_RDONLY` 本地只读供体头部/ELF 校验及 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室合成回退实测。
  - 全仓无 `.pyc` 缓存或专有索尼二进制文件进入 Git 跟踪。
- **未执行物理相机台架操作（BLOCKED / NO-GO 红线保持）**：
  - 本任务未连接真实物理 ILME-FX3 相机，未对物理相机执行任何 eMMC/SPI-NOR 刷写、USB/SD 烧录、EL3 载荷发送、OTP 熔丝操作或物理电池拔插；真机红线始终锁定在安全关断状态。
