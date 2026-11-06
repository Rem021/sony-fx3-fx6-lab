# FX6 AP 三项软件差分候选：静态构建与独立审计

**结论（2026-11-03）：** [guest-three-entry.cpio](guest-three-entry.cpio) 已构建，SHA256 `bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02`，总长仍为 453,184,500 字节；仅相对固定 FX3 客体替换 FX6 `bootin.elf`、`im.elf`、`appFw.so` 三个内容。本轮**没有启动 QEMU，未证明 FX6 AP 装载、符号解析、IPC 或菜单运行**。文件只用于后续现有 runtime owner 的受控、只读装载观察，不能视为完整 FX6 固件。

## 固定输入与再现

- 原两入口 CPIO：`../hybrid-entry-candidate/guest-two-entry.cpio`，SHA `ff2f927de24b801d334ce9111fb486fb2af85d24c509ab20c43eda0a69ffdc40`，453,184,500 字节。
- 原 FX6 AP：`../nflasha15-files/lib/appFw.so`，SHA `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`，50,520,424 字节；原 FX3 AP 是 79,015,712 字节、SHA `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`。
- 完整固定 FX3 `guest.cpio` SHA `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d`；固定平台 JSON SHA `854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669`。完整绝对路径、QEMU/kernel/DTB/Backup 的哈希在 [receipt.json](receipt.json) 和 [manifest.json](manifest.json)。外盘 UUID 核验为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。
- 首次生成执行 `python3 -B build.py`；已生成时脚本拒绝覆盖，直接执行 `python3 -B verify.py` 重算独立回执。验证器自行解析三份完整 CPIO、旧 ELF 身份基线和固定 DTB，并用系统 `bsdtar -tf` 二次核对 1,140 个名称及顺序；清单在 [bsdtar-list.txt](bsdtar-list.txt)。不调用旧候选的构建/验证器。

## 精确字节边界

新归档逐条核对 1,140 个成员，除 `usr/lib/appFw.so` 外，**所有 member 的 110 字节 header、名称/对齐、payload 和权限都与两入口源一致**；AP header 仅 `c_filesize` 八个十六进制字符改变，payload 与固定供体逐字节相同。AP 原 header/file offset 为 62,762,896／62,763,024，大小由 79,015,712 改为 50,520,424 字节。之后 741 个记录的偏移随之减少 28,495,288 字节，首个是 `usr/lib/dataflowInfraFramework.so`；`TRAILER!!!` 结束于 424,689,212 字节，后面严格零填充 28,495,288 字节。原归档没有尾部额外字节。`/init`、17 个预载、FX3 `libObj`、Backup、FX3 AP 以外所有库/模块/链接的内容、头、顺序与权限均经上述全员比较保留。没有增加 FX6 AV/CP。

完整 FX3 CPIO 对比只出现三项内容变化，精确旧/新 SHA 见 [manifest.json](manifest.json)；任何额外成员差异都使验证器失败。**旧 38 成员、20 ELF 的 `fx3-original-app-loader-probe.cpio` 身份门实际上不含 `appFw.so`，所以它自身仅拒绝 `bootin.elf`、`im.elf` 两项**；它不是覆盖 AP 的全域身份门。后续放行须保留旧门全部其他判断，并另以完整 FX3 CPIO 对 `appFw.so` 做独立的第三项精确 SHA/长度检查。不能把旧门全局关闭，也不能把“旧门只报两项”误当 AP 已验。

## 格式与固定 DTB

