# v25-r3 真实网页与 FX3 guest 诊断：失败

## 结论

本轮只启动一次 QEMU。真实 Orca 浏览器在 English 菜单内逐图操作 16 次：原生界面显示 Power Save Start Time 为 **5 Min**，ENTER 弹窗仍选 5 Min，MENU 正常取消弹窗而未改值。第 16 次 DOWN 的宿主控制字已写入并读回，但 guest 发键线程未报告该步轮询、原生 down/up 或完成；最后原生帧 3718 在该次请求前约 22.237 秒已提交。因此第 16 键不是已证实的冻结原因，也不能把这次停滞归为 OSD wait 死锁。清理期间 API16 原字未恢复，整体 `health_pass=false`、`lifecycle_pass=false`，本次结果 **failed**；31/32 键及长期可用性未验。

## 固定输入与实际运行

- 卷 UUID：`F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，启动前双锁空闲且无 QEMU。候选 SHA256 `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`；runner SHA256 `1a3af0b8fb6be5c79bf4e58548e622fec03263281badf147e0cff67dae7d3429`。沿用冻结 guest、DTB、English gen4 Backup；未改原 5000ms、APO、种子或默认入口。
- 命令：`run_trial_v25_diag_r3.py --max-minutes 30 --max-steps 4096 --port 0`。runner PID 53060，QEMU PID 53476，本机 URL `http://127.0.0.1:64077`；网页启动和按键来自真实浏览器，不是 internal-hoststep。实耗 550.403 秒，实际键数 16，未达到本轮人工 36 键上限。
- `trial-input-events.jsonl` 记载每键一次 100ms 请求；`trial-step-*.json/png/raw` 为不可变帧，`manual-browser/*.png` 是逐键网页截图。已实际看图再决定下一键，无自动补键/重试。源码冻结 diff 中 assignment 与最终 runner 的 `setdefault` 小差异仍存在，本轮按上述 runner SHA 运行，未改冻结件。

## 逐键可见结果

| 步 | 键 | 亲看 PNG / 页面 | 原生帧 | 网页截图 |
|---:|---|---|---:|---|
| 0 | — | English 待机 HUD | — | `manual-browser/step00-standby.png` |
| 1 | MENU | 初始闪动后完整 Setup / Area/Date，橙色焦点 | 123 后继续更新 | `step01-menu-complete-browser.png` |
| 2 | LEFT | Setup 类别列表 | 510 | `step02-left-complete-browser.png` |
| 3 | DOWN | Reset/Save Settings，仅浏览 | 778 | `step03-down-browser.png` |
| 4 | DOWN | Operation Customize | 1081 | `step04-down-browser.png` |
| 5 | DOWN | Dial Customize | 1276 | `step05-down-browser.png` |
| 6 | DOWN | Touch Operation | 1457 | `step06-down-browser.png` |
| 7 | DOWN | Monitor | 1768 | `step07-down-browser.png` |
| 8 | DOWN | Display Option | 2026 | `step08-down-browser.png` |
| 9 | DOWN | Power Setting Option | 2236 | `step09-power-setting-browser.png` |
| 10 | RIGHT | Power Save Start Time = 5 Min | 2485 | `step10-power-save-current-browser.png` |
| 11 | ENTER | 5 Min 保持选中；未改数值 | 2709 | `step11-power-save-popup-browser.png` |
| 12 | MENU | 弹窗关闭，仍为 5 Min | 2938 | `step12-menu-closed-browser.png` |
| 13 | DOWN | Auto Power OFF Temp = Standard | 3239 | `step13-auto-power-temp-browser.png` |
| 14 | LEFT | Power Setting Option 类别 | 3549 | `step14-left-power-category-browser.png` |
| 15 | DOWN | Sound Option 类别 | 3708，随后 3718 | `step15-sound-category-browser.png` |
| 16 | DOWN | 请求后仍显示上帧；未取得原生 down/up，立即终止输入 | 无新帧 | `step16-pending-last-frame-browser.png` |

上表的帧号是该步记录的已校验图或后续只读帧，不把“看见下一帧”推断为输入处理函数完成。第 6 步确认后有一次浏览器点击回执 `false`，页面仍为第 6 步；重新看图后才产生第 7 次实际 guest 键，未把失败点击计作一步。

## 失败同钟时间线与机制边界

宿主 `time.monotonic()`：最终提交帧 3718 的只读捕获为 `383422.792740916`；第 16 次请求 `383445.014567458`，QMP 停止态控制字写入并读回 `100000003000000064000000` 后 `sent_monotonic=383445.029627083`。最后帧捕获与请求相隔 **22.236886542 秒**；这里均为宿主时钟。`ap101-control-final.bin` 显示 pending step16、done step15，串口无 `FX3_SYNTH_KEY step=16`、`FX3_KEY_INPUT_RECV step=16` 或 `FX3_KEY95_STEP_DONE step=16`。旧错误文案只称缺 key-up，掩盖了 down 同样缺失；独立 host 候选已修正文案分类。

