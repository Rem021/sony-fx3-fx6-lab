# r24：按键后审阅快照候选，offline-only passed

**15组server、6组真实browser/实际wrapper链及准备核验通过；未启动runner/QEMU、未部署。真实八步仍待另派。** 仅写本目录；旧r21/r22/r23源、旧测试证据、部署入口和协调ledger未改。

## 问题与设计

r23本轮7键6确认；第7步待机已返回图并做语义判断，但旧explicit_confirm在点击前拒绝，expected=null。`r23-vm-9710706aa341/FAILURE-BOUNDARY.json`记录capture→confirm调用9306.6ms、alarm仍剩8934.1ms；不是20秒到期。附近HTTP出现不同gen/SHA支持动态竞争风险，**没有eval瞬时联合快照，具体子条件仍unknown**，旧失败不改判。

[实现前设计](DESIGN.md)与[合同](CONTRACT.md)分离“已审阅指定后置图”和“下一键实时许可”。新server在原生收键证据观察之后，才接受新的合格publish/sequence；一个input最多一个绑定run/launch/document/step/attempt和精确PNG的对象，独立于原64帧cache，单份≤4MiB、资源TTL20秒、单次消费/不可失效后复活。收键后的新宿主观察不等于像素因果或原生handler完成。

## 最小实现边界

- 新`trial_web_r24_review_snapshot.py`继承冻结r21全部实时submit门，增加单向审阅对象状态、身份/失效、pin/PNG/abort及历史confirm；新PAGE明确live与固定副本，异步终态/unknown使用单调latch。
- 新`review_snapshot_cli.py`、capture/confirm JS，返回确切原PNG并供代理实际查看，之后单独明确confirm。新指纹见`PAGE-IDENTITY.json`，不冒充原PAGE字节；deadline计时仍原20秒。确认不发guest键，不等待动画回到某SHA，不用最新gen改写旧图。
- 新runner只加新web导入、原生down/up+sender-up后宿主fence hook、明确依赖顺序及隔离输出路径；固定kernel/DTB/QEMU/CPU/memory/N64不动。实际import probe核5个关键依赖均来自冻结r21。
- r23 wrapper/历史前提消费者仅在候选副本接线新schema：PNG SHA/length、snapshot identity、launch/document origin和精确confirm绑定；下一键实时门逐项见[对照](INPUT-GATES.md)。`MINIMAL.diff`、`SOURCE-REUSE.json`列实际差分与复用。

## 针对性验证

| 原件 | 结果与边界 |
|---|---|
| `evidence/SERVER-RESULT.json` | 15组：跨run/step/attempt/document/未来帧/收键前帧/bytes/hash拒绝；64帧淘汰后原字节仍在；TTL/bytes失效/暂时状态撤销后不可重pin；stop/error/unknown/新身份撤销；重复pin/confirm拒绝；有界存储；原实时旧帧409、新帧202 |
| `evidence/BROWSER-RESULT.json` | 6组，单一自有service/session，真实候选PAGE/server及实际`operate.py __main__` subprocess：capture后继续A→B→A动态发布约9.3156秒，原序号被cache淘汰，原PNG仍被精确确认，再新planned单步成功capture，合计2keyPOST/1confirmPOST；其它PNG/doc/origin前提拒绝，未确认下一步不发键，丢确认回包不重复，迟到pin/confirm遇End不复活 |
| `evidence/HTTP-PROTOCOL-TRACE.json` | 保留真实host端请求结果；native receive和视觉语义均明确MOCK oracle，没有真实菜单/真人看图声明 |
| `evidence/IMPORT-PROBE.process.json` | 候选→冻结r21→旧ROOT，5个实际`__file__`/hash匹配，无VM |
| `evidence/preparation-fixture_audit/INPUTS-BEFORE.json` | 实际prepare/preflight入口：pins2、source40、**逐行delivery145含manifest自身**、fixed14、QEMU1全部match；没有起browser/runner/guest |
| `evidence/ALARM-IDENTITY-CHECK.json` | 封存时恢复helper原完整alarm version/URL/launch/sealed断言；现有成功原回执满足，静态编译核对，无需重跑browser |
| `evidence/PREPARATION-FINAL-RESULT.json` | 最终源码新准备及common冻结导入通过，无新browser/VM |

此次测试没有失败回执被覆盖，也没有泛跑旧矩阵。browser观测中代数15采样发生在next capture后，已明确命名`live_generation_after_next_capture`，**不能当作confirm瞬时代数**。动态期间、精确历史回执和cache淘汰各有原件，未为补这个数字重跑。

所有自有server线程、服务PID、12个browser PID和port已回收，外层再核见`evidence/FINAL-CLEANUP.json`。原输入前后与旧冻结清单核对见`INPUTS-*.json`，最终源码和交付精确hash分别在`CANDIDATE-SOURCE-FREEZE.json` / `SHA256SUMS`。

## 后续

按[准备说明](PREPARATION.md)由新task创建独占运行目录；r24可变checkpoint/preflight输出只写该轮`FX3_NAV_RUN_DIR`，**不再有旧runtime三个输出例外**。网络分区无法让服务端瞬知客户端unknown，协议以客户端sticky锁定+abort/End、单次消费及TTL保守处理，绝不据未知回包重发。同步job边界不扩大到server/guest（[MDN执行模型](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model)，2026-11-04回读）。

真实八步菜单、人类连续视觉体验、长时稳定性及FX6均未验；后续仍需唯一一轮真实VM逐键图审阅与完整收尾，离线通过不能替代它。
