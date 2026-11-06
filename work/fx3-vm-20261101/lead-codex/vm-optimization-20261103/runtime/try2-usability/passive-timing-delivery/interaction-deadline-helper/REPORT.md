# 测试专用20秒截止辅助：离线验证通过，未部署

仅在专用单标签 `fx3-deadline-*` 会话、原文匹配的 `http://127.0.0.1:PORT/`、本次launch UUID、r12 PAGE脚本指纹及DOM/End handler身份都符合时安装。生产固定20,000ms，nonce一次性；过期只调用当前页面完整可见的原End.click。没有直接HTTP、固件键、自动确认/重发或修改产品文件。

**最短操作流程**（具体命令见 [OPERATION.md](OPERATION.md)）：
1. 独占测试session固定1280×1200，先看完整图和End同时在视口；核URL/launch，显式install。
2. 每个目标用新UUID，在目标键之前显式arm，保存armed/nonce/due；worker再按真实页面键。武装期间不滚动、改viewport、导航或关闭。
3. 亲看完整语义目标并完成必要的人工看图确认/ready核验后，显式cancel同nonce，保存cancelled+nonce+elapsed<20000回执；未达目标/失败先End，不能提前cancel再重武装续时。

[deadline.js](deadline.js) 是页面内辅助；[deadline_cli.py](deadline_cli.py) 包装器只读核单标签/当前URL，显式调用install/arm/cancel/status/dispose。旧nonce不解除新alarm；同/不同nonce在已有alarm上都不能改变原due；重复安装也不替换timer。到期sealed，已End中/终态不再click；辅助不修改PAGE的状态、错误显示或输入准入。

## 真实Chrome离线验证

[最终RESULT.json](evidence-final/RESULT.json)：11例passed，真实r12 PAGE/TrialState与原HTTP handler，橙色12×12测试fixture，不是guest/VM画面。短版 **1200ms** 仅从生产JS唯一20,000常量替换生成，见 [短版](evidence-final/deadline-short.js)；另有原生产20秒包装器arm/cancel/dispose样例。

| 用例 | key / confirm / Stop请求 | 定时End实测elapsed ms | 结果 |
|---|---:|---:|---|
| uncancelled_once | 0 / 0 / 1 | 1203.200 | passed |
| timely_cancel | 0 / 0 / 0 | 无timer End | passed |
| old_nonce_does_not_cancel_new | 0 / 0 / 1 | 1201.600 | passed |
| repeat_arm_no_extension | 0 / 0 / 1 | 1202.600 | passed |
| wrong_URL_refused | 0 / 0 / 0 | 无timer End | passed |
| wrong_DOM_refused | 0 / 0 / 0 | 无timer End | passed |
| real_key_pending_End_enabled | 1 / 0 / 1 | 1202.300 | passed |
| existing_End_not_clicked_twice | 0 / 0 / 1 | 无timer End | passed |
| terminal_not_reversed | 0 / 0 / 0 | 无timer End | passed |
| blocked_event_loop_is_not_hard_deadline | 0 / 0 / 1 | 1917.200 | passed |
| production_20s_wrapper_arm_cancel | 0 / 0 / 0 | 无timer End | passed |

pending例在闹钟武装后，测试代码明确点击一次MENU，真实submit留下pending=1/busy=true；武装后轮询亲证 key disabled、End仍enabled，到期只增加1 Stop，没有辅助新增key或confirm。最初evidence/的pending_observation采样早于等待busy，显示false；已保留该初版证据。最终evidence-final先await再采样/断言busy=true；另补了轻量End DOM身份复核后整套复核通过，未改r12。

终态例的1个final_ack是原PAGE正常收终态回执，区别于0个confirm。生产20s例current.deadline_ms=20000、显式同nonce cancelled/elapsed回执在RESULT.extra内，Stop/key/confirm均0；未等待20秒到期，不将1200ms实测写成生产20秒实跑。

## 限制与清理

- 浏览器timer不是硬实时。阻塞事件循环1800ms后，1200ms闹钟延迟才执行；晚cancel不能撤掉已过due的alarm。系统挂起、后台节流、浏览器卡死/关闭/导航均可能使截止无效，不保证30秒硬界限。
- End必须始终完整可见；固定视口是操作合同。URL/document/DOM/handler或可见性失配只记录拒绝，不改点其他标签、不自动滚动。`end_click`不等于HTTPACK或VM回收，后续真实运行仍核原恢复/退出/锁/finalACK。
- r12 PAGE脚本canonical SHA为 `fe56b4846b9cb0c386216b38cc7e5b0707f616cab5ee6a526a217e68ce114478`，仅规范化随机token行；不记录token。未来PAGE不同先另审，不能临时跳过pin。
- [CLEANUP.json](CLEANUP.json)：所有fixture服务器线程join、已记录9个fixture端口关闭，专属浏览器session inactive/pid=null；没有自建守护进程/launchd/后台遗留。22个r12冻结源仍匹配，实际module前后SHA一致。
- 本任务没有启动VM、读取/改变guest平台、改旧run/r12/r13/入口/README/ledger；没有部署。只证明轻量真实浏览器条件下测试规约可用，未来VM运行须另授权。

[SHA256SUMS](SHA256SUMS) / [校验回执](HASH-CHECK.txt) 封存实现、规约、两版离线证据及截图。当前任务已完成；生产20秒到期与实际guest收尾尚未进行。
