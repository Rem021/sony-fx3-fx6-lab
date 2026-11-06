# AP83 / AP84a：多核对照与首清屏后的真实等待

**AP84a已启动4核，AppFw实际允许CPU0–3，但仍只进入UI更新2次，随后与AP83一样等待OSAL信号量。积压保护确实执行过；现有证据不足以将持续黑屏唯一归因于TCG单核过慢。** 下一项最小取证是UI更新的返回点、信号量ID/timeout及同线程用户栈，供运行链决定后续动作。这里没有运行QEMU或改变guest行为。[原门控`appFw+16f2478..2488`、更新调用`16f2640`；AP84a serial120、23689/23715、29796/43102；详细逐值证据见[proof](ap83-clock-gate-proof.json)。]

范围：只读原AP、7.02设备树、QEMU11.1.2本地源码及三轮**已结束**的不可变运行产物；只写本目录。未访问运行中guest，未执行run/prepare/review程序，未改runtime/STATE/原件或取得运行锁。以下serial行号按原文件LF分行，保留CR/NUL；VA为ELF image VA。A=直接原码/保存运行证据，B=受约束推断，U=未证实。

## 1. 对照基线与不能混合的时钟选项

**A：原FX3 7.02 setting设备树有四个`arm,cortex-a35`CPU，reg=0/1/2/3；原enable-method是spin-table，release-addr均0。** 脚本直接解析DTB结构与字符串表，proof保存每个属性的token/data文件偏移。固定原件SHA256=`c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280`。这证明原设备树描述的数量，不证明四个虚拟CPU的硬件性能等价。[原DTB `/cpus/cpu@0..3`；GPL参考`stage205-…/reference-source/linux-kernel/arch/arm64/boot/dts/cxd/cxd90057.dtsi:87–125`。]

**A：AP83a-r4/AP83b的归档command均为`-smp 1 -accel tcg`，无icount；各候选DTB只有cpu@0。** 原kernel报告`NR_CPUS=4 → nr_cpu_ids=1`及`Brought up 1 CPUs`，AppFw三份实际`Cpus_allowed_list`都是0。[AP83a serial75/116、14124–14181/33157–33217/46347–46407；AP83b75/116、14131–14188/33007–33066/46196–46255；proof中DTB/command哈希和属性偏移。]

**A：两轮CPIO `/init:17` 都将七组cpuset.cpus写0。U：仅据这些文件，不能推断换成多核后任务仍被限制在CPU0。** AP84a保持**同一CPIO SHA256**，但实际AppFw允许0–3；本轮直接读出的事实优先于对脚本文本的推断。因此多核对照必须同时核对DTB/CPU启动、任务实际亲和性和cgroup归属，不将“组文件为0”当作线程已经迁入该组的证明。[CPIO `/init:9–26`；AP84a serial13575、29791、43097；两轮候选initrd SHA均`1dbc6883ad1fff354ada9272cc9d7439a78c229030d37baaf50bf350701b0ec5`。]

