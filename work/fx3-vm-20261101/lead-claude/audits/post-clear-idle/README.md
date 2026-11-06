# AP83a 首清屏后停绘审计

**首要阻断是上一帧的 OSD 消费完成闸门，B 级强证据；不是已经证实的 live view 缺帧，也不能把持续增长的 timer 生产计数称为 UI 一直运行。** AP83a r4 在第二次 UI 更新后没有继续出队，第二、三快照的 AppFw 都等待 OSAL **semaphore**。原 `drawFramebuffer` 的首个前置回调会等待 ExternalOSDIF 发布闸门；第一帧发布已占用该闸门，收到 source=`8280074d` 的 `6003/6005` 才释放。对应调用链的 **0x5f0 栈深、ioctl 参数地址及 libc PC 三项均与保存快照吻合**，但未保存 semaphore ID/用户 LR，故不升级为动态逐帧 A 级证明。（libObj `16ea28、15d8e8、1543cc、f3620、f2210、f2448、f227c、f22cc`；serial **27255、27260–27278、33207–33215、46396–46404**。）

**另有独立同步阻断：SeqQueueCommon 等 VDF `0152` / peaking，不能承诺解除首帧闸门后菜单即出现。** UUD 的 option6 入口已返回，后续人脸存储/复制推进，线程又进入独立 `sequence_set_peaking::run`；本次没有后续 option0 请求或当前 mode/option 属性读回，不能验收为正常拍摄待机。（AP `2d95948、2d95a14、2dcfcbc、2dea0e0、2de72fc..7300`；serial **23537、23772–23850、23857–23896、48576–48584**。）

只读冻结的 `runs/ap83ar4face-4cd8574a`、原 ELF、观察器源码和现存参考；未启动 QEMU、运行 guest/CP、接设备、修改 runtime/STATE/锁/原件/Git。仅本目录三个交付文件。[脚本](audit_post_clear_idle.py) 与 [proof](post-clear-idle-proof.json) 保存 SHA、40 段原字节/反汇编、22 项指令断言、全部三轮线程快照与 maps、独立 RAM 解码和逐行证据。A=原码/实捕直接事实，B=受约束推断，U=未证实；AP/Obj 地址分别为 appFw.so/libObj.so image VA。**本文行号重新按原 serial 的 LF 计数**；旧 `ap83ar4-review.json` 的某些行号偏移，不复用其行号。

## 1. UI 实际停在哪里

| 事实 | 证据和含义 |
|---|---|
| boot future 已返回 | serial **23221–23241** 的同 event/cv 关联与 notify/wait-return；旧 AP77 的 boot 条件变量等待已越过。AP `2b68374..838c、285e430` |
| UI 先排空积压再推进两次 | serial **23898–23937** 尚有 backlog 跳过；**27074、27083、27260–27261** 两次 `a18=2` 通过时间/更新门。AP `16f2478..2488、16f2600、16f2640` |
| timer 注册正常 | 两次 `input_id=expected=12`、table hit、getTimerInfo=true，随后原 `1004`；serial **27084–27090、27262–27268**；AP `176fb4c..fbe8`（完整实现见前审计，本 proof 保留本轮直接捕获） |
| 只有一条清屏、一条 Flush | serial **27245–27255、27295–27296**；原请求 fmt0、640×480、flags ff、dst43feb5100。保存 raw 1228800B 全0；其中 native fmt0 有效像素为614400B，不能把宿主 dump 长度当 native RGBA32 格式 |
| 第二次更新进入后，UI 不再出队 | **27261** 为末次 id8；其后无 id4/5/6/7/8/10/11 样本。计数 RAM 独立解码：processSystemMessage-return=561、出队561、timer消费532、UI调用2，timer生产12853；读回 bank=`100`、对应源码 `fx3-ui-gate-v11.c:6,67,105–111` |
| 末段等待不是“只在丢弃积压” | serial **33207、46396** 两次相同 syscall：`29 fd3 request=ffffffff80000001 argument=7f551ad870 SP=7f551ad4c0 PC=7fa950acbc`；内核 `osal_wai_sem_tmo`。AP 主循环不是 futex boot wait，也不是等待5503e0收包 |

