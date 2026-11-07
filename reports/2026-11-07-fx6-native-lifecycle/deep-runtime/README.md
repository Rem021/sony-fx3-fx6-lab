# FX6 原厂 UI 第二轮运行复核：Candidates 287–290

最新确定进展是：288 已出现 UXEngine 屏幕对象初始化及全部 24 MiB Arena 注册；289/290 在此之后同样崩于 **MWF 日志模块的空 error-monitor 指针**。现有日志没有直接证明执行到了 WidgetSystemFactory。四轮均未取得原厂菜单像素。

本轮没有控制 VM、QMP、GDB、端口或相机。只读已具备 `process_reaped=true`、`locks_released=true` 回执的 287–290。写入前重新核验外盘 UUID 正确。所有产物仅在本目录；没有提交或推送。

## 交付及复跑

- `review_latest.py`：复用协调者 `reports/2026-11-07-fx6-parallel-native-ui/inspect_cpio_binding.py`，完整扫描首 TRAILER 后的追加 newc 成员；比较最后出现的成员指纹、全部 477 个 `usr/lib/*so*` entry、init 差异、launcher ELF sections、完成回执与原始串口。
- `latest-summary.json`：四轮完整 provenance 结果、关键原始行号、异常归属及逐轮差异。CPIO 不解包落盘，仅读取选中成员到内存。

```sh
python3 -B reports/2026-11-07-fx6-native-lifecycle/deep-runtime/review_latest.py \
  --root /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic \
  --scanner reports/2026-11-07-fx6-parallel-native-ui/inspect_cpio_binding.py
```

扫描器的最后出现成员规则不是 Linux hardlink/文件系统抽取模拟；报告保留其明确语义，不把索引结果等同于内核最终状态。四轮整包 SHA/bytes、loader 路径、manifest 对完成回执、serial SHA 对完成回执均一致，读取期间检查的输入未变化。

## 绑定与真正变更

四份完整容器的 `usr/lib/appFw.so`、`libMWF.so` 及除 shim 外的库闭包不变。appFw 为原件 SHA `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`、50,520,424 B，不能套用旧 79 MB 文件的 VMA。

| 轮次 | 完成 run | init SHA 前缀 | shim SHA 前缀 | 实际变化 |
| --- | --- | --- | --- | --- |
| 287 | `cp-bind-810b960b` | `249e640274ab` | `46161fe7ff7f` | 已恢复 `Application_System_Init` wrapper 调用原件入口 |
| 288 | `cp-bind-9a736b1c` | `249e640274ab` | `46161fe7ff7f` | init 和全部 477 个库 entry 均与287相同；launcher只有调试/符号字符串 sections 变化 |
| 289 | `cp-bind-93fb917b` | `2725a0f41bb5` | `46974fad8e0c` | 移除早期并行 appfw 与旧 bootin/探针长分支，改为 native 最小模块顺序后启动 appfw；只有 shim 库 entry 改变 |
| 290 | `cp-bind-8d4a255b` | `797b9e900d48` | `46974fad8e0c` | 所有库与 launcher 均同289；init增加 power seed、upm、udate、date seed、kikilog |

