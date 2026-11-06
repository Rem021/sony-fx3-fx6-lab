# r28 首次只读取样候选

**offline candidate passed；真实八步、长期可用性未验。** 只写新r28目录，没有真实VM/Start/部署/实机/USB/SD/FX6动作；r26/r26b/r27失败和封存保持。仅使用1组完整实际多调用演练，未追加第二组。

## 最小变化与身份边界

core只改3个源：postkey_read.js增加browser原arm+5000ms首图门及原身份复核；postkey_observation.py从reservation确定是否首图、保留browser截图前后区间；prepare_run.py将core pin与返回工具加入本轮源冻结。其余30个core源逐字节同r26，包含PAGE/server/native observer/runner/operate、原按键门、deadline、精确snapshot/confirm和未入队恢复。PAGE canonical仍852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b；计划仍4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f。

等待以原browser alarm.armed_ms+5000为绝对点，已过就直接继续，绝非每次再加5秒。前/中/后复核原document对象/timeOrigin/UUID、run/launch/step/accepted attempt/nonce/due、原20秒与End/unknown。local约25ms检查，fresh status约200ms复核且读取有界；发现变化即拒绝，不主张硬实时或server/guest原子事务。后续observe不等待，恢复仍用另一套原helper。

5秒只安排采样，不是语义完成、像素稳定或输入许可。实际截图仍只有before/after browser区间，精确compositor瞬时未知，不把host墙钟或某个显示generation冒充截图时刻。保持最多3观察、8accepted/10attempts/2恢复每步一次；原20秒持续走，不延长/重置/重武装，不自动pin/confirm/重试/补键。

返回路径只派生原adapter的候选根/core pin及短模板import；show_result/tool_call与原字节相同。生产argv实际指向本r28 runtime-wrapper/operate.py，原文件本体SHA仍97e41bc5687fd6c9397fcca639355624c70e368761e1e24ad4329a85d9408741；adapter核本r28 core清单a253a42c1f6aa56a929df85890a0d13e2e4e043bccafa8fa134f6a70d78e4cd4及每个core源。完整stdout/stderr和本次PNG校验、非零无图、不读旧current-return、不重发规则保留。差异见MINIMAL-CORE.diff、MINIMAL-RETURN.diff和SOURCE-REUSE/RETURN-SOURCE-REUSE。

## 定向离线检查：10项通过

实际候选PAGE/server与自有browser，native ACK和延迟4.5秒出菜单为明确MOCK。

- 首图在原arm+5秒之后，后续明确observe立即取图，不重复5秒。
- 到达首图路径已超过arm+5.25秒，记录applied=false且无额外5秒。
- 原PAGE明确未入队恢复在5秒内返回，0keyPOST，未套用新等待。
- 等待中End、launch、document、nonce、attempt、unknown均fail closed，0pin/confirm、无合格PNG，wrapper terminal/原失败清理生效。
- 原20秒自然到期拒绝。健康的5秒门本身早于20秒，因此此项在arm+19.2秒进入“native未就绪”的原共用等待/身份分支，原timer实际到期；没有伪造browser时间或改timer。

[原始回执](evidence/WAIT-TEST-RESULT.json)。这批是host断言，不冒充模型实际审阅或完整演练。

## 唯一实际模型多调用演练

实际使用本r28 wrapper、捕获、原PAGE pin/confirm及新绑定返回路径，模型每张图真实收到并查看后，下一独立调用才作动作；没有sleep模拟模型延迟。fixture故意4.5秒出完整菜单，不代表真实固件时延。

| 边界 | 实测 |
|---|---:|
| 首图browser取样区间，相对原arm | 5.0040–5.0899秒 |
| click child（含等待） | 5.2308秒 |
| 观察图emit完成→pin Node入口 | 6.0963秒 |
| pin child | 0.1584秒 |
| 固定PNG emit完成→confirm Node入口 | 6.1812秒 |
| confirm child | 0.3497秒 |
| 原browser cancelled event.elapsed | 18.2588秒 |
| 原20秒余量 | 1.7412秒 |

首图可见完整Setup > Area/Date 45/59、橙色Area/Date/Time Setting、Language English；单独pin后模型重新看独立640×480固定PNG，再独立confirm。最终1key POST/1pin POST/1confirm POST，mock native down/up各1，flow=confirmed。没有额外observe或补键；全链每次真实argv均指向新r28目录。[MODEL-REHEARSAL-RESULT](evidence/MODEL-REHEARSAL-RESULT.json)及run-model1下原始tool-return目录、PNG和精确确认回执。

跨调用间隔包含图片交付、模型及调度，无法细分；model_received_at、model_review_completed_at仍unknown。Node记录epoch与timeOrigin，browser取样和alarm用各自真实browser时钟，不跨域相减。只有这一组离线成功、余量很窄，不能推断真实八步稳定通过；真实固件仍可能更晚/过渡、合法拒绝或到期，必须按原End处理。

## 冻结、准备、资源

实际prepare/preflight通过，LOCAL-SOURCE-FREEZE包括新增返回工具/core pin；实际runner仅import（未main）确认5个关键模块来自冻结r21，所有生产JS/Python语法、原PAGE/计划、原QEMU/fixed14预期哈希匹配。core33/生产38已冻结，未复制千项历史产物。原43项源/封存清单在运行前记录并在运行后匹配；另2项（历史fixed.png与r26返回适配清单）是结束后依据已有封存pin回溯补核，不声称运行前采样过45项，来源与时间见INPUT-SUPPLEMENT.json。合并清单45项现值一致；固定平台在收尾preflight与最终只读检查匹配；没有guest启动可供“运行前”比较。[验证](evidence/IMPORT-SOURCE-VERIFICATION.json)。

原End按钮结束本fixture、browser关闭；自有service PID80508、共87个service/browser PID独立核不存在，51849端口connect拒绝、lsof无监听。[FINAL-CLEANUP](evidence/FINAL-CLEANUP.json)。fixture中的fake-run最终回执明确是MOCK，不能充真实QEMU回收证明。

本任务完成的是可复核候选及评估，未部署；真实完整8步骤由协调端另行统一运行。
