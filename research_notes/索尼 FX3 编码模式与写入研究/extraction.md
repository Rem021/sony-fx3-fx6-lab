# FX3 7.02 嵌套文件系统与程序提取

## 能否从官方固件进入实际主程序而不接触相机

### Takeaway
已从上一轮解密成功的 FDAT 中按真实文件系统结构提取 `appFw.so`、`cpapp-b.bin` 及相关库，跨过了“只列 tar”的阶段。五个分区的字节长度与 CRC32 均匹配包内官方 `part_image.sum`；所有读取只作用于电脑端副本，没有挂载镜像、执行固件或连接相机。

### Cited Findings
- 从 FDAT 按清单中的精确偏移取得五个原样镜像；自写脚本首先验证整个 FDAT SHA256 `694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768`，随后进行边界检查并输出文件 SHA256 / CRC32。五项 CRC32 全与包内官方表一致：`nflasha15 a208a5a6`、`nflasha3 ed27be4d`、`nflasha5 7b479920`、`nflasha7 ef506ae5`、`nflasha8 93e5f241`。[提取脚本](../../work/sony-firmware-20261024/stage2/extraction/extract_partition_images.py)、[分区清单](../../work/sony-firmware-20261024/stage2/extraction/partition-carve-manifest.json)、[官方检查表](../../work/sony-firmware-20261024/stage2/extraction/official-part_image.sum.txt)、[一致性结果](../../work/sony-firmware-20261024/stage2/extraction/official-partition-verification.json)
- `/usr`（nflasha15，479,846,400 B）与 rootfs（nflasha7，5,218,304 B）在 1024 字节处有标准超级块，其魔数为 `0xEF53`，块大小 1024，inode 大小 128，不含 extents；本轮按 ext2 direct / indirect / double / triple indirect block map 解析，分别列出 **915** 与 **153** 项目录对象（含目录和符号链接，不是文件数）。没有因镜像开头为零就误判加密。[Linux 超级块说明](https://www.kernel.org/doc/html/latest/filesystems/ext4/super.html)、[块映射](https://www.kernel.org/doc/html/latest/filesystems/ext4/ifork.html)、[目录结构](https://www.kernel.org/doc/html/latest/filesystems/ext4/directory.html)、[usr 索引](../../work/sony-firmware-20261024/stage2/extraction/nflasha15-files.json)、[rootfs 索引](../../work/sony-firmware-20261024/stage2/extraction/nflasha7-files.json)
- `/system`（nflasha3）与 `/cp`（nflasha8）均是 **FAT12**，不是按名字或容量猜测的 FAT16：每扇区 512 B，每簇 32 扇区，数据区偏移 65536，数据簇数分别 1930、1366。两份 FAT 镜像相同；分别列出 10 项目录对象。12bit 簇链与 LFN 已被真实读取，成功提取 CP 程序；首次按 FAT16 读取产生边界异常后改为依簇数判定的 FAT12，最终校验和长度均通过。[Linux FAT 主实现](https://raw.githubusercontent.com/torvalds/linux/master/fs/fat/inode.c)、[system 索引](../../work/sony-firmware-20261024/stage2/extraction/nflasha3-files.json)、[cp 索引](../../work/sony-firmware-20261024/stage2/extraction/nflasha8-files.json)、[双 FAT 检查](../../work/sony-firmware-20261024/stage2/extraction/fat-mirror-checks.json)
- 自写读取器只读 mmap 输入，拒绝文件边界外读取及循环目录/簇链；不跟随固件符号链接、不创建固件符号链接、不应用固件可执行权限、不使用映像中的程序。输出只允许固定任务目录下的常规文件。[只读文件系统读取器](../../work/sony-firmware-20261024/stage2/extraction/read_filesystems.py)

### Inferences
- 当前没有“主应用仍被加密所以不能继续研究”的障碍：主 ELF 已完整读出，可进行反汇编及交叉引用分析。这与主应用能否在相机上接受修改、启动或恢复无直接等价关系。

### Gaps
- WBI2（nflasha5）只取出并校验原样镜像，没有解析内部热启动内存布局。
- 没有重新构建文件系统、打包或尝试写入；离线 CRC 正确只证明本次提取一致性，不能代替设备签名或运行检验。

## 已交付哪些供模式分析和写入审计使用的程序

### Takeaway
两项核心程序已交给模式分析；Jiritsu、按需加载器、动态加载器与启动脚本已交给写入审计。所有输出包含原目录、inode 或 FAT cluster、长度、SHA256。

### Cited Findings
| 固件原路径 | 本次提取长度 | 格式与状态 |
|---|---:|---|
| `/usr/lib/appFw.so` | 79,015,712 B | ELF64 little endian，AArch64，ET_DYN，动态链接、静态符号表已剥离，动态符号表 803 项 |
| `/cp/cpapp-b.bin` | 15,980,568 B | 非 ELF；头部与 AArch32 指令形式相符，未完整判定装载格式/地址 |
| `/usr/lib/libJiritsu.so` | 225,200 B | ELF64 AArch64，供服务入口静态审计 |
| `/usr/lib/libOnDemandLoader.so` | 73,728 B | ELF64 AArch64，供加载路径静态审计 |
| `/usr/lib/libsencore.so` | 377,328 B | ELF64 AArch64，服务相关依赖 |
| `/usr/lib/libInfraUsbCmn.so` | 159,504 B | ELF64 AArch64，供 USB/服务审计 |
| `/lib/ld-2.25.so`（rootfs） | 120,616 B | ELF64 AArch64，供 preload 路径审计 |
| `/usr/scenario/CAMERA_SCN_MOVIE_REC_START.so` | 69,264 B | ELF64 AArch64，供录像启动参数分析 |
| `/usr/kmod/codec_drv.ko` | 19,216 B | ELF64 AArch64 relocatable 模块 |

表中路径与格式来自真实文件系统读取及 ELF 头、节表检查；`appFw.so` SHA256 为 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`，`cpapp-b.bin` 为 `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`。ELF 全部非 NOBITS 节均位于文件边界内；未执行装载或初始化函数。[核心程序清单](../../work/sony-firmware-20261024/stage2/extraction/extracted-manifest.json)、[补充清单](../../work/sony-firmware-20261024/stage2/extraction/supplementary-extracted-manifest.json)、[ELF 元信息](../../work/sony-firmware-20261024/stage2/extraction/elf-metadata.json)

- 三份 `/usr/codec/vcd_firmware*.bin` 已提取，大小分别 5,445,340 / 8,837,324 / 10,934,476 B，头部含 `SW_VER_*` 文本且不是 ELF。它们的目标 ISA 仍未在本子任务核定，不能从文件名就认定编码模式已实现。另提取 `/system/av-cam.bin` 13,348,560 B，头含 `ORIL`；同样仅作为后续入口。[补充清单](../../work/sony-firmware-20261024/stage2/extraction/supplementary-extracted-manifest.json)
- `/usr/bin/up.sh`、`common.src`、`compat_firmware.sh`、rootfs `/sbin/init`、`init2`、`initrc/setup_rootfs` 已供写入审计读取；未运行。rootfs `/root/chassis` 原始文本为 `CXD90057+CXD90058`，它只能证明包内这个标记，不能独自证明安全启动、服务漏洞或具体主板相同。[补充提取脚本](../../work/sony-firmware-20261024/stage2/extraction/extract_supplementary.py)、[补充清单](../../work/sony-firmware-20261024/stage2/extraction/supplementary-extracted-manifest.json)

- 根据模式子任务请求，继续提取 `/usr/lib/libmpr.so`（3,517,008 B，SHA256 `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c`），供定位真正 `mpr::SetMovieRecParam` 实现；另根据写入审计请求提取 `sen.elf`、`bootin.elf` 与 rootfs 的 `fstab`、`fstab.root`、`setup_console`。这两个 ELF 的直接 `DT_NEEDED` 没有 `appFw.so`，但单凭这个不能排除动态装载及间接依赖。[追加精确清单](../../work/sony-firmware-20261024/stage2/extraction/late-selected-manifest.json)

### Inferences
- 主应用和 CP 文件名与现代 Sony 局部补丁通常关注的程序相同，因此可以具体比较版本哈希、函数及固定写入窗口；不能将别的机型的偏移直接套用。
- 编码器底层枚举和主应用参数转换的分析由独立模式子任务负责；本提取结果不代替其结论。

### Gaps
- 本子任务不做录像模式控制流、设备服务认证、patch 写入或实际录像验证。
- 仅提取选定常规文件，没有将全部 915 项 usr 对象复制成可运行根文件系统。

## 如何复核和继续使用

### Takeaway
全部程序均可从先前的官方 FDAT 复现，无需重新下载或连接相机。

### Cited Findings
在 Mac 项目根依次执行下列本轮自写解析器，仅会重建本任务新建的派生输出；原始 BODYDATA 与解密 FDAT 保持只读：

```sh
python3 work/sony-firmware-20261024/stage2/extraction/extract_partition_images.py
python3 work/sony-firmware-20261024/stage2/extraction/read_filesystems.py
python3 work/sony-firmware-20261024/stage2/extraction/extract_supplementary.py
```

原始参考代码没有下载为第三方仓库或执行；本轮只有自写解析器与官方固件派生文件。[分区脚本](../../work/sony-firmware-20261024/stage2/extraction/extract_partition_images.py)、[读取器](../../work/sony-firmware-20261024/stage2/extraction/read_filesystems.py)、[补充脚本](../../work/sony-firmware-20261024/stage2/extraction/extract_supplementary.py)

### Inferences
- 这些派生材料可支撑后续最小函数与配置研究，仍不构成可刷入成品。

### Gaps
- 未进行第三方工具的全文件系统独立交叉提取；本轮以官方分区 CRC、两份 FAT 一致、真实 inode/簇链边界、完整 ELF 节表及重复提取哈希一致提供检查。
