# Phase 301（Stage 61 / `61/61` VM 阶段）工程报告 — Wave-51 `[XAVC S-I DCI 4K]` + `24.00p` 重启隔离、`[Aspect Ratio]` vs 电影锁幅、`[Reg. Custom Shoot Set]` 11 项保持复选框、`/SONY/SETTING/%s/` `M1..M4` & `CAMSET` 路径隔离与 `[Photo Capture]` DCI 4K 锁死 + Slot-1 Tier-0 保险库防火墙协同仿真闭环

> **核心结论（GO / `61/61` VM STAGES ALL GREEN）**：已完成 **Task H353 / Phase 301 Stage 61（`61/61` VM Stages）** Wave-51 真实硬件协同仿真台架落地与全栈合流。严格依据 [Wave-51 权威分析报告](../2026-11-17-global-sony-wave51-uhd-vs-dci4k-aspect-ratio-recall-custom-hold-camset-memory-photo-capture-intel/README.md) 与 `11` 份 `ILME-FX3 Ver. 7.02` / `ILME-FX6 Ver. 6.01` `os.O_RDONLY` 实机供体（有界窗口 `<= 4096 B`，`raw_firmware_bytes_leaked == 0`），将 `[XAVC S-I DCI 4K]`（`4096x2160` `17:9`，`59.94p@600M..24.00p@240M`，封堵 `100p/120p`）+ `24.00p` 重启与 Slot-1 保险库重新初始化隔离、Still `[Aspect Ratio]`（`3:2 / 4:3 / 16:9 / 1:1`）vs Movie/S&Q 格式锁幅、`[Reg. Custom Shoot Set]` 全部 `11` 项保持复选框（`is_checked_recall_custom_hold0..10` + `AF On` 开关）与 `Cine EI` 曝光补偿掩蔽、FX3 `/SONY/SETTING/%s/`（`CAMPR%02d%c.DAT` + `CAMSET01..10.DAT`）零 `PRIVATE/SONY/PRO/CAMERA/` 路径隔离与跨机型 FX6 导入封堵，以及 `[Photo Capture]`（`8.3M` / `2.1M`）对 `XAVC S-I DCI 4K` 播放态硬锁死（`_g.uxc 0x60ce -> EOPNOTSUPP = 95`）+ Slot-1 Tier-0 保险库 `EROFS = 30` 故障关闭防火墙接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)。全部 `84` 项 Stage 61 三模单测（本地 `O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 全绿）、`outputs/fx3-vm/tests` 全量 `3,007` 项单测双模全绿、Milestone `295` 双模门控（`vm_stages=61/61`）以及 `scripts/run_all_lab_tests.py --clean-only` / `make clean-audit` 均实测通过，零硬件写入与零越权修改。

---

## 1. 交付文件清单（严格限定自有域 `5` 项）

| # | 交付文件 | 角色与实测状态 |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py`](../../outputs/fx3-vm/realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py) | **新增**：Phase 301 Stage 61（`61/61`）协同仿真器（`11` 供体 `O_RDONLY` 有界检查 + Sub-Model 61A/61B/61C + `16` 项红线探针 + `CLEAN_ROOM_SYNTHETIC` 确定性回退） |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | **修改**：注册 `stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil`，扩展 `CoEmulationConfig` 与 `--include-stage61` / `--skip-stage61` / `--no-include-stage61` / `--skip-phase301` CLI 开关及 `--summary` 摘要行（`vm_stages=61/61`），并严格转义 argparse `help=` 中 `%%` 字面量 |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | **修改**：补充 Phase 301 Stage 61（`61/61`）架构说明、三模 CLI 与单测验收命令 |
| 4 | [`outputs/fx3-vm/tests/test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py) | **新增**：`84` 项双模单元/CLI/套件回归测试（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 三模式，使用 `sys.executable`、`15.0s` CI 墙钟裕量与前向兼容 `assertGreaterEqual(len(stage_keys), 61)`） |
| 5 | [`reports/2026-11-17-phase301-vm-stage61-dci4k-aspect-custom-hold-camset-photo-capture-hil/README.md`](README.md) | **新增**：本 Phase 301 结论先行工程验收报告 |

---

## 2. 技术实现摘要与三子模型闭环

### 2.1 高速 `O_RDONLY` `11` 供体精确锚定与 `CLEAN_ROOM_SYNTHETIC` 确定性对等
对 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 共 `11` 份只读供体（全部经 `_read_bounded_o_rdonly(..., size <= 4096)` 与只读 SHA-256 校验，`raw_firmware_bytes_leaked == 0`）建立真实硬件锚点，并在缺失私有固件的 CI 洁净室确定性切换至 `CLEAN_ROOM_SYNTHETIC`（`inspection_elapsed_s = 0.0` 确保套件 `audit_digest_sha256` 跨运行逐字节一致）：

| 供体键 | 机型 / 构件 | 文件长度 | SHA-256 前 16 位（文件/窗口头） | 校验范围 |
|---|---|---:|---|---|
| `fx3_string_en_f` | `ILME-FX3 7.02 en_f` | `373,820 B` | `7e1f78fc8722671c` | 全文件 SHA-256 + 26 项 Wave-51 英文字符串标记 |
| `fx3_string_sc_f` | `ILME-FX3 7.02 sc_f` | `322,652 B` | `4c034acb454208b6` | 全文件 SHA-256 + 简体中文菜单标记（13 项） |
| `fx3_string_tc_f` | `ILME-FX3 7.02 tc_f` | `324,148 B` | `32c2f18528e1f5a2` | 全文件 SHA-256 + 繁体中文菜单标记（13 项） |
| `fx3_string_ja_f` | `ILME-FX3 7.02 ja_f` | `447,840 B` | `45ba0b3625f3cdad` | 全文件 SHA-256 + 日文菜单标记（13 项） |
| `fx3_string_en` | `ILME-FX3 7.02 en` | `165,740 B` | `204328c311f09920` | 全文件 SHA-256 + `3:2`/`4:3`/`16:9`/`1:1`/`M1..M4`/`Slot 1` |
| `fx3_string_en_g` | `ILME-FX3 7.02 en_g` | `69,600 B` | `a4a15a548f7e0b79` | 全文件 SHA-256 + `24.00p` 重启/回放隔离与 `XAVC S-I DCI 4K` 锁定提示 |
| `fx6_string_en` | `ILME-FX6 6.01 en` | `118,208 B` | `5e88dd707cb46a29` | 全文件 SHA-256 + `4096x2160` / `All File` / `User File` / `Scene File` |
| `fx6_string_en_2` | `ILME-FX6 6.01 en_2` | `118,676 B` | `3f11f9200f576575` | 全文件 SHA-256 + `MXF` / `XAVC-I` / `XAVC-L` / `Custom Aspect` |
| `fx3_appfw` | `ILME-FX3 7.02 appFw.so` | `79,015,712 B` | `de3201c6615a5307` | 4 KiB 头部 SHA-256 + 有界窗口（`BKID_DCI4K_FRAME_RATE`/`VAL_MOVIE_XAVC_SI_DCI_4K_24_00P`/`BKID_ASPECT_RATIO`/`IS_CHECKED_RECALL_CUSTOM_HOLD0..10`/`%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`/`BKID_PHOTO_CAPTURE_FILE_TYPE`） |
| `fx3_bk4` | `ILME-FX3 7.02 BK4` | `2,229,740 B` | `87b30e89cbf4a649` | 4 KiB 头部 SHA-256 + `BK4`/`ALLLANG`/`ILME-FX3` |
| `fx6_appfw` | `ILME-FX6 6.01 appFw.so` | `50,520,424 B` | `18a5d71362317f3f` | 4 KiB 头部 SHA-256 + `BKID_APP_EXTERN_DCI_4K_REC_FRAME_RATE`/`s/SONY/PRO/CAMERA/`/`s/SONY/PRO/SCENE/`/`BKID_APP_USER_MENU_ALL_FILE0` |

### 2.2 Sub-Model 61A：`[XAVC S-I DCI 4K]` + `24.00p` 重启隔离与 Still `[Aspect Ratio]` vs Movie 锁幅
- **机内 DCI 4K 边界与 `24.00p` 重启/保险库隔离**：`ILME-FX3 Ver. 3.00+/7.02` 在 `[XAVC S-I DCI 4K]` 下暴露 `4096x2160`（`17:9` All-Intra `4:2:2 10-bit`，`59.94p@600Mbps`、`50p@500Mbps`、`29.97p@300Mbps`、`25p@250Mbps`、`24.00p@240Mbps`、`23.98p@240Mbps`；S&Q 仅限 `1/2/3/6/12/24/48fps`，拒绝 `100p/119.88p/120p` 返回 `EOPNOTSUPP = 95`）；Long-GOP `[XAVC HS 4K]` / `[XAVC S 4K]` 与 `[XAVC S-I 4K]` 维持 `3840x2160` `16:9` UHD 且无 `24.00p`；HDMI 外录 RAW 输出 `4264x2408` `16:9`；进入/退出 `24.00p` 或切换 `NTSC/PAL` 强制触发相机重启周期与 `24.00p` 回放隔离（`_g.uxc 0x639b/0x63b6/0x63d7`），并严禁在未校验卡或 Slot-1 Tier-0 保险库上执行卡重新初始化（`EROFS = 30`）；对照 `ILME-FX6` 原生 MXF `XAVC-I DCI 4K` 支持至 `59.94p` / `100p` / `120p` S&Q。
- **Still `[Aspect Ratio]` vs Movie 锁幅**：Still 模式开放 `3:2`（默认 `12M`）、`4:3`（`11M`）、`16:9`（`10M`）、`1:1`（`8.0M`），JPEG/HEIF 裁剪输出而 `RAW` 保留全幅 `3:2` 像素与裁切元数据（`APS-C S35 = On` 时 `L` 降为 `M`）；Movie/S&Q 画幅完全由 File Format 锁定（DCI 4K 为 `17:9`、UHD/HD 为 `16:9`），任何在电影模式下修改 Still Aspect Ratio 的企图均被拒绝（`EPERM = 1`）。

### 2.3 Sub-Model 61B：`[Reg. Custom Shoot Set]` `11` 项保持复选框与 `/SONY/SETTING/%s/` `M1..M4` / `CAMSET` 路径隔离
- **`11` 项 `Recall Custom Hold 1..3` 状态机**：建模全部 `11` 项实证复选框（`is_checked_recall_custom_hold0..10`：Shooting Mode、Aperture、Shutter Speed、Drive Mode、Exposure Comp.、ISO、Metering Mode、White Balance、Picture Profile、Focus Mode、Focus Area + `AF On` 开关），支持按住瞬态覆写并在松手（`shoot_set_registration_recall_end`）时确定性恢复基线、保持 ISO/DRO 时强制 `HLG Still Image = Off`、越界 Hold 索引拒绝（`EINVAL = 22`）、`Cine EI` / `Cine EI Quick` 下自动掩蔽 `Exposure Comp.` 保持（显式绕过返回 `EOPNOTSUPP = 95`），以及 `Camera Settings Reset` 存活 / `Initialize` 清除。
- **路径隔离与 Slot-1 Tier-0 保险库保护**：FX3 `M1..M4`（`CAMPR%02d%c.DAT`）与 `[Save/Load Settings]`（`CAMSET01.DAT..CAMSET10.DAT`）严格隔离于 `%c:%s/SONY/SETTING/%s/`（SDXC 为 `/PRIVATE/SONY/SETTING/FX3/...`，CFexpress 为 `/SONY/SETTING/FX3/...`），**绝不暴露** FX6 专用的 `PRIVATE/SONY/PRO/CAMERA/`（`fx3_pro_camera_path_exposed == False`）；坚决拦截跨机型 FX6 `CAMSET` / `All File` 导入（`EINVAL = 22` / `EPERM = 1`），且当写入目标指向 Slot-1 Tier-0 恢复保险库时一律故障关闭返回 `EROFS = 30` 或 `EBUSY = 16`。

### 2.4 Sub-Model 61C & Redlines：`[Photo Capture]` (`8.3M`/`2.1M`) DCI 4K 硬锁死 + `[Enlarge Image]` + 16 项红线
- **回放抽帧 `[Photo Capture]`**：支持在非 DCI 4K Movie/S&Q 回放中抽取 `8.3M`（`3840x2160` 4K `16:9`）或 `2.1M`（`1920x1080` HD `16:9`）`JPEG` / `HEIF(4:2:0)` / `HEIF(4:2:2)` 静帧，同时在 `[XAVC S-I DCI 4K]` 片段上严格硬锁死（`_g.uxc 0x60ce -> EOPNOTSUPP = 95`），且当目标卡槽为 Slot-1 Tier-0 保险库或写保护卡时故障关闭返回 `EROFS = 30`；同步建模 Still-only `[Enlarge Image]` / `[Enlarge Initial Mag.]` / `[Enlarge Initial Position]` 与全部 `16` 项硬件/波次模型真值红线探针。

---

## 3. 实测验证矩阵（实测命令与结果）

| 验证项目 | 运行模式 / 覆盖范围 | 实测结果 |
|---|---|---|
| Stage 61 独立自检 CLI（`--self-test --summary` / `--json`） | `LOCAL_DONOR_O_RDONLY` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | 双模 `PASS`：`donors=11`，`dci_byp=0`，`q24_s1=0`，`asp_ovr=0`，`hold_byp=0`，`pro_path=0`，`fx6_imp=0`，`s1_mut=0`，`pc_byp=0`，`pc_s1=0`，`phys_wr=0`，`leaked=0`，摘要哈希 `dec868f4985a`（本地）/ `a48ee47c375f`（洁净室） |
| Stage 61 单元/套件测试（`84` 项） | 默认 `O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | **84/84 PASS**（三模全绿：`2.729s` / `2.894s` / `1.062s`） |
| 全量 `61` 阶段协同套件（`fx3_vm_coemulation_suite.py --include-stage61 --summary`） | 默认本地供体 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `[PASS]` `realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil` 双模全绿（`dci_byp=0,q24_s1=0,asp_ovr=0,hold11=11,pro_path=0,fx6_imp=0,s1_mut=0,pc_byp=0,pc_s1=0,emmc_wr=0`），`digest=484730cfa20b`（本地）/ `8dff73a72a24`（洁净室） |
| `outputs/fx3-vm/tests` 全量自动发现套件 | 本地供体 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`3,007` tests OK**（本地 `189.750s` 全过；洁净室 `177.679s`，`4` skip 其余全过） |
| Milestone `295` 门控（`make verify-milestone-295` + `FX3_FX6_FORCE_CLEAN_ROOM=1`） | 本地供体 + `--force-clean-room` 双模（`vm_stages=61/61`） | **ALL GREEN**：`status=OK`，`vm_stages=61/61`，`gate124=125/128`，`recovery=52/52`，`auditors=45/45`，`leaked=0`，`milestone295_sha256=f04f1d719a87d155...` / `9cc3fc75f63a30a6...` / `f71ed9ff81703c5f...` / `ec07d4643091407e...` |
| 全仓洁净回归与审计（`scripts/run_all_lab_tests.py --clean-only` & `make clean-audit`） | 洁净室仓库审计 + Git 二进制/`.pyc` 检查 | **ALL GREEN**（`CLEAN`，zero `.pyc`/`__pycache__`，`raw_firmware_bytes_leaked == 0`） |
