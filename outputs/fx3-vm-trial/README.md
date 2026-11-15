# FX3 / FX6 固件菜单本机试用

## 最新成果入口：FX6 固件在 FX3 虚拟机上的 Big6 菜单体验（2026-11-07）

双击 [FX6菜单.command](FX6菜单.command)（或在终端执行 `./FX6菜单.command`），将自动在浏览器打开本机地址 **`http://127.0.0.1:8768/`**：

- **即时体验 Big6 菜单交互**：页面打开即显示已通过 Candidate `255` 实机验证的 `1024×540` RGBA8888 FX6 Big6 HOME 菜单帧（18 次 `GRM_gpermFillrect` + 5 次 `GRM_gpermRectblit`、2560 帧 `0 SEGV`），支持网页 7 键（`MENU` `0x1ab`、`▲ 上` `0x3`、`▼ 下` `0x30`、`◀ 左/右列` `0x15`、`▶ 下一档` `0x1af`、`SET 切换值` `0x1ac`、`REC/C4` `0x1f8`）、点击 6 个 Big6 参数框或使用电脑键盘方向键实时切换 **FPS / Shutter / ISO / ND Filter / Base Look (S-Cinetone / S-Log3) / White Balance / STBY·REC**。
- **QEMU 实机后台会话（可选）**：点击页面右侧 **「启动 FX6-on-FX3 QEMU 实机运行」**，将在后台拉起 FX3 QEMU 虚拟机运行 FX6 固件，通过 GDB 物理内存门（`0x41df00000` `SRM3KYE5` 与 `0x41e000f00` `FX6M`）向客体 `libgrm-fbinit25.c` 注入按键，并通过 QMP `pmemsave 0x41e001000` 实时回读客体 GPE0 显存帧。

- **原生 UI 图标渲染与多击卡死根治（2026-11-14 Phase 19）**：
  - `run_fx6_menu_trial.py` 自动从只读供体打包 `image_00_169.uxc` 512B 对齐 SVR4 `newc` 叠加层至隔离 `--workdir`，`libgrm-fbinit25-542.c` 使用 `/dev/mem` 物理池（`0x410524000..0x410e64000`）满足 `fx3_ldec_soft103_v1` 解码地址校验，`fx6_live_guest.c` 合流 `RGBA4444`/`RGBA8888`/`A8`/`ARGB4444` 贴图渲染与 `fx6_px` `R/B` 通道修复。
  - 修复多击冻结三大根因：直接拦截 `liblibra.so!_ZN5libra20GenerateImageCommand6notifyEb` 防止 `x2=0` 空指针跳转 `PC=0`；`s_vs_pool`/`s_vf_pool`/`s_ic_pool` 升级为 32 槽环形缓冲池并在销毁前排空 `processCommands(0)`；`run_fx6_menu_trial.py` 序列化 `gdb_lock`、清理异步停止回执、在 `finally:` 保证发送 `$c#63` 恢复 VCPU，并在 `get_status()` 检测 `APPFW_SEGV`（标记 `CRASHED_APPFW_SEGV`）。已在隔离端口 `--port 18769` 完成 **60/60** 快速多页连点压力测试（0 `APPFW_SEGV`，19 个页面渲染原生图标）。详情见 [Phase 19 报告](../../reports/2026-11-14-phase19-live-icon-rendering/README.md)。

- **FX3 物理机身按键台（`Stage-B P10`）、实时中英文切换（`🌐 中文 / EN`）与全量 128 页零崩溃扫描（2026-11-14 Phase 23）**：
  - **端口隔离运行目录**：`run_fx6_menu_trial.py` 对 `--port != 8768` 自动启用端口隔离目录（如 `/private/tmp/fx6-live-gpe0-run-18770`）及 `{port}-{pid}` 命名 QMP/GDB socket，保证绝不干扰 `8768` 实时会话。
  - **真机多语言 `.uxc` + CJK 字体实时切换（`GET/POST /api/lang`）**：只读（`O_RDONLY`）打包供体 `string_simplifiedchinese_2.uxc`、`MYingHeiC-GB18030-SJ_wIcon.ltt` 与 `string_japanese_2.uxc` 至 CPIO 叠加层，页面顶部按钮 **`🌐 中文 / EN`** 通过 `mb[16]` 调用客体 `ResourceManager::switchBank`（`bank 4/19/12`）与 `FONT_S_CHINESE`（`0x0200a01c`）实现不停机实时中英文切换。
  - **ILME-FX3 物理按键台（`GET/POST /api/fx3_button`）**：网页新增 `Fn`（Big-6）、`MENU`（3-Layer Menu）、`DISP`（`p16` / `p6` 循环）、`C1`（Base Look）、`C2`（WB）、`C3`（Audio/TC `p17`）、`C4`（Media `p13`）、`C5`（Assignable `p4`）、`C6/PLAY`（Clip Browser `p14`）、`WHEEL UP/DOWN/SET` 与 `BACK/CANCEL`，在状态栏实时展示 `Stage-B P10` 物理码/功能码遥测（`mb[17]`）。
  - **全量 128 页（`fx6_all_pages[0..127]`）长稳零崩溃**：`libgrm-fbinit25-542.c` 为 `FX6_GPE_POOL` 增加 LRU 块回收与归属校验，`fx6_live_guest.c` 增加 16 MiB 预分配图标像素 RAM 缓存，彻底消除连续 ~155+ 帧后 LDEC `-22 destination_range` 溢出；已在 `--port 18770` 完成 **170/170** 连续渲染（24 精选页 + 中英切换 + 14 次 FX3 机身按键 + 128 全量页），`0` 崩溃、`ack_seq == cmd_seq`（`171/171`）。详情见 [Phase 23 报告](../../reports/2026-11-14-phase23-128page-multilang-fx3deck/README.md)。

- **Phase 30 交互式 Cinema Line 参数实时调节、`P4` ND-Clear 硬件锁定与 `P11` 桥接遥测条（2026-11-14）**：
  - **Big-6 主页 & HUD 实时参数渲染（`fx6_live_guest.c`）**：新增无堆分配 `fx6_render_string_text(...)` / `fx6_hud_live_str(...)` 与 `cell_vals[0..5]` + `mb[18]`（`P11` `ibis_idx` / `xlr_idx`），在 Big-6 主页（Page 0）、Setting（Page 2/3）及 Viewfinder HUD（Page 6 / 16 / 17）直接通过 `libuxengine.so` + FreeType 实时重绘 **FPS**（`23.98p..119.88p (S&Q)`）、**Dual Base ISO / Cine EI**（`800/400/1600 EI (800 Base)` ↔ `12800/6400/25600 EI (12800 Base)`）、**Shutter Angle / Speed**（`180.0°..1/100`）、**Base Look / 3D LUT**（`S-Cinetone` / `S-Log3.Cine / S-Gamut3.Cine` / `User1..2 (33³ .cube)`）与 **White Balance**（`5600K..ATW..Mem B`）。
  - **`P4` ND-Clear 硬件契约强制锁定**：在非内置电子可变 ND 的 ILME-FX3 机身上，`Cell 3 (ND Filter)` 始终锁定为 `Clear [FX3 P4 Locked]`；无论通过 `/api/cinema_param` 还是 Big-6 `SET` / `WHEEL_SET` 尝试切换 ND，`mb[8+3]` 均在客体与宿主双端被锁定为 `0`，并在 Web 控制台弹出 `P4` 硬件契约提示横幅。
  - **Web 控制台 `/api/cinema_param` & FX6-on-FX3 硬件桥接遥测条**：新增 `GET/POST /api/cinema_param`（`fps|ei|shutter|nd|lut|wb|ibis|xlr`）、`/api/status` `stage_b_telemetry` 与顶部遥测条，实时展示 **`P1 (/lut->p30)` · `P4 (ND=Clear)` · `P10 (FX3 Keys)` · `P11 (Base ISO 800/12800 + 33³ LUT + XLR-H1 + IBIS Lock)` · `P12 (WF-12 Safe)`**，并支持 `EN / 中文 / 日本語` 一键切换。已在隔离端口 `--port 18771` 完成 **105/105** 连续交互压力验证（0 崩溃、`ack_seq == cmd_seq == 116`，全参数与三语 GPE0 像素差异全通过）。详情见 [Phase 30 报告](../../reports/2026-11-14-phase30-cineei-lut-nd-interactive-trial/README.md)。

