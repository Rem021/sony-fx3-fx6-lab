# r17/N64 唯一8步菜单链复测：failed

第1键MENU HTTP202并被原生接收后，冻结r2取图辅助误拒绝原runner合法的visual_pending中间态；没有合格截图返回、没有确认或cancel，下一工具立即点原End。本轮不重发、不修冻结件、不重开。**8步链未通过**：第1步语义未验收，2–8未执行/unknown；正常退出和诊断通过不代替交互验收。

## 身份、预检与边界

- 本轮run：v25gate-n64-r17-07c897a7；URL http://127.0.0.1:65218/；专属单标签session fx3-deadline-v25gate-n64-r17-07c897a7，1280×1200。runner491、QEMU1114；现均不存在，browser已关闭，端口无监听。
- 网页launch_request_id b3c3ba6f-9a29-4a88-8a27-0af0440bcbf6；host launch_uuid eb4042ff-c577-4fde-b61d-0cd589cd30bb。两种身份不混用。
- 卷UUID F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B；启动前无既有QEMU/runner，两既有锁可独占probe；32源/14输入及deadline36交付、bounded-r2 30交付、explicit45交付哈希全核。停止后再核固定输入/源码/辅助不变。
- r17 SOURCE-FREEZE267ac6e3080511aecb4a7e8ae549d6d2f7140f6bb43eaeada9e204aa497473c0；runner845a1f2d33a00d10ede293d5e397c88f7b0e387460ce1f890475b5b18a4006f8；N64 candidate96666a719b1a4cf576e4d2d7ec461e10f5ce1143650450719e5273d75d970672；CPIOaaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9。
- 原命令：run_trial_v25_diag_r3.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2。实际仅1键/1VM；固定cortex-a35、4核、5120MiB、TCG multi、无icount及原kernel/DTB/Backup，没有FX6/实机/USB/SD操作、设置写入或部署。
- 新操作脚本及8个独立nonce在Start前写入本run并AST检查。第1步调用原冻结r2 CLI；其返回非0时capture_validation确实拒绝展示，没有旧图/缺失图view错误。步骤2–8的只读逐图脚本未执行，没有硬传step1。原宿主源码和所有guest输入未改。

MENU8-PREFLIGHT / MENU8-VERIFICATION / MENU8-HELPERS-CLEANUP保存核验回执。预检限定日志15min查询exit0无匹配；本轮Start-5s至finalACK+5s窗口也exit0无匹配（MENU8-RUN-STORAGE），均不构成存储可靠性证明。

## 已执行的图像与步骤

首个host导出帧seq1：PNG2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e，Popen后39.857392–39.857603s；首帧原raw只保留hash元数据，不声称另有首帧独立raw文件。真实浏览器亲看待机于21:48:35工具结果：seq168、gen18、PNGe0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4，截图前后身份一致、ready，图像和End完整可见。最早浏览器显示首帧的精确时钟unknown；不能把该较晚待机截图时间冒充首帧时间。

| 步骤 | 请求/原生接收 | 目标语义与看图确认 |
|---|---|---|
|1 MENU→Setup Area/Date/Time焦点|HTTP202一次；down/up/done通过|取图helper失败；完整橙色焦点未获合格截图，目标unknown/未通过，0确认|
|2 UP→Language English|未发送|unknown/unexecuted；step2前快照未触发|
|3 C4语言帮助|未发送|unknown/unexecuted|
|4 MENU返回Language|未发送|unknown/unexecuted|
|5 OK只看English列表|未发送|unknown/unexecuted|
|6 MENU取消|未发送|unknown/unexecuted|
|7 MENU关闭待机|未发送|unknown/unexecuted|
|8 MENU重开菜单|未发送|unknown/unexecuted；跨7→8分支未测试|

原生证据见MENU8-STEP-RESULT：serial.log byte6068634为status1，wait_return_ns65853909008；byte6078913为status0，wait_return_ns65972243008，均clock_id1/native_result0；byte6079901为FX3_KEY95_STEP_DONE，one_down_one_up1、wait_result0、measured_down_up_ns110727008。它们证明原生接收对和发送者done，不证明完整下游菜单绘制。

runner后来将NO CARD闪烁造成的PNG2914→e014变化记为visual_changed（seq268、gen36），这是像素状态而非目标语义，未被agent确认。停止时原trial-final.png/浏览器frame seq269、gen37、PNG168a2787c26a0ec885b6ae816404991f6dcce5e770a0f904d66d6000229a265e；停止后独立查看仅见Setup > Area/Date基础文字，缺橙色Area/Date/Time Setting焦点和English值，不能算完整目标。其rawSHA ead80219131035911c7338b69f8102fe2158bb160df25cd82ec28c47a12b356c；不是尝试期间的合格目标截图。

## 明确定位：宿主取图对visual_pending误拒绝

原始捕图回执operator-step-01/capture/capture-result.json保留逐字段现场，轨迹为：

1. 21:48:45.547Z：steps0 / awaiting_step1 → accepted_menu_waiting_for_status。
2. 21:48:45.715Z：steps1 / status_busytrue / input_receivedfalse / review_requiredfalse → step_one_processing。
3. 21:48:46.131Z：steps1 / status_busytrue / **input_receivedtrue** / review_requiredfalse / review_stepnull / awaiting_step1，error与explicit_rejection均null、render_validtrue，仍余19332.7ms；抛step_one_without_expected_processing_or_review。

