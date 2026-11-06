# FX3 Start 调用者、返回层与错误回调记录

2026-10-27，仅 Mac 的 Unicorn 客体。**原单流 Start 调用者提供 128 字节参数和非空 48 字节回复区，期待事件为 `0x1003`。局部 API 返回值不能单独作为编码成功依据；请求还关联四条错误回调记录。** 新增 22 例、106 个有界片段，全部通过。没有运行相机接口、Windows、UU、真实线程服务或硬件编码。

## 原调用点和参数

执行原 ExecEncStart 序言与回复清零；GPS/元数据 helper 入口前停止。随后从独立声明的 post-GPS 帧执行原 128 字节 memset、SetEncStartParam 原字段写入和返回，直至原 Codec::EncStart 入口前停止。原调用点传入 CodecType `0x20`、声明 FileFormat 15、count 1、ViewId 0，以及栈内非空回复指针。

本轮输入为明确的人工 56 字节请求，不是自然队列输出。原参数区全部字节由原清零与原构建器产生，但这不代表 GPS、缓冲、实际实例、正确 MAIN 配置或硬件已经准备好。FileFormat 15 也不能单独证明目标 HD HEVC42010 主录。

**字段语义更正：** 原 RecStart 从 GOT `2fafd0` 取得 `mpr::s_thumbnailId`（ELF `375505`，1字节），经 EnqueueExecEncStart 输入低8位、请求 `+2`，到 Start 参数 `+0x5c`。它是缩略图编号，不能当作配置代次。初始执行脚本保留 `seq`／`sequence_byte_at_Start5c` 这一测试标签以匹配已执行源码和原始回执；该标签的语义以本轮来源审计及诊断约束中的 thumbnailId 更正为准。此前其它 STOP 包中独立命名的 seq_id 不在此更正范围。

Start `+0x5a` 字节来自请求 `+1`；原 Enqueue 代码的静态来源是 ConvertWriterIdListForShotId。该转换及真实 writer 列表本轮未执行。

## 三层结果必须分别观察

| 独立声明的条件等待返回 | 独立声明的回复 `+0x14` | 原等待后 sender 布尔值 | 原 Codec 等待后返回码 |
| --- | --- | --- | --- |
| 0 | 0 或 2 | 1 | 0 |
| 5 | 0 或 2 | 0 | 2 |

这张表只覆盖明确声明的 post-send/post-wait/post-unlock/post-log 帧。分配、真正发送、等待、唤醒、回复到达、锁和日志本体没有执行；**不是正常回复或真实错误被相机忽略的复现，也不是 Sony 缺陷结论。** 本轮证明的是这些局部返回指令没有用所声明的回复状态字来区分结果，诊断不能只记录返回 0。

原 GetExpEvt 对 `(MID0x210, command1)` 产生 `0x1003`。原 ConvertAvconEvent 对人工 `(MID0x4e0, sub3)` 也产生 `0x1003`，对 sub2 产生 1。没有执行实际 Start 回复生产者，也没有证明真实消息会以这些声明条件到达。不能把 Open 的期待 `0x1001` 套用到 Start。

48 字节是本轮原调用者的回复存储范围，不能直接当作实际 Start 线上的有效载荷长度；捕获时仍须记录实际长度、分配范围和寿命。

## 请求如何关联错误处理记录

原 ExecEncStart 读取请求 `+0x30` 的指针。声明 Codec 返回 0 后，原 `fc4c0` 在锁后片段向四条、步长 `0x60` 的记录各 `+0x10` 存入 `mpr::NotifyMovieRecError`；声明返回 2 时，把同一记录指针和错误码传至 `fc29c` 前停止。

指针的原 Enqueue 静态来源是 MovieRecInfo `+0xa48`。本轮记录区域是人工对象，没有证明它属于当前 MAIN、已激活、尚存活或与当前配置同代；实际错误分发、NotifyMovieRecError 和全部回调均未执行。后续应追该区域的创建/登记/复用和队列执行者，不能把指针相同当作实例或生命周期验收。

## 证据与下一步

- [原 Start/返回结果](run-native-Start-caller-20261027/start-caller-results.json)：18例94片段。
- [错误回调记录结果](run-native-Start-owner-20261027/start-owner-results.json)：4例12片段；复用前94片段结果，没有重复运行。
- [诊断约束](diagnostic-contract.json) · [来源审计](source-and-scope-audit.json) · [复核](completed-evidence-review.json)
- [Start 脚本](start_caller.py) · [回调记录脚本](start_owner.py)

逐片段核对允许区之外的栈、scratch 和映射镜像不变；纯函数/原返回片段检查保存寄存器及 SP。原 libc 和原参数构建器执行，未知依赖在入口前停止，未提供返回成功桩。

下一步追四条回调记录的实际生产者、原 execRecMovie 工作队列及正常 Start 回复到调用者的关联，同时补录制实例/配置的一致性依据。目标仍为经典 FX3 7.02、1920×1080、30000/1001、HEVC42010约16Mbps，精确30另列。实际主录、音画/长录/冷启动、同机备份与受限恢复回读、独立救援未验收；全部16项状态和权限保持，未修改旧前后端或固件。
