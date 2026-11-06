# FX3 原始过渡固件与 WBI 保护函数恢复

持续目标仍为 **active**：完成 FX5／VENICE 目标专业功能和完整色彩链替换，并有可复核证据支持修改固件可正常刷入经典 FX3，达到门槛后停在实际刷机之前。**当前没有可刷入包，未完成色彩科学替换。**

本目录承接[上一轮封包研究](../package-20261028/README.md)。Orca 重启后先核对已完成的下载、旧封存材料和进程；没有待重问的问题，没有继续运行的下载／解压进程。修正尚未完成的 WBI2 映射，继续原安装器提取和校验入口研究，没有重跑已经封存的旧阶段。

## 已完成的原件提取

索尼官方 3.00 更新页面仍链接包含过渡安装器和 3.00 安装器的 ZIP。静态读取 ZIP 中央目录，只下载并解压 `01_Update_ILMEFX3V20x.exe`，没有下载第二个安装器，没有运行任何索尼 EXE／DLL。[官方页面](https://support.d-imaging.sony.co.jp/support/ilme/products/ilmefx3/update/v300/ja/win/index.html)

过渡 EXE 长度 1,540,002,320 字节，ZIP 成员 CRC32 为 `ee79e26f`，CRC 和长度均通过。SHA-256 为 `ed2983c4ae9e5299585c8b307d67503bab9ddbc0bb3e8ab86c144d7fd5e699ea`。外层 Sony 容器把 CAB 每个字节取反保存；在 EXE 偏移 `0x6ef5a` 找到长度 1,539,537,813 字节的 CAB，11 个文件夹、46 个文件，各文件夹使用 LZX21。

系统 libarchive 3.7.4 在提取第一个 DAT 到 515,899,392 字节时报 `LZX decompression failed (-25)`。保留失败片段、当时脚本和摘要；两个大文件夹的全部 CAB 数据块头均符合长度和边界约束。随后从维护者固定提交编译任务内独立 libmspack 解码器，正常完成两份 DAT 和一个 DLL；第一个完整 DAT 与失败片段的全部字节一致。该结果排除了本次失败片段已经错解的情形，**未把错误归因于某一已知上游 bug**。[维护者源码](https://github.com/kyz/libmspack/tree/55d501976171397ccd5d5a7a1ca7da065b1d9a06)

| 原始成员 | 字节数 | SHA-256 |
|---|---:|---|
| `FirmwareA1Data_ILMEFX3V204.dat` | 779,108,760 | `774982ecfbeae1cd9d822a2da6599cc390438ae4012b3f9ba8c43e75ec4e9068` |
| `FirmwareA2Data_ILMEFX3V205.dat` | 756,424,088 | `dc411c1e1ea77e1c8614d6045a345d85553e46f60ec9105e6236299a3620740a` |
| `FirmwareUpdaterImg.dll` | 111,392 | `3aa25ddf1768dcc13f2ab231d93b6f0a210dc69be8d93d5b100fcd640e376849` |

见 [ZIP 回执](interim-zip-range-receipt.json)、[安装器成员回执](official-interim/member-receipt.json)、[CAB 索引](cab-index-results.json)、[独立解码结果](cab-mspack-extraction-results.json)和[失败片段对照](decoder-prefix-comparison.json)。只清除了本任务下载的临时第三方参考源码，保留 URL、固定提交、逐文件摘要、本地工具和许可证；没有删除原下载或失败材料。

## 只读随机解密与更新引擎线索

新增 `read_original_fdat.py`，使用上一轮 Apple CommonCrypto 实现读取原 CBC 数据。读取任何明文范围都核对实际涉及的块校验、长度、结束标志和填充；不写完整解密副本、不生成修改封包。对照原 7.02 已完整验证的明文，在 13 个位置检查首块 ECB／CBC、1020 字节逻辑边界、中段和末尾，均逐字节相同。[对照回执](random-reader-validation.json)

2.04／2.05 的完整 UFU 外层 CRC、FDAT 头 CRC 通过，均使用公开格式中的 `key_cxd90057_k0`。分别稀疏枚举 135／134 个 tar 项。**稀疏索引没有检查全部明文块**，回执明确记录实际检查块数；不能将其表述为两份完整明文已全部校验。

两份旧包均含 `0400_updater/dev/nflasha1`，长度 19,377,152 字节；当前 7.02 的 tar 没有这一项。它是继续寻找未覆盖更新输入环境的明确候选，**尚未提取完整明文，也未确认其中存在 sdfileinput**。准备好的 `extract_interim_updater.py` 会按原 `updater.sum` 检查单独提取结果，但运行在取得固定格式源码之前遇到 TLS 连接错误，尚未创建候选分区输出。

公开格式常量只按固定源码 SHA-256 在内存中读取，不另写数值。成功索引之后，直接原站、固定内容镜像、curl 和 web 工具相继遇到连接失败。保留失败记录，没有降低内容摘要校验、关闭 TLS 校验或修改本机网络设置。[稀疏清单](interim-fdat-inventory.json)、[连接失败记录](attempts/network-source-failures.json)

## 从 WBI 原快照恢复可读 SKD 函数

上游作者指出新更新输入组件及受保护的 `libInfraSKD.so` 值得研究；这是一条作者线索，不是 FX3 尾部验证合同的现成证明。[作者 issue](https://github.com/ma1co/fwtool.py/issues/39)

首先以原 `nflasha5.img` 固定摘要恢复 WBI2 的 1,399 条 64 字节区段记录。1,317 个保存区段的累计字节数与头部一致，82 个省略区段保持未知，没有补零；按物理地址排序后无重叠。原记录顺序并非全局升序，最初的错误升序假设及失败脚本已保留。记录中的内核线性别名不冒充用户态 ELF 地址。[WBI2 映射](wbi2-map-results.json)

原 AP 分区的 `libInfraSKD.so` 为 7,611,988 字节，SHA-256 `7d1fbd9a53794def916ca3ff2fc3a00f295268bb0f4ea7c07d0e8356d2840f9b`。磁盘中的六个导出入口跳到保护跳板，后续字节不能直接当作正常函数。根据原 DT_INIT 中的写入地址和长度字段，静态提取内嵌的 1,838,096 字节运行库；没有执行它或调用 dlopen。[内嵌运行库回执](skd-embedded-runtime-results.json)

在 WBI 保存数据中找到同一原 ELF 头后，按 4 KiB 粒度、39 位用户地址假设逆向查找三级页表，得到唯一能够回读该头的链：根表物理地址 `0x40867a000`，库基址 `0x7f73ef9000`。随后做独立身份核对：

- 原 ELF 头和 GNU hash 完全相同。
- 快照的原始位置 `0x198` 对上磁盘扩展符号表的前 144 条完整记录。
- 原字符串前 1024 字节、SONAME 及六个函数名全部相同。
- 六个符号的数值、大小和记录均与原磁盘表相同。

保护后的磁盘把动态表移到了较高偏移；直接假设这些页面在快照仍映射的第一次检查失败。后续改为核对已经恢复到原位置的元数据，没有把不可读页面填零或忽略身份失败。前后脚本和失败说明均保留。[身份核对](skd-snapshot-identity-checks.json)、[页表候选](wbi-page-table-candidates.json)、[恢复结果](skd-snapshot-code-results.json)

恢复出的六段原快照代码均可完整解码，没有数据伪指令：`SKData_Init`、`SKData_Exit`、`SKD_Sign`、`SKD_Verify`、`SKD_SignBufAlloc`、`SKD_SignBufFree`。片段和反汇编在 `snapshot-fragments/`、`disassembly/`。这是原离线快照的静态恢复，**没有执行 SKD、读取实际 ROM／OTP／MMIO、推导私钥、生成签名或连接相机**。

原 `SKD_Verify` 检查输入数组和模式范围，强制摘要选择值 2，接口表的长度为 64、标识为 674，验证参数长度固定 `0x100`。其 helper 处理多个指针／长度段，并构造 RSA 对象。对这些事实与完整 FDAT 尾部消费者之间的关系仍需另行举证。

## 尾部 RSA 探测的负结果

从原快照中的只读区域读取五组 **公开 RSA 模数和指数**，各模数 2048 位、指数 65537；仅记录模数摘要，不复制参数数值。将三份原包的尾部最后 256 字节按大端签名候选，分别尝试五组公开模运算，15 组均未得到有效 PKCS#1 v1.5 填充，因此也没有产生预期 DigestInfo／覆盖范围匹配。[探测结果](fdat-public-rsa-probe-results.json)

这排除了本次具体的“五组公钥＋大端 PKCS#1 v1.5”解释，**不能据此认定尾部不参与验证、不是其他签名／加密材料，或可以重算块校验后直接刷入**。也不能把存在 `SKD_Sign` 当作已获得私钥或签名能力。没有读取硬件派生的私有参数，没有输出任何新签名。

进一步遍历同一页表根的保存表页，并从 SKD 对应记录验证 glibc 五字段 `link_map` 的前后互指关系，读出 129 个模块记录，128 个名字可读、1 个名字不可读。可读名包括 SKD、InfraCryptCore 和旧 updater 库，没有 `sdfileinput`。页表遍历中还有两页不在可读保存范围，普通页映射计数也不等于这些页内容均被保存；没有声称恢复完整内存或所有进程。[模块清单](snapshot-link-map-inventory.json)

## 当前边界与下一步

下一步先完成两份旧包内 19 MB 更新引擎分区的只读提取和原 CRC 核对，再查其文件格式／输入组件；另可用已恢复的页表及模块基址继续读取受保护 CryptoCore 的原静态代码。实际 CBC／尾部输入消费者、验证材料的算法与覆盖范围、修改包准入和启动合同仍未恢复。

FX5 完整公开专有固件与 VENICE 完整 ISP／RAW 色彩链的来源门槛没有因这次 SKD 恢复而消失；前几轮已有 FX3 ACESREC709 外观和有界原指令实验仍不能替代完整 VENICE 移植、正常主录像素或机身验收。也未修改另一 agent 的 HEVC／USB／恢复目录或状态文件。

本轮脚本只读取固件／快照和输出研究材料；相机、USB、手机及刷写动作均为 0。[验证与封存回执](final-receipt.json)将固定原件、旧封存材料和本轮交付物的摘要；持续目标保持 active。
