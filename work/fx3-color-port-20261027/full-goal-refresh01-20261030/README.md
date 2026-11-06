# 完整移植与刷入条件复核01

2026-10-30；沿用原完整目标。**本轮未取得能解除完整私有供体、目标 FX3 AP 或修改整包准入缺口的新输入。仍不能提供可正常刷入 FX3 的 VENICE 全链路修改固件。**

上一轮 WBI 分派与暂存区范围研究属于实际研究进展；本轮把新公开工具和官方来源重新核对后，未形成新的目标实施路径，记为恢复后这一连续受阻序列的首次无完整目标进展复核。目标保持 active、未完成；没有沿用10月29日曾经触发 blocked 的旧计数。

## 官方供体来源

- [FX5 日本下载页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)实际结果区仍明确表示本页暂无更新信息。本轮没有取得 FX5 机身固件。结论仅覆盖所查页面，不扩大到全球、维修或未公开渠道。
- [FX5 OSS 页](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)仍是开源软件分发入口，没有由此取得完整私有菜单／ISP。页面快照的长度与 SHA 保存在来源清单中。
- [VENICE 2 官方 V5.00 下载页](https://www.sony.com/electronics/support/software/00376811)与[型号下载目录](https://www.sony.com/electronics/support/professional-cameras-digital-cinema-cameras/mpc-3628/downloads)仍列该版本。[官方路线图](https://pro.sony/ue_US/products/professional-cameras/broadcast-venice-2-firmware-roadmap)将 V6.0列为2027年的计划；计划不等于现在已有可下载供体。
- 核读现有862,640,780B VENICE 2 ZIP的中心目录：里面是此前已经取得的3.92、4.10、5.00三版 `.bin`，不是另一份尚未研究的新版本。另核读三版既有 outer-member 提取回执。这里没有重新提取全部ZIP载荷，也没有恢复私有内层；按目录文件名不推断内部传感器版本划分。[包目录核对](venice-current-package-members.json)

美国 FX5 页本轮直接抓取遇403，web打开超时；搜索缓存中的 RAW Viewer 项目不能当作当前完整固件目录。GitHub API也遇速率限制，后续通过公开 `git ls-remote` 与固定提交 raw 源码补齐了仓库核查。失败记录保留，不把抓取失败当作“没有内容”。

## 新 PMCA-RE RELOADED 是否补上准入

实际核对的默认 HEAD 为 `0f03359e72cdf9d75330219c7ae15bf97180486a`，与阶段7记录的 `d4bcaef29191a44b290ff23c3290f8551c8303fa` 不同。取得该提交的公开源码归档2,814,818B并固定 SHA；仅捕获所需文本，没有编译、安装或运行。

在[该固定版本](https://github.com/masterflai/pmca-re-reloaded/tree/0f03359e72cdf9d75330219c7ae15bf97180486a)核对：

1. 当前 README 将约2018年以后的较新 Sony 的 firmware／updater shell 标为不支持，并说明官方固件刷写仍属未实机验证的实验性功能。
2. `pmca-core/src/firmware.rs::read_dat`检查UFU头并定位FDAT片段；这个入口没有提供当前 VENICE type3／type4 私有内层解包结果。
3. `pmca-app/src/firmware.rs::flash_firmware`把FDAT交给相机 `check_guard`，随后才调用发送。它没有为经典 FX3 7.02 的目标修改包提供通过回执。
4. updater-shell生成器的 `crypter_for`只有 CXD4105、CXD4115、CXD4115_ilc、CXD4120、CXD4132、CXD90014六个分支，其余报 unknown chip。随附 `models.tsv`按原代码的tab／十六进制字段规则解析为121行，没有精确 FX3／FX3A／FX5项。

这是对所查解析器、发送器、生成器和机型表的限定核对，不推定所有现代机型的设置读取／service操作都不可用，也不宣称整个仓库任何路径均已穷尽。其旧FDAT算法代际不能仅凭数字或名称套到 VENICE 私有容器。没有读取或导入密钥，没有运行任何新工具。

[源码适用性核对](reloaded-applicability-review.json) · [机型表](reloaded-model-table-review.json) · [固定源码捕获](reloaded-selected-source-capture.json) · [额外源码](reloaded-extra-source-capture.json)

其余三个已审公开仓库的 HEAD 与上次核对一致：

| 仓库 | 当前提交 |
|---|---|
| leogenot/sony-a7iv-feature-research | `12582457829e34eae7211df5b0c599fa46b7e5e1` |
| nicolvus/a6000-fw-decomp | `8a28f96bde389f1d4c24a2be3503a120eebbc927` |
| ma1co/fwtool.py | `cdba742b73eed5981480c326aeb30033aabf0223` |

[实时HEAD](git-head-fallback.json) · [固定README来源](pinned-readme-capture.json) · [初始HTTP成功／失败清单](public-source-capture.json)

## 完整要求逐项状态

| 原要求 | 本轮可证明的状态 |
|---|---|
| FX5 整套私有菜单与依赖供体 | 未取得完整可读供体 |
| VENICE 完整实时色彩／ISP链 | 私有内层与完整域映射未完成 |
| RAM芯片、DMM与实际缓冲区调用 | 已有静态描述符／参考分派，缺目标硬件初始化与实际数据绑定 |
| CMOS RAW与传感器标定 | 缺实际采集链、样本及域验证 |
| 专业菜单与MAIN录制接通 | 未完成整套UI／控制／目标输出 |
| 包含所求全部变化的精确FX3修改固件 | 未生成 |
| 经典FX3 7.02修改整包准入 | 未取得可复核通过证据 |
| 正常启动与独立恢复 | 未通过实机／独立恢复验收 |
| 停在实际刷机之前 | 持续遵守，不替代前八项 |

三个原FX3包的当前完整SHA与原验证输入一致；8份关键历史成员及对应历史封存摘要通过复核。本轮未重跑原RSA测试：保留原三包签名有效、保留旧签名的12处单字节变化均被拒绝，以及原7.02密文加IV的独立主机验证结果。它们证明原签名边界，不证明目标修改包会被接受。没有搜索签名私钥或尝试签名。

最新协作[阶段225](../../sony-firmware-20261024/stage225-im-reaper-and-loader-ABI-audit/README.md)仍为原厂im静态分析与自写ARM64模型；它找到了子进程回收竞争和加载ABI缺口，没有提供目标 AP、同机备份或实机独立恢复。本轮只读报告，没有运行其工具、修改其文件或重问其待答事项。

[完整要求与输入核验](readiness-refresh.json) · [可复核程序](audit_refresh.py)

## 持续目标与受阻计数

此次复核后，同一关键缺口连续计数为 **1**，未达到 blocked 的三轮阈值。所有本轮抓取／校验进程已确认结束，没有把对话或旧锁当作仍在运行的任务，也没有记录 verified wait。

能改变下一步实施条件的输入包括：可读完整私有供体或适用解包器、目标修改内容的准入／加载证据、由其授权 owner 提供的当前同机 AP／备份／独立恢复证据。本轮不以其他机型模拟、设置开关、主机发送器或LUT替代这些要求。

原件、旧封存及共享历史均保留；无设备、USB、手机、相机 IPC、管理员、Sony原程序执行或实际刷写。目标仍 active、未完成，没有输出可刷包。
