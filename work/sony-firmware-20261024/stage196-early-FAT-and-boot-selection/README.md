# FX3 7.02 NOR文件回退与早期标志生产者

2026-10-29。本轮取得两项会改变恢复路线判断的静态证据：**当前NOR原件的FAT-open入口没有正常成功返回；模式谓词所读word的一个确定生产者，是早期UPDATE_MIRA寄存器采样。** 因而不能把可见的 `updater/mode` 字符串当成已可用的独立救砖入口。

只读取已经保存的官方包原件并做宿主静态分析。没有执行Sony代码、guest、相机、USB、管理员、Windows或GUI动作，没有新的固件/驱动/程序安装。195的root01问题仍待用户确认；本轮既不视“继续”为批准，也不重复发起询问。

## 文件回退的精确限制

原件是[182提取的loader_nor.bin](../stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin)，101888字节，SHA256为 `4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942`。`pformat_config.txt`给出的配置基址是 `0xFE049000`，本文地址均为配置VA，不是机身PC。

谓词 `0xFE053C78` 在cache没有明确结果、word `0xFE170028` 为0时，才检查partition2及 `\updater\mode`。这保留183的条件分支描述，但其调用的 `0xFE057FA0` 需要补充一个关键事实：

- [完整118条原指令](fat-open-selected-original.txt)构成一个无未知间接跳转或越界尾跳的局部控制流图。对子调用仅采用“按普通ABI返回到下一条”的模型，不执行它们。
- 所有建模的正常返回都经过 `0xFE05816C` 的 `mov w0, #-0x198`；唯一RET在 `0xFE058174`，正常返回恒为 **-408**。该赋值之后没有写w0的指令。
- [Capstone控制流/支配分析](fat-open-normal-return-proof.json)与[独立A64位编码解码](selected-source-evidence.json)对分支图和MOVN常量一致。

因此，即使先假设FAT-ready和当前partition2都满足，**这份未改原字节的该入口仍没有普通成功返回**。文件检查的正常失败路径会把cache置2并返回0；成功置cache1/word1的分支不能由该普通返回走到。该结论限定于原件局部正常返回，不证明子调用必定返回、不排除其他阶段/处理器的文件消费者或运行时替换代码，也不等于整个机身永远不能进入更新器。

本轮没有证明FAT-ready的所有别名写者。两个线性地址扫描输出只是候选，不能拿“没找到写点”证明全局不存在初始化。[初始候选](reference-candidates.json)、[MOVK感知候选](word-reference-candidates.json)。

## word生产者已从未知缩到硬件采样

`0xFE0532B4`在COMMON序列表的 `DBG/UPD SW Read` 项中，flags为0。它调用 `0xFE0542CC`，将返回值最低位存到 `0xFE170028`，同时写入上下文 `+0x238` 的bit1。

该叶函数先向 `0xF102E008`、`0xF102E024` 写掩码2，再读取 `0xF102E010`，普通结果为 `(sample >> 1) & 1`。原日志文字是 `UPDATE_MIRA`，参数为通道0x11、bit1；内存地址构造、位提取和调用目标也用原始编码复核。[采样原件](gpio-update-mira.txt)、[生产者](sample-to-shared-word.txt)、[证据汇总](selected-source-evidence.json)。

这是寄存器/硬件输入候选的内部证据，**尚未对应到FX3外部按键、板上pad、有效电平或可用服务夹具**，不提供短接/写寄存器操作。它不是Google Fastboot的识别或进入证明。

序列表中这项位于 `SPI 1st` 之前；表执行器对flags0没有bit1跳过或bit15条件跳过。不过，先前步骤仍可能失败，实际入口/热启动/WBI是否走完整COMMON链未验，不能称每一种重启都会重新采样。

模式谓词的使用也不直接等于p1装载：`0xFE054AE4`在另外两个byte优先条件之后，按谓词选择发送字段4/7；已见直接caller `0xFE05B268`还有状态==7的门。另一消费者 `0xFE054C88`在SPI协议处理中有更长状态机。**GPIO位、发送字段4/7、loader枚举updater3、up.sh参数5/6仍是不同数值域。** 此轮没有补作远端mode与p1/p3选择的证明。[选择函数](spi-choice.txt)、[直接调用门](spi-choice-call-gate.txt)、[协议前缀](spi-mode-predicate-prefix.txt)。

## 对安全恢复的影响

| 候选 | 此轮证据 | 尚不能承诺 |
| --- | --- | --- |
| 靠这份NOR打开mode文件 | 原FAT-open普通返回恒-408 | 仅放mode就能独立恢复 |
| 早期UPDATE_MIRA采样 | 确定word生产者和寄存器/位 | Mac/Windows可直接触发、真实按键/夹具映射 |
| SPI选择与远端更新器 | 谓词、字段和状态门可见 | loader updater3、实际p1/p3映射及故障态可用 |
| 官方SD更新失败重试 | Sony公开限定版本/文件错误流程 | 自定义appFw/p1损坏后的独立逆写 |

Sony当前[经典FX3 7.02页面](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)的失败重试章节针对更新包复制/前置版本等错误，不能据此推广成任意改机救砖。这里没有让用户拔电池、重试更新或操作相机。

下一项从 `0xFE054C88` 的实际SPI状态消费者、首轮输入及已导入bootdata继续追远端mode/p1选择；同时保持当前同机p1缺件，不能用旧2.05替代。Root01仅主机方案仍是195原包、未批准未启动，不改变任何设备授权。原来16项目标状态完整保留，`goal_complete=false`、`persistent_write_release=false`。
