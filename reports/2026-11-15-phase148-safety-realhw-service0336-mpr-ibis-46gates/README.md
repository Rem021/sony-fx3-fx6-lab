# 第 148 阶段 — 真机主线 Part 10：`054C:0336` `op=0xFF` 金丝雀与 `MSC` 确定性回退门禁（`G45`）、Stage-B `p18:/lens` 只读锁 / 5 轴 IBIS 线圈停泊 / 原厂 `DmmCfg.bin` 池守卫（`G46`）与 46 门禁主安全预检（`verify-46-gates`）

- **日期**：`2026-11-15`
- **分支 / 工作区**：`h159-phase148-safety-service0336-mpr-ibis-46gates`
- **核心模块**：[`realhw_service0336_mpr_ibis_and_46gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/fx3_safety/realhw_service0336_mpr_ibis_and_46gate_guard.py)
- **单元测试**：[`test_realhw_service0336_mpr_ibis_and_46gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/tests/test_realhw_service0336_mpr_ibis_and_46gate_guard.py)
- **硬安全红线（不可越界）**：
  - `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
  - `PERSISTENT_WRITE_RELEASE = False`
  - `overall_ready_for_hardware_attach = False`（默认离线与 `--dry-run-simulated-backup` 模式均锁死）
  - 既有门禁模块（`G01..G44`、`verify-40-gates`、`verify-44-gates`）保持 100% 向后兼容且零改动。

---

## 1. 已验证事实：只读参考件审计、门禁实现与离线/仿真测试回执

### 1.1 双模 `os.O_RDONLY` 参考件合约审计（`audit_phase148_donor_contracts`）
严格通过 `os.open(..., os.O_RDONLY)` 读取本地 FX3 `7.02` 与 `p18` 只读参考件，并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或参考件目录缺失时确定性回退到合成 Clean-Room 元数据，JSON 序列化零原始索尼固件字节泄露：

| 键名 | 制品路径（相对 `work_root`） | 实测字节数 | SHA-256 前缀 | 已校验标记 |
| :--- | :--- | :---: | :--- | :--- |
| `fx3_libsencore` | `sony-firmware-20261024/.../libsencore.so` | `377,328` | `a2907111c4a22314...` | `AdjustControlFunc`, `SenserIfStart`, `SenserPacket`, `TransactionStart`, `Inconcurrent` |
| `fx3_lib_jiritsu` | `sony-firmware-20261024/.../libJiritsu.so` | `225,200` | `bdef58b24a3b67b4...` | `JIRITSU_SET_FILE2`, `JIRITSU_GET_FILE2`, `/tmp/jbusy`, `/tmp/jiritsu/libJit.so`, `/dev/nflasha6` |
| `fx3_libmpr` | `fx3-vm-20261101/.../libmpr.so` | `3,517,008` | `9aeef3b9edb3d011...` | `DmmMemInfo`, `GetUnitInfo`, `UDAMSetGyroscopeValue`, `ExecEncStart`, `SetMovieRecParam` |
| `fx3_ap_dmmcfg` | `fx3-vm-20261101/.../DmmCfg.bin` | `66,796` | `48c90ca08ae8174d...` | `for ilc32g12m-ipsxmp` |
| `fx3_cpapp_b` | `sony-firmware-20261024/.../cpapp-b.bin` | `15,980,568` | `c90d00d807874a53...` | `LiroSeq`, `SteadyShot`, `GyroPIDOUT_0`, `GyroStart`, `GyroStop` |
| `p18_lensfile` | `fx3-color-port-20261027/.../lens/lensfile.bin` | `262,592` | `49a08398bd47b917...` | `VX8900`, `VX8901`, `VX8902` |

### 1.2 Gate `G45`：`054C:0DA1 -> 054C:0336` `SERVICE` 会话金丝雀、`64 KiB` ELF 自删与 `MSC` 确定性回退门禁
实现函数：[`verify_service0336_canary_64k_unlink_and_msc_return`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/fx3_safety/realhw_service0336_mpr_ibis_and_46gate_guard.py#L467-L686) / [`evaluate_g45_service_0336_canary`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/fx3_safety/realhw_service0336_mpr_ibis_and_46gate_guard.py#L963-L1039)
1. **Stage-286 Branch-A `op=0xFF` 纯 RAM 槽位回显金丝雀前置**：进入任何 `op=0x00`（`/tmp/jiritsu/libJit.so`）帧前，必须完成 `054C:0DA1 -> 054C:0336` 下 `slot <= 0x11`、`1 <= size <= 5 MiB`、`sys_mount_calls == 0`、`dlopen_calls == 0` 的纯 RAM 回显校验，否则阻断为 `BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE`。
2. **`SenserPacket` 单飞串行化**：强制 `pFunc=0x0040` / `category=0x1001`、`concurrent_inflight_packets <= 1`、`seq_monotonic_strict == True` 与 `inconcurrent_lock_held == True`（`BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT`）。
3. **`64 KiB` 对齐 ELF 自删与非截断 `528 B` `FX3S0OK` 回执**：要求 `p_align == 0x10000`、`unlinkat` 已执行且无残留、完整读取 `528 B`（`16 B` `FX3S0OK` 头 + `512 B` payload）并通过 CRC32 校验（`BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID`）。
4. **确定性退场看门狗**：强制按 `STOP_0336_7 -> RELEASE_0336_8 -> MSC_REENUM_054C_0DA1 -> DRIVER_RELEASE_0DA1_9` 顺序在 `<= 5000 ms` 内回退至 `054C:0DA1` `MSC` 状态，严禁滞留 `054C:0336` `SERVICE`（`BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336`）。

### 1.3 Gate `G46`：Stage-B `p18:/lens` 只读锁、5 轴 IBIS 线圈安全停泊与原厂 `DmmCfg.bin` 池守卫
实现函数：[`verify_stageb_p18_ibis_park_and_dmmcfg_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/fx3_safety/realhw_service0336_mpr_ibis_and_46gate_guard.py#L694-L955) / [`evaluate_g46_mpr_ibis_p18_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/fx3_safety/realhw_service0336_mpr_ibis_and_46gate_guard.py#L1042-L1119)
1. **`p18:/lens` 工厂光学标定只读锁**：锁定 `/dev/nflasha18` 挂载至 `/lens` 必须为 `MS_RDONLY`（禁止 `MS_RDWR`/`RW`）、`p18_write_attempts_blocked == True`、`p18_mutation_bytes == 0`、`p18_writes_requested == 0` 且 `lensfile.bin == 262,592 B`（`BLOCKED_G46_P18_LENS_RO_OR_MUTATION`）。
2. **物理 FX3 5 轴 IBIS 音圈安全停泊**：确保 Stage-B 启动、休眠、关机全生命周期处于 `OFF`/`STANDARD`/`CENTER_LOCK_PARK`、无浮圈故障、`coil_current_ma <= 450.0 mA`、`0x0400 -> 0x1400` 居中锁死应答，并屏蔽 FX6 无防抖机身刚性传感器查询（`BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD`）。
3. **原厂 `66,796 B` AP `DmmCfg.bin` 20 池预算守卫**：校验 `66,796 B` 体积与 `for ilc32g12m-ipsxmp` 标识、`20` 个共享 MAIN 池不超额分配、`dmm_pool_overflow_bytes == 0`、`sdi_blocking_wait_ms == 0.0`，并严格屏蔽 FX6 `12G-SDI` / `SDI-RAW` / `Darwin-ND` 池请求（`BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING`）。

