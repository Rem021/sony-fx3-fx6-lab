# FX3 7.02 原包的 DMA 与缓存接口绑定

2026-10-30。**已将上一轮7.00公开源码中的部分接口，绑定到经典 FX3 7.02 原包的内核导出及驱动调用重定位。** 原包中的 DMA 地址转换与前轮源码规则一致，原缓存分派也已追到实际 `DC` 指令之前。当前仍缺完整 FX5／VENICE 私有供体、MAIN 像素链与实际机身状态，未产生可正常刷入的修改固件。

## 原包证据

从已固定摘要的原分区重新读取所需成员，没有重跑旧固件解包、符号恢复、USB或恢复工具。

- 原 `/vmlinux.bin`：6,610,952B，SHA256 `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`，内含 `Linux version 4.9.337`。
- 复用阶段146已恢复、固定 SHA 的41,269项符号目录导航；本轮没有重跑其 main、guest 或设备流程。
- 取得14个相关内核函数范围，另补一个原始失效缓存的顺序落入范围；10个导出另由原 `__ksymtab` 的16B地址／名称记录独立核对。
- 在原 `/usr` 和 initrd 的565个AArch64 ELF中，找到22个内核模块及1份共享库对选定名字的217处重定位。共享库仍未解析到符号提供者，不能全部算成内核调用。

这里绑定的是**原包中的链接关系**，不是当前机身已加载的模块、实际内核地址或KASLR状态。公开参考仍分别来自 [Sony FX3 Ver7.00](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html) 与 [Sony FX5](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)；它们不替代7.02原二进制证据。

## 原指令验证

[12个独立RAM案例](original-instruction-probes.json)共执行158条原指令，没有 helper 成功桩或硬件回复：

| 输入／路径 | 原结果与停止位置 |
|---|---|
| AP默认起点 `0x412000000` → DMA32 | 返回 W0=`0x12000000` |
| DmmCfg AP投影 `0x4132D8E00` → DMA32 | 返回 W0=`0x132D8E00` |
| ESRAM `0xFE001000` → DMA32 | 返回 W0=`0xFE001000` |
| `0x132D8E00` → 64位物理地址 | 返回 `0x4132D8E00` |
| `0xFE001000` → 64位物理地址 | 返回 `0xFE001000` |
| FX5地址域、CP地址域及两个上界反对照 | 进入原 `printk` 调用前停止；没有执行日志、读运行时debug值或声称取得最终错误返回 |
| UDIF flag1／flag3 | 原分派进入 clean；在原 `DC CVAC` 前停止 |
| UDIF flag2 | 原分派进入 invalidate；在原 `DC IVAC` 前停止 |

`arch_p64_to_p32` 返回类型是32位：有效分支可能保留 X0 中的输入高位，调用者应读取 W0。若将该返回值按64位地址消费，会误读接口。这是本轮原编译指令显示的ABI细节。

所有完整返回案例均核对SP和callee-saved寄存器恢复。缓存案例只是前缀，尚未返回，也没有执行任何 cache／TLB／系统寄存器指令，不作为缓存一致性或传输完成验收。

## 哪些驱动确实引用了它们

| 原模块 | 选定调用的含义 |
|---|---|
| `dmm.ko` | 2处 `arch_phys_to_noncache`；11处 `arch_phys_to_cache` 位于保留名称的 `dmm_log_CreateArea`，这些是日志区线索，不能充RAW像素分配 |
| `cachecontrol.ko` | 引用 `arch_phys_to_va`、`arch_phys_to_cachetype2`、`__udif_cache_ctrl`，可继续追缓冲描述和缓存动作 |
| `mcmn_drv.ko` | scatterlist及block请求函数引用 `udif_dma_map_sg/unmap_sg`，不凭媒体／Cetus名称认定为CMOS采集 |

这些模块的 vermagic 为 `4.9.337-scel+ SMP preempt mod_unload aarch64`。实际模块装载和重定位落地仍待证。

`dataflowInfraFramework.so` 为ET_DYN，只保留动态符号，含未定义的 `arch_phys_to_cache`；DT_NEEDED列的是标准运行库。在上述565个ELF的动态定义表中没有找到该组名字的提供者。这只限定所查动态表，不排除自定义加载、全局注入或其他输入，不能把同名内核导出当成该库已经解析成功。

## cachecontrol 的内部描述流程

依据原模块 `.text+0x130` 的分派及 `.text+8` 的缓存帮助代码，恢复了以下**内部回调命令**，没有将其当成可直接发送给设备的外部 ioctl 规范：

| 内部命令 | 原代码作用 |
|---|---|
| `0x3000` | 从 frame+0x10 的起点和 frame+0x28 的长度计算对齐字段，然后查询缓存类型 |
| `0x3001` | 要求缓存类型为 `0x11`，再给帮助函数传 flag1 |
| `0x3002` | 要求缓存类型为 `0x11`，再给帮助函数传 flag2 |

同一准备分支可推得最少48B的frame：+0命令、+4状态、+8对齐起点、+0x10原始起点、+0x18原始含尾终点、+0x20对齐含尾终点、+0x28长度。代码使用 `0x3f` 掩码处理64B对齐；尚未找到其上层参数生产者和外层设备接口，因此这些字段还不是已验证的完整用户态ABI。

帮助函数 `.text+0xa4..0xb4` 的零值分支可跳到 `.text+0xe8`，将状态置0并跳过 `__udif_cache_ctrl`。这是静态条件路径，未制造映射失败或伪造帮助函数回复来执行它。它说明状态0本身不能证明缓存动作发生。原 `arch_phys_to_cachetype2` 也只检查首尾属性，不能作为整段每页同属性的证明。

## 保全与剩余工作

[原包链接与指令](original-binding.json)、[选定消费者](selected-consumers.json)、[作用域核对](consumer-scope.json)、[独立字节核验](verification-receipt.json)保存了原始位置、字节及摘要。前轮60份封存文件再次一致。

初始缓存失效前缀在另一个已命名原符号 `__inval_cache_range` 前被保护停止；补取该80B原范围后才继续到DC边界，未放开未知代码。一次采集遇到共享库没有 `.symtab`，修正为区分静态表与动态表；已取得的原模块逐字节复用。诊断记录保留在 `attempts/`。

下一步需追缓冲描述的上层生产者，区分DMM日志、一般传输与MAIN像素，并把私有色彩后端接入实际调用链。原九项完整要求保持：完整FX5私有供体、完整VENICE ISP／校准、真实RAM／DMM、CMOS RAW、专业UI与MAIN录像、精确修改包、经典7.02修改包准入、正常启动与独立恢复、实际刷机前停止。此次原包绑定补充了证据，未解除准入和恢复缺口。

目标回读为 active，未完成。无相机／USB／BLE／手机／相机IPC、原生Sony程序或实际刷写；没有运行另一 owner 的工具或修改其文件。所有原指令实验只在有界Unicorn RAM内进行，原件与旧回执保留。
