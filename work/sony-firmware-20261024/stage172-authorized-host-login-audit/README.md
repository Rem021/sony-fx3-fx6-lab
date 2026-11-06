# 第172轮：仅主机的登录身份对照已完成

2026-10-29。用户明确批准第171轮固定方案后，原运行包未变更，单次 Terminal/sudo 对照已完成。无需再做管理员验证。本轮没有 USB、相机、TCC 或系统隐私设置操作。

## 实测结果

| 字段 | Terminal 普通用户 | Terminal/sudo 管理员 |
|---|---|---|
| UID / EUID | 501 / 501 | 0 / 0 |
| audit UID | 501 | 501 |
| audit session | 100022 | 100022 |
| Security session | 100022 | 100022 |
| 图形登录 / TTY | true / true | true / true |
| 远程会话标志 | false | false |

两份结果的 getauid、getaudit_addr 和 SessionGetInfo 均成功；audit flags 和 Security attributes 一致。固定程序先通过 root 私有路径/所有者/权限及不可复用入口检查，再输出 root JSON。Terminal 打开返回0曾只代表启动请求；结论依据实际生成且通过字段核对的两份 JSON。

[身份比较及边界](host-identity-comparison.json) · [运行文件观察](runtime-observation-01.json) · [用户结果](runtime-terminal-user.json) · [管理员结果](runtime-terminal-root.json)。密码仅在用户自己的 Terminal 验证流程中处理，本轮未读取验证界面、键盘输入或凭据。

## 这说明什么

本轮确认：这个固定 Terminal/sudo 启动路径能让 root 程序保留当前用户501的审计归属及图形登录会话。04号既有 TCC 日志中，相机 helper 的访问归属为 audit UID0，嵌套鉴权 token 为-1，并伴随可移动卷授权转发失败。这里证明了一处启动上下文差异，为后续离线审阅提供依据。

这不是同一相机 helper 的同步对照：程序与启动路径均不同，本轮没有触碰相机。不能认定 audit UID 是04失败的唯一原因，不能据此认定 TCC 已许可、USB 插件可用或安全刷写已经具备。代码身份、负责进程归属等仍需分别核对。[Apple DTS 关于 GUI 登录、负责代码与 MAC 的说明](https://developer.apple.com/forums/thread/678819)见第171轮已保存的来源审阅；本轮不新增隐私权限。

## 授权和留档

独立编号 fx3-host-audit-20261028-01 已消耗，不自动重试。第171轮固定运行包 SHA-256 为 7204be8281541c4ec157c9be23282a4f3e54e03b53bb21d77d5ef649bd19f4c8，probe 为 86ee5e828e78b1ecf41e040567c86f57449fa9e17a055e92354bfd23f3fd03c5。20个原封存成员均复核一致；程序和 command 的内置盘副本也与固定 SHA 一致。

已保留授权、原始输出和曾出现的中间状态。`goal-status-after.json` 是首次看到 root 结果时仍待比较的历史快照；最终 canonical 对应 `goal-status-completed.json`。此前相机01—04的结果和耗用记录均未修改，也没有启动新的相机编号。

下一步可据本轮身份结果离线审阅新的固定启动方案；任何新的相机接管、认证、文件读取或刷写仍须符合其具体授权。目标主录、完整备份恢复和独立救砖尚未通过，`goal_complete=false`、`persistent_write_release=false`。
