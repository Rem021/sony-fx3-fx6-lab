# FX3 Sony通信入口：阶段影响与退出准入

2026年10月31日。**12号Mac接管/归还实测仍通过；本轮没有新增真机验收。** 已补一份通信阶段影响清单和离线结果判定代码。Sony认证/挑战试验尚未形成可执行的完整退出方案，本轮不申请上机，也不把4次传输称为零副作用。

## 新增的原件核对

[静态审查器](audit_phase_effects.py)核对4个完整FX3 7.02原函数、39处指令和7项原跳表。原库SHA256为a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410；只解析文件，没有执行原指令。

1. 逻辑命令1进入挑战分支0xbce8；命令5和7都进入完成分支0xbe28。今后的“只取挑战”发送端必须是明确的命令1白名单，不能仅写成“不发命令5”。正常挑战分支没有直接跳到完成尾部，但这不排除其它线程或异常停止的影响。
2. Serialize在回调返回-6/-4、其它负值、零或超出剩余长度时，不是返回一个普通错误供NIN处理，而是进入pthread_testcancel/sched_yield循环。-6/-4分支先经0xb19c尝试释放属于当前线程的两项互斥锁；该helper不是关闭USB或恢复模式。正的短进度会继续累计至请求长度，函数自身没有截止时间。实际底层回调是否阻塞、如何被STOP解阻塞仍未证明。
3. 完成回复Serialize在0xbe6c；之后才是Hasp回调0xbea4、完成回调0xbf2c、条件日志更新0xbf4c和后续模式文件分支。已保存的136/149证据说明，最终6/1回复既不能证明摘要被接受，也早于后续条件写入与线程结束。

完整函数、原字与分阶段清单见[phase-impact-audit.json](phase-impact-audit.json)。初始审查将0xb19c暂称transport-state helper，完整FDE和pthread_self/mutex_unlock核对后改为条件互斥锁释放helper；初始代码/输出保留，未把它误列为实际USB清理。

## 本轮实际写出的代码

[auth_observation.py](auth_observation.py)是未来主机报告可复用的纯CPU判定器，没有USB、管理员或程序启动入口。它区分单次挑战、部分交换和交换结束；只凭返回码/最终字节，始终保留authentication、mode transition和camera thread exit为未验证。

[回归检查](test_auth_observation.py)直接消费149已保存的5组原函数CPU夹具记录，不重跑guest：正确摘要和错误摘要都曾得到8/4/8/4/8/4/6、最终字节1，现在均只标记EXCHANGE_FINISHED_AUTHENTICATION_UNVERIFIED。另检查3种合成帧格式场景、拒绝6种畸形或不一致输入。此代码尚未接入任何获准的原生发送包，不构成认证成功证据。

## 为什么仍不启动挑战试验

START/STOP已有原证据表明会影响驱动/异步队列；单次挑战避免了正常认证完成分支，却没有补上STOP后的接收解阻塞、取消等待及线程终止证据。现有250原生channel本来就只放行本机OBSERVE/STATUS/END；若曾发START，local started/start_sent未解除时会保留所有者。不能为让程序退出而擅自清这两个标志。

本轮也审查了GET_MAX_LUN一类标准MSC查询作为退出凭据的想法。Sony官方Ver700参考类请求分派按配置/接口调用类回调，不带NIN线程结束记录。它可作为接口就绪的辅助信息，不能单独证明Sony服务线程已结束；这里没有把Ver700源码当作精确7.02实机测量，也没有发送该查询。

下一步明确到两件事：在现有模式摘要工具基础上，绑定初始MSC与0336服务两段的实际处理者，寻找真正只读且受认证级别限制的验证指令；继续追STOP到底层接收回调的解阻塞及主机可观察完成条件。若没有这两项，就交付缺失条件，不再包装同一4传输候选或重复Mac接管测试。[机器可读准入结论](admission-decision.json)。

## 最新公开参考核对

本次API固定PMCA HEAD为a82f5ba（提交日期2022-08-18），Sony源码字节与既有固定参考一致；不是新的FX3实现。[维护者源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py)。

A7CII服务预加载仓库HEAD为1619f938（2026-10-15），[维护者协议](https://github.com/YuuLuo/a7c2-service-preload/blob/1619f938663a36d41e72302a8cfee89a0f6acd1a/PROTOCOL.zh-CN.md)仍说明其2.01机身先MSC、再0336二次认证；其临时代码执行和永久更新准入分开，不能据此证明FX3退出或救砖。

QAQ仓库取得HEAD ef7db116（2026-10-25），本次README内容下载失败；保留网络错误，不把失败说成仓库没有变化或恢复方法已验证。PMCA commands和Yuu协议在后续Contents API取得固定原文；所有下载材料只作文本读取。

同机完整备份、独立恢复、MAIN1080p H.265及最小持久化准入仍未通过。G01至G16保持；12号授权已消耗，11号UNKNOWN保留；没有USB缓存、管理员、Sony认证、上传、读卡、驱动或固件写入操作。
