# FX3 剩余时间缓存身份与原调用参数准备

本阶段把实验profile接入剩余时间使用的缓存副本，串起原缓存getter复制、原调用输入复制、原query及音频/代理转换，执行到真正调用 `GetMovieRemain` 之前。19组原合法HS组合在后续开关改变时仍保持捕获身份；目标准备参数为6/6/3。**尚未计算实际剩余秒数、查询卡空间或运行硬件，不能据此称为实机功能可用。**

## 绑定正确的缓存对象

通过原ELF的RTTI、相对重定位、虚表run槽、构造函数设置vptr的指令和析构尺寸，将缓存明确绑定到 `model::sequence_get_media_remain`：

| 证据 | 原件位置 |
|---|---|
| RTTI名称 | 0x3928f50：N5model25sequence_get_media_remainE |
| 虚表base / run槽 | 0x46e7ff0 / 0x46e8010，run为0x2baf850 |
| 虚表GOT / 构造函数 | 0x47827d8 / 0x2c3d618 |
| 原分配及删除尺寸 | 0x4d8字节 |
| model_lock范围 | 0x2c3d654进入，0x2c3dbbc退出 |

构造函数在锁范围内读取模型。新增客体分支位于退出锁之前的0x2c3dbb8，只对符合实验条件的缓存对象将0x388字段标成2。该字段原本由HS帧率getter复制而来；原厂全局槽位保持合法原值。

原件有87次标量getter读取，写85个不同槽位，另复制19字节不透明字段。两处重复getter读取也按原指令执行，未去重。标签值测试核对了字段来源；其中一种getter使用临时寄存器相加，最终脚本按它的确切原指令解析并执行。

真实模型锁、线程、构造函数前缀和早先的MPR上下文memcpy没有在这组客体实验中执行。宿主提供既存缓存、合成栈和零值上下文元数据作为前提；这些不是从相机捕获的状态。

## 从缓存到原GetMovieRemain输入

原序列从缓存复制局部调用输入，实验随后执行原剩余时间实现的初始化、传参、query和有效默认音频/代理转换。主要对应关系由原代码和动态逐字节比较共同确认：

| 缓存偏移 | 调用输入偏移 | 含义 |
|---|---|---|
| 0x37c | 0x10 | 模式 |
| 0x380 | 0x14 | 文件格式 |
| 0x388 | 0x1c | HS帧率；仅该缓存字段携带实验标记 |
| 0x4a4 | 0x138 | setting_sq_proxy_recording |
| 0x4b8起19字节 | 0x14c起19字节 | 保留的不透明字段 |

原复制覆盖全部74个query标量参数及其它输入字段，缓存本身不变。后续复制与转换的内存读轨迹确认不再读取私有开关。

最终停止点是原0x2e6a960调用指令，目标PLT符号为 `mpr::GetMovieRemain(const getMovieRemainInParam&, getMovieRemainOutParam*)`。没有执行该API。它收到的0x3c字节已初始化参数区由原指令准备，其中主录字段为VPC6、VQuality6、FrameRate3；原初始化常量0x0c及其它原字段保留。此FrameRate仍对应已独立确认的30000/1001，目标规格和精确30.000fps的区别不变。

音频与代理帮助函数实际执行原指令，没有填字段或返回值的stub。未纳入音频函数时，实验停在其原入口；核对实际函数范围后才继续。当前仅覆盖这组合成有效默认音频配置与两个proxy设置值，不是完整音频/代理格式回归，也没有运行真实代理录制。

## 新验证结果及仍未闭合的边界

- 19组原合法HS组合：关闭时缓存与原厂复制一致；开启时只有缓存0x388四字节变化。复制到调用输入后，query和MPR调用前准备均得到6/6/3；关闭时返回原厂元组。音频选择字段在该对照中一致。
- 7组入口控制：其它格式/模式、无效开关等保持相同缓存；只验证复制范围，不能推成全模式或损坏状态回归。
- 2组proxy输入：设置值保持，原代理转换路径实际执行，目标主录身份保留。
- 4组联合输入对照：主录setter、实时状态query、缓存剩余时间准备，在给定相同捕获身份且后续开关变化时得到同一主录元组。它们仍是分别构造的对象，没有执行一次真实原子事务。
- 2组不同捕获身份：主录与缓存仍可得到不同元组；若二者应描述同一次录制配置，仍需真实配置代次/用途和发布策略。没有擅自将这种不一致称为已经修复。

首次19组对照覆盖的是原合法设置。非法原值入口控制只证明没有新增改包行为，不是异常设置恢复保证；NTSC/PAL精确数值绑定和启用条件也尚未接入。

## 退出必须处理缓存对象

标记现在会随缓存对象跨越局部调用栈。清除当前开关后，旧缓存仍携带标记；若将其交给原查询消费者，会进入原断言入口。重新生成未标记缓存后，原消费者可完成本阶段的原参数准备路径。

这要求退出时同时处理带标记的缓存序列对象、局部输入包、在途调用及活动目标元组。构造函数的5个直接调用点都涉及实际对象生成，后续应继续追其发布、替换、调度和释放流程。当前没有真实缓存失效观察器、队列清空器、统一代次或录制空闲门禁；不能把重新生成客体副本当作实机恢复。

同机健康原件、受限加载/恢复器、原字节回读、WBI/冷启动和应用失效后的独立恢复入口仍缺证据，未进行刷写或诱发故障。菜单固定质量显示、保存和长录也保持在完整目标中。

Sony官方的“Display Media Info.”显示所选卡槽的电影剩余录制时间。后续实机验收须绑定实际卡槽和媒体状态，并对照新profile的真实文件与时间显示；本阶段没有这些输入或结果。[官方帮助指南](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000843999.html)（2026-10-25读取，经典FX3 Ver.2或以后指南）。

## 重现与证据

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage18-cached-remain/cached_remain.py --output work/sony-firmware-20261024/stage18-cached-remain/new-remain-run
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage18-cached-remain/cache_identity_boundary.py --output work/sony-firmware-20261024/stage18-cached-remain/new-boundary-run
```

输出必须为新目录。执行前核对目标卷；原件和依赖前后哈希一致。客体限定代码/内存/执行量，无USB、syscall、MMIO或宿主后端转发。

- [缓存到调用准备摘要](run-complete-20261025/summary.json) · [完整轨迹与指令](run-complete-20261025/cached-remain-results.json) · [来源收据](run-complete-20261025/source-receipt.json)
- [类型/联合身份摘要](boundary-verified-20261025/summary.json) · [绑定、捕获代次与退出负例](boundary-verified-20261025/cache-boundary-results.json) · [来源收据](boundary-verified-20261025/source-receipt.json)
- 保留的阶段停点：[getter形式](run-20261025/attempt-failure.json)、[重复复制](run-corrected-20261025/attempt-failure.json)、[音频白名单边界](run-verified-20261025/attempt-failure.json)、[静态PC标注](boundary-run-20261025/attempt-failure.json)。各自的原脚本和哈希均保留，成功结果绑定最终脚本。
- [阶段前目标](goal-status-before.json) · [阶段后目标](goal-status-after.json) · [持续目标](../GOAL_STATUS.json)

本阶段没有新增UU连接尝试、Windows交接或相机主动访问。授权仍仅Windows缓存PnP；未认证、切模式、安装驱动、访问机身/卡文件、上传模块、运行WBI或刷写固件。
