# r33 布局与身份审计：未取得运行候选准入

结论：`[0x7000,0x7800)` 是 UI v15 已知常态直接 writer 的局部空隙，**不是已证明全 writer 安全的空闲区**。首次 status 为 `msg_20dc1b7d1aef`；发现动态 GPE writer 后已用 `msg_7d631368eb23` 报告停止生成运行候选。本目录没有新的 guest helper、CPIO、candidate.json 或部署入口。

## 实际成员与审计范围

N64 CPIO SHA `aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9`，453213884B；1140 个成员逐项匹配 r31 实际 `cpio-audit.json`。26 个 simulation ELF 的 mmap imports/exports、snapshot exports 与地址/文本发现筛查在 `CPIO-WRITER-SCREEN.json`，全成员在 `ACTUAL-MEMBERS.json`。这份筛查**不是**对计算地址、间接指针、原生驱动写入的完备排除证明。

`simulation/fx3-ui-gate-v1.so` SHA `6673b9be…258df` 实际装入 v15 N64；与原始 N64 build 的 `.text` 地址、长度、SHA 相同（`UI-COMPILED-BINDING.json`）。静态 `bind_ram`/`bind` 被编译器内联，因此保留两次 missing-symbol 警告，最终按实际导出 `dlopen` 反汇编，不以工具 exit=0 冒充找到符号。原 `dlopen+0x1d8` 附近 `0x14170–1418c` 构造 `0x41dc00000`、65536B、prot3、MAP_SHARED；`0x141a4–141b0` 实际 memset 为 p+0x10/0xfff0，接着覆盖前16B magic/version，之后 `0x141f4` 写 PID。候选空隙在真实机器指令清零覆盖内。

## UI64KiB 所有已识别 writer（偏移，右端不含）

| writer | 范围 | 来源/约束 |
|---|---|---|
| UI bind 初始化 | `[0000,10000)` | v15:160，整个旧内容被清零/新 header 取代；不只常态 bank |
| header / backup / reverse / boot/overflow/topology 计数 | `[0000,0070)` 中若干字段 | :35、98–107、123、160；有常态多线程字段，不是事务 header |
| N64 statistics bank0 / bank1 | `[0100,0410)` / `[1100,1410)` | :6、35，98Q=784B；普通 BSS 原子读取后发布，可能滞后 |
| host snapshot request | `[3000,3040)` | snapshot_tail_v15.py:151、153；唯一已识别 UI 区宿主写；原 ready/PID/root/tag/nonce 后按 commit 协议写入 |
| ready/ACK / payload 保留 | `[3040,3100)` / `[3100,3410)` | :19–23、40–64；协议定义 ACK192B、payload784B |
| boot records 0–63 | `[4000,7000)` | :123；64×192B，record commit 单独末写 |
| 待证区 | `[7000,7800)` | 2048B；常态 UI 局部 store 不进入；初始化和动态别名尚未排除 |
| change-mode 输入 | `[7800,7818)` | :100，24B |
| 四个 topology 槽保留 | `[8000,a800)` | :101–107；每槽0xa00，实际64+1200+1200=0x9a0B；最后实际写到a7a0 |
| pin header / 实际 payload | `[b000,b040)` / `[b040,bec8)` | :78、94；CAPID49 实际 ELF `fx3_pin_snapshot` :0x15c60/15c80 明确0xe88=3720B；capacity0x2fc0不是实际写长 |
| panel header / 实际 payload | `[c000,c040)` / `[c040,c0b8)` | :112；CAPID49 实际 ELF `fx3_panel_config_snapshot` 明确0x78=120B |
| UUD change 输入 | `[c800,c818)` | :83，24B；与实际 panel payload 不重叠 |
| boot records 64–127 | `[d000,10000)` | :123，64×192B |

以上已识别常态 UI/callback 范围彼此不把 `[7000,7800)` 当作 payload。pin/panel exporter 只复制固定结构、检查 capacity、CAPID process_owner 和 ready 状态，持有原 CAPID enter/leave 锁；它们通过 caller 提供的 UI 虚拟地址间接写，不独立 map UI。不得只搜索 `41dc` 常量就漏掉它们。

## 使全 writer 审计停止的具体路径

实际 GPE `simulation/fx3-gpe-observe-v7.so` SHA `30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4`，与 AP105 helper、`build/cross-build.json` output 一致，来源为 gpe-perf/fx3-gpe-observe-v26-perf.c、resource-v26.inc、cache-v26.inc。所用源片段与其 build/provenance hashes 相符。

