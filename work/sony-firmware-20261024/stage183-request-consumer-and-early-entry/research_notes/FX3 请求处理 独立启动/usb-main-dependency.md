# FX3 7.02 USB 服务与 MAIN 装载依赖

## 普通 USB/NIN 请求是否属于独立于 appFw 的进程？

### Takeaway

正常 NIN 启动器属于 `im.elf` 动态装入的 `libObj.so`，`appFw.so` 也由同一个 `im.elf` 装载器 `dlopen/dlsym`；`THREAD_INFRA*`、`THREAD_APP` 是线程创建调用，不能按名称解释成相互隔离的进程。因此这条普通路径不能作为 im/appFw 进程已经终止后的独立救援入口。[原装载表与15段原代码哈希](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)

### Cited Findings

- 资料为官方 FX3 7.02 包的原 AP 分区，SHA-256 `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5`；不是当前机身读回。原 `im.elf` 为 `5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91`；`libIMDB.so` 为 `6ceaea432bc7c4645897c2f1272941b33b0c04115ec62ffa000b37faf3d8517d`。[本轮原件登记](../../evidence/usb-main-dependency/ap-topology.json)
- `libIMDB` 的 `IMDB_get_entries` `0x9b1c` 返回 `imdb_raw+0x100`，`IMDB_find_entry` `0x9ab0` 按 `0x48` 字节步进，读 `+0xc` 的模块号与 `+8` 的 target。初始探索尝试的88字节步长已被这份原代码否定；本轮正式表统一使用72字节，没有据字符串位置猜进程。[原 get/find 指令](../../evidence/usb-main-dependency/disassembly/libIMDB.so.txt)、[72字节原表](../../evidence/usb-main-dependency/imdb-table-raw.json)
- 表 VA `0x1dae0` 是 `libsensapi.so / senser_init / senser_sus / senser_res`，type=`0x20000002`、me=`0x3d`、`+0xe`=`0x7fb`。`im.elf` `0x40625c..0x406270` 为 type `0x20000001..3` 选择 `0x405f5c`；后者在 `0x405f78` 读取 `+0xe`，非零时于 `0x405f90/94` 选择 `/usr/lib/libObj.so`，`0x405f9c` 调 `dlopen`，`0x406004` 调 `dlsym`，`0x40602c` 调取到的入口。原 AP 中没有独立的 `/lib/libsensapi.so` 普通文件/符号链接；这里有明确的 loader alias 行为。[表与代码范围SHA](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)、[原 im 指令](../../evidence/usb-main-dependency/disassembly/im.elf.txt)
- 表 VA `0x1f670` 是 `appFw.so / Application_System_Init`，type=`0x20000004`、me=`0x83`、`+0xe`=`0`。同一 `im.elf` 的 `0x406274..0x406288` 选择 `0x405e24`；`0x405eac` 调 `dlopen(appFw.so)`，`0x405f0c` 调 `dlsym(Application_System_Init)`，`0x405f44` 调初始化函数。该分支没有 `fork/exec`。[原装载表和范围SHA](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)、[原 im 指令](../../evidence/usb-main-dependency/disassembly/im.elf.txt)
- `im.elf` 的 `0x403bcc/0x403be8/0x403c04/0x403c20` 分别带 `THREAD_APP/THREAD_INFRA0/1/2` 名字与入口，全部进 `0x403b90`，最终 `0x403bc0` 调 `osal_create_waitable_thread`。这是共同用户态装载器中的线程，不是按库创建的独立 ELF 进程。[原线程创建指令](../../evidence/usb-main-dependency/disassembly/im.elf.txt)
- 先前精确原件分析已接通：`libObj.so` `senser_init` 非 mode1 分支 → `senif_init` 注册回调 → 事件1且对象状态≤1 → 动态打开 `libsencore.so` → `dlsym(NinThread)` → `pthread_create`。原 `libObj` SHA 为 `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae`，原 `libsencore` 为 `a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410`。协作者实型为 `Senser::SenUsbIf`，不是服务模式的 `WorkerThreadManager`；不能混用虚表。[原动态入口](../../../stage148-initial-MSC-handler-inventory/dynamic-NIN-route-review.json)、[原协作者对象](../../../stage149-normal-cooperator-and-NIN-checkpoint/normal-cooperator-static.json)、[本轮引用文件SHA](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)
- 既有原 `usbg_sen.ko` setup handler 匹配START/STOP控制头后投递 common event7/subtype4 的命令0/1；用户态 `CUsbGadgetSen::proc_kevent` `0x18be8` 才取对象 `+0xf0/+0xf8` 回调。该范围未见内核 `call_usermodehelper/exec` 或独立进程装载行为，不能把“内核收到了包”升级为“MAIN死后会启动服务”。[精确原内核与消费者证据](../../../stage138-USB-stop-dispatch-and-Mac-ownership/vendor-dispatch-review.json)、[本轮消费者片段](../../evidence/usb-main-dependency/disassembly/libInfraUsbCmn.so-18be8.txt)

