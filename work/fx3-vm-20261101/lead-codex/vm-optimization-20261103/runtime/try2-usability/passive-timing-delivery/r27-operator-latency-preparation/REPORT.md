# FX3 r27｜原20秒操作链可行性

**评估完成；当前实际两观察路径仍没有合理余量，不建议据此再开真实VM。** 短模板可减少机械交互，但没有证明消除了模型/调度耗时。首次只读取样稍后的方案仅有条件窗口，应先另立离线候选，不修改本轮生产、不追加第三组。r26/r26b真实失败保持，未启动VM/Start/服务/浏览器，未改原20秒、PAGE/runtime、输入门、计划、模型或运行政策。

## 已有真实记录说明什么

r26b原20秒从arm开始，首个观察在约2.568秒准备好。实际click child为2.671秒，其中wrapper入口至返回2.620秒；observe child为0.226秒，wrapper段0.163秒。wrapper返回至child退出仅约5.5–5.8毫秒。两次返回至下一动作入口却为9.709秒、9.032秒；pin入口已在arm后21.472秒，未生成固定图或confirm。[HISTORICAL-BUDGET](HISTORICAL-BUDGET.json)。失败pin child的2.353秒含清理，不能作为成功pin耗时。

这些间隔混合了图片序列化/交付、模型接收与审阅、调度和外层工具开销。原记录没有图片送达模型、审阅完成及wait各自的准确时间，不能把整个9秒称为模型思考，也不能把child几毫秒优化称为解决方案。

即使假设删去额外observe、其处理成本归零，把两次已有间隔当作“观察图审阅”和“固定图重看”所需交互，条件预算仍是2.568+9.709+9.032=21.309秒，且pin/confirm处理暂记零。它是明确假设下的预算，不是未来所有调用的数学下界。

## 两组实际多调用演练

两组均用已封存历史PNG和明确fake child；每一步是一次独立真实Node图像工具调用，图片确实回到本模型查看后，下一调用才明确选择pin或confirm。没有script sleep假充模型延迟，没有VM/native或自动语义判定。

A组首个历史观察正常返回，独立pin调用在child之前因模块内Map顺序状态未延续而拒绝，**不计三步通过，也没有重试A**。两次实际probe显示同URL import的模块instance不同、计数均1，而globalThis对象保留；这是此工具通路的实测行为，不能假定ESM模块实例跨请求相同。故障及原回放源码保留在evidence/GROUP-A-FAILURE.json、NODE-PROBE-1/2、replay-group-a-failed.mjs；没有将它归咎于冻结生产适配，原生产适配并无此Map。

B组使用预载持有的单步函数，顺序由group、前一次真实回执SHA和PNG SHA文件链接约束；哈希只验完整性，不代替看图。实际查看历史观察图为完整Setup > Area/Date、橙色Area/Date/Time Setting、Language English后，另一调用请求固定图；重新实际查看独立固定PNG后，第三调用才确认回放。[REHEARSAL-MEASUREMENTS](REHEARSAL-MEASUREMENTS.json)。

| B组可测边界 | 秒 |
|---|---:|
| click历史child | 0.1074 |
| 第1张image_end到下一pin Node入口 | 6.1269 |
| pin历史child | 0.1045 |
| 固定图image_end到下一confirm Node入口 | 6.6463 |
| confirm历史child | 0.1020 |
| 首个Node入口至最后确认返回准备完成 | 13.0946 |

约12.773秒在两次跨调用间隔中，仍不能细分模型接收/审阅/调度。一次完整历史链不是稳定性统计；A失败也计入两组预算，未再加组。

B组逐次记录performance.timeOrigin、epoch_ms、Date_ms、perf_ms；这三次origin实测均1793848264141.51。跨调用分析使用origin+now的epoch映射，不默认不同origin的perf_ms可相减，并保留墙钟变化限制。图片emitImage返回只代表宿主工具调用完成，不代表模型已收到；其后的交付也落在未知混合间隔内。

## 短模板有效到什么程度

