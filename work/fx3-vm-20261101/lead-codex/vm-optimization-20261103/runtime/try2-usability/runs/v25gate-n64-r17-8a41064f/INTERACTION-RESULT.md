# N64 八步交互唯一轮：第1步操作确认截止，整体 failed

2026-11-04。**八步指定链未通过：只接受1个MENU，原生菜单与预期焦点实际出现，但操作者未在20秒内完成宿主确认/ready/cancel，deadline自动End。** 这是操作执行链超时，不能写成固件无响应或菜单打不开；正常收尾也不等于交互通过。步骤2–8未执行，没有重跑、续键、重武装、自动确认或改变任何设置。先前N1/N64零键通过结论各自独立封存，未改。

## 本轮身份、授权与冻结

run **v25gate-n64-r17-8a41064f**；实际URL `http://127.0.0.1:55240/`；专用单标签Chrome session `fx3-deadline-v25gate-n64-r17-8a41064f`，1280×1200。runner PID83582/QEMU PID83750。网页launch_request_id **`9cdf9222-7feb-4d41-9bc0-0a6376311571`**，helper绑定此网页身份，而非host snapshot UUID。

沿用冻结r17：SOURCE-FREEZE SHA `267ac6e3080511aecb4a7e8ae549d6d2f7140f6bb43eaeada9e204aa497473c0`，交付清单 `9cfe744df158c209b8cf02719b41fc56015e3fd6ffc82e293943c5c31ed91116`；N64 candidate `96666a719b1a4cf576e4d2d7ec461e10f5ce1143650450719e5273d75d970672`，CPIO `aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9`。原DTB/kernel/4核/5120MiB/MTTCG/noicount等平台保持，command.json保留实际VM参数。

唯一调用：`python3 -B run_trial_v25_diag_r3.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2`。实际授权最多8键；32仅runner最小参数，不是本轮验收数量。

写前核卷UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，双锁free、无既有VM/runner；32源/14固定输入与deadline冻结36项hash核对通过，未重复离线测试。结束后32源和14固定输入独立重算一致。没有修改guest、host冻结源、平台、入口、README/ledger或部署，没有FX6/实机操作。

deadline SHA256SUMS固定为 `8d95b85bf5666ebd0bd898ec95c670e673fe5eb732852766dff3f82d8f53fbdc`。安装核精确带斜线URL、单标签、launch_request_id、DOM/原End处理器，PAGE canonical SHA **`fe56b4846b9cb0c386216b38cc7e5b0707f616cab5ee6a526a217e68ce114478`**。production deadline_ms=20000，未用短测试版本；armed期间未滚动、缩放、导航或更换viewport。

## 每步结论

| 步 | 键与语义目标 | 语义证据 | 完整操作结论 |
|---|---|---|---|
| 1 | MENU → Setup > Area/Date，焦点Area/Date/Time Setting | **passed**：第二张完整截图亲看，原生full菜单像素及commit有证据 | **failed**：未完成手动确认/ready/cancel，20s到期End |
| 2 | UP → Language / English | unknown，未执行 | unexecuted |
| 3 | C4 → Language帮助 | unknown，未执行 | unexecuted |
| 4 | MENU → Language条目 | unknown，未执行 | unexecuted |
| 5 | OK → 语言列表且保留English | unknown，未执行 | unexecuted |
| 6 | MENU取消列表 | unknown，未执行 | unexecuted |
| 7 | MENU关闭待机 | unknown，未执行 | unexecuted |
| 8 | MENU重开完整菜单 | unknown，未执行 | unexecuted |

因此r12第7→8跨帧确认修复路径 **未触发/未实测**；step2 pre-input采集也 **未触发**（没有第二个key请求，文件及QMP记录均无），不能把开关静态存在当成已采集，更不能把N64旧镜像叫精确普通RAM瞬时状态。本轮无409或重试。

## 第1步20秒截止因果时间线

所有UTC为本轮浏览器或文件系统记录，未知时间明确留空。**截图mtime只是保存完成记录，不是精确原生显示时刻。**

| 事件 | 记录 |
|---|---|
| Start请求 | 20:44:26.775Z，HTTP202 |
| helper安装 | 20:45:25.396Z，固定20,000ms，无活动alarm |
| arm内部事件 | **20:45:41.901Z**，nonce `9223f9ce-16c2-49f8-87df-451ce928edc7` |
| arm保存 | 20:45:41.903096Z；current armed_ms=78273.90000003576，due_ms=98273.90000003576；外部调用开始/CLI返回未另加钟，不冒称mtime为返回时间 |
| MENU请求 | **20:45:42.102Z**，HTTP202，key0x1ab/427，observed_sequence337，accepted next_step1 |
| 首次观察图 | 20:45:43.742998Z保存，seq344仍是待机/NO CARD；没有误确认任意像素变化 |
| 第二次完整目标图 | **20:45:54.109556Z**保存；Setup > Area/Date 45/59，橙色焦点Area/Date/Time Setting |
| 亲看完成 | 实际view_image后作出目标成立判断，但没有独立精确UTC打点 |
| 首次手动确认尝试 | view_image后的下一次明确UI动作；返回 `Element @e9 is disabled`，未送HTTP；没有精确调用UTC，不能从其它mtime补造 |
| expiry / 原End.click | **20:46:01.903Z**，elapsed_ms=**20002**，唯一end_click，state expired/sealed |
| Stop请求 | **20:46:02.002Z**，HTTP202，一次；MENU请求→Stop **19.900s**，原30s要求内 |
| 随后人工End尝试 | 在ready短等超时后返回 `Element @e11 is disabled`，无第二次Stop请求；原自动End已生效 |
| final ACK | 20:46:04.802Z，HTTP200 |

