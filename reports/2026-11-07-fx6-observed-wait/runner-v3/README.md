# Runner v3：明确验证 snapshot proof 与完整父链

已支持 `fx6-wait-snapshot-member-diff-v1`，实际 wait-snapshot candidate 的离线 `--check` 通过。未 Start、未获取共享锁、未连接任何运行中 VM，也未重跑 QEMU smoke。v2、candidate、manifest 和父链证据保持原样。

入口：[run_observer_once.py](run_observer_once.py)，SHA-256：`8147eaa9eed628c7bf30d7d2b92f478b3d434cf047a3d8959d317451108c007b`。

## 明确支持与拒绝

只接受两种 member proof schema；未知 schema、缺字段或非 literal `true` 均拒绝：

- `fx6-observer-only-member-diff-v1`：保留原三项证明，并验证 baseline/candidate 引用与真实文件。
- `fx6-wait-snapshot-member-diff-v1`：要求 `all_other_raw_records_byte_identical`、`original_order_preserved`、`both_original_trailer_records_byte_identical`、`appfw_launcher_observer_shim_backup_unchanged` 四项严格为 true。

snapshot 路径进一步核验：

1. proof 的 `derived_cpio` 与 manifest initrd 的 path/bytes/SHA 一致，实际文件大小与哈希也一致。
2. proof `parent_observer_cpio`、child `parent_observer_initrd`、parent manifest initrd 三方一致；实际 parent CPIO 固定 SHA 为 `d02c7909458dcf8dff73fdf426953d07034cb386f8c8bd0bbd40a9440d32569e`。
3. parent observer manifest 的实际 SHA 固定为 `d5732c03c54f76f676a5fbf42fd2256715ae2afce42f9f6ddbf4e537d6c954fe`；其原始 input proof 的实际 SHA 固定为 `849a5e4d1cce49002481678dd880ea64c7c24e2ab409b399efe34740528529d3`，且再次验证原 schema/三项 bool/295→observer 的实际 CPIO。
4. parent 与 child 的 kernel、DTB、Backup、平台、model env、owner baseline 均逐项等于实际固定 SHA 的 295 manifest；baseline manifest/initrd 引用也闭合。

这是 295 → observer → snapshot 的输入证据链验证。没有把布尔字段替代为文件真实性，也没有因新 schema 而跳过旧父链。

其余运行逻辑沿用 v2，包括 Unix GDB gate、同 SHA `.started-…` 禁止重跑、未验证原厂画面标识、软件写入/回读与 guest 消费区分、未知投递停止且不重发。`command.json` authorization 精确改为 `user requested continuing repair; bounded diagnostic derived295`，涵盖短暂 ptrace 诊断，未改候选。

## 验证

- [test_runner_proof_schema.py](test_runner_proof_schema.py) 覆盖新旧 schema 接受、四项 bool 的 false/缺失/数字/字符串拒绝、未知/缺失 schema、派生引用不一致、父 manifest 固定 SHA、父 proof、295 字段和真实 CPIO 篡改拒绝。
- 原 QMP/argv 测试保留，合计 15 项通过。
- [check-result.json](check-result.json)：对 `work/fx6-wait-snapshot-20261107/candidate-manifest.json`，SHA `df39ee856ea9c667d786920c0ec9c12b43992fbc17525870cbd53b38f5c8da42` 实际执行 `--check`，返回 0、guest_started=false；有效 argv 保留 Unix `g`，没有重复 `-s`。
- [runner-v3.diff](runner-v3.diff) 记录相对 v2 的全部改动；[validation-record.json](validation-record.json) 保存来源、文件指纹及检查结果。保护输入审计前后哈希一致。

本次仅证明离线输入门正确接受已知 snapshot 派生并拒绝不完整证明。guest ptrace 成功、用户栈、软件键消费及原厂菜单行为均待主 agent 排队运行后另行验收。
