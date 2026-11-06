# 276仅主机收尾实际完成

用户单独批准后执行固定程序一次，原helper PID29141仅SIGKILL一次，确认消失后，原观察器PID12633仅SIGTERM一次。两者均已结束，独立PID查询为空，原exec session22872以143结束；不再轮询或重启它。

固定程序及批准包前后摘要一致，程序返回0、stderr为空，journal文件身份及完整摘要未变。原通信03的81帧、私有回执及HELD/UNKNOWN保持保留，不写CLEAN、不授权新通信。

相机全部USB线始终断开，未访问USB、相机、驱动或固件；用户此前已确认电池拍摄界面和菜单正常。收尾后缓存未见Sony节点。无需再做管理员验证。

[实际结果](actual-host-cleanup.json) · [原始stdout](root-stdout.log) · [启动结果](launcher-result.json)。这证明主机收尾完成，不证明原SERVICE正常STOP返回、固件救砖或录像成功。
