# r32：零 ring 的因果审阅与下一步决策

**决策：现有证据足以定位“首个原更新/绘制与 publication 之前的推进不足”，不足以选择一个有因果依据的行为修复；本轮不修代码、不增加运行。** 已确认地址/装入版本一致，发现 ring 懒初始化的诊断盲区，并厘清 counter 不是队列深度。r31 仍是180秒未合格首帧、0键失败；没有 boot/menu 通过声明。本任务只读、仅写本目录，无 VM/Start/服务/浏览器/QMP/设备操作。它是 FX3 可靠性支线，不改变或绕过 FX6 provider 拒绝。

## 1. 全零证明什么

原 `osd-ring-final.bin` 是暂停证明成立后的完整16MiB导出（读回完整，不是有效v25诊断事务；全零头使parse_valid=false），**16777216字节全部0**，SHA=`080acf35a507ac9849cfcba47dc2ad83e01b75663a516279c8b9d243b719643e`。r30观测为399次 `bad_magic`，initial/last16Q均0；**并未保留399份16Q，不能说每份都全零**，但所有已计数采样均未通过magic门。见 [r31证据](r31-ANALYSIS.json)。

实际四轮同一 N64 CPIO、固定argv及所核helper字节完全相同。OSD member SHA=`67155b38…9b5fba8`，与固定 candidate、实际run CPIO audit和所读编译产物相符；C源码 SHA=`1c4d2b42…c5956eb` 同契约。compiled `observer_bind` 在 `0x14030–0x14050` 把 **0x41e000000/0x1000000** 传给 mmap，和每轮实际 QMP导出地址/长度一致；`0x140a0` 写入的编译常量也确为 magic/version2，见 [BINDING.json](BINDING.json)、[编译代码](osd-bind-compiled.txt)。简单的导出地址写错不受支持；运行时 mmap 返回、ring指针和别名映射未采到，不能绝对排除另处写入。

初始化不是开机动作：`fx3-osd-headless-v25-r3.c:121` 在原 `hsend` 返回0后才调用 `observe`；`:111–112` 的当前 queue_owner 分支还要求 enabled/API齐全、source=`0x8288076c`、dst=`0x8280074d`、符合 `qo_publication` 的12B `0x1002→1003/1005` 包，才进入 `observer_bind`。`:81` 依次检查claim/cmdline、打开mem、mmap、清零、写magic/version/诊断头，最后才设 observer_ready并输出BOUND。GUI `0x9088076b` 的63条config本身不触发此分支。

**新的盲区：`:33` 的 `v25_diag` 在 ring为空时直接返回0，而`:121`首次publication的 produce_enter恰在绑定之前。** 因而零诊断既不能证明“从未尝试publication”，也不能区分bind未进入、失败或尚未完成。成功绑定之后当前代码没有常规清零/重置observer_ready路径；唯一显式大清零在初始化写magic之前。全零/无BOUND支持“未完成初始化”，不支持“已正常发布后按正常路径清零”；外来覆盖、损坏或异常重装没有写入历史证明，仍不能排除。编译器把冗余清零优化为ring+0x20起，随后覆盖前32B；本审阅没有把C层面的语句顺序误当成每字节机器指令。

r31完整serial含22个NUL，按bytes扫描未在原startup接收前缀发现 TIMER_ENTRY、UI_FILL_EXEC、GPE_CMD、OSD BOUND/OWNER_START/COMMIT。已有timer/UI hook的BOUND存在，故与未推进到原更新/绘制路径相符；它不是“固件从未产生任何私有/offscreen像素”的绝对证明，更不是死锁证明。

## 2. 同一root究竟在数什么

原 appFw SHA=`545c5053…8290f` 与四轮actual成员一致。[生产者反汇编](app-producer-full.txt) 精确显示：`0x16f1a48` 接收root→以root+0xa20调用原辅助→`1a68/1a6c/1a74` 读、加1、写32位root+a18→条件解锁→`1acc` 才分配28B→写type `0x150000`、source `0x830128`→`1bb0` send到 `0x5503e0`。可见错误分支没有计数回滚；不能把一次意向/前置hook计数等同成功入队。

[消费者](app-consumer-full.txt) 在 `0x16f1d3c` 校验source、`1d4c` 校验type后，才在同root+0xa20辅助后由 `1d60/1d64/1d68` 读、减1、写root+a18。它随后把分派输出type设为5。UI主循环 `0x16f2478–2488` 以 **signed<=2 或 a12非零** 进入计时分支；`0x16f2600` 还要满足原时间差>0x62f4及后续原条件，`0x16f2640` 才调用 `0x16f1998` 的updateCurrentTime/processEvent/resource/条件绘制链。达到低水位不是保证一定出图。外层生产函数由哪些定时注册/调用者驱动、每笔alloc/send结果和消息身份对齐仍缺失，不能只按函数名推定期望频率。

