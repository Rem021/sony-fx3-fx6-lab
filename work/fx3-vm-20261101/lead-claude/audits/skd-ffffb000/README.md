# SKD 0xffffb000：AP80c 故障、原厂消费者与最小诚实模型

**结论：故障是 AP 读取 Mira BootROM 中的加密取数垫，不是网络 MAC/序列号读取，也没有证据表明该页是 CP 写入的 SRAM。** `libInfraSKD.so+0x63fc0` 是 `ldrb w0,[x1,x0]`；来源是 `SKData_Init` 对物理 `0xffffb800` 的页对齐映射，故障读为表 9 的第 0 项 `(source=0, offset=0xeb)`，即 `0xffffb8eb`。原机同版 ROM 尚未取得，但已有可核验的公开 Mira ROM：可为 QEMU 提供**明确标为 A7 IV 公开 Mira 参考原件**的只读 4096 字节页；它不是 FX3 同机 ROM 证明，且后续 `0xf340f000` 仍会缺设备。证据：S/W 的 `0x63f98..0x63fe4`、`0x64568..0x646f4`，P 的 `descriptor_table[9]`、`runtime`、`rom_model_candidate`。

本审计只读原件，未启动 QEMU，未执行库/CP/内核代码，未访问相机、ROM、OTP 或物理内存，未生成密钥、签名或修改运行链。只写本目录的 Python、JSON、README；没有新增运行回执。P 的 `scope`、`inputs` 可复核。

## 复跑与文件索引

在 `/Volumes/KAFU2T/AI/Projects/Mac` 运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python \
  work/fx3-vm-20261101/lead-claude/audits/skd-ffffb000/audit_skd_ffffb000.py
