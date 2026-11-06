# 专业设备更新组件：实际 SVU 读取器与 VENICE 格式边界（2026-10-29）

**新增取得并静态解开索尼 SNC toolbox，定位其真实升级 DLL；原指令验证了一个 SVU 文件头门槛，但尚未找到 VENICE `type3/type4` 的读取入口，仍无可正常刷入 FX3 的完整替换固件。** 本轮把 SNC 工具作为可能共用的读取器参考，不把 SNC 固件、监看 LUT 或桌面处理当成用户要求的 FX5／VENICE 完整专业系统和色彩链。

开始前核对外盘 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，逐项回读[上一轮](../donor-loader-20261029/README.md) 32 个封存文件。所有新增材料位于本阶段；没有写另一 agent 的工具、目标状态或设备。实际相机、USB、网络相机、更新器、Windows MSI 引擎均未操作。

## 从官方旧安装包取得实际组件

[当前索尼日本下载页](https://www.sony.jp/snc/download/)明确标注 SNC toolbox 已停止提供，旧下载详情页返回 404。本轮取得[2019-07-19 的官方详情页档案](https://web.archive.org/web/20190719190522/https://www.sony.jp/snc/download/service/snc_toolbox.html)，从其原链接恢复地址，并从索尼当前服务器下载成功，HTTP 200：

[SNCToolboxV1.6.1.0.zip](https://contents.sony.jp/professional/snc/SNCToolboxV1.6.1.0.zip)

这是公开页面留下的具体地址；未猜测下载目录。网页当前不再列出软件与原文件 URL 此次仍可读取，是两项不同的观测。

| 原件／提取结果 | 字节数 | SHA-256 |
| --- | ---: | --- |
| 官方 ZIP | 119,665,922 | `ec18e66965423093fab8edf535446524b8b6df49a51300e2a0382fdd3f867b2e` |
| `SncToolbox_Setup.exe` | 119,508,225 | `52feb1eac680e2da5ed17da333e979b9985b293a363596cf2bc1f35764cce1a7` |
| `SNC toolbox.msi` | 121,112,576 | `ad631b592ff73733136e74f56ecd9fe6a61e1074767e7ab63575c46bc90c8549` |
| MSI 内 CAB | 115,710,745 | `04d0d4067a27d0f0342912685b8fe9aa2917e6067a114bae3006eb55150e5e57` |
| `sncverup_tool.dll` | 905,216 | `a96aecd93432bded2d90a116338082fffe42d302af899bd18f547d2e91e365c8` |

ZIP 四成员 CRC 全部通过；三份 PDF 仅检查 ZIP CRC／元数据，没有阅读或运行。EXE 是 PE32，末尾 `ISSetupStream` 位于文件偏移 `0x103400`，包含三个成员。参照 MIT 许可的 [ISx 源码](https://github.com/lifenjoiner/ISx/blob/3c4177ddd0519244490ff8e78d380110c8dacdc8/ISx.c)，编写有界数据读取器，恢复两个 INI 和上述 MSI；三个 zlib 流都完整结束、Adler 校验通过，成员解析恰好到 EXE 末尾。这里处理的是通用 InstallShield 安装格式，**不是 Sony 私有固件解密成功**。

MSI 只以只读复合文件解析：76 个流、无解析告警，取得一个 CAB。所选 26 个 SNC／Sony 组件、库和数据文件合计 173,615,339 字节，全部按数据提取；包括真实的 `sncverup_tool.dll`、`snccore_tool.dll`、`snccgiw_tool.dll` 和 `sncverup_tool.svu`。没有加载 DLL、执行 EXE／MSI 自定义动作或创建设备会话。

## 实际读取代码提供的边界

按 [Microsoft PE/COFF 格式](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)静态读取五个原组件的导入／导出。升级 DLL 有 23 个命名导出，包括 `sncvSetFile`、`sncvGetFileSetting`、`sncvCheckMatching`；诊断字符串指向 `svu_file_header_0x01` 和 `svu_file_control_0x01`。函数存在和错误文字本身未被算成 VENICE 解密证据。

在 DLL 原 VA `0x1001fbb0` 定位了连续 25 字节、六条 x86 指令的检查：依次比较输入第 0、1、2 字节与 `0x56`、`0x55`、`1`。也就是 `VU` 与版本字节 `1`。两个签名字节不符时转到原拒绝分支 `0x1001fd3f`；版本不同到 `0x1001fbc9`；通过这三字节只到下一阶段 `0x1001fc19`，后面的时间戳／解密没有执行。

Unicorn 中只运行这 25 个原字节，显式提供只读 16 字节输入，指令地址白名单和停止点固定；没有模拟成功的读文件／解密服务。9 组案例结果：

| 输入 | 原分支结果 |
| --- | --- |
| 同包 SNC `.svu` 原开头 | 通过前缀，到时间戳处理前停止 |
| 合成 `VU`＋版本 2 | 不支持版本分支 |
| 合成错误首字节／次字节，各一组 | 签名拒绝分支 |
| VENICE V2.01、V6.30 原内层开头 | 均为签名拒绝分支 |
| VENICE 2 V3.92、V4.10、V5.00 原内层开头 | 均为签名拒绝分支 |

六份原输入（SNC 数据和五份 VENICE 负载）全文件重新核对 SHA，并逐字节确认其前缀与 guest 输入一致。代码和输入在 guest 中保持不变。这个结果只证明**所定位的 SVU 分支不能直接读取现有 VENICE 内层开头**；未运行完整 `sncvSetFile`、构造器、时间戳或解密器，也不能据此断言整个工具不存在其他读取路径。通过 `VU1` 更不是整个 SVU 有效、更新成功或修改包可刷入。

另对 26 个原组件检查七个具体包装标记的 ASCII／UTF-16LE／UTF-16BE，未命中 `BinaryPackProperty`、`ProductCodeVersion`、`DATA23213` 等。它是精确字符串搜索的范围结果，不能排除无字符串实现，也没有把 SNC 的解密错误文字等同于 VENICE 的算法、密钥或 IV。

## VENICE 同版本公开构建资料

从[官方 MPC-3610 V6.30 OSS 页](https://oss.sony.net/Products/Linux/B2B/MPC-3610_V630.html)直接列出的地址取得 BusyBox 与 RPM 两份源 RPM，分别 2,332,015 和 10,971,632 字节。仅从归档读取 23 份 spec、配置和补丁，没有执行任何 `%prep`／`%build`／安装步骤。

重要区别：`sony-target-dev-rpm.spec` 第 33／57 行说明该包只包含 `popt`；第 112、119 行构建和安装也限定到 `popt`。因此，公开包名称中的 RPM 不能当成已经取得相机固件安装器的证据。BusyBox 的 12 个列出补丁涉及常规功能／安全修复；所查五个私有封装标记未在这 23 份文件中命中。本轮没有扫描全部嵌套上游源码或声称所有公开源码都不存在读取器。

## 保留的失败与工具范围

- 系统 `bsdtar` 无法直接识别 EXE；之后按已识别的 InstallShield 结构读出成员，没有运行安装器。
- OLE 解析依赖首次下载 wheel 超时；改从维护者固定 `v0.47` 提交取得源码，两个已成功下载的模块保留，只重取失败的许可证。依赖只在本任务路径，未修改系统或另一 agent 的 venv。
- `bsdtar` 列出 CAB 成功，但提取第三个选定成员时报告 `Invalid CFDATA`。两个已完成成员保留。随后使用[7-Zip 官方下载页](https://www.7-zip.org/download.html)直接链接的 macOS 26.05 工具，复核两份原提取结果逐字节相同并取得其余选定成员；未把失败时的输出当成有效 DLL。7-Zip 只放本阶段 `tools/`，无系统安装。
- 一次临时反汇编输出的起点回退过宽，终端输出已截断；后续证据只保留上述固定 25 字节、六指令和有限输入，不依赖那份大范围输出。

ISx 参考提交、OLE 解析器提交／许可证、工具下载 URL／摘要和失败记录均保留。上述工具、输入材料和暂存代码仍属在研任务资料；不是交付给机身的修改固件。

## 完整目标状态

本轮实际取得一个可分析的专业设备更新组件，并用原代码限定其已定位分支的格式范围，未将“有解密器”误写成“能解 VENICE”。接下来仍需取得真正的 `BinaryPackProperty`／type3/type4 加载器或相应明文系统来源，不能在缺少依据时直接套用 SNC SVU 算法。

FX5 私有系统／完整菜单、VENICE 内层明文与完整传感器校准／WB／解马赛克／降噪／ISP、FX3 主录绑定、目标修改整包准入、正常启动及独立恢复均未通过。本轮不输出修改固件，不执行实际刷机。持续目标保持 active，尚未达到用户要求的停止条件。

## 证据入口

- [官方现页回执](host-source-pages.json) · [历史页回执](host-archive-pages.json) · [旧包下载](host-tool-download.json)
- [安装器结构](host-installer-structure.json) · [实际 InstallShield 解包](setup-stream-unpack.json) · [MSI 流与 CAB](msi-streams.json)
- [26 组件提取／搜索](host-component-review.json) · [五组件 PE 接口](host-PE-interfaces.json)
- [原头部指令验证](svu-header-guest-results.json) · [六份完整输入摘要](svu-header-source-pins.json)
- [公开源包回执](public-source-rpms.json) · [23 文件检查](source-patch-review.json)
- [验证封存程序](validate_and_seal.py) · [最终回执](final-receipt.json)
