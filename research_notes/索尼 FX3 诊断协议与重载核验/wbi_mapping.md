# FX3 7.02 WBI 内核接口与重载语义

## 官方快照能否证明 image_dev 和 image_drop 接口真实存在？

### Takeaway
本轮把证据从裸字符串提升到真实内核属性结构、show/store 函数及调用链：FX3 官方 7.02 的 WBI2 快照中有 `image_dev`、`image_mode`、`image_drop` 的可读写实现。它支持适配现有 WBI 接口的研究方向，但不是用户机身当前 sysfs 状态或实际调用成功证明。[静态审计](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)

### Cited Findings
- 分析原件是官方 `nflasha5.img`，209112512字节，SHA256 `ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1`。镜像内 Linux 标识为 `4.9.337-scel+`，构建日期为2025-12-25；这属于发布包保存内容，不是本机 `uname` 结果。[原始命中与上下文](../../work/sony-firmware-20261024/stage9-protocol/wbi/wbi-image-observations.json)、[来源收据](../../work/sony-firmware-20261024/stage9-protocol/wbi/source-receipt.json)
- 自写只读解析器识别1399条64字节 section 记录；已存储长度总和精确等于头部 `0xc717000`，其中82条记录为0存储字节、原长度非0、flag1，其他记录 stored size等于original size且flag0。没有把这项结构一致性说成所有厂商校验和已验证。旧公开 fwtool 的 WBI1/32位 parser 不直接支持该 WBI2/64位布局，本轮未导入或执行它。[可复现脚本](../../work/sony-firmware-20261024/stage9-protocol/wbi/audit_wbi.py)、[section映射](../../work/sony-firmware-20261024/stage9-protocol/wbi/wbi2-section-map.json)、[固定公开参考收据](../../work/sony-firmware-20261024/stage9-protocol/wbi/parser-reference-receipt.json)
- ARM64 Image头位于快照文件 `0x15200`，section将其映射到物理 `0x400080000`；从属性指针及函数指令对应可确定这里的内核 Image VA 起点为 `0xffffff8008080000`。下述“Image偏移”均减去此VA起点，不能把它当快照文件偏移或可覆盖地址。[原始section及属性字节](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)、[三种坐标对应](../../work/sony-firmware-20261024/stage9-protocol/wbi/source-receipt.json)
- `image_dev` 名称在快照文件 `0x542018`，内核VA `0xffffff80085ace18`；其属性结构位于文件 `0x5f3620`，含0644权限、show VA `0xffffff80080e3818`、store VA `0xffffff80080e3928`。`image_mode`、`image_drop` 和 `image_mem` 也有同型结构及独立处理函数。[属性原始32字节及入口指令](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)
- `image_dev` show确实遍历 backend链表，取节点+0x10的名称，以 `%s%s\n` 格式输出；比较当前选中节点后，选中项前缀为 `*`，未选中项为空格。官方快照另保存唯一 `wbi4` 名称及周边回调对象，但本轮没有把保存的选中节点模块VA映射到该名字，因此**尚不能断言输出必为 `*wbi4\n`**。[show原始指令及格式字符串](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)、[可读反汇编](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-handler-disassembly.txt)

### Inferences
- 已有真实接口、模式与backend选择语义，不能再把FX3的WBI sysfs说成“只有别机源码、FX3完全未知”。未闭合的是当前机身状态和选定 backend，而不是这些处理器是否编译存在。[属性与show/store证据](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)

### Gaps
- 未读取用户FX3的 `/sys/power/*`、内核日志或选中backend；官方快照保存 `image_mode` 全局值2，不代表用户这台当前值也是2。保存的选中节点指针为模块VA，未继续追模块虚拟映射；`wbi4` 名字存在不足以补全这一关系。[保存状态及证据层级](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)

## drop 与 mode0 的顺序及持久影响能否在 FX3 原字节中解释？

### Takeaway
可以：FX3 的 `image_drop` 路径先判断模式、backend及缓冲区；若 `image_mode` 已为0就跳过底层drop，仍可返回成功。可执行到的drop分支经选定backend写入512字节全零头并打印 `dropped wbi`；这与libsencore固定写nflasha5并可写`invl`的路径应分列，尚未证明两者选中同一实际介质范围。[drop原字节与完整调用片段](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)

