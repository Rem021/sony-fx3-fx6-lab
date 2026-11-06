# HDMI配置、远端DMM和显示查询继续修复

2026-11-01（本地日期）。AP46–50新增五次原生QEMU运行，均host退出0、reaped、输入SHA未变、全部候选要求的marker出现、未见guest异常标记。**原应用已越过音频格式、照片预设、两次远端DMM分配及显示信息查询；当前等待014c布局配置等请求。原厂UI仍未运行，五次GPE绘图请求均为0。**

## 本轮实际结果

|候选|新增内容|实际原应用行为|
|---|---|---|
|AP46|032d未连接输出的音频格式状态|消费132d/580000回复，原release返回0，继续发HDMI0102|
|AP47|0102未连接输出的照片预设|请求值1真实保存到raw/preset6，消费8102回复并释放0，继续远端DMM|
|AP48|被动观察9061003c，原样委派|读到40B op20/unit63a/option1，未添加分配回复|
|AP49|两槽虚拟DMM存储，每槽512KiB|原应用接收8400/8401句柄、CP域地址1d900000/1d980000和80000长度，原两份回复均释放0|
|AP50|016a软件显示几何查询|原应用接收并释放18B116a回复0，随后请求014c布局，含640×480|

原Application_System_Init仅有进入记录，尚无返回；不能将越过上述等待等同于完整应用启动。全部运行保留在[逐次摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/audio-display-dmm-run-summary.json)，摘要含serial行号、原消息释放、原始请求和RAM摘要；每个目录有原serial、printk、QMP、receipt及运行器源码。

## FX3自身字节与明确软件模型

原CP文件cpapp-b.bin SHA c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba，以Thumb、VA=file+108000读取；未运行原CP。

032d对应的内部c1分派到1b2494，构造旧式2004/0304/12B音频格式报文；161004接收，5981c6将四字节写入singleton+8，5981ee读取同字段，接受值0/1。原通知原因3、旧回复8304与音频域580000合成，以及5ca3b2构造132d，分别保留在[原指令证明](../../work/fx3-vm-20261101/menu-repair-01/runtime/fx3-audio-format-proof.json)。当前模型只保存未连接输出的音频格式和通知原因，不生产音频、不报告输出就绪。

HDMI0102注册指向21799d，原wrapper经659fc2调用状态vtable+4c；九个原状态vtable该槽均为65b765。65b764保存raw byte到singleton+97，通过65b0be/656c5a/213a48，将selector6的desired值写profile+60，再构造8102/status0，返回无状态切换。原实现将>=3的desired钳到0；本模型只支持0..2、其余显式拒绝。完整活动输出重算未实现。[原HDMI证明](../../work/fx3-vm-20261101/menu-repair-01/runtime/fx3-hdmi-photo-proof.json)

FX3原appFw+2e4f0e4发40B远端分配；原等待后读回复status+2、handle+c、address+18和size+20，并调用原free。下一组API在2e4f2b8检查句柄bit15以选择61003c/9061003c。原dmm.ko的MakeHandle使用10bit索引、5bit代际并为本地清bit15。[同机协议证明](../../work/fx3-vm-20261101/menu-repair-01/runtime/fx3-dmm-protocol-proof.json)

远端DMM复用维护者固定提交的[有限存储模型](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/dmm-service.c)，支持unit63a的两槽、分配/打开/关闭/释放/段查询与代际。**它是独立虚拟存储，不冒充原CP内存管理器。** 未沿用A7C2物理地址，且删除其私有creator栈偏移判定，creator始终unknown；FX3原CP单元几何和CP代际实现尚未复核。派生差异与来源摘要见[源码收据](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-dmm-source-derivation.json)。

独立选41d900000/1MiB，检查全部原memrsv、现有FDT和CAPID保留区无重叠，写入FDT reservation及原内核memrsv参数；guest懒初始化采用O_EXCL/NOFOLLOW、0600的独占claim和PID校验，/dev/mem写读探针通过。AP49/50停止时QMP独立读回1MiB全零，SHA30e14955ebf1352266dc2ff8067e68104607e750abb9d3b36582b8af909fcb58；它证明有实际内存、当前没有生产载荷，不证明PCM/capture或原CP工作。[保留区审计](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap49-remote-dmm-r2/exclusive-reservation.json)

016a的18B回复格式来自FX3原1b087c：200d/116a/18/8001，四个u16尺寸与两个aspect枚举；[同机原指令](../../work/fx3-vm-20261101/menu-repair-01/runtime/fx3-display-info-proof.json)。640×480/aspect1是显式软件画布配置，参考维护者[显示协议实现](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/hdmi-format-service.c)，不声称物理LCD/EVF验证。

## 所有权、验证及保留失败

新增模型均使用原消息allocate/set_source/send/free；发送成功后才释放原请求，原接收方通过租约校验调用原free。分配或发送失败释放自身回复、回滚逻辑状态并保留原请求；有PID与重复消息地址防护，不在入队后读取回复或释放后读取请求。host ASan/UBSan检查涵盖音频/预设/显示状态回滚、非法格式、DMM存储、旧句柄、开关/释放、容量耗尽、分配/发送失败和PID归属；native回复消费与host检查分别记录。

- [音频检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/capid-audio-transport-host-check.json)、[预设检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/capid-photo-host-check.json)、[DMM最终检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/dmm-transport-host-check-v2.json)、[显示检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/display-transport-host-check.json)。
- DMM最初host夹具把access_owner=1、initialized=0，首断言失败，crossbuild及candidate均未生成。误发出的候选准备随后因helper不存在停止，没有新VM。失败收据与空目录保留；修正为具名initialized=1后全测通过，重试在ap49-remote-dmm-r2，不覆盖原记录。
- 一次按错误文件名display-info-service.c联网得到404；实际函数已在此前核验的hdmi-format-service.c中。[失败与解析收据](../../work/fx3-vm-20261101/menu-repair-01/runtime/display-info-source-lookup.json)保留。
- AP46旧被动日志original_delegated=1只表示进入观测点，对随后由模型处理的032d不准确；AP47起改为dispatch_pending=1。旧日志未改写。AP46–49的scope含继承历史文字，AP50已重写为实际完整模型集合；以[每份CPIO实际helper字节](../../work/fx3-vm-20261101/menu-repair-01/runtime/audio-display-dmm-helper-provenance.json)为准，guest旧别名fx3-capid-v1.so实际依次为v6..v10。

## 当前未闭合

AP50原请求还包括118/22B、13d/10B、159/10B；最后明确等待014c/40B，原字节为0d204c012800018007010100000000008002e0010000000000000000000000000300000000000000。已从FX3内部请求表找到14c对应内部98→1b4a50，转旧式2001/0305；完成分派1ac6de→5c9aaa构造114c。13d对应内部8b→5cb9ca，转旧式2001/010d，完成5c9962构造113d。**旧VDF消费者如何保存配置、完成状态与后续像素所有权仍待闭合，尚未添加这两条成功回复。**

后续应继续追这两个旧式消费者，保留状态、验证完成时序，再接GPE真实布局/资源界限、Sony LZ77、bitmap读写锁/寿命和像素输出。当前没有GPE绘图、原UI、键到新帧、长期运行、guest正常关机、真实蓝牙/CMOS/capture验收。全部新内存只在隔离guest；无相机、USB、NIC或主机磁盘透传。冻结runtime和原固件保留，五个QEMU均已回收。
