# FX3 备份读取入口范围与服务登记副作用

2026-10-27。对象为经典 ILME-FX3 7.02 官方已解包原件；继续原1920×1080、30000/1001、HEVC42010约16Mbps MAIN与同机恢复目标。

**本轮收紧了几个候选入口的适用范围，没有发布可执行的实机备份工具。** 原旧版GET_FILE与“高容量GET”仍然按文件总大小分配并读取，不能当作设备端受限分块备份；另发现服务ID登记存在有条件的持久历史写入，未来认证方案不能统称零写入。

## 读取候选实际做什么

| 候选 | 原代码证据 | 能否据此备份系统原件 |
|---|---|---|
| `adj_cmd_get_file` kind0 | 挂载 `/dev/nflasha6` 到 `/tmp/jiritsu`，按服务区选择文件 | 不是直接系统文件入口；挂载和日志副作用仍需审查 |
| 同函数kind1 | 在 `/mnt` 前缀下拼接传入路径 | 不能把正常路径直接解释成 `/setting`、`/usr`；不采用路径穿越绕过 |
| 同函数数据读取 | stat得出文件大小，整文件DMM分配、O_RDONLY打开、read、fsync、close | 请求中没有本轮已核验的offset/count限制；不能用主机输出上限代替设备分配上限 |
| `cmd_high_capacity_get_file` | type1建立全局DMM，type4转交旧GET/file2/hash/list，type16释放 | “高容量”是会话/传输包装，不证明文件分块；初始化失败、空对象和断线后的恢复未证 |
| `adj_cmd_get_file_hash` | 整文件申请/读取后计算MD5；某分支还挂载媒体 | 哈希不含原字节，不能算健康备份，也不是固定内存占用的流式文件验证 |
| PMCA FileControl/MemoryDump | 固定源码分别为ff01文件读取、ff03地址/大小请求 | 缺经典FX3目标接收器/有效范围证明；不能直接调用通用工具试探 |

本轮完整静态读取10个原函数、核对21处PLT目标，并另核对DeviceIo两个包装函数。原件SHA固定：libJiritsu.so为 `bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9`；libsencore.so为 `a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410`。逐条指令、字符串及调用地址见[读取范围审查](reader-scope-review.json)。这里只证明所查原函数的代码行为，不证明认证、当前对象、实际文件或完整异常清理。

阶段131已有10组原Parse前缀试验本轮未重跑，保留原目录及所有文件SHA作为局部来源。它们只证明三个已提供表没有ff01/ff03，不能排除实际插件、定制表或其他版本中的实现。`LoadSenserMode`、`GetPluginModule`等存在，并不自动证明这些文件/内存命令已经注册；本轮不作所有动态路径均不存在的断言。

## 服务登记不是已证明的纯RAM操作

`WorkerThreadManager::registHaspId`尾调用 `Regist_HaspId`。后者在历史文件存在、`Read_Hasp`成功、记录头/状态符合条件时，准备更新 `/setting/.hasp`：

- DeviceIo.open传递flags `0x101241`到libc open，对应Linux的写入、创建、截断及同步标志；随后准备写入88字节并调用sync。
- DeviceIo.write确实将数据交给libc write；这不是单凭函数名称推测的写路径。
- **没有证明每次认证必经该登记，也未检查用户机身文件是否存在，更未执行写入。** 后续需要追完整认证调用链、当前挂载与分支条件，把可能的服务历史更新写入具体授权说明；不能承诺“服务读取全过程零写入”。

原函数、包装器和固定版PMCA语法证据见[包装与上游审查](deviceio-and-upstream-review.json)。flags定义参考[Linux原始头文件](https://github.com/torvalds/linux/blob/v4.9/include/uapi/asm-generic/fcntl.h)。

[PMCA固定版服务入口](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L656)在MSC分支会启动/认证、等待重枚举，再次启动/认证后才进入shell；其枚举和shell均不属于现有缓存元数据授权。本轮只下载源码并用AST读取，未导入或执行PMCA。

## 对下一步的影响

1. 不再把旧GET、文件哈希或高容量会话作为已具备受限系统备份的替代方案。真实备份须有同机原字节、长度、两次一致摘要及相应恢复证据。
2. 优先补服务认证到历史登记的实际调用链与分支，再定位真正读取系统原件的接收器/插件及请求长度、对象寿命、超时和退出路径。没有对应请求/退出审查与授权时，不自动进入服务。
3. 保留阶段130的GET_FILE2副作用和路径/容量限制、阶段129上机计划及全部16项实机验收。原前后端、原Sony字节均不修改；缓存授权持续有效但不扩大到主动协议。

最初审查脚本将一处 `mov w2,#0` 的地址误标为9190，实际为918c；失败脚本与原因保存在 `attempt-initial-address-check/`，更正地址后静态核对通过。此为主机审查标注修正，不是Sony原代码故障或设备试验。

本轮仅Mac离线源码/ELF静态解析，无新增缓存采集、相机协议、文件读取、驱动、认证、RAM载荷、Windows/UU或刷写。目标未完成，备份、MAIN编码成片及实机恢复均未验收。
