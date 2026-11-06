# FX5 与 FX3 的 DMA 地址转换和缓存协议核对

2026-10-30。**两代公开源码的 UDIF 缓存参数定义相同，但 DMA 地址域及底层缓存入口不能按函数名直接替换。** 本轮把 FX3 原始默认 AP／CP 地址与这些源码逐项连接，明确了移植缓冲层必须保留的地址、缓存属性和数据所有权约束。仍未取得完整 FX5 私有供体，也未绑定经典 FX3 7.02 的实际运行内核；尚无可正常刷入的整套菜单／VENICE 色彩链修改包。

## 来源与适用范围

沿用已下载、已校验的官方归档，没有重复下载或运行厂商源码：

| 来源 | 内核参考 | 归档 SHA256 |
|---|---|---|
| [Sony FX5 OSS](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html) | 5.15.179 | `1e1cf32816e841462bd1d0f4e93c4897a44d0a9b95641387c74cafb6d6f44190` |
| [Sony FX3 Ver7.00 OSS](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html) | 4.9.337 | `bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f` |

FX3 参考源码不是 7.02 实机指纹。FX5 的多份设备树、ASIC／QEMU／FVP 分支也不证明量产机当前选中了哪份配置。旧记录已做 CPU／内核版本比较，本轮新增的是地址转换、页表属性和缓存消费函数的成对核对。

已捕获并校验 44 份源码，以及 4 个既有内存样例；42 个源码字面位置保存于 [memory-contract-evidence.json](memory-contract-evidence.json)。FX3 源码初次按 `mach-cxd90057` 查找未命中，归档目录显示实际为 `drivers/udif/mach-cxd900xx`；初始空结果和后续取得的 8 份文件均保留，没有据空结果声称缺少实现。

## DMA 地址不能共用

两份 `dma32.h` 的实际区间与转换规则不同：

| 操作 | FX3 公开实现 | FX5 公开实现 |
|---|---|---|
| 64→32 的 DDR 窗口 | `[0x400000000, 0x4FE000000)` | `[0x200000000, 0x300000000)` |
| 64→32 的 ESRAM 窗口 | `[0xFE000000, 0xFF000000)`，保留数值 | 无对应独立分支 |
| 32→64 的 DDR | 有界检查后加 `0x400000000` 地址域 | 与 `0x200000000` 按位或 |
| `0xFE001000` 的 32→64 结果 | `0xFE001000`，ESRAM | `0x2FE001000`，DDR |

经典 FX3 默认 DmmCfg 的 AP 投影地址 `0x4132D8E00`，经 FX3 公开公式得到 `0x132D8E00`；送入 FX5 64→32 公式则得到错误值 `0xFFFFFFFF`。如果不检查就截低32位，再按 FX5 规则还原，会变为 `0x2132D8E00`，已改变物理地址含义。

对[既有原默认地址记录](../AP-staging-record-routing-20261030/default-span-roundtrip.json)的 20 个范围进行区间算术核对：9 个 AP 文件槽及主暂存区均在 FX3 公开 DMA32 DDR 窗口内；对应 CP 地址及整体 CP 目标不属于这个 **AP 转换器** 的窗口。20 个范围都不落入 FX5 该 DMA32 窗口。CP 地址属于另一地址域，不能把它在 AP 转换器中被拒绝解释为 CP 地址本身无效。

这里执行的是公开公式的整数运算，没有执行原驱动或探测物理内存。这些 FX3 数据是原包默认配置及 A7 IV AP 参考中的角色连接，不代替本机当前 Backup／AP 启动状态。

## 缓存接口中可复用与必须适配的部分

两代 `include/linux/udif/cache.h` 逐字节相同，类型参考都使用 `size_t` 和指针；标志为 FLUSH=1、INVALIDATE=2、NONE=3。这个源码接口可作为适配起点，不能据此确认私有模块二进制 ABI 相同。

