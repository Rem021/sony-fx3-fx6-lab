# A7C II 原生加载／文件恢复／WBI机制向经典 FX3 7.02 的适配评估

## 1. 能否在二进制和加载 ABI 层面证明可移植性？

### Takeaway
可以具体评估为“原生 worker 框架值得做 FX3 专用适配”，理由已超过同系列或同 CPU：FX3 有真实的标准 `dlopen(path,1)` 路径，而固定上游的两个实际 worker 是没有外部符号依赖、带 `DT_INIT` 的 AArch64 共享 ELF。它仍只证明加载模型相容的必要条件，未证明 worker 在 FX3 上获准加载、取得权限或安全执行。[FX3 原始加载分支](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)

### Cited Findings
- 上游固定为 QAQLeonard `b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d`，本轮取得源文件和实际 `installer.so`、`wbi.so`，逐个记录固定 URL、大小和 SHA256；不是以当前浮动 main 推论。[来源收据](../../work/sony-firmware-20261024/stage8-adaptation/device/upstream-source-receipt.json)、[固定树索引](../../work/sony-firmware-20261024/stage8-adaptation/device/upstream-tree-receipt.json)
- 实际 `installer.so` 为56,864字节，SHA `68c19f096f42381a0dcdc9d7b0029452164bf43fe5eaeb89ec889d9f058df206`；`wbi.so` 为17,608字节，SHA `8d73d55bf89a8400b1c00130b514405d850553536f222fca0eb3959eb0a0be25`。两者均为 ELF64、小端、`EM_AARCH64`、`ET_DYN`，没有解释器、`DT_NEEDED`、未定义动态导入或 GNU symbol-version 依赖。installer 仅见类型1027的相对重定位；WBI没有重定位项。`DT_INIT` 分别为 `0x12ee4`、`0x10318`，恰与其导出 `_init` 一致。[实际 ELF 静态审计](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)
- 两个 worker 源码均用寄存器 x0–x5、x8 和 `svc 0` 直接进入 Linux syscall，不调用 Sony 私有 C++ API 或 libc 导入。因而“payload 缺少某个 Sony 符号”或“payload 需要另一版 GLIBC 导入”不是这两个现成 ELF 当前显示的障碍；CPU/kernel syscall 和权限语义仍须另证。[installer.c 固定原文](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/installer.c)、[wbi.c 固定原文](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/wbi.c)
- FX3 7.02 原 `libJiritsu.so` SHA 为 `bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9`，也是 ELF64 小端 AArch64。既有五个函数的每条原始指令字节本轮重新核验一致，包括 `adj_cmd_set_file_path @0x89b4`、`adj_cmd_set_file2 @0x9528`；补充读取 `adj_cmd_get_file2 @0x9e74` 与 `cmd_file_delete @0x8c78`。这是实际 FX3 二进制，不是 A7C II 地址照搬。[本轮逐指令及来源复核](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)
- FX3 的精确 `libJit.so` 特殊分支在原文件写入并 fsync/close 后，调用未定义导入的标准 `dlopen(path,1)`，然后 dlclose；导入版本来自 `libdl.so.2: GLIBC_2.17`。它检查 `/tmp/jbusy` 等前提，不能简化成任何文件都可加载或没有上游 gate。[本轮函数原字节](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)、[既有加载版本及参数映射回执](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)

### Inferences
- 无外部导入、使用标准 ELF 初始化入口，显著降低了私有 C++ ABI 对接成本；适配可以从一个极小、FX3绑定的原生 worker 开始，而非把整个相机固件移植过来。`dlopen→DT_INIT` 的模型相容不等同于已在 FX3 加载成功。[两侧 ELF 对照](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)
- 直接 syscall 同样是 ABI 依赖：仍需要匹配 FX3 的 AArch64 Linux syscall 编号、结构布局、内核支持、文件系统语义及执行上下文权限。没有动态导入不能消除这些约束。[上游显式 Stat ABI 和 syscall 使用](../../work/sony-firmware-20261024/stage8-adaptation/device/packet-binding-and-worker-facts.json)