[短模板](SHORT-TEMPLATE.md)只在未来明确授权run的Start/arm前预载函数；每次仍单独执行原executeAndLoad一次、显示图片、让模型实际看，再决定下一动作。它不保存旧成功图、不自动pin/confirm、不改变timer或输入门。生产short_tool.mjs本轮只导入/类型检查，未执行原operate。

预载模块约1.166毫秒（B回放预载约0.690毫秒）；B摘要从1253/1226字节缩为351/330字节，confirm从884缩为299字节。这能减少代码/上下文冗余，不能解释或承诺消除6–10秒间隔。

原r26b click约2.67秒，1000ms初始yield确实进入过同cell wait；将初始yield设10000ms可减少这种额外往返的可能，之后仍只wait同cell，绝不重发。此次A、B本身child短，1000ms与10000ms均未触发yield，所以**没有测得可归因的wait节省数值**，不能声称提高yield就赢回若干秒。[OUTER-TOOL-BOUNDARIES](evidence/OUTER-TOOL-BOUNDARIES.json)。

## 首个观察图仍可能是过渡帧

将B组仅替换为r26b click child所得15.658秒只是条件估算：历史回放首图已经完整，而r26b首图实际过渡，不能省掉所需observe。若额外observe沿用真实0.226秒，再假设多一个handoff只取B较小6.127秒，即使真实pin/confirm归零也约21.694秒；这仍是条件推演，不能伪称所有未来运行必定失败。[后移取样情景](LATER-FIRST-OBSERVATION-SCENARIOS.json)。

协调端只读统计显示r25七步及第8步的经视觉识别的历史目标图中，最长“key POST→首次目标status请求”约4.496秒。它不是精确native/绘制完成时刻，也不是未来上界；SHA仅用于历史时序归属，绝不能拿来自动判语义。本轮arm至key POST约0.087秒，映射最长历史观测约arm+4.582秒，故arm+4.5秒取图甚至未必足够。

**具体下一步建议（本轮不实现）：** 仅在新离线宿主候选中，让首次只读截图在原arm+约5秒开始取样。之前只保持有界只读生命周期检查，20秒照常走，不能冻结guest、停timer、等SHA或像素稳定来判完成；仍需实际看观察图→明确pin→重新实际看固定图→独立confirm。若仍是过渡，只能明确observe或End，不得因此自动pin。

若假设首图在arm+5秒已经可用，沿用本次两handoff，先占17.773秒；若5秒才开始取样并用真实observe child0.226秒作代理，先占17.999秒。历史成功r25的capture总1.52–4.53秒含pin POST前等就绪，**不能整段再加一次而双算等待**。已分出的pin POST至capture返回尾段，加confirm helper及其guard，七步配对约0.155–0.375秒；尾段不是完整独立pin，r26新增前置flow检查和适配开销仍未知。

因此“5秒开始取样”情景约18.154–18.374秒，剩约1.626–1.846秒，尚未覆盖r26 flow前置检查/独立pin额外等待、适配器与图片通路的新增尾段及未来模型调度波动。单次B的handoff已比r26b快了约6秒，不能从这个偶然差异推出小于2秒余量可稳定守住。这个方案值得进一步离线核查，但本轮证据不足以建议新VM，也没有实施延迟取样。

## 最小后续选择

保留原20秒合同：先另派上述首次只读取样时点的窄离线候选，同时完整测一次真实工具多调用链，不增加自动动作或假审阅；若仍没有可解释余量，直接报告不足，不重复盲跑VM。若要改变“20秒必须覆盖所有跨工具审阅”的宿主测试自定合同，应由协调端明确提出替代证据/边界并获新授权；本任务没有更改它，也不默认放宽。

## 输入与资源边界

只写新r27目录。所有用到的封存源/回执/PNG及清单pin前后哈希一致；r26b的251项清单pin仍为6a80d33a2040a385c0291e5e1e648cd7a16fddf627de4f0d53ce5c212ca0e6ad。协调端补充pin/confirm分析的原始来源hash也只读核验。未复制整runtime，未改封存候选/部署/ledger。4个历史fake child均同步退出；无新VM、Start、浏览器、服务或端口，未改模型/运行政策。source及全交付见SHA256SUMS。
