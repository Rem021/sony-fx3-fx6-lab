# FX3 主机回执与状态控制端整合

2026年10月30日。**已将246阶段实际验证过的主机身份/握手/回执代码接入MSC拥有者候选，控制入口限定为观察、状态、结束。8项整合检查和当前端口的2项进程检查通过；另外完成一次已授权的Mac USB缓存盘点。** 没有执行原生相机程序或再次调用管理员helper，第2项整体仍未完成。

## 已交付的代码

[host_transport.c](host_transport.c)承担对端身份、连接、HELLO确认及字节回执传递。其原生政策代码与195固定方案一致，仅调整测试宏名称；[helper_hello.c](helper_hello.c)和[host_login.c](host_login.c)与已实测源文件逐字相同。MSC拥有者不再维护另一份连接/ACK/字节发送实现。[源码与构建核验](integration-review.json)

[owner_channel.c](owner_channel.c)在绑定上下文前拒绝scope≠1，收到消息后只接受OBSERVE、STATUS、END。START、AUTH和STOP在进入原生传输层前拒绝。这里的三类消息是本机父子进程控制，不是发往相机的Sony命令；实际接管仍会涉及IOKit和存储驱动状态，不能称为零影响读取。

保持FX3_NATIVE_RELEASED=0，实际启动工厂仍拒绝执行。没有把195的已用完授权改成USB授权；没有加载或执行当前原生helper。此构建尚不能直接上机。

## 当前相机缓存与端口适配

用户确认“已连接Mac，保持MSC”后，只执行了一次ioreg缓存盘点。识别到唯一的054C:0DA1、ILME-FX3设备节点，locationID为**0x01100000**。[缓存结果](current-cache-target.json)

新候选使用当前端口，原0x02100000构建和测试源码快照仍保留。当前端口构建下，两次真实的普通用户夹具进程分别验证正常和互换管道编号，3条本机消息及私有最终结果均完成，假SDK的控制/OUT/IN调用次数都是0。[端口检查](current-port-verification.json)

缓存只保留白名单设备、端口和节点字段，没有选择、使用或保存序列号值，也没有保存原始缓存。设备节点号只是本次缓存关联，尚未作为原生入口的准入约束；没有据此证明同一台机身的程序哈希、7.02安装内容、接口健康或驱动归还。MSC模式来自用户报告。

## 本批验证的实际范围

[8项整合检查](integration-receipt.json)覆盖观察/状态/结束、互换管道编号、START/AUTH/STOP拒绝、错误nonce、错误程序摘要在拥有者动作之前拒绝，以及阻塞时伪造共享完成标志仍不被接受。执行的是自己的普通用户Mac进程、本地Unix连接及显式假SDK对象，使用ASan/UBSan；不是新的root或真机验收，也未运行Sony/内核指令或旧整套模型。

首次8项针对整合版本；取得当前缓存后只因端口常量变化重新构建，并补2项端口/管道检查，没有重复全部旧套件。当前采用[端口构建回执](build-receipt-current-port.json)，此前构建回执、initial-integration-sources.zip及[最终源码差异](source-final-revisions.json)保留。

Apple的[getpeereid说明](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getpeereid.3.html)支持Unix连接对端有效UID/GID的核验含义；PID出生时间、程序自读摘要和会话nonce另行核对，不能只用UID代替全部身份。

## 距一次真实接管诊断还差什么

[诊断草案](diagnostic-plan.json)限定为单次接管、验证接口和本机状态、归还驱动，不发Sony认证或文件/固件命令。目前有三个具体代码与交付缺口：

1. 接通原生数据页准备与root监督器工厂；当前只有可执行的夹具工厂，实际工厂始终拒绝。
2. 将夹具中的机身标签替换为明确的同机绑定材料，并把当前目标准入真正接入运行检查。当前端口绑定不能代替这一步。
3. 固定新的单次构建、nonce、完整操作范围及批准包。届时的管理员/USB接管与归还需要新的具体授权，195授权不能复用。

草案中的20秒工作预算/30秒最终观察预算不能强制中断阻塞调用。状态不明时保留原实例，不强杀、重置或自动重试；USB返回、驱动缓存与相机工作状态仍分别判定。以上缺口补齐前不请求执行草案。

本轮缓存盘点已经结束，没有在进行中的相机操作。G01至G16、恢复优先和正式0.4/0.5保持，首刷前第2至6项仍有5个前置里程碑未通过。[路线表](../../../outputs/fx3-recovery-adapter/ROADMAP.md)
