# FX3 04号：接口插件失败已定位至Mac隐私授权链

2026-10-28。**接口枚举成功，阶段103创建接口插件失败；已有系统日志进一步指出插件Start被Mac拒绝。** 04使用169轮已保留的一次授权，用户手动推出卷后重新缓存核验唯一MSC且无挂载，再执行一次。没有复用01/02/03或重试04。

## 真机和主机事实

原生root身份、微秒出生时间、固定路径及父ACK已核对。设备capture/reopen返回0，子步骤102 CreateInterfaceIterator返回0，103 IOCreatePlugInInterfaceForService返回0xe00002be（NoResources）；104 QueryInterface650及后续接口open均未进入，没有Sony载荷。错误码和子步骤保存在原SHA绑定结果中。

helper PID12230在06:49:04.955473（本机-0700）已有cfplugin日志：start failed ((iokit/common) not permitted)。同一PID在前一毫秒的TCC日志请求kTCCServiceSystemPolicyRemovableVolumes，并记录向com.apple.tccd/0转发时Connection invalid；日志带root请求/主体和auid信息。只按固定PID、子系统和短时间窗读取已存在日志，没有读TCC数据库、开启隐私日志或更改任何权限。

这将问题定位到本机可移动卷授权/归属处理路径。具体是GUI登录/audit归属、既有选择还是其他系统策略，仍需对照测试；不能把推断当作已验证修复。固定程序是ad-hoc签名且没有自行声明entitlement，但这并不能排除继承的限制。

归还、关闭返回0，helper、父监管器和中继的当前内核身份均已缺席。最初完整独立驱动比较失败，正式原回执UNKNOWN_INDEPENDENT_DRIVER_ASSOCIATION保留；稍后只读缓存复核同机HMAC/MSC/全部原驱动类别通过，用户确认“正常显示 USB／MSC，无报错”。这些不等于实际介质I/O、主录、备份恢复或救砖验收。

## 依据与下一步

[完整结果](actual-trial-result.json) · [具体子步骤及原回执](runtime-supervisor-result.json) · [已产生的插件日志](existing-helper-plugin-system-log.json) · [同PID的TCC日志](existing-helper-targeted-policy-log.json) · [稍后完整缓存比较](settled-cache-comparison-01.json)。

[Apple IOCFPlugIn实现](https://github.com/apple-oss-distributions/IOKitUser/blob/main/IOCFPlugIn.c) 中Start失败最终可汇总为NoResources；本轮固定上游提交及SHA另存，未声称与本机系统库完全同版。[Apple DTS权限说明](https://developer.apple.com/forums/thread/678819) 解释root同样受MAC约束、Files and Folders提示依赖GUI登录以及负责代码的身份归属。[Apple可移动卷说明](https://developer.apple.com/documentation/bundleresources/information-property-list/nsremovablevolumesusagedescription) 对应本次实际TCC服务。

下一步先做不含USB操作的主机身份/登录归属诊断准备，避免再用相机重复相同失败。此前批准不涵盖额外管理员运行、可移动卷隐私授权或完全磁盘访问。没有改签名/entitlement、系统权限、TCC设置、驱动、常驻服务或审计身份，也未发起下一次试验。

04已消耗；原固定程序及全部历史记录保留。Sony认证、卡内/机身文件、模块、WBI、设置和固件写入均未执行；目标MAIN主录、完整恢复回读和独立救砖继续未验。
