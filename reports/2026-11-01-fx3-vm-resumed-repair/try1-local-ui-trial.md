# TRY1 本机网页菜单试用

Lead `msg_3a52a0ab7e46` 要求优先提供用户亲自操作入口，AP102 保存触发观察顺延。交付入口：[中文使用说明](../../outputs/fx3-vm-trial/README.md)，默认网址 `http://127.0.0.1:8765`，需要先执行说明中的启动命令。默认最长60分钟，每轮最多30次按键；结束试用后 HTTP 服务也退出。

## 实现范围

固定使用 AP101-r4 candidate，SHA `fdcd0a3cf614473e233d0d39df78a47765f9eff433b9a0e5d67e9253f943a1f9`。原 CPIO、DTB、QEMU、GPE-v8、OSD消费者、原 Backup.bin、原模块和所有模型逐字复用。新文件只实现宿主网页、日志检查及已提交帧的只读导出。`run_trial.py` 是入口，当前实现保留在 `run_trial_v3.py`；旧宿主版本及各轮 observer-source 全部保留。

HTTP仅监听127.0.0.1，提供七个按钮：上3、下30、左15、右1af、确定1ac、MENU1ab、删除1f8，hold固定100ms。HTTP线程只提交单个待处理请求，主循环单独持有QMP/GDB，复用冻结 `gate_input101.InputGate` 的白名单、步数、头部、写入及读回校验。每次点击记录用户所见提交帧编号和PNG SHA，写入自身软件控制区41df00008/12B，保存native down/up及按键后的帧证据；没有预设导航脚本。

画面沿用冻结 OSD ring 的提交、映射/父资源身份、span及FNV检查，只采样 `(sequence-1)%8` 最新提交槽，不重复读取可能已改变的原绘制表面。约0.4秒查看一次新帧；静态画面只读256B头部。每次已提交快照的RGBA导出保持原ring解释与不透明展示约定，宿主不发OSD ACK，也不写原UI/参数。七键、步数上限、用户看图与慢速固件响应分别保留边界。

串口原文件完整保留；增量扫描每一新增字节，跨块保留匹配窗口，所有原先的断言、异常、未支持GPE/媒体/按钮合同检测继续生效，发现后网页提示并停止接收按钮。页面结束、SIGINT/Ctrl-C、SIGTERM、总时限及宿主错误共用收尾路径，恢复原API16B、QMP quit、reap、PID/输入SHA/锁复核，输出receipt。

## 自测与证据

两版接口边界测试各5组通过：[v1日志](../../work/fx3-vm-20261101/menu-repair-01/runtime/check-trial-v1.log)、[v2日志](../../work/fx3-vm-20261101/menu-repair-01/runtime/check-trial-v2.log)。覆盖七键、重复并发点击、非白名单/类型拒绝、未知帧、30步限制、结束后拒绝、127.0.0.1/Host/Origin/会话与路由范围、跨块原断言阻断，以及实际AP101提交槽的FNV/注册身份损坏拒绝；接口测试不等于固件UI验收。

第一轮 `try1-5bddcce3` 在实际 Orca 浏览器完成：启动→待机帧8→点击一次MENU→原厂Principal菜单→点击结束试用。待机画面为HD、Fixed-59,94fps、EV+0.0；菜单可见 `Principal > Principal1 > Tx. quadros grav.`、2/59、59.94p、ISO100、PP11、Página和MENU Fechar：[原菜单PNG](try1-menu-v1.png)、[网页截图](try1-browser-menu-v1.png)、[视觉记录](../../work/fx3-vm-20261101/menu-repair-01/runtime/try1-selftest-visual-v1.json)。MENU发送到首次采样新提交帧约87.931宿主秒，这是本轮具体测量，不能当作固定响应时间。

第一轮receipt `health_pass=true`、必需标记齐全、无串口断言/异常，QEMU exit0/reaped/PID absent、原API16字节恢复、native unbind0、输入SHA不变、两锁释放。回执：[try1-5bddcce3](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/try1-5bddcce3/receipt.json)。用户点击已送达与实际画面更新是不同阶段，首版等待提示过早恢复；v2增加原生双事件/新提交帧等待，以及明确的画面未变提示，调整窄窗口布局。

第二轮 `try1-313c21b7` **未通过UI自测**：宿主新增120秒首帧门槛过短，提前终止尚未首绘的固件，零按钮。`health_pass=false`，不能称为首屏成功；异常收尾仍QEMU0/原API16恢复/native unbind0/reaped/PID absent/输入不变/两锁释放：[失败回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/try1-313c21b7/receipt.json)。v3取消固定首帧停止门槛，继续显示等待提示，仅保留用户结束、异常和总时限收尾；模型没有改变。

最终 v3 `try1-740a3263` 也在实际浏览器完成冷启动待机→一次MENU→原Principal菜单，画面与七键按钮在880px窗口同时可见，浏览器console为空：[菜单PNG](try1-menu-v3.png)、[最终网页截图](try1-browser-menu-v3.png)、[视觉记录](../../work/fx3-vm-20261101/menu-repair-01/runtime/try1-selftest-visual-v3.json)。随后向本轮已核对命令行的observer PID发送SIGINT，走与终端Ctrl-C相同的处理路径；全轮189.669秒，receipt `stop_cause=Ctrl-C`、`health_pass=true`，必需标记齐全。实际活跃帧采样间隔中位数0.4934秒，约2.027fps；这只衡量宿主导出频率。

独立只读复核两轮成功及一轮宿主门槛失败：QEMU均exit0/reaped/PID absent，实际恢复文件逐字等于原API16字节 `000b00b4fd7bbba9fd030091f35301a9`，全部输入SHA相同，每步down/up均有原生接收，两锁可重取、8765端口释放，所有RM lease原生free恰好一次0。最终轮完整检查11196092B串口，与实际文件大小一致，未发现断言、异常或GPE拒绝。[最终回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/try1-740a3263/receipt.json)、[独立复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/try1-independent-review-v1.json)。

**TRY1已完成，当前自测实例已退出；用户先运行说明中的命令，再打开本机网址。** 原有AP101-r4保持preferred candidate，AP102继续顺延到用户试用结束、运行锁空闲后按Lead安排执行。未进行60分钟持续性验收；60分钟是程序配置的防遗留上限。

## 限制

高亮可能不可见；部分底色缺失及文字叠印；没有实时取景；语言修改落盘尚未验收；画面仍采用近似混合。冷启动与首次菜单可能需要几分钟，2–5fps仅表示宿主查看新帧的频率，不表示固件界面响应速度。30步是冻结按钮模块的每轮限制。关闭网页不会退出模拟器，需要“结束试用”或Ctrl-C；用户下轮从固定原保存文件冷启动。

技术依据：[QEMU监视器](https://www.qemu.org/docs/master/system/monitor.html)、[Python HTTPServer接口](https://docs.python.org/3/library/http.server.html)（2026-11-02核对）；原厂菜单、文件与固件状态结论以本项目当前运行证据为准。
