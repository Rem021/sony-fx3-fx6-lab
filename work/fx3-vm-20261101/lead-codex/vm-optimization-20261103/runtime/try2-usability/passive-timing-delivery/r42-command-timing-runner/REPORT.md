# r42｜计时包精确宿主绑定

**离线宿主集成验证通过；未 VM、网页、服务、QMP、guest 或部署。** 没有性能改善、根因修复、菜单或 FX6开机结论。

从 r39 SOURCE43 仅复制必要冻结文件，未复制历史交付树/fixtures/缓存/运行目录。4个运行文本变化为 selector 的硬包路径/hash/APPROVED_HOST/profile/label及来源 pin、runner 的一处准确选择说明、preflight 的3处回执标签、return_adapter 的当前 CORE 摘要；另生成 CORE/SOURCE。完整差分 `r39-to-r42.diff`。其余 **38个 SOURCE成员逐字节一致**；runner 全文件只逆向消除 help 文本后即与 r39 一致。preflight/adapter 逆向相等、selector 仅绑定规范化后 AST 相等，见 `EQUIVALENCE.json`。

r39 原独占 cleanup 证据、End-first、重复清理幂等、失败流完整保存全部原样保留；PAGE/server、ready、输入接收、180秒/20秒、两次额外观察、独立看图→pin→看固定图→confirm、recovery和8accepted/10attempts/2recoveries等预算均未改。没有新增自动 pin/confirm/retry。

新 profile **r41-entry-timing-r42**、label **v41timing-n64-r42**，固定包 `../r42-command-timing-package`。实际正例选择通过，17个负例覆盖 options、manifest/hash/体积、原包路径/缺包无fallback、host/输出边界、真实CPIO摘要故障和解析后路径/平台错误。故障在受控内存注入，未修改原包；`SELECTOR-TESTS.json` 保留原因。

实际 `prepare_run.py __main__` 只在本目录 `run-inputs/preflight-926a20c9ff87` 生成5份离线输入；40个实际模块和 Node 适配器完成 guarded import，无副作用尝试，所有运行 main 未调用。导入路径/摘要均匹配本轮 SOURCE 或原允许冻结源。没有执行完整历史 preflight 的1398项扫描；原协议仍保留。

`PLANNED-ARGV.json` 从实际 runner AST 只执行纯命令列表/env构造；**不是实际运行 command.json**。同一占位输出目录下与原 r36 命令比较，仅 initrd 精确路径不同，模型环境相同：4×A35/5120MiB/MTTCG、无icount，原 QEMU/kernel/DTB、initrd 0x440000000 不变。计划回执中的 QMP/GDB/暂停参数只是原字符串，未连接/执行。快照列表在此计划回执中故意为空，未调用读取DTB快照构造；真实 runner 对应分支逐字节不变，不能用空列表替换运行策略。

本轮复用 r39 40清理/6边界/5Node及 r41 5组成对host/18组解析等**既有验收**，未重跑大矩阵；本轮新回执只证明封装、选择和源码绑定。输入区分初始/后来观察/导入后首次pin，结束复核仅必要技术材料。下一轮真实串口必须用当轮原 End cutoff，不用清理后帧或摘要补启动成功。

最终必要技术 pin 去重 **122项**，其中外部原技术输入 **99项**、本轮产物依赖 **23项**；结束复核全部一致。时点口径见各观察清单及 `INPUTS-AFTER.json`。
