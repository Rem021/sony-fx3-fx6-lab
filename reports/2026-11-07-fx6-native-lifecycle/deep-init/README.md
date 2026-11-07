# FX6 288–290：原生 UI 已前进，下一处为未初始化的 MWF 日志对象

2026-11-07，第二轮只读研究。未启动、暂停或修改 VM，未修改任何 `/tmp` 或共享源码。日志、CPIO、原厂 donor 均只读。这里的结果是虚拟机混合系统诊断，不是完整菜单或实机验收。

## 本轮新结论

**上轮 OSAL 未启动 UI 线程的假说，对 288–290 已被后续日志排除。当前可精确复核的故障是 `libMWF.so` 的 `MonCtrl::GetFlag(this=NULL)`。独立 `appfw-launch` 缺少原厂模块生命周期，是该空指针的具体候选原因。**

不能把当前情况继续描述为“尚未进入 UXEngine”或“缺少 Arena”。也没有直接 WidgetSystemFactory marker，暂不声称该 Factory 已成功完成。

## 1. 越过 OSAL 与 uxengine_init2 的运行证据

已读取现有运行：288 `cp-bind-9a736b1c`、289 `cp-bind-93fb917b`、290 `cp-bind-8d4a255b`。三者均有 GRM framebuffer callback、9 个 `FX6_UX_SCREEN_AREA_1024` 与以下原厂 Arena 注册打印：

| Arena | 实际字节数 |
|---|---:|
| mpMemoryHeap | 8,388,608 |
| mpMemoryHeap2 | 4,194,304 |
| mpTextHeap | 12,582,912 |

FX6 `appFw+0xc0b484` 调 `uxengine_init2`，下一条 `+0xc0b488` 才进入打印三条 Arena 的函数 `+0xc0b258`。因此这些日志证明 UI worker 运行，且 `uxengine_init2` 已返回、三大 Arena 已注册。该排除结论只适用于本轮有上述日志的候选，不能倒推 287 当时的线程状态。

JSON 保存各次只读日志快照的字节数、SHA-256、命中行号。运行证据会继续增长，SHA 仅绑定读取时快照，不冒称最终运行回执。

## 2. 重复故障的实际函数

289 与 290 均出现：`APPFW_SEGV sig=11 addr=0x10`、`X0=0`，PC/LR 均归属真实 `libMWF.so`：

| 项目 | 偏移/实际含义 |
|---|---|
| PC | `libMWF+0x3e908` = `MonCtrl::GetFlag() const` |
| 出错指令 | `ldrb w0, [x0, #0x10]` |
| LR | `libMWF+0x38f14`，刚从 `RsrcDP::MyPrintf` 的 GetFlag 调用返回的位置 |
| 日志指针 GOT | `+0x63f08` 的动态重定位符号为 `MWF::RsrcDP::smp_monErr` |
| 全局指针对象 | `smp_monErr` 位于 `+0x67e00`，尺寸 8 B |

`MyPrintf+0x4c`（`+0x38f0c`）读取该全局 MonCtrl 指针，`+0x38f10` 不做空检查直接调用 GetFlag。现场 x0 为 0，故“调用日志时全局错误日志对象为空”是已确定的直接故障机制。

这条 PC 本身不是 kikilog 的 ioctl，也不是 WidgetSystemFactory 的构造函数。上游资源错误可能在打印时被这个空日志对象掩盖；单纯屏蔽 GetFlag 会损失真正失败上下文。

`libMWF.so` 实际 CPIO 输入为 353,120 B、SHA-256 `3c9666c49bde90076cf69af13295dc07e585d87c51a27ecaf7f1926df87d1782`；288–290 相同。

## 3. 原厂应如何创建这些对象

`RsrcDP::Initialize`（`libMWF+0x38cb0`）创建 5 个 `MonCtrl`，分别写入错误、警告、消息、顺序、调试全局指针。其原厂调用链为：

```text
MWF_Init +0x27e74
  → MWF::Initialize +0x27d68
    → RsrcMcmd::Init +0x393b4
      → RsrcDP::Initialize +0x38cb0
        → MonCtrl 构造 ×5，写入 smp_monErr 等全局指针
```

