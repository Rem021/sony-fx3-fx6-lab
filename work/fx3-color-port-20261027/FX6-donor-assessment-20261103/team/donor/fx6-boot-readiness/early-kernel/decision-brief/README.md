# 固定 FX3 环境中的 FX6 运行边界：一次实测与两条路线

**结论：原版 FX6 6.01 Image 已在固定 FX3 模拟平台运行到 FX3 CPIO 的 CP Backup helper；该 helper 的绑定入口实测返回 `-7`，未进入 AP。** 这不是“整套 FX6 固件已启动”，也不是 FX3 机身硬件兼容性结论。协调方正在征询用户是否接受 FX3 内核承载 FX6 上层的**混合移植**；在明确选择前不生成或运行混合候选。

## 独立核对的唯一 pre-CP 运行

[`verify_run.py`](verify_run.py) 重新哈希 owner 原件、比对冻结基线 argv/env 与实际命令，并逐行核串口先后；回执为 [`verification.json`](verification.json)。原运行目录 `../runs/fixed-fx3-4571c53b/` 中命令 SHA `f4a2b1ae34b873d8b02f2d8496325772ef78ea5e7d1cc61eada6921bbd910ecd`、owner receipt SHA `eb3990eb822a57322a496c7819aa47e502f875f0a7f0ca898235a45080164830`、串口 SHA `dfd0ef290ff0ea0c07335682f3e5a68b0ee5f626d41034a927a7031342df2be8`。原冻结基线 SHA `854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669`；实际 argv 与基线只差 `-kernel` 的 FX3→FX6 Image（FX6 SHA `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9`）和串口日志路径。相同的 QEMU、`virt/gic2`、A35×4、5120 MiB、完整 DTB/CPIO/Backup 与五个模型 env 均逐文件 SHA 核验；除 Image 替换和串口日志路径外，平台及 guest 输入未变。

| 原串口顺序 | 可确认的边界 |
|---|---|
| FX6 `u24-002` 内核版本、`nokaslr` bootargs；`devno`、`osal_utm`、`osal_uipc` 均 `insmod RC0`，`FX3_UIPC_ORIGINAL_NODE_PRESENT` | 原模块入口及字符节点到达；不等于设备/队列所有行为通过。 |
| `FX3_LDEC103_INSMOD_RC=0`；三个 fixture 各有 `GUEST_EXACT byte_equal=1`，最终 `FX3_LDEC103_SELFTEST_RC=0` | **固定 FX3 simulation** LDEC 在预留 RAM 的客体自检通过；不是原 FX6 LDEC/ISP。 |
| `FX3_FILE100_OBSERVER_READY`、generation1 双读 `Backup.bin` 2,229,740 B、`FX3_FILE103_READY_CONFIRMED` | 固定观察程序以 O_RDONLY 读取 FX3 Backup 文件并写独立预留观察区；不是 CP 同步成功。 |
| `FX3_BACKUP_CP_INSMOD_BEGIN`；`FX3_SYNC100_DISABLED reason=binding_failure` **两次**；对应 `init_module ... returned -7` **两次**；BusyBox `insmod ... Argument list too long`，`FX3_BACKUP_CP_INSMOD_RC=7`、`FX3_BACKUP_CP_OWNER_FAILED` | **实测绑定拒绝**。`-7` 是原 module init 返回，`7` 是 BusyBox insmod 进程 RC；不是 host QEMU argv 过长。未见 `FX3_UTIMER_BEGIN` 或 AP 标记。 |

owner receipt 记本轮 2.811 秒、QEMU PID80035 exit0/已回收、双锁已释放；本工人核了 receipt 与命令/串口文件摘要，没有启动 QEMU、取锁或独立见证释放动作。串口没有打印 `kallsyms_lookup_name("pcidma_transfer_async")` 的**运行态返回地址**。原 helper 的地址比较、`aarch64_insn_patch_text` 非空、16B 读回/比对都能走同一 `binding_failure`；故本轮可将“会拒绝”由静态预测提升为**运行态拒绝实测**，但不能把其中某一个失败子条件冒充为已直接读到。

