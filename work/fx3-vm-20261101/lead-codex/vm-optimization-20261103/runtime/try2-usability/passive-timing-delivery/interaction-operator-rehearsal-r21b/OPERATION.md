# r21b 单次独立操作员演练命令

授权 task_2036cb0e6c75 / ctx_832894b219cf；只运行一次，最多2次MENU点击、1次恢复、1次confirm，实际guest=0。不得重发、复用nonce、修改原helper、自动按SHA批准。

1. `PYTHONDONTWRITEBYTECODE=1 python3 preflight.py`：两项定向无browser/server/arm检查已通过，非额外计时演练。
2. `PYTHONDONTWRITEBYTECODE=1 python3 prepare.py`：核验、启动仅本轮服务/browser、原Start、安装deadline；返回未arm截图供实际亲看。
3. 亲看初始图并保存判断后，`PYTHONDONTWRITEBYTECODE=1 python3 operate.py reject_capture`：原20秒A arm、实际operator_click一次MENU、只读归属409、原recovery capture，外层工具校验子进程exit0/精确status/新目录普通PNG/hash后同结果展示。
4. 亲看拒绝提示及新图后，另一次工具 `PYTHONDONTWRITEBYTECODE=1 python3 operate.py cancel_A`：只原recovery cancel，返回新的取消后截图；不confirm、不发键、不rearm。
5. 再亲看新图后，另一次工具 `PYTHONDONTWRITEBYTECODE=1 python3 operate.py accept_capture`：新nonce B原20秒arm、实际operator_click一次MENU、原bounded capture完整菜单并同工具返回。
6. 亲看完整Setup > Area/Date与橙色焦点后，另一次工具 `PYTHONDONTWRITEBYTECODE=1 python3 operate.py confirm_B`：仅原explicit_confirm匹配历史ACK与当前frame、取消原B；不arm/发键。
7. `PYTHONDONTWRITEBYTECODE=1 python3 cleanup.py`：End、原finalACK、dispose（仅alarm已非armed时）、关闭本轮browser/service、核PID/端口。

`run_action` 的真实调用路径包含异常清理，import和CLI共用；失败即调用cleanup并重新抛出非零，不现场重试。清理只读记录alarm；仍armed时不为dispose强行取消，关闭文档后说明timer随文档结束。失败不展示旧图、不进入下一键/确认。

后端历史PNG只用于工具链操作，不代表VM绘图时延。只比较同钟域；模型接图/看完无仪器则unknown，工具准备返回边界不可冒充实际接图。
