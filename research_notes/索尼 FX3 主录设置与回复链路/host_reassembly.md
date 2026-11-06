# FX3候选诊断回复：离线分段重组与完整目标长度验证

## 本轮确证了哪些边界，哪些仍不代表USB完成？

### Takeaway

新组件已能离线重组目标大小79,015,712字节的合成文件回复，按精确manifest长度拒绝多字节或少字节结果；它只处理提供的bytes，不连接相机。逻辑回复完整、单次USB传输完成、真实相机读回验收是三个结果，组件只报告第一个，`target_verified`和`usb_termination_verified`保持false。

### Cited Findings

- 2026-10-25重新核对upstream refs：PMCA master仍为`a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`，A7CII main仍为`ef7db116e13e37be91e9af20360dc9bba8d64a9b`。只阅读相关固定文件，没有扩大审计范围。[PMCA固定源码](https://github.com/ma1co/Sony-PMCA-RE/tree/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0)、[A7CII固定源码](https://github.com/QAQLeonard/a7c2-fl23-research/tree/ef7db116e13e37be91e9af20360dc9bba8d64a9b)
- PMCA `UsbBackend.read`直接返回PyUSB读取的bytes，没有在该层保证请求长度等于实际长度；Senser `_readAll`另循环补足payload。初始header读取与payload补足是不同步骤，不能将一次read调用当成完整逻辑回复。[backend读取](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/generic/libusb.py#L77-L81)、[逻辑读取](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L841-L875)
- libusb官方说明bulk read的length是主机接收上限，实际可更少；timeout也可能已有部分传输，须检查实际传输量。短返回或timeout均不能被简单当成文件EOF。[同步I/O](https://libusb.sourceforge.io/api-1.0/group__libusb__syncio.html)
- libusb把底层USB packet抽象成transfer；主机接收缓冲区长度不会通知设备，溢出还可能使部分结果不可靠。因此本地manifest/parser上限不等于设备端读取上限，更不能反推出真实USB的终止条件。[packet与overflow](https://libusb.sourceforge.io/api-1.0/libusb_packetoverflow.html)
- libusb默认可把短于请求量的transfer视作COMPLETED；这一状态不保证请求的全部字节都已传完。本组件没有使用这个状态作协议成功判据。[异步I/O状态与SHORT_NOT_OK](https://libusb.sourceforge.io/api-1.0/group__libusb__asyncio.html)

### Inferences

本组件的`feed(bytes)`参数是离线逻辑字节片段，既不是声称的一次USB packet，也不是重建真实端点描述符、padding或总线时序。`feed(b'')`只是无字节输入，不代表ZLP、更不代表EOF。`finish()`表示调用者结束这一份离线capture；即使成功，也不自动宣称相机传输结束。

### Gaps

真实FX3服务PID、端点wMaxPacketSize、ZLP/short packet出现位置、timeout时驱动保留多少数据、非0336路径的最小包/padding都没有实机验证。源码默认值不能代替这些目标事实。本轮无backend、USB、GUI、卡文件、认证、驱动或刷写操作。

## 1MiB逻辑段、0x8000读写块、header/status如何重组？

### Takeaway

PMCA的header.size表示当前剩余逻辑payload长度，超过1MiB时后续有新header、size按剩余量递减；0x8000是读/发送块层的另一粒度。status只属于整个逻辑payload的首4字节，不能在每个1MiB续段重新剥除。设备同事本轮的静态回复链证据增强这些对应，但真实USB结束仍未验收。

### Cited Findings

- PMCA结构是12字节`<IHHBBBB>`，字段依次size、pFunc、sequence、version、miconType、offsetType、response；常量minSize=200h、chunkSize=8000h、maxSize=100000h。发送header.size取剩余payload总长，发送最多1MiB后扣减；接收亦依size判断是否继续。[header/remaining-size](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L822-L876)
- A7CII Jiritsu路径要求outer response=0，payload至少4字节，然后按`<I`取status，成功返回后续数据；这里没有逐段status剥除。非0 status报错，10000006的缺失解释也只是该host实现语义。[Jiritsu status](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py#L404-L412)
- A7CII响应framing验证短header、sequence与pFunc；它只在CP0x603/0x40读路径特殊处理对齐结束包，且保留非空lookahead。不能把“再读一个结束包”泛化到Jiritsu文件读取。[A7CII边界处理](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py#L21-L104)

设备端静态证据由同轮设备任务提供，详见同目录[device_reply.md](device_reply.md)及其[final-reply-proof.json](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)，本host子任务没有再次反汇编：

- `SendResponse@B4C0`强制回复header字节`+8=3`，把PacketData长度写到`+0`；分离缓冲时每轮先序列化12字节header，再序列化最多1MiB数据，header.size是当前remaining；底层发送callback另按最多8000h拆分。
- `+4/+6/+9/+10`保留现有请求header字段，并非由回复函数强制清零；`+11`是命令/底层错误相关response，不能宣称总是0。
- 普通setpath结果通过MemoryData指向OSALmsg+1C，默认长度4；raw read成功路径分配filesize+4并清零，再把文件内容读到buffer+4，故成功逻辑payload有一次4字节零status前缀。续段Advance不会重新插入status；完整错误/加密路径本轮没有泛化覆盖。

字段命名须准确：`+8`在PMCA源定义中名为`version`，但设备静态事实只是该字节被写成3；本文不把它扩大解释成“FX3协议版本3”。代码profile名`fx3-static-version3-candidate`沿用PMCA字段名，验收语义仍是固定字节profile。

### Inferences

- Stage9的全零回复golden只适合其合成profile；stage10显式区分`upstream-zero-fixture`和`fx3-static-version3-candidate`，后者严格要求+8=3、pFunc40、expected sequence、+9/+10=0和成功response0。+9/+10取0是受限候选请求上下文约束，不是宣称所有合法回复都必须如此。
- 纠正上阶段内部路由推测：设备活跃表实际family起点为0x31D98；record的family/code/name/queue偏移分别为+0x00/+0x02/+0x04/+0x44，stride为0x48，cmd15对应索引1504（十进制）。内部命令0x400F的0x4000高位用于权限/adjCodeLevel，并非pFunc40的编码；匹配命令低8位15–18。pFunc40由独立level路由进入AdjustControl。wire命令仍是15/17，不能编码400F/4011。
- 本组件接受的是无未解释padding的逻辑header+payload序列；header、status、数据可在任意输入片段之间截开。header只在1MiB逻辑段边界出现，8000h输入切点不制造新header或新status。

### Gaps

源代码与设备静态链并不等于真实USB抓包。仍未知真实驱动/相机何时产生或省略ZLP，以及其他flags、错误状态、加密数据是否有不同封装。组件继续将目标与USB完成标为false。

## 新组件如何做到有界、严格失败并支持实际目标长度？

### Takeaway

保留小范围默认策略，同时新增绑定精确manifest的大响应模式，支持79,015,712字节目标文件；没有把4MiB测试上限固定成架构限制。实现采用本轮允许的80MiB有界内存方案，未实现流式sink或落盘；完整组装后才公开返回数据，后续错误不会留下已公开的“成功前缀”。

### Cited Findings

自写代码与合成验收：

- [offline_reassembly.py](../../work/sony-firmware-20261024/stage10-mainpath/host/offline_reassembly.py)：只导入stdlib dataclasses、struct；没有请求编码、设备backend、文件/系统I/O、认证或写入接口。
- [verify_reassembly.py](../../work/sony-firmware-20261024/stage10-mainpath/host/verify_reassembly.py)：只执行自己的parser和合成字节fixture；生成大文件模式时每次输入不超过8000h，不读取或保存真实目标文件。
- [offline-fixtures.json](../../work/sony-firmware-20261024/stage10-mainpath/host/offline-fixtures.json)：固定golden、manifest、计数与摘要收据。
- [source-receipt.json](../../work/sony-firmware-20261024/stage10-mainpath/host/source-receipt.json)：固定来源URL/commit/hash、自己的文件hash、第三方参考源码清理与独立验证记录。

策略和状态机：

| 约束 | 当前实现 |
|---|---|
| 显式回复计划 | 仅cmd15/17上下文，1–8个小响应，sequence逐一递增、不复用或回绕 |
| 默认/普通上限 | 默认每响应数据64KiB；非manifest最大2MiB，capture累计4MiB |
| 大响应manifest | 超2MiB必须精确expected_data_bytes；仅单个read上下文，最大80MiB |
| 精确总长 | 首header.size必须等于manifest文件长度+4；每个续header.size必须等于剩余payload |
| 段与片段 | 每逻辑段≤1MiB；输入片段不决定协议边界；空片段不代表结束 |
| 首status | 累计到4字节后检查一次；非0立即锁止，不在续段重新解释 |
| 错误处理 | 过长/截断、错序/pFunc/flags、意外帧/尾随数据、错误status或显式abort均清空私有结果并锁止 |
| 结果提交 | 只有finish确认整个离线回复计划完成后才返回；USB结束与target验证仍为false |

### Inferences

- 80MiB是本地资源策略，不是设备协议最大文件大小。当前实现会暂存整个逻辑payload并生成返回bytes，峰值内存可能包含额外副本；它服务完整长度校验基础，不是低内存流式落盘备份工具。
- 精确manifest拒绝截断/超长，不提供内容真实性。当前真实机身程序hash尚未由本组件取得；长度一致无法识别所有等长损坏、位翻转、文件版本混淆或错误来源。
- 如果未来要低内存sink，可保留相同header/remaining/status状态机，但必须明确数据在最终校验前是临时内容，失败时不应被当成已验收备份；本轮没有加入这种I/O。

### Gaps

本文没有产生任何相机备份、真实读回hash、实机文件内容或恢复能力证明。完整读取79MB的设备操作仍未获本轮授权，也未执行。

## 精确测试结果与未证明事项是什么？

### Takeaway

31项合成测试全部通过；协调端独立检查AST并复跑31项同样通过。目标大小合成数据经76个逻辑段，输出长度和SHA-256均一致。这是离线重组测试，不是FX3硬件协议验收。

### Cited Findings

执行`python3 -B verify_reassembly.py`：31 tests，0.106s，OK。协调端另以`PYTHONDONTWRITEBYTECODE=1 python3 verify_reassembly.py`复核31/31 PASS，并检查parser仅dataclasses/struct导入、无I/O/backend调用。

| 合成manifest结果 | 值 |
|---|---|
| 数据字节数 | 79,015,712 |
| payload含首status | 79,015,716 |
| 逻辑段数 | 76 |
| 含76个12B header的wire字节数 | 79,016,628 |
| 生成模式数据SHA-256 | `230af254530f2e190b465ff48e15c19b27367c3e5e5bae9657f71a146a5de981` |

覆盖：header/status任意切分、所有小golden两段切点、单字节片段、20组确定性随机切分、多个有计划回复拼接及lookahead、每个截断前缀、尾随/超长、错序/重放、非零状态与错误profile、缺失末尾、1MiB边界、remaining-size错误、续段数据形似status但不应再剥除、空片段预算、失败锁止、默认上限与精确manifest模式。大manifest的±1首header、超长尾字节均拒绝。来源是上述自己的代码和[fixture收据](../../work/sony-firmware-20261024/stage10-mainpath/host/offline-fixtures.json)，非相机抓包。

### Inferences

现在可以明确说：候选组件在离线合成条件下能够验证实际目标长度范围，关闭stage9只接完整小frame的若干重组盲点。不能说：已取得FX3程序备份、已验证USB稳定、已经具备安全刷写或救砖能力。

### Gaps

不能从纯字节parser判断未知USB末尾、驱动丢失的部分数据、合法padding或真实总线错误；没有真实目标完整性hash时，也不能对所有等长内容错误作保证。所有相机能力仍未启用；stage9历史文件未改动。
