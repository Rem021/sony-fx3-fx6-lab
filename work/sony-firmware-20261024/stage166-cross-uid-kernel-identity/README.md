# FX3 跨用户身份读取修正与03号候选

2026-10-28。**已修正主机身份读取并通过36项当前本地检查；03号未授权、未运行。** 02号实际程序已通过内置复制并进入原生ready，父ACK未放行，原生USB提供者调用0；该次正式状态仍UNKNOWN，不能当作接管或归还成功。01和02占用凭据、失败材料均保留。

## 修正及实际验证

旧观察器的完整BSD进程信息接口跨UID会遭拒。本机现存root launchd实测旧接口EPERM，而路径可读。新实现使用KERN_PROC_PID的内核有效UID和微秒出生时间，保留固定可执行路径；在路径读取前后再核对身份一致，元数据失败仍独立判断PID是否实际缺席，不能当作进程退出。没有放松父ACK，也没有新增系统权限。

[6项内核身份检查](kernel-identity-tests.json)：新方法实际读到现存root PID1的UID0、出生时间及/sbin/launchd；UID与另一短BSD接口一致，自身微秒出生时间与原完整BSD接口精确一致；混合身份、元数据EPERM保持拒绝，真实自建短进程退出与不存在PID分别核对。读取现存root进程不等于启动或验证新的root-private helper。

[12项内置复制检查](internal-stage-tests.json)、[13项启动检查](hardened-entry-tests.json)、[5项记录观察检查](recorded-observer-tests.json) 均通过，共36项。新增有界去重错误日志保存实际helper PID、errno与阶段；诊断日志写入失败时继续监管原在途进程。9个已有验证记录的fixture helper已重新核对内核缺席。所有fixture均为用户态自写程序，不含IOKit，未运行原生USB helper或管理员命令。

[固定Apple源码核对](pinned-upstream-policy-review.json) 对应[公开XNU提交](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/kern/proc_info.c)，源文件SHA 557092f14fbad3341100f59e0391d2e812c54b79a7404c89b2af97471ad67082。完整BSD同用户要求与短身份/路径分支已核验；不声称该源码与当前内核逐字节一致。本地SDK头结构、独立接口实测和错误注入分开保存。02当时未保存逐次helper errno，因此本次解释仍不能替代历史helper特定错误记录。

## 可供确认的03号单次方案

[完整候选方案](candidate-plan.json) · [固定运行包](release-bundle.json) · [源码与限制复核](local-source-and-runtime-review.json)。

- 编号：fx3-702-msc-owner-20261028-03。
- 运行包SHA-256：ababb876b9f57187f9faab6fe3d75d601a2a7c75483919c3a2d670ac1118f569。
- 原生helper SHA-256：bcbdf155ae928c88d909166b5598c66757402c4be93041706e1ac21e1a63d441。
- 目标：经典ILME-FX3、用户确认固件7.02，VID/PID054C:0DA1，location0x02100000。
- 用户目录：/private/tmp/fx3-702-msc-owner-20261028-03/；目录0700、源副本0500、共享帧0600。
- root目录：/private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-03/；目录0700、root helper0500。

新候选已编译，设备核心、IOKit提供者、原生入口流程和ABI布局与164相同；身份读取/二次核对、错误日志及编号03已按新SHA固定。继续保留用户态内置预复制、管理员复制后的精确SHA和固定不可重用租约、父进程ACK、工作期限及归还/独立缓存的分层验收。默认CLI只输出PLAN_ONLY；02授权不会继承到03。

确认本方案后，先核验卷仍已手动推出、相机开机并保持MSC、缓存唯一身份及程序哈希，再只启动一次USB接管与归还。可能短暂断开存储连接，管理员原生验证由用户本人完成；只创建上述本机固定程序和记录。不新增完全磁盘访问、驱动或常驻服务，不进行Sony认证/服务，不读卡或机身文件，不读写WBI、设置、模块或固件，不自动卸载、USB reset、强杀或重试。任何启动失败也占用03，调用在途则保留同一worker和UNKNOWN。

03现在authorized=false、released=false，未创建实际任务目录或占用凭据。真实root-private helper身份确认、IOKit接管/归还及相机功能仍待验证；完整备份恢复、独立救砖和目标MAIN 1080/29.97 HEVC尚未实现，持久刷写继续关闭。