v15的id9/id10探针在原STR之前：9记录r3拟写加值，10记录r0拟写减值，5记录原分支已装入的决策值；日志首次50次及每1000次采样，N64发布也逐字段、可能滞后。r31已发布bank的gate803/skip803/time_pass0/peak1954、producer2742/consumer788、last_a18=1955有明显不平衡迹象，但**采于End后，不是startup终态或事务核算**。独立tail是更晚的非事务checkpoint，同样不混入本节startup统计。

本次以同root日志采样证明局部绑定：各轮id5/9/10/11的完整样本都只有同一root，不能用跨轮ASLR地址相同作为要求。原窗口见 [COMPARISON.json](COMPARISON.json)：

| 指标 | r31 | r28 | r26 | r26b |
|---|---:|---:|---:|---:|
| 窗口末字节 | 3819978 | 4915799 | 3031595 | 3040214 |
| `0x150000`预发送日志 | 2736 | 4427 | 503 | 514 |
| 其他预发送类型合计 | 27 | 27 | 27 | 27 |
| GUI config `1001+1000` | 59+4 | 59+4 | 59+4 | 59+4 |
| 已记录gate7/gate8更新入口最大n | 0/0 | 1/1 | 2/2 | 2/2 |
| 匹配的task诊断区间字节覆盖 | 2255433 | 2511628 | 404679 | 389697 |

r31窗口是host开始原finally前**已消费**字节前缀，不含cleanup后读到的部分；不是guest在End瞬间的全部已发生事件。成功轮截至首个原commit之前，均无按键。**r28只能给首次timer前的程序/日志序前缀，没有准确pre-End字节截点，因此不将它冒充严格host startup窗口**，其首commit观测还跨越End。四窗不是等时样本，表中差异不能直接算成消息每秒速率或性能因果。全部统计排除partial_record；窗口解析曾可能借用cut后LF，现已收紧并加回归，四轮上述汇总未变，属于分析器边界修正而非r31根因。

## 3. 来源、状态与日志开销的证据

预发送记录均指向队列5503e0。四轮所见非周期类型/source/caller/长度计数一致，主要差别是同一source830128、type150000、caller_relative16f1bb4的重复量；r31这些记录来自4个TID。r31 id11完整样本有48个150000与两个其他类型，成功轮首批样本44个150000及6个其他类型；这不是完整消费分布。

实际 CAPID49源码与编译hash绑定成立，`:609` 的 `BOOT_QUEUE_SEND` 是**原send之前**同步dprintf，没有rc。不能说r31全部2736次都成功。已有 `UIPC_SEND_UNIQUE` 对5503e0有15类、所见result均0，包含首个150000的返回0；但 `ioctl-trace-v12.c:46` 去重key不含result/TID，后续同体失败也可能不再输出，另有256容量/锁丢弃边界，不能外推全体成功或无错误。`RECV_BEGIN` 按TID/queue去重，仅证明开始等待原调用，不是接收数量、队列深度或停滞证据。

日志成本不是纯推测：CAPID每笔预发送做hex/dladdr/dprintf；ioctl observer `:43–52` 即使去重也会 `send_stats`，`:23–27` 打开并写/tmp统计；init还会遍历每个线程的status/syscall/stack/stat/cgroup。失败窗诊断覆盖字节更多，r31首screen的实际clock_id1值113.990203s，对照27.604531/27.156464s，r28为83.836416s；但r31 pre-AP宿主取证+8.638s反而比r28+16.794s快，不支持单一固定比例启动减速。**当前没有这些观察操作耗时/阻塞的完整计数和原始调用配对，不能认定日志就是根因，也不能据此直接删日志、改定时器或合并消息。** 慢启动可能先导致多轮诊断暴露，也可能被诊断进一步拖慢；不同guest clock、host clock、token收到和完整record保持分开。

## 决策与交付

直接可修的生产逻辑：**无已证因果、足够安全的最小项**。强行改a18、阈值、周期、丢/合并150000消息都可能破坏原增减配对和原生事件功能；跳过首帧/延长180秒也不合合同。当前能直接落实的只有本目录分析器窗口回归，未修改候选。

[下一次最小观测方案](NEXT-OBSERVATION.md) 精确列明独立的first-publication / bind入口与返回见证、同root alloc/send/consume分阶段计数和有界成本证据，解释为何r30无法提供这些数据。它仅是后续离线候选设计，未实施、未增加VM次数或申请扩大FX3硬件配置。

可重现：`python3 -B analyze_zero_ring.py`。输入先pin、结束123项SHA/大小全回核；源代码摘录、限定窗口、原始偏移、反汇编参数与绑定分别在CODE-EVIDENCE、四份ANALYSIS、BINDING及INPUTS前后清单。没有复制大日志；r31操作代理的封存报告/目录保持只读，本报告不等待其最终清单，也不替代它的收尾验收。
