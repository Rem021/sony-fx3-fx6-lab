# Phase 18 跨代际 AP（FX6 6.01）↔ Stock-CP（FX3 7.02）影像核心链路协议级审计与验证报告

- **任务代号**：`Hydrogen-4`｜Phase 18（CMOS / 双原生 ISO / Cine EI / 3D LUT / XAVC 编码 / E 卡口 AF / 五轴 IBIS 防抖）
- **架构红线**：Stage-A 混合架构 `U2` 原厂 CP 红线（`p8_cp_mutation_forbidden = True`，`cp_mutation_bytes = 0`）
- **AP 侧运行软件**：FX6 Ver. 6.01 `im.elf` + `appFw.so` + `libmpr.so` + `libInfraLensCommunicator.so`（Linux AArch64）
- **CP 侧运行软件**：FX3 Ver. 7.02 原厂 `p8:/cpapp-b.bin`（TOPPERS-FMP 1.4.0 ARM32 SMP RTOS `@ 0x00108000`）
- **验证器源码**：[`ap_cp_imaging_pipeline_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/ap_cp_imaging_pipeline_verifier.py)
- **单元测试集**：[`test_phase18_ap_cp_imaging.py`](../../outputs/fx6-on-fx3-closure/tests/test_phase18_ap_cp_imaging.py)（18 项测试，实机只读 Donor 模式 + `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室模式双通过）

---

## 一、全量结论摘要

| 核验维度 | 定量结论 | Stage-A 处置 / 风险等级 |
|---|---|---|
| **1. `SeqQueue*` / UIPC 跨机型阻塞扫描** | FX6 `appFw.so` 通过 `MOVZ/MOVK` 共构造 **38** 个 `0x9xxxxxxx` 队列；FX3 7.02 CP 与 FX6 6.01 CP 在 Thumb-2 `MOVW/MOVT` 层面分别注册 **254** / **299** 个 `0x9xxxxxxx` 句柄。`0x92840747` 端点上 `send_and_wait_cmp_i` 发出的全部 **44** 个 `0x200d` 操作码（含 `0x032d`、`0x0400/0x0402/0x0404/0x0152`、3D LUT DMA `0x0165`/`0x0166`、`0x016b`、`0x016c`、`0x0416`、`0x0426`、`0x0428`）在 FX3 7.02 `cpapp-b.bin` 中 **44/44 全部命中 `op \| 0x1000` 应答分派**。精准定位 **仅 2 个** FX6 独占 CP 队列在 FX3 `cpapp-b.bin` 中零命中：**`0x92d2091c`**（RTC 状态同步，`std::future<bool>::wait()` **永久阻塞**）与 **`0x91db059b`**（Smart Handle/Grip 回调注册）。 | **中危可控**：AP-CP 拦截桥新增 **`0x92d2091c`** 与 **`0x91db059b`** 合成应答即可清零未知挂起；已实跑 Unicorn 验证 `0x92d2091c` 挂起与 `0x03 0x00` 解除阻塞。 |
| **2. CMOS / 双原生 ISO / Cine EI / 33³ 3D LUT DMA** | FX3 7.02 `libmpr.so` 与 FX6 6.01 `libmpr.so` 中 `mpr::SetLutData`（`0xd484c` vs `0x1505a8`，均为 **164 B**）及 `mpr::ExecuteSetLutData`（`0xd4668` vs `0x150358`）保持 **ABI 同源一致**：均分配 **`0x6a1b9` = 434,617 B** 解析 `33³ .cube` LUT，并按 `+0x04` 开关、`+0x05..+0x1e`（26 B 元数据）与 `+0x1f..+0x5e`（64 B 路径）写入状态槽。`appFw.so::video_set_lookname_procam` 通过 `0x92840747` 发送 `0x0165`（36 B DMA，阈值 `0xbb80 = 48,000 B` 区分 SRAM/Reg）与 `0x0166`（10 B 启停）。FX3 CP 具备完整 CXD90057 ISP MLUT/EI 驱动符号及双原生 ISO（800 / 12800）管线；仅 LiroSeq 字符串键名存在局部差异（`uc_HighGainMode`/`ul_EIGainValue` vs `HyperGainMode`/`EIValue`），通过共享 `baseSensitivity` 与 `Base_Picture_Setting_*` 对齐，且可按需补充桥接映射。 | **原生兼容（High）**：Unicorn 实执行 FX6 & FX3 `mpr::SetLutData`（3 分支 × 2 机型 = 6 用例）全部通过，26 B + 64 B 拷贝字节零偏差。 |
| **3. XAVC-I / XAVC-L 录制与 E 卡口自动对焦** | `libInfraLensCommunicator.so`（**14,544 B**）在 FX3 7.02 与 FX6 6.01 间 `.plt` / `.text` / `.rodata` / `.data` / `.dynsym` **完全逐字节一致（0 字节差异）**，全文仅 `.comment` GCC 编译时间戳差异 **6 字节**，E 卡口 AF 线协议 100% 等同。`mpr::SetMovieRecParam` 在 FX6 侧扩展至 **2,248 B**（`0x8c8`）以承载 AP 侧 `GetDProXavcIntraVQuality` / `libXavcMxf::SetClipName`（`codec=8`），FX3 侧为 **445 B**（`0x1bd`）。FX3 7.02 已原生合入 DCI 4K（4096×2160 XAVC S-I），QFHD XAVC-I/XAVC-L 与 S&Q 120p 均由 FX3 CP `mov_size_req` / `frate_req` / `e_set_img_frame_size` 支持；仅 1080p 下 FX6 CP 独有 `developing_mode_FHD` 校验键需设置参数守卫。 | **AF 100% 兼容；XAVC 4K/DCI4K/S&Q 原生支持**：FHD 需留意 `developing_mode_FHD` 守卫。 |
| **4. FX3 五轴 IBIS 机身防抖执行器安全性** | FX3 CMOS 悬置于五轴音圈防抖浮动平台，FX6 CMOS 为刚性固定（`appFw.so` 携带 `PRM_is_imager_stabilization_unit_fixed` 且无 `set_steadyshot_advanced_movie_i`）。**关键物理证据**：FX3 7.02 原厂 `cpapp-b.bin` 在启动阶段自行执行 `LiroSeq: Restore.` 加载本机未触碰的 `p2:/Backup.bin` + `p2:/psd.bin` + `p6:Jiritsu`，独立运行五轴 **HallPIDOUT / GyroPIDOUT / FusionOUT / AllPIDOUT / PWMOUT** 闭环伺服与 `FWCP-isRetract` / `steadyshot_body_axis`，保持物理音圈平台**通电居中锁止（Standard Center-Lock）**；且 FX6 `appFw.so::set_tc_mode_i` / `set_tc_on_movie_i` 与 FX3 CP 共享 `is_mode` / `is_on_movie` / `is_type` 键控制 OSS/IS 基本开关。因此在 Stage-A 下 **FX3 传感器不会自由下垂偏心或撞击机械限位**；仅主动防抖（Active IBIS）动态 UI 调节需后续在 AP 侧补建菜单桥接。 | **物理安全已证伪风险（Safe in Standard Center-Lock）**：仅 Active IBIS 高级开关待后续适配。 |

---

## 二、Pillar 1：全量 `SeqQueue*` / UIPC 阻塞型请求跨机型扫描

### 2.1 `0x9xxxxxxx` 队列跨端指纹总览

- **FX6 `appFw.so`**（`fx6-donor/nflasha15-files/lib/appFw.so`）：通过 AArch64 `MOVZ Rd, #lo; MOVK Rd, #hi, lsl #16` 静态解码出 **38** 个 `0x9xxxxxxx` 队列常数。
- **FX3 7.02 `cpapp-b.bin`**（`sony-firmware-20261024/.../cpapp-b.bin`）：Thumb-2 `MOVW/MOVT` 共匹配 **254** 个 `0x9xxxxxxx` 句柄地址（含 135 个独立队列 ID）。
- **FX6 6.01 `cpapp-b.bin`**（`fx6-donor/fat-files/nflasha8/cpapp-b.bin`）：Thumb-2 `MOVW/MOVT` 共匹配 **299** 个 `0x9xxxxxxx` 句柄地址（含 153 个独立队列 ID）。

#### 共享核心 AP ↔ CP UIPC 队列对照表（FX3 7.02 CP vs FX6 6.01 CP 均实存）

| 队列 ID | 子系统与职责 | FX3 7.02 CP 存在性 | FX6 6.01 CP 存在性 | 备注 |
|---|---|---|---|---|
| `0x92840747` | UIPC BB 主控制/成像/Lookname/`P5`/`P6` | **是**（MOVW/T） | **是**（MOVW/T） | 挂载全部 44 个 `send_and_wait_cmp_i` 阻塞命令码 |
| `0x909a015a` | Camera / Sensor 主序列同步（`0x2500`） | **是**（MOVW/T） | **是**（MOVW/T） | 相机状态机核心同步通道 |
| `0x909c015b` | Camera 子序列同步 | **是**（MOVW/T） | **是**（MOVW/T） | 传感器/曝光/格式切换从通道 |
| `0x912f0335` | 48 B `0x8102` 同步队列 | **是**（MOVW/T） | **是**（MOVW/T） | 镜头与基础配置通信 |
| `0x905a0048` | `Avbbc` / `ObjAvAdjCtrl` OSAL 控制回包 | **是**（18 条字面池 + 6 条 MOVW/T） | **是**（30 条字面池 + 5 条 MOVW/T） | AP↔CP 控制命令共轨 |
| `0x9004015e` | `libmpr.so` 录制/编解码器同步队列 | **是**（MOVW/T） | **是**（MOVW/T） | `SetMovieRecParam` 关联 |
| `0x92850750` | `libmpr.so` UIPC 伴随队列 | **是**（MOVW/T） | **是**（MOVW/T） | 录像/文件管线伴随状态 |
| `0x92a50981` | `libmpr.so` MXF / 媒体写入队列 | **是**（MOVW/T） | **是**（MOVW/T） | MXF 元数据与索引交互 |
| `0x90610823` | CP 媒体与流媒体同步队列 | **是**（MOVW/T） | **是**（MOVW/T） | 视音频流并发同步 |

#### FX6 独占 CP 队列差集（FX3 7.02 `cpapp-b.bin` 零命中 → 必拦截合成）

| 队列 ID | FX6 `appFw.so` 调用位置 | 报文格式与阻塞机制 | FX3 CP 命中数 | 合成应答规范 |
|---|---|---|---|---|
| **`0x92d2091c`** | `infra_wrapper_rtc_procam_chaplin_base.cpp::get_rtc_status` `@ 0x2159bb0`（发送 `@ 0x2159cc8`，回调 `@ 0x2159b4c`） | 2 字节同步消息 `[0x03, arg]` 经 `send_sync_msg`（`0x215c38c`）发出，随后调用 `std::future<bool>::wait()`（`0x1ca0878`）**永久挂起**直至收到 `osal_get_msg_src == 0x92d2091c` 且 `msg[1] == 0x00` 的消息 | **0**（FX6 CP 有） | 拦截发往 `0x92d2091c` 的 `[0x03, *]`，向等待方投递 2 B 应答 `b"\x03\x00"`（`src=0x92d2091c`） |
| **`0x91db059b`** | `infra_wrapper_handle_procam_chaplin_base.cpp::register_callback` (`0x2107ce0`) / `unregister_callback` (`0x2107c0c`) | 12 字节小端消息 `<III(cmd, 0, cb_qid)`，其中 `cmd ∈ {0x81000001, 0x81000002}`（FX6 XLR 智能手柄/Smart Grip）经 `send_sync_msg` 同步发送 | **0**（FX6 CP 有） | 拦截并返回 12 B `<III(cmd \| 0x01000000, 0x0, cb_qid)` 成功回执 |

### 2.2 `0x92840747` 端点全量 44 个 `0x200d` 阻塞命令码完备性证明

FX6 `appFw.so::send_and_wait_cmp_i`（`@ 0x20ef604`）在 `0x92840747` 上分派的全部 **44** 个 `0x200d` 命令码在 FX3 7.02 `cpapp-b.bin` 中全部存在对应 `op | 0x1000` 完成态分派常数：

```
0x0112, 0x0114, 0x0119, 0x011a, 0x011f, 0x0121, 0x0133, 0x0136,
0x013c, 0x0145, 0x0152, 0x015e, 0x0162, 0x0163, 0x0165, 0x0166,
0x0167, 0x0168, 0x0169, 0x016a, 0x016b, 0x016c, 0x031b, 0x032b,
0x032c, 0x032d, 0x0400, 0x0401, 0x0402, 0x0404, 0x0405, 0x0406,
0x0408, 0x0409, 0x040a, 0x040c, 0x040d, 0x0411, 0x0412, 0x0414,
0x0416, 0x0421, 0x0426, 0x0428
```

关键成像/扩展命令码说明（覆盖 `P5`/`P6` 之外的拍摄与 LUT 链路）：
- **`0x0165`**：`video_set_lookname_procam`（36 B 3D LUT DMA 描述符，含 `0xbb80 = 48,000 B` 阈值）
- **`0x0166`**：`video_set_lookname_procam` LUT 使能开关（10 B `<HHHHH(0x200d, 0x0166, 10, 0x8001, enable)`）
- **`0x016b`**：变形宽银幕反挤压显示（De-squeeze display setting，12 B）
- **`0x016c`**：监视器扩展辅助（Monitor extender setting，20 B）
- **`0x0416`**：`video_set_mode_procam`（8 B，电影/相机视频输出模式切换）
- **`0x032d` (`P5`)** / **`0x0400, 0x0402, 0x0404, 0x0152` (`P6`)**：冷启动与电子 ND/SDI/时码链路

---

## 三、Pillar 2：CMOS / 双原生 ISO（800 / 12800）/ Cine EI 与 33³ 3D LUT DMA 契约

### 3.1 `libmpr.so` `SetLutData` / `ExecuteSetLutData` 跨机型二进制结构对齐

| 指标 | FX3 7.02 `libmpr.so` | FX6 6.01 `libmpr.so` | 兼容性评估 |
|---|---|---|---|
| `mpr::SetLutData` 入口 & 长度 | `0xd484c`（**164 B**） | `0x1505a8`（**164 B**） | **100% 同构** |
| `mpr::ExecuteSetLutData` 入口 & 长度 | `0xd4668`（**484 B**） | `0x150358`（**592 B**） | **核心状态机同构**（FX6 增加 MXF LUT 元数据钩子 `0x555ac4`） |
| 33³ `.cube` 缓冲区分配 | `malloc(0x6a1b9)` = **434,617 B**（`@ 0xd46ec..0xd46f0`） | `malloc(0x6a1b9)` = **434,617 B**（`@ 0x1503e4..0x1503e8`） | **完全相同** |
| 入参结构体 `setLutDataInParam` 布局 | `+0x04`: `enable` (1B)<br>`+0x05..+0x1e`: **26 B** 头部/色彩元数据<br>`+0x1f..+0x5e`: **64 B** `.cube` 路径字符串 | `+0x04`: `enable` (1B)<br>`+0x05..+0x1e`: **26 B** 头部/色彩元数据<br>`+0x1f..+0x5e`: **64 B** `.cube` 路径字符串 | **字节偏移 100% 相同** |
| 状态槽写入目标 | `g_lut_state + 0xa98`（26 B），`+0xab2`（64 B 路径） | `g_movie_rec_state + 0x13f8`（26 B），`+0x1412`（64 B 路径） | 仅进程内全局地址偏移不同，线协议无感 |
| 内部 Notify Tag | `0x6f`（111） | `0x7b`（123） | 各自 `libmpr.so` 自闭环通知标签 |

### 3.2 `appFw.so` 3D LUT DMA（`0x0165` / `0x0166`）与 CXD90057 ISP 下发链路

1. **AP 下发链路**：`appFw.so::video_set_lookname_procam`（`0x20f1c60` / `0x20f1d60`）、`set_base_picture_setting_procam_i`（`0x21126d8`）与 `set_user_lut_binary_data_procam_i`（`0x2112b10`）通过 `0x92840747` 下发 `0x0165`（36 B DMA 描述符，大小阈值 `0xbb80 = 48,000 B`）和 `0x0166`（10 B 开关），配合共享 LiroSeq 键：
   - `Base_Picture_Setting_base_look`
   - `Base_Picture_Setting_color_gamut`
   - `Base_Picture_Setting_input_gamut`
   - `Base_Picture_Setting_shooting_mode`
   - `Base_Picture_Setting_target_display`
   - `baseSensitivity`（双原生 ISO 800 / 12800 基准选择）
2. **CP ISP 硬件消费链路**：FX3 7.02 `cpapp-b.bin` 与 FX6 6.01 `cpapp-b.bin` 均原生内置同一套 CXD90057 ISP MLUT/EI 驱动符号：
   - `ddl_VfxSetMlut`、`ddl_VfxSetMlutEIGain`（格式化串 `ei_gain:%d base_iso:%d`）
   - `SendVEF_PathSetLut`、`SendVDF_SetMonitorLut`、`SendVEF_PathSetEiGain`、`MlutLookNameCallback`
3. **Unicorn AArch64 实指令执行结果**（真实 Donor 二进制片段直接加载验证）：
   - FX6 & FX3 `mpr::SetLutData`：`disable_reset_lut`（`rc=0`, 调用 `ResetLutData`, `notify_tag=123/111`）、`enable_empty_path_error`（`rc=2`, 调用 `ExecuteSetLutData` 但零分配）、`enable_33_cube_valid`（`rc=0`, `malloc(434617)`, 精确拷贝 26 B 元数据与 `/usr/data/lut/SLog3SGamut3Cine.cube`、SP 守恒）。
   - FX6 `appFw.so`：`0x0166` 构造 `0d2066010a0001800100` 并消费 `0d2066110c00018000000000`；`0x92d2091c` 在未拦截时触发 `future::wait` 永久挂起，注入 `[0x03, 0x00]` 且 `msg_src == 0x92d2091c` 后回调 `0x2159b4c` 返回 `true`（`1`）。
4. **Cine EI / Dual ISO 命名分化提示**：FX6 CP 额外包含 `uc_HighGainMode` / `ul_EIGainValue` / `eiGainSetting` / `ul_IsoValue`，FX3 CP 对应侧重 `EIValue` / `HyperGainMode` / `IsoSpeedRate`。AP 侧 `convert_model_baseSensitivity` 与 `set_base_picture_setting_procam_i` + `ddl_VfxSetMlutEIGain` 可驱动底层双原生 ISO 切换，UI/LiroSeq 曝光指数细粒度遥测可按需补充键名桥接。

---

## 四、Pillar 3：XAVC-I / XAVC-L 录制矩阵与 E 卡口自动对焦

### 4.1 E 卡口镜头通信库 `libInfraLensCommunicator.so` 逐字节对比

- **文件总长**：FX3 7.02 = **14,544 B**，FX6 6.01 = **14,544 B**
- **可加载段差异（`.plt` / `.text` / `.rodata` / `.data` / `.dynsym` / `.got` / `.got.plt`）**：**0 字节差异**（`.text` SHA-256 = `a1196fddd4a029c634fc392fcb8509132a59b3fa457b0f49b33aa208af0dcfa1`）
- **总字节差异**：仅 **6 字节**，全部位于非加载节 `.comment` 中的 GCC 构建日期与平台版本号（`20201211 / 14.0.1.0` vs `20240928 / 14.0.2.0`）。
- **结论**：AP↔镜头通信线协议以及 CP 共享 LiroSeq AF 键（`af_mode`、`af_adjust_mode`）在 FX6 AP + FX3 Stock-CP 下 **100% 原生无损**。

### 4.2 `mpr::SetMovieRecParam` 与 XAVC 录制格式支持矩阵

`mpr::SetMovieRecParam`（FX3 `0xf0ff0` 拷贝 **445 B = `0x1bd`** vs FX6 `0x16c5e0` 拷贝 **2,248 B = `0x8c8`**）差异主要来自 FX6 AP 侧的 `GetDProXavcIntraVQuality` 与 `libXavcMxf::SetClipName`（MXF `codec == 8`）。下表为 FX3 7.02 Stock-CP 实际支持矩阵：

| 格式 ID | 分辨率 | 编码/封装 | 帧率 | FX3 7.02 Stock-CP 支持状态 | CP 依据 |
|---|---|---|---|---|---|
| `XAVC_I_DCI_4K` | 4096×2160 | AVC-Intra 4:2:2 10-bit（MXF `codec=8`） | 23.98p / 24.00p / 25p / 29.97p / 50p / 59.94p | **`NATIVE_SUPPORTED`** | FX3 7.02 已合入 DCI 4K（`FILE_FORMAT_XAVC_SI_DCI_4K`），CP 含 `DCI4K` 与 `mov_size_req`/`frate_req` |
| `XAVC_I_QFHD` | 3840×2160 | AVC-Intra 4:2:2 10-bit | 23.98p / 25p / 29.97p / 50p / 59.94p | **`NATIVE_SUPPORTED`** | 共享 `QFHD` / `mov_size_req` / `frate_req` / `e_set_img_frame_size` |
| `XAVC_L_QFHD` | 3840×2160 | Long GOP 4:2:0 8-bit / 4:2:2 10-bit | 23.98p / 25p / 29.97p / 50p / 59.94p | **`NATIVE_SUPPORTED`** | 共享 `QFHD` + AP 侧 `libmpr` 封装 |
| `XAVC_I_L_FHD` | 1920×1080 | AVC-Intra / Long GOP | 23.98p..59.94p | **`SUPPORTED_WITH_LIROSEQ_GUARD`** | 基础 1080p 由 `mov_size_req` 支持；FX6 CP 新增 `developing_mode_FHD` 键需在 AP 参数下发时注意兼容 |
| `SQ_HFR_4K_120P` | 3840×2160 / 1920×1080 | S&Q 高帧率（100p / 120p） | 100p / 120p | **`SUPPORTED_SHARED_IMAGER_FRAMERATE`** | FX3 7.02 CP 与 FX6 AP 均经 `frate_req` 与 `e_set_img_frame_size` 支持 4K 120p S&Q |

---

## 五、Pillar 4：FX3 五轴机身防抖（IBIS）执行器安全锁止/居中契约

### 5.1 硬件物理差异与静态二进制证据链

- **FX6 侧（刚性固定 CMOS，无 IBIS）**：FX6 `appFw.so` 明确包含参数标志 **`PRM_is_imager_stabilization_unit_fixed`**，且 **不包含** `set_steadyshot_advanced_movie_i`；FX6 `cpapp-b.bin` **完全不含** `steadyshot_body_axis*` 与 `CheckSetSteadyShotAdvancedMovie` 等五轴机身电机控制模块。同时，FX6 `appFw.so` 的 `set_tc_mode_i` / `set_tc_on_movie_i` 接收 `model::setting_movie_steadyshot_t`，通过共享 LiroSeq 键 `is_mode`、`is_on_movie`、`is_type` 与 CP 交互镜头防抖（OSS）/基础防抖状态。
- **FX3 7.02 Stock-CP 侧（五轴电磁音圈防抖平台，完备自举闭环）**：FX3 `cpapp-b.bin` 内置完整的五轴 IBIS 上电恢复与 Hall/Gyro PID 闭环伺服驱动栈：
  1. **出厂校准与上电自恢复**：`LiroSeq: Restore.`（`0xcbea70`）在上电初始化阶段读取 FX3 本机未修改的 `p2:/Backup.bin`、`p2:/psd.bin`（PSD 霍尔位置零点校准数据）与 `p6:Jiritsu`（机械/陀螺自检数据），直接恢复五轴执行器基准零位与 `steadyshot_body_axis` / `steadyshot_body_axis_movie` / `steadyshot_body_axis_still` 状态；
  2. **实时 PWM 闭环居中伺服**：运行 `HallPIDOUT_0`、`GyroPIDOUT_0`、`FusionOUT_0`、`AllPIDOUT_0`、`PWMOUT_0` 闭环维持音圈电流居中锁定（Center-Lock / Standard IS），关机/收起阶段调用 `FWCP-isRetract`；
  3. **高级 IBIS 命令兼容边界**：`CheckSetSteadyShotAdvancedMovie`、`CheckSetSteadyShotAdvancedStill`、`CheckSetS1SteadyShotMode`、`CheckSetFrameLockOnSteadyShot` 仅在接收对应命令时切换动态主动（Active）或帧锁定模式，上电默认即维持安全闭环居中。

### 5.2 安全性定论

> [!IMPORTANT]
> 在 Stage-A 混合架构下运行 FX6 6.01 AP + FX3 7.02 Stock-CP，**五轴防抖音圈平台会上电通电并维持 Standard 闭环居中锁止（Center-Lock）**，**不会**因 FX6 AP 缺少 `set_steadyshot_advanced_movie_i` 而出现无电自由下垂偏心或音圈撞击限位器的硬件物理风险；同时 FX6 AP 仍可通过共享 `is_mode` / `is_on_movie` / `is_type` 开关控制基础防抖与镜头 OSS。动态 Active IBIS 切换可在后续阶段通过 AP 侧扩展菜单桥接实现。

---

## 六、Phase 18 AP-CP 拦截与合成命令码清单

| 类别 | 队列 / 命令码 | 方向与行为 | Stage-A 处理动作 |
|---|---|---|---|
| **新增独占阻塞队列 #1** | `0x92d2091c`（cmd `0x03`, 2 B） | `appFw.so` 查询 RTC 状态后 `std::future<bool>::wait()` 死等 | **拦截并合成回执**：投递 `b"\x03\x00"`（标记源队列 `0x92d2091c`） |
| **新增独占阻塞队列 #2** | `0x91db059b`（`0x81000001` / `0x81000002`, 12 B） | `appFw.so` 注册/注销 FX6 Smart Handle 回调 | **拦截并合成回执**：返回 `<III(cmd \| 0x01000000, 0, cb_qid)` |
| **直通/校验成像命令（10 个重点关注）** | `0x92840747` 上 `0x0165`, `0x0166`, `0x016b`, `0x016c`, `0x0416`, `0x032d`, `0x0400`, `0x0402`, `0x0404`, `0x0152` | FX3 Stock-CP 均原生注册对应 `op \| 0x1000` 处理分支 | `P5`/`P6` 继续按既定策略仿真，**`0x0165`/`0x0166` 3D LUT DMA 与 `0x0416` 等直通 FX3 Stock-CP** |
| **后续可扩展桥接项（非阻塞）** | `developing_mode_FHD`、Cine EI 扩展 LiroSeq 遥测键、Active IBIS UI | 不阻塞 CP 启动/拍摄，仅涉参数名称映射或扩展功能开关 | 按格式/功能白名单映射至 `baseSensitivity`、`mov_size_req`、`is_mode` |
