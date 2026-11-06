# 成功案例优先：A7C II 原菜单路径对 FX3 的直接复用

## 已经成功运行原厂菜单的案例是什么

### Takeaway

本轮以真正有原 AP 界面、菜单、输入与像素证据的 `chocotan/a7c2-qemu` 为首要参照，刷新 main 后仍为 `b3d7c1fed349f1d918acc4259f1d2b3a7c52a500`，不重复下载上一轮完整35文件，也没有先研究空仓库。它运行 Sony ILCE-7CM2 2.01 ALLLANG 原 Linux/AP 程序，辅以明确的软件协议与显示模型；原菜单进展不能转写为 FX3 已成功，也不能把黑取景/未成片略去。[固定项目](https://github.com/chocotan/a7c2-qemu/tree/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500)、[10月31日进展](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/2026-10-31-current-progress.md)

### Cited Findings

- 成功范围：原 bootin/im 启动、原首设、640×480 AP OSD、菜单与若干原输入消费；原 AP 软件绘图产出的帧被模型按租期复制，显示桥独立消费；取景仍黑、尚无原AP保存并独立解码通过的JPG/MP4，物理ASIC/原CP RTOS兼容未验。[动态进展](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/2026-10-31-current-progress.md)、[显示链](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/05-display.md)
- 这条成功路线使用 `qemu-system-aarch64` 和原内核；UIPC 底座是原 `devno.ko→osal_utm.ko→osal_uipc.ko`，并非拿 qemu-user 的伪 ioctl 绕开初始化。另有显式 `args.transport_errors` 实验时使用不同 ko，该可选分支不应该混入正常路线。[源码L1129–1135](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1129)
- `menu-observe.c` 解析真实 OSAL 分配、发送、接收、释放和队列注册函数；这份观察器没有直接定义 open/ioctl 或 osal_initipc 的替代实现。其主要适配在协议消息、GOT/PLT、原软件图形服务边界，不能据此把原UIPC init/mmap异常按成功返回覆盖。[constructor与原函数解析L733起](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L733)
- 原 `bootin.elf 'target=qemu ' dmode=3` 是自然启动入口；直接启动 `im.elf target=qemu` 只作为受控对照。IMDB/服务过滤、软件GPE/LZ77/CP服务是派生策略，不是完整无修改硬件仿真。[原AP启动](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/04-app-and-first-setup.md)、[资产准备](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-assets.py)

### Inferences

- 当前最直接的可复用成果是已经跑通原菜单所需的原模块、初始化、消息/图形模型代码，逐层与FX3原件校准；无需先找到“完整硅片数字孪生”才能推进菜单。
- 原内核能打印、原模块能注册、原UIPC实际请求、原程序建屏、软件绘图、像素提交、显示、按键消费分别有不同证据，不能互抵。用户要求的菜单验收至少要到原菜单实际画面和操作变化。

### Gaps

- 维护者原始运行日志/用户固件不在公开源码；本研究分支只做源码取证，没有借维护者成功冒充本机运行。Mac/FX3实际运行由唯一 host agent保存证据。
- 本轮泛检索没有新增更近FX3、A7 IV可下载的“原菜单已跑通”实现；A7IV硬件启动/服务改机不等于虚拟机菜单。没有为列名录而重新收集上一轮已确认空库/未启动项目。

## UIPC与UDIF前提怎样从成功源码精确复用

### Takeaway

第一条可直接行动的成功序列是：initramfs先挂 devtmpfs，挂 proc/sysfs及用户运行目录，原devno→UTM→UIPC，无手工UIPC mknod，再推进真实定时器、Backup/DMM/电源/日期。`echo set > /proc/udm/drivers` 在成功源码中有明确条件与位置；不能仅因默认源码没写它就认定FX3不需要，也不能把它宣称为所有A7C II成功菜单的必需步骤。[setup源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1113)、[initramfs源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-menu-initramfs.sh#L36)

### Cited Findings

| 源码顺序 | 固定位置与具体实现 | 迁移条件 |
|---|---|---|
| initramfs入口 | `prepare-menu-initramfs.sh`：挂devtmpfs到/dev，原busybox shell连接ttyAMA0；未手工创建uipc节点 | FX3仍用原模块/devtmpfs节点，major/minor从FX3原devno核定。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-menu-initramfs.sh#L36) |
| 基础setup | qemu-menu-probe.py L1113–1121：proc、sysfs、tmpfs /tmp /setting /tmp_wbshd、PATH/LD_LIBRARY_PATH；cpuset cgroup命名组与CPU/mems | 单核guest各组先填0；不能只建普通目录冒充cgroup。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1113) |
| IPC | L1130–1131：`/kmod/devno.ko`→`/usr/kmod/osal_utm.ko`→`/usr/kmod/osal_uipc.ko`→`ls /dev/uipc` | 不以mknod存在代替模块初始化/原mmap/原ioctl成功。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1129) |
| DMA330（后续） | L1133–1135：原initrc drv1早于LDEC/LIRO，参数`phy_inst_area=0x4102E4000` | 该物理地址是A7C2实例，FX3须独立核。只有到真实消费者需要时再加。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1133) |
| UDIF set | L1170–1189：只在MENU_EXTRA_MODULES非空时`echo set`，先记录`UPM_DRIVER_SET_RC`；额外模块实际延到L1208才加载 | start-menu.py自然基线L226–233不设EXTRA_MODULES；仅可选imaging/PNG分支L251/L266设safe。不能为FX3凭空删/加此条件。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1170)、[profile](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/start-menu.py#L226) |
| utimer | L1190–1191原模块 | 需要真正推进的counter/比较/IRQ；不能让原驱动读0或全1就认为成功。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1190) |
| Backup | L1192–1200：已核seed到/setting/Backup.bin，`Backup_load=1 Backup_save=0`，随后stream/stream2 | 官方同机型seed；save仅显式opt-in。原启动记录由原Backup API读写并验证。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1192) |
| DMM/日志 | L1201–1205：setting种子，`osal_ulogio.ko ulogio_initfile=...`，`dmm.ko DmmConfig=...`，grm_ma | 日志配置、DMM映射与内存域必须用FX3原件，不能复用A7C2地址。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1201) |
| 电源/时钟 | L1242–1246：upm→udate→seed-date-clock，只有原API设置且读回advance才出DATE_CLOCK_INIT_OK | 不能只touch ready；seed-date-clock读原默认epoch并走原udate API。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1242)、[helper](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/seed-date-clock.c) |

