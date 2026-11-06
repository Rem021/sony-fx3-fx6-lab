# 只准备，不启动

prepare_run.py保持r24接口：--run-dir、--task-id、--dispatch-id、--session。目标目录必须不存在，包含task后缀并位于DEL；源文件从本r25候选目录冻结。环境 FX3_NAV_RUN_DIR 指向该run目录。

先执行其CLI模板中的 preflight.py，独立核原r21 SHA清单145项、r24 SHA清单151项及其清单文件pin、固定14项和真实QEMU，加载源冻结。未来部署/真实VM由协调端另行授权，本任务不执行 launch_prepare.py。

恢复CLI次序不变：click返回取消前恢复图 → 实际看该图 → recovery_cancel返回取消后独立图 → 实际看该图 → recovery_review → 单独新nonce click。任何未知由原wrapper End；不能跳过图像审阅或直接重发。
