# r25 恢复观察设计（实现前）

只处理原 PAGE 已明确未入队的恢复路径。r24 真实轮仍是 7 keys / 7 confirm / 第8次 not_posted，整体失败，不回写历史结论。

恢复观察是受控浏览器实际截图在采集区间内的不可变文件：保存实际PNG SHA、字节数、来源session/tab/URL、宿主起止时间、前后原状态。前后严格绑定document对象在各JS job内的身份、页面脚本、timeOrigin、reviewDocumentId、launch、step、完整attempt binding、同nonce alarm状态及due；ready/无busy/review/unknown/End，原frameLoadedFor在两端保留。只取消跨截图 SHA/gen相等要求，绝不标qualified_current_screenshot，无firmware字段，无单一generation/causality主张。

取消前模式armed，原RecoveryEligibility仍须真；取消后模式cancelled，要求同一已确认取消回执、同一未入队attempt、无新alarm。保存前后差异作为证据，既不冻结live也不复制旧图。截图是独立CDP采集，非JS job原子数据；期间不可见的短暂状态变化无法由端点证明，明确此限制，后续点击决不使用它作当前帧许可。

取消需要先单独查看取消前返回图，且校验回执链接与PNG；取消后返回另一独立恢复观察。recovery_review必须在另一次wrapper调用实际查看后显式记录；与来源attempt/cancel/PNG/receipt/ledger绑定，只一次消费，下一次显式click才创建新nonce，原prerequisite及所有实时PAGE/server门照常。

任何身份变化、未知、End、非归因未入队、过期alarm、错误nonce、篡改、重复恢复或预算耗尽均End，绝不自动重试。最多8accepted /10attempts /2recoveries且每步一次，NAVIGATION-PLAN保持原SHA。正常postkey快照/确认源不变。

依据：[MDN JavaScript execution model](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model)（2026-11-04核查）：同步job run-to-completion不跨await或截图工具，也不覆盖server/guest；[Window.performance](https://developer.mozilla.org/en-US/docs/Web/API/Window/performance)的时间信息限其上下文，timeOrigin只与document UUID/脚本/launch组合使用。
