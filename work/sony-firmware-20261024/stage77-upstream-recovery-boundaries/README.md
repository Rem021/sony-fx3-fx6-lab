# FX3：上游恢复路线、备份范围与REA入口复核（2026-10-26）

**本轮核对的上游项目仍未提供可直接用于FX3 7.02的独立救援保障。** A6700／A7 IV的硬件启动研究值得继续对照，但机型入口、RAM程序、存储映射和同机恢复必须分别验证。拥有Mac与Windows还不足以证明能救砖。

本轮只读取公开资料、复核本地官方包及计算参考区间，没有新增相机、编码器或恢复执行结果。原型进度仍为离线阶段：16M参数局部链路已有证据，硬件主录、音画长录、健康备份和独立救援未验收。完整16项目标不变。

## 上游变化与没有变化的部分

- [A7C II Tools 3.0.3](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)修复了USB接收、只读失败退出等问题；[支持范围](https://github.com/QAQLeonard/a7c2-fl23-research#supported-cameras)仍仅为ILCE-7CM2／2.01。main HEAD为`ef7db116…`，与stage46已审代码相同，不重复算成新增移植成果；发布tag固定于另一提交`78278564…`，不能混同main与安装包。
- [故障讨论#31](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)在10月26日新增一名用户对既有视频／P模式旁路的成功确认。仍是社区自述，不是FX3复现；其余“准备试试”和维修讨论不能算成功恢复。该旁路依赖仍能启动的功能路径，不能保证视频链修改后仍成立。
- [A6700项目](https://github.com/xyzhangxin/sony-a6700-powerful)提供特定机型的Pico／RAM Fastboot参考，但明确完整备份恢复尚未提供。[A7 IV原作者研究](https://github.com/DavidBuchanan314/ILCE-7M4-RE)有独立启动及备份／恢复实现，同时保留boot0加密处理边界；均不能直接迁入FX3。
- [fwtool PR#52](https://github.com/ma1co/fwtool.py/pull/52)仍为Open，head仍为`3955d789…`；解密测试列有FX3，不构成修改包刷回、主录实现或独立恢复证据。

以上复核不下载讨论中的机身诊断附件，也不执行上游应用、RAM程序、认证或硬件注入。

## 参考备份到底覆盖多少

固定A6700文档提交`d5bb9485…`后，按[操作手册](https://github.com/xyzhangxin/sony-a6700-powerful/blob/d5bb9485dfe7cc4bf13a4ead3a7437c2f40240a9/%E6%93%8D%E4%BD%9C%E6%89%8B%E5%86%8C.md)逐项复算：

| 文档记录的范围 | 区间字节量 |
| --- | --- |
| 用户区分区表覆盖的`0x379000`个512字节扇区 | 1,864,368,128 |
| 两个引导区各前4MiB | 各4,194,304 |
| 上述已知范围合计 | 1,872,756,736 |

用户区按16MiB划分是111个整块加一个2MiB末块，共112块。此处只生成参考区间并核对连续性和总量，**没有读取这些区间、验证备份文件或核对真实双读哈希**。

原文未确认整个物理eMMC容量，也未验证完整恢复，因此不计算“完整备份百分比”。范围读回一致并不能证明遗漏容量、同机真实性、加密／明文格式一致或写回可用。表中的数值不是FX3分区常量。

该硬件路线会将程序加载进相机RAM并改变启动环境；文档的“只读”限定固件／区间读取，不把它纳入当前仅缓存PnP授权。本轮只下载文档，未下载载荷或生成注入／刷写命令。

## REA当前能接收什么

固定[REA固件说明](https://github.com/morluto/rea/blob/f89b03e738fe94f2bea6927c84e05871293707ea/docs/firmware-analysis.md)后核对：该固件入口限制128MiB，验证范围是Linux x64及有限格式；分析覆盖标记不证明完整重建。当前官方FX3包811,876,768字节约774MiB，超过该入口限制。本地包完整SHA-256本轮重新核对一致。

已解出的`av-cam.bin`约13MiB、不是ELF。大小合格不等于该文档的ELF子文件流程已支持它；不能把本轮专用原字节分析说成已经跑过REA固件引擎。其它REA工具／分析器的支持也须分别确认，本轮不启动引擎、不修改其准入限制。

## FX3仍需跨过的恢复门槛

1. 证明FX3自身的独立启动入口、身份、所用程序与RAM／存储映射，不能借其它机型标签或一次HID枚举判定。
2. 获得同机健康原件和有明确范围、几何、格式与身份绑定的备份；通用官方包不能替代机身独有内容。
3. 建立FX3受限恢复器及回读、启动、功能和对应故障范围验证。恢复文件、写入成功、启动成功和录像正常须分开。

当前这些要求未满足，不会为获得证据而故意破坏主力相机。Windows继续按用户要求延后，没有轮询UU或催代发；所有相机接口、模式、认证、驱动、模块、WBI和刷写权限保持原范围。

- [原始来源与观察回执](upstream-observation-receipt.json) · [文档提交与哈希](source-manifest.json)
- [参考备份区间计算](reference-backup-coverage.json) · [REA与本地样本输入范围](REA-input-and-native-admission-scope.json)
- [FX3独立恢复迁移矩阵](FX3-independent-recovery-transfer-matrix.json) · [完成复核](completed-evidence-review.json) · [复核器](audit_boundaries.py)
- [阶段封存](final-receipt.json) · [完整目标](goal-status-after.json)

GitHub REST API请求遇到403限额，未以API失败推断项目状态；改用公开原页与只读git引用核对。仅保存公开参考文档，没有克隆新仓库、下载机身附件或执行第三方程序。
