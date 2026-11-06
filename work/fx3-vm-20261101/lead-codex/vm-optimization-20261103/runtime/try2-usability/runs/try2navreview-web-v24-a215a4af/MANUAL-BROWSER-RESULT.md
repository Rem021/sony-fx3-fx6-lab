# TRY2 v24 单轮浏览器与 FX3 guest 回执

**结论：本轮网页启动、前 11 键逐图确认和干净退出通过；第 12 键 MENU 的原生 down/up 已接收，但省电选项弹窗未关闭，故完整交互和 31/32 键边界未通过。** 没有把无变化当作合法取消，也没有继续发键。本轮不提升默认入口。

## 固定件与边界

- 唯一运行目录：`try2navreview-web-v24-a215a4af`；2026-11-03 19:19:42 UTC 启动，host 总计 625.8515 秒，网页 `http://127.0.0.1:53445`，仅 loopback。独立 Chrome 新标签操作，结束后只关闭该标签。卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、启动前两锁 free、无其他 QEMU，见启动预检与 `receipt.json`。
- 启动命令：`python3 -B run_trial_v22_navigation_review.py --max-minutes 30 --max-steps 4096 --port 0`。runner SHA256 `1f27f7078b3f26752ef1b73053a07607300750e4d2523d8e96e6f615a090d39d`，web SHA256 `3cf9544f08fbdf62dee46420170f5fb85dfae1c656b8a24c062c7b055d64fde1`，候选 JSON SHA256 `90adc5fda97a4b26293e4763da1ed3d5eec22eaf2f0115292c1b720c5049e9aa`。guest CPIO `e0f05f36e7da388d452508ba0d2cc85c2ae43e1884757632ef752b807849fd76`，guest DTB `ffcc274affaefd49186c1bfd1f227485dbf6703985add3610d1b5ab4f6db5fd8`，English generation 4 固定源 SHA256 `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f`。完整原件 SHA 见 `STATE-v24.json` 和 `receipt.json`。
- 第一次点击 MENU 因 NO CARD 闪动造成网页像素身份过期而被拒，`steps=0` 且无 guest 写入。重新亲看完整待机画面后才发出实际第 1 键。此拒绝不计为按键或自动重试。

## 人工逐键画面

每行的 PNG 是当时从真实 Chrome 页面保存的**不可变截图**；相应 `trial-step-XX-key-*.png/.json` 是原生环提交帧。每次在完整页出现后点击一次宿主“我已看图，继续”；此确认不发 guest 键。下一键依据上一张所见选定，没有预排序列。

| 实际键 | 按键与看图理由 | 浏览器截图 | 可见结果与判定 |
| --- | --- | --- | --- |
| 0 | 完整待机可见，English HUD | `manual-browser/step00-standby-browser.png` | 允许试探 MENU；NO CARD 闪动引发的过期点击已单独拒绝 |
| 1 | MENU，进入原生菜单 | `manual-browser/step01-menu-browser.png`、`step01-confirmed-browser.png` | Setup / Area/Date，橙色焦点与完整文字可见；确认后选 LEFT 切类别 |
| 2 | LEFT，查看类别列表 | `manual-browser/step02-left-browser.png` | Setup 左侧类别列表完整，确认后向下逐类只读浏览 |
| 3 | DOWN | `manual-browser/step03-down-browser.png` | Reset/Save Settings，页 46/59；未进入重置/保存项 |
| 4 | DOWN | `manual-browser/step04-down-browser.png` | Operation Customize，页 47/59 |
| 5 | DOWN | `manual-browser/step05-down-browser.png` | Dial Customize，页 49/59 |
| 6 | DOWN | `manual-browser/step06-down-browser.png` | Touch Operation，页 50/59 |
| 7 | DOWN | `manual-browser/step07-down-browser.png` | Monitor，页 51/59 |
| 8 | DOWN | `manual-browser/step08-down-browser.png` | Display Option，页 52/59 |
| 9 | DOWN | `manual-browser/step09-down-power-browser.png` | Power Setting Option，页 54/59；右侧出现 Power Save Start Time，因此选 RIGHT 只读查看 |
| 10 | RIGHT | `manual-browser/step10-right-power-browser.png` | 焦点在 Power Save Start Time，当前显示 **5 Min**；确认后选 ENTER 读取完整选项 |
| 11 | ENTER | `manual-browser/step11-enter-power-options-browser.png` | 原生弹窗列 Off、30 Min、**5 Min 已选**、2 Min、1 Min、10 Sec；未改数值，确认后选 MENU 取消 |
| 12 | MENU | `manual-browser/step12-menu-no-change-browser.png`、`step12-menu-no-change-late-browser.png` | 输入已接收，但弹窗仍在，约 30 秒有限观察及后续复看均无关闭；不确认合法无变化，点击网页 End |

