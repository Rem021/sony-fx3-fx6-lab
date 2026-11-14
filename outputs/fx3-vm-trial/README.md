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

## 离线自动化单元测试（`tests/test_vm_trial.py`）

无需启动任何 QEMU 进程，也无需自备专有固件二进制，即可离线验证编译态 C 扫描线打包器（`fx6_pack_scanlines` 与纯 Python 参考实现逐位一致性）、RGBA PNG 编码与 IEEE CRC-32/IDAT 解压、SVR4 `cpio newc`（`070701`）确定性构建与 `mode/uid/gid` 保持、`src/fx6_live_guest.c` 内存/符号缓存/`DISP`/多语言银行切换回归检查、`outputs/fx3-vm` 补丁与重定位溯源，以及 Phase 23 / Phase 30 / Phase 40 / Phase 49 / Phase 56 端口隔离、多语言 `.uxc` 发现、11 分类 128 页双语菜单搜索直跳（`/api/menu_catalog` & `/api/jump_page`）、`EN/ZH/JA` `GPE0` 像素差自检（`/api/verify_multilang_diff`）、HTTP 客户端断连零堆栈加固（`HardenedThreadingHTTPServer`）、`.cube` 防崩清洗、`XLR-H1` 4-Ch 音频回退、`P4` ND-Clear 锁、Cinema Line 监看辅助叠加（`/api/assist_tools`）与实时 `GPE0` 亮度波形/直方图遥测（`/api/scope_stats`）（共 **103 项**测试，已接入顶层 `make test`，支持正常与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py" -v
```
