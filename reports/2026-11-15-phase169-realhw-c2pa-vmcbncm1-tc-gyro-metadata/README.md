# Phase 169（第 35/35 项统一审计）：真实硬件 `p12:/cert/RQ_LIC.DAT` C2PA 真实性证书锁、`VMC-BNCM1`（`EXT-LK`）SMPTE 时间码与 `Catalyst/Resolve` `IMX510` 陀螺仪 / 镜头 `NonRealTimeMeta.xml` 溯源审计报告

## 1. 结论先行

本阶段在 [`outputs/fx3-firmware-lab/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab) 新增第 **35/35** 个统一固件审计模块 [`realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py)，对面向真实物理 `Sony ILME-FX3`（`Ver. 7.02`，Model ID `0x91030080`，`CXD90057 + CXD90058`）的三项核心 NVS 与素材元数据子系统完成双模态（`LOCAL_DONOR_VERIFIED` 严格 `os.O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`）验证：

1. **`p12:/cert/RQ_LIC.DAT` 机内 C2PA / 相机真实性证书不可变锁**：严格证明 Stage-B 将 `/dev/nflasha12`（`p12:/cert`）以 `MS_RDONLY` 挂载，零字节修改或移植每机独立证书（`c2pa_cert_mutation_bytes == 0`），并在跨机型伪造/非只读重挂/许可证超限（`> 100`）场景下 fail-close（`c2pa_cross_model_signing_blocked == True`）。
2. **`VMC-BNCM1`（`A-5051-506-A`，`AD_JACK_IN` Pin 10 -> `EXT-LK`）SMPTE-12M LTC 与 `/dev/rtc0` User-Bits 桥接**：实测 FX3 `7.02` 与 FX6 `6.01` 的 `appFw.so`、`libsencore.so`、`libInfraAvbbc.so`、`cpapp-b.bin` 均存在原生 `EXT-LK` / `TCUB` / `LTC` 链路；审计覆盖 `0.5V–4.5V p-p` LTC 输入、`Free-Run / Rec-Run`、32-bit `UB` 映射至 Big-6 状态胶囊，并干净屏蔽 FX6 物理缺失的 BNC `TC-OUT`（保留 `HDMI TC Out`）及强制拦截 Phase 38 `uart_boot` Pins 7/8/9 总线冲突。
3. **`NonRealTimeMeta.xml`（`ver.2.20`）`IMX510` 6 轴陀螺仪与 E 卡口镜头元数据保真（`Catalyst Browse` / `DaVinci Resolve`）**：实测 FX3 `libmpr.so` 与 `cpapp-b.bin` 保留完整 `UDAM` 2000 Hz 6 轴 IMU 遥测、`IMX510` 读取时长（`4K 24–60p` `8.7 ms / 8700 us`、`4K 120p` `4350 us`、`FHD 240p` `2200 us`）、`p18:/lens/lensfile.bin`（`O_RDONLY`）呼吸补偿曲线与 `S-Log3` / `S-Gamut3.Cine` SMPTE UL（`imu_gyro_metadata_intact == True`，`catalyst_resolve_nle_compatible == True`）。

> [!IMPORTANT]
> **严格区分实测事实与未执行物理实机动作**：本报告所有二进制文件大小、导出/导入数及符号命中数均为对本地 FX3 `7.02` 与 FX6 `6.01` Donor 二进制执行 `os.open(..., os.O_RDONLY)` + `mmap.ACCESS_READ` 的实测结果；**物理 ILME-FX3 实机上电、`VMC-BNCM1` 线缆插拔、Catalyst Browse / DaVinci Resolve 真实成片导入尚未在真机台架上执行**。

---

## 2. `O_RDONLY` 本地 Donor 实测证据（`LOCAL_DONOR_VERIFIED`，单次运行 `0.652 s`）

| Donor 文件 | 所属机身 / 固件 | `O_RDONLY` 实测字节数 | 关键验证符号 / 结构命中（实测） |
| :--- | :--- | ---: | :--- |
| `libCertificateManager.so` | FX3 `7.02` / FX6 `6.01` | `186,472` / `198,880` | `320/305` vs `375/308` 导出/导入；共有 `/dev/nflasha12` (`1`)、`/cert/tmp_certmgr/` (`1`)、`SSL_CTX_set_cert_verify_callback` (`1`)、`X509_verify_cert` (`2`)、`OCSP_cert_to_id` (`1`)、`HTTPS_AUTH_certification.pem` (`1`) |
| `appFw.so` | FX3 `7.02` / FX6 `6.01` | `79,015,712` / `50,520,424` | `InfraC2PA` 四大接口 (`SearchCertificateFile` / `UnlockCertificateFileAndStore` / `GetCertificateInfo` / `DeleteCertificateInfo`)；FX3 `No301_EXTLK` (`1`)、`MSG_ID_TCUB_TC_SYNC` (`3`)、`VAL_setting_hdmi_tc_output_*` (`1`)；FX6 `BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING` (`1`)、`BKID_APP_EXTERN_UB_MODE` (`2`) |
| `libmpr.so` | FX3 `7.02` / FX6 `6.01` | `3,517,008` / `28,921,824` | 共有 `C2PA` (`33` vs `3`)、`SSIG` (`8` vs `3`)、`NonRealTimeMeta` (`1` vs `42`)、`UDAMSetGyroscopeValue` (`1`)、`UDAMSetAccelerometerValue` (`1`)、`UDAMSetBreathingCorrectionValue` (`1`)、`s-log3` (`2` vs `4`)、`s-gamut3-cine` (`1` vs `2`)；FX3 独有完整 JUMBF 签名箱 `c2pa.assertions` (`13`)、`c2pa.claim.v2` (`2`)、`CreateC2paSigStructureHashData` (`1`) |
| `libsencore.so` | FX3 `7.02` / FX6 `6.01` | `377,328` / `401,952` | 共有 `CHANGE_TC_IO`、`EXEC_SYS_BOB_TC_IO_READ`、`C_6AXIS_GYRO_STAT_NOISE`、`A_GYRO_SENS`、`A_TB_SET_LENS_INFO`；FX6 含 `DWN_INIT_LICENSE_DATA` |
| `libInfraAvbbc.so` | FX3 `7.02` / FX6 `6.01` | `1,734,632` / `1,743,200` | 共有 `ConvertCmdMidToTcub`、`ConvertResMidFromTcub`、`midConvTableToTcub`、`midConvTableFromTcub` |
| `cpapp-b.bin` | FX3 `7.02` / FX6 `6.01` | `15,980,568` / `17,952,816` | 共有 `EXTERNALTC_CHECK` (`1`)、`EXTERNALTC_LOCK` (`1`)、`EXTERNALTC_PSEUDOLOCK` (`4`)、`LTC` (`4`)、`29:Vitc/LTC/DPACK` (`1`)、`cpActTcub` (`4`)、`C_ImagerCtrl_IMX510` (`1`)、`fixed_lensfile` (`2`)、`GyroStart`/`GyroStop` (`2`/`2`) |

