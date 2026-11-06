# FX3｜r29 首帧启动只读分析

入口：[REPORT.md](REPORT.md)。时间线：[TIMELINE.json](TIMELINE.json)；逐轮证据：`r26-EVIDENCE.json`、`r26b-EVIDENCE.json`、`r28-EVIDENCE.json`；平台与实际 helper 来源：[PLATFORM-AND-HELPER-BINDING.json](PLATFORM-AND-HELPER-BINDING.json)；代码行与原始语义：[CODE-EVIDENCE.json](CODE-EVIDENCE.json)。

重现：`python3 analyze_startup.py > ANALYSIS-RECEIPT.json`，然后 `python3 make_timeline.py > TIMELINE-RECEIPT.json`，最后 `python3 verify_analysis.py`。仅在本新目录生成结果；不导入运行器或启动服务。输入均在原路径读取，完整 SHA 见 `INPUTS.json`；重现前仍需按项目规则验证外盘 UUID。

边界：只读分析通过，底层原因未定；原 r28 180秒/0键失败保留，没有新运行或平台/门禁修改。
