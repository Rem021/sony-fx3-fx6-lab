# 追清 FX3 恢复启动与同版准入

2026-10-29，经典 **ILME-FX3 7.02**，目标仍是1080p29.97 HEVC主录，当前先解决修改失败后的退回。本轮确认了三项新事实：**旧更新器确有同版续行和显式跳版本分支；当前7.02更新body会先写版本、后写完成标记；7.02启动请求已追到内核队列的间接回调，但最终消费者未解。** 这让恢复研究有了具体切口，也说明“同版一律不能恢复”和“脚本返回0就已进入恢复”都不成立。完整7.02官方包的重新审计没有找到独立p1更新器载荷，包内kernel/initrd属于MAIN。当前同机p1、p2状态和MAIN失效后的独立选择仍待接通；缺少已验证修改包继续作为研究问题，不作为停止理由。([版本原证据](../version-admission/static-admission-evidence.json)、[启动请求笔记](<../research_notes/FX3 恢复启动 版本准入/boot-request.md>))

## 同版能否续行取决于真实入口

旧2.04／2.05原程序逐字节对照一致：版本取自nflasha2的`updater/dat4`，机型／地区取自nflasha1的`dat2/dat3`。普通`sauu`在版本相等时查询有效标志，实际依据只是`updater/comp`是否存在；**comp缺失可使版本子条件通过**。`sauu -s`更直接在比较前返回通过，已由原指令确认。SD入口却采用严格“大于”，比较时不消费comp状态。以下仅描述旧原代码的版本门，假设元数据可读、未触发额外外部override；并非当前7.02机身结果。([来源与地址](../version-admission/static-admission-evidence.json))

| 旧入口 | 同版、comp存在 | 同版、comp缺失 | 低版 |
|---|---|---|---|
| 普通`sauu`，非`-m` | 拒绝 | 版本通过 | 拒绝 |
| MODE6→`sauu -s` | 版本通过 | 版本通过 | 版本通过 |
| MODE5→`sdfileinput` | 拒绝 | 拒绝 | 拒绝 |

