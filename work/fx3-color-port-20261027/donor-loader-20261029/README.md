# VENICE V2.01 旧供体取得、封装反例与 FX3 加载器补查（2026-10-29）

**新取得并实际解开 VENICE V2.01 官方固件的 ZIP／tar 外层，私有内层仍未解开；尚无可正常刷入 FX3 的整套专业功能／色彩链替换固件。** 旧包提供了封装长度关系的反例，纠正了把此前四个样本的共同现象推广为通用规则的风险。本轮没有运行索尼程序、操作相机或生成修改固件。

## 来源与实际下载

[索尼 V2.01 官方条目](https://www.sony.com/electronics/support/professional-cameras-digital-cinema-cameras/mpc-3610/software/mpueus00000921)仍能从搜索索引读到版本信息，但直接 HTTP 读取失败。尝试内置浏览器时返回 `The browser access host is unavailable`；这是本机工具服务缺口，没有将其解释为网页或固件不存在。

通过公开网页档案 API，取得[2025-10-30 的上述官方页快照](https://web.archive.org/web/20251030193220/https://www.sony.com/electronics/support/professional-cameras-digital-cinema-cameras/mpc-3610/software/mpueus00000921)。其嵌入的软件条目保留原索尼下载 URL。去掉档案服务的重写前缀后，从**索尼当前服务器**成功下载，HTTP 200；没有猜测 CDN 目录，也没有从第三方取得固件二进制。

[官方 ZIP 直接地址](https://download.pro.sony/FNGP/watcha/MPC-3610_V201.zip)

| 原件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `MPC-3610_V201.zip` | 170,041,914 | `c6f5a3ad1a71234af265430b50ef87b29c8c7bba16d5c2e8edd4fb58d47f00d7` |
| `MPC-3610_V201_firmware_SSB.bin` | 169,625,600 | `67e63286fa84f9e2b13412237492d222ac027f51b68c102b1c9c4103dcf0c0c5` |
| `VENICE/DATA23213` | 169,621,368 | `498d047ca2f6f11d54c502a399e2c5a9f4740e6fae4913eba1aaaf486349c785` |

ZIP 五个条目 CRC 全部通过；固件与同包 MD5 相符。MD5 文件中记录的构建文件名比 ZIP 内固件名多出版本／时间字段，校验的是固件实际字节，未按文件名推断同一性。两份 PDF 只做 ZIP CRC／成员元数据验证，未提取阅读或执行；其余 `.bin`、`.md5`、`Readme.txt` 原样保存。

外层仍是四成员、未压缩 tar。根 `property.xml` 指定 `multiproduct`／`VENICE`，内层 `VENICE/property.xml` 指定 `multiversion`、`href=VER201`、`enctype=type3`。三个普通成员均按 tar 边界实际提取，未挂载或执行任何内容。

另取得 2020-09-30 日本更新页档案，其中显示 V5.02 的原下载地址；本轮没有继续下载 V5.02，也没有声称它已经解包。日本最新消息页中 V2.01／V2.10 的历史条目均指向目前复用的 `VENICE.html`，不是独立保留的旧包页。

## 旧包带来的有效反例

此前[四样本记录](../donor-venice1-20261029/README.md)均满足 `N = roundUp8(L) + 296`，其中 `N` 为内层长度，`L` 为末尾倒数 16 字节处的 little-endian u64。原四份观测仍然成立，已封存文件保持不变。

新增 V2.01 得到 `N=169621368`、`L=169621057`，按 8 字节上取整后的余量是 **304**，并非 296。因此，**不能把旧关系作为所有版本的解析规则**。

| 原负载 | XML 类型 | `N − roundUp8(L)` | `N − roundUp16(L)` |
| --- | --- | ---: | ---: |
| VENICE V2.01 | type3 | 304 | 296 |
| VENICE V6.30 | type3 | 296 | 296 |
| VENICE 2 V3.92 | type4 | 296 | 296 |
| VENICE 2 V4.10 | type4 | 296 | 296 |
| VENICE 2 V5.00 | type4 | 296 | 288 |

两个 type3 样本符合 `roundUp16(L)+296`，三个 type4 样本符合 `roundUp8(L)+296`；这是有限样本的区别，尚未成为已恢复的格式定义。不能据此指定密码算法、加密区、密钥、IV、签名或摘要的位置，也没有对未知明文进行盲目密码／密钥尝试。

V2.01 私有内层首 1 MiB 熵约 7.999837 bit/byte。所查 ELF、XZ、SquashFS、UBI、CPIO、tar、ZIP、zstd 标记没有命中。9 个 gzip 三字节候选和 8 个 bzip2 三字节候选经有界解码检查，均未形成有效完整压缩流。该结果没有恢复菜单、可执行系统或 ISP，也没有将高熵直接等同某种加密算法。

## FX3 文件系统补查与读取实现缺口

本轮把先前选取文件的 ASCII 搜索扩展到四个固定原镜像中的**全部普通文件**，分别检查五个标记的 ASCII、UTF-16LE、UTF-16BE：`BinaryPackProperty`、`ProductCodeVersion`、`DATA23213`、`PackageType`、`multiversion`。

| 原文件系统 | 普通文件 | 扫描字节 | 精确标记命中 |
| --- | ---: | ---: | ---: |
| AP `nflasha15` | 797 | 435,648,400 | 0 |
| 初始根文件系统 `nflasha7` | 50 | 4,598,505 | 0 |
| AV `nflasha3` | 9 | 25,682,089 | 0 |
| CP `nflasha8` | 10 | 18,192,220 | 0 |
| 合计 | 866 | 484,121,214 | 0 |

所有输入镜像核对已固定 SHA，逐文件记录路径、大小和 SHA；不跟随符号链接，不扫描空闲区／slack，不把 WBI 的缺失页填成假数据。这只能排除上述具体字符串，不能排除无字符串、枚举实现或混淆过的解析器。

[fwtool 维护者说明](https://github.com/ma1co/fwtool.py/blob/master/README.md)列出 FDAT、Msfirm、DSLR、ASH 格式；它没有给出本次 `BinaryPackProperty`／type3 的读取路径。未因说明未列出而断言代码或全网一定不支持。公开 issue-list API 请求出现 SSL EOF，未取得列表内容；相关检索也没有给出可复核的 type3 实现。本轮未运行该工具、未下载新第三方可执行程序。

## 对完整目标的影响

已增加一个真实、来源可追溯的早期官方供体，并发现类型／版本相关的封装差异。**尚未获得 type3/type4 内层明文或其实际读取器。** FX5 私有系统和整套菜单缺口本轮也未补齐。

因此，完整传感器校准、白平衡、解马赛克、降噪、ISP 及主录像素链仍不能提取迁移；FX3 的正常绑定、目标修改整包准入、启动和独立恢复也未通过。保留完整菜单／功能及色彩链目标，不以 LUT、桌面显影片段、字符串或离线模拟替代。

下一步应优先寻找同类 type3 封装的实际加载器／明文系统来源，并用本轮反例约束格式解析；不能仅通过继续扩大 magic 或盲目密码枚举来宣称解密。本轮属于新增供体与纠正解析假设的进展，目标保持 active，未达到“可以正常刷入时停止研究”的门槛，实际刷机不执行。

## 可复核文件

- [官方访问记录](early-pages.json) · [日本历史原页](japan-history.json)
- [网页档案取得程序](archive_sources.py) · [档案来源回执](archive-sources.json)
- [下载程序](download_early_package.py) · [下载回执](early-download.json)
- [实际解包程序](unpack_early_package.py) · [成员及 MD5 结果](early-unpack.json)
- [内层检查及反例程序](probe_early_payload.py) · [五原件比较](early-payload-structure.json)
- [FX3 全普通文件搜索](scan_fx3_markers.py) · [范围及逐文件摘要](fx3-whole-filesystem-markers.json)
- [维护者 API 尝试](maintainer-issue-review.json) · [工具访问缺口](access-gaps.json)
- [验证与封存程序](validate_and_seal.py) · [最终回执](final-receipt.json)
