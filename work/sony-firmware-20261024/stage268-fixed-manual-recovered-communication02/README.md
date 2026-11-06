# FX3 人工恢复后单次通信诊断02固定方案

本包用于验证 FX3 7.02 的 MSC→SERVICE 认证、条件固定读取和返回 MSC。**当前只完成编译及离线验证，必须取得本包新的单次批准后才能启动；这不是固件包。** 旧261通信授权及265主机清理授权已使用，不覆盖本次新增通信及恢复日志追加。

## 固定目标与前提

目标为用户的经典 ILME-FX3、固件7.02，当前 MSC `054C:0DA1`，缓存节点 `4295963942`，位置 `0x01100000`，物理 USB-C 锚点 `4294968654`。节点、线或端口发生变化时拒绝启动，不能在批准后静默换绑。物理端口关联依赖期间机身及线缆未被替换，并非 SERVICE 自带的加密身份认证。

用户已确认相机侧USB曾完全拔下，电池供电的拍摄界面及菜单正常，之后重新接回MSC；录像尚未验收。缓存中的原机身 HMAC、MSC和存储驱动恢复已核对。新试验开始前需在Finder手动安全推出相机所有卷，保持MSC、当前线和端口；程序不代替用户推出卷。主机还会核对当前缓存、驱动、IOMedia属性、内核挂载表及旧实例身份，条件不全即拒绝。

单次标识：`fx3-702-recovered-communication-20261101-02`。共享帧schema7、范围SVC5、许可v2及RCPT5私有回执均已固定，不能复用旧许可。固定构建、程序SHA和范围由[批准包](approval-bundle.json)绑定；完整具体参数见[固定计划](fixed-plan.json)。

## 这次会执行什么

1. 最多启动一个管理员helper。程序、单次标记和记录保存在 Mac 内置盘 `/private/tmp/fx3-702-recovered-communication-20261101-02` 及 `/private/var/root/fx3-owner-trials/fx3-702-recovered-communication-20261101-02`；必要的sudo／Touch ID验证由用户本人完成。
2. 使用原全局日志 `/private/var/root/fx3-owner-trials/global-fx3-owner.journal`。在同一锁内验证旧owner/observer的身份、出生时间和退出、旧试验与机身证据，再检查新鲜同机缓存及卷状态。**只追加 MANUALLY_RECOVERED 和本次 OWNED，保留旧字节及旧 UNKNOWN／OWNED，不把旧试验改成成功。** 若仅追加恢复记录后失败，保留阻止续接的尾部，不自动重试。不能通过换日志路径绕过旧状态。
3. 暂时接管USB并释放存储驱动，MSC阶段最多七次OUT/IN认证交换。等待SERVICE最多5秒、每100毫秒检查一次、最多50个样本；只接受原受控物理端口上的候选。
4. 发现SERVICE后读取设备／配置描述符，核对原厂64／512／1024字节包长三速策略及接口／管道。只有匹配策略才执行SERVICE START与最多七次认证交换，随后最多一条固定read0请求，响应体上限88字节；只保留长度、结构及HMAC摘要，不保存原始Hasp或认证内容。
5. 尝试原STOP路径及MSC返回，并分别核对调用回执、helper真实退出及独立缓存。描述符不匹配时的“仅控制STOP”分支仍是未经实机验证的退出尝试，不能当成可靠救砖能力。

Sony START、认证及STOP可能改变服务模式、历史记录或`.hasp`／`.etools`等内部状态，**不能宣称相机零写入**。本包不读存储卡或机身文件，不上传模块或运行自写机内程序，不写固件，不初始化机身，不自动申请或修改隐私权限。

## 失败与停止边界

工作预算20秒，收尾预算30秒；单个有超时参数的设备调用目标上限1秒，但内核调用无法保证可强行中断。这些预算不是程序必定退出的承诺。

仅在MSC对象已释放、尚未获取SERVICE对象、没有未返回设备调用等条件全部成立时，允许新的“空闲HELD”分支协作退出，机身结果仍为UNKNOWN。SERVICE已持有或调用未返回时保留UNKNOWN和原实例，不强杀、不重置、不自动重试；上次265清理例外不适用于本次。诊断异常后需根据实际屏幕、访问灯和缓存另定恢复步骤，不能预先保证自动恢复。

## 如何判定结果

成功目标是：取得可信的SERVICE阶段回执和固定响应结构，STOP正常返回，helper结束，独立缓存看见同机MSC及存储驱动恢复，并由用户确认屏幕正常。任何一项缺失都单列未完成；仅主机退出或USB重现不证明服务线程和机身状态全部正常。即使名义返回，本次Sony命令后的全局机身状态仍记UNKNOWN。

本地fixture使用真实普通用户进程、IPC和文件，但USB／机身为人工模拟。检查结果见[test-receipt.json](test-receipt.json)和[package-test-receipt.json](package-test-receipt.json)，不能代替真机结果。构建见[build-receipt.json](build-receipt.json)；原人工恢复证据见[fixed-prior-evidence.json](fixed-prior-evidence.json)。

上游参考固定为 [Sony-PMCA-RE a82f5ba 的USB流程](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py)，2026-11-01核对公开HEAD未变。其等待和finally退出流程是实现参考，不代表维护者已验证本机FX3或承诺救砖。

完整健康备份、独立恢复／写回、真实MAIN 1080p H.265输出、最小持久化与首刷验收仍未完成。原G01至G16和[路线表](../../../outputs/fx3-recovery-adapter/ROADMAP.md)保持不变；本次批准不授权固件刷写。
