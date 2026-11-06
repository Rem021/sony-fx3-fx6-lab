# FX3：合法 STOP、PCIATU 清理与完成通知

本轮14段原代码片段的离线验证通过。STOP状态表中的动作会调用**PCIATU图像缓冲映射清理**，不能把这个调用直接当成硬件停止或全局代码退出证明。原日志同时将STOP结果+4/+5绑定为`seq_id`、`forced_stop_flag`；前者是8位值，也被传作本地参数索引键，尚无当前请求/配置代次的完整关联。

没有连接相机或Windows，没有运行机身模块、改变权限或刷写。完整STOP迁移、硬件编码、主录成片与同机恢复均未验证。

## 合法状态的完整路径仍停在真实依赖前

| STOP输入状态 | 原表目的状态 | 原动作 | 本轮完整包装函数的实际终点 |
|---|---|---|---|
| 8 ENC_STOP_WAIT | 10 ENC_INFRA_STOP_WAIT | 0x24cb90 | 迁移诊断0x27d528之前 |
| 9 ENC_ENC_STOP_WAIT | 4 ENC_IDLE | 0x24cbb0 | 迁移诊断0x27d528之前 |

目的状态是原表选择结果，不是已完成迁移。两次包装函数执行中，状态字尚未更新，动作也尚未进入。原顺序0x2534f0起先检查guard，经退出动作与迁移诊断后写状态，再调用事件动作及新状态entry。因此，原状态字即便在别的运行中变为IDLE，也必须结合动作、entry、返回和真实同步确认；本轮没有通过跳过诊断来制造完整成功。

另从两处原动作入口分别执行，均沿原代码以`outer+0x31f70`调用0x22e638，在运行时锁等待0x2ef4c之前停止。未获取真实锁。

## 清理的是映射，局部清零不是底层回执

0x22e638的原源文件字符串是`common/imola_common_pciatu_map.cpp`，诊断明确写`unmap_yc`与`pciatu_unmap`。原函数先获取锁并记录诊断；这些运行时依赖尚未绑定。

本轮独立执行0x22e6b8之后的原片段，输入对象、守卫和保存栈帧均明确标为fixture，前面的获取锁/诊断没有执行：

- 映射标志为0，或句柄为`0xffffffff`时，原分支清本地标志、将句柄设为无效并返回1，**没有调用底层unmap服务**。
- 标志为1且句柄有效时，原分支到达0x2f604底层unmap入口即停止，本地映射仍保留；未伪造该服务返回值。
- 守卫“已持有”输入为1的对照里，本地映射及守卫字节已清零，仍在运行时释放锁0x2ef60之前停止。这个输入字节不是实际获得锁的证据。
- +0x34计数在这些分支前增加，32位溢出会回到0；它不能充当服务成功次数或安全退出证明。

这些是人工输入下的原分支行为，不是机身已发生故障、原厂存在漏洞或某种刷机恢复能力的证明。实际映射成功/失败后的全程清理、全局计数更新、锁获取/释放及硬件状态仍待验证。

## STOP结果字段及通知包

原0x225934识别type3后，将消息+0xa复制到结果+4，同时以该字节作第一次参数索引归还的键；消息+0xb复制到结果+5。本轮在归还函数入口停止。

随后独立从0x24cc14执行原格式化片段，读取同一份解析结果，将两字节作为原日志参数：

```text
[IMLENCSTAT]enc_stop_done seq_id:%d forced_stop_flag:%d
```

`seq_id=255/0`及`forced_stop_flag=1/0x56`两组输入均原样传递。0x56是人工非规范字节对照，不能据此推断真实flag允许值。日志函数没有执行，也未执行高层完整STOP动作。8位seq_id的重用、回绕、生产者、锁与请求生命周期均须追踪；它不是已经证明的配置epoch或全局唯一完成凭据。

另两段原片段构造并准备发送`VIDEO_ENC_STOP_COMP`：CID`0x2103`、MID`0x113`、长度12字节，payload仅包含通道号。通道7输入的原构造结果为`032113010c00000007000000`。原getter与发送传参已执行，实际发送0x27dab4之前停止。

这两个片段之间仍隔着未执行的强制诊断；没有声称整段动作或消息投递成功。包本身没有seq_id或配置epoch，是否由外层会话、接收状态或其它机制完成关联，仍须继续查证。不能从该局部包结构推断整个原系统缺少关联校验。

## 回执与后续

- [正式结果](run-20261025/stop-completion-results.json)、[摘要](run-20261025/summary.json)、[执行源指纹](run-20261025/source-receipt.json)。
- [脚本](stop_completion.py)、[同agent逐项复核](coordinator-observations.json)、[后续入口](next-stop-completion-anchors.json)、[封存清单](final-receipt.json)。

在项目根复现，输出目录必须不存在：

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage44-stop-unmap-and-completion/stop_completion.py --output work/sony-firmware-20261024/stage44-stop-unmap-and-completion/run-new
```

下一步追踪MID0x113接收端、ENC_INFRA_STOP_WAIT的基础层完成条件、seq_id生产/重用与真实共享同步，以及合法STOP的完整诊断/动作/entry和所有代码执行者退出。保留52字节初始化、真实start-input与有效HAL请求、模型/query/cache/mux统一、实机主录/音画/长录/温度、健康同机备份、受限恢复与回读、WBI/冷启动及独立救援全部验收缺口。目标保持进行中。
