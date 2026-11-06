# FX3 零键 B 组真实网页 + guest 回执

2026-11-04。**B 在零键冷启动出现有效图标待机帧；完整 VM 健康仍 failed。** `render_pass=true`、`lifecycle_pass=true`，但 `protocol_pass=false`，因为本轮结束前缺少冻结合同中的 `FX3_AP_SNAPSHOT_DMM_SKIPPED` 标记；不能以可见首帧替代完整健康通过，也不据此判定后台故障。仅执行一次 B，没有重跑 A 或再次启动 VM。

## 固定身份与时间

| 项 | 实测 |
| --- | --- |
| run | `v25procdiag-web-r6-d4254d75`，本文件所在目录 |
| runner / 源冻结 | r9 runner SHA-256 `902869ee48c1c80dbe770316d0515ac429a5679beb1af73971dfabf7be041126`；`SOURCE-FREEZE.json` SHA-256 `48b0b0abfd2f6ac633c6ac74f5c6ff912ece0290e938206b09c42163a77a5c36` |
| B 原 guest | r4e manifest `ced1644fbcecc542c3d90f16be2a461876e7f3af92ff639c793742f090136d22`；原 CPIO `439f9089d3e36b6a5ee0d3f16a170a608761f315a4a2169d1d859cb0f66952db`，未重打包 |
| 命令 | `run_trial_v25_diag_r3.py --review-procdiag-r4e --max-minutes 20 --max-steps 4096 --port 0`；实际 guest 按键 0 |
| 独立网页 | `http://127.0.0.1:61207`，agent-browser 会话 `fx3-ab-b-b83358633d9e`；仅一次 Start |
| PID | runner 85041，QEMU 85447；结束后两者 `ps -p` 无输出，QEMU exit 0、已 reap，runner exit 2 |
| UTC | runner 创建 `2026-11-04T16:27:39.887659+00:00`；观察结果文件 mtime `2026-11-04T16:28:48.938318+00:00`；receipt mtime `2026-11-04T16:28:51.617593+00:00`。这三者为宿主时间，不能直接与 guest ns 混算。 |

启动前和退出后 `ab_preflight.py` 均实际 PASS：外盘 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，两锁空闲、无运行中的 QEMU/runner、r9 全源及 A/B 原候选/CPIO pins 匹配。两臂 `command.json` 的 34 个 QEMU args 长度一致，差异仅为各自 `serial.log` 输出路径和原 CPIO 路径；`model_env`、1200 秒预算、4 核 MTTCG 与无 icount 配置一致。精确位置见 `ab-args-diff.json`，不把单轮结果当严格随机实验。

## 首帧与原生观察

`ab-zero-key-observation.json`：screen0 presenter `clock_id=1 ns=38604596000`，第一次 `OSD102_COMMIT op=0x1003` 为 `ns=46093361008`、frame 1，即同一 guest 时钟下距 screen0 **7.488765008 秒**；最新 KEY96 poll `ns=48144220000`。观察器在宿主验证 frame seq 6、`render_valid=true`、非全零且像素非均匀时按合同停止；`stop_response={"stopping":true}`，实际 0 键。该帧 PNG SHA-256 `e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4`，`trial-frame.png`、`trial-standby-ready.png`、`trial-final.png` 哈希相同。已亲看[原生 PNG](trial-frame.png)和[真实浏览器终态截图](ab-browser-final.png)：黑底上有 HD/帧率、AF-C、AWB 等图标；这只证明当前软件 OSD 采样有可见图标，不证明原 CP 全图层合成或菜单长期稳定。网页终态显示最后提交帧 7；观察器先看到 seq 6，后续相同像素 SHA 的 seq 7 不构成额外按键。

暂停态 `osd-ring-final.bin` 完整 16 MiB，SHA-256 `15123486acfff1759f71bbecbea8fe4c290555172fd974e6992c095f0c887367`。`osd-ring-final-diag.json` 有有效 magic/version 2、52 个 accepted events、0 dropped busy writer、0 invalid/torn slots，`diagnostic_readback_pass=true`。这些是 B 的诊断环有效性，不外推到 A 的全零环。

`serial.log` SHA-256 `322a7ef98fee827ae3e5bf27dcdd5797996746e18cebafaedcbd1057723c1406`；逐行粗计 `FX3_UI_WIRE=94`、`FX3_UI_FILL_EXEC=4`、`FX3_GPE_CMD=89`、`FX3_OSD102_COMMIT=7`、`FX3_AP89_SCREEN_CREATE=8`。串口有交织粘连，计数仅作位置线索，不将发送等同完成。第 9 条 UI_WIRE `tag1=0xe5d41000` 仍有高位而本轮产生绘图；单看该高位不构成“阻止绘图”的充分条件。

## 未过的健康门与清理

`receipt.json`：`standby_ready=true`、`render_valid_at_end=true`、`render_pass=true`、`diagnostic_readback_pass=true`、`lifecycle_pass=true`；`protocol_pass=false`、`health_pass=false`，runner exit 2。`markers` 中唯一 false 为 `FX3_AP_SNAPSHOT_DMM_SKIPPED`。冻结 init 流程将该 echo 放在延迟的批量/proc 任务快照循环之后，而非首帧提交前；本轮 `serial.log` 可数 `FX3_AP_SNAPSHOT_1_BEGIN=1`、`FX3_AP_SNAPSHOT_1_END=0`、`FX3_AP_SNAPSHOT_DMM_SKIPPED=0`、`NATURAL_OBSERVATION_END=0`。观察器在首次有效帧立即 End，因此缺标记与较早结束有关的可能性存在；**不能据此断定后台卡住，也不删除或放宽健康门**。

网页 End 后 `stop_cause=end_trial_button`。原 20 秒 API16 路径约 1.548 秒内 guest ACK 并读回原 16 字节 `000b00b4fd7bbba9fd030091f35301a9`，F100FILE header identity、`restore_seen=1`、`restore_status=0`；未由 host 写原 guest code。`API16_restored=true`、`native_unbind_return=0`、`quit_sent=true`、QEMU exit 0、`process_reaped=true`、`PID_absent=true`、`inputs_unchanged=true`。两把锁在 receipt 为 `free_at_close=true`，退出后的独立预检再次可独占。`trial-web-final-receipt.json` 的 `acknowledged=true`、`end_reason=browser_ack`，真实浏览器显示已结束并保存截图。首帧与完整生命周期各自有证据，仍须以 protocol/health 的 false 如实记整轮失败。

## 存储窗与 A/B 限制

`ab-b-storage-query.json` 保存只读 kernel USB/APFS 查询完整 argv、输出哈希、退出码和超时位。本机时间 08:27:30–08:29:00 两段覆盖 B 的 runner 创建至 receipt 写成，两段均 exit 0、无超时、零匹配掉盘/重挂/USB 断连谓词；A 的五段查询同样无匹配。这只表示具体谓词在对应时间窗未命中，不是外盘全程可靠性证明。

只读 `ab_compare.py` 输出保存在 `ab-compare.json`：A 身份与输入门通过，但 screen0 后 60.593419008 guest 秒无 commit/宿主帧；B 身份与输入门通过且有首帧。两臂观察模式可并列，工具仍固定 `paired_observation_comparable=false`、`storage_window_verified=false`，需协调端结合原始核日志及运行控制条件评定。单次 A/B 的不同结果**不能把 r4e procdiag 改动、某个 UI tag 高位、宿主或调度中的任一项确定为根因**；B 也未通过完整健康门，未测试菜单输入/长期使用。后续仅由协调端决定，不在本轮重启或继续按键。