- **Phase 40 交互式 `.cube` 3D LUT 防崩溃实时导入、4 通道 `XLR-H1` 音频 VU/回退与 `CAMSET` 场景预设（2026-11-14）**：
  - **防崩溃 `.cube` 3D LUT 导入与 `User1..User4` 槽位（`GET/POST /api/lut_upload`）**：支持直接粘贴/上传 `.cube` 文本或一键导入内置预设（`709_typeA`、`teal_orange`、`film_2383`、`slog3_bypass`）。在写入客体状态前执行全量确定性防崩溃清洗：校验 `LUT_3D_SIZE`（默认仅允许 Sony 标准的 `17` 与 `33`，拒绝 `LUT_1D_SIZE`）、精确 `N³` RGB 三元组行数、零 `NaN`/`Inf`、`DOMAIN_MIN < DOMAIN_MAX` 与 `[0.0, 1.0]` 钳位，以及路径/控制字符拦截；非法载荷按 fail-closed 返回 HTTP `400` + 结构化错误码保护 `libmpr.so::SetLutData`。校验通过后计算 `sha256` 与 `(0.5, 0.5, 0.5)` 三线性中灰 RGB 色块，并通过 `mb[19..25]` 驱动客体 `fx6_live_guest.c` 在 `GPE0` (`0x41e001000`) 实时绘制激活 User LUT 名称与色块（真实非零 `GPE0` 像素变化）。
  - **4 通道 `XLR-H1` 音频增益/VU 表与 `RTMD 0xE304` 遥测（`POST /api/cinema_param` & `mb[26..27]`）**：扩展 `ch1_db..ch4_db`（钳位 `[-60..+12]` dB）、`xlr_phantom_48v`、`xlr_handle_attached` 与 `rtmd_0xe304_ibis_lock`（`ACTIVE_5AXIS` / `OFF_CENTER_LOCKED` / `STANDARD`）。当 `xlr_handle_attached == False` 时，遵循 `P11` `0x91db059b` 契约无崩溃自动回退至 `Internal Stereo` 并更新 `GPE0` HUD 条与 Web VU 电平条。
  - **`CAMSET` 场景预设导出/导入（`GET /api/preset_export`、`POST /api/preset_import`）**：导出含确定性 `preset_sha256` 的 `fx6_on_fx3_camset_v1` JSON 快照；导入恢复完整 Cinema Line / User LUT / 4-Ch 音频 / `RTMD 0xE304` / 语言配置，同时强制执行 `P4` ND-Clear 硬件锁（拦截任何光学/电子 ND 篡改并递增 `p4_nd_reject_count`）及 `P12` `BK4` 飞行模式影子锁。详情见 [Phase 40 报告](../../reports/2026-11-14-phase40-vm-trial-cube-lut-xlr-presets/README.md)。

- **Phase 49 — 128 页双语菜单即时搜索/直跳目录、机内 `EN/ZH/JA` `GPE0` 像素差异自检与 HTTP 断连零堆栈加固（2026-11-14）**：
  - **零堆栈客户端断连加固（`HardenedThreadingHTTPServer` + `make_handler`）**：在 `ThreadingHTTPServer.handle_error` 与 `handle_one_request` / `finish` / `do_GET` / `do_POST` / `_send_bytes` / `_send_json` / `_safe_send_error` 中统一捕获 `BrokenPipeError`、`ConnectionResetError`、`ConnectionAbortedError`、`TimeoutError`、`socket.timeout` 及 `EPIPE`/`ECONNRESET`/`ECONNABORTED`/`ETIMEDOUT` 等 `OSError`，快速刷新浏览器标签或并发中断 `/frame.png` / `/api/frame.png` 拉取不再向终端输出 `Exception occurred during processing of request` 堆栈。
  - **11 大分类 / 128 页中英双语菜单目录与即时搜索直跳（`GET /api/menu_catalog`、`POST /api/jump_page`）**：结构化暴露全部 11 个 FX6 分类、`15` 个旗舰入口（`Big-6 Home`、`Shooting -> Cine EI / S&Q / Shutter`、`Project -> Base Look / Rec Format`、`Paint/Look -> User 3D LUT`、`TC/Media -> Dual CFexpress Slot`、`Monitoring -> Output / Display`、`Audio -> XLR-H1 4ch`、`Thumbnail`、`Technical -> P4 ND Lock / IBIS`、`Network -> P12 Airplane Guard`、`Maintenance -> Version`、`Assignable Buttons Page 110`）以及全量 `fx6_all_pages[0..127]`（含 `zh_title`、`en_title`、`category`、`page_id`、`macro`、`fx3_bridge_note`）。Web 界面顶部新增 `🔍 搜索菜单 / Quick Jump (128 Pages)` 中英文实时搜索栏与一键直跳胶囊。
  - **按需机内三语（`EN -> ZH -> JA`）`GPE0` 像素差异校验器（`POST /api/verify_multilang_diff` & `GET` 缓存回执）**：Web 顶部新增 **`驗 / Verify EN-ZH-JA GPE0`** 按钮；触发后自动切换 `en -> zh -> ja`（并在 `finally` 中严格恢复用户原语言与页面），采集三帧 `1024x540` `GPE0` 物理显存的 `SHA-256` 及成对字节/像素差异（验证 `en_vs_zh_diff_bytes > 0`、`zh_vs_ja_diff_bytes > 0`、`ack_seq` 严格递增）。详情见 [Phase 49 报告](../../reports/2026-11-14-phase49-vm-trial-menu-search-hardening/README.md)。

