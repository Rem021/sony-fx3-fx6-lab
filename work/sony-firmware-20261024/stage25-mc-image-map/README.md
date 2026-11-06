# FX3 编码映像定位与原地址模型

本阶段把后续追踪重点从 CPapp 的通用 `MCODEC` 名称记录，转向 `av-cam.bin` 中更直接的编码实现线索。已核对一个内部一致的 AArch64 静态地址模型、6组类型信息指针链、10处局部地址引用，以及编码 Open 构造函数的原指令。

**这些证据尚未把上游 MAIN Open 包绑定到实际注册的接收处理器，也没有验证目标格式通过检查。没有运行固件、模拟整机、访问相机或导出补丁。** 完整目标仍是经典 ILME-FX3 7.02 的 MAIN 1920×1080、30000/1001（29.97fps）、HEVC 4:2:0 10-bit 约16Mbps；精确30.000fps另列。健康备份、恢复、冷启动、真实成片及长录验收均未被本阶段替代。

## av-cam.bin 的静态坐标

原件为 `stage2/extraction/files/nflasha3/av-cam.bin`，13,348,560字节，SHA256：

`0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf`

头部+8是 `ORIL`，+0xc原始32位值为5；本轮不把5解释为段数或格式版本。多个头部绝对指针与入口封装函数相符，诊断文本的原ADRP/ADD引用，以及C++类型信息/名称的绝对指针，也共同符合：

`候选VA = 0xffffffc001000000 + 文件偏移`

这里是分析坐标的一致性检查，没有观察真实装载器、MMU、页权限、当前内存或执行进程。非ELF文件也不能直接沿用之前应用库的ELF段/重定位解析器。入口中存在状态写入，本轮未执行入口或其封装函数。

两个独立的原指针链将相关表关联到 `12CdSeqCtrlEnc` 和 `N8sfmc_enc8sfmc_encE`。另核对 `CdCtrlCore`、`CdMemEnc`、`CdSeqCtrlDecIf`、`CdSeqCtrlDec`，避免仅凭邻近地址把不同编码/解码对象混为一体。类名是原类型信息证据，仍不能证明当前实例、路由或硬件支持。

## 相同 MC 标识仍需实际路由绑定

上一阶段追到应用侧向 `0x805700f9`、特定条件下向 `0x805720f9` 发送。本轮在 av-cam 的原指令中确认了相同常量：

| 文件偏移 | 原局部行为 | 证据范围 |
|---|---|---|
| 0x7c1b4起 | CdCtrlCore 构造中，分别以0x805700f9、0x805720f9调用0x803a8 | 两个CdMemEnc相关对象的构造传参；未执行构造 |
| 0x803a8起 | 0x803d0把传入标识保存到对象+0xb40 | 原存储与类型信息一致；不是注册处理器的证明 |
| 0x87f88–0x885d4 | 诊断文字指向 CdSeqCtrlEnc::SendEncOpenCommand；局部比较0x805700f9，构造0xa8字节参数并调用后续发送依赖 | 保留完整函数反汇编；内存/资源取得、地址转换和发送均未执行 |
| 0x8bb3c起 | CdSeqCtrlEncIf::ExecMovieCodecMsg，读取消息字段并按响应/错误条件分派 | 这是该控制对象的消息处理线索，尚未建立其为上游MAIN Open接收者 |
| 0xa60dc起 | sfmc_enc构造的类型表写入及依赖初始化 | 仅静态类身份，不等于消息队列注册和Open处理器已经绑定 |

因此现在的结论是“找到更合适的编码代码候选和相同标识”，还不是“MC接收端闭合”。尤其 SendEncOpenCommand 的输入是自己的紧凑参数结构，不能未经调用链核对就把它与上游MPR包直接互换。MAIN与代理身份、缓冲区要求和单/双流差异仍保留。

## unsupported format 日志的实际分支

在文件偏移0x44431d找到原 `imola unsupported format...` 诊断。引用它的0x24b2ec函数中，当前这处分支执行的是：