### Cited Findings
- `image_drop` store VA `0xffffff80080e3e28`（Image偏移 `0x63e28`，快照文件 `0x79028`）要求非空输入且首字节为ASCII `1`，调用 VA `0xffffff80080e3dc0`（Image `0x63dc0`，文件 `0x78fc0`）。wrapper读取mode全局，mode为0或backend/缓冲指针为空时跳过drop；通过时调用 VA `0xffffff80080e3ce8`（Image `0x63ce8`，文件 `0x78ee8`）。[入口、wrapper与backend函数指令](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)、[坐标收据](../../work/sony-firmware-20261024/stage9-protocol/wbi/source-receipt.json)
- 底层函数先经backend+0x40可选回调，准备512字节零缓冲，再经backend+0x48回调发送 `(backend, buffer, 0, 1)`；成功后引用并打印 `dropped wbi`，再调用可选的backend+0x58收尾。尚未追完这些驱动回调到分区和扇区映射，故这里标记为“选定backend的一个头部扇区失效路径”，不称全盘、NOR或boot0写入。[调用寄存器、常量与日志字符串](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)
- `image_mode` store VA `0xffffff80080e3150`（Image `0x63150`，文件 `0x78350`）解析首字符0–3并更新mode内存全局；在此store函数里没有持久文件写入调用。它会影响之后wrapper的分支，不能因“只改内存”就说整套重载无持久影响。[mode处理器字节](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)
- A7CR维护者文档记录的Image偏移 `0x63e28→0x63dc0→0x63ce8`、`0x63150` 与本轮FX3实际代码坐标吻合，且说明先drop再mode0。这只是对公开机制的交叉核对，不是A7CR实测可以替代FX3实测。[维护者原文](https://github.com/lzh2016zzz/a7cr-fl23-research#4-invalidating-the-old-boot-snapshot-existing-interfaces-and-functions)、[本轮FX3独立原字节](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-handler-disassembly.txt)
- 另一条既有FX3 `libsencore` VA `0x118ac` 路径直接打开 `/dev/nflasha5` 并写512字节，条件分支可写`invl`；它既不是本轮内核sysfs store入口，也未证明由auth.stop调用。[既有原厂库路径](../索尼%20FX3%20独立诊断与恢复入口/firmware.md)、[既有原字节](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)

### Inferences
- 对FX3而言，“先mode0再drop”可能形成表面返回成功、实际未失效的情况，顺序约束已获本机型静态语义支持。即便顺序正确，仍需backend、错误返回、真实介质读回与随后运行版本的证据；单条日志不足以证明冷启动已加载新程序。[FX3 wrapper与drop语义](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)

### Gaps
- 尚未把内核选定backend映射到nflasha5、WBI2头部或其他实际分区范围；不能推导sysfs零头drop与libsencore的`invl`写入必然等价。没有执行任何sysfs写入、WBI失效、重启或断电实验。[执行边界收据](../../work/sony-firmware-20261024/stage9-protocol/wbi/source-receipt.json)

## 这是否补齐独立恢复和冷启动救砖证明？

### Takeaway
没有。新增证据解释了运行中内核如何失效选定快照，不能证明BootROM/loader如何选择有效/无效WBI，也不能证明主应用或usr损坏后仍可建立USB服务。[本轮范围](../../work/sony-firmware-20261024/stage9-protocol/wbi/source-receipt.json)

### Cited Findings
- 既有磁盘启动脚本 `init→pivot_root→init2` 与非零MODE、`/setting/sen/smode=UU` 条件式Senser路径仍是静态磁盘控制流。WBI快照恢复是否重走这些脚本、外部能否在故障时满足条件，均未在本轮闭合。[前轮磁盘路径证据](../索尼%20FX3%20独立诊断与恢复入口/firmware.md)
- 本轮仅对官方保存镜像进行mmap只读解析、字符串/数据指针核对及Capstone静态反汇编，没有固件仿真、相机枚举、文件读取、认证、驱动变更或原生模块执行；全部输出为本地研究文件。[可复现分析脚本](../../work/sony-firmware-20261024/stage9-protocol/wbi/audit_wbi.py)、[来源与操作收据](../../work/sony-firmware-20261024/stage9-protocol/wbi/source-receipt.json)

### Inferences
- 接下来最小缺失的运行时观察是：经审计的已授权通道返回当前mode、完整backend列表及选中标志，并与该机固件/原件绑定；它可区分“接口存在但当前backend不符”和“现成WBI guard适用”两种情况。上述观察尚未授权或执行，不能以“继续研究”视为可直接采集。[属性与状态边界](../../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json)

### Gaps
- 冷启动loader的WBI选择、无效头部处理、磁盘回退与失效后服务入口仍无证明；不因本轮接口实现闭合而放行固件写入或承诺救砖。[本轮来源与限制](../../work/sony-firmware-20261024/stage9-protocol/wbi/source-receipt.json)
