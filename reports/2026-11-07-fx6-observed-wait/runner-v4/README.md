# Runner v4：只允许恢复指定 worker factory 调用

v4 已通过实际 worker-pool-restore 候选的离线检查，源码随后冻结。本子 agent 只做 tests/check；未启动、连接或控制 VM。实际运行与验收由主 agent 负责。

入口：[run_observer_once.py](run_observer_once.py)，固定 SHA-256：`cc2e0ab98d66a62eb767f5afe5a8f8eff2b288e50e36a0cbdc4f3fa75c2b9d39`。

## 严格的变更边界

新增明确的 `fx6-worker-pool-restore-member-diff-v1` 分支；新 shim 变化不会落入通用放行逻辑。要求 `changed_existing_members` 精确为 `['usr/lib/libgrm-fbinit9.so']`，raw records/order/两原始 trailer 的三项证明严格为 literal true。

此外，runner 直接只读解析父/新 CPIO 完整 newc 流，继续越过首个 TRAILER，重核：记录顺序与数量、两 trailer、间隔和尾零填充一致；只有一个 shim raw record 可改变；其 header 除 filesize 外不变；before/after payload SHA 与 proof 及实际旧/新 shim 文件相符。其他成员、metadata 或 trailer 的变化直接拒绝。

`fx6-worker-pool-source-change-v1` 也独立验证实际文件，严格允许两行联动：

1. 原五点 `offs[5]` 删除 `0x12d825c` 后成为四点 `offs[4]`。
2. 同一函数的 `for i < 5` 改为 `i < 4`，避免残留第五个隐式零地址。

其余源码字节必须相同；完整 unified diff 按绑定的两个源文件重算一致，offset 前后列表及 removed 列表也严格匹配。baseline/restored source、diff、shim、baseline reproduction 和新 build receipt 均校验 path/bytes/SHA 及彼此关系。

旧源复现不只读布尔值：实际重算旧 shim 与重编 ELF 的 `.text`、`.rodata`、`.got.plt` 内容/类型/flags/VMA/大小；`.got` 明确双缺失。receipt 记录的新源/output 必须绑定实际新 shim。builder 另有全部 17 个 allocated section 的复现报告，本 runner 本轮要求并独立核验上述四个约定 section 项，未声称整 ELF 字节复现。

## 全链与运行范围

新 CPIO → snapshot manifest `df39ee85…da42` / CPIO `453890e3…c926` → observer manifest `d5732c03…54fe` / CPIO `d02c7909…569e` → 固定 295 manifest/CPIO 完整递归校验。每级 proof schema、实际文件哈希、引用一致性及原冻结平台字段都保留，不跳过 v3 证明链。

mode 必须为 `worker-pool-restore`。运行目录前缀为 `worker-pool-restore-`，receipt schema 为 `fx6-worker-pool-restore-owned-run-v1`，receipt/command 均记录 mode，authorization 精确注明该诊断变更。其余预算、Unix GDB gate、120 s 上限、同 manifest SHA 的独占 `.started-…`、未知按键停止且不重发逻辑保持 v3。

这是对一个明确恢复点的输入门验证，不证明恢复后 worker 已启动、cold-boot completion 到达或菜单可用。

## 验证与来源

24 项测试通过，覆盖旧父链/argv/QMP，以及新 schema、错误成员列表、非 literal flags、实际非 shim/trailer 改动、源码额外变化、错误 diff/offset、假复现、payload/父链 pin、mode 不匹配等拒绝路径。未重复 QEMU smoke。

[check-result.json](check-result.json) 保存实际候选 `--check=0`：

- manifest：`8f3dc13a934a5d35110b7527bbae9a913c1ffdbb462a3646d4066949b462dcc1`
- CPIO：`6c698c7d1d4eac7ff54fc2bd6a54a54c3d4c9156f308aefae96b043ef22c5993`
- 新 shim：`0f2d372411e09a1aeb387a38ba7c48a3f943e5b0c2612548d965f8aa98927c9d`

[runner-v4.diff](runner-v4.diff) 是对冻结 v3 的完整差异；[validation-record.json](validation-record.json) 和 [copied-source-record.json](copied-source-record.json) 保存测试/文件/来源指纹。v3 和候选 manifest 前后哈希不变。源码已用于主 agent 的运行，此后不再修改或重测。