```

脚本先核对外盘 UUID，只写同目录 [skd-ffffb000-proof.json](skd-ffffb000-proof.json)，无联网依赖。PASS 表示静态证据重建与断言通过，不能代替运行、加密或 UI 验收。脚本不使用磁盘上受保护的乱码冒充 SKD 运行指令：先对照原 WBI 中的 ELF 头、GNU hash、144 个动态符号记录、1024 字节动态字符串前缀及 SONAME，再按原三级页表取代码；每段保留物理地址、WBI 文件偏移及页表描述符。见 P 的 `wbi_identity`、`skd_blocks.*.provenance`。

本说明使用以下文件缩写，路径均相对 Mac 项目根；完整 SHA256 在 P 的 `inputs`：

| 缩写 | 原件/证据文件 |
|---|---|
| P | 本目录 `skd-ffffb000-proof.json` |
| S | `work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraSKD.so`，SHA256 `7d1fbd9a53794def916ca3ff2fc3a00f295268bb0f4ea7c07d0e8356d2840f9b` |
| W | `work/sony-firmware-20261024/stage2/extraction/nflasha5.img`，原 WBI SHA256 `ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1`；区段表 `work/fx3-color-port-20261027/tail-20261028/wbi2-map-results.json` |
| A | 与 S 同目录的 `appFw.so` |
| O | 与 S 同目录的 `libosal_uipc.so` |
| K | `work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin`，SHA256 `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c` |
| D | `work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/setting/cxd90057.dtb` |
| C | `work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin`，Thumb，基址 `0x108000` |
| R | `work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap80cpanel-5dd371e5/serial.log`；另核对 `runtime/ap80c-review.json`、同次 `command.json` |
| M | `work/sony-firmware-20261024/stage204-public-AP-boot-reference/reference/bootrom/CXD90057_Mira_0xFFFF0000.bin` |

W 中的 S 基址为 `0x7f73ef9000`，页表根物理地址为 `0x40867a000`；R 中 S 的运行基址为 `0x7fb6021000`，A 为 `0x7f62cec000`。它们分别来自离线快照与 AP80c，不能互换运行地址。P 的 `wbi_identity`、`runtime.actual_call_chain_return_addresses` 保留换算证据。

## 谁映射，读什么

S 的导出函数 `SKData_Init` 位于 `+0x64568`，大小 `0x190`。它调用 `sysconf(0x1e)` 取得页大小，原日志确认 `0x1000`；以 `open("/dev/mem",0)` 打开只读 fd，随后三次 `mmap(NULL,page_size,1,1,fd,page_aligned_phys)`，即 `PROT_READ|MAP_SHARED`。`open` 的字符串位于 S/W `+0x206c70`，PLT `+0x627f0` 为 open、`+0x62a50` 为 mmap、`+0x62d50` 为 sysconf。证据：P `skd_blocks.SKData_Init`；R 行 2095–2097 的原有 mmap 观察值。

| 来源 | 请求物理地址 | mmap offset/长度 | 保存的页内偏移 | 消费者 |
|---|---|---|---|---|
| source 0 | `0xffffb800` | `0xffffb000 / 0x1000`，r--s | `0x800`，S 全局 `+0x2ca360/+0x2ca368` | S `+0x63f98`，offset `0..0x3ff` |
| source 1 | `0xf340f000` | `0xf340f000 / 0x1000`，r--s | `0`，全局 `+0x2ca390/+0x2ca398` | 同函数，offset `0..0x1f` |
| 额外 cipher 材料 | `0xf13b8000` | `0xf13b8000 / 0x1000`，r--s | `0`，全局 `+0x2ca378/+0x2ca380` | S `+0x6436c` 读 8 字节、`+0x64378` 再读 4 字节 |

映射和全局写入分别见 S/W `+0x645c4..0x6460c`、`+0x64618..0x6465c`、`+0x64668..0x646b0`，P `source_maps`。这三次映射**不读页内容**；因此 AP80c 启动时返回成功，稍后真正解引用才 external abort，与 R 的原日志一致。

S `+0x63f98` 是**内部无导出名的字节取数函数**，没有可证的原符号或 RTTI 名称；本文仅按用途命名 `read_source_byte`。输入为 4 字节描述符：`u16 source @+0`、`u16 offset @+2`。source0/offset≤1023 从 ROM 取 1 字节；source1/offset≤31 从第二来源取 1 字节；其他描述符返回 0。`+0x63fc0` 精确字节为 `20686038`、指令为 `ldrb w0,[x1,x0]`。见 P `skd_blocks.read_source_byte`。

S `+0x6402c` 是**内部无导出名的取数表装配函数**。表在 `+0x279eb8`，每项 `{descriptor_pointer:u64, entry_count:u64}`，每项 16 字节；P 的 `descriptor_table` 已恢复 0..30 全部项及每个 `(source,offset)`。0..18 按描述符逐字节输出，19..30 每四个来源字节经高低半字节 XOR 组合为一个输出字节；19 项为 `{NULL,0}` 的空项。所有表合起来覆盖 source0 的 1024 个字节与 source1 的 32 个字节。证据：S/W `+0x64050..0x64124`，P `descriptor_source_coverage`。

故障处 LR `S+0x64098` 来自 `+0x64094 bl +0x63f98`；`r4=0`、`r5=32`、`r6=S+0x206ca0`，对上表 9 的第 0 项 `(0,0xeb)`。该表前 16 项来自 ROM，后 16 项来自 source1；本次首读即失败，还未执行后 31 次读取。地址等式为 `mapping_base 0x7fb79b8000 + page_offset 0x800 + descriptor_offset 0xeb = 0x7fb79b88eb`，物理为 `0xffffb8eb`。证据：R 行 23384–23387、P `runtime.fault`、`descriptor_table[9]`、`skd_blocks.descriptor_gather`。

用途可闭合到**AES cipher 的 key/IV 材料装配**：S 的注册回调 `+0x64134` 在 `+0x64214..0x64244` 为 cipher 初始化选择表 9 或 25，再在 `+0x64300..0x64324` 按 key selector 选择另一表。cipher selector0 返回的描述符在 `+0x27b0b0`，首四字段 `(NID427,block16,key32,iv16)`；selector1 在 `+0x27b9b0` 为 `(NID901,block1,key32,iv12)`。NID 与 [OpenSSL 原头文件](https://raw.githubusercontent.com/openssl/openssl/OpenSSL_1_0_2u/crypto/objects/obj_mac.h) 的 AES-256-CBC / AES-256-GCM 一致，消费者也按这些长度调用初始化。见 P `cipher_descriptors`、`skd_blocks.cipher_selector0/1`、`sync_callback`。这证明消费者用途，不等于得到了原机密钥；本审计没有读取第二/第三硬件来源，也没有装配或输出实际密钥。

## 哪个网络 sequence 调用

故障发生在 `sequence_init_access_authentication::run()`，并非 `sequence_get_wifi_mac_address`。A `+0x2bcc0a4` 的进入日志引用原字符串 `+0x392df10`：`virtual void model::sequence_init_access_authentication::run()`；实际栈返回地址落在这段函数的 `+0x2bcc1a0`。证据：P `strings`、`app_blocks.sequence_init_access_authentication_run`、R 的原始 FP 栈。

从内到外的调用链如下，表中每个返回地址都有 R 原栈值和原指令 BL/BLR 相互印证，P `runtime.actual_call_chain_return_addresses` 保存模块换算：

| 原代码调用点 / 返回位置 | 含义 |
|---|---|
| S `+0x63fc0`，LR `+0x64098` | 表 9 取 32 字节，首次 ROM 读取失败 |
| S `+0x64244` → S `+0x6402c`，栈返回 `+0x64248` | cipher 初始化回调装配 key 材料 |
| O `+0x3b18 blr x2`，返回 `+0x3b1c` | `u_osal_snd_sync_msg` 在调用线程内执行注册回调 |
| O `+0x6390`，返回 `+0x6394` | `__osal_snd_sync_msg` → 用户同步消息分发 |
| A `+0x2ea9be4`，返回 `+0x2ea9be8` | 发同步消息 `0x025906be` |
| A 返回 `+0x2ea9d10`、`+0x2ea9de0` | 封装消息 → `SKD_CipherInit`；命令类型 2 |
| A 返回 `+0x2eaa0a4` | `data_encryption` 调用 CipherInit；原错误日志 `Error SKD_CipherInit err=%d` 在 A `+0x399e282` |
| A 返回 `+0x2de2810` | infra wrapper 数据加密 |
| A 返回 `+0x279f050`、`+0x279f15c` | 认证数据对的加密 / 命令 `0x1d39` |
| A 返回 `+0x2bcc1a0` | `sequence_init_access_authentication::run()` |
| A 返回 `+0x2bd76fc`、`+0x2f71ba0` | sequence 队列的外层执行路径；线程名由 R 标识为 SeqQueueNetwork/TID332 |

S `SKData_Init+0x646b4..0x646c8` 注册 `osal_reg_sync_msg_queue_cb(0x025906be, ..., S+0x64134,0)`，与 A 发出的 ID 相同，因而不是另一个 CP sequence。O 的同步回调执行点解释了为什么网络队列线程直接在 S 里崩溃。证据：P `skd_blocks.SKData_Init`、`osal_blocks`、`app_blocks.SKD_send_wrapper`。

## 原机地址含义与来源边界

**BootROM 区域的可证来源。** 已有 M 是作者公开的 CXD90057/Mira AP ROM 原件，物理起始 `0xffff0000`，长度 49152=`0xc000`，终点不含 `0xffffc000`；故 `0xffffb000` 是它最后一个 4 KiB 页。作者原说明把 Mira/CXD90057 明确称为 AP BootROM，并描述可从 `/dev/mem` 读取。固定提交 [原作者说明](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/e85e137fc3b88b7cb26e69faa9f1304184678ff7/bootrom/README.md) 已于本轮联网核对，二进制固定 URL 也重取为 49152 字节，与 M 完全一致。见 P `rom_model_candidate`、`inputs`；源 Git blob SHA1 为 `c7d37785caddd0bc1b5d7ae4dde1a9d66a0c2194`，脚本独立从字节重算并核对现有上游目录。

因此，把本次 source0 判为 **Mira ROM 末端 1 KiB 加密取数垫**有地址、消费者和真实同 SoC 公开 ROM 三项相符证据；上游 `reference/scripts/parse_emmc_boot0.py:44` 也取 `brom[0xb800:0xbc00]` 作为 `scramble_pad`。**FX3 自身 mask-ROM 版本与该 A7 IV 参考字节相等仍未证实**，不能把参考 dump 重命名为 FX3 原机 ROM。第二来源 `0xf340f000` 是否是芯片 ID/eFuse/OTP、第三来源 `0xf13b8000` 的官方寄存器名，均未闭合；本说明只称硬件来源。证据：M、S/W `+0x645c4..0x646b0`、P `unproven`。

**D/内核能证什么。** D 与原厂 GPL `cxd90057.dtsi:78..84` 仅把 `0xff000000..0xffffffff` 覆盖为广域 `iomem2`/`MT_DEVICE_nGnRE`，线性别名起点 `0xffffffffff000000`；其中包含 BootROM 页。D 的 `memreserve` 为空、无 `reserved-memory` 子树，没有名为 `ffffb000` 的独立设备或 RAM。普通 DDR 为 `0x400000000+0x200000000`；ESRAM 为 `0xfe000000+0x1000000`，都不同于故障页。P `device_tree`、`gpl_archive_scan.cxd90057_dtsi_iomap_lines` 保存全部相关属性。

K 未发现 `ffffb000/ffffb800/f340f000/f13b8000` 的 32 位原样小端常量；`ffff0000` 命中属于原始字节搜索，不能自动作物理地址。原厂 GPL 的 576 个有界相关文件搜索未给出这四个地址的细分名字；`AARCH32_VECTORS_BASE=0xffff0000` 是用户虚拟向量宏，不能借此把物理 ROM 叫向量页。eFuse reset 位的存在也不能定位 source1。K `mmap_mem` 为 `0xffffff80082f8228`，`phys_mem_access_prot` 为 `0xffffff8008096910`，P 保留原指令；R 行 2095–2097 已直接证明 mmap 可以成功而实际总线读取失败。没有真机 `/proc/iomem` 回执，不声称取得了其资源名称。证据：P `kernel_blocks`、`kernel_literal_search`、`gpl_archive_scan`。

126 个原厂 `.ko` 逐个校验既有 manifest SHA 后扫描：唯一 `ffffb000` 命中是 `wlan.ko` 文件偏移 `0x37f8af` 的**非对齐 `.data` 四字节重叠**，不是已定位的设备描述或访问代码；没有 `ffffb800/f340f000/f13b8000` 原样常量命中。P `kernel_module_scan` 保存包括负结果在内的逐模块记录和该重叠上下文字节。只查原样常量不能排除分步构造地址，未将负结果写成全代码无访问证明。

**CP 是否写入。** C 中 `ffffb000` 原样常量 0 命中、`ffffb800` 三个命中全非四字节对齐，位于数据表的字节重叠；不是 CP 写页的证据。另对前 `0xa00000` 字节按 Thumb 搜 `b800/47ff/f340/f13b` 立即数构造候选，结果及随后 24 字节都进入 P `cp_search`；`movw #0xb800` 的可读代码候选实际配的是 `movt #0xb` 等其他地址，未闭合到该 ROM。**未发现 CP writer，不声称已经排除间接/其他别名写入**；已有正向证据是 AP BootROM 原件和 AP 的只读取数函数，并无必须等待 CP 填 SRAM 的链。见 P `cp_search`、S/W `+0x63f98`、M。

