# r39｜重复收尾与证据保留候选

**仅宿主离线候选通过；未运行 VM、浏览器、服务、QMP、guest 或设备，未部署。** r38 仍为 1 accepted / 0 pin / 0 confirm 的失败轮；本任务未修复菜单延迟、零首帧根因或 FX6 开机。仅写本 r39 目录，卷 UUID 已核匹配；r37/r38、部署 r10、固定平台、共享 README/ledger 均未修改。

## 修复及证据边界

每次 cleanup 创建独占 `cleanup-calls/<UUID>`，保存身份、原命令完整 stdout/stderr（含 transport 异常的部分流）、process 回执、截图、HAR、deadline 状态、各阶段回执、native 原回执副本及清单。`stdout.txt/stderr.txt` 为内部流，`return.stdout.txt` 是准确的公共 CLI 返回，另有 `RETURN-HASH.json`；任何同名写入均独占创建。后续调用不写前一调用目录。

`.cleanup-owner.lock` 是长期保留的 inode；`LOCK_EX|LOCK_NB` 竞争失败即返回 `busy`，不等待、不删除锁抢占、不执行第二遍 End/HAR/dispose。owner 异常退出后由 fd 生命周期释放锁，下一次明确调用可继续真实未完成的收尾。公共 `CLEANUP.json` 只作 first/latest/completed 引用索引；`CLEANUP-FIRST.json` 保留首次结果，不能按存在或 `errors=[]` 推断完成。

`already-cleaned` 要重新核验同一 run/session/task/dispatch/launch、SOURCE/CORE/LOCAL 冻结、全部原始制品 hash、准确 finished 页面/document、alarm、browser-close、native run/command/source/进程回收/双锁/API16/quit 及 finalACK 证据，并复核当前 runner/QEMU PID 不存在、端口明确拒绝连接、双锁可取得。它不再调用任何 browser/End/HAR/deadline/dispose。检查是分时证据，不是全局 End 原子快照；finalACK 本身仅证明网页交付，须结合完整绑定。

按协调初审 msg_65bdcb794e26，坏完成索引不能阻挡本轮必要 End：先原样归档坏索引；独立核当前 native run/session/包、RUNNER-LAUNCH、准确 runner argv、QEMU 父子关系/可执行文件、资源状态，再只读核精确 URL/launch/document/run-incarnation（存在当前 attempt 时也须一致）。这些成立才进入原 End 清理；新完成后替换兼容完成引用，坏索引原文与旧调用证据仍在。资源已关闭时不访问浏览器；身份或当前归属不明则 `unknown + End_required`，没有按 PID 终止进程或访问 QMP。

所有原动作异常仍抛出。operate 自动清理仅派发一次原 100 秒 child，完整流进入新 `cleanup-dispatches/<UUID>`；首个失败 dispatch 引用不覆盖，后续都保留独立记录。return adapter 用本次 call ID 关联该 child 的清理报告，始终维持 `return_failed/ok=false/无图`；Node 仅允许本次有界、身份匹配的失败 summary 独立展示 cleanup。未知退出、缺失/错 action summary 不回读旧结果。audit_after 验证完成证书及当前资源，不消费 latest 索引的表面成功。

## 改动与不变项

9 个原文件改变，新增 `runtime-wrapper/cleanup_evidence.py`；完整差分见 `r37-to-r39.diff`，前后逐文件 SHA 见 `SOURCE-LINEAGE.json`。32 个原文件逐字节一致，包括整个 runner、PAGE/server、prepare、launch/start、startup-observation、全部键/观察/pin/confirm/recovery/helper/20 秒逻辑。common 输出路由只在 cleanup ContextVar 激活时使用，正常函数 AST 与原件一致。

`EQUIVALENCE.json` 核验原首次清理核心 AST：仅将输出改为调用目录，增加只读 ended 身份保存，移出原根目录最终打印；原 End、65 秒 finalACK 等待、5 秒退出复核、alarm 准入/不取消 armed、HAR/关闭顺序均保留。runner 整文件未改，因此 API16/QMP quit/reap/双锁/网页 finalACK、180 秒启动与原输入控制流不变；这里没有实际执行这些 guest 路径。