原远端发送器有另一层独立前提：A7C2 `menu-observe.c` L448–467记录，目的SID bits28..30为非零时不进普通kernel callback表，而走单个内核 `osal_reg_public` sender；原 `pcie-if.ko`可注册它。用户态同名API只写本地BSS，不能满足内核分支。成功软件方案在实际发送者的GOT提供特定协议服务，或加载真正 `libInfraAvbbc.so` 原初始化入口；缺sender的 `No snd_msg registered` 不能靠用户态注册补上。[sender源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L448)

历史陷阱：observer L6602附近有一段已#if0的post-init对象walk，注释记过“icount下 init-time UIPC ioctl abort 与二进制大小变化相关”。这是相关性线索，不是已证明的根因或可以随意改ioctl的依据。[原注释](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L6597)

### Inferences

- FX3当前原cdev_ioctl的-1020/-1021必须先绑定到具体op/init16/mmap/队列SID/注册状态；不能把所有负返回都归因UDIF set或笼统“硬件未ready”。最先闭合原映射/初始化，再决定是否到缺远端服务的下一层。
- 三原模块装载顺序可先用于无set的对照包；原AP操作成功仍要实测。不写set本身不是“成功原AP启动”的保证。
- A7C2不以手工mknod补UIPC，更不截获open/ioctl制造成功；这为FX3原模块路径提供具体可证伪参照。

### Gaps

- FX3原UIPC opcode、映射长度、major/minor以及内核分支实测由 original-uipc 与唯一 host 负责；这里只列成功案例的可核源，不能借用其他会话动态结果。
- 未找到公开A7C2完整原驱动初始化日志里每一个ioctl的序列，不能以代码脚本补成运行日志。

