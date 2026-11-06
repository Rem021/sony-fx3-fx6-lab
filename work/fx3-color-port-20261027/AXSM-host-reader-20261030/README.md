# AXSM Drive 原始读取器与 AXS-R7／VENICE 格式边界

**实际取得并拆读索尼 AXSM Drive Utility 3.5.0，定位原始固件读取函数；已验证的读卡器头部判定会拒绝两份 AXS-R7 原件和现有 VENICE type3 内层。本轮没有解开它们的主体，没有可正常刷入 FX3 的完整移植包。**

上一轮[两版 AXS-R7 原件及有界头部模型](../AXS-R7-donor-loader-20261030/README.md)的 28 个封存文件逐项核对通过，本轮没有重下两版固件，也没有重复原来的线性模型拟合。继续保持完整 FX5 专业菜单／功能及 VENICE 实时色彩链目标。

## 官方来源与实际取得

[索尼 AXSM Drive Utility 3.5.0 说明](https://www.sony.com/electronics/support/software/00380433)列出的适用产品是 AXS-CR1、AXS-AR1、AXS-AR3，并说明它能更新 AXS 存储卡固件、恢复部分损坏的录制片段。这提供了检查真实更新读取器的具体理由，不能据此认定它包含 VENICE 机身更新器或完整 RAW／ISP。

中国官方目录查询 `AXS-AR3`、类型 `SONY_CASCH_DOWNLOAD_SOFTWARE`，返回 3.5.1／3.5.0／3.4.0 三个条目；进一步的 `findOne` 也返回成功，但下载地址是索尼支持页，没有直接二进制链接。[实际目录](official-catalog.json)、[后续来源探查](source-discovery.json)

根据[索尼同目录公开发布说明的地址](https://www.sonystyle.com.cn/minisite/cross/app/download/pro/broadcast_production/AXSMDriveSoftware_ReleaseNote_3_5_0_en.pdf)与官方明确列出的 ZIP 文件名，推导一个同目录候选 URL。先范围读取，服务器实际返回 206 和 ZIP 前部；再以该响应 ETag 取得完整 ZIP，200、长度及前缀逐字节匹配。因此这里的**候选地址是推导后由服务器确认的**，不是中国目录直接给出的二进制链接。未读取 PDF 内容。

[实际官方 ZIP](https://www.sonystyle.com.cn/minisite/cross/app/download/pro/broadcast_production/AXSMDriveSoftware_3_5_0_mac.zip)，15,207,327 字节；三个普通 ZIP 成员的 CRC32 均通过。提取的 DMG 为 14,168,975 字节，SHA-256 `b370ea33a9a677b9c9a2f28ca3c8bcff1f2ec18b0bbb5fd2dfe58102c8131947`。[取得及 CRC 记录](package-acquisition.json)

## 安装包始终只作为数据读取

复用已固定 SHA 的 7-Zip 26.05，仅进行 DMG 归档列表与单成员读取，没有挂载映像、执行 Sony 应用、启动安装器或运行脚本。取得原 `AXSMDriveSoftware.pkg`，13,355,017 字节。

`bsdtar` 列表存在路径重复拼接现象，原输出保留但没有用它生成提取路径。改按原 XAR 目录和 heap 偏移读取：75 项，压缩 TOC 的 SHA-1 及每个普通数据流的 archived／extracted SHA-1 全部匹配。这里是内部完整性校验，未宣称 Apple 安装签名链已经验证。[XAR 记录](XAR-structure.json)

六个组件 Payload 都是 gzip／旧 ASCII cpio，gzip 流完整结束，CPIO 解析到 `TRAILER!!!` 后只剩零填充；合计保存 439 个普通文件。符号链接及特殊节点只记录，不创建；权限不按包内值恢复，脚本不运行，安装位置不采用系统实际路径。[目录及逐文件 SHA](payload-inventory.json)

组件包括主应用、监听器、挂载 helper、驱动及 Firmware。Firmware 组件实际有：

- 五份 AXS 存储卡 `.ascr` 固件。
- `AR3_01_20_684.bin`、`AR1_01_20_686.bin` 两份读卡器固件，各 7,526,400 字节。

这些不是 FX5／VENICE 机身供体。没有更新存储卡、读卡器或机身，也没有修改系统安全策略。

## 读取器原代码

主应用的原 `libAxsMemContorlLib.dylib`（原拼写如此）整体 SHA-256 为 `a5fe60af34fff1bc434cc033769377c1e4f4027ec620df7edd5574d7753ac424`。与监听器里的同名文件整体 SHA 不同，按各自来源分别固定，未将二者当作同一文件。

只读解析 ARM64 slice 的原 LC_FUNCTION_STARTS、符号和跳板，完整捕获五个函数，共 5,928 字节：

| 函数 | 原 VA | 字节数 |
|---|---:|---:|
| `checkFileMode` | `0x1dbc` | 996 |
| `MemFirmwareUpdateEx` | `0x2d90` | 1152 |
| `AXSMemControl::R5FirmwareUpdate` | `0x6c14` | 968 |
| `AXSMemControl::CheckNewMemFirmware` | `0x948c` | 1920 |
| `AXSMemControl::ReadDriveFirmwareFile` | `0x9d0c` | 892 |

`ReadDriveFirmwareFile` 打开文件、请求读入 512 字节，读不足时走错误分支。其后在 `0x9e68` 读取缓冲区偏移 8 的八字节，要求等于 `UPDATE ` 加 NUL，才到 `0x9e84` 后续分支。原库另有明确的 `.ascr` 扩展名检查、`AXS-AR1 UPDATE` 与 Intel HEX `:02` 分支，不能仅因文件也是 `.bin` 就套成 AXS-R7 或 VENICE 解密器。[完整函数及调用引用](reader-contract.json)

R5 更新函数中恢复了 `fopen/fread/fwrite` 和介质控制调用的原位置；其存在不等于主机已经具有 VENICE type3/type4 解密器。本轮只读取这些指令，未执行该函数或设备控制 helper。

## 原始格式判定的有界验证

在隔离 Unicorn RAM 内只执行 `0x9e68..0x9e80` 七条原指令。输入为实际原件的 512 字节前缀；明确把“已有 512 字节输入”作为这个独立判定的前提，没有伪造文件读取成功返回值，也没有执行完整读取函数。

| 原始输入 | 头部判定结果 |
|---|---|
| 同包两份读卡器固件、五份存储卡固件 | 7/7 到标记匹配后的分支前停止 |
| AXS-R7 V6.00、V6.01 | 2/2 到标记不符的错误日志分支前停止 |
| VENICE V2.01 实际 type3 内层 | 到同一标记不符分支前停止 |

十份原输入全量 SHA 重新核对，70 条原指令执行完成；原代码、输入前缀和 SP 保持不变，未声明内存访问立即拒绝。匹配这个标记**不表示整个读取器接受文件**，也未执行错误日志、异常展开、解密或更新。[原始判定回执](original-header-gate-results.json)

该结果明确排除的是这里已经定位的读取分支，不能扩大成“整个 AXSM 软件所有路径绝无其他解密器”。本轮没有根据函数名称或字符串就宣称取得了 VENICE 读取器。

## 保留的开发问题及整体验收

静态采集时的断言分别发现了同名库内容不同，以及 N_STAB 调试符号与真正定义符号重名。两个问题都在捕获输出和 guest 执行之前停止；按实际主应用来源选择，并排除调试记录后，五个函数完整捕获。没有用失败采集产生的片段做验证。原件、旧封存、失败探查和有重复路径的列表均保留。

本轮新增了真实可分析的专业设备组件与确定的格式边界，下一步仍需取得 AXS-R7 或 VENICE type3/type4 的实际读取器及主体明文。FX5 完整专有系统、VENICE 传感器标定与实时 ISP、FX3 RAM／RAW 适配、整套专业菜单到主录像素、精确修改整包、当前 7.02 准入、正常启动及独立恢复均未完成。九项整体验收保持原样；实际刷机前停止的要求继续有效。
