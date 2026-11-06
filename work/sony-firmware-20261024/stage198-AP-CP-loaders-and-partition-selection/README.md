# FX3 7.02 SPI加载器交接目标与AP恢复边界

2026-10-29。**本轮找到并核对了当前包另一份SPI加载器，但它已追清的固定交接目标是`0x00108000`，与同包`cpapp-b.bin`配置一致；不能因为日志写着jump_to_kernel，就当成AP的p1恢复加载器。** 这缩小了下一步的搜索范围，尚未提供可上机刷写或独立救砖的方案。

仅分析本机已有官方原件。没有执行Sony/guest代码、挂载镜像、操作相机/USB/管理员/Windows/UU/GUI。195的root01仍未收到新的具体批准，固定作业未创建，不重复询问；之前的相机单次授权不复用。原16项目标及全部授权保持。

## 找到的组件与真实来源

7.02包已保存的p8分发载荷是`nflasha8.img`，22450176字节，SHA256 `3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b`。通过已有只读FAT解析器提取，不执行其中代码。

| 组件 | 字节数 | 此轮用途 |
| --- | ---: | --- |
| `loader_spi.bin` | 39184 | 追固定交接地址、寄存器设置和原指令 |
| `DGU.bin` | 24336 | 独立来源绑定，暂未完成入口/调用链解释 |
| `MIS.bin` | 119296 | 首部`MIS_HEAD`，与SPI加载器分开保存；不把参数内容当已执行程序 |
| `tomco.txt` | 710 | 配置对照，包含电源/复位/异常相关字段，未据此操作硬件 |
| `darwin_core.bin` | 243000 | 从已校验完整FDAT的明确TAR成员提取；内部有电源与启动日志，尚未证明是SPI模式发送端 |

[来源清单](source-inventory.json)、[剩余启动候选](remaining-candidates.json)。182此前保存的NOR-loader目录并不包含这些独立组件，因此这轮补的是新原件及实际交接检查，不重复上轮C88待机状态机。

## 固定交接已由原始编码核对

`loader_spi.bin`本身SHA256为`314d372d0d2b9883c3b9dc04b40389edb3100e6d5ef529633cc427c3d0cab72e`。以下采用文件偏移作为权威定位；显示VA基址`0xFE049000`仅为内部指针相符的布局假设，不声称实机PC或已配置SPI加载地址。

1. 文件`+0x5AAC/+0x5AB0`用MOVZ/MOVK把`w0`设为`0x00108000`。后续BL到`+0x41BC`，那里B到`+0x3CA8`。
2. 目标叶函数的两个条件分支均不改`x0`；设置`SCR_EL3=0x30`、`SPSR_EL3=0x13`，把`x0`写入`ELR_EL3`并执行ERET。[调用者](spi-handoff-caller.txt)、[尾跳](spi-handoff-tail-stub.txt)、[叶函数](spi-handoff-eret-leaf.txt)。
3. 独立原始位编码检查了目标常量和两次相对分支，结合Capstone核对叶函数没有写`x0`；这是固定交接前缀的静态证明，前面的序列/日志/缓存调用仍采用普通返回假设，不保证实机能走到这里。[证明与范围](fixed-handoff-proof.json)。
4. 同一7.02包的`pformat_config.txt`把`cpapp-b.bin`加载位置明确写成`0x00108000`。寄存器值对应AArch32 SVC交接解释，可对照[Linux原定义](https://github.com/torvalds/linux/blob/master/arch/arm64/include/asm/ptrace.h)与[Arm异常返回说明](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Exception%20model.pdf)。

因此，已看到的路径更符合CP/TOPPERS一侧的交接。该推断有配置、目标值及模式位支持，但尚无机身CPU追踪；没有逐个证明全部序列子函数，更没有证明整份文件与任何p1/p3逻辑绝对无关。**准确结论是：当前这条交接不足以证明AP恢复环境可达。**

## AP参考资料与缺件分开

旧官方2.05 p1仅作为历史结构参考。其FAT目录包含`/boot/initrd.img`、`vmlinux.bin`、`cxd90057.dtb`、`kemco.txt`、`loadaddr.txt`及`p1chksum`，未将它登记为当前机身备份。`loadaddr.txt`首地址`0x400080000`与上述`0x00108000`不同；这个历史值也不冒充7.02当前AP的实测入口。

重新核对了[A7IV原作者的boot0解析器](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/main/scripts/parse_emmc_boot0.py)：它读取独立的eMMC boot0和BootROM原件，解析EXBL信息区并提取下一阶段。这提供了寻找AP早期原件的具体方向，**不证明该机型的格式、偏移、密钥或恢复payload已适配FX3**；本轮没有下载/运行该脚本或其他机型的二进制，也未取得FX3同机boot0。

7.02当前包已确认的分发分区仍只有p3/p5/p7/p8/p15；p5首部`WBI2`本轮只做签名和来源复核，不把它称作完整备份、冷启动救砖或已解析的AP选择器。完整包没有独立p1载荷的182结论保持。没有因文件名未匹配而宣称所有可能的AP早期代码都不存在。

Darwin原件首部看似向量表，但尝试的0及0x4000显示基址尚未建立经过验证的reset入口/字符串引用关系；[候选记录](darwin-mapping-candidates.json)不证明这两个基址在所有运行环境下都不可能。不确定的MCU映射不进入触发方案。内部启动/电源文字只作后续定位候选，不能证明它发送SPI命令1或选择更新分区。

## 下一步

优先检查可取得的FX3 AP早期加载原件及公开资料，寻找明确的p1/p3选择与故障态入口；并把CP、Darwin等候选的发送者身份与这个问题分开。对同机早期原件的真实读取，仍需受审查的传输/启动/退出路径和对应具体授权，不能由离线分析自动扩展。

root01待此前确认；继续研究不消耗任何设备次数。`goal_complete=false`、`persistent_write_release=false`。当前同机p1、真实逆写、独立断电恢复以及1080p29.97 HEVC主录和长录验收仍未完成。
