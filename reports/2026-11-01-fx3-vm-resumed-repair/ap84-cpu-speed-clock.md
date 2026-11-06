# AP84：原厂四核与QEMU速度/时钟对照

**三轮AP84均完成300秒健康观察，四核/原厂cpuset/icount0均未增加UI更新或菜单绘制。** UI实际更新均2、GPE均仅清屏与Flush且approx0，AppFw末次均在原ioctl→osal_wai_sem_tmo等待。后续采用四核+原厂cpuset，待OSD完成链合同；计数不能单独闭合停绘全部因果。

原厂`setting/cxd90057.dtb`（SHA c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280）明确提供4个`arm,cortex-a35`节点，reg0..3、原spin-table。原vmlinux Image SHA da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c与冻结manifest一致；未内嵌IKCFG，不能冒称提取到kernel config或把QEMU的/proc/cpuinfo当实机证据。该原内核实际启动日志显示NR_CPUS=4；当前虚拟DTB只含cpu0，所以nr_cpu_ids=1/Brought up1。硬件拓扑来自原DTB，kernel日志仅证明支持上限4。

AP84a沿用AP83b全部CPIO/helpers/原内核/模型，只把虚拟DTB同步到4个CPU节点/PSCI/cpu-map，并将GICv2的timer与PMU PPI CPU mask由01改0f，IRQ编号和level-high触发不变；FDT预留、bootargs及所有其他属性不变。QEMU仍cortex-a35/GICv2，使用`-smp 4 -accel tcg,thread=multi`，300秒。虚拟PSCI是QEMU次核启动合同，不能照搬原spin-table的零release地址。

AP84b同AP83b单核候选不变，只加`-icount shift=0,align=off,sleep=off`，300秒。新runner`run_speed_candidate84.py`增加smp/thread参数、QMP vCPU清单及既有guest `/proc/uptime`样本首次观察的宿主时间戳；不改原默认runner、guest逻辑、原厂节流或timer模型。首次观察时间受0.25秒轮询及QMP短暂停影响，不能冒称精确同步；真实uptime值来自既有cat，独立于printk时间。

