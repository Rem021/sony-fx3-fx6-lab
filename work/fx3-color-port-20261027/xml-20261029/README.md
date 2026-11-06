# FX3 原 XML 解析、可选配置回调与插件分派

2026-10-29。**原预置更新库确实能够从提取目录载入可选 XML，并经原键匹配、队列与插件生成系统调用请求。** 本轮把上一阶段的 XML 替身换成当前 FX3 AP 原 `libul_xml.so`，并接上原 `ConfigKeyTag::PostExecute`。这缩小了候选路径的缺口，但仍不证明完整外部输入能到达它，也没有可正常刷入的 FX5／VENICE 色彩替换固件。

接续[标志缓存、文件提取与可选配置](../marker-20261029/README.md)。没有操作机身、USB、恢复会话、原生 Sony 库、mount 或原更新脚本；未产生可供用户刷写的新固件容器。

## 原 XML 来源

只读校验官方 7.02 AP ext2 分区 `nflasha15.img`，SHA-256 `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5`，按 inode 从 `/lib/libul_xml.so` 提取 72,784 字节，SHA-256 `22e19c05a5816b6d358a8d037297a9472cc53230c2045051b830316c59902acd`。未挂载文件系统。

解释执行使用这份 XML 库、原预置 `libupdaterbody.so`，以及前阶段核对过 StringHandler 字节等价的当前 AP `libupdatercommon.so`。映射源 ELF 段并解析原重定位，不执行原生动态加载。原文件、导入和导出清单见[来源](xml-source.json)，实际进入的 87 个唯一函数体及 23 个复核片段见[原函数契约](xml-contract-results.json)。这不是实际机身加载器身份的证明。

## 十组原逻辑检查

| 检查 | 结果 |
|---|---|
| 只有原官方配置 | 官方键能匹配，补充键和未知键不能匹配 |
| 加载有效的普通测试 XML | 原 `LoadUserConfig`／`DomDocument::loadFile`／`Parse` 成功，补充键能匹配，官方键仍匹配 |
| XML 不完整 | 原加载返回 0 |
| 文件不存在 | 原加载返回 0 |
| 官方配置键经过原队列和插件 | 到达 `system()` 请求入口，模块为原 `us_crc32sum.sh config file` |
| 补充配置键经过原队列和插件 | 到达相同请求入口，模块为无执行权限文本测试所用名称 `probe.txt` |
| 未知键经过原队列 | 不产生系统调用请求 |
| 原 ConfigKeyTag 收尾，有效文件存在 | 原代码组合根目录及 `config/uconfig.xml`，经原虚槽载入、匹配，继而到系统调用请求入口 |
| 原 ConfigKeyTag 收尾，文件缺失 | stat 失败后跳过可选文件，不请求打开它，也不产生测试键调用 |
| 原 ConfigKeyTag 收尾，文件存在但 XML 损坏 | 原代码到达异常抛出边界，错误码 `0x30002`；未执行原生异常展开 |

前三类检查分别记录在[XML 加载和匹配](xml-guest-results.json)、[队列及插件分派](dispatch-guest-results.json)、[原配置收尾回调](post-config-guest-results.json)。测试补充配置只声明一个无 guard、无异步线程属性的普通 proc，没有执行任何模块。

## 已接通的局部链与明确替身

原 `XmlConfigHandler::Initialize` 创建原执行队列、空闲队列和线程记账对象；随后原 XML 文档和 DOM 处理、字符串比较、`CheckGuardResult`、`checkGuardResult`、`executeGuard`、队列出入、`Plugin::Execute` 和 `ShellPlugin::Execute` 实际解释执行。这里所选 proc 无 guard 子节点，不能由此宣称真实 guard 程序已执行或其返回结果已验证。`pthread_create` 未获模拟器允许，也没有真实线程。

有效请求仍含 `UPDATER_ACTION_MODE=6` 和以提取目录 `program` 子目录为首的 PATH。两个配置来源都生成了请求，因此原预置库可以消费输入中的补充行为配置。每个匹配案例都停在原 `system` PLT 入口，没有调用 shell，也没有给它伪造成功返回值；所以不能从请求字符串推出 PATH 已实际解析、文本能执行、功能已安装或机身能恢复。

宿主替身只承担合成内存分配、有限字节／字符串和 ASCII 字符分类、内存 FILE 读取、明确的内存文件存在性及单线程 mutex 结果。没有让宿主打开请求中的相机目标路径。ConfigKeyTag 检查中的 stat 状态是显式输入，不是当前机身状态。

首次 XML 实验因全局写入保护停止。定位原指令后确认其为 `TiXmlString::nullrep_`：原 24 字节 BSS 空字符串对象内重复写零。随后只允许该精确符号内写零，记录每次地址、大小、值与原 PC，并核对对象始终全零；其他原库全局写入继续拒绝。另一次断言把无 param 的请求误设为带尾空格，已按原请求逐字回读修正为精确字符串。两次失败均保留在[attempts](attempts/)，没有作为通过结果。

## 仍未跨过的条件

本轮没有运行完整 TAR 控制器和分组转换、整个旧输入 API／外部服务及原实际启动环境。原补充 XML 读取和系统请求已证实，不等于正常更新入口接收了自定义容器；此前官方密文 RSA 尾签名的约束仍成立。真实文件权限、PATH 查找、进程执行、加载／更新与恢复也未验收。

完整 FX5 专有固件和菜单、VENICE 不透明内层及实时 ISP、FX3 正常 MAIN 像素链绑定仍未取得完整证据。下一研究点是完整外部输入对该配置回调的可达性和格式限制，之后才能评估这条路径能否承载真实色彩代码替换。不能将本轮的局部分派当作完整 VENICE 移植或可刷包，用户要求的停止研究条件尚未达到。

本轮复核上一阶段 43 项封存材料，并重新核对所有新来源、87 个函数体和 23 个片段的哈希；十组 guest 的主程序不作为验证步骤重复运行。[验证结果](validation-results.json)、[封存回执](final-receipt.json)
