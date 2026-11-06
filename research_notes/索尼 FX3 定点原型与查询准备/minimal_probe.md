# Windows 11 x64 最小 MSC 查询准备

## 1. 当前交付能做什么，下一步到底开放什么？

### Takeaway

已交付可审查源码和离线 fixture；**主动入口关闭、绑定缺失、尚不可运行主动查询**。本轮没有连接 Windows、相机或桌面 UI，没有在 Windows 编译或执行脚本，也没有获取序列号、读取卡或相机文件；本轮本地验证回执见 [offline-verification.json](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/offline-verification.json)。

### Cited Findings

- 当前真实缓存采于 `2026-10-25T09:54:17.7315333Z`，只有一个匿名 USB 父节点：`054C:0DA1`、`ILME-FX3`、`USBSTOR`、Microsoft 已签名 `10.0.26100.9444`。它没有 Disk 类子节点、磁盘接口路径、父子关系或机身身份哈希，所以不能把该记录转换成任何可打开目标。此结论直接来自[现有缓存](../../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/sony-pnp-inventory.json)，不是本轮新采集。
- 默认命令只输出计划 JSON，且在 `Add-Type` 之前退出。下列命令是包目录内的**默认离线复核**，不会编译或调用 native 声明：[Review-Fx3Msc.ps1](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Review-Fx3Msc.ps1)。

```powershell
& .\Review-Fx3Msc.ps1 -Mode DryRun
```

- 下列是给协调者审查的**后续仅缓存关联命令**，本轮没有执行。执行条件是先把本包放在已确认的 Windows 主机本地任务目录，输出也只能放主机本地任务目录；不得选相机卡、映射设备、共享路径或设备命名空间。已有输出会拒绝覆盖；无自动 UAC、ExecutionPolicy 绕过、驱动变更或远程调用。它只编译 `Fx3CachedAssociations.cs`，不会编译 `Fx3OneInquiry.cs`：[脚本源码](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Review-Fx3Msc.ps1)。

```powershell
& .\Review-Fx3Msc.ps1 -Mode CachedAssociations -OutputFile .\fx3-cached-associations.private.json
```

