# Phase 157（VM Stage 27，`27/27`）：真机 `IMX510` 双原生 ISO `800/12800`、`psd.bin`/`defdet.bin` 传感器 NVS、`.cube` 3D MLUT、`CDC-NCM` USB-LAN `Monitor & Control` 与 `054C:0DA1` 恢复口 HIL 联合仿真报告

- **任务编号**：`H169 / Phase 157 (VM Stage 27, 27/27)`
- **目标主线**：物理 ILME-FX3（`7.02` `4.9.337-scel+` 内核 + 原厂 `cpapp-b.bin`）Hybrid Userland Stage-B 全链路成像 + 通信 + USB `054C:0DA1` 恢复口保全 HIL 联合仿真
- **双模式摘要**：
  - `LOCAL_DONOR_RDONLY`：Stage 27 单阶段 `audit_digest_sha256[:12] = 29b3a0af902b`；27/27 全套联合仿真 `digest = d9d3cb7c0a01`（耗时 `2.09 s < 2.4 s`）。
  - `CLEAN_ROOM_SYNTHETIC`（`FX3_FX6_FORCE_CLEAN_ROOM=1`）：Stage 27 单阶段 `audit_digest_sha256[:12] = 459da1bddbb1`；27/27 全套联合仿真 `digest = 9b616abaeab9`（耗时 `0.72 s < 1.0 s`）。
- **安全红线**：`p8_cp_mutation_forbidden = True`、`sensor_cal_mutation_bytes = 0`、`rf_nvs_p12_p13_mutation_bytes = 0`、`slog3_master_double_baked = False`、`bt_hci_blocking_wait_ms = 0`、`bt_hci_blocking_wait_eliminated = True`、`usb_msc_0da1_recovery_intact = True`、`persistent_emmc_writes_authorized = False`、`emmc_nflasha_write_count = 0`。

## 1. 修改与交付文件清单（严格限定 5 个 Owned Files）

