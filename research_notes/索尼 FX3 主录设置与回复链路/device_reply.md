# FX3 7.02 活跃Jiritsu查找与回复序列化：阶段10静态闭合

## 1. 外层 pFunc 与Jiritsu命令记录是否进入了实际查找链？

### Takeaway
**本轮补上了活跃指针赋值、pFunc=0x40选择器、真实记录查找和OSAL发送的静态连接。** 这些是条件成立时的代码行为；没有验证当前机身的认证level、初始化回调或USB可达性。[权威聚焦回执](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)

### Cited Findings
- 来源固定为FX3 7.02原 `libsencore.so` SHA256 `a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410` 和 `libJiritsu.so` SHA256 `bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9`。本轮只做原始字节、符号、重定位和反汇编，不执行/仿真固件。[固定哈希与复核脚本](../../work/sony-firmware-20261024/stage10-mainpath/reply/derive_reply_proof.py)
- `Parse @0xe9f4` 的GOT `0x6aec0` 是 `pFunc`，其本体在BSS `0x6bfa0`。`WorkerThreadManager::onComplete @0xc108` 按参数1/2/3，分别把 `pFunc_level_C/B/A` 的地址写入pFunc，并将同一值写入 `adjCodeLevel`；其他值清空pFunc。authentication开始路径另有清零pFunc操作。故磁盘中的BSS零值不能代表运行时列表永远为空。[指针赋值原字节](../../work/sony-firmware-20261024/stage10-mainpath/reply/active-pointer-and-data-builder.json)、[GOT和认证入口引用](../../work/sony-firmware-20261024/stage10-mainpath/reply/serializer-and-pfunc.json)
- A/B/C三个实际列表都含 `u16 key=0x40`，其函数指针通过 `R_AARCH64_ABS64` 重定位绑定 `AdjustControlFunc @0x10344`。`Parse` 读取收到的header+`0x04`，按每项`0x10`字节匹配列表键并间接调用对应函数。[三个列表原字节、重定位及修正后的值](../../work/sony-firmware-20261024/stage10-mainpath/reply/active-lists-and-receive.json)、[Parse原字节](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)
- `SenserThread` 在 `0xb880/0xb88c` 通过接收函数读取`0x0c`字节header，然后调用Parse。`AdjustControlFunc` 另读取4字节命令前缀，交给 `SubsystemCommunicationCommand::TransactionStart`。该函数在 `0xfc50–0xfc60` 以两个u16读入命令族和命令，分别放进本机结构+`0x24/+0x26`。[header读取和命令前缀转换](../../work/sony-firmware-20261024/stage10-mainpath/reply/transaction-and-frame-read.json)、[AdjustControlFunc](../../work/sony-firmware-20261024/stage10-mainpath/reply/active-lists-and-receive.json)
- `TransactionStart` 在 `0xfddc–0xfe04` 从family键基址`0x17698`、以stride **`0x48`** 扫描，匹配family及命令低8位。实际Jiritsu命令15–18的索引为1504–1507，记录起点分别为 `0x31d98/0x31de0/0x31e28/0x31e70`。字段布局为 **family+`0x00`、flags/command+`0x02`、name+`0x04`、queueID+`0x44`**。[查找原字节与四条完整记录](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)
- `0xff68` 按索引计算记录，`0xff74` 从记录+`0x44`取queueID，写入命令对象并分配消息；`0xffb4` 调用 `osal_snd_sync_msg`。四条记录的queueID均为`0x016f0480`，与前轮实际 `jiritsu_init @0x6dbc` 注册的回调 `0xb278` 相符；后者按两级跳表到15/16/17/18的精确处理器。[记录选择→OSAL发送](../../work/sony-firmware-20261024/stage10-mainpath/reply/selected-record-and-file-prefix.json)、[Jiritsu回调注册](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/gate-and-registration.json)、[前轮handler表](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/command-handler-table.json)
- 表中 `0x400f/0x4010/0x4011/0x4012` 的`0x4000`是权限标志：查找后用`0xe000`掩码；`adjCodeLevel==2`时bit15未置可通过，level1因非零权限位被拒绝，level3通过当前正常分支。不能把高字节`0x40`当成wire pFunc编码；外层pFunc=0x40来自另一张列表。[权限条件原字节](../../work/sony-firmware-20261024/stage10-mainpath/reply/permission-and-status.json)