## 工程路线对照

下表的 provider、Backup 格式和历史 FX3 LIRO 资料复用已封存的静态或旧 VM 回执，**不是本轮对 FX6 上层的运行重测**。

| 路线 | 现有事实 | 第一确定冲突及完成条件 |
|---|---|---|
| **A：FX6 原内核及其固件继续在固定 FX3 仿真平台启动**（原目标） | FX6 Image 原字节已运行到上述固定 FX3 CPIO 的 CP helper。原 `firmware-side-contract.json` SHA `e11089388950dbd511416bef26ceb5b30cec0a8dc6d98a3f4495f564eb2049af`：helper 要求 `pcidma_transfer_async` 固定 FX3 VA `0xffffff80083220c8`，而 FX6 Image 链接导出为 `0xffffff8008322f70`；旧 VA 在 FX6 是有效 `watchdog_touch_exception` 代码，两处硬编码 fallback 分别落在 `subsys_new_mm`/watchdog。完整 pcidma 函数另有 5 个不同指令字，补丁 API 也非逐字同体。 | **本次实测 CP helper 绑定拒绝**；当前冻结 helper 与 FX6 内核布局不兼容。保持 helper 守卫不变的固件侧适配需系统性代码布局/导出/跳转/热补丁合同工作，不能只改导出指针或覆盖旧 VA；当前没有安全的最小可用 Image 补丁。即便此门解决，当前客体仍是 FX3 CPIO，尚需 FX6 AP/AV/CP、原分区/Backup 与 Sony MMIO/IRQ/PCI/DMA 逐层接入。 |
| **B：保留 FX3 原内核，移植 FX6 上层电影路径**（仅备选，尚未获准） | 历史 FX3 VM 已到 FX3 AP 入口；两版 LIRO 的 provider 表复制与三槽 ABI 静态相同（`kernel-provider-binding/binding-evidence.json` SHA `e701967407d6a8f543652249c875b4f32fc656c5f04bac04d528a773889193c5`），可复用字段/事件接口研究。固定 CPIO 的 `im.elf` SHA `5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91` 是 FX3 原版，**缺 `/system/av-cam.bin`**；FX6 `im.elf` SHA `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec`、FX6 AV SHA `56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf` 尚未在此客体运行。历史 FX3 LIRO 的四个未解析符号由 `dma330`/`pcieatu`/`icdt` 模块提供，已有 9 模块静态闭包，但加载/硬件初始化未通过。 | **直接替换上层并不可用**：先有 AV 缺件和 LIRO 装载缺符号；若直接带入 FX6 默认 Backup，另有明确结构冲突：固定 FX3 CP helper 要求 CP 银行 `1,369,580` B、819 组/31,197 项，而 FX6 CHAPLIN 默认 CP 记录为 `1,380,885` B、840 组/35,088 项（`backup-state-binding/bk4-receipt.json` SHA `02fba0ed849552074c414fac62c16c688e836d9d5b59d5fa20f8aebdfcb5ae96`）。版本化状态映射、AV/LIRO 装载、真实 look/IP、CP/DMA/像素及机型菜单行为仍须工程化和验证；不能把现有人工 look22/word fixture 称已移植功能。 |

路线 B 如果获准，也只能标为 **FX3 内核上的 FX6 上层混合移植**，不能改称“完整 FX6 固件启动”。两条路线都没有实机、相机、USB/SD、RAW/ISP、电影菜单视觉验收。下一动作取决于用户的路线选择：选 A 才设计受原字节约束的固件侧布局适配，选 B 才制作隔离且可审的混合候选；当前不再重复运行已知 CP 拒绝，也不修改冻结模拟器、helper 或固件原件。

离线复核：在本目录运行 `python3 verify_run.py`，只读原运行、基线、候选、固件与 CPIO；写本目录的 JSON，不启动 QEMU。