- `resource-v26.inc:40–45` 从 live 原生对象读取 state10/identity/type/uhdl/logical/**phys/bytes**，检查非零、溢出及256MiB上限；没有 UI reserve 排除谓词。
- `:54–64` 在成功 native open 后注册此范围，代码自身的拒绝文案写明 `no_address_allowlist=1`；`observe_resource_open:66–70` 保持原调用一次及 rc/errno。
- `:108–118` 对所需像素范围复核 active、live fields/identity 与唯一 parent。原生打开的 type403/resource_class_vptr 在 adapter:212–214 不需 child 补充路径。
- `fx3-gpe-observe-v26-perf.c:229–245` 对 destination parent 物理全跨度以 prot=3 map，之后送 backend；`cache-v26.inc:13–21` 按 base 对齐映射页，不排除 `[0x41dc00000,0x41dc10000)`。编译 `map26_get:0x2a770–2a794` 也从实参生成 offset/size/prot 并调用 mmap，没有 UI 常量比较。

`reproduce_layout_counterexample.py` **原样提取** object_fields/resource_same/resource_add/observe_resource_open/resource_lookup/map26_get，使用合成的 successful native-open 对象、同 identity、type403、同 class_vptr、phys=UI_BASE、bytes=65536。实际本地谓词接受 gap 查询并请求 `mmap(UI_BASE,65536,prot=3)`；只含 `[7000,7800)` 的合成 parent 则会 map 4KiB 页。fixture 没有调用真实 native open、screen、mmap、pread 或任何 guest API，没有实际物理写。它不证明原固件能合法构造这样的对象、不证明整条真实 draw 路径已执行。

**缺口正是原生 DMM/resource::open 到上述字段的来源/排除证明**：cmdline memrsv 存在并不能替代“所有此类 native-open/alias/import 路径都不会把 observer reserve 当作可写 resource”的源码/反汇编证明。四轮既有窗口各4条注册，UI overlap全0；这是已记录前缀的事实，不是所有可能 writer/后续路径的完整排除证据。不能把本次准入失败回溯成 r31 零 ring 的根因。

## 初始化、跨模块和身份

`init` 的实际 LD_PRELOAD 在 bootin 命令包含 UI、OSD、CAPID、GPE、两个 mmap interposer。UI 的唯一 private `ram` 在 `dlopen(appFw.so)` 原调用返回后，由 bind 检查原60条指令、claim O_EXCL、cmdline、mmap 后设置；随后原自测和逐条装 probe，最后 st.bound/ready/N64 publication。claim 成功后失败也不删 claim，不能擅自恢复或重试。header magic/version/PID 已写不等于全部 hook 都成功安装。

UI 普通 BSS 的 ram/root/app_base/locks 没有现成跨模块导出 ABI；CAPID exporter 从 caller 获得目标地址。OSD reserve在0x41e000000，懒绑定且 ring为空时原 v25_diag早退，仍存在r32盲区。OSD 的 publication 可能先于 UI ready：不能先 map 空隙写 witness，再让 UI 的 memset 抹掉后断言“publication未发生”。当前没有已实现的、带 PID/module epoch/初始化状态的 BSS→单 UI owner 搬运协议，所以本目录**不声称早期 witness 可导出**。原 UI header PID 也不是 host launch UUID，不能跨进程/重载/重启合并；没有证据时必须 unknown。

UC 上不新增 exclusive RMW/atomic/锁；未来普通 RAM try-claim 与计数预算不能移植到 UC。原有独立 header、N64 bank、tail snapshot 均不能冒充全局事务。End 原暂停下的完整 UI64KiB 导出在原 runner:238–239/806–807；pre-input只读路径在 pre_input_observation:83；snapshot-tail只写3000–3040。这里仅审阅源码/历史回执，没有调用这些 transport、增加读回或暂停。

## 后续实施边界（全部未实施）

若排除证据闭合，优先普通 BSS 保存 earliest publication/bind 结果；只由完成初始化、身份匹配的 UI owner 用普通 aligned store+commit 导出≤2KiB。初始化失败、跨PID/模块epoch不明、首次bind早于record-ready或export丢失，报告 unknown。保留原rc/errno/调用次数和门表达式，不能靠更早强制bind解决记录问题。

原 app_pool 8192B、每island128B、已装60个，只剩4个槽。原id9/id10是STR前意向；完整新增entry/post-STR/alloc/send-entry/send-return/consumer-post/exit至少7点不能直接塞入。该容量事实不是另一个已证根因；可以先缩减到有证据的阶段下界并标缺口，但本轮布局门已失败，没有修改 probe 池、增加 mmap 或选择任何新 native ABI。CAPID send 的原尾调用和父栈身份保持原样。