### Inferences
- 这一静态链支持候选wire“pFunc=0x40，族=0x1001，cmd=15或17”与FX3接收实现相符；不应把wire命令写成`0x400f/0x4011`。[查找与两侧字段](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)
- A/B/C列表都能进入AdjustControlFunc，不等于三个认证level都能操作Jiritsu；必须同时满足记录权限gate。[列表与权限对照](../../work/sony-firmware-20261024/stage10-mainpath/reply/active-lists-and-receive.json)、[gate指令](../../work/sony-firmware-20261024/stage10-mainpath/reply/permission-and-status.json)

### Gaps
- 未观察当前机身onComplete参数、pFunc/adjCodeLevel实际值及OSAL回调注册状态；“静态可达”不是“现在已认证/可访问”。
- 未验证原厂库实际符号插桩、驱动、USB transport及故障时服务入口独立性。

## 2. 回复header、4字节status及大文件分段如何形成？

### Takeaway
设备端已证明12字节header、header+`0x08`强制3、header.size不含header，以及分离缓冲按最多`0x100000`字节推进、每轮size表示remaining的规则。普通setpath的4字节状态payload和成功原始文件read的一次4字节状态前缀，也有从本机回复缓冲到发送器的静态支撑；真实USB完成仍未验证。[回复发送原字节](../../work/sony-firmware-20261024/stage10-mainpath/reply/serializer-and-pfunc.json)

### Cited Findings

| header偏移 | 本轮确认的设备端行为 |
|---|---|
| `0x00..0x03` | SendResponse写入payload大小；分段路径每轮写当前remaining，排除`0x0c`字节header |
| `0x04..0x05` | Parse以此u16匹配pFunc；SendResponse本身不改写 |
| `0x06..0x07` | 请求标识/PMCA所谓sequence被线程用于查找；SendResponse本身不清零 |
| `0x08` | SendResponse固定写3；仅称该字节值，不宣称“FX3协议版本3” |
| `0x09/0x0a` | SendResponse本身保留当前header值，未证明必须为0 |
| `0x0b` | 命令错误及底层回复路径会写此response字段；不能泛化恒0 |

表中依据为 `SendResponse @0xb4c0`、`SenserThread @0xb7ac` 和 `SubsystemCommunicationCommand::DoExecute @0xf894` 的真实指令；“SendResponse不改写”不能扩展为所有上游handler都不可能改写。[发送器](../../work/sony-firmware-20261024/stage10-mainpath/reply/serializer-and-pfunc.json)、[接收线程](../../work/sony-firmware-20261024/stage10-mainpath/reply/transaction-and-frame-read.json)、[命令返回构造](../../work/sony-firmware-20261024/stage10-mainpath/reply/active-pointer-and-data-builder.json)

- `SendResponse` 在 `0xb4e0` 写header+`0x08=3`；成功PacketData的GetSize结果写header首u32。若buffer恰等于header+`0x0c`，fast path调用Serialize发送 `size+0x0c`。分离缓冲路径先发`0x0c`字节header，再发 `min(remaining,0x100000)` 数据，推进并扣减remaining，再决定是否重复。[SendResponse完整指令](../../work/sony-firmware-20261024/stage10-mainpath/reply/serializer-and-pfunc.json)
- 这有三个不同层次：整个逻辑payload；上层每轮至多`0x100000`数据字节；`SenserIfSend @0xcf98` 每次传递给回调的长度至多`0x8000`。generic Serialize会按回调实际返回字节推进指针并重试未发送部分。**回调调用次数/大小不等于USB packet数，更不证明ZLP或short-read终止条件。**[Serialize与回调限制](../../work/sony-firmware-20261024/stage10-mainpath/reply/active-pointer-and-data-builder.json)、[SenserIfSend](../../work/sony-firmware-20261024/stage10-mainpath/reply/serializer-and-pfunc.json)
- 普通无raw地址的OSAL回复在 `ReceiveOsalMessage @0xf838–0xf848` 返回 `message+0x1c`。`DoExecute @0xf94c–0xf9cc` 识别这个地址，取消息+`0x18`长度并用标准发送函数构造MemoryData。前轮Jiritsu dispatcher对setpath默认结果长度4、handler把状态写消息+`0x1c`，因此该正常路径payload是那4个状态字节。[缓冲选择与MemoryData](../../work/sony-firmware-20261024/stage10-mainpath/reply/active-pointer-and-data-builder.json)、[ReceiveOsalMessage尾分支](../../work/sony-firmware-20261024/stage10-mainpath/reply/transaction-and-frame-read.json)、[前轮packet builder](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/route-tables-and-caller.json)
- 命令17原始读取模式（参数第三字节不为1，对应候选`00 ff 00`）中，`adj_cmd_get_file2 @0xa134` 按文件大小+4分配DMM并清零；`0xa1e4` 让文件数据读到buffer+4，成功后累加文件长度。此成功路径逻辑payload前4字节为零状态，随后才是文件字节。Serialize通过MemoryData Advance推进指针，所以跨上层分段后不能再为每段剥4字节状态；这是**整个逻辑回复的一次前缀**。[实际文件前缀构造](../../work/sony-firmware-20261024/stage10-mainpath/reply/selected-record-and-file-prefix.json)、[Advance及聚焦原字节](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)
- 上述状态字段的本地u32存储与12字节header内u32/u16存储均来自小端AArch64 ELF，并被原发送器按原始缓冲传递；本轮代码路径中未见字节反转。它增强了LE framing依据，但没有测量USB线上实际字节或驱动层行为。[源字节及发送链](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)

