# FX3 原生owner与通信通道整合候选

2026-10-29。完成 **32项整合测试＋55项底层回归＝87项本地检查**，另有2组既有纯夹具流程。实际进程、Unix socket、同UID的内核peer身份检查与自写C代码均参与测试；IOKit设备对象由SDK形状的假vtable提供。未启动原生设备候选、管理员验证、相机通信或刷写。

## 实现结果

- 将通信阶段接到原 `owner_core` 的接口核验之后、归还之前；原生 `owner_iokit` 保留实际发现的pipe索引。USB对象只在其创建进程内借用，不传递地址给Python或另一进程。
- 新增固定长度流协议：4字节长度＋572字节请求，响应4＋676字节。有限时间内接收分段数据，限制64条请求、固定操作和消息序列，拒绝辅助FD和其它非协议输入。
- 使用真实 `getpeereid`、`LOCAL_PEERPID` 和内核PID出生时间核对固定观察者，连接核对在任何owner设备动作之前完成；每条请求和OUT／IN间再次核对。实际root到UID501跨用户连接尚未测试。
- 配置、目标快照、工作截止时间、运行结果和保留判断放进管理员程序私有内存。共享区只发布进度与结果；清理判断使用私有返回码，不信任共享报告。观察者改写报告、PID或截止时间不会更改已捕获的私有决策。
- 实际调用未返回时不终止线程或清理。任何START尝试之后，即便STOP已返回，仍保留owner、句柄及其堆／栈存储；不把它当作机身线程退出证据，也不自动STOP、重置或归还驱动。原生入口会保持进程存活。测试程序仅通过独立的假设备gate终止这类场景，未伪造物理恢复。

owner ABI更新为4，entry schema为3。新候选标识 `fx3-702-native-owner-channel-20261029-07`，**不是已获批准的试验**。`entry_target.h` 固定 `FX3_NATIVE_RELEASED=0`；原生入口整体拒绝执行，原生路径另限制为observe/status/end，MSC鉴权只在假设备测试编译中启用。旧05等一次授权没有复用，06仍未批准。

## 关键文件与验证

- [owner与清理门槛](owner_core.c)、[同进程IOKit接线](owner_iokit.c)、[有界通道](owner_channel.c)、[入口与私有状态](owner_entry_main.c)。
- [最终构建](build-receipt-v5.json)：原生候选仅编译／链接；测试helper启用AddressSanitizer和UndefinedBehaviorSanitizer；假设备helper和IPC库不依赖IOKit框架或libusb。
- [32项真实进程整合](integration-results.json)：正常归还、分段帧、反向pipe、nonce／代次／超时／长度拒绝、FD关闭、身份错配在owner前拒绝、START权限限制、共享区篡改、64条上限、一次lease重放、三类原生调用阻塞和真实观察者退出。观察者退出时，阻塞的假OUT仍保留；显式释放假调用后不再IN，owner继续保留，三项清理调用为0。
- [55项底层回归](wire-regression/results.json)：在本轮C／头文件／假vtable上重跑已有通道检查，另含2组纯夹具流程。未把此前工具0.4的47项算作本轮重跑。
- [交叉核对](verification-receipt.json)绑定最终构建、源码、执行报告与前轮原件；[实施限制](implementation-review.json)列出剩余项。主测试报告的helper_processes=31是主进程Job计数；计入孤立owner任务及重放，本轮最终测试有32个owner任务、33次假helper执行，另终止1个自建观察进程；没有终止真实设备owner。

## 修复过程与保留证据

初次测试在假设备旧61秒时间基准处提前拒绝；修正为本轮整体截止时间。随后真实Mac辅助FD测试暴露截断接收后的描述符残留：小缓冲区失败时前后为3／19。最终按[XNU控制消息约束](primary-source-review.json)接收一个流字节并预留512-FD容量，拒绝且关闭收到的FD；32／200个FD和零数据情形的最终描述符计数相同。该边界只按当前测试环境与所查源码陈述，不是任意未来内核的保证。

另一次失败是测试先观察到假调用gate、尚未等到10ms进度镜像就断言pending；改为同时等待两者。初始校验器误把旧回归报告的sources字典当列表，也已纠正。所有失败报告、当时脚本、早期二进制和对应源码ZIP保留，未覆盖为成功记录。

## 尚未完成与下一步

整合完成的是C owner／通道候选，**不是已发布的实机控制器**。尚须把固定Terminal启动、用户侧监督器和受保护结果交付移到ABI4/schema3；补跨未来grant／进程的全局排他机制。单进程once标志与单grant lease不等于全局相机租约。

共享映射采用协作观察者模型；未验证恶意截断映射的安全性，也不是完整的恶意本机客户端隔离边界。root跨UID、真实MSC后续身份／模式变化、SERVICE接口、真实鉴权退出、机身读取准入均未验证。实际原生入口仍关闭。

后续先完成启动／监督与全局排他，再形成可核对代码和范围的单次预检；不复用已消耗授权。当前7.02同机p1备份、受限ET_DYN装载、冷启动/WBI和独立恢复仍是完整目标的必需项，不能用这些本地通过替代。持续目标[active](native-goal-observed.json)，goal_complete及persistent_write_release均false。