### Gaps
- 没有 FX3 服务认证、实际模块上传、加载或 worker 执行证据；未证运行时符号插桩、额外安全检查、sandbox 或特权状态。
- 源码对128字节 AArch64 Linux `stat` 的静态断言，只验证其编译布局，未与 FX3 kernel 返回布局做运行验收。
- 没有 A7C II 原厂 `libJiritsu.so` 的逐字节比较；这里只把固定上游 host/worker 约定与真实 FX3 接收实现对应，不声称两机原厂库 ABI 全同。

## 2. 文件备份／恢复和 WBI 哪些可复用，哪些不能原样迁移？

### Takeaway
可复用的是受限临时文件通道、请求／结果协议和经过哈希与读回验证的局部恢复框架。现成 installer 内含 A7C II 的目标身份；WBI worker 还锁定 A7C II 的 sysfs 状态，不能把它们直接用于 FX3。[实际 payload 与来源](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)

### Cited Findings
- 固定上游 host 在 service packet `0x40` 内发送 little-endian `(0x1001, cmd)`，只允许15/16/17/18四个 Jiritsu 命令；选路径发送 `00 + ASCII路径 + 00`，读发送 `00 ff 00`，写发送 `00 ff 00 + data`，删除发送 `00 ff`。host 将路径限制在 `/tmp/jiritsu/` 并检查返回的4字节状态。[transport.py L404–424](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L404)、[固定行及哈希收据](../../work/sony-firmware-20261024/stage8-adaptation/device/upstream-source-receipt.json)
- FX3 原 `adj_cmd_set_file2` 对 `00 ff 00` 的已解释分支是 Work 挂载、已选路径、原始文件写入；精确 libJit 路径另外进入上述加载分支。`adj_cmd_get_file2` 与删除／选路径函数确实存在，并有本轮原字节回执。**本轮尚未把全部外层命令15–18的FX3分派编号逐一闭合**，不能把相应 Python method 名称当作完整协议兼容测试。[FX3 参数解释](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)、[新增实际函数指令](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)
- installer 的原生操作对象固定为 `/usr/lib/appFw.so` 与 `/cp/cpapp-b.bin`；它要求 euid0、原挂载状态、原文件类型/大小/哈希及窗口字节，重挂载 usr 后以原 inode 原位写入，并对错误尝试反向恢复。FX3 的原 fstab 与已提取文件具有相同逻辑路径，usr也来自 `/dev/nflasha15` 的 ext2；这支持文件层框架复用，未验证当前机身实际挂载权限。[固定 installer.c](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/installer.c)、[FX3挂载及原字节对照](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)
- 实际 installer.so 在文件偏移2840嵌有 A7C II 原AP SHA `2ea02f7ecbc5bb917316fe8ef4ce5ffd87eb66efaae78ba2ce11420552df539b`，与 FX3 原AP SHA `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` 不符。旧的跨机型审计也已报告整文件及多处窗口前置字节不匹配。现成二进制不能作为 FX3 安装/还原器。[实际二进制内嵌哈希位置](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)、[旧跨机型否决结果](../../work/sony-firmware-20261024/stage2/write-audit/fx3-vs-a7c2-compatibility.json)
- 上游 `runtime.c` 固定六个 A7C II AP 偏移，且对高于 `0x51a7718` 的区域另加 `0x10000` 映射修正。这是具体固件布局假设，不能把“只读 probe”误认为无需适配的通用程序。[固定 runtime.c](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/runtime.c)、[行事实收据](../../work/sony-firmware-20261024/stage8-adaptation/device/packet-binding-and-worker-facts.json)
- WBI worker 要求 request magic `A7WBI001`、16字节请求、mode0或1、euid0；其 Report 编译断言为192字节。运行前置条件硬编码 `image_mode == "2\n"` 与 `image_dev == "*wbi4\n"`。mode0仍会创建结果文件、初始化时 unlink `/tmp/jiritsu/libJit.so`；mode1则向 `image_drop` 写1、向 `image_mode` 写0，核对读回及新鲜 `dropped wbi` 日志。[固定 wbi.c](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/wbi.c)、[固定行和ABI收据](../../work/sony-firmware-20261024/stage8-adaptation/device/packet-binding-and-worker-facts.json)
- FX3 的官方 nflasha5 是 WBI2 镜像；原 core另有一个显式 packet 分支直接向 `/dev/nflasha5` 写512字节，并可写 `invl`。该事实并没有证明 FX3 的 sysfs `image_dev` 是 `*wbi4`，也没有证明上游 worker 的 sysfs流程与这个原厂分支等价。[先前已核验的 WBI／服务边界](../索尼%20FX3%20独立诊断与恢复入口/firmware.md)、[原厂WBI调用字节](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)

