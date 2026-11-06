# FX3 主机侧诊断入口、隐含动作与最小探测边界

核查日：2026-10-25。范围是静态阅读公开主机源码，没有运行任何下载代码，没有打开相机、USB、存储卡或 Windows GUI。目标机身份由主协调者本轮盘点提供：经典 ILME-FX3、7.02、普通 MSC 054C:0DA1、Windows 11 x64、Microsoft USBSTOR；本子任务没有独立重读设备。

固定来源：Sony-PMCA-RE master 的本轮 `git ls-remote` 结果是 `a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`；A7CII 项目按主协调者已固定的 `b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d` 阅读。PMCA 提交日期本次未成功取得，不将访问日期冒充提交日期。逐文件 URL、提交号、字节数与 SHA-256 在同任务 [source-receipt.json](../../work/sony-firmware-20261024/stage7-entry/host/source-receipt.json)；下载的原始参考代码结项删除，只保留分析与收据。

## Key question：PMCA 的 info / serviceshell / updatershell 真正做什么？

### Takeaway

这三个现成命令都不符合当前“只读 Windows 缓存盘点”的授权。`info` 会真实打开接口并发送 Sony 指令；`serviceshell` 明确发送开始、认证、切换服务身份及退出操作；`updatershell` 走自定义 FDAT 的 updater 传输流程。不能根据 `writeFirmware` 函数名断言具体负载必然永久写入闪存，也不能根据 `info` 名称断言绝无相机状态变化。

### Cited Findings

