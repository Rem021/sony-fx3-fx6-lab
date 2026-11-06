# FX3 MAIN、代理与编码器入口边界

本阶段把目标参数继续追到了编码库的消息身份和资源选择层。目标MAIN与同规格代理的核心视频字段相同，但**外层FileFormat、部分包字段和实际Open路径不能直接互换**。原指令片段通过，没有证明硬件EncOpen/Start成功。

## 新增原件与官方基线

从已核验的7.02 `nflasha15.img` 只读提取 `/lib/libInfraAvbbc.so`，未挂载或运行固件。镜像SHA256为 `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5`；新增库1,734,632字节，SHA256为 `87a2246084567abca0e43228b5289bc728839a13ab4251e92828ea4c463e3c26`。提取后重新核对镜像和库哈希，旧阶段原件没有改变。见[提取收据](extraction-receipt.json)。

Sony的经典FX3帮助指南明确列出XAVC HS HD代理：1920×1080、最高59.94p/50p、16或9Mbps、4:2:0 10bit、HEVC/H.265。[官方原文](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)（2026-10-25核对）。这支持同机已有对应代理编码链路，不能代替目标MAIN主录验收。本阶段没有拍摄代理或主片，也没有以代理方案缩减目标。

## 核心视频参数相同，外层身份不同

以此前确定的目标输入 `[VPC6, DefStruct质量6, FrameRate3]` 作合成输入，分别运行原 `SetEncOpenParam` 和 `SetEncOpenParam2`。缓冲区地址和未列出的运行标志为0，并非真实录制环境。

| 字段 | 目标MAIN | 同规格代理 |
|---|---:|---:|
| 包内视频codec，0x66 | 15 | 15 |
| 宽×高 | 1920×1080 | 1920×1080 |
| codec FramePerSec枚举，0x80 | 3 | 3 |
| 逐行标志，0x81 | 1 | 1 |
| MPR质量枚举，0x82 | 22 | 22 |
| chroma / bitdepth，0x94/0x95 | 0 / 1 | 0 / 1 |
| 外层Codec::FileFormat | 15 | 18 |

外层身份由原 `GetCodecInfoForCodec(VPC, StreamType)` 返回。6组对照包括HEVC的VPC5/6和AVC的VPC1，MAIN/proxy分别得到15/18、15/18、5/17。原入队标量片段把MAIN返回值写入 `exec+0x77c`，实际调用者再把它作为 `Codec::EncOpen` 的FileFormat参数。**外层15与包内codec15属于不同空间，数值相同不是身份绑定依据。**

原质量转换帮助函数对目标包中的22保持不变；本函数中只有输入188被转成57。5组纯原指令对照覆盖该分支和目标/其它质量值，没有以宿主代码填写转换结果。

完整0x98字节包并不相同。在本轮零运行标志前提下，与指针配套的3个16位字段分别为：

| 偏移 | MAIN | proxy |
|---|---:|---:|
| 0x28 | 1200 | 300 |
| 0x38 | 1200 | 600 |
| 0x48 | 768 | 235 |

未把这些字段的单位或所有权进一步猜作已知。另有0x7f字节为MAIN=0、proxy=2：原MAIN根据 `exec+0x760` 取0或2，proxy固定写2，所以不能把本轮差异推广到所有状态。

同一 `exec+0x760` 也控制完整执行者的单流/双流路径：为0时构造MAIN包并调用EncOpen；非0时构造MAIN及proxy包并调用EncOpen2。这里仅确认静态分支，未运行真实双流资源分配或录制。见[字段和路径复核](route-and-field-audit.json)。

## 消息结构的绑定与未执行区间

原 `CreateMessage` 把FileFormat写到PayloadMpr+0x1c；原发送片段用3组LDP/STP复制0x30字节。接收函数调用外部 `DataflowInfraMsg::GetMsg(out+8, 0x30)`，因此在这一复制契约成立时，对应的MPR_CMD字段为+0x24，包指针也相应位于+0x30。

本阶段运行了原发送复制与接收头部写入片段；固定内存取得、OSAL分配/发送/等待以及外部GetMsg没有运行。接收片段的payload是明确的输入前提，不能把这些分段拼成完整传输成功。

