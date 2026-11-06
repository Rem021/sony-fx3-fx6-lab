# r40 review-revision-1｜复核意见处理与变化摘要

本目录是 r40 初稿的**独立修订副本**。原 `r40-deepseek-menu-timing/` 下的封存文件未覆盖、未移动；修订只新增本子目录。原 r40 的 `SHA256SUMS` 仍可验证（原 `SHA256SUMS` 文件 SHA256 为 `c16edd8920f742b4bc5980f9f99a4f132474614f1dcbc5516b43d3749799660a`），其中关键文件原哈希：

| 原封存文件 | SHA256 |
|---|---|
| `REPORT.md` | `37bde41762ed15bd2c8bce365444d48415e4b1ecd9e831be130980bd9602b797` |
| `results.json` | `33a6714978f33cf2ee5abb4df72d5b000fb38bb627e28bc8a0f4e582fb081df8` |
| `analyze_menu_timing.py` | `7184d9bf85cd25b37e3e8708cb3d7702d2978e0edabfab42ecf6f5ccc62629a5` |
| `input-manifest-before.json` | `541f7f2eca8bc328c8f06427efc3006718745711b1aae3188c84b317e692ea3f` |

本修订的输入仍是同一批 38 项，输入前后哈希一致（`manifest_sha256 = e4db93f34d05c6c76740507ccb8b926eb8a6c5f6ec7242f15c16f4bd5b39b9f9`）；未复制 CPIO/serial，未启动 VM/QEMU/浏览器，未改任何输入或原封存文件。

## 1. 三项复核意见与对应修改

| 复核意见 | 修订处理 | 具体落点 |
|---|---|---|
| 1）建议“第二观察与 pin 合并/预绑定 pin”破坏“观察图真实返回→独立视觉决定→pin→固定 PNG 再审→独立 confirm”边界 | **删除该可执行建议**，改为“合同边界（不列为建议、不实施）”，明确不承诺省 11.53 s；建议数从 3 条改为 **2 条**，不凑满；并引用 r27 短模板“每次只发起一个动作、不自动 pin/confirm” | `REPORT.md` 第 8 节；`results.json.revision.host_merge_suggestion="removed (outside contract)"` |
| 2）“0.0989 s 差值跨度说明 ring 读回延迟稳定 0.1 s”不成立；恒定 H-G 偏移/斜率 1 未验证；[下界,上界] 只是条件区间，不是校准 | 重写时钟段：只记录逐帧差值 `d_i`；只描述差值变化，不推断绝对读回延迟；明确“恒定偏移/斜率 1/因果锚点”是条件假设，区间未校准；**不建立 guest↔host 换算**，主要结论只用同域量；删除所有 host_est 字段与按偏移中点的 host 相对时间 | `REPORT.md` 第 2 节 H 行、锚点 1–3；`results.json.clock_domains.domains[H].cross_domain_differences`（`calibration_status="not calibrated; conditional interval only"`、`conversion_used_for_conclusions=false`）；`menu` 中不再有 `*_host_est` |
| 3）表 5.2“期间无 GPE 命令/无新 GPE 命令”不成立：命令日志在完成侧，不能排除执行中的长命令 | 全部改为“期间没有记录到 GPE 命令完成（不排除已在执行的长命令）”；标题改为“完成点分段（非 CPU/因果）”；加入“七段只是完成点间隔，不称 CPU 时间/因果归因”的限定 | `REPORT.md` 第 5.2 节标题/三行空档说明/表后说明；`results.json.coverage.command_start_times_logged=false`、`gap_interpretation`；`attribution.unknown.gap_semantics` |

## 2. 日志生产源码版本（按复核提示定向确认）

复核提示 `fx3-complete104-observe-v2-profile104.h` 与 `fx3-complete104-observe-v1.h` 均存在。本修订不按文件名猜，改用实际 run 的 CPIO 成员内容确认：