**重要次序：559 次 backlog_skip 大部分发生在首清屏以前；末次 a18=12320 不能反过来证明首清屏之后仍在持续消费 UI。** 第二次更新后的 timer 生产仍增长，末样本 serial **63710、64791** 已分别生产11000/12000，而 timer消费最终只有532。`last_ns` 只在抽样打印时刷新，并非 QMP 停机时刻。上述是本轮 RAM/serial事实，不能直接归因为 TCG 时钟缺陷或以清零 a18 修复。（AP `16f1a74、16f1d68、16f2488`；proof `gate/updates_and_observation_stats`。）

### 1.1 新闭合的 native 前置绘制闸门

```text
AP16f2640 ->16f1998 ->16f1a1c
  Obj GraphicsEngine::drawFramebuffer 16ea10
    ->16ea28 ->15d8e8 [interface slot18]
      interface = singleton1549fc+8，构造154890
      slot18: GOT261d70 ->153f9c -> singleton vtable+28
      vtable25cba8+28=25cbd0 ->1543a8
        ->1543cc ->f3604
          ->f3618 ->f2f20 [准备 framebuffer]
          ->f3620 ->f2e80 ->f2210
            ExternalOSDIF对象+48 ->fd344 ->osal_wai_sem_tmo(-1)
    [随后才到 16ea30/16ea58..60 的引擎/dirty 检查]

上一帧发布：f2fa0 ->f2428
  f2448先wait同一ExternalOSDIF对象+48 semaphore
  f24fc发本地msg1到8288076c；f2638处理
    ->1002到8280074d [声明下一包1003]
    ->1003到8280084d [bitmap/geometry/dirty矩形]
正常完成：8288076c收到source8280074d
  f2820 ->f28d8 ->f22f0
    6003 ->f2238 ->f227c ->fd384 ->osal_sig_sem
    6005 ->f22b0 ->f22cc ->fd384 ->osal_sig_sem
```

这张链的所有实线均由原指令/GOT/虚表恢复（proof `graphics_callback_binding/code/checks`），不是把时间相邻的1004连成 ACK。`f25f4` 只是发送返回成功，**不等同消费完成**；`f2638` 在发送失败才本地调用完成路径，正常发送成功会等待异步6003/6005。serial **27255、27275、27278** 的三次发送结果均0，解释了“消息成功入队而闸门没有归还”的可行机制。日志未见6003/6005，但观察器已满256、capacity_drop=143（serial **65809** 末统计），不能单靠缺 marker 宣布原端从未发送过。

### 1.2 末快照与原帧布局的精确拟合（B强）

原 RAM 的 id40 返回记录给本轮 main FP=`7f551adab0`；原 prologue 所需帧依次：

| 原函数 | 本链保存的栈大小 |
|---|---:|
| AP16f1998 | 30 |
| Obj16ea10 | 40 |
| Obj1543a8 | 20 |
| Objf3604 | 10 |
| Objf2210 | 20 |
| Objfd344 | 10 |
| libosal4858 | 160 |
| libosal37b0（u_osal_wai_sem_tmo） | 30 |
| 当前 ioctl-trace-v12 10d74 | 60+330=390 |
| libc c1cb0（裸 syscall） | 0 |

均为十六进制；总 **5f0**，`7f551adab0−5f0=7f551ad4c0`，两轮都等于实际 SP。trace前 SP=`7f551ad850`，原 `u_osal_wai_sem_tmo+14` 将参数放在 FP+20，因此 `7f551ad850+20=7f551ad870` 又等于实际 ioctl 参数。maps 给 libc基址`7fa9449000`（serial **41838**），实际PC−base=`c1cbc`，正是原svc后的指令；AP/Obj基址见 **41249、41711**。**这是三个约束同时命中的归因，不是展开了未保存的用户栈；仍缺sem ID/对象指针/LR采样。**（proof `UI_wait_fit`；原 syscall行 **33207、46396**。）

## 2. 末次关键线程等待清单

第三轮 snapshot 范围 serial **40672–53341**。名称按 `/proc/task/status` 保存的截断名；**没有独立 wchan 字段或文件**，不能补造用户栈。下表“条件futex”指op80、PC=`pthread+d5f0`；“限时futex”指op189、PC=`pthread+dae0`，其业务归属未知。OSAL收包见 `osal_rcv_msg_tmo` 内核栈。每行引用该线程完整snapshot范围/具体syscall行；proof还保留全部线程。（maps **41869**；pthread函数归属沿用原库PC，不把睡眠本身叫死锁。）

