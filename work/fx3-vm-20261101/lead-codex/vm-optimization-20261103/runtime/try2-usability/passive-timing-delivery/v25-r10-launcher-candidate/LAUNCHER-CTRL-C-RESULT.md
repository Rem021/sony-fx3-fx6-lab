# FX3 候选图标入口与 Ctrl-C 实跑回执

**结论：**本轮候选 `.command` 经 Finder 图形界面双击动作启动，真实浏览器 Start、待机首帧、一次 MENU、宿主画面确认，以及专属 Terminal 窗口 Ctrl-C 退出均取得回执。运行健康检查通过，API16 在原 20 秒期限内由 guest ACK 并恢复原字，QEMU 退出且回收、双锁释放。此为一次约 129 秒的候选入口验收，不是长时使用或默认入口部署验收。

## 启动身份与操作

- 候选：`FX3菜单.command`，SHA256 `28c677bcce47e54acd9ec00909dde5c784df2e5a8b4fd84663f8effe1a10e3fb`。执行前 `--check`、目标卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、`ab_preflight.py` 对双锁/无 QEMU/冻结 pins 均通过。SOURCE-FREEZE SHA256 `65db2b1048d62b07c656b2af56078227e2ca84d86960fe6ce643f2130dbbe9ce`，入口逐项核 22 个源文件。
- 入口方式：`orca computer` 对 Finder 窗口 16059 中 `FX3菜单.command` 项执行 `click --click-count 2 --restore-window`；该动作由系统标记为 synthetic input/unverified，但随即出现**新** Terminal 窗口 17245，窗口文本显示该 `.command` 的准确路径及其执行的 runner 命令。这是 Finder 图形界面双击请求及可观察启动结果，未使用 `open` 命令或直接 shell 运行候选。`terminal-launch.png` 保存了启动输出。
- 新窗口固定 `--port 0 --max-minutes 60 --max-steps 4096`；runner PID 6812、QEMU PID 7067，运行目录 `try2-usability/runs/v25diag-web-r6-18bef2ff`；URL `http://127.0.0.1:55219/`。真实独立 agent-browser 会话 `fx3-launcher-ctrlc-b83358633d9e` 打开该 URL 并点击 Start 一次。未使用 internal-hoststep、直接 POST 按键或 zero-key observer Stop。
- 入口固定原 A/r3 candidate SHA256 `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`、CPIO SHA256 `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`；runner SHA256 `9b70b1281c130e909deb0ae7091cb8738c44f304d847db2162a4a21635ae2ba0`。`receipt.json` 中 `inputs_unchanged=true`。

## 网页及原生输入

- 待机画面实际可辨 HD、Fixed-59.94fps、AF-C、D-R OFF、AWB 等元素，网页显示固件就绪；`launcher-browser-standby.png` SHA256 `9bd144c8988d959ecd08bd1cfb14509ba0829c46ab6e4160b7fa8d45f7bda699`。
- 只点击一次网页 MENU。页面随后显示 `Setup > Area/Date`，`Language English`，橙色焦点 `Area/Date/Time Setting` 以及底部 `MENU Close`；`launcher-browser-menu-initial.png` SHA256 `b60b3e535cf57e6a7e8f95663dd472334ae6b0c9f99eff65f03c1c46aa75d538`。网页回执为 `按键 1/4096`、原生队列已接收、帧 311；我实际看图后点击一次“我已看清当前完整画面，继续”，网页记录该确认没有发送新 guest 键。runner 的 `menu_verified=false` 保留原值，不把人工视觉观察写成该内部自动门通过。
- 未再按 guest 键。Ctrl-C 前网页状态为 `画面已由用户确认；可决定下一键`，最后显示提交帧 429。

## Ctrl-C 与资源回执

- 向匹配 runner PID 6812 的 **Terminal 窗口 17245** 执行 `orca computer hotkey --key Ctrl+C --restore-window`；终端树出现 `^C`，随后打印 `HEALTH True QEMU_EXIT 0 REAPED True API16_RESTORED True INPUTS_UNCHANGED True`，最终显示 `[Process completed]`。`terminal-completed.png` 保留屏幕证据，`stop_cause=Ctrl-C` 见 run 内 `receipt.json`。动作本身被系统标记 synthetic/unverified，但 `^C`、receipt 及进程退出共同证明效果；未向其他 Terminal 窗口发送输入。
- `receipt.json`：`created_utc=2026-11-04T17:23:18.962677Z`、`duration_seconds=128.715995`，`key_steps=1`，`health_pass/lifecycle_pass/protocol_pass/render_pass/diagnostic_readback_pass=true`，`host_observer_error=null`。暂停后完整 ring 16 MiB，SHA256 `7c4a12187d822dfa7db1f48e30a63bc9fd1f12b0fac48578205ae6766193c801`，解析有效；可选采集 paused 再确认且无 error。
- API16 原字 `000b00b4fd7bbba9fd030091f35301a9`，guest ACK 与原字回读 `restore103.passed=true`、耗时 14.1405 秒，未延长原 20 秒规则；最后尝试记录 `restore_seen=1`、`api16_original=true`。`native_unbind_return=0`、QMP quit sent、QEMU exit 0、reaped true、PID absent true。独立 `ps -p 6812,7067` 为空；退出后 `ab_preflight.py` 再次确认两锁 free、无 runner/QEMU，输入哈希未变。
- 真实浏览器终态显示“本轮健康检查通过，资源已回收”，最后提交帧 429；`launcher-browser-final.png` SHA256 `a4516b31f97bbd1ccf6a40e7b4cb00df8efd8634146edae3661e730c77e3d31b`。`trial-web-final-receipt.json` 为 `acknowledged=true,end_reason=browser_ack`。

## 存储与边界

- 启动前只读 15 分钟 kernel USB/APFS 限定谓词查询（09:07:27–09:22:27 PST）exit 0、未超时、无匹配；运行及退出窗口两段（09:23:00–09:25:00、09:25:00–09:26:40）同谓词查询均 exit 0、未超时、无匹配。原始查询范围与摘要见 `LAUNCHER-STORAGE.json`。这仅排除所列谓词在该窗口的日志命中，不是外盘全面可靠性证明。
- 未改固件、Backup、QEMU 硬件、原 5000ms 绘制期限、原生省电设置或默认入口；未部署。仅本轮 1 键与 Ctrl-C 路径通过，连续操作、31/32 键和持续省电行为仍依其他回执单独评估。
