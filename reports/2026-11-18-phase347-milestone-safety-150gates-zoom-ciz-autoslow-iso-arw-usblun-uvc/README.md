# Phase 347 工程结项报告：`150/150` 硬件安全门控里程碑（`verify-150-gates`，Wave 65 `G149` + `G150`）

- **日期**：`2026-11-18`
- **任务**：`H432` · **Phase 347（Wave 65 / 150/150 Hardware Safety Gates Milestone）**
- **目标基线**：`ILME-FX3 Ver. 7.02`（`ilc/2210`、`0x0502`、`PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6 Ver. 6.01`（`PRODUCT_MODEL_CHAPLIN`）
- **上游实证依据**：[Wave 65 情报报告](../2026-11-17-global-sony-wave65-zoom-ciz-autoslow-iso-arw-rawcomp-usblun-uvc-intel/README.md)

---

## 一句话结论（结论先行）

**Phase 347 已在 `outputs/fx3-safety/` 端到端交付 `150/150` 硬件安全门控里程碑引擎（`G01..G150` / `verify-150-gates`）**：严格基于 Wave 65 官方 UXC/ELF/内核模块实测依据完成 **`G149`**（变焦三档倍率与 8 档分速 Reset 分化 + `[Auto Slow Shutter]` 7 项互锁 / 抗 Reset `[ISO Range Limit]` / 静态专属 `[ISO AUTO Min. SS]` / 双原生 Base ISO）与 **`G150`**（静态 `.ARW` 100% 休眠 `Lossless Comp` 辟谣 / `[HLG Still Image]` `BT.2100` / `[Sort Recording]` `Slot 1` 防溢写 / `[USB LUN Setting] = Single` **仅暴露 Slot 1** 陷阱与 macOS MSC 防污染 / `NP-FZ100` USB-PD 门控 / `FX3`/`FX6` `UVC` 双辟谣）；离线默认稳态 **`147/150`（`NO-GO / BLOCKED` 待 Tier-0 物理备份）**，`--simulate-bench-dry-run` 与 `--force-clean-room` 下 **`150/150` 全通**，且所有只读红线（`emmc_writes_authorized=False`、`cross_model_flash_authorized=False`、`hardware_live_attachment_authorized=False`、`usb_packets_transmitted=0`、`raw_firmware_bytes_leaked=0`）全链锁死，`milestone324` 与 `milestone311` 均已自动发现 `150` 门控并双模式通过。

---

## 实测事实 vs 推断严格分层

### 1. 实测事实（可直接由代码、ELF/UXC 偏移、内核模块哈希与测试执行验证）

1. **核心交付模块与自动发现接入**：
   - 新增 [realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h432-phase347-milestone-safety-150gates-zoom-ciz-autoslow-iso-arw-usblun-uvc/outputs/fx3-safety/fx3_safety/realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard.py)，向后委托 `evaluate_148gate_preflight()` 并叠加 `G149` + `G150` 生成 `Master150GateReport`（`schema_version = "realhw_150gate_preflight_v1"`）。
   - 已接入 [\_\_init\_\_.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h432-phase347-milestone-safety-150gates-zoom-ciz-autoslow-iso-arw-usblun-uvc/outputs/fx3-safety/fx3_safety/__init__.py)（完整导出至 `__all__`）、[\_\_main\_\_.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h432-phase347-milestone-safety-150gates-zoom-ciz-autoslow-iso-arw-usblun-uvc/outputs/fx3-safety/fx3_safety/__main__.py)（新增 `verify-zoom-ciz-autoslow-baseiso-guard` / `verify-g149`、`verify-still-arw-hlg-usblun-uvc-guard` / `verify-g150` 与 `verify-150-gates`）及 [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h432-phase347-milestone-safety-150gates-zoom-ciz-autoslow-iso-arw-usblun-uvc/outputs/fx3-safety/README.md) 第 75 节。
   - 更新 [test_realhw_breathing_camid_copyright_powersave_ntscpal_148gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h432-phase347-milestone-safety-150gates-zoom-ciz-autoslow-iso-arw-usblun-uvc/outputs/fx3-safety/tests/test_realhw_breathing_camid_copyright_powersave_ntscpal_148gate_guard.py) 中 `test_95`/`test_96` 为前向兼容断言（`>= 148` / `>= 145`），新增 98 项 4 模式单元测试 [test_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_150gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h432-phase347-milestone-safety-150gates-zoom-ciz-autoslow-iso-arw-usblun-uvc/outputs/fx3-safety/tests/test_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_150gate_guard.py)。

