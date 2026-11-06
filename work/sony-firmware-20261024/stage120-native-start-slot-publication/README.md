# FX3 槽位选择如何进入录制状态

2026-10-27，仅 Mac 的 Unicorn 客体。**原状态 `+0x0c + 槽位×16` 字节来自 GetStartSlotId 的选择记录；本次 RecStart 的编码 Open/Start 排队调用在这个函数之后。另确认 GetSlotID 会登记新映射，不能因名称带 Get 就把它加入只读诊断。**

本轮通过 18 个案例、62 个有界执行片段。它们是原代码的字段来源和调用顺序证据，没有实际录制、真实空闲、编码器启动或配置代次证明。没有访问 Windows、UU、相机或媒体，没有修改固件、旧前端或阶段 75 后端。

## 状态字节的原来源

原 GetStartSlotId（ELF `dc194`）使用 8 字节的槽位/布尔记录。原 append helper `dc168` 在声明的已分配容量内复制记录。原调用者 `dc47c..dc4c4` 随后通过 ForUpdate 取状态，将每条记录的布尔字节写至状态结构的 `+0x0c + slot*16`，并调用原 SetMovieRecStatus。

本轮执行了原 append、GetStartSlotId 序言、原构造器、ForUpdate 的复制/返回、原调用者循环、原 SetMovieRecStatus 比较/复制与原解锁包装器；pthread 写锁、解锁、日志和 SetIssueEvent 本体仍在进入前停止。初始状态、已接受的选择结果及锁间隙均明确为人工前提。没有执行介质可用性检查、实际选择、vector 扩容、完整 GetStartSlotId 或完整 RecStart。

两种填充值分别覆盖单槽、混合布尔、四槽乱序、重复槽位结构控制。原循环只改变被选记录对应的状态字节；重复槽位控制呈现最后一次写入的结果，**不证明真实选择器会产生重复记录**。所有槽位输入明确限定为 0..3，没有把未见的完整调用者校验视为已经通过。

原 RecStart 在 `dc690` 调用 GetStartSlotId，检查其返回后，稍后在 `dc7f8`（有条件）排队 Open、在 `dc82c` 排队 Start。这里的顺序不能证明排队完成或硬件执行；也不排除复用已经打开的编码器。`dc840` 的 MovieRecStarted 事件同样只是本轮静态识别的排队调用。

原 ProcessWriterEvtStopCmp 在部分分支中清除同一结构的相应字节。本轮只保留其静态上下文和偏移关系，没有执行 writer 停止、编码器停止、全体消费者退出或释放，不能把单字节清零当作安全恢复完成。

## GetSlotID 的写入副作用

原 `mpr::msidconv::GetSlotID` 位于 `9a95c`，维护四条、步长 `0x80` 的转换记录，介质 ID 在每条 `+0x7c`：

| 声明条件 | 原函数结果 |
| --- | --- |
| 已存在介质 ID | 返回对应槽位，不改表 |
| 未存在，且有 ID 为 `0xffffffff` 的空位 | 写入新 ID，再返回该槽位 |
| 刚登记过的 ID 再查询 | 返回同一槽位，不再写表 |
| 表满且没有匹配项 | 返回 `0xffffffff`，不改表 |

两种填充值各连续执行 5 次原函数；检查仅声明的新 ID 字段可改变，剩余 512 字节映射记录和寄存器/栈保持。对象是人工转换表，**不是相机当前介质记录**。这些介质 ID 与 USB VID/PID、设备序列号不是同一类标识，不能相互替代。

## 对下一步的影响

[更新后的诊断约束](diagnostic-contract.json) 保持不可部署：排除会保留锁的 ForUpdate，以及可能登记映射的 GetSlotID；状态里的槽位字节不用于判断硬件已经开始或结束。真实诊断仍需证明当前介质 ID、已有槽位、录制实例、配置与锁域的关联。

下一步应沿原 Open/Start 消费者和完成事件追同一录制实例，并继续核对槽位记录的实际来源及写者同步。主录目标仍为经典 FX3 7.02、1920×1080、30000/1001、HEVC42010 约16Mbps；精确30另列。实录成片、音画/长录/冷启动、同机备份与受限恢复回读、独立救援全部未验收，16项状态与权限保持。

- [52片段主结果](run-native-slot-publication-20261027/slot-publication-results.json) · [10片段映射结果](run-native-slot-map-20261027/slot-map-results.json)
- [原执行脚本](slot_publication.py) · [映射脚本](slot_map.py) · [原来源审计](source-and-scope-audit.json) · [封存复核](completed-evidence-review.json)

阶段119已核对的 Sony SDK 公共支持结论沿用原范围；没有因此取得具体 FX3 私有状态 API、额外权限或恢复能力。本轮新结论来自已固定哈希的原厂 `libmpr.so` 指令和客体执行，不依赖论坛推测。
