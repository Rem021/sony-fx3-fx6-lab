# FX3 接收序列选择与格式掩码范围

本阶段确认：普通输入条件下，MAIN FileFormat15和proxy18在已追到的接收选择器里都得到usecase1；这一步没有验证目标视频格式。另将此前待核对的 `SetAvailableFormat` 掩码绑定到了**解码启动**的一个消费者，不能把它当成已确认的主录编码能力表。

43个原指令边界用例通过，没有实际创建编码序列、修改设备状态或取得硬件Open/Start成功回复。原件为上阶段核验并提取的 `libInfraAvbbc.so`，SHA256 `87a2246084567abca0e43228b5289bc728839a13ab4251e92828ea4c463e3c26`；原文件和上阶段封存材料保持不变。

## 接收字段与普通Open选择

接收执行者把完整消息指针加8，得到CMD_PAYLOAD。该结构+0x24是消息ID（如0x210），+2是命令ID，+0x1c是此前绑定的外层FileFormat。它们不能与完整MPR_CMD同偏移的字段混用。

`SetCommandId` 先调用参数控制器写入，再按消息和命令分派。8个原表分派对照覆盖消息0x210/0x1610、命令0/1/5/6；停在各原目标代码入口，未执行后续控制器和单例。

普通Open的原分支读取包+0x60的输入选择值，以及payload中的codec type和FileFormat。本轮从诊断调用之后进入，结果如下：

| 合成输入 | 观察 |
|---|---|
| selector0、codec type0x20、FileFormat15 | usecase1 |
| 同条件、FileFormat18 | usecase1 |
| 同条件、FileFormat0x44 | usecase14 |
| 同条件、FileFormat0xff | usecase1 |
| FileFormat15，但包内codec和帧率均改成0xff | usecase1 |
| selector3 | usecase16 |
| selector1或2 | 进入需要参数控制器操作的原分支，本轮在该操作之前停止 |

这证明该选择分支没有提供完整的格式/分辨率/帧率支持检查，不能把“选中usecase1”解释为1080p29.97 HEVC已经获准。相同序列选择也不消除上阶段确认的包字段、单/双流和外层身份差异。

## Open、Start与控制器状态

`CreateCommandSequence` 在前面读取控制器键0x1049、0x104a、0x104b和0x106b。10个对照从这些读取之后开始，键值只是明确的输入前提，没有通过stub返回一个“允许”状态。

| 命令ID | 明示键0x104a | 选中的原类 |
|---|---:|---|
| 0 | 0 | EncOpenAstra |
| 0 | 1 | 2ndEncOpen |
| 1 | 0 | EncStartAstra |
| 1 | 1 | 2ndEncStart |
| 5 | 0 | EncOpen2Astra |
| 6 | 0 | EncStart2Astra |

这些片段停在原allocator入口，未分配对象。另用6个独立的构造前传参片段核对所选构造函数及msg-manager、parameter-controller、长度等参数，停在原构造PLT；分配已完成是显式前提，没有制造分配或构造返回值。

真实控制器值、其跨请求更新、并发和当前use-case均未读取。上述表不能替代原SetCommandId的前置操作、完整工厂调用或实际Start验收。

## 当前状态仍是独立条件

usecase1在 `UcsMgr::SetCommand` 中转到当前状态对象的虚表槽。一个受限对照以“原mutex已取得、当前对象为合成Null实例”为前提，用原虚表的真实重定位值执行分派，抵达 `UcsStateNull::RcvEncOpenHD` 入口就停止。

该虚表槽在文件中原值为0，ELF记录为类型257、符号 `_ZN12UcsStateNull12RcvEncOpenHDEv`。本轮仅在客体中按S+A补齐这一原ABS64槽，未伪造处理器返回值，也未通过宿主加载固件库。[Arm ELF64原规范](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst)规定了类型257及其S+A操作（2026-10-25核对）。

真实机身的当前状态未知；该方法后面还有SetState调用，本轮没有运行。“EncOpenHD”方法名也不是某个具体宽高已经通过检查的证明。

## SetAvailableFormat掩码绑定到解码启动

此前这个名字是一个未闭合的能力线索。本轮查明：原SetAvailableFormat把一个32位掩码存入参数控制器键0x1030；库内对这个常量的直接MOVZ引用共找到两处：

- 0x13cd64：SetAvailableFormat存入该键。
- 0x12a900：`ExecCmd_MC_DecStart::ExecCmd` 读取该键，随后把值写进解码命令参数+0x2c。

2个原复制片段核对了掩码写入位置。另以4个原静态表、两种合成backup字节运行8个 `CheckFlagAndUnsetBit` 对照，确认缺少对应flag时会清除表中位，存在时保留。没有读取当前机身backup，没有发送解码或编码命令。

扫描范围是本库.text中直接MOVZ常量引用，不能证明其它库或计算得到的键不存在其它消费者。但当前证据已足以收窄这条线索：**已确认的是一个解码侧用途，编码Open是否使用相同或其它能力表仍未知。** 后续不能再只凭SetAvailableFormat名称把这里当作编码支持表。

## 验证边界与下一步

本轮用例包括8个命令表跳转、8个普通Open判断、10个控制器读取后的选择、6个构造前传参、1个合成Null状态分派、8个掩码帮助函数和2个解码掩码复制。没有诊断返回、参数控制器输出、allocator或其它原生输出stub。各段之间的原生依赖均保留为未执行前提。

在已验证的普通选择器中没有找到对目标HD HEVC的专门拒绝，这只描述当前片段。MC接收端可能还有参数检查、资源/缓冲区要求和错误回复；真实当前状态、完整Open/Start、硬件码流、音频和容器均未闭合。

下一步应核对发送到MC的命令接收者、参数校验及返回码，结合ARM32原固件的加载地址和处理器表继续追踪。读取到原bin头部不构成加载地址或运行状态证明；不得直接把AArch64应用库的地址或语义套给它。

同机健康备份、受限恢复/回读、原生线程安全点、独立救援入口、WBI/冷启动、实际成片和音画同步/长录/温度验收仍缺。完整目标保留为经典FX3 7.02的1920×1080、29.97fps、HEVC420 10bit约16Mbps MAIN；精确30.000fps继续单列。

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage24-receiver-dispatch/receiver_dispatch.py --output work/sony-firmware-20261024/stage24-receiver-dispatch/new-run
```

输出目录须不存在；写入前核对目标卷，验证原件、依赖和上阶段封存文件。该轮首次运行通过，没有重跑同一套已通过用例。

- [摘要](run-20261025/summary.json) · [完整原指令与结果](run-20261025/receiver-dispatch-results.json) · [来源收据](run-20261025/source-receipt.json)
- [阶段前目标](goal-status-before.json) · [阶段后目标](goal-status-after.json) · [持续目标](../GOAL_STATUS.json) · [协调复核](coordinator-observations.json)

用户本轮要求的两次Orca协作消息检查均已完成；收到的是其它线程的容量协调状态。本线程没有迁移/删除相关材料或启动模拟器任务。UU仍等用户通知恢复；未尝试Windows连接或发任务。相机授权仍仅缓存PnP，无主动接口、认证、切模式、驱动、机身/卡文件、模块执行、WBI或刷写。
