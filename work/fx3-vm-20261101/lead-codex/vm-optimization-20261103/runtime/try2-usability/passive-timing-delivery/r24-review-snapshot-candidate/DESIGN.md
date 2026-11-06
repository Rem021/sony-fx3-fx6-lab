# r24 实现前设计与边界

审阅对象与下一键许可分开。只在新候选 PAGE/server/helper/wrapper 中实现，固定 FX3 guest/平台不变。

1. 服务端原 submit 全部门保持，成功入队后额外绑定 request_id/独占 document_id/launch/expected step；runner 在首次观察到同 step/key 的原生 down/up 证据时调用只读宿主登记 hook，记录当时 publish/sequence 下界。只允许此后新 publish 且 sequence 更大的有效非黑 PNG 作为待审对象。证据含义是“原生收键后宿主新观察到的合格帧”，不宣称该键导致像素或原生 handler 完成；若没有新的有效帧，拒绝建立对象。
2. 明确的 pin-review 按钮建立一个不可替换对象，绑定 run incarnation、launch、document、step、input attempt、pin request、随机 snapshot_id 和精确 PNG bytes/SHA/gen/seq；原 frames 缓存淘汰不影响它。最多1份≤4MiB PNG，20秒资源TTL，确认后释放字节，仅留1份精确历史元数据回执。资源TTL不是延长原客户端20秒alarm。
3. 页面分别显示“当前实时画面”和“本次按键后固定审阅副本”，独立加载并核PNG哈希；明确确认按钮只确认该副本。capture 返回确切 snapshot PNG 文件及页面证据给操作代理，随后单独显式确认；JSON不能证明实际视觉语义。
4. 确认在服务端同锁核对象、run/launch/doc/step/attempt、精确bytes摘要、生命周期及review状态后一次消费，不要求历史图等于当前动态图；确认不发键。不接受跨身份、未来/收键前帧、替换、重复pin或确认重放。下一步 planned helper 仍核全部实时准入和原server SHA/gen门，历史回执不能充作当前帧。
5. stop/error/unknown、其它accepted input、review step/launch改变、过期均撤销对象。客户端未知与终止采用单调latch、先同步丢弃本地对象，再尽力上报abort/原End；迟到响应不能恢复对象或解锁。网络分区无法让服务端瞬时得知客户端未知：服务端单次消费/TTL与独占文档能力限制残留，客户端未知后绝不再确认/重发/发键；不把无法观察的远端状态说成known。确认回包丢失保留unknown并End，即使服务器已消费也不重发。
6. 新runner只加“原生接收已观察”宿主hook和显式候选web导入；其余平台/原生写入/错误/超时/清理不变。准备审计直接按固定SHA256SUMS逐行核全部145项，包含manifest本身。

最小改动范围：新web子类+新版PAGE、runner候选导入/hook、快照capture/confirm CLI与JS、r23历史确认消费者副本精确schema接线，以及对应准备/测试。旧源与旧结果全部只读，真实八步另派。
