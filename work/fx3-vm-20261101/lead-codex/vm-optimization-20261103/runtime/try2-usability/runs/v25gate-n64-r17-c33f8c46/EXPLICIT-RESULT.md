# 显式确认辅助复测：第一键观察截止，八步链 failed

2026-11-04。**只接受1个MENU，八步链failed；explicit_confirm_cli未调用，保持runtime未验证。** 首张6秒采样图进入Setup > Area/Date，但目标橙色选中条尚不完整，不能批准；第二次取图前原20秒闹钟已自动End。原始证据证明完整菜单稍后已经绘制和导出，本次失败不能归类为固件无响应。没有续键、延长闹钟、确认、重跑或部署，步骤2–8未执行。

## 身份和冻结范围

run `v25gate-n64-r17-c33f8c46`；URL `http://127.0.0.1:58463/`；单标签Chrome session `fx3-deadline-v25gate-n64-r17-c33f8c46`，1280×1200。runner PID88593/QEMU PID88745。网页launch_request_id **`7f817bca-60aa-4dfe-a6a0-022ddea71496`**，用于deadline绑定；与下述尾段host launch UUID不同。

- r17 SOURCE-FREEZE SHA `267ac6e3080511aecb4a7e8ae549d6d2f7140f6bb43eaeada9e204aa497473c0`，交付清单 `9cfe744df158c209b8cf02719b41fc56015e3fd6ffc82e293943c5c31ed91116`。32源/14固定输入启动前和结束后核验一致。
- 原N64 candidate `96666a719b1a4cf576e4d2d7ec461e10f5ce1143650450719e5273d75d970672`；CPIO `aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9`；原kernel/DTB/4核/5120MiB/MTTCG/noicount等保持。
- 新辅助SOURCE-FREEZE **`8c751f05ab82a94ee06c7c0154ba48967bc7909a6100fd1a77cc9f022c23285a`**，交付清单 **`b0f7d8e107ec5758227792bfb76d91ac33f8acfc640f83c044f8772fe6d4a49f`**；4源/3依赖/45交付核验，通过，未重复13项fixture测试。结束后4源/3依赖仍相同。
- 协调澄清文件SHA **`6e06006f886ef952a290f5e012946df975cd48b20003be88f09c5de9bb8e9a53`** 已读：前后shownSHA/gen相同、各自匹配当前有效frame；sequence允许同内容下单调递增，不把gen变化/ABA当作同一图。
- 原deadline固定20,000ms，PAGE canonical SHA `fe56b4846b9cb0c386216b38cc7e5b0707f616cab5ee6a526a217e68ce114478`。精确URL/网页launch/DOM/handler均通过原安装门。没有修改旧helper、PAGE、guest、平台、入口、README/ledger或旧failed记录。

唯一启动 `python3 -B run_trial_v25_diag_r3.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2`。实际上限8键；32只是runner参数最小值。卷UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、无占用、双锁free后启动；未涉及FX6/实机。

## 实际流程及每步结论

首次有效host导出帧相对Popen约39.8255s，浏览器首个带帧status为21:06:31.020Z；亲看待机图后安装deadline。第一键前在一个tool内依次完成：新nonce arm并核20000ms/due、一次真实MENU click、key202核验、约6s有界采样、before identity→截图→after identity，直接在同一tool结果展示截图。整个tool约6.2s，其中顺序宿主命令块6.036s。`OPERATOR-CAPTURE.py`只执行本次明确调用的1个键，不识图、不确认、不预置或循环8键。

| 步 | 目标 | 本轮结论 |
|---|---|---|
| 1 MENU | Setup > Area/Date，橙色焦点Area/Date/Time Setting | native down/up/done成功，完整目标后续已绘制；**未在deadline前亲看批准并确认/cancel，完整步骤failed** |
| 2 UP | Language / English | unexecuted / unknown |
| 3 C4 | Language帮助 | unexecuted / unknown |
| 4 MENU | 返回Language | unexecuted / unknown |
| 5 OK | 语言列表，English不变 | unexecuted / unknown |
| 6 MENU | 取消列表 | unexecuted / unknown |
| 7 MENU | 关闭待机 | unexecuted / unknown |
| 8 MENU | 重开完整菜单 | unexecuted / unknown |

