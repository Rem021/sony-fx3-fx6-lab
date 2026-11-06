# FX3 writer 时序与最小 FX6 侧 veneer 原型

**结论**：固定 FX3 MPR 在 `Init` 内已把 u16 传给 Xavcs writer：先用于一条 OSAL 诊断消息，再写两个 writer 的 `+0x24`。FX6 的 Mxf/Xavcs 选择则在后续 `EnterRec`，因此**没有原码证据支持“等模式选完再改 FX3 writer 私有字段”是安全接缝**。可测试的软件策略是：由于固定 FX3 此 Init 路径只构造 Xavcs，先把已证的 FX6 Xavcs 有效阈值 `780` 交给 FX3 Init，另外保存 FX6 原输入 `1440`；在真实电影模式首次使用前，若原 FX6 选择 Mxf 则明确停止，绝不把 780 当 Mxf 等价。这里实现了 host 可编译/链接的字段 veneer、57 个独立不返回诊断 thunk、单次原函数转发合同及针对性测试，**没有 guest 装载、原 Sony 函数执行或录制放行**。

## 固定来源与证据级别

`audit.py` 从原 ELF `PT_LOAD` 换算每个 VA/fileoff，逐条保存 little-endian 原字和 objdump，核 AP 两个 `JUMP_SLOT` 与 FX3 MPR 导出；[evidence.json](evidence.json) 含全部 53 个原指令点。`gen_inputs.py` 以固定历史回执生成 656B `genuine-input.bin` 和 57/18 项 `callback_map.hpp`，并不执行原库。来源：FX3 `libmpr.so` SHA `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c`；FX6 `libmpr.so` `814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e`；FX6 `appFw.so` `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`；既有字段索引 `aef19dda30c2120538ad4ed66b536b25f01eb94c8326239658b0f5953ff660a5`；历史 `mpr-observation.json` `fa8e834e999aafb573118ee34de89b1d7b38111fc13ef1c7122ddef774ef31e2`；原参数 `585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1`。历史观测到原 FX6 AP `mpr::Init` 返回 3，未观测到后续 writer 分支；本报告后半是静态原码和 host fixture。

### 原 u16 存储 → 首次已定位消费

| 时点 | 固定 FX3 原码（VA=fileoff；原字见 evidence） | 可证明的作用 |
|---|---|---|
| Init 传参 | `b7080:7943e663` 从输入 `+0x1f2` 取 u16，`b7094:97ff229b` 调 `IntegRecordMovieInit` | 原 FX6 AP 源 `212f498:5280b400` 写 1440 到 `+0x28a`，原样按 FX3 布局误传并非保行为。|
| 保存并两次初始化 | `d603c:53003c79` `uxth w25,w3`；`d60a8/d60c8` 各 new `0x2c58`，`d60e4:790143b9` / `d6110:790193b9` 向两个参数记录写 w25，`d60f8/d6120` 两次直调 `0x11975c` | **发生在 Init 内**，且早于后续 FX6 原 `EnterRec` 模式选择。`d6278/d6284` 后续建执行队列，不能假设 Init 完成前没有异步观察。|
| Init 内首次读与诊断 | `119798:79403020` 读参数 `+0x18`，`1197a8:b900a7a0` 放局部消息，`1197c4:97fff09a` 调 `0x115a2c`；该函数 `115a70` 调 `osal_valloc_msg_wait` | u16 **在 Init 阶段已经被读并送诊断路径**。本报告只把它称为诊断副作用，不推测消息最终呈现或硬件效果。|
| Init 内有效成员写 | `1197c8:79403280` 再读参数 `+0x18`，`1197cc:79004a60` 写 writer `+0x24` | 已有原码直接写入，未找到有证的公开“模式选择后改此成员”API。不能仅为换阈值在录制中无锁写该私有成员。|
| 首个已定位时间比较 | `11d178:aa0003f9` 证明 x25=this；`11faac/b4/bc` 分别检已通知、stream、正帧率，`11fac8:79404b22` 读 writer `+0x24`，再算 `60*u16-60` 并与帧数/帧率比 | 此点在 `XavcsMovieWriter::CreateFreeBoxHeaderInStreamBuffer` 的原码内。它是已闭合的阈值消费者，**不是全程序无其它别名读取的证明**；其自然调用时序及首使用前模式门仍需运行态证实。|
| FX6 实际模式分流 | FX6 `157960:b9427ec0` 读 manager `+0x27c`，`157964:7100201f` 比 8，`157968:54fff501` 非 8 跳 Xavcs；等于 8 于 `15796c/157978` 建 Mxf，否则 `157808/157814` 建 Xavcs | 上游来自 `GetMovieRecParam`→`SetEnterRecInfo`，原 FX6 Xavcs `1b0f44/48` 强写 780，Mxf `194124/28` 保留输入 1440；真实模式值未被本次 VM 快照读取。|

