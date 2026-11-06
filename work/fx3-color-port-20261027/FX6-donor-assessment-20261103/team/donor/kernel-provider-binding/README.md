# FX6 6.01 原内核符号与 ORIL provider 真正绑定链

2026-11-03。**已从固定 FX6 原 Image 恢复 41,294 个 kallsyms，并把 AV 头 `+0x20` 所指 provider 表的三处目标槽追到真实模块实现：`+0x3c0` 是 LIRO 的接收包装函数，`+0x3e8` 是 `osal_uipc.ko:osal_free_msg`，`+0x4c0` 是 `backup.ko:Backup_nread`。** 这是原指令、ELF 重定位、定义和导出的**静态绑定链**；本轮未启动内核/模块，也未观测自然事件或 `0x2ae0000` 的实际四字节值。旧 `provider-binding` 阶段的“AV 内无法单独判定”边界由本阶段跨镜像证据推进，不能再说整个固件中这三槽实现未知。

## 原件与证据等级

| 只读原件 | SHA256 | 本轮用途 |
|---|---|---|
| FX6 `fat-files/nflasha3/vmlinux.bin` | `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9` | 6,610,952 B ARM64 boot Image；恢复 kallsyms 与模块加载调用边 |
| FX6 `fat-files/nflasha3/av-cam.bin` | `56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf` | ORIL 头和待填表区；AV VA=`0xffffffc001000000`+文件偏移 |
| FX6 `nflasha15-files/bin/im.elf` | `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec` | AP 侧 `init_module` 参数构造/系统调用 |
| FX6 `nflasha15-files/kmod/liro.ko` | `8a7cfcaef07ad18ca2a97847d44d31bb9152f57c0fcbccd96056ad683649f2e1` | ORIL 加载、校验、provider 表复制和本地包装函数 |
| FX6 `nflasha15-files/kmod/osal_uipc.ko` | `07bafe9c7cf0cba42de4e7c8f62229d298881552b144e0ee43ff3b404ca379ee` | 事件接收/释放实现与导出 |
| FX6 `nflasha15-files/kmod/backup.ko` | `0fe57e43eb9b868f7011c4ea02ad002f0860d9d10fc2a644c772a074fc7532e6` | 状态 word 读取实现与导出 |
| FX3 `liro.ko`、`osal_uipc.ko`、`backup.ko` | 分别为 `b4bd80cc614751e0092ee19e89cb90632db580bc01f23f1a1df23544e9b10186`、`6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38`、`8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d` | 只读字段级对照，不能代替 FX6 地址或运行态值 |

`binding-evidence.json` 逐点保存原指令字节/偏移、文件 SHA、ELF section 与 `R_AARCH64_ABS64`/`CALL26` 重定位、导出条目。`.ko` 为 ET_REL，**section offset 不等于运行时 VA**；只有内核与 AV 映射在原件中可独立恢复。原件未复制、修改或重新下载；本目录索引与回执小于固件原件规模。

## FX6 自身符号恢复与双重校验

旧 FX3 stage146 的 16 B 代码签名只用于在 **FX6 自身** 寻找同形的 `kallsyms_expand_symbol` 指令序列；FX6 唯一命中是 Image 文件 `0x95c70`，不是借用 FX3 的 `0x95bf8`。六个 LDR64 literal 操作数均从 FX6 原指令取得：名称表 `0x4aad00`、token 索引 `0x522900`、token 表 `0x522500`、计数 `0x4aac00`、相对地址 `0x482500`、relative base `0x4aab00`。其中 token-index 的独立结构签名只在 FX6 文件 `0x522900` 出现一次，和其 literal 指针相减推出 FX6 基址 `0xffffff8008080000`；relative-base 表内容又等于该基址。计数为 **41,294**，压缩名称解码、排序和范围全部通过。

随后原 `__ksymtab` 普通 3,633 项和 GPL 2,456 项共 **6,089 对**名称/地址，逐项与解码目录一致；其它三个命名组为空。隔离 Unicorn 中按固定原 `kallsyms_expand_symbol.constprop.1` 入口执行 **1,007 例**，核对名称、返回的下一压缩偏移、128 B 输出边界与前后哨兵、SP、x19–x29；均通过。完整目录为 `fx6-kernel-symbol-catalog.json`，表定位/选中符号在 `symbol-recovery.json`，导出与 CPU 回执在 `export-crosscheck.json` 和 `symbol-verification.json`。这属于静态原字节与单叶函数 CPU 证据，**不是内核启动**。

## AP → 原内核 → LIRO → AV 的装载链

