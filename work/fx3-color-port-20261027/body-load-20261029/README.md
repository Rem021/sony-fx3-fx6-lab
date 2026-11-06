# FX3 旧加载链的镜像选择条件

2026-10-29。**旧文件更新链会组装输入包中的更新镜像，但不一定加载该镜像。** 原代码检查 `/root/IAMUPDATER`：存在时选择刚组装的 `/tmp_updater/updater/bodyimg`，不存在时选择预置的 `/usr/bin/udtrbody.bin`。这一条件限制了前轮候选链的适用范围，不能从“组装成功”直接推出上传文件中的动态库会被加载。目前仍没有可正常刷入的 FX5／VENICE 色彩替换固件。

本轮接续[原更新入口与上传边界](../entry-20261029/README.md)。只使用已有官方包原件和本任务有界解释执行，没有操作相机、USB、更新模式、机身文件或另一 agent 的 HEVC／恢复工作。

## 原函数组装出的真实镜像

原 `CryptFileInputUpdaterManager::Initialize` 以 action mode 6、布尔参数 1 创建文件加载器。本轮对原 `BaseBodyLoaderModule` 使用相同两个构造参数，执行原构造、头部 SetHeader／Check、文件系统信息读取及 `createBodyImage`（`0x95a0`）。

输入是官方 7.02 已解密 FDAT，SHA-256 `694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768`。原头部检查通过，原组装函数产出 1,253,376 字节，SHA-256 为 `62e86fad175e0326969d5f1cea29d780feb496ce8034acd2c9c3954320d8ccaa`，与[此前独立提取的更新文件系统](../package-20261028/updater-inventory.json)完全一致。处理后的明文位置为 1,253,888。

这里的环形输入是只读明文适配器，目录和文件输出是内存接收器，mutex 是替身；没有执行原解密器、完整管理器和并发线程流程，也没有原生写文件或保存新的固件容器。该结果证明这段原消费代码恢复了相同镜像，不证明整个输入格式或刷机准入。[原组装结果](body-assembly-guest-results.json)

## 组装完成后选择哪个镜像

原 `bodyExecute`（`0x9064`）先调用虚槽 `+0x98` 组装镜像，再检查运行标志。其调用的 `0xc1a8` 是 `__xstat` 包装函数，传入路径为 `/root/IAMUPDATER`。原分支关系是：

| stat 结果 | 选择的镜像 |
|---|---|
| 0，标志存在 | `/tmp_updater/updater/bodyimg` |
| 非 0 | `/usr/bin/udtrbody.bin` |

随后原函数准备挂载点 `/tmp_updater/updater/bodyfs`，请求挂载所选镜像；此前恢复的动态库路径位于该挂载点下。也就是说，后续使用哪一份 `libupdaterbody.so` 取决于这一镜像选择，而不只取决于上传包的内容。

两组离线检查执行原构造、头部检查、组装、线程运行标志和 `bodyExecute` 前半段，只把 stat 的存在／不存在作为明确的输入替身。两组均先恢复出相同的官方镜像，然后分别选中上述两条路径，均在 Mount helper 入口停止。没有执行 mount、机型检查、dlopen 或镜像内动态库；替身中的标志状态不是机身状态。[两组原分支结果](image-selection-guest-results.json)

## 机内预置镜像的来源

重新校验 AP ext2 原分区 SHA-256 `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5`，读取全部 797 个普通文件。分区内 `/bin/udtrbody.bin`（inode 80976）恰好也是 1,253,376 字节，上述 SHA-256 完全相同。这里 `/bin/udtrbody.bin` 是 AP 分区内的相对路径；原运行选择字面值是 `/usr/bin/udtrbody.bin`。

这说明官方 AP 已提供相同的预置更新镜像。若运行标志检查失败，输入包即使已组装出 bodyimg，原分支仍选择预置路径；不能据此把旧文件入口当作可加载替换动态库的入口。[镜像来源与原选择片段](image-origin-results.json)

对 AP 原文件搜索 `IAMUPDATER`／`udtrbody.bin`，命中 `up.sh`、`libupdatercorecommon.so` 和 `libObj.so`。原 `libObj` 的两个静态窗口分别关联运行版本查询和初始化时保存 stat 结果；它们不是创建标志的证明。这两个地址没有匹配到导出符号或 unwind 函数边界，因此仅保存有界窗口，不称为完整函数或完整写入者审计。[libObj 片段](obj-marker-reference-results.json)

**AP 分区不是完整的 Linux 运行根目录。** 这次扫描既不能证明相机上没有 `/root/IAMUPDATER`，也不能证明存在它；不能用分区内未列出该路径、字符串命中或明确提供的 stat 替身替代运行状态证据。

## 复核和剩余条件

本轮完成一组原镜像组装和两组原选择分支检查。原核心库 SHA-256 `6441a8c33e586685bcd3fcc9b6b43803c1c5660fbbca13e3ebd8239f7677b8fb`；新提取的原 `libObj.so` SHA-256 `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae`。首次 libObj 探查未找到函数边界时生成的空窗口已保留为失败尝试，随后重新保存真实的 512 字节窗口，没有把空结果作为证据。[验证记录](validation-results.json)、[封存回执](final-receipt.json)

尚需恢复正常运行环境中的标志状态和来源、整个旧输入容器及后续真实装载条件。与此同时，完整 FX5 专有功能／菜单、VENICE 实时 ISP、FX3 正常 MAIN 像素链及有效目标修改包仍未完成。上述局部复现没有改变“目前不能刷入”的结论，也未达到用户指定的停止研究条件。
