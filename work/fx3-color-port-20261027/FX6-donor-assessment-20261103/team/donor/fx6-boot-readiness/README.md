# FX6 启动准备度：固定来源离线预检

**结论（2026-11-03）：现有 FX3 TRY2v2 VM 不能作为 FX6 固件已启动或 FX6 电影色彩已移植的证据。** 它启动的是 FX3 7.02 内核和原版 FX3 AP 入口，带大量 `/simulation` 模型；CPIO 虽含原版 `liro.ko`，却没有 `system/av-cam.bin`。历史 TRY2 串口在约 guest 501.9 秒出现 LIRO 未解析符号，未见 AV/ORIL 装载成功回执。下一步先由 VM 负责人在黑帧工作允许后验证 **FX3 原版 LIRO + 原版 FX3 AV 的最小装载基线**；FX6 自身内核在 `virt` 的早期启动是另一条独立路线。本目录只提供离线预检和声明性候选，不生成可启动镜像。

## 可复核物与证据等级

- `preflight.py` 逐个 SHA-256 校验固定来源，解析 ARM64 Image 头、DTB、原版 init 脚本、CPIO 审计、ELF64 `.symtab` 和 `__ksymtab_strings`；结果见 [`preflight-receipt.json`](preflight-receipt.json)。所有文件偏移均是原始文件偏移；模块为 `ET_REL`，未加载前没有固定运行 VA。
- `build_manifest.py` 生成 [`candidate-manifest.json`](candidate-manifest.json)，标记为 **声明性候选，不可直接启动**，分开记录 FX6 独立启动与 FX3 后端功能接入的试验门槛。
- `verify.py` 重新计算两份 JSON 并比较，输出 [`run-receipt.json`](run-receipt.json)。此为静态/离线回执。本文引用的 TRY2 串口仅是**既有 VM 历史**；本轮 QEMU、CP、AV、相机、USB、SD 操作均为零。

### 固定输入

| 输入 | SHA-256 | 用途 |
|---|---|---|
| TRY2v2 `candidate.json` | `67eb81401a457bf7ffecb21f7367e7819b5bf3e13aef39dd8a4c9001ce408417` | VM 参数和 CPIO 指针 |
| TRY2v2 `cpio-audit.json` | `cc0b3c5b1925aa4bb0cb14aab275f2831833c7378490ca5408789f3824eb4847` | 1140 个成员与 guest init 原文 |
| guest CPIO | `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d` | 原版文件是否已打包 |
| TRY2 `serial.log` | `8157737391d2d8e3acf46790312826b0084539bda82e2bbe228bc1f1d6f1d16b` | 历史运行边界 |
| FX3 7.02 Image | `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c` | 当前 VM 所用内核 |
| FX6 6.01 Image | `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9` | FX6 独立启动候选 |
| FX6 AV / CP | `56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf` / `60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668` | 供体镜像，均未执行 |
| FX3 7.02 AV | `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf` | 第一条路线的原版基线 |
| QEMU guest DTB | `b6f9f4c04d0da101565d67244629a0ad7a3954c8af004f353c16ae0c8b499de7` | 当前 virt 设备树 |

路径、长度及其余输入 SHA 在回执 `fixed_sources` 中，校验不符即失败。TRY2 串口与回执均只读；运行回执 SHA 为 `50d317dee9de7eff4b7e238a384565357c491e5a5de078508888d0c676e2184d`。

## 当前 FX3 VM 真正加载了什么

| 层 | 固定证据 | 当前判断 |
|---|---|---|
| 内核/入口 | TRY2 `command.json` 指向 FX3 Image；`virt,gic-version=2,secure=off`、`cortex-a35`、4 vCPU、5120 MiB；CPIO init 第 288 行运行 `/usr/bin/bootin.elf 'target=qemu ' dmode=3`。串口还记录 `FX3_AP_IM_PROCESS=237` 与 `/usr/bin/im.elf` 原进程路径。 | FX3 AP/IM 入口启动有历史串口，**不是 FX6 Image 启动**；原进程同时使用 `/simulation` 的 LD_PRELOAD/软件模型。 |
| Backup | init 第 125/126/128 行原版 FX3 `backup.ko`，历史串口 `FX3_BACKUP_INSMOD_RC=0`。 | 证明该历史 guest 模块加载；不证明 FX6 Backup 状态/持久化或 CP 同步。 |
| LIRO | CPIO `usr/kmod/liro.ko` SHA `b4bd80cc614751e0092ee19e89cb90632db580bc01f23f1a1df23544e9b10186`。init 无显式 `liro.ko`；自然 AP 路径尝试装载，串口出现 4 个未解析符号。 | **文件存在、装载失败**。 |
| AV | CPIO 无 `system/av-cam.bin`；原版 FX3/FX6 `im.elf` 均在文件偏移 `0x7df6` (`32246`) 含 `fn=/system/av-cam.bin load=1 debug=1`；既有串口无 `av-cam.bin`/`ORIL` 文本标记。 | 装载配置有原字节，路径对应文件缺失；没有 AV 成功加载证据。 |
| CP | CPIO 有 FX3 `usr/sabin/sa_sabin_cp_cam_post.bin`，当前 init 设置 `FX3_CP_VERSION_TRANSPORT=unavailable-v1` 等软件模型。 | 没有 CP CPU、原版 CP app 执行或真实 DMA 的证明。 |