官方[MTTCG说明](https://www.qemu.org/docs/master/devel/multi-thread-tcg.html)说明每vCPU各一宿主线程、icount回退单线程；[virt平台](https://www.qemu.org/docs/master/system/arm/virt.html)列出Cortex-A35与GICv2最多8核；[icount参数](https://www.qemu.org/docs/master/system/invocation.html)规定shift/align/sleep。2026-11-02联网核对，并以本机冻结QEMU11.1.2源码复核：arm/cpu.c的mttcg_supported=true、virt.c的PSCI/CPU-map与PPI掩码生成；tcg-all.c明确拒绝forced multi+icount，故不试图组合二者，也不把多核icount单线程轮转叫MTTCG。

[CPU/源码/官方来源回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap84-cpu-source-check.json)；[DTB逐属性差异与原拓扑](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap84a-four-core-mttcg/cpu-topology-and-dtb-receipt.json)。

## AP84a：ap84amttcg-953a9d56

QEMU profile={'smp': 4, 'tcg_thread': 'multi', 'icount_profile': None}；计划300秒，receipt总时长300.92秒含退出取证。健康观察=True、末次im maps=True，missing=[]；QEMU0/reaped/inputs_unchanged/两锁释放/PID不存在，observer_error=None。

|a18 peak/末值|backlog skip|UI实际更新|dequeue/timer消费|timer生产探针|时间pass/skip|mirror skip|
|---|---:|---:|---|---:|---|---:|
|12320/12319|435|2|437/405|12725|2/0|0|

原四任务屏障=True、Backup1841/1842=[4, 4]，pin提交/消费=42/42，face DMM=4/4，ICDT真实copy/原生消费=3/3；三块QMP目的hash匹配=True。GPE共2条，approx_blend=1实际条数0；所有命令/拒绝raw/读回PNG均在review。

真实/proc/uptime样本（非printk）：

|样本|uptime|累计idle|宿主首次观察elapsed|
|---|---:|---:|---:|
|1|13.88|34.05|14.481|
|2|26.34|72.49|27.481|
|3|38.86|119.76|40.011|

/sys online实际读回=[]；该轮没有该字段时，只用原kernel Brought up/SMP日志证明4核启动，不伪称读取过sysfs。关键线程采样到的last CPU=[]，全部线程last CPU=[]；没有stat时不把allowed掩码等同实际CPU使用。

AppFw末次等待：TID307、state=S (sleeping)、Cpus_allowed_list=0-3、last_cpu=None、cgroup=None。原syscall：`29 0x3 0xffffffff80000001 0x7ee5c9f870 0x2 0x7ee5ca1150 0x7ee5ca1258 0x7ee5c9f4c0 0x7f95ffbcbc`；原kernel stack：

```text
[<ffffff80080879fc>] __switch_to+0x5c/0x80
[<ffffff80004c439c>] osal_wai_sem_tmo+0x1e4/0x278 [osal_uipc]
[<ffffff80004bf4ac>] osal_unlock+0x12cc/0x22b0 [osal_uipc]
[<ffffff80004be584>] osal_unlock+0x3a4/0x22b0 [osal_uipc]
[<ffffff800839724c>] cdev_ioctl+0x4c/0xb0
[<ffffff800819e17c>] do_vfs_ioctl+0xa4/0x838
[<ffffff800819e954>] SyS_ioctl+0x44/0x80
[<ffffff8008082798>] el0_svc_naked+0x4c/0x5c
[<ffffffffffffffff>] 0xffffffffffffffff
```

AppFw停在ioctl/原生信号量等待与UI积压计数同时成立；没有据积压一个指标宣布全部停绘因果。VDF发布/等待对象的精确语义仍由独立审计闭合。

[完整回执/CPU线程与等待raw](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap84a-review.json)；[不可变receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap84amttcg-953a9d56/receipt.json)；[实际QEMU命令](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap84amttcg-953a9d56/command.json)。

## cpuset来源与AP84a-r2控制变量

原厂full-v4投影`/sbin/init2:59`在minas模式调用setup_shielding，随后setup_cpuset_CPU3定义七组：cpu0=0、cpu1=1、cpu2=2、cpu3rt=3、cpu0_1=0,1、cpu0_1_2=0-2、cpu0_1_2_3rt=0-3；full组cpus_migratable=0-2，init子进程和kthreadd移入full。原kernel Image也包含cpus_migratable接口名。harness的prepare_uipc_module_probe09.py明确为one-online-CPU探针，将七组统一设0；该单核假设是我们的接线，不是原厂策略。

AP84a保持旧harness作为仅smp对照；三份实际status却显示AppFw/SeqQueue等允许0-3，harness没有原shielding的移组步骤，因此不能仅看cpuset文件写0便断言im绑定CPU0，也不能把idle总量或允许掩码冒称AppFw实际使用四核。AP84a-r2按原厂七组/迁移掩码/父进程分组复原，不平铺所有组0-3；只另加只读online、threadstat/cgroup与组文件快照。初始原生策略写入返回0,0,0。后续实际last CPU由/proc/task/stat字段39取样，只证明采样点所在CPU，不是完整调度轨迹。

[cpuset原厂与harness来源SHA/变更回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap84a-four-core-native-cpuset-r2/cpuset-source-receipt.json)。

## AP84ar2：ap84ar2native-4b70eab2

QEMU profile={'smp': 4, 'tcg_thread': 'multi', 'icount_profile': None}；计划300秒，receipt总时长301.33秒含退出取证。健康观察=True、末次im maps=True，missing=[]；QEMU0/reaped/inputs_unchanged/两锁释放/PID不存在，observer_error=None。

|a18 peak/末值|backlog skip|UI实际更新|dequeue/timer消费|timer生产探针|时间pass/skip|mirror skip|
|---|---:|---:|---|---:|---|---:|
|12319/12318|335|2|337/306|12625|2/0|0|

原四任务屏障=True、Backup1841/1842=[4, 4]，pin提交/消费=42/42，face DMM=4/4，ICDT真实copy/原生消费=3/3；三块QMP目的hash匹配=True。GPE共2条，approx_blend=1实际条数0；所有命令/拒绝raw/读回PNG均在review。

真实/proc/uptime样本（非printk）：

|样本|uptime|累计idle|宿主首次观察elapsed|
|---|---:|---:|---:|
|1|13.9|34.71|14.309|
|2|42.34|121.86|43.702|

/sys online实际读回=['0-3', '0-3', '0-3']；该轮没有该字段时，只用原kernel Brought up/SMP日志证明4核启动，不伪称读取过sysfs。关键线程采样到的last CPU=[0, 1, 2]，全部线程last CPU=[0, 1, 2]；没有stat时不把allowed掩码等同实际CPU使用。

AppFw末次等待：TID308、state=S (sleeping)、Cpus_allowed_list=0-2、last_cpu=0、cgroup=['1:cpuset:/cpu0_1_2_3rt']。原syscall：`29 0x3 0xffffffff80000001 0x7ede123870 0x2 0x7ede125150 0x7ede125258 0x7ede1234c0 0x7f8e489cbc`；原kernel stack：

```text
[<ffffff80080879fc>] __switch_to+0x5c/0x80
[<ffffff80004c439c>] osal_wai_sem_tmo+0x1e4/0x278 [osal_uipc]
[<ffffff80004bf4ac>] osal_unlock+0x12cc/0x22b0 [osal_uipc]
[<ffffff80004be584>] osal_unlock+0x3a4/0x22b0 [osal_uipc]
[<ffffff800839724c>] cdev_ioctl+0x4c/0xb0
[<ffffff800819e17c>] do_vfs_ioctl+0xa4/0x838
[<ffffff800819e954>] SyS_ioctl+0x44/0x80
[<ffffff8008082798>] el0_svc_naked+0x4c/0x5c
[<ffffffffffffffff>] 0xffffffffffffffff
```

AppFw停在ioctl/原生信号量等待与UI积压计数同时成立；没有据积压一个指标宣布全部停绘因果。VDF发布/等待对象的精确语义仍由独立审计闭合。

[完整回执/CPU线程与等待raw](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap84ar2-review.json)；[不可变receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap84ar2native-4b70eab2/receipt.json)；[实际QEMU命令](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap84ar2native-4b70eab2/command.json)。

### QMP thread-id的Darwin局限

两轮四核QMP前/后均返回4个不同cpu-index/core-id/QOM对象，与原kernel SMP4及r2 online0-3相符。但四条thread-id均等于QEMU进程PID；冻结11.1.2 util/oslib-posix.c:97..110在Darwin的qemu_get_thread_id回退getpid，因此不能用这项去数宿主vCPU线程，也不能由其相同便推断单线程。forced `tcg,thread=multi`被成功接受，冻结ARM mttcg_supported和tcg setter/ops路径支持该配置；未额外伪称采到四个不同Mach线程ID。

## AP84b：ap84bicount0-b2028788

QEMU profile={'smp': 1, 'tcg_thread': None, 'icount_profile': 'shift=0,align=off,sleep=off'}；计划300秒，receipt总时长301.08秒含退出取证。健康观察=True、末次im maps=True，missing=[]；QEMU0/reaped/inputs_unchanged/两锁释放/PID不存在，observer_error=None。

|a18 peak/末值|backlog skip|UI实际更新|dequeue/timer消费|timer生产探针|时间pass/skip|mirror skip|
|---|---:|---:|---|---:|---|---:|
|12318/12317|532|2|535/506|12824|2/1|0|

原四任务屏障=True、Backup1841/1842=[4, 4]，pin提交/消费=42/42，face DMM=4/4，ICDT真实copy/原生消费=3/3；三块QMP目的hash匹配=True。GPE共2条，approx_blend=1实际条数0；所有命令/拒绝raw/读回PNG均在review。

真实/proc/uptime样本（非printk）：

|样本|uptime|累计idle|宿主首次观察elapsed|
|---|---:|---:|---:|
|1|12.93|9.47|10.402|
|2|23.25|17.69|17.629|
|3|33.57|27.66|20.403|

/sys online实际读回=[]；该轮没有该字段时，只用原kernel Brought up/SMP日志证明4核启动，不伪称读取过sysfs。关键线程采样到的last CPU=[]，全部线程last CPU=[]；没有stat时不把allowed掩码等同实际CPU使用。

AppFw末次等待：TID290、state=S (sleeping)、Cpus_allowed_list=0、last_cpu=None、cgroup=None。原syscall：`29 0x3 0xffffffff80000001 0x7f501b5870 0x2 0x7f501b7150 0x7f501b7258 0x7f501b54c0 0x7fa4518cbc`；原kernel stack：

```text
[<ffffff80080879fc>] __switch_to+0x5c/0x80
[<ffffff80004c439c>] osal_wai_sem_tmo+0x1e4/0x278 [osal_uipc]
[<ffffff80004bf4ac>] osal_unlock+0x12cc/0x22b0 [osal_uipc]
[<ffffff80004be584>] osal_unlock+0x3a4/0x22b0 [osal_uipc]
[<ffffff800839724c>] cdev_ioctl+0x4c/0xb0
[<ffffff800819e17c>] do_vfs_ioctl+0xa4/0x838
[<ffffff800819e954>] SyS_ioctl+0x44/0x80
[<ffffff8008082798>] el0_svc_naked+0x4c/0x5c
[<ffffffffffffffff>] 0xffffffffffffffff
```

AppFw停在ioctl/原生信号量等待与UI积压计数同时成立；没有据积压一个指标宣布全部停绘因果。VDF发布/等待对象的精确语义仍由独立审计闭合。

[完整回执/CPU线程与等待raw](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap84b-review.json)；[不可变receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap84bicount0-b2028788/receipt.json)；[实际QEMU命令](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap84bicount0-b2028788/command.json)。

## 最终对照

|模式/run|UI|a18峰/末|skip|dequeue/timer消费|timer生产探针|time pass/skip|GPE/approx|
|---|---:|---|---:|---|---:|---|---|
|默认单核 / ap83bgpe14-f83e3fc5|2|12321/12320|530|532/503|12824|2/0|2/0|
|四核/旧harness组 / ap84amttcg-953a9d56|2|12320/12319|435|437/405|12725|2/0|2/0|
|四核/原厂cpuset / ap84ar2native-4b70eab2|2|12319/12318|335|337/306|12625|2/0|2/0|
|单核/icount0 / ap84bicount0-b2028788|2|12318/12317|532|535/506|12824|2/1|2/0|

四个profile的四任务屏障、Backup4/4、pin42消费、DMM4消费、ICDT3真实复制/原生完成与目标QMP核验全部保持；各receipt QEMU0/reaped/inputs_unchanged/锁重取通过、missing空、末次im maps存活。三个AP84观察窗口均300秒，receipt多出的约1秒为退出/取证。全部仍只有同SHA黑清屏，无非均匀PNG或菜单。

原厂cpuset轮online=0-3，实际采样应用CPU0/1/2，AppFw最后有效allowed0-2且full组，符合原迁移策略；不声称采到CPU3应用负载。仅smp轮AppFw allowed0-3并非CPU0锁定；四核QMP各4个vCPU对象，Darwin reported thread-id局限见上。

真实uptime对照只覆盖启动阶段三份cat快照，icount的首样本至第三样本推进20.64秒/约10秒宿主，四核两轮约为实时推进；轮询/QMP暂停、r2日志读回及clock模式会影响比值。没有把它解释为整个300秒性能倍率，也未把printk时间代替/proc/uptime。计数显示四种配置没有解除相同AppFw原生等待；后续精确OSD发布/完成语义仍待独立审计，不调整原厂节流门槛。

[机器可读四模式对照](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap84-comparison.json)。
