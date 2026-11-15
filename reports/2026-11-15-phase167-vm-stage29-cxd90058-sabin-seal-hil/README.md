# Phase 167（Stage 29 / `29/29`）技术交付报告：`CXD90057`（`Mira`）+ `CXD90058`（`Cetus`）双 SoC IPC、`sabin` SA-DSP、`XAVC-I / HEVC` 编解码与 `H0 == H3` 出厂封签 HIL 协同仿真

## 1. 结论先行
- 已在 [`outputs/fx3-vm/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h181-phase167-vm-stage29-cxd90058-sabin-seal-hil/outputs/fx3-vm/realhw_cxd90058_sabin_codec_and_seal_coemulator.py) 实现 **Stage 29（`29/29`）** 协同仿真器并接入 [`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h181-phase167-vm-stage29-cxd90058-sabin-seal-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)（支持 `--skip-phase167`）。
- 全量双模验证全部通过（`/usr/bin/python3 -B`）：Stage 29 单测 `46/46`（本地与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模 PASS）、`outputs/fx3-vm/tests` 全量 `1,038` 项单测双模 PASS（洁净室模式下既有 3 项本地供体专项按设计跳过），`scripts/run_all_lab_tests.py --clean-only` 全绿（`3.12s`），全板 `29/29` 协同仿真在洁净室约 `0.49s`（`< 1.2s`）、本地只读供体约 `2.00s`（`< 2.6s`）内完成。

## 2. 交付与修改文件清单
- 新增模块：[`realhw_cxd90058_sabin_codec_and_seal_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h181-phase167-vm-stage29-cxd90058-sabin-seal-hil/outputs/fx3-vm/realhw_cxd90058_sabin_codec_and_seal_coemulator.py)
- 套件编排更新：[`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h181-phase167-vm-stage29-cxd90058-sabin-seal-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)
- 模块文档更新：[`outputs/fx3-vm/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h181-phase167-vm-stage29-cxd90058-sabin-seal-hil/outputs/fx3-vm/README.md)
- 新增单元测试（46 项）：[`test_realhw_cxd90058_sabin_codec_and_seal_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h181-phase167-vm-stage29-cxd90058-sabin-seal-hil/outputs/fx3-vm/tests/test_realhw_cxd90058_sabin_codec_and_seal_coemulator.py)
- 既有阶段计数断言兼容放宽（`== 28` -> `>= 28`）：[`test_realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h181-phase167-vm-stage29-cxd90058-sabin-seal-hil/outputs/fx3-vm/tests/test_realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py#L557-L645)

## 3. 实测事实（`os.O_RDONLY` 本地供体审计 & HIL 协同仿真）
1. **10 份真机供体只读审计（`os.open(..., os.O_RDONLY)` + `mmap.ACCESS_READ`）与洁净室回退**：
   - 实测 FX3 `7.02` 与 FX6 `6.01` 的 `cpapp-b.bin`（`15,980,568 B` vs `17,952,816 B`，均具备 `0x00108000` ARM32 入口向量及 `TOPPERS`/`DmmWrapper`/`memcfg`/`/usr/sabin/aed_dic1.bin`/`bed_dic1.bin`；FX6 独有 `Mew`/`MoniFpga_StartStopSDI`/`Darwin` 在 FX3 中为 `0` 命中）、`libmpr.so`（`3,541` vs `4,271` 导出）、`libsencore.so`（`355` 导出 / `130` 导入完全对等）、`im.elf`（`40,920 B`，`11` 导出 / `85` 导入零差异 ABI）与 `Backup.bin`（`BK4\x00`，`819` vs `840` 子系统及 `\sabin\idt_cam.bin`/`tomco` 标记）。
   - Stage 29 CLI 自检摘要：`LOCAL_DONOR_RDONLY` 摘要 `ddc982da1a6f`；`CLEAN_ROOM_SYNTHETIC` 摘要 `dd4766de6c29`；全板 `29/29` 摘要本地 `d9093d09b604`、洁净室 `1c13f0e767c6`。
2. **Pillar A — `CXD90057`（`Mira`）<-> `CXD90058`（`Cetus`）双 SoC 互联与 `1,724.00 MiB` `memcfg=` 池**：
   - 验证 4 段 non-cacheable `memcfg=` 池精确合计 `1,807,745,024 B`（`1,724.00 MiB`）且两两不重叠；在持续 `4K 120p`（`240` 帧 / `480` UIPC 往返包）仿真中实现 `ipc_deadlocks == 0`、`mailbox_stalls == 0`、`cxd90058_mutation_bytes == 0`、`cp_mutation_bytes == 0`，并拦截全部 `/dev/nflasha8`/`cpapp-b.bin` 等写请求。
3. **Pillar B — `sabin` 32 位 SA-DSP 与 `XAVC-I / XAVC S-I / XAVC HS (HEVC)` 编码桥接**：
   - 验证 `sabin` 窗口 `0x809139000..0x809178FFF`（`0x40000 B`）位于 `memcfg=` 池内且与 `cpImg` 零重叠；5 项 XAVC-I (MXF) / XAVC S-I (MP4) / XAVC HS (HEVC) 预设准入原厂 `libmpr.so` 桥接，FX6 独占 `16-bit SDI RAW`（`mew.bin` FPGA）被 fail-closed 拦截且 `appfw_crashes == 0`。
4. **Pillar C — Tier-0 冷备份 RAID-6 `GF(256)`（`0x11D`）双片损坏内存自愈**：
   - 11 个 Tier-0 分片在 `GF(2^8)` P+Q 编码下，覆盖全部 $\binom{11}{2}=55$ 种双分片损坏组合均可于 RAM 内 `11/11` 比特精确自愈；修复前阻断 Stage-A 暂存，修复后放行，`>= 3` 分片丢失 fail-closed 拒绝（`UNRECOVERABLE_QUORUM_LOSS_GE_3`）。
5. **Pillar D — `H0 -> H1 -> H2 -> H3` `16/16` 出厂封签与零残留质保审计**：
   - 全部 `16` 个存储面（`sector0, p1..p30, spi_nor, otp, rpmb`）证明 `SHA256(H0) == SHA256(H3)`，零 `.orig`、零 `/tmp/jiritsu`、零 `p6` 分片残留、`OTP == 0`、`RPMB == 0`、`emmc_nflasha_write_count == 0` 且 `persistent_emmc_writes_authorized == False`。

## 4. 事实与未执行物理真机实操边界（重要声明）
- **已实际验证**：上述结果全部基于仓外本地只读供体二进制（`os.O_RDONLY`）的静态结构/符号核验与软件侧 HIL 协同仿真模型、GF(256) 代数重建验证及单元测试。
- **未执行物理真机台架操作**：本阶段**未**连接真实物理 `ILME-FX3` 相机、**未**对真实机身执行任何 `eMMC` / `SPI NOR` / `OTP` / `RPMB` 写入、SD/CFexpress 卡实机刷写或双机位实拍烧录；物理机身仍受项目安全红线硬锁定（`persistent_emmc_writes_authorized == False`）。
