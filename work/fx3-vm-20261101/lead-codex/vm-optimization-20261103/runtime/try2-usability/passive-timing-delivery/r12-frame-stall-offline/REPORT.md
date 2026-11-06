# FX3 R12 画面停更：离线定位

2026-11-04。**已定位到“原生输入队列收到了 UP，但已记录帧生产在 UP 之前停止；UI 主循环积压门是首要观察点”，尚未定位可实施的根因修复。** 宿主成功读到最新已提交帧65，不能仅以浏览器缓存解释这次停更。结束时 UI gate 的3852/3918次决策绕过定时更新，a18约786；但只有全轮累计和普通采样，没有停更区间的计数差分，故仍不能证明该区间每次更新都被该门挡住。

仅写本目录；只读三轮既有原 FX3 证据、已有原分支导出及实际 v3 timer/v11 gate 源码。无 FX6、VM 启停/控制、guest/平台改动、编译、部署、历史测试重跑或额外 worker。卷 UUID 已在建目录及解析前核为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。Mac 根目录不是 Git 仓库，未写 README/ledger/历史 run。

## 证据与版本

以下路径相对 `try2-usability/`，记 `DEL=passive-timing-delivery/`。

| 样本 | run | 有效比较范围 |
|---|---|---|
| R12 | `runs/v25diag-web-r6-49f9bf9d` | MENU完整打开，第二键UP已接收，焦点停在Area/Date/Time Setting |
| R11 | `runs/v25diag-web-r6-814c425f` | 七键原生交互有语义目标；第七次确认后宿主未解锁，总体任务failed，不称完整链成功 |
| R10 | `runs/v25diag-web-r6-8456422c` | NAV32逐键导航验收；全菜单/长时稳定性仍未知 |

复用 `DEL/r9-ui-startup-offline/REPORT.md` 的原生门、16位GUI opcode、CPIO实际成员绑定及原ELF导出，不重扫固件。实际别名 `fx3-timer-observe-v1.so` 是 **v3**，`fx3-ui-gate-v1.so` 是 **v11**；实际 OSD 是 **v25-r3**，不是旧v7。相关源和复用材料已纳入输入哈希。

三轮receipt的14项输入路径/哈希完全相同，原A/r3 `guest.cpio=31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`，candidate=`a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`。两份SOURCE-FREEZE比较为22项中仅PAGE文件不同，21项相同；本次重新核验R12冻结22源及三轮各20份实际归档source copies，均匹配回执。这里复用既有CPIO绑定/运行输入回执，未重新哈希整个大镜像。

## 四个阶段分别成立到哪里

| 阶段 | 直接证据 | 边界 |
|---|---|---|
| 网页请求/原生队列接收 | R12两个key均HTTP202；UP `FX3_KEY_INPUT_RECV` status1/0、native_result0；STEP_DONE one_down_one_up1 | receive线程261返回不代表UI事件处理/焦点更新完成 |
| 实际UI处理 | gate id4/5/9/10/11末段仍有记录，root相同、UI线程380继续取内部150000/source830128消息 | 未取得UP进入WidgetSystem/目标widget处理器及返回身份；不能写“UP已被UI处理” |
| 帧生产/提交 | 最后记录commit65/source40；随后signal_return0；末端环及串口未记到后续提交 | 环只保留256事件，且probe有选择条件；缺记录不能绝对证明没有任何原调用 |
| 宿主读回/显示 | `trial-final.json` matches_committed_ring=true、latest_native_committed_sequence65；step2/final原始像素逐字相等；网页shownSHA等于帧PNG SHA | 宿主读到最新已记录帧，不证明当前源surface内容，也不证明菜单语义通过 |

已亲看 `R12-01-MENU.png` 和 `R12-02-UP-observe.png`：两者均Setup > Area/Date，橙色Area/Date/Time Setting，Language右侧English。R12已跨过R11的宿主确认锁：step1确认HTTP200后确实有第二个key202，无需假设前端未放行。

## 同钟顺序与最后生产链

原串口行号按 **LF**，不按Python splitlines；保留交错文本和原字节偏移，见 `EVIDENCE.json`。