1. FX6 AP `im.elf` 文件 `0x7df6` / ELF VA `0x407df6` 有 `fn=/system/av-cam.bin load=1 debug=1`；`0x406134` 接收的 `x0` 是待加载**模块文件路径**，`x1` 为参数串，`0x4061b0–0x4061c0` 依标志位选择是否把 `fn` 字面量放进 `snprintf` 参数，`0x4061d4` 调用 `0x406040`。后者 `open`/`mmap` 的是该模块文件，并在 `0x4060e0` 设调用号 `0x69`，`0x4060e0–0x4060e4` 把映射模块字节与参数交给 `syscall`。Linux 4.9 [asm-generic/unistd.h](https://github.com/torvalds/linux/blob/v4.9/include/uapi/asm-generic/unistd.h) 定义 105 为 `init_module`；该上游只解释系统调用编号，**Sony 原行为以下述原 Image 为准**。这修正了旧阶段可能将 `fn=/system/av-cam.bin` 当作 `init_module` 的直接模块文件的歧义。
2. FX6 原内核 `SyS_init_module` 文件 `0x94bc8` / VA=`0xffffff8008080000+0x94bc8` 在 `0x94d64` 直接 BL 到 `load_module` `0x92ba0`。其 `0x92bd4–0x92c04` 对模块缓冲区核验 `\x7fELF`（FX6 内核比较常量文件 `0x524b88`）、AArch64 ET_REL 与 section header；平面 ORIL AV 不能直接走这条 ELF 模块入口。`load_module` 在 `0x93c2c/0x9445c` 调 `resolve_symbol.isra.32`，后者 `0x9210c` 调 `each_symbol_section`；`0x94524` 调 `apply_relocate_add`，`0x94a18` 调 `do_init_module`。调用 PC/目标 VA、原机器码和区段 SHA 见回执。上游 Linux 4.9 [module.c](https://github.com/torvalds/linux/blob/v4.9/kernel/module.c) 与 ARM64 [module.c](https://github.com/torvalds/linux/blob/v4.9/arch/arm64/kernel/module.c) 仅作方法对照，不代替这些 Sony 原码边。
3. FX6 `liro.ko` 的 `.modinfo` 原字节含 `parmtype=fn:string`、`load:int`、`debug:int`。它的 `.init.text+0x294/0x2cc/0x314/0x324` 经 ELF CALL26 重定位到 `filp_open`/`vfs_read`/`filp_close`/`flush_icache_range`；读取 `fn` 路径后，`.init.text+0x33c–0x368` 核验加载图像 `+8` 为 `ORIL`、`+0xc` 为版本 `5`。这是连接 AP 参数与 LIRO 装载代码的原字节/参数名证据，运行时选择到的具体模块项和加载成功尚无进程回执。
4. LIRO `.init.text+0x4b0`（文件 `0xa340`）把已加载 AV 基址放入 `x20`；`+0x4b4` 的 literal 重定位为 `.init.data+0`，`+0x4b8` 设长度 `0x698`，`+0x4bc/+0x4c0` 计算 `x0=*(AV+0x20)+0x48`，`+0x4c4` 的 CALL26 重定位为 **`memcpy`**，随后 `+0x4d4/+0x4e0` 调 AV `+0x10` 的入口。FX6 AV 文件头 `+0x20` 原值 `0xffffffc0010001a4`；目标 `[0x1ec,0x884)` 在原 AV 文件全零。LIRO 的原复制是**填表者和写入规则**；未有运行态内存回读，不能称这次 memcpy 已在相机执行。

## provider 三槽真实来源

LIRO 的 `.init.data` 恰为 `0x698` B；复制到 provider 表 `+0x48`。下表每个源 qword 原文件均为待重定位零，目标函数来自该 ELF 原 `R_AARCH64_ABS64` 记录，**不能把零 qword 或字符串命中当实现**。

| AV provider 槽 | LIRO `.init.data` 源偏移 / 文件偏移 | 固定重定位目标 | AV 文件目标偏移 / VA | 实现/导出来源 |
|---|---|---|---|---|
| `+0x3c0` 事件获取 | `0x378` / `0xc4a8` | LIRO `.text+0xc28` | `0x564` / `0xffffffc001000564` | LIRO `.text` 文件 `0xc90`；原 `+0xc44` 禁用 hook、`+0xc54` 调 `osal_rcv_msg_tmo`、`+0xc5c` 恢复 hook，回传结果 |
| `+0x3e8` 事件释放 | `0x3a0` / `0xc4d0` | `osal_free_msg` | `0x58c` / `0xffffffc00100058c` | FX6 `osal_uipc.ko` `.text+0x4650`，文件 `0x46b8`，原 `__ksymtab` 导出重定位 `0x10` |
| `+0x4c0` 四字节 word 读取 | `0x478` / `0xc5a8` | `Backup_nread` | `0x664` / `0xffffffc001000664` | FX6 `backup.ko` `.text+0x1ca8`，文件 `0x1d10`，原 `__ksymtab` 导出重定位 `0x80` |

`osal_rcv_msg_tmo` 的真实定义在 FX6 `osal_uipc.ko` `.text+0x4198` / 文件 `0x4200`，`__ksymtab` 导出重定位 `0xa0`。FX6 原 `Backup_nread` 先取读锁，传原请求号/目标/长度进入本模块 `.text+0x700`；后者的原 CALL26 重定位依次落到 `Data_SearchId`、`Data_GetSize`、`Data_GetDataPt`，按运行态 Backup 记录查找并返回长度/状态。于是旧 AV `+0x4c0` 调用的 `w0=0x2ae0000,x1=sp+0xc,w2=4` **确实进入 Backup 读路径**；`0x2ae0000` 的自然记录内容、返回值和四字节 word 仍需实际 Backup 数据/运行态绑定，不能用旧人工 `0x30` 冒充。

## FX3 对接边界与本轮 CPU 回放

固定 FX3/FX6 `liro.ko` 全文件 SHA 不同，但 ORIL 校验、`0x698` B provider 复制原指令、接收包装函数原字节、完整未重定位 `.init.data` 字节及上述三处重定位目标**逐项相同**。两版 `osal_rcv_msg_tmo`、`osal_free_msg` 原函数也逐字相同；两版 `Backup_nread` 的函数体 SHA **不同**（FX6 `e645c650...`，FX3 `6adf01d7...`），且 offset 分别为 `0x1ca8` 与 `0x1eb8`。因此 FX3 后端可复用 LIRO/OSAL provider **ABI 与事件契约**；Backup 数据实现和记录内容要按各机本地版本映射，不能把 FX6 运行时函数 VA 或人工 word 搬过去。更不能由 provider 绑定推出 RAW、ISP、DMA 或自然 MAIN 路由完成。

`replay_wrapper.py` 另把固定 FX6 LIRO `.text+0xc28..0xc74` 原指令放进隔离 CPU，**只对客体副本**三处原 CALL26 重定位为明确的 `liro_disable_hook`、`osal_rcv_msg_tmo`、`liro_enable_hook` 桩。外部接收桩分别返回声明的 `-7` 或 `0`，不写事件对象；原包装函数两例均将 `0x2ae085a`、输出指针、`-1` 超时原样交给接收边并回传状态，SP、x19–x29、哨兵与受限栈写集检查通过，每例低于 200 指令。`wrapper-replay.json` 包含原补丁字节、PC 与调用/写回执。这里执行的是**原 LIRO 包装函数**，并未执行原 OSAL 队列、LIRO 初始化 memcpy、Backup 读取、AV 消费者或实际相机。

## 最小后续工程动作

静态注册来源和实现已定位；**下一阻断点从“回调是谁”收窄为运行态数据**：给 `backup.ko` 的 `Data_SearchId(0x2ae0000)` 建立 FX6/FX3 各自的原记录/初始化来源，并对一次真实读取的状态及 4 B 输出做只读绑定；另需观测 `osal_rcv_msg_tmo(0x2ae085a,...)` 取到的事件对象 `+0/+4/+8/+0x10`，才能判定自然 look/IP 与 MAIN/monitor。最小离线阶段可先静态追 Backup ID 到两个固定模块的数据注册表并做有界原函数查找回放，**只在地址/ABI/输入均由原字节闭合时执行**；若记录由相机动态产生，就明确要求受控只读运行态快照。现阶段不可发布/刷写或把本地回放称真实色彩移植。

## 复现

在本目录：

```sh
sh prepare.sh
python3 recover_symbols.py
PYTHONPATH=.vendor python3 verify_symbols.py
PYTHONPATH=.vendor python3 analyze_binding.py
PYTHONPATH=.vendor python3 replay_wrapper.py
python3 verify.py
```

依赖仅固定版本 Capstone 5.0.6、Unicorn 2.1.4、pyelftools 0.32，临时安装在本目录 `.vendor`。`run-receipt.json` 是实际执行的 `PASS`：9 个原件 SHA、41,294 符号、6,089 独立导出对、1,007 次原内核单叶 CPU、2 次原 LIRO 包装函数 CPU；证据等级为**静态与隔离 CPU**，无 VM/设备/USB/SD/相机验收。