表中通过不等于可刷入：机型、地区、签名和实际写入条件仍各自存在。Sony FAQ的同版／旧版错误描述属于正常准入，不能覆盖代码中的其他分支；同样，旧分支不能直接保证当前p1可用。([sauu比较](../version-admission/fragments/sauu-sauu-version-admission.txt)、[SD比较](../version-admission/fragments/libsdfileinputupdaterapi.so-sd-condition-comparisons.txt)、[SD签名门](../version-admission/fragments/libsdfileinputupdaterapi.so-sd-signature-before-stream.txt)、[Sony FAQ](https://support.sony.jp/electronics/support/compact-cameras-dsc-p-series/articles/00282342))

当前7.02 body在相应更新开始路径删除comp；完成路径中，输入information有效才写dat4，之后才创建comp、删除mode。因此代码顺序存在**dat4已新、comp仍缺的窗口**，不能假定失败时版本总留在旧值。断电是否恰落此处并持久落盘未验；关键问题已经缩小为：当前失败续行到底进入可放同版的普通`sauu`，还是严格SD比较，或另一条入口。([开始原指令](../version-admission/fragments/libupdaterbody-7.02.so-body-start-flags.txt)、[完成原指令](../version-admission/fragments/libupdaterbody-7.02.so-body-complete-flags.txt))

这里的“有效”不等于应用仍能启动，也不等于录制正常；完成标记只是状态机输入。当前包头的版本字节也不能代替同机dat4现值。尚未证明当前官方断电续行使用哪条入口，不能为了让表格闭环而任选旧分支。([元数据与缓存原证据](<../research_notes/FX3 恢复启动 版本准入/version-admission.md>))

## 返回0尚未证明启动选择发生

7.02 `up.sh`先写mode文件并sync；`ms`准备mode5、传5，`verskip`准备mode6、传6。helper先读Backup项`0x004b0000`，仅首字节为1或2才把argv原值作为4字节消息送出。其他值可完全不发送而返回0；发送后接收0或-1022也可返回0，且不检查回复正文。**返回码无法充当恢复入口回执。**([原helper全文](../evidence/boot-request/disassembly/ud_send_lsi.elf.txt)、[原脚本](../evidence/boot-request/originals/bin/up.sh))

请求链现为`/dev/uipc`→ioctl低32位`0x80000004`→共享地址转换→队列`0x376`→登记节点`+0x10`函数指针，最终在`osal_uipc.ko .text+0x3644`执行`blr x3`。**实际登记者和target仍未解析**，尚未到达已证明的LSI／bootloader消费者，更无持久selector写入结论。历史mode5证明独立updater内部选择SD输入；当前消息5的早期启动意义仍须另证。MAIN启动后的`upm_bootmode`只反映已选结果，不能补上因果链。([内核原指令与重定位](../evidence/boot-request/disassembly/osal_uipc.ko-full-text.txt)、[分析边界](<../research_notes/FX3 恢复启动 版本准入/boot-request.md>))

还须区分脚本mode编号、body的action枚举和发给消息消费者的整数：当前body的MSCRYPT／VERSKIP是6／7，脚本对应mode5／mode6，不能凭相似名称串成一条链。可见ELF与内核候选扫描未找到登记地址，也不能排除动态构造、其他处理器或WBI中的实现。([编号原件与限制](<../research_notes/FX3 恢复启动 版本准入/version-admission.md>))

## 官方7.02包补全不了当前p1与p2

本轮以完整原包哈希、UFU边界与CRC、FDAT全部28槽、155项TAR及105条官方SUM重核，**未找到独立p1载荷**；结论不再依赖旧提取白名单。p3的kernel/initrd及50个普通文件与p7对应，启动后pivot至MAIN；1,253,376字节U-body只有更新执行组件，均不能冒充p1冷启动环境。Sony当前经典FX3页面确认7.02包为811,876,768字节，但未称其为整机备份。([完整审计](../current-updater-evidence/current-updater-asset-audit.json)、[表与SUM核验](../current-updater-evidence/table-and-sum-validation.json)、[Sony官方页](https://www.sony-mea.com/en/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298560))

包内几何声明p1从扇区128起、49,024个512字节扇区，即**25,100,288字节**；p2为20,971,520字节。它们是声明，尚非同机读回。旧19,377,152字节p1只是历史裁剪载荷，不能替代当前全分区身份。后续缺件明确为当前p1原像／kernel、initrd、DTB及dat2/dat3，配套p2的dat4、mode、comp／uincomp和实际块映射／透明加密合同。([原几何](../current-updater-evidence/tar-selected/0300_partconf/partinf.conf)、[缺件与容量](<../research_notes/FX3 恢复启动 版本准入/current-updater.md>))

## 下一项直接识别队列回调的真实消费者

最窄的离线任务是恢复**queue0x376登记节点及其`+0x10`原函数**：从`osal_reg_msg_queue_cb`／`reg_msg_queue_cb`登记者或可识别的官方WBI数据结构取证，绑定0／2／5／6的实际效果，再追其后续selector及p1／p3选择。当前p1仍缺时应保留精确缺件，不用2.05填空；若原件不可见，则交付具体只读获取合同，再讨论设备动作。版本门、独立启动、签名／机型、原字节恢复四项分别成立，才能评估一次最小可逆修改。

恢复材料继续按拟改范围决定：纯RAM修改先查退出与重启是否撤销；持久模块要有同机原文件及独立逆写路径；若涉及启动器或独立协处理器，合同再扩大到相应介质。整包在手并不能替代这些入口，但也无需先要求所有层面修改包都已验证才能继续离线研究。

本轮仅做宿主静态解析、原件哈希与结构核对；未执行Sony固件或脚本，未新增相机／USB／管理员／Windows／UU／GUI动作。尚无FX3独立救援闭环或目标HEVC主录实录；目标继续，持久写入仍未放行。([操作边界](../evidence/boot-request/static-tools-and-scope.json)、[资产审计回执](../current-updater-evidence/research-receipt.json))
