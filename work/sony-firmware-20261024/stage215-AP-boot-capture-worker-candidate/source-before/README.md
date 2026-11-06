# FX3 恢复适配工具 0.4

**已实现的第一版是离线镜像工具：识别 FX3 更新分区、生成限定候选、检查改动范围，以及从备份重建原始镜像。** 参考了 A7C II 社区的原件绑定、片段长度保持和逆修改设计，重新绑定到 FX3 自己的原库和函数。代码没有相机传输、管理员启动或刷写入口。

当前在 Mac 上，以 Sony 官方 FX3 2.04、2.05 的原始 p1 载荷完成真实文件闭环。0.2新增本地采集；0.3新增机身侧C工作器候选；0.4把固定C源码与显式入口链接为静态Linux ELF，并在ARM64指令模拟环境中完成三组383块读取和精确还原。**系统调用、内核状态与数据源仍为自建夹具，未在相机上加载或执行；尚未取得或验证你这台7.02机身的p1原件，没有完成真机恢复，也没有包含1080p29.97 H.265功能补丁。** Windows主机运行未验证。

## 可以实际运行的功能

| 命令 | 本地操作 |
|---|---|
| `inspect` | 检查逻辑／已解密的FAT12 p1镜像；验证FAT副本、簇链、长文件名、内核／initrd MD5，识别两份更新库 |
| `build` | 保存完整输入，动态定位SquashFS压缩片段，生成固定长度候选和变换清单；再次解析核对 |
| `verify` | 复核完整原件与候选SHA、全部允许范围、压缩流及新库内容 |
| `diagnose` | 将本地镜像分为原件、候选、已知范围混合或未知状态；不自动修复 |
| `rollback` | 在新目录生成与备份逐字节相同的原镜像；不是向机身写回 |
| `capture-local` | 从已保存的完整本地p1文件逐块读取、留档、关闭来源，再组装和回读镜像 |
| `verify-capture` | 用外部提供的SHA复核完整读取记录、三组清单、383块数据和镜像；不证明机身来源 |
| `assemble-worker` | 解码已保存的三组工作器格式文件，核对请求、精确长度、范围、设备号及CRC，再在本地重组；不加载C代码 |
| `build-worker` | 本机编译固定C／汇编源码，完成限定重定位，生成静态Linux ELF与链接记录；不执行该文件 |

输入只接受本项目内的单链接普通文件，拒绝设备节点、FIFO和符号链接；输出必须使用不存在的新目录，不覆盖原件。中断或失败留下的目录保留，缺少完整manifest的结果会被拒绝。原件、候选和结果文件按0600创建，输出目录按0700创建；不上传。

## 首次复核

无需安装新Python依赖。在当前工作区运行：

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-recovery-adapter
python3 -B -m fx3_recovery --help
python3 -B -m fx3_recovery inspect \
  --input ../../work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1 \
  --out ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-inspect
python3 -B -m fx3_recovery build \
  --input ../../work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1 \
  --out ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-bundle
python3 -B -m fx3_recovery verify \
  --bundle ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-bundle
python3 -B -m fx3_recovery rollback \
  --bundle ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-bundle \
  --input ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-bundle/candidate.p1 \
  --out ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-restored
```

再次运行须换输出目录名。检查报告中的`flashable`、`hardware_validated`和`current_body_p1_identity_verified`始终为false。命令没有`--execute`或`--flash`，不能用上述结果启动机身刷写。

已有本地完整快照时，`build --scope unverified-snapshot --body-tag <64位十六进制摘要>`可以记录操作员提供的分组标记。输入须为25,100,288字节且两库全部匹配；标记不得填原始序列号。**这只是本地关联，不是机身身份验证或采集回执。**默认`reference`只接受两份固定官方历史原件。输入应是`cnflasha1`类逻辑／已解密视图，不是完整BODYDATA.DAT或未经识别的物理密文。

## 0.2 定长读取与留档

`capture-local`只打开本地普通文件，使用`O_RDONLY`和固定偏移读取。固定研究配置为25,100,288字节，分383块、每块65,536字节；三组分别为128／128／127块。**该长度来自已保存的FX3配置证据，不是本次实测相机分区长度。**历史2.04／2.05分发载荷较短，不能直接作为完整输入，工具不会自动补尾。

读取前检查外部提供的完整SHA和文件元数据；每块关联本次随机请求，检查精确返回长度、状态、来源一致性，再保存0600数据和哈希。三组清单按SHA串联。结束时重算来源全SHA，确认来源关闭，重新读取已落盘的383块、组装镜像并回读，最后才写`complete.json`。

调用前写入`read-in-flight`日志。总预算600秒、单次5秒，超期返回的数据拒绝入库；**这些是调用前后的检查，不能中断正在阻塞的系统调用**。不创建超时替代调用、不强杀、不自动重试。未正常返回的调用记为`UNKNOWN_IN_FLIGHT`并保留提供者引用，关闭失败记为`UNKNOWN_CLOSE`；两者均不能形成完整备份。进程退出或主机重启后的实际设备状态没有在本版得到处理或验证。

已保存完整本地镜像时可运行：

```sh
python3 -B -m fx3_recovery capture-local \
  --input <项目内已有的完整p1普通文件> --sha256 <独立保存的完整SHA256> \
  --body-tag <本地分组用64位十六进制标记> --out <不存在的新目录>
