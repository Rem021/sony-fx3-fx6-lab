# FX6 Native First-Frame Master Plan & Full Authorization (2026-11-07)

## 0. 用户最高授权与不中断执行令（必读，立即生效）

1. **权限全部放开（Full Authorization）**：
   - 用户明确授权所有在 QEMU / Guest 内的技术手段，**无需再停下来等待用户拍板**，严禁因权限顾虑进入 `⛔ blocked` 状态：
     - **允许** 在 Guest 内挂载用户态调试器（`gdbserver` / `ptrace` / 按 `tid` 单步追踪任意线程）。
     - **允许** 在 Guest Shim (`libgrm-fbinit*.so`) 内注入任意单步探针、寄存器/栈转储、符号拦截（PLT/GOT/inline hook）。
     - **允许** 重写或旁路 `model_lock` / `model_mutex` 协议（包括构造一致的 owner/count 状态、旁路任意 cond_wait/trylock、替换整个锁类实现）。
     - **允许** 合成任意 OSAL / UIPc / Dataflow / Input 消息，或直接反射调用 `ux::wgtsys::WidgetSystem`、`ScreenManager`、`RemotePresenter`、`GRM` 内部方法以驱动原生渲染管线。
   - **唯一边界（不变）**：
     1. 绝不触碰或刷写任何物理真机（仅限本地 QEMU 虚拟机与镜像文件）。
     2. 严禁用自己手写的假像素/测试条纹直接填充 `0x41e001000` (`gpe0`) 冒充成功——像素必须由 FX6 原生 `appFw.so` / `libux*.so` / `libGrm.so` 渲染管线生成并刷入帧缓冲。
2. **禁止自动停止等拍板（No Self-Blocking）**：
   - 只要 `gpe0-late.bin` (`0x41e001000`) 仍全为 0，或尚未渲染出可读的 FX6 原生拍摄设置/菜单画面，**不得将任务标记为完成或 `blocked` 停机等待**。
   - 完成一个阶段列表后，必须自动拆解并追加下一阶段的子任务，按本计划逐步推进。

---

## 1. 双终端明确分工（防止抢占同一个 QEMU Runtime Lock）

当前存在两个 DeepSeek (`dsh`) 终端，必须严格按以下职责分工，避免同时启动 QEMU 争抢锁或覆盖彼此的候选编号：

- **终端 B（`term_4b286158`，`FX3 运行时实验接管与注入`）——【主运行时与 QEMU 验证线】**：
  - **独占 QEMU 执行权**，使用候选编号 **`440+`**（递增，绝不复用旧号）。
  - 负责编译 `libgrm-fbinit25-<N>.so`、打包 CPIO、运行 QEMU、检查 `gpe0-late.bin` 非零像素并迭代实验。
- **终端 A（`term_22969527`，`继续结构化代理会话任务`）——【静态逆向与渲染管线状态机拆解线】**：
  - **禁止启动任何 `qemu-gpio5` 进程**（避免与终端 B 抢锁），立即解除 `⛔ blocked` 状态。
  - 专注于静态反汇编 `appFw.so`、`libux*.so`、`libGrm.so`、`libInfraInput.so`，为终端 B 提供精确的函数偏移、虚表（vtable）结构、画面脏标记（dirty flag）偏移以及 `GRM_fbrmUpdate` 触发条件，将结果实时写入 `reports/2026-11-07-fx6-uxengine-init-assist/STATIC-PIPELINE-MAP.md`。

---

## 2. 一步一步出图作战计划（Step-by-Step Execution Plan）

当前基线（Candidate 395–440）：
- `17b9f1c` 的 13,793 项 model table 遍历已压缩至 ~30 秒跑完；
- `C09DE4B_RET -> C14DFC_CALL/RET -> PRESENTER_CALL (0x1397450)` 已完整跑通；
- `1024×540` GRM Framebuffer 已分配并触发回调；
- 10 轮 `0x696` (`0x61003c -> 0x807e0030`) 初始化握手已走完；
- `tid 222` (AppFw) 与 `tid 228` (`RemotePresenter`) 的死锁已可通过 `0xde304c` 谓词补丁解除；
- 正在验证直接驱动 `ux::wgtsys::WidgetSystem` (`sys_getInstance` / `updateFrame` / `notifyDraw` / `processEvent`)。

请严格按以下 **Step 1 → Step 6** 顺序推进，每一步都有明确的验证指标与下一步分支：