- 缓存模式枚举 present 的 `GUID_DEVINTERFACE_DISK` 接口，用返回的 `SP_DEVINFO_DATA.DevInst` 和 `CM_Get_Parent` 沿缓存父链寻找已知 USB 硬件身份，并核对 `ILME-FX3`、USB 父服务 `USBSTOR`、子服务 `disk` 和 started/active 状态；只对匹配的 Sony 节点导出关联，不打开任何磁盘句柄。[磁盘接口官方定义](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/guid-devinterface-disk)、[SetupDiGetDeviceInterfaceDetailW](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupdigetdeviceinterfacedetailw)、[CM_Get_Parent](https://learn.microsoft.com/en-us/windows/win32/api/cfgmgr32/nf-cfgmgr32-cm_get_parent)。
- 接口路径必须使用 SetupAPI 原样返回的值；不通过解析其符号名识别机身，不拼接 `PhysicalDriveN`，不轮流尝试磁盘，不取第一项兜底。Microsoft 明确接口路径可以交给 `CreateFile`，并要求不要解析符号路径；本实现额外拒绝所有包含 `PhysicalDrive` 的路径。[官方说明](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupdigetdeviceinterfacedetailw)、[选择器源码](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Fx3CachedAssociations.cs)。
- 缓存输出私有文件包含接口原始路径；路径可能嵌有不透明唯一标识，不应贴进共享报告。父/子 instance ID 仅输出 SHA-256，不单独查询 `SerialNumber` 属性；后续签名驱动缓存按 USB 父节点 ID 哈希精确关联，记录匹配数、provider/version/signed。公开 stdout 仅输出候选数、INACTIVE 和文件哈希：[实现](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Review-Fx3Msc.ps1)。

### Inferences

- 缓存接口 + DevInst + 父链比单凭 VID/PID 选择路径更可复核；这仍是 OS 元数据关联，不是相机返回的机身身份或固件验证。`BusReportedDeviceDesc` 是 PnP 保存的总线描述，不能当作本轮实时设备字符串。[属性来源](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/devpkey-device-busreporteddevicedesc)。
- 缓存模式 stdout 预期为 `CACHED_ASSOCIATION_CANDIDATE_COUNT=n`、`STATE=INACTIVE; NO_DEVICE_HANDLES; NO_SCSI_COMMANDS`、`PRIVATE_OUTPUT_SHA256=...`。这里的 NO_DEVICE_HANDLES 专指相机/磁盘接口；为写主机回执会正常打开主机文件。JSON 的 `binding_status` 只能为 MISSING、AMBIGUOUS、INCOMPLETE 或 UNIQUE_CACHED_CANDIDATE，`active_probe_ready` 始终为 false。[脚本](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Review-Fx3Msc.ps1)。

### Gaps

- 缓存关联源码未在 Windows 编译或实测；C# / PowerShell 语法、运行时 marshalling 和当前 Windows 环境都尚未验收。[离线回执限制](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/offline-verification.json)。
- 真实 Disk 接口、唯一 LUN、每机绑定哈希和 adapter alignment mask 全部缺失；如果两张卡产生两个接口，当前选择器会整体拒绝，不能擅自挑其中一个。[选择器](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Fx3CachedAssociations.cs)。

## 2. 单次 INQUIRY 的精确 API、ABI 和权限是什么？

### Takeaway

拟议的唯一主动命令为普通 SCSI INQUIRY：`12 00 00 00 60 00`，DATA_IN、allocation 96、应用层仅一次同步提交、`TimeOutValue=3` 秒。只保留供审查的 private 方法，位于未定义的编译符号内，无主动 CLI 或 public 入口；当前包无法启用该方法。[源码](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Fx3OneInquiry.cs)。

### Cited Findings

- 选择缓冲式 `IOCTL_SCSI_PASS_THROUGH` 而非 DIRECT：Microsoft 将它用于小于 16 KB 的小请求，要求同步发送、目标有 class driver 时经 class driver，不允许绕到 port driver。96 字节适合这个 API；不新增查询适配器属性的 IOCTL。[官方 IOCTL 说明](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ni-ntddscsi-ioctl_scsi_pass_through)。
- IOCTL 值为 `0x0004D004`：设备类型 controller=4、function=0x401、METHOD_BUFFERED=0、access=READ|WRITE=3。其 RW 访问位来自 Microsoft SDK 头文件；因此未来 `CreateFileW` 拟用 `GENERIC_READ|GENERIC_WRITE=0xC0000000`，share READ|WRITE=3、OPEN_EXISTING=3、flags=0，security/template=NULL。这意味着句柄具有写能力；实际构造的 CDB 始终只有 DATA_IN。不能把 RW 句柄叫作只读权限句柄。[Microsoft 头文件](https://raw.githubusercontent.com/microsoft/win32metadata/main/generation/WinSDK/RecompiledIdlHeaders/shared/ntddscsi.h)、[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)。
- Microsoft 明确 SPTI 本身不普遍要求 administrator，但要求目标 RW 访问。本原型使用现有 token，一次打开失败即停；不以管理员组为硬门槛，也不要求扩大权限或尝试 UAC。[官方权限说明](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ni-ntddscsi-ioctl_scsi_pass_through)。
- Windows x64、Pack=8 下本实现 ABI 如下。数值由官方字段定义加本地 `clang -target x86_64-pc-windows-msvc -fsyntax-only` 静态断言推导，**不是当前 Windows SDK/runtime 验收**。[SCSI_PASS_THROUGH](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ns-ntddscsi-_scsi_pass_through)、[SP_DEVINFO_DATA](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/ns-setupapi-sp_devinfo_data)、[SP_DEVICE_INTERFACE_DATA](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/ns-setupapi-sp_device_interface_data)、[本地 ABI fixture](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/layout_fixture.c)。

| 结构 | sizeof | 关键偏移（字节） |
|---|---:|---|
| SCSI_PASS_THROUGH | 56 | Length 0；CdbLength 6；SenseInfoLength 7；DataIn 8；DataTransferLength 12；TimeOutValue 16；ULONG_PTR DataBufferOffset 24；SenseInfoOffset 32；Cdb[16] 36 |
| SP_DEVICE_INTERFACE_DATA | 32 | GUID 4；Flags 20；ULONG_PTR Reserved 24 |
| SP_DEVINFO_DATA | 32 | GUID 4；DevInst 20；ULONG_PTR Reserved 24 |
| SP_DEVICE_INTERFACE_DETAIL_DATA_W 固定部分 | 8 | cbSize=8；WCHAR DevicePath 起点 **4**，不是 8 |

- SetupAPI detail 使用两次 metadata 调用：第一次 NULL/0 取 RequiredSize 并预期 ERROR_INSUFFICIENT_BUFFER；第二次按 RequiredSize 分配，写 cbSize=8，从 byte 4 读 UTF-16 路径。两个 fixed data 结构 cbSize 都是32。该两次调用不是两次相机查询。[函数说明](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupdigetdeviceinterfacedetailw)、[detail 结构](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/ns-setupapi-sp_device_interface_detail_data_w)。
- 拟议 IOCTL packet 固定160字节：56字节 header、8字节零 padding、96字节输入数据区；Length=56、DataBufferOffset=64、DataTransferLength=96、CdbLength=6、DataIn=1、TimeOutValue=3、SenseInfoLength=SenseInfoOffset=0，其余初值0。不申请 sense buffer，不发送 TEST UNIT READY、REQUEST SENSE、Sony ExtCMD、INIT 或认证；无重试、模式切换、reset、清错、rescue、媒体或文件读写。[本包源码](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Fx3OneInquiry.cs)。
- DataBufferOffset 必须满足目标对齐要求。本包不知道当前 alignment mask，不能把 offset64 视为已证实可用；private 源码要求已审查的、形如2的幂减1且≤63的 mask，并验证 offset 位约束。它没有获取 mask 的额外 IOCTL。若将来只能用额外设备查询获得该值，需要另行审查命令范围。[官方结构要求](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ns-ntddscsi-_scsi_pass_through)。

### Inferences

- 将来若允许运行，应用预期记录一次 CreateFile 结果、一次 DeviceIoControl 结果/Win32 error、ScsiStatus、bytesReturned 与实际 DataTransferLength。成功仅接受 ScsiStatus=0、36–96字节、返回边界完整，解析 Vendor[8]、Product[16]、Revision[4]；超长或残缺都停，不按 AdditionalLength 再查询。非ASCII标识也停；未知响应可以保存在主机私有回执，不能触发额外设备 I/O。[INQUIRYDATA 字段定义](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/scsi/ns-scsi-_inquirydata)、[纯解析器](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Fx3OneInquiry.cs)。
- Revision 是 vendor 定义的四字节产品修订字段；不能据此证明完整 FX3 7.02 机身程序哈希或恢复能力。[官方字段定义](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/scsi/ns-scsi-_inquirydata)。

### Gaps

- `TimeOutValue=3` 是端口驱动考虑超时的秒数，不是 CreateFile 或整个同步调用严格在三秒内返回的保证。不得承诺硬墙钟≤3秒；当前不采用异步、强制中断或第二条命令。[超时字段](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ns-ntddscsi-_scsi_pass_through)、[同步调用行为](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-deviceiocontrol)。
- 本源码只能证明**应用构造并提交一条 CDB**，不能证明 Windows class/port/USB 栈或相机不会自主进行 auto-sense、恢复、后台命令或协议级重传。SenseInfoLength=0 不能被当作整栈“永不 REQUEST SENSE”的证据；若要求总线上严格只出现一条命令，当前方案不满足已验证条件，必须继续保持入口关闭。[API 作用范围](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ni-ntddscsi-ioctl_scsi_pass_through)。

## 3. 已验证边界和最终审查包是什么？

### Takeaway

43项本地静态/合成检查通过；**不等于 C#/PowerShell 编译通过、Windows 运行通过或相机查询通过**。当前只适合交给协调者复核以及规划下一次仅缓存关联采集；主动查询仍无可执行命令。[离线回执](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/offline-verification.json)、[审批包](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/approval-packet.json)。

### Cited Findings

- 检查覆盖：Microsoft x64 target 结构大小/偏移和 IOCTL 常数；固定零初始化160字节包与唯一 CDB；默认 DryRun、主动代码条件排除及仅一次 call site；0/2候选、未知路径、PhysicalDrive、错误VID/PID/型号/服务、未started/未active、断父链全部拒绝；合成 INQUIRY 正常、截断、超长、声明不足、非ASCII。Python selector/decoder 是独立规范 fixture，未执行 C# 实现，不应把43项说成43项 Windows 单元测试。[验证脚本](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/offline_verify.py)。
- 审批包绑定本包源码、fixture、验证回执、官方来源 receipt、说明文件以及已知旧缓存的 SHA-256。它明确 `binding_missing=true`、`active_entry_disabled=true`、`ready_to_run=false`、`active_execution_command=null`，不是用户已授权主动访问的回执。[approval-packet.json](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/approval-packet.json)。
- 本轮保存官方来源 URL、抓取UTC、bytes、SHA-256；原文缓存在完成来源 receipt 后删除，只保留 receipt，不残留第三方 SDK/header 副本。[primary-source-receipt.json](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/primary-source-receipt.json)。

### Inferences

- 未来真正的最终审批应放在：缓存关联/驱动事实得到复核、唯一目标和对齐问题闭合、Windows 源码编译验证完成、额外命令和栈行为边界明确、形成含**真实本地路径私有绑定哈希与最终源码哈希**的新审批包之后。编译符号、公开主动入口、source/binding 的任何修改都要重新生成哈希，不沿用本包准备回执。[当前关闭门禁](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/approval-packet.json)。
- 预期失败条件均停在当前步骤：缓存读失败、歧义或身份不完整、驱动签名缓存精确匹配非一条、绑定变化/过期、未知alignment、权限拒绝、打开失败、IOCTL失败、非GOOD状态、残缺或异常响应；不选择替代路径、不重试、不自动提权、修复、rescue或切换USB模式。[源码](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/Fx3OneInquiry.cs)。

### Gaps

- 本包没有建立救砖保障，也没有解决主录 HD HEVC、机身程序读回/哈希、模式写入或真实录像验收；标准 INQUIRY 即使将来成功也不能替代这些验收。[本包能力边界](../../work/sony-firmware-20261024/stage12-prototype/msc-probe/approval-packet.json)。