2. **Gate `G149` 实测规则落地**：
   - **变焦 Reset 分化**：`[Zoom Range]`（`_f 0x7164`：`Optical zoom only` 默认 / `ClearImage Zoom` 4K `1.5x`、HD `2.0x` / `Digital Zoom` Movie `4.0x`、Still `S` `8.0x`，Movie 禁用 `Smart Zoom`）与 `[Zoom Ring Rotate]`（`_f 0x6be7`：`Left(W)/Right(T)` 默认 / `Right(W)/Left(T)`）均抗 `[Camera Settings Reset]`（`Not available`）；而 `[Zoom Lever Speed]`（`1st=3` 默认 / `2nd=8 Fast` 默认，1..8 分 Standby/Rec）、`[Custom Key Z. Speed]`（1..8 默认 `3`）及 `[Remote Zoom Speed]`（`Variable` 默认 / `Fixed 1..8` 默认 `3`）均可被 Reset（`Can be reset`）。
   - **进入前与激活期互锁**：Still `RAW`、Movie `119.88p/100p`、`S&Q >= 100/120fps` 及 HDMI 16-bit `RAW` 禁用非光学变焦；激活 CIZ/Digital 期间 `[Focus Area]` 禁用并切回中央优先 AF、`[Metering Mode]` 锁定 `[Multi]`、`Face/Eye Prior.` 与 `Tracking` 关闭；对比 `ILME-FX6` 仅暴露 `Optical Zoom Only` / `On(Clear Image Zoom)`（零用户 `Digital Zoom`）与 `Handle Zoom`（`Off/Low=3/High=8/Variable`），任何 `FX6` 伪造请求均以 `EOPNOTSUPP=95` 阻断。
   - **曝光与双原生 Base ISO**：Movie 专属可 Reset 的 `[Auto Slow Shutter]`（`_f 0x76ee`，默认 `On`）在 7 种互斥条件（`S&Q`、`S`、`M`、手动 `ISO`、`Flexible Exp.` 手动快门、`Cine EI`/`Cine EI Quick`、`Shutter Mode = Angle`）下锁定禁用；`[ISO Range Limit]`（`_f 0x69cb`）抗 Reset 且仅限手动 ISO；`[ISO AUTO Min. SS]`（`_f 0x778b`）严格限 Still `P/A + ISO AUTO`（闪光灯下 `1/250 s` 优先，`FX6` 零暴露）；`[Base ISO]`（`_f 0x78ce`）仅在 `Cine EI`/`Cine EI Quick` 显式暴露 `800`/`12800`，其余模式按 Gamma 自动 `20x` 切换（`640/12800`、`100/2000`、`80/1600`、`64/1280`、`50/1000`）。