- 实际成员 `simulation/fx3-gpe-observe-v7.so`（276984 B，SHA256 `30667f76...`）内嵌源码路径字符串 `menu-repair-01/runtime/helpers/fx3-complete104-observe-v1.h`；
- 该成员中 **没有** `fx3-complete104-observe-v2-profile104.h`，也没有 `P104`/`pr104`/`profile104` 标记；
- 因此 r38 实际绑定的是 **v1 头**；v2-profile104 文件存在但未绑定到该成员。v1/v2 的 `CMD_RETURN`/`COMPLETE_ENTER` 格式字符串相同，但 v2 的 `pr104_start/pr104_end` profiling 标记在实际成员中不存在，进一步排除 v2。

`results.json.clock_domains.producer_binding.member_binding.members[0].header_binding` 保存了 `v1_header_path_present_in_binary=true`、`v2_header_path_present_in_binary=false`、`v2_profile_markers_present=false`、`bound_header_from_binary_path="fx3-complete104-observe-v1.h"`。

## 3. r27 既有方案（不再重复建议）

已只读定位并核对：

- `passive-timing-delivery/r27-operator-latency-preparation/REPORT.md`：短模板只减少机械交互，不消除模型/调度间隔；r26b 两次返回至下一动作入口约 9.709/9.032 s，成功 pin POST 尾段约 0.024–0.080 s，不能把含前置等待的完整 capture 再加算；12.773 s 只是单次历史回放，不是未来下界。
- `passive-timing-delivery/r27-operator-latency-preparation/SHORT-TEMPLATE.md`：预载持有单步函数、每次只发一个动作、真实图片返回并看过才决定下一步，不自动 pin/confirm；r37/r38 已使用预载与 +5 s 首观察。

因此本修订**不再**把“预载/短模板/5 秒首观察”当新增建议；仅保留两条 guest 侧建议（起始侧标记、三次 flush 与 89 次重复提交核查）。未重做 r27 回放，未扩展历史。

## 4. 交付变化摘要

| 文件 | 变化 |
|---|---|
| `REPORT.md` | 修订三项；删除主机合并建议；不建立 guest↔host 换算；完成点措辞；补 v1 头绑定与 r27 边界 |
| `results.json` | schema 不变但字段修订：新增 `revision`；`clock_domains.domains[H].cross_domain_differences` 取代 `bridge_to_G`；删除 `menu.*_host_est`；新增 `coverage.command_start_times_logged`、`gap_interpretation`；新增 `host.ring_reads_host_domain`（host 同域）；新增头绑定 |
| `analyze_menu_timing.py` | 同步上述计算与字段；不再做 guest_to_host 转换；新增头绑定/覆盖字段 |
| `input-manifest-before/after.json` | 重新生成，38/38 与初稿相同 |
| `data/*.csv` | 重算，数值与初稿同源；字段同初稿（命令/动态/COMPLETE/OSD/ring） |
| `REPORT.diff` | 原 `REPORT.md` → 本修订的 unified diff |
| `SHA256SUMS` / `SHA256SUMS.sha256` | 本修订目录交付哈希 |

**未改变**：r38 仍 failed；原 20 秒截止；不自动语义通过；不 pin/confirm；不重试按键；不启动 VM/QEMU/浏览器；不涉及 FX6；不修改原封存候选/输入。

## 5. 复核命令

```sh
cd "$(dirname "$0")"
python3 analyze_menu_timing.py manifest --out input-manifest-before.json
python3 analyze_menu_timing.py analyze --out results.json --data-dir data
python3 analyze_menu_timing.py manifest --out input-manifest-after.json
python3 - <<'EOF'
import json
b=json.load(open('input-manifest-before.json')); a=json.load(open('input-manifest-after.json'))
assert b['groups']==a['groups']
d=json.load(open('results.json'))
print(d['revision']['id'], d['menu']['key_up_to_full_menu_ns'], d['coverage']['command_start_times_logged'])
print(d['clock_domains']['domains'][2]['cross_domain_differences']['calibration_status'])
EOF
shasum -a 256 -c SHA256SUMS
```
