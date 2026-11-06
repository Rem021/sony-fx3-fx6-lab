# FX3 7.02 当前更新器、MAIN 早期启动与容器完整性

## 现有 7.02 官方整包是否带独立 p1 updater 的 kernel／initrd

### Takeaway

**没有在当前这份完整 7.02 官方包的定义结构中找到独立 p1 updater 载荷。** 这不是沿用“五分区提取白名单”的猜测：本轮从原包重验 UFU 全 chunk、FDAT 全 28 个槽、全部 TAR 及嵌套 NOR TAR，并核对原官方校验表。包里确有当前更新执行 body 和 MAIN 的 kernel／initrd，但不能把它们当成独立 p1 rescue 环境。[本轮完整审计](../../current-updater-evidence/current-updater-asset-audit.json)；[表与官方 SUM 复核](../../current-updater-evidence/table-and-sum-validation.json)

### Cited Findings

- 2026-10-29 联网核对的 Sony 官方资料明确适用经典 **ILME-FX3**，当前页列 `BODYDATA.DAT`、7.02、811,876,768 字节、发布日期 2026-03-17；2.02 或更旧须先经 2.04／2.05。下载页没有声称该包是完整机身备份或强制救援镜像。[Sony 官方原文](https://www.sony-mea.com/en/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298560)
- 现存原件来自 Sony `di.update.sony.net/NEX/ey8d8a84ee/BODYDATA.DAT`；本轮重读整文件 SHA-256 `f040affe234a8b6ec996ba616108c0014573f3cf28deb8b442fd0be091cac854` 与下载回执相同，长度也与官方现页完全一致。现存解码 FDAT 为 808,704,512 字节、SHA-256 `694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768`，整文件本轮重新哈希通过。[原下载来源](../../../fx3-7.02-download-receipt.json)；[本轮 sources](../../current-updater-evidence/current-updater-asset-audit.json)
- UFU 从偏移 8 至 EOF 依次只有 DATV、PROV、UDID、FDAT、DEND，chunk 边界精确闭合，外 CRC32 `92be8c5f` 重算匹配。FDAT 原始载荷位于原包偏移 132、长 811,876,624；其中既有格式合同为密文 811,876,352 + IV 16 + RSA 签名 256 字节。既有完整解码记录检查了全部 792,848 个块的校验和及 end flag；本轮没有再次取密钥或重新解密，而是核对原件／解码件整哈希与全部解码结构。[本轮 UFU 与 sources](../../current-updater-evidence/current-updater-asset-audit.json)；[旧完整解码回执](../../../fx3-7.02-offline-manifest.json)；[旧解码器源](../../../decrypt_fx3_offline.py)
- FDAT 头 CRC32 `3ec3b1e3` 重算通过。计数为 2：U 槽为偏移 512／长 1,253,376；P 槽为偏移 512／长 0；其余 26 槽逐字节为零。头 512 + U body 1,253,376 + TAR 807,450,624 = FDAT 全长 808,704,512，区间连续，无未解释的末尾或槽外区间。[28 槽原字节、区间账本](../../current-updater-evidence/current-updater-asset-audit.json)
- TAR 起始偏移 1,253,888；本轮独立顺序解析 **155 项、114 普通文件**，全部头校验、成员数据边界和零填充匹配；结尾恰有 1,024 零字节。规范化目录尾斜线后与既有完整 TAR 清单全等。不存在 `0400_updater/`、`0401_updater_sum/` 或 `0200_loader/`；`0700_part_image/dev/` 只有下表五个载荷。原提取脚本确实使用白名单，但本轮结论来自完整 TAR，不来自该白名单。[完整成员及哈希](../../current-updater-evidence/current-updater-asset-audit.json)；[旧提取脚本适用边界](../../../stage2/extraction/extract_partition_images.py)

| 原成员 | FDAT 数据偏移 | 原包中解码后载荷长度 | 本轮 SHA-256 |
|---|---:|---:|---|
| `0700_part_image/dev/nflasha15` | 51,579,392 | 479,846,400 | `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5` |
| `0700_part_image/dev/nflasha3` | 531,426,304 | 31,695,872 | `ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568` |
| `0700_part_image/dev/nflasha5` | 563,122,688 | 209,112,512 | `ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1` |
| `0700_part_image/dev/nflasha7` | 772,235,776 | 5,218,304 | `ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7` |
| `0700_part_image/dev/nflasha8` | 777,454,592 | 22,450,176 | `3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b` |

表中五项均重新计算载荷哈希及 CRC，且与现存分区文件全哈希、旧提取回执匹配。105 条官方 `.sum` 普通文件记录的长度与 CRC32 另逐项匹配，不只验证五个分区。表内偏移是**解码 FDAT 的逻辑偏移**，不是密文文件偏移或真实 eMMC 物理地址。[独立审计](../../current-updater-evidence/current-updater-asset-audit.json)；[105 条 SUM 比对](../../current-updater-evidence/table-and-sum-validation.json)

### Inferences

- 可以否定“7.02 只是旧提取器漏取了一个显式 p1 成员／另一个 FDAT 文件系统槽”的说法。现有包提供的是增量式的设备目标载荷集合；p1 是否沿用历史安装，必须另取实际原件核对，不能由 `up.sh` 相同推定。[区间与成员证据](../../current-updater-evidence/current-updater-asset-audit.json)

### Gaps

- 上述完整性是**容器定义、成员及其边界**完整性，不是每个匿名内存页的语义完整解码。p5 WBI 本轮只整哈希／CRC和边界校验，没有把所有缓存页重建为任意潜藏文件；本轮也没有全语义反编译 114 个普通文件。因此不宣称数学上排除所有可重组成 updater 的匿名字节，而是没有取得可独立使用、可识别的当前 p1 kernel/initrd 工件。
- Sony 官方页、地区 CDN 的另一个同版本包是否采用另一种工程封装，本轮未广泛下载比较。结论严格限定于来源、大小、哈希均明确的这份现存经典 FX3 7.02 整包。

## 当前可恢复哪些启动组件，它们为何不是 p1 rescue 环境

### Takeaway

已从 7.02 p3 实际恢复 MAIN 的 ARM64 `vmlinux.bin` 和 ext2 `initrd.img`，并恢复嵌套 NOR 更新组件。其 initrd 的全部 50 个普通文件与独立 p7 rootfs 完全相同，启动脚本明确 pivot 到 p7，再通过 MAIN 启动链继续；这与旧 p1 的自包含 updater init／UdtrMain／sdfileinput 链不同。[新恢复工件](../../current-updater-evidence/current-updater-asset-audit.json)；[50 文件对照](../../current-updater-evidence/table-and-sum-validation.json)

### Cited Findings

- p3 `/vmlinux.bin`：6,610,952 字节，SHA-256 `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`，含 ARM64 image 头。p3 `/initrd.img`：5,213,184 字节，SHA-256 `5ba4076f0f0765d57767736c824b12ed345a38cbb6541d61546570a4470c9f52`，可作为 ext2 静态解析，152 项／50 普通文件。两份均从固定 SHA 的 p3 FAT 原像只读取出，已保存为不可执行的普通文件。[内核副本](../../current-updater-evidence/p3-main/vmlinux.bin)；[initrd 副本](../../current-updater-evidence/p3-main/initrd.img)；[来源、长度和完整根目录](../../current-updater-evidence/current-updater-asset-audit.json)
- p3 initrd 与 p7 ext2 的所有 50 普通文件字节相同；只有目录形态上的 `/rootfs`、`/initrd`、`/usr/lib` 差异。`/sbin/init` 装基础驱动、`setup_nflash`、`setup_rootfs`；`fstab.root` 指定 `/dev/nflasha7 /rootfs ext2 ro,...`，`setup_rootfs` 使用 pivot_root／chroot 后进入 `/sbin/init2`。[init](../../current-updater-evidence/p3-initrd/sbin/init)；[setup_rootfs](../../current-updater-evidence/p3-initrd/sbin/initrc/setup_rootfs)；[fstab.root](../../current-updater-evidence/p3-initrd/sbin/initrc/fstab.root)；[对照](../../current-updater-evidence/table-and-sum-validation.json)
- `init2` 读 `/proc/udm/upm_bootmode`，其可见条件仅为 `BIS`：该分支对 `/log` 执行格式化后重挂载；普通流程读 `/setting/mode/dmode`，启动 `/usr/bin/bootin.elf`。这些是 MAIN 环境原脚本，不是独立 updater 选择器的完整定义。已把副本路径与危险写分支交给启动请求研究员静态追踪，未执行脚本。[原 init2](../../current-updater-evidence/p3-initrd/sbin/init2)
- 7.02 U-body 为 SquashFS 1,253,376 字节，SHA-256 `62e86fad175e0326969d5f1cea29d780feb496ce8034acd2c9c3954320d8ccaa`，既有完整索引 65 项／58 普通文件；没有 kernel、initrd、`/sbin/init`、`UdtrMain.sh` 或 `sdfileinput.elf`。它含 bodylib、配置、CP body 和执行 helper，是启动后的更新执行组件。该 U-body 与 AP `/bin/udtrbody.bin` 全字节相同，不构成独立 Linux 冷启动环境。[本轮 body 副本](../../current-updater-evidence/original-members/udtrbody.squashfs)；[完整 body 索引](../../../../fx3-color-port-20261027/package-20261028/updater-inventory.json)；[AP 身份与选择边界](../../../../fx3-color-port-20261027/body-load-20261029/image-origin-results.json)
- `0750_nor_loader/loader_nor.tar` 在 FDAT 偏移 799,907,328、长 112,640 字节，内层仅四项：`loader_nor.bin` 101,888（SHA-256 `4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942`）、`LdrBkupList.txt` 650、`pformat_config.txt` 1,274、`loader_nor.md5` 152 字节。配置把该 loader 称为 Loader2，并另外引用 `LdrBkup.bin`、DGU、MIS、TOPPERS、PCIe Patch；因此当前官方更新组件集合不能冒充同机全 NOR／boot0 原始备份。[嵌套索引与哈希](../../current-updater-evidence/current-updater-asset-audit.json)；[原更新配置](../../current-updater-evidence/nor-loader-members/pformat_config.txt)

### Inferences

- MAIN 内核／initrd 的恢复对定位 UDM／UPM 启动请求消费者有价值，但恢复“应用已坏仍能进入 updater”的关键仍在更早的选择器和实际 p1。把本轮 p3 文件改名为 rescue kernel 不会补全这条证据链。
- 当前 NOR loader 是一个可供静态分析的原厂组件；其配置、配套记录及 CP 数据不等于已经具备可冷启动的完整低层恢复包。

### Gaps

- 没有新取得用户机身 p1，也没有证明该机 p1 与 2.04／2.05 任一历史分区相同。未尝试由 MAIN 内核临时拼装独立 updater，也未证明其驱动／DTB／更新库兼容。
- 本轮没有展开 UDM／UPM 接收函数、ud_send_lsi、版本比较或 settings 写入时机；这些已划给并行研究员。这里只提供镜像和原脚本身份。

## 恢复准备下一步精确缺什么，官方包不能替代哪些原件

### Takeaway

下一份最关键缺件是**当前同机 p1 的完整原件及其实际几何**，其次是与它配套的 p2 updater 设置／版本记录。原包已能说明“声明在哪里”，却不能证明“当前装了什么”或“损坏后怎样选择它”。应先形成具体只读获取合同再操作机身，本轮没有任何机身读写。[官方几何](../../current-updater-evidence/tar-selected/0300_partconf/partinf.conf)；[容量核对](../../current-updater-evidence/table-and-sum-validation.json)

### Cited Findings

- 7.02 的 `partinf.conf` 与 `mount.conf` 30 行逐项对应：按 512 字节扇区换算，全部容量相等、分区行连续。p1 从扇区 128 起、49,024 扇区，即 **25,100,288 字节**，类型／角色为 SYSTEM Updater、vfat、无常规挂载点；p2 20,971,520 字节、`/setting`；这些是**包中声明**，不是当前相机实时读回。p1 在几何中存在而在更新载荷中缺席。[原 partinf](../../current-updater-evidence/tar-selected/0300_partconf/partinf.conf)；[原 mount](../../current-updater-evidence/tar-selected/0100_config/mount.conf)；[30 行核对](../../current-updater-evidence/table-and-sum-validation.json)
- 包中五个分区载荷长度均小于配置容量，例如 p3 载荷 31,695,872 对容量 78,643,200、p15 载荷 479,846,400 对容量 524,288,000。不能把这些裁剪后的官方更新像视为真实全分区备份或用其长度确定设备读回范围。[载荷及几何对照](../../current-updater-evidence/table-and-sum-validation.json)
- 既有历史 2.04／2.05 p1 各仅 19,377,152 字节，是历史更新包载荷；它们含独立 kernel/initrd，但来源／版本及长度均不能替代当前 p1 全容量备份。[历史来源与CRC](../../../../fx3-color-port-20261027/input-20261028/original-update-engine-results.json)；[历史 boot 文件索引](../../../../fx3-color-port-20261027/input-20261028/updater-fat-inventory.json)
- 可见的 7.02 AP `up.sh` 第 148／159 行分别解码／写入 `/setting/updater/dat4`；它的历史同字节身份已知。这个手工修改版本分支不证明正常更新成功或中断阶段何时写 dat4／comp，不能用来替代完整版本状态机。[原 AP up.sh](../../../stage2/extraction/files/nflasha15/bin/up.sh)；[原身份](../../../../fx3-color-port-20261027/body-load-20261029/image-origin-results.json)

### Inferences

- **MAIN 失败恢复的最低后续原件合同**：当前 p1 原像／完整 fingerprint，含 kernel、initrd、DTB 与 dat2/dat3；当前 p2 下 updater 的 dat4、mode/mode5、comp／uincomp 等实际状态及来源；实际块映射／透明加密合同。只有在独立选择入口与版本准入同时确定后，才谈官方 7.02 回装测试。上述是准备目标，不是现在已获机身读取授权或已读回。
- 若未来改动仅在 p15 的某个模块，应保存同机原模块和真实加载／WBI 影响；若动到 p3／p7／p5 或 CP／更早引导，恢复合同相应扩大。官方包缺少 p1、p2 个体状态，NOR 更新载荷也不是全低层备份，因此“已有 BODYDATA 就可救所有失败”不成立。

### Gaps

- 仍缺经典 FX3 的 MAIN 无效时独立选择 p1 的入口与结果、当前 p1 实物身份、同版本准入及完整机内恢复回读。此处不重复要求先有修改包，也没有把旧 2.05 条件代码替代当前机身。
- 本轮主机验证仅使用 Python 标准库与已有只读 FAT/ext2 解析器；未运行 Sony ELF／脚本，未构建、启动 VM、接触相机／USB／管理员操作／Windows／UU／GUI、修改原件、广泛新增下载或更改 README／memory。脚本开发中的两次早停分别是 diskutil plist 键名与 TAR 目录尾斜线规范化，均在宿主解析阶段，修正后完整检查通过。[复核脚本](../../audit_current_updater_assets.py)