不能把“post-choice、pre-consume 写 +0x24”作为现成方案：即使阈值比较在录制时才发生，FX3 初始诊断和成员写已经发生，`Init` 后还建立队列；晚改可能与线程并发、对象更换及早期使用冲突。更可控的候选是 **provisional Xavcs**：在 FX3 Init 入口用 780，同时保存源 1440；未获真实分支证据时不得放行录制，遇 Mxf 原分支显式拒绝。它只保 Xavcs 的这一个已证时间阈值，不证明整条录制行为相同。固定 FX3 `EnterRec` 的 `d7e98` 调 `SetEnterRecInfo`、`d7e28` 有 `EnqueueExecEncOpen`，两者与阈值读取的自然先后尚未在这套混合系统实测。

## 可编译原型与装载合同

源码 [veneer.hpp](veneer.hpp)、[veneer.cpp](veneer.cpp) 的 `prepare` 从原 656B 复制 count、四槽、skip/method/node、源空位与尾域到 504B；源 u16 必须是历史实际 `1440`，目标暂填 `780`；保存所有 57 个共有 FX6 原回调地址和 18 个专有地址。实测 46 个共有非空源槽只装不同的诊断 thunk 地址，11 个原空槽保持空；10 个非空专有回调强制要求 AP API 边界停止。缺 thunk、源指针直通、重复/哨兵槽、错误 count/u16/长度都拒绝，失败重试清空旧 plan。

`install_before_init` 先发布包含原回调/新 thunk 的 Registry；`call_original_once` 在所有身份和停止门均确认、Registry 已装、原函数指针非空时，**恰调用提供的原函数一次并原样传播返回码**，重入拒绝。host 测试用显式 `original_probe` 返回非零 3 证明单次调用和返回传播；`guard_writer_branch` 对该返回明确报 `OriginalInitFailed`，不会把模式判定误作成功。它不模拟 Sony 初始化成功。`RuntimeGates` 目前是需要外部独立证明的合同布尔量，**不是**运行态身份验证器。全部未知 thunk 是独立函数，进入后不读事件 payload，打印 `FX6_BRIDGE_UNSUPPORTED_CALLBACK_SLOT=N` 并 `_Exit(86)`；host 负例验证不返回。它们是 host 诊断实现，不能直接当 AArch64 guest thunk：将来须以入口第一指令可识别 trap/host 停止捕获寄存器及线程，证明 trap 未被 guest 吞掉或继续启动。不能将这个 `_Exit` 当 guest 已实现。

`translate_poweron_12` 只作 host 字节变换：要求原 12B、事件 `0x1026`、结果原值 0、显式 live waiter/唯一 key/FX3 dispatcher 所有权证明，然后复制 echo 并改副本事件为 FX6 `0x102d`；不调用 FX6 回调、不释放原块、不声称已通知。对未知回调、电影录制、播放计时或 FX6 专有 API 不能返回成功。`classify_writer_branch` 用符号化 host 分支案例检验 Xavcs/Mxf 政策；`guard_writer_branch` 还要求原 Init 实际返回 0、真实原分支已核实且阈值首消费尚未发生。两者都不产生录制许可。

