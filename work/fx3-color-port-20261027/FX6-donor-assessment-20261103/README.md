# FX6 供体、FX5 菜单和 A7C II 安装方法：续接核查

2026-11-03。承接用户提出的完整 RAW／底层色彩链及专业电影菜单方向。供体研究已完成下述有界静态与 CPU 仿真阶段；尚未完成移植。外盘 UUID 已核验；Mac 项目本身不是 Git 仓库。原件和相机未修改；另一路已在独立运行目录完成 AP105 模拟器首轮实跑，后续验收仍在进行。下方早期“未运行 VM”等描述是各阶段当时的记录，以最新总协调状态为准。

## 最新总协调状态

- **供体离线阶段已收束，移植未完成。** [调用者与选择审计](team/donor/cp-av-analysis/init-routing/caller-selection/README.md)确认 5 处原 DMA 构造调用，以及事件字段、覆盖标志到构造参数的数据流；5 个有界 CPU 用例通过。人工 look 22 / ip 0 输入不等于自然 MAIN 选择。首个缺失证据是 provider 表 `+0x4c0` 的返回值与 4B word，以及 `+0x3c0` 返回的事件对象与真实输出路径的对应关系。
- [原始初始化与 DMA 描述构造](team/donor/cp-av-analysis/init-routing/README.md)已验证原 memcpy、152B 目标描述符及带显式地址映射/cache 桩的 70 条链表。没有实际 DMA 提交或像素输出。30 组 VENICE 描述及数据与 FX3 相同，不能把复制这些表当作 FX6 完整色彩移植。
- [Base ISO 研究](team/installer/ap-abi-comparison/base-iso/dirty-consumer/README.md)确认本地模型及 dirty 位图读写，但运行时对象列表、IPC 与消费者未闭合；该有界分析阶段结束，兼容性仍未知。
- [Gemini V2](team/gemini-menu/README.md)已撤回 V1 的完整 DMA、落盘和 1K 白平衡映射结论；接受固定输入、显式 30 处桩及正反例的局部包构造/写入实验。其 AP105 离线状态为旧快照，完整 RAW/ISP 架构说明不等于逐段二进制或像素证明。
- **模拟器仍在验收。** [AP105 首轮实跑报告](../../fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/vmopt-20261103-runtime-report.md)记录 1200 秒运行、English UI/RAM/原生文件字段对应和正常退出。182 个已配对绘制样本上界最大 2839.466ms；140 条未配对记录仍须分类，不能据此宣称全部绘制达标。关闭菜单后静置、日期原值 OK 与冷启动重载尚未完成。运行负责人独占推进下一轮；未提升默认候选。

- **后续 1800 秒上限轮未通过。** [保存轮报告](../../fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/vmopt-20261103-save1800-report.md)确认 English 关闭后静置 91 秒稳定、日期中心键确认及有效 generation4 文件。旧 140 条记录已确认属于非 GPE 模块。新轮 452 组 GPE 均有完成/释放记录，但存在内核队列释放错误、两段超过 5 秒的保守区间，并在 1415.585 秒触发现有 OSD allocation deadline 停止门。冷启动未执行、TRY2 未部署。运行与 host 两路正在分别查生命周期根因及性能压力；不把正常退出或局部保存证据算整体验收。

- **生命周期修复与冷启动阶段已通过。** [最新两轮回执](../../fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/lifecycle-repair/RESULT.md)证明注入 observer 的计时起点误含自身日志阻塞；修复并集成 host 降负载后，1561 秒/819 组与冷启 264 秒/250 组均完整配对，无相关错误或超过 5 秒的已测上界。English 原生保存、固定副本冷启动及实际图标画面通过，退出和双锁释放完整。旧内核释放错误的唯一底层成因仍未知。已进入 TRY2 本机网页交付阶段，网页与启动/中途退出边界验收尚未完成，当前未提升试用入口。

机器可读分工与验收状态：[coordinator-state.json](team/coordinator-state.json)。没有可刷入候选，完整 RAW/ISP、主录／监看选择和实机效果继续明确保留为未知。

