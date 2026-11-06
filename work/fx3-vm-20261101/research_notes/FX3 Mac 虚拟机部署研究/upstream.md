# A7C II QEMU 源码与经典 FX3 迁移条件

## 最新公开实现究竟运行了什么

### Takeaway

截至本轮 2026-11-01 查证，chocotan/a7c2-qemu 的 main 仍是 `b3d7c1fed349f1d918acc4259f1d2b3a7c52a500`（2026-10-31 18:58Z）。这是以原 Sony Linux 内核为 guest 的 QEMU **system** 仿真，加大量明确的软件设备／协议适配；有原程序首设、菜单、OSD 与输入证据，但不是已完成的原 CMOS／ISP／编码成片仿真。[固定源码](https://github.com/chocotan/a7c2-qemu/tree/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500)、[10月31日进展](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/2026-10-31-current-progress.md)

### Cited Findings

- `runtime/analysis/qemu-kernel-probe.sh` 实际启动 `qemu-system-aarch64`，机器 `virt,secure=off,gic-version=2`，CPU `cortex-a35`，默认单核；`aarch64-linux-user` 是构建附带的另一目标，不能把两者混为一谈。[源脚本](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-kernel-probe.sh)
- 导入器只接受 `model=0x20030014/version2.01/region0/非Accessory` 的 ILCE-7CM2 ALLLANG。输入镜像、Backup、DmmCfg、DTB、字体等固定 SHA；`prepare-assets.py` 从原 ext2 initrd 与 nflasha15 提取运行资产，再生成实验身份卷。[资产说明](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/01-firmware-assets.md)、[安装器](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-assets.py)
- 原厂原件与派生物均存在：安装器遍历 libIMDB 的 `VA0x1db20..0x21d80`，步长72，对10个明确服务清掉mask低3位，得到派生 `libIMDB-menu.so`；因此不能称整套 guest 二进制毫无修改。[安装器](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-assets.py)
- 原 `bootin.elf 'target=qemu ' dmode=3` 拉起机身应用。另有直接启动 `im.elf target=qemu` 的定位入口，后者不等于自然冷启动。`dmode=3` 也不是通用硬件仿真开关。[原应用启动说明](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/04-app-and-first-setup.md)
- 应用启动前依赖原 `/proc`、sysfs、tmpfs、cpuset cgroup 与有顺序的 devno/osal_utm/osal_uipc/utimer/backup/stream/dmm/grm_ma/upm/udate。模块顺序依据该机原 initrc，不是删掉报错模块就能认为兼容。[guest准备](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/03-guest-environment.md)
- 显示链是真原 AP 控件请求加软件 GPE 绘制、软件 LZ77 资源解码、受约束 LIRO/OSD 消费，再转 ramfb。RGBA4444、GPE模式、OSD消息和租期为特定模型合同，不能称 Sony 实体 GPE/面板已模拟。GUI 是 QMP截帧→PPM→PNG→Python GTK，默认QEMU `-display none`；10秒采样LCD不等于实时取景。[显示实现说明](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/05-display.md)
- 软件 RGB888 源、软件镜头/对比度AF及真实JPEG/H264组件已有独立消费与读回，但没有原 AP→同一 CMOS 源帧→编码→原 MPR/Fsys→虚拟SD→独立解码的 JPG/MP4，`capture_verified=false`、物理ASIC兼容未验；原CP模块/RAM/RTOS并未随软件模型进展成为已支持。[成像前沿](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/11-imaging-frontier.md)、[最新进展](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/2026-10-31-current-progress.md)
- 附近项目不能充 FX3 成功证据：OpenMemories-CI 的固定HEAD `4f8c6367a75e9afd02bc684425e3fbff424b2223`（2021-11-12）README展示CXD4108的DSC-T100/G3；`chuer749/sony-camera-qemu` 的HEAD `d8044758fb1e9849b0c07ae9eb862c315ecca328`（2026-11-01）只有README，明确A7R3A尚未启动；Aetherion当次网页为空库且commits API409。[OpenMemories-CI](https://github.com/ma1co/OpenMemories-CI/blob/4f8c6367a75e9afd02bc684425e3fbff424b2223/README.md)、[A7R3A项目](https://github.com/chuer749/sony-camera-qemu/blob/d8044758fb1e9849b0c07ae9eb862c315ecca328/README.md)、[Aetherion](https://github.com/Timeline692/Aetherion)

### Inferences

- FX3 部署必须分成宿主能运行 QEMU、原内核到 shell、原应用到菜单、实际成像四个验收层。A7C II 的一层通过不能替 FX3 任何层完成。
- 原 AP 程序运行和软件替身共同推进界面是有价值的研究路线；适配这套方法比重建完整Sony硅片模型更现实，但每份替身都必须标明行为与不能外推的范围。
- 当前最有实质内容的参照是 A7C II 的 system 路线，不是只有仓库名称或 旧机型截图的项目。

### Gaps

- 本分支未执行 A7C II 上游脚本、QEMU、Sony程序，也未复现其菜单；其动态能力来自维护者公开记录。
- 没有找到上述公开项目已支持 FX3 7.02 的证据。不能把未找到扩大为所有公开／私有渠道不存在实现。

## 哪些具体接口能迁移到 FX3，哪些不能直接复制

### Takeaway

可迁移的是仿真分层与测量方法，以及经FX3原件逐一重核后的基础外设模型；导入器身份、表偏移、消息、资源池、OSD和控制器均须FX3专门适配。直接删除A7C II `supported()` 或只替换 `BODYDATA.DAT` 不构成FX3启动器。[跨机型限制](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/01-firmware-assets.md)、[启动迁移边界](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/02-qemu-boot.md)

### Cited Findings

| 层／接口 | 上游实际实现 | FX3迁移判断 |
|---|---|---|
| 固件身份／资产 | 固定A7C II 2.01 tuple、镜像SHA、ALLLANG seed、字体 | 必须从FX3 7.02原件重建身份和清单。不能以A7C2配置制造“FX3”。[源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-assets.py) |
| 地址装载 | 该profile DTB=`0x400002000`，Image=`0x400080000`，initrd=`0x440000000`，写入DTB `/chosen` bootargs/initrd-start/end | 固定loader方法可借；地址必须独立核。上游记录普通 `-append` 会被原内核拒绝覆盖。 [源](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/02-qemu-boot.md) |
| GIC/UART | patch给GICD/GICC加`0xf13a1000/0xf13a2000`别名，UART0加`0xf1000000`别名 | 需由FX3 DTB／原内核核同一寄存器合同。`QEMU_SONY_TIMERS`开关同时控制这些；不能按变量名只理解timer。[patch](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/source/qemu-sony-native.patch) |
| Sony定时器 | `sony_hwtimer.c`，四设备`0xf1042000+i*0x1000`，IRQ200+i，参考ma1co的BIONZ timer | 可成为核对后的实现起点；真实FX3 tick/IRQ/寄存器未核前不算完成。[patch](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/source/qemu-sony-native.patch) |
| WBI外设替身 | SPAcc=`0xf7fc0000`；F0000000外设窗口catch-all读全1、写吸收，低优先级 | 为快照恢复绕过poll设计，不能默认启用于FX3冷启动或把轮询放行当真实设备工作。[patch](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/source/qemu-sony-native.patch) |
| 内核initcall | blacklist跳未建模 hwtimer/wdt/otg/pcie/ddrc/pcidma/usb，profile按模型打开部分 | 需逐项按FX3符号与调用确认；未建模拒绝与blacklist写在运行清单。[脚本](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-kernel-probe.sh) |
| 原应用观察器 | menu-observe.c=668098B；含GOT/PLT、函数入口和原字节检查，示例appFw `+0x165fe30`与`+0x5bc1d70` | A7C II专属偏移不可抄。FX3按PT_LOAD转换、符号／字符串xref／原指令重定位。原字节不符应停止。[代码](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c) |
| 原服务／IMDB | 10项SKIP mask位清除、dmode3启动、模块顺序 | 需按FX3原initrc/IMDB重建；禁用服务是显式派生配置。[准备](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/03-guest-environment.md) |
| UIPC/CP边界 | 内核IPC加用户态模型服务，镜头/曝光/2040快照等有特定 SID、消息长度和租期 | 消息号和payload须FX3重核，不能移植成功ACK或把软件CP当原CP RTOS执行。[成像](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/11-imaging-frontier.md) |
| OSD/GPE/LZ77 | 软件GPE与真实资源解码，LIRO成对消息→ramfb→QMP截图 | 架构可借；FX3像素格式、资源压缩与队列、屏幕ID、首设页序全部重核。[显示](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/05-display.md) |
| 成像／编解码 | 功能profile明确RGB888，JPEG/H264组件；原媒体成片失败 | 可研究原控制消费和软件图像源；不能据此宣称FX3原RAW/ISP或H265硬件兼容。[成像](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/11-imaging-frontier.md) |

### Inferences

- 最便宜的首个实测是：FX3原Image + 独立推导的DTB + 最小newc initramfs + 串口shell，先给stock QEMU确定的基线；原硬编码访问构成具体阻塞时再加核对后的alias／timer模型，不需要先装齐A7C II的GUI、观察器和全部CP模型。
- 缩窄高位RAM backing窗口、保持FX3原PA域，有望避免上游大跨度 `-m` 配置；这是自定义板模型的候选设计，需要真正测量，而不是已验证方案。
- 应先将 shell、原模块／服务、原menu首屏作为递进的最小验收，不宜在无原FX3首屏时直接承诺取景与H265。

### Gaps

- FX3 Image header/DTB/原initrc/同一功能偏移由兄弟 assets 审计负责，本notes不冒充已完成这些二进制核对。
- 上游 `report/virtual-pcidma/stage_hardware.py` 还会在三份基础patch之后增加模型源码，故“取三份patch”不等于完整最新QEMU构建。基础冷启动试验不应被无关PCI/WBI路线拖住。[构建脚本](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/build-qemu.sh)

## 在 Apple Silicon Mac 上的宿主迁移需要什么

### Takeaway

上游正式使用环境仍限定Linux x86_64。维护者的macOS说明是2026-10-21的静态移植评估，明确未经Mac构建／运行验证；“中等工作量可行”应作为待验证推断。以macOS原生TCG运行AArch64 guest是值得先做的受限路线，不必先搭建x86 Linux嵌套虚拟机。[主README](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/README.md)、[跨平台评估](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/PORTING-WIN-MAC.md)

### Cited Findings

- 原构建为QEMU11.1.2，外部压缩包固定141815216B、SHA256=`731b5681e4bb18be313231579b8efd0296c5b015fa36dc533874b639ba838016`；源状态记录这只是上游声明，此分支未下载该141MB输入。configure同时目标system+linux-user，要求GTK3/SDL2/pixman/glib/libseccomp、bwrap、flock、GNU工具。[来源清单](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/SOURCE-ORIGINS.json)、[构建](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/build-qemu.sh)
- macOS首要移植点：bwrap/seccomp/linux-user不可原样用；`/proc/self/fd`与目录FD后缀不可简单统一替成`/dev/fd`；取消强制X11；debugfs/dosfstools/cpio需找到兼容工具或替代；guest工具须保持Sony glibc2.25，防outline atomics/C23/旧fxstat等ABI问题。[Mac评估](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/PORTING-WIN-MAC.md)
- Python socketpair/fcntl/pass_fds、进程组回收、flock、目录FD相关能力在macOS有原生支持基础。QEMU模型patch位于hw/include/ui，不修改宿主构建系统；headless QMP采样设计有利于先用无GUI原生TCG启动。[Mac评估](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/PORTING-WIN-MAC.md)
- `qemu-kernel-probe.sh` 的 `memory_config=24576` 服务固定高地址稀疏backing，DTB描述范围另有约束，不表示实体相机24GiB内存或每次运行实际驻留24GiB。其低布局boot-memory实验也明确是稀疏host分配。[脚本](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-kernel-probe.sh)、[启动说明](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/02-qemu-boot.md)
- 上游文档“允许跳过／降级bwrap、seccomp、X11自动验收”属于其自己的需求方决定，不是本用户已接受相同降级的授权。此任务应报告真实隔离与验证范围，不能复制上游“已批准”作为本机的事实。[Mac评估](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/PORTING-WIN-MAC.md)

### Inferences

- 最小宿主试验可只需要原生AArch64 system emulator、DTB编辑器和cpio组装，不需要Linux-user、GTK、SDL、完整A7CII交叉工具链；全菜单阶段才补原应用软件模型与显示桥。
- 在16GiB主机上，不应仅看`-m24576`就判不可做，也不应承诺性能；观察RSS/内存压力和真正访问范围，必要时单独映射高地址RAM。
- 可以先以TCG做可靠的跨机型调试与单核串口启动；HVF能否支持原内核/定时器/EL布局需另验，不应预设硬件虚拟化加速可直接用。

### Gaps

- 本分支未安装QEMU、启动VM、改变宿主系统或原机；Mac实测由host分支负责。
- 没有本机完整菜单、虚拟成像的性能数据；没有Mac GUI/长期稳定性或FX3原物理接口兼容验证。

本轮取证范围：Scrapling现有0.5环境实际抓取主仓库HTTP200并导出Markdown，CLI带`--ai-targeted`；GitHub API固定commit和完整tree；35份选择文本共2060042B逐份SHA256与Git blob验证，未导入／运行这些代码。复核入口 `upstream/source-state.json`、`selected-source-receipt.json`、`selected-interface-evidence.json`、`adjacent/source-receipt.json`。外盘UUID已核；没有相机、USB、手机、服务载荷或刷写操作。第三方参考副本仅在任务work下，待父协调者统一结项窗口按AGENTS处理；URL/commit/摘要记录保留。
