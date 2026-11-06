# r40 review-revision-1

r40 初稿的独立修订副本，用于处理协调端三项复核意见。原 `r40-deepseek-menu-timing/` 封存文件未覆盖、未移动。

- `REPORT.md`：修订后的中文报告（删除主机 observe+pin 合并建议；不建立 guest↔host 换算；完成点措辞；补 v1 头绑定与 r27 边界）。
- `REVISION-NOTES.md`：三项复核意见逐条处理、v1/v2 头绑定、r27 既有方案、文件变化摘要。
- `REPORT.diff`：原报告到修订报告的 unified diff。
- `results.json`：修订后的机器可读结果（含 `revision`、`cross_domain_differences`、`command_start_times_logged`、`gap_interpretation`、v1 头绑定）。
- `data/*.csv`：命令、动态、COMPLETE、OSD 提交、ring 样本。
- `analyze_menu_timing.py`：纯标准库复算脚本。
- `input-manifest-before.json` / `input-manifest-after.json`：38/38 输入前后哈希一致。
- `SHA256SUMS` / `SHA256SUMS.sha256`：本修订目录交付哈希。

复算：

```sh
cd "$(dirname "$0")"
python3 analyze_menu_timing.py manifest --out input-manifest-before.json
python3 analyze_menu_timing.py analyze --out results.json --data-dir data
python3 analyze_menu_timing.py manifest --out input-manifest-after.json
shasum -a 256 -c SHA256SUMS
```

边界：r38 仍 failed；本修订不改变原 20 秒截止，不自动语义通过，不做 pin/confirm，不重试按键，不启动 VM/QEMU/浏览器，不涉及 FX6。