TRY2 串口四个符号位于字节偏移 `336763`、`336834`、`336892`、`337448`：`dma330_mem_transfer_async`、`pciatu_unmap`、`pciatu_map`、`interchip_transfer_async`。其中首尾两处附近有其他线程日志交错，不能仅凭截断的 `Unknown symbol` 行推断完整时间线；对应 LIRO ELF 中四项均为未定义全局符号，给出了独立静态佐证。

### 原版模块链接边与硬件边

FX3 与 FX6 的 `insmod_drv1`/`insmod_drv2` **各自字节相同**，SHA 分别为 `22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591` 与 `19757bdd450061f861e2da44a6a93be2525668e3f7edc64e5a99a25bde56564e`。原顺序先 `dma330.ko phy_inst_area=0x4102E4000`（drv1:2），再 `pciedma.ko`（drv2:6）、`pci_ep_cp.ko`（:7）、`pcieatu.ko`（:9）、`backup.ko`（:15）、`icdt.ko`（:25）。当前自定义 init 只显式加载 Backup 等若干模块，没有显式加载 `dma330`/`pcieatu`/`icdt`。原脚本列出 43 个 insmod 项，其中 8 个文件在当前 CPIO 不存在（回执 `native_insmod_order`）；它们是否均为此缩减 guest 的必要条件需要按调用依赖逐项判断，不能按脚本缺项直接判启动失败。

| LIRO 未定义导入 | FX3/FX6 定义者（原 ELF `.text` 偏移，文件偏移） | 静态结论 |
|---|---|---|
| `dma330_mem_transfer_async` | `dma330.ko` `+0x87c8`，文件 `0x8830` | 两版函数体 SHA 均 `c993f50e0370f29a9f9cc5031aac2c04a0a8c21b5c2a9934ab93b4a3131ea9b2`，有 `__ksymtab_strings` 导出名。 |
| `pciatu_map` | `pcieatu.ko` `+0xed8`，文件 `0xf40` | 两版函数体 SHA 均 `60e400072fb75d6d9a014b3c9f5bd4a6e6828f2782e0c3984eecec23e625ee15`，有导出名。 |
| `pciatu_unmap` | `pcieatu.ko` `+0x13b8`，文件 `0x1420` | 两版函数体 SHA 均 `8c76feadc92adaa07e14349c8efe9f56c04baef63d3b1dc9de89f0ee4c1d7fdb`，有导出名。 |
| `interchip_transfer_async` | `icdt.ko` `+0xf18`，文件 `0xf80` | 两版函数体 SHA 均 `82e09f6a322b54b8751fbf16a3688502f5dbab0df8ca1a14ff7b3ee947ab6402`，有导出名。 |

这些是 **ELF 符号与导出资格**，不表示能在 virt 初始化。FX3/FX6 原版 LIRO 分别 SHA `b4bd80...` 与 `8a7cfc...`；供体 provider 模块的完整 SHA 与 FX3 不同，完整值在回执 `modules`。当前 guest DTB root `linux,dummy-virt`，含 generic PCI ECAM `pcie@10000000` 和 virtio MMIO；FX6 原生 updater DTB root `cxd,cxd90057`（SHA `87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca`），其 `arm,pl330` 设备为 `0xf1057000`，另有 `snps,dw-pcie` 和 Sony 端点节点。通用 PCI/ECAM 的存在**不等于** Sony PCI ATU、DMA 控制器或 CP 设备模型，模块链接成功也不足以证明硬件路径。

## 两条路线与第一个阻断