**固件分区有无默认页。** 原 WBI 的保存区段没有物理 `ffffb000/f340f000/f13b8000` 页，脚本拒绝将未保存区补零。对已提取的 `nflasha3/5/7/8/15.img` 搜索 M 的这 4096 字节，没有逐字匹配；未找到可证明属于 FX3 的该页镜像或默认内容。这不排除其他 ROM 版本、压缩/加密或未提取成员。P `wbi_physical_page_availability`、`partition_exact_public_page_search` 给出范围、哈希和限制。

## 不合法值、失败处理与 UI 关系

S `+0x63f98..0x63fe4` 只检查**来源编号与偏移范围**，不检查读出的 byte 是 `00`、`ff` 或其他值；`+0x6407c..0x640a0` 只按描述符数量装配并返回 1。没有已证明的“空白 ROM / 未配置芯片 → 非致命缺省”分支。给 QEMU 填零/全 FF 会作为成功 key/IV 材料进入 cipher，不能声称是诚实未配置状态。P `skd_blocks.read_source_byte/descriptor_gather`。

S 的硬件映射失败有不同路径：`+0x645ec/0x64640/0x64690` 检测 `MAP_FAILED` 后跳 `+0x646cc`，关闭 fd 后返回，不再执行 `+0x646c8` 的回调注册；不是 abort。第一次映射失败时 `+0x2ca360` 仍为零；前面已增加的 refcount 不回退，前两次成功/后次失败也没有在此统一 munmap。故降级需要以新进程、精确缺失设备规则验证，不能宣称可热重试。P `skd_blocks.SKData_Init/SKData_Exit`。

