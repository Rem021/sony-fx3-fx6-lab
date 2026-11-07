# ADF HDMI 不可用负面模型：独立决策评审

**当前不可实施，本轮不增加 completion reply，保留已经实证的线程池恢复。** 诚实的“下游发送不可用”负面模型在概念上可以成立，但当前最前置的失败条件没有证明：没有完整运行时队列/路由状态证明 `0x9058003f` 不可投递，也没有本轮原 CP 子发送返回非零的观测。仅仅没有专项 shim 分支，不等于原 CP 的 send-failure 条件成立。

这一缺口已足够阻止实施，无需为本轮评审继续补整条协议。AP 对错误的处理及外层继续，只说明接收方行为；既不能证明服务失败，也不构成注入 `-1` 的理由。

## 已有证据与不能跨越的边界

[bb-request-contract 原证据](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-07-fx6-observed-wait/bb-request-contract/bb-request-contract.md) 支持：原 CP 构造 `{0x200d,0x132d,12,0x8001}`，状态是可变 incoming 值；特定 handler 的下游 send 非零分支返回 `0xffffffff`，再由即时错误路径装入 completion。AP 将该值映射成 `0x6f`。这是 **send 失败 → -1 → completion** 的证据，不是“任意未实现服务 → -1”的普遍规则。

仍未知的边界保持未知：外部 `0x032d` 到内部 `0xbb` 的完整 ingress；完成目的在原 CP 路由 FIFO 中的选择/取消/并发所有权；子服务真正完成条件。对于一个先于子服务执行就失败的负面模型，不必先实现子服务正常功能，但必须证明其失败前提及当前事务的回复路由，不能用命令头相似和 AP 宽松消费替代。

## 实际 CP shim 与当前运行策略

本轮实际 CPIO 的 `simulation/fx3-cp-backup-reset-v1.ko` 为 66,552 B，SHA `7e8d859ecb0fc66c5e05909ae5688b966838a6aa7bb0a478b6b4139177004aaa`，init 第128–131行加载它。对应现存模块文件、主 C、关键 sync header、module unit 均与 `BUILD.json` 指纹一致；本评审没有重编或声称全部传递依赖复现。来源与行号保存在 [source-hashes.json](source-hashes.json)。

该 owner 路由只显式承接既定 Backup/date/sync 模型；非其目标进入 `cp_reset_send_backup100_prior`。其未知分支会记录 `no_reply=1 no_free=1 prior_absent_route_return=0 terminal_unproven=1` 并 **return 0**。实际 10B HDMI 请求正走这个分支，source 为 `0x81cf610f`。

因此：

- 当前未知路由不是“返回发送失败”的实现；不能把 return 0 改称下游 send 非零。
- 它在不生成回复、不释放未知请求方面保持保守，但不能笼统称为 transport 层 fail-closed：调用者仍看到返回0。
- 若未来设计精确新模型，未知/不匹配请求必须继续保持现有路由与所有权行为；不得顺带对整个 ADF/BB 目标补错误回执或调整默认返回值。

## 分配、源 qid 与所有权

已知 Backup 模型提供一个**已实现模式的例子**：用实际 AP qid 申请新回复、设置模型 source、send 成功后不再读/释放回复；send 失败释放新回复；提交后才按原目的释放原请求。date 模型也显式管理异步工作项、重复请求和释放边界。

这些代码不能自动证明 10B/12B BB 的新适配正确。它们分别针对不同目的、schema、qid 族与消息尺寸。原 CP 的 BB completion sender 从上下文/FIFO 取目标；当前 native AP source 与 waiting qid 相等，是这次事务的强关联，但不是完整 FIFO/取消契约。不得直接把 Backup 的尺寸、source 常量或生命周期复制到新 BB 分支，也不能把 source-qid echo 等同于原 CP 路由已恢复。

## 未来最窄候选的必要条件

只有独立满足以下条件，才可重新讨论一个明确标注为“虚拟环境下游发送不可用”的候选：

1. **失败前提独立成立：** 完整运行时路由/队列/提供者状态证明这条子发送不可投递，并明确其与原 CP 非零 send 分支的对应。证据不能来自 AP 继续、菜单推进、无专项源码分支或当前接收超时。
2. **精确事务可选择：** 仅接受已绑定的目的、完整10B内容 `0d202d030a0001800000` 与有效 native metadata/source；原 ingress 缺口须闭合，或先明确证明一个不会误选其它事务的模型入口。不得扩展到 payload=1、其它头/长度、任意 `0x032d` 或所有 BB 请求。
3. **回复与原请求所有权闭合：** 动态 qid 的取得、有效期、目的/source、native 12B allocation、send 成功/失败、原请求释放、重复/并发/取消都需要独立证据和明确提交点；不得释放请求后保存指针做迟到回复，或在未知投递状态下重发。
4. **只传播已经成立的失败：** 新申请并完整初始化原 CP 12B completion，`status=-1` 只表示该明确失败模型，日志始终标明 synthetic/model、原 CP 未执行、子服务未实现；不能宣称成功、HDMI能力、原 CP 完整实现或实机兼容。
5. **其它请求保持关闭：** 不匹配请求不回复、不夺取所有权、不改变既有 route；alloc/send/free 异常保留未知/失败状态，不回退为成功或另一个臆测错误码。

本轮第一项未满足，其余 ingress/路由/所有权亦有缺口。因此这里列的是重新评审门槛，不是实施授权或已准备好的修复方案。

## 网上资料的作用与限制

2026-11-07 核对 QEMU 官方 [Memory API](https://www.qemu.org/docs/master/devel/memory.html) / [Load and Store APIs](https://www.qemu.org/docs/master/devel/loads-stores.html)：模拟事务可以显式表示成功/失败，非法访问的行为与设备/总线有关。这支持“负面模型本身并非必须假装成功”的一般判断，**不**提供 Sony command、状态值、qid 或释放规则，不能用来填补上述私有协议缺口。

本评审只保存文字、JSON、来源哈希及 [只读收集器](collect_sources.py)。未改 shim、候选、供体、消息或运行政策，未实现/运行负面模型，未操作 VM/端口/相机，未执行 Git/sync。
