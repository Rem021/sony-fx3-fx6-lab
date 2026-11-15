# Phase 165 — 实体 FX3 硬件安全护栏 `G53`（`CXD90057` *Mira* + `CXD90058` *Cetus* 双 SoC 链路、`sabin` SA-DSP 只读锁定与 `16-bit SDI RAW` 掩码）、`G54`（`16/16 H0 == H3` 出厂封印、零 `/tmp/jiritsu` 残留与官方更新就绪守卫）及统一 54-Gate 主预检报告

> **任务 ID**: `H179` · **目标硬件**: Sony ILME-FX3（`Ver. 7.02`, Model ID `0x91030080`, AP `CXD90057` *Mira* + CP `CXD90058` *Cetus*）
> **核心结论**: 在严格保持 `G01..G52` 历史模块 100% 未修改的前提下，已完成安全门 **`G53`**、**`G54`** 与统一 **54-Gate 主预检引擎（[`evaluate_54gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/realhw_cxd90058_sabin_seal_and_54gate_guard.py#L1630-L1985) / `verify-54-gates`）** 的双模式实现与验证。离线默认模式 `51/54` 通过（`G10..G12` 实体 Tier-0 门维持 `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`），`--dry-run-simulated-backup` 模式 `54/54` 演练通过；全部核心写入/发射/挂机红线（`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`overall_ready_for_hardware_attach = False`）均保持硬锁定。

---

## 1. 严格区分：已实测事实 vs 未执行的实体台架操作

### 1.1 本次已实测事实（`os.O_RDONLY` 固件契约审计 + 离线安全门单元测试 + CLI + 净室卫生审计）
1. **双模式只读 (`os.O_RDONLY`) Donor 审计 ([`audit_phase165_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/realhw_cxd90058_sabin_seal_and_54gate_guard.py#L567-L689))**：
   - 实测经 `os.open(..., os.O_RDONLY)` 读取并校验 FX3 `7.02` 本地供体 `libsencore.so`（`377,328 B`）、`libmpr.so`（`3,517,008 B`）、`im.elf`（`40,920 B`）、`cpapp-b.bin`（`15,980,568 B`，SHA-256 `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`）及 `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`），5 项供体 SHA-256 与关键标记（`Cetus`、`sabin`、`memcfg`、`OTP`、`SDI`、`DSP`、`mode`、`XAVC`、`HEVC`、`mew`、`orig`、`BK4\0`、`90057`）全量通过；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或缺失供体目录时确定性回退至 `CLEAN_ROOM_SYNTHETIC`，JSON 输出零原始索尼固件字节泄露。
2. **Gate `G53` (`CXD90057` *Mira* + `CXD90058` *Cetus* 双 SoC 链路、`sabin` 32-bit SA-DSP 不可变性、`16-bit SDI RAW` 掩码与 `memcfg=` 编码池守卫，[`verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/realhw_cxd90058_sabin_seal_and_54gate_guard.py#L984-L1268))**：
   - 硬阻断对 `p8:/cpapp-b.bin`、`CXD90058` 副处理器引导固件或 `sabin/` 32-bit SA-DSP 微码的任何修改或写入/补丁请求（`p8_cpapp_mutation_bytes == 0`、`cxd90058_mutation_bytes == 0`、`sabin_dsp_mutation_bytes == 0`，否则 `BLOCKED_G53_CXD90058_OR_SABIN_MUTATION`）。
   - 校验 `CXD90057 <-> CXD90058`（`SLVS-EC` / `IVSHMEM` / `UIPC_CP_IPC`）双 SoC 链路健康且绑定 `p8:/cpapp-b.bin`（否则 `BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION`）。
   - 对仅限 FX6 的 `16-bit SDI RAW` 与 `mew.bin` FPGA 输出路径实施 fail-closed 掩码屏蔽（`fx6_sdi_raw_masked == True`、`mew_bin_fpga_probe_masked == True`、`output_path` 禁止 `SDI`/`MEW`，否则 `BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED`），同时验证 FX3 `1,724.00 MiB` `memcfg=` 预算内 `XAVC-I` / `XAVC S-I` / `XAVC HS` 编码池 2 的幂（`>= 4096 B`）对齐与零溢出（否则 `BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW`）。
3. **Gate `G54` (`16/16 H0 == H3` 出厂封印、零 `/tmp/jiritsu`/`p6` 残留与官方更新就绪守卫，[`verify_post_bench_factory_seal_and_official_readiness_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/realhw_cxd90058_sabin_seal_and_54gate_guard.py#L1271-L1455))**：
   - 校验全部 16 个存储表面（`sector0`、`emmc_boot0`、`emmc_boot1`、`p1_updater`、`p2_setting`、`p3_system`、`p5_wbi`、`p6_jiritsu`、`p7_rootfs`、`p8_cpapp`、`p10_vfat`、`p12_cert`、`p13_rf_nvs`、`p15_usr`、`p18_lens`、`spi_nor_ro`）实现 `SHA256(H0) == SHA256(H3)` 按位一致还原（否则 `BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH`）。
   - 校验零 `/usr/bin/im.elf.orig`、零 `/etc/ld.so.preload`、零 `/tmp/jiritsu/*` 与零 `p6` 分块残留（`residual_artifact_count == 0`，否则 `BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT`）。
   - 校验 `OTP == 0`、`RPMB == 0` 与 `/setting/updater/mode* == 0` 且 `official_update_ready == True`（否则 `BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY`）。
4. **全量自动化验证实测**：
   - 新增 48 项双模式单测（正常 `LOCAL_DONOR_O_RDONLY` 模式 `Ran 48 tests in 2.365s — OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 48 tests in 1.655s — OK`）。
   - `outputs/fx3-safety/tests` 全套测试：正常模式 `Ran 987 tests in 22.722s — OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 987 tests in 20.824s — OK (skipped=1)`。
   - CLI `verify-g53-cxd90058-sabin`、`verify-g54-factory-seal`、`verify-54-gates`（`verified=51/54`）与 `verify-54-gates --dry-run-simulated-backup`（`verified=54/54`，`el3_payload_transmit_authorized=False`、`spi_nor_write_authorized=False`、`persistent_emmc_writes_authorized=False`、`overall_ready_for_hardware_attach=False`）均实测返回退出码 `0`。
   - `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.14s`。

### 1.2 未执行的实体相机台架操作（仅离线软件门禁就绪，未接触物理机身）
- 尚未对真实物理 **ILME-FX3** 机身采集或比对任何实机 `H0` / `H3` 16 存储表面 SHA-256 封印哈希，实体 Tier-0 门 `G10..G12` 仍维持未签发状态，`overall_ready_for_hardware_attach` 硬锁定为 `False`。
- 尚未向真实物理机身的 `CXD90057` / `CXD90058` / `sabin` SA-DSP / `p8:/cpapp-b.bin`、SPI NOR 或 eMMC 执行任何读取回传写或刷机操作（`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`）；跨机型整分区刷写仍为 `BLOCKED / NO-GO`。

---

## 2. 交付清单（严格仅修改/新增 6 个所属文件）

| 序号 | 文件链接 | 变更类型 | 职责摘要 |
| :---: | :--- | :---: | :--- |
| 1 | [realhw_cxd90058_sabin_seal_and_54gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/realhw_cxd90058_sabin_seal_and_54gate_guard.py) | 新增 | 实现 [`audit_phase165_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/realhw_cxd90058_sabin_seal_and_54gate_guard.py#L567-L689)、纯辅助校验器、[`evaluate_g53_cxd90058_sabin`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/realhw_cxd90058_sabin_seal_and_54gate_guard.py#L1463-L1545)、[`evaluate_g54_factory_seal`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/realhw_cxd90058_sabin_seal_and_54gate_guard.py#L1548-L1622) 及 [`evaluate_54gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/realhw_cxd90058_sabin_seal_and_54gate_guard.py#L1630-L1985) |
| 2 | [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/__init__.py) | 更新 | 导出 `G53` / `G54` 与 `evaluate_54gate_preflight` 等 Phase 165 符号（无历史符号碰撞） |
| 3 | [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/fx3_safety/__main__.py) | 更新 | 新增 CLI 子命令 `verify-g53-cxd90058-sabin`、`verify-g54-factory-seal`、`verify-54-gates` |
| 4 | [outputs/fx3-safety/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/README.md) | 更新 | 补充 Section 3.3 导出项与 Section 27（Phase 165 `G53`/`G54`/`verify-54-gates` 说明） |
| 5 | [test_realhw_cxd90058_sabin_seal_and_54gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/outputs/fx3-safety/tests/test_realhw_cxd90058_sabin_seal_and_54gate_guard.py) | 新增 | 48 项双模式单元测试与故障注入用例 |
| 6 | [reports/2026-11-15-phase165-safety-54gates-cxd90058-sabin-seal/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h179-phase165-safety-54gates-cxd90058-sabin-seal/reports/2026-11-15-phase165-safety-54gates-cxd90058-sabin-seal/README.md) | 新增 | 本 Phase 165 验证与交付报告 |