既有两入口运行 serial SHA `caecd00446ad09840606d63d199978683787ebf0fe276476ffac12e36f41a23c` 的第 2 行显示运行内核 **4.9.337-scel+**。与其主版本匹配的 Linux [v4.9 initramfs 格式](https://raw.githubusercontent.com/torvalds/linux/v4.9/Documentation/early-userspace/buffer-format.txt) 明确 `initramfs := ("\\0" | cpio_archive | cpio_gzip_archive)*`，并允许任意零字节填充；[v4.9 `init/initramfs.c`](https://raw.githubusercontent.com/torvalds/linux/v4.9/init/initramfs.c) 的 `do_reset` 消耗零字节，`unpack_to_rootfs` 分支跳过零字节。**这是上游 v4.9 格式/源码依据，不是 Sony 修改版逐指令验证，更不是新归档启动回执。**

冻结完整 DTB SHA `b6f9f4c04d0da101565d67244629a0ad7a3954c8af004f353c16ae0c8b499de7` 的 `/chosen/linux,initrd-start=0x440000000`、`linux,initrd-end=0x45b030bf4`，范围正好 453,184,500 字节；固定 loader 地址也是 `0x440000000`。新归档总长相同，因此静态上无需改 DTB 或 initrd-end。固定 FX3 kernel、QEMU、机型和环境同样未改。

## 后续唯一装载观察合同

由现有 runtime owner 在排队窗口执行一次**无按键、无人工 IPC** 的 host-only 观察，保持 FX3 平台、原 `/init`、17 helpers、Backup 与所有功能保护原字及哈希不变。用上述三项旧/新 SHA 白名单加旧门其余原有拒绝条件核候选，逐次记录 loader verify/list/BusyBox 三类**全部**返回值；任一后续非零也立即归类真实失败。四个已由固定 FX6 AP 字节及客体同字节 helper 反汇编支撑的精确 FX3 诊断行见 [guard-disassembly.md](guard-disassembly.md)，只有这些完整单行可列为“旧观察器未绑定”，不能宽泛忽略 `FAIL`/`REJECT`。功能性 SKD/CAPID 保护和任何真实 loader/进程/IPC 失败仍须首故障停止。新目录存日志，不覆盖旧 serial；结束按现有 API16 恢复、只回收自身进程并确认双锁释放。本报告不提供启动命令，也不放行运行。

[preload-audit.json](preload-audit.json) 逐项固定 17 个实际预载客体 SHA、同字节本地 SO、可定位源码及功能/绑定风险；五条涉及 AP 固定 RVA 的读写边有 [反汇编范围](asm-index.json)。[classify_serial.py](classify_serial.py) 是**只读宿主日志组件**，从旧 runner 的健康监视器固定 SHA 提取全部原失败规则，并额外约束四条完整诊断文本；`python3 -B classify_serial.py` 的 19 个 fixture 包括“先 0 后 -7”、同一行 0/-7、混合错误、未知 guard 和原有硬件/媒体/帧失败。它不启动或控制 VM。具体排队、首故障和撤销要求见 [observation-contract.json](observation-contract.json)。

协调审阅后新增独立 [run_ap_once.py](run_ap_once.py)，父运行器 SHA `3bdc9121ac331a947fc157fc5aa1455a531140a0d2700dd1fed77f9db1f37a5e`，本版 SHA `aaa9ca518d580fde7ca9fdbf2c33bebe78545d96876f997168643f33bdf4a24a`，[精确差分](runner-diff.patch)。其预检在旧 20-ELF 门维持两项原例外，另外逐成员比较完整 FX3 CPIO，只放行 `bootin/im/AP` 三项固定 SHA/长度；实测无 VM 预检为 `1140` 成员、旧门拒绝 `2`、完整三项例外和其余 `1137` 成员相等。宿主观察限原双锁、原相对 QMP socket、零键、120 秒观察／180 秒含收尾；结束只报实际故障、精确旧诊断或 bounded unknown，**不再用 `FX3_BOOT_QUEUE_SEND` 或 `FX3_APP_INIT` 认定 FX6 AP 成功**。[host-tests.json](host-tests.json) 的 8 组无 QEMU 测试覆盖候选错 SHA 拒绝、后续及同行非零 loader RC、无换行故障尾部、API16 恢复成功/失败时自身进程收尾与保护未放行；假 QMP/进程仅用于测试，没有运行真实固件。该 runner 尚未执行，须唯一 runtime owner 完成最后审查并排队。

**当前冻结客体不能保证获得 IM 调用 `dlopen` 前的实时 flags/目标、同一时点 `libObj`/`libmpr` 全局 link-map、`dlsym` 返回或 AP 入口执行。** 已有 GPE 装载标记是条件发出；某个 post-`dlopen` guard 行最多证明该 helper 收到了非空 handle。通用 FX3 boot queue 标记不代表 FX6 AP IPC。若下次仅得三 loader RC 与 guard 拒绝，它仍是有效初次装载边界，后续实时字段需另审一个独立、只读、逐字节门控的 guest 观察探针；本轮没有制作或注入探针，没有复制旧运行器来伪称可见字段。

47 个立即重定位符号虽有 FX3 同名候选，但 AP `dlopen` 时 link-map/ABI 尚未验证；182 个无现有候选的延迟调用与 15 个仅 FX6 `libmpr` 候选仍开放。即使 loader 三 RC 为 0 或出现 FX3 菜单，也不等于 FX6 AP/系统运行，更不证明电影控制、RAW/ISP 或实机功能。
