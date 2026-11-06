# 完整移植条件第二次复核

2026-10-30。**本轮仍未取得完整可读 FX5／VENICE 私有供体、当前 FX3 AP／备份，或经典 FX3 7.02 目标修改包的准入通过证据。完整移植仍不能正常刷入。**

上轮 [完整条件复核01](../full-goal-refresh01-20261030/README.md) 的34个封存文件全部复核通过。其9项原要求继续保留，功能完成项仍为0；实际刷机前停止这一约束持续遵守。

## 当前输入

- 公开实时 `git ls-remote` 核对4个仓库，提交全部与前轮一致：A7 IV `12582457829e34eae7211df5b0c599fa46b7e5e1`、A6000 `8a28f96bde389f1d4c24a2be3503a120eebbc927`、fwtool `cdba742b73eed5981480c326aeb30033aabf0223`、PMCA-RE RELOADED `0f03359e72cdf9d75330219c7ae15bf97180486a`。没有重复下载或运行旧源代码。
- [FX5 日本官方结果页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)仍明确表示本页暂无更新信息。结论只覆盖所查页面，不扩大为全球或维修渠道不存在固件。
- 最新已出现的协作[阶段226](../../sony-firmware-20261024/stage226-static-keeper-and-parent-image-contract/README.md)报告已核读并固定摘要。其7项／11场景是自己的 ARM64 程序与假 Linux 联测；报告明确没有相机操作，真实加载适配和机内运行仍缺，首次刷写未放行。本轮只读报告，没有运行它的工具或修改它的文件。

[实时HEAD与协作报告摘要](current-input-check.json)

## RAW 解码搜索线索

本轮定向搜索还发现 rawspeed 的 [FX5 placeholder PR978](https://github.com/darktable-org/rawspeed/pull/978)。页面抓取遇 cache miss，随后直接取得作者的公开patch，782B、固定SHA，完整检查：它仅在 `data/cameras.xml` 添加三行 `ILME-FX5` 条目，状态为 `unknown-no-samples`。没有新增CMOS采集、色彩链、固件解包或目标安装实现。[原patch](rawspeed-978.patch.source.txt) · [捕获回执](rawspeed-lead-capture.json)

另核读 [ARW6 decoder PR983](https://github.com/darktable-org/rawspeed/pull/983)：作者描述的是把ARW6参考解码器移到rawspeed，关联A7R VI相机支持。它不提供当前 FX3 的机内RAW数据链、完整私有ISP或修改整包准入。本轮没有把文件解码器当作整套实时色彩科学，也没有构建、运行或应用这些patch。

上述是限定线索的适用性核对，不是互联网范围不存在其他实现的证明。

## 结论与连续计数

上一目标轮为首次无完整目标进展，本轮仍是相同条件：完整私有供体／有效解包器、目标 AP 与修改包准入／正常启动恢复证据缺失。现连续计数为 **2**，目标保持 active、未完成；尚未达到三轮 blocked 阈值，没有沿用此前10月29日的旧计数。

两项本轮抓取任务均有具体句柄并已确认退出；没有仍在等待的本轮进程，不记录 verified wait。原签名、供体原件和旧模拟结果不重跑，也不因它们仍在磁盘上就推定新固件已可刷。

要改变实施条件，需要上述缺失输入中的有效新证据。当前没有可在本任务授权及设备边界内直接落实整套移植的下一步。未请求签名私钥，未触碰相机／USB／手机／IPC／管理员／其他owner设备；没有修改原固件、生成目标修改包或执行刷写。