| 线程 | tid | 等待点 / 同步业务归属 | serial snapshot / syscall行 |
|---|---:|---|---|
| uipc_proxy_0 |205|OSAL收包；timer生产者仍活动|42191–42250 /42240|
| grm_result |229|限时futex；无未完成GPE请求证据|43148–43206 /43198|
| ExternalOSDIF |231|OSAL收包；应消费6003/6005完成通知|43265–43325 /43315|
| grm_gpe |233|限时futex；首FillRect已return|43387–43444 /43436|
| MPGRM_GPE0 |234|OSAL收包|43445–43505 /43494|
| MPGRM_GPE0_COMP |235|OSAL收包|43506–43565 /43555|
| AppFw |289|OSAL semaphore；B强：等待上帧ExternalOSDIF发布完成|46347–46407 /46396|
| SeqThreadPool1 |324|条件futex；早先0119已消费，不是仍等0119|48352–48409 /48401|
| SeqQueueCommon |327|OSAL收包；B：VDF0152同步reply队列81cf61c2|48527–48586 /48576|
| SeqQueueIndexTh |328|条件futex；具体事件U|48587–48644 /48636|
| SeqQueueStillCa |329|条件futex；具体事件U|48645–48703 /48695|
| SeqQueueMedia |330|条件futex；具体事件U|48704–48761 /48753|
| SeqQueueAutoRev |331|条件futex；具体事件U|48762–48819 /48811|
| SeqQueueNetwork |332|条件futex；已走SKD失败降级，未见当前服务收包等待|48821–48878 /48870|
| SeqQueueFtpTran |333|条件futex；具体事件U|48879–48936 /48928|
| SeqQueueSelfTim |334|条件futex；具体事件U|48937–48995 /48986|
| SeqQueueFaceReg |335|条件futex；不能据此断言人脸识别硬件完成|48996–49053 /49045|
| SeqQueueGetCurr |336|条件futex；具体事件U|49054–49111 /49103|
| SeqQueueHdmiCon |337|条件futex；具体事件U|49112–49170 /49161|
| SeqQueueVgaCach |338|条件futex；具体事件U|49171–49228 /49220|
| SeqQueueDispSwi |339|条件futex；最后0500是no-wait，不是未回同步包|49229–49286 /49278|
| SeqQueueSetYuvO |340|条件futex；具体事件U|49287–49345 /49336|
| SeqQueueBackgro |341/342|条件futex；具体事件U|49346–49461 /49395、49453|
| SeqQueueApo /ZoomDri |343/344|条件futex；具体事件U|49462–49578 /49512、49570|
| SeqQueueGetStil /GetVers |345/346|条件futex；具体事件U|49579–49695 /49628、49686|
| SeqQueueGetAudi /HttpReq |347/348|条件futex；具体事件U|49696–49811 /49745、49803|
| SeqQueueInterce /CreateO |349/350|条件futex；具体事件U|49812–49928 /49862、49920|
| SeqQueuePtpOper /PtpGetL |351/352|条件futex；具体事件U|49929–50045 /49978、50037|
| SeqQueueCPAppMe /WaitSeq /NotifyE |353/354/355|条件futex；具体事件U|50046–50220 /50095、50153、50212|

**能具体定位的未回同步服务只有当前327的0152；不能把其余条件futex线程都列成缺CP回复。** 通用观察器去重且满表；proof `pending_sync/reply_observation_limit`保留这个范围限制。AppFw则是本地帧完成信号量等待，其原发布协议异步，不能编造一个“UI send_and_wait请求”。（AP `2de72fc..7300`；Obj `f2210、f2428、f22f0`；上述各syscall行。）

### 2.1 VDF0152 的完整 raw、目的与原栈

serial **23895**：目的`92840747`、source`81cf61c2`、16B：

```text
0d205201100001800300010000eb8080
```

