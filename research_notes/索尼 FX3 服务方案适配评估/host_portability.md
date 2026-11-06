# A7CII / PMCA 主机协议移植到经典 FX3 7.02 的边界

## 哪些是可复用协议机制，哪些必须针对 FX3 重新证明？

### Takeaway

可复用的是分层协议构造、传输接口和有界错误处理的思路，不是把 A7CII 的 PID/型号改成 FX3 后运行整个 Session。最有价值的适用性结果是：Sony MSC 扩展协议在 PMCA 内通过抽象 SCSI 驱动传输，所以原生 USBSTOR/SPTI 存在承载候选；而服务认证使用 USB vendor control 与裸 bulk，属于另一条能力链。前者是源码推断，尚无本台 FX3 的主动传输验证。

本增量研究访问日为 2026-10-25；重新 `git ls-remote` 确认 PMCA master 仍为 `a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`、A7CII main 仍为 `b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d`。访问日不作为提交日期。目标条件来自协调者本轮任务：人工菜单 FX3 7.02、Windows 缓存普通 MSC 054C:0DA1、USBSTOR 健康；没有机身程序 hash。本子任务没有读取设备、卡或 GUI，也没有运行/导入下载的第三方代码。

### Cited Findings

- PMCA `_BaseSonyMscExtCmdDevice` 把 Sony 扩展请求包成 opcode `0x7a` 的 SCSI CDB，调用驱动 `sendWriteCommand` 后按需 `sendReadCommand`；它并未要求底层必须是 libusb。Windows `_MscDriver` 正好提供这两种 SCSI 接口。[Sony MSC 扩展](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L83-L112)、[Windows 原生 MSC](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/windows/msc.py#L95-L132)
- 相反，`SonySenserAuthDevice` 需要 `vendorRequestOut` 和裸 bulk `write/read`；PMCA GenericUsbDriver 提供这组接口，Windows 原生 `_MscDriver` 只提供 SCSI command/read/write。服务认证无法只靠替换普通 MSC PID 获得所需传输能力。[认证接口](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L890-L936)、[GenericUsbDriver](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/generic/__init__.py#L67-L100)、[原生驱动能力](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/windows/msc.py#L95-L132)
- PMCA 识别 service PID 的候选是 `02A9` 和 `0336`；认证在 PID=0336 时拼接对应认证材料，在其他 PID 使用另一数据处理分支；Senser 收包最小长度也以 PID=0336 分支。这说明 service PID 同时影响发现、认证和 framing，不能只修改一处查找。[候选身份](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L29-L45)、[认证分支](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L918-L936)、[收包分支](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L822-L876)
- A7CII 当前 transport 相比 PMCA 又改了 Senser 响应边界处理：校验短 header、sequence 和 pFunc，保存非空 lookahead，CP `0x603/0x40` 读路径才处理对齐后的结束包；这是一套针对其已测试行为的 framing，不是任意同品牌机型的协议保证。[A7CII length-delimited-zlp/3](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L21-L104)

以下“需改动”是离线移植设计，不是已完成适配；FX3 已知项仅限上述任务输入。

| 源码假设 | FX3 已知值/证据 | 必须调整的代码/契约 | 未闭合阻碍 |
|---|---|---|---|
| A7 普通 PID 写死 0E8A | 缓存为 0DA1 | 把普通身份发现抽成目标 profile；`get_device`、Camera 检测、usbidentity、正常返回等待必须共用同一 profile | 只证明缓存匹配，未证明端点可打开。[Session](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L322-L359)、[usbidentity](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/usbidentity.py#L4-L12) |
| USB product string 必须等于 ILCE-7CM2 | 人工型号 ILME-FX3；真实 USB product string 未主动读 | 型号判断须独立绑定到已核验的目标字符串，不能以人工型号替代 USB 响应 | 未取得描述符证据，不能放宽为“任意 Sony”。[型号 gate](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L334-L345) |
| 普通 USB 序列可用且稳定 | 未保存/验证该字段 | 保留每机绑定与隐私 hash；分别标记普通 USB 序列与服务序列，不能相互冒充 | 不能套用 A7 serial 格式/黑名单或无序列时绕过。[绑定实现](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/usbidentity.py#L1-L25) |
| GenericUsbDriver 按枚举顺序选第一个 bulk IN/OUT | 只有 USBSTOR 缓存，未知配置与端点 | profile 应明确目标接口、备用设置、端点地址、方向与最大包长；未验证前为空并拒绝服务操作 | MSC 与 service 的端点布局都尚未知。[端点选择](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/generic/__init__.py#L67-L100) |
| A7 服务身份固定 0336 | FX3 service PID 未知 | service PID、认证 profile、minSize/framing 必须成组参数化；保留 null blocker | 不能把 FX3A 或 A7CII 的 0336 自动赋给本机。[等待 service](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L344-L374) |
| 三轮 challenge-response，根据 ret2/8 选择 SHA1/SHA256，再发结束阶段 | 本台 FX3 未认证 | 认证对象/版本、返回码、长度、状态转换与 stop 语义须有目标证据；不更改 key/分支碰运气 | 普通 VID/PID 不证明认证兼容；设备端副作用未知。[认证](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L890-L936) |
| A7 服务身份绑定读整份 preset，用 key00E70003 的4字节序列 | 无 FX3 preset/hash | 诊断与全量 backup 获取分开；目标 serial 字段/长度未证明前不做该读 | 不应为“识别”默认大范围读设置。[service_identity](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L249-L257)、[默认 preset 读](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L367-L375) |
| A7 cooldown30秒、最多3次服务进入、可自动退服务 rescue | FX3 无同等字段日志 | 重试/退出策略独立 profile；本声明契约 retry=0、所有 auth/stop 禁用 | 不能拿 A7 时序证明 FX3 安全退出。[时序](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L259-L318) |
| Senser header/chunk/ZLP 与 CP read 收尾规则 | FX3 未取得服务响应 | 包构造与纯解析可复用思路；块长、边界、结束包、sequence/pFunc 校验目标化 | 任意错位可能让后续包解释错误，不能靠增大超时掩盖。[PMCA framing](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L822-L876)、[A7 framing](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L21-L104) |
| Jiritsu命令15/16/17/18、固定临时路径和 CP/AP keys | 无 FX3 机身程序 hash/布局验证 | 传输层与能力层分离，目标 profile 不提供文件/native/CP/AP能力 | 这些不是从普通 MSC PID 可推出的兼容项。[能力实现](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L398-L435) |
| RecoverySession 续接已认证0336并校验既存机身 | 当前只有正常 MSC | 恢复入口应要求既存 session/身份与明确状态收据，不能把它作为冷砖连接入口 | 它不会凭空建立冷启动恢复通道。[RecoverySession](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L438-L467) |

### Inferences

- 可把候选移植分成纯字节编码/解析层、操作系统传输层、产品协议 profile、授权白名单四层。前三层的存在都不替代第四层，也不把候选协议提升为已验证 FX3 支持。
- 主机 source 已有 Sony 通用协议骨架，因此“研究适配”是合理方向；“改两行就能安全用”没有证据。当前适配状态应是 **offline profile only / device operations disabled**。

### Gaps

- 没有 FX3 7.02 的 service 身份、接口布局、认证结果、完整回包 trace、主程序完整 hash、原生模块 ABI 或冷砖模式枚举证据。
- 本子任务没有对比 FX3A/经典 FX3 的设备端服务分发器。服务可进入性和正常主应用损坏后可恢复性仍是不同命题。

## USBSTOR/SPTI 能否支持下一步诊断，最容易漏掉什么隐式命令？

### Takeaway

原生 USBSTOR/SPTI 可作为“下一步标准 SCSI 查询”的候选底层，不应为了查普通设备信息先更换驱动。这个判断是源码与 Windows 官方接口能力推断，**不是本台 FX3 已通过测试**，当前也未授权执行 Sony 查询。原生 SCSI pass-through 不能直接替代 Senser 所需的 vendor USB control/bulk 接口。

### Cited Findings

- Microsoft 说明 IOCTL_SCSI_PASS_THROUGH_DIRECT 可让应用发送 SCSI CDB（有命令/方向限制），已有 class driver 时应把请求发给相应 class driver；还要求正确的数据缓冲区对齐和长度。此接口能力不是目标相机接受任意 Sony CDB 的保证。[Microsoft 原文，页面更新2021-05-18，本轮访问2026-10-25](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ni-ntddscsi-ioctl_scsi_pass_through_direct)
- PMCA Windows MSC 枚举依赖可移动盘符、存储号、磁盘与 USB 父子关系，且每 USB 只选首个匹配磁盘；`_getStorageNumber` 已打开存储句柄发 IOCTL。故 USBSTOR 缓存健康不保证这套枚举一定找到设备，尤其没有符合条件的盘符时；也不宜为诊断读取所有可移动盘的存储号。[枚举实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/windows/msc.py#L62-L92)
- 单次原生 SCSI 交换会以读写访问打开真实设备句柄，设 `TimeOutValue=5`，发送 SPTI；传输方向由接口参数控制。这不是缓存查询，句柄具有写访问也不等于该次查询已写介质。[原生传输](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/windows/msc.py#L100-L132)
- **隐式命令的精确计数**：`MscDevice(driver)` 的 `UsbDevice.__init__→reset→MscDevice.reset` 会调用一次 `sendCommand(6*b'\0')`，即**一次6字节全零CDB（TEST UNIT READY），不是6次命令**；`getDeviceInfo()` 再调用一次 INQUIRY allocation length5，按返回的 additional length 再调用第二次 INQUIRY。因此 `MscDevice(driver).getDeviceInfo()` 正常路径合计 **3次 SCSI 命令：1 TUR + 2 INQUIRY**，不能称“仅发一次 INQUIRY”。[构造与查询](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/__init__.py#L23-L64)
- **仅 libusb BBB 实现的条件性附加动作**：`_readResponse` 在 CSW status非0且 `failOnError=False` 时额外调用一次 REQUEST SENSE（18字节），若其自身失败则 `failOnError=True` 终止，非无限递归；bulk data读/写抛 GenericUsbException 时会 clearHalt 对应端点，再读状态。原生 Windows `_MscDriver` 则从同一次 SPTI 的 sense buffer解析错误，不能混称两者都自动发 REQUEST SENSE。[BBB响应/REQUEST SENSE](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/generic/__init__.py#L121-L172)、[原生sense](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/windows/msc.py#L100-L120)
- A7 `_query_initial_ready` 先 `MscDevice(driver).getDeviceInfo()`，再实例化继承 MSC 对象的 `BoundedInfoDevice(driver)` 查询 Sony model，因此**正常无重试基线是2次 TUR、2次 INQUIRY，及Sony0x7A OUT/IN各1次，共6次SCSI命令**；ReadyDriver 还可在限定 sense集合内重复 TUR，SonyBusy 可重复对应查询方向。这些实际次数高于入口名称暗示的一个“info”。[两个实例与重试门控](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L173-L239)、[MSC继承关系](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L83-L108)
- Sony “读取”model query 本身使用 OUT请求后IN响应；默认请求与响应缓冲区都是0x2000字节。只读语义不意味着USB或SCSI没有 OUT方向数据；OUT传输也不能单独证明写入闪存。[Sony命令封装](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L268-L291)

### Inferences

- 如果未来获得主动普通 MSC 查询授权，应新写一个只接受已核定单目标与显式命令白名单的精简传输入口；不要实例化会自动 TUR 的 MscDevice，也不要调用带全盘枚举的 MscContext 发现流程。第一阶段只考虑固定标准 INQUIRY；是否保留第二次 INQUIRY须写清长度上限，不能信任设备给的长度而无限扩展。
- SPTI路径不提供 vendorRequestOut，因此本次没有找到“不变更当前 USBSTOR 绑定，直接复用 A7 Senser认证”的完整主机路径。若另找 Sony SCSI service-entry 命令，需要新的设备端/维护者证据，不能自行把 vendor USB 请求塞进0x7A。
- 可复用有界超时、短传输拒绝、状态未知即停止等设计，但自动 REQUEST SENSE、clearHalt、retry、auth.stop 都须列入契约。不能因为异常处理名为 cleanup/rescue 就默认有权限。

### Gaps

- Windows真实权限、可用句柄、对齐、目标SCSI支持、卡状态及是否有盘符均未主动验证；不能把缓存驱动健康宣称为SPTI已通过。
- 没有执行 Sony0x7A、INQUIRY、TUR、REQUEST SENSE、端点读取或驱动操作。以上只是下一步设计依据。

## 现阶段可交付什么适配契约？

### Takeaway

已交付非可执行 JSON：只把当前已知的普通身份写入，service、端点、认证、程序hash全部留空并列为阻碍；所有真实设备能力都是false。它是复核范围的声明，不是相机适配器，也没有提供任何服务命令开关。

### Cited Findings

当前公开实现把服务进入、身份绑定、backup读取、自动重试、退出组合在同一 Session；重用该对象会把多个行为一并带入。原生 Windows MSC 与 GenericUsbDriver 又是不同接口能力，必须在候选设计中分开。[A7 Session](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L322-L397)、[Windows MSC](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/windows/msc.py#L95-L132)、[generic](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/generic/__init__.py#L67-L100)

本增量文件：

- [声明式 compatibility-contract.json](../../work/sony-firmware-20261024/stage8-adaptation/host/compatibility-contract.json)：包含各级 capability禁用值、未知目标字段与隐式I/O计数。
- [source-receipt.json](../../work/sony-firmware-20261024/stage8-adaptation/host/source-receipt.json)：6份原始源码的URL/固定commit/SHA-256和删除收据；新增代码未执行，结项删除本子任务下载的原始参考源码。
- 上阶段完整调用链保持在 [host.md](../索尼%20FX3%20独立诊断与恢复入口/host.md)，本次没有改写。

### Inferences

应把“具备可研究的通用协议骨架”“完成FX3离线profile”“成功一次正常相机受控诊断”“主应用损坏可恢复”“刷写失败可救回”作为五个独立验收结果。当前只达到前两者中的设计/声明层面，没有硬件适配通过，也没有新增实际救砖保证。

### Gaps

当前所有未闭合项都由契约阻断；没有以 PID/型号替换绕过守卫，没有开启 service 命令，也没有创建可执行设备适配器。本轮授权仍只有 Windows 缓存PnP，不包含本文讨论的任何主动查询。