- **Phase 56 — 机内 Cinema Line 示波器（`📊 Waveform / IRE Scope`）、斑马纹（`70%` / `S-Log3 94%` / `100%`）、峰值对焦（`Peaking`）、画幅线框（`2.39:1` / `1.85:1` / `17:9` / `9:16` / `CenterCross`）与变形宽银幕反挤压（`1.33x` / `2.0x`）（2026-11-14）**：
  - **机内 `GPE0`（`0x41e001000`）曝光与构图辅助叠加（`GET/POST /api/assist_tools`）**：无堆分配复用 `mb[27]` 位段（bits `12..24`，100% 保留 Phase 40 位 `0..11` 与 Phase 19/23/30/49 契约），在客体 `fx6_live_guest.c`（`fx6_render_phase56_assist_overlays`）直接将半透明电影遮幅/角标线（`2.39:1` / `1.85:1` / `17:9` / `9:16` / `CenterCross`）、45° 对角线斑马纹（`70%` / `94%_SLog3` / `100%`）、边缘峰值（`Red` / `Yellow` / `White`）与底部 Cinema Line 状态徽标写入 `0x41e001000` 物理显存，并支持变形镜头反挤压（`1.0x` / `1.33x` / `2.0x`）Web CSS 实时视口预览开关及 `fx6_on_fx3_camset_v1` `CAMSET` 导出/向后兼容导入。
  - **实时 `GPE0` 物理显存亮度波形图与 RGB 直方图遥测（`GET /api/scope_stats`）**：编译态 C 快速核与纯 Python 逐位等价计算 `1024x540x4` 显存的 **32 列 IRE 亮度波形（`min`/`avg`/`max` `0..109%` IRE）**、**16 阶 R/G/B/Luma 直方图**、非零像素占比与高亮/琥珀像素计数（离线测试无 QEMU 时自动无缝回退至 PNG/合成参考帧），在 Web 控制台实时绘制 **`📊 Waveform / IRE Scope`** 双示波器面板。详情见 [Phase 56 报告](../../reports/2026-11-14-phase56-vm-trial-cinema-scopes-markers/README.md)。

- **Phase 64 — Cinema Line 双原生 Cine EI、快门角度 / ECS 消闪、S&Q（1–240fps）、REC Tally 与有线 I/O 控制台（2026-11-14）**：
  - **主机 REST API（`GET/POST /api/cine_exposure` & `/api/status`）**：完整实现 `Base 800`（`200..3200 EI`）与 `Base 12800`（`3200..51200 EI`）各 13 档 EI 及 14.0 档动态宽容度分配（`+6/-8` 基准）；支持 **Shutter Angle**（`5.6°..360.0°`）、**Shutter Speed**（`1/24..1/8000`）与 **ECS LED 墙抗闪烁微调**（`23.98..7900.0 Hz`，如 `100.2 Hz`）；支持 **S&Q `1–240fps`** 变速比率计算（如 `120 / 23.98 -> 5.00x Slow`）及真机一致的 `audio_rec_muted_by_sq` 自动静音契约；支持 `STBY`/`REC` 时间码推进与 4 种 Tally 灯光模式（`on` / `front_only` / `rear_only` / `off` 隐蔽模式）；支持 `usblan_ptpip`（`CDC-NCM + PTP-IP 15740`）与 `hdmi_raw16`（`4264x2408 16-bit Linear RAW + MLUT`）有线 I/O，并严格执行 `P4 ND=Clear` 硬件缺失锁与 `P12` Wi-Fi/BT RF-OFF 飞行模式隔离。
  - **客体 `GPE0`（`0x41e001000`）原生 Cinema Line HUD 叠加（`fx6_live_guest.c`）**：通过扩展控制邮箱 `mb[28..31]` 与 `CINE_EXP` 协议，在客体无堆分配渲染 `REC / STBY + 前后 Tally 指示灯 + TC`、`EI (Base +over/-under)`、快门/ECS 徽标、`S&Q fps (ratio) [CH1-4 MUTE]` 与 `[HDMI RAW16 4.2K]` / `[LAN PTP-IP P12-SAFE]` 徽章。已在隔离端口 `--port 18775` 完成实机 QEMU 像素差异与 `CAMSET`（`/api/camset_export` & `/api/camset_import`）往返验证（`23,926` 像素真实变化，`0` 崩溃，端口 `8768` 零干扰）。详情见 [Phase 64 报告](../../reports/2026-11-14-phase64-vm-trial-cineei-shutter-sq-tally/README.md)。

- **Phase 73 — 实时白平衡（`Shockless WB` / Kelvin / Tint）、Base Look（`S-Cinetone` / `S-Log3`）、双卡槽 `CamID/Reel` 场记与一键 `NonRealTimeMeta M01.XML` 导出（2026-11-14）**：
  - **主机 REST API（`GET/POST /api/color_and_media`、`GET /api/xml_sidecar` & `/api/status`）**：完整支持 `preset_3200k` / `preset_4300k` / `preset_5600k` / `mem_a` / `mem_b` / `atw` 六模式白平衡（FX3 无物理 `B/A/PRST` 拨键，软映射标记 `fx3_wb_switch_soft_mapped: True`）、`[2000, 15000]K`（`50K` 步进）、`[-99, +99]` `CC MG/GR` 绿品偏移与 `Shockless WB`（`off/1/2/3`）；支持 `S-Cinetone` / `S-Log3 / S-Gamut3.Cine` / `S-Log3 / S-Gamut3` / `ITU709` / `709(800%)` / `HLG Live` / `User 3D LUT` 并自动映射 `capture_gamma_equation` 与 `capture_color_primaries`（联动 `User1..User4` `.cube`）；支持 Cinema Line `CamID/Reel/Pos/ClipSeq`（如 `B004C012_261114_FX3B.MP4` + `S03.MP4` 代理）与 4 种双卡槽策略（`simul` / `relay` / `sort_main_proxy` / `single_slot_a`），并在 Phase 64 `sq_enabled == True` 时自动挂起代理录制（`proxy_effective_active = False`、`proxy_auto_suspended_by_sq = True`）。
  - **一键 Sony `NonRealTimeMeta v2.20` `*M01.XML` 边车导出（`GET /api/xml_sidecar`）**：生成可被达芬奇（DaVinci Resolve）与 Catalyst Browse 解析的 `urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20` XML（支持原始 XML 下载与 `?format=json` 预览），实时同步 `Cine EI`、`Base Look`、`White Balance`、快门/S&Q、`.cube` LUT 与 `ILME-FX3` Stage-B 易失 RAM 溯源（`c2pa_spoofed = False`），并纳入 `CAMSET` 导出/向后兼容导入与双语 Web 控制台卡片。
  - **客体 `GPE0`（`0x41e001000`）Cinema Line 遥测徽章（`fx6_live_guest.c`）**：通过扩展控制邮箱 `mb[32..35]`（`0x57424c4d` `'WBLM'`）渲染 WB+Base Look 与双卡槽/ClipID/Proxy 状态胶囊；已在隔离端口 `--port 18776` 实机 QEMU 完成验证（`3200K-5 S-Log3.Cine + B004C012 RELAY` 产生 `27,578` 像素真实变化，开启 S&Q 后 `PRX:OFF(S&Q)` 产生 `21,498` 像素变化，`0` 崩溃，端口 `8768` 零干扰）。详情见 [Phase 73 报告](../../reports/2026-11-14-phase73-vm-trial-wb-look-dualslot-xml/README.md)。