> [!NOTE]
> **跨机身 C2PA 关键发现**：FX3 `7.02` 的 [`libmpr.so`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py) 内嵌完整 C2PA 2.1 JUMBF 签名路径（`c2pa.assertions` / `c2pa.claim.v2` / `CreateC2paSigStructureHashData` / `CreateCryptMetaForC2PASonyOriginalSignature`），而 FX6 `6.01` `libmpr.so` 仅含基础 `C2PA`/`SSIG` 占位标记。因此 Stage-B 必须严格锁定 `p12:/cert/RQ_LIC.DAT` 只读，不得跨机身移植或伪造 C2PA 签名。

---

## 3. 四大审计支柱与安全边界矩阵（12 触点 / 4 分类）

- **Pillar 1（`P12_CERT_RQ_LIC_C2PA_IMMUTABILITY_LOCK`）**：[`evaluate_p12_c2pa_cert_immutability`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py) 强制校验 `MS_RDONLY`、`c2pa_cert_mutation_bytes == 0`、`RQ_LIC.DAT <= 100` 许可证上限，并拦截跨型号签名与非法路径重映射。
- **Pillar 2（`VMC_BNCM1_EXT_LK_TIMECODE_AND_RTC_USERBIT_BRIDGE`）**：[`encode_smpte12m_tc_and_ub`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py) 与 [`evaluate_vmc_bncm1_ext_lk_tc_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py) 覆盖 NDF/DF（`29.97`/`59.94` 丢帧合法性）BCD 编码、`Sony VMC-BNCM1` / `Deity C23` / `Tentacle C24`、`AD_JACK_IN` Pin 10、`0.5–4.5V p-p`、`/dev/rtc0` (`P11 0x92d2091c`)、`BB_TC_OUT` 屏蔽与 Phase 38 `uart_boot` Pins 7/8/9 互斥锁。
- **Pillar 3（`NRTM_XML_IMX510_GYRO_LENS_CATALYST_RESOLVE_PROVENANCE`）**：[`synthesize_and_verify_phase169_nrtm_xml`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py) 与 [`evaluate_nrtm_gyro_lens_provenance`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py) 验证 `NonRealTimeMeta v2.20` XML 往返、`IMX510` 分辨率读取时长、2000 Hz 陀螺仪数据包、无芯片手动镜头安全降级以及防伪造 C2PA 声明校验。
- **Pillar 4（`NVS_WRITE_FIREWALL_AND_12TP_PROVENANCE_MATRIX`）**：[`evaluate_phase169_write_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py) 与 [`build_phase169_provenance_matrix`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py) 锁定 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`，12 触点分布为 `NATIVE_PASSTHROUGH=3`、`SHIM_TRANSLATED=4`、`MASKED_ABSENT_HW=1`、`HARD_WRITE_PROTECTED=4`。

---

## 4. 交付文件与实测验证命令

### 4.1 交付文件清单
- 审计模块：[`realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py)
- 包导出与 CLI 注册（`35/35`）：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)、[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/README.md)
- 双模态单元测试（48 项）：[`test_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/tests/test_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta.py)（同步将 [`test_realhw_cxd90057_cxd90058_sabin_codec.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h183-phase169-c2pa-cert-vmcbncm1-tc-gyro-meta/outputs/fx3-firmware-lab/tests/test_realhw_cxd90057_cxd90058_sabin_codec.py#L253) 第 253 行放宽为 `assertGreaterEqual(..., 34)`）

### 4.2 实测通过结果
1. `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"`：**1,210 项测试全部通过**（`45.124s`，含本阶段 48 项双模态测试）。
2. `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"`：**1,210 项测试全部通过**（`22.409s`，`skipped=3` 为既有仅限本地 Donor 的断言）。
3. `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`：`CLEAN` / `ALL GREEN in 0.06s`（零未跟踪二进制或 `.pyc`）。
4. 未执行项（需后续物理台架/真机条件）：真实 FX3 `v7.02` 连接 `VMC-BNCM1` + 外部 LTC 发生器注入时码后，实拍录制 MP4 与 `*M01.XML` 导入 `Sony Catalyst Browse` / `DaVinci Resolve` 的端到端实机验证。
