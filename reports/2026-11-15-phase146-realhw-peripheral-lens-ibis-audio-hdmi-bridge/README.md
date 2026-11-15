# Phase 146：Real-HW Stage-B 外设跨机身桥接第 29 号审计器（E-Mount 镜头 `p18` / 5 轴 IBIS / `XLR-H1` 4 声道音频 / HDMI-vs-SDI）

> **日期**：2026-11-15 | **工作区**：[`h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi)  
> **核心结论**：已在 [`outputs/fx3-firmware-lab/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi/outputs/fx3-firmware-lab/README.md) 完成第 29 号统一审计器 [`realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor.py) 及 46 项双模单测；本地真实 Donor（`os.O_RDONLY` + `mmap.ACCESS_READ`）与 Clean-Room（`FX3_FX6_FORCE_CLEAN_ROOM=1`）全部通过，`audit-all` 扩展至 **`29/29`**。

---

## 1. 交付文件清单（严格限定 6 个自有文件）

1. [`realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor.py) — 第 29 号双模外设桥接审计器（4 大子系统 + 16 触点 4 类兼容矩阵 + 写保护门禁）。
2. [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) — 导出 Phase 146 全部公开常量、数据类、评估函数与报告接口并加入 `__all__`。
3. [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) — 新增 `audit-realhw-peripheral-bridge` 子命令并接入 `run_audit_all`（`29/29`）。
4. [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi/outputs/fx3-firmware-lab/README.md) — 更新第 29 号模块文档与 CLI 示例。
5. [`test_realhw_lens_ibis_audio_hdmi_peripheral_bridge.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi/outputs/fx3-firmware-lab/tests/test_realhw_lens_ibis_audio_hdmi_peripheral_bridge.py) — 46 项双模单元测试（正例/反例 Fail-Closed、AST `O_RDONLY` 检查、`audit-all >= 29`）。
6. [`reports/2026-11-15-phase146-realhw-peripheral-lens-ibis-audio-hdmi-bridge/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h156-phase146-realhw-peripheral-lens-ibis-audio-hdmi/reports/2026-11-15-phase146-realhw-peripheral-lens-ibis-audio-hdmi-bridge/README.md) — 本报告。

---

## 2. 实测真实 ELF / 二进制事实与工程推论严格边界

### 2.1 已实测的本地 Donor ELF / 二进制事实（`os.O_RDONLY` + `mmap.ACCESS_READ`，耗时 `< 0.30 s`）