- **Phase 81 — 交互式点击画布追踪 627 点 PDAF 框、`Focus Magnifier x4.0`、`S-Log3` 伪色 / EL-Zone 与 `Clear Image Zoom` 清晰影像变焦（2026-11-14）**：
  - **主机 REST API（`GET/POST /api/touch_focus_ciz` & `/api/status`）**：完整支持 `touch_af_mode`（`off` / `touch_focus` / `touch_tracking` `Real-time Tracking AF`）与 `(touch_x: 0..959, touch_y: 0..539)` 到 `IMX510` `33×19 = 627` 点 PDAF 网格精确映射（`pdaf_col`、`pdaf_row`、`pdaf_index`），并在 `aspect_marker`（`2.39:1` / `1.85:1` / `9:16`）或变形反挤压（`1.3x` / `1.33x` / `2.0x`）存在遮幅黑边时自动识别区外点击（`letterbox_ignored: True`，保持原对焦点不动）；支持 `Focus Magnifier`（`1.0x` / `2.0x` / `4.0x`）以 `(touch_x, touch_y)` 为中心放大 ROI 并保证 `clean_hdmi_unmagnified: True`；支持 `S-Log3` 伪色 / EL-Zone（`3.5%` 紫黑裁切、`41.0%` 绿 18% 灰、`52.0%` 粉肤色 +1EV、`94.0%` 红高光裁切）及 `base_look == "S-Log3*"` + `Zebra 100%` 漏报警告（`slog3_zebra100_clip_warning: True`）；支持 `Clear Image Zoom`（`4K` 上限 `1.50x`，`FHD` 上限 `2.00x`，变焦杆速度 `1..8`）及与 Phase 64 `hdmi_raw16` / `S&Q >= 120fps` 互斥自动钳回 `1.00x`（`ciz_clamped_by_exclusion: True`）。
  - **客体 `GPE0`（`0x41e001000`）原生渲染（`fx6_live_guest.c`）**：通过 `mb[36..39]`（`0x54414643` `'TAFC'`）在 `GPE0` 物理显存直接绘制双框 `[ ⌜ ⌝ ]` Touch-AF 追踪框 + PDAF 徽章、`S-Log3 False Color / EL-Zone` 色带叠加与右侧 IRE/EV 图例条、`[MAG x4.0]` 橙色边界框及 `[CIZ]` 变焦徽章；已在隔离端口 `--port 18777` 实机 QEMU 验证（开启 `touch_tracking@(640,260)` + `slog3_ire` + `CIZ 1.40x` 产生 `312,372` 像素 / `962,395` 字节真实 `GPE0` 变化，`0` 崩溃，端口 `8768` 零干扰）。
  - **Click-on-Canvas 实时画布点选对焦与 `CAMSET` 往返**：Web 控制台新增 `#phase81-touchaf-ciz-card`、**🎯 点击画面触控对焦（Click-Canvas-to-Focus）**开关与 `CAMSET` 向后兼容持久化。详情见 [Phase 81 报告](../../reports/2026-11-14-phase81-vm-trial-touchaf-falsecolor-ciz/README.md)。

- **Phase 88 — 实时 `ShotMark1/2`（`M01.XML` `<EssenceMark>`）、`Cine EI` `Push Auto Iris`（`1/8`-Stop `41% IRE`）与 `ILME-FX6`->`ILME-FX3` 多机位 `CAMSET` 清洗器（2026-11-14）**：
  - **主机 REST API（`GET/POST /api/shotmark_and_iris`、`GET /api/xml_sidecar` & `/api/status`）**：
    - **实时 `ShotMark1`（`OK`）& `ShotMark2`（`KEEP`）场记打点**：支持 `add_shotmark1`、`add_shotmark2`、`clear_shotmarks` 与批量 `shotmarks`（每条剪辑上限 `64` 个、按 `(type, frame)` 去重），并自动注入 `GET /api/xml_sidecar`（`NonRealTimeMeta v2.20`）的 `<KlvPacketTable>` / `<EssenceMark name="_ShotMark1|_ShotMark2" start="<frame>" tc="..." value="OK|KEEP" />`，可直接导入 DaVinci Resolve / Catalyst Browse。
    - **`Cine EI` `Push Auto Iris`（E 卡口 `1/8`-Stop `1.4..22.0`）与测光模式（`multi` / `center` / `spot` / `highlight`）**：按当前 `EI` 与快门参数计算使 `18%` 中灰准确落于 **`41.0% IRE`** 的光圈值（在 `highlight` 模式下优先保障高光 **`< 94.0% IRE`**），全程锁定 `p4_nd_motor_faults: 0`。
    - **4 通道 `24-bit` 安全轨垫音（`ch34_safety_pad_db`: `0` / `-20` dB）与 `SMPTE 12M` `User-Bits`**：支持手动 `AA:BB:CC:DD` 或 `auto_camid_reel` 自动联动 Phase 73 `cam_id` + `reel_num` + `clip_seq`（如 `A0:01:00:01`）。
  - **A-Cam `ILME-FX6` -> B-Cam `ILME-FX3` 多机位 `CAMSET` 清洗器（`POST /api/camset_import`）**：识别 `source_model == "ILME-FX6"`、`sanitize_fx6_fleet == True` 或 FX6 专属字段（`fx6_nd_preset`、`sdi_12g_out`、`wifi_ap_enabled`、`vf_peaking` 等），自动钳位回 `nd_preset -> "Clear"`（`P4`）、`sdi_out -> "CONTAINED_DISABLED"`、`wifi_bt_rf_disabled -> True`（`P12`）并在回执中列出 `sanitized_fx6_fields`，同时 100% 保持非车队模式严格校验向后兼容。
  - **客体 `GPE0`（`0x41e001000`）原生 HUD 徽章（`fx6_live_guest.c`）与双语控制台**：通过 `mb[40..43]`（`'SMRK'`）在 `GPE0` 直接绘制金色 **`[★M1 / ★M2]`** 计数胶囊、**`[F.. AUTO-IRIS 41%IRE]`** 测光徽章及 **`[CH3/4 -20dB SAFE]`** 徽章；已在隔离端口 `--port 18778` 完成实机 QEMU 验证（`71.18s` 就绪，打点 `ShotMark1` + `F4.0 Highlight` + `CH3/4 -20dB` 产生 **`68,453` 字节** `GPE0` 真实像素变化，`0` `APPFW_SEGV`，端口 `8768` 零干扰）。详情见 [Phase 88 报告](../../reports/2026-11-14-phase88-vm-trial-shotmark-pushiris-camset/README.md)。