| 路径 | FX3 参考源码 | FX5 参考源码 |
|---|---|---|
| UDIF FLUSH | `__dma_map_area` → clean，传入起点和长度 | `dcache_clean_poc`，传入起点和终点 |
| UDIF INVALIDATE | `__dma_map_area` → invalidate，传入起点和长度 | `dcache_inval_poc`，传入起点和终点 |
| scatter-gather map | FROM_DEVICE 分支先 invalidate | `__dma_map_area` 统一先 clean |
| scatter-gather unmap | 非 TO_DEVICE 时 invalidate | 非 TO_DEVICE 时 invalidate |

两代的直接 SG map 时序不同，不据此认定实现有缺陷。移植时须保留设备／CPU 对缓冲区的交接顺序，不能只见相同名字就替换底层符号。所查 UDIF wrapper 只拒绝空地址或零长度；NONE 并未在此短路，仍会走非 INVALIDATE 的 clean 分支，不能按名称假设为无操作。

FX5 `arch_phys_to_cache/noncache` 经 `p2v`／`v2p` 核验反向地址及 PAR_EL1 属性；该路径包含 `AT S1E1R`。`arch_phys_to_va` 只走算术 `__p2v`，不能把两个入口的保证混同。`arch_phys_to_cachetype2` 只查首尾字节的属性，不证明中间每页同属性。`mmap.c` 的 debug 默认为0并直接允许，debug=1也只警告，不能把它当作常开的完整缓存属性检查。

## 设备树范围与实际缓冲区仍须区分

FX5 四个样例的主 memory 范围分别为：

| 样例名 | 起点 | 终点，不含 |
|---|---|---|
| 3G | `0x200000000` | `0x2C0000000` |
| 4G | `0x200000000` | `0x300000000` |
| 6G | `0x200000000` | `0x380000000` |
| 8G | `0x200000000` | `0x3FE000000` |

`cxd90xxx.dtsi` 还描述 `0x640000000` 起的512MiB memory／reserved-memory。新取得的消费者代码把 `arm,rmem` 的 memtype 送到 `rmem_arm_add`，分页时使用对应属性；`iomap` 节点则由 `map_io` 读取 physaddr、virt、size 和 memtype。它们解释了静态描述怎样参与映射，尚不证明该512MiB是RAW池、实装芯片容量或实际录像分配结果。

`early_init_dt_scan_memory` 优先读取运行时 FDT 的 `linux,usable-memory`，否则读取 `reg`；启动入口接收的实际 FDT 仍是决定量产映射的输入。公开平台范围、DMA32可寻址范围、Linux可分配范围和DMM槽位大小不能互相替代。

## 对完整目标的下一步要求

缓冲层适配应使用 FX3 目标自身的地址域和缓存 API，并将 AP／CP、物理地址／DMA地址、起点长度／起点终点明确对应。下一处必须补上的证据是：这些公开接口怎样绑定到经典 FX3 7.02 的实际运行模块，以及 FX5 私有 ISP／菜单供体怎样调用它们。现在没有生成一个靠猜测地址或模拟硬件回复工作的“适配器”。

原九项完整要求保持：完整 FX5 私有菜单供体、VENICE 完整 ISP／校准、真实 RAM／DMM、CMOS RAW、专业 UI 与 MAIN 录像、精确修改包、经典7.02修改包准入、正常启动与独立恢复，以及停在实际刷写之前。本轮补充缓冲层的源码约束，未将其缩为缓存或单张LUT目标。

上一轮公共接口查询带来了改变下一步取供体路径的证据，本轮新增成对接口约束；两轮按当前目标的进展定义归为 progress，准备状态仍未达到可刷入。原生目标回读为 active，未沿用旧 blocked 计数。

复核入口为 [analyse_memory_contract.py](analyse_memory_contract.py)。它核对44份源码摘要、42个字面位置、20个原配置范围、9个边界输入，及先前 AP 暂存与公开目录阶段共109份封存文件。没有执行 Sony C／汇编、cache／TLB 操作、原生更新程序、机身／USB／BLE／相机IPC或刷写，没有修改另一 owner 的文件或运行其工具。