step2前只读采集未触发（无第二键、无对应raw/receipt/QMP条目），不能称采集失败或精确普通RAM瞬时统计。第7→8历史确认/新gen分支、C4/OK等均未测。无409、无重试、未改变用户设置。

## 截止前后精确时间与身份

下表分列browser UTC、文件记录和host/guest单调域。HTTP时间是浏览器记录的请求时间附实际状态码；**mtime不冒充精确截屏或人眼/模型看见时刻**。

| 事件 | 记录 |
|---|---|
| Start | 21:05:50.818Z，HTTP202 |
| arm内部事件 | **21:06:51.059Z**，nonce **`203109c1-1a5f-42f9-9e16-76466de5c753`**；armed_ms63491.69999998808，due_ms83491.69999998808 |
| MENU HTTP | **21:06:51.082Z**，202；key427/0x1ab，observed_sequence203，accepted next_step1 |
| 首幅图before→after | **21:06:57.093Z..57.149Z**；seq212→212，shownSHA `e3be36326011c3ca84cd3d69283dd53ec5833efb775bc32ce574d4e2850257fd`，gen32，分别与当前有效frame匹配 |
| 首幅图保存 | 21:06:57.142711Z；Setup > Area/Date可见，目标橙色选中条尚未完整，未批准 |
| 完整焦点首个host导出 | **seq213，host_monotonic410103.939458875**；Popen相对67.519436..67.519605s；没有同点直接UTC，不回推精确墙钟显示时刻 |
| alarm / 原End.click | **21:07:11.061Z**；elapsed **20002.600ms**，state expired/sealed，原due不变，一次end_click |
| End HTTP | **21:07:11.120Z**，202；key→Stop **20.038s**，原30s合同内 |
| 第二图before→after | **21:07:16.308Z..16.457Z**；seq410→410，shownSHA `60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292`，gen33，分别匹配有效frame；PAGE已finished |
| 第二图保存 | **21:07:16.407794Z**，完整目标橙色焦点可见，但已晚于expiry约5.347s |
| final ACK | 21:07:14.119Z，HTTP200 |

两次截图均按before→screenshot→after顺序获取，并在同tool结果调用view_image展示；实际截图命令在相应before/after UTC之间。模型实际接收/亲看完成时间未独立打点，记unknown，不用文件mtime补造。两次网页截图保存相隔 **19.265083s**；第二取图tool约0.3s，其余空窗包含图像判断、编排/排队和工具往返，缺少逐段完整时钟，不能精确拆分，也不能全算固件绘制耗时。

第一图确实是稳定的部分内容（前后SHA/gen均相同），不是“身份不一致所以没看”；第二图gen从32变成33，必须重新亲看。第二对身份虽然也一致，但phase=finished，禁止确认。两对sequence都未在各自capture内前进，所以“同SHA/gen的sequence递增允许”分支没有在本轮实际触发。没有在截图后随意取新SHA冒充已审图，也没有调用explicit_confirm_cli的机会。

网页文件SHA与固件shownSHA严格分开：`page-01.png`文件SHA **`2ed45dd9758112af53e31762ac060707b39719beb13796e3a0095002e13c12bc`**；`page-01-observe2.png`文件SHA **`a38495afa6324d39e6ab3a1a88acf0b48cfbda6fd7806de8409ae78b3af3b1c2`**。其对应固件SHA分别为上表e3be…/60e9…，没有把网页文件SHA传给CLI。

## 原生绘制证据，不等同人工观察延迟

serial原行和byte offset在 `EXPLICIT-STEP-TIMELINE.json`：

- down `FX3_KEY_INPUT_RECV step=1 key=0x1ab status=1 ... native_result=0 clock_id=1 wait_return_ns=58668189008`。
- up同step/key status0、native_result0、clock1 wait_return_ns58892001008。
- `FX3_KEY95_STEP_DONE ... one_down_one_up=1 measured_down_up_ns=408537008 elapsed_ns=451680000 wait_result=0`。它不是目标画面完成证明。
- 完整焦点对应 `FX3_OSD102_COMMIT clock_id=1 ns=65477675008 ... frame=213 op=0x1003`；其像素与最终完整菜单相同，raw SHA `7161e977a5f37b5940702cde45272586f88973b2fb5d7df292323885590c0d52`、PNG SHA `60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292`。

