# 固定 FX3 模拟器中的 FX6 原内核：首串口、原 init、首模块门槛

**最新运行结果：原版 FX6 6.01 Image 在未改 FX3 QEMU/DTB/CPIO 平台执行到固定 CP Backup helper，绑定入口实测返回 `-7`、BusyBox `insmod RC=7`，没有进入 AP。** runtime owner 唯一 pre-CP 轮 `fixed-fx3-4571c53b` 的 receipt SHA `eb3990eb822a57322a496c7819aa47e502f875f0a7f0ca898235a45080164830`、串口 SHA `dfd0ef290ff0ea0c07335682f3e5a68b0ee5f626d41034a927a7031342df2be8`；独立命令/基线/原日志复核见 [`decision-brief/README.md`](decision-brief/README.md)。FX3 原模块、synthetic LDEC 自检和 FILE100 观察链到此之前通过各自有限门槛；这仍不是 FX6 AP/AV/CP、电影菜单、RAW/像素或实机通过。

## 固定平台与已撤回的探索候选

唯一平台基线来自 runtime 负责人的 [`fx3-platform-frozen-baseline.json`](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json)（SHA `854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669`），本目录没有另定义平台。`fixed_platform.py` 验证它与历史 command/env、完整文件 SHA 一致，产出 [`fixed-kernel-candidate.json`](fixed-kernel-candidate.json)（SHA `42cddf844eb37a4712feb59a0c595ab9746eee21b37b210a7f81741bdb16797c`）。逐字段差异如下：

| 字段 | 固定 FX3 基线 | 本轮 FX6 内核候选 | 差异 |
|---|---|---|---|
| QEMU | `qemu-gpio5-bf4d46481998b8fb`, SHA `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d` | 同一二进制 | 无 |
| machine/CPU/内存 | `virt,gic-version=2,secure=off`; `cortex-a35`; SMP 4; 5120 MiB; `tcg,thread=multi` | 完全相同 | 无 |
| 设备/模型 | `-nodefaults -nic none -display none -no-reboot`；原 `FX3_VM_ESRAM_RAM/HIGH_DDR/SONY_TIMER/SCU_REQUEST/GPIO_BANK5=1` | 完全相同；runner 拒绝额外继承 `FX3_VM_*` | 无 |
| 完整 guest DTB | SHA `b6f9f4c04d0da101565d67244629a0ad7a3954c8af004f353c16ae0c8b499de7`，载入 `0x400002000` | 同文件、同字节、同地址 | 无 |
| 完整 CPIO/Backup | SHA `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d`，载入 `0x440000000`；Backup SHA `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f` | 同文件、同字节、同地址 | 无 |
| Image | FX3 SHA `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c` | FX6 SHA `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9` | **仅 `argv[29] -kernel` 固件载荷替换** |
| host 观察 | 历史串口文件 | 每轮独立串口文件 | 仅日志去向，不改变 guest/设备 |

先前离线生成的 `minimal-initrd.cpio`（SHA `1351de617d8a58cab2e9bf435f0e2b066cb195ea89dc1a72c756a44c61a738ae`）、`fx6-virt-early.dtb`（SHA `a1d0494b9f5c116872bef8b4151dcb6d514388445153f24163819e94fc3ae363`）与探索 `candidate.json` **已撤回，禁止运行**。该 DTB 改了 `/chosen/bootargs` 与 `linux,initrd-end`，initrd 从固定 453,184,500 B 换成 1,860,816 B，违反用户指定的固定 FX3 平台；文件为审计保留，旧 `withdrawn-original-candidate.json` SHA `98c36623a2cf3788b3f6a0cd7ba54385e32e7ef24200a67ba0568c4e762b4dc0`。它从未启动。

## 运行与 host 回执

`fixed_runner.py` 只供 runtime 负责人显式 `--run`，按现有 TRY2 顺序非阻塞取得 `outputs/fx3-vm/.run.lock` 和原 runtime `.run.lock`；占用就拒绝、不会停止别的 QEMU。它用同一 `-S`/QMP 顺序 `capabilities → info registers → query-cpus-fast → cont`（原历史 QMP SHA `92db3fc52db0c2a42e55b52d127d795a2ccd56fc5f3e713c32c1c8f8f84a810c`；pre-cont `PC=0x400000000`, `X00=0`），限定 ≤180 秒、仅回收自身进程组、记录完整串口/退出/锁。串口轮询不是精确 CPU 断点，停止时可能多出几行。