## 可直接复用哪些模型源码与跨编译条件

### Takeaway

最小可复用组件已经固定取到本轮 `success-cases/source/runtime/analysis/` 并逐文件匹配Git blob。首先解决原定时器与原guest ABI，再以协议与像素合同移植软件GPE/LZ77/OSD/输入桥；不要把整个668KB、依赖大量A7C2偏移和模型的observer直接塞进FX3。[构建脚本](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/build-observers.sh)

### Cited Findings

- 定时器原参考已重取：`source/qemu-sony-native.patch` 30215B，SHA256 `29a84ae7a23897af25279f3c438bef387a01d59137767e0362631d4c294f78f8`，L389–546为完整 `hw/timer/sony_hwtimer.c`（GPL-2.0-or-later）。它使用4MHz基准，period=`250ns << (control&7)`；control `0x1000`启用、`0x100`中断、`0x30`模式；MMIO偏移0/4/8/12/16分别为控制、复位/IRQ清除写、比较、计数读、计数写。[patch](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/source/qemu-sony-native.patch#L389)
- 该模型四设备MMIO `0xf1042000+i*0x1000`，GIC输入200+i；GICD/GICC与UART别名也在同patch。FX3必须独立检查SPI/INTID、频率和原驱动访问，不能把同一CXD90057注释当作数值恒同证明。WBI专用SPAcc及F0000000 catch-all读全1不应被为timer而顺手移入。[模型装配](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/source/qemu-sony-native.patch#L44)
- 原guest跨编译成功条件：`clang --target=aarch64-linux-gnu -fuse-ld=lld -nostdlib -O2 -mno-outline-atomics -Wl,--no-undefined`，显式链接该guest自己的libc/libdl/libpthread/ld2.25；helper自定义_start→__libc_start_main，指定 `/lib/ld-linux-aarch64.so.1`。Sony库helper另用`--no-as-needed`及`--allow-shlib-undefined`；不是用宿主Darwin头或新libc替掉原库。[build-observers L12–15及helper命令](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/build-observers.sh#L12)
- Zig `aarch64-linux-gnu.2.25` 在维护者macOS移植说明中是未验证建议，不是该项目已经实测成功的工具链；本机若采用，应先无头最小helper对原ld加载、再到原OSAL API，实际运行分别验收。[跨平台说明](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/PORTING-WIN-MAC.md)

| 源文件 | 已成功案例中的作用 | FX3需要重核 |
|---|---|---|
| sony-lz77.c/.h | 严格资源解码，精确输出字节，短读/越界拒绝 | 原资源格式与调用ABI。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/sony-lz77.c) |
| gpe-raster.c、gpe-sprite.c | 有界Fill/Copy、显式RGBA4444/A8/source-over/nearest | 原GPE参数块/格式/stride与callback生命周期。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/gpe-raster.c) |
| headless-osd.c/.h | hosd_claim、capture_frame、step/worker；真实租期内复制，完整提交后才ACK | libObj对象偏移、LIRO queue/消息长度、像素与锁API。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/headless-osd.c) |
| ramfb-viewer.c | HOSDAP02→XRGB8888→保留scanout→fw_cfg ramfb | 原/派生内存域、地址与格式，需独立QMP像素证据。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/ramfb-viewer.c) |
| inject-key.c | 原OSAL分配/设置source/发送/失败释放；App32与Infra20 | FX3队列及raw→UIBIZ表，短按press/release与拨轮不同，不以返回0当画面已消费。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/inject-key.c) |
| seed-date-clock.c | 原udate API读默认时钟、初始化、再次读回并验证实际计时推进 | FX3原udate消息合同与定时器；不能直接touch ready。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/seed-date-clock.c) |
| seed-power-on.c | 原Backup API读取启动记录、显式虚拟loader状态、写后逐word核验 | FX3记录号及结构；默认Backup_save=0仅VM内存。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/seed-power-on.c) |
| prepare-assets.py | 名称驱动的10项IMDB过滤mask，已核原公包seed/字体 | FX3表位置、条目大小、服务清单，不能仅抄A7C2偏移。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-assets.py) |

