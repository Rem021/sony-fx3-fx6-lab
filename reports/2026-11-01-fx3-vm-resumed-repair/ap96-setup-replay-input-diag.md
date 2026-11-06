# AP96 设置后RAM回放与输入线程诊断

2026-11-02，600秒已收尾；QEMU生命周期通过，原应用assert后停止，未达待机或菜单。Lead msg_48dccc7b7d3d授权600秒轮：以AP95保存RAM启动、按钮worker只读诊断、稳定后MENU为step1；菜单出现后才浏览。

候选 ap96-v1-setup-replay-input-diag：原回放算法不变，新helper v2固定输入SHA 191924ef39d996171ae06ab4ca85e249b655b16db6b68fd1e2ddea45efc60bdc；AP95provider v6的新v7仅追加自己软件控制页的逐poll字段/计数、条件变化及每秒串口采样、原接收队列是否存在的每秒只读查询，screen_gate_used=0（原输入worker没有screen门控）。init从新tmp身份文件取得pid/tid，独立读/proc线程status/stack/wchan，worker本身即使停住也可取证。GPE/backend/OSD/所有原件不变；除新观测init段、输入provider、固定回放helper与输入RAM外其他CPIO成员体一致。

回放宿主ASan/UBSan：准确SHA、两bank头、完整复制、重映射读回、实际回滚、错误源/短文件无写均通过；实际输入worker宿主13命令（第13条MENU）及未知第14条拒绝通过，未发现静态12步上限。init语法、身份文件换行、外盘UUID、双锁FREE与无QEMU预检通过。

运行 ap96v1replaydiag-0f72a1e0：guest回放SHA与独立host QMP 2232320B SHA均精确相同，before_AP=true。首屏仍是Language语言选择列表，原开屏2ae→fa，因此“回放后跳过首次设置、直接到待机”未通过；英语标题说明至少语言状态可见，不能据此认定其余设置全部持久化。

实际查看 ap96-phaseA-before-SETUP.png 后，MENU为step1已发送down/up并被原IInputRecv接收；ap96-step-01-key-1ab.png仍是语言页，没有菜单。不将它等同于设置后MENU失效。新worker tid327持续poll、failed0、receiver_seen1、原输入队列存在；独立内核栈在正常等待时含hrtimer_nanosleep。当前尚未重走设置流程，故也未复现第12步后停滞。

[逐步截图](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-01-key-1ab.png) · [阶段回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap96v1replaydiag-0f72a1e0-interim-review.json)。本轮仍在600秒有界观察中；退出码、进程回收、输入不变、锁释放均须收尾后核验，不能提前算健康通过。

## 最终结果与停止诊断

Lead msg_2b097e11c8bf授权继续原设置。实际English确认后跳过隐私页，进入手机引导；删除→区域/日期→高温Set later→HOME→Creators说明。第11步ENTER后原开屏到screen0，原应用在infra_wrapper_bb.cpp:870断言，继而lib_assert.cpp30 Assertion false，最后key线程327呈T(stopped)/do_signal_stop。最后poll35068/stage7/done11/control11/failed0/receiver_seen1/last_send0/原输入队列存在；不是固定12步上限。未再发键，未发SIGCONT或改门控。

请求600秒/实际600.909秒；qemu_exit0、reaped、独立PID不存在、双锁FREE、所有输入SHA重核相同、missing[]；22包发出并原接收，11个完成步骤和11张PNG，provider全部lease原接收者恰好free0。`health_pass=false,native_application_failed=true,lifecycle_pass=true`，不能把maps存在当作运行存活。531条完整GPE记录，交错记录与停止前后-1021/-1022邻接目标/栈单列。

现有三次全进程快照都在assert之前；之后独立观测只覆盖key线程。因此本轮没有事后全进程State/所有线程stat，不能伪造或由单线程T推定全部线程停止。已解析保存已有/proc/228/status、各task/stat及停止计数；AP97 init将加全窗口独立采样。

证据：runtime/ap96v1replaydiag-0f72a1e0-review-v3.json、同名-thread-live-readonly.json、同名-process-stop-evidence.json及ap95-ap96-native-assert-correction.json。Lead msg_1866471baef3授权AP97重复面板enum2消费修正与600秒验证；未改既有run/原件。

| step/key | 实际查看画面与后续选择理由 | PNG |
|---|---|---|
| 1/0x1ab | MENU后仍是Language语言页，English已选，按钮线程已执行step1；Lead msg_2b097e11c8bf授权继续原设置，确认English | [ap96-step-01-key-1ab.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-01-key-1ab.png) |
| 2/0x1ac | 确认English后直接进入手机设置引导，底部垃圾桶图标Set on the camera，未再出现隐私页；按实际画面删除/C4选择机身设置，继续复现设置退出路径 | [ap96-step-02-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-02-key-1ac.png) |
| 3/0x1f8 | Set Area/Date/Time 对话框，Enter与Cancel；确认Enter进入区域页 | [ap96-step-03-key-1f8.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-03-key-1f8.png) |
| 4/0x1ac | Area Setting，Tokyo/Seoul、GMT+9.0，底部OK；接受本轮默认区域，继续 | [ap96-step-04-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-04-key-1ac.png) |
| 5/0x1ac | Date Format列表，Y-M-D等四项；确认默认日期格式进入日期时间 | [ap96-step-05-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-05-key-1ac.png) |
| 6/0x1ac | Date/Time显示2021-1-1 12:00 AM，底部OK；确认日期时间，查看后续首次设置页 | [ap96-step-06-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-06-key-1ac.png) |
| 7/0x1ac | 高温断电设置提示，Set now / Set later；下移到Set later，保持与AP95相同选择以复现 | [ap96-step-07-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-07-key-1ac.png) |
| 8/0x30 | 下键后仍为高温设置提示，当前截图高亮不清晰；确认刚才下移的Set later，查看下一页 | [ap96-step-08-key-030.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-08-key-030.png) |
| 9/0x1ac | HOME使用设置提示，Would you like to set up HOME for use；确认原默认选项，沿AP95路径继续 | [ap96-step-09-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-09-key-1ac.png) |
| 10/0x1ac | Creators App说明页，介绍图像传输、遥控与MENU网络连接入口；确认说明，复现设置退出后输入停滞并立即查看只读诊断 | [ap96-step-10-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-10-key-1ac.png) |
| 11/0x1ac | Creators说明页早帧；随后原assert，停止发键 | [ap96-step-11-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-step-11-key-1ac.png) |
