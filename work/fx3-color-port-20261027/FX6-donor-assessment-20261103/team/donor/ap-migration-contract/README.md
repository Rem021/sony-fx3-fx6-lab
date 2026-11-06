# FX6 `appFw.so` 在固定 FX3 客体上的装载合同

2026-11-03。结论：**可以设计只更换软件载荷的 FX6 AP 候选，不需改变 FX3 模拟器、内核、完整 DTB、原 `/init` 或功能性 SKD/CAPID 保护；现在还不能把该候选放行为“AP 可运行”。** 已闭合原 IM→IMDB 记录→`dlopen`→`dlsym`→`Application_System_Init` 的静态边，也找到 AP 装载前的 47 个立即重定位符号条件。原 FX3 两入口无键运行给出了继承预载与 FX3 `libObj` 装载的实例，但没有加载 FX6 AP，`libmpr` 在 AP 装载前是否进入全局作用域仍缺同一时点的证据。本轮未构建 AP CPIO、未启动 QEMU、未改原件。

运行 `python3 -B analyze.py` 重算 [receipt.json](receipt.json)。脚本固定实际 1,140 成员 FX3 CPIO SHA256 `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d`、先前逐符号版本回执 SHA `96742cf3ba840bd5f76d37dd76364371b2f150167e0f367de8396940f1c5c647`、两入口审计回执 SHA `29319c645a435fb8e5606b8bbccea6fd710a0fb77f5f559da99d4ad4267fd603`。完整原件 SHA、17 个预载的顺序与 SHA、557 项逐符号候选、原指令 VA→文件偏移和重定位类型均在机器可读回执中；沿用固定 ELF 解析器并核其 SHA。供体 IM `87d672bd...` 的 `PT_LOAD` 与 FX3 IM 完全一致（两入口审计），所以此入口运行没有新增 IM 装载代码。

## 原入口与实际客体记录

| 原字节来源 | 精确位置和数据流 | 静态结论 |
| --- | --- | --- |
| FX6 `libIMDB.so` SHA `a088ef30...` | `imdb_raw+0x100+151×0x48`：VA `0x213e8`／文件 `0x113e8`；记录字 `0x20000004, 1, 0xffffff9f, 0x83`，`+0x10→0xc6a7`=`appFw.so`，`+0x18→0xc6b0`=`Application_System_Init`，`+0x38/+0x40` 指向 `AdjChkConfig.so`／`AppConfig.so`。 | 原供体有 AP 装载记录和入口名，不是字符串孤证。配置选择依赖运行状态位 `0x4000`，自然请求未观测。 |
| **实际固定 CPIO** `/simulation/libIMDB.so` SHA `d475e9f4...` | `/init` `LD_LIBRARY_PATH=/simulation:/usr/lib:/lib` 首选它；其 `imdb_raw` 记录索引 143，VA `0x1f670`／文件 `0xf670`，类型／ID／两个配置名与供体记录相同。 | 当前 FX3 客体没有装入 FX6 `libIMDB`；但实际库也有相同 AP 名与 ID，支持软件侧换 AP 的入口设计。表序号不同，不能用供体地址读实际客体。 |
| FX6 原 `im.elf` SHA `87d672bd...` | VA／文件 `0x406274/0x6274` 检测类型 `0x20000004`，`0x406284/0x6284` 调 `0x405e24`；后者 `0x405e3c` 读记录 `+0x10` 路径，`0x405ea4` 读 flags，`0x405eac` 调 `dlopen@plt`，`0x405f0c` 调 `dlsym@plt` 取记录 `+0x18`，`0x405f44` 间接调用返回函数。FX6 AP SHA `a1c58b69...` 动态导出 `Application_System_Init` VA／文件 `0xc0b044`。 | 入口调用边闭合到原字节；不代表执行成功或请求 ID `0x83` 曾自然选中。 |
| 同一 IM 的 flags 字 | 初始 VA `0x41973c`／文件 `0x973c`=`0x101`；VA `0x4057b4–0x4057b8` 是写入该字的函数。 | 按 glibc 常量，初始值为 `RTLD_LAZY | RTLD_GLOBAL`；运行值可变。此边调用 `dlopen`，未调用 `dlmopen`，依常规 glibc 语义进入调用者的 link-map namespace，实际 namespace 与 flags 仍需同次观测。 |

