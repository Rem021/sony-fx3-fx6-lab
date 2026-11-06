# FX3 7.02：原 Dataflow 消息复制、清理和 AV 指针消费

2026-10-27。**本轮补足了原消息库与同固件 libc 的有界执行证据，尚未得到可部署的 1080p29.97 HEVC 主录或救砖方案。** 只在 Mac 上读取已保存的官方固件样本并运行 Unicorn 指令实验，没有访问 Windows、UU、相机接口或卡内文件。目标仍为 MAIN 1920×1080、30000/1001 fps、HEVC 4:2:0 10-bit、约 16 Mbps；精确 30.000 fps 单独验证。

## 新证据及其适用范围

从既有、已校验的原始文件系统镜像直接读取 `dataflowInfraFramework.so` 和 `libc-2.25.so`，未挂载镜像、未用主机原生加载器执行固件。提取前后路径、inode、大小和 SHA-256 见两份 extraction receipt。原库的 `memcpy`、`memset` 是 AArch64 `STT_FUNC`；实验只把明确的导入调用绑定到它们的原始指令，不代写输出或返回成功。此绑定属于实验输入，不证明 Sony 实际加载器的符号解析、装载地址或当前进程状态。

正式结果在 [dataflow-results.json](run-native-payload-and-header-20261027/dataflow-results.json)。2 种旧内存填充值、8 组消息条件、4 组发送端参数复制、4 组 AV 消费，合计 64 个有界执行阶段：

| 原函数／路径 | 本轮观察 | 尚未证明 |
| --- | --- | --- |
| MPR `0x282d6c` → 原 libc `memcpy` | 从原消息头 `+0x28` 取虚拟目标，将 `0x98`（152）字节参数逐字复制；源和消息头不变 | 此入口的帧和映射是声明输入；完整 `Codec::EncOpen`、实际固定区映射、SendMsg 与同步未执行 |
| Dataflow 构造、`SetGlobalMsg`、`SetSrcId`、`GetSrcId` | 原对象的 raw/global 状态为 2；48 字节消息头进入对象内联区，来源 ID 可读 | 没有建立 `ReceiveASync` 到该 setter 的完整真实路径 |
| `GetMsg` → 原 `memcpy` → `Clear` → 原 `memset` | 48→48 情形逐字复制；状态、长度、来源 ID 和已存内联消息被原指令清零；重复 Get 返回 -27 | 清理消息对象不等于释放或取得 Open 参数区的独立所有权 |
| AV `ReceiveCommand` 后段 | 在精确复制的 48 字节前写入 `0x7000 / 0x9000 / 0x38`；消息其余字节保留 | 该 AV 阶段与消息库是独立 guest，字节交接不证明跨进程传输或共享地址映射 |
| AV `SetParameter` 有界段 | 从 CMD `+0x30`（消息头 `+0x28`）读取虚拟指针，并在该区读取 raw `+0x64`；ViewId 0/1 分别选择不透明值 `0x805700f9 / 0x805720f9` | 两处 ParameterControl 虚调用均停止，目标显式为零；调用后段是独立输入，未假造回调成功。标签不能据此命名为已验证的硬件通道 |

## 完整性和寿命边界

原 raw/global `GetMsg` 复制 `min(已存长度, 请求容量)`，随后清理整个已存消息。人为声明的 16→48、48→16 对照都只复制 16 字节，却同样返回 0，剩余目的字节保持原填充值。**返回 0 不能作为完整 48 字节消息头的证据。** 这些部分消息未交给 AV 解引用，也不能据此断言相机的真实消息传输会产生截断或存在漏洞。原结构化 state1 消息有另一套长度／计数逻辑，本轮没有将它与 raw/global 路径混用。

本轮保留阶段107更正：消息 `+0x08` 是物理／设备域地址，`+0x28` 是虚拟地址，`+0x1a` 是 ViewId；不是容量。实验的物理域数值未映射，也未被用作用户态指针。消息对象清理仅涉及自己的内联消息，不证明外部固定参数区能并发复用、真实接收进程具有同样虚拟映射，或存在已验证的锁和回复寿命。

每个阶段检查完整 scratch 允许区之外、栈允许区之外及映射原库字节未变；完整函数返回还检查 X19–X29、D8–D15 与 SP。没有日志跳过、返回值／输出补写、硬件成功适配器或虚调用替身。原日志 helper 在本轮 0 和 -27 条件下自行提前返回；未知日志后端保持停止边界。第一份 `run-original-libraries-20261027` 是加入 MPR 参数复制前的 60 阶段成功检查，源码副本保留；正式封存使用上述 64 阶段结果，不混用两份计数。

## 公开恢复证据复查

本轮重新读取原讨论／维护者仓库，日期与范围记在 [public-source-notes.json](public-source-notes.json)：

- [REA 的 FX3 7.02 讨论](https://github.com/morluto/rea/discussions/3027) 当前可见为电池行为改动请求，0 评论；该页没有给出本目标的主录或恢复验收。不能从单个讨论推导全网没有其他结果。
- [A7CII 失败与恢复报告 #31](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31) 包含无法启动／循环灯报告；其中部分用户通过仍能工作的录像模式回到系统再恢复。此路径依赖未损坏的应用分支，不能保证 FX3 录像链被改坏后仍能进入。
- [A7IV 维护者的 BootROM／fastboot 说明](https://github.com/DavidBuchanan314/ILCE-7M4-RE) 讨论该机备份恢复，并明确 boot0 加密处理尚未实现；不是 FX3 7.02 的独立救援验证。没有在本机执行其中操作。

## 仍须解决

上游应用 MAIN 的原格式转换仍未自然产出目标 VPC6。已有目标参数来自声明候选，且有旧值／未绑定缓冲区；不能直接提交到相机。原 quality6→22/FH 与约16 Mbps 资源匹配仍未解决，原型仍是阶段75的 `UNDEPLOYABLE_GUEST_ONLY`。

接下来追 `ReceiveASync`／OSAL 的实际消息成帧、两个 ParameterControl 虚调用的原对象来源与接口、固定区映射和外层同步／回复寿命；这些工作仍可在 Mac 离线进行。实际硬件 Open/Start、输出 HEVC 文件、音画同步、码率、长录／温控／冷启动、同机健康备份、受限恢复回读及独立救援都未验收。全部16项验收状态与现有权限保持，不将有界执行通过当作可安全刷入。

代码：[dataflow_copy.py](dataflow_copy.py)；原指令与范围：[source-and-scope-audit.json](source-and-scope-audit.json)；复核：[completed-evidence-review.json](completed-evidence-review.json)；封存：[final-receipt.json](final-receipt.json)。