- **Phase 95 — 变形镜头（`1.3x/1.33x/1.5x/1.8x/2.0x`）IBIS 非对称/居中锁仲裁、Gyroflow `2000Hz` RTMD 就绪遥测与 `1kHz -20dBFS` 基准音/限幅器（2026-11-14）**：
  - **主机 REST API（`GET/POST /api/gyroflow_anamorphic`、`GET /api/xml_sidecar` & `/api/status`）**：
    - **变形镜头反挤压与 FX3 5 轴 IBIS 自动仲裁器**：支持 `squeeze_factor`（`1.0 / 1.3 / 1.33 / 1.5 / 1.8 / 2.0`）与 `ibis_mode`（`Off / Standard / Active / Anamorphic_Asymmetric / Center_Lock_Gyroflow`）；当 `squeeze_factor > 1.0` 且请求未补偿球面 `Active` 时，自动仲裁降级为 `Anamorphic_Asymmetric`（`yaw_gain = 1/squeeze_factor`）或 `Center_Lock_Gyroflow`（`0x0400` 居中锁定），消除边缘果冻晃动，并与 Phase 81 Touch-AF X 坐标逆反挤压联动同步（`desqueezed_touch_x -> touch_x`）。
    - **Gyroflow / Sony Catalyst `2000 Hz` 6 轴 IMU RTMD 就绪遥测与 IMX510 卷帘果冻延迟**：实时计算每帧 IMU 采样数（`83.4 @ 23.98p`、`33.4 @ 59.94p`、`16.7 @ 119.88p`）与传感器读出延迟（`8.7ms` FF 4K / `4.3ms` 4K120），在 S&Q VFR 激活时自动标记 `RTMD_SUSPENDED_BY_SQ`（与真机行为一致），并在 `GET /api/xml_sidecar`（`NonRealTimeMeta v2.20`）中注入 `<Lenses><Lens anamorphicSqueezeFactor=.../></Lenses>` 及 `<AcquisitionRecord>` 的 `AnamorphicGyroflowRtmd` / `AudioReferenceAndLimiter` 元数据组。
    - **`1 kHz -20.0 dBFS` 基准测试音 / SMPTE 彩条 & 4 通道 `24-bit` `-3.0 dBFS` 软拐点限幅器**：`STBY` 待机下可注入 `1kHz -20dBFS` 测试音与彩条，`REC` Tally 激活瞬间自动抑制测试音（`ref_tone_inhibited_by_rec: True`）避免污染实拍音轨；限幅器自动将超出 `-3.0 dBFS` 阈值的通道钳位保护。
  - **客体 `GPE0`（`0x41e001000`）原生 HUD（`mb[44..47]` `'GYRO'`）与四语控制台（`EN / 简体中文 / 繁體中文 / 日本語`）**：`fx6_live_guest.c` 无堆分配渲染变形线框、**`[DSQ ... IBIS:... YAW=...]`**、**`[GYRO .../8.7ms RTMD_READY|SUSP_BY_SQ]`** 与 **`[1kHz -20dBFS TONE / INHIBITED:REC / LIM:-3dB]`** + 7 色 SMPTE 彩条块；支持 `CAMSET` 导出/向后兼容导入。已在隔离端口 `--port 18779` 完成实机 QEMU 验证（`53.33s` 就绪，`2.0x Active -> Anamorphic_Asymmetric` + `1kHz` + Bars + Limiter 产生 **`76,674` 像素**真实 `GPE0` 变化，`1.8x Center_Lock_Gyroflow + REC` 产生 **`33,591` 像素**变化，`S&Q 120fps` 产生 **`46,606` 像素**变化，`0 APPFW_SEGV`，端口 `8768` 零干扰）。详情见 [Phase 95 报告](../../reports/2026-11-14-phase95-vm-trial-gyroflow-anamorphic-tone/README.md)。

- **Phase 102 — 预录制 DDR 环缓（Picture Cache）、电子快门间隔摄影（Interval Rec）、用户 `.cube`（`17³/33³/65³ -> 33³` 四面体）实时上传与有线 USB-LAN FTPS 后台队列（2026-11-14）**：
  - **主机 REST API（`GET/POST /api/interval_cache_lut_ftp`、`GET/POST /api/upload_cube_lut`、`/api/xml_sidecar` & `/api/status`）**：
    - **FX6 Picture Cache（Pre-Rec 环形 DDR 缓存）**：支持 `cache_seconds` ∈ `{0, 2, 4, 8, 16}`，根据当前编解码器与帧率动态核算 DDR 占用并在 FX3 `2048 MiB` 内存上确定性钳位至 **`<= 384.0 MiB`**（如 `8s @ XAVC-I 4K60` 钳位为 `5s / 375.0 MiB`）；当 `S&Q`、`Interval Rec` 或 `HDMI RAW16` 激活时自动挂起并在退出后恢复。
    - **Interval Recording（电子快门保护）**：支持 `interval_rec_enabled`、`interval_sec`（`1..60s`）、`target_shots`（`1..9999`）与 `ae_tracking`（`High / Mid / Low / Lock`），严格强制电子快门（`mechanical_curtain_actuations == 0`，拒绝机械快门篡改）并与 `S&Q` / Picture Cache 互斥。
    - **用户 `.cube` 3D-LUT 清洗器与 `33³` 四面体重采样（`POST /api/upload_cube_lut`）**：解析 `17³ / 33³ / 65³` Adobe `.cube`（`TITLE`、`DOMAIN_MIN`/`DOMAIN_MAX`），对 `NaN`/`Inf`/倒置域或截断载荷执行 fail-closed 拦截（HTTP `400`），仅在易失 RAM 中四面体重采样至 `33³`（`emmc_mutation_bytes == 0`），同步至示波器 `lut_preview` 与 `GET /api/xml_sidecar`（`MonitoringLutTitle`、`MonitoringLutResampled33Sha256` 与 `PictureCacheIntervalCubeFtps` 组）。
    - **有线 USB-LAN FTPS 后台队列（`P12` 射频关闭强制）**：支持 `ftps_mode` ∈ `{Off, Proxy_Only, Original_And_Proxy}`，限定经有线 `CDC-NCM / RTL8153` USB-LAN 传输并强制 `P12` 飞行模式（`wf12_00342260_hits == 0`），拦截一切 `p1..p15` / `nflasha` / `..` 路径穿越请求（HTTP `400`）。
  - **客体 `GPE0`（`0x41e001000`）原生 HUD（`mb[48..51]` `'ICLF'`）与四语控制台（`EN / 简体中文 / 繁體中文 / 日本語`）**：`fx6_live_guest.c` 无堆分配渲染 `[CACHE ... /384M]`、`[INTVL ... E-SH]`、`[LUT U...:... 33^3]` 与 `[FTPS:... P12-LAN]` 徽章；支持 `CAMSET` 导出/导入往返。已在隔离端口 `--port 18780` 完成实机 QEMU 验证（`66.39s` 就绪，Cache `5s/375 MiB` + `17³->33³` `.cube` 产生 **`28,212` 像素**变化，Interval `3/240 E-SH` + USB-LAN FTPS + `p1` 穿越拦截产生 **`31,436` 像素**变化，Viewfinder HUD Page 6 产生 **`352,103` 像素**变化，`0 APPFW_SEGV`，端口 `8768` 零干扰）。详情见 [Phase 102 报告](../../reports/2026-11-14-phase102-vm-trial-picturecache-cube3dlut-ftps/README.md)。