1. 从对象+0x18取通道选择值。
2. 从原文件0x44fcea读取字节0xff，与通道值比较（0x24b37c）。
3. 相等时记录 unsupported/expected close，跳过0x246154调用并把后续回复字段设0。
4. 不相等时调用0x22ba98及0x246154，再把该字段设1。

这处判断没有直接比较宽、高、HEVC或帧率。它不是目标HD HEVC被拒绝的证据，也不能说明目标被接受。通道值的上游生成、资源调用语义、错误状态和完整回复仍未追通；这里的0/1回复字段没有被解释为完整成功码。本轮只读原指令，没有给资源依赖制造“成功”返回值。

## CPapp 的部分映射与未解释区域

原 `cpapp-b.bin` 为15,980,568字节，SHA256：

`c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`

ARM引导指令及复制站点为候选基址0x108000、文件0x20000元数据提供线索。元数据的四组三元组如下；source按文件0x20000起解释只是当前模型：

| metadata内偏移 | source | size | virtual |
|---|---:|---:|---:|
| +0x124 | 0 | 0x9a29f0 | 0x128000 |
| +0x130 | 0x9a3000 | 0x4085fc | 0xacb000 |
| +0x13c | 0xdac000 | 0x131818 | 0xed4000 |
| +0x148 | 0xedf000 | 0x4dd280 | 0x1007000 |

前三组符合 `VA=0x108000+文件偏移` 的候选关系。第三组末端至实际EOF还多0x40000字节；按相同办法解释第四组则超出EOF。未把第四组擅自认作BSS，也没有丢弃尾部或将整份文件声明为已确认的平坦装载映像。

文件0x7bc08处保留了有明确push、movw、movt的Thumb候选函数片段。它与ARM引导片段一起提醒后续分析必须区分指令模式；不代表所有区域的模式与运行映射已知。文件0xc27e18只有u16组号0x57与内联 `MCODEC` 名称，未识别其接收函数。

同时复核了两份VCD载荷和codec_drv.ko的既有哈希。VCD头部字节与版本文字保存在证据中，未根据开头几个字节认定指令集，也没有证明实机选择哪一变体、装载关系或恢复能力。

## 验证记录与复现

当前有效结果是 **run-reviewed-20261025**。脚本重新核对目标卷UUID、5个原件、上一阶段8个封存文件和上一阶段manifest；分析前后原件哈希一致。结果是静态证据核对通过，不计作原指令执行或硬件测试。

首次 `run-20261025` 因脚本把常量首指令限成MOVN而断言失败；源件与错误已保留。修正为原32位MOVZ/MOVN宽常量解析后，`run-corrected-20261025` 通过，但复核发现其Thumb示例窗口位于字符串区域，因此该轮已被替代。有效轮改用0x7bc08的原函数开头，并检查push和MOVW/MOVT指令。旧轮材料保留供追溯，不作为当前Thumb证据。

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage25-mc-image-map/mc_image_map.py --output work/sony-firmware-20261024/stage25-mc-image-map/new-run
```

输出目录必须不存在。脚本不调用固件本身、不创建相机接口、不含刷新或补丁发布入口。

- [有效摘要](run-reviewed-20261025/summary.json) · [原指令和结果](run-reviewed-20261025/mc-image-map-results.json) · [来源收据](run-reviewed-20261025/source-receipt.json)
- [协调复核](coordinator-observations.json) · [阶段前目标](goal-status-before.json) · [阶段后目标](goal-status-after.json) · [持续目标](../GOAL_STATUS.json)

下一步优先追 sfmc_enc 的实际注册与命令分派、把MAIN Open消息绑定到enc_open处理器，再追输入校验、通道选择和完整回复。随后核对VCD变体选择和资源层约束。找到某个支持的代理模式、一个类名、相同通道ID或一个分支，都不能替代这一链路。

本轮按用户要求执行一次 `orca orchestration check --json`，返回count0。Windows/UU仍等用户通知恢复；无新连接尝试、发任务或相机访问。相机授权继续只限Windows缓存PnP盘点；同机健康备份、受限恢复与回读、独立救援入口、WBI/冷启动、真实MAIN码流、音画同步、长录/温度和既有模式回归仍待各自证据。目标保持active，未放行持久写入。