网页最终截图 `manual-browser/final-browser.png` 显示 `12/4096`、健康检查通过且资源回收，但保留弹窗画面；这只是**收尾健康**，不是菜单交互通过。第 31/32 键未执行；没有为凑数修改设置或绕过视觉门。人工按钮动作可核：Start 一次、12 次实际 guest 按键、前 11 次画面确认、End 一次；原始浏览器 HTTP 请求总数未抓包，保持 unknown，`trial-input-events.jsonl` 的 12 条本地网页输入与 `trial-web-final-receipt.json` 的 final ACK 可核。

## 第 12 键与首个 MENU 的同钟对照

以下 guest `clock_id=1` 纳秒只在 guest 内比较；host monotonic 见 `trial-visual-outcomes.json`，不混钟。

| 项目 | 首个 MENU | 第 12 键 MENU |
| --- | --- | --- |
| 原生输入接收 | tid261 down `wait_return_ns=152093827008`、up `152207373008`，均 `native_result=0` | tid261 down `531132451008`、up `531337516000`，均 `native_result=0` |
| 发送与完成 | `FX3_SYNTH_KEY` down/up 发送 `result=0`；`KEY95_STEP_DONE` one_down_one_up=1，测得 118.684 ms | 同样发送 `result=0`、one_down_one_up=1，测得 296.694 ms；完成仅指输入协议，不证明原生 UI handler 已处理 |
| 画面生产 | down 后 `OSD102_COMMIT op=0x1003` 首见 frame797 / `ns=152197951008`，随后 frame799 等；菜单完整画面在浏览器确认 | 最后一帧 frame5739 是 **down 前** `ns=530923844000`、`op=0x1005`、`pixel_source_seq=5532`；down/up 后无新 `0x1003`，也没有任何新 `OSD102_COMMIT` |
| 图像身份 | 第 1 键原生 PNG SHA `168a2787...`，与之前不同 | 第 11 键与第 12 键原生 PNG SHA 均 `5a496c4d0995...`，均为 token `0x402`，后者是 1005 重述 source seq5532；浏览器晚复看仍同一弹窗 |

最后 `FX3_OSD_HEADLESS_ACK frame=5739`、`FX3_OSD_NATIVE_SIGNAL frame=5739 result=0 matched=1` 有记录；`FX3_OSD_DRAW_WAIT_RETURN` 最后只到 frame5738。`osal_wai_sem_tmo` 的源码在原生 wait **返回后**才打印该标记，因此缺 frame5739 返回只将阻塞位置缩到“未见返回/未见下一绘制”，不能证明 wait 已进入，也不能单凭 signal 成功认定下游已消费。frame5739 的 `FX3_OSD_LIFE_ALLOC_RETURN result=0 errno=1022` 以 result 为准，errno 可能是旧值；串口的 UIPC `-1022` 也不在此证据下直接等同故障。`FX3_KEY_INPUT_RECV` 明示 `downstream_processing_unproven=1`。没有可归属的 MENU handler entry/return 证据，因此**首个因果缺口是输入接收与 UI handler、以及 UI handler 与 OSD 新 1003 之间**；是否 handler 未触发、线程等待、合法弹窗语义或更早绘制阻塞仍 unknown。尤其末次 1005 停在 down 之前，不能说第 12 键导致绘制停止。

下一轮最小定向观测点：在同一固定 FX3 候选的独立诊断派生件中，给原生 MENU handler 的入口/返回及弹窗关闭状态只读打点；给 TID900 的绘制 wait **入口和返回**、frame5739 后 OSD 1003 producer 发送/接收/完成及线程 wchan 配对。记录原队列 QID、source、guest `clock_id=1`、frame/source seq，保持返回值与 5 秒原超时不变。先离线审计挂点与原字，再由协调端决定是否再给 QEMU 窗口；本轮不运行或部署该探针。

## 退出与未通过门

- `receipt.json`：`stop_cause=end_trial_button`、`key_steps=12`、`health_pass=true`、`lifecycle_pass=true`、`protocol_pass=true`、`render_pass=true`、`menu_verified=false`、`native_shutdown_after_ready=false`。健康与视觉验收分开。
- `restore103-receipt.json`：20 秒约束内 1.562 秒获得 guest ACK 并读回 API16 原字 `000b00b4fd7bbba9fd030091f35301a9`。`trial-web-final-receipt.json`：浏览器 final ACK true，等待 0.290 秒。
- QEMU PID 91133 exit 0、reaped；runner PID 90630 与 QEMU 均独立 `ps` 检查不存在。输入 SHA 未变，原 `outputs/fx3-vm/.run.lock` 与 `menu-repair-01/runtime/.run.lock` 在退出后独立 `flock LOCK_EX|LOCK_NB` 检查 free。没有留下 guest 长跑。
- 未通过：第 12 键菜单取消、连续使用、真实 31/32 键、Finder/默认入口。保留现有入口与所有原件；不将本轮 host fixture 或健康退出推成用户可用性通过。
