# r26 未固定观察、显式固定与独立确认

本合同只约束宿主操作流程。r25真实轮8accepted/7confirm、第8次首个固定图仍待机，整体失败保留；不追补确认。r26未启动真实VM、未部署。

## 不变部分

原r25 PAGE/server/CSP、单次snapshot生命周期、runner/native ACK observer、planned click、deadline/20s、初始待机和未入队恢复helper逐字节复用。PAGE canonical SHA仍为852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b。NAVIGATION-PLAN SHA仍为4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f；最多8accepted、10次显式attempt、2次归因恢复且每步一次。FX3 QEMU/kernel/DTB/CPU4×cortex-a35/5120MiB/MTTCG/noicount等固定平台不变。

## 未固定观察

accepted后的click返回 qualified_unpinned_postkey_observation / fx3-postkey-observation-r26-v1，不调用pin或confirm，不占用server单次review snapshot。随后每个observe是另一明确调用，必须填写实际看上一张观察图后“仍为正常过渡，需要再观察”的判断；最多3次含click后的首次。每次先fsync不可重用reservation，结果未知立即terminal/原End；不自动循环输出、重试或重置timer。

观察使用真实agent-browser screenshot，保留实际PNG、字节数、SHA256、独立目录、reservation ID、session/唯一tab/URL和宿主起止时间。PNG SHA只绑定截图字节，不等同frame PNG SHA。before/after分别保留显示SHA/gen/seq和server状态，允许它们变化；firmware_generation=null、snapshot_pinned=false、input_permission=false、postkey_confirmation=false，不主张截图瞬间帧、像素因果或UI处理已完成。

每个端点先验PAGE脚本指纹，读fresh /api/status，随后同步无await复核同document对象/脚本、timeOrigin/document UUID、run incarnation、launch、step、已接受attempt、同nonce/due/armed20s原alarm、未到期、无unknown/error/End/已有snapshot。截图前后各核同session唯一tab和精确loopback URL。返回观察前/后都要求当前step对应review_required/input_received/review_step阶段、无busy、有效已加载画面；这在冻结runner中只由匹配native down/up且sender up后分类进入，不表示handler完成。新accepted后PAGE短暂仍缓存前一步时仅允许有限只读同步，最终返回前必须处于本步完整阶段。端点/HTTP/截图/guest并不原子，区间内未被观察的变化仍不能排除，因此观察图始终不提供按键许可。

原CSP connect-src只允许self，早期Blob fetch方案失败原件保留；最终截图方案不改CSP。依据：[MDN CSP connect-src](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src)说明fetch受此指令控制；[JavaScript execution model](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model)说明job边界不跨await/外部截图（2026-11-04核查）。CSP作为Blob失败原因是结合源码和Failed-to-fetch错误的推断，不伪称已捕获浏览器CSP console事件。

## 显式pin与重新看图确认

操作agent实际看最新观察图完整后，另一单独pin调用才执行原r25 review_snapshot_cli capture / 原PAGE按钮一次。先核最新观察receipt和实际PNG哈希、当前身份和未固定状态，再fsync pin_reserved_unknown；丢包也不重发。返回新的精确固定PNG，与之前观察PNG严格区分。操作agent必须重新实际看该固定PNG，再独立confirm，不能复用前一张图的语义判断。

固定后只允许原精确confirm；不能observe、repin、替换图或失效后复活。观察图冒充capture、无pin直接confirm、语义不符、身份变化、次数耗尽/到期、unknown/End、confirm回包丢失，均进入持久run terminal锁并调用原End；错误后新读帧不能恢复。显式reject用于操作agent看到错误/不确定语义时立即End。不会自动加键、重新武装或放宽server gate。

## 与r25恢复观察区分

r25 qualified_recovery_observation属于已证明未入队的取消前/后观察，只能支持原独立recovery_cancel、recovery_review及下一次显式新nonce planned click。它不能被r26 postkey flow当作已接受按键的观察或确认；r26观察同样不能充当固定snapshot、postkey prerequisite或恢复许可。

冻结新源、prepare/preflight/import、原输入清单与进程端口退出均在REPORT和evidence。离线native/语义判断为MOCK；成功只证明候选流程，真实八步与后续可用性仍待统一VM验收。