### Step 1：验证 `ux::wgtsys::WidgetSystem` 直接驱动与内部状态（Candidates 440–443）
1. **观察 440 结果**：检查 `WidgetSystem::sys_getInstance()` 返回的 `ws` 实例指针是否非空，以及调用 `updateCurrentTime()` / `updateFrame()` / `notifyDraw()` / `processEvent()` 后是否触发 `GRM` 绘制或 `FX6_OSD_FLUSH` 非零图元（`prims > 0`）。
2. **若 `updateFrame()` 已执行但 `prims == 0`**：
   - 反汇编 `_ZN2ux6wgtsys12WidgetSystem11updateFrameEv` 与 `_ZN2ux6wgtsys12WidgetSystem10notifyDrawEv`（由终端 A 立即输出完整控制流和所有 early-return 条件）。
   - 检查 `ws` 对象偏移处的开关字段（例如：isInitialized、isVisible、dirtyFlag、activeScreen 指针、rootWidget 指针、displayEnable 标志）。
   - 在 Shim 中转储 `ws` 前 `0x200` 字节内存（`FX6_WS_DUMP`），对照反汇编找出哪一个字段导致 `updateFrame()` 提前返回，并直接补丁该字段或调用缺失的 `Screen` / `Page` 激活函数。

### Step 2：挂载 Root Screen / 激活 Shooting 或 Menu 视图树（Candidates 444–448）
1. **定位视图树挂载点**：
   - 在 `appFw.so` 和 `libux*.so` 符号表中检索所有包含 `Screen`、`Page`、`View`、`Layer`、`Window`、`Menu`、`Shooting`、`Status`、`enter`、`show`、`attach`、`setRoot` 的符号。
   - 检查 `PRESENTER_CALL` (`0x1397450`) 返回后、`c0a86c -> df91e8` 路径中，原本应该由哪个事件或状态迁移来调用的首屏创建函数（如 `createScreen` / `changeScreen` / `requestScreen`）。
2. **强制挂载首屏**：
   - 如果视图树根节点为空（`root == NULL` 或 `screenList` 为空），在 `PRESENTER_CALL` 完成后直接调用首屏注册/切换函数，或伪造触发首屏切换的内部状态码，然后再调 `WidgetSystem::updateFrame()`。

### Step 3：打通 `RemotePresenter` (tid 228) 的 100ms 轮询至 `GRM` 渲染提交（Candidates 449–453）
1. **拆解 `RemotePresenter` 循环体**：
   - 反汇编 `appFw+0xde3000..0xde3400`（特别是 `0xde304c` 谓词之后到 `usleep(100000)` 之间的全部调用）。
   - 查明 `RemotePresenter` 唤醒后检查了哪些队列或标志位才会调用渲染提交（`draw` / `render` / `GRM_fbrmUpdate` / `gperm`）。
2. **闭合提交回路**：
   - 观察当 `WidgetSystem::updateFrame()` 生成绘制命令后，图元落在哪个内存缓冲区或 GRM 图层（Layer/Surface/Bitmap）。
   - 如果 `UXEngine` 把像素画到了某个离屏 `GRM` Bitmap 而未触发 `flush_pixels_to_osd`，则在 Shim 中拦截 `GRM_gperm*` / `GRM_blt*` / `GRM_screen*` / `GRM_layer*` 全部导出函数，打印实际被调用的 GRM 函数与目标缓冲区地址。

### Step 4：全量拦截 `libGrm.so` 调用并桥接真实渲染缓冲区到 `gpe0`（Candidates 454–458）
1. **定位像素落点**：
   - 如果原生 UI 实际通过别的 GRM 接口（例如 `GRM_layerSet*`、`GRM_gpermDraw*`、或另一个 `fb` 虚拟地址）完成了绘制，而没有走旧的 `flush_pixels_to_osd` 路径，立即记录所有非零写入的帧缓冲/Bitmap 地址。
   - 将真实的非零原生 GRM 渲染缓冲按 `1024×540` 格式同步到 `0x41e001000` (`gpe0`)。
2. **禁止伪造**：同步的源数据必须是 FX6 原生 `appFw`/`UXEngine` 真实渲染出的 UI 图层数据（含真实文字/图标/边框），并在报告中附上非零像素统计、唯一色值数量及解码后的 PNG 截图验证。

### Step 5：Input 按键表精确匹配与菜单交互验证（Candidates 459–462）
1. 根据 `libInfraInput.so` 的 `KeyConfigInital` (`0xb284`) 和 `GetPhyKeyConfig` (`0xb38c`) 反汇编结果，提取完整的有效物理按键 ID 与 `0x20` 字节事件结构（含 press/release 状态位）。
2. 在首帧出图或待机状态下，向 `q=0x7ae01d` 注入精确格式的 `MENU` 按键事件，验证状态切换与界面重绘。

### Step 6：落盘证据与同步报告
- 每跑完 2–3 个候选，将关键发现追加至 `reports/2026-11-07-fx6-uxengine-init-assist/HANDOFF-20261107-RUNTIME.md` 与 `reports/2026-11-08-gemini-coordination.md`。
- 一旦 `gpe0-late.bin` 出现非零原生 UI 像素，立即将其转换为 PNG 图像并生成完整里程碑报告。
