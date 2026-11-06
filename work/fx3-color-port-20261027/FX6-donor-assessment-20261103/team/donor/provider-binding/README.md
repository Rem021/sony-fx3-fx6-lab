# FX6 ORIL provider 绑定边界与 FX3 电影 look 控制接口

2026-11-03。**本阶段闭合了一个可复用的条件控制路径，但没有找出 ORIL provider 表的实际填表者或回调实现。** 固定 FX6/FX3 原字节表明二者的事件获取、事件释放、四字节状态读取、look22 选择与 70 项源描述符具有相同的字段语义；隔离 CPU 回放证实模拟状态字 `0x30` 将人工事件 `{type=0, look=22, ip=0}` 送到各自的 70 项构造入口。这个输入是明确的 fixture，**并非 FX6 自然 MAIN/monitor 选择或实际 DMA/像素结果**。

## 固定输入与地址规则

| 原件或旧回执 | SHA256 | 地址规则及作用 |
|---|---|---|
| FX6 `fat-files/nflasha3/av-cam.bin` | `56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf` | ORIL AArch64，VA=`0xffffffc001000000`+文件偏移 |
| FX3 7.02 `work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin` | `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf` | 独立验证同一映射，不能借 FX6 偏移 |
| FX6 AP `nflasha15-files/bin/im.elf` | `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec` | AArch64 ET_EXEC；文中所引 `.text/.rodata` VA=文件偏移+`0x400000` |
| FX6 `nflasha3/vmlinux.bin` | `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9` | ARM64 Linux boot Image；不能套 ELF VA 映射 |
| FX6 WBI2 `tree/0700_part_image/dev/nflasha5` | `d33f0bd9c305cd9217815cd1e1a4fd86ea48b28ddbbbe6c581c8665dc5fde2d1` | 1197 节原始内存容器；不把其文件偏移当 AV VA |
| 旧 FX6 初始化 CPU 回执 `init-routing/init-trace.json` | `7bad0475d6d02adffc51e508f5189e398639d30eae72d82a210a3ccf1a09a9fd` | 仅用其原 `memcpy` 源→目标对应关系，不在本轮重放初始化 |
| 旧 FX3 初始化 CPU 回执 `initializer-guest-results.json` | `29c76396ae58e8caca2bd96e0eb0408854c163e60556b5d27b4da9d6bd76ab95` | 同上 |
| 旧 FX6 caller 静态/CPU 回执 | `9db38bfaa4f21b34d1501818001118cf71560287d53dd1d94e6a76c1e35c4c0a` / `ea43f9e1ba8f7825312e583dbf3b826fc84e9ffd8e718b9311f523ed154d8cda` | 固定旧结论，非本轮重跑 |

另四个 AP `.ko` 的 SHA、AArch64 ET_REL 类型和符号边界在 `binding-evidence.json`。所有记录均按原字节偏移和实际文件重新哈希；`run-receipt.json` 核对 13 个固定输入。此前的固定供体包和旧回执均未修改。

## 跨镜像装载、重定位与注册边界

