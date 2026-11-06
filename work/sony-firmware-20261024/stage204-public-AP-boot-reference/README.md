# A7 IV公开AP启动原件与FX3恢复适配参考

2026-10-29。**本轮实际取得了A7 IV公开的AP BootROM、4 MiB boot0和190464字节启动SRAM，并从原始字节绑定了“模式3→更新序列表→选择1号分区→读取启动文件”。这是新的参考原件与具体代码证据，尚未取得FX3自身的AP boot0，也未证明FX3恢复入口可用。**

来源是DavidBuchanan314/ILCE-7M4-RE的固定提交 `e85e137fc3b88b7cb26e69faa9f1304184678ff7`。本轮GitHub API完整目录包含98项、`truncated=false`；11份选定文件均核对Git blob SHA-1、长度及SHA-256。[来源清单](source-capture.json)、[完整目录](upstream-tree.json)。没有新clone、运行上游脚本、执行Sony代码/guest、操作相机或申请管理员权限。

## 修正之前资料取得的缺口

之前stage135保存的本地参考目录没有boot0/ROM二进制；这不等于上游未公开它们。本轮成功取得并核验这些原件。不能把此事描述成作者今天才发布，也不能继续沿用“公开参考仅有README”的表述。

作者[boot0说明](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/e85e137fc3b88b7cb26e69faa9f1304184678ff7/emmc_boot/README.md)将这份转储标为A7 IV 2.00，其内容没有被重命名为FX3原件。以前未成功取得当前API结果的记录保留；本轮的成功响应单独作为证据。

## boot0与SRAM已经整份绑定

`EXBL`头的实际字段为：起始扇区4，装载地址 `0xFE040800`，加密段长度 `0x2E000`，入口 `0xFE049000`。boot0开头2048字节与提供的SRAM前缀一致。

本轮只借鉴公开解析器的格式，由自己的宿主机数据检查程序处理368个扇区，结果与提供的190464字节SRAM逐字节完全一致。公开ROM原件完整保留；派生对称密钥只在内存中使用，未输出或另行保存。没有运行原解析脚本，更没有执行这些启动代码。[整份绑定结果](public-SRAM-binding.json)、[检查程序](verify_public_SRAM.py)。使用已有宿主机cryptography和已有虚拟环境capstone，未安装依赖。

## 更新启动读取路径的具体证据

| 环节 | 固定原件中的证据 | 结论范围 |
| --- | --- | --- |
| 模式选择 | `0xFE05D708`比较模式3，分支选择`0xFE069CC8`序列表 | 已定位参考模式3的分派，不是FX3实机进入证明 |
| 表消费 | `0xFE06066C`内以32字节步长读取：callback+0、flags+8、label+16，并`BLR`调用 | 用消费者确定结构，未把标签排列猜成布局 |
| 更新装载步骤 | 表中`Ld Kernel UPD`项指向`0xFE04F190` | 仍受先前步骤、运行标志与错误路径影响 |
| 分区选择 | 该回调令W0=1，调用`0xFE059E94`，后者进入分区索引读取并检查FAT引导扇区 | 参考代码选择1号分区；没有读取当前机身p1 |
| 文件读取 | 先读`\\boot\\loadaddr.txt`，随后引用内核、initrd、可选kemco及设备树路径 | 已定位A7 IV更新启动文件来源；未运行/跳转/恢复 |

全部8份选定原码切片与独立指令位解码、表记录、文件路径关联见[AP启动证明](AP-reference-boot-proof.json)、[复核程序](prove_reference_boot.py)。扫描产生的其他locator只用于定位，不计作已经证明的恢复链。

## 如何用于FX3适配

FX3 7.02官方包中现有NOR装载器与这份AP转储的入口前128字节相同，但整份二进制不同。这是通用ARM64初始化代码的匹配，不能证明芯片角色、ROM版本、后续板级初始化或启动区相同。既有7.02更新成员盘点也没有提供独立AP boot0。

现在可以用真实参考代码对照FX3的启动选择、eMMC读路径和更新文件装载规则，减少只依靠日志名推测的工作。后续优先核对FX3当前DTB/内核公开资料能否满足参考载荷的内存、eMMC、USB及看护条件，再区分可复用部分与必须取得同机原件的部分。任何实际注入、认证、读取机身启动区或写入仍需对应具体授权和方案。

**尚缺FX3原机AP ROM/boot0身份、当前p1身份、故障层之外的进入与逆写、真实恢复与冷启动验收。** 参考ROM没有可打印USB字符串，也不能单凭这一点证明不存在USB实现或其他装载路径。A7 IV的[Fastboot说明](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/e85e137fc3b88b7cb26e69faa9f1304184678ff7/payloads/fastboot/README.md)仍将其描述为型号专用裸机载荷；A7C II的[服务执行说明](https://github.com/YuuLuo/a7c2-service-preload)则依赖已经运行的MSC/Senser/Jiritsu链。两者均未提供本轮可直接对FX3执行的独立恢复方案。

本轮没有生成可刷修改包或运行载荷。16项完整要求、所有原授权、native10候选及195仅主机root01固定方案保持不变；root01仍未取得具体批准、未启动、未重问。工具0.4未变，相机/USB/root/管理员/Windows/UU/GUI操作均为0；`goal_complete=false`、`persistent_write_release=false`。上一轮203提供新的WBI范围证据，归类为progress；本轮取得公共AP原件并完成绑定，也归类为progress。
