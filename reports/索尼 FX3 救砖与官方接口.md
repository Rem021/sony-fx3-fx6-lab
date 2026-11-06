# 先厘清 FX3 故障，再建立恢复能力

核查截止：2026-10-27。对象：经典 **Sony ILME-FX3、用户菜单确认的 7.02**，目标为 1920×1080、30000/1001（29.97，用户所称“30”）、H.265/HEVC 主录；精确 30.000 另列。本报告综合官方资料、维护者源码与原始机主后续，分别标注其证明范围。

**索尼确有可以恢复的更新失败、设置异常和启动状态故障；现有 Mac＋Intel/AMD Windows 11，尚不构成经过验证的经典 FX3 7.02 修改固件救援环境。** 官方公开方法覆盖部分保留更新能力的故障，社区亦有黑屏后成功恢复和最后换主板的真实记录。Sony 有维修技术资料体系，但公开页面没有交付一套已确认适用于这台机身的独立恢复软件、接口和载荷。A7 IV 已公开 BootROM/eMMC 研究，尚无经典 FX3 的同等适配闭环。因此，可以继续离线研究及设计可逆试验，**不能以“刷坏后两台电脑总能救回”为依据放行持久修改**。

## 官方能处理指定更新错误，未公开任意强刷入口

Sony 7.02 发布于 **2026-03-17**，经典 FX3 正常流程为槽 1 存储卡中的 `BODYDATA.DAT`，由机身版本菜单执行；≤2.02 须先经 2.04/2.05。正常更新约六分钟黑屏，访问灯按 1→3→5 次循环闪烁，期间不能任意断电。5 长 6 短或 7 长 7 短才对应页面列出的失败分支：核对前置版本与文件，按说明重新准备正确卡及文件后重试。这里记录的是**适用故障场景，不是让当前健康机身执行恢复**。([Sony 中国 7.02](https://service.sony.com.cn/download/firm/00003048.html)、[Sony 美国操作与错误处理](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561))

日本卡更新 FAQ（2026-06-10 更新）明确把**同版或旧版 DAT**列为版本错误原因；换卡重试后每秒一闪表示续行，仍无改善则要求维修。因此，保存 7.02 官方包不能视为已拥有 7.02 同版强制覆盖或降级能力。另一份专业机 FAQ 的“黑屏超过十五分钟后断 USB、取电池、重启电脑并按 MSC 重试”，位于**电脑 USB 更新**分支，不能套用到 7.02 卡更新。旧 2.04/2.05 USB 程序只服务指定旧版本过渡。([Sony 卡更新 FAQ](https://support.sony.jp/electronics/support/articles/00282342)、[专业摄像机失败 FAQ，2026-06-25](https://support.sony.jp/electronics/support/articles/00405391)、[旧版过渡更新](https://service.sony.com.cn/content/casch/download/firm/00002966.html))

一处仍需保留的来源差异是：中国 7.02 页同位报错写“更新文件版本不正确”，美／日页写目标机型不符。应保存实际完整提示，不能只凭译文把两个原因合并。([中国操作页](https://service.sony.com.cn/download/firm/00003048.html)、[美国操作页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561))

官方也承认过实际故障：6.00 曾于 2024-09-13 停发，处理后于 10-09 恢复；6.02 修复特定带用户 LUT 的 6.00→6.01 升级后不能录像或操作的问题。这证明“更新后异常”存在多种层级，并不提供统一底层恢复法。另有 Sony 署名通报 **22PV028 Rev0，2022-11-18** 的经销商公开预览，对 FX3 2.01／FX30 1.01 特定循环重启规定换 SY 板；它不是 7.02 的现行救援承诺。([Sony 版本历史](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243)、[旧通报公开预览](https://store.professionalshow.com/ImagesNoZoom/TECHDRAW/BA026/BA026118.jpg))

## 一手机主记录显示，黑屏既可能恢复，也可能最终换板

**旧 FX3 确有电脑更新恢复成功的完整自述。** 2023-10-10 发帖的机主在 2.02→2.05 失败后，屏幕不开、插电池红灯常亮，但 Windows 更新器仍能通信；他称依 Sony 电话支持建议断电后运行 3.00 成功，再用卡升到 4.00。2024-07-28 另一位 2.00→2.05 机主黑屏，次日满电、换 USB 口后完成 3.00，再到 5.00；作者不能确定电池或端口哪个起作用。两例证明部分黑屏仍保留更新通道，**绝非 7.02 降到 3.00 的依据**。([2023 原帖及本人后续](https://www.reddit.com/r/FX3/comments/174wsav/firmware_update_failed_now_camera_wont_turn_on/)、[2024 原帖及结局](https://www.reddit.com/r/FX3/comments/1edyf73/fx3_firmware_update/))

相反，2025-01-05 的旧版 FX3／M2 Max Mac 记录中，更新器持续探测得到相机，却始终更新失败，公开无最终结局；“电脑认得到”并非必救。2025-04-11 的 FX3 4.00→6.02 机主报告异常灯序、多次重试无效，后续明确服务中心换主板；2024-09-27 另一位 6.00 更新失败机主也报告保内换板、返还后正常。**这些是未经独立实物复验的一手结果；换板不能证明原芯片物理死亡，也不能证明官方没有软件修复选项。** ([Mac 失败未结案](https://www.reddit.com/r/FX3/comments/1hu6qui/fx3_firmware_update_failed_camera_wont_turn_on/)、[6.02 换板结局](https://www.reddit.com/r/FX3/comments/1jwp86i/602_firmware_update_bricked_fx3/)、[6.00 返修后续](https://www.reddit.com/r/FX3/comments/1fqgexj/in_need_of_the_fx3_ver_600_dat_update_file/))

设置初始化也有适用前提：2022-12-08 的 FX3 2.00 机主视频报告装镜头后 System error、偶发不开机及 USB 不识别，仍能进菜单，以 Setting Reset→Initialize 后称恢复；未找到长期复验。这是可进菜单的异常恢复个案，不能称为底层硬砖救回。([机主原视频说明](https://www.youtube.com/watch?v=-NlrQcuYGBQ))

A7C II 外观修改项目 **#31 的旧结论必须更新**：2026-10-27，首帖作者表示从视频模式开机、切回拍照模式后恢复，FL23 等仍保留；另有操作者以 Movie／曝光 P 启动恢复，第三人确认有效。早先“官方要求换板”的口述没有成为最终必然结局。行为提示其中存在可绕过的模式／启动状态问题，**根因仍未证实，办法也未适配 FX3**。项目“一键原厂恢复”仅覆盖所改程序区域和设置，仍依赖服务，不是全机镜像或独立救砖。([#31 最新本人后续](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6442900646)、[其他操作者办法](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6399306736)、[恢复范围说明](https://github.com/QAQLeonard/a7c2-fl23-research/blob/main/docs/en/development.md))

## 官方确有维修体系，但 FX3 工位软件与早期接口仍未公开闭合

Sony Professional 的技术订阅页列出维修手册、服务菜单、电气校准、错误码与诊断、固件升级流程、板图和技术公告；访问须经登录及订阅申请，公开页没有经典 FX3 的逐型号覆盖表。历史 Sony 署名 HXR-MC2500 手册镜像确有 **Adjust Station／Adjust Manual**，DSC-WX1 手册镜像也有换板前保存序列号及传感器数据的要求；这些不是 FX3 的工具名、平台条件或校准项目清单。本轮未取得 FX3 型号模块、认证条件、硬件夹具或早期恢复流程。([Sony 官方技术订阅](https://pro.sony/ue_US/support-services/professional-subscriptions)、[HXR-MC2500 手册镜像](https://www.manualslib.com/manual/2054656/Sony-Hxr-Mc2500.html?page=23)、[DSC-WX1 手册镜像](https://www.manualslib.com/manual/2053917/Sony-Dsc-Wx1.html?page=5))

公共软件须按功能而非名称判断。Creators’ App 是手机下载→传到相机卡→机内更新；Imaging Edge Desktop 公开能力是遥控、浏览与照片 RAW 显影。**不能笼统声称官方 SDK 都没有更新 API**：Camera Remote SDK 当前为 **2.02.00，2026-06-10**，FX3 在总支持表内，Windows 11 条件为 Intel/AMD、排除 ARM；历史 1.13 远程更新脚注当时仅列 ILX-LR1。Camera Remote Command 2.00 也宣传常规远程固件更新，但最新 FX3 逐 API／命令兼容表需经表单取得，本轮未提交。即使支持常规远程更新，仍不能推成无主系统时的紧急恢复、裸闪存备份或校准接口。([Creators’ App](https://helpguide.sony.net/di-app/ca/v1/en/contents/CA_update_software.html)、[Imaging Edge](https://support.d-imaging.sony.co.jp/app/imagingedge/en/)、[SDK](https://support.d-imaging.sony.co.jp/app/sdk/en/index.html)、[Camera Remote Command](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/en/index.html))

公开官方处理终点是按症状重试、无效送检；中国政策确列 ILME 系列软件升级与维修服务，但具体是否重装原板、换板、校准以及费用须检查后报价。可进一步核实的正是型号专用工位能力及恢复范围，不能预先宣称某软件必救或必换主板。本轮没有联系服务方或提交序列号、表单。([Sony 中国服务政策](https://www.sony.com.cn/content/casch/serviceinfo/servicepolicy.html)、[FX3 官方支持入口](https://service.sony.com.cn/products/di/ILME-FX3.html))

## 公开底层研究有价值，现有双机仍缺目标机身恢复链

PMCA 的 Senser 是实验性维修模式逆向；`serviceshell` 要启动、认证、重枚举、再次认证，其通用参数备份、文件和内存 API 也互不等价。FX3A 2.02 在 M2 Mac 上改 PAL/NTSC 成功，仅证明该型号与操作。经典 FX3 已封存的本地静态审计发现 `GET_FILE2` 候选有条件写日志、挂载、整文件分配与同步依赖，**GET 名称不能保证只读**；这也是为什么现成“备份”按钮不能直接视为已审计的安全读取路径。([PMCA 会话源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L656)、[FX3A 案例](https://github.com/ma1co/Sony-PMCA-RE/issues/715)、[本地读路径审计](../work/sony-firmware-20261024/stage130-backup-read-path-side-effects/README.md))

更独立的证据来自 **ILCE-7M4／A7 IV**：研究者通过早期串行 BootROM、RP2040-Zero 桥板与自制裸机 fastboot，经 USB 读写 eMMC。SDM2 分区有透明加解密，boot0 的相应转换尚未实现；这不等于不能读取 boot0 原始字节。相同 CXD90057 不证明 FX3 引脚、触发、布局或载荷兼容。另一工具 `fwtool.py` 的 CXD90057 分支能解包 FX3，但加密输出明确未支持，不能据此制作安全可刷的修改包。([A7 IV 固定版研究](https://github.com/DavidBuchanan314/ILCE-7M4-RE/tree/2328d18ce640e6c8cd9341efcf0043ce9042a135)、[fastboot 限制](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/2328d18ce640e6c8cd9341efcf0043ce9042a135/payloads/fastboot/README.md)、[fwtool PR52](https://github.com/ma1co/fwtool.py/pull/52)、[未支持加密的源码](https://github.com/DavidBuchanan314/fwtool.py/blob/3955d7890fc38daf942bb52827599bfe35de4a14/fwtool/sony/fdat.py#L191))

| 故障／前提 | 方法或工具 | 已证适用范围 | 对经典 FX3 7.02 与现有双机的判断 |
|---|---|---|---|
| 官方更新器仍活、指定卡／版本错误 | 正确 DAT、槽 1 卡更新 | FX3 官方流程 | Mac、Windows 可准备材料；同版强刷及任意损坏恢复未获支持 |
| 菜单仍可进、设置／状态异常 | 菜单初始化或型号特定模式切换 | FX3 2.00、A7C II 分别有自述 | 不覆盖底层启动损坏；不跨型号照搬 |
| 旧版黑屏、USB 更新器仍通信 | 旧官方 USB 过渡程序 | FX3 2.0x 升级链有成功自述 | 不可移作 7.02 降级或通用重装器 |
| 正常通信、需遥控或常规更新 | App、SDK／Command | 各自型号／功能条件 | FX3 最新更新 API 未核验；不构成独立救援 |
| 主应用局部失效、OS／服务仍存 | FX3 专用 Senser／Jiritsu 恢复候选 | 公开通用协议及本地静态证据 | 目标入口、权限、备份、回写及退出均未验收 |
| OS／服务不可用、早期硬件仍活 | BootROM、RP2040、型号载荷 | A7 IV 原始研究 | 尚无 FX3 适配；普通 USB 线及双机不足 |
| 无公共入口或疑似硬件故障 | 官方诊断、板级维修／换板校准 | 官方维修体系与换板个案 | 可送检；公开资料未确认 FX3 工位工具或保证结果 |

当前本地新增证据只到 **Mac 系统缓存**：一台 ILME-FX3，`054C:0DA1`，接口 0 为 `08/06/50`，关联 MSC 驱动。它不证明当前可独占通信、实际程序哈希、服务认证或故障后可达；旧 Windows 普通 MSC 记录也不能补齐这些门槛。授权仍仅限 Mac 缓存，没有主动 USB/SCSI/PTP/vendor 请求、认证、机身文件、驱动变更、模块、WBI 或闪存操作。本轮写作没有执行上述动作；没有健康同机备份、目标 HEVC 主录文件或 FX3 救援闭环。([本地缓存与授权回执](../work/sony-firmware-20261024/stage130-backup-read-path-side-effects/README.md))

## 试验的下一道门是恢复证据，而非增加电脑或备份按钮

后续应先固定机身型号、7.02 实际程序指纹与拟改范围，取得同机健康原字节和必要设置，并证明对应读路径的副作用、边界和退出语义。局部程序恢复不必一律要求全盘镜像；若要承诺 OS／启动损坏后仍能救，则还需独立入口及匹配的存储、boot 区、身份和校准材料。**官方 DAT、另一台机身 dump、参数导出、正常状态认证成功，各自都不能替代该恢复承诺。**

随后应以不依赖拟改主应用的型号专用入口，完成原字节恢复、完整读回、受控冷启动及原功能复验；不以让主力机先变砖来取得证据。功能试验优先采用经过审计、可撤销的 RAM 路线，验证真实编码器输出为目标主录 HEVC，并检查可解码文件、音频、时戳、长录与温度；RAM 可撤销也须实证。最后才评估可持久安装版本及其失败恢复。本报告没有给出成功率或保证日期：**当前缺口是经典 FX3 的实机恢复证据，继续增加离线阶段或主机软件不能将其自动标为通过。**
