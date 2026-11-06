# FX3 旧更新库的标志缓存、文件提取与可选配置

2026-10-29。**原旧更新库能够把规范化后的普通文件提取到更新目录，配置收尾也确实支持读取输入目录下的 `config/uconfig.xml`。这些是继续检查输入驱动行为的线索，尚不是完整修改包准入、代码执行或可刷入证据。** 目前仍不能把完整 FX5／VENICE 菜单和色彩链正常刷入 FX3。

接续[镜像选择条件](../body-load-20261029/README.md)。本轮所有目标指令均在 Unicorn 合成内存中有界解释执行；未操作相机、USB、机身文件、mount、原生目标库、原更新脚本或另一 agent 的 HEVC／恢复流程。

## WBI 中的标志缓存不能替代实时状态

对原 `nflasha5.img` 的只读页表恢复找到 `libObj.so` 的模块记录，基址 `0x7f7647b000`。原库重定位把 GOT 指针指向匿名 BSS 相对地址 `0x2d2c2c`；快照中的该指针、`/root/IAMUPDATER` 字面值及四字节缓存可读，缓存为 `0xffffffff`（有符号 -1）。

但 ELF 头、初始化代码、运行版本查询代码均不可读，全部 361 个 `.plt`／`.text` 页片段也未恢复。这既不能确证快照执行了所查精确原代码，也不能证明缓存已初始化、当前 stat 结果或当前机身运行根目录中标志不存在。没有把不可读页填零后称为匹配。[快照结果](marker-snapshot-results.json)

## 原策略与调用边界

从 SHA-256 `6582eba530025d17fab81420050433cd998714c922aa4c16fd4d5cdc5a378ee9` 的原 `libupdaterbody.so` 保存 14 个策略函数、8 个提取／XML 函数和 3 个明确标记的控制器窗口。

- `isAccessoryMode` 自己查询 `IAMUPDATER`，不是仅检查 action mode 6。脚本中的 action mode 6（MSCRYPT）与 AP boot mode 5 是不同枚举。
- 初始 StartUpdate 使用绝对路径的预置脚本，后续 shell 插件则构造以 `update/program` 为首的 PATH，并使用官方配置中的模块名。五组原 ShellPlugin 检查只到 `system()` 请求边界停止，没有执行请求；XML 属性和字符串组合在该检查中使用显式替身。
- `ConfigKeyTag::PostExecute` 组合提取根目录和 `config/uconfig.xml`，stat 成功后调用 XML 对象虚槽 `+0x20`。已按原 `.rela.dyn` 确认该槽为 `XmlConfigHandler::LoadUserConfig`，其原函数请求载入该文件。尚未运行原 XML 解析器和整个配置执行流程。

因此，“标志缺失时选择预置更新镜像”仍成立，但不能进一步推导“预置更新库完全不消费输入中的行为配置”。PATH 和可选配置是待核实候选，不能称为已证实的未签名代码执行路径。[原策略片段](body-policy-static-results.json)、[提取／虚表契约](extract-contract-static-results.json)、[shell 请求](shell-request-guest-results.json)

## 文件名解析与普通文本提取

八组原 KeyTagFactory＋原 StringHandler 检查区分了直接字符串输入与 TAR 规范化后的键名。原 TAR 解析的四组检查实际执行头部校验、八进制字段读取、四位编号提取和前缀移除：官方 `0100_config` 变为 `config`／编号 100，单独的 `0001_program/probe.txt` 变为 `program/probe.txt`／编号 1；单字节破坏且未更新校验和的头部被原解析器拒绝。

原控制器仅在编号变化时切换 KeyTag，不能把对每个文件名直接调用工厂的结果当成完整控制器行为。编号 1／100／0x9999 也不是 action mode。[工厂检查](keytag-factory-guest-results.json)、[原 TAR 解析](tar-header-guest-results.json)

另四组解释执行接上原 BaseKeyTag 提取、NewFirmwareFile 构造、BaseNewFirmwareFile 分派及普通文件提取循环。测试内容是无执行权限的普通文本（mode 0644），目标路径由原 StringHandler 组合为 `/tmp_updater/updater/update/program/probe.txt`。FileHandler 和输入缓冲区由严格内存适配器承接，XML `IsKey` 明确为 false 替身。

| 输入条件 | 原提取返回 | 内存接收结果 |
|---|---|---|
| 完整正文 | 1 | 29 字节，哈希与输入一致，显式关闭 |
| 每次最多 5 字节 | 1 | 同上，实际循环读取／跳过 |
| 头部声明有正文但正文缺失 | 0 | 0 字节 |
| SkipCurrentBlock 失败 | 0 | 未请求打开目标 |

没有打开上述宿主目标路径、写出完整 TAR 或固件容器。该检查不包含整个控制器、实际 action mode、权限、目录创建、真实 XML、异常展开和外层验签。[文本提取结果](extract-text-guest-results.json)

解释执行使用原 AP `libupdatercommon.so` 解析 StringHandler。它与更新镜像内的同名库整体哈希不同；20 个导出符号体（18 个唯一地址）逐字节相同，已记录地址、长度和哈希。这只支持所用字符串函数的字节等价，不证明实际加载器选择或全部 ABI 等价。[比较结果](extract-contract-static-results.json)

## 核验与下一步

本轮共 21 组有界 guest 检查。静态片段、来源和上一阶段 22 项封存材料重新核对；首次缺少 `memcmp` 适配器的失败保留在 attempts，不把失败当作通过。[验证记录](validation-results.json)、[封存回执](final-receipt.json)

下一步是从原 AP 文件恢复 `libul_xml.so`，核对真实 XML 读取、键匹配、guard 和插件分派；不能继续用 XML 替身推导完整输入链。此前确认的官方完整密文 RSA 尾签名仍未被这些局部结果改变。FX5 完整专有镜像、VENICE 不透明内层与完整实时 ISP、FX3 MAIN 像素绑定、正常入口准入及可恢复的实际加载条件仍有缺口，未达到用户指定的停止研究条件。

本轮联网复核了[解包工具维护者讨论](https://github.com/ma1co/fwtool.py/issues/39)中的 BIONZ XR 解包来源；其 2026-09-11 A7 IV 硬件研究说明不构成本机 FX3 的修改包准入或新平台通用支持证明。
