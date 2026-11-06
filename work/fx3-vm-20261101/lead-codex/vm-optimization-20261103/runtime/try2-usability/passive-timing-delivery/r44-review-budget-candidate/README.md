# r44 60 秒整步审阅期限候选（隔离离线）

**状态：候选，未启用。** 当前有效政策仍是 r42 的 20 秒；本目录未修改任何运行入口、固定 FX3 硬件配置、CPIO、内核、DTB、QEMU 或旧输入。不要在本轮直接运行本目录的任何启动/浏览器/VM 命令。

## 先看

1. [REPORT.md](REPORT.md)：结论、输入身份、改动、保留边界、离线回执与限制。
2. [POLICY-CHANGE.md](POLICY-CHANGE.md)：旧 20 秒 → 候选 60 秒的具体范围、未改项、用户批准后的未来命令（现在不得运行）。
3. [CANDIDATE-POLICY.json](CANDIDATE-POLICY.json)：机器可读 profile/label/预算/封存包/保留项。
4. [CANDIDATE-DELTA.json](CANDIDATE-DELTA.json)：43/38 清单、13 个源码改动、29 个未改条目的 old/new hash。
5. [receipts/r42-to-r44-source.diff](receipts/r42-to-r44-source.diff)：精确 unified diff（含 return_adapter 自绑定与 CORE 清单）。

## 候选身份

| 项目 | 值 |
|---|---|
| profile | `r44-review-budget-60s` |
| label / run 前缀 | `v44review-n64-r44` |
| SOURCE43 | `3ab27924f456209af961412b876cefa9d23b7f0230b10bc160103a8ef58d995c` |
| CORE38 | `b9d92bc251fb6da2577af7d7f50c2b646db9797000913b747327636c2e3999f1` |
| 封存包 candidate | `857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806` |
| 封存包 CPIO | `59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63`（453213884 B） |
| 固定 DTB | `5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b` |

## 回执

- `receipts/fake-clock-deadline.json`：14/14，核心 60 秒 fake-clock 行为。
- `receipts/guard-behaviour.json`：6/6，6 个浏览器侧 guard 的 60000/20000 行为。
- `receipts/host-binding.json`：10/10，清单/预算/保留边界/Python 预算函数/selector/package/prepare/import-only/输入 hash。
- `receipts/VERIFY-RESULT.json`：顶层离线验证 `passed_offline_only`（纯函数 12/12、fake-clock 14/14、guard 6/6）。
- `receipts/input-hashes-before-after.json`：47 项 r42 输入/包/DTB 在整套测试 start/end 采集，content 不变；明确不是编辑前快照。
- `tests/python_pure_tests.py`（补充套件）复跑 12/12，stdout 在 `receipts/python-pure-tests.stdout.txt`。
- `receipts/process/`：prepare、common import、run_trial import-only 的完整 stdout/stderr。

## 明确未做

没有启动 VM、浏览器服务、guest、QMP、部署、相机、USB、SD 或刷写；没有真正运行 runner/server/八步菜单。离线通过不等于 VM 通过，也不是性能改善或固件绘图超时证明。审批请求仅由协调器在复核后发起。
