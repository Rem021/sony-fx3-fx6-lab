# r40-deepseek-menu-timing

FX3 r38 单次运行的 MENU 延迟离线分解（只读，不启动 VM/QEMU/浏览器）。

- `REPORT.md`：中文结论、时钟域、GPE/key 语义、分段、host 对照、归因与最多 3 条优化建议。
- `results.json`：机器可读完整结果（含 391 条命令、329 对动态调用、38 对 `SendDrawComp`、289 条 OSD 提交、时钟锚点、覆盖/未配对与归因）。
- `data/*.csv`：命令、动态、COMPLETE、OSD 提交、ring 样本表。
- `analyze_menu_timing.py`：纯标准库脚本；`manifest` 生成输入哈希，`analyze` 生成结果与 CSV。
- `input-manifest-before.json` / `input-manifest-after.json`：38/38 输入前后哈希一致（`e4db93f3...`）。
- `SHA256SUMS` / `SHA256SUMS.sha256`：交付哈希及清单自身哈希。

复算：

```sh
cd "$(dirname "$0")"
python3 analyze_menu_timing.py manifest --out input-manifest-before.json
python3 analyze_menu_timing.py analyze --out results.json --data-dir data
python3 analyze_menu_timing.py manifest --out input-manifest-after.json
```

结论边界：r38 仍为 failed；本目录不改变原 20 秒截止、不做 pin/confirm、不把 observation-2 历史截图当作固定快照，也不证明稳定性/全菜单/FX6。