实际捕获帧在 **23857–23896**（中间有339线程交错，脚本按原FP范围挑327的9帧）：`2de7264 ←2dea0e4 ←2dcfcc0 ←2d95a18 ←2bd76fc ←2f71ba0 ←libosal_utm1184 ←pthread7020 ←libc c8dbc`。字符串`3953db8`明确 `sequence_set_peaking::run()`，`3967ae0`明确 `vdf_set_peaking`；`2dea0e0`交公共同步封装，`2de72fc`设timeout−1、`2de7300`收包，调用方预期12B结果。**1152是配对命令候选，CP状态域/错误映射未在本审计闭合，不给凭空status0回复**。末4B按实捕保留，不当作可任意清零的padding。（proof `pending_sync/strings/code`。）

339最后请求 **23884** 是`0d2000050a0001800000`（VDF0500，10B，source6189）；其调用者`2de6884`为no-wait路径。它与0152的 `2de7264` 同步路径不同；随后339已回条件futex。旧review的 `new_pending_request`还停在早先0119，**不是末快照327的实际阻断**。（serial **23872–23895、49278**；公共封装 `2de70a8..7344`与原no-wait调用地址。）

## 3. option6 是否完成，下一步是什么

**A：原UUD比较0<4、写版本4、写desired option6、调用mode2/option6，且入口返回，不能再说仍卡新增pin GET。** serial **23292–23364** 保存比较/写入/24B输入`020000000600000001000000000000000100000000000000`；**23534–23537**保存第42个pin提交/消费及face入口返回。`2d2f408→2d11dd4`只完成该mode的控制拓扑；返回后仍要运行common preparation等尾段。（AP `2d2f290..2f2b8、2d2fed8..fee0`；proof `mode`。）

**A/B：后续 common_preparation_sequence_of_face_registration 已完成三单元分配/三次真实复制及1db open；随后同一327进入独立peaking sequence，因此mode_transition原run已退回调度器是强推断。** DMM最终open的原栈 **23837–23852**仍含`2d1dc7c ←2d2fee0`；0152栈 **23857–23896**已变为`2d95a18 ←2bd76fc`，没有mode_transition。两者不是同一函数里等待live-view。**没有mode_transition return探针/当前143与145属性内存，不能写成A动态完成或“已正常待机”。**（原common preparation串`3937760`，AP `2d1dc78、2d2fedc、2d2f7b4..f948`。）

**下一实际步骤是已观察到的 peaking 配置等待，不是第三次 change_mode。** 全日志参数144仅写0一次、6一次（serial **7988、23294**），24B mode输入仅boot `1/0`（**21604**）及`2/6`（**23364**）；没有option0后续输入。正常still拍摄通常是mode2/option0，但本轮未出现该请求；不能替原程序硬写0或断言下一次必选哪个拍摄模式。原run尾部会写current mode/option并notify（`2d2f7b4..f848、2d2f90c..914`）；本次没有这些属性/通知的直接readback。（proof `mode/serial_evidence`。）

## 4. 首次真实内容绘制的条件与未满足项

| 条件 | 本轮结论、等级与证据 |
|---|---|
| UI出队→时间推进→Widget timer | 已发生2次A；随后停在第二次update内B强。AP `16f1998..1a1c`；serial **27074–27090、27260–27268** |
| 前帧消费完成 | **本轮最直接缺口B强**：Obj `16ea28`的前置callback在dirty检查前等待，首帧发布后须6003/6005释放；serial **27255、27275、27278、33207、46396** |
| Widget可见/notifyDraw/资源/dirty | 原 `16f19c4..1a1c`还会processEvent、资源命令、isFrameDelay（最多10次updateFrame）、notifyDraw；Obj `16ea30..60`检查引擎/dirty，非0才绘制。**本轮未抓完整树/dirty，U；不是已有文字等待GPE补混合**。原GPE只有清屏，serial **27253、27296** |
| live view帧、1142、1160、f024/f029 | **未证明是AP Widget/GRM这条路径的前置**。局部恢复链没有这些检查；本轮f024/f029仅软件pending（serial **21271、21300**），1142/1160无记录；不能把“未记录”升级为因果。真实sensor/CP帧也未验收。需要的是可归属的帧消费完成，不等同伪造一张live-view帧 |
| 输出ON/模式ready | 业务可能改变Widget树/dirty，U；**已不阻止首清屏与两次timer成功**。当前mode2/6并非普通待机验收；首帧完成闸门在上述native回调已能单独解释停住。AP/Obj VA见本表；serial **23364、27083、27261** |