1. 两版 AV 文件 `+0x0` 的首指针均为 `BASE+0x58`、`+0x8` 为 `ORIL`。文件 `+0x20` 的 qword 均为 `BASE+0x1a4`，而 `+0x1a4` 的首 qword 是零，紧邻 `+0x1ac` 已进入非零镜像元数据。原文件不含可直接使用的完整 `0x4c8` 字节 provider 回调表；需要装载后的实际绑定地址。此处只证明**文件快照**，不称装载时一定如何写入。
2. FX6 AP `im.elf` 的字符串 `fn=/system/av-cam.bin load=1 debug=1` 在文件 `0x7df6` / ELF VA `0x407df6`，`/usr/lib/libObj.so` 在 `0x7e2e` / `0x407e2e`。原 `0x406178–0x4061d8` 将前者传入装载命令构造；原 `0x406040–0x406134` 经过 `open`、`mmap`、`syscall(0x69)`、`munmap`，其 PLT/`.rela.plt` 符号分别为 `open` `0x402050`、`mmap` `0x402200`、`syscall` `0x402180`、`munmap` `0x402260`。`0x405f5c` 另有运行时 `dlopen` 到 `libObj.so` 的路径，但未建立它与 ORIL 表写入的调用边。上游 Linux [asm-generic/unistd.h](https://github.com/torvalds/linux/blob/master/include/uapi/asm-generic/unistd.h) 把系统调用 105 定义为 `init_module`；这只支持**标准 syscall 编号解释**，不能替代 Sony 内核实现或成功装载回执。
3. WBI2 内 `0x5804690` 有与 `im.elf` `.text` 开头 32 B 一致的拷贝；这支持 AP 代码曾进入该容器，**不是** provider 绑定回执。已核对固定 kernel Image 与 `grm_ma.ko`、`osal_uipc.ko`、`stream.ko`、`stream2.ko` 的类型、`init_module` 符号和相关字面量；这些模块的 `init_module` 是通用模块入口，未找到能由重定位/导出直接连到 AV `+0x20` 或回调槽的边。内核是非 ELF boot Image，当前文件不提供可直接按 ELF 解析的导出/重定位表。`ORIL` 字面量缺失只是有限检索结果，不能排除动态、私有装载器或压缩符号路径。

因此目前**真实 provider 表填入者、`+0x3c0/+0x3e8/+0x4c0` 的实现地址和注册时机均未定位**。`im.elf` 装载边是有原指令支持的候选上游，不是已证实的填表者。`binding-evidence.json` 保存逐指令机器码、VA、文件偏移和片段 SHA。

## 字段级契约：FX6 与 FX3

| 字段/动作 | FX6 原 AV 文件偏移 | FX3 原 AV 文件偏移 | 原码能证明的输入输出 |
|---|---:|---:|---|
| ORIL `+0x20` provider 表指针 | `0x20` | `0x20` | 两版 import thunk 均先 `LDR x8,[BASE+0x20]`；文件 qword 指 `BASE+0x1a4`，运行态值未知 |
| 表 `+0x3c0` 事件获取 | thunk `0x2ede0`，调用 `0x2a72d0` | thunk `0x2efd8`，调用 `0x2c40ec` | `w0=0x2ae085a`、`x1=sp+8`、`w2=-1`；返回零时读出指针并进入分派。事件生产者和对象所有权未知 |
| 表 `+0x3e8` 事件释放/后续调用 | thunk `0x2ee44`，调用 `0x2a732c` | thunk `0x2f03c`，调用 `0x2c4148` | 原码传同一请求号及 `x1=[sp+8]`；从调用时序推为消费后的操作，**具体回调语义未证实** |
| 表 `+0x4c0` 四字节 word 获取 | thunk `0x2efd4`，调用 `0x29b2a4` | thunk `0x2f1cc`，调用 `0x2b80cc` | `w0=0x2ae0000`、`x1=sp+0xc`、`w2=4`；返回值 `>0` 时取输出 word，否则只清覆盖标志。真实生产者和含义未知 |
| word 驱动的状态 | flag `0xb45884`、mode `0xbb0bfc` | flag `0xba81ec`、mode `0xc148b8` | 低四位==1 置 flag；高半字节 0/1/2/其他映射 mode 0/0/2/3。原文件快照均 flag0、mode2，不等于相机运行态 |
| 事件 type0 选择 | `0x2a7374`→`0x2a7458` | `0x2c4190`→`0x2c4274` | 事件 `+0` 为分支号；flag1 强制 look31，否则 `+4` 为 look；`+8` 传入构造器 ip。`+0x10` 在后续链交给回调，尚未绑定 |
| look22 查表至构造器 | 查表 `0x2a650c`，BL `0x2a74e4` | 查表 `0x2c3334`，BL `0x2c4300` | 都构造 `{ip=0,count=70,本地 descriptor VA}`，**只在下述人工输入中可回放** |

上述所有偏移均可用各自 VA 基址相加获得绝对 VA；机器码见 `binding-evidence.json`。旧初始化回执把两个原文件中**未初始化的目标区**分别映射回 70 个原 `memcpy` 源描述符；本轮从固定原 AV 的源字节重算名称、寄存器偏移、长度及 payload SHA，70/70 逐项相同，归一化摘要 `8147502e4d8131c2a90678bd735ad55e1c82cd2a2d3dcfd85756ce4d0dd61c74`。FX6 目标 `0xaa2ca0` 与 FX3 目标 `0xb05638` 均是各自镜像内地址，不能互换；VENICE 或其它 look、上游像素预处理并未由这 70 项相等推出相同。

## 本轮原码 CPU 回放与适配原型

`replay.py` 分别映射固定 FX6/FX3 AV 原字节，只对**客体 RAM** 执行两处补丁：头 `+0x20` 指向人工表 `0x62000000`，人工表 `+0x4c0` 指向带 `RET` 的 `0x61000000` stub。stub 核对原码传来的请求号、输出地址和长度，按用例写 word 并返回状态；没有冒充实际 provider 实现。原 `mode-update`、import thunk、flag/mode getter、事件分派及 look 查表均运行原字节，执行到 builder `BL` 前停住；失败模式在日志调用前停住。每阶段最多 1200 条，监控原码写集、事件原样、栈哨兵、mode-update 的 x19–x28 保存情况与返回 PC；六例均通过。

| 模型与人工 provider 输入 | 原码产生 mode/flag | 停止偏移 | 构造器入口前参数 |
|---|---|---:|---|
| FX6，成功、word `0x30` | 3/0 | `0x2a74e4` | ip0，70 项，`0xffffffc001aa2ca0` |
| FX3，成功、word `0x30` | 3/0 | `0x2c4300` | ip0，70 项，`0xffffffc001b05638` |
| FX6，成功、word `0x31` | 3/1 | `0x2a74e4` | 强制 look31，84 项，`0xffffffc001a822b8` |
| FX3，成功、word `0x31` | 3/1 | `0x2c4300` | 强制 look31，84 项，`0xffffffc001ae4c50` |
| 两版，provider 返回零 | 2/0 | 各自日志入口 | 未抵达 builder；原码未将测试 word 当成功结果 |

`provider-replay.json` 含每例 PC、写集、stub 参数、停止点和限制。`adapter.py` 是**纯主机声明式原型**：只接收独立观测到的 provider 成功/word `0x30` 与 type0/look22/ip0，验证两版 70 项源 payload 完全相同后，输出 FX3 本地事件字段和本地描述符地址。它拒绝 word `0x31`、ip1、其它 look、失败状态、其它 type 共五个负例；不注入代码、不绑定事件 `+0x10` 回调、不提交 DMA。`adapter-receipt.json` 保存正负例。

## 可复用工程边界与下一最小动作

可复用的是**同条件下的字段级控制桥**：保留 FX3 自己的 ORIL ABI、原事件消费者和描述符/构造器地址，把已验证等价的 FX6 look22 控制输入在 FX3 侧表述为 type0/look22/ip0。此处有具体原码及数据一致性支持，可作为后续 FX3 后端接入的窄接口原型。仍需适配的是 FX3 运行态 provider 绑定、事件对象生命周期和 `+0x10` 回调、真实 look/IP 选择、后续 DMA/CP/像素链；**不能把本原型当可安装代码或电影色彩已搬移**。

首个确切阻断点是装载后 `AV+0x20` 实际表指针及其 `+0x3c0/+0x3e8/+0x4c0` 函数指针。下一最小离线工程动作：从固定 `vmlinux.bin` 与装载器的实际模块加载/ORIL 重定位规则提取填表写入边，或取得一份受控运行态只读快照，**仅记录**装载后头 `+0x20` 的 qword、三槽函数指针、一次事件获取的状态/对象 `+0/+4/+8/+0x10` 及 word 请求的返回值/四字节输出，并与对应模块的映射及 SHA 绑定。未有此观测前，不为 IP=0 或 word `0x30` 命名 MAIN/monitor，不扩散 RAW/ISP 逆向。

## 复现

在本目录运行：

```sh
sh prepare.sh
PYTHONPATH=.vendor python3 analyze.py
PYTHONPATH=.vendor python3 replay.py
PYTHONPATH=.vendor python3 adapter.py
python3 verify.py
```

`prepare.sh` 仅在本目录安装固定版本 Capstone 5.0.6、pyelftools 0.32、Unicorn 2.1.4；原固件始终从既有只读路径读取，脚本只写此目录的 JSON 回执。`run-receipt.json` 为本轮实际 `PASS`，属于静态原字节与隔离 CPU 证据，不是 VM、CP、DMA、相机或视觉验收。
