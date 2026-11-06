# FX3 v25 OSD/MENU 停帧离线诊断候选

**结论：已修正一个可复现的观察归属错误，尚未证明第 12 键 MENU 未关闭弹窗的 guest 根因。** v24 的 `FX3_OSD_DRAW_WAIT_RETURN frame=N` 在原 wait 返回后读取全局 `hm.seq`，这不能标识进入 wait 时的帧；期间若有新提交，旧日志会把返回归到较新的帧。v25-r2 在 wait 入口冻结当前 committed seq、source seq、epoch、token、信号量与 guest `CLOCK_MONOTONIC`，在返回时引用同一次入口记录。另记录 1003/1005 控制消息发送入口/返回、原生接收、环提交、信号入口/返回；固定 256 条记录，不在每次原生调用前写串口。未加入虚构 MENU handler 探针。

## v24 第 12 键已知边界

- 原生 `libObj.so` SHA256 `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae`，精确指令与文件偏移见 `original-elf-audit.json`。`0xf2220` 从对象 `+0x48` 取绘制信号量，`0xf2224` 调用 `0xfd344`；`0xfd354` 调原 `osal_wai_sem_tmo`。`6005` 分支 `0xf22c8` 同样从对象 `+0x48` 取值，`0xf22cc` 调 `0xfd384`，`0xfd390` 调原 `osal_sig_sem`。当前 helper 观察到的 sem 为 `0x2886049`，frame5739 的 signal `result=0 matched=1`。
- v24 最后一条 `OSD102_COMMIT` 为 frame5739、`op=0x1005`、`pixel_source_seq=5532`、guest `clock_id=1 ns=530923844000`，早于第 12 MENU down 接收 `531132451008` 与 up 接收 `531337516000`。最后一个旧 `DRAW_WAIT_RETURN` 日志标 frame5738。frame5739 的 `HEADLESS_ACK`、`NATIVE_FREE result=0` 和 `NATIVE_SIGNAL result=0 matched=1` 存在；但旧 wait 日志**没有入口时间与调用 ID**，无法判断 frame5739 后是否进入或停在 wait。第 12 键后无新 `0x1003`/环提交，浏览器弹窗持续显示 5 Min。
- 当前 `ho_signal_begin` 在原 `hsignal` 前更新软件匹配阶段，`ack_freed` 在原 free 成功后置位。v24 对 frame5739 记录了 free 与 signal 成功，没有已证的信号量 ID/epoch 错配、失败返回或软件锁死。提前软件阶段提交有潜在时序竞争，但缺少失败对应实测，**本候选未改变其逻辑或返回值**。`FX3_KEY_INPUT_RECV` 与 `KEY95_STEP_DONE` 仅证明队列接收和一次 down/up，不证明菜单 handler 运行。
- 原 `appFw.so` SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`；字符串存在 `UIBIZ_KEY_TACT_MENU`、`input_status_key_tact_menu` 等名称，但原 ELF stripped，这些字符串不能唯一指向处理函数入口/返回。当前无可审计 MENU handler 地址、原字与调用约定，因此保留 `menu_handler_offset=null`，没有添加 BL 探针。

## 实际代码、差异与身份

- 最终源码：`src/fx3-osd-headless-v25-r2.c`，SHA256 `dcdaea207d7187e1d2798876d7f432fab0b149fc07da2436c5c8ed527dca0597`；完整与前版差异 `src/fx3-osd-v4-to-v25-r2.diff`。SO：`build/fx3-osd-headless-v25-r2.so`，SHA256 `5b9632aa641e6df2d931850944c26d8ceb233cc93617d987b3182fbb7bbbca7c`。原 `hwait(id,timeout)`、`hsignal(id)`、`ho_signal_begin`、返回值及错误门保留；新增日志函数保存/恢复 errno，避免观测影响原生错误状态。没有新动态未定义依赖。
- 最终候选：`vmopt-20261104-v25-menu-osd-diagnostic-r2/candidate.json`，SHA256 `c1467c2673b700b1988335694bcbf67dfb03c90c9acf486bc2b61c4b04867795`；CPIO SHA256 `962a8b338ebe42034b3102d6419bf4b0240a0407d21ac85f218d0fc4c58473ad`；DTB SHA256 `ac6070683b9b12df5baaa0821fc7a0f4a05e53d7cace067f2c5738c06c4ca1d1`。以 v24 FX3 候选 SHA256 `90adc5fd...` 为基；1140 个 CPIO 成员中仅 `simulation/fx3-osd-headless-v5.so` 从 SHA256 `8023300a...`、99232 B 变为上述 SO、108144 B，模式/次序/其余 payload 一致。DTB 仅 `linux,initrd-end` 从 `0x45b035894` 更新至 `0x45b037b64`；固定 English gen4 Backup SHA256 `92fe4031...` 未变。`build_v25_candidate_r2.py` 用 SHA guard 派生，`build-receipt.json` 可核。
- 同目录初版 `vmopt-20261104-v25-menu-osd-diagnostic/` 是**未使用的离线历史件**。编译复核时发现诊断 syscall 应恢复 errno，于是保留初版而另生 r2；`src/v25-r1-to-r2.diff` 精确显示这两处保存/恢复。只有 r2 列为下一轮待审候选。
- 诊断缓冲使用已有 `osd-ring` 的 `0x2000..0x8040` 头部空白，256 条 × 96 B，serial 原子递增；每条有提交帧快照、source seq、tid、原生 sem/队列、op、结果、epoch、token、关联 ID。`parse_v25_diag.py` 验证 header、槽 serial、入口/返回 TID 并标记截断或尾部缺入口。环覆盖历史时只解读保留窗口，绝不推断被覆盖事件。原像素槽从 `0x10000` 开始，未挪动。

## 宿主验证与下一轮最小观察

`verification-r2.json`：原 ELF 十个指令 guard 通过；原生 wait/signal 调用及失败门源码比对通过；SO 新未定义依赖为零；CPIO/DTB/seed/candidate SHA 回读通过；解析 fixture 覆盖入口/返回配对、期间新提交、256 槽回绕、未配对 wait、半写槽与截断。以上仅为**宿主/静态**证据，`guest_runtime_validated=false`，没有启动 QEMU、触碰 FX6 冻结平台、原件、旧候选、默认入口或原生 5 秒门。

下一轮由协调端排唯一 FX3 窗口后，以 r2 候选和独立 runner 手工逐键：预检 UUID/双锁/进程/源 SHA，真实浏览器 Start、待机图、MENU、左右与类别导航，只有每张完整 PNG 经人看图确认才继续；如自然走到省电弹窗，ENTER 原值只读后单次 MENU，若无关闭即 End。结束时保留完整 `osd-ring-final.bin` 并运行 `parse_v25_diag.py`，按同一 guest `clock_id=1` 对照 1003 producer/receive/commit、wait enter/return、signal enter/return 与原生 key down/up；原生返回错误、全零帧、未知 ACK 或清理预算到线即停止。至少预留 240 秒，完整 API16 ACK/原字、PID/reap、输入 SHA 与两锁回执。若记录显示 wait 已进入但无返回且 signal 已成功，再定向查对象 epoch 和原生阻塞；若无 wait 入口或无 1003 producer，先定位 AP UI handler。**不以当前候选宣称已修好菜单或 31/32 边界。**
