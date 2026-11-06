# R10 A/r3 零键实跑回执

结论：本轮真实浏览器启动、原 FX3 guest 首帧、诊断读取与退出清理均通过；这仅证明此单次零键运行健康。此前 A 零帧未在本轮复现，不能据此认定 r10 宿主补丁修复了零帧根因；全零 ring 时仍独立采 UI 区的失败分支，本轮也没有运行到。

## 身份和范围

- 运行目录：`v25diag-web-r6-5010d535`；UTC 起点 `2026-11-04T16:55:04.362397Z`，receipt 写成 `2026-11-04T16:56:31.810738Z`。runner PID 1121，QEMU PID 1308；网页 `http://127.0.0.1:49802`，浏览器真实点击 Start 一次，实际 guest 键数 0，网页 End 一次。
- runner SHA256 `9b70b1281c130e909deb0ae7091cb8738c44f304d847db2162a4a21635ae2ba0`；SOURCE-FREEZE SHA256 `65db2b1048d62b07c656b2af56078227e2ca84d86960fe6ce643f2130dbbe9ce`；r3 candidate SHA256 `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`；CPIO SHA256 `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`。运行参数 `--max-minutes 20 --max-steps 4096 --port 0`，无 `--review-procdiag-r4e`。输入源检查见 `receipt.json`，`inputs_unchanged=true`。
- 启动前 `ab_preflight.py` 通过：目标卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、双锁空闲、无既有 QEMU、源 pin 匹配；退出后相同检查再次通过。见同级 `v25-r10-zero-key-review/PREPARATION.json` 及本轮预检回执。

## 观察和时间关系

- `ab-zero-key-observation.json`：guest `screen0_ns=34746322000`，第一笔原生 0x1003 commit `38817220000`、frame 1，差 **4.070898 guest 秒**。最新 KEY96 poll `44309214992`；`native_key_seen=false`。
- 浏览器获得 host verified frame seq 23，640×480、非全零、非均匀像素，PNG SHA256 `2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e`；`trial-frame.png` 和 `r10-browser-start.png` / `r10-browser-final.png` 已实际查看。最终网页显示画面及健康检查通过，浏览器 final receipt `acknowledged=true,end_reason=browser_ack`。这不是菜单或长时可用性验收。
- 串口行序：`UI_GATE_BOUND` LF8719（physical `0x41dc00000`，count 60），首个 `TIMER_ENTRY` LF22571（seq3），`UI_FILL_EXEC` LF22659（seq7），`GPE_CMD FillRect` LF22668，`OSD102_COMMIT` LF25941（上述 guest ns 38817220000）。前几个串口 marker 无同钟时间戳，行距不能换算为耗时或推定因果。计时和绘制的首发关系只以已有 guest 时间字段和事件顺序描述。

## 暂停态诊断

- `receipt.json` 记 QMP stop 确认、query-status `paused,running=false`，完整读取 `osd-ring-final.bin` 16,777,216 字节，SHA256 `c25d752bb9373340b3057863b034e7f8340b6d979a2f2620a8faa0c75e3673b5`；解析有效，`dropped_busy_writer_events=0`、`invalid_or_torn_slots=[]`。内容有效与暂停读取完整性分别成立。
- 再证 paused 后，10 秒可选预算内读取 `ui-gate-counters.bin`，地址 `0x41dc00000`、65,536 字节、SHA256 `42818369e1a7b6861bef13b47b51da317dd710ebe186a78afc83919e99c3aa53`；receipt 状态 `complete`、无 optional error。其他已声明 optional 区也均完整，未替换原 ring 文件。
- `r10-ui-counter-summary.json`：magic `0x3145544147335846`、version 2、active bank 1、publication serial 6007；count4..11 为 `[852,851,824,27,27,828,825,852]`，gate_hist `[0,0,27,207,268,349]`，peak_gate 284，backlog_skip 824，time_skip 0，time_pass 27，timer_dequeue 825，a12/a13 nonzero 均 0。镜像字段是各自原子读值，跨字段不保证事务一致；最终累计值不能定位第一笔 timer、Fill 或 commit 的耗时根因。

## 收尾与存储窗口

- `receipt.json`：`health_pass/lifecycle_pass/protocol_pass/render_pass/diagnostic_readback_pass` 均 true；API16 原字节 `000b00b4fd7bbba9fd030091f35301a9`，guest ACK 与原字回读在 20 秒合同内完成（1.56965 秒）；原生 unbind return 0、QMP quit sent、QEMU exit 0、wait/reap true、PID absent true。`ps -p 1121,1308` 再查为空；两把运行锁 `free_at_close=true`，输入哈希未变。finalACK 另见 `trial-web-final-receipt.json`。
- 启动前 15 分钟 USB/APFS 精确谓词查询 `PRE-RUN-STORAGE.json` exit0、无 timeout、无匹配。运行窗口覆盖 08:55:00–08:56:40 PST 的两段只读 kernel 查询见 `r10-storage-window.json`：各 exit0、无 timeout、无匹配事件；这只排除所列谓词在该时间窗内的记录，不是完整存储可靠性证明。

未验：全零/坏头 ring 时独立 ui-gate 读取的真实失败路径、菜单按键、长时间可用性、31/32 键边界、存储全面健康以及零帧唯一根因。没有启动第二轮，也没有改默认入口、固件或 guest 超时。