| 回合 | 固定回执/串口 SHA | 实际边界 |
|---|---|---|
| 首次 `fixed-fx3-0b8eaf59` | receipt `f946ef3cdd740ff5efb9df6eafc66cb496cd3d5744ee5fa50a6d288d80f80a4b`，serial 0 B | host 端连接绝对 Unix socket 路径过长，QEMU 在 `cont` 前退出；**没有内核结论**。 |
| 修复后 `fixed-fx3-9581d529` | receipt `18890489ebb215641b43213b380d7eb06367ffb5861a020f1d5254395910b921`，serial `24b010d7d6aafb4fa84d5c34dec3b9d73bd93d88f40e9c8a0f2c23f01da005b3` | 0.323 秒主动退出；有 `Booting Linux` 和第 2 行 FX6 `Linux version`，无 init。原 receipt 的 `linux_version_marker=false` 只查首行，派生 [`host-selftest-and-run-addendum.json`](host-selftest-and-run-addendum.json) 更正解释，**原回执未改**。 |
| init 边界 `fixed-fx3-306428ab` | receipt `9c3e04bc3a6b62c57ea411b781c3093321d4b0543eb7c12e039bc4cf3daa204f`，serial `69eea39535b90eeb4e02584a2256bd6ecca5218314c5f61fadf95c288a50a978` | 完整 `FX3_DEVTMPFS_RC=0` 后停，随后少量 CPUSET 输出；无 panic/oops、无 AP。runtime 审阅回执 SHA `63b04f21d58cf90f1add79bd705b8fde56dcd52eb9c4424ce945b713a4b73a42`。 |
| 原模块入口 `fixed-fx3-c72ee0b9` | receipt `c37ad1d014d90fd3311722eec1ff025468aeeccc1001d91456bd06cf6b278ceb`，serial `034552e396f4dbd49aa55e85fb931272d009e41cf7c0a413d85b373b9c7b8536` | `devno/osal_utm/osal_uipc` 各 RC0，`/proc/modules` 开始处停；无 `/dev/uipc` 节点结果、无 simulation/AP。 |
| pre-CP 唯一短轮 `fixed-fx3-4571c53b` | receipt `eb3990eb822a57322a496c7819aa47e502f875f0a7f0ca898235a45080164830`，serial `dfd0ef290ff0ea0c07335682f3e5a68b0ee5f626d41034a927a7031342df2be8` | LDEC 自检、FILE100 ready 后，CP helper 两次 `binding_failure`/`init_module -7`，`insmod RC7`，无 AP。 |

修复后的 socket 连接先临时 `chdir(run_dir)` 再连相对 `q`，异常也恢复原 cwd。`host_selftest.py` 在**不启动 QEMU、不取锁**的条件下验证 157 字节绝对路径环境可用相对 Unix socket 通信，并从固定 FX3 历史串口（SHA `8157737391d2d8e3acf46790312826b0084539bda82e2bbe228bc1f1d16b`）解析完整 `FX3_DEVTMPFS_RC=0` 与首模块 `FX3_INSMOD_RC_/kmod/devno.ko=0`。当前审阅 runner 源码快照为 `fixed_runner-reviewed-527c789e.py`，SHA `527c789ed3be11c0c0387ce8ea5fb0e9837bf3ddc5a03ecd5d57d18f39bb0f41`；首次失败运行时的 runner 源文件未被单独快照，本目录保留失败运行、历史命令与补充说明，不把后来的源码冒充当时字节。

## LIRO 的 FX3 原模块递归闭包

`closure.py` 从**原版** FX3 LIRO 的 136 个 ELF 未定义符号出发，用 126 模块固定 catalog 的导出候选做 BFS，再逐个以原 `.ko` SHA、ELF64 `.symtab`、`__ksymtab_strings` 和固定 CPIO 成员重验；内核侧核对 FX3 原 Image 的 41,269 kallsyms 与 6,089 项独立导出交叉清单。结果 [`liro-closure.json`](liro-closure.json)：**9 个模块、122 条模块符号边、283 条内核符号引用（121 个不同内核名字）、0 个未解析强导入**。这只闭合链接名字，不能证明 init、MMIO/IRQ 或 CP 能工作。九个模块都已在固定 CPIO，当前 `/init` 显式加载 devno、osal_utm、osal_uipc、Backup、DMM；`dma330`、`pcieatu`、`icdt` 无显式加载。

