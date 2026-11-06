# Sony 相机固件失败与恢复：社区原始案例账本

检索截止：2026-10-27。只读网页与源码；未连接相机、切 USB 模式、认证、换驱动、运行固件、安装软件或联系任何人。写本文件前核对 KAFU2T 卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、实际挂载点与可写状态。

证据口径：**B**＝原始机主/操作者的明确症状与后续自述，未经独立实物复验；**B+**＝另一个原始操作者确认同一恢复路径，仍非统计研究；**A(范围)**＝维护者文档/源码能复核功能范围，不等于所有机身恢复成功；**C**＝一手但没有结局，或二手转述。没有任何一项可以从帖子数量推算失败率。下表中的“恢复方法”记录历史事件，不是对 FX3 7.02 的操作指令。

## 1. FX3 官方升级失败：哪些真恢复，哪些只看到送修

### Takeaway

FX3 有黑屏但电脑升级器仍能通信、最终由官方升级流程恢复的真实自述；也有同为更新后黑屏，普通尝试失败、最终更换主板的后续。黑屏、红灯、能否出现盘符不能单独决定故障层级；“售后换板”也不能证明原板物理损坏。[HotVenusian](https://www.reddit.com/r/FX3/comments/174wsav/firmware_update_failed_now_camera_wont_turn_on/)；[Unlikely_Speech_5711](https://www.reddit.com/r/FX3/comments/1jwp86i/602_firmware_update_bricked_fx3/)

### Cited Findings

| 来源 / 发布与事件日期 | 机型 / 固件 | 变更与症状 | 仍可访问接口 | 实际恢复与结局 | 证据强度 | 对用户 FX3 7.02 的适用性 |
|---|---|---|---|---|---|---|
| [HotVenusian 原帖及本人回复](https://www.reddit.com/r/FX3/comments/174wsav/firmware_update_failed_now_camera_wont_turn_on/)，2023-10-10 帖；后续另有较晚回复，准确日页面未给 | FX3，2.02 → 2.05，Windows 官方升级器 | 升级报失败，无法正常开机，插电池红灯常亮 | 作者后续明确：屏幕不开，USB 接电脑仍能完成升级；未给 VID/PID | Sony 电话支持让其断电放电，再运行 3.00 电脑升级器成功；随后 SD 升到4.00，恢复工作 | B，有同一作者症状、方法、成功和 USB 补充 | **同机型、旧版本升级链**；证明某类黑屏不是死板。不证明7.02可刷旧3.00，也不证明改固件后仍有该通道 |
| [redshiftquasars 原帖及本人结局](https://www.reddit.com/r/FX3/comments/1edyf73/fx3_firmware_update/)，2024-07-28 帖；次日重试 | FX3，原2.00，先用01*20x.exe到2.05，目标5.00 | 电脑显示结束但机身不重启，屏幕黑，开关任意位置后红灯常亮 | 当时电脑不识别为 mass storage；后续升级器可通信，VID/PID未给 | 当晚尝试3.00失败；次日充满电池并换电脑USB口后3.00成功，再到5.00并正常使用。作者明确不能分离电池/端口哪个起作用 | B | 同机型旧链，不能把换口/电池写成普适救砖原因，更不能对7.02做降级操作 |
| [TheSilentPhotog 一手评论](https://www.reddit.com/r/FX3/comments/1ffv4hi/60_bricked_my_fx3/)，2024-09-13 帖；首帖正文已删 | FX3，作者评论称由V3到6.00，经SD | 初次更新未完成；具体灯码、屏幕与日志未保留 | SD升级状态机能继续；无USB证据 | 作者称等灯停后断电，隔夜重试，总计第三次成功；换电池最初也没帮助。另评论确认自己用SD，不是Creators App | B，第一人称结果但正文缺失 | 有SD重试恢复个案；不支持“仅App会砖”，也不证明 bootloader/eMMC完整 |
| [Fragrant_Ad_7938 详细失败记录](https://www.reddit.com/r/FX3/comments/1hu6qui/fx3_firmware_update_failed_camera_wont_turn_on/)，2025-01-05 | FX3，1.01，经20x再3.00；M2 Max Mac官方升级器 | 第一步末尾报错，重跑却说该步已完成；第二步反复失败；红灯常亮、机身无响应 | 3.00升级器仍探测得到相机并运行，但最终“Could not update” | 换线、端口、重启、卸镜/卡、满电、断电与按快门均试过，仍失败；公开帖无本人最终结局 | C，一手详尽、恢复结局缺失 | **反证“电脑认得到就一定能救”**；也不能据此断言Mac不行或主板物理坏 |
| [Unlikely_Speech_5711 原帖更新](https://www.reddit.com/r/FX3/comments/1jwp86i/602_firmware_update_bricked_fx3/)，2025-04-11 帖；事件为前一天 | FX3，4.00 → 6.02；格式化SD，作者具体注明Lexar SDXC256GB1667x | 正常1/3/5进度后，约10分钟出现6长9短；持续1–1.5小时；多次断电/重新置卡不恢复 | 灯号/SD更新相关活动仍存在；没有 USB 描述符或读写证据 | 作者正文新增：服务中心**更换主板**。多次重试和建议视频方法对他无效 | B，有本人最终处理，未给维修工单与芯片故障诊断 | 同机型官方6.02也可能最后送修；不能得出7.02必失败，不能把换板诊断成存储芯片物理坏 |
| [ajlion_10 帖中另一位机主及返修回复](https://www.reddit.com/r/FX3/comments/1fqgexj/in_need_of_the_fx3_ver_600_dat_update_file/)，2024-09-27；返还后回复2024-09-28 | FX3，6.00更新失败，原版本未给 | 在该失败帖回复自己送Sony Pro Service；缺具体灯码和USB | 未给 | 保内约一周；本人后续称已收到，正常工作、版本5.00、主板更换且免费；附一条iCloud照片链接，未依赖其内容 | B，第一人称返修后续；不能采信作者“不可逆”的硬件因果解释 | 另一例**已完成更换主板后恢复**；售后能换板≠已经证明其无法通过维修级重写修复 |
| [GTMM music 原视频说明](https://www.youtube.com/watch?v=-NlrQcuYGBQ)，2022-12-08；2.00发布后数月逐渐出现 | FX3，2.00 | 装镜头System error、偶发不开机、PC USB不识别 | 至少曾能进机内菜单 | 作者通过菜单 Setting Reset → Initialize 后称恢复；表示将观察后续，未找到长期复验 | B，仅机主当时验证；**不是完全无法启动的硬砖例** | 只能说明可进菜单的异常有设置初始化恢复个案，不能解决无法进入菜单/底层存储损坏 |

- [2024-09-16 的6.00故障视频帖](https://www.reddit.com/r/FX3/comments/1fibhxz/help_new_fx3_fw_update_destroyed_my_camera/)是儿子代父发帖，原3.00，经Creators App更新后快门异响、ISO AUTO闪烁、无响应；没有发现原作者确认最终恢复。评论“朋友两台换电池并逐级更新恢复”属于二手，未作为上表已证实个案。帖内对Sony责任、签名验证流程等的推断，不能当技术事实。[同帖](https://www.reddit.com/r/FX3/comments/1fibhxz/help_new_fx3_fw_update_destroyed_my_camera/)

### Inferences

- 在这组一手记录里，“黑屏仍有USB升级通信”“SD状态机仍活动”“正常菜单尚可进”“最后更换主板”是不同状态，不能统一称为彻底砖；也不能由红灯常亮推断只有主板更换一路。[2.05成功例](https://www.reddit.com/r/FX3/comments/174wsav/firmware_update_failed_now_camera_wont_turn_on/)；[Mac可探测但失败例](https://www.reddit.com/r/FX3/comments/1hu6qui/fx3_firmware_update_failed_camera_wont_turn_on/)；[6.02换板例](https://www.reddit.com/r/FX3/comments/1jwp86i/602_firmware_update_bricked_fx3/)
- 换电池、重新准备正确官方SD文件、按适用版本链重跑，是某些保留升级能力的状态曾成功的办法；这些证据没有给出 FX3 7.02 在自定义改写后、系统不能启动时的独立救援通道，更没有成功率。

### Gaps

- Reddit JSON入口被403拒绝，网页大多只显示相对评论时间；表中绝对发帖日期来自页面的当日“Top posts”导航和可读搜索结果；具体后续日无日期即写未知，没有用现在的相对“几年前”倒算。
- 未找到本用户经典FX3 7.02、与其拟修改目标相同、发生故障后由公开底层工具完整恢复的可复核案例；不能据现有材料承诺Mac+Win11可救。
- 上述换板例没有维修原始数据、存储读回、boot日志或电源检测，无法区分“官方标准维修换板”和“原板存储/CPU确有不可修物理故障”。

## 2. QAQLeonard A7C II：issue31最新后续与恢复边界

### Takeaway

**issue31不能再概括成“按教程操作也变砖，只能换主板”。** 截至10/27，至少有原始操作者通过视频档启动/模式切换恢复，首帖作者甚至表示补丁保留、无需恢复。这证明该组症状含可绕过的启动状态问题；仍不证明根因、长期稳定或FX3可迁移。[issue31](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)

### Cited Findings

| 来源 / UTC日期 | 机型 / 固件 / 变更 | 症状与仍可访问接口 | 恢复方法与最终结局 | 证据强度 | FX3适用性 |
|---|---|---|---|---|---|
| [lipu0324首帖](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)，2026-10-23 12:45 | A7C II项目；仓库只支持2.01，**此首帖未独立列机身/固件/工具具体版本**；第二次拔电池后出故障 | 无法启动，读写灯2-3-5循环；作者报告HID `054C:0D68`；诊断附件存在但本研究未下载/执行 | 先送修；10/26称官方要换主板约3000；[10/27 13:19本人后续](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6442900646)：视频模式开机→切回相机模式→再关机开机正常，FL23等仍保留，不需要恢复 | B，原帖到成功后续；无完整日志/长期录像验收 | **不能迁移**；FX3无同样Still/Movie/S&Q机械选择器，也未验证同一出错路径 |
| [CRAZYShimakaze](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6395226486)，10/25 08:08同故障；[10/25 15:08办法](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6399306736) | 同项目，版本未独立列；询问是否只勾选FL23与六款内置外观，**问题句不是已确认配置** | 原先称同故障，曾预约送修；无本人USB属性 | 关机，移除USB/电池/SD，置Movie与曝光P，重新开机进入系统；称可再用仓库恢复固件功能回原状态。10/27表示先观望，不继续改 | B，第一人称找到方法；未提供恢复后的独立程序读回 | 仅A7CII个案，不是通用HID救援 |
| [dt-nb](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6395018821)，10/25 07:44；[10/26 03:32](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6407606480) | 同项目，具体版本未给 | 称按提示操作后不开机、灯2-3-5循环，提供诊断包；无USB属性 | 引用上述办法并回复“好了”；无法从短回复分离仅开机成功还是已执行恢复 | B+，另一个原始操作者确认办法有效，验收范围有限 | 不外推FX3 |
| [#28原帖及维护者回复](https://github.com/QAQLeonard/a7c2-fl23-research/issues/28)，10/23；[维护者原文](https://github.com/QAQLeonard/a7c2-fl23-research/issues/28#issuecomment-6369627082) | A7CII2.01，Windows工具3.0.3，合并安装 | appFw.so 0x3528804 patch conflict；此前竖屏准备已完成；机身可正常重启，菜单、拍照、回放正常，USB稳定性检查通过 | 没有最终恢复结局。维护者明确：总FAILED不代表先前改动自动回滚，需先看诊断，不能先确认此状态可用3.0.3恢复 | B（部分安装失败），A(范围)（维护者解释）；不是砖 | 说明工具“失败”与相机坏开机应分开；不提供FX3救援 |
| [#44机主完整报告](https://github.com/QAQLeonard/a7c2-fl23-research/issues/44)，10/25 | A7CII2.01，Win11x64 26300、3.0.3；MSC `0E8A`/libusbK，service `0336`/WinUSB | 设置保留核对因0x2CF19xx变化中断；本机journal WinError5；服务身份出现过晚。记录到中间PID `096F`/`0D68` | 报告者**自行修改本地校验白名单后**称factory restore与一键安装完成；没有机身永久不开机的证据，也没有维护者确认这项放宽是正确修复 | B，用户修改后成功；根因及校验放宽安全性未证实 | 不能作为绕过FX3检查的理由；还说明 `0D68` 单独出现不等于已经证明一个可用底层恢复协议 |

- 最新正式Release页面仍标识 **v3.0.3，2026-10-23 04:59，提交7827856**；维护者README现在明确“写入成功、读回一致不代表开机安全，恢复不保证救回”。工具范围只为A7CII2.01；Windows10/11x64有包，Mac14+AppleSilicon包的真实Mac USB尚未验证。README所列FL23/六外观/恢复实机证据是作者的单台Windows+A7CII。[Release](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)；[README](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/README.md)
- **一键原厂功能恢复不是整机镜像恢复。** 维护者开发说明写明：内置 `factory-regions-2.01.json`只有项目改动区域的通用原厂字节，没有完整固件、没有机身数据；区域外与校准保留。源码 `checkpoint.py` 明列 AP/CP两程序、68名称资源、FL23绑定/色彩单元、六自定义配方，并明确 `not a full camera filesystem or calibration reset`。[开发说明](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/docs/en/development.md#L86)；[checkpoint源码](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/src/looks/looktool/checkpoint.py#L15)
- 正常连接需要A7CII MSC `054C:0E8A`，经过认证切换`054C:0336`、再次认证、再核机身。源码仅在已有记录身份与允许续接时接入已经存在的0336服务会话；没有用0D68 HID任意重写全部eMMC的恢复分支。[devicesession.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/src/looks/looktool/devicesession.py#L29)；[开发说明USB流程](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/docs/en/development.md#L88)
- 更新日志3.0.2记录：旧任务68资源残留导致某机身超过60MB、ENOSPC；其清理修复当时只有仿真。恢复先存ST再撤代码，以免中断后配方仍指向已移除功能；3.0.3记载 cp-restore.2 原厂恢复经作者冷启动核对达LOADED，为**单台恢复实测**。不能拿某个离线修复或LOADED替所有故障机身背书。[更新日志](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/docs/zh-CN/changelog.md)

### Inferences

- #31首帖作者最后保留补丁仍能开机，明显削弱“该案例已经证明flash损坏/必须拆焊”的解释；目前更适合记作启动/模式状态相关故障，**这是从行为推论，具体根因未被维护者证实**。[本人最新后续](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6442900646)
- “出厂恢复”“完整checkpoint”“firmware file restore”这些工具标签，均须按实际区域清单理解；本项目的可运行服务会话与文件/参数恢复，不能当作启动链或存储完全坏掉后的独立保险。[checkpoint源码](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/src/looks/looktool/checkpoint.py#L34)；[USB源码](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/src/looks/looktool/devicesession.py#L29)

### Gaps

- #31没有维护者最终根因、失败前准确选项、相机原始字节或对照；“只修改拍照功能所以视频没事”是操作者解释，不是已证实代码因果。
- 首帖“第三方拆flash一两百”、HaoDingg“拆芯片报价500”、官方主板3010均是帖子口述/报价；没有对应芯片重写完成并验收的交付，不作为可用拆焊救砖证据。
- 截至所读页面未见任何由`054C:0D68` HID直接修复A7CII整机存储的开源实测；没有FX3 7.02服务/低层恢复与机身完整备份验收。

## 3. 其他机型与Mac/Win11环境：能够借鉴到哪一步

### Takeaway

跨机型社区案例最多证明某种故障仍保留部分入口、可在特定条件恢复；公开工具能跑在Windows或Mac，并不意味着已经覆盖FX3 7.02。关键是机型/版本、故障后仍活着的协议、同机恢复数据和实测结局。[A7CII范围与要求](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/README.md)；[A7IV底层研究](https://github.com/DavidBuchanan314/ILCE-7M4-RE)

### Cited Findings

| 来源 / 日期 | 机型 / 版本 / 变更 | 症状 / 可访问接口 | 实际恢复与结果 | 强度 / FX3适用性 |
|---|---|---|---|---|
| [axel-counter等一手回复](https://www.reddit.com/r/SonyAlpha/comments/xdp7ad/a7iv_firmware_update_failed/)，2022-09-14帖；后续也有2024年底→2025初用户反馈 | A7IV，早期升1.10；另一作者1.01→1.05→4.00 | 5长6短、不能正常开机；SD更新逻辑仍活跃；无USB证据 | 重新从Sony下载固件、核对大小、重做卡后更新成功；另有人送修无后续、另有3.01仅多等待便完成 | B，多种一手结果但原因未经独立隔离；**不外推FX3相同灯码或适用固件** |
| [Mr_BananaPants](https://www.reddit.com/r/SonyAlpha/comments/1wh11m5/enabled_shutter_angle_on_my_a7iv_by_doing_some/)，2026-09-15 | A7IV，固件版本未说明；先显示快门角度，再尝试8K | 作者称bootloop；未披露还可用何种USB/串口 | 首帖Edit2及本人评论称bootloop已修好，机器再次工作；**未给恢复方法、备份或命令** | B（曾出错及自称恢复），方法证据C；不能拿来承诺8K/跨机型或独立救援 |
| [MDHan macOS适配器](https://github.com/MDHan/a7c2-fl23-macos)，文档记录2026-10-21用户结果 | A7CII2.01，Mac工具0.2.3+；首次安装服务入口超时 | 此类首次0336等待错误在进入安装主体前可能还未写；不同于进入写入后未知结果 | 维护者记一例用户明确重试后完成安装，程序/参数/9处运行区域验证通过；拍摄回放、预设、NTSC人工结果未反馈；首次保存设置中断仍列已知风险 | A(文档范围)+B（维护者转述用户截图）；**不是Mac独立救砖成功案例** |

- DavidBuchanan的ILCE-7M4-RE维护者公开串口BootROM入口、bare-metal Fastboot兼容payload，能USB备份/恢复eMMC分区；README同时说明boot0的透明加解密尚未实现。这是一条有原始代码的**A7IV低层研究能力**，不是这里已找到的FX3故障救回案例，不据“同BIONZ XR”迁移结论。[维护者README](https://github.com/DavidBuchanan314/ILCE-7M4-RE)
- 本轮没有找到A7SIII、A7RV或A6700“与FX3 7.02同样改动失败→同样接口→可复核恢复”的原始完整闭环。仅WiFi/Bluetooth故障、更新后设置异常、无后续求助、第三方收费宣传，不合并成救砖成功案例。

### Inferences

- **对用户环境的裁决：目前只能说具备运行部分主机工具的平台条件，不能说具备FX3 7.02可靠救砖能力。** Windows官方升级器有旧FX3成功例；M2Mac也有仍可探测但一直失败例；A7CII工具的Windows支持和单机恢复不能补齐FX3的救援实证。[Windows成功](https://www.reddit.com/r/FX3/comments/174wsav/firmware_update_failed_now_camera_wont_turn_on/)；[Mac失败未结](https://www.reddit.com/r/FX3/comments/1hu6qui/fx3_firmware_update_failed_camera_wont_turn_on/)
- 用户缓存`054C:0DA1` MSC只说明以往正常系统USB存储枚举；本账本没有任何将它与故障态Fastboot、Senser、HID或BootROM可用性等同的证据。当前主机OS、USB透传、驱动准备、实际相机状态也未在本子任务测试；需要主报告的官方接口研究分别判断，不能由这里推断。

### Gaps

- 无本用户FX3同机完整低层备份、恢复演练和故障态入口验证；无拆焊eMMC的同机读写前后校准一致性验收。只读研究不会改变这些验收缺口。
- 公开案例通常没有故障码解释出处、分区图、存储/供电诊断，因此不能把“更新之后发生”提升为所有个案均由固件或某芯片损坏导致。
- 记忆只用于复用“本地离线研究不算真机/恢复验收”的边界；当前新事实均重新读取网页/源码。相关记忆：`MEMORY.md:189-202`，rollout `01a17199-bf59-7172-aa74-d2a604ebd5ff`。
