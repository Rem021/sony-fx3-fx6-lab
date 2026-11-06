# 第185轮：FX3 恢复适配代码 0.1

2026-10-29。**已从研究转为可运行实现：FX3离线p1识别、限定候选生成、完整回读和逆向重建。** [使用入口](../../../outputs/fx3-recovery-adapter/README.md) · [源码包](../../../outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.1.0.zip)。

工具不是A7C II脚本改名。FX3旧原库的SD版本函数为0x9fd4，签名检查函数为0xabf0；A7C II的0xa0cc／0xace8在该FX3库中分别属于其他代码，不能套用。共享core库的0xd208／0xd27c则有完整SHA匹配。四处窗口都检查原指令和完整库指纹，模型／地区谓词字节不改。原函数的宿主反汇编保存在本目录，未执行Sony代码。

实际实现包括FAT12双副本／簇链／长文件名校验、SquashFS有界解析、按原文件系统定位压缩片段、固定长度重压缩、initrd MD5更新、仅允许片段及p1chksum变化，以及完整原件保存和字节级还原。没有相机后端、native工作器、管理员启动或USB接口。

## 当前验证

[13项测试回执](runs/tests/test-receipt/results.json)核对当前实现源码与执行版本一致。两份真实官方FX3参考p1：

- 2.04原SHA：e5b71cc24bf5232c2e182a979b60c5f080dcbabe2775b32214dc0f394cf53c67。
- 2.05原SHA：ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591。

两者均完成生成→重新解析新库→验证范围外不变→逆向还原，恢复文件与原输入逐字节相同，原始来源未改变。另验证了FAT损坏／循环／交叉簇、长名校验错误、解压超限与尾随数据、未知或已修改库、混合镜像拒绝、manifest篡改／重复JSON键、重复输出／原件路径保护、符号链接、缺失manifest和Python -O下继续执行显式检查。

完整25,100,288字节快照路径只使用人工补尾的已知参考镜像测试，明确标为未验证快照，**不是本机7.02的读回**。命令行inspect、verify、rollback也已执行，本地输出不代表设备读写。

首轮解析因未支持原VFAT长名拒绝；[失败记录](runs/initial-builder-failure/failure.json)保留。补充顺序／短名checksum／Unicode范围校验后全部通过，没有绕过原件检查。

## 交付与未完成项

源码包23,132字节，SHA-256：`23287b817cad613388f33252e1ec637d1c80504bad19f2a67a51fb7709e9f3a5`。仅源码、说明及测试，不含Sony镜像或私有备份。[发布回执](release-receipt.json) · [源码检查](implementation-review.json) · [派生来源](source-derivation.json)。

这是恢复／安装通路的离线参考组件适配：候选会改变版本和签名检查，不产生新的Sony签名。它不是完整修改DAT安装器，也没有菜单RAM门、1080p29.97 HEVC功能补丁或实体相机写回能力。Windows未作运行验证。

下一项应在该实现上接可信的本机p1来源／精确组件匹配和受限采集合同，先证明目标提供者可达，再实现设备恢复后端。现有GET／SET的im／Jiritsu依赖没有因这个工具而消失。混合／未知状态不自动写回，实际断电救砖、当前p1启动及HEVC主录均未验。

本轮无相机、USB、服务认证、管理员、Windows／UU／GUI或固件执行。16项要求、全部授权、原prepared与恢复优先次序保持；`goal_complete=false`、`persistent_write_release=false`。
