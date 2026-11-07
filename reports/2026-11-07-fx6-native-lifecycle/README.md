# FX6 深入研究第二轮：原厂模块生命周期与屏幕状态机

> 后续：[第三轮队列契约复核](../2026-11-07-fx6-queue-contract/README.md) 已确认293有限窗口无异常但帧仍全零；其运行时NOP跳过了70项infra初始化及App定时生产者。真实等待尚无caller/qid归属，不应把 BB finalize 的等待直接改短。

2026-11-07。接续[首轮并行复核](../2026-11-07-fx6-parallel-native-ui/README.md)，核查主线已完成的 Candidates 287–290，完成三个并行研究任务及一项设备契约分析。本轮没有启动/控制 VM、修改共享候选或操作相机。

## 当前结果

**288–290 已越过原厂 UI 线程和 `uxengine_init2`，当前重复故障是 MWF 日志对象为空。独立启动器跳过原厂模块初始化，是具体可验证的缺口候选。** 已找到原厂 `MWF_Init`、Kikilog 初始化和屏幕管理器的静态路径；尚未通过运行证明补齐这些步骤就能出现菜单。

| 项目 | 已证实结果 | 尚未证实 |
|---|---|---|
| 初始化达到点 | 288–290 有 9 条 ScreenArea 观察与 8/4/12 MiB Arena 打印；按原厂调用顺序，UI worker 已运行、`uxengine_init2` 已返回 | ScreenArea 对象不是 9 个已打开的相机界面；无 WidgetSystemFactory 直接运行 marker |
| 直接故障 | 289/290 同为 `libMWF+0x3e908`，`MonCtrl::GetFlag(this=0)` 读 `0x10`；LR `+0x38f14` 来自 `RsrcDP::MyPrintf` | 更早触发资源构造错误的业务条件尚未查明 |
| 生命周期缺口 | 原厂 `libIMDB` 表声明 `libMWF.so / MWF_Init`；当前 launcher 只 dlopen，没有执行该初始化。原厂初始化会创建五个日志对象 | 原厂调度顺序、一次性初始化条件及完整依赖，不能从表的物理排列直接推定 |
| Kikilog | 实际候选的 devno/provider 和用户态库共同指向 `/dev/usb/kikilog`，字符设备 `248:10`；用户态初始 fd=-1，由 `KikiLogGenerator_init` 打开 | guest 运行时节点是否由其他机制创建、初始化是否执行、ioctl 的即时 errno |
| 原厂屏幕状态机 | 已确认 manager、registry、controller 请求和 boot 事件处理路径；Shooting/HOME/Menu 首层对应 registry ID 2/10/15 | 未证明 guest 已到这些入口，事件数值及模型条件枚举尚未还原 |

所有 FX6 AppFw 地址均绑定 50,520,424 B、SHA-256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`。运行时需要真实模块基址。

## MWF：日志自身先崩溃

实际库 `libMWF.so` 为 353,120 B、SHA `3c9666c49bde90076cf69af13295dc07e585d87c51a27ecaf7f1926df87d1782`。两个完成运行的 PC、LR、X0 和故障地址相互吻合：`MyPrintf` 读取全局 `smp_monErr` 后，不做空检查调用 `GetFlag`。

原厂链为 `MWF_Init → MWF::Initialize → RsrcMcmd::Init → RsrcDP::Initialize`，末端创建五个 MonCtrl 对象。`libMWF` 的 ELF 自动构造入口没有执行该链；当前 launcher 也没有显式调用。这解释了为什么仅加载真库仍不能保证日志设施就绪。不能把 GetFlag 改成常量来当作修复，否则会掩盖正在报告的 RsrcAcsr 构造错误。

已交付[只观察的 shim](deep-init/observe_mwf_lifecycle.c)：转发初始化函数，记录五个指针；在精确 caller `libMWF+0x38f14` 处记录现场后保留原调用和原故障。它不主动初始化、不构造假对象、不吞掉错误。**仅通过宿主 C 语法检查，尚未构建 guest 库、打包 CPIO 或运行。**

详见[初始化链与源码绑定](deep-init/README.md)、[运行归属与逐轮差异](deep-runtime/README.md)。对应实际自编 launcher/shim 源码已保存，完整构建回执仍缺失。

附加[模块管理器顺序复核](deep-init/lifecycle-order.md) 已进一步定位真 FX6 `im.elf` 的实际消费代码：扫描器按 enable、target mask、flags 和阶段边界过滤，再派发库加载与 init。Kiki 与 MWF 均位于 `0x08000003`–`0x08000004` 区间；正常过滤通过时 Kiki 的加载请求先派发、MWF 后派发。工作线程与完成屏障尚未完整还原，因此不声称 Kiki 的 init 返回先于 MWF 的 init 进入。表项类型 `0x20000001/2` 也不是 phase 1/2。

## Kikilog：内核加载与用户态初始化是不同步骤

[可复跑契约核验](audit_kikilog_lifecycle.py) 读取整个 Candidate 290 CPIO 的追加记录，按精确 SHA 验证实际装入的 FX3 内核模块与 FX6 用户态库，不把另一份 FX6 `kikilog.ko` 的结构套到当前运行。

- `usr/kmod/kikilog.ko` 为 80,536 B、SHA `78fb1e9d…`。其初始化重定位引用 `udif_devnodes+624`。
- 实际 `kmod/devno.ko` 为 6,344 B、SHA `cca1d9ac…`，该位置为第 39 行，名称 `usb/kikilog`，类型字符设备、major 248、minor 10。
- 真 `libInfraKikiLogGenerator.so` 的初始 fd 槽 `+0x162b0` 为 -1；`KikiLogGenerator_init → +0x38f8` 才打开 `/dev/usb/kikilog`。
- `kikilog_set_notify_cb +0x2978` 使用已保存 fd，提交 `0x80044a10` ioctl；第三参数是消息/队列 ID 标量，不能把函数指针传给它。非零 ioctl 返回被该库压成 -127，原始 errno 因此需要当场观察。
- 同一份真 `libIMDB.so` 明确声明 `libInfraKikiLogGenerator.so / KikiLogGenerator_init`。仅 insmod 成功不能替代这段用户态生命周期。

完整 archive 没有设备节点成员，**不等于运行时一定没有该节点**；devtmpfs、mdev 或后续创建仍需运行证据。当前也没有读到实际 ioctl 的 errno，不能把“初始 fd=-1”直接当成运行现场的 EBADF 结论。

复跑及指纹见 [kikilog-contract-290.json](kikilog-contract-290.json)。脚本只向 stdout 输出元数据，不提取或执行固件：

```sh
python3 -B reports/2026-11-07-fx6-native-lifecycle/audit_kikilog_lifecycle.py \
  --manifest /path/to/cp-helper-agnostic/vm-candidate-gpecap25-290.json \
  --fx6-imdb /path/to/fx6/nflasha15-files/lib/libIMDB.so