同guest clock1，down→完整目标commit为 **6.809486s**，up→commit **6.585674s**；这些不是host墙钟或精确显示时延。部分画面frame212的host样本410102.163322875与完整frame213样本相隔 **1.776136s**，而再次截图晚了19.265s。可证固件/host在观察空窗内完成了完整目标，不能写成无响应；具体人工/模型判断完成UTC仍unknown，不混减clock1、clock7和host单调时钟。

## 确认辅助和停止合同的结论

**explicit_confirm_cli调用0次，confirm POST 0，confirmed_and_cancelled 0；新辅助runtime仍unknown/not_invoked。** 首图不满足语义目标，所以没有批准；等到完整目标重新被观察时原End已生效，不能越过终态。原deadline始终同nonce/同due，没有重装、延期、取消后续命或自动确认；唯一Stop来自原End按钮的deadline处理器。此次只实测了production 20秒到期保护，不能据此承诺挂起/阻塞情况下硬实时30秒。

## 原End读回、尾段与资源收尾

health/protocol/render/diagnostic/lifecycle均passed，host error/early stop为空，但**交互链仍failed**。总guest阶段82.767047s，guest keys1。原End暂停态完整16MiB ring SHA **`76d0ad788e390c97f4f4613334b411bb2a1f52a785ab19ed7c6fa75a0b7e1227`**；UI bank SHA **`f5bf8dc6075e9fd280c83ac796f3d1328e8b79fe73979ad37a29d2fbe983f4c6`**，原始serial/raw/PNG均保留。

原读回之后v5独立尾段为 **valid_nontransactional_tail_checkpoint**，两份976B一致，完整98Q/header/FNV **`0x5369f488`**独立通过，SHA **`092ccfdda00fa3d42cbae7b843cc47015b77e253572921be185846d1f1445021`**。host launch UUID **`8aa1d19c-484a-424e-a1f6-d85ac0c0f79f`**、tag`0xa29d44a6d3b2dc66`、snapshot nonce **`0xd8f5b19796d01e12`**、guest PID237/root`0x7ef8d96d60`，probe9/TID240；与网页launch/deadline nonce分别核对，不混用。attempted/acknowledged true，旧sent字段不存在；QMP暂停/cont ACK/再次暂停有原始回执。采集24.574ms，含停机两读27.011ms。

**snapshot_is_end_state=false**，非事务逐字段原子自然probe检查点，后续计数unknown；不证明按键前后事务一致、不补step2或性能结论，尾段不计启动/交互性能窗口。98Q完整字段和原End镜像分列在EXPLICIT-SNAPSHOT-INDEPENDENT.json。

API16保留原20s恢复合同，**1.575783s通过**；原16字节 `000b00b4fd7bbba9fd030091f35301a9` 与F100FILE/control0x100c1ea9/status0/seen1独立核对，host没有写原代码。QMP quit id318同idACK及SHUTDOWN，exit0/reaped、独立ps证明88593/88745消失，双锁exclusive探测free，网页finalACK HTTP200，helper dispose/sealed，专用浏览器close且active=false/pid=null。限定存储日志pre/run均25s上限内exit0无匹配，不称一般存储可靠性证明。

## 最小下一步建议（本任务不实施）

**先不再开VM。** 用本轮已存部分/完整PNG接入既有轻量PAGE fixture，演练实际操作员链“部分图判断→再次取图→亲看完整目标→一次显式确认CLI”，在每段入口/出口同时记host UTC与monotonic，保持原20秒及人工批准、不自动识图/确认。先证实整个操作链能在原due内留出余量，再另审真实轮次。现有13场景只证明CLI/PAGE合同，不覆盖这次多模态判断与工具编排的19秒空窗；在此缺口未定位前不重复同样的8步VM流程，不改生产PAGE、guest或deadline。

本轮原件/旧failed均未改；完整新增证据与原run冻结于 `EXPLICIT-SHA256SUMS`，校验 `EXPLICIT-HASH-CHECK.txt`。本任务完成封存后worker_done failed并停止，不开启其它VM。
