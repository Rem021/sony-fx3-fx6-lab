# AP92运行链恢复入口

AP92已完成，不重跑：ap92media-9e1c3a07，301.547s，receipt健康/必需marker空缺0/双锁FREE。报告 ap92-media-detection-mount-observation.md，STATE phase AP92_PASSIVE_MEDIA_DEFAULT_INSERT_AND_NATIVE_MOUNT_FAILURE_PROVEN_WAIT_AP93。

原ThreadInit wait110→默认三次80000006→StartInOut state0/fa24 status0/fa3c status1，为两槽插入来源。RM两次80000004均未实际send，FRONT与GetInOutStatus均未执行。Common两次228B回复valid1；路径/nondev/rm3、/nondev/rm2，原open80000004，Mount7fffffff。参数见报告。

新增weak hook无应用插入发送栈，既有capid完整28B/tid/source/caller保留；Lead msg_394ac6fda280明确不为此再跑。observerv2/AP92r2仅构建未运行，不要误启动。等待Lead audits/rm-media-service及AP93合同。未worker_done；继续唯一运行链所有权。Heartbeat80723，stopfile .heartbeat-stop-ctx_ee4f6943c8d7-ap91，17:07UTC附近到期时若仍工作应核对重启；不要重复创建存活的heartbeat。

使用过的helpers v1/capid47和run92均冻结；原件/旧runs/旧helpers不改。证据辅助脚本verify_media92.py复跑SHA/36点/20getter/40ASLR/20setterxref；review_media92.py会生成PNG，已有PNG时不要无条件重跑。所有编号行按read_bytes.decode.split('\n')。报告PNG已目视仍日文槽1警告、SHA与AP90一致，77GPE均0，非菜单。