- **Phase 109 — Sony Monitor & Control 4 机位有线 USB-LAN 联机矩阵、HDMI→12G-SDI AVI InfoFrame / SMPTE RP 188 REC 触发桥接、E-Mount/PL 阴影热插拔仲裁与 C2PA 2.1 / `cnflasha` 零接触溯源护盾（2026-11-14）**：
  - **主机 REST API（`GET/POST /api/mc_fleet_sdi_c2pa`、`GET /api/xml_sidecar` & `/api/status`）**：
    - **Sony Monitor & Control 4 机位千兆有线 USB-LAN 联机与 Gang-REC 矩阵**：支持 `fleet_role` ∈ `{'Solo', 'A_Cam_Master', 'B_Cam_Follower', 'C_Cam_Follower', 'D_Cam_Follower'}`、`fleet_cams_online`（`1..4`）及 `gang_rec_trigger`，通过有线 `CDC-NCM / RTL8153 / AX88179` PTP-IP 同步 Phase 64 REC Tally，同时强制 `P12` Wi-Fi/BT 射频关闭（`wf12_00342260_hits == 0`），fail-closed 拒绝一切非零射频或无线请求（HTTP `400` `p12_rf_off_violation`）。
    - **HDMI CEA-861 AVI InfoFrame 与 HDMI→12G-SDI Active Converter REC 触发桥接**：实时合成 17 字节 CEA-861 AVI InfoFrame 十六进制载荷与校验和（`0x100 - sum == 0`），按当前 `S-Log3 / S-Cinetone / 709 / HDMI RAW16` 映射量化范围（阻断外部录机合法/满格范围暗部死黑挤压），并在 REC Tally 切换时同步 `SMPTE RP 188`（`DID=0x60 / SDID=0x60`）SDI 触发比特。
    - **E-Mount 12-Pin 电子触点 vs 无芯片 PL 卡口热插拔阴影仲裁器**：支持 `mount_type` ∈ `{'Sony_EMount_12Pin_GM', 'Manual_PL_Adapter_Unchipped'}`；切换至无芯片 PL 卡口时在 `<1` 帧内强制将径向暗角/色差/呼吸效应补偿归位为 `1.00x` 单位矩阵，当 `lens_kg > 1.2` 且未启用 `rod_support_15mm_lws` 时触发 `G31` 15mm LWS 导管支撑告警。
    - **C2PA 2.1 / `cnflasha` 零接触洁净室研究溯源护盾**：锁定 `c2pa_vault_status == 'CNFLASHA_RDONLY_ZERO_TOUCH'`（`private_key_reads == 0`、`cnflasha_writes == 0`、`hardware_attestation_claimed == False`），fail-closed 拦截任何私钥读取/重写/`cnflasha` 写入/真机签名伪造请求（HTTP `400` `c2pa_cnflasha_zero_touch_blocked`），并在 `/api/xml_sidecar` 中注入诚实的研究溯源元数据 `<Group name="McFleetSdiAndC2paProvenance">`。
  - **客体 `GPE0`（`0x41e001000`）原生 HUD（`mb[52..55]` `'MCFL'`）与四语控制台（`EN / 简体中文 / 繁體中文 / 日本語`）**：`fx6_live_guest.c` 无堆分配渲染 `[M&C A-MST 4/4 GANG-REC P12]`、`[SDI:... RP188:... AVI:OK]`、`[E-12P / PL-0PIN SHD:1.00x-ID ... G31:LWS!]` 与 `[C2PA:RO-ZERO-TOUCH KR=0 CW=0]` 徽章；支持 `CAMSET` 导出/导入往返。已在隔离端口 `--port 18781` 完成实机 QEMU 验证（`81.5s` 就绪，S-Log3 + `A_Cam_Master 4/4` Gang-REC + BMD 12G SDI 产生 **`51,214` 像素**变化，PL 热插拔 `1.00x` 归位 + `1.8kg` `G31` 告警产生 **`9,732` 像素**变化，Viewfinder HUD Page 6 + C2PA 拦截产生 **`367,761` 像素**变化，`0 APPFW_SEGV`，端口 `8768` 零干扰）。详情见 [Phase 109 报告](../../reports/2026-11-14-phase109-vm-trial-mcfleet-sdi-c2pa/README.md)。

- **Phase 116 — HLG1/HLG2/HLG3 ITU-R BT.2100 (ARIB STD-B67)、Gamma Display Assist 洁净 HDMI/SDI 隔离、CTA-861.3 (`0x87`) HDR InfoFrame、外部 ProRes RAW / BRAW 16->12-Bit Log 与呼吸效应补偿 HUD（2026-11-14）**：
  - **主机 REST API（`GET/POST /api/hdr_hlg_raw_breathing`、`GET /api/xml_sidecar`、`CAMSET` 导出/导入与 `/api/status`）**：
    - **HLG1/HLG2/HLG3 BT.2100 & `CTA-861.3 (0x87)` HDR 静态元数据打包**：支持 `HLG1`（`87%` / `~925 nit`）、`HLG2`（`95%` / `~1000 nit`）、`HLG3`（`100%` / `~1090 nit`）与 `FX6_HLG_LIVE / FX6_HLG_NATURAL`、`BT.2020 / BT.709` 色域、Knee（`Auto/87%/95%/100%`）与 Detail（`-7..+7`）；实时合成 30 字节 `CTA-861.3 (0x87)` HDR Static Metadata InfoFrame（`EOTF=3 HLG_ITU_R_BT2100`、精确 `(sum % 256) == 0` 校验和），Fail-Closed 拦截将 `BT.2020` 装入 `BT.709` 容器的标签错配（HTTP `400` `bt2020_in_bt709_container_blocked`）。
    - **Gamma Display Assist VF/LCD 隔离护盾**：支持 `OFF / AUTO / S-Log3->709(800%) / HLG->709(BT.2020) / HLG->709(709)`，硬性强制 `clean_hdmi_sdi_unassisted == True`、`xavc_internal_unassisted == True` 与 `external_output_assist_leak_px == 0`；任何试图将 Display Assist 烘焙进外部 HDMI/SDI 或内部 XAVC 的请求均按 Fail-Closed 返回 HTTP `400`（`display_assist_clean_feed_leak_blocked`）。
    - **外部 HDMI 16->12-Bit Log RAW 与 Focus Breathing Compensation 呼吸效应补偿**：支持 `Atomos ProRes RAW` 与 `Blackmagic BRAW` `16->12-bit Log` 携带 `Base ISO 800/12800`、`Kelvin` 与 E-Mount 镜头元数据（双向联动 `wired_io_mode == "hdmi_raw16"`）；支持 E-Mount 12-Pin 焦段动态裁切（`1.02x..1.08x`），并在切换至无芯片 PL 卡口或启用外部 HDMI RAW 时自动降级回 `1.00x` 旁路。
    - **`NonRealTimeMeta M01.XML` 与 `CAMSET` 往返**：自动覆盖 `CaptureGammaEquation=rec2100-hlg`、`CaptureColorPrimaries=rec2020`，注入 `<Group name="HlgBt2100AssistRawBreathing">`，并完整支持 `CAMSET` 导出/严格校验导入。
  - **客体 `GPE0`（`0x41e001000`）原生 HUD（`mb[56..59]` `'HLGA'`）与四语控制台（`EN / 简体中文 / 繁體中文 / 日本語`）**：`fx6_live_guest.c` 在 `0x41e000e00 + 0xE0..0xEC` 零堆分配渲染 HLG/Nits/CTA `0x87` 徽章、Display Assist Clean-Out 隔离状态、ProRes RAW / BRAW 16->12L 徽标、呼吸效应裁切比与亮度波形柱（并在客体端硬锁定 Clean HDMI/SDI 位与 PL/RAW `1.00x` 旁路）；Web 控制台新增四语 `#phase116-hlg-raw-breathing-card`。已在隔离端口 `--port 18782` 完成实机 QEMU 验证（`37.73s` 就绪，HLG3 BT.2020 + Assist AUTO 产生 **`36,768` 像素**变化，ProRes RAW 16->12L 产生 **`24,199` 像素**变化，BRAW Base12800/3200K 产生 **`13,062` 像素**变化，E-Mount 50mm `1.06x` vs PL `1.00x` 旁路分别产生 **`24,145`** 与 **`37,687` 像素**变化，Page 6 Viewfinder HUD 产生 **`381,966` 像素**变化，`0 APPFW_SEGV`，端口 `8768` 零干扰）。详情见 [Phase 116 报告](../../reports/2026-11-14-phase116-vm-trial-hlg-bt2100-proresraw-breathing/README.md)。

