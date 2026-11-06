# FX3：原装载器、内核内存函数与状态对象完整清零

本轮从官方7.02包补提取内核及相关模块，找到av-cam的原LIRO装载链，并在离线客体中让两段原状态机构造函数执行完自己的两次清零、沿原栈正常返回。此前只能在未绑定清零入口前停止；本轮使用官方内核原`memcpy`、`memset`指令，没有以自写清零、假返回或跳过调用替代。

共16段原片段通过：8段头部/导入验证，另8段内核清零、原装载复制及构造执行。仍不是完整系统仿真、真实实例或硬件验收，没有连接或写入相机。

## 头部与导入槽已由原装载器绑定

原`liro.ko`的`.init.text`检查映像+8的`ORIL`及+0xc的版本5。本轮分别执行正确头部、错误magic及错误版本的原检查片段，观察相应诊断分支；没有执行诊断或完整装载/错误收尾。

它从映像头部+0x20取接口区，再加0x48，将自己的`.init.data`复制过去：长度0x698，共211项。该复制发生在调用映像头部+0x10入口之前。模块原重定位项把以下槽与符号明确对应起来：

| av-cam入口 | 接口偏移 | LIRO表偏移 | 原符号 |
|---|---:|---:|---|
| 0x2ef4c | 0x388 | 0x340 | osal_wai_sem_tmo |
| 0x2ef60 | 0x390 | 0x348 | osal_sig_sem |
| 0x2f604 | 0x698 | 0x650 | pciatu_unmap |
| 0x2f67c | 0x6b8 | 0x670 | memset |

这也说明锁接口不能只凭参数外形套成另一种信号量API。补提取的`osal_uipc.ko`包含前两者的实际函数符号，真实内核/任务同步仍未执行。

原av-cam接口区为映像+0x1a4，清零指针槽的原文件偏移是**0x85c**。未装载时四个上述槽均为0；本轮原veneer读到0后在间接跳转前停止，没有把零目标当成功调用。

## 官方内核原实现与受限链接输入

内核原导出表及相邻完整字符串记录绑定：

| 符号 | 内核文件偏移 | 原导出值 |
|---|---|---|
| memcpy | 0x1efe80 | 0xffffff800826fe80 |
| memset | 0x1f0180 | 0xffffff8008270180 |

内核链接地址模型为0xffffff8008080000，由导出值、名字指针和相邻记录共同核对；不是实机ASLR地址观察。内核banner与模块vermagic均为4.9.337-scel+。

客体仅解析三处原ELF重定位：LIRO复制调用到内核memcpy、原表字面量到客体数据段、表中memset到内核导出值。ABS64/CALL26按[Arm AArch64 ELF规范](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst)核对类型与计算，仅用于明确的客体section地址输入，不代表实际机身装载地址已确定。

随后执行原LIRO复制片段，由原内核memcpy实际写入av-cam接口数据区，正常返回原复制调用者，在后续诊断前停止。**av-cam表中只绑定memset，其余210槽保持未解析的0**；LIRO自身memcpy调用是另一处已解析依赖。

官方磁盘原件未改变。客体接口数据由原复制写入；该页只在此阶段可写，之后改为只读。其它av-cam字节保持一致，没有修改其指令逻辑，也没有生成供相机使用的新模块或固件。

## 原清零与构造函数实际执行

原内核memset在人工缓冲上验证了88、337、1409字节清零及337字节非零填充，目标内容和两侧保留区均符合预期。

较长清零会执行原`MRS DCZID_EL0`及`DC ZVA`。本轮让Unicorn 2.1.4实际解释这些指令，记录虚拟DCZID=0x4；没有修改寄存器返回值或由宿主代写零。这个CPU模型不是FX3实测，不能支持其缓存、并发或弱内存语义。

将两个对象先填为0xa5后，原构造函数实际运行至正常返回：

| 原构造入口 | 原初始状态 | 原状态区清零 | 原队列区清零 |
|---|---|---:|---:|
| 0x253b38，IMOLA编码状态 | INITIAL_PSEUDO=14 | 337字节 | 88字节 |
| 0x155bd0，sfmc输出状态 | INITIAL_PSEUDO=42 | 1409字节 | 88字节 |

两者均经原av-cam veneer调用原内核memset，SP回到调用前位置。普通写入hook记录逐项复核，构造写入限定在各自对象与客体栈内；清零对照未改动保留区。

这证明的是这两段**有界构造正文在部分链接输入下完成**。真实工厂/单例、owner、实例生存期、锁、日志、线程、配置代次、HAL、全局代码退出均未绑定；对象也仍处INITIAL状态。它不等于已打开编码器或完整系统已启动。

## 下一步与证据

优先将已定位的真实清零依赖带回编码请求构造，追52字节的初始化来源及完整start-input；再闭合真实日志/锁、对象登记、请求代次和有效HAL参数。不能将本轮状态对象清零误计为编码块52字节已解决。

本轮ORIL链属于内核装载av-cam，不是Jiritsu上传ELF的实机ABI或权限验收。Sony公开的[FX3 7.00源码目录](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)可作后续线索，未被当作7.02逐字节对应源码；本轮实现证据来自已核验的官方7.02二进制。

- [头部/导入验证](run-20261025/provider-binding-results.json)、[原内核与完整构造结果](native-run-20261025/native-initialization-results.json)。
- [提取回执](official-extraction-receipt.json)、[补提取OSAL](supplementary-provider-extraction.json)、[同agent复核](coordinator-observations.json)、[后续入口](next-native-runtime-anchors.json)、[封存清单](final-receipt.json)。

项目根复现，输出目录必须不存在：

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage47-runtime-provider-binding/provider_binding.py --output work/sony-firmware-20261024/stage47-runtime-provider-binding/run-new
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage47-runtime-provider-binding/native_initialization.py --output work/sony-firmware-20261024/stage47-runtime-provider-binding/native-new
```

所有相机授权和目标保持不变。主录规格/码率、模型/query/cache/mux统一、音画同步/长录/温度、健康同机备份、受限恢复/回读、WBI/冷启动和独立救援仍待实机验收。
