# r24：指定的按键后快照确认，不是下一键许可

仅适用于本候选。r23真实本轮仍是7键、6确认，第8键未执行；其第7次确认前置拒绝不追溯改判。八步计划仍完整：MENU→Setup/Area-Date橙色Area/Date/Time Setting；UP→Language English；C4→语言帮助；MENU→Language；OK→只查看English列表；MENU→取消；MENU→待机；MENU→重开完整菜单。

## 对象身份和生命周期

- 输入依据仍为冻结r23计划、明确单步调用、前步真实后置审阅与确认及当前实时准入；`scripted_navigation=true`、`visual_review_at_click=false`。初次实际查看合格待机图；其后实际查看每步新返回的确切PNG，再另行显式confirm。JSON自证或fixture oracle不算视觉验收。
- 原server submit全部实时输入门保留。成功入队后绑定launch、document UUID、attempt/request UUID与expected step。新runner仅在观察到匹配step/key的原生down/up及sender-up记录后，登记当前publish/sequence下界；可pin的帧必须为此后新publish且sequence更大的有效、非黑、原验证PNG。这证明收键后新的宿主帧观察，不证明原生绘图因果或最终handler完成。
- 一个input最多发放一个快照，`unissued→issued→consumed/revoked`单向变化。对象绑定snapshot_id、run incarnation、launch、document、step、attempt、pin request和精确bytes/SHA/generation/sequence；拒绝重复pin和失效后重建。缓存淘汰不改变已保存字节；最多保留1份≤4MiB服务端PNG、1份确认历史元数据，原64项frame metadata缓存不扩大。
- pin只接受当前合法loaded观察；拒绝任意历史/未来/收键前帧、别run/step/attempt/document、替换bytes/hash。确认在同一锁内核对象和当前review/lifecycle身份，然后一次消费；重复confirm即拒绝。确认不发guest键，也不要求指定快照等于当时的实时PNG/gen。
- stop/native error/unknown、launch/step/review身份变化、其它accepted input、TTL和字节异常均撤销；过期/撤销后即使状态恢复也不可重建。20秒资源TTL不延长原客户端20秒alarm，确认成功立即释放服务端PNG。

## 页面、证据和下一键

页面分别标明实时画面和固定审阅副本，后者加载时核原PNG hash。capture保存该**原PNG**及服务端身份，返回文件给代理实际查看；confirm只表示“已审阅本次按键后的这张指定副本”，按钮不宣称当前实时画面已被审阅。第1步仍保留原完整MENU参考图的capture资格检查；它不是等待动画回到某SHA后自动确认，确认始终另一次明确调用。

历史回执精确保留原snapshot身份；planned prerequisite同时核capture文件/hash、实际PNG SHA/length、document origin、snapshot document/launch与对应confirm。下一键必须新的单步调用、新nonce，并再次通过所有原实时PAGE/server SHA+gen/ready/step/error/stop/busy/review/unknown门；历史确认不能替代实时输入帧，不重绑旧图片身份。

## 未知、竞态和预算

任何回包丢失或协议unknown都保留锁定并原End，不重发、不因GET看到历史回执就恢复。客户端先同步撤销本地对象并latch unknown/终态，再尽力abort/End；迟到pin/confirm/状态回包不得恢复对象或按钮。网络分区无法令服务端瞬时知道客户端unknown，残留对象由独占文档、单次消费、TTL约束；不宣称分区下远端已known结束。

保持原20秒alarm、End/finalACK/API16/QEMU回收链、固定FX3平台和原生错误/超时。唯一后续真实测试仍8分钟、8accepted、10显式attempt、2有归因未入队恢复且每step最多1；只有原PAGE明确未入队结果可走原恢复链。helper no-click/unknown默认End；语义不符不得补键或换路径。本任务不启动VM、不部署，真实八步另派。
