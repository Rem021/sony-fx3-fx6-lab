# FX3受控物理端口切换关联

2026年11月1日UTC。**已修复259发现的“没有SERVICE串号就无法继续”这一代码路径；新实现明确使用有界物理端口关联，不伪造SERVICE串号。** 原生后端编译、八组自写代码检查和四单元静态检查通过。实际相机仍只做Mac缓存元数据读取，没有USB接管、认证、模式命令或管理员程序。

## 实际取得的主机证据

用户确认FX3已连接MSC且全部卷推出。IOUSB与IOService缓存看到唯一经典FX3，位置0x01100000、节点4295901308、三个MSC存储驱动类别；该子树没有IOMedia节点，挂载表也未见相机卷。[缓存记录](current-MSC-port-cache.json)。这个状态不证明相机固件指纹或拍摄健康。

[普通用户C探针](cached_port_probe.c)实际运行了一次：用与原生后端共用的[port_anchor.c](port_anchor.c)取得逻辑端口4294969719和物理USB-C端口4294968654。它只读取IORegistry父节点和`UsbIOPort`属性，未选取串号、打开USB用户接口或发送请求。[构建和执行回执](cached-port-probe-receipt.json)。本机匹配的父类是`AppleUSBHostPort`，不能误写为没有匹配项的`IOUSBHostPort`。

物理USB-C标识用于关联同一插口的HS/SS逻辑端口；逻辑位置和节点可在切换时变化。新后端会先确认源MSC在该物理端口唯一，再进入任何Sony交换。经过集线器而出现多个匹配设备、缺失该物理锚点或身份不明时拒绝，不退化为仅比较locationID。

## 实现的边界

[transition_identity.c](transition_identity.c)保留初始MSC串号HMAC和独立的物理端口窗口。只有原MSC固定交换完成、旧对象释放后才允许等待SERVICE。每个进入/返回窗口最多2秒和20次采样，受全局工作期限约束；原节点仍在、暂时无节点、正确的新节点分别记录，错误或超时不重新打开窗口。

SERVICE没有串号时，实际串号字段保持全零，身份类型标为`CONTROLLED_PORT`。若它确实提供串号，则必须与原MSC一致。不同物理端口、复用旧节点、错误厂商/模式、复制MSC标签冒充SERVICE串号、时钟倒退或超时均拒绝。退出后还必须出现新的MSC节点，恢复原逻辑位置和原串号，之后才请求归还驱动。

**这是采样窗口内的受控拓扑关联，依赖期间不拔线、不更换设备的物理保管条件；不能排除采样间的恶意替换，也不是密码学机身认证或完整USB事件捕获。** 对应结果单列为`HOST_RETURN_CONTROLLED_PORT_ASSOCIATION`，不会自动把G01或机内线程状态判为完成。完整独立救砖没有因此成立。

[原生后端](iokit_adapter.c)与[主机入口委托](flow_native.inc)已经接通此路径；源MSC的唯一端口与串号检查在接管前和转交前分别执行。SERVICE仅在已开启并满足窗口的状态下允许缺失串号，普通缓存身份API仍不接受这一条件作为通用替代。

[逐调用回执](flow_journal.c)新增显式物理/逻辑端口、身份类型、窗口、采样次数、源串号上下文与返回节点，保持私有文件fsync后发送。[父端](flow_receiver.py)核对进入/退出标记、原MSC交换已完成、窗口不被延长、SERVICE原串号字段未被填造及返回串号。新scope为SVC4/schema6，逐调用帧672B/FX3FLOW3，最终帧FX3RCPT4，旧格式与授权不复用。

[主机预检](cache_preflight.py)也修复了258的一处误判：Finder推出全部卷后，缓存IOMedia节点可以为0；应拒绝挂载卷、未知状态或无存储驱动，不应强制媒体节点非空。该修复用这次真实缓存形状做了纯数据检查，未重新读取介质。

## 完成的验证与仍缺的实测

[八组检查](transition-test-receipt.json)包含原生纯C窗口边界、缺失SERVICE串号且逻辑端口变化的人工SS链、错SERVICE物理端口、错返回串号、异常SERVICE串号、无SERVICE认证的控制退出、重算摘要链后仍被拒绝的伪造字段，以及零媒体预检。所有普通用户测试子进程均已退出；私有日志与父端原始帧相同。[静态检查](analysis-receipt.json)四单元无诊断。

这些测试中的USB、SERVICE节点及物理保管条件都是人工提供，未执行Sony原指令。真实证据仅覆盖Mac缓存中的源端口。真实跨模式关联、SERVICE描述符/认证/read0与退出尚未测试；不能把85条人工记录当成真机传输成功。

新候选的两个native release标志均为0，factory和渲染关闭；没有暂存、Terminal、sudo或新单次许可。下一步按用户已保留的整体继续授权，绑定新鲜源节点、物理锚点、nonce和许可，固定新的操作范围与包。原258仍不可直接运行；真实上机前必须重新确认节点和全部卷已推出。

首轮Sony诊断仍可能更新认证历史/工作模式，不是零写入或刷机。完整同机备份、独立恢复、MAIN1080p H.265和持久化准入仍未完成；16项原验收不变。[实施路线](../../../outputs/fx3-recovery-adapter/ROADMAP.md)。

公开API依据：[Apple父节点查询](https://developer.apple.com/documentation/iokit/1514454-ioregistryentrygetparententry)与[Apple USB接口定义](https://github.com/apple-oss-distributions/IOUSBFamily/blob/main/IOUSBFamily/Headers/IOUSBLib.h)。API定义不提供同机身份或可救砖保证。