| 模块（原 SHA 前 12 位） | 原 `init_module` 文件偏移 | 硬件/状态依赖证据与边界 |
|---|---:|---|
| `devno.ko` `cca1d9acd87a` | 无 init 符号 | 零未定义导入；仍须实测模块格式/装载返回。 |
| `osal_utm.ko` `f6679c6481ad` | `0x670` | `init_module` `.init.text+0x20` 重定位到 `udif_driver_register`；原内核/FX6 实现不能按名字相同推 ABI 相同。 |
| `osal_uipc.ko` `6aa0f5c8c72f` | `0x7088` | UIPC/队列注册；`init_module` `+0x11c` 到 `udif_driver_register`，后续需要 `/dev/uipc` 实物节点观察。 |
| `backup.ko` `8a8d8c949699` | `0xd178` | `Backup_load`、物理映射及内核 `pcidma_transfer_async`；FX3 历史成功不等于 FX6 内核上成功。 |
| `dmm.ko` `1e28a4921b` | `0xc520` | `Backup_read`、`arch_phys_to_*`、原 DMM 配置；物理布局和 Backup 值未迁移。 |
| `dma330.ko` `9ba277f011b3` | `0x90c0` | 原脚本参数 `phy_inst_area=0x4102E4000`；有 `__udif_request_irq` 导入，原生 DTB `arm,pl330` 在 `0xf1057000`，固定 virt DTB 无该节点；IRQ/MMIO 尚未验证。 |
| `pcieatu.ko` `08c61d2d889f` | `0x1aa0` | `init_module` `+0x39c` 调 `udif_driver_register`；数据引用 `udif_pciatu+0x38 → .data+0x88 → .init.text+0`；其 callback 在 `.init.text+0xd4`（文件 `0x17f4`，原指令 `000040b9`）按默认 `pcie_ctrl=3` 读计算地址 `0xfffffffff7300004`。原生 DTB `pcie_i` 范围以 `0xf7000000` 起，固定 guest 仅 `pci-host-ecam-generic` 于 `0x10000000`；该读**未运行**。 |
| `icdt.ko` `9cb41cfbd87` | `0x1ad8` | 内核 `pcidma_transfer_async` 加 OSAL 消息队列；链接不是 CP/Interchip 已提交。 |
| `liro.ko` `b4bd80cc6147` | `0xa4d0` | 四个具体导入 `dma330_mem_transfer_async`、`pciatu_map/unmap`、`interchip_transfer_async` 来自上列三模块；缺 `/system/av-cam.bin` 的旧缺口仍在。 |

原生 FX3 DTB SHA `c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280`，root `cxd,cxd90057`；固定 guest DTB root `linux,dummy-virt`。物理 `0xf7300004` 的计算来自原 `pcieatu.ko` `.data` 默认值 3 和 `.init.text+0xc4..0xd4` 原指令，不是已捕获运行态访问；原生 DTB 的 `pcie_i` 节点本身标记 `disabled`，故它也不是模块必然成功的证明。

## FX3 模块与 FX6 内核的 ABI 预检

[`fx3-modules-vs-fx6-kernel.json`](fx3-modules-vs-fx6-kernel.json) 交叉核对 FX6 原 Image SHA、41,294 kallsyms、6,089 导出与上面 9 个**固定 CPIO 中的 FX3 `.ko`**：

- 两版内核原 `vermagic` 字节均为 `4.9.337-scel+ SMP preempt mod_unload aarch64`（Image 文件 `0x43a150`），九模块一致。
- 九模块均无 `__versions` 节；两版 kernel 符号表中的普通/GPL 等 `__start___kcrctab` 与 `__stop___kcrctab` 地址相等，表跨度 0。未取得精确构建配置文本，故 `CONFIG_MODVERSIONS` 值**未直接证实**；当前材料没有可对照的逐符号 CRC。
- 原 FX3 闭包引用的 121 个不同内核导出名在 FX6 导出表**全部存在**；108 个目标地址不同。ET_REL 模块通过符号重定位，不应把原 FX3 绝对地址抄进适配器；名字存在也不能证实结构布局、调用约定或驱动行为一致。
- 关键 `udif_driver_register` 前 32 个原指令字节 SHA 在两版不同；`pcidma_transfer_async`、`__udif_request_irq`、`arch_phys_to_noncache` 的前 32 B SHA 相同。这个窗口很短，仍不能证明完整函数同语义。精确文件偏移、地址、字节与哈希在 JSON。

