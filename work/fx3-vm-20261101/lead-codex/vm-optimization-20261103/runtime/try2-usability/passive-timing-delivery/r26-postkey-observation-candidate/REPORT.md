# FX3 r26｜先观察再固定快照

**offline candidate passed；真实VM八步仍待验。** 只写本r26新目录，未部署、未启动真实QEMU，FX6/物理相机/USB/SD未触及。任务给定的r25真实轮仍是8accepted/7confirm，第8次首个固定图仍待机、稍后才完整菜单，整体failed保留，不追补确认。

## 最小改动

只派生4个宿主文件：operate.py、common.py、preflight.py、prepare_run.py；新增postkey_flow.py、postkey_observation.py、postkey_read.js。原r25 PAGE/server/CSP/runner/native observer、snapshot一次生命周期、planned click、deadline、初始待机、全部归因未入队恢复helper逐字节相同。PAGE canonical SHA仍为852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b；NAVIGATION-PLAN SHA仍为4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f。

accepted后的click现在返回真实浏览器截图形式的未固定观察，不自动pin。最多3次含首图，每次另一次observe须填写实际看上一张图后的过渡判断；所有时间计入原20s。看到完整目标后另一明确pin才调用原capture一次，返回新的精确PNG；必须重新实际看该固定PNG再独立confirm。观察图不提供输入许可，不是postkey确认，也不能变成正常prerequisite。错误/未知/耗尽/到期写持久terminal锁并原End；固定后不能observe/repin或替换复活。详见[合同](CONTRACT.md)、[具体未来VM操作模板](VM-OPERATIONS.md)。

每次截图前后核同session唯一tab/URL，并由fresh status加同步片段核document/timeOrigin/UUID、run/launch/step/attempt/nonce/原alarm和native已接收审阅阶段。两端可有不同显示SHA/gen/seq，截图SHA只绑定实际PNG字节，firmware_generation=null，不声称截图瞬时单帧、因果或handler完成。端点不覆盖区间内未观察瞬变，不是server/guest原子事务。依据[MDN execution model](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model)；早期Blob路径受原CSP限制的推断与修正见下，[MDN connect-src](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src)明确fetch受其控制（2026-11-04核查）。

## 实际离线验证

最终[浏览器回执16组](evidence/browser-attempt04/BROWSER-RESULT.json)、[HTTP/native mock原始跟踪](evidence/browser-attempt04/HTTP-PROTOCOL-TRACE.json)、[server核心负例15组](evidence/server-core/SERVER-RESULT.json)全部通过。使用当前实际PAGE/server、真正operate.py/helper的__main__，native和操作语义oracle均明确为MOCK，不能据此声称真人看图或真实菜单可用。

| 场景 | 实际结果 |
|---|---|
| mock native后持续动画，约4.5s才菜单 | 第1/2观察为不同MOCK过渡图；第3截图完整菜单，均未pin/confirm |
| 独立pin、重新看固定PNG、独立confirm | 恰1key POST / 1pin POST / 1confirm POST / 1mock down+up，无补键 |
| 原20s覆盖工具及模型间隔 | 菜单首次发布约4.531s；原alarm实际8095.8ms取消；独立模拟审阅间隔0.8/0.65/0.8s及其余等待均真实经过 |
| 连续下一步 | step2也经新observe/pin/confirm，原历史prerequisite仍约束下一key |
| 旧过早pin问题复现 | 同原capture确实固定MOCK待机；4.5s后live菜单出现，旧固定图仍待机，未confirm |
| 原r25完整恢复链 | 首次not_posted/0POST → 返回恢复图 → 单独cancel → 新恢复图 → 单独recovery_review → 新nonceclick → r26 observe/pin/confirm，合计仅1key POST |
| wrong attempt/document/launch/step/nonce/run/timeOrigin | 实际新helper CLI均unknown拒绝，无新PNG、无pin/confirm/额外key |
| 未pin confirm、观察冒充固定图、第四次observe | 实际wrapper均End，无pin/confirm/补键 |
| pin后observe、repin、篡改观察PNG | 实际wrapper均End，最多原1pin，不能替换固定对象 |
| 截图阶段异步launch/unknown/End注入 | 实际wrapper/helper拒绝并End，0附加POST |
| 丢失confirm回复 | server只处理1confirm；wrapper保持未知并End，不重发 |
| 原20秒自然到期后再次observe | 未重置或伪造时钟，约等待原剩余19.2秒后实际调用拒绝/End，0pin/confirm |

