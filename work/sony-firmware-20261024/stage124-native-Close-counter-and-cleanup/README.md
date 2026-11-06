# FX3 Close 计数门控与清理结果

2026-10-27，仅 Mac 的 Unicorn 客体。**18例、108个有界片段通过：原 ExecEncClose 可因剩余记录计数非零而跳过 Codec Close；后续模式字清零也不能单独证明 DMM 释放成功。** 本轮未访问相机、Windows、UU、媒体或真实线程服务，未修改固件及旧前后端。

## 原计数确实参与 Close 选择

原 `s_recordCounter` 是4字节对象（ELF `376158`），原 GetRecordCounter/SetRecordCounter 按声明索引读写1字节。原 ExecEncClose 根据 s_movieRecInfo 的索引列表求和，并按请求 `+0x24` 控制字选择是否扣减请求 `+0x20` 对应计数。

本轮从原 Close 序言开始，原回复区清零；在明确声明的日志/锁间隙之间，实际执行原 GetRecordCounter、SetRecordCounter、调用者求和/扣减和选择，没有提供计数返回桩。声明的全局列表只含一个有效索引，各例分别覆盖索引0..3。

| 初始计数 | 请求控制字 `+0x24` | 原计数结果 | 原局部分支 |
| --- | --- | --- | --- |
| 0 | 0 | 0 | 准备单流 Codec Close |
| 1 | 0 | 0 | 原扣减后准备单流 Codec Close |
| 2 | 0 | 1 | 跳过底层 Codec Close |
| 255 | 1 | 255 | 不扣减，跳过底层 Codec Close |

255是人工字节边界控制，不代表机身会自然达到该计数。计数非零跳过关闭是原分支，不把它判为异常；这些计数也没有被当作所有硬件消费者的完整引用数。

在准备 Close 的分支，原调用点给出16字节清零参数、CodecType32、声明 FileFormat15、count1、ViewId0，以及原栈内非空48字节回复区。在实际 Codec::EncClose 入口前停止，没有关闭编码器。

## Close 回复与清理标志要分别记录

原 GetExpEvt 对 `(MID0x210, command4)` 生成 `0x1006`；原 ConvertAvconEvent 对人工 `(MID0x4e0, sub9)` 也生成 `0x1006`，对 sub8 生成1。没有执行真正 Close 回复生产或到达，不与 Open/Start 的期待事件混用。

独立 post-FreeDmmMemory 尾部实验明确声明低字节结果0或1。结果0走错误诊断路径，结果1直接走公共尾部；两者都由原指令清除 s_movieRecInfo `+0xa6c` 控制字。**实际 FreeDmmMemory、流缓冲删除、Codec Close、日志和锁都未执行。** 清零不是释放成功、全体退出或恢复完成证明；也不能由人工输入推断 Sony 存在实际泄漏或忽略错误。

原调用顺序还显示：ExecEncClose 在 s_integRecordMovieLock 下进入计数处理，计数 getter/setter 又使用 s_RecCounterLock。这里只核对原调用和对象，没有执行锁或验证完整锁层级。诊断不能在未知线程/已持锁上下文中盲目组合这些 API。

## 验证边界与下一步

所有“当前”列表、计数和请求都是人工声明数据，不是健康机快照；模式控制字的静态 Enqueue 来源是 MovieRecInfo `+0xa6c`。原文件和指令未改，只有 guest 数据段中声明的计数字节/控制字允许原代码写入。栈、scratch 和映射镜像在允许区之外逐片段核对不变。

- [通过结果](run-native-Close-counter-20261027/close-counter-results.json) · [执行脚本](close_counter.py)
- [诊断约束](diagnostic-contract.json) · [来源及锁对象审计](source-and-scope-audit.json) · [复核](completed-evidence-review.json)

下一步核对完整 Close 消费、实际回复状态、流缓冲/DMM释放结果及记录的上游关闭条件，结合前几轮的队列/在途回调寿命。目标保持经典 FX3 7.02、1920×1080、30000/1001、HEVC42010约16Mbps，精确30另列。实录、音画/长录/冷启动、同机备份与受限恢复回读、独立救援未验收；16项状态和设备权限保持。