### Inferences

- 可以借用通用纯软件数据处理实现（LZ77/raster）及清晰的hosd_ops接口，重新连接FX3真实数据/回调/锁；这比移植整个大observer更易定位。
- 无头最小helper可避免Darwin头和新glibc ABI混入；必须由原guest执行验证动态链接、UIPC init、消息生命周期，host编译成功只是前置。
- 所有虚拟CP、显示、镜头和时钟策略应写入运行profile，不能把缺硬件“回复成功”当作原ASIC兼容性证据。

### Gaps

- 本分支没有下载QEMU整归档，唯一host runtime负责实际取源/编译/运行，避免重复占资源。
- 本轮代码副本持续保留供修复，不按上一轮报告结束提前清理；运行到原菜单验收或收到统一结项窗口后再处理第三方参考代码。

本轮证据入口：`a7c2-main.json`／`a7c2-tree.json`（刷新身份）；`scrapling-current.md`（实际HTTP200、CLI带--ai-targeted）；`code-fetch-receipt.json`、`model-fetch-receipt.json`、`scrapling-code-receipt.json`（先前urllib TLS失败保留，后续Scrapling成功不改历史）；`qemu-patch-fetch.json`；`current-source-inventory.json`；`successful-path-contract.json`（机器可读顺序与API合同，不是可执行成功recipe）。本分支只静态读取代码，没有执行Sony程序、上游脚本、相机/USB/手机操作。宿主原AP/原模块实测独立属于runtime记录。

### 同步队列无callback的原服务修复补充

成功案例还有一个与当前FX3 `-1020` 更直接相关的原服务修复：`menu-observe.c` L706起记录，原16B同步请求 category `0x6107` / command `0x1000`、raw SID `0x12282f6` 因 `libBusPower.so` 没被启动而无receiver，导致OSAL返回-1020、sequence_boot::run_i断言。维护者修复为在依赖已映射后启动原服务，让原 `BusPower::preProcessCateBusPower` 处理；并不是把ioctl改成功。[原说明](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L706)

具体 `start_bus_power_module` 在L9586：`dlopen("libBusPower.so",RTLD_LAZY|RTLD_GLOBAL)`（0x101）→`dlsym("BusPower_Init")`→`void(void)`原入口，记录返回。`start_avbbc_module`在L649，以同样方式调用原`InfraAvbbc_Init`。这两条都是原厂服务初始化；若FX3原库确有相同入口／协议，优先于捏造消息回复。[BusPower函数](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L9586)、[Avbbc函数](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L649)

时机来自L11410：截获 `dlsym(...,"Application_System_Init")` 的真实返回，依赖这时才可在同一组映射中解析；L6551–55再按环境开关调用BusPower/Avbbc。太早在preload constructor加载BusPower曾出现SIGTRAP。最小FX3观察器可以核对这个导出符号并用`dladdr`得到库身份，避免复制A7C2的`symbol-0x1796918`硬偏移。是否对FX3可用仍须原符号/调用与实际日志核验。[时机](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L11410)、[依赖与原服务启动](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L6551)

还需防止把成功仓库内的旧实验误当推荐实现：L500的 `pipeline_endpoint_callback` 原请求echo，已被L590后的注释明确指出command/结果字/长度/source与no-wait生命周期均有错误。后续 `pipeline_virtual_serve` 已缩小命令范围，但其+8=0等仍为明示软件策略，不是物理CP协议证明。不能复制泛echo或泛成功ACK到FX3。[历史错误及收窄策略](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L569)

上述发现已逐条即时发给root、original-uipc和唯一host：先绑定真实op/SID与原callback，再决定启动原BusPower或建立特定软件endpoint；不以缺callback笼统归因udif set。当前所有运行成果仍由host拥有，本研究只提供源码／语义与检查点。

### 0x003e014d 的稳定分级契约与表述纠正