**A：MTTCG与icount应拆成两组对照。** 本地QEMU11.1.2 `accel/tcg/tcg-all.c:127–132`在icount开启时不自动选multi，`:197–198`明确拒绝显式multi+icount。官方[MTTCG文档](https://www.qemu.org/docs/master/devel/multi-thread-tcg.html)与[icount文档](https://www.qemu.org/docs/master/devel/tcg-icount.html)亦确认二者不兼容；icount按指令推导虚拟时间，不是硬件周期精确模拟。本轮2026-11-02核对的在线master文档显示11.1.50，具体适用性以固定的本地11.1.2源码为准。

**A：现Sony timer模型使用同一个`QEMU_CLOCK_VIRTUAL`。** `sony_hwtimer.c:28`给出`period_ns=250 << (control&7)`；`:36/44/55/135`分别从虚拟时钟计数、排期、更新epoch和建立timer。因此icount会改变其时间来源，不能将icount结果称作“仅提高主机算力”。模型与FX3实际硬件频率/分频的逐位等价仍U。[QEMU本地源码SHA和原行均在proof.Sony_timer。]

| 对照 | CPU/TCG | 时间模型 | 本审计状态 |
|---|---|---|---|
| AP83b基线 | 1 / 默认TCG | 无icount | 保存回执已复核 |
| AP84a并发 | 4 / thread=multi | 无icount | 保存回执已复核；持续等待未解除 |
| 指令时钟 | 1 / thread=single | shift=0,align=off,sleep=off | 本脚本未运行，效果U |

四核虚拟拓扑应使用已有virt PSCI方法、匹配CPU节点/cpu-map和GIC PPI掩码；不直接照抄原机spin-table release-addr0。运行链另准备的原生cpuset恢复r2不在本脚本三轮冻结输入中，不能据准备文件验收运行结果。[AP84a候选DTB各CPU enable-method=`psci`，实际启动serial120；proof.original_CPU_DTB与runs中DTB属性；运行链`prepare_speed84.py:4–16`、`prepare_speed84_r2.py:8–35`仅作下一轮范围说明。]

## 2. 三轮RAM直接解码：UI入口均两次

本脚本从各轮已保存64KiB `ui-gate-counters.bin`独立解码头部与活动统计bank，**没有抄review的计数**。header magic=`3145544147335846`、version2，bank从header+16读取，统计始于文件`100 + bank*1000`；前64个u64为各探针count，再接32个u64统计字段。部署CPIO成员`simulation/fx3-ui-gate-v1.so`实际绑定v11 SHA=`54eeed923a6412cd2c6743f6e8c968d1ede71b92aa79aca4575868ebccc4a9ec`，其60处原指令均逐条核对。[`helpers/fx3-ui-gate-v11.c:6/12/105–106`；proof记录RAM文件SHA、receipt同名物理快照SHA及60条原字节。]

| 冻结run | CPU | 入更新id8 | dequeues / timer消费 | timer生产id9 | backlog_skip | gate峰值 / 全采样峰值 | 最后a18 |
|---|---:|---:|---:|---:|---:|---:|---:|
| AP83a-r4 `ap83ar4face-4cd8574a` | 1 | 2 | 561 / 532 | 12853 | 559 | 370 / 12321 | 12320 |
| AP83b `ap83bgpe14-f83e3fc5` | 1 | 2 | 532 / 503 | 12824 | 530 | 360 / 12321 | 12320 |
| AP84a `ap84amttcg-953a9d56` | 4 | 2 | 437 / 405 | 12725 | 435 | 328 / 12320 | 12319 |

三轮system_false/time_skip/a12_nonzero/a13_nonzero/mirror_skip均0，time_pass=2，observer selftest/bound均1；`count5 = backlog_skip + time_pass`逐轮成立。**这些是探针统计，不是队列不变量**：生产与消费在不同线程，取值发生于原加减存储之前，最后a18也不是保证同时取到的“生产数减消费数”。gate峰值与全采样峰值不同，不能将末次12320写成末次门控读取过12320。[`appFw+16f2478/247c/2488`与`16f1a74/16f1d68`；observer v11 `fx3_gate_event`；proof.counter_RAM逐值。]

id8位于`16f2640 bl 16f1998`之前，只证明进入两次更新，**不证明第二次返回**。原`16f1998`先updateCurrentTime/processEvent，再经ResourceManager/WidgetSystem，最后`16f1a1c`调用GraphicsEngine::drawFramebuffer。因此“只更新两次”不能进一步直接命名成其中哪一API卡住。[proof.AP_blocks `16f1998..16f1a44`，两次入口见下表。]

| run | 两次更新入口 | 唯二GPE命令 | 后续timer仍生产 |
|---|---|---|---|
| AP83a-r4 | serial27083/27261 | FillRect27253、Flush27296 | producer n12000行64791 |
| AP83b | 27068/27108 | FillRect27096、Flush27138 | producer n12000行64663 |
| AP84a | 23689/23715 | FillRect23702、Flush23703 | proof保存全部稀疏producer样本 |

三轮receipt均观察≥300秒，qemu_exit0/reaped/inputs_unchanged、guest_exception_markers空、menu_verified=false。三份首绘raw均1228800B全零，SHA=`3630e065eb7b4540fbab11dbfd2619e8500f211b9c404380a1867fdc44b77c0c`。这些关闭健康清屏回归，不关闭菜单/文字、输入循环或硬件显示验收。[proof.runs.receipt与first_draw_surface；GPE原命令serial如表。]

## 3. 清屏后不是一直执行门控：后续已睡在信号量

**A：三轮首份AppFw快照仍为boot事件futex等待，第二/三份均改为相同的OSAL信号量等待。** 不能继续把后两份快照归给已完成的boot condition variable。后两份原syscall逐字一致，kernel栈含`osal_wai_sem_tmo+1e4/278 [osal_uipc]`；各轮SP/arg/PC随ASLR变化，不能跨轮硬套地址。[各轮serial如下；boot事件机制见本目录[BOOT-TAIL](BOOT-TAIL.md)。]

| run / AppFw TID | 首份futex syscall行 | 后两份ioctl syscall行 | 后两份arg pointer / SP |
|---|---|---|---|
| AP83a-r4 / 289 | 14173 | 33207 / 46396 | `7f551ad870 / 7f551ad4c0` |
| AP83b / 289 | 14180 | 33056 / 46245 | `7f2b148870 / 7f2b1484c0` |
| AP84a / 307 | 13580 | 29796 / 43102 | `7ee5c9f870 / 7ee5c9f4c0` |

后两份均syscall29（ioctl）、fd3、request=`ffffffff80000001`；原`libosal_uipc+37b0 u_osal_wai_sem_tmo`把**实际semID(u32)**存到FP+20，把timeout(u64)存到FP+28，并于`37e0`传入原ioctl。参数布局精确为16B：`+0 semID LE32 / +4 padding4 / +8 timeout LE64`；padding不能用作业务值。本轮syscall只保存该块的指针，**没有该16B内容或完整用户栈，semID/timeout/上层等待调用者仍U**。[原指令37c8/37d0/37d8/37dc/37e0；proof.OSAL_sem_wrapper保存原字节。]

**A：现有ioctl日志也不能补出尚未返回的这次参数。** `ioctl-trace-v11.c:192`先调用原ioctl，`:197–206`之后才打印FX3_IOCTL_PASS/FX3_UIPC_PASS；提前的recv_begin只覆盖command7，不覆盖本次command1。故“末尾没有该日志”不能作为信号量请求未发生的证据。[proof.pending_ioctl_observer_limit保存精确源码行；原syscall与内核栈如表。]

**B：单核性能/积压可能贡献此前的skip，但“四核已启动且AppFw允许0–3”仍重现相同后续等待，使它不足以独自解释持续黑屏。** 三轮均已将a18降到2而实际进入更新两次，然后进入等待；后续timer继续生产能造成新积压。不能倒置因果，将等待之后的积压直接认作等待之前唯一根因。当前还不能区分绘制完成、资源、消息队列或其他信号量路径，更不能补发1004或替它signal。[原分支16f2480、原更新调用16f2640；三轮入口、producer和后续syscall证据如上。]

另有可测混淆：大量被动观察会消耗模拟执行/串口时间。其性能贡献本轮未测，不能将observer影响认定为根因，也不能删除原timer消息来降低计数。若运行链做观察成本对照，应保持原请求、消息、门槛与状态，只改变观测采样频率并保留入口/返回与计数收据。[v11每命中mirror、首50/每1000次打印的源码；本条是U级实验建议。]

## 4. 下一轮最小观测合同

仅供持有运行链的协调者加入**被动**取证；本worker未部署/执行。每条需记录TID、当轮模块基址、单调序号和同线程进入/返回对应，限制为目标AppFw，避免将其他线程的等待嫁接过来。

| VA | 最小字段/字节 | 解决的问题 |
|---|---|---|
| appFw+`16f2640` / **`16f2644`** | x0对象、x20、TID、a18/a12；入口/返回各一条 | 第二次16f1998是否返回 |
| appFw+`16f1a1c` / `16f1a20` | TID、调用前x0；调用后w0仅作原始值 | drawFramebuffer是否返回 |
| appFw+`16f22c8` / `16f22cc` | TID、调用前x0、调用后w0 | processSystemMessage是否返回 |
| libosal_uipc+**`37b0`** | w0=实际semID，w1=timeout，x30、x29及有界用户帧链 | 识别本次等待对象/调用者 |
| libosal_uipc+`37e0` | x2指向的**16B原样**、x0 fd、x1 request、TID | 将用户参数与已见ioctl29对应 |

上述VA均由本脚本原码解码绑定；其中37b0/37e0原库固定SHA、16f2644等原AP固定SHA并保留窗口。完成这项取证后，再按真实semID回溯原sig_sem生产者；在拿到前不假设semID等于队列ID、不猜timeout=-1、不加signal/sleep/成功返回。[proof.AP_blocks/OSAL_sem_wrapper/minimal_followup。]

## 5. 重建与保留项

```sh
PYTHONDONTWRITEBYTECODE=1 \
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B \
work/fx3-vm-20261101/lead-claude/audits/boot-barrier-remaining/audit_ap83_clock_gate.py
```

本轮退出0：原DTB与本地源码SHA、部署gate ELF成员SHA、60处原AP指令、原OSAL wrapper、三轮候选/receipt/RAM快照哈希、三组实际线程亲和性/内核等待、首清屏字节均校验。解析器遇到交错serial时，明确按同TID marker、紧邻Name字段及完整结束标记界定线程块，拒绝跨线程归并；uptime按marker后的数字行读取，允许中间穿插observer输出。脚本只写邻接[JSON](ap83-clock-gate-proof.json)。

U保留：当前具体semID与timeout、上层调用者/通知者、AP84原生cpuset r2和icount结果、时钟/硬件等价、非均匀菜单帧与按键→原厂处理→新帧闭环。三份`/proc/uptime`采样只位于较早的init快照，不能当300秒结束时的guest时间，也不能与稀疏打印更新的`last_ns`直接除算倍率；需有每样本的宿主采样时间/暂停时间才能比较吞吐。[CPIO `/init:153–174`；proof.serial.uptime_samples与counter_RAM.statistics。]
