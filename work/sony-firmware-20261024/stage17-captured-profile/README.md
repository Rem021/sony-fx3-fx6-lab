# FX3 捕获后的 profile 身份与退出边界

本阶段实现客体内的局部副本标记，让后续转换/查询使用捕获时的身份，避开逐次读开关造成的不一致。同时定位原厂 `model_lock`，并用原参数准备函数验证移除消费者前必须清理在途数据。**尚无真实配置代次、录制空闲门禁、剩余时间缓存接入或可上机恢复器。** 完整主录、菜单、保存、冷启动和恢复目标保持不变。

## 捕获身份，保留原厂合法全局值

新实验组合采用三个既有/新增部件：

1. 主录builder在捕获时依据实验开关写出目标元组15/6/2/0，保留原厂模型设置。
2. setter只解释输入元组本身，目标元组转成6/6/3；转换时不再重新读开关。
3. 原状态查询的模型采集片段执行79次真实getter复制。新增客体分支在合适的普通movie/格式6及原合法帧率输入下，只将**栈上局部副本**的HS帧率字段置为2。查询消费者依据该局部标记返回6/6/3，不再重新读开关。

标记位置是局部输入对象的0x1c，不是全局模型key写入、闪存地址或安装位置。实验代码仍在新增的Unicorn映射中；未导出安装二进制或刷机包。原全局帧率、质量、格式及proxy模型槽位前后值一致。

19组原合法HS组合中：关闭时副本与原复制代码一致；开启时只有局部0x1c字段变化，其余字节相同。新查询在随后开关变化后仍返回与捕获身份一致的结果。额外使用不同标签值核对79个字段来源，避免全零输入掩盖错位。

| 对照 | 观察与范围 |
|---|---|
| 8种“捕获开关 × 后续setter开关 × 后续query开关” | 主录转换和查询均一致；后两者的内存读轨迹确认没有读私有开关 |
| 2种不同捕获身份 | 仍出现不同参数，说明尚未强制同一配置代次 |
| 8组入口控制 | 对其它模式/格式、无效开关等保持相同局部包；不代表完整模式回归 |
| proxy模型值0/1 | 局部输入0x138保持原值，目标主录元组仍为6/6/3；未运行真实代理编码 |

这些是分别构造的客体调用。原producer前面的模式筛选、memset、模型锁进入、完整包装和后续硬件调用没有在这组实验中执行；相关栈和入口状态是合成前提。捕获同一开关值也不等于真实线程或整个配置已冻结。原厂设置须先合法；非法frame2入口控制只检查没有额外改包，不能证明异常状态可恢复。

## 找到原厂 model_lock 的实际作用域

原件字符串将构造/析构明确命名为 `model::model_lock::model_lock()` 和 `model::model_lock::~model_lock()`，对应0x2aa1ea8与0x2aa1ab4。

静态正常路径显示，它维护全局所有者线程0x8e29ce8和线程上下文的0x30嵌套计数。空闲时记录当前线程，同线程重入增加计数，其它线程进入等待队列并调用条件变量；最外层退出时交接所有者并通知等待者，或清除所有者。内部短互斥锁释放后，逻辑所有权仍保持到配对析构，不能只看pthread锁的释放位置判断整个作用域结束。

两处真实调用关系给出可继续接入的范围：

- 主录对象构造：0x2c5b5c4进入model_lock，0x2c5b5d0构造并尾调原builder，0x2c5b5d8退出。
- 实时状态采集：0x27cb6ec进入model_lock，复制模型并在0x27cbbac调用状态包装，正常结果处理后回到0x27cb764退出。

这是静态作用域证据。两次严格入口测试都在原 `pthread_mutex_lock` 的未实现PLT处停止，没有补线程、锁或条件变量stub，也没有对宿主线程调用相机的锁。尚未验证实际调度、加载上下文、所有读写者参与规则或录制期间行为。

此前识别的包装记录锁仍只保护记录；本阶段找到的model_lock是另一套模型访问机制。实际激活写入者尚未实现，不能据此声称它已经安全使用这套所有权。