- **Phase 123 — Live QEMU FX6-on-FX3 USB-C UVC 1.5 / UAC 2.0 洁净推流、有线 `P12` 安全 SRT/RTMPS（AES-128/256, ARQ）与 CRSDK PTP / PTP-IP 遥控及销毁指令防火墙 HUD（`'UVCS'` `mb[60..63]`）（2026-11-14）**：
  - **主机 REST API（`GET/POST /api/uvc_srt_crsdk_ptp`、`GET /api/xml_sidecar`、`CAMSET` 导出/导入与 `/api/status`）**：
    - **USB-C UVC 1.5 / UAC 2.0 洁净输出与 USB 2.0 `480 Mbps` 自动降档**：支持 `OFF / UVC_4K30P_MJPEG_5G / UVC_1080P60P_YUY2_5G / UVC_720P30P_MJPEG_USB2_FALLBACK` 及 `UAC 48kHz 16-bit 2ch PCM`；检测到非 SuperSpeed USB 2.0（`USB2_480M`）线缆时，客体与主机双端自动降档至 `UVC_720P30P_MJPEG_USB2_FALLBACK`（`1280x720@30p MJPEG, 35 Mbps`）；硬锁定洁净无 OSD 烧录输出（`uvc_clean_feed_no_osd == True`、`uvc_osd_burnin_px == 0`），Fail-Closed 拦截一切 OSD 烧录请求（HTTP `400` `uvc_osd_burnin_blocked`）。
    - **有线 `CDC-NCM` `SRT` & `RTMPS TLS 1.3` 推流（客体硬强制 `P12` Wi-Fi-OFF）**：支持 `SRT_CALLER / SRT_LISTENER`（`PBKEYLEN` `NONE / AES-128 / AES-256`，ARQ 延迟 `20..1000 ms`）与 `RTMPS_TLS13`（`1..50 Mbps`，拒绝明文 RTMP）；客体 `fx6_live_guest.c` 与主机双端硬强制 `p12_wlan_off = 1`、`wf12_00342260_hits = 0`，Fail-Closed 拦截一切 `use_wifi` / `wlan0` / `bt` 射频请求（HTTP `400` `p12_wlan_off_enforced`）。
    - **Sony `CRSDK` `PTP / PTP-IP`（`0x054C` / TCP `15740`）遥控与破坏性 Flash 指令防火墙（`0x9280..0x92FF`）**：放行安全 `0xD2xx` 属性控制（`0xD20D` 快门、`0xD210` `Cine EI / Base ISO 800/12800`、`0xD21C` WB、`0xD220` Look/LUT、`0xD224` `P4 ND-Clear` 钳位、`0xD2C1` Touch AF、`0xD2C4` REC 触发）；Fail-Closed 拦截所有破坏性固件刷写/eMMC 篡改指令（`0x9280..0x92FF`、`0x9201..0x920F` 及 `firmware_flash` / `emmc_write` / `nvram_tamper` 动作，HTTP `400` `ptp_flash_opcode_blocked`，锁定 `emmc_mutation_bytes == 0`）。
    - **`NonRealTimeMeta M01.XML` 与 `CAMSET` 往返**：注入 `<Group name="UvcSrtRtmpsAndCrsdkPtpFirewall">`，完整纳入 `CAMSET` 导出/严格校验导入。
  - **客体 `GPE0`（`0x41e001000`）原生 HUD（`mb[60..63]` `'UVCS'`，物理偏移 `240..255`）与四语控制台（`EN / 简体中文 / 繁體中文 / 日本語`）**：`fx6_live_guest.c` 零堆分配渲染 UVC/UAC 洁净推流徽章、有线 `CDC-NCM` SRT/RTMPS `P12=1` 状态徽章、`CRSDK` `0x054C` 与 `Flash-Opcode` 防火墙横幅条，随 `FX6_LIVE_FRAME ... UVCS=...` 实时回传；Web 控制台新增四语 `#phase123-uvc-srt-crsdk-ptp-card`。已在隔离端口 `--port 18783` 完成实机 QEMU 验证（`47.4s` 就绪，UVC 4K30p + SRT Caller AES-256 + PTP-IP 产生 **`55,957` 像素**变化，USB2 480M 降档 + RTMPS TLS1.3 + `0x9280` 刷写拦截/P12 Wi-Fi 拦截/OSD 烧录拦截产生 **`48,217` 像素**变化，Page 6 Viewfinder HUD 产生 **`342,009` 像素**变化，`0 APPFW_SEGV`，端口 `8768` 零干扰）。详情见 [Phase 123 报告](../../reports/2026-11-14-phase123-vm-trial-uvc-srt-crsdk-ptp/README.md)。

技术报告与逆向记录见 [2026-11-07 FX6 UXEngine 初始化与 Big6 菜单渲染报告](../../reports/2026-11-07-fx6-uxengine-init-assist/README.md) 及 [EVIDENCE-255-MENU.md](../../reports/2026-11-07-fx6-uxengine-init-assist/EVIDENCE-255-MENU.md)。

---

## FX3 原厂菜单入口（2026-11-04）

双击 [FX3菜单.command](FX3菜单.command)，打开终端打印的本机网址，再点击网页 **开始本轮模拟器**。端口每轮可能不同。每次按键后看清目标画面，网页提示时点击 **我已看清当前完整画面，继续**。结束时点击 **结束试用** 或在本轮终端按 **Ctrl-C**，等待回执输出。

新版默认 **4096 次按键／60 分钟**，已部署；已完成一轮真实浏览器 **32 键、约 11 分 14 秒**导航及独立的 Finder 启动／Ctrl-C 退出验收。

[完整使用说明](使用说明.md) · [新版验收记录](新版验收记录.md)

## 保留的 TRY2 入口与开发状态

[FX3菜单TRY2.command](FX3菜单TRY2.command) 保留原样，仍有 **30 键／15 分钟**限制。该限制来自旧宿主参数，不是 FX3 硬件限制。历史试用曾出现持续导航后的原生省电关机；增加新版上限不等于解决省电行为。旧入口与记录见 [TRY2 使用说明](TRY2-使用说明.md)，不作为新版启动入口。

## 旧 TRY1 入口

这是在 QEMU 中运行的 FX3 原厂菜单，复用已验证的 AP101-r4 模拟器。需要本机已部署内盘 `~/AI-Workspace/AI/Projects/Mac/work`（或挂载回退路径），并使用现有 Python 3。每次启动都会从固定保存文件冷启动。

在终端运行，保持终端开启：

```sh
python3 -B ~/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/run_trial.py
```

