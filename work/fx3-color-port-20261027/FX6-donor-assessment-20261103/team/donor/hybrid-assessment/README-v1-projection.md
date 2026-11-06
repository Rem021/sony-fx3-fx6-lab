# FX3 内核 + FX6 上层：首阶段离线可行性评估

2026-11-03。**结果：动态装载入口存在可实施的软件侧差分，但还没有可运行的混合候选，更没有“完整 FX6 固件启动”。** 固定 FX3 QEMU、Image、完整 DTB、CPIO、Backup 与 helper 均只读保留。本轮没有运行 QEMU、AP、AV、CP 或设备。

## 可复现回执和范围

在项目根执行 `python3 work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/hybrid-assessment/preflight.py`。脚本拒绝固定来源 SHA 不符，解析 ARM64 ELF `PT_DYNAMIC` 的 `DT_NEEDED`、强/弱未定义符号、GNU version need/def，并递归追 FX6 `bootin.elf`、`im.elf`、`appFw.so`、`libmpr.so` 的静态动态库闭包。结果是 [preflight-receipt.json](preflight-receipt.json)（SHA `0380fd97043bdf818f4eec9edd20d3e04a7d4005ce4a863b8127a2ceebc86194`），声明性载荷次序是 [migration-manifest.json](migration-manifest.json)（SHA `08b008ca5ecb2c13f8a1236d1517c6df505ca3f6ccbcef01d5476c1ac0692a4c`）。脚本 SHA `e8ca6e8462a38fe30bde05f60dce2b9556f2cb7b1f06c8d8d4bbee8f928a84fe`；27 个 FX6 ELF 节点全部可在供体中找到直接依赖，FX3 投影目录中引用的 21 个库与冻结 CPIO 审计逐文件 SHA 一致，**不表示在 FX3 客体动态装载成功**。提取目录失去部分 SONAME 符号链接，`libc.so.6` 等采用明示的 `2.25` 实体别名；脚本标记 `alias_suffix_or_missing`，真实客体路径仍须确认。

固定根是 FX3 Image SHA `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`、冻结 baseline JSON SHA `854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669`、原 guest CPIO SHA `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d`。供体 `im.elf` SHA `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec`、AV SHA `56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf`、LIRO SHA `8a7cfcaef07ad18ca2a97847d44d31bb9152f57c0fcbccd96056ad683649f2e1`、CP SHA `60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668`。均由本轮脚本复核。

## 入口与确定的首个软件差分

| 边 | 本轮原字节/ELF 结果 | 工程结论 |
| --- | --- | --- |
| ELF 解释器 | FX6 `bootin`/`im` 的 `PT_INTERP` 为 `/lib/ld-linux-aarch64.so.1`；固定 CPIO 审计（SHA `cc0b3c5b1925aa4bb0cb14aab275f2831833c7378490ca5408789f3824eb4847`）含同路径符号链接和 `ld-2.25.so` 实体。FX3 loader SHA `90b4fe734ba7faa08d4591b1363bff478e7bde399a821fc0b2d021c062a58a9a`，FX6 loader SHA `8eeed290e0992ef3717e61450831a3b1e25e9bff11e5062204cc0dc96a617a75`。 | 固定客体能满足解释器**路径**；实体字节不同，不能称 loader ABI 或初始化成功。首阶段沿用 FX3 loader，先取得真正装载回执。 |
| FX6 `bootin.elf` → `im.elf` | 原 `bootin.elf` 文件 `0x399a` 有 `/usr/bin/im.elf`；两版入口各自 SHA 不同，但各自 `DT_NEEDED` 集及强导入名称集相同。FX6 `bootin` 10 个、`im` 15 个直接依赖；其强导入在现有 FX3 同名/别名直接库导出中全部有名称匹配，要求的 GNU 版本定义也有匹配。 | **仅通过名称/版本预检**。FX3 `libbackup`、`libosal`、glibc、C++ 等可作为首阶段候选后端，二进制不同及语义尚未通过。不能从静态匹配推断进程、IPC 或 Backup 成功。 |
| FX6 IM 动态装载 | FX6 IM 文件 `0x7df6`（ELF VA `0x407df6`）含 `fn=/system/av-cam.bin load=1 debug=1`，`0x7e2e`（VA `0x407e2e`）含 `/usr/lib/libObj.so`。已封存的原指令审计（`provider-binding/README.md` 第 23 行）确定 `0x406178–0x4061d8` 构造前者装载命令，`0x405f5c` 有后者 `dlopen` 路径。 | 固定 CPIO **缺 AV**，没有 FX6/FX3 ORIL 成功装载回执；因此只放 FX6 IM 不能宣布 AP 初始化成功。FX6 供体提取目录没有 `libObj.so`，现有 FX3 guest 有它（SHA `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae`），可保留作后端，但未证明 FX6 IM 与它的运行时 ABI。 |
| FX6 AP 候选 `appFw.so` | `DT_NEEDED` 直接包含 `libopus.so.0`、`libSoundTouch.so.1`，固定 FX3 guest 均无；供体对应实体 SHA `635d7031f820ae2cdd60513636abda4cc1ed4c325c1eccbc4f61e9e375cc94f9` / `b9d8be287efcfafd7c385150e0bb578935f0ffc92f4e66443efcc24e7c515a20`。FX6 appFw 的强导入有 586 项不在其**直接** `DT_NEEDED` 的 FX3 导出并集，属潜在全局注册/插件依赖，不能直接判全部缺失。 | **若进入 appFw 装载阶段，直接仅替换 appFw 必然少两项声明依赖。** 软件侧做法是按 FX6 SONAME 连同两库及其递归依赖构造隔离载荷，再单独审计全局符号解析和初始化顺序；不改 FX3 内核/设备。当前 `appFw` 是否由此 IM 自然装载仍未闭合。 |
| 资源 | FX6 `appFw.so` 文件 `0x22458cd`/`0x22458dd` 含 `/usr/share/app/` 与 `/usr/share/app/area_check_data.dat`，`0x2245918` 含 `global.xdb`。两文件 FX6 SHA `b73de11722ba2c48625f1c99f4ddf3bab088144cf8ed60b629fa29afeed9f7a2` / `577461fc6bfd968e0cb84ec374aa4c76f621349532cac41f8f74736792c74871`，与固定 FX3 版本均不同（见 JSON）。 | AP 资源必须按引用逐件版本化适配；字符串路径仅证明引用候选，不证明曾被打开、渲染或菜单可用。 |

