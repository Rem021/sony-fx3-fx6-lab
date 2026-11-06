# FX3 SD 更新入口和官方尾签名

**已确认正常 SD 更新包的尾部是 RSA-2048／SHA-256 签名，覆盖全部 FDAT 密文和其后的 16 字节 IV。当前仍没有完成 FX5／VENICE 完整色彩链替换，也没有可正常刷入的修改固件。**

此前[尾部研究](../tail-20261028/README.md)未解释最后 256 字节。本轮取得真实 SD 更新输入组件，用其官方公钥对 7.02、2.04、2.05 三份原包验签全部成功，并用独立宿主机 OpenSSL 复核 7.02 的覆盖边界。这将“重新加密后能否保留原尾部”的问题收敛为一个明确门槛：修改签名覆盖的数据后，需要有效的新签名，或另行验证允许修改镜像的安装／启动通路。

## 原始更新引擎已经完整拆读

两份原过渡固件来自上一轮已验证的索尼 3.00 官方 ZIP，提取原 `0400_updater/dev/nflasha1`，均为 19,377,152 字节，通过各自 `updater.sum` 的 CRC32。[官方来源页](https://support.d-imaging.sony.co.jp/support/ilme/products/ilmefx3/update/v300/ja/win/index.html)

| 版本 | 原分区 SHA-256 | 原 CRC32 |
|---|---|---|
| 2.04 | `e5b71cc24bf5232c2e182a979b60c5f080dcbabe2775b32214dc0f394cf53c67` | `cc3a8d60` |
| 2.05 | `ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591` | `4c6a5739` |

分区为 FAT12，包含 SquashFS 初始化文件系统、内核、设备树和配置。两份 `/p1chksum` 中的四条内核／initrd MD5 记录也全部匹配。MD5 是原件内部完整性层，与下面独立验证的 RSA 签名分别记录。[分区回执](original-update-engine-results.json)、[FAT 提取](updater-fat-extraction-results.json)、[原启动成员校验](original-boot-md5-results.json)

初始化文件系统各枚举 342 项，提取 216 个普通文件，合计各 35,523,243 字节。符号链接和设备只记录，普通文件保存为不可执行数据，没有挂载或运行原程序。网络读取解析依赖失败后，改用本任务无外部依赖的 SquashFS 4.0／gzip 只读解析器；先对照上一轮独立 PySquashfsImage 的 65 项结果，完整复现 58 个普通文件的 SHA-256、符号链接目标和所有模式，再拆读两份新 initrd。[独立对照](squashfs-reader-oracle-results.json)、[完整目录与文件摘要](original-initrd-inventory.json)

关键组件在两版中逐字节相同：

| 原路径 | 字节数 |
|---|---:|
| `/usr/bin/sdfileinput.elf` | 10,296 |
| `/usr/lib/libsdfileinputupdaterapi.so` | 60,584 |
| `/usr/lib/libInfraSKD.so` | 8,020,712 |
| `/etc/VerificationKey.pem` | 451 |

这正是作者曾指出的新更新输入研究入口。本轮用实际原件接上了该线索，没有把作者对其他机型的研究当作 FX3 兼容证明。[作者原文](https://github.com/ma1co/fwtool.py/issues/39)、[ELF 元数据](original-input-component-inventory.json)、[两版比较](original-initrd-version-comparison.json)

## 实际 SD 校验路径

原 `execute_ufp.sh` 在 SD 加密更新模式下预加载 `libInfraSKD.so`，运行 `sdfileinput.elf`。原 ELF 的依赖和导出符号把控制接到 `libsdfileinputupdaterapi.so`。

| 原函数 | VA | 恢复的行为 |
|---|---:|---|
| `SDDecryptorModule::execWriteFirm()` | `0x95b8` | 等待原数据复制完成，组装签名信息并验证，成功后才进入后续 CBC 解密与逐块校验 |
| `SignatureVerification::VerifySignature()` | `0xabf0` | 检查公钥信任，读取 `/etc/VerificationKey.pem`，计算 SHA-256，调用 `RSA_verify` |
| `SignatureVerification::verifyKey()` | `0xa9a8` | 计算 PEM 文件 SHA-1，经 OSAL 服务取得预期公钥哈希并比较 |
| `SDDecryptorModule::decrypt()` | `0x9418` | 首 512 字节执行原 ECB 处理，其后调用 SKD 服务解密 |

`execWriteFirm()` 把输入总长度减 `0x100` 作为签名覆盖长度，末 `0x100` 字节作为签名。后面再减 `0x110` 取出 IV。因此覆盖包含密文及 IV，签名本身除外。`VerifySignature()` 的原调用参数为摘要长度 `0x20`、摘要标识 `0x2a0`；失败进入原异常路径，错误码 `0x30002`。[原片段与 PLT 名称](sd-input-static-results.json)

虚表指针经原构造函数及 ELF 重定位核对：签名前的虚调用 `+0xa0` 是 `WaitForFirmwareCopyCompletion()`，其中是互斥量／条件变量等待，不能误认为已经执行待更新的载荷。[虚表](sd-input-vtable-results.json)、[构造及前置分派](sd-preverification-dispatch-results.json)

这些是历史官方更新引擎的原代码，尚未读回用户机身当前安装的更新引擎。三份原包的数学验签结果则直接覆盖当前研究的 7.02 原件。

## 三份原包的签名和覆盖范围均已验证

从两份原 initrd 中取得同一份官方 **公钥**，公钥文件 SHA-256 为 `8281413b5607446939613e07d020b2c7d8ee2371349099de56bc8288f7be0a43`，模数 2048 位、指数 65537。使用只读 DER 解析、公开 RSA 模运算及 SHA-256，对三份原签名恢复 PKCS#1 v1.5 DigestInfo。

| 原包 | 被签名的字节数 | 签名验证 |
|---|---:|---|
| 7.02 | 811,876,368 | 通过，完整密文＋IV |
| 2.04 | 779,108,368 | 通过，完整密文＋IV |
| 2.05 | 756,423,696 | 通过，完整密文＋IV |

尝试仅密文、IV 前置、UFU 外头加入等候选，只有“完整密文后接原 IV”匹配。每包另在内存中分别改变密文起始、中段、末字节和 IV 的一个字节，12 例均不能再匹配原签名；没有保存完整修改包或生成新签名。[全部数值结果](official-key-rsa-verification-results.json)

另以宿主机 LibreSSL 3.3.6 的 `openssl dgst -sha256 -verify` 独立验证 7.02：

- 原密文＋16 字节 IV：退出码 0，`Verified OK`。
- 原密文、去掉 IV：退出码 1，`Verification Failure`。

这是原始数据的宿主机密码验证，没有执行 Sony 更新器、SKD、机身程序或任何写入流程。[独立验证回执](native-openssl-verification-results.json)

## 公钥信任和 SKD 签名入口需要分清

PEM 文件的 SHA-1 信任比较与 FDAT 的 SHA-256 签名是两层。原 `verifyKey()` 使用服务 ID `0x025906be`、消息操作 1 读取预期哈希，比较 20 字节；此官方 PEM 的 SHA-1 内没有 NUL。本轮没有建立可通过字符串提前结束来替换该公钥的方法，也没有读取实际 ROM／OTP 的内容。

之前从当前 WBI 恢复的 SKD 回调注册在同一服务 ID。静态回调操作 1 可接到相应索引查找，但当前 WBI 的 SKD 与历史 initrd 的 SKD 是不同二进制，不能把相同接口当作已在机身执行的完整信任链。[回调片段](skd-key-trust-callback-results.json)、[索引代码](skd-key-lookup-results.json)

官方 FDAT 公钥的模数，与此前快照中 `SKD_Sign` 的五组公开 RSA 模数均不相同。存在 `SKD_Sign` 导出函数没有证明它可以生成 FDAT 所需签名；未读取或推导任何私有 RSA 参数。[公钥家族对照](rsa-key-family-comparison.json)

本轮也从原快照恢复了 CryptoCore 的两个导出入口，五处元数据核对通过；实际 SD 签名函数已经定位在更新输入库，后续应以此直接调用证据为准。[CryptoCore 恢复](cryptcore-snapshot-results.json)

## 可刷入门槛仍然开放

正常 SD 更新路径已确认有完整内容签名层。只重算 CRC、块校验或 CBC 密文，无法把修改包变成已通过此层验证的包。仍需研究有效签名能力或其他可验证的安装／启动通路，以及 FX3 的机型、版本、启动和恢复合同。

作者在 A7 IV 上公开了通过附件接口串行启动进入自制 fastboot 的研究，并称该机 eMMC 分区使用 AES-XTS、没有分区签名校验。这提供另一条研究线索；其测试对象是 ILCE-7M4，当前没有 FX3 的相同入口、分区写入、启动和恢复实证，本轮未下载或执行启动载荷。[作者仓库](https://github.com/DavidBuchanan314/ILCE-7M4-RE)、[适用范围记录](alternative-install-source-review.json)

完整 FX5 专有菜单／功能、VENICE 传感器标定和实时 ISP 实现、FX3 主录像素与缓存／RAW 适配仍未完成。本轮未新增 FX5 整机包或已解密 VENICE 专有内层，未将以前恢复的 FX3 ACESREC709 外观改称为完整 VENICE 移植。下一步继续查独立安装／启动条件和目标色彩实现；完整目标保持不变。

所有原件与旧封存材料保留，另一 agent 的 HEVC／USB／恢复文件未改动。相机、USB、手机及刷写动作均为 0，持续目标 **active**。[最终核验与封存](final-receipt.json)