## 接下来的最小软件门槛

已审固定 CPIO `/init` 第 1–88 行与第 114–118 行，前版 [`software-first-gate.json`](software-first-gate.json) 保留当时的首模块运行未知记录；新回执将该边界推进到**第 86 行 `/dev/uipc` 字符节点判断**，尚未证明队列或硬件功能。第 89–113 行的 simulation 前序和固定 CPIO 构建/源码/物理预留区现已逐项审阅，见新 [`pre-cp-audit/README.md`](pre-cp-audit/README.md) 及回执；其中没有发现未守卫的旧 FX3 内核绝对 VA 补丁或跳转，但会对固定 guest 预留 RAM 作有界写入，FX6 内核导出函数语义仍须运行验证。

以下原字节分析在运行前给出了**条件性软件阻断预测**，对应 `/init` 第 115 行的 CP Backup helper；最新运行现已实测 `binding_failure` 与 `init_module -7`，但串口未记录 lookup 的实际返回地址，不能把某个子条件写成直接观测。固定 CPIO 成员 `simulation/fx3-cp-backup-reset-v1.ko` SHA `f4d7a1fa048d3548840fb2b9dd91e9538b19a34e48089a01ee466c02d3c277ca` 与本地 `fx3-cp-backup-v5-native101.ko` **逐字相同**；固定构建回执 SHA `d9a14d32fd284e9deb9253c159d2c91e61f3568141426b72085e70eda47570e4` 将模块绑定到 C 源 SHA `b0de532abb5c688f360f46d862abe1c8c1b2114f8448b5e3a91573cd9987b4c0`，该源在第 49 行引入 header SHA `6f2116440d17db50f7c35b57f7ab967ce304318a431649a76885c096bd87ee96`。`init_module` 第 51 行首先调用 `sync100_start`，失败即返回；header 第 90–96 行按名字取得 `pcidma_transfer_async`，随即要求地址**恰等于 FX3 `0xffffff80083220c8`**，否则走 `fail` 返回 `-7`。编译后的原模块 `.text+0x46c..0x4cf`（文件 `0x4ac..0x50f`，SHA `f6300113b90b236b0c8417f8d6cc257e7de448d24f8db6c9f889a590e5bad4cb`）亦有原指令 `cmp x8,x20` 于 `.text+0x4c0`、`b.ne` 于 `+0x4cc`、`mov w0,#-7` 于 `+0x7a8`；`.text+0x484` 的 CALL26 重定位指向 `kallsyms_lookup_name`，字符串偏移 `0x55` 为 `pcidma_transfer_async`。本次 FX6 原 Image 独立导出索引该函数链接地址为 **`0xffffff8008322f70`**（文件偏移 `0x2a2f70`）：**若运行抵达该 helper 且 lookup 返回这个 FX6 地址，现有 helper 必拒绝绑定**。这不是已观察到的 guest 错误；FX6 内核的运行回执还未越过首模块，运行态 lookup 地址也未观测。header 第 10 行的 native fallback 又硬编码 FX3 `0xffffff8008322228`、`0xffffff80083220d8`；单改第一处地址会留下错误跳转风险。旧 `fx3-cp-backup-reset-v1.ko` 本地构建 SHA `7e756a4e9a2edb9770baf92c07cb88f342690b1636d6c258f0ec2e1d6a98abd2` 与 CPIO 不同，不能代替本次匹配的 v5 源。

## 固件侧合同与候选判定

