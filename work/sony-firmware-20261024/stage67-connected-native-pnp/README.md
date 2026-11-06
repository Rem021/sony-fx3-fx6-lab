# FX3 重新连接后的缓存筛选与 USB 身份证据

用户确认已接好相机并保持MSC后，新做了一次仅系统缓存的当前连接筛选。`054C:0DA1`没有匹配根节点，查询正常退出0；没有进入设备树或磁盘分支。因此磁盘候选数量、当前驱动与接口状态仍为UNKNOWN，不能把这条筛选结果直接解释为相机没接好。

## Windows 新快照

本次唯一查询发生于2026-10-26 16:41:07 UTC；旧材料保留，五件脱敏回执已传回本阶段目录。见[总回执](from-windows-public/receipt.json)、[命令](from-windows-public/commands.json)和[节点状态](from-windows-public/nodes.json)。原始stdout/stderr保留在Windows私有目录，只传回其哈希。

后续需要按Sony厂商及ILME-FX3或Sony DSC型号交叉核对缓存，避免固定使用旧VID/PID造成漏检。完整任务文件已通过UU发送到本机系统C盘的本次任务目录，发送计数49→50；接收上述五件回执后计数50→55。任务原文与传出副本逐字节一致，SHA256为`c3a5c02b8e1f3609a49b73d7a7e47571d73d29f45780e443ce85ede3da37f078`。

远程键盘未能把交叉核对指令送入Windows输入框；尚未确认原因，也没有归因于输入法。用户随后在原FX3 Codex会话提交了读取任务文件的一行指令；UU界面已观察到新消息及处理状态。**交叉核对已提交，最终结果仍待回传核对。** 本轮此前的新快照任务已经完成。没有改变UU快捷键、权限、执行策略或驱动。

## 原固件中的 USB 组件

从固定SHA256的官方7.02分区镜像读取7件普通文件，包括Sony存储模块、扩展命令模块、通用存储模块及USB相关库。没有挂载镜像，没有执行脚本、模块、内核或下载源码，也没有向相机传送这些文件。[提取收据](usb-original-extraction.json)逐件保存来源inode、大小和哈希。

在`libInfraUsbCmn.so`中找到3份初始INQUIRY字节模板，厂商字段为Sony、产品字段初始为空格、版本字段均为`1.00`。另5个名字相似的8字节对象是指向DEFAULT的静态ABS64重定位，不能误当作5份响应头。运行时的加载、符号介入、初始化及产品字段填充仍未观察。

原`usbg_storage.ko`的`inquiry_std`为632字节，仅有一条CALL26重定位指向memcpy；`checkExtCommand`及`storage_detect_ExtCommand`的静态调用也已记录。Sony公开7.00源码中的普通EVPD0 INQUIRY从每个逻辑单元所配置的响应数据复制有限长度，初始化结构提供逻辑单元数量和逐单元配置，扩展事件也携带LUN。这些与原7.02选定函数作了对应核对；不是整个7.00源码与7.02构建完全匹配，也不是当前实机已加载该组件的证明。[Sony公开源码页面](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)。

由此保留两项实际约束：普通INQUIRY的通用版本字段不能充当实机7.02或同机程序指纹；同一USB父节点和相似身份字段也不能替代多个磁盘接口之间的明确选择依据。见[原字节与源码对应记录](usb-inquiry-source-correlation.json)。

## 后续诊断的边界

微软定义的SPTI缓冲区偏移须符合设备对齐要求，适配器描述符可提供AlignmentMask。取得该描述符需要新的设备控制请求，不能将它冒充本次已授权的PnP缓存查询。[SCSI_PASS_THROUGH](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ns-ntddscsi-_scsi_pass_through)；[STORAGE_ADAPTER_DESCRIPTOR](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddstor/ns-ntddstor-_storage_adapter_descriptor)。

旧原型中的应用调用次数和超时参数不能保证总线只出现一次传输或硬性三秒结束。微软通用存储栈文档描述了分层重试及可伸缩超时，但本机FX3的实际USBSTOR行为尚未追踪，不据此声称它已发生任何重试或复位。[存储驱动重试](https://learn.microsoft.com/en-us/windows-hardware/drivers/storage/storage-class-driver-s-retryrequest-routine)；[端口驱动超时](https://learn.microsoft.com/en-us/windows-hardware/drivers/storage/capabilities-provided-by-scsi-port)。

当前仍没有唯一的当前设备绑定，也没有完成最终主动诊断源码的Windows编译及上述对齐等条件核对。主动查询方案尚未就绪，没有申请或执行接口访问。全部16项主录、音画、长录、冷启动、同机健康备份与恢复要求保留；goal_complete=false，persistent_write_release=false。
