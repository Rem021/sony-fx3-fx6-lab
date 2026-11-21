# Phase 371 工程闭合报告：`24/24` 第 24 级物理台架准备度预检器（`preflight-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-creatorsapp-ble-and-shotmark` / `preflight-phase371`，Global Sony Waves 79–80 收官里程碑）

- **日期**：`2026-11-18`
- **任务 / 阶段**：`H469` · **Phase 371（`24/24` Physical Bench Readiness Verifiers）**
- **上游实证情报基线**：
  - [Global Sony Wave 79 实证情报报告](../2026-11-18-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` Model `0x91030080` vs `ILME-FX6 Ver. 6.01` `5-024-458-18`：`Shooting -> [Zoom]` Reset 分裂与 `Custom Key Z. Speed` 仅 Fixed `1..8`、`Setup -> [Dial Customize]` 仅 Initialize 5 项、`[Different Set for Still/Mv]` 8-bit 掩码、`[DISP]` 4 页与零 EVF `[Finder/Monitor]` 休眠、`[Select LUT]` vs `[Gamma Display Assist]` 互斥，以及 `[External Output]` HDMI 4K 10-bit 4:2:2 / Sony ELF 拼写勘误 vs FX6 25 组合 12G-SDI 双管线）
  - [Global Sony Wave 80 里程碑实证情报报告](../2026-11-18-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/README.md)（`80/80 Waves` 收官：7 项抗 Reset `[TC/UB]` + `[TC/UB Disp. Setting]`、`VMC-BNCM1` 单向 `TC-IN-Only` `EXT-LK` vs FX6 BNC `TC IN/OUT` & Hex `Users Bit`、`[FTP Transfer Func.]` Passive-only 明文 `FTP` / Explicit `AUTH TLS` `FTPES`（零 SSH-SFTP / 零 Implicit FTPS）与 `Slot 1` `cacert.pem`/`FTPSET01..10.DAT` `EROFS=30` 防火墙、`Creators' App` 5 组 BLE GATT 表 + Ver. 3.00+ 位置联动外迁 + `LMP_WAKEUP_CONFIG` + **Wave 80 `G114` 勘误** `[Airplane Mode] = On` 抗 `[Reset Network Set.]` 且必须电气隔离 `USB-LAN`，以及 Playback `Shot Mark`/`Rating`/`Protect`/`Delete`/非对称 `Copy` `Slot 2 -> Slot 1` `EROFS=30` vs FX6 `Clip Flag`）
- **前序模板基线**：
  - [Phase 368 工程闭合报告](../2026-11-18-phase368-preflight23-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-srt/README.md)（第 23 级预检器模板）
  - [Grand Milestone Phase 364 闭合报告](../2026-11-18-phase364-grand-milestone-364-master-gate/README.md)（6 支柱总闸门基线）

---

## 1. 核心结论（结论先行）

1. **`实测事实`：第 24 级物理台架预检器严格在 6 文件所有权范围内落地，将 `fx6_closure` 只读物理台架预检体系推进至 `24/24`**
   - 新增 [`realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py)（`2,929` 行，Schema `realhw_preflight24_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_shotmark_v1`，版本 `phase371_v1`），成为只读物理台架预检器链路的 **第 24 级**（`Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334 -> Ph338 -> Ph341 -> Ph342 -> Ph345 -> Ph354 -> Ph358 -> Ph368 -> Ph371`）。
   - 全部 `159` 项公共符号已以非遮蔽方式接入 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L4180-L4340) 与 `__all__`（[#L8408-L8566](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L8408-L8566)，AST 查重 `DUPLICATES: []`，全包导入 `4,185` 项零回归）；CLI 主命令 `preflight-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-creatorsapp-ble-and-shotmark` 与短别名 `preflight-phase371` 已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7667-L7677)（处理入口 [#L7295](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7295)、参数定义 [#L8913](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L8913)、分派 [#L11894-L11898](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L11894-L11898)，`help=` 中 `%` 已全部安全转义且 `--help` 实测返回 `rc=0`），长命令与短别名在干跑模式下生成 **字节级一致的 `report_sha256`**；并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L553-L556) 追加第 `# 68.` 节。

2. **`实测事实`：Waves 79–80 实证合同已建模为 Check Groups A–D 并与 `16/16 H0 == H3` 双介质 `528 B FX3RCPT1` Tier-0 门控闭环**
   - **Check Group A（Wave 79.1–79.3：Zoom Speed 分裂、`[Dial Customize]` 5 项、`[Different Set for Still/Mv]` 8-bit 掩码与零 EVF 边界）**：[`evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py#L1262) 校验 `[Zoom Range]`（`Optical`/`CIZ` `4K 1.5x, HD 2.0x`/`Digital 4.0x`，`Smart Zoom` 仅 Still `M/S`，抗 Reset）与 `[Zoom Ring Rotate]`（抗 Reset）对比可重置三联项 `[Zoom Lever Speed]`（`1st=3, 2nd=8` Stby/REC）、`[Custom Key Z. Speed]`（**仅 Fixed `1..8`，零 `Variable` 模式**）与 `[Remote Zoom Speed]`（`Variable`/`Fix` 经 `BKID_APP_setting_fixed_zoom_speed_type` + `1..8`），以及 CIZ/Digital 在 `RAW`/`100/120p`/`S&Q>=100fps`/HDMI `RAW` 下的硬锁定与 `Focus Area`/`Tracking`/`Face AF` 禁用规则，对比 FX6 `Zoom Type`（零 Digital Zoom）与 `Handle Zoom`（`0..99` 仅 HUD 焦段读数）；校验 `[Dial Customize]` 精确 5 项全抗 Reset（`Custom Key/Dial Set.`、`My Dial 1..3` 临时解锁 `Lock Operation Parts`、`Av/Tv Rotate`、`Function Ring(Lens)` `Power Focus` vs `APS-C/FF`、`Lock Operation Parts`）并拒绝休眠 `Dial Setup`/`Dial/Wheel Lock`/`Rear Dial L/R`；校验 `[Different Set for Still/Mv]` 8 位掩码（`Picture Profile` 勾选框抗 BOTH Reset & Initialize）与 `12+12` `Fn` 槽位、Monitor `[DISP]` 4 个拍摄页（拒绝休眠 `Graphic Display` 与整个 `[Finder/Monitor]`，`fx3_builtin_evf_present = False`），以及 `[Select LUT]`/`[Display LUT]` vs Log 下自动失活的 `[Gamma Display Assist]`。
   - **Check Group B（Wave 79.4：External Output HDMI 4K 10-bit/RAW vs FX6 25 组合 `12G-SDI + HDMI` 双管线）**：[`evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py#L1611) 校验 FX3 `[HDMI Resolution]` 精确 4 项（`Auto`/`2160p`/`1080p`/`1080i`，**零 `720p`**，`fx3_hdmi_720p_supported = False`）、`[4K Output Set.(HDMI Only)]` 精确 6 档 `10bit` `4:2:2`（零 `4:2:0`、拒绝休眠 `24.00p 8bit` 与 `24p/60p Output`、强制 `24.00p` `MODEL_EVENT_REBOOT_BY_CROSS_2400P` 重启门控）、`[HDMI Info. Display] = On` 仅在 `Rec. Media = On & RAW = Off` 时熄灭机内 LCD（`Off(HDMI Only)` 或 `RAW = On` 自动降级 Clean HDMI + 恢复机内 LCD）以及 Sony ELF 3 处著名拼写错误（`BKID_APP_setting_ctrl_for_hmdi`、`PRM_HAITA_hdmi_4k_outpute_apsc_restriction`、`BKID_APP_setting_4ch_output_ch`），对比 FX6 25 组合 `12G/6G/3G-SDI + HDMI` 矩阵与 `SDI/HDMI Remote I/F` vs `Parallel Rec`。
   - **Check Group C（Wave 80.1–80.2：`[TC/UB]` `VMC-BNCM1` 单向 `TC-IN-Only` & `[FTP Transfer Func.]` Explicit `FTPES` / `Slot 1` `.DAT`）**：[`evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py#L1830) 校验全部 7 项 `[TC/UB]` + `[TC/UB Disp. Setting]` 均抗 `[Camera Settings Reset]`（仅 `Initialize` / Delete 键 / FW 升级清零 `Preset`；ELF 原厂勘误 `VAL_setting_tc_make_TC_MAKE_REGENRATE`）、`DF`/`NDF` 仅在 NTSC `29.97p`/`59.94p`/`119.88p` 可选（`23.98p`/`24.00p`/PAL 锁定 `NDF`）、`VMC-BNCM1` 经机身 Multi/Micro USB 单向 `TC-IN-Only`（`Preset` + `Free Run` -> `EXT-LK`，严禁接入 `XLR-H1` 手柄口）对比 FX6 物理 BNC `TC IN/OUT` 开关 + `Clock` 模式 + Hex-only `Users Bit`（`Title1(ASCII)` 系 Clip Title）；并校验 FX3 `[FTP Transfer Func.]`（`Server 1..9`、Passive-only 明文 `FTP` 与 OpenSSL 3.0 `libInfraFtpClient.so` Explicit `AUTH TLS` `FTPES`；**零 SSH-SFTP / 零 Implicit FTPS**；`Slot 1` `cacert.pem` 及密码加密 `SONY/SETTING/<Model>/FTPSET/FTPSET01..10.DAT` + Load 重启均在 Tier-0 `Slot 1` 触发确定性 `EROFS=30`）对比 FX6 `File Transfer`（`Slot B` `certification.pem`、Active/Passive、Chunk Proxy）。
   - **Check Group D + Tier-0（Wave 80.3–80.4 + `16/16 H0 == H3`：`Creators' App` 5-GATT BLE / `G114` `[Airplane Mode]` 勘误 & Playback `Shot Mark`/`Rating`/`Protect`/`Copy` `Slot 1 EROFS=30`）**：[`evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py#L2074) 与 [`_extract_tier0_evidence`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py#L688) 校验 `Creators' App` 5 张 BLE GATT 服务表（`8000CC00`/`DD00`/`EE00`/`FF00`/`BB00`）、Ver. 3.00+ `[Location Info. Link Set.]` 外迁至手机端（`8000DD00`）、`bt_stack.conf` `LMP_WAKEUP_CONFIG`（`[Cnct. while Power OFF]`）、BLE 绑定在 `[Reset Network Set.]` 与 `[Initialize]` 下均被擦除，以及 **Wave 80 `G114` 勘误**（`[Airplane Mode] = On` **不被** `[Reset Network Set.]` 清除，仅 `Initialize` 复位，且零射频台架必须电气隔离 `USB-LAN` 保障 `rf_tx_packets == 0`）；校验 Playback 写盘矩阵（`libmpr.so` / `libInfraFsys.so`：`[Add/Delete Shot Mark 1/2]` 写 `*M01.XML` + `AVF_INFO`、`[Rating]` 写 `<xmp:Rating>`、`[Protect]` 调 `Fsys_Chmod`、`[Delete]` 以及非对称 `[Copy]`——`Slot 1 -> Slot 2` 对 `Slot 1` 只读安全放行，而 `Slot 2 -> Slot 1` 触发 `EROFS=30`，`slot1_sector_writes == 0`）对比 FX6 `Clip Flag`（`OK`/`NG`/`KEEP`），并强制双介质（不同 `st_dev`）`528 B FX3RCPT1` 与 `16/16 H0 == H3` 验签。

3. **`实测事实`：4 模式 `112` 项单元测试、双模 `verify-milestone-364` 与 `clean-audit` 实测全数通过**
   - **Phase 371 四模式 `112` 项单元测试**：[`test_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py)（`2,022` 行，`112` 项测试，`>= 104` 要求，子进程统一设置 `timeout=60`）在 **4 种环境模式** 下全部实测 **`Ran 112 tests -> OK`**（`448/448` 全绿）：
     1. Normal（默认 `LOCAL_DONOR_O_RDONLY`，清除 clean-room 环境变量）：`Ran 112 tests in 116.366s -> OK`；
     2. `FX3_CLEAN_ROOM_TEST=1`：`Ran 112 tests in 54.819s -> OK`；
     3. `FX3_FX6_FORCE_CLEAN_ROOM=1`：`Ran 112 tests in 45.470s -> OK`；
     4. 无供体模式（`FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase371_missing`，且测试内含显式 mock `_resolve_work_root_or_none -> None` 与 `work_root=Path("/nonexistent/...")` 用例）：`Ran 112 tests in 47.349s -> OK`。
   - **Grand Milestone Phase 364 双模总闸门**：
     - `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-364` 双模式（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` `CLEAN_ROOM_SYNTHETIC`）均实测返回 **`status=OK`**、`pillars=6/6`、`gate156=153/156`、`recovery=67/67`、`cnflasha_ro=True`、`otp=0`、`rpmb=0`、`passive_tx=0`、`auditors=45/45`、`vm_stages=83/83`、`preflights=22/22`、`h0_eq_h3=16/16`、`qemu=49/49(147/147)`、`pngs=98/98(max=27467B)`、`leaked=0`、`ready_attach=False`（`milestone364_sha256` 分别为 `55d71ee2a696db12...` 与 `2d8145be548a890a...`）。
   - **洁净度审计**：`PYTHONDONTWRITEBYTECODE=1 make clean-audit` 实测输出 **`[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.05s) / ALL GREEN`**（零 `.pyc` 或未跟踪二进制残留）。

4. **`推断`（未执行物理真机边界声明）**
   - 本阶段全部验证均基于宿主机只读契约模型、`os.O_RDONLY` 有界（`<= 64 B`）供体头核验以及确定性模拟回执（`--simulate-bench-dry-run`），尚未在真实物理 `ILME-FX3` 机身上采集双卡 `528 B FX3RCPT1` 实体回执或执行真机 USB/SD/HDMI/网络/BLE 联机操作，因此所有报告输出均硬锁定 `overall_ready_for_hardware_attach == False`、`live_attach_authorized == False`、`hardware_live_attachment_authorized == False`、`emmc_writes_authorized == False`、`persistent_emmc_writes_authorized == False`、`cross_model_flash_authorized == False`；物理台架联机前仍须以真实双介质 `528 B FX3RCPT1` 验签放行。

---

## 2. 四态确定性 CLI 实测指纹与 6 文件清单（`实测事实`）

### 2.1 CLI 四态 `report_sha256` 实测表

> 以下四态均于当前工作树通过 `/usr/bin/python3 -B -m fx6_closure preflight-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-creatorsapp-ble-and-shotmark ... --json` 与短别名 `preflight-phase371` 实测捕获，长命令与短别名生成的 `report_sha256` 字节级一致（均实测 `8c781f70cfdd3d25510c9a3f278aba40d3ecb6e873b1ffd1c6a56d5c40ffe5f6`）。

| 验证模式（`verification_mode`） | 模拟干跑 | `overall_status` | `go_no_go` | CLI `rc` | 供体读取（`O_RDONLY`） | `raw_firmware_bytes_leaked` | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `1/9`（`64 B`，`fx6_appfw_so=4809d8af884a2ecc`） | `0` | `f377a1aa09426eb1e320459eaab5f81988f6508b899be3e2933bba41e30cadee` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `1/9`（`64 B`，`fx6_appfw_so=4809d8af884a2ecc`） | `0` | `8c781f70cfdd3d25510c9a3f278aba40d3ecb6e873b1ffd1c6a56d5c40ffe5f6` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0/9`（`0 B`） | `0` | `14f92f5609736f9a68780b2eda017a189c8f4b98024d8c9e20051b3cc0ef24bf` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0/9`（`0 B`） | `0` | `af38d4b86f4303069c2ef50b4d383c61f2ec1e93ebc637518cbe4eefc07a309f` |

### 2.2 严格 6 文件所有权修改清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py)（新增，`2,929` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L4180-L4340)（新增 Phase 371 `159` 项非遮蔽导入与 `__all__` 导出 [#L8408-L8566](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L8408-L8566)）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7667-L7677)（新增 `preflight-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-creatorsapp-ble-and-shotmark` 主命令及 `preflight-phase371` 短别名、全量参数 [#L8913](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L8913) 与分派 [#L11894-L11898](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L11894-L11898)）
4. [`outputs/fx6-on-fx3-closure/tests/test_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py)（新增，`112` 项 4 模式单元测试，`2,022` 行）
5. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L553-L556)（追加 Section `# 68.`）
6. [`reports/2026-11-18-phase371-preflight24-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-ble-shotmark/README.md`](./README.md)（本工程闭合报告）

---

## 3. 可复现验证命令与实测结果（`实测事实`）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py"
CMD="preflight-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-creatorsapp-ble-and-shotmark"

# 1. 四模式 112 项单元测试（均已实测 Ran 112 tests -> OK）
env -u FX3_CLEAN_ROOM_TEST -u FX3_FX6_FORCE_CLEAN_ROOM -u FX3_FX6_MAC_WORK_ROOT PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase371_missing PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"

# 2. CLI 门控与别名一致性实测（rc=0 / rc=2 / rc=0 / rc=0 / rc=2 / rc=0）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --simulate-bench-dry-run --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure preflight-phase371 --simulate-bench-dry-run --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure preflight-phase371 --force-clean-room --simulate-bench-dry-run --json

# 3. Milestone 364 双模总闸门与洁净度审计（均已实测 status=OK, pillars=6/6, auditors=45/45, preflights=22/22, leaked=0, ALL GREEN）
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-364
PYTHONDONTWRITEBYTECODE=1 make clean-audit
```