3. **Gate `G150` 实测规则落地**：
   - **静态 `.ARW` 休眠辟谣与 HLG 静态照片**：`[RAW File Type]`（`_f 0x6ff2`）仅暴露 `Compressed`（默认）与 `Uncompressed`（14-bit `.ARW`），对 100% 休眠 `Lossless Comp (L/M/S)` 返回 `EOPNOTSUPP=95`；`[HLG Still Image]`（`STILL_HLD_PHOTO_{OFF,ON}`）严格要求 `HEIF` + `File Format = HEIF` + `P/A/S/M`，强制 `BT.2100` 且将 ISO 下限升至 `100/125`；`[Sort Recording]` + `[Auto Switch Media]` 满卡回流与静态写盘请求在 `Slot 1` 触发 `EROFS=30`（`slot1_data_sector_writes == 0`）。
   - **`[USB LUN Setting] = Single` 陷阱与 macOS MSC 防火墙**：`[USB Connection Mode]` 4 档（`Sel. When Connect` / `MassStorage(MSC)` / `MTP` / `Remote Shooting`）及 `[USB LUN Setting]` / `[USB Power Supply]` 均抗 Reset；`Multi` 暴露 `Slot 1 + Slot 2`，**`Single`（`_f 0x776d`）暴露“仅 Slot 1”而非隐藏 Slot 1**，且 `MTP` 同样默认映射 `Slot 1`；所有针对 `Slot 1` 的主机 MSC 直连在 Tier-0 保险库层硬阻断（`EROFS=30`，`slot1_data_sector_writes == 0`）。
   - **`NP-FZ100` USB-PD 门控与双 `UVC` 辟谣**：`[USB Power Supply]`（`_f 0x721e`）仅接收 Type-C 供电且 USB-C PD 必须机内插有带电 `NP-FZ100`（无电池供电须 `DC-C1` + `>=65W PD` + `5A e-Marked` 线缆，区别于 `FX6` `19.5V DC IN`）；`FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 均无用户可用原生 `UVC/UAC USB Streaming`（均返回 `EOPNOTSUPP=95`），区分网络推流 `[Movie Rec During Streaming]`（`_f 0x79d5`）与 HDMI `[Rec. Media dur HDMI Output]`（`_f 0x6144`），两者涉及 `Slot 1` 写卡时均触发 `EROFS=30`。

4. **本地只读取证账本与四模式 CI 验证**：
   - `audit_phase347_donor_contracts` 仅以 `os.O_RDONLY` + 精确 `os.pread` 审计 17 个 Wave 65 donor 构件（`FX3 appFw.so` `79,015,712 B` 31 切片、`FX6 appFw.so` `50,520,424 B` 6 切片、`BK4`、4 个 FX3 内核模块、2 个 FX6 内核模块与四语言 UXC 包，`raw_firmware_bytes_leaked == 0`），并在无 donor / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / `work_root=None` 时无缝降级为 `CLEAN_ROOM_SYNTHETIC`。

### 2. 推断（物理硬件与台架边界推断）

1. **macOS `MSC` 挂载 `Slot 1` 污染机制（推断）**：结合 `FX3 usbg_storage.ko` 导出可读写 SCSI/ATAPI 块设备（`atapi_dvd_read_write`、`pInfoLun`）与 macOS `mds`/`fseventsd`/`fsck_exfat` 默认挂载行为推断，即使将相机设为 `[USB LUN Setting] = Single` 以 `MSC` 直连 macOS，宿主仍会向 `Slot 1` 写入 `.Spotlight-V100` / `.fseventsd` 或改写 FAT 脏位；因此必须维持台架 `Slot 1` 禁写 / 主机 MSC 阻断门控。
2. **`[Sort Recording]` + `[Auto Switch Media]` 溢写路径（推断）**：在 `Sort Recording` 定向至 `Slot 2` 的台架场景中，一旦 `Slot 2` 空间耗尽或未就绪，`Auto Switch Media = On` 将切回 `Slot 1` 落盘，因此在未接入物理只读硬件锁前需由软件保险库无条件拦截针对 `Slot 1` 的所有 `.ARW`/`.JPG`/`.HIF` 写入请求。

---

## 验证汇总（实测执行结果）

| 验证门 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| 4 模式 Phase 347 专项测试 | `test_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_150gate_guard.py`（normal / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / `work_root=None`） | `98/98` 全模式通过 |
| `verify-150-gates` CLI 校验 | 离线默认、`--simulate-bench-dry-run`、`--force-clean-room` | 离线 `147/150` (`NO-GO`) / 仿真 `150/150` |
| `outputs/fx3-safety` 全量单测 | 正常模式 + `FX3_FX6_FORCE_CLEAN_ROOM=1`（`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B`） | 正常模式 `4409/4409 OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` `4409` 项 `OK`（`10 skipped` 为早期模块仅本地 donor 用例） |
| Milestone 324 双模式联调 | `make verify-milestone-324`（正常 + `FX3_FX6_FORCE_CLEAN_ROOM=1`） | 自动发现 `150` 门控，`gate142=147/150`，`leaked=0` |
| 产物卫生审计 | `make clean-audit` | `ALL GREEN`，零 `.pyc` |
