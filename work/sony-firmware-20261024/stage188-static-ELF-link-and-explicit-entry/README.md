# 第188轮：静态ELF链接、ARM64执行与入口核对

2026-10-29。**工作器已由可重定位对象推进为静态Linux ELF，并在ARM64模拟环境中执行实际机器码，完成三组383块读取→候选构建→原件精确还原。** [工具0.4](../../../outputs/fx3-recovery-adapter/README.md) · [构建实现](../../../outputs/fx3-recovery-adapter/fx3_recovery/elflink.py) · [源码包](../../../outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip)。系统调用与来源仍为自建夹具，没有启动真实Linux或FX3内核，没有上机。

## 新增可复核实现

C源码保持0.3固定SHA `22d6e613fb2c33861eac93653c7148e34ad22dd3b5b14ac0d4c75d5b903efb29`。新增汇编`_start`先调用读取函数，再以Linux AArch64 syscall93退出，传播真实返回值；不是构造函数，也没有preload或动态库注入。

使用本机已有Clang交叉编译，再由自写限定链接器处理当前两份固定源码产生的对象。只支持已观察到的5类重定位：ADRP／ADD低12位／64位LDST／128位LDST／CALL26，共59处。每处核对原操作码、目标、范围、对齐、写入窗口与回算；再检查所有分配节在记录窗口之外不变。外部导入、初始化段、未知类型／对象／符号、异常对齐或RWX拒绝，不猜地址、不加跳板或运行时修补。[Arm ABI原文](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst)。

产物`worker.elf`为20,480字节、ET_EXEC／EM_AARCH64、无动态加载器或导入，入口0x402328。四个载入段为R／RX／R／RW，GNU_STACK为RW／不可执行。研究布局固定起点0x400000，不能据此推断Sony内核的装载支持。完整SHA：`c3a7b81d95d1d537d1f97bdab9eb0117f55bdeaee9b232d1f561d3d58040e2fd`。

新增`build-worker --out <新目录>`，创建0700目录与0600结果，保留两份对象、源码计划与链接记录。构建前后重验两份源码；生成ELF后重新解析并回读。重复构建逐字节一致。**该命令只编译／链接，不执行目标ELF，更不上传到机身。** [正式本地构建与链接记录](runs/link-tests-final/built/link.json)。

## 47项当前本地检查

- [9项链接及ARM64测试](runs/link-tests-final/test-receipt/results.json)：实际执行生成的ARM64机器码，只有SVC边界进入自建系统调用提供者，未替换工作器内部CRC、循环、元数据检查或清理指令。三组共383块完整组合、候选及精确还原通过；另外8个失败场景正常返回非0。Capstone独立反汇编检查重定位字段，损坏操作码／偏移／符号／权限／入口／文件长度均拒绝。命令行构建实际运行、没有执行产物。
- [11项C系统调用夹具与解码回归](runs/worker-tests-final/test-receipt/results.json)：保持设备／容量／tmpfs、短读、缓冲、时钟、写入／关闭、入口重放及混组拒绝。
- [14项主机采集回归](runs/capture-tests-final/test-receipt/results.json)与[13项镜像构建／还原回归](runs/adapter-tests-final/test-receipt/results.json)：原件保护和已有能力保持；两份真实Sony 2.04／2.05来源哈希不变。

ARM64程序在Unicorn2.1.4中以实际指令和寄存器传参运行；root身份、FP／SIMD启用、设备号、分区容量、时钟、Linux元数据与tmpfs属性都是显式模型条件。`read／pread`源字节与输出为本地普通文件，没有真实Linux或Sony设备系统调用。三个成功进程均到达syscall93退出0，生成全量字节与输入合成文件一致。**这是指令级程序验证，不是FX3整机模拟、真实驱动或恢复验收。**

完整源仍是明确标注的2.05参考载荷人工补0xff至配置长度，不是当前7.02读回。所有47项回执绑定当前Python源码，工作器回执另绑定C源码及测试源码；新增链接器测试绑定汇编和所复用的系统调用夹具。没有新增测试依赖或链接器安装，复用既有stage4虚拟环境。早期构建和测试运行保留，正式引用final目录。[边界检查](implementation-review.json)。

## 显式启动路径的真实结论

[7个原函数的字节／调用／字符串核对](launch-route-review.json)没有发现可直接采用的任意RAM路径子进程启动入口：

1. `cmd_debug`将年月日时分秒固定为2017／7／4／21／42／26，经固定格式下发`/bin/date -s 070421422017.26`，没有用户shell文本参数。未被拦截的正常执行会尝试改时间；社区构造函数会提前结束匹配子进程，不能据此说所有调用必然改时，也不能把拦截缺失／失败称作零副作用。
2. 原`CShellExecute`使用fork→execv(`/bin/sh`, `-c`, 固定文本)→waitpid。fork失败分支在调用进程执行`_exit(-1)`；waitpid选项0，没有内部超时。仅看到shell函数名不能当作有界安全进程入口。
3. 两个直接文件加载分支比较固定`/tmp/jiritsu/libJit.so`；Jiritsu线程复制到固定`/tmp/jiritsu/ramdsk_libJit/libJit.so`后，在当前进程dlopen并调用CreateScriptI／LoadScriptI。它们不是本工具的独立进程启动接口。
4. 模块辅助函数接受格式串；观察到的ProductInfo调用使用`libpro%02X.so`。尚未证明USB请求能提供任意RAM可执行路径，不能把辅助函数的C签名扩展成可发送的任意执行命令。

[终端路径核对](terminal-route-review.json)补充：默认禁用标志的原数据为1，但原onComplete(3)确实可清零，不能只看默认值就断言认证后仍禁用。禁用分支NoAction将响应字节设为1；启用后`libpro00.so::command00F1`原函数也只有`mov w0,#1; ret`，本身没有其它动作。**成功响应不能证明shell已开启。** ADJUST的TERM_MODE静态记录为family0x601、command0x801f、目标字段0x003d025f；具体下游与实际USB终端端点／提示符未验证，下一项应追它的消费端，不能强改开关试机。

首轮终端检查曾错误预期空返回而失败，现依原字节确认返回1；[失败源码](terminal-audit-initial-source.py)和[原始失败及纠正解释](terminal-audit-initial-failure.json)保留，未修改固件以迎合检查。

联网复核两社区当前HEAD仍分别是YuuLuo `f124d87c26110a82db54775bfa64a0843ff21410`与QAQLeonard `ef7db116e13e37be91e9af20360dc9bba8d64a9b`，沿用固定源码结论。[公开来源回执](public-source-refresh.json)。没有发消息给维护者或执行社区工具。

## 发布与下一项

源码包63,622字节，SHA-256：`43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f`，仅19份自写源码／说明／测试，不含生成二进制、Sony原件、私有备份或模拟器依赖。0.1／0.2／0.3包保留。[发布回执](release-receipt.json)。

链接和自写ARM64机器码验证已完成，后续集中在TERM_MODE目标消费端、单个临时进程的真实启动／返回、root拥有者及SERVICE传输接合、同机绑定和正常归还。存在真实入口后，也应先验证不打开相机分区的启动／返回条件，再评估完整采集；当前没有此类设备放行。

P1仍不是完整eMMC／MAIN／设置／校准备份；分组原子性、当前7.02原件、实际写回、独立救砖及1080p29.97 H.265主录都未验证。**ELF能在模型运行，不表示相机可安全刷入。** 新增相机／USB／管理员／Windows／GUI操作均为0；16项要求、全部授权、prepared与恢复优先次序保持，`goal_complete=false`、`persistent_write_release=false`。
