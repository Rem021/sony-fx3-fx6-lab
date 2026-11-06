# FX3 读取错误、句柄清理与成功回复的边界

2026-10-28。**旧整文件读取的成功回复，不能单独证明文件句柄已经正确清理。** 本轮在原异常表选择下执行12组原指令错误路径，验证关闭错误可被数据成功回复掩盖。没有运行真实Sony C++ unwinder、POSIX设备调用或相机文件服务。

156单次USB接管与管理员试验已获用户明确授权；最近一次缓存检查中disk10s1仍挂载，按原方案等待手动推出。授权已保留，运行包和编号不变，runtime release仍为false，试验次数未消耗。本轮没有请求同一授权，也没有自动卸载或调用管理员。

## 原件与实际执行范围

158材料原本未封存，160在重验当前159主状态后采用。158保存的旧157 before快照只作历史来源，不回写当前授权状态。[158入口](../stage158-original-LSDA-and-read-error-cleanup/README.md)

- 原7.02 libJiritsu.so SHA：`bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9`。
- [异常表解析](../stage158-original-LSDA-and-read-error-cleanup/original-LSDA-review.json)：原GET_FILE2及stat/open/read/fsync/close六函数，共46个调用区间。五个FileAccess方法的filter1为FileAccessException，filter2为std::exception；filter2不是catch-all。GET_FILE2本身的相关表是清理路径。
- [12组错误路径](../stage158-original-LSDA-and-read-error-cleanup/run-LSDA-selected-errors/results.json)：5030次原指令/边界进入，19次处理上下文由原LSDA选择。原函数的栈和帧保持，CFI核对保存返回地址；异常参数寄存器及落点由明确的运行时提供者交付。
- 系统调用、DMM/挂载/加密、异常申请/类型匹配/释放仍是声明模型；没有执行实际personality或unwinder，也未宣称异常析构或完整线程退出通过。[完整结果复核](../stage158-original-LSDA-and-read-error-cleanup/error-cleanup-admission-review.json)

## 新结果

| 声明错误条件 | 原代码在模型中的结果 |
| --- | --- |
| read返回错误，经FileAccessException处理 | 读取回复报 `0x1000000a`，正常关闭路径可运行 |
| open/stat返回错误 | 分别形成 `0x10000008` / `0x10000006`；没有实际打开成功或读取 |
| 两次fsync均报错 | 对应处理器运行后，GET_FILE2仍可回复成功及完整声明长度 |
| 两次close均报错 | 原方法再次尝试相同FD，最终数据回复仍成功；文件对象的open标志保持1、FD字段保持3 |
| 第一次close报错、第二次成功 | 出现两次close尝试，第二次将对象标志清0、FD字段置-1 |
| read和close都报错 | 数据回复报读取错误，但对象清理标志仍未清0 |

上述标志只是原程序内存，不证明真实内核FD仍然打开，更不证明已经发生泄漏或误关闭其它线程文件。Linux的close即使报错，也可能已经释放描述符；重试可能碰到被复用的FD。因此既不能把报错简单等同“仍开着”，也不能靠再次close来证明恢复。[Linux close(2)](https://man7.org/linux/man-pages/man2/close.2.html)

157中“4GiB减1与-1低32位相等”的独立调用者反例，本轮连接原FileAccess处理分支后，在声明的运行时/系统调用条件下仍形成成功字与3字节长度。它仍是离线反例，没有向机身发送这类请求，也不是已确认的实机漏洞。

## 对备份流程的实际约束

未来读取必须分别证明：完整目标的数据/长度/强摘要、句柄与分配对象的清理、服务/线程退出、对应同机恢复与回读。单个成功应答不覆盖这些条件。旧GET_FILE2没有提供独立的每个清理结果，尚不能直接发布为健康备份/恢复工具；此前查到的挂载、日志及认证历史条件写入仍保留。

异常上下文与原处理代码也需分开。设计对照 [C++异常ABI](https://itanium-cxx-abi.github.io/cxx-abi/abi-eh.html) 和 [GCC6.4源码](https://github.com/gcc-mirror/gcc/tree/abaef5489e27672c45aa05f41ea7ed52f3fa2748)。原库注释标记GCC6.4.0/Sony CE构建，不能因此认为实际Sony运行时与上游相同。保存的上游三份文件只作静态参考，不运行。[来源与SHA](../stage158-original-LSDA-and-read-error-cleanup/upstream-reference-receipt.json)

后续继续核对设备端有界读取路线与可独立观测的清理机制；真实USB接管须先满足已批准方案的卷前置条件。目标仍为MAIN 1920×1080、30000/1001、HEVC42010约16Mbps及完整同机恢复；16项要求保持，首次刷入仍无可用包或可靠日期。