| 事件 | guest CLOCK_MONOTONIC id1 ns | 来源 |
|---|---:|---|
| 最后produce_enter，frame64/source40 | 100725256992 | ring serial511，tid274，op1005 |
| produce_return0 | 100841168992 | serial512，link511 |
| receive | 100905194000 | serial513，tid1243 |
| 最后commit65/source40 | **101041568992** | serial514，tid1243 |
| signal_enter/return0 | 101134396992 / **101134468000** | serial515/516，tid274，link515 |
| UP down接收 | **112335182992** | serial.log LF62819，tid261 |
| UP up接收 | **113231536992** | LF63144，tid261 |
| UP完成注入回执 | 不提供独立绝对ns | LF63151，STEP_DONE |

最后commit比UP down早 **11.293614秒**、比up早 **12.189968秒**，均仅由guest id1相减。因此“UP造成帧停更”没有这份时序支持。R12完整16MiB环独立重解析与既有JSON逐行相同：accepted516、drop0、invalid[]，尾部261..516；32套produce/receive/commit/wait/signal各类事件数量均32，已有parser无unpaired enter。最近一次已记录draw wait也已return0，未见一条悬挂等待足以支持“卡死在最后draw semaphore”；仍不能排除未记录调用或别的等待。

串口最后原FillRect执行/返回为seq181，LF57749/57762，tid280，返回0；最后OSD ACK为frame65/source40，LF61004。最后timer snapshot在LF61001为bound1、patch_mask0xf、timer/id/info/table各37、config3、fill30、event_seq181；它在UP之前，**不是结束时timer累计快照**。本轮v3详细日志未见达到1024序号限幅，后续没有记录到新的Fill或timer；这一点只能作为已留存轨迹的支持。

## 双bank与真实UI分支

v11 `mirror()`：header为8个Q；统计区地址是 `0x100 + active_bank*0x1000`，每bank 96个Q。R12 header magic=`0x3145544147335846`、version2、active0、publication28282、pid237；**不能从header后直接解count**。本次同时保留两bank字段，以下采用active0。

| 结束累计字段 | R12 | R11七键 | R10 NAV32 |
|---|---:|---:|---:|
| id5：真实cmp输入决策次数 | 3918 | 14009 | 32148 |
| id6 / backlog_skip | 3852 | 10087 | 22779 |
| id7：到达时间比较 | 66 | 3922 | 9369 |
| id8：调用原更新链 | **65** | 3506 | 8216 |
| time_skip / time_pass | 1 / 65 | 416 / 3506 | 1153 / 8216 |
| id9：a18增量store前probe | 4674 | 13964 | 32024 |
| id10：a18减量store前probe | 3887 | 13959 | 32022 |
| gate_hist [0,1,2,3..10,11..100,>100] | [0,0,66,837,1651,1364] | [118,261,3543,8464,1258,365] | [346,704,8319,19623,2813,343] |
| last_a18 / peak_gate | **786 / 786** | 4 / 283 | 1 / 269 |
| a12_nonzero / a13_nonzero | 0 / 0 | 0 / 0 | 0 / 0 |

这不是等长性能A/B。R12全轮有66次低水位机会，否定“从未获得更新机会”；普通id5日志漏掉低水位也不能当作相反证据。样本根对象为 `0x7f06f75d60`，id5 n3000在LF60494 decision5，id6 n3000在LF60988 r0=0/decision19；更晚id5 n4000在LF73537 decision862，id11 n4000在LF73533继续取150000/source830128消息，id10 n4000在LF73628减量值888。LF73402已有 `FX3_AP100_CONTROLLED_CLEANUP_BEGIN acceptance_window_closed=1`；**n4000是清理恢复运行后的额外串口，不属于先前暂停保存的3918次bank**，不把两者强求为同时快照。

原 `appFw+0x16f247c/0x16f2480` 为cmp w0,2 / **signed b.le**；只有a18 signed<=2，或随后a12非零，才进入 `0x16f25ec` 时间检查。正值>2且a12=0会走 `0x16f248c` 绕过本轮定时更新。`0x16f2600` 时间比较通过后还需其余条件，`0x16f2640` 才调用 `0x16f1998`；内含updateCurrentTime、processEvent及条件性drawFramebuffer。主循环在这道gate之前也有processEvent路径，不能把绕过此更新链说成所有UI处理均被阻断。

原 `0x16f1a68..74` 在分配/发送内部150000消息之前增加a18；`0x16f1d30..68` 校验source/type后减少。R12最终4674−3887=787，接近last786；probe在原store前，mirror逐字段atomic load，不能据差1称计数损坏，也不能把787直接称内核队列深度。它支持生产/消费尚有存量的机制假设，但分配/发送失败、同对象逐条消息身份与原计数平衡未闭合。

