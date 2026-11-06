# FX3 r28｜首次只读取样时机候选

**离线候选通过；仅1组实际多调用fixture，原20秒剩1.741秒。** 未运行真实VM、未部署，真实八步与稳定性仍待另行验收。

- [报告](REPORT.md) · [运行模板](RUN-TEMPLATE.md)
- [10项等待检查](evidence/WAIT-TEST-RESULT.json) · [实际模型多调用](evidence/MODEL-REHEARSAL-RESULT.json)
- [输入/路径验证](evidence/IMPORT-SOURCE-VERIFICATION.json) · [独立清理](evidence/FINAL-CLEANUP.json)
- CORE-SOURCE-FREEZE.json绑定33个core源；SOURCE-FREEZE.json覆盖38个生产文件；SHA256SUMS覆盖全部交付。

只对accepted按键的首张未固定观察等到原browser arm+5000ms；到达时已过该点就不再等。等待中持续查原身份/20秒/End/unknown，后续observe、未入队恢复不套用。5秒不代表菜单完成，仍实际看观察图→独立pin→重新实际看固定PNG→独立confirm。

原PAGE/server/native/runner/按键门/20秒/计划/恢复策略不改。返回适配明确定位本r28 operate及core哈希，不回退旧候选、不取旧current-return、不重发。fixture native与画面变化为MOCK，不是原固件执行证明。