python3 -B -m fx3_recovery verify-capture \
  --capture <上一步目录> --sha256 <同一个外部SHA256>
```

这里的外部SHA用于验证已有本地文件及采集程序，不是对首次机身读取提出“必须提前知道机身SHA”的循环条件。首次真实采集仍需实现机身来源绑定、双次一致性检查等独立方案。操作员标签、全文件SHA、读取成功及来源关闭都不等于相机身份认证、服务正常退出或救砖证明。

主机采集目前只提供`RegularFileSource`，内部读取接口预留给后续评审；主机端没有动态插件加载、相机节点打开、服务认证、工作器上传或Sony运行时导入。未来实际相机后端需要另行实现。参见[读取实现](fx3_recovery/capture.py)与[故障测试](tests/test_capture.py)。

## 机身侧工作器候选与0.4链接

[C源码与明确限制](native/README.md)只提供显式函数入口，固定目标为`/dev/cnflasha1`；根据内核分区记录、块设备身份和容量进行检查，不照搬A7C II的设备编号。分区始终O_RDONLY，输出仅限经fstatfs核验的tmpfs新目录。短读、容量变化、来源变化、超期返回、证据写入和关闭失败均拒绝完成；没有preload、构造函数、删除、自动重试或刷写代码。

0.3只有AArch64可重定位对象与Mac系统调用夹具；0.4新增[限定链接器](fx3_recovery/elflink.py)和显式`_start`，生成无动态加载器／外部导入的静态ELF。47项当前本地检查通过，其中ARM64模拟环境实际执行生成的机器码，完整输出三组383块，再完成本地候选和原件还原。Linux系统调用、设备与tmpfs仍是假提供者，未启动真实Linux或FX3内核。

构建只支持当前两个固定源码和5类已观察的重定位，检查操作码、目标、对齐、范围、字段回算及范围外不变；页分为R／RX／RW，栈不可执行。不支持的编译器输出会拒绝，不进行地址猜测、导入补齐或宽松回退。生成文件以0600保存在新0700目录，不自动执行。

```sh
python3 -B -m fx3_recovery build-worker \
  --out ../../work/sony-firmware-20261024/stage188-static-ELF-link-and-explicit-entry/runs/manual-worker-build
```

输出含`worker.elf`、两份中间对象、源码计划及59处链接记录；再次运行须换目录。**可执行文件格式不等于机身可启动方案。** 当前没有上传／启动命令；受审查的机身入口、实际传输、同机绑定、服务归还与Sony内核支持仍待验证，不能将构建物直接上机试运行。

`assemble-worker --windows <第0组目录> <第1组目录> <第2组目录> --returns 0 0 0 --body-tag <64位分组标记> --out <新目录>`仅复核已保存的本地格式。返回码是调用者提供的记录，不是工具独立观察的相机退出证明。即使每组内部一致，分组之间也可能发生内容变化；全部来源、硬件与独立恢复标志保持false。

FX3原日期触发命令固定设置2017年的时间，不接受任意shell文本；原固定库加载分支仍在当前进程中加载libJit.so。本工具没有采用这些路径，也不把终端切换的成功响应当作shell已经开启。[188轮入口核对](../../work/sony-firmware-20261024/stage188-static-ELF-link-and-explicit-entry/launch-route-review.json)。

## FX3 专用改动

第一版配置`fx3-p1-reference-v1`绑定以下完整库指纹，任何不符都会停止：

| 原库 | 长度 | SHA-256 |
|---|---:|---|
| `libsdfileinputupdaterapi.so` | 60,584 | `257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2` |
| `libupdatercorecommon.so` | 72,864 | `b2b066b963a42d96556f811a773579eb16a0358de1b3a9206a1845c0df99bb74` |

前者使用FX3原`isVersionOK`的`0x9fd4`与`VerifySignature`的`0xabf0`，并保留`isModelOK/isRegionOK`字节；后者使用已完全匹配的`0xd208/0xd27c`。A7C II的`0xa0cc/0xace8`没有被移植到FX3。它们是原ELF内已核验的文件偏移，不是运行地址。

**该配置会在离线候选中改变版本／签名检查及核心版本判断；不会生成Sony新签名。** 压缩片段由实际文件系统映射推导，不硬套A7C II的initrd长度、片段偏移或p1chksum位置。重新压缩必须保留原长度并完整解码，额外字节、截断和填充流均拒绝；FAT映射和校验文件之外的字节必须保持原样。

这是恢复与安装通路的参考组件适配，不是完整改机安装器。即使本地快照的库指纹匹配，也只证明组件代码匹配，不能证明它来自指定机身或故障时仍有路写回。

## 下一步接入与限制

尚需补齐当前机身p1的可信来源与组件指纹、实际相机读取／恢复后端、菜单RAM版本门的FX3专用绑定、DAT重封和功能补丁，以及服务退出和独立救援验证。现有两份历史原件不能冒充7.02机身读回。

未知或混合状态会保留并拒绝自动回退；本地重建原件不证明断电后机身能接收它。也没有把standalone sen的USB存活当作独立文件服务：目前GET／SET仍依赖im里的Jiritsu消费者。

[源码与参考说明](NOTICE.md) · [实现](fx3_recovery/engine.py) · [测试](tests/test_adapter.py) · [本轮证据](../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/README.md)
