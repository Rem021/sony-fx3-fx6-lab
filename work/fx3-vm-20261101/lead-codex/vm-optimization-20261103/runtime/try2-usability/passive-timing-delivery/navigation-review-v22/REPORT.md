# FX3 TRY2 v22 宿主导航确认候选

结论：**host 候选与真实浏览器历史画面测试通过；guest 联动未验。** v21 把按键后任意像素变化视为可继续，MENU 后的 NO CARD 闪动即可提前解锁。v22 在原生按键接收并到达有限观察终点后设置 `review_required`，网页持续显示新帧，但七个输入键保持锁定；用户实际看清当前完整画面后，按单独确认键解除宿主门。该确认不排队、不重发、不调用 InputGate/QMP。未提升默认入口或 TRY2 状态，本任务没有启动 QEMU。

## 证据与边界

| 层 | 本轮证据 | 结论范围 |
|---|---|---|
| 历史 guest | v21 `trial-step-01-key-1ab.png` 序号 1996 是 NO CARD 待机，后续 `internal-observe-02.png` 序号 2705 是可读 Setup/Area/Date/English；LEFT 后 2951 为部分切换，3349 为完整类别页。 | 历史图像，不能代表 v22 guest 已运行。 |
| v22 host | `navigation-test-receipt.json` 使用上述 SHA 固定 PNG：闪动与部分切换均不自动解锁，过期确认拒绝，完整帧确认仅改变 host 门；合法静态无变化键可人工确认。A→B→A 旧代次不能提交键。 | 本机 HTTP/状态机，无 guest 输入。 |
| v22 浏览器 | `browser-v22-final-normal/server-receipt.json`：实际 Orca 浏览器中依次查看闪动、完整菜单、部分切换、完整类别图；2 个 `/api/key`、2 个 `/api/confirm-visual`、1 个 End、最终 ACK，服务线程回收。截图 `01` 至 `04`。 | 浏览器对历史 PNG 的 UI 门验证，无 QEMU。 |
| ACK 错误 | `browser-v22-receipt-confirm-ack-drop/server-receipt.json`：故意丢掉已接受确认的 HTTP 回执，浏览器凭 `request_id + step + sequence + generation + PNG SHA` 精确状态回执恢复；仅 1 个 key POST、1 个确认 POST、无新增固件键。`browser-v22-final-key-ack-drop/server-receipt.json`：固件键回执丢失仍锁七键，End 与最终 ACK 可用。 | 不把 host 确认未知等同于 guest 键未知。 |
| 缓存组合 | `cache-nav-sd4x7n9d/receipt.json`：缓存 reader 对历史 8 个真实 slot 仍校验，每次重新建立序号身份；7 hit、1 miss，同像素序号 4267→4274 仍可确认当前显示内容。缓存源码与独立审定件 SHA 完全一致。 | 离线假 QMP；不声称 MENU 响应或 guest 绘制加速。 |
| 生命周期 | `v22-startup-test-receipt.json`：端口占用、进程启动错误、早退三种宿主 fixture 仍产生失败回执并释放锁；HTTP 最终回执可读。 | 真实 VM 的 API16、QEMU 回收、双锁本轮未验。 |

自动检查只能证明：原生接收回执、已提交帧身份和不可变 PNG 字节；**不能从 screen ID、token、非零像素或一次 `visual_changed` 自动证明目标菜单已完整**。确认按钮代表用户亲眼判定当前显示内容；如果用户在 NO CARD 闪动上自行确认，host 无法证明其判断正确。页面明确要求等目标页完整出现再点继续。`no_change_observed` 仍标明下游处理完成未知，用户可判断静态无变化为合法操作，系统不伪造像素变化。原生全零帧、未知输入 ACK、关机检测、有限观察期与原超时门继续生效。

## 实现与冻结

- `run_trial_v22_navigation_review.py` 从 v21 派生，SHA256 `3ee1422bdd75ce82f4e67ebf4323810a67ccfe82dd1d3f075b2a393f1c8185ff`；差分 `runner-v21-to-v22.diff`。固定同一 guest manifest，未更改 DTB/CPIO、Backup 种子、硬件参数或 100 ms 输入。
- `trial_web_v22_navigation_review.py` SHA256 `6f1a3ae9017162a5941b98df5eb87a72c9b64a806f6e11a5b185ea2af1095e1a`；差分 `web-v21-to-v22.diff`。加载后的 PNG SHA 与 `content_generation` 绑定；同像素新序号可继续，A→B→A 过期身份不可继续。
- `trial_ring_cached.py` SHA256 `9309794feded60291d6748bd4d19ab98a909e7ba73c91233a2ffb983551f9e11`，逐字等于 `host-frame-cache` 审定源；`ring-original-to-cache.diff` 为合并差分。旧 reader、v21、cache owner 源码均未改。
- 所有源码/固定 guest 输入的 SHA、启动参数与来源见 `SOURCE-FREEZE.json`；浏览器、状态机、缓存组合和启动 fixture 的具体回执见 `VERIFICATION.json`。v21 原有 8 秒 HTTP/解码期限、20 秒 guest ack/API16 收尾、最终浏览器 ACK、故障停机路径保留，宿主新确认没有重发。

## 下一次最小运行

由唯一 runtime owner 在确认 UUID、双锁、PID 和其他 owner 空闲后，用本目录 runner 与冻结 SHA 做一次顺序有界 browser+guest。首键 MENU 后先检查 NO CARD 闪动期间七键仍锁、网页持续更新；实际看到完整菜单时才点确认，再按一次 LEFT，看部分切换期间仍锁、完整页出现后确认。每键实际看 PNG 与截图、核原生 down/up/done 与客观时钟；任何未知 ACK、全零帧、原生关机或预算触发即停止，保留 240 秒收尾。按 v21 原规则核 API16、QEMU PID/reap、输入原件 SHA、两锁释放。另行安排真实 31/32 边界与长时间网页使用；本轮 host fixture 不能替代。

默认 60 分钟、4096 键，可通过参数收紧；`--internal-hoststep` 没有浏览器确认通道，v22 会将下一内部请求记为 `stale_no_guest_write`，不能用它绕开逐图确认。旧 TRY1/v21 入口不受影响。