A 同步发送返回非零时，`+0x2ea9bec` 保留错误并直接返回；若回调把请求首字段清零，`+0x2ea9c3c` 返回 `-1018`。`data_encryption+0x2eaa0a4` 检查 CipherInit 结果，失败时输出 `Error SKD_CipherInit err=%d`，将 result `+0x10` 置 2 后正常返回。**这个 API 错误路径是非致命的；总线 SIGBUS 不会走它。** `auth_encrypt_pair+0x279f04c` 返回后没有检查 result.status，而是继续第二组处理；外层 sequence 继续后续参数更新并在 `+0x2bcc544` 正常 ret。P `app_blocks` 保存各分支与返回指令。

对 UI 的结论限于两层：AP80c 的实际同步 external abort 已导致 im 进程消失，影响所有 UI/菜单，不能只隔离成网络不可用；但“正常 API 错误返回后该 sequence 的可见功能、后续认证状态和菜单是否仍正常”没有本轮运行证据。当前 sequence 也含有其余字符串长度断言，不能由一个无直接 abort 的分支推出全部 UI 完全安全。原 R 已记录启动屏障与 UI future 越过；故本故障是后续独立存活问题，不是那道启动屏障仍未完成。证据：R/`runtime/ap80c-review.json` 的 `fault`、`im_alive_at_end_verified`、`boot_notify_and_future_return_serial`，P `app_blocks.sequence_init_access_authentication_run`。

