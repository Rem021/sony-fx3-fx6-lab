# FX3 零键 A 组真实网页 + guest 回执

2026-11-04。**运行结果 failed：screen0 presenter 后 60.593419008 guest 秒内无 `0x1003` 绘制提交、无宿主验证帧；按键为零。** 清理与浏览器终态分别通过。本轮只执行 A，未启动 B；不得把该现象称为根因或可用性通过。

## 身份与时钟

| 项 | 实际 |
| --- | --- |
| 唯一 run | `v25diag-web-r6-0dfbd0ab`，本文件所在目录 |
| runner | r9 `run_trial_v25_diag_r3.py` SHA-256 `902869ee48c1c80dbe770316d0515ac429a5679beb1af73971dfabf7be041126` |
| 源冻结 | r9 `SOURCE-FREEZE.json` SHA-256 `48b0b0abfd2f6ac633c6ac74f5c6ff912ece0290e938206b09c42163a77a5c36` |
| guest | 默认 r3 manifest `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`，原 CPIO `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`；未加 r4e flag |
| 命令 | `--max-minutes 20 --max-steps 4096 --port 0`；实际 0 键 |
| loopback URL | `http://127.0.0.1:58761`，独立 agent-browser 会话 `fx3-ab-a-b83358633d9e` |
| PID | runner 78823、QEMU 79157，结束后 `ps -p 78823,79157` 无输出，runner 退出码 2、QEMU 退出码 0 |
| UTC | runner `created_utc=2026-11-04T16:18:05.838527+00:00`；观察器结果文件 mtime `2026-11-04T16:22:02.263414+00:00`；receipt mtime `2026-11-04T16:22:15.135696+00:00`。先行卷/进程预检为 16:17:58 UTC 左右；mtime 是文件完成的宿主时钟，不与 guest ns 直接相减。 |

启动前 `ab_preflight.py` 实际通过：外盘 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、两锁可独占、无 QEMU/runner、r9 全源与两臂原候选/CPIO pins。网页真实打开并点击一次 Start；没有任何 guest 按键或重启。`ab_observer.py --arm A --run <本 run> --send-stop` 独立进程 exit 0，监听 PID、launch ID、manifest/CPIO 身份通过；其 End HTTP 回应为 `stopping=true`，不能代替后续 cleanup。

## 绘图观察与证据限制

`ab-zero-key-observation.json`：screen0 `presenter_factory_return` guest `clock_id=1 ns=153012348992`；最新 KEY96 poll `ns=213605768000`，差 `60593419008 ns`；`first_commit_ns=null`，`frame=null`，`render_valid=false`，`native_key_seen=false`，`steps=0`。状态决策为 `no_commit_or_verified_frame_after_60_guest_seconds`，发生时 runner 剩余 981 宿主秒。网页从启动待机直到 End 都未显示固件 PNG；[启动截图](ab-browser-start.png)、[停止中截图](ab-browser-stop.png)、[结束截图](ab-browser-final.png)已保存并实际查看，最后显示“本轮健康检查未通过，资源已回收”与最后提交帧“无”。网页截图中的纯黑占位框不是原生全黑帧。

独立逐行统计本轮 `serial.log` SHA-256 `2bb9d2157e39028a618e528b2f3e474d6978dd4a8ad4e97b12303f8ab20831e7`：`FX3_UI_WIRE=63`、`FX3_AP89_SCREEN_CREATE=8`、`FX3_UI_FILL_EXEC=0`、`FX3_GPE_CMD=0`、`FX3_OSD102_COMMIT=0`。UI_WIRE 第 9 条 `tag1=0x9831000`、末条 `tag1=0x1000`，target 均 `0x8280074d`。这表示原 r3 CPIO 也可出现此前 B 观察到的 UI 发送后无绘制执行/提交状态，**使新增 procdiag 成为该现象必要条件的解释不成立**；并不证明高位字段、宿主实现或任何单一原因就是根因。发送记录不能当消费/渲染完成。

`osd-ring-final.bin` 在 QMP 暂停态完整读回 `16,777,216` 字节，SHA-256 `080acf35a507ac9849cfcba47dc2ad83e01b75663a516279c8b9d243b719643e`，逐字节均为零，前 64 字节也为零。这是**取得完整数据但没有有效环格式/未初始化状态，原因未知**，不能说成“未取到数据”、成功的空环或已证明损坏。`diagnostic_readback_pass=false`，cleanup 内 `diag_snapshot` 报 `not a v25-r3 diagnostic readback`；A 候选本来不含 r4e procdiag，记 `not_available_by_candidate`，不得将其缺失当绘图原因。

## 退出、输入、网页

`receipt.json` 的 `stop_cause=end_trial_button`，`key_steps=0`，`inputs_unchanged=true`，所有 `input_checks` 留原回执。原 20 秒 API16 路径在 9.990515 秒内收到 guest ACK 并读回原 16 字节 `000b00b4fd7bbba9fd030091f35301a9`；F100FILE identity/header 成立、`restore_seen=1`，未由 host 写原 guest code。`API16_restored=true`、`native_unbind_return=0`、`quit_sent=true`、QEMU exit 0、`process_reaped=true`、`PID_absent=true`。两把原运行锁在 receipt 均 `free_at_close=true`，结束后再次执行 `ab_preflight.py` 也通过；runner/QEMU PID 不存在。`trial-web-final-receipt.json` 为 `acknowledged=true`、`end_reason=browser_ack`，浏览器实际显示终态并保存结束截图。`lifecycle_pass=true`；`protocol_pass=false`、`render_pass=false`、`health_pass=false`，runner 退出码 2。首帧不存在，不能以清理通过替代运行通过。

## 宿主存储窗口

`ab-a-storage-query.json` 保存只读 `/usr/bin/log show` 的完整 argv、每段退出码、超时标记与输出哈希。以本机时区 08:17:55–08:22:20 分成五段，覆盖 runner 创建到 receipt 写成；谓词限定 kernel 的 KAFU2T unmount/mount、APFS unclean/transaction failure、USB `cableChangeOccurred`/`Extreme 55AE`/`m_connectionActive`。五段均 exit 0、无超时、零匹配行；**仅表示该谓词在这些窗内未命中，不能证明外盘全程可靠**。本轮没有观察到与此前 r6 相同的核日志掉盘事件；其他存储错误或漏日志仍未知。r8 比较工具的 `storage_window_verified` 仍固定 false，因果 A/B 对照需协调端审核，B 本轮未运行。

## 未通过与后续

实际 A 的屏幕绘制/宿主首帧未通过；B、两臂因果对照、真实菜单及长时间使用均未验。最窄下一问题是：为什么 screen0/63 个 UI_WIRE 已发生但本轮没有 UI_FILL_EXEC/GPE_CMD/OSD102_COMMIT；需用保留的串口、原 ELF 与原生调用链定位，不能靠放宽帧门或延长原厂 5000 ms 超时宣称修好。本轮无第二次 VM、无 keepalive、无修改 guest/Backup/定时器、无 FX6 工作。