`0x101` 的常量及 `dlopen`／`dlmopen` 作用域解释见 [glibc `bits/dlfcn.h`](https://codebrowser.dev/glibc/glibc/bits/dlfcn.h.html) 与 [Linux `dlopen(3)`](https://man7.org/linux/man-pages/man3/dlopen.3.html)。这些是接口定义；本报告没有执行固定客体的 glibc 链接器。FX6 `bootin.elf` VA／文件 `0x402ed8/0x2ed8` 对 bit 6 分支，`0x402ee4/0x2ee4` 可调用 `unsetenv("LD_PRELOAD")`，其参数字符串在 `0x403a08/0x3a08`；故仅凭 `/init` 不能保证预载传入 IM。

## 真实 CPIO 导出顺序与 FX6 AP 的强导入

按原 `/init` 第 288 行的 17 项预载、原 IM `DT_NEEDED` 广度优先次序、`/simulation:/usr/lib:/lib` 的实际符号链接构造**候选全局顺序**；实际 link-map 的精确优先级要由同次运行确认。FX6 AP 根有 900 个强导入、9 个弱导入；既有本地 AP `DT_NEEDED`＋预载的逐项版本审计给 343 个静态提供者、557 个无版本全局待定。弱导入独立列在回执，允许无定义，不视为九项强失败。新脚本对 557 项按顺序给出每个可见导出者的强／弱属性和原 AP 重定位类型：

| 557 项中互斥类别 | 符号数 | 解释 |
| --- | ---: | --- |
| IM 初始全局闭包有同名候选 | 69 | 本次固定命令 IM maps 确认 17 预载继承，但仅证明这些库映射；按同一进程／全局可见规则可作为静态候选，不是已解析地址或 ABI 通过。 |
| 需 FX3 `libObj.so` 先以全局方式进入作用域 | 213 | 其中 45 个有 `.rela.dyn` 立即重定位；实际 FX3 运行先有 `FX3_GPE_LOAD ... flags=0x101` 再有 FX3 AP guard 绑定，仍不能直接移用 FX6 AP 调用约定。 |
| 需固定 FX3 `libmpr.so` 先全局装载 | 78 | **其中两个是 `.rela.dyn` `R_AARCH64_GLOB_DAT` 立即条件**：`_ZN4sidb7referer7s_countE`、`_ZN4sidb6entity7s_countE`。实际客体库 SHA `9aeef3b9...` 导出同名；尚无它在 AP `dlopen` 前的明确时间点。 |
| 仅在另带 FX6 `libmpr.so` 时有候选 | 15 | 固定 FX3 `libmpr` 无这些导出；新增该库还要单独评估与 FX3 后端的 ABI，不作为默认修复。 |
| 已检查的全局范围仍无候选 | 182 | 均为 `.rela.plt` `R_AARCH64_JUMP_SLOT`。在初始 `RTLD_LAZY` 且无强制 NOW 的条件下可延迟到调用点；不能称为已解析，也不能据此断言 `dlopen` 必然失败。后续插件／`dlsym`／前置动态库状态仍未知。 |

47 个有 `.rela.dyn` 的**不同强符号**全有现存 FX3 库同名候选：45 属 `libObj`，2 属 `libmpr`。其中 `libObj` 41 个不同符号被 `R_AARCH64_ABS64` 引用共 1,752 次、另有 4 个 `GLOB_DAT`；这比单纯看 557 名称更具体。在全部 557 项中，FX3 `libObj` 有 2 项、FX3 `libmpr` 有 8 项只有弱导出候选，回执逐项标识；弱导出的存在不能直接升格为绑定成功。旧口径按 FX6 `libmpr` 比对，本轮改用**实际 FX3 `libmpr`** 重新归类；两套条件分组不可混用。名称、版本和同名导出仍不证明 C++ 类布局、对象生命周期或 ioctl/IPC 语义。

## 17 预载的保护与诊断边界

| 项 | 固定源码／原字 | 对下一 AP 候选的影响 |
| --- | --- | --- |
| `fx3-skd-hw-unavailable-v1.so`，首项功能保护 | 固定源码 SHA `2d0a30d5...` 第 5–12 行要求环境、调用者 `/usr/lib/libInfraSKD.so+0x645ec`、`/dev/mem` 偏移 `0xffffb000` 等全部命中才返回 `ENODEV`，其他调用透传 `mmap`。 | 不能删保护或将 FX6 硬件请求一律成功；FX6 AP 是否触发相同原调用尚未知。 |
| `fx3-capid-v1.so`，第二项功能性 IPC 后端 | 实际为 v49-touch100，源码 SHA `8d65d690...` 第 40–42 行通过 `dlsym(RTLD_NEXT)` 取六个 OSAL 函数，缺项 `_exit(126)`；第 604–705 行按目的、消息大小、原字请求处理 FX3 profile 或透传，某些未知/非法请求会返回 `-1024`／`-1021`。 | 不能用全返回 0 stub。下一阶段要在自然 FX6 AP 首次 `osal_snd_msg` 记录 dst、type、长度、来源、返回，再按实际协议决定是否增加受限软件适配。 |
| `fx3-preset-context-v2-screen.so`，第 5 项 FX3 观察器 | 实体是 v6-save102；源码 SHA `32bb3b5a...` 第 43–47 行在 `dlopen(appFw.so)` 后先验 48 字。FX3 **48/48**，FX6 **0/48**；首点 VA `0x2dca610`，预期 `0xa9bb7bfd`，FX6 文件 `0x2dba610`=`0x255`。不匹配打印 `FX3_PRESET_CONTEXT_BIND_REJECT` 后返回，`dlopen` handle 仍返调用者。 | 条件性**诊断绑定拒绝**，不等于 AP `dlopen` 失败；原 host monitor 会把该标记当错误早停。保留原字守卫，未来版本化 FX6 只读观察点需重新证明指令与回退合同。 |
| `fx3-ui-gate-v1.so`，第 13 项 FX3 观察器 | 实体是 v11；源码 SHA `bb665076...` 第 104–114 行先验 60 字。FX3 **60/60**，FX6 **2/60**；首点 VA／文件 `0x16f2220`，预期 `0xd10cc3ff`，FX6 为 `0xf9400bf3`。不匹配打印 `FX3_UI_GATE_BIND_FAIL` 后返回；保留后续自测与受限 RAM 模型。 | 条件性诊断观察缺席，不证明 FX6 UI 失败；不得套 FX3 PC、关闭守卫或改动功能性保护。 |

这次实际两入口运行的固定 [runtime receipt.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/fx6-entry-no-key-20261103/runs/fx6entry-a39715a8/receipt.json) SHA `426bd282...`、serial SHA `caecd004...` 已在脚本逐字节检验：32.38 秒、loader 三 RC 均 0、无按键、原 IM 映射与 17 预载映射（serial 行 1921–2186）、`/simulation/libIMDB.so` 映射、FX3 `libObj` 装载标记行 2336、FX3 两观察器绑定行 8720／8760、首个 FX3 AP 调用行 10735 和原 FX3 AP IPC 发送行 11350。该 run 的 FX3 `libmpr` 只在后续堆栈中首见（行 11195）；不能据此证明它先于 AP `dlopen`。AP 与 `libObj` 均仍是 FX3 原件，当前回执只收窄相同输入下的**前置装载方式**，不证明 FX6 AP、菜单、像素或色彩功能。API16 已恢复、双锁空闲的判断引用原 runtime 回执，本轮未再次运行。

## 最小后续实现合同

1. **先读一次自然时间点。** 在未来获得授权的唯一 runtime owner 观察窗口，保留当前固定平台、原 `/init`、Backup、17 预载与功能性保护；记录 IM 调用 `dlopen(appFw.so)` 前的 link-map 顺序、`libObj`／`libmpr` 是否已全局装载、flags 实值、目标路径与实际解析到的 `Application_System_Init`。本轮 FX3 AP 回执不能填 FX6 AP 项。若 `libmpr` 不在先，两个 `GLOB_DAT` 是首个明确的软件侧装载阻断；只能用有原调用证据的加载次序／导出适配修复，不补全返回 0 符号。
2. **再造隔离软件候选。** 若上述条件闭合，可在新、审计的 CPIO 中仅替换真正 FX6 `appFw.so` 和明确必需的用户态库／资源；保持原 `/init`、FX3 kernel/QEMU/DTB/Backup/硬件参数与功能性 helper 的 SHA。AP 长度不同，需另审 CPIO member、归档总长与 DTB `initrd-end` 约束；旧全 FX3 ELF 身份门应以精确文件哈希允许清单扩展，其他失败规则保留。本轮没有制作这个包。
3. **把诊断拒绝与真正故障分列。** 现有 48／60 guard 必拒绝 FX6 原字，旧 runner 将前者当故障早停。后续隔离 host 观察器必须记录这两个预期诊断并继续保留所有 loader／保护／进程真实失败停止点；若需要等价观察功能，另以 FX6 原指令构建并验证版本专用观察器。当前代码、原 helper 和 runner 不改。
4. **首个真实 AP 故障即止。** 记录 glibc 首个未解析符号或 `dlsym` 失败及自然 AP 首条 IPC 的原字、来源、返回；182 项当前无候选只在真实调用前保持未知。加载成功仍不等于 ABI、菜单或 RAW/ISP 完成。

判定层级：供体原字节、CPIO 静态闭包与既有 FX3 AP VM 历史回执；**无本轮 VM、无 FX6 AP 运行、无设备/相机验证**。
