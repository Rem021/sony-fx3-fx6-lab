# FX6 6.01 完整供体：离线取得与解包回执

2026-11-03。**阶段完成：已取得并在本地保留官方 847,081,840 B 包，核对全包容器和各分区实际文件。** 本阶段只有公开下载、静态解包和本机 CPU 解析；没有 VM、相机、USB、SD、刷写或分发验证。这里没有恢复 RAW/ISP 算法，也没有 FX3 7.02 可用的移植件。

## 来源与固定输入

- 官方下载：[Sony FX6 6.01 BODYDATA.DAT](https://di.update.sony.net/NEX/Dobb4b83c7/BODYDATA.DAT)。HTTP 长度 `847081840`，ETag `"bb5889444b135bf412958a2cabec1a37:1788139615.370836"`；101 个最大 8 MiB 的范围请求逐个检查 206、Content-Range、ETag、长度，回执见 `download-state.json`、`download-receipt.json`。
- `BODYDATA.DAT` SHA256 `0654a32ba1458006edb909f0294ecb1913d8d7f89fb17b19fc5b306c5dc04ba0`。上层 `probe_fdat.py` 与 `fdat-probe.json` 的首块 6.01、型号和 CRC 结果作为前置线索；本轮从完整文件重新核对。
- 解析方法固定在 [DavidBuchanan314/fwtool.py 提交 3955d789](https://github.com/DavidBuchanan314/fwtool.py/tree/3955d7890fc38daf942bb52827599bfe35de4a14)；源码压缩包 SHA256 `6abc19ad21aedaa90bf52cc16ff635bc78a209af377ac95e00a445c27a580fb3`。审阅并调用其 `sony/dat.py`、`sony/fdat.py`、`archive/ext2.py`、`archive/fat.py` 和 `archive/squashfs.py`；FAT32 单独用 pyfatfs 1.1.0 只读解析。第三方参考源码在结项后删除，可用 `prepare.sh` 按固定提交重取。

## 容器与文件系统核验

- 完整 UFU 的 DATV/PROV/UDID/FDAT/DEND 路径由 `dat.readDat` 读取，DEND CRC32 通过；FDAT 全部块校验及结束标记通过，头 CRC32 通过。`CXD90057_k0` 解出的型号 `0x91040086`、版本 `6.01`。**官方签名未验证。** 详见 `unpack-receipt.json`。
- 解密 `firmware.fdat`：843,771,904 B，SHA256 `ff58a4d00a3c26b17629c943a3ef149fc3deff9fb851e830d1d74a0e715984a4`。解出的 `firmware.tar`：842,518,016 B，SHA256 `53fe3dabbe23da2ddea9fa1a42d8c1a36e681ec90b6398fe4b903f5217aac099`；`updater.img`：1,253,376 B，SHA256 `d204fcf2b2b6ca4777b0fae5dda3af919af85e9b7651c1b6b87eac760363183a`。
- TAR 有 152 个成员，其中 104 个常规文件。安全展开时跳过相对符号链接 `0800_appli/tmp/mtab -> ../proc/mounts`，未创建链接。每个常规文件的长度、SHA256、`file` 判型与 ELF 架构见 `manifest.json`。
- `nflasha15` 是 ext2，得到 753 个常规文件和 514 个 AArch64 ELF；详见 `nflasha15-manifest.json`。其中 9 组文件名只差大小写，在本机不区分大小写的卷上不能直接同路径保存；各自保存在 `nflasha15-files/case-collisions/`，清单 `stored_path` 精确对应原路径，逐个 SHA 均复核通过。`nflasha1/3/8` 为 FAT12，得到 24 个文件；`nflasha23` 在 MBR 第 1 扇区是 FAT32，得到 35 个授权/许可证文件。见 `fat-manifest.json`、`fat32-manifest.json`。`updater.img`、`nflasha1` 的 initrd 是 zlib SquashFS，`nflasha3` initrd 是 ext2，共再得 325 个常规文件，其中 245 个 AArch64 ELF，见 `nested-manifest.json`。
- `nflasha5` 为 WBI2，1197 个静态节记录，存储尺寸合计与头一致，1143 个有数据、54 个零填充标记；仅核对节表，没有还原内存语义，见 `wbi2-receipt.json`。

## 已定位的实际成员

| 层 | 本地相对路径 | SHA256 | 静态判型 |
|---|---|---|---|
| AP | `nflasha15-files/lib/appFw.so` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | AArch64 ELF shared object |
| 媒体控制 | `nflasha15-files/lib/libmpr.so` | `814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e` | AArch64 ELF shared object |
| CP | `fat-files/nflasha8/cpapp-b.bin` | `60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668` | 非 ELF 镜像，架构未定 |
| AV | `fat-files/nflasha3/av-cam.bin` | `56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf` | 非 ELF 镜像，架构未定 |
| updater 内核 | `fat-files/nflasha1/boot/vmlinux.bin` | `58f595d53a0bfb328ee6530c7e93cbdd29d3296d1f2ee08c8322f5b1ba77c70b` | ARM64 Linux Image |
| 主内核 | `fat-files/nflasha3/vmlinux.bin` | `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9` | ARM64 Linux Image |
| DTB | `fat-files/nflasha1/boot/cxd90057.dtb` | `87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca` | DTB v17 |
| 应用设置 DTB | `tree/0800_appli/setting/cxd90057.dtb` | `c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280` | DTB v17 |

AP 资源位于 `nflasha15-files/share/`，148 个常规文件：`app/` 72、`avsystemsound/` 41、`screenreader/` 20、`lut/` 4 等。四份 `.cube` 的各自 SHA 在 `nflasha15-manifest.json`，它们只是资源层。`candidates.json` 列出 `appFw.so` 的 Colorimetry 状态入口、`libmpr.so` 的 VideoParamComb/RawInfo/RawSet 动态符号，以及 CP、AV、WBI2 的文件出处和未知项。符号和文件名只指明调查入口，**没有证明去马赛克、黑电平、ISP 算法的模块边界或 FX3 兼容性**。

## 复现

在此目录依次运行 `sh prepare.sh`、`python3 fetch.py`、`python3 unpack.py`、`python3 inventory.py`、`python3 extract_ext2.py`、`python3 extract_fat.py`、`PYTHONPATH=.vendor python3 extract_fat32.py`、`python3 extract_nested.py`、`PYTHONPATH=.vendor python3 analyze.py`、`python3 verify.py`。要求 Python 3、PyCryptodome、curl 和 `file`；`prepare.sh` 只将固定上游代码与 Python 依赖暂放本目录。`verify-receipt.json` 记录 1,241 个常规文件和 4 个核心产物重新哈希全部通过。现有完整官方包与全部固件产物仅本地保留，不进入分发或 Git。

下一精确动作：在固定 SHA 的 CP/AV 镜像上先解析其容器与处理器映射，再用 AP 导入/导出及 IPC 交叉定位 RAW/ISP 控制与消费者；取得固定 RAW 输入/输出和 FX3 对应链路之前，不宣称算法恢复或移植可用。
