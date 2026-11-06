# r42 command 入口计时运行器

**仅宿主集成候选，未 VM、未部署。** 派生自封存 r39，不复制历史 fixtures/缓存/run。实际42个运行源/数据文件加生成 CORE 清单组成 SOURCE43；CORE38。r39 的清理 schema 名称继续保留，避免把身份升级误写为协议变更。

`r35_package_selection.py` 的历史文件名和 `--r35-diagnostic-package` 开关保留；在本目录它只选择固定 r42 包。profile=`r41-entry-timing-r42`，run label=`v41timing-n64-r42`。必须同时 snapshot-tail/N64，互斥 procdiag/N1/internal；无任意包路径或缺包 fallback。新包、旧来源 manifest 和 r41 冻结摘要均硬 pin。

绑定图：`prepare_run.py` → 本目录 config/LOCAL-SOURCE-FREEZE → `runtime-wrapper/common.py` → 本目录 preflight/launch/operate/cleanup；launch 指向本目录 runner → 本目录 selector → 固定新包。runner 优先导入本目录 startup/ring/log/PAGE，其他允许依赖仍来自 r21 冻结源。Node short_tool → 同目录 tool_call/show_result → 同目录 return_adapter → 本目录 operate；adapter pin 当前 CORE，源码实际路径详见 `IMPORT-BINDING.json`、`NODE-BINDING.json`。

本轮执行的是 prepare-only、选择器和有副作用阻断的 import-only；**没有调用** launch_prepare/start/main/动作或完整历史 preflight。原 preflight 协议和全部准入表达式保留，下一轮仍须按原协议执行。17个针对性拒绝、计划 argv 和等价证明在本目录 JSON；旧 r39/r41 测试只引用已验收回执，不冒称本轮重测。

`derive_runner.py` 为独占新建，`verify_r42.py` 为本轮有限准备/验证脚本，原 prepare 生成目录已存在时拒绝覆盖。`../r42-command-timing-package/verify_frozen.py` 可只读重核交付与外部 pin。后续运行使用另行批准的新 run-inputs，不能复用离线 preflight 输入或执行下面模板冒充授权。
