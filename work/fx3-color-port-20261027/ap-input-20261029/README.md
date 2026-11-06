# FX3 当前 AP 旧文件更新链和加载条件

2026-10-29。**7.02 原应用分区内存在一条值得继续验证的旧文件加载链，但还不能据此正常刷入修改固件。** 已定位 `crypter.elf`、它调用的更新 API、更新镜像的动态库路径及模块登记。原 CBC 包不能直接经过该旧解密器；孤立块转换与头部 CRC 检查已通过，正常入口可达性、完整镜像准入和实际加载仍未验证。

上一轮 [USB 和 UUD 研究](../transport-20261029/README.md)使用历史更新引擎。本轮材料来自 7.02 官方包的 AP ext2 原映像，SHA-256 `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5`。这里的“当前 AP”指该版本原文件，不是用户机身的实时读回。

## 原调用者和模块登记

扫描原 AP 的全部 797 个普通文件、435,648,400 字节，其中 532 个 ELF，找到：

- `/bin/crypter.elf` 导入 `GetCryptFileInputModeUpdater`。
- `/lib/libupdaterufp.so` 保存 `/usr/bin/crypter.elf` 路径及相应进程参数表。
- `/lib/libIMDB.so` 的三个连续重定位槽指向 `libupdaterufp.so`、`udtr_ufp_init`、`udtr_ufp_exit`。

普通 fileinput 工厂的真实名字是 `GetFileInputProductModeUpdater`，不是最初按名字猜测的 `GetFileInputModeUpdater`。两次前置扫描保留为 v1／v2，最终范围包含真实工厂名及上层模块标记。[全部原 ELF 摘要和命中](current-consumer-results.json)

`libupdaterufp` 的原参数表分别描述 `up.sh ver`、`up.sh user`、`crypter.elf /tmp_updater/Firm.dat`、`up.sh ms`。这些只是原数据和调用指令的读取，未执行进程、切换模式或创建机身文件。[原参数与虚槽](current-loader-contract-results.json)

## 旧解密器与现代 CBC 包的差别

`crypter` 的原 main 位于 `0x400bc0`，原 unwind 范围为 864 字节。它经虚表依次调用 `Initialize(FILE_CHUNK)`、`StartWriting`、`Finalize`。三个槽经 ELF 重定位对应到 `CryptFileInputUpdaterManager` 的实际方法；工厂以 action mode 6 构造管理器。

原初始化创建 `MsDecryptorModule`。其基类 `DecryptorModule::decrypt`（`0xa780`）每次对 16 字节调用 `Dec_Scramble`；原 `libupdatertalk.so` 的 `Dec_ScrambleInit`（`0x8c0`）设置 AES 128 位解密 key schedule，`Dec_Scramble`（`0x8d8`）直接调用单块 `AES_decrypt`，没有 CBC 链接操作。原 KeyArray 符号为 32 字节，实际位数参数明确只使用前 16 字节；值仅在内存中使用，输出记录摘要。

对已有官方首个 1 KiB 密文向量应用这条旧规则：

| 对照 | 结果 |
|---|---|
| 与正确原块的前 512 字节比较 | 相同 |
| 后 512 字节比较 | 不同 |
| 正确解密原块送入原 AP `verifySum` | 返回通过 |
| 旧规则解出的原 CBC 块送入同一函数 | 原错误 `0x30002` |
| 将正确原块在内存中重编码为旧 AES 格式，再解密 | 全部 1024 字节恢复，原块校验通过 |

使用宿主 CommonCrypto 做 AES 数学，原 AP 校验 helper 在限定 Unicorn 内执行。只测试一个孤立块，没有保存完整旧格式容器或修改固件。这支持进一步研究格式转换，不能扩大为整包、菜单、色彩或设备准入通过。[格式对照和原函数结果](legacy-format-compatibility-results.json)

## 头部校验和更新动态库路径

实际 7.02 解密头部使用 `UDTRFIRM`、版本字节 `0100`，其保存的 CRC32 与 `[12,512)` 范围计算一致。原头部构造、SetHeader、Check 及小型内部 helper 已执行八组有界检查：两个构造布尔值分别测试原头部、CRC 区损坏、重算 CRC 和 magic 损坏；结果分别为通过、拒绝、通过、拒绝。重算 CRC 的通过只适用于这个头部检查函数。[原头部检查](header-guest-results.json)

恢复的后续关系为：

```text
crypter
  → CryptFileInputUpdaterManager
  → FileInputUpdaterManager StartWriting
  → 所选 FILE_CHUNK 分支的 CRC 检查
  → 旧式块解密和块校验
  → FileInputBodyLoaderModule checkFirmware
  → createBodyImage
  → bodyExecute 的机型检查
  → 打开镜像内的 libupdaterbody.so
```

`FileInputBodyLoaderModule` 的虚槽 `+0x98/+0xa0/+0xa8/+0xb0` 分别解析为 `createBodyImage`、`checkFirmware`、`checkChassis`、`getActionMode`。`bodyExecute`（`0x9064`）挂载 body image、执行机型检查，随后打开 `/tmp_updater/updater/bodyfs/bodylib/libupdaterbody.so`，解析 `GetBody` 和 `ReleaseBody`。这里的后续执行仍有 callback、状态和原生 loader 条件，尚未运行完整流程。[虚槽与路径](current-loader-contract-results.json)、[原函数切片](current-static-results.json)

另核对官方嵌入的 `libupdaterbody.so`，SHA-256 `6582eba530025d17fab81420050433cd998714c922aa4c16fd4d5cdc5a378ee9`，保存七个相关原 factory、执行和 plugin 函数的静态片段。它是同包更新环境的一部分，未加载或执行。[动态库片段](body-loader-selected-results.json)

这些证据把“另一个 CRC 文件 API”接到了具体原调用者和加载路径，仍不能称为已验证的签名绕过。还需恢复上层请求的前置认证和可达性、整个旧格式容器的处理、原生动态库加载政策，以及后续启动和恢复条件。

## WBI 快照的范围

此前原 WBI 的 link-map 记录含 `libupdaterufp`、`libupdatertalk`、`libupdatermedia`，与本轮登记线索一致。但在原先核验的页表根下，UFP 的 ELF 头、动态符号、字符串、代码和只读常量五处读取均返回 invalid descriptor。本轮因此只保留模块名记录，没有确认该快照的相应代码身份，没有为缺失页面填零或宣称初始化已执行。[部分结果](registry-and-snapshot-results.json)、[首次不可读记录](attempts/registry-snapshot-unreadable-first-results.json)

## 尚未达到可刷入条件

这条候选链还没有设备端准入或实际加载证据。完整 FX5 应用／菜单与专有依赖、VENICE 实时 ISP、FX3 正常 MAIN 像素链及有效目标修改包也仍未完成；矩阵、孤立块或头部通过均不代替这些要求。

本轮只执行原件解析、宿主 AES 数学和明确限定的原校验函数 guest，没有本机执行 Sony 程序、挂载固件文件系统、运行原脚本、加载目标 DLL／ELF 或操作相机／USB／手机。没有完整修改包，没有刷写，也未修改另一 agent 的 HEVC／设备／恢复材料。持续目标保持 active。[封存回执](final-receipt.json)
