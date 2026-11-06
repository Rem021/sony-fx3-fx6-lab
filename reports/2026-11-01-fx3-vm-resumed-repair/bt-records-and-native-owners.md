# 蓝牙空记录与原生模块启动

2026-11-01。AP37–40新增四次原生QEMU运行，均QMP退出0、reaped、输入摘要未变。最新AP40无guest异常，已越过蓝牙、BusPower、Kikilog初始化阻塞，当前等待CAPID共享表；**仍无GPE绘图请求或原UI帧**。

## 实际推进

|候选|改动|原生结果|
|---|---|---|
|AP37|显式虚拟新状态：加入0600、0B的/setting/bt_conf.cnf；其他AP36资源保留|原BluetoothCore1600错误和BLE空logger崩溃未再出现；原819e0580请求0/12返回transport0；AppFw推进到共享CP端点请求4后等待|
|AP38|只对912503d0请求4返回明确传输不可用-1021，不分配回复、不消费请求|真实8B、source811d6190；原libupdaterufp+1984错误分支释放请求并返回；应用继续，随后原BusPower包装层断言|
|AP39|恢复原FX3 libBusPower IMDB mask ffffff98→ffffff9f，其余原字节保留|原BusPower初始化执行，先前断言不再出现；应用到Imaging包装层后在Kikilog断言|
|AP40|启动原kikilog.ko并检查insmod0|原Kikilog初始化通过，Imaging/UPM/DataService/Mpr/Mwf等原包装线程建立；SeqQueueCommon发送9004015e/1000后等待|

## 配置原义与纠正

原libInfraBluetoothCore+1ff60打开配置文件；字面候选路径为/tmp_bt/bt_conf.cnf、/setting/bt_conf.cnf。原20058循环fgets，按[MAC]段和DevType = 条目解析；EOF走20214 fclose，保存条目数，置返回0。因此0B文件表示显式零设备条目，未写入虚构地址、芯片型号或版本。这不是官方包中找到的原件，而是隔离虚拟状态。原Bluetooth回调和处理函数均保留；BLE仍有738行告警，未验BSA、UART、HCI或无线功能。

**先前把912503d0统称镜头端点不准确。** 当前请求来自原libupdaterufp（IMDB11d），8B命令4；libInfraGetVersion的镜头getter是另一个20B命令0。原1928 helper只交换控制状态，当前证据不支持把命令4精确称为CP版本读回。日志标签FX3_CP_VERSION_UNAVAILABLE为旧命名，以实际8B/command4和原调用点为准，未生成CP版本或伪造成功。

上游[原请求分派](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L10437)对未建模CP更新器请求使用明确不可用策略；FX3原helper的1988非零分支→1998原free→返回已独立核对。当前v2 guard为size>=4，实际仅观察到8B；进一步复用前须新版本收紧exact8和调用者绑定，不改写已固定旧候选。

上游[BusPower说明](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L706)及其原入口启动方式作为参考。FX3自己BusPower_Init在3e78，调用原GetInstance/PreInit/SetAvailableBusPowerPort后创建线程；这里恢复原IMDB启动条件，而非伪造回包。原库无/dev/字面量不等于所有间接调用均无设备；本轮未新增USB控制器或主机设备访问。Kikilog前置加载也来自[原成功入口](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1249)。

## 复核与后续

- [四次原始运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/bt-records-native-owners-summary.json)、[当前状态](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)。所有run的serial、printk、QMP和receipt保留，无强杀遗留QEMU。
- [原蓝牙配置解析](../../work/fx3-vm-20261101/menu-repair-01/runtime/bt-record-config-proof.json)、[原CP控制请求与BusPower](../../work/fx3-vm-20261101/menu-repair-01/runtime/cp-version-buspower-proof.json)：同机ELF摘要、原字节、命名PLT与实际caller基址绑定。
- [最新候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap40-kikilog/candidate40.json)：原件保留；simulation内库/新状态和原始资产的区别在构建脚本中明确。AP38沿用guest路径fx3-hdmi-registration-v1.so但装入SHA绑定v2二进制，以CPIO与build receipt为准。

当前原SeqQueueCommon发往9004015e的24B请求为command0/operation1000，随后等待803061c0。维护者CAPID服务使用有状态共享表和专用虚拟保留区，下一步必须从FX3原消费代码核表布局、初始化/所有权/完成与回滚，并选择排除所有现有owner的内存，不直接抄A7C2的4102e0000。尚未实现该服务，无原CP执行、镜头/CMOS/capture或菜单稳定性验收。

本轮未执行下载的start-bt-virtual.sh或virtual-hci.c；上游源码只作参考。最初urllib获取启动脚本遇TLS EOF，curl严格TLS重试成功，均记入收据。