## 0x138字段已追到S&Q proxy设置

实时状态producer把getter0x2935aac的值写到栈基址+0x338，局部对象基址为栈基址+0x200，所以对应输入偏移0x138。该getter的模型槽位是0x831a87c；真实更新路径使用内部key0x3f3，注册名为 `setting_sq_proxy_recording`。

这补上上一阶段未确定的类型关系。输入0x138不应被当作NTSC/PAL或逐行字段修改。实验标记仅改0x1c；两组proxy输入也确认0x138及其原转换结果保持不变。NTSC/PAL数值与名称的精确绑定仍未完成。

## 退出不能只关开关、移除代码

新原型保留了合法全局模型值，但在途局部副本仍需要匹配的消费者。原指令负例验证了两个不同问题：

- 保留已标记局部包、移除查询消费者后，原查询进入断言入口；重新生成未标记原厂包后，原查询片段正常完成。
- 保留目标builder元组、移除setter消费者后，转换从VPC6变为VPC5。原MPR包准备均为codec15，但尺寸从1920×1080变成3840×2160。只核对“H.265仍然存在”不能判断回退正确。

这些是客体中的消费者缺失对照，没有制造相机故障，也未执行实际卸载、录制或恢复。它们要求将“停止新profile进入、观察/清空在途调用和标记包、重建合法原厂副本”列为移除消费者前的条件。当前还没有真实在途观察器、停录/空闲门禁、受限加载/恢复器、同机健康备份、原字节回读或冷启动/WBI验收，不能称为已具备救砖能力。

## 剩余工作保持完整

局部标记目前只接入实时状态producer。实际剩余时间producer从缓存上下文复制参数；它的缓存生成身份与新profile尚未接通，需要继续研究。主录与查询在不同配置代次捕获时仍可能不一致，必须把实际写入者、消费者、缓存和录制状态纳入统一策略。

菜单固定质量显示、NTSC/PAL条件、持久化/WBI和退回原厂设置也未实现。实际MAIN HEVC1080/29.97成片、音频、时间戳、长录温度与对应恢复仍需实机证据，精确30.000fps继续单列。没有将最终目标改为仅RAM可用或仅局部CPU测试。

## 重现与证据

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage17-captured-profile/captured_profile.py --output work/sony-firmware-20261024/stage17-captured-profile/new-capture-run
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage17-captured-profile/model_owner.py --output work/sony-firmware-20261024/stage17-captured-profile/new-owner-run
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage17-captured-profile/drain_boundary.py --output work/sony-firmware-20261024/stage17-captured-profile/new-drain-run
```

输出目录必须不存在。复用固定环境，校验目标卷、原件和依赖哈希；无USB、相机文件、后端、syscall或MMIO转发。额外分支保存所用临时寄存器/LR并保持16字节栈对齐，参考[Arm AAPCS64官方规范](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst)（2026-10-25读取）。ABI通用规则和这些局部检查不能替代机身完整调用验收。

- [捕获摘要](run-corrected-20261025/summary.json) · [捕获完整轨迹](run-corrected-20261025/captured-results.json)
- [模型锁摘要](owner-run-20261025/summary.json) · [作用域、类型绑定和停止负例](owner-run-20261025/model-owner-results.json)
- [移除消费者摘要](drain-corrected-20261025/summary.json) · [完整退出边界对照](drain-corrected-20261025/drain-results.json)
- [保留的复制解析器失败](run-20261025/attempt-failure.json) · [保留的codec差异假设失败](drain-run-20261025/attempt-failure.json)
- [阶段前目标](goal-status-before.json) · [阶段后目标](goal-status-after.json) · [持续目标](../GOAL_STATUS.json)

两次失败分别促成调度指令间隔的解析修复，以及撤回“VPC不同必然codec不同”的假设；原失败源代码与记录保留。本阶段没有新的UU连接尝试或Windows任务，仍等用户告知连接恢复；相机主动接口、认证、模式/驱动/文件/模块/WBI及任何刷写权限均未新增。
