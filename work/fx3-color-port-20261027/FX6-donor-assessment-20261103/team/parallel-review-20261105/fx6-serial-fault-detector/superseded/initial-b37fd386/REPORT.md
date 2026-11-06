# FX6 serial fault detector — offline fix

- Task：`task_17c0a14d5ec7`
- Dispatch：`ctx_ed697c8d3cd6`
- Status：**OFFLINE_DETECTOR_FIXED; NOT RUN; NOT BOOT/MENU ACCEPTANCE**
- 仅本目录；旧回执、源、固件、CPIO、Backup、helper、平台、r6 观察器、协调账本均未改。
- 无 VM/guest/QMP/browser/server/live-process；无 camera/USB/SD。UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 已核。
- 输入 6 项前后 hash 不变（`receipts/input-compare.json`）。

## 缺陷复现

`fixed_runner.py:serial_observation` 的旧 detector 只匹配 `Kernel panic/Oops:/Unable.../Internal error:/SError`，没有 `assert at`：

- 66ed serial：旧 `fault_markers=[]`，但实际有 **4** 条 `assert at`（model_api 3147/3176、infra_wrapper 1075 两次）；旧 run-receipt 同为 `[]`。
- 84db serial：旧 detector 只识别 `Oops:/Internal error:`，漏掉 **2** 条 assert。
- 实际复现用 minimal `fixed_platform` stub 导入原 `fixed_runner.serial_observation`，见 `receipts/old-detector-reproducer.json`；未改旧源。

## 新 detector

`detect_serial_faults.py`，仅标准库：

```sh
python3 detect_serial_faults.py --serial <serial.log> --output <new.json>
```

- 行号基于 `bytes.splitlines(keepends=True)` 的逻辑行（与既有审计 66ed 11688/11738/14502/14734、84db 11597/11644/16408 对齐）；输出原始行。
- `assert at source:line` → `type=assert`、`classification=assert_reported_nonfatal`、`fatal=false`；记录 source/source_line/function（下一条 `function:`）。新输出 `fault_markers` **包含 assert+fatal**，另有 `fatal_fault_markers` 只含致命项，避免旧 `fault_markers=[]` 的兼容盲区。
- 已知 fatal：`Internal error: Oops:`、`Oops:`、`Kernel panic`、`Unable to handle kernel`、`SError Interrupt`、`BUG: unable/NULL pointer`；`type=fatal_fault`、`fatal=true`。普通文本/命令行 `panic=-1` 不匹配。
- 输入缺失/空/不可读/目录/截断（无末尾换行）分别 `unknown_*`/`incomplete_truncated`，`complete=false`、exit 2；**不默认为通过**。
- `screen_markers` 只报告 marker 计数；无 marker 不推出零像素（`visible_pixels_zero_claimed=false`）；`boot_menu_passed=false`、`functional_success=false`。无 fault 也不等于 boot 成功。

退出码：2 unknown/incomplete（即使包含 marker）；1 有 assert/fatal；0 完整且无 marker（仍非 boot/menu 证明）。

## 当前日志结果

| log | status | asserts | fatal | screen markers |
|---|---|---:|---:|---|
| 66ed | `incomplete_truncated`（源文件末尾无换行） | 4 | 0 | 0（`fault_markers` 4） |
| 84db | `incomplete_truncated` | 2 | 1 (`Internal error: Oops: 96000005`) | 0（`fault_markers` 3） |

66ed 修复输出：`receipts/66ed-detected.json`；84db：`receipts/84db-detected.json`。两者都保留 `incomplete`，不冒充完整运行。

## 测试

`tests/test_detector.py` 6/6：

- 66ed 四条 assert 的精确 line/raw/source/source_line，fatal=false；
- 84db 两条 assert + 一条 Oops fatal 区分；
- 旧 detector `fault_markers=[]` 复现；
- 空/缺失/目录不可读/截断 -> unknown/incomplete；
- 普通说明文本/`panic=-1` 不误报，精确 `assert at` 能命中；
- screen marker 出现只报告 presence，不声明像素/菜单。

## 边界

本任务只改善日志故障可见性与审计输出；未运行 VM，未改运行器，不证明 FX6 boot、screen、menu 或备份读链通过。旧源与 r6 观察器保持封存。

## 交付

`detect_serial_faults.py`、`REPORT.md`、`RESULT.json`、`SHA256SUMS`、`receipts/`（新旧检测/Oops/输入封存）、`tests/`、`input_seal.py`。