本轮即时消息中曾先按旧observer注释把`0x003e014d`叫CP-side，又按更新分析报告把它称作本地入口。这两种未经本分支独立核对FX3原注册调用的表述都不足以指导实施。此处固定统一术语为：**待核的本地Backup候选**，以 `backup-3e014d-contract-v1.json` 为准；后续需要新证据才另增版本，不能凭相同ID升级。

本分支确证的是固定Git版本的文本/代码：旧observer里相关假ACK/malloc分支均if(0)，注释不能当实际端点归属；新 `backup-noop-sync-contract.md` 报告了A7C2原backup.ko（144976B，SHA167715ebd8086b0751e95396ecc214c4d65ec54e11a9f2737a05664e03ad237b）的用户库→AP KO分派与结果回填。但本分支没有该原KO字节或其实际SID注册调用的独立复核，所以这些应标为**维护者原二进制分析报告的结论**，而非本机FX3已验证事实。[新报告](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/report/backup-noop-sync-contract.md)

报告所给具体坐标：原KO ET_REL，`.text+0x7aa8`为backup_osal_call_func，selector+1索引半字表；selector0xf的entry16=215，转到`0x7b1c+215*4=0x7e78`，`0x7e84`调用Backup_sync_subsystem并写消息+4。用户库分配112B，selector+0、结果+4、参数数+8、参数+0x20；只有传输返回0才拷结果。当前FX3捕获只证明op5/arg0=003e014d，selector尚待实际快照，不能套这条selector0xf路径。[源分析](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/report/backup-noop-sync-contract.md)

另已取sidecar定义的是**另一个**目标`0x903e0811`、40B请求/4096B回复，有真实后端冻结、完整读回、唯一kernel sender与阶段约束；不能因名称Backup就接到003e014d/112B当前请求。只有FX3原callback实际走向该远端后，才讨论适用性。[sidecar代码](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/report/virtual-cp/udate-distribution/backup-endpoint.c)

当前另外两项：`8f013a`在成功源码中明确为ulogio sink，精确initparam为`ulogio_initfile=/setting/ulogio.bin`；脚本放在stream后不证明必需stream，应由FX3原符号依赖和实际insmod核定。`94016a`仍未知，不分配推测性服务名。此版已发给双方，要求只以original owner独立核FX3原注册call、callback和实际selector后升级。[setup](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1201)

### uipc06 selector9 与同机官方种子的具体进展

此处以original owner独立回报为级别记录：FX3 `backup_osal_init`在`.text7920/7924`构造003e014d，7934调用原reg_sync；callback79d0→74e8→backup_osal_call_func。06实测selector9，原半字表index10 signed237→7ed0→7ee0调用**Backup_write**。它不是read、selectorf/no-op或远端903e0811；原模块实际加载后的callback返回/属性内容仍由host下一次实测确认。稳定v1保留，新增`backup-3e014d-contract-v2.json`记录独立owner来源与未验边界。

本研究者已对现存同机FX3 7.02原FDAT做有界读回核验，未运行旧提取脚本：完整Backup原模板 `0110_backup/SYSIPSX-DSLR/ALCIN/CX95900_ALLLANG.bin` 位于FDAT绝对1262080，2229740B，SHAbf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2；官方backup.sum大小/CRC4607d0ba匹配，两个BK4数据和checksum均通过。`0800_appli/setting/ulogio.bin`位于800427008，2784B，SHAdd5a1729788d6ee49b2217afc949eeb1e7c04c7244166d174bc90fda303dfc96。各tar头checksum、名字和长度都核对，不依赖A7C2种子。只验证选定member，未再次全hash808MB FDAT；不能声称确认了真实用户机身地区/当前bank。准确回执为`fx3-public-seed-source-receipt.json`。

成功参考的实际候选加载顺序：/setting为私有tmpfs；同一验证Backup字节进入`seed-backup.bin`与`seed-setting/Backup.bin`（避免后copy覆盖成另一份）；拷到/setting后以`Backup_load=1 Backup_save=0`加载原backup，随后使用原同机ulogio配置和`ulogio_initfile=/setting/ulogio.bin`。original owner另已报告FX3两模块符号可由当前原kernel/IPC/backup闭合，未发现stream依赖；是否实际init/访问了所需物理工作区仍须运行核验。upstream脚本把ulogio放在stream之后不能独立证明stream必需。

