# r29：首次出图超时只读定位

**已定位到浏览器之前的启动推进迟缓，以及原 UI 更新门的长时间积压；底层根因尚未确定。** r28 在原 180 秒窗口内确实没有合格待机，0 键，失败结论不变。首个已验证 ring 像素在 End 后的清理观察中才发布，`render_valid_at_end=true` 不能改写 `standby_ready=false / render_pass=false`。本任务仅分析已有证据，没有 VM、Start、浏览器、服务、部署、源码或平台变更。

别名：r28=`r28-vm-cb12b6256797 / f7903939`；r26=`r26-vm-49f0c1c3663b / 740bafa8`；r26b=`r26b-vm-93b3e243da6f / 45304842`。run 均位于 `TRY/runs/v25gate-n64-r17-*`。精确文件、LF 行、字节偏移和字段见 [TIMELINE.json](TIMELINE.json)、三份 `*-EVIDENCE.json`；相关代码摘录见 [CODE-EVIDENCE.json](CODE-EVIDENCE.json)。没有复制大日志。

## 首帧、ready 与 loaded 是不同边界

下表前两行采用各轮原 `FIRST-FRAME-CLOCK.start_monotonic`；不是 QMP journal 的 Popen 原点。host 像素时间是验证/转换/发布时的观察点，不是 guest 绘制或浏览器 compositor 的精确时刻。

| 边界 | r26 | r26b | r28 |
|---|---:|---:|---:|
| 首个 host 已验证非均匀像素（秒） | 38.979721 | 38.841301 | 180.544021，清理阶段 |
| operator 的合格首帧回执/超时（秒） | 44.173687，通过 | 44.088576，通过 | 180.322012，超时 |
| 首个 HAR `frame` 请求起点（UTC，11-05） | 02:37:51.076297 | 03:00:02.871369 | 03:51:01.602697，stopping |
| 首个 HAR `ready=true` 请求起点（UTC） | 02:37:55.986265 | 03:00:07.326180 | 从未出现 |
| 保存的 browser poll | loaded/ready 均 true | loaded/ready 均 true | 03:51:00.041559 起，均 false |

成功轮先有像素，再满足 host 待机条件，浏览器最终报告 loaded/ready。原 PAGE `showFrame` 必须 GET `/frame.png`、校验响应身份、等待 `image.onload` 后才写入 shown SHA/generation；`frameLoadedFor` 另外要求与 status 帧身份一致。HAR 的 GET 200 本身不证明解码完成；保存的 poll 只有最后一次结果，缺逐次 stdin/DOM onload 时间，无法精确还原首次 loaded。r28 首个 `/frame.png` GET 在 03:51:01.605373，已经停止；并非有可用帧而浏览器长期不加载。

r28 关键边界（host monotonic）：最后有效 seq0 header 为 **434346.478554125**；End 工具开始 **434346.606129583**，对应 Stop POST 请求起点 03:51:01.115732；final poll 看到 seq1 为 **434346.715256791**，首像素记录 **434346.781459375**，比 End 工具开始晚 **0.175329792 秒**。**两次 header 观测夹住 End，不能判定 guest 首 commit 究竟在 End 前还是后，更不能说 End 促成出图。** 该像素来自原 runner 清理阶段 `ring_reader.poll(final=True)`，而非启动循环合格捕获；同阶段 `phase=stopping/ready=false`。

原暂停诊断环只有 5 条事件、无 busy 丢失/坏槽，首 commit 为 `clock_id=1, guest_ns=173139872000`；serial 同次 `FX3_OSD102_COMMIT frame=1` 为 173139890000 ns，字节 **5038071 / LF47728**。serial 的 frame2/3 在 `serial_bytes_before_cleanup=5041741` 之后，是后续恢复/诊断尾段，不能当作原窗口状态。`TrialState.publish` 的 render_valid 只表示提交像素非全零；health 的 render 条件还要求 standby_observed，因此两个 receipt 字段并不矛盾，也不是可通过弱化判定修复的错误。

## 最早可证分叉与推进链

三轮实际 launch `command.json` 仅 run/cwd/serial 路径不同，模型环境一致；四核 cortex-a35、5120 MiB、MTTCG、无 icount。QEMU、kernel、DTB、N64 CPIO、candidate 的各轮运行前后 pin 全一致，当前字节再次匹配；原 runner/observer 的 26 项 source snapshot 也完全一致，见 [PLATFORM-AND-HELPER-BINDING.json](PLATFORM-AND-HELPER-BINDING.json)、[COMPARISON.json](COMPARISON.json)。r26/r26b 另有运行中 argv；r28 没有 live ps argv 快照，绑定依赖 runner launch record、紧接的 `Popen(args)` 代码、实际 QMP CPU 类型和输入 pin，不虚称有该快照。r28 没有 click/arm，新增按键后 5 秒采样逻辑尚未执行。