8095.8ms是**此离线fixture的工具/等待/模拟审阅流程耗时**，不是固件真实性能指标。测试使用已知PNG的断言只充当fixture oracle，生产流程没有颜色/SHA白名单自动判通过。另通过view_image实际核看本轮3张截图和固定PNG：前两张MOCK动画色块、第三张完整Setup > Area/Date、独立固定图橙色Area/Date/Time Setting和Language English；这只说明fixture产物可见内容，操作语义仍为MOCK。[文件QA](evidence/IMAGE-ARTIFACT-QA.md)。

汇总字段原名observation_hashes实际存显示帧SHA，现更名displayed_frame_SHAs_before_observations，另列actual_observation_screenshot_SHAs；原生成汇总副本、修正哈希/原因保留在[SUMMARY-FIELD-CORRECTION](evidence/SUMMARY-FIELD-CORRECTION.json)。原截图、observation-result、process回执均未改写。两个同目录case曾复用observation.json，首case数据一直保留在BROWSER-RESULT，现另导出delayed-timing-observation.json；未来测试源只改为不同case文件名，无生产/验证行为变化。

## 失败原件与边界

- browser-attempt01：原Blob读取方案首次observe失败，只有RuntimeError摘要；按原End清理，0通过case。
- browser-attempt02：补充具体eval原始stderr后，定位fetch(blob:)处Failed to fetch；原server CSP的connect-src仅self、img-src才允许blob。结合源码推断CSP是原因，未声称捕获了CSP console事件。最终改真实截图而不改PAGE/server/CSP。两轮错误原件均保留。
- browser-attempt03：完整4.5s首步通过（alarm8004.2ms），下一步首次local合并门拒绝；旧cached input_received可仍true的条件不适合新accepted后的短暂同步。失败时没有逐谓词现场快照，不能排除同时条件。候选改为只在新accepted、同nonce/expected step且awaitingStep表明新step待同步时允许有限只读等待；最终返回前仍要求当前step的fresh/PAGE/native审阅阶段。增加失败字段诊断，attempt04连续step2通过，未改真实输入门。

## 冻结、准备与退出

实际prepare/preflight通过：r25清单pin和594项、r24清单pin和151项、r21清单pin2项和145项（含manifest本身）/source40、固定14项、真实QEMU全部一致。912个既有输入前后哈希不变，额外菜单fixture PNG独立前后匹配。33个生产候选源固定在CANDIDATE-SOURCE-FREEZE.json，原输入/差分在INPUTS-BEFORE/AFTER、SOURCE-REUSE、MINIMAL.diff；全部交付见SHA256SUMS。

实际runner import-only（未执行main）确认own→r21→ROOT路径和5关键模块__file__/SHA；全部新旧生产Python AST、JS node语法、PAGE/计划原SHA通过。[IMPORT-STATIC-RESULT](evidence/IMPORT-STATIC-RESULT.json)。prepare的LOCAL-SOURCE-FREEZE包含所有新增helper/flow/read文件，CLI模板含observe/pin/reject/独立confirm。

[FINAL-CLEANUP](evidence/FINAL-CLEANUP.json)重核4轮fixture service/browser均退出：最终service PID65909、port58342以及记录的134个browser PID均不存在，端口connect拒绝且lsof无监听；前三轮失败也有原独立退出回执。fixture中fake-run final receipt显式标MOCK，不能充当真实QEMU收尾证明。

剩余工作是协调端另行统一真实8步与后续可用性验收。本轮没有真实VM、部署、补键或追溯确认。
