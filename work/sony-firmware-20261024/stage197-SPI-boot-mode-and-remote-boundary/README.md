# FX3 7.02 SPI启动模式输入与恢复边界

2026-10-29。**补齐了NOR首轮SPI数据到启动模式变量的来源；长状态函数的证据指向关机/待机备份协议，尚不能充当独立救砖入口。** 这轮仍未获得“主程序损坏时，Mac/Windows可独立启动并写回原件”的证明，不能开始修改固件的实机刷入。

只静态读取已经保存的官方FX3 7.02原件；没有运行Sony/guest代码，没有相机、USB、管理员、Windows、UU或GUI操作。195的root01仅主机问题仍待用户明确回答，固定作业未创建，不把“继续”解释为单次批准。全部16项目标、原授权、原生10候选和root195方案保留。

## 首轮模式值的来源已连起来

原件仍是[182的loader_nor.bin](../stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin)，101888字节，SHA256 `4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942`。以下VA采用原`pformat_config.txt`配置基址`0xFE049000`，不当成机身实测PC。

| 原件步骤 | 已确认的局部行为 | 证据边界 |
| --- | --- | --- |
| COMMON表SPI 1st → `FE05C03C` | 首字节为1的命令分支接收到本地栈缓冲，再复制前0x38字节给调用者 | 调用者把计数字初值设为0xC0，但接收器进入即清零；不能把初值当成已验证的长度上限 |
| `FE05331C` → `FE059198` | 成功分支把该前缀传给bootdata导入器 | 另一命令2返回1并走不同分支，不混成同一成功路径 |
| 导入器 → `FE053EB0` | 从输入`+0x30`取32位值，写全局`FE0615D4` | 未识别SPI另一端的具体控制器/固件及发送条件 |
| getter `FE053AB4` | 从同一全局读取模式值 | 不把SPI字段4/7或up.sh参数5/6当作这个枚举 |
| COMMON表Copy BM/BF | 若该项执行，把getter结果写上下文`+0x1B4` | 表flags为0x8000，有条件跳过，不能声称每种冷/热/WBI启动都必经 |

[首轮原指令](first-spi-input.txt)、[COMMON调用者](common-first-spi.txt)、[bootdata导入](bootdata-import.txt)、[setter](mode-setter.txt)、[上下文复制](context-mode-copy.txt)。底层接收通过GPIO握手和内部SPI/FIFO调用；没有因此取得电脑侧USB服务入口，也未证明可以从外部设置这些值。

## 长状态函数的职责进一步收窄

`FE054C88`的完整局部范围到`FE055724`前，共679条指令。所有条件分支的两个后继、普通BL返回模型下，679条均进入控制流上界，唯一普通RET为`FE0556D4`。RET后仍有函数自己的尾块，因此最初截到RET后的位置被检查器拒绝；[初始窗口](spi-state-initial-window.txt)保留，最终范围包含这些尾块。

原日志包括`PWD:Set Reg`、`PWD:Snd Bkup`、待机模式、watch key和ontimer。函数构造0x12备份分块、0x13设置数据，通过`FE052348`交换并核对响应。已见直接调用点在`FE05B0E0`的模式/电源序列函数内，另有状态word等于7的门。[完整函数](spi-state-consumer.txt)、[调用者](power-sequence-caller.txt)、[控制流](spi-state-cfg.json)。

这些证据支持“关机/待机配置和备份交换”的职责判断，**没有形成p1恢复环境装载、USB暴露、任意固件还原或故障态独立运行合同**。未逐一证明全部子函数及另一端处理器；因此也不反向宣称全机绝无恢复能力。

## 社区资料重新核对

本轮重新打开[A7CII工具说明](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/README.md)及[Issue31完整讨论](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)。这是对184已引用路线的现状复核，不冒充新的FX3成功案例，也不声称取得仓库最新提交身份。

- Issue的2026-10-23首报是修改后无法开机、灯号循环和HID枚举；10月25日至27日有参与者报告切到录像模式后能重新进系统并恢复，另有人报告之后仍保留修改。它说明存在依赖未受影响模式的绕行经验，不等于主系统失效后的独立重刷。
- 维修报价/拆芯片说法是参与者陈述，未提供可复核的FX3板级读写及救回记录。本轮不据此承诺维修价格、官方售后方案或拆焊成功率。
- 维护者当前说明仍限定A7CII 2.01，并明确写入及回读一致不能证明启动安全，恢复也无保证。不能直接改型号名/偏移后套用给FX3 7.02。

## 本轮验证与后续实质缺口

[独立原始编码复核](raw-source-verification.json)与Capstone图一致；10处直接调用目标、13处关键原指令及输入/全局/上下文字段由原始编码核对。共10份来源绑定的反汇编切片，原文件SHA前后不变。检查没有执行原代码，不能代替实机验证。

下一步需要区分并定位：SPI发送端如何生成loader模式；NOR与AP侧早期加载器如何选择p1/p3；这条链在appFw或更新过程中损坏时是否仍可达。7.02包缺少独立p1原件的事实保持，旧2.05只可作为历史结构参考，不能替代当前同机备份。

root01待此前具体确认；独立静态研究继续。`goal_complete=false`，`persistent_write_release=false`，真实p1采集、独立恢复、修改后的主录及长录验收均未完成。