- CLI 映射是 `info → infoCommand`、`updatershell → updaterShellCommand`、`serviceshell → senserShellCommand`。[CLI 入口](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca-console.py#L65-L88)
- PMCA 的 `UsbDriverList.listDevices` 不只列缓存：它对每个发现的设备调用 `openDevice`；后续 MSC 检测调用 `getDeviceInfo`，MTP 检测也调用设备信息接口。识别 MSC “Sony 相机”的条件是 SCSI manufacturer/model 特征，注释称其为 guesses，不是对 FX3 型号与固件的验证。[发现与打开](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L113-L214)、[识别谓词](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L37-L54)
- `infoCommand` 的 ExtCmd 路径：`getCameraInfo()` → `SonyUpdaterCamera(...)` → `updater.init()` → `getFirmwareVersion()`；还尝试 `getLensInfo()` 与 `getGpsData()`，打印序列号等信息。AppInstallDevice 分支会调用 `installApp(device)`。因此不能直接复用整个 info 作“最少读取”。`init()` 源码只显示发送 `CMD_INIT` 并解析回应；其 FX3 7.02 上的设备端持久副作用为 **UNKNOWN**，没有证据称它写固件。[info 调用链](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L231-L272)、[init 与版本查询](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L559-L570)
- Windows 原生 MSC 驱动 `_sendScsiCommand` 对设备调用 `CreateFile(... GENERIC_READ | GENERIC_WRITE ...)`，然后 `DeviceIoControl(IOCTL_SCSI_PASS_THROUGH_DIRECT,...)`。即使命令只读，它也需要真实设备句柄及 SCSI 传输；这不是 PnP 缓存查询。句柄带写访问本身不等于已写入介质。[Windows MSC 实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/windows/msc.py#L97-L131)
- `serviceshell` 的普通 MSC 路径要求 GenericUsbDriver；当前 USBSTOR 原生路径不满足时会退出并提示 Zadig/libusb-win32。它先 `start()`、`authenticate()`，等待服务设备重新枚举，再对服务身份第二次 `start()`、`authenticate()`，进入 shell，`finally` 中 `stop()`。驱动替换与服务认证是两项真实操作，不能以“启动只读 shell”为由合并授权。[完整 serviceshell 流程](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L656-L710)
- `SonySenserAuthDevice.start/stop` 分别发送 vendor OUT request `(1,0x37ff,0xd7aa)` / `(1,0xc800,0x2855)`；认证还通过 bulk write/read 进行 challenge-response（阶段 1/3 循环及最后阶段 5）。这不是读描述符。主机只显式发送这些请求，设备端是否额外保存日志/标志，仅凭此类无法证明。[认证实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L890-L936)
- Senser shell backend 启动会 `readHasp`；交互 shell 会 `setTerminalEnable(False)` 再 `True`，结束后 `False`；同 backend 同时暴露读写文件、读内存、写 backup 和 `saveBackup(0)`。所以进入通用 shell 不是仅开放一个固定只读操作的最小界面。[Senser backend](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/platform/backend/senser.py#L5-L35)
- `updatershell` 先按型号查 `updatershell/fdat` 中的 `.hdr` 与 `.dat`；缺少型号 payload 会拒绝。随后走 `firmwareUpdateCommandInternal`：`init`、`checkGuard` 上传待检内容、查询版本、普通模式下 `switchMode()`、等待 updater 身份、`writeFirmware()` 上传、`complete()`，再开启 updater shell。不能把“支持 Sony 检测”当成“存在 FX3 7.02 自定义 FDAT”。[FDAT 查找](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L319-L338)、[updatershell/更新传输](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L350-L423)

### 调用与副作用矩阵

下表依上列固定源码调用链整理；“未知”不表示已发现持久写入。

| 入口/操作 | 真实设备传输 | 认证/模式状态 | 文件/负载/设置 | 持久副作用结论 |
|---|---|---|---|---|
| Windows 缓存 PnP | 不打开相机接口 | 无 | 仅主机证据文件 | 本契约不写相机 |
| PMCA 自动发现 | 开接口、MSC/MTP 设备查询 | 未见显式认证 | 设备信息 | 不能称缓存检测 |
| PMCA info（ExtCmd） | Sony model、INIT、version、lens/GPS | 初始化 updater 协议 | 无显式 firmware payload | INIT 设备端效果未知 |
| PMCA serviceshell | vendor OUT、bulk challenge-response | 进入 service、二次认证、stop | backend 可读写/终端开关 | host stop 未显式调 WBI；设备端未知 |
| PMCA updatershell | guard/payload/update 传输 | 进入 updater、complete | 自定义 FDAT 上传 | 是否永久落盘须审具体 payload/设备端 |
| A7CII USB 稳定性 | 认证后多轮程序文件读取 | service 进入/退出；失败可 rescue | 本函数不上传 worker、不写程序/设置 | 不等于零模式副作用，不适配 FX3 |
| A7CII native read-only probe | 上传并执行模块/结果回读 | 依赖服务连接 | /tmp 写入/删除 | 不能称不写相机 |
| A7CII property/save | service backup 调用 | mutating | AP/CP/backup/save | 设置持久化路径，单独授权 |
| A7CII checkpoint WBI | native invoke | 按 runtime 状态调用 | 上传 wbi.so，mode0/1 | 与通用 auth.stop 分开；FX3 映射未证 |

### Inferences

`updatershell` 的确定事实是传输自定义更新负载及改变 updater 会话/模式；具体 FDAT 处理器是否仅驻留 RAM、会触及哪些闪存，必须再核对该目标型号 payload 和设备端 updater，不能从函数名推定。当前授权下，连先调用 `checkGuard` 都不应执行。

### Gaps

未发现本次源码能单独证明经典 FX3 7.02 的认证协议、通用 shell 命令或 FDAT payload 已被验证。没有将 FX3A 的成功/失败报告泛化到经典 FX3。未证明 FX3 设备端处理 CMD_INIT、Start/StopSenser 时绝无任何持久副作用。

## Key question：A7CII 的“USB 稳定性 / 只读”是否可直接迁移？

### Takeaway

不可直接迁移。最新 USB 稳定性子程序本身不上传 native worker，但默认连接已包括服务模式认证、重枚举和完整 backup preset 读取；“不写固件和设置”是其应用层声明，不等于“不开接口、不认证、不切模式”。它还明确只接受 A7CII 的普通 PID 0E8A 与 ILCE-7CM2；经典 FX3 的 0DA1 不会匹配。

### Cited Findings

- `devicesession.modules()` 优先选 `src/camera_runtime`，不存在时才回落旧 `src/fl23`。因此当前入口不能只审旧 transport。当前 runtime core 明确 `MODEL='ILCE-7CM2'`、`VERSION='2.01'`，还固定程序 hash、CP/AP keys 与 native 临时文件名。[模块选择](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/devicesession.py#L12-L20)、[型号/资产范围](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/core.py#L10-L23)
- `usbcheck.run` 默认创建 `looktool.devicesession.Camera()`，服务连接准备好才计时；每轮读 `/usr/lib/appFw.so` 与 `/cp/cpapp-b.bin`，默认至少 5 轮、120 秒、每文件 1–256 MiB，逐字节与首轮比较并检查速率。它自身没有调用 invoke/native staging，也明确通过不保证刷写期间不断线。[USB 稳定性实现](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/desktopapp/usbcheck.py#L1-L95)
- `Camera._connect` 搜索普通 `054C:0E8A`；默认正常连接进入 `transport.Session`。Session 先检查 USB product string 等于 core.MODEL，再普通侧 start/authenticate，等待 `0336`，服务侧再次 start/authenticate，并 `getBackupPresetData(True)` 生成机身绑定。源码可最多尝试 3 次服务进入（SERVICE_ATTEMPTS），两次间冷却；并不是固定“一次认证后停止”的诊断。[Camera 连接](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/devicesession.py#L29-L76)、[Session](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L259-L382)
- 已知初始 busy/no-media 的后备 `open_service` 也会真实 SCSI INQUIRY、校验 Sony manufacturer、普通侧 start/authenticate、等待 0336、服务侧 start/authenticate；注释只称临时 USB 身份变化，而非无设备写传输。[后备连接](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/usbservice.py#L1-L46)
- 正常退出 `Session.__exit__` 调用 `auth.stop()`；健康状态未知且未发 mutating 命令时，会 `_rescue_service()`，新开 0336 句柄并尝试 start/authenticate/stop。主机的“read-only rescue”同样有控制 OUT 与认证传输。它只是尝试退服务模式，不是刷坏闪存后的救砖实现。[退出/自动退服务](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L296-L318)、[Session exit](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L383-L423)
- 一般 native probe 与 usbcheck 必须区分。`temp_write` 发 Jiritsu command16 写 `/tmp/jiritsu/`；`invoke` 会上传 staged native 模块、可选 request、`libJit.so`，读结果再 command18 删除临时文件。因此名为 read-only model/runtime probe 的 native 工作器仍有文件上传、执行和清理。USB 稳定性函数本身不走此 invoke。[临时文件/工作器调用](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/devicesession.py#L109-L133)、[invoke](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/devicesession.py#L158-L197)
- `property_write` 与 `save_settings` 分别调用 `writeBackup`、`saveBackup(0x02cf)`，属于应单独审计的设置写入。Jiritsu16/18、CP write、AP write 都会设置 mutating 标记，使自动退服务逻辑停止适用。[设置写入门控](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/devicesession.py#L122-L133)、[底层 mutating 标记](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L398-L435)

### Inferences

删掉 PID/型号守卫只能让不适配的代码继续执行，不能增加 FX3 支持；固定内存/属性 key、native 模块、程序 hash 都仍针对 A7CII。项目的“只读”通常描述固件/设置不落盘，不能作为当前缓存授权的同义词。

### Gaps

源码默认工厂到传输链已追到，但没有实测其 Windows 自动驱动准备回调。不能在本机为了“看看能否连接”先启动桌面工具，因为它可能进入已超出当前授权的连接或驱动流程。

## Key question：哪些“退出/收尾”涉及持久 WBI，哪条入口独立于主应用？

### Takeaway

主机 `auth.stop()` 与 native WBI invalidate 是可区分的两条调用链。不能因为固件存在持久 WBI 写函数，就说所有退出服务都会调用它；也不能因为主机没有显式写文件，就保证设备端 stop 没有内部副作用。服务入口在主机侧绕过正常 getCameraInfo，但尚不足以证明经典 FX3 主应用损坏后仍可从冷启动进入。

### Cited Findings

- A7CII `checkpointjob.native(kind='wbi')` 选择 `src/fl23/assets/wbi.so`，以 `A7WBI001`、mode 与 request/result 文件，经 `invoke` 上传执行；checkpoint 恢复在写入程序/设置、再读 runtime 后，若 `image_mode=='2'`，依次 `native(wbi,0)` 和 `native(wbi,1)`；随后才是 `RESTORED_AWAITING_RELOAD` 与手动断电重启提示。这不是 Session 的通用 stop。[WBI native 分发](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L65-L86)、[恢复收尾](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L184-L205)
- PMCA 正常型号查询通过 SonyExtCmdCamera 的 `DevInfoSender_GetModelInfo`；A7CII 当前普通 Session 则用 USB product string 后直接 vendor start/authenticate，服务身份绑定用 backup preset 序列字段，并明确注释“不经过那个 application query”。这证明“避免正常应用信息查询”这一主机调用链事实。[正常应用查询](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L281-L291)、[服务身份绑定](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L249-L257)、[服务进入](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L334-L375)
- 现有 `RecoverySession` 注释是续接已认证的服务 endpoint，获取阶段不发 start/authenticate/stop；这要求服务设备已经存在以及已记录的机身身份，不是从未知冷砖状态强行启动服务。[RecoverySession](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L438-L465)

### Inferences

独立性应拆成三级：① 主机命令不调用 app 查询；② 相机端服务文件/backup 控制器不依赖 app 正常响应；③ 主应用坏、启动镜像失效时仍能冷启动并枚举。当前主机源证据可支持①，不能独立证明②或③。已经进入 updater/service 的设备可被相应主机类识别，不等于这些模式有不依赖损坏组件的硬件进入路径。

### Gaps

本子任务没有分析 FX3 原生 WBI worker 或设备端 Start/StopSenser 分发器；固件分析者发现的 `/dev/nflasha5` 持久写入，应由其设备端证据单独归属。不能把 A7CII checkpoint 的 WBI mode1 映射直接套到 FX3 地址，也不能将 auth.stop 与该写入等同。

## Key question：下一步最小探测契约是什么？

### Takeaway

当前可执行范围仍是缓存 PnP 盘点。不存在经此审计就可以直接运行的“FX3 安全 service probe”成品。可以先准备一个独立审计的固定命令白名单，再取得与实际动作一致的授权；不是授权一次“只读”就顺带执行认证、切模式或驱动替换。

### Cited Findings

现成命令的超范围动作见上述入口，特别是 PMCA 打开设备与 updater.init、serviceshell 两阶段认证、A7CII USB 稳定性默认 Camera() 连接链。[PMCA info](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L231-L272)、[A7CII usbcheck](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/desktopapp/usbcheck.py#L27-L55)

### Inferences

建议把后续审核拆成以下具体边界，均只是待审契约，本次没有执行：

1. **已有授权，可继续**：只从 Windows 缓存取当前 Present/历史 PnP、VID/PID、服务/驱动绑定、硬件 ID 与问题码；唯一目标 054C:0DA1；写入新本地证据目录；设备实例 ID/序列信息本地保留、对外脱敏。无 CreateFile 相机接口、无 DeviceIoControl、无卡目录枚举。
2. **若确需主动 MSC 协议证据，另行授权**：先静态审一个独立的精简入口，只对已核定的单台 FX3 打开原生 USBSTOR 接口并发事先列出的标准 SCSI 查询，限定次数/超时/数据长度；首先只准备普通 INQUIRY 的固定命令清单，未审其具体实现前不执行。不调用 PMCA info/getDevice 的整套自动发现；不跑 updater.init、镜头/GPS查询、TUR 循环、认证或模式切换。保留 USBSTOR，不为这一步装 WinUSB/libusb。
3. **服务入口是单独实验，当前不批准执行**：若以后有完整 FX3 7.02 适配证据，授权文本必须明确包括真实 USB 接口打开、普通侧 start/authenticate、预期重枚举、服务侧认证，以及成功/失败时允许的 stop 行为。只允许预先限定的一项响应，不默认 full backup preset、shell、文件读取、native probe、自动重试或自动 rescue；状态不明即停止。主机侧禁止意外认证重试，并列明无法保证设备端绝无持久状态变化。
4. **任何 native/WBI/程序写入都继续独立隔离**：不允许 libJit 上传、临时文件写删、CP/AP/backup/save、固件负载上传、WBI invalidate、boot 分区访问。先具备可复核回读和该机型离线恢复证据，才讨论是否允许。

### Gaps

即使未来一次受控服务进入和退出成功，也只证明这一正常机身当时可进入/退出，不能证明 main app 已损坏、WBI 失效、启动分区损坏或断电写坏后的可恢复性。
