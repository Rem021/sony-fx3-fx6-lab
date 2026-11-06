# FX3 可刷入条件：官方更新环境、CBC 重编码与原校验器

用户于 2026-10-28 指定“可以刷入时停止研究”。持续目标已建立：完成目标功能和色彩链替换，并有可复核证据支持修改固件可正常刷入 FX3；离线模拟不作为完成，达到门槛后停在实际刷机之前。当前目标仍为 active，**没有可刷入包**。

本轮从此前的[色彩资源绑定](../binding-20261028/README.md)转向封包与准入问题。新增三项结果：官方更新环境完整拆读；CBC 算法的六个独立块重编码与原密文逐字节相同；原 AP 长度／校验和函数的 17 组有界执行通过。**尾部 256 字节的验证合同、完整更新准入和启动行为仍未恢复。**

## 官方更新环境不是普通应用分区

固定原件 `fx3-7.02-decrypted.fdat` 的偏移 512、长度 1,253,376 字节是一份 SquashFS 4.0 更新环境。以有界内存视图读取，枚举 65 项记录，提取普通文件合计 3,151,747 字节；符号链接只记录，不创建，设备记录不创建，不挂载文件系统，不执行提取件。

主要组件包括 `libupdaterbody.so`、`libupdatercommon.so`、`uc_crc32sum.elf`、`pformat.elf`、`ud_cp_firmup.elf`、`udtrcp.bin` 和更新流程脚本。完整清单、原件摘要及路径见 [updater-inventory.json](updater-inventory.json)，解析器版本／下载摘要见 [parser-source-receipt.json](parser-source-receipt.json)。解析器仅作为本轮隔离读取依赖使用，不安装到共用环境；成功运行后删除本任务下载的 wheel，保留 URL 与摘要以便复现。

配置 `config/config.xml` 对 `part_image_sum/part_image.sum` 调用 `us_crc32sum.sh`；普通分区映像清单因此有明确的 CRC32 层。更新环境还有前端、备份、loader、NOR loader 等独立步骤。脚本中的写入、格式化、加载模块、挂载和启动指令均只作为原文件读取，未在 Mac 或相机执行。

这些脚本位于更新流程内部，不能替代输入文件的完整准入检查，也不能据此认定重算 CRC32 就能正常刷入。原 `nor_loader_writer.sh` 的 CP 写入分支还取决于机型／启动设备信息；脚本内存在此路径不代表用户的 FX3 当前运行该分支。

另从已验证的原 AP ext2 分区选取 11 个更新／密码相关库，单独提取到本目录，保留分区哈希、inode、文件哈希及符号清单，见 [verifier-library-inventory.json](verifier-library-inventory.json)。现有原分区、其他 agent 的文件和所有旧封存材料保持原样。

## 加密算法已有可复核的实现结果