### Inferences

- 若 appFw 中故障导致整个 `im.elf` 进程被终止，其同地址空间的 libObj 普通NIN回调/线程也不能继续；仅内核存活并不足以保住这条普通用户态路径。这是由共同装载器拓扑得出的进程故障推论，不是实际故障测试。[装载拓扑](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)
- appFw文件损坏导致的 `dlopen` 失败，与运行中进程致命崩溃不同；本轮不能推导前一种错误必然杀掉所有infra，也不能推导剩余infra必然正常接USB。[原错误返回分支](../../evidence/usb-main-dependency/disassembly/im.elf.txt)

### Gaps

- 尚未证明真实USB在MAIN损坏后选择、登记、恢复了哪些存活对象；现有离线证据没有这个运行状态。
- `av-cam.bin`/LIRO 域的故障与 appFw 用户进程故障必须分开。该域的queue消费者由另一研究线程处理，本笔记不把它称为独立用户进程、CP或可被NIN直接替代的服务。

## 是否确实存在独立启动的 sen.elf？启动与寿命边界是什么？

### Takeaway

存在真正独立的 `sen.elf` ELF和在 `init2` 中早于 `bootin.elf` 的条件后台启动，且服务自建USB对象和自己的事件循环。这是本轮新增、可以继续证明的恢复候选；它要求预先存在可读的 `smode=UU`，并没有说明普通USB请求能在MAIN死后补建该标志，也没有证明整体看护系统不会重启它。[完整init2](../../evidence/usb-main-dependency/originals/sbin/init2)、[独立启动图](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)

### Cited Findings

