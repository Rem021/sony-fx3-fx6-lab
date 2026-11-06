> 最新：AP86B v2 `ap86bdisplayv2-3d542078` 302.2s，0400/三队列释放/原进程存活及回收核验=True；类别270=7、方向243=2，仍无菜单。详见文末完整回执。

# AP86：消息池因果已取证，接收端与显示观测实施中

AP86A仅被动观察，已证实普通kernel vpool无可用128B块；2632条原OSD分配/发送无userfree、无pointer reuse，74D/84D/84E积压。尚未改接收所有权或回复0400；下一合并轮实施原接收/free、0400与显示/铰链被动采样，不改铰链输入。

## AP86A 原运行

`ap86apooltrace-bc28575f`，286.34秒（上限300秒，按原owner停止取证）。exit0/reaped/inputs_unchanged/PID消失/双锁释放，结束窗口im.elf maps存活，无symbol/fatal。缺两个pairdeadline marker：本次未停在control之后的pair阶段，而是上游尚未进入下一条被跟踪CP分配；不能宣称全部诊断marker通过。

- 原nativeconstructor分配2632次、返回2632次、发送2632次，userfree0、native pointer reuse0。跟踪只涵盖原libObj f1db8(74D/12B1002)、f1e44(84D/36B1003)、f1d2c(84E/8B1005)。下一版补76c/40B local及headless8B ACK分配、active-allocation deadline/原栈，不能把未覆盖的阻塞线程伪称已捕获。
- 原proc normal vblock最后160个free块均64B，共10240B；原CP高位路径分配8/12/36B body至少需128B，无法满足，属于该尺寸的分配饥饿/碎片化，非“总剩余字节0”。
- 原kernel vpool独立QMP 56B读回：maximum524288、free/minimum10240、waiter_head非零，和proc统计一致；地址由只读sysfs模块.bss绑定、原符号偏移3740，模块SHA与实际CPIO成员一致。
- GMSGQ最后74D原列 `1663 0 0 0 1 1663 0 0`、84D `1 0 0 0 1 1 0 0`、84E `1315 0 0 0 1 1315 0 0`。M为待收链数，A为原分配引用；F/W来自flag byte+1的bit1/bit0，**不是free计数**。之前status简写“free0”已向Lead明确更正。
- 最终OSD1316次snapshot/ACK/nativeSig均消费，stage0/pending0；没有新的CP valloc begin不意味着池正常。此变体与AP85尾段stage1不同，下一版须覆盖更上游local/ACK分配。

[运行复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap86a-review.json)，[原代码/分配算式/队列字段](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap86-lifetime-original-proof.json)。`osal_stat_msgq`会在不存在时创建队列，故被动轮不调用；只读proc/QMP，不让观测创建额外协议对象。

## Lead 后续明确授权

池因果条件满足后，软件消费者可作为缺失CP的74D/84D/84E接收端，按原OSAL rcv/free语义处理。Lead阻塞ask答复选择A，进一步允许74D GUI1000/1001/1004保存冻结字段、无回复；1002配对1003/1005。未知类型必须完整raw、计数后原free，无副作用/无回复，报告单列；启动积压按序处理，不给不能精确匹配当前pending的旧批补ACK。

下一轮同时接入0x400精确10B→1400/12B裸status0（不是590000），保存mode0/counter pending，失败回滚；采样原五键cache、d72..d76、270/243/modelindex、旧/新display、Widget root/visible/resource/dirty以及SYS0400 completion observers与queue next。当前只完成capidv43交叉构建和ASan/UBSan黄金/10字节变异/长度/source/重复/回滚/原request caller-owned检查，尚未运行该回复。

原6003/6005完整CP schema、颜色/alpha/面板、非黑菜单/输入仍未验收。AP86B尚在实施，不能将后续授权写成已运行结果。

## AP86B 第一轮：早期 external abort（失败，2026-11-02）

`ap86bnative-37785e4e` / `ap86b-native-osd-sys400-display/candidate86b.json` 运行7.303秒，在启动阶段发生 `synchronous external abort (0x92000050) at 0x0000007f97ae3280`。fault字段是故障访问VA，尚不是已证PC归属；UI/display selftest及绑定、0400、OSD receiver均未到达，因此不能以本轮评判队列修正或显示状态。运行器立即QMP stop→只读快照→quit，exit0、reaped、hostPID21483不存在、inputs unchanged、两锁释放均通过；missing markers非空，im末尾maps未采到，不宣称主进程存活。原UI计数器尚未初始化，专用postboot decoder不适用，基础回执独立保留。