上游固定提交 `3955d7890fc38daf942bb52827599bfe35de4a14` 的 `AesCbcCrypter.encrypt()` 明确抛出 `Encryption not supported`。该事实只是上游实现状态，不表示 CBC 算法本身不可逆，也不能直接证明存在无法解决的签名限制。该版本的解密器在尾部取 16 字节 IV，并跳过剩余 256 字节。[固定源码](https://github.com/DavidBuchanan314/fwtool.py/blob/3955d7890fc38daf942bb52827599bfe35de4a14/fwtool/sony/fdat.py)

本轮使用 Apple CommonCrypto 的 AES 函数，对官方包中的六个独立 1 KiB 密文块做实验，涵盖第 0／1／256 块、中点、倒数第二块和末块：

- 从已验证 FDAT 原件取回对应有效载荷，重建 16 位和校验、长度／结束标志和 `0xff` 尾部填充。
- 第一个块保留其前 512 字节的旧 ECB 处理，其余使用 CBC；非首块使用原前一块的末 16 字节作为局部验证 IV。
- 六个重建密文均与官方原块逐字节一致，解密也回到同一原数据。
- 每个样本另改一个字节并重算块校验，均可完成本地重新加密／解密往返。输出仅为不可独立刷入的 1 KiB 实验向量。

见 [cbc-vector-results.json](cbc-vector-results.json)及 `experimental-vectors/`。使用的公开格式常量只在内存中读取，输出保留来源和摘要，不另复制其数值。

这确认了被测试的 ECB／CBC 重编码和逐块校验；没有创建完整修改 FDAT 或 BODYDATA.DAT。局部向量使用原块边界和原前块密文作为 IV，不冒充一份内容改变后、全程重新链接的完整 CBC 流。

尾部 256 字节仍作为未解释验证材料：其算法、覆盖范围、密钥来源和实际消费函数均未恢复。本轮没有验证其为 RSA 签名，也没有证明可以保留旧值或省略它。

## 原 AP 校验器的实际行为

在原 `libupdatercorecommon.so` 内执行这些 AArch64 函数：

| 原函数 | VA | 本轮恢复的行为 |
|---|---:|---|
| `DecryptorModule::calSum()` | `0xa8a0` | 累加块头校验字之后的 511 个半字，按 16 位取模 |
| `getHdEndFlag()` | `0xa8c8` | 取标志的 bit 15 |
| `getHdDataSize()` | `0xa8d4` | 以 `0x0fff` 掩码取长度 |
| `getHdSum()` | `0xa8e0` | 读取原校验半字 |
| `verifySum()` | `0xa8e8` | 拒绝长度 0／大于 1020 或校验不匹配 |

17 组实验共执行 46,672 条原指令：六个原数据样本通过，六个不重算校验的损坏样本进入原异常分支；另外检查长度 0／1021 和三个保留位组合。原错误码为 `0x30002`。异常在 `__cxa_throw` 入口明确停止，没有把终止模拟说成真实异常展开、更新恢复或返回成功。

三个带 bit 12／13／14 的组合在重算校验且低 12 位长度有效时通过这个单独 helper。这表明原 helper 与公开解包器的 `0x7fff` 长度掩码并非完全同一合同；**不代表整个更新流程接受这些组合**。完整调用返回检查保存寄存器、SP 和栈哨兵，未映射访问或未声明执行入口立即停止。

原 `libcryptfileinputupdaterapi.so` 另有 `searchFDAT`、`verifyFile` 和 `CrcChecker`。本轮固定了其原片段与 PLT 引用，但尚未从实际初始化、文件对象到最终更新建立完整执行路径。见 [original-block-checker-results.json](original-block-checker-results.json)和 [19 份源片段](static-source-results.json)。

## 排除名称相似导致的误判

`libInfraCryptCore.so` 含 CodeMeter 保护及通用验证入口，尚未建立它与 FDAT 尾部的调用关系。不能因名字包含 verify 或 RSA 字符串就称其为固件签名检查器。

`libCryptoController.so` 的符号属于 `DefInfraVericLiveStreaming`，目前作为直播密码模块线索排除，没有混同为更新解密器。

原 WBI 映像的 `BODYDATA`／`FDAT` 和密码 API 字符串位置已记录为[后续候选](wbi-verifier-candidates.json)；它们不是已经恢复的函数、运行时映射或当前机身状态。下一步从实际输入消费者追第四代 CBC 和尾部验证，继续核对启动时 CP／AP 原件校验的真实边界。

上游 A7 IV 研究称其分区使用 AES-XTS 且没有分区签名校验。这是 A7 IV 的作者实测背景，不能直接替代经典 FX3 的更新或启动结论。[作者原文](https://github.com/DavidBuchanan314/ILCE-7M4-RE)

## 持续目标与复现

本轮把“上游工具不能 pack”的问题细化为：块重编码已经实测；完整尾部验证与更新／启动准入仍待恢复。同时，整套目标色彩链、正常主录输入、运行时选择字、元数据和像素验收仍按[上一轮边界](../binding-20261028/README.md)继续研究，没有将当前已有的 ACESREC709 外观当作完整 VENICE RAW／ISP 替换。

使用现有 Python 环境依次运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/package-20261028/unpack_updater.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/package-20261028/extract_verifier_libraries.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/package-20261028/cbc_vectors.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/package-20261028/original_block_checker_guest.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/package-20261028/static_sources.py
```

首次脚本会按固定 URL／SHA-256 下载隔离解析器，成功后删除该 wheel。脚本只写本轮目录，不运行旧阶段 main 或提取的相机程序。[最终检查](validation-results.json)、[封存回执](final-receipt.json)、[开发失败说明](development-notes.json)。机身／USB／手机操作为 0，持续研究目标仍未完成。