更下游的Astra SetParameter包含参数控制器虚调用、当前use-case、资源分配和命令对象构造。MC命令继续交给 `OsalSndMsg`，并有独立确认/完成流程。本阶段没有制造这些调用的返回值，也没有模拟成功的硬件回复。

## 资源选择不等于能力校验

对原 `NeedAcquire4KRsrc`、`NeedAcquire60pRsrc`、`GetExternalCodec` 做了18次调用，包括目标、匹配代理、HD59.94代理、已知原厂UHD59.94参数控制，以及非法枚举和诊断边界：

| 合成参数 | 4K资源 | 60p资源 | external-codec选择 |
|---|---:|---:|---:|
| 目标HD29.97 MAIN | 0 | 0 | 0 |
| 同规格proxy | 0 | 0 | 0 |
| HD59.94 proxy | 0 | 1 | 0 |
| 原厂UHD59.94参数控制 | 1 | 1 | 1 |

这些是相应原函数的返回数值，不是资源已获准、编码可用或设备接受的状态。把codec和帧率枚举故意改成0xff后，三个函数仍可都返回0，因此“无需4K/60p资源”不能用作支持性检查。

AV库的诊断开关是未解析的导入变量 `avbizPrintLevel`。本轮明确把这个只读输入绑定为客体中的0；改成1的控制停在原BizPrintf PLT，没有补AV日志返回值。该设置不是设备状态或编码能力的替代。

`SetAvailableFormat` 的原入口先读取机内backup字段，后面还有消息交互；本轮停在首个Read1Byte，不存在当前机身能力值。完整Codec::EncOpen入口停在未纳入执行范围的诊断帮助函数，完整SendMsgToAvbbc停在OSAL分配入口。这些是受限客体边界，不是实机拒绝或接受的证据。

## 字段更正

较早材料把包0x65标作 `file_format_65`。原MAIN在0xd1508、proxy在0xd1780写入的是 `GetCodecAudioFormat` 的返回值，不能用它替代本阶段绑定的外层 `Codec::FileFormat`。旧材料保留，当前来源标签改为 `GetCodecAudioFormat_result_65`。0x80和0x81继续分别使用codec FramePerSec枚举、逐行标志，不恢复旧的输入FrameRate/NTSC标签。

## 验证范围与下一步

本轮包括4个原参数包、6个身份转换、5个质量转换、2个原入队标量片段、2组消息片段（每组3段）、18次资源帮助函数和3个完整入口停止控制。MPR沿用已审查的诊断适配器：只记录诊断输入并令PC返回LR，不写返回寄存器或输出，原指令轨迹验证返回值未被读取。AV没有输出或日志返回适配器。

下一步应追踪外层FileFormat15/18分别进入的接收状态机、可用格式掩码和MC接收校验，并核对真实DMM缓冲区及缩放输入。完整地址转换、资源取得、消息回复、编码Open/Start、HEVC参数集与成片均未执行；G11硬件接受要求仍为缺失。

同机健康备份、受限恢复/回读、线程安全点、独立救援入口、WBI/冷启动和实际音画同步/长录/温度验收也未完成。29.97与精确30.000fps继续分开，完整目标不变。

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage23-encoder-boundary/encoder_boundary.py --output work/sony-firmware-20261024/stage23-encoder-boundary/new-run
```

输出目录须不存在。第一次运行未对身份帮助函数应用同库ELF数据重定位，触发预期值核对；第二次已完成用例，但报告生成使用了不匹配的dump接口。两次源码和失败记录分别保留在 [run-20261025](run-20261025/attempt-failure.json)、[run-linked-20261025](run-linked-20261025/attempt-failure.json)。更正重定位配置和报告接口后，在新目录完成。它们不是固件兼容性结论。

- [摘要](run-corrected-20261025/summary.json) · [完整结果与原指令](run-corrected-20261025/encoder-boundary-results.json) · [来源收据](run-corrected-20261025/source-receipt.json)
- [阶段前目标](goal-status-before.json) · [阶段后目标](goal-status-after.json) · [持续目标](../GOAL_STATUS.json) · [协调复核](coordinator-observations.json)

本阶段未尝试恢复UU或发送Windows任务。授权仍仅Windows缓存PnP；未打开相机接口、读取机身/卡文件、认证、切模式、装驱动、上传模块、执行WBI或刷写。新增文件是官方原库的离线提取件，没有生成修改固件或可刷入补丁。