已冻结capid43/headless5/lifetime2/display-observe1，实际源与构建哈希见candidate build-receipt、四组ASan/UBSan宿主回执；88处原字节与21个审计输入检查通过仅是静态/宿主证据。此故障已发escalation并按停下规则向Lead申请最小隔离A/B：只撤新display preload，其余同候选及铰链不变；尚未获答复前不再运行。

联网复核：QEMU官方[icount说明](https://www.qemu.org/docs/master/devel/tcg-icount.html)仍明确与MTTCG互斥；A7C II维护者[公开项目](https://github.com/QAQLeonard/a7c2-fl23-research)针对ILCE-7CM2 2.01，[service-preload研究](https://github.com/YuuLuo/a7c2-service-preload)定位为该机型服务认证/加载链，本轮未借用其地址或声称FX3运行验收。

## AP86B 无显示探针对照：队列/0400局部通过

Lead ask5679批准仅撤新display preload、保留capid43/headless5/lifetime2、80秒，增加早期1秒maps。`ap86bnoobserver-fe62ded9` 实际81.756秒，exit0/reaped/inputs unchanged/hostPID不存在/两锁释放，无fatal或新symbol；原完整snapshot有im.elf映射。missing仍有TIMER_OBSERVER_END、UIPC_OBSERVER_END、compactENDMAPS：80秒时原全线程快照尚未结束，不能宣布空缺或结尾compact存活通过。

0400保存mode0后精确12B回复，原AP自然free result0；物理counter仍pending。875次快照/ACK/nativeSig成功，原生接收与free逐队列相等：74D1211、84D1、84E874，GUI336，unknown/stale/errors均0，无持有descriptor。kernel normal-vpool空闲392064/524288、waiter0，对比AP86A空闲10240且waiter非零，支持缺CP接收释放引起耗尽并已被软件consumer修正。GPE仍只有原FillRect fmt0 flagsff+Flush，各result0，无新像素/菜单。

新lifetime观察确认76c的40Blocal原constructor返回地址f1fe4与8B软件ACK持续分配/释放；出现SEND record=-1是消息先被原消费释放的观测竞争，不能据此判send失败。实际native返回码0、free计数与ring/ACK/信号分别保留。上述协议合同均未因隔离改变。

故障范围收敛到display DSO路径，尚非已证某条指令根因。v2只增强bind逐点/selftest/映射阶段诊断，以procselfmem检查原指令，NOLOAD|LAZY避免提前强制NOW解析；23点事件逻辑及寄存器保护ASM逐字保持，新版单独冻结。原kernel BSS/vpool只由宿主QMP只读，不是lifetime guest mmap；headless仅首次1002映射独立41e000000/16MiB。首轮没有receiver启动/selftest PASS，尚无故障VA的同期maps，不能伪造归属。

## AP86B v2 完整窗口回执（2026-11-02）

`ap86bdisplayv2-3d542078`，candidate=`ap86b-display-v2-diagnostic/candidate.json`，capid43/headless5/lifetime2/display-observe2，302.184秒；四A35/MTTCG/原cpusets/原kernel不变。exit=0、reaped=True、hostPID不存在=True、inputs unchanged=True、两锁独立释放核验通过；missing=[]，结束compact `/proc/222/maps`含im.elf=True，新fatal/symbol和软件reject=False。完整机器回执见runtime/ap86bv2-review.json；本轮分类 `AP86B_SOFTWARE_OWNERSHIP_0400_PASS_DISPLAY_CAUSE_PARTIAL_NO_MENU`，菜单仍未通过。

- 原生CP替身：74D/84D/84E receive=[6912, 1, 5198]，free=[6912, 1, 5198]，GUI=1713、unknown=0、stale=0、errors=0；未知若发生则完整raw计数/free且无作用/回复。软件ring快照/ACK/原sig分别5199/5199/5199，duplicates/rejected/failed=0/0/0，结束stage=0、pending=0x0。原生接收/释放所有权变更是Lead明确授权的缺CP接收者模型，ACK原厂完整schema仍未证实。
- normal-vpool最终free=96064/524288、waiter=0x0、minimum_free=94784；对比AP86A仅10240B/64B碎片且waiter非零，持续分配/释放已越过旧耗尽规模。76c8BACK、40Blocal及CP原constructor分开计数，见review lifetime；发送返回前原消息已被free时SEND ledger record=-1仅为采样竞争，不等于native send失败。
- 0400精确1400/12B/status0被原AP释放，converted_result0、run成功尾部、原completion调用返回、queue继续均有同task/tid/epoch证据。task+158/+160实际begin=end=0；queue继续时length11，首4候选run为2dca7fc/2dca610/2b7f8cc/2d9ac90，原输入0/0/0/80000033，未编造后继命令或observer。counter后端仍pending，不声称物理timecode。
- 五个原cache状态都是7fffffff哨兵；H/V/C/S/hinge模型均0。原分类函数前270=0/243=0，返回后270=7 VALI_ANGLE/243=2，采样d22=1 MONITOR。runtime model index6，原不可变表槽6=type0；文件初值index8/type2不等于运行值。27ed854..888 selection/set marker=0/0（未触发，不补造旧/新值），没有证据把enum2叫REVERSE_CLOSE或将本轮停绘归为LCD关闭。所有铰链输入/270/243/d22均未强改。
- 原WidgetSystem候选字段+8ac采到78，Layer候选非空，qualifier原返回有0/1，resource_impl非空；这不闭合实际Widget根、visible或资源加载完成。旧marker layer_id只按Layer+8原始字段处理，尚不能命名ID。原GRM128518返回0计5165、非0计1，仅首次dirty有像素分支、其后未见新增绘制；不能强制visible/dirty或用重复6005冒充新帧。
- GPE仍只有FillRect fmt0/flagsff/dst545/result0与Flush/result0，各一次，approx/HV均未触发。所有保留采样pixel_source_seq=[1]，PNG与raw仍均匀黑；ring覆写存在采样缺口，不是逐帧全历史。本轮无非均匀菜单像素。

四组宿主ASan/UBSan检查与原字节88块/输入21项检查独立于guest回执；display v2正常事件逻辑及ASM与已测v1逐字一致，guest完整寄存器自测和23点绑定通过。v1早期fault的精确VA映射归属仍未闭合；v2增强分阶段日志、原字节改procselfmem安全读及NOLOAD|LAZY后本窗口未复现，不能把任何单项差异升为已证根因。v2新增header映射41e000000/10000位于已预留16MiB ring内、物理QEMU后备由本次真实ring/PNG读回交叉证实；lifetime不建立kernelBSS或/dev/mem映射。

0x11a之后的全部实际捕获请求按LF顺序保存在runtime/ap86bv2-post11a-requests.json；底层有界trace会去重/丢弃，不能称全局无损时间线。完整同epoch显示/0400/queue原marker和原生owner表在ap86bv2-review.json。

![AP86B逻辑OSD原样读回；均匀黑，非菜单](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap86bdisplayv2-3d542078/osd-frame-004770-format0-RGBA-opaque.png)

池趋势补充：GLOBAL normal-vblock heading 从49152升至约429504后末几次采样进入平台，最终QMP free96064/min94784/waiter0；不能把80秒free392064当300秒结尾，也不承诺无限期无耗尽。并发serial会把内核日志插进数字，解析总和/最大块仅是可能损坏的样本，最终quiesced kernel结构为权威。AP86A首GLOBAL区独立复核仍是160个64B碎片与10240B、未改变其耗尽结论。

Lead验收：ask36013答复接受AP86Bv2为新健康基线（capid43/headless5/lifetime2/display2），保持本Dispatch、不worker_done，等待AP87的0402及后续timecode_preset/delete_all_individual_face/set_release_lock合同；STATE preferred已更新，保留AP84r2旧基线身份。


### AP88 补证：首轮 external abort 的归因更正（2026-11-02）

AP88 `ap88cpreset-a6a5f2b1` 保存了完整PC/LR/原映射：原 `libgpe.so+dc88` 的 `STR w2,[x0,x1]` 将15写入物理f3400280，线程MPGRM_GPE0，经原worker dcb0进入Initialize(db74)。v14只在dlopen后替换入口，无法撤回已经进入原函数的工作线程；这是运行时绑定竞争。AP86B首轮故障VA页内偏移同为280，且同样在原GPE加载/绑定附近，高度吻合同一竞争；旧现场未保存完整PC，不能冒称两个PC逐字核对。撤回把display DSO当成根因的推断；无display那轮成功本身不能排除时序变化。Lead批准的v15仅在精确原GPE0/1线程创建前完成既有setup/GOT绑定，不新增寄存器模型，详见 [AP88报告](ap88-cp-backup-reset-shutdown.md)。
