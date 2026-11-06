# FX3 r25 恢复观察离线候选

**offline candidate passed；runtime / 真实八步仍待验。** 只写本 r25 新目录，未部署、未启动真实 QEMU，FX6/实机/USB/SD未触及。原 r24 真实轮仍为 **7 keys / 7 confirm，第8次 not_posted，整体失败**，没有把离线结果改写成真实菜单通过。

## 改动与边界

仅派生5个既有源文件（operate、preflight、recovery_tools/read/cancel），新增 recovery_observation 与 recovery_guard。原 r24 PAGE/server/runner、正常postkey快照/确认、planned click、deadline、initial standby capture逐字节相同；PAGE canonical SHA仍为 852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b。NAVIGATION-PLAN SHA仍为 4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f。

取消前、取消后均返回独立新采集且哈希固定的 qualified_recovery_observation；保留全部前后状态，不再要求跨截图 SHA/gen相等，绝不标 current firmware frame、不指定单一generation、不声称像素因果性。每端点读fresh status并复核PAGE/document/launch/step/完整attempt/同nonce alarm及ready、无unknown/End等门；fresh状态与历史画面不作SHA/gen等值比较。下一次显式 recovery_review 固定PNG/receipt/cancel/binding/ledger链接，随后另一显式click单次消费审阅并新建nonce；原实时按键门及20秒和8/10/2预算完全保留。恢复图不能产生postkey确认或后续正常prerequisite。

端点只是有限观测，不覆盖截图区间未观察到的瞬变，不构成server/guest原子事务；这张历史恢复图不是新按键许可。同步片段含义参照 [MDN execution model](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model)，时间上下文参照 [MDN Window.performance](https://developer.mozilla.org/en-US/docs/Web/API/Window/performance)（2026-11-04核查）；细节见 [CONTRACT.md](CONTRACT.md)。

## 针对性验证

最终证据：[恢复验证11组](evidence/recovery-attempt05/BROWSER-RESULT.json)，[逐次HTTP/native mock跟踪](evidence/recovery-attempt05/HTTP-PROTOCOL-TRACE.json)。实际调用 runtime-wrapper/operate.py 的 __main__ 完成 click → 原PAGE not_posted归因 → 取消前图返回 → 另一调用审阅/cancel → 取消后新图返回 → 另一调用recovery_review → 新nonce click → postkey capture → 再单独confirm。视觉语义及native接收均为明确MOCK，不是人工看图或真实固件效果证明。

| 场景 | 结果 |
|---|---|
| 两次显式planned click | 首次0 key POST；合计1 key POST、1 confirm POST、1 mock native down/up |
| 取消前/后实际截图间强制A/B切换 | 两处SHA/gen均不同，旧等值断言必失败；新观察通过 |
| 正常postkey历史确认 | 快照gen5，确认时live gen6，精确原快照确认通过 |
| 前后document/launch/step/attempt变化 | 实际capture CLI均拒绝；launch/step不等待PAGE缓存刷新，fresh GET检出 |
| unknown/End | 实际capture CLI拒绝；实际wrapper unknown点击走End，0额外POST/native |
| 错误nonce | 实际cancel CLI拒绝，原alarm仍armed，未取消 |
| 同步重复恢复、2recoveries预算、10attempts预算 | 实际CLI拒绝，无新cancel/click |
| 已消费恢复审阅重用 | 实际wrapper recovery_review拒绝并End，无额外POST |
| PNG、观察receipt、cancel receipt篡改 | 实际host guard子进程拒绝（原始process回执保留） |
| cancel赋值/日志两个时刻、伪造elapsed/nonce | 原不同日志时刻可通过，两个伪造回执在真实JS reader拒绝 |

[原 r24 postkey server回归15组](evidence/postkey-regression/SERVER-RESULT.json)与[实际浏览器/helper/wrapper回归6组](evidence/postkey-regression/BROWSER-RESULT.json)全部通过，含动态发布9.3066秒、64缓存淘汰后精确快照确认、原server gate拒绝、丢失确认回包/迟到确认与End/迟到pin不能复活。

## 过程中真实失败全部保留

- evidence/recovery：fixture用第二个同session eval解锁挂起GET，被串行等待阻塞；未获得产品恢复正链，0 case通过，退出回执保留。后改为仅fixture独有GET屏障驱动切帧。
- recovery-attempt02：取消前动态观察通过，新增guard误要求 cancelled event.performance_ms == current.cancelled_ms。原deadline先赋值后另读日志时间，真实差0.1ms；修复为精确elapsed关联、严格先后次序，不加epsilon、不改timer。
- recovery-attempt03：完整恢复正链通过；launch服务端变化尚未进入PAGE缓存时负例意外qualified。新增每端点fresh status生命周期检查，保留该负例原件，没有仅等缓存后改称通过。
- recovery-attempt04：工具JSON对象数字重编码导致宿主相加1 ULP假失败（due 23575.60000002384、armed 3575.600000023842）。20秒精确谓词改在浏览器同片段判断，取消身份以浏览器JSON.stringify字符串原样往返；不放宽时间门。
- verify.stderr.txt：首次import-only审计忘传必需的FX3_NAV_RUN_DIR而退出，无VM启动；带最终fixture环境的verify-attempt02通过。上述失败原始stdout/stderr/PNG/JSON均保留。

## 冻结与清理

实际prepare/preflight通过，检查r21清单pin2项、全部145项（含manifest本身）、原source40、r24清单pin及全部151项、固定14项和真实QEMU。输入前后317个哈希完全相同；额外菜单PNG fixture独立前后匹配。实际runner import-only核验own→r21→ROOT顺序和5个关键模块__file__/SHA，未进入runner main；[IMPORT-STATIC-RESULT](evidence/IMPORT-STATIC-RESULT.json)。

30个候选生产源在 CANDIDATE-SOURCE-FREEZE.json 固定，差分见 MINIMAL.diff。实际准备产生的 LOCAL-SOURCE-FREEZE覆盖当前源；最终preflight及import和编译/node语法核验通过。全部交付在 SHA256SUMS；清单本身摘要由最终回传给协调员。

[FINAL-CLEANUP](evidence/FINAL-CLEANUP.json)独立重查6次自有service测试收尾（含4次失败与2次成功）：所有service/browser PID不存在，所有端口connect拒绝且lsof无监听。最终恢复fixture service PID59789 / port53666，browser24个PID均回收；postkey回归另有独立退出证据。fixture内fake-run final receipt明确标MOCK，不充当真实QEMU清理证据。

剩余工作仅是协调端另行统一真实VM/八步验收；本候选不绕过动画导致的合法PAGE拒绝，也不保证下一次点击一定入队。
