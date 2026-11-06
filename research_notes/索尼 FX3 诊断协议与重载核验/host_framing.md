# FX3候选诊断：主机Senser/Jiritsu字节布局与离线校验

## 当前源码是否变化，哪些结果仍可复用？

### Takeaway

A7CII main已更新，但本次完整定向比较只包含免责声明文字；用于packet/framing的transport未变化。本任务只完成主机源码字节布局、自己的离线codec和合成fixture验证，未读取相机接口、卡、认证、驱动或模块，不能称FX3实机适配通过。

### Cited Findings

- 2026-10-25重新核对ref：PMCA master为`a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`；A7CII main由`b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d`更新至`ef7db116e13e37be91e9af20360dc9bba8d64a9b`。新提交元数据为2026-10-25 19:23:19+0800。[PMCA固定来源](https://github.com/ma1co/Sony-PMCA-RE/tree/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0)、[新提交](https://github.com/QAQLeonard/a7c2-fl23-research/commit/ef7db116e13e37be91e9af20360dc9bba8d64a9b)
- 两个A7CII固定commit之间的完整compare.patch只改README英中版、notices英中版，扩充禁止收费代刷、付费安装等说明；没有release、恢复、写入或回滚行为代码变更。[定向完整比较](https://github.com/QAQLeonard/a7c2-fl23-research/compare/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d...ef7db116e13e37be91e9af20360dc9bba8d64a9b)
- 本地逐字节核对：新旧`src/camera_runtime/transport.py`均为SHA-256 `52f2c34f4b5c5d2361a7a5869320fec3711b753299a74fd814a87129d1a9d10a`；新A7CII vendored `pmca/usb/sony.py`与上述PMCA固定源码相同，均为`53ffb4d9d49cb5146623fda2b66ecb137681a6fc9ab0c98d23a51e75128af97e`。[当前transport](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py)、[当前vendored Sony](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/vendor/pmca/usb/sony.py)

### Inferences

这些新旧结果只允许复用packet源码事实，不把上轮未闭合的FX3 service身份、认证或恢复能力提升为已验证。README说明变化也不是新恢复功能发布。

### Gaps

本次未获取实机响应，当前设备授权仍仅Windows缓存PnP。没有导入或执行下载的第三方源码；下载参考内容只作静态文本分析，结项已删除，URL/commit/hash留在来源收据。

## 请求wire的精确字节布局是什么？

### Takeaway

PMCA实际方法名是`sendSenserPacket`。主机普通Senser header是12字节小端`<IHHBBBB`，A7CII Jiritsu请求在其payload前加小端`<HH>(0x1001,cmd)`。因此主机wire的族、命令、参数分别在+12/+14/+16，不能用设备内部控制结构的+24/+26/+28替代。

### Cited Findings

PMCA `Struct`默认little-endian且使用无本机对齐的`<`格式；`SonySenserDevice.SenserPacketHeader`依次声明size/u16 pFunc/u16 sequence/4个u8字段，发请求时size取payload长度，四个u8均为0，sequence起始1。[Struct定义](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/util/__init__.py#L36-L63)、[外层header与发送](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L822-L851)

| 相对wire起点 | 字段 | 类型/大小端 | host源码语义 |
|---|---|---|---|
| +0..3 | size | u32 LE | 本次payload字节数，不含12字节header |
| +4..5 | pFunc | u16 LE | Jiritsu候选走0x40（AdjustControl） |
| +6..7 | sequence | u16 LE | 调用上下文序列；PMCA起始1 |
| +8 | version | u8 | host请求填0 |
| +9 | miconType | u8 | host请求填0 |
| +10 | offsetType | u8 | host请求填0 |
| +11 | response | u8 | host请求填0；回复语义依pFunc区别 |
| +12..13 | inner category | u16 LE | A7CII Jiritsu填0x1001 |
| +14..15 | inner command | u16 LE | 候选setpath=15(0x000F)，read=17(0x0011) |
| +16.. | arguments | bytes | 各命令参数 |

表中外层字段来自上述PMCA定义，内层来自A7CII `jiritsu`对`struct.pack('<HH',0x1001,cmd)`的明确调用。[内层请求](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py#L404-L416)

- 候选setpath：cmd15，arguments=`00 + ASCII路径 + 00`；A7CII host守卫要求路径前缀`/tmp/jiritsu/`、无内嵌NUL、字符数≤510。候选read：cmd17，arguments固定`00 FF 00`，其中没有客户端最大返回长度字段。[select/read](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py#L413-L423)
- A7CII较高层`Camera.read`构造`/tmp/jiritsu/../../`再拼目标路径，依赖路径处理行为；自己的离线codec刻意拒绝`.`/`..`与空路径分量，没有继承这一跨目录假设。[高层读取路径](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/devicesession.py#L101-L109)
- PMCA还存在另一条pFunc=FF01 FileControl，参数是cmd/filenameSize和按4字节填充的latin1路径；它不是0x40/0x1001的Jiritsu协议，不能混用其成功码或参数布局。[FileControl独立布局](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L939-L1004)

### Inferences

- `0x1001`编码为`01 10`，cmd15编码为`0F 00`；设备内部记录的`0x400F`不能直接替换wire command，否则发出的会是不同的16位值。内部控制结构偏移与wire偏移必须分别记载。
- 设备同事本轮静态桥接线索：libsencore连续记录含msgID016F0480、族1001、内部命令400F/4010/4011/4012及对应JIRITSU名称；Jiritsu注册同msgID；MakeOsalMessage去除内部命令高字节后分派15–18。这增强0x40/1001与Jiritsu对应关系，但本host子任务未独立复核二进制，活跃入口与最终USB序列化仍以设备同事[内部路由笔记](jiritsu_route.md)及其[命令映射表](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/command-handler-table.json)为准。不能由内部结构直接推导wire header或返回字节序。

### Gaps

尚未由本台经典FX3 7.02的真实响应证明上述完整wire请求、setpath路径语义、read参数及回复包装。自己的encoder只反映公开host源码候选，标记`TARGET_ROUTE_VERIFIED=False`。

## 回复长度、status与流边界应如何区分？

### Takeaway

A7CII host把outer response和inner u32 status当作两个不同成功条件；其Jiritsu返回payload不含命令echo，前4字节是小端status，余下为数据。这是host实现事实，最终FX3 USB序列化尚未闭合。自己的parser只验证一个已组装、严格限长的候选frame，不实现USB收包、ZLP或多帧续传。

### Cited Findings

- PMCA AdjustControl要求outer `response==0`，ProductInfo/FileControl则要求1。不能把同一个outer成功码套给所有pFunc。[各pFunc成功码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L983-L1004)
- A7CII `jiritsu`拒绝outer response非0或返回payload短于4；`struct.unpack_from('<I',out)[0]`取inner status，0视成功，`missing=True`且status=10000006时视缺失，其余非0报错，成功返回`out[4:]`。该方法不解析返回的族/命令echo。[status实现](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py#L404-L412)
- PMCA Senser参数为minSize=0x200、chunkSize=0x8000、maxSize=0x100000，PID0336特殊处理最小包。发送超maxSize时header.size仍表示剩余数据长度，接收可继续处理后续header；因此完整协议不是简单的“单个header+所有剩余USB字节”。[PMCA分块](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L833-L876)
- A7CII `length-delimited-zlp/3`增加短header、sequence+pFunc校验、已失败通道锁止、非空lookahead保存；仅CP0x603/0x40读取路径做对齐结束包处理，其他文件/设置快照保留其已有无eager-read行为。不能给所有read无条件追加“读一个结束包”。[A7响应framing](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py#L21-L104)

### Inferences

自己的离线parser采取更窄策略，不声称这些都是通用协议要求：

- 输入必须是immutable bytes、完整单frame；header≥12字节，声明payload≥4，实际长度必须严格等于12+声明值，拒绝截断和尾随字节。
- 验证pFunc=40、expected sequence、四个outer u8均0；只允许cmd15/17上下文，命令上下文来自调用者而非回复echo。未知flags拒绝，不自动容错。
- 局部返回数据上限64KiB，限制由自己的分析策略设定，**不是FX3协议上限，也没有通过read参数发送给相机**；大于上限和续传形式都拒绝。未来若真做传输，必须在读入payload前检查header，且单靠本parser不能限制相机实际发送量。
- inner status=0才返回数据；10000006仅作为upstream缺失候选抛异常，不默认为FX3同义；其他非0报错，不吞掉未知状态。setpath ack有额外数据也拒绝，这是本地保守策略。
- 设备内部packet state8/0x11、内部status偏移、outer response、wire payload status是不同层，不能相互替代。设备同事已发现内部handler写u32状态及raw-data处理，但最终USB包装未证，本parser仍不升级为FX3实测解析器。

### Gaps

尚无真实FX3 frame验证：header字段非零值是否有效、错误回复status清单、是否echo命令、零长度文件、文件数据总长、分块与终止包、状态码10000006、服务PID及上述最小包分支。不能把19个合成测试通过当成这些缺口关闭。

## 自己的离线codec交付了什么、如何验证？

### Takeaway

已实现并运行纯bytes分析工具：只提供候选setpath/read编码及单frame回复解析，没有USB/backend、认证、重试、相机文件操作或模块/固件写入接口。19项合成fixture测试全部通过，覆盖独立golden字节和主要畸形回复；这只证明本地策略与实现一致。

### Cited Findings

本地交付与实测收据：

- [offline_codec.py](../../work/sony-firmware-20261024/stage9-protocol/host/offline_codec.py)：自写实现；只导入stdlib dataclasses与struct；无设备backend。对外encoder仅cmd15/17，没有16/18/native/WBI编码接口。
- [verify_offline_codec.py](../../work/sony-firmware-20261024/stage9-protocol/host/verify_offline_codec.py)：只导入自己的codec，用固定hex golden fixture与畸形变体验证，不导入第三方源码。
- [offline-fixtures.json](../../work/sony-firmware-20261024/stage9-protocol/host/offline-fixtures.json)：固定请求/回复golden、限制、未验证项与本地运行结果。
- [source-receipt.json](../../work/sony-firmware-20261024/stage9-protocol/host/source-receipt.json)：固定来源URL/commit/hash、upstream比较结果、自写文件hash及下载源码删除收据。

执行`python3 -B verify_offline_codec.py`：19个测试方法，全部OK。测试包括每个截断前缀、超长、长度不匹配、尾随数据、错误sequence/pFunc、非零flags/response、错误inner status、缺失候选、setpath多余数据、64KiB边界、类型/长度参数、路径穿越/NUL/非ASCII、命令16/18及内部400F/4011作为上下文时拒绝。运行只使用自己的纯字节实现和合成数据，无相机行为。协调端随后独立检查AST并以`PYTHONDONTWRITEBYTECODE=1 python3 verify_offline_codec.py`复跑19项全部PASS；复核范围仍仅本地fixture和无设备I/O的实现，不能视为硬件协议验收。

固定候选read request（sequence2）：`0700000040000200000000000110110000ff00`。固定read回复fixture：`07000000400002000000000000000000414243`，表示outer size7、pFunc40、sequence2、outer response0、inner status0和ASCII ABC。它们是合成host布局fixture，不是设备抓包。

### Inferences

下一步仍应先由设备端同事完成活跃路由与最终序列化证据；如未来另有主动诊断授权，才讨论针对已验证目标的传输设计。当前本地codec可用于离线审阅字节、拒绝明显错误frame及对照未来获准获取的响应，不能直接拿来连接相机。

### Gaps

当前没有相机实测、真实USB trace或读回程序hash。本轮没有新增active能力，没有改变先前缓存PnP授权范围，也没有证明任何刷写失败后的救砖路径。
