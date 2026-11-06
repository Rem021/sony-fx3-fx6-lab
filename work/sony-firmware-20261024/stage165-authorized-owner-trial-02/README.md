# FX3 02号单次接管：原生入口成功，ACK未放行

2026-10-28。**内置盘复制问题已越过；本次没有进入USB接管。** 用户明确批准164轮一次，固定包及162项检查点材料已核验；唯一FX3缓存仍MSC、卷未挂载。原程序启动后发布helper_ready=true，但parent_ack=false，native_started=false，native_return=3（DENIED），事件0、capture/claim均未发生。中继及原监管器正常结束，helper/中继/监管器当前内核PID均已缺席。

共享结果与标准输出的nonce、编号、PID、出生时间、返回码和SHA一致，但父监管器没有保存通过内核检查的helper身份；因此正式状态保持UNKNOWN_TERMINAL_WITHOUT_VERIFIED_HELPER_RECEIPT，不以进程exit0证明接管或归还成功。内置副本SHA和固定root入口执行记录得到进展，02一次编号已消耗，无强杀、reset或重试，旧01仍保留。

## 身份观察问题

本机用户501的同一旧观察API读取自身成功；读取现存root进程launchd的PROC_PIDTBSDINFO返回EPERM，proc_pidpath可读到/sbin/launchd，KERN_PROC_PID能确认其存在。这个只读主机复现与未ACK相符，但本次没有逐次记录helper特定errno，不能把对launchd的测试当作历史helper的直接错误记录。

[Apple公开XNU策略](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/proc_info.c) 对完整BSD信息要求同用户或额外权限，而路径及短身份flavor按另一权限分支处理。公开源码仅为参考，未断言与当前内核逐字节相同。下一步离线修复应保留内核UID、出生时间或唯一身份及固定路径校验，不放松ACK，也不扩大系统权限；先用现存root进程验证。

后置只读缓存以本次键在内存比较HMAC，仍为同机MSC和原存储驱动类别，未保存或输出键。该结果不是实际磁盘I/O、相机健康或救砖验收。Sony认证、卡内文件、模块、WBI、设置、固件刷写均未执行；目标主录和完整备份恢复仍未实现。
