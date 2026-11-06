# r37｜r35 诊断包的隔离宿主启动器接入

**仅宿主集成候选通过。未启动 VM、网页或服务，未部署；零首帧根因未修复。** r31 的180秒无首帧失败保持失败，FX6受拒实现不在此任务内。卷UUID已核为F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B；仅新r37目录写入，无Git操作、原CPIO/DTB或runtime复制、共享README/ledger更改。

## 最小接入

从r30的40个必要宿主源派生；只改6个原文件并新增一个纯选择/核验模块：

| 文件 | 差异 |
|---|---|
| run_trial_r24_review_snapshot.py | 新增`--r35-diagnostic-package`及互斥检查、固定selected_root/pinned_manifest、准确label、来源回执；保留原模式 |
| r35_package_selection.py | 新增；只允许固定r36 root/candidate/CPIO/DTB与摘要/体积，固定r37输出边界；无启动逻辑 |
| prepare_run.py | 输出限定本目录run-inputs直接子目录；配置写入本source root/profile，LOCAL冻结绑定新SOURCE清单 |
| runtime-wrapper/common.py | 校验新root/profile、输出边界与完整LOCAL/SOURCE对应；原操作函数不变 |
| runtime-wrapper/preflight.py | 新core/包验证、实际import-only绑定回执；保留全部原冻结/平台检查 |
| runtime-wrapper/launch_prepare.py | 原固定runner argv追加新selector；入口未执行 |
| return-tools/return_adapter.py | 精确更新新CORE摘要，增加本候选run/profile/freeze/输出边界拒绝；原单动作、完整stdout/PNG/失败End语义不变 |

其余34个原文件逐字节一致，包含operator/JS、PAGE/server、pin/confirm/recovery、20秒deadline、startup observation与串口消费；Node三模块不变，`import.meta.url`实际解析到本r37 adapter。原runner的全部非main函数未变；去掉精确列出的selector/provenance节点后**整个runner AST与r30一致**，且从`journal = ACTIVE_HOST_JOURNAL`起至文件末尾逐字节一致，覆盖原ready/输入/停止/End、restore/reap、双锁与网页finalACK分支。180秒启动、20秒动作、NAVIGATION-PLAN均未改。见EQUIVALENCE.json和r30-to-r37.diff；新增完整源为r35_package_selection.py，未用全局替换pin。

## 包与平台绑定

新选择必须同时`--snapshot-tail --gate-publish-interval 64`；procdiag/N1/内部逐键或任意`--candidate`路径均拒绝。新包缺失、摘要/体积/路径异常不会回退旧N64。新参数检查和新包纯文件验证位于任何runner进程/服务创建之前；原diskutil、原所有准入条件仍保留。

- root：`../r36-fixed-slot-package`；candidate SHA `0bf214178ab8e60d1ac7755e1d1b2fcc0d2c325ff8473abd50402f09ab81fab4`。
- CPIO：453213884B，SHA `49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff`，loader地址`0x440000000`。
- DTB仍来自原r3 guest目录，SHA `5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b`，loader地址`0x400002000`。
- QEMU SHA `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`；kernel SHA `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`。
- 原4×cortex-a35、5120MiB、`tcg,thread=multi`、无icount与model_env完全相同。新label=`v35diag-n64-r36-r37`；保留原runner basename以兼容原排他检查。

PLANNED-ARGV.json用**实际原命令构造AST**产生新旧命令，未调用runner.main、launch_prepare或start：QEMU argv只有CPIO loader文件路径一项改变，加载地址不变；candidate path/hash、来源回执与label准确更新。占位cwd的PLANNED-NOT-CREATED从未创建，不能把这份计划回执冒充真实QEMU进程argv。未来真实run仍走原TRY/runs及原资源流程。本阶段没有修改r36包内的历史`runner_bound/VM_authorized/runtime_validated=false`字段。

## 针对性离线证据

OFFLINE-CHECKS.json的7组脚本全部exit0，完整stdout/stderr在receipts/final-*；不是重跑旧43项矩阵。

1. 在执行help前检查实际CLI入口的main guard及parse_args前调用，只有parser构造/加参数；未将`--help`天然当无副作用。实际preflight受审计hook限制，只允许diskutil只读及已审查help/import-only Python，拒绝启动/网络/外部写。实际prepare/preflight只写本目录预检子目录，ledger仍空、无Start-once/runtime.json。
2. 21项selector/构造检查：五类旧选择root/label/参数保持；新合法选择；缺snapshot-tail/N64、N1/procdiag/internal/任意路径拒绝；manifest/CPIO/freeze hash、体积、固定成员缺失与输出/symlink边界拒绝。故障注入不改原包。
3. 11项**实际CLI/common/adapter**边界检查：错profile、旧source root、缺LOCAL项、外部输出，以及prepare越界/相对路径/错session/重复目录均非零退出，未创建返回目录或调浏览器/operate。各stderr原文保留在BOUNDARY-TESTS.json。
4. 实际新runner以import-only执行，审计hook拒绝process/socket/mkdir/write，main不调用；24个Mac项目模块均匹配新SOURCE或原r21 SOURCE清单。ACTUAL-IMPORT-GRAPH.json、ALLOWED-IMPORT-BINDING.json记录精确路径/sha；没有使用r30旧runner执行运行流程。
5. Node实际模块import-only，child_process方法置为拒绝，导出/相对adapter路径验证通过；没有调用executeAndLoad动作。
6. 独立调用原`cpio_audit.audit(r36, frozen/share/fx3-original-app-loader-probe.cpio)`，先检查其纯文件副作用并加拒绝process/socket/外写hook。1140成员、无目录顺序错误、20个原始基线ELF无变化，`safe_to_unpack=true`。ORIGINAL-CPIO-ADMISSION.json保留完整原结果；该门不等于VM启动验收。
7. 原preflight全部检查保留：r37 core37、原source40/delivery145、r24 delivery151、r25 delivery594、fixed14及QEMU等原链均通过，新r36路径/hash/体积/DTB追加验证。1206/1206技术输入结束复核一致，原r30/r35/r36清单以及固定平台未变；共享项目README未列为运行冻结。

## 冻结与范围

- SOURCE-FREEZE.json：42项，SHA `861b26c5aefbe393a5e58e1015914e517f0bb9e928c6f5e572a9f56816084ca9`。
- CORE-SOURCE-FREEZE.json：37项，SHA `7752a6fd7cdb74def7a3cfa9659ed6a1a4f6ab23708a5aaaed5f345e7c46f303`。
- BINDING-GRAPH.md、RUN-TEMPLATE.md说明新路径；derive_sources.py与run_offline_checks.py可在任务目录复现。预检使用独占新子目录，早期失败/被新冻结替代的预检留作历史，不当最终通过回执。最终成功目录见PREPARE-PREFLIGHT.json。
- 所有宿主子进程都已等待退出，无自有服务/浏览器/TCP端口；EXECUTION-SCOPE.json记录原始限定。没有执行launch_prepare、start_and_wait、runner.main、guest/helper ELF、QMP/设备或部署命令。

r35解析器只在未来该轮End后离线读实际串口，截止必须来自原消费证据；不得用cleanup后字节/帧回填启动成功，亦不把snapshot说成全局End原子状态。具体边界见RUN-TEMPLATE。当前没有新VM数据、首帧或连续菜单验收；后续VM须另行调度，零首帧根因仍待定位，FX6状态不改。
