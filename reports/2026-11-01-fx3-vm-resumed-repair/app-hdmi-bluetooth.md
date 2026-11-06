# 应用初始化、HDMI注册与蓝牙故障前移

2026-11-01。新增AP32–36五次原生QEMU观测，均QMP退出0、reaped、输入摘要未变。**原菜单尚未运行，无GPE绘图请求或原UI帧。** AP32无异常；后四次到达后续原蓝牙失败/断言，不能将host退出0当guest成功。

## 已闭合的局部链

原FX3 appFw的Application_System_Init（RVA16efb90）入口16字节校验，重定位两条ADRP后原样执行，实际ENTER/RETURN均观察到。AppFw随后发往909a015a的2500/0127，等待自身81cf6187。

重新核对固定提交的[上游HDMI模型](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/device-models/hdmi-device.c)，没有直接套用其其他命令。FX3原CP映像SHA c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba，与提取清单相符；659d64将0127绑定21825c，九个具体状态的vtable+98都指65ca7e。该函数将payload的观察者ID写入13个条件对象，再构造12B的2500/8127/12/1/status0。注册不改变条件值、不切换状态、不发热插拔通知。

新增显式软件注册模型，使用原OSAL分配、source、发送和释放。13字段状态、完整回复字节、重复注册、分配/发送失败回滚、错误释放与地址复用租期检查经host ASan/UBSan通过。AP33–36实际观察到observer802a0116、回复投至原81cf6187、原等待者释放0。**这是软件状态模型被原AP消费，非原CP执行或HDMI输出证明。**

## 保留的失败与GPIO修复

|候选|实际结果|
|---|---|
|AP32|原App初始化返回，随后0127等待；无绘图|
|AP33|0127消费/释放通过；原BLE错误记录器空对象解引用|
|AP34|尝试明确BLE不可用能力，原IM正确返回失败，但原appFw断言infra_wrapper_bluetooth.cpp1804；候选拒绝采用|
|AP35|恢复原加载路径，只观测原BT errorPlace；定位Core1600→Bluetooth3616/627/203→BLE2595/2655/251→nil logger418|
|AP36|恢复原ResourceBluetooth表mask，补GPIO5映射与受限寄存器；四次原写入通过，蓝牙仍因更早配置读取失败而崩溃|

AP12原故障PC对应hw_gpio_set_mode_port+60的MMIO写入，不是NULL回调。依据[Sony 7.00公开源码](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)的GPIO寄存器定义，并对照7.02原内核字节，新增f1022000 bank5的DIR/INEN/PORTSEL/WDATA数据、置位、清位backing；输入、IRQ、其他bank不实现。qtest逐组写入/置位/清位/读回通过；AP36原写34/80、24/80、48/80、04/80实际出现。7.00是参考源码，不称精确7.02构建。

GPIO独立二进制bf4d46481998b8fb…，旧timer-only路径仍恢复到f20d9448…；冻结输出和SCU独立二进制保留。

## 当前最早失败与下一步

蓝牙Core1ff60的fopen失败先于BLE崩溃。原代码给出的路径为/tmp_bt/bt_conf.cnf、/setting/bt_conf.cnf。不能把此错误继续归因GPIO，也不能通过跳过logger、断言或回成功解决。下一步查原配置生成和字段合同，结合维护者[虚拟蓝牙报告](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/report/virtual-bluetooth.md)的显式ROM HCI、原BSA、guest自有PTY方案；尚未在FX3部署HCI/BSA或配置fixture。

## 回执与边界

- [五次运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/app-hdmi-bt-run-summary.json)、[当前状态](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)。各run原始serial/QMP/receipt不可覆盖。
- [FX3注册原字节](../../work/fx3-vm-20261101/menu-repair-01/runtime/hdmi-registration-proof.json)、[应用/BT/GPIO原件审计](../../work/fx3-vm-20261101/menu-repair-01/runtime/app-bt-progress-proof.json)。audit_hdmi_registration.py、audit_app_bt_progress.py可复跑；后者BT Core块保留fopen调用。
- [注册host检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/hdmi-registration-host-check.json)、[GPIO qtest](../../work/fx3-vm-20261101/menu-repair-01/runtime/gpio-model/qtest-19b554ad/receipt.json)、[GPIO构建](../../work/fx3-vm-20261101/menu-repair-01/runtime/gpio-model/build-result.json)。

AP35/36构建metadata中继承的“v6/不可用policy”文字不准确；实际init-reviewed.sh和CPIO/SHA使用v7，未设置FX3_BLUETOOTH_POLICY，原BLE加载未拒绝。历史候选回执未改写，本说明作为纠正。原HDMI注册模型、GPIO5和当前GPE诊断均是明确软件profile；无物理设备访问，无新相机/USB/磁盘操作。原UI、按键新帧、长期运行、guest正常关机及capture仍未验。
