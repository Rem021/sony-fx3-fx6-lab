# r3取图辅助真实r17/N64八步复测：failed

唯一run bdd09f6b在第1次MENU**浏览器点击**时得到明确HTTP409（画面已变化或不可用），原TrialState在入队前拒绝，**实际接受固件键0、原生down/up/done均0、confirm/cancel均0**。r3正确以explicit_key_rejection停止，包装器非0且没有展示旧图或不存在图。下一工具立即原End，无补键、重跑、VM重启或改源。八步链failed；这次未执行r3的原生ACK等待态，不能把409重写成其误拒或固件MENU故障。

## 身份和预检

run：v25gate-n64-r17-bdd09f6b；URL http://127.0.0.1:51504/；专属唯一session fx3-deadline-v25gate-n64-r17-bdd09f6b、1280×1200。runner6654、QEMU7008，现均absent；HTTP端口无监听，browser activefalse/pidnull。网页launch_request_id ea487f43-7c0a-47cd-bb5e-7c0963a819f3；host launch_uuid 0ee933fb-ace2-40f9-9ec3-e4093c38316a。

启动前后卷UUID F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B正确；启动前无既有runner/QEMU，两既有锁probe free，32份r17源码/14输入固定SHA全核，停止后再核一致。原cortex-a35/4核/5120MiB/MTTCG/noicount/kernel/DTB/Backup/N64固定槽CPIO不变；无FX6、实机、USB/SD、设置提交或部署。原命令：run_trial_v25_diag_r3.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2。实际仅1VM/0接受键。

r17 SOURCE-FREEZE267ac6e3080511aecb4a7e8ae549d6d2f7140f6bb43eaeada9e204aa497473c0；runner845a1f2d33a00d10ede293d5e397c88f7b0e387460ce1f890475b5b18a4006f8；candidate96666a719b1a4cf576e4d2d7ec461e10f5ce1143650450719e5273d75d970672；CPIOaaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9。

r3 SOURCE-FREEZE07dbabe08d891d100ffcaaf8c9c75e0b7051ba304c54aa98b30e777ece9e8a6e，manifest9506d6a4da24fa6dfee6ef4b52280c4d2f8cb69544239e7bd20b076f3921fc14，JS1c0597091002bef06dcf53e918653b1ad4444b1db38c1f4defa0bf7e562d2879；36交付/13依赖匹配，原explicit45、deadline36交付也前后匹配。按本任务协调判断复用已通过的人工模拟链，不重复未变fixture。所有新操作源/nonce/参数在真实Start前写本run，沿用07c897a7已审脚本，**只改第1键helper路径r2→r3**；capture_validation三门及真实PNG文件/hash门保留，步骤2–8只读捕图代码未执行。旧139项failed不改。

## 步骤结果

|步|计划目标|实际HTTP/固件输入|语义与确认|
|---|---|---|---|
|1 MENU|完整Setup > Area/Date、橙色Area/Date/Time Setting|一次浏览器点击/一次POST409；未入队，0native|目标unknown/not_executed；无合格截图、无confirm|
|2 UP|Language English|未发送|unknown/unexecuted；step2前快照未触发|
|3 C4|语言帮助|未发送|unknown/unexecuted|
|4 MENU|返回Language|未发送|unknown/unexecuted|
|5 OK|只看English语言列表|未发送|unknown/unexecuted|
|6 MENU|取消|未发送|unknown/unexecuted|
|7 MENU|关闭到待机|未发送|unknown/unexecuted|
|8 MENU|重开完整菜单|未发送|unknown/unexecuted；跨7→8分支未测|

首个host导出帧Popen后39.208860–39.209095s，满足180s首帧门；最早浏览器显示首帧的精确UTC未捕获，不用较晚截图冒充。实际亲看待机于22:02:02.619Z记录，seq106/gen16、PNG2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e，前后SHA/gen相同且ready，End完整可见（standby-page.png）。

## 409竞争：已保全与仍未知

原HTTP详情MENU8-HTTP-key.json：POST body精确为{“key”:427,“observed_sequence”:212}，HTTP409 body为“当前画面已变化或不可用，请等待并查看最新画面。”；网络记录UTC22:02:10.158。原PAGE/TrialState.submit:101–105的render_valid/frame/SHA/content_generation复合门返回该错误，早于pending.append和busy写入（:111–115）。receipt.key_steps0、无step_captures、serial原生RECV/DONE计数0交叉证明未入队；不是未知送达。

既存导出元数据（MENU8-409-EVIDENCE.json / osd-ring-readback.json）：

|本机host monotonic|已存事实|
|---|---|
|413414.669167833|seq209，PNG291427…（NO CARD待机）|
|413415.143619833|请求引用seq212，PNGe0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4；raw b10896e7772ab4eb12f434e8c8035ab19d41ffc4451acbe9c0ef9e0052e03051|
|413415.672432791|下一导出seq221，PNG291427…，内容与212不同|
|413415.692086000|本次真实MENU按钮click入口|
|413415.702638875|click调用返回|
|413415.763222166|r3 before_eval工具入口|
|413415.771106750|capture函数结束，明确拒绝|
|413416.200248916|后续导出seq230，PNGe0140e…|