| 序号 | 文件 | 职责 |
| :--- | :--- | :--- |
| 1 | [realhw_imx510_color_and_network_usb_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/realhw_imx510_color_and_network_usb_coemulator.py) | Phase 157 Stage 27 独立联合仿真模块（16 个 FX3/FX6 `O_RDONLY` Donor 审计 + 四大 HIL 支柱 A–D + Clean-Room 合成回退） |
| 2 | [fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py#L1594-L1643) | 接入 [`run_stage27_realhw_imx510_network_usb_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py#L1594-L1643) 与 `--skip-phase157`，推进全套联合仿真至 `27/27` |
| 3 | [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/README.md#L900-L934) | 更新 `outputs/fx3-vm/` Phase 157（Stage 27）CLI 命令与红线说明 |
| 4 | [test_realhw_imx510_color_and_network_usb_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/tests/test_realhw_imx510_color_and_network_usb_coemulator.py) | 46 项双模式（Local Donor / Clean-Room）单元测试（涵盖 Stage 27 模块与 27-Stage 套件总控） |
| 5 | [Phase 157 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/reports/2026-11-15-phase157-vm-stage27-realhw-imx510-network-usb-hil/README.md) | 本期结项报告 |

## 2. 实测事实与未执行真机边界（严格区分）

### 2.1 `O_RDONLY` 本地 Donor 实测与 Python HIL 联合仿真事实

通过 [`inspect_phase157_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/realhw_imx510_color_and_network_usb_coemulator.py#L917) 严格经 `os.open(..., os.O_RDONLY)` + `mmap.ACCESS_READ` 对 16 份 FX3 `7.02` 与 FX6 `6.01` 本地 BYOF 镜像执行零写入静态检查（JSON 输出含 0 字节原始索尼固件），并完成 4 大支柱 HIL 协同验证：

- **16 份本地 Donor 实测指标（`O_RDONLY`）**：
  - 零差异跨机身共享库（FX3 = FX6）：`libInfraMscServer.so`（`64,456 B`，`125` exp / `69` imp）、`libUsbControl.so`（`135,424 B`，`351` exp / `128` imp）、`libWlanAdjust.so`（`73,168 B`，`188` exp / `119` imp）、`libWlanResource.so`（`56,464 B`，`94` exp / `90` imp）。
  - 跨机身扩展共享库：`libsencore.so`（FX3 `377,328 B` vs FX6 `401,952 B`，均为 `355` exp / `130` imp，FX6 新增 `WIREDLAN_NETIF_DOWN` / `WIREDLAN_WOL_ENABLE`）、`libmpr.so`（FX3 `3,517,008 B` / `3,541` exp / `356` imp vs FX6 `28,921,824 B` / `4,271` exp / `497` imp，均含 `SetLutData` / `setLutDataInParam` / `GetMovieRecParam` / `SetMovieRecParam` / `ExecEncStart` / `EncWfiStop`）。
  - RTOS 与双备份 NVRAM：`cpapp-b.bin`（FX3 `15,980,568 B` vs FX6 `17,952,816 B`，均含 `IMX510`、`defdet.bin`、`DFS_FACTOR_WIFI_CONNECT`、`MSG_ID_INFRABB_AUDIO_SET_TX_RF_POWER`、`GpHCI`、`HCIpJ`，FX3 额外含 `DFS_FACTOR_ETHER_CONNECT`）、`Backup.bin`（FX3 `2,229,740 B` `BK4\x00` `819` 子系统 vs FX6 `2,253,333 B` `BK4\x00` `840` 子系统）。
- **四大 HIL 联合仿真支柱（Stage 27）**：
  - **Pillar A**（[`evaluate_pillar_a_imx510_cine_ei_and_sensor_nvs`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/realhw_imx510_color_and_network_usb_coemulator.py#L1211)）：验证 `IMX510` Cine EI 双原生 ISO `800` LCG（`[200..3200 EI]`）↔ ISO `12800` HCG（`[3200..51200 EI]`）精确在 `ISO 12800` 切换高增益路径，保持 `15.0+` 档动态范围、未烘焙 `S-Log3` XAVC 母版 + EI XML 元数据，并强制拦截 `p2:/setting/psd.bin` 与 `p2:/setting/defdet.bin` 写入请求（`sensor_cal_mutation_bytes == 0`）。
  - **Pillar B**（[`evaluate_pillar_b_mlut_and_slog3_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/realhw_imx510_color_and_network_usb_coemulator.py#L1448)）：仿真从 `/mnt/sd/PRIVATE/SONY/PRO/LUT/` 装载 16 个 `.cube`（`17^3 / 33^3`）槽位至易失内存 `/tmp/fx3_mlut_slots/`，对 LCD / HDMI Type-A Clean 输出应用监看 LUT 同时保持 `slog3_master_double_baked == False`（`LUT Burn-in = Off`），且对格式错误、维度不匹配或非有限（non-finite）数值 `.cube` 失败关闭。
  - **Pillar C**（[`evaluate_pillar_c_network_rf_lock`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/realhw_imx510_color_and_network_usb_coemulator.py#L1722)）：验证 `802.11ac` Wi-Fi 与 `CDC-NCM` 千兆 USB-LAN（`PTP-IP TCP/15740` `Monitor & Control` + `FTPES`）协同，`/dev/ttyAMA3` BLE 守护进程零阻塞等待（`bt_hci_blocking_wait_ms == 0`），`WIREDLAN_WOL_*` 零延迟掩码，`P12` 飞行模式硬切断 `wlan0` 且保持有线 `CDC-NCM` 在线，并锁死 `p12/p13` RF NVS（`rf_nvs_p12_p13_mutation_bytes == 0`）。
  - **Pillar D**（[`evaluate_pillar_d_usb_recovery_preservation`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h169-phase157-vm-stage27-imx510-network-usb-hil/outputs/fx3-vm/realhw_imx510_color_and_network_usb_coemulator.py#L1847)）：验证在 `MSC (054C:0DA1)`、`MTP/PTP Remote`、`CDC-NCM USB-LAN`、热拔插与 `SERVICE (054C:0336)` 间切换角色时，永不劫持或禁用 `054C:0DA1` 恢复口（`usb_msc_0da1_recovery_intact == True`、`persistent_emmc_writes_authorized == False`、`emmc_nflasha_write_count == 0`）。

### 2.2 尚未在真实物理 ILME-FX3 相机上执行的测试（明确未测项）

以下项目属于物理主机/相机实机验证，**本次仅完成宿主端 `O_RDONLY` 静态审计与 Python HIL 仿真，尚未在真实物理 ILME-FX3 机身通电执行（`UNEXECUTED ON PHYSICAL FX3 CAMERA`）**：
1. 物理 ILME-FX3 `IMX510` 实拍切换 `ISO 800 / 12800` 时 XAVC `S-Log3` 素材波形、EI XML 元数据及 SDI/HDMI 外部监看 `.cube` 3D MLUT 实时色彩渲染核验。
2. 物理机身接入 `CDC-NCM` USB-LAN 适配器后，`Monitor & Control`（`PTP-IP TCP/15740`）与 `FTPES` 实机吞吐与 `P12` 飞行模式射频断电切换。
3. 物理机USB Type-C 在 `CDC-NCM` / `MTP` 与 `Mass Storage (054C:0DA1)` / `SERVICE (054C:0336)` 间切换后的实际 USB 描述符枚举与断电重启恢复测试。

## 3. 定向与全量验证结果

| 验证命令 | 模式 | 结果 |
| :--- | :--- | :--- |
| `PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_imx510_color_and_network_usb_coemulator.py` | Local Donor | **46/46 PASS** |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_imx510_color_and_network_usb_coemulator.py` | Clean-Room | **45 PASS / 1 SKIP**（跳过本地 donor 专属对比） |
| `PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | Local Donor 全量 | **946/946 PASS**（`67.775s`） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | Clean-Room 全量 | **946 tests PASS (2 skipped)**（`67.691s`） |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 全仓 Clean-Room & 卫生门禁 | **ALL GREEN**（`0.05s`） |