本机真实 FX6 donor `libIMDB.so` 为 79,728 B、SHA-256 `a088ef303793497a443e89d6de4c8f12e07ec791c945f54e2dc1b52cd42db896`。其同一模块记录的 `+0x1f280` 指向字符串 `libMWF.so` (`+0xaadb`)，`+0x1f288` 指向 `MWF_Init` (`+0xaae5`)。这证明原厂模块管理表明确规定了该库对应的初始化入口。

相对地，当前实际 `appfw-launch` 对 libMWF 仅执行 `dlopen(..., RTLD_NOW|RTLD_GLOBAL)`，没有调用 `MWF_Init` 或 `MWF::Initialize`。库本身 `.init_array` 只有 `+0x243f8` 的 frame-dummy 类型入口，没有自动运行上述生命周期。因此“库存在、动态链接成功”不会自动得到这 5 个日志对象。

**候选原因边界：** 本轮证明了启动器缺少显式 MWF 初始化，证明原厂生命周期要求该初始化，并证明故障时该对象为空；尚未通过运行确认补齐原生模块初始化顺序是否完全解决问题。不能把这当成可以随意单独调用 MWF_Init 的运行许可：它还会初始化 Monitor、线程、消息接口和资源关系，必须与原厂模块管理顺序/既有初始化状态对齐，避免重复初始化或依赖缺失。

## 4. 实际构建源与输入绑定

288–290 的 `usr/bin/appfw-launch` 均为 92,488 B、SHA-256 `0a4eb7a70b38aed52b644dfc044515197334a7d3842ef254e56e5ff809376ea6`；`.symtab` 文件名为 `appfw-launch288.c`。对应 `/tmp/appfw/appfw-launch288.c` 已只读保存到本目录，12,398 B、SHA-256 `862547d6460cbdd7e1f7fbb26b254aa16e0e9c272000a0207323f54fc9c012a9`。

289–290 的 shim 为 72,168 B、SHA-256 `46974fad8e0c1cd23460036bfc18f2566599482650157bc1b1d678d274685798`。对应 `/tmp/libgrm-fbinit25-289.c` 已只读保存，58,055 B、SHA-256 `849ff8bff38ed2206925f75847257b057b3347ec3817dde46ff52fe9ed43cae3`；未找到独立 `-290.c`，不能凭候选编号虚构一份。源码与二进制文件名/包装逻辑吻合，完整可复现构建仍需命令与工具链回执。

三个候选中的 `appFw.so` 本体仍为 50,520,424 B 的原厂 `a1c58b69...`，本轮没有把 290 名称中的 `upm` 误解成 appFw 已打 UPM 二进制补丁。

此外，启动器中 `init("AppConfig.so")` 调用的 shim 随后永久 sleep，因此位于这行之后的手工 UXEngine 初始化/patch 代码，在这条实际路径上无法正常到达；不要用那些不可达代码解释本轮原厂 Arena 日志。

## 5. 观察候选与后续最小判别

`observe_mwf_lifecycle.c` 是独立观察源码候选，**未构建为 guest 二进制、未打包 CPIO、未运行**。它仅：

- 转发原厂 `MWF_Init` 和 `RsrcDP::Initialize`，记录进入/返回时的 caller 与五个指针值；
- 对 `GetFlag` 只在 caller 精确归属 `libMWF.so+0x38f14` 时输出现场，随后原样调用真实 GetFlag；
- 不补对象、不主动调初始化、不跳过 NULL 故障、不改 caller 参数；保留 errno。

若该候选未来被单独审阅集成，期望先分辨：初始化入口根本未调用；已调用但中途失败；初始化完成后被其他路径改空。第一种才支持按原厂模块表补生命周期的下一步候选。修复后应继续保留 RsrcAcsr 原始错误、kikilog/UPM 的具体失败，不能把“空日志崩溃消失”当作菜单已运行。

宿主 `clang -fsyntax-only -Wall -Wextra` 通过，只证明 C 语法/宿主声明通过，不代表 guest 链接或 ABI 验收。

## 复核工具与限制

`inspect_deep_init.py` 从自备 CPIO 只读提取成员到内存、解析调用目标/重定位，并采样现有日志。它输出 JSON，不写出固件字节。依赖 `pyelftools`、`capstone`；参数 `--agnostic` 为已有运行目录，`--donor-lib` 为真实 FX6 donor 库目录。

CPIO 解析器仅覆盖首个 newc archive，不能判定后续 archive 的同名覆盖；协调者的全容器核验负责此项。`inspection-288-290.json` 为本次结果。未给已有日志重新附加通过状态。