seq221的不同图导出在click入口前约19.653ms；页面却提交212。这与页面/服务器画面身份竞争一致，**但导出时钟不是TrialState.publish或HTTP handler的直接采样**。没有保存请求瞬间server.current_frame、frames[212]的content_generation或复合门每个布尔值；不指定唯一失效项或确切拒绝current帧/gen。相邻status只保存网络元数据，responseBody未留存，均明确unknown；没有再打开已关闭session补取或操作恢复。

拒绝后22:02:10.226Z原helper诊断直接记录：steps0、phase ready、input_receivedfalse、status_busyfalse、host_busyfalse、awaiting_stepnull、review_requiredfalse、review_stepnull、delivery_unknownfalse、errornull、render_validtrue、explicit_rejection.kind=key且含完整409文本；lastStatus/frame/displayed均seq212、gen27、PNGe0140e…，余19914.2ms。这里的gen27是**拒绝后PAGE最近status所见**，不是捏造的请求瞬间server历史gen。r3页内0.600ms即正确拒绝，capture宿主15.168ms、未尝试截图；没有进入ACK等待或参考PNG等待。

协调端msg_94e6d7c0454f额外要求的可见性边界：

- 内部明确拒绝状态及真实HTTP409已覆盖。
- **持续拒绝提示的可见截图未覆盖**：失败后按合同先End，没有拒绝期间的屏幕截图或操作员亲看提示证据；不把expected的PAGE源码分支等同浏览器实际绘制验收。
- **刷新后按钮ready/解锁未覆盖**：未采key.disabled或status.ready，phase ready不等同七键enabled；没有恢复/重试操作。End后snapshot所有按钮disabled只证明终态，不能代替拒绝恢复分支。
- 原始字段、请求和近邻帧、status metadata均保存在MENU8-409-EVIDENCE.json，交给协调端独立只读分析；未虚构缺失瞬间证据。

## 停止时限与时钟

UTC均2026-11-04，原HTTP元数据、host monotonic和网页performance分列，不跨原点相减。

|边界|UTC|
|---|---|
|真实网页Start HTTP202|22:01:10.670|
|待机截图前/后|22:02:02.619 /22:02:02.668|
|原20s alarm armed|22:02:10.140|
|MENU click入口/返回|22:02:10.148500 /10.159050|
|HTTP409网络记录|22:02:10.158|
|r3拒绝/外层CLI返回|22:02:10.226 /10.234602|
|下一工具原End HTTP202|22:02:14.674|
|网页finalACK HTTP200|22:02:17.575|
|后备到期发现已finished|22:02:30.144|

nonce1a61a99c-1610-46dd-b5c8-e81b0a3247d5，armed_ms85937.5、due_ms105937.5不变，没有cancel或重新武装。原alarm到期elapsed20003.6ms只记录already_stopping_or_disabled，0自动End click，无终态逆转。409记录至End记录4.516s；同host键click入口到End后的QMPstop请求上界4.500s，满足30秒停止合同。End按钮自身事件没有独立采样，不把HTTP元数据当精确click时间。浏览器timer仍非硬实时保证。无目标图像返回，模型接图/语义审完时间及确认CLI入口不存在/unknown。

## 收尾与raw独立核验

health/protocol/render/diagnostic/lifecycle均true；host error/early_stop null。API16原20s合同1.549229s完成，原16字节000b00b4fd7bbba9fd030091f35301a9实读，SHA1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75；F100FILE/control0x100c1ea9/status0/seen1，host未写原代码。QMP quit257同ID ACK/SHUTDOWN、exit0/reap，runner6654/QEMU7008独立ps absent，两个锁独立probe free；Stop202和finalACK200匹配，浏览器关闭/端口无监听。原生shutdown/power-off after ready均false，不声称观测到原生关机。

16MiB原暂停诊断环SHA9dc7533b57e10d6896ff55d0eba8706ee9c8398d14cd7c7e9191371c2b59497a；原parser停止后重新解析与自然JSON逐项一致，2116事件、0丢失、0坏槽。原End UI bank64KiB SHA b5140b318d7d00ee435a62633b9256e50ead22400ffb87e5ea6a14785a64f51f，active bank按真实0x100+bank*0x1000解析98Q，publication_serial199。尾256记录并非完整调用史，缺标记不作没有调用的证明。

v5尾段单独列：valid_nontransactional_tail_checkpoint，snapshot_is_end_statefalse，两次976B完全一致，SHA3eb9d20c96e9c2e610f090a1c2e5f890641bca077733452461ff00a35099f7e6；独立48I ACK+784B/98Q/FNV f8503155通过，host tag0xb4cfb25ebdb98126、nonce0xb174563fabdad67b、PID237/root0x7efe37cd60、probe9/TID240绑定。selftest/bound通过，object_mismatch/root_change0。尾段capture23.3985ms、total26.0763ms，guest clock1复制53008ns，不计启动性能；attempted/acknowledged true、实际cont/running/stop/paused各ID匹配，无旧qmp_cont_sent字段。原End bank和尾段字段镜像非事务一致、不当作同一瞬间，不做跨clock1/clock7/host差值。step2没有执行，前输入快照未触发，无UP区间结论。

预检15分钟与本轮限定存储窗口均exit0无匹配、无timeout，不作为通用存储可靠性证明。MENU8-verify.py和MENU8-HELPERS-CLEANUP确认32源/14输入、三辅助及本轮操作源不变。最终只有一次浏览器key POST409、0成功key、0confirm，0第二轮；明确failed交付证据，不把正常cleanup改写为八步通过。
