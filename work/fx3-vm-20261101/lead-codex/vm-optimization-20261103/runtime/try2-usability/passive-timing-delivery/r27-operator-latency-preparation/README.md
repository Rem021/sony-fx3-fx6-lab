# FX3 r27｜操作链耗时可行性评估

**评估完成；不建议据此再开真实VM。** r26b的真实失败与20秒原约束保持，未改PAGE/runtime/模型/部署/ledger。

- [报告与下一步选择](REPORT.md)
- [条件预算](HISTORICAL-BUDGET.json) · [实际多调用测量](REHEARSAL-MEASUREMENTS.json) · [稍后首次取样方案](LATER-FIRST-OBSERVATION-SCENARIOS.json)
- [可复用短模板](SHORT-TEMPLATE.md) · short_tool.mjs（便利候选，未宣称解决模型延迟）
- evidence/group-a：首次历史观察后模块Map状态丢失，中止；不算三步通过。
- evidence/group-b：实际历史PNG分别返回模型看图，三次独立调用完成观察→固定图→确认回放，无script sleep；仅此一组完成，不能作稳定性统计。

本轮只写新r27目录，没有Start、QEMU、原operate、浏览器或服务动作。历史图片和确认回执不充新运行或固件语义证明。全部输入前后哈希与交付清单见INPUTS-BEFORE/AFTER、SHA256SUMS。