UI gate first/last_ns来自 **clock id7**，last_ns仅在普通采样打印时更新；本轮143396292992不能当快照时间，不能与id1的commit/输入时刻相减。timer input_time是原widget入参，也未当作id1纳秒。

## timer停止并不是已验证根因

成功R10的最后timer ENTRY为LF43872、seq425，随后在全轮尾部snapshot仍为timer99、id/info/table各99，但fill202，OSD ACK8220；其bank仍有8216次更新、环最后commit8215在guest id1 668194158000。说明这个特定 `appFw+0x176fb4c` widget timer停止增加可以与后续大量UI更新/帧提交并存。R11最后snapshot timer340/fill129/event_seq1497；详细ENTRY/Fill因共享seq>1024限幅，不能用打印行数229/100当累计总量。

因此R12中37次timer都通过ID/info、最后有原返回，不应优先给该timer加keepalive、改ID/getTimerInfo或强行补1004。当前更小的缺口位于定时更新门的区间状态，以及UP从输入队列到实际widget处理的下游身份。

## 事实、推断、未知与下一步

**事实**：原生队列收到两键；帧65已在UP前提交；宿主最终仍读到65；结束bank显示大量backlog bypass及高a18；UI消息处理循环仍有后续进展，非整线程静止。health/protocol/render/lifecycle/diagnostic五门true、duration159.803815秒、字面`-1018`计数0，均不能替代焦点变化验收。HTTP UP→End请求为 **43.821秒**，超过30秒要求，属另行执行程序偏差；不作为guest处理延迟或根因。

**推断**：优先怀疑内部消息积压使UI很少进入定时更新/绘制，而非宿主只显示旧缓存或UP未送达。单次运行及不等长对照不能证明调度、observer负担、生产率或计数错误的因果关系；尚无可保持语义且有证据支持的guest最小修复。

**未知**：最后commit到停止之间id7/8是否完全不再增长，UP具体widget handler进入/返回，最后draw后timer累计终值，原150000逐条alloc/send/recv平衡，a18存量增加的业务/调度原因，以及任何未记录原调用。

**一个最小下一观察设计（仅提案，未实现/运行）**：保持同一原A/r3 guest、硬件型号、配置、原返回、5000ms和输入门；在宿主 `run_trial_v25_diag_r3.py:main()` 的**现有按键写入QMP暂停窗口**保存一次既有 `0x41dc00000` 64KiB双bank及ring header，结束时复用现有 `optional_paused_snapshots.capture()` 独立保存同两区。使用相同root、header publication/active、id5..11、gate_hist、a12和committed sequence作两点差分；只记host monotonic界定采集窗口，不将bank clock7混减ring clock1，不加额外暂停/重放或写guest计数。若复现无后续commit且Δid5/9/10/11>0、Δid7/8=0，才将本段定位为更新门前；若Δid8>0，则否定“这段完全没有更新机会”，下一轮才需要更新链内部/目标handler的更细观察。此任务不启动该观察；采样暂停自身的扰动也应记录，不能当无扰动因果试验。

## 复核与交付

执行 `PYTHONDONTWRITEBYTECODE=1 python3 analyze.py`：三环原始bin重新解析与既有diag JSON逐行相同，三bank依v11布局解析，22源及60份归档源码匹配，**138项登记输入分析前后SHA256一致**。未重跑历史tests。先用HTTP/截图/回执/原始串口独立分析；收尾时runtime worker的 `R12-INTERACTION-RESULT.md` 已出现并读取，语义失败、双bank、原生LF行号及43.821秒程序偏差均与本次解析一致，已列入输入哈希。

- [EVIDENCE.json](EVIDENCE.json)：可复核字段、全部留存ring rows、LF行号/偏移、两bank、版本比较及同钟差值。
- [analyze.py](analyze.py)：只读解析，所有写入限本目录，写前核UUID。
- [INPUT-SHA256SUMS](INPUT-SHA256SUMS)：138项输入哈希。
- [SHA256SUMS](SHA256SUMS)：交付文件哈希（不包含自身）。

R12三原件SHA256：serial=`1668510a6fc3fe00b921434ec0a7128611c71bfd5f2af926abb86ecced93c71f`；ring=`c58cedd911c57226a7fa922939b5329185ef89fcad33f3141d5657a55277463c`；bank=`71d5318d2444f491090e736a95463f0d83ed04ee93e83658382f9f377542635d`。本次离线定位完成；画面停更根因及修复仍未验证。