UIPC `-1021` 风暴在故障后出现与时序一致，但本审计没有证明“这页内容错误引起 UIPC -1021”的独立因果机制，也没有修改 UIPC 返回码。证据：R 行 23334 起；未证实范围见 P `unproven`。

## 最小方案排序与精确字节

1. **优先：有来源的只读参考 ROM 页，作为有界硬件模型。** 在 QEMU 物理 `0xffffb000` 新增严格 4096 字节只读 ROM region，内容只取 M 文件 `[0xb000:0xc000]`，不覆盖 `0xffffc000`。P `rom_model_candidate.exact_contents_hex` 含全部 8192 个 hex 字符，可离线直接恢复字节；长度、SHA、Git blob、固定 URL 均已钉住。该页足以让本次首个 ROM 读取有真实来源的返回值，**不能保证整个网络初始化通过**；表9第17次读 `0xf340f016` 会继续遇到未建模硬件，其他 cipher 也可能读 `0xf13b8000`。运行 marker 应明确 `reference_rom=public_mira`、`fx3_same_revision_verified=0`，无需伪造身份、eFuse 或“未配置”值。
2. **次选：明确硬件不可用，让原错误路径返回。** 不提供假页；只对已匹配 `/dev/mem` 的这一个精确请求 `(offset=0xffffb000,len=0x1000,prot=1,flags=1)` 返回 `MAP_FAILED` / `ENODEV`，避免创建稍后必 fault 的映射，交回 S 的原厂初始化失败路径。所需内容 **0 字节**、映射大小 **0**。静态链证实 A 对 API 错误不直接 abort；“缺注册同步队列的确切返回值是否立即返回、refcount、未来重试、UI实际存活”仍需 Lead 单独运行回执。它表示 SKD 硬件服务不可用，不表示加密成功。P `alternatives[0]` 记录限制。
3. **完整保真模型后续项。** 只有取得同版 Mira ROM 和 `f340f000/f13b8000` 的文档化语义及可证原件，才扩展其他区域；不复制其他相机 OTP/身份，不以当前调试 ROM 页等价 FX3 本机。当前额外字节和完整模型均未闭合，P `alternatives[1]`。

拒绝零页/全 FF/随机页、广域 MMIO 成功兜底、强制 CipherInit 成功或返回伪造签名：原取数代码没有空白值特殊处理，无法证明这些内容进入非致命“未配置”分支。P `alternatives[2]`。

参考页精确合同：

| 项目 | 值 |
|---|---|
| 物理基址 / 大小 / 权限 | `0xffffb000 / 0x1000 / readonly` |
| 来源切片 | `M[0xb000:0xc000]` |
| 原 ROM 大小 / SHA256 | `49152` / `f93eaef410a47ec65f3487cd1edf63e1982df77163f3461206118ba5d6ee3fc3` |
| 页 SHA256 | `f2bcb4103c039ef6fdc258fd4abc08487f4c7c70e568034da9f04261c78651a2` |
| 本次首读字节 | 页 `+0x8eb` = `0x16`，原文件 `+0xb8eb` |
| 全部内容 | P `rom_model_candidate.exact_contents_hex`；不另造 .bin 交付物 |
| 来源身份 | A7 IV 公开 CXD90057/Mira 参考 BootROM；FX3 同版未证实 |

本审计交付完成：脚本可重建证据、来源可追、未知项已列出；候选 region 的集成、后续缺设备、API 降级和 UI/菜单验收均留给持有运行链的 Lead。P 的 PASS 仅表示审计完成。