| 子系统支柱 | 实测 Donor 文件 | 实测尺寸 / 符号与标记计数（FX3 `v7.02` vs FX6 `v6.01`） | 桥接分类与安全约束 |
| :--- | :--- | :--- | :--- |
| **1. E-Mount 镜头与 `p18:/lens`** | `libInfraLensCommunicator.so`<br>`libsencore.so`<br>`appFw.so` | `libInfraLensCommunicator.so` 均为 `14,544 B`，导出/导入 **完全一致（`27` exports / `25` imports）**；`libsencore.so`（`377,328 B` vs `401,952 B`）导出/导入 **完全一致（`355` exports / `130` imports）**，共享 `SenserIfStart`/`MiconAccessFunc`/`/dev/nflasha5`/`/dev/nflasha8` 且均不直写 `/dev/nflasha18`；`appFw.so` 镜头标记命中 `5/5`（FX3）与 `8/8`（FX6）。 | 底层 12-pin IPC `NATIVE_PASSTHROUGH`；`T/F-stop`、`ft/m`、呼吸/畸变/暗角补偿走 `SHIM_TRANSLATED`；`p18:/lens/lensfile.bin`（FX3 LBA `0x0031C000` vs FX6 `0x00312000`）硬性只读（`p18_lens_writes_permitted == False`）。 |
| **2. 5 轴物理 IBIS vs Catalyst 陀螺** | `appFw.so`<br>`cpapp-b.bin`<br>`libmpr.so`<br>`Backup.bin` | FX6 `appFw.so` 含刚性传感器参数 `PRM_is_imager_stabilization_unit_fixed`（`7/7` 标记）；`cpapp-b.bin` 中 FX3 `LiroSeq` 命中 **`529` 次** vs FX6 **`148` 次**，共享 `SteadyShot` / `GyroPIDOUT_0` / `GyroStart` / `GyroStop`；`libmpr.so` 共享 `UDAMSetGyroscopeValue` / `UDAMSetAccelerometerValue`（`3/3` FX3、`4/4` FX6）；`Backup.bin` 双 `BK4\0` 校验和有效（`819` vs `840` 子系统）。 | `libgrm-fbinit9.so` 屏蔽刚性传感器查询；`Off` 强制经 `0x0400 -> 0x1400` Center-Lock 锁止音圈防悬空（`ibis_coil_safe_park_verified == True`）；`Active+` 安全限幅至 FX3 `ACTIVE`；`Backup.bin`/`psd.bin`/`Jiritsu` 零写入。 |
| **3. MI-Shoe `XLR-H1` 4ch 音频** | `appFw.so`<br>`libInfraHotshoe.so`<br>`AVBB_SCN_START_AUDIO.so` | FX6 `libInfraHotshoe.so`（`47,808 B`，`76` exports / `44` imports）含 `INFRA_HOTSHOE_UIPC_GETSHOEID` 等 5 项 UIPC 标记；`AVBB_SCN_START_AUDIO.so`（`70,096 B`）含 `AvbbScnStartAudio`/`BO_ID_MIC`/`BO_ID_SHOE_MIC`；`appFw.so` 音频标记 `7/7`（FX3 & FX6），共同采用 `48 kHz / 24-bit / 4ch = 4,608,000 bps` LPCM。 | `XLR-H1` 接入为 `NATIVE_PASSTHROUGH`；无手柄/仅 3.5 mm TRS 时由 `P11 0x91db059b`（`E_TMO=-50 -> 0x8000`）非阻塞回退至机内立体声/TRS + CH3/CH4 静音（`phantom_device_timeout_eliminated == True`）。 |
| **4. HDMI Type-A + Multi-USB `TC-IN` vs `12G-SDI` / `BNC`** | `appFw.so`<br>`libInfraAvbbc.so`<br>`cpapp-b.bin` | `libInfraAvbbc.so` 双方均含 5 项 `ObjAvbbcCmn::ConvertCmdMidToSdi/Hdmi/Tcub` 与 `ConvertResMidFromSdi/Hdmi` 桥接符号；`cpapp-b.bin` 中 FX3 `HDMI=404, SDI=16` vs FX6 `HDMI=421, SDI=71`；`appFw.so` 命中 `4/4`（FX3）与 `8/8`（FX6，含 `PRM_FEATURE_MANAGER_sdi_output` 与 `PRM_genlock_detect_ref_notify_receive_state`）。 | `HDMI Type-A`（`4K60 10-bit 4:2:2` / `16-bit RAW` / `Clean OSD`）走 `NATIVE_PASSTHROUGH`；Multi-USB `VMC-BNCM1`（`Pin 3 LTC+`、`680 kOhm`、`P11 0x92d2091c`）走 `SHIM_TRANSLATED`（严禁 `H0 uart_boot` 期间接入）；`12G_SDI_OUT`/`BNC_TC_OUT`/`BNC_GENLOCK_IN`/`DARWIN_ND` 为 `MASKED_ABSENT_HW` 非阻塞零等待（`sdi_blocking_wait_eliminated == True`）。 |

- **16 触点 4 类兼容矩阵汇总**：`NATIVE_PASSTHROUGH = 5`，`SHIM_TRANSLATED = 5`，`MASKED_ABSENT_HW = 3`，`HARD_WRITE_PROTECTED = 3`（合计 `16`，全部 `blocking_wait_eliminated == True`、`write_protected == True`、`persistent_emmc_writes_authorized == False`、`emmc_mutation_bytes == 0`、`calibration_mutation_bytes == 0`）。

### 2.2 未执行事项（物理真机外设链路留待实机阶段验证）

- **尚未执行物理 FX3 机身实机外设联动测试**：本离线 macOS 开发环境未连接物理 ILME-FX3 (`7.02`) 机身、E-Mount 实体镜头、XLR-H1 热靴手柄、VMC-BNCM1 时间码线或外部 Atomos HDMI RAW 录机；因此 Stage-B 运行时 `libgrm-fbinit9.so` 拦截真实 `cpapp-b.bin` IBIS 音圈锁止电流与 `XLR-H1` 热插拔瞬态耗时属于基于 ELF/CP 符号分析的**工程设计与边界判定**，需在后续授权物理机验证阶段实测确认。

---

## 3. 验证命令与实测结果

- `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` — 全部通过（含本阶段新增 46 项测试，真实 Donor 模式）。
- `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` — 全部通过（强制 Clean-Room 模式）。
- `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --json` 与 `--clean-room --json` — 返回退出码 `0`，`29/29` 审计器全部 `all_checks_passed: true`。
- `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` — 全部通过。