287→288 的 launcher SHA 虽不同，但 `.text`、动态 sections、所有 `SHF_ALLOC` section 均相同。只有 `.strtab`、`.debug_line`、`.debug_str` 改变。ELF gABI 将 `SHF_ALLOC` 定义为运行内存映像占用属性；结合这些具体字节比较，不能把“fast-init”文件名视作实际执行优化证据。[ELF gABI section flags](https://gabi.xinuos.com/elf/03-sheader.html#section-flags)

四轮预算均约120秒，288比287观察到更深初始化不能归因于已证实的代码加速；调度/运行时序差异仍是可能解释。本轮未做性能实验。

源码相关文件另记录 SHA：`/tmp/libgrm-fbinit25-289.c`、`/tmp/appfw/appfw-launch288.c`。它们是有用的源线索；当前摘要没有 build receipt 可把源码 SHA 与执行 shim 一一绑定，所以以容器内编译产物为准。协调者的 deep-init 研究负责保存源码及生命周期分析。

## 原始运行到达点

以下行号对应各 run 的原始 `serial.log`；完整 SHA 在 JSON。

| 轮次 | 已观察到的进展 | 尚未证明的部分 |
| --- | --- | --- |
| 287 | 1621 `FX6_APP_CONFIG_ENTRY arg=AppConfig.so ... real=...`；1622 `FX6_APP_CONFIG_HOLD real_returned` | 只证明 wrapper 调用了并返回原件入口；异步 UI worker 是否完成不能由入口返回判定 |
| 288 | 1481/1482 同入口与返回；1483原生 stella HeapAllocator；1485–1495 framebuffer/屏幕 area 初始化；1496–1498 三 Arena 为8/4/12 MiB；1499–1505更多屏幕 area | 这些是 UX 图形初始化观察，缺少 native UI worker PC、具体 screen/controller/view id、WidgetSystemFactory 运行 marker；不能据9个 area 对象声称完整菜单建成 |
| 289 | 1181/1182入口；1183 HeapAllocator；1185–1205 同图形/24 MiB Arena初始化；1207/1209/1215/1218分别FTP/Kikilog/remote/UPM assert；1264明确APPFW_SEGV | 原厂菜单尚未出现；后续MWF日志路径崩溃，不能从该异常直接推出控件工厂是根因 |
| 290 | 1116/1120/1124/1128 stream/stream2/dmm/grm_ma加载RC=0；1130/1138/1147/1171/1174 power/upm/udate/date/kikilog准备RC=0；1227入口；1229–1251图形/24 MiB Arena；1253/1255/1261 FTP/Kikilog/remote assert；1266同MWF异常 | UPM回调assert本轮未再出现，但Kikilog模块加载RC=0并未消除它的register_callback assert；缺失marker不能作为所有对应功能通过 |

`FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0` 分别位于288:1492、289:1192、290:1238。287只有一份gpe0采样，288–290各gpe0/gpe1均为2,211,840 B，非零字节全部为0。因此“UI ready”若仅依赖OSD_FLUSH marker会过早通过。

287/288的通用 `SEGV (PC=...)` 前 current task 是 busybox，继续单独列出。289/290则具有明确 `APPFW_SEGV` 及模块归属，不混淆两类。

## 289/290 的确定失败点

两个运行具有同样的库相对地址：

- 289 serial:1264，`sig=11 addr=0x10`，PC `0x7f9ab53908`；1298/1299提供 `libMWF.so base=0x7f9ab15000`，因此 PC=`libMWF+0x3e908`，X30=`libMWF+0x38f14`。
- 290 serial:1266，`sig=11 addr=0x10`，PC `0x7f812df908`；1298/1299提供 `libMWF.so base=0x7f812a1000`，得到完全相同的相对PC与LR。
- CPIO内同一 `libMWF.so` 的 ELF动态符号绑定：`+0x3e908` 是 `MonCtrl::GetFlag() const`，两条指令为 `ldrb w0,[x0,#0x10]; ret`。两个现场 X0 都为0，精确解释访问地址 `0x10`。
- LR `+0x38f14` 位于 `MWF::RsrcDP::MyPrintf(...)`。调用前 `+0x38f04..+0x38f10` 取 GOT slot、取对象指针并调用 GetFlag。GOT `+0x63f08` 的重定位指向 `MWF::RsrcDP::smp_monErr`（symbol `+0x67e00`）。
- 现场保存的 X22 指向库内 `+0x433c8` 的短字符串 `[RsrcAcsr]`；X21 指向 `+0x437c7` 的 `Constructor. acsrId = %d subsystemId = %x`。因此上游至少是在 RsrcAcsr 构造的错误日志路径，不能仅凭当前两帧归属到 WidgetSystemFactory。

这是**已确认的故障机制**：MWF error-monitor 对象为空，日志自身先崩溃。导致构造进入错误日志的更早业务条件，以及为何monitor未初始化，是下一步待验证问题。静态存在 `MWF::RsrcDP::Initialize()`（`+0x38cb0`），不等于该初始化在本次运行曾执行/成功。

优先候选是恢复原厂 MWF 模块初始化生命周期，并在日志对象就绪后捕获原始资源构造错误；应验证 `MWF_Init/Initialize` 被实际调用、返回值和五个MonCtrl对象，再定位首次RsrcAcsr错误来源。直接把GetFlag改成常量会掩盖可定位的上游错误，本轮没有实施任何补丁。

## 已可排除与仍不能排除

- 286 的 wrapper 符号缺失已不是287–290的停止点：四轮都有 `FX6_APP_CONFIG_ENTRY` 和 real_returned。
- 24 MiB Arena容量不足已不能解释288–290的停止：三块Arena均记录完整成功注册；不能推广为其他所有分配一定成功。
- 280误读OSAL线程入口导致的未对齐 PC 已不是289/290的同一故障：这次PC位于有效RX库函数且4字节对齐，访问机制为`this=0`的数据读。
- 289→290的新增power/upm/date/kikilog准备没有解决MWF崩溃；不能把缺少这些模块当成当前空MonCtrl故障的已证实单一根因。
- `dlopen(libMWF)`成功不能等同原厂`MWF_Init`生命周期成功；需要额外执行证据。
- 无直接WidgetSystemFactory运行marker，故是否已到/阻塞其中仍需其他caller或静态路径证据。不能用原生屏幕area数替代该证据。

## 历史字段漂移仍在

四份 manifest 都继承 `grm_fbinit.member="usr/lib/libgrm-fbinit9.so (content=fbinit8)"`；该带注释字符串不是容器内精确成员名，诊断SHA `ca4d57...` 也不等于真实shim。

`appfw_future_skip` 四轮仍声称SHA `b1fe2274...` 及旧 `+0x2159c50` patch；完整容器中的appFw却均为原件 `a1c58...`。因此该历史字段既不能证明旧future补丁存在，也不能把旧VMA用于50MB原件。

以上造成扫描器 `binding_inconsistent`，同时整包和loader绑定均通过；这是成员描述漂移，不是整包损坏结论。回执 `fault_markers=[]` 也依然漏掉289/290的原始assert与APPFW_SEGV，原始日志应优先于摘要。