## 已确认的新进展

FX6 6.01 官方更新包不是缺失供体：已取得头部 65,536 字节和尾部必要区间。UFU 包含 FDAT，完整长度为 847,081,840 字节。使用固定版本 fwtool 的公开方法，首块成功识别 `UDTRFIRM`、版本 `6.01`、model ID `0x91040086`，块校验及头 CRC 均通过。见 [首块实测](fdat-probe.json) 与 [传输/容器记录](firmware-prefix.json)。这证明可以继续研究其解包，不证明完整解密、官方签名有效、SoC 相同或 ISP 兼容。首块阶段当时尚未下载完整包；后续完整取得与解包已完成，见下方团队验收。

来源：[Sony FX6 6.01](https://www.sony.com/electronics/support/software/00259043)、[官方包](https://support.d-imaging.sony.co.jp/download/NEX/Dobb4b83c7/BODYDATA.DAT?fm=cn)、[fwtool 固定提交](https://github.com/DavidBuchanan314/fwtool.py/tree/3955d7890fc38daf942bb52827599bfe35de4a14)。公开常量只在内存读取，未保存或打印密钥。

## A7C II 实际如何扩展功能

必须区分两份项目：

- `chocotan/a7c2-re`，当前 API 返回提交 `d79257cf6815642b9794fa5b590c9626bfbc2c67`。11月1日 HEVC30 文档说明只改 AP 应用的菜单、限制、参数与消费者，沿用原编码器；VM 菜单往返通过，实际录像未验收。它的研究加载路径与官方升级包签名不是一回事。
- `QAQLeonard/a7c2-fl23-research`，当前 API 返回提交 `ef7db116e13e37be91e9af20360dc9bba8d64a9b`。不是只改设置。`src/fl23/native/installer.c:38` 指向 AP 与 CP 文件，`:71` 核对 `/dev/nflasha15 /usr ext2`，`:130–147` 校验原文件和补丁窗口、remount 可写、打补丁、完整 hash 回读及错误回退，`:158` 恢复只读。主机 workflow 还读取本机设置和两份原程序；冷启动后的实际装载状态另行核对。这里只审阅源码，未运行其安装器。

[HEVC30 原文](https://github.com/chocotan/a7c2-re/blob/d79257cf6815642b9794fa5b590c9626bfbc2c67/report/2026-11-01-hevc30-ntsc-retest/README.md) · [FL23 原安装器](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/fl23/native/installer.c) · [本轮源码定位及 SHA](a7c2-native-review.json) · [主机侧定位](a7c2-source-review.json)。源码仅在内存审阅，保留定位摘录，不另克隆仓库。

因此，“官方 DAT 需要签名”不能推导成“不能做功能扩展”。文件级持久修改是实际存在的另一种路线；它仍依赖机型、固件、文件布局、加载链与恢复方式。A7C II 的偏移和分区不直接套到 FX3。作者的 A7C II 成果也不构成 FX3 验证。

## 菜单移植的具体目标

[FX6 6.01 官方说明](https://www.sony.com/electronics/support/software/00259043)包含 BIG6；因此可直接研究 FX6 现有菜单，而不必等待 FX5 完整私有固件。该版还修正高饱和区域色彩再现，说明供体版本应固定，不能把不同版本的色彩结论混用。

[FX5 快捷菜单](https://helpguide.sony.net/ilc/2630/v1/en/contents/quick_menu.html)与[完整菜单操作](https://helpguide.sony.net/ilc/2630/v1/en/contents/fullmenu_use.html)可用作交互规范：短按进入概览，长按进入完整菜单；返回取消未完成更改；项目格式、TC/Media 等分类连接相应真实参数。它们是菜单行为参考，不能充当原始菜单代码。

FX3 侧适配必须沿菜单事件 → 原参数模型 → 模式限制 → CP/AV 消费者 → 实际输出逐层建立映射。没有实现的 ND／SDI 等硬件项不能显示为可用。先验证有原生后端的参数；不能只改文字、截图或界面皮肤就称为移植。

## 完整 RAW／色彩目标不降级

用户要的链路按以下范围保留：传感器读出及黑电平/坏点/镜头校准，去马赛克与降噪，白平衡/色彩矩阵及色域、曲线/高光处理，MAIN 录像及监看分流，菜单控制和保存。各层仍须从 FX6 二进制、FX3 对应消费者和固定输入输出证明。

[FX3 既有色彩研究](../README.md)已恢复的 VENICE 命名矩阵、1D/3D 表及 look 22 是 ACES Rec.709 外观链的部分证据，不能替代上述 RAW/ISP。FX5 的 `ldec` 是图片/资源压缩解码，也不等于 CMOS RAW 去马赛克。

完整取得、摘要固定和解包清单已由供体工人完成；下一项是比较 AP/CP/AV 的处理器、装载地址、导出符号和 IPC。找到可分离的 RAW/色彩模块后，先做固定输入的离线重放，再接 FX3 VM 参数链。当前没有可刷入候选，也没有完成 RAW 像素结果或菜单移植验收。

## 本次运行说明

`collect_evidence.py` 仅读公开源码和包头；`probe_fdat.py` 仅读公开常量和更新包区间。首次 urllib 包头请求遇 TLS EOF，改用 curl 得到 206 和精确区间；全包内核下载改为带 ETag 的分段请求。未改变原 VM 的 preferred candidate、锁、按键输入或运行状态。进程盘点未见 `run_trial`／`qemu-gpio5`，不能沿用旧聊天“试用仍在运行”的说法。

## FX6 官方 GPL 平台实查结果

本轮完整读取官方两个源码压缩包，在内存中核验长度及服务器 Content-MD5 后扫描，未执行其中代码、未另存第三方代码目录：

- `linux-kernel.tar.gz`：109,952,792 B，Linux 4.9.337；SHA256 `2e5bdfa72018cef6bdfa209635794973d7266c7ee657db094c7ee2c414dbcc42`（完整值以[原回执](linux-kernel.tar.gz.evidence.json)为准）。
- `linux-kernel-u.tar.gz`：108,790,863 B，Linux 4.9.186；[原回执](linux-kernel-u.tar.gz.evidence.json)。两个包的运行角色尚未从启动链确认，不根据 `-u` 文件名断言。
- 两份 `cxd90057.dtsi` 都列出 `cxd,cxd90057`、四个 Cortex-A35 CPU 节点和 GIC-400；普通内核的该文件与现有 FX3 官方源码副本 SHA256 完全相同。见[独立本地比较](fx3-fx6-dtsi-comparison.json)。

这为优先研究 FX6 提供了比 BIONZ XR 商业名称更具体的平台依据；仍不证明量产DTB选择、板级外设、传感器校准、CP/AV ABI或完整ISP相同。[Sony FX6 V6.00 OSS入口](https://oss.sony.net/Products/Linux/B2B/ILME-FX6V_Ver600.html)。注意源码关联版本为6.00，固件供体为6.01，不混称同一制品。

## 总协调验收与下一轮

- 接受[完整FX6供体](team/donor/README.md)取得/静态解包阶段：全包SHA、容器校验、1,241个展开文件及4个核心产物重哈希回执齐全。官方签名、WBI恢复与RAW算法仍未知。
- 接受[本地原件审计](team/installer/README.md)及路径越界修复。它没有设备访问或安装能力。
- 接受[FX3 im到appFw静态装载边](team/installer/loader-binding/ap-reader/README.md)。总协调另用Capstone只读核对PLT 0x402150→GOT 0x4190F0、0x405e24起连续参数处理及0x406274起类型分派，与工人结论一致。没有将VM日志当作真机冷启动身份。
- 后续已派两路：供体CP/AV映射及MLUT/上游像素链比较；AP依赖ABI与电影色彩参数生产者比较。Gemini专业菜单首轮已回报，但总协调复核未接受其完整链结论；受限包构造/setter模拟不能充DMA或像素链，已要求修正及补验。所有运行链/相机操作仍未执行。
