# 第一代 VENICE 官方供体 V6.30：外层解包与 type3 边界（2026-10-29）

**新增取得并解开第一代 VENICE 官方包的 ZIP／tar 外层；私有内层仍未解开，没有可正常刷入 FX3 的整套替换固件。** 新供体内层标为 `type3`，与先前 VENICE 2 的 `type4` 不同。本轮把调查重点放回完整供体，既有 FX3 配置链不重跑，完整菜单／功能及色彩链目标保持。

开始前复核外盘 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，[前轮默认参数封存](../dmm-backup-20261029/README.md) 的 26 个文件逐项校验。VENICE 参考工作树 HEAD 仍为 `28f74ffe76ee845ec7b51cf4ae5229a56688a4bd`，分支 `codex/venice-color-fidelity`；仅只读查询与复用原件，未改该工作树。没有操作机身、USB、手机、真实 IPC、更新器或另一 agent 的设备／恢复工具。

## 新供体的官方来源

本轮实读[索尼日本 VENICE（MPC-3610）更新页](https://www.sony.jp/ls-camera/update/VENICE.html)，该页列 V6.30、页面注明 2023 年 1 月、约 188 MB。实际下载 URL 从原 HTML 的 form action 取得，未猜测 CDN 路径：

[MPC-3610_V630.zip](https://download.pro.sony/22/12/KJBBLlo_bA/MPC-3610_V630.zip)

| 原件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| 官方 ZIP | 188,874,442 | `7e2a1135653fb17d9b6ec741e316e90cd5f53c07cde32959ca0c513342e6be25` |
| `MPC-3610_V630_firmware.bin` | 187,985,920 | `f27a0c8ef9a3841964b7ee1fa2dcbdc91830451536c2469459b81293a183dc78` |
| `VENICE/DATA23213` | 187,973,304 | `93d01601322e3d1931a76b1c6f4f3bfdfb9a0745cfc0ec4eecb253c694b30d5c` |

ZIP 内 5 个条目的 CRC 全部通过；固件 `.bin` 与同包 MD5 文件一致。MD5 用于同包完整性对照，不能代替来源或修改包签名。原下载 HTTP 头、时间、SHA 和页面原件均保留。

## 外层已经实际解开，私有内层未解开

`.bin` 是未压缩 tar，包含根 `property.xml`、`VENICE` 目录、`VENICE/DATA23213` 和内层 `property.xml`。所有普通成员已按原 tar 边界提取并记录 SHA；没有运行成员或安装脚本。

内层 XML 标明 `ProductID=VENICE`、`href=VER630`、`enctype=type3`。此前 VENICE 2 三版的 ProductID 是 `BERLIN`、内层为 `type4`。这建立了一个不同的完整供体封装入口，未证明两者算法或密钥相同，也未证明已能读取其中的菜单／ISP。

新内层的首 1 MiB 熵约 7.999834 bit/byte；所查 ELF、XZ、SquashFS、UBI、CPIO、tar、ZIP 标记未命中。11 个 gzip 三字节候选与 19 个 bzip2 三字节候选经过有界检查，没有得到有效完整压缩流。另有 1 个 zstd magic，按[维护者的帧格式规范](https://raw.githubusercontent.com/facebook/zstd/dev/doc/zstd_compression_format.md)检查：单段帧声明内容／窗口为 57,726 字节，首 RLE 块却声明展开 322,747 字节，超过该帧块上限，结构不成立。没有因未使用位被置位而拒绝它，也未把随机 magic、部分解码或高熵当作解密成功。

与先前 VENICE 2 V3.92/V4.10/V5.00 原件逐一重新核对摘要和尾部后，四份负载均满足：

```
文件长度 = ceil(末尾倒数16字节处的 little-endian u64 / 8) * 8 + 296
```

这是新的跨代封装关系。它没有指定加密区域、分组算法、IV、密钥、摘要或签名的位置与含义。本轮未做盲目密钥尝试、未搜索私有签名材料，也未把 type3/type4 名称当成算法说明。

## 同版本公开源码的检查

实读[官方 MPC-3610 V6.30 OSS 页](https://oss.sony.net/Products/Linux/B2B/MPC-3610_V630.html)，取得其直接列出的两个源码压缩包：

| 源码包 | 压缩字节数 | 遍历成员 | 扫描文本文件 |
| --- | ---: | ---: | ---: |
| `linux-2.6.29-patched-arm.tar.gz` | 64,118,371 | 20,849 | 18,155 |
| `linux-2.6.29-patched-armv7a.tar.gz` | 63,626,489 | 19,934 | 17,759 |

两份顶层 Makefile 均标 Linux `2.6.29.6-rt24`。按文件类型及单文件大小界限扫描源码，未找到所查 `BinaryPackProperty`、`ProductCodeVersion`、`DATA23213`、`enctype="type3"/"type4"` 标记。这只是这些内核源码中的精确标记结果，不能扩大为全网不存在解包器、所有私有代码不存在或密码算法已被确定。

另提取并阅读四份相关平台源文件：

- `memoryDriver.c`：提供保留内存地址换算及 `pgprot_noncached` 映射。不能仅凭源码包存在就认定 VENICE 正常使用的具体 SoC、DDR 芯片或 RAW 路径，也未形成可直接复制到 FX3 的 ABI。
- `phyadr.c`：物理地址／映射接口，未证明完整图像缓冲分配或传感器读取。
- `csi_datalink.c`：实际调用 `spi1_csi_fdx_rw` 并使用 GPIO 握手，未形成 CMOS RAW 获取入口。
- `switch-vup.c`：外设／版本更新寄存器操作，未恢复 `DATA23213` 的私有 type3/type4 解包器。

完整压缩包和所选源片段均只放本任务 `work/`，没有构建、加载内核或运行源代码。

## 当前完整目标与下一步

本轮取得一个此前本任务未持有的官方完整供体包，并确认其外层、type3 内层和跨代尾部关系；没有把公共内核、桌面显影库或监看资源冒充完整相机 ISP。接下来需要定位 type3 的真实解析／加载实现，优先核对更早的官方供体或实际加载器证据；FX3 的正常备份选取、MMU 映射和真实分配链仍保留待接。

完整 FX5 私有系统、VENICE 内层明文／传感器校准／WB／解马赛克／降噪／ISP、整套菜单移植、MAIN 像素绑定、目标修改整包准入及正常启动／独立恢复均未通过。目标保持 active，未输出修改固件，未达到用户要求的停止条件，实际刷机不执行。

## 文件

- [官方页捕获](capture_source.py) · [来源回执](official-source-page.json)
- [下载程序](download_package.py) · [下载回执](download-receipt.json)
- [实际解包](unpack_package.py) · [成员与校验](package-unpack.json)
- [内层结构检查](probe_payload.py) · [候选与跨代关系](payload-structure-results.json)
- [zstd 候选结构验证](check_zstd_candidate.py) · [结构拒绝结果](zstd-candidate-results.json)
- [源码检查](inspect_oss.py) · [源码包回执](OSS-kernel-review.json)
- [平台接口区分](review_platform_sources.py) · [四份源文件证据](platform-source-review.json)
- [验证与封存](validate_and_seal.py) · [最终回执](final-receipt.json)

封存前第一次核验错误预期所有 magic 均零命中，失败促成上述 zstd 候选的独立结构检查；原探测 JSON 保持不变，未封存的报告已更正。失败记录见 `attempts/zstd-zero-hit-assumption.json`，不计通过结果。
