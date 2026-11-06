# 265仅主机清理实际结果

批准包和暂存程序重新核对后，用户授权的单次清理已完成。固定程序回报helper85066收到一次SIGKILL、观察器82324随后收到一次SIGTERM，二者均退出；普通用户独立libproc核对两PID均不存在，原exec51030结束码143。launcher退出0、stderr为空。本次没有额外管理员验证等待。

程序对原全局journal的前后文件身份和字节摘要核对相同，保持原OWNED/UNKNOWN；没有USB、驱动、相机或固件操作。此处关闭的是主机进程收尾，不把262的通信HELD改成正常完成，也不授权下一轮相机试验。相机侧USB继续断开。

[实际结果](actual-host-cleanup.json) · [启动前许可与身份](authorization-and-preflight.json) · [原输出](root-stdout.log)。root私有原件继续保留。
