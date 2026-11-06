# 不接触相机的Mac主机登录身份对照候选

2026-10-28。**已编译并执行普通用户基线；尚未启动Terminal或管理员程序，也未触碰相机。** 04已有同PID系统日志显示接口plugin Start not permitted及可移动卷TCC转发到root会话失败；下一步先核对启动归属，不继续用相机重现相同拒绝。

## 当前已知及边界

当前用户进程实测UID/EUID501、audit UID501、Security session有图形登录与TTY。4项普通用户/默认计划/root角色拒绝/错误模式检查通过；启动器另实测当前授权不足时在创建目录、占用次数和打开Terminal之前拒绝。shell源码仅做语法解析。编译链接和未定义符号复核未发现USB/IOKit开接口、TCC、审计设置器或提权API；真正提权只由待授权的系统sudo执行。

[Apple DTS说明](https://developer.apple.com/forums/thread/678819) 解释root同样受MAC约束、Files and Folders提示依赖GUI会话和负责代码身份。目前对root登录归属的解释是日志支持的推断，并未完成本候选对照。即使Terminal下root保留GUI归属，也不能据此宣称可移动卷权限已获准或相机接口可用。

## 具体候选

[完整范围](candidate-plan.json) · [固定运行包](release-bundle.json) · [源码及权限门复核](local-source-and-authority-review.json)。

- 独立编号：fx3-host-audit-20261028-01；它不是新的相机接管编号。
- 运行包SHA-256：7204be8281541c4ec157c9be23282a4f3e54e03b53bb21d77d5ef649bd19f4c8。
- 主机probe SHA-256：86ee5e828e78b1ecf41e040567c86f57449fa9e17a055e92354bfd23f3fd03c5。
- 用户临时目录：/private/tmp/fx3-host-audit-20261028-01/，0700；程序0500、固定command0700、JSON记录0600。
- root私有目录：/private/var/root/fx3-host-audits/fx3-host-audit-20261028-01/，0700；固定probe0500，独占entry.once0400。

取得这项独立授权后，准备器才会复制哈希固定的程序和command到内置盘私有目录，打开一个Terminal窗口。你在该窗口自行完成sudo验证，不向我发送密码；程序与结果不读取或收集密码。sudo仅执行固定内联bootstrap：创建固定root目录、复制程序、复核精确SHA，再运行一次root probe。程序核对root所有者/固定路径/权限并创建不可重用租约。

probe只输出自身PID、父PID、UID/EUID、audit UID/session、Security session图形/TTY标志。不记录终端网络地址，不申请可移动卷、完全磁盘访问或相机权限，不读取TCC数据库，不更改审计身份、签名、entitlement、系统设置、驱动或常驻服务。不会连接相机、读卡或机身文件、发Sony命令、切模式、写固件或重置USB；相机可以保持原状，本测试不需要再次推出相机卷。

任何准备后失败都保留占用记录，不自动重试。Terminal打开成功不代表root程序完成；只有核对输出JSON才判断对照结果。现有04相机授权不覆盖这项额外管理员程序，准备器使用独立授权字段，当前authorized=false、released=false；尚未创建实际私有目录或占用次数。

本候选用于缩小Mac启动/归属问题，不是可移动卷权限修复或安全刷写保证。相机主录、完整备份恢复及独立救砖仍未验收。