- 当前7.02 root分区 SHA为 `ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7`。其fstab把p2挂到`/setting`，p15挂到`/usr`，`init2`先挂载文件系统、读取`/setting/mode/dmode`（默认3），只在MODE非0时继续driver/用户程序路径。[p7原件与闭包来源](../../evidence/usb-main-dependency/static-dependency-closure.json)、[原fstab](../../evidence/usb-main-dependency/originals/sbin/initrc/fstab)、[原init2](../../evidence/usb-main-dependency/originals/sbin/init2)
- 精确顺序为：`echo set >/proc/udm/drivers` → shielding → source `insmod_drv2` → `setup_bis || setup_senser` → `/usr/bin/bootin.elf &`。`setup_bis`只有bootmode=BIS才返回0，因而BIS成功会跳过`setup_senser`。后者先要求smode可读，再只在读出的字符串恰为`UU`时执行`/usr/bin/sen.elf &`。**UU不会跳过bootin/im/appFw**；两条后台启动都会被尝试。[完整原init2](../../evidence/usb-main-dependency/originals/sbin/init2)
- 该 `insmod_drv2` 原文在sen之前装入 `osal_utm/osal_uipc/backup`、`usb_portMonitor/usbg_sen/usb_extcmd/upm` 等模块；该脚本中没有 `liro.ko` 行。此事实只说明脚本显式顺序，不证明更早或后续没有装LIRO，也不证明所有insmod都成功。[完整原driver脚本](../../evidence/usb-main-dependency/originals/sbin/initrc/insmod_drv2)
- `init2` 在后台启动后进入 `ash --login` 的永久循环，没有在脚本中对sen/bootin作`wait`、退出状态判断、`trap`或失败联动`kill`。这只排除了这份shell文本中的直接联动，未排除内核、UPM、watchdog、其他服务的整体重启。[完整原init2](../../evidence/usb-main-dependency/originals/sbin/init2)
- 原 `/usr/bin/sen.elf` SHA为 `9e3236666176b69746848edaac31e1e0ef00c4e80a9f062794ff62be2d605470`。main的原FDE `0x401cb0` 236字节；`0x401d78`读模式（`0x402a60`优先`/setting/sen/smode`，否则`/boot/sen/smode`），`0x401d7c`进入`0x401f80`，再于`0x401d88`进入它自己的`0x402e58`事件循环。[原件SHA](../../evidence/usb-main-dependency/ap-topology.json)、[原sen指令与FDE范围](../../evidence/usb-main-dependency/disassembly/sen.elf.txt)
- `sen.elf+0x401f80`自己注册同步电源消息queue `0x003d032e` 回调；模式非零时经 `0x402b84`打开`libsencore.so`并查找`senser_usb_mode_start`。失败分支会 `abort`，并非无限保证存活。主事件循环 `0x402e58` 在handler为空时sleep，否则用自己的handler集合 `poll(...,-1)` 分派；它不等待im的进程退出。[原sen startup/dispatcher](../../evidence/usb-main-dependency/disassembly/sen.elf.txt)
- 原 `senser_usb_mode_start` `libsencore+0xb094` → `SenserIfStart+0xceb0`，后者 `Usb::open_channel`、登记自己的handler，再到 `Usb::initialize_usb_interface+0xcaec`。初始化调用 `senif_init`、`usbif_initialize`，并调用新USB API表的槽0。[原服务入口与SHA](../../evidence/usb-main-dependency/service-start-slices.json)、[SenserIfStart](../../evidence/usb-main-dependency/disassembly/libsencore.so-ceb0.txt)、[USB初始化](../../evidence/usb-main-dependency/disassembly/libsencore.so-caec.txt)
- `usbif_initialize` 在 `libInfraUsbCmn+0x17da4` 自己 `new CUsbSvc`、填API表、调用 `CUsbSvc::init`、注册service；`CUsbSvc::init+0x13cd8`调用 `usb_event_start+0x16730`。后者直接open原字符串`/dev/usb/event`，设置fd并建立本进程pthread；并非把所有工作交给appFw线程。[原self-init](../../evidence/usb-main-dependency/disassembly/libInfraUsbCmn.so-17da4.txt)、[原CUsbSvc::init](../../evidence/usb-main-dependency/disassembly/libInfraUsbCmn.so-13cd8.txt)、[原事件线程](../../evidence/usb-main-dependency/disassembly/libInfraUsbCmn.so-16730.txt)、[字符串及库SHA](../../evidence/usb-main-dependency/ap-topology.json)
- 按原p7+p15文件与原symlink数据解析 `sen.elf + libsencore` 的全部静态 `DT_NEEDED`，闭包18个文件、0个未解析项；其中没有appFw、libObj，其成员也没有这两个basename字面量。该结果限定为ELF静态装载闭包，明确不覆盖后续动态插件、命令、内核设备、IPC与实际驱动状态。[完整闭包、原件SHA及每条依赖](../../evidence/usb-main-dependency/static-dependency-closure.json)
- `im.elf` 本身另有处理 `0x00920152` 消息后准备`/usr/bin/sen.elf &`的分支（`0x4048f4`起），但它还先向queue `0x80924127`发送同步消息并检查返回字段。这个晚启动器仍在im中；没有证据可用它救活已经死亡的im。[原im分支](../../evidence/usb-main-dependency/disassembly/im.elf.txt)、[范围SHA](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)

