# 原 FX3 显式确认宿主辅助：离线交付

**结果：新的候选 CLI 与同页面 JS 已在真实 r17 PAGE/TrialState、独立 Chrome 单标签和 loopback fixture 下通过 13 个定向场景；未运行 QEMU、未部署、未修改旧 helper/PAGE。** 真实 r17/N64 运行 `8a41064f` 第 1 键 MENU 的完整菜单截图时间为 20:45:54.109556，原闹钟 20:46:01.903 到期，剩余约 7.793 秒属于尚未打点的人工判断/宿主调度间隙，不能当作固件无响应。本候选只减少确认决定**之后**的多次宿主调用，不改变 20 秒。

## 合同与拒绝边界

`explicit_confirm_cli.py` 必须收到操作员显式调用、专属单 tab `fx3-deadline-*`、精确 loopback URL（尾斜线）、launch UUID、当前已 armed alarm nonce、step、亲看图 SHA 与非空目标说明；receipt 独占创建。`explicit_confirm.js` 在点击前重核 r17 PAGE canonical SHA `fe56b4…4478`、原确认 handler SHA、同 document/timeOrigin、原 alarm due、当前已加载图 SHA+generation、review step、原按钮可见且 enabled、无未知/错误/停止。它不读图判断目标、不改 handler/PAGE 状态、不直接 POST、不发键，不重试确认。

唯一 DOM click 后同步冻结原 handler 新建的 request ID、step、sequence、generation、SHA。后续只在原 `confirmationMatches` 对这份身份完全匹配且 `guest_input_written=false`、最新当前图仍有效并使原七键放行、原 alarm nonce/due 仍未过期时，调用原 `cancel` 一次。旧 ACK/错误身份、409、5xx、未知送达、画面/输入未放行、过期或终态都不取消。确认 A 后当前帧前进到 B，或 A→B→A 但 generation 新增，按 r12 合同仍可放行；这不是自动确认 B/A 的语义内容，而是消费**既有特定历史确认回执**。HTTP 回应丢失但原 PAGE 根据同 request ID 的后续 status 完整 receipt 合法恢复时可取消；这类测试只称 **status recovery**，不称已看到 HTTP200。

## 真实浏览器 fixture

最终证据在 `evidence/run-94d50984/RESULT.json`，13 场景全部 passed，13 张页面截图和独占 CLI 回执同目录。基本成功、当前 B 帧、ABA 新 generation、HTTP 响应延迟但 status 恢复均是单次原 confirm POST、0 guest key、闹钟 cancelled；旧 step/SHA/nonce 在点击前拒绝且 confirm POST 为 0。409、5xx、错旧 receipt、当前 ready 被撤销、迟到且无 server receipt 均保持 alarm armed、confirm 最多一次、0 guest key；1200ms 短版到期例确认 0 次且 alarm expired。成功例 click→cancel 分别为约 418.5/168.5/211.4/251.3ms，**仅是本地 fixture 宿主间隙，不是 VM/固件性能值**。

快测失败等待仅把候选 JS 的 10,000ms 等待上限在内存替换为 800ms；到期例仅把原 deadline.js 的 20,000ms 在内存替换为 1,200ms。生产候选 JS 和旧 helper 文件均不变，常规成功及 status recovery 使用生产 20s/10s。原 `evidence/RESULT.json` 是早期独占文件名冲突的失败回执，原样保留；最终轮改为独立 `run-94d50984`，不放宽 CLI 的 exclusive receipt。浏览器 session 清理见该轮 `CLEANUP.json`：`active=false, pid=null`；本轮 10 个 fixture 端口均无监听进程。

## 范围与下一门

这里只验证 host PAGE、原 HTTP handler/状态和人工**显式调用**机制；fixture 人工布置 review 状态和橙色测试 PNG，测试回执内的“MENU完整菜单”只是输入字符串，并非看到真实菜单，不代表原生菜单语义确认、运行计时、API16 或真实 VM 生命周期。新辅助尚未投入入口；需协调端审查哈希并在另获授权的真实运行中逐图人工使用，才能评估是否把先前 7.793 秒间隙实际缩短。源码/依赖与交付哈希见 `SOURCE-FREEZE.json`、`DEPENDENCIES.json`、`SHA256SUMS`。