Guest `clock_id=1` 纳秒：step15 原生 DOWN 接收 `487766085008`、UP 接收 `487894501008`、完成 `487924837008`；KEY96 输入 worker TID343 最后 `poll=48836,stage=1,done=15,control_step=15` 在 `492004519008`。这次轮询发生在 step16 的宿主请求之前；不能用不同单调时钟直接相减。最后 OSD：wait_enter frame3716 `491645199008` → wait_return `491682916000,result=0`；produce frame3717 `491694125008` → return `491705138000,result=0`；receive frame3717 `491859355008`；commit frame3718 `491866358000`；signal frame3718 enter `491993824000` → return `491993919008,result=0`。QMP 暂停态 16MiB 环 SHA256 `fbaa97cb5d4fe9205b961fe494fcca606c6238fc486802b5cd324a5c79004f57`，尾部 96 组配对有效、无半写槽、全局 busy 丢 5 条；尾部缺项不能证明历史绝无阻塞。`osd-ring-final-diag.json` 和 `osd-ring-final-readback-receipt.json` 可复核。

串口在最后 KEY96 poll 之后仍有三轮 `FX3_OSD_LIFE_FILE_END tag=periodic` 和其他 guest 输出；因此不能称整机停止。最后 `FX3_PROC97_STATUS` 在约 guest 492.02 秒记主线程 PID237 为 `S`、192 线程、TracerPid0、Cpus_allowed_list 0-2；最后全线程快照是更早的 round290，其中 TID343 曾为 `R`，不能当作第 16 键故障时线程状态或等待点。QMP 日志配对 105 个 STOP 与 105 个 RESUME、一次 quit；未发现无请求 STOP，亦不能把本次归因于 GDB ACK 意外暂停。历史 `lead-claude/audits/thread-stop-standby/README.md` 有 assert→同 mm SIGSTOP 静态链，但本轮未见对应 assert，不能移植结论。

FILE100 独立 observer PID148 的最后原生文件读取是 generation2；最终文件只读双次相等，`shutdown_control=0`。收尾写入控制字后，79 次样本约 20.004 秒均见控制字，却 `restore_seen=0,restore_status=0`，API16 始终为 trampoline `5000005800021fd6bcfc4d0080ffffff`，非预期原字 `000b00b4fd7bbba9fd030091f35301a9`。由 `fx3-file100-observer-v2.c` 可知 `restore_seen` 仅在 `system(fx3-sync100-shutdown.sh)` **返回后**写入；0 不能区分 observer 未读控制字、卡于前次 Backup 双读、已进入 shell 但未返回。没有该 PID 故障时的线程快照，尚不能证明输入线程和 observer 的共同同步点。

## 退出与未通过项

网页 `final-failed-browser.png`、`trial-web-final-receipt.json`：终态显示失败，browser ACK 为 true。`restore103-receipt.json`：guest ack/API16 原字恢复 **失败**，`completion_timeout`；没有宿主替写原 API。随后 QMP quit，QEMU exit=0 且 reaped，PID53476/53060 已不存在，输入哈希未变，双锁独立复核均 free，卷 UUID 再核正确。`receipt.json` 的 `diagnostic_readback_pass=true` 只证明暂停态环读取；`lifecycle_pass=false`、`health_pass=false`。未验证 31/32 键、无故障长期使用、浏览器正常 End/完整恢复；不得部署默认入口。

## 离线 host 候选与下一次最小观察

`runtime/try2-usability/passive-timing-delivery/v25-r3-postmortem-host/` 是独立 host 候选，沿用冻结 guest 候选 SHA。它把“既无原生 down”和“已 down 但未见发键线程 up 完成”分开，并在首次故障清理已暂停的 QMP 状态下、16MiB 环读取前保存 `query-cpus-fast` 与 `info registers -a` 原始回执；不据 vCPU PC 推断 guest TID/锁。宿主 fixture 和 py_compile 通过；**没有 guest 运行验证**。候选未改原 5s 超时、还原规则、按键门、CPIO/DTB/Backup、默认入口。下一轮须另获授权，并先人工看最新完整 PNG，只发一次 MENU 或一个有意义类别键；一旦再有 ACK 缺失，冻结 vCPU PC/寄存器及可识别线程状态，再查 FILE100 未读/双读阻塞/进入 shell 三段，不为凑 31/32 补键。现阶段没有证据支持行为性修复。