### Inferences
- 离线assembler应把remaining-size分段拼成一个逻辑payload，再解释一次4字节状态；不能把一次`0x8000`回调或每个上层分段都当作独立status+file回复。[分段与前缀共同证据](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)
- 生成fixture可以验证实现遵循已见规则，不能代替真实抓包、USB transfer completion或实际相机文件读回。[静态执行边界](../../work/sony-firmware-20261024/stage10-mainpath/reply/derive_reply_proof.py)

### Gaps
- 未闭合完整USB驱动调用、transfer/chunk边界、short packet/ZLP完成语义及真实packet顺序。
- 未宣称所有失败路径、加密模式、压缩模式或所有命令都采用同一4字节前缀；本轮重点是setpath正常返回及成功plain文件read。

## 3. 哪些旧解释需要纠正，本轮完成到哪里？

### Takeaway
本轮保留旧证据原件，并明确纠正stage9的记录起点及高位含义。静态“接收/选择→查表/权限→OSAL/Jiritsu handler→回复构造/分段发送”已有实质闭合；实际机身访问、独立救援与HEVC实录目标仍未完成。[本轮最终回执](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)

### Cited Findings
- stage9的两份artifact将cmd15切片从`0x31d94`开始，按前4字节当queueID，随后才是family/code；同样处理相邻三条。新 `0xff68/0xff74` 明确证明记录起点应是family地址`0x31d98`，queueID位于**同一记录+`0x44`**。旧切片前置u32实际是上一条记录尾；相邻Jiritsu记录queue相同，故旧数值吻合掩盖了结构起点问题。**不静默修改stage9原件。**[旧原始切片](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/parse-and-command-records.json)、[旧解释表](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/command-handler-table.json)、[新选择/取queue指令](../../work/sony-firmware-20261024/stage10-mainpath/reply/selected-record-and-file-prefix.json)
- stage9仅把高位标为未完成桥接；本轮明确区分独立pFunc键`0x40`和record权限`0x4000`，并解出level1拒绝、level2在bit15未置条件下允许、level3允许。该判断绑定真实掩码与分支，不等于当前authenticated level已知。[旧命令记录](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/parse-and-command-records.json)、[新权限与活跃列表](../../work/sony-firmware-20261024/stage10-mainpath/reply/permission-and-status.json)、[新列表值](../../work/sony-firmware-20261024/stage10-mainpath/reply/active-lists-and-receive.json)
- 本轮没有外部参考下载、原生/Unicorn固件执行、相机/USB/UI访问、认证、模块上传或设备文件操作；所有新增证据位于stage10-mainpath/reply。原始两库SHA保持一致。[复核方法](../../work/sony-firmware-20261024/stage10-mainpath/reply/derive_reply_proof.py)

### Inferences
- 现在可将“内部路由与正常回复生成规则”列为设备端静态已证，并继续将“目标机身运行验收/USB完成”标为未证；不能用两者共用一个verified布尔值掩盖差别。[已证与未证清单](../../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json)

### Gaps
- 未产生FX3实际文件读取、服务初始化或机身程序哈希证据；当前普通MSC/缓存PnP信息不能补足这些gate。
- 本子任务没有验证安全持久写入、故障后独立恢复、编码器接受或1080p29.97 HEVC42010实际主录输出；用户总体目标仍需后续实际证据，不能因本轮静态闭合标完成。