冻结interaction-bounded-capture-helper-r2/bounded_capture.js:70–72在!review_required分支把s.input_received为true直接判错；该JS SHA3af6a0f690783f6437ab200c56148eeb05f94af8751cea06afd2f321370e0540。原r17 runner:606–607却明确在visual_pending时设置input_received=True，且不会在此清busy或立刻建review，稍后:628才require_visual_review。故这一真实现场**有证据地定位为helper与原runner状态合同不匹配**。不是旧r1“尚未收到新status”的同一断点，也不是7/8秒PNG等待超时：页内仅584.600ms、capture函数599.650ms便拒绝，未尝试截图。

本任务不修改helper或原runner；没有补跑。已向协调端发msg_7aff5856e05b交接具体现场。仅能提出后续单独审查该合法busy+input_received+尚未review暂态，不扩大原8s/20s预算，不放宽错误/未知/终态门。本轮不能判断若继续等待固件是否会形成完整菜单，不能把宿主标记缺失当原调用未发生。

## 停止、nonce与时钟

UTC均2026-11-04；原始host monotonic和网页performance分别保留，未直接跨域相减。

| 边界 | UTC |
|---|---|
|真实网页Start HTTP202|21:47:38.159|
|待机图前后身份|21:48:35.263 /35.320|
|原alarm armed|21:48:45.464|
|MENU按钮click入口/返回|21:48:45.471817 /45.485289|
|MENU HTTP202网络回执时间|21:48:45.540|
|r2拒绝/CLI返回|21:48:46.131 /46.141457|
|下一工具原End，HTTP202网络回执|21:48:49.384|
|网页finalACK HTTP200|21:48:51.784|
|后备到期发现已finished，仅记状态|21:49:05.467|

nonce0ad6b10d-53b4-4945-a4dc-15c423fc3e46，armed_ms85900.69999998808、原due_ms105900.69999998808，始终不变；没有cancel/重arm/确认。End已先完成；后备elapsed20003ms只记already_stopping_or_disabled，没有第二次End click。dispose成功后关闭专属browser，activefalse/pidnull，网页端口已关闭。

Key HTTP202→End HTTP202为3.844s；同host monotonic的键click入口到End触发后QMP stop请求上界小于3.884s（MENU8-STOP-BOUNDS），满足原30s停止合同。没有精确测得浏览器End按钮事件时钟；HTTP网络元数据时间不伪装为精确click。timer并非硬实时保证。因为无合格目标图像返回，本轮模型接图/语义审完时钟和explicit确认入口均不存在/unknown。

## 收尾与独立raw验证

| 项目 | 结果 |
|---|---|
|health/protocol/render/diagnostic/lifecycle|全true；host_observer_error=null，early_stop_reason=null；不代表菜单语义|
|API16原20秒合同|1.314678s；原16字节000b00b4fd7bbba9fd030091f35301a9实读，SHA1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75；F100FILE/control0x100c1ea9/status0/seen1；host未写原代码|
|QMP/进程/锁|quit279同ID ACK及SHUTDOWN；exit0/reaped/PID491、1114 absent；两个锁独立probe free|
|网页|Stop202、finalACK200，trial-web-final-receipt acknowledgedtrue|
|原生关机/省电观察|native_shutdown_after_ready=false、native_model_power_off_after_ready=false；不声称观测到原生PowerOff|
|16MiB诊断环|SHA15b2fea5ecdb48d87948c672a9002feed7364436df6ea5e4ab0b72fe2648e820；QMP暂停完整读回，原parser独立重解析与自然JSON逐项相同，2148事件、0丢失、0坏槽；tail256不证明全部历史调用|
|原End UI bank|64KiB，SHA761728e0efc26189dab19da003cc4937c99820bd35496dbb5483036a4bb2fc98；真实activeoffset0x1100、98Q、publication_serial235|
|冻结源码/输入/辅助|32源/14输入和三helper全部前后不变；OPERATOR-SOURCE-FREEZE中的本轮4操作源亦未改|

v5诊断尾段单列，**不是End状态**：原读回后执行，snapshot_is_end_state=false；两份976B完全相同，SHA3024cbaa126470a53cd058e601917a855df0d3326b2460cbc24e77eed016d3bc。独立解析48I ACK头+784B/98Q，FNV32 c6a70c0a正确；PID237、root0x7ef249bd60、tag0xf21a7f586cd57067、nonce0xef916db75113addc绑定完整，probe9/TID240，selftest/bound1、object_mismatch/root_change0。尾段capture42.942ms、total45.592ms，guest clock1复制104000ns；不纳入启动性能。

实际cont251 ACK→query running252→stop253 ACK→paused254成立，attempted/acknowledged true，无旧qmp_cont_sent字段。尾段98Q id5..11=[2098,1816,282,270,2102,2068,2097]，原End active bank为[2098,1816,282,270,2080,2068,2097]；字段镜像并非事务一致，尾段有执行扰动，不将两者当同一瞬间，也不把id8=270说成零绘制机会。无step2区间快照，不能做UP停帧区间推断。

全部证据仅在本run；MENU8-verify.py独立检查通过，原始HTTP详情已脱敏token。MENU8-STEP-RESULT逐步标明failed/unknown，MENU8-TIMELINE和STOP-BOUNDS保留停止证据。最初保存预检JSON时一次字符串转义失败已在Start前改为直接写JSON，不涉及guest或重跑；不改变本次真实取图失败原因。只此一轮，未运行下一VM，后续须协调端按证据安排。
