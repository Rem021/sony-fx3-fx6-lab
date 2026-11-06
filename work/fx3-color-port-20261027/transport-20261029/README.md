# FX3 历史更新引擎：USB 与文件输入的签名合同

日期：2026-10-29。**在实际取得的 2.04／2.05 原更新引擎中，普通 USB 的 UFP 路径和 UUD 文件路径也会在写入处理函数中验证尾签名。改换传输方式，目前没有形成允许修改固件刷入的证据。** 本轮没有操作相机，用户机身当前 7.02 的同名程序尚未读回，不能将历史二进制当作当前机身实测。

## 原件与入口

原件来自此前已完成 CRC32、FAT、SquashFS 和文件摘要核验的 [2.04／2.05 更新分区](../input-20261028/README.md)，来源是 Sony [官方 3.00 更新页](https://support.d-imaging.sony.co.jp/support/ilme/products/ilmefx3/update/v300/ja/win/index.html)所链接的过渡安装器。本轮只读其中四个输入 API 库；两版的对应文件均逐字节相同：

| 原文件 | 字节数 | SHA-256 |
|---|---:|---|
| libupdaterapi.so | 105,984 | `2c2915ecb998e2dfc1cbe90400b469db7a1aefa9669eb03e7f062591b022b2a7` |
| libuudfileinputupdaterapi.so | 52,288 | `f8a622fd2b038080cf682b22febe60e379b916f72d8890687b1a6b2109c5182e` |
| libcryptfileinputupdaterapi.so | 27,088 | `06ee88247f9d1da34f28aebbe9ff5b355b661ce9645e1b83c6ee6a0bf292d17a` |
| libfileinputupdaterapi.so | 27,232 | `7f8ab4a0f2b1a92497cce8cc655eb59c62cdd6fb2760722ee9b614b2d67ea3a6` |

原 `common.src` 和 `execute_ufp.sh` 将 mode 3 接到 `sauu -m`，mode 6 接到 `sauu -s`，mode 5 接到 `sdfileinput.elf`，mode 7 接到 `uudfileinput.elf /mnt/firm.dat`，其他分支接到 `sauu`。这是原脚本内容，没有运行脚本、切换模式或执行其中 mount／模块／写入操作。

## USB 与 UUD 的实际签名调用

| 组件 | 原函数 | 地址 |
|---|---|---:|
| libupdaterapi | UpdaterManager::Initialize | `0x10c24` |
| libupdaterapi | UFPDecryptorModule::exec_write_firm | `0x12ea8` |
| libupdaterapi | SignatureVerification::VerifySignature | `0x13574` |
| libuudfileinputupdaterapi | UUDFileDecryptorModule::execWriteFirm | `0x8774` |
| libuudfileinputupdaterapi | SignatureVerification::VerifySignature | `0x97f4` |

USB manager 的原初始化在 `0x10d44` 构造 UFPDecryptorModule，并存入自身 `+0x38` 字段。其写入处理在 `0x12f70..0x12fb4` 组装签名参数、调用验证；UUD 对应逻辑位于 `0x882c..0x8870`。两处都以总输入长度减 256 作为签名覆盖长度，以末 256 字节作为签名。成功分支之后，再以总长减 272 定位 16 字节 IV。

两份实际 verifier 都先验证公钥信任，再读取 `/etc/VerificationKey.pem`，调用 SHA256，随后调用 `RSA_verify`，摘要类型 `0x2a0`、摘要长度 32。失败进入 `0x30002` 异常路径。公钥路径来自各 caller 的实际只读字符串，不是根据导入名称推测。[原指令、PLT 解析和摘要](input-path-static-results.json)

签名调用之前的虚调用 `+0xa0` 经构造函数、GOT 符号重定位、vtable `+16` 和实际槽重定位核对：USB 解析到 `WaitForFirmwareCopyCompletion` `0x12c28`，UUD 解析到继承的相同方法 `0x7cc8`，不是已经执行固件载荷。[构造及虚槽回执](input-dependency-and-vtable-results.json)

这里不声称“所有解析和解密都在签名之后”：UFP 另有 `exec_chk_guard` `0x12cf0`，能先解密和检查头部。该前置检查与写入时的整段签名验证分别存在，不能用“有前置解密”推导签名已被绕过，也没有在本轮证明任何可利用的解析缺陷。

## CRC 文件 API 与可达性边界

`libcryptfileinputupdaterapi.so` 的 `CryptFileInputUpdaterManager::verifyFile` `0x3f88` 在相应 action mode 下执行 CRC 检查；这个函数本身不是 RSA 校验器。此前当前 AP 环境的另版库也已经静态记录过 CRC／FDAT 查找，二者来源不同，不混用偏移。

对本原 initrd 的 usr/bin、usr/lib 内 70 个普通 ELF 建立 `DT_NEEDED` 图。从 `sauu`、`sdfileinput.elf`、`uudfileinput.elf` 出发，均没有通过该图到达普通 fileinput 或 cryptfileinput API 库。三个入口实际分别依赖 updaterapi、sdfileinputupdaterapi、uudfileinputupdaterapi；不能因为其他库存在一个 CRC 检查就宣称这些入口可免签写入。

这只是所查原文件的静态依赖图；未解析的运行库名字完整列在回执，`dlopen`、可选模块、其他环境或其他入口仍未排除。当前 AP cryptfileinput 的实际调用者、完整初始化／准入／写入合同仍值得继续追踪。本轮没有把“图中没到达”当成绝对不可达，也没有验证可刷入的替代通路。

## 结果与下一步

上一轮已经用真实公钥对 7.02、2.04、2.05 原包完成数学验签；本轮补上了历史 USB／UUD 的直接调用证据。CRC、CBC 重编码、USB 传输和尾部 RSA 属于不同层，前几层可重建并不自动获得有效签名。

完整 FX5 菜单／功能和 VENICE 实时色彩链仍未移植；正常 MAIN 像素绑定、有效修改镜像的安装／启动和同机恢复合同仍缺。本轮不缩小目标，未输出完整修改固件、未运行 Sony 程序、未操作机身／USB／手机，未干扰另一 agent 的设备与恢复工作。目标保持 active。[核验及封存](final-receipt.json)
