# r33 因果观测候选：布局准入失败，未构建运行候选

**结果是 failed。** 已完成可实施性审计和可复现失败证据；由于全 writer 安全边界尚未闭合，依正式任务的“任何潜在覆盖或身份不明即停止生成运行候选”要求停止。没有把报告完成或host夹具通过标成候选完成，没有VM/boot/menu或根因修复通过声明。FX6 provider及固定FX3平台未改变。

## 关键发现

1. 实际 N64 CPIO 的 **1140 个成员**逐项匹配r31运行审计，26个simulation ELF纳入mapper/exporter发现清单。UI常态直接writer和CAPID两个间接复制回调没有使用 `[0x7000,0x7800)`；实际pin/panel复制长度分别3720/120B，不能把capacity误当实际写长。UI初始化仍会覆盖这段：实际编译代码先清零p+0x10起65520B，继而写magic/version及PID。原before/after ELF `.text` 绑定与反汇编见 `UI-COMPILED-BINDING.json`、`compiled-ui-dlopen.txt`。
2. **不能因此宣布这2KiB可用。** 实际装入GPE v26-perf从成功native-open的resource对象接受phys/bytes，按live identity/epoch/range复核，然后用prot3映射整个destination parent；这些本地谓词没有UI reserve排除。`resource-v26.inc:40–70,108–118` → adapter`:212–245` → `cache-v26.inc:13–21`，源码/实际ELF绑定在 `GPE-SOURCE-BINDING.json`。尚缺原生resource::open/DMM对该保留区的完整排除证明，因此全 writer 审计在此停止；没有继续穷尽其他动态路径后声称通过。
3. 原样提取的基线函数host审计 **11项通过**：合成的native-open/type403/同class/同identity/UI物理范围可被本地谓词接受并请求65536B/prot3的mock映射；仅gap范围会按页扩成4096B。并覆盖原native open一次/rc/errno、错误state/identity/溢出/越界/多parent/identity变化，以及UI claim/cmdline/open/mmap失败和真实bind函数的清零行为。**native open、screen、物理内存、mmap/pread均mock；反例的真实固件可达性未证明，没有真实物理写。** 原始编译和运行stdout/stderr在 `host-fixture/`，提取位置/hash在 `EXTRACTED-FUNCTIONS.json`。
4. 四个既有窗口各有4条完整resource注册记录，UI overlap均0。`HISTORICAL-WRITERS.json` 保留字节偏移/范围/限定窗口；r28仍只是pre-first-timer日志前缀，r31窗口为原finally前host已消费前缀；不同host/guest时钟、token/完整record、End后快照不混用。没有用这个“0”排除所有潜在writer，也没有将本次布局缺口归因为r31实际零ring。

完整范围表、跨模块映射、宿主唯一已识别UI写请求 `[3000,3040)`、实际既有End读回路径、UI claim/清零/ready/PID和early publication unknown边界在 [LAYOUT.md](LAYOUT.md)。原probe池只剩4个槽，不能直接塞入完整新增阶段集；该事实作为后续缩减预算的约束，未擅自扩池或改变原native ABI/尾调用。

## 验证边界和交付

| 层级 | 结果 |
|---|---|
| 全writer/初始化/身份准入 | **失败：动态GPE alias的原生DMM排除未证** |
| 基线本地谓词host审计 | 11项通过，非guest witness实现 |
| 新collector/helper/源差分/guest CPIO | **未生成；旧运行源码差分为空** |
| guest交叉编译、候选成本/完整等价性测试 | **未执行：布局停止；不可当通过** |
| VM/Start/浏览器/服务/QMP/guest命令/设备 | **均未执行** |

本轮不实现publication/bind/分阶段collector，所以正式规格要求的全部候选负例、并发完整性、摘要边界、有界成本和成员绑定准入仍未完成。失败路径保留具体证据，不弱化错误、不改判断、不扩范围去改GPE或DMM。

输入在各细化分析前pin；结束 **168项中167项SHA/大小匹配**。唯一变化为项目根 `README.md`：148033B / `ba8e847d1aee012145dae1f39bb2dd0933b52c0879dc7a10903e6bba70b28360` → 148889B / `ceb8e504ce5e305ae74ed8b5c4a3f528c8049508766dd8abd2fae2ba59cb44a4`。原始非零复核结果未改写。协调员在 `msg_8d4c13ba6a19` 确认是其新增“FX6 主线当前状态”段，且在内存移除该段能精确还原原hash；本任务未写此文件。r32所pin123项、r32交付20项、r30源码freeze41项全部一致；QEMU/kernel/DTB/原CPIO及所分析的技术输入均未变。说明和原始复核保留在 `COORDINATOR-NOTES.json`、`INPUTS-AFTER.json` 和 `INPUT-VERIFY-TOOL-RECEIPT.json`。

复现（仅本目录host输出）：

```sh
python3 -B audit_layout.py
python3 -B reproduce_layout_counterexample.py
python3 -B analyze_existing_writers.py
python3 -B verify_inputs.py  # 保留README差异时按设计非零，不能当全匹配
```

上述脚本只读旧输入，不导入runner或执行guest ELF。host compiler/audit进程均已退出；未创建fixture服务、端口或浏览器，无此类资源需要回收。`EXECUTION-SCOPE.json` 记录本次执行范围，`SHA256SUMS` 覆盖所有交付文件（清单本身除外）。

下一步仅为 [NEXT-DATA.md](NEXT-DATA.md) 的精确离线证明：沿实际libObj native resource open到DMM/kernel reservation及alias/import路径，补齐UI reserve不可成为此类可写parent的证据；证明失败则请协调端另定隔离合同。证明闭合前不生成运行候选、不安排VM。本报告不重复建议延长180秒/20秒，也不建议放宽原PAGE/server或视觉确认。