## 机型、Backup、IPC 与首个运行阻断

`backup-state-binding/bk4-receipt.json` SHA `02fba0ed849552074c414fac62c16c688e836d9d5b59d5fa20f8aebdfcb5ae96` 校验 FX6 `MainDest.txt`（SHA `51bc347fed1435a0afb93b4e694722aceea809751bd7748482432650bebd98f2`）选择 `SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin`；FX6 CHAPLIN 第二 CP 记录 1,380,885 B、840 个 subsystem/35,088 项，现有 FX3 CP helper 合同要求 1,369,580 B、819/31,197。**不能整包覆盖 FX3 Backup**。两版原 `Backup_nread`/`Data_SearchId(0x02ae0000)` 已有固定源码和 CPU 回执；该 ID 的默认值是 1 B `00`，自然运行值及写入者未观测。保持 FX3 Backup 驱动和数据，未来只对确认的字段做版本受限映射，读返回状态/长度与真实字节后才能放行消费者。

`kernel-provider-binding/binding-evidence.json` SHA `e701967407d6a8f543652249c875b4f32fc656c5f04bac04d528a773889193c5` 证明两版 LIRO 的 provider 表复制及 `+0x3c0/+0x3e8/+0x4c0` 静态 ABI 对应；FX3 本地 `osal_uipc`/Backup 可作为接口研究起点。历史 FX3 TRY2 的 LIRO 装载实际遇四个未解析导入 `dma330_mem_transfer_async`、`pciatu_unmap`、`pciatu_map`、`interchip_transfer_async`；旧 `liro-closure.json` SHA `e2c617cdd786c3536eeaca8090ac59b8367abf2e98af8281fa82b9dfbb5cf7a6` 给出九模块静态闭包，不能把内核导出匹配视为硬件/MMIO/IRQ 可用。FX6 AV 的自然 look/IP、MAIN/monitor、CP/DMA/RAW/ISP 仍无运行态证据。独立 FX6 Image 在固定 FX3 helper 下的绑定拒绝另见旧 `decision-brief/verification.json` SHA `df0b21965146518aabb1d1e8bf54ca82ebeb74c7d1ce837c91b7a486530e3a7d`；这不是本混合路线的新运行结果。

## 有界实施建议与停止点

1. **首个隔离软件差分，仅预备、不执行：** 在冻结 FX3 平台及原 CPIO 的派生载荷中，候选只替换 `bootin.elf`/`im.elf`，保留 FX3 kernel、DTB、环境、`libObj`、Backup 和 helper。先逐件验证动态链接路径、符号版本及启动入口，第一故障规则是任一 ELF 装载/版本错误或 IM 到 AV/`libObj` 的真实调用失败即停。现有 CPIO 无 AV，因此此阶段最多说明 FX6 IM 到达某个调用点，不得报 AP/电影功能通过。此次只生成 [migration-manifest.json](migration-manifest.json)，没有构建或运行该载荷。
2. **下一软件载荷差分：** 在上述真实首故障确认后，按 FX6 `appFw` 直接 `DT_NEEDED` 带入 `libopus`、`libSoundTouch`，核对全局导出/插件注册，再逐件对照 `area_check_data.dat`、`global.xdb`。必须留住 FX3 本地驱动/Backup，用受限适配层转换已证字段；不携 FX6 CP 或覆盖 Backup。此阶段即使动态装载成功，也不代表菜单、AV 或视频链可用。
3. **更后阶段：** 先让 FX3 本地 LIRO 四导入闭包及 AV 基线有真实装载回执，再分别评估 FX6 AV provider 绑定与电影消费者；要抓实际 `Backup_nread` 状态/1B、队列包字段及首个 MAIN/monitor 下游。无原码/运行态绑定时停在首个未知点，不用人工 look22 或 synthetic 状态冒充自然路径。

本轮验收层级为**静态原字节与离线解析**。没有生成混合 QEMU 候选，没有执行 `bootin`/`im`/`appFw`，也没有实机或像素/色彩结果。首个确定的软件阻断是后续 AP 直接依赖库缺件；首个实际运行故障仍要由独占 runtime owner 在获准的隔离候选中按上列停止规则捕获，不能从本回执臆定。
