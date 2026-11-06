# r24 后续独立运行准备

当前只交付离线候选，未起runner/QEMU。后续由另派操作任务核卷UUID，再创建自己的独占task目录，不能复用本次fixture目录。

```sh
python3 -B /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r24-review-snapshot-candidate/prepare_run.py \
  --run-dir /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r24-run-NEW_TASK_SUFFIX \
  --task-id task_NEW_TASK_SUFFIX --dispatch-id ctx_NEW_DISPATCH \
  --session fx3-deadline-r24-NEW_TASK_SUFFIX
```

该命令只创建config、ledger、精确源码SHA冻结和`CLI-TEMPLATES.json`，不执行模板命令。其后设置`FX3_NAV_RUN_DIR`为这个新目录，所有wrapper均`python3 -B`执行，按序调用：

1. `runtime-wrapper/preflight.py`：先核固定SHA256SUMS自身字节，再逐行核全部145项（包含DELIVERY-MANIFEST.json）；另核40源码、14固定输入、实际bf4d QEMU。当前实际离线执行已通过，原件在`evidence/preparation-fixture_audit/INPUTS-BEFORE.json`。不能用未核自身hash的JSON表替代145清单。
2. `runtime-wrapper/launch_prepare.py`：未来才调用，启动本目录`run_trial_r24_review_snapshot.py`；依赖优先级明确为候选→冻结r21→旧ROOT。当前5个关键模块的真实`__file__`/hash已在`evidence/IMPORT-PROBE.process.json`核验，无VM。
3. `runtime-wrapper/start_and_wait.py`：未来只点原Start一次，返回待机PNG，安装适配新PAGE指纹的原20秒deadline；代理实际看图后另调`operate.py standby_review "实际判断"`。
4. 每步单独`operate.py click N "计划目标"`。内部新`review_snapshot_cli.py capture`只pin一次并导出原PNG；操作代理必须实际查看返回的`review-snapshot.png`，再单独`operate.py confirm "该指定快照的实际语义判断"`。第1步仍检查完整MENU参考PNG，后续语义仍逐图人工式代理审阅，不默认通过。
5. 原PAGE明确未入队才沿用recovery capture/显式cancel/独立recovery_review/新的planned调用；其他失败立即原`cleanup.py`。完整API16、退出/reap、双锁、port、网页finalACK证据照旧，不能把fixture回收当实机回收。
6. 收尾后`audit_after.py`只读复核原固定输入；它不宣告八步成功。另核本轮真实截图语义、原生收键及完整退出原件。

## 不变和新增边界

- 固定4×cortex-a35、5120MiB、MTTCG/noicount、原kernel/DTB/N64 CPIO与实际QEMU SHA `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`。runner参数沿用8分钟、server max_steps32、snapshot-tail/gate interval64/pre-input step2；计划和helper仍仅允许8accepted，32只保留第8键后原确认ready条件。
- 新PAGE/server/confirm版本必须使用本候选配套helper，准确指纹见`PAGE-IDENTITY.json`；不冒充原PAGE SHA。依赖原库的输入门和guest/native错误路径不变。
- **原r21 runtime没有写入例外。** r24 runner的`preflight-*.json`、`STATE-v25-r3.json`和`STATE-v24.json.tmp`全部改写到本轮`FX3_NAV_RUN_DIR`；runner的正常runs证据仍沿用TRY/runs。不要再套用r23“旧runtime三个输出例外”的描述。
- r23派生`later_capture.py`仅复用当前accepted-attempt的只读guard；本候选capture/confirm入口是新`review_snapshot_cli.py`，不要调用旧live-frame capture/explicit-confirm入口。

当前15组server、6组真实browser/实际wrapper链与准备核验只证明离线协议；真实八步菜单、人类连续视觉体验、长时稳定性、FX6仍未验。