真实 guest 装载至少要闭合这些点：

1. 原 FX6 AP `0x212f7b8` `BL` 到 MPR Init PLT，`R_AARCH64_JUMP_SLOT` GOT `0x2ef1368`；`0x214314c` `BL` 到 EnterRec PLT，GOT `0x2ef2670`；固定 FX3 MPR 原件同时导出两函数。须在独立候选中证明实际 loader/global scope 将这**两个特定调用**解析到 veneer，而 veneer 对原 FX3 Init 用另一个经身份验证的指针恰转发一次；仅有相同名字 `.so` 或 host 编译成功不足以证明此点，也不能改原 init/17 helpers 或全局关闭守卫。
2. 进入 veneer 时核 AP ELF/PHDR/load bias/调用点和参数来源；核固定 FX3 MPR ELF，按原目标 ABI 验一次函数指针/返回。基础寄存器规则见 [Arm AAPCS64](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst)，但它不证明 Sony C++ 回调签名或对象生命周期。所有回调 thunk 注册先于原 Init，至少保持至异步线程/PowerOn 等待者完全退出。
3. 同轮验证 FX6 模式真实来源；若源分支等于 8 的 Mxf 路径，进入任何 FX3 writer 使用前停，不把 1440 退化成 780；若非 8 的 Xavcs，仍须确认目标 FX3 当前 writer 对象是先前构建的 Xavcs，并观测 `0x11fac8` 未在分支门前执行。未支持事件必须在原 callback 解引用前停，host 结束诊断并保留现场，不吞事件或返回 0。

首次后续只读观测最少是：AP `0x212f7b8` 的真实重定位/返回、源与目标回调表登记顺序；AP `0x214314c` 前后的 movie mode 来源与固定 FX3 `SetEnterRecInfo` 返回、`EnqueueExecEncOpen` 入口；固定 FX3 writer `0x1197cc` 两个对象实际写值及 `0x11fac8` 首次命中顺序。若阈值先于模式门被消费、对象身份不同、原函数返回非零或任何未知 thunk 被触发，单轮停止而非绕过。需要 runtime owner 排队的只读断点/日志窗口；本轮无 VM。

## 电影回调尺寸勘误（历史文件不改）

旧 `init-field-adapter/README.md` 把“FX6 producer 分配尺寸 `0x788/0x780`”写成电影 callback 的“读取到 `0x788/0x780`”，混淆了两个边界。固定 FX6 MPR producer 原字 `1450f8` / `1455c0` 分别设置 `0x788`（1928B）/`0x780`（1920B），并经 `14516c→145178` / `145630→14563c` 将尺寸传 `SetIssueEvent`；**FX6 AP 的最高无条件读取末端**分别为 `+0x780`（`213caec` 读取 `+0x778..+0x77f`）和 `+0x778`（`212da54` 读取 `+0x770..+0x777`）。另有无条件 byte 读 `+0x770`/`+0x76c`，均超出 FX3 producer 的 32B 原载荷；这依旧否定原指针直通，但不能把 producer 尺寸当成 AP 最高读取末端。既有 [callback-adapter-review](../callback-adapter-review/README.md) 的原字链保留。

## 复现与限制

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/writer-veneer-prototype
python3 build_and_test.py
```

脚本只在本目录生成小型 header、656B 原参数副本、`evidence.json`、host 可执行测试与 `receipt.json`。编译参数 `clang++ -std=c++17 -O2 -Wall -Wextra -Werror`；不执行未知 ELF、不启动 QEMU、不改固定 FX3 环境/旧候选/历史回执。host positive、错误长度/count/槽/u16/回调直通/漏装/重复调用/Mxf 分支、PowerOn 负例和未知 thunk 退出码 86 均由 `receipt.json` 记录。没有 ABI、异步事件、真实硬件或 FX6 系统启动验收。