### 1.4 46 门禁主预检（`evaluate_46gate_preflight` / `verify-46-gates`）实测验证回执

| 验证命令（均使用 `/usr/bin/python3 -B`） | 模式 | 实测结果 | 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_service0336_mpr_ibis_and_46gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `46/46` passed (`OK`) | `2.416s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_service0336_mpr_ibis_and_46gate_guard.py -v` | Clean-Room | `46/46` passed (`OK`) | `2.345s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | 全量安全套件（Local Donor） | `797/797` passed (`OK`) | `14.035s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | 全量安全套件（Clean-Room） | `797` run, `796` passed, `1` skipped (`OK`) | `13.698s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-g45-service-0336-canary` | CLI Gate `G45` | `valid=True`, `slot=0x00`, `inflight=1`, `pkt=528B/FX3S0OK`, `msc_return=850.0ms->054C:0DA1`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-g46-mpr-ibis-p18-guard` | CLI Gate `G46` | `valid=True`, `p18_flags=MS_RDONLY`, `coil=120.0mA`, `dmm_pools=16/20`, `sdi_wait=0.0ms`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-46-gates` | CLI 默认离线 | `status=VERIFIED_43_OF_46_AWAITING_PHYSICAL_TIER0`, `verified=43/46`, `g45_to_g46_all_passed=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.4s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-46-gates --clean-room --dry-run-simulated-backup` | CLI 仿真备份演练 | `status=VERIFIED_ALL_46_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=46/46`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.4s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-44-gates` & `verify-40-gates` | 向后兼容检查 | `verified=41/44` & `verified=37/40`, `persistent_emmc_writes_authorized=False` | `<0.5s` |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库 Clean-Room 卫生检查 | `ALL GREEN` (`CLEAN`) | `0.04s` |

---

## 2. 未执行事项：物理真机上机实测边界

以下事项涉及真实物理 **ILME-FX3（`7.02`）** 硬件会话，本阶段仅完成离线策略守卫、只读参考件校验与仿真测试，**尚未在物理真机上执行**：
1. 物理相机 USB `054C:0DA1 -> 054C:0336` `SERVICE` 会话中的实机 `op=0xFF` RAM 金丝雀探测、`SenserPacket` 实测往返与 `MSC` 重新枚举耗时测量（`G45`）。
2. 物理相机 Stage-B 运行时对 `/dev/nflasha18`（`/lens`）内核挂载标志、5 轴 IBIS 音圈驱动电流及真机 `DmmCfg.bin` 20 池内存分配的在线遥测采集（`G46`）。
3. 物理相机同机身 `Tier-0` 完整冷备份回读（`G10..G12`），因此 `overall_ready_for_hardware_attach` 保持 `False`，严禁对真机执行持久 eMMC 写入或跨机型分区刷写。

---

## 3. 本阶段专有文件清单（仅 6 个文件）

1. [`outputs/fx3-safety/fx3_safety/realhw_service0336_mpr_ibis_and_46gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/fx3_safety/realhw_service0336_mpr_ibis_and_46gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_service0336_mpr_ibis_and_46gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/outputs/fx3-safety/tests/test_realhw_service0336_mpr_ibis_and_46gate_guard.py)
6. [`reports/2026-11-15-phase148-safety-realhw-service0336-mpr-ibis-46gates/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h159-phase148-safety-service0336-mpr-ibis-46gates/reports/2026-11-15-phase148-safety-realhw-service0336-mpr-ibis-46gates/README.md)