首/次截图保存相隔10.366558s；完整目标图保存到expiry还有**7.793444s**。我未在这段余量内完成确认，是本轮操作执行失败。工具回执能区分的部分：首组arm/点击/等待/截图/view合计约2.0s，其中等待review_required约1.413s；第二截图/view工具组约0.1s；之后ready等待上限2s。它们不是完整agent判断/排队/浏览器耗时打点，无法把余下空窗精确分摊，也不能全归因于浏览器或固件。

## 固件响应与像素证据（区别于操作超时）

原serial精确行及byte offset保存在 `INTERACTION-STEP1.json`：

- native down：`FX3_KEY_INPUT_RECV step=1 key=0x1ab status=1 ... native_result=0 clock_id=1 ... wait_return_ns=73951626000`。
- native up：同step/key status0，native_result0，clock1 wait_return_ns=74089716000。
- sender done：`FX3_KEY95_STEP_DONE ... one_down_one_up=1 ... measured_down_up_ns=142434000 elapsed_ns=175871008 wait_result=0`。它不等于语义绘制完成。
- 完整菜单对应commit：`FX3_OSD102_COMMIT clock_id=1 ns=78511861008 ... frame=347 op=0x1003`；与最终完整菜单相同raw/PNG身份的首份host导出也为seq347，host_monotonic=408832.709770041。

同guest clock1：down→该commit **4.560235008s**，up→commit **4.422145008s**。不能把guest clock1差当成精确host墙钟/显示延迟。pre-key被审阅seq337的host_monotonic=408827.254755958，与完整目标host样本间隔5.455014083s；这是同域观测区间，不是精确按键或原生显示时延。它和完整目标截图共同证明菜单实际已到达，不能用本轮“整体failed”推断固件无响应。

完整菜单raw SHA **`7161e977a5f37b5940702cde45272586f88973b2fb5d7df292323885590c0d52`**，原生PNG **`60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292`**；第二张网页目标PNG SHA **`67fcb019b2ca84a61950fffb936c0b80050b110e76fb41d77426ca921d75f4d0`**。源数据/截图均保留，没有图像编辑。

HTTP只1个key202，0个confirm，1个stop202。最终server steps1/review_step1/review_required=true/review_confirmation=null；final frame seq578、content_generation54。按键时generation没有写入key POST，未另采，明确unknown；不能倒填成final54。未产生成功确认nonce/HTTP200、未解除该alarm；deadline nonce与服务端review identity严格区分。runner原visual_changed记录的是seq337→344待机像素差，**没有把它当完整MENU目标**。

## 独立末尾诊断与清理

health/protocol/render/diagnostic/lifecycle全部passed，host error/early stop为空。总guest阶段97.726398s；菜单语义发生但本链仍failed。API16原20秒恢复 **1.550614s**通过，原16字节 `000b00b4fd7bbba9fd030091f35301a9` 与F100FILE/header control0x100c1ea9/status0/seen1独立核对，host没有写原代码。QMP quit id390同idACK及SHUTDOWN，exit0/reaped/PID absent，独立ps与双锁free通过，网页finalACK通过。helper dispose后sealed，专用浏览器close、active=false/pid=null，无后台残留。

原End完整OSD/ring/UI bank/raw/serial独立保留并核hash。原读回之后v5尾段 **valid_nontransactional_tail_checkpoint**，两份976B逐字节相同，SHA **`6336f82c2ad821c651c81be0b314fa61680138a9d50df804d9fb2af091c5af6d`**；独立98Q/header/FNV **`0x312c3195`**、身份与nonce通过。host launch UUID **`79f090d5-d408-44af-97c1-6cdf62683d7b`**、tag`0xe471404985332ff4`、snapshot nonce **`0x72799e1b73e84ba5`**、guest PID237/root`0x7ed5c4ed60`；与deadline nonce无关。r17 attempted/acknowledged true、旧sent字段不存在，实际cont/暂停证明吻合。

**末尾snapshot_is_end_state=false**，非事务逐原子字段的自然probe检查点；不证明按键前后事务一致、不补证步骤2，也不计启动/交互性能窗口。完整98Q及原End镜像分列于 `INTERACTION-SNAPSHOT-INDEPENDENT.json`，运行/恢复/锁/源和14输入hash详见 `INTERACTION-VERIFICATION.json`。

pre-run及run限定kernel USB/APFS查询均25s上限内exit0无匹配，不能泛称存储可靠。helper实际20秒到期仅比due晚约2ms并有效End，**这是本次实测，不是系统挂起/浏览器阻塞情况下的硬实时承诺**。

## 交付状态

执行流程截止保护passed，原生MENU语义passed，宿主确认/cancel failed，8步链failed；步骤2–8、step2 pre-input、第7→8分支unknown/unexecuted。没有保存设置值或测试其他菜单。HTTP与关键字段已脱敏保存；原始运行、nonce、步骤/工具动作、截图、timeline、原字恢复和清理证据全部冻结在 `INTERACTION-SHA256SUMS`，校验回执 `INTERACTION-HASH-CHECK.txt`。本阶段到此结束，不开下一轮、不部署。