### Inferences

- 此候选的“独立”目前准确含义是：独立ELF、独立init2后台启动、独立用户态USB对象/事件循环、静态动态库闭包不含appFw/libObj。它不是“已证明所有命令不依赖MAIN/av-cam”，也不是已经可用的恢复方案。[边界图](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)
- 若仅appFw导致im致命退出，而sen此前已按UU条件正常启动、其驱动/UPM与系统寿命仍保持，这个独立进程有继续研究价值。但这些条件尚未在损坏态满足或验证，不把它写成保证存活。[原启动顺序及局部生命周期](../../evidence/usb-main-dependency/originals/sbin/init2)、[原sen事件循环](../../evidence/usb-main-dependency/disassembly/sen.elf.txt)

### Gaps

- 未证明av-cam/LIRO损坏后 `/dev/usb/event`、port/gadgetcore、backup/UPM/OSAL与服务完成回调仍可用。静态依赖闭包没有av-cam文件，不能排除这些内核或IPC依赖。
- 尚未完整恢复sen独立模式的WorkerThreadManager/Cooperator初始化及其实际命令表。独立启动/事件循环**不等于**鉴权后可读写目标文件、可设置updater标志、可恢复appFw/av-cam。
- 未证明整体系统看护不会因im/appFw/av-cam故障而复位；未证明sen退出、清标志、普通USB恢复与冷启动归还。

## 下一项最小独立性证明是什么？

### Takeaway

下一切口应收敛到独立 `senser_usb_mode_start` 的实际Worker/Cooperator与命令表，以及它对UPM/LIRO的具体请求；不要再从“有SENSER名字/可枚举/内核还能收包”直接跳到“可救砖”。本轮没有写smode或updater marker，也没有新增相机、USB、Windows、UU、载荷或guest执行。[本轮图与范围](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)、[51项证据清单](../../evidence/usb-main-dependency/manifest.json)

### Cited Findings

- 最小可复用源锚点：`sen.elf+0x401f80`（独立服务入口），`libsencore+0xb094`（usb mode启动），`+0xceb0`（handler/USB自建），`+0xcc1c`（输入事件分派，调用WorkerThreadManager start_authentication/run_workers/join），以及其`Usb::initialize_usb_interface+0xcaec`保存的接口/回调绑定。本轮保存对应原文件、选定函数与代码哈希，后续无需运行Sony程序即可继续静态追踪。[原选定函数清单](../../evidence/usb-main-dependency/independent-service-slices.json)、[原input dispatcher](../../evidence/usb-main-dependency/disassembly/libsencore.so-cc1c.txt)、[原启动图](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)
- 已有普通协作者只证明 `Senser::SenUsbIf` 的对象/虚表与特定NIN行为，不能自动转用到独立sen模式。后续应从独立模式原构造器证明实际Cooperator，再证明目标命令表的发布与下游IPC，才能评价appFw/av-cam坏时能否设置恢复请求或读写文件。[原普通协作者边界](../../../stage149-normal-cooperator-and-NIN-checkpoint/normal-cooperator-static.json)、[独立模式当前缺口](../../evidence/usb-main-dependency/process-registration-dependency-graph.json)

### Inferences

- 恢复优先的最小实验前置研究是“独立sen模式实际命令能否在目标故障域外完成”，而不是先做修改包。对smode原值/存在性、同机备份、冷启动、归还的任何后续验证都需要独立方案与明确设备授权；本轮没有执行或放行标志写入。

### Gaps

- 未证明MAIN死后普通USB能写入p2 `\\updater\\mode`、创建smode或触发早启选择。早启选择器本身由其他研究线程取证，本笔记不把其存在当作USB生产者独立性。
- 本轮没有互联网新断言或宽泛机型恢复教程；全部结论来自本地已取得官方7.02原件和固定SHA的既有静态证据，不借用FX3A、A7 IV、A7C II的成功案例。
