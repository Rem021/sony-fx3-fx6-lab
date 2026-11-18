# Phase 306（Stage 62 — `62/62` VM 里程碑）：Wave-52 `[Sensor Cleaning]` >= 51% 电量门槛与强制断电 vs `FX6` e-ND + APR、`[Exposure Comp.]` ±5.0/±2.0 EV + `[Cine EI]` 全锁定、`[Focus Mode]` 5/2 模式分离与回放 `[Rotate]` Slot-1 Tier-0 Vault 防火墙 HIL 协同仿真报告

## 结论先行

1. **Stage 62 (`62/62`) 全闭环通过并接入全板总装门禁**：新增 [`outputs/fx3-vm/realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py`](../../outputs/fx3-vm/realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py)（Schema `realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator_v1`），并接线至 [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 作为第 62 阶段（`vm_stages=62/62`），`Stage 1..61` 保持向后兼容（支持 `--include-stage62`、`--skip-stage62`、`--no-include-stage62`、`--skip-phase306`）。
2. **11 份真实 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 实机供体双模审计零失真**：通过受界 `os.O_RDONLY`（`<= 4096 B`）校验全部 11 份供体（8 份 `.uxc` 字符串全集 + `FX3 appFw.so`、`FX3 BK4`、`FX6 appFw.so`）字节长度、SHA-256 与机器码/符号偏移，`LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 三模完全一致，`raw_firmware_bytes_leaked == 0`。
3. **88 项 Stage 62 专项单测 + 全量 `fx3-vm` 单测 + Milestone 295 双模门禁全绿**：所有物理硬件写/刷写权限红线硬锁定为 `False`/`0`（`persistent_emmc_writes_authorized=False`、`hardware_live_attachment_authorized=False`、`slot1_vault_rotate_mutation_bytes=0`、`physical_device_writes=0`）。

---

## 一、交付文件清单（严格限定 5 个自有文件）

| 序号 | 类型 | 路径 | 职责摘要 |
| --- | --- | --- | --- |
| 1 | NEW | [`outputs/fx3-vm/realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py`](../../outputs/fx3-vm/realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py) | Phase 306 Stage 62 核心模型、11 供体 `O_RDONLY` 审计、62A..62D 仿真器、16 项红线门禁与 CLI |
| 2 | EDIT | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 接入 `stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil`（总阶段 `62/62`）与 CLI 开关 |
| 3 | EDIT | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 补充 Phase 306 Stage 62 架构契约与双模运行/单测命令 |
| 4 | NEW | [`outputs/fx3-vm/tests/test_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py) | 88 项双模单测（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`） |
| 5 | NEW | [`reports/2026-11-17-phase306-vm-stage62-sensor-cleaning-ev-comp-focus-mode-rotate-hil/README.md`](README.md) | 本中文结论先行工程报告 |

---

## 二、Wave-52 实机四大硬件契约验证摘要

### 1. Sub-Model 62A：`[Sensor Cleaning]` `>= 51%` 电池门槛与强制关机 vs 无 IBIS `FX6` e-ND + APR

- **FX3 Ver. 2.00+/7.02 契约**：`_f.uxc 0x67d6`（旧版 `.uxc 0xe7d7` `Cleaning Mode`）严格校验 `NP-FZ100 >= 51%`（`<= 50%` 立即返回 `EACCES=13` 并对齐 `.uxc 0xe574 Power insufficient.`；`Ver. 1.x` 拦截 `<= 2` 格并放行 `>= 3` 格）。
- **物理电源 `OFF` 硬锁**：触发 `MODEL_CLEANING_MODE_COMP` 5 轴 IBIS 抖动后居中并进入 `_g.uxc 0x6221` 强制物理开关 `OFF` 锁态；未断电前任何拆镜头或恢复拍摄请求均 fail-closed（`EBUSY=16`）。
- **跨机型硬件边界**：`ILME-FX6` 无 5 轴 IBIS（`fx6_has_ibis_sensor_shake=False`），拒绝 IBIS 超声清洁抖动（`EOPNOTSUPP=95`），保留光学 e-ND（`CLEAR`, `1/4..1/128`, `PID_SET_VARIABLE_ND_VALUE`）与 `Technical > APR`（`MODEL_APR_EXECUTE_COMP`）；`ILME-FX3` 保持 `fx3_has_builtin_end_filter=False`。

### 2. Sub-Model 62B：`[Exposure Comp.]` Still ±5.0 EV / Movie ±2.0 EV 与 `[Cine EI]` 全锁定

- **幅值与模式门控**：Still `P/A/S` 与 `M + ISO AUTO` 支持 `-5.0..+5.0 EV`（实时标尺钳位 `±3.0 EV`）；Movie / `S&Q` 严格钳位 `-2.0..+2.0 EV`（越界返回 `EOPNOTSUPP=95`）；`iAuto` 与固定 ISO 的手动 `M` 档禁用。
- **Log Shooting 差异**：`[Log Shooting] = Cine EI / Cine EI Quick` 下 `[Exposure Comp.]` **100% 锁定**（`cine_ei_exp_comp_enabled=False` -> `EOPNOTSUPP=95`），由 Base ISO `800`/`12800` + `[Exposure Index]` `±2.0 EV` 负责监看；`Flexible ISO` 保留 `±2.0 EV`。
- **重置与休眠拦截**：`Camera Settings Reset` 仅将曝光补偿归零 `+0.0` 而保留 `Initialize-only` 的 `[Exposure step]`（`0.3EV` / `0.5EV`）；严禁暴露休眠 `[Reset EV Comp.]`、Ver. 1 `[Dial Ev Comp]` 及 FX6 跨机型 `5EV` 补偿。

### 3. Sub-Model 62C：`[Focus Mode]` 5 档 Still vs 2 档 Movie/S&Q 分离与优先设置

- **模式分离**：Still 开放 5 档（`AF-S / AF-A / AF-C / DMF / MF`，默认 `AF-A` 随 `Camera Settings Reset` 恢复），Movie / `S&Q` 严格收敛至 **2 档**（`AF-C / MOVIE_AUTO` 与 `MF`），`AF-S/AF-A/DMF` 在 Movie/`S&Q` 固定返回 `EOPNOTSUPP=95`；拒绝休眠 `PF / SEMI_MANUAL`。
- **子项生命周期**：`[Priority Set in AF-S/AF-C]`（`AF / Release / Balanced Emphasis`）与 Movie `AF-C` `[AF Assist]` 跨 `Camera Settings Reset` 保留、仅 `Initialize` 复位；`[AF Illuminator]` 仅限 Still `AF-S/AF-A/DMF` 且在 `AF-C` / 放大 / 转接环 / Movie 下自动禁用。对比 `FX6` 物理 `AF/MF` + `Push AF Mode`。

### 4. Sub-Model 62D：回放 `[View Mode]` / `9·25` `[Image Index]` / `[Display as Group]` & `[Rotate]` Slot-1 Vault 防火墙

- **索引与视图**：`[Image Index]` 严格仅开放 **`9 Images / 25 Images`**，拒绝休眠 `12 Images / 30 Images`；支持 `Date View / Folder View(Still) / Movie View / AVCHD View / XAVC S View` 并拒绝休眠 `Folder View(MP4)`；4 项回放显示偏好均跨 `Camera Settings Reset` 保留。
- **Slot-1 Tier-0 Vault 防火墙**：`[Rotate]`（`FUNC_rotate_content`）需改写 EXIF 朝向及 `AVF_INFO` 数据库 -> 当 `Slot 1` 为 Tier-0 Vault 或写保护卡时强制 `EROFS=30`，后台传输期间返回 `EBUSY=16`，视频片段拒绝旋转（`EOPNOTSUPP=95`）；`slot1_vault_rotate_mutation_bytes == 0`，仅虚拟 `Slot 2` 静态图允许零物理写入 `90°` CCW 步进。

---

## 三、跨平台 CI 合规与安全红线实测项

- **Python 3.14 / CI 兼容**：全模块及单测零硬编码 `/usr/bin/python3`（统一 `sys.executable`）、`argparse` 内全部 `%` 已转义为 `%%`（含 `>= 51%%`）、计时断言包含 `GITHUB_ACTIONS == 'true'` 的 `15.0s` 裕度、舞台计数使用 `assertGreaterEqual(..., 62)`。
- **验证覆盖与实测指标**：
  - Stage 62 独立 CLI 与 **88** 项专项单测在 `LOCAL_DONOR_O_RDONLY`（digest `47c74feac295`）、`FX3_CLEAN_ROOM_TEST=1`（digest `c9a3aa6d34a5`）、`FX3_FX6_FORCE_CLEAN_ROOM=1`（digest `c9a3aa6d34a5`）三模均 88/88 全绿通过。
  - `outputs/fx3-vm/tests` 全量单测发现双模全绿：`LOCAL_DONOR_O_RDONLY` 模式 `Ran 3095 tests in 195.907s (OK)`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 3095 tests in 176.061s (OK, skipped=5)`。
  - `make verify-milestone-295` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` 双模全绿通过：`vm_stages=62/62`、`pillars=6/6`、`gate124=129/132`、`recovery=53/53`、`auditors=45/45`、`qemu=33/33(99/99)`、`leaked=0`、`live_attach_auth=False`、`emmc_writes_auth=False`、`usb_tx=0`。
  - `make clean-audit`（`scripts/run_all_lab_tests.py --clean-only`）`CLEAN (3.06s)`，零 `__pycache__`/`.pyc`、零未授权写操作。