`Backup_load=0`不能用作绕过缺种子方案（original owner已报告其仍先select_path/load_file）；`Backup_save=0`不能保证完全不写文件，隔离来自私有tmpfs与仅虚拟存储；`Backup_save=1`也不是保存成功证明。成熟配置保存链是原API改值→具体原sync SID→原文件提交→完整双bank及目标字节/API校验→独立完整导出→不可变实例代→新VM两份同源seed→原getter真实改值回读。上游08-settings明确只有限语言/日期恢复通过，跳过首设仍未完成。[持久化说明](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/08-settings.md)

实际helper已取，但`user-settings-checkpoint.c`硬编码A7C2文件2390264B、子系统819、bank几何与属性，不能直接用于FX3 2229740B。应按FX3真实BK4与原属性改写校验，再由原guest运行；不能把A7C2严格校验删除成泛接受。[原helper](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/user-settings-checkpoint.c)。上述可执行条件另落`settings-virtual-data-contract-v1.json`，仍没有新增VM/原Sony执行。

### 原IMDB过滤与更新器边界的成功源码核对

当前成功case的`prepare-assets.py:147–165`仅对10个固定name清原mask低3位（mask&~7，原IMDB哈希/条目数固定），名单不包含Jiritsu或InfraUpdaterDPro。`target=qemu dmode=3`不是“不调用更新器”保证；`QEMU_NO_CP_UPDATER`只在observer10437拒绝目的912503d0，observer6683的udtr_ufp_init包装仍调用真实原入口。另`prepare-menu-initramfs.sh --without-updater`只是prune libupdaterufp.so文件。[过滤源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-assets.py#L147)、[真实init包装](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L6683)、[文件排除](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-menu-initramfs.sh#L8)

因此本轮FX3若按parent明确边界禁Jiritsu/DPro根，必须用original owner已核FX3表和targetmask做显式模型策略；不能声称A7C2成功案例已有同一过滤，也不能将投影排除引发的ENOENT解释为硬件故障。准确事实与限制保存在`imdb-entry-filter-contract-v1.json`。

original owner另报告原im在402600注册94016a callback402e08，body9400e1回填12345678；本分支据其来源记录为“im自身服务注册已报”，不再分配外部接收服务名。“已有im实例探测”仍仅是假设，未当作业务语义结论。

### 最新运行范围澄清：保留原依赖的普通idle初始化

Root已澄清本轮自己加入的宽泛库禁令：用户正常VM目标授权包括无真实设备guest中的原依赖库普通idle init/IPC注册，可保留原IMDB与Jiritsu/updater依赖，避免人为缺库ENOENT。禁止的是实际更新工作流、独立root执行载荷、真实设备操作。此前v1的严格投影要求只保留历史，最新以`imdb-entry-filter-contract-v2.json`为准。

当前设计/执行约束由root指定：无NIC、USB或host磁盘目录透传，不给guest更新包，写入限guest RAM或task虚拟文件；`NO_CP_UPDATER`的不可用更新传输语义保留。是否实际满足这些约束由唯一host的运行命令/收据独立证明，不能把此澄清或普通初始化提升成安全、更新功能、实机兼容通过。上游源码关于wrapper会调用原init的事实不变，原引用码/历史notes均不改写。

### IMDB逻辑模块名与实际库文件分开

针对FX3投影中105个IMDB名字没有独立`.so`的问题，成功case的安装器并不按这些名字造文件：`prepare-assets.py413–427`完整提取原initrd与usr，147–165只清10项mask、不重写type；`menu-observe.c1283–1360`始终调用真实dlopen，除了剥离DEEPBIND和绑定几个已加载真符号，没有失败时回退appFw或返回虚拟handle。dlsym同样先取真实符号。[安装器](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-assets.py#L413)、[loader包装](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L1283)

所以IMDB逻辑名不自动构成DT_NEEDED文件清单；应保留原entry/type，由FX3原im loader分支和实际dlopen/dlsym决定文件需求。公开取到的实现没解释`0x20000001/2/4`精确enum，本分支不猜；独立文件缺失、appFw内嵌导出模块及不同启动类型需要original owner反汇编核定。`imdb-logical-name-contract-v1.json`固定这些已证事实和未知项，不允许删所有缺名entry、造空库或虚拟handle。


### 显示与输入适配：同机导出、原消息、私有布局分开（2026-11-01 新增）

本轮先读v2时发现投影没有libObj，随后资源owner补齐v3，已改用同机真实原件；“v2缺件”不是“FX3没有这个库”。v3的libObj为2876600B、SHA c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae；libgpe为106480B、SHA363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464。新增`display-reuse/audit_fx3_display.py`只读原ELF并验证清单SHA，未运行原库、guest或QEMU；可复跑原有mac-verification/.venv解释器，结果`fx3-display-static-proof.json`保留原指令字节、38个导出函数块、23个内部目标块与重定位。

FX3原libgpe与成功case八个导出同名：GpermFillRect/a430、GpermBitBlit/a514、FillRect/c30c、BitBlit/cf2c、Flush/c760、SendDrawComp/d888、InitializeDraw/c1d0、Gperm::Init/9ae8。libObj有notifyDraw/1771f4、drawFramebuffer/16ea10及sys_getInstance/1749b0。appFw导入的对应JUMP_SLOT为47ccdd8/47cd040，libObj的原GPE导入也都有命名重定位。因此可用真实handle+dlsym/dladdr与符号重定位找hook位点，不必抄A7C2基址反推或GOT常数。符号匹配仅证明可绑定，参数块布局、格式和完成顺序仍要原请求验证。完整名与地址见`display-hook-contract-v1.json`。

surface候选有真正原GRM API：screenGetOnBitmap/f377c将原bitmap写输出指针，不AddRef；fbrmLockSwap/f3820和UnlockSwap/f383c内部查manager并锁两把原sem，避免外部猜manager。FX3内部current槽为fb+60、两锁对象fb+88/fb+78，与A7C2身份读取不同。锁API无限等待，初始化前/同线程重入不宜调用；Release不能用于未取得reference的借用handle。只读导出存在不代表可直接启动异步抓帧，寿命/ReadLock/raster锁和析构协调仍需闭合。

同机原消息角色已从常数升级为分配/来源/tag调用证据：f1db4分配8280074d/12B，tag1002；f1e40分配8280084d/36B，tag1003；f1d28分配8280084e/8B，tag1005；三者源均8288076c。原f2a10接收8288076c，f28c8将源8280074d送f22f0分派6003/6005，再进入原信号/回调分支。与成功case AP输出链相符，但完整transaction、GUI侧9088076b及几何格式尚未实测，不因此立即回ACK。

资源方面，原RTTI名N2ux4core11Lz77DecoderE/1e77c8经RELATIVE链定位typeinfo25cc80、vtable地址点25cca8，其decodeImpl槽25ccc0指154c40；不抄A7C2的277900/15a8b8。原函数确实读取stream+8、image+10、format+18、wh+1c/1e、压缩长度+20并调用/dev/ldec。纯sony_lz77_decode可复用，但FX3实际stream纯getter和image write-lock/stride/范围需核；原私有write-lock已不同，不能拿A7C2函数地址替代。[成功解码与帧链源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c#L11081)

显示传输有两条具体路径。`headless-osd-export.c:29–67`直接对一份已原子持久化的HOSDAP02 inode做完整有界base64导出，经串口回host，不需要QEMU ramfb/pixman。第二条才是原surface→ramfb-viewer→fw_cfg etc/ramfb→QMP screendump。host报告旧78e有ramfb设备但Pixman=NO、display仅none，正在独立构建带pixman派生版；设备名存在不证明截图消费。两条路径共同前提都是真实原surface与租期，不画替代菜单。[独立导出器](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/headless-osd-export.c)、[ramfb桥](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/ramfb-viewer.c)

输入原InfraInput GetInstance/SetCallback/SetEventKeyList及WidgetSystem::processEvent均导出，可透明观察原注册/消费；四个原OSAL发送API存在。807a0020在libObj多个原MOV链出现，但A7C2 raw→UIBIZ表和键码不能照抄，提交0也不算原消费。需要先核FX3表与一次导航、新帧闭环，尚未做输入验收。

### 成功入口的最终默认值与模块顺序复核（2026-11-01 新增）

本次补取并Git blob核验run-menu-probe.sh、menu_control.py、menu_live.py、原回归checker及validation README，另取kernel wrapper/developer-modes；全部固定b3d7c1f并记录SHA，未执行上游脚本。raw TLS首次失败、blob API403及后续成功分别在收据保留。`startup-resolved-contract-v1.json`取代仅凭start-menu没赋值的简写。

链为menu_control._run→profile_environment→native_display_environment→run-menu-probe.sh→qemu-menu-probe.py。profile先清调用者MENU_/QEMU_/SONY_旧环境，普通natural分支不赋MENU_EXTRA_MODULES；native-display分支也只加窗口/输入/构建目录。shell wrapper没有这个变量默认值。probe只用os.environ.get真值条件。因此在无imaging/PNG/custom后改的普通natural profile中它确为absent/false；直接手跑shell则会继承非空值，字符串0也是真值，不能把“没写CLI参数”当unset。imaging/PNG分支显式safe才产生echo set及extra列表。[实际wrapper](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/run-menu-probe.sh#L42)

标准wrapper固定启sony-timers/load-ipc/seed-backup/load-dmm/load-power/load-kikilog/seed-power-on等，故实际源码生成顺序是挂载/cpuset/字体→devno/utm/uipc→dma330→utimer→Backup→stream/2→ulogio→DMM→grm_ma→固件身份→seed-power→upm→udate+seed-date-clock→sound gate→kikilog→observer/media准备→date/sound ready gate→原bootin target=qemu dmode3。额外模块若显式开，会先set、再延至Backup/DMM后加载。没有成功对照证明上述哪些能后置，不把“当前FX3未自动加载”写成“成功case不需要”。自然profile与MENU_APPLY_MENU诊断入口分开。

公开validation README205–225报告run-0wfqbd6k原简体中文、高亮选择、原640×480 HUD与稳定MENU有人工图像复核，自动proof总体false保留。其原始运行env/console未公开；当前源码默认解析和历史成功报告是不同证据，不能据前者声称复核了该run精确环境。[公开成功限定记录](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/validation/README.md#L205)

LIRO另立边界：prepare-assets的10项SKIP精确名单为UsbBusPower、InfraUsbCmn、sensapi、UsbControl、BusPower、Hotplug、InfraCrypt、InfraMediaPwrMgr、NetServiceTethering、TetheringResource（均对应lib*.so）。LIRO不在其中；patch只清mask低3bit，不改type/argv。headless hosd_claim却明确要求/proc/modules无liro，原developer-modes文档又说dmode3含s/g/r/u/l/i/a。这些事实还不能唯一解释成功run为何未保留原LIRO：不能编造十项过滤屏蔽LIRO、不能说原CP RAM已执行。若FX3原l阶段启LIRO load1，应基于本轮平台策略显式派生过滤，并单独记录，不把它冒作同上游完全相同。[过滤源码](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-assets.py#L55)、[排他consumer](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/headless-osd.c#L67)

成功case大cpio高处加载也已核：qemu-kernel-probe.sh273与402–405固定initrd440000000，DTB chosen同步start、end按实际size；kernel400080000、DTB400002000。cpio的Linux memory reg为400000000+140000000（5GiB），官方同机kemco所有memrsv行除tmonitor进入bootargs，另有三个A7C2 FDT workspace保留。FX3须自己的kemco/实际owner，不能从8GiB DTB或-m值推断专用内存；-m24576是稀疏可达地址覆盖，并非Mac必须24GiB内存。已给host/original精确文件支持修复当前低处initrd冲突。[内存实现](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-kernel-probe.sh#L164)