选择器只更新本 r39 root/profile/label 并保留 r37 来源 pin；同一 r36 包仍硬 pin，无旧 N64 fallback。profile=`r35-diagnostic-r36-n64-r39`，label=`v35diag-n64-r36-r39`；candidate SHA `0bf214178ab8e60d1ac7755e1d1b2fcc0d2c325ff8473abd50402f09ab81fab4`，CPIO 453213884B / SHA `49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff`。4×A35/5120MiB/MTTCG/noicount、QEMU/kernel/DTB 与加载地址不变；没有复制或改动 CPIO/DTB。

## 离线验证

`OFFLINE-CHECKS.json` 的 10 组检查均 exit 0，记录具体脚本 SHA/argv/原 stdout/stderr：

- 40 个 cleanup 场景：实际 CLI/main、真实独占文件和 APFS flock；browser/native/PID/端口全为 mock。包含完成后再调用、部分失败/transport 部分流/写入失败/独占冲突、armed/坏 alarm、坏/缺/错 run/source/session/launch/图像/公共 stdout、native ACK/reap/source 不成立、资源存活或检查未知、并发 owner、owner 中断、prelaunch 仍执行 End/close、坏索引当前 owned-live 必要 End、当前 owner/page 不明拒绝等。
- 代表性同 run 重复：总数保持 browser 7 / End 1 / HAR 1 / close 1 / deadline 2，第二调用增量全部为 0，首次文件逐字节不变。并发非 owner 约 0.060 秒返回 busy；中断用真实宿主进程 exit 93 释放同 inode 的 fd 锁，再明确收尾。
- 实际 operate 异常 guard 派发清理成功后，原动作仍 exit 19；实际 adapter 返回 exit 2、无图，单独报告 cleanup。Node 5 个当前失败/未知退出/错 action/缺失结果用例通过。
- 6 个实际 common/adapter CLI 新 root/profile/LOCAL 冻结拒绝；输出未创建、无动作派发。实际 prepare/preflight 和 runner/common/cleanup/operate/audit/adapter 只导入绑定通过；import audit 拒绝进程/网络/外部写，未调用 action main/launch_prepare/start。

未无差别重跑旧 43 项矩阵。真实 native/视觉/服务语义没有被 host fixture 证明；新增文件写入/fsync、hash、资源探测和格式化有宿主成本，未声称零扰动。坏索引 live 分支的三条 ps 查询各限 2 秒，不改变原 20 秒 alarm 或原等待预算；当前身份再变会由原 End guard 拒绝。

## 冻结及输入口径

SOURCE 43 项：`3f4d9894d2bfdd1bf15f2c01132006c78f8331220f8e8da1bcee4adcbd37ff43`；CORE 38 项：`642149dac737315d19dc6910804538eec6df79a43261527c06fcaf23d374bd50`。实际新 import hash、原允许依赖与 Node 相对 adapter 见 `WRAPPER-IMPORT-BINDING.json`、`ACTUAL-IMPORT-GRAPH.json`。

1398 项技术输入复核全部一致：**192 项为 r39 开工时实际观察输入，1206 项继承 r37 已验收的历史技术 pin**；合并口径见 `TECHNICAL-INPUTS-BEFORE.json` 与 `INPUTS-AFTER.json`，不能称 1398 项全是本轮 fresh before/after 快照。共享项目 README 不列运行冻结。原 r38 回执/空 HAR 的历史失败及覆盖事实没有被本任务改写。

所有宿主子进程已等待退出，无自有浏览器/服务/监听端口；过程与限制见 `EXECUTION-SCOPE.json`。早期失败/被后续源码替代的 fixture 留作原始历史，最终通过仅以 OFFLINE-CHECKS 所指原流、CLEANUP-TESTS 和最终冻结为准。后续 VM/菜单验收须单独授权；本交付不授予 Start/部署权限。

接口依据复核：[Python 3.14 fcntl](https://docs.python.org/3.14/library/fcntl.html) 的非阻塞独占锁与 fd 生命周期，[os.open](https://docs.python.org/3.14/library/os.html#os.open) 的独占/不跟随链接标志。接口文档不代替本目录的真实 APFS 行为测试。