| 路线 | 已能复用 | 第一确切门槛 | 后续独立依赖 |
|---|---|---|---|
| **FX6 自身固件在现有仿真平台启动** | FX6 ARM64 Image 原字节；两版 Image 头的 text offset `0x80000`、image size `0x6af000`、flags `0xa`；现有 QEMU `virt` 平台与只读 donor 分区。 | **FX6 Image 从未在 virt+适配 DTB 下取得首条内核串口。** 原生 `cxd90057` DTB 不能直接当 virt DTB，须用当前 virt DTB 适配最小 console/init 并记录首个故障；不能预设 FX6 kernel 可用。 | `/dev/nflasha2/3/8/15` 等原生挂载、Sony 驱动设备、AP/AV/CP 调度与 Backup/机型状态。FX6 fstab 把 `/system` 接 `nflasha3`、`/cp` 接 `nflasha8`、`/usr` 接 `nflasha15`；当前 CPIO不提供这套分区挂载。 |
| **FX6 功能接入 FX3 固件后端** | FX3 VM 可到 AP 入口；FX3/FX6 原版 insmod 顺序一致；四个 LIRO 导入在两版原始 provider ELF 中可定位；此前离线 descriptor/表算法材料可复用作接口研究。 | **先解决 FX3 原版 LIRO 的四个缺符号，并提供 FX3 原版 AV 路径，取得真实 ORIL/AV 装载回执。** 当前首个已见运行阻断是 LIRO 未解析符号；AV 文件缺失是静态前置缺口。 | 按依赖闭包筛选原版模块；处理其 MMIO/IRQ、Backup 实际字节、AP/AV/CP ABI、事件来源及机型差异；FX6 CP、DMA、像素与 RAW 仍未进入实测。 |

FX6 `nflasha3`/`nflasha8`/`nflasha15` 原分区镜像 SHA 分别为 `a78c28d835b0cc9c3105332d82f7f404e319d3bf289146935482fd0c887c9b02`、`7fbf12865eef11ea4db2d822af88deb0b95e565d10dbf80eee31f23689858315`、`c62b1775a2fe36669b644a55cac7eab9ce2636e6fb8469cbf791d00b8ed6fc6a`；它们均只读，未复制或挂载。通用 `virt` 的能力边界也可复核本地 QEMU 11.1.2 维护者文档 `work/fx3-vm-20261101/menu-repair-01/runtime/qemu-display-build/sources/qemu-11.1.2/docs/system/arm/virt.rst`（SHA `9fbcc9fc3040ef695e3058cd4bab05e10f6282ab7ba0846a93ee9f524933e3e1`，第 6–7、33、49 行）：它描述不对应真实硬件的虚拟平台及 PCIe/virtio 能力，不等于 Sony SoC。

## 交 VM 负责人的单次最小试验

**选择 FX3 后端装载路线优先。** 基于固定 TRY2v2 候选制作**新的隔离候选**，不覆盖当前黑帧候选；先离线计算拟加载 FX3 模块的递归导入/导出闭包及硬件访问，区分内核自带导出与必要 `.ko`。原版 `icdt.ko` 引用 `pcidma_transfer_async`，既有 FX3 `original-full-module-provider-catalog.json` 把它列为内核导出；因此当前 CPIO 缺 `pciedma.ko` 是原生脚本差异，尚不是已证实的此路径硬阻断。闭包后补原版 FX3 `/system/av-cam.bin`（上表 SHA），按原版相对顺序和 fail-fast RC 检查装载必需模块，保留既有 Backup 与 IM。只读记录每个 insmod RC、`/proc/modules`、LIRO 错误、ORIL header `+0x20` 与 provider slots、AV 首个映射/入口 PC 或首故障；遇第一处原版模块初始化、符号、文件打开或 ORIL 装载失败即停止，不用成功桩。此为设计，**没有执行**。

按当前 VM 参数单次需要 4 vCPU、5120 MiB，建议上限 650 秒（历史 LIRO 错误约 guest 501.9 秒），隔离 CPIO 约现有 453,184,500 B 加 FX3 AV 13,348,560 B 与经闭包判定的少量模块；不需再复制完整供体，也不增加模拟设备。FX6 自身 Image 的独立第一门槛可在同一现有 QEMU `virt` 运行器由 VM 负责人做 ≤180 秒早期串口试验（仅 Image、适配 guest DTB、最小 console init，不启动 AP），需另存内核/DTB/initrd SHA、QEMU 命令、串口和退出码。两次试验均排在当前 VM 黑帧优先工作之后，遵守既有独占运行安排。

## 重跑

在本目录执行：

```sh
python3 preflight.py > preflight-receipt.json
python3 build_manifest.py > candidate-manifest.json
python3 verify.py > run-receipt.json
```

脚本使用 Python 标准库，校验完整 CPIO 与 donor 分区摘要，但不解压/复制/更改原件。`verify.py` 只在两份产物与固定来源重新计算结果逐字段一致、且没有把运行边界写成通过时成功。由于这些回执只是离线核查，`PASS` 不代表 FX6 内核、AV、LIRO、CP、DMA、UI、像素或实机通过。