### Inferences
- 可以移植“备份绑定该机身→目标整文件/窗口校验→原位修改→完整读回→同一目标的原字节恢复”的原则；必须重做 FX3 的 manifest、窗口、大小、哈希、模型与权限门禁。现成 A7C II 回退窗口只会恢复 A7C II 字节，不是 FX3 备份。[installer的具体边界](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/installer.c)
- WBI方案可复用“先读取实际状态、限定厂商接口、写后核对”的设计，但不能删除或猜改 `*wbi4` guard 来追求通过，更不能未经验证改用 nflasha5 原始写入替代。[上游 WBI guard](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/wbi.c)

### Gaps
- 未取得用户FX3运行时的 sysfs 状态，未证 `image_drop` 支持、权限、日志行为和冷启动结果。
- 未验证 FX3 的服务 packet 外层路由、结果状态布局及所有读/删命令的协议对应；本地函数存在不等于 host 请求已验收。
- 局部原位回滚要求存储与进程仍可用。它不是断电原子事务，也没有证明设备失去服务后可重新获得入口。

## 3. 最小 FX3 专用重建是什么，安全写入仍卡在哪里？

### Takeaway
现实可行的下一项工程是“FX3专用、先读后验证的原生适配器”，不是直接跑现成 A7C II installer。最小改动应收敛到模型绑定、协议封装、原始文件 manifest、请求/结果 ABI 和 WBI状态门禁；在独立恢复入口和运行时前提未证前，不能开放持久写入。[已证平台层与未证层](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)

### Cited Findings
- 需要重新生成 FX3 的 AP/CP 文件尺寸与原始哈希、每个允许窗口的 before/after、预期最终哈希；重建与该 manifest 相绑定的 installer。相同文件路径和原位写逻辑可保留，A7C II 的颜色补丁或AP映射地址不能保留。[实际installer绑定证据](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)、[runtime布局假设](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/runtime.c)
- 需要为FX3明确请求/结果尺寸、版本、端序与目标身份；直接 syscall worker 的128字节 stat、文件类型、euid、mount/read/pread/pwrite/fsync 返回检查必须在FX3验收。现有 worker 无 imports 可减少重新链接工作，不会免除这些布局与语义检查。[worker源事实](../../work/sony-firmware-20261024/stage8-adaptation/device/packet-binding-and-worker-facts.json)
- 上游 host当前仍以普通PID `0x0e8a` 等待返回，并在 service会话中认证、读取备份身份；这些是A7C II host政策，不是设备端worker自动提供的FX3身份保障。它也不能由当前仅有普通MSC信息推导出FX3服务权限。[固定transport.py L350–396](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py#L350)
- 本轮没有原生/Unicorn执行、相机枚举/认证、模块上传、机身文件访问或WBI操作。下载的上游参考源码及二进制仅在本任务临时目录作静态解析；固定URL、SHA、ELF元数据和聚焦事实保留，原始参考文件按任务要求移除。[执行边界与ABI收据](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)、[清理回执](../../work/sony-firmware-20261024/stage8-adaptation/device/reference-cleanup.json)

### Inferences
- “能构建FX3专用原生payload”属于有具体ABI依据的工程可行判断；“能安全安装功能补丁”还要有补丁逻辑、原字节、完整读回和失败恢复的实际证据；“能救砖”更要求主应用失败时仍独立可达的服务/启动入口。这三层不能互相替代。[服务入口已知边界](../索尼%20FX3%20独立诊断与恢复入口/firmware.md)
- 可先设计严格限定只读结果的FX3诊断worker，验证最小加载、syscall和结果ABI，再逐级决定后续；这是下一步方案，本轮未构建或执行它。[静态审计脚本](../../work/sony-firmware-20261024/stage8-adaptation/device/audit_device.py)

### Gaps
- 当前安全写入的阻碍是：FX3特定补丁/回退manifest尚无、服务认证及模块执行未验收、运行时权限与WBI状态未证、故障后独立入口未证。它们不能靠改PID或移除哈希/guard绕过。
- 本轮ABI结论不证明1080p30 HEVC硬件编码可用，也没有产生任何可刷固件或安装包。