```

## 菜单应经原厂状态机进入

已确认的路线为 `App::run → App::initialize → presenter_controller_manager::initialize → 原生事件 → open_screen_internal → controller/presenter 工厂`。

manager 位于 `App+0xa40`，初始化 `+0xde31ac`；屏幕过渡入口 `+0xdf790c`，内部创建入口 `+0xdf6680`。HOME 的 controller 请求入口为 `+0xf2dec0`。原厂 `MODEL_POWER_ON_COMP` handler 位于 `+0x1009be0`，其中存在通往 ID 2 或 7 等路径的条件分支，不能在未还原模型条件时伪造一个“开机成功事件”。

这些对象依赖既有 App、预分配池、screen manager 和模型状态。直接调用 `procam_*_presenter` 构造函数不会替代正常开机链。详见[状态机路线](deep-screen/REPORT.md)、[SHA 约束解析器](deep-screen/audit_screen_route.py)。

## 因果边界与下一轮

287→288 的 init、全部 477 个库 entry 和 launcher 的运行 sections 均不变；只有 launcher 的调试/符号字符串 sections 改变，预算也同为约 120 秒。故不能把更深的运行达到点归因于已实现的 `fast-init` 优化。289→290 的所有库和 launcher 相同，只增加 init 准备序列；UPM assert 未再出现，MWF 崩溃仍保留。四轮采样帧均全零，没有原厂菜单通过。

下一轮应由运行负责人继续独占 VM：先确认原厂 module-manager 生命周期及依赖，再在明确顺序、避免重复初始化的条件下恢复 MWF；同时观测 Kikilog 的节点/打开/回调 ID/即时 errno。日志设施就绪后保留首次 RsrcAcsr 错误，再沿 screen manager 观察原生状态机。验收仍须绑定原厂 screen/model、同一 run 的 guest 帧读回与 native key ACK。

本轮已通过 Orca `orchestration` 向现有主线发送内部研究状态，receipt `msg_a8e56f83ffaf`；该收件箱是 terminal-only，回执表示消息提交成功，不证明对方已采用或实施。

## 验证与资料

实际 donor/容器静态断言、已结束回执与原始日志、完整 CPIO 指纹和逐轮成员对比已通过。脚本对不匹配 donor 拒绝；观察 shim 的检查仅限宿主语法。未做 guest 链接、菜单交互或实机验证。

`dlopen` 加载库及其 ELF 自动构造器，不会凭普通函数名执行任意应用初始化入口；本项目的 `MWF_Init` 要求由原厂表与代码证明。[Linux dlopen 文档](https://man7.org/linux/man-pages/man3/dlopen.3.html)

ioctl 要求已打开的 fd；命令语义与参数取决于设备实现。本项目的 callback ID 标量约定由用户态和驱动静态读取确定，不能只靠 ioctl 编码推断。[Linux ioctl 文档](https://man7.org/linux/man-pages/man2/ioctl.2.html)

容器追加记录的解释沿用已核对的[Linux initramfs 格式](https://www.kernel.org/doc/html/latest/driver-api/early-userspace/buffer-format.html)；运行 section 的比较参考 [ELF gABI](https://gabi.xinuos.com/elf/03-sheader.html#section-flags)。公共文档不证明 Sony 私有模块已执行。