因此不能选“无live view→OSD必不画”作为已证根因，也不能承诺“回0152→菜单必出现”。**最小下一步应闭合已发布AP帧的真实软件消费生命周期，并单独支持0152原业务合同；恢复持续出队后，再根据Widget/dirty实测决定缺哪个业务事件。**（Obj `f2448、f22f0、16ea28..60`；AP `2de72fc..7300`；末等待serial **46396、48576**。）

## 5. 最小诚实修正方向（方案，未实现/未运行）

1. **原协议下的软件OSD consumer**：明确接管`8280074d`控制队列及`8280084d/84e`更新队列，先核现有owner/历史pending防双消费；保存1000/1001 Widget配置、1004 timer状态；配对1002与对应1003或1005。原1002在`f1d90..1e18`清零12B，`f2690`写+8=1003，因此这一已捕获分支的静态raw为`021000000000000003100000`；**本轮未抓完整运行payload/1003 descriptor，不能把静态构造值冒称实捕raw**。（serial **27275、27278**；Obj上述VA。）
2. 对本次bitmap/ID/物理地址、格式/stride/容量、buffer generation及owner做FX3自己的校验，获取原生产者遵守的read lease/锁，完成有界快照/导出并释放锁和引用，才向`8288076c`交source=`8280074d`的完成通知。**6003用于完整帧、6005用于metadata更新的语义由FX3接收分支及1002 pairing支持；8B零扩展格式是A7C2软件实现参考，FX3原发送端完整schema仍U，不能称原厂逐字等价。** 拒绝/超时不得ACK，通知失败保留可核对状态，不强行`osal_sig_sem`。（Obj `f22f0..2310、f2638..27d4、f2820..2924`。）
3. **先补有界被动readback再运行方案**：在`f2210/fd344`记录sem ID、LR和ExternalOSDIF对象+48；在`f2238/f22b0`记录source、收到的size/raw及signal结果；确认上面B强栈拟合的对象身份。再验同一帧ID的消费、6003被原waiter处理、下一次UI出队及下一帧，分别记录。运行链可在准备实现时纳入这些观测；本worker不改runtime。（Obj上述VA；serial **33207/46396**缺sem ID为本项来源。）
4. **0152单独按原CP映射补齐**：冻结当前16B raw、3/0/1与颜色域等有效参数，审计旧VDF命令/状态域/失败码，再作有界虚拟peaking配置consumer；成功只能表示软件参数接受，不能宣称sensor peaking生效。不要先给1152/status0，也不要用0500或display-on替代。（AP `2de9de4..dea170、2de72fc..7300`；serial **23895**。）

A7C2现存固定commit `b3d7c1f…` 的 `headless-osd.c:285–365`采取1002→1003/1005、持租快照、落盘后6003/6005，失败不ACK，marker明确CP composition/panel unimplemented；这是**源代码参考**，本worker没运行它，也没把A7C2的格式1、偏移2ebde0/FB90或vtable移到FX3。源SHA与原本已存在的commit回执在proof，查阅入口：[headless-osd.c固定源码](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/headless-osd.c)。本轮联网请求GitHub失败，因此不声称再次验证了远端现状；使用的是本地冻结材料。（FX3独立等待链在第1节，故结论不依赖A7C2成功宣称。）

## 6. 重建与剩余边界

在项目根运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/post-clear-idle/audit_post_clear_idle.py
```

退出0重建唯一相邻proof；独立解码64计数+32统计和72条提交记录，核对原库/当前trace SHA、关键指令/回调虚表、两次SP/参数地址拟合、3轮命名snapshot、原0152 raw及交错栈、2条GPE和实际全黑内存。`dis <库名> <VA> <长度>`、`str`、`xref`为只读查询；不调用前审计rebuild，不生成pycache。Capstone方法按[官方Python API](https://www.capstone-engine.org/lang_python.html)核对；Sony语义依据本地VA/serial。

**未关闭**：当前sem对象/LR动态身份；FX3原6003发送者与完整schema；0152原CP状态合同；mode_transition完整动态return及current143/145；完整Widget树/dirty/真实非黑帧；改动后持续绘制与按键响应。f024/f029软件pending、GPE清屏、AP软件快照均不充CP运行、物理scanout、live view或可操作菜单验收。（相关原VA、实捕位置及缺失范围逐项见上文与proof `open_items`。）