打开 **[http://127.0.0.1:8765](http://127.0.0.1:8765)**。等待“固件已就绪”，再按 **MENU** 打开菜单；冷启动及首次打开菜单可能需要几分钟，请等画面更新再继续操作。网页约每 0.4 秒查看新帧，只有固件提交了新画面才更新。画面高亮可能不可见，建议每次只按一下并观察标题、页码和项目文字。

| 网页按钮 | 机身按钮模拟码 |
|---|---|
| 上 / 下 | `0x3` / `0x30` |
| 左 / 右 | `0x15` / `0x1af` |
| 确定 | `0x1ac` |
| MENU | `0x1ab` |
| 删除 / C4 | `0x1f8` |

每次按键持续 100ms，每轮最多 **30 次**。点击网页的 **“结束试用”**，或在启动终端按 **Ctrl-C**。等待终端显示回执及退出检查结果后即可关闭；关闭网页本身不会退出模拟器。默认最长 **60 分钟**，到时自动收尾。端口冲突时可用 `--port 8766`，并打开终端打印的新网址；也可用 `--max-minutes 10` 缩短上限。已有运行占用锁时会直接拒绝启动，避免互相干扰。

当前限制：**高亮可能不可见、部分底色缺失和文字叠印、无实时取景、语言修改暂未确认落盘、画面为近似混合**。下一轮仍从固定保存文件启动；画面和菜单试用不代表拍摄、录像或实体相机硬件已完成模拟。出现原厂断言、异常或当前模型不支持的请求时，网页会提示并停止接收按钮，随后退出和保存证据。

网页仅监听本机 `127.0.0.1`。原始固件和已完成的运行目录保持只读；每轮日志、按钮记录、提交帧证据和退出回执分别保存到新建的 `work/fx3-vm-20261101/menu-repair-01/runtime/runs/try1-*`。退出会核对原 API 16 字节恢复、QEMU 退出码、进程回收、输入 SHA 和锁释放。

技术参考：[QEMU 监视器](https://www.qemu.org/docs/master/system/monitor.html)、[Python 本地 HTTP 服务接口](https://docs.python.org/3/library/http.server.html)。这些接口仅用于宿主机控制与观察，设备模型沿用冻结基线。

验证记录：[实际网页菜单截图与退出回执](../../reports/2026-11-01-fx3-vm-resumed-repair/try1-local-ui-trial.md)。已完成待机→MENU→菜单→网页结束，以及独立一轮Ctrl-C收尾；自测实例均已退出。

---

## 离线自动化单元测试（`tests/test_vm_trial.py`, `tests/test_phase64_cine_exposure_deck.py`, `tests/test_phase73_wb_look_dualslot_xml.py`, `tests/test_phase81_touchaf_falsecolor_ciz.py`, `tests/test_phase88_shotmark_pushiris_camset.py`, `tests/test_phase95_gyroflow_anamorphic_tone.py`, `tests/test_phase102_picturecache_cube3dlut_ftps.py`, `tests/test_phase109_mcfleet_sdi_c2pa.py`, `tests/test_phase116_hlg_bt2100_proresraw_breathing.py` & `tests/test_phase123_uvc_srt_crsdk_ptp.py`）

无需启动任何 QEMU 进程，也无需自备专有固件二进制，即可离线验证编译态 C 扫描线打包器（`fx6_pack_scanlines` 与纯 Python 参考实现逐位一致性）、RGBA PNG 编码与 IEEE CRC-32/IDAT 解压、SVR4 `cpio newc`（`070701`）确定性构建与 `mode/uid/gid` 保持、`src/fx6_live_guest.c` 内存/符号缓存/`DISP`/多语言银行切换回归检查、`outputs/fx3-vm` 补丁与重定位溯源，以及 Phase 23 / Phase 30 / Phase 40 / Phase 49 / Phase 56 / Phase 64 / Phase 73 / Phase 81 / Phase 88 / Phase 95 / Phase 102 / Phase 109 / Phase 116 / Phase 123 端口隔离、多语言 `.uxc` 发现、11 分类 128 页双语菜单搜索直跳（`/api/menu_catalog` & `/api/jump_page`）、`EN/ZH/JA` `GPE0` 像素差自检（`/api/verify_multilang_diff`）、HTTP 客户端断连零堆栈加固（`HardenedThreadingHTTPServer`）、`.cube` 防崩清洗与 `17³/33³/65³ -> 33³` 四面体 RAM 重采样（`/api/upload_cube_lut`）、`XLR-H1` 4-Ch 音频回退、`P4` ND-Clear 锁、Cinema Line 监看辅助叠加（`/api/assist_tools`）、实时 `GPE0` 亮度波形/直方图遥测（`/api/scope_stats`）、Cinema Line Cine EI / Shutter-ECS / S&Q 1–240fps / REC Tally / 有线 I/O（`/api/cine_exposure`）、实时白平衡 / Base Look / 双卡槽 CamID-Reel / `NonRealTimeMeta M01.XML` 导出（`/api/color_and_media`, `/api/xml_sidecar`）、交互式 Click-to-Track 627-pt PDAF / Focus Magnifier x4.0 / S-Log3 False Color-EL-Zone / CIZ（`/api/touch_focus_ciz`）、实时 `ShotMark1/2` `<EssenceMark>` / `Push Auto Iris`（`41% IRE` / `<94% IRE`）/ 4-Ch `-20 dB` 安全轨与 `SMPTE 12M User-Bits`（`/api/shotmark_and_iris`）、`ILME-FX6` -> `ILME-FX3` 多机位 `CAMSET` 清洗器（`/api/camset_export`, `/api/camset_import`）、变形镜头（`1.3x–2.0x`）IBIS 非对称/居中锁仲裁、Gyroflow `2000Hz` RTMD 就绪遥测与 `1kHz -20dBFS` 基准音/限幅器（`/api/gyroflow_anamorphic`）、预录制 DDR 环缓（`<= 384 MiB` on `2048 MiB` DRAM）/ 电子快门间隔摄影（`mechanical_curtain_actuations == 0`）/ 有线 USB-LAN FTPS 后台队列与 `p1..p15` 路径穿越拦截（`/api/interval_cache_lut_ftp`）、Sony M&C 4 机位有线 USB-LAN Gang-REC 矩阵 / HDMI→12G-SDI CEA-861 AVI InfoFrame & RP 188 REC 触发 / E-Mount 12-Pin 与无芯片 PL 阴影归位仲裁 / C2PA 2.1 `cnflasha` 零接触溯源护盾（`/api/mc_fleet_sdi_c2pa`）、HLG1/HLG2/HLG3 BT.2100 / CTA-861.3 (`0x87`) HDR InfoFrame / Gamma Display Assist 洁净 HDMI-SDI 隔离 / 外部 ProRes RAW & BRAW 16->12L / 呼吸效应补偿互锁（`/api/hdr_hlg_raw_breathing`），以及 USB-C UVC 1.5/UAC 2.0 洁净推流与 USB2 480M 自动降档、有线 P12-Safe SRT/RTMPS 与 CRSDK PTP + `0x9280..` 销毁指令防火墙（`/api/uvc_srt_crsdk_ptp`）（共 **367 项**测试，已接入顶层 `make test`，支持正常与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py" -v
```
