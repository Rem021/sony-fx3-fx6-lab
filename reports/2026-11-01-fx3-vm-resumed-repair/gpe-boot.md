# GPE 诊断绑定与原厂 UPM 边界

本轮AP20–26新增7次实际QEMU观测。最新原appFw.so已映射，im为S(sleeping)、76–77线程，三次采样未见此前SIGSTOP；采样窗口无异常监视器。但未观察到GPE工作请求，没有原厂UI或软件绘制成功证据。

## 图形初始化适配

五个FX3原导出（InitializeDraw、Gperm::Init、FillRect、BitBlit、Flush）的原指令和重定位已核。原im实际用flags0x101惰性加载，JUMP_SLOT初值为本机libgpe PLT+8750；AP20按已解析指针检查未绑定，AP21改为同时核对符号RVA、dlsym解析和原PLT范围后绑定。FX3槽偏移29650/29520/29660/29158/29108由符号查得；没有使用上游A7C2槽常数。

五槽仍不能覆盖原线程前置私有db74：原MPGRM_GPE0在GetInstance/Main之前映射f3090000和f3400080，并写硬件寄存器，导致此前dc88的signal7。AP22按同机SHA及原16字节核对替换这一个硬件初始化入口，保留原GetInstance及之后的原Main/FIFO。运行中代码页临时可写后恢复RX，并做ARM指令缓存维护；原文件未修改。初始化0只表示诊断后端打开/dev/mem及/proc/self/mem成功。

该后端当前只准备有界捕获真实worker参数。Fill/Blit/Flush若收到请求会返回5，明确不支持，没有像素写入、原完成回调或ACK。新请求未出现前，不把“绑定成功”说成“软件光栅完成”。最新AP26对loader指针、绑定状态做原子发布并串行化bind，实际guest回归通过。

## 开机服务缺口

AP22已能加载原appFw。按固定上游[启动顺序](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py)，随后测试原开机记录和UPM/udate。AP23 helper因libbackup的UIPC依赖未显式链接而127，原门槛阻止继续；AP24修正依赖，原Backup_nread/write读回验证通过：mode2、boot_type1、原boot_type0、eecap1、bis1。修改仅guestRAM，Backup_save0；不是机身启动状态或几何真实性证明。

原UPM随后在k_upm_snd_rec_inh_msg路径访问VAfffffffff1388f54时发生真实内核异常。Sony GPL平台头确认SCU基址f1388000；该控制区不能按普通RAM假定语义。AP25/26明确暂不加载UPM，保留已验证的虚拟开机记录并加载原udate（RC0），不声称日期有效时刻已初始化，也不声称电源服务已完成。

扩展原样委派的IPC观察后，捕获到8次发往80924127的同步请求返回-1/errno1020（无接收者）；同机原UPM的k_upm_init_boot_factor在41a8重定位到osal_reg_sync_msg_queue_cb，注册常数正是80924127。另有一次819e0580无接收者，owner未闭合。成功调用遗留errno不作为失败解释。seq8192上限已饱和，不能作全启动无请求证明。

## 复核材料

- [7次运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/gpe-boot-run-summary.json)：原始serial/QMP/receipt在各run目录。全部host QMP退出0、reaped、input SHA不变；guest失败原样保留。
- [原GPE ABI和私有入口](../../work/fx3-vm-20261101/menu-repair-01/runtime/gpe-abi-proof.json)、[可复跑审计](../../work/fx3-vm-20261101/menu-repair-01/runtime/audit_gpe_abi.py)、[诊断helper源码](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-gpe-observe-v4.c)
- [UPM端点原件绑定](../../work/fx3-vm-20261101/menu-repair-01/runtime/upm-boot-endpoint-proof.json)、[真实发送回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap25-ipc-readback.json)
- [最新候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap26-gpe-atomic/candidate26.json)、[当前状态](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)

原DMM表实际显示active unit0400/type400、0401/0402/type403及各分配范围；这只是分配证据，不能代替bitmap引用、读写锁或完成前的生命周期保证。受限CPU栅格实现参考[上游gpe-raster.c](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/gpe-raster.c)；FX3相应布局和所有权仍需实请求闭合。

下一步核对SCU单寄存器语义，补齐原UPM的真实依赖，使80924127可以原生注册；再观察GPE实请求，验证布局/分配租期后实施绘制。无原UI、按键闭环、分钟稳定或guest正常关机验收。timer频率/中断到期未校准，不用内核日志的虚拟秒数冒充墙钟稳定。无真实设备、刷写或主机盘透传。
