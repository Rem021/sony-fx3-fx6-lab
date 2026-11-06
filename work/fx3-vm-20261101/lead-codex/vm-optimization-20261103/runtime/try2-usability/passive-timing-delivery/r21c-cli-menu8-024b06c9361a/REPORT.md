# r21c CLI 修复及八键真实 VM：failed

纯 host 接线修复通过，真实 VM 八键 **0/8**，本轮只启动一次。两个模块均直接导入 sys；17项独立子进程用实际源码 `runpy(...,run_name='__main__')` 覆盖 click1–8、confirm、recovery_cancel、异常入口、later_capture argv及cleanup null/nonarmed/armed/malformed/异常；未向被测globals注入sys、common替身不导出sys，无browser fixture或guest副作用。这些只证明CLI接线。

- 本任务 `task_024b06c9361a / ctx_08d29caf3254`；run `v25gate-n64-r17-fb894841`。旧29e7c98f失败原件与冻结r21/r10均未改。差分和本地源冻结在 `MINIMAL-WRAPPER.diff` / `LOCAL-SOURCE-FREEZE.json`。
- 实际固定命令与执行中argv保存在 `RUNNER-LAUNCH.json` / `ACTUAL-RUNNING-ARGV.json`；4×cortex-a35、5120MiB、MTTCG、noicount、原kernel/DTB/N64；实际QEMU SHA256 `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`。唯一tab 1280×1200。
- 启动健康通过，Start工具入口至合格待机图返回 **44.183秒**（上限180）。亲看NO CARD待机完整图；不是菜单验收。
- 首次实际CLI进入run_action、arm成功，随后原冻结operator_click在 `b.click()` 前抛出合并的 `operator_click_preflight`，helper exit2、外层exit1；ledger保留1个unknown reservation，没有PAGE attempt UUID。实际按钮点击0、key POST0、accepted0、guest step0、native down/up/done无记录、恢复0、confirm0；八项语义全未执行。实际异常入口立即原End，没有恢复或重试。
- 身份与时间：已审图gen9/seq38/SHA2914275c…；图已准备返回边界到click helper前eval边界 **8256.516ms**。这是同host时钟工具边界间隔，不是纯模型思考；模型接图/看完时刻unknown。紧邻的HAR GET `00:17:30.901103872Z` 为ready、steps0、busy=false、review_required=false，gen20/seq146/SHAe0140ea1…；`00:17:31.305347072Z`已stopping。这支持freshness失配推测，**没有eval当刻原子DOM快照，无法确认具体哪条前置条件触发**；GET不构成原子权限。详见 `TIMING-IDENTITY.json` 与原HAR。
- 完整收尾通过：API16 ACK与原字节核回，原20秒预算内用时 1.579120秒；QMP quit id213 return ACK、exit0/reap、runner/QEMU PID absent、双锁free、端口关闭、网页finalACK、自有browser关闭均核实。cleanup errors=[]；alarm仍armed时正确不取消/不dispose，以原End及关闭自有文档结束，无延长20秒窗口。
- 真实HTTP仅Start202、Stop202、finalACK200，原始HAR及body/hash见 `HTTP-INDEX.json` / `raw-http/`；browser-ready发生在HAR开始前。原始拒绝导出304B、total0，SHA256 `4e5df69aab716d362926502d18a85144b2ca5c2098ddf8744115f8ea9e5f4096`；原字节副本 `web-key-rejections.raw.json`，零拒绝不充发键成功。v5 tail明确非事务结束快照，尾后事件计数unknown。
- 前后40源码、145交付、14固定输入、实际QEMU及pre-Start本地源全部匹配。仅允许三项非冻结运行输出自然更新，前后原字节复制到run的 `authorized-runner-outputs/before|after/`；冻结manifest未改，无其他候选目录新增文件。

未部署、未操作FX6/物理相机/USB/SD/刷写。八键语义仍全未验；后续应独立处理可归因前置拒绝或预审图时效，本任务不再试跑。