新 [`firmware_contract.py`](firmware_contract.py) 固定 FX3/FX6 两版原 Image、kallsyms 和原 Backup `.ko` 的 SHA，重跑得 [`firmware-side-contract.json`](firmware-side-contract.json)。原 FX3 Backup `.ko` SHA `8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d` 中 `backupfile_get_cp_data` 位于 `.text+0x7030`；`.text+0x70bc`（文件 `0x7124`）的原 CALL26 重定位确实调用 `pcidma_transfer_async`，返回 PC 为 `get_cp_data+0x90`，与 helper 特定调用者门吻合。该门只放行精确 40 B DMA 描述：源 `0x404000000`、目标物理 `0x4040d2000`、长度 `1,369,580`、回调 `backupfile_cb_getcp`、其他字段为 0，且要求锁/快照/校验状态；非目标调用由原指令 fallback 接手。合成 CP 银行还要求固定 BK4 头、819 组/31,197 行等结构，见原 core header SHA `ffa767cec3bdd7f94fa9aaf985024535f550446a2cd8ec7524fd10dc63701e47`。这是固定 **FX3 VM helper** 的消费合同，不能冒充 FX6 原 CP 或新电影数据合同。

| 固定门 | 原字节结果 | 对固件侧适配的影响 |
|---|---|---|
| API 地址与入口 16 B | FX6 `pcidma_transfer_async` 在 `0xffffff8008322f70`，首 16 B 与 FX3 相同；FX3 必需地址 `0xffffff80083220c8` 在 FX6 Image 文件 `0x2a20c8`，实为 `watchdog_touch_exception` 内代码，首 16 B `620000b9c20e805223300091620000b9`，不等于门要求。 | 只改导出指针会使 helper 在占用的 watchdog 代码上补丁，不能作为候选。 |
| 两个原跳转 | helper 固定 `0xffffff8008322228`、`0xffffff80083220d8`；FX6 中分别落在 `subsys_new_mm`、`watchdog_touch_exception`。 | 不能用 FX6 函数首 16 B 一样来推断 fallback 安全；需要重新布局或独立兼容函数，且保持原 watchdog/subsys 行为。 |
| 完整函数和 patch API | 两版 `pcidma_transfer_async` 均 360 B，但 SHA 分别 `79e37093...`、`fdfe1137...`，有 5 个不同指令字；两处 `add` 立即数由 `0xd00` 变 `0xe00`，另有 3 个调用偏移差。`aarch64_insn_patch_text` 地址均 `0xffffff800808b268`、大小 216 B，但整段 SHA 不同（JSON 有全值）。 | 名字、地址及入口 16 B 不能证明函数/结构体/热补丁语义相同，须核实完整调用路径与写集。 |
| patch 生命周期 | helper 调 `aarch64_insn_patch_text` 写 4 指令，再读回；停止时恢复原 16 B；出错禁用。 | 固件侧必须保留可读/可写补丁目标、恢复行为和非目标调用语义，不得只伪造成功返回。 |

此结论限定于**现有 FX3 模拟器及其固定 helper 对 FX6 内核布局的绑定**；不能据此推出真实 FX3 硬件无法运行 FX6 固件，也未做任何真实硬件验证。

**本阶段没有生成 FX6 Image 补丁。** 固件侧若要在不变更固定模拟器及 helper 的前提下满足合同，需要使真实 `kallsyms_lookup_name` 返回旧 VA，并在该 VA 放可安全补丁的完整兼容实现，同时迁移现有 watchdog/subsys 代码与引用、确保两处硬编码 fallback 跳转正确、重验 `aarch64_insn_patch_text` 和 Backup 的 DMA/CP 银行 ABI；这已超出有界单点 diff。当前最小候选 diff 因原 VA 代码冲突而**拒绝生成**，回执 `minimal_firmware_diff_feasible_now=false`；不是说任何固件侧工程绝不可能。保持 FX3 原内核承载部分 FX6 AP/AV 是另一条**混合移植**路线，不能称 FX6 整套固件在模拟器启动，且仍需逐项证实模块/Backup/CP/硬件边界。

`pre-cp-first-result` 模式已经由 runtime owner 运行**一次**，结果和两条路线的工程边界见 [`decision-brief/README.md`](decision-brief/README.md)。不再重复已知 CP 拒绝、不放宽 helper 门，也不在用户选择混合路线前生成混合候选。

离线重跑：`python3 fixed_platform.py`（只生成固定候选声明）、`python3 closure.py`、`python3 abi_check.py`、`python3 audit_software_gate.py`、`python3 firmware_contract.py`、`python3 pre-cp-audit/audit_pre_cp.py`、`python3 pre-cp-audit/host_selftest.py`、`python3 host_selftest.py`、`python3 fixed_runner.py --check`。这些命令不启动 QEMU；只有 runtime owner 可在现有锁协议下显式使用 `--run`。