最早已记录的耗时差在握手：r28 QMP capabilities 阶段 **0.648559 秒**，对照 0.065057/0.121942 秒，均成功；首次 cont 的 Popen 相对请求时间 **0.953013 / 0.133257 / 0.191842 秒**。这不到一秒的差不能解释后续百余秒差距。**第一个带明确 guest 阶段身份的 host 延迟分叉已在 pre-AP**：原 Backup 加载窗口取证请求为 Popen+**16.794286 秒**，对照 **6.668259 / 6.777827 秒**；三轮原文件/加载/pre-AP gate 均通过。该观测仅给出阶段到达/取证边界，不能还原每条 guest 日志的精确 host 发出时间。

| 原 guest/UI 事件 | r26 | r26b | r28 |
|---|---:|---:|---:|
| 首屏 open 0x2ae，clock_id1 秒 | 27.604531 | 27.156464 | 83.836416 |
| open screen0，clock_id1 秒 | 33.104345 | 32.329151 | 116.120070 |
| 首 timer 的原 input_time（毫秒） | 36228 | 35951 | 172015 |
| 首 OSD serial commit，clock_id1 秒 | 37.596067 | 37.361997 | 173.139890 |

timer input_time 保留原应用时域；不与相邻 printk `[timestamp]`、host monotonic 或文件 mtime 混算。r28 首 timer 位于 **4915799 / LF45907**；紧接 ID/info 都通过、首原 Fill 为 **4917965 / LF45921**，然后才有首 OSD commit。对应成功轮首 timer/Fill/commit 偏移也在结构化时间线。r28 首 UI_WIRE tag1=`0x21004`，低16位为 0x1004，**不能误判无 timer 消息或高位即损坏**。

原 UI `appFw+0x16f247c` 的 signed `counter<=2` / byte+a12 条件进入时限/更新路径；`+0x16f2640` 随后调用原 update，才可能进入 timer/绘制。r28 原 End 暂停时 N64 已发布计数为 gate4495、backlog_skip4493、time_pass2、peak_gate1947、gate>100 共4321次、a12/a13非零0、object_mismatch/root_change0。对照 peak257/254、time_pass440/645；**对照计数包含后续一键，不能当作同长启动窗口的速度比较**。N64 发布银行可能滞后，publication interval=64 也不提供精确终态新鲜度保证；逐字段复制不是事务快照。它仍支持“本轮原更新门大量被 backlog 条件跳过、低水位时才出现两次更新”的具体路径，不能证明积压的生产/消费平衡或起因。

协调端补证已并入并独立复算：r28 **397** 次 header 请求均按 id 匹配空成功返回，中位请求间隔 **0.4349535 秒**、最大 **1.84494975 秒**；不支持宿主长期停止轮询。reader 在长度/MAGIC/version 拒绝时不保存 polls，而早期 header 文件被覆盖，故 **397 次请求≠397 次有效 header**，亦非单调用耗时。End POST 前配对 QMP STOP/RESUME 显式暂停共 **3.224597 秒**；这项加总不能解释百秒差，仍不能排除间接 timer/队列影响、初始-S、调度停滞或 realtime 跳变。

## 能排除什么，仍缺什么

证据支持 guest 原 UI/timer/已提交软件 ring 生产链迟到，并非仅浏览器加载或 host ready 门误拒绝；尚不能证明 guest 之前所有私有/offscreen 像素都不存在。startup 未有 `current_record` 已足以让原 standby 门保持关闭；原门还要求原 Backup 验证、屏幕 open 后 host 观察安静10秒、媒体分支/notify/free/key-ready/正文及非均匀帧，不能从最终 serial marker 集倒推这些条件在早期某瞬间同时成立。当前没有可立即修复且已证因果的单行错误，不能将“放宽 ready/180秒、改 FX3 配置、重复 Start”作为修复。

**最小下一步是先离线准备宿主启动观测候选，再由协调员决定统一运行。** 复用现有 header 读取和 serial poll，在每次已有读取完成时保留有界状态转移回执：请求id、host mono 前后、文件长度、原16Q/拒绝原因、serial 已消费 offset；记录首次命中 marker 的 offset+host收到时刻，以及原 standby 各谓词的命名结果和最后 screen 观察时刻。保留 invalid→valid、seq0→positive 和 stop 前后独立边界，避免无效 header 令诊断一并消失；不添加 guest 写入/暂停、按键、额外 QMP 轮询或改变任何等待。用现存无效/有效 header 与 A/B 成功失败日志离线回放验证日志不参与准入、不会把清理帧升级为 ready。它可区分“guest 软件 ring 尚未初始化/发布”“读取无效”“host 资格谓词阻塞”，但还不足解释 backlog 起因；若仍需要队列因果，再单独设计同一 root 的累计生产/消费/更新时序观测并评估开销，不能以 Futex/线程忙状态猜死锁。

## 交付与复核边界

`analyze_startup.py` 只读原件、校验平台/来源并写本新目录；`make_timeline.py` 生成简明时间线。`INPUTS.json` 记录所有消费原文件的完整 SHA/大小及分析结束回核，`VERIFY.json` 和 `SHA256SUMS` 给出复核结果。当前 r28 操作代理封存仍独立处理，本报告仅固定读取过的命名原件，不宣称核过其最终全目录清单。离线分析完成；底层根因、原生菜单完整可用性及下一轮真实验收仍未完成。
