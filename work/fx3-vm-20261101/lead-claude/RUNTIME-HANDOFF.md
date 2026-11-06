# 运行链交接书（2026-11-02，Lead: Claude）

本项目是在 QEMU 中运行用户自有 Sony FX3 相机固件的**模拟器兼容开发**：为缺失的相机副芯片服务提供软件设备模型，导出显示画面，并模拟用户按机身按钮操作原厂界面（普通 UI 自动化测试）。

## 你的角色
本 Run 唯一的运行链持有者：只有你在 `work/fx3-vm-20261101/menu-repair-01/runtime/` 下构建候选件、运行 QEMU（`.run.lock` 串行）、更新 `STATE.json` 与 `reports/2026-11-01-fx3-vm-resumed-repair/` 报告。原件只读，不清空废纸篓，不做 git 操作，不改既有 runs/ 与已冻结的 helper 版本（新改动一律新版本号）。

## 先读
1. `runtime/STATE.json`（当前 phase、current/preferred 候选、各模型版本）
2. `reports/2026-11-01-fx3-vm-resumed-repair/` 最新报告：`ap93-empty-slots-first-setup.md`、AP94 报告、`runtime/AP95-IMPLEMENTATION-NOTES.md`
3. `work/fx3-vm-20261101/lead-claude/PLAN.md`（Lead 决策记录）
4. `lead-claude/audits/key-input/README.md` 与 `lead-claude/audits/key-delete-c4/README.md`（按钮码）

## 当前状态
- 基线 AP94-r4（`runs/ap94r4object-37305ab2`）健康：原厂首次设置界面可显示并响应按钮（语言页→隐私说明→手机引导→蓝牙→QR 页）。
- AP95 的"宿主逐步放行按钮"机制已实现并通过宿主测试（控制区 41df00008，12B step/key/hold_ms），尚未生成含删除按钮的候选，也未运行。
- 白名单按钮（Infra 码）：上 0x3、下 0x30、左 0x15、右 0x1af、确定 0x1ac、MENU 0x1ab、删除/C4 0x1f8（down 20B `f801000000000000010000000000000001000000`，up 同字节 status=0）。

## 下一项任务 AP95
生成包含删除按钮的按钮模拟模块与候选（基线 AP94-r4），运行 300 秒，逐步放行：每步发送后读回截图并实际查看，再从白名单选下一个按钮。已知路径：语言页 上→确定（English）→ 隐私页 确定 → 手机引导页 删除按钮（Set on the camera）→ 其余首次设置页按画面提示 → 拍摄待机 → MENU → 下×2/右/确定 浏览菜单。≤30 步；每步记录画面描述与选键理由；遇未知按钮、新的绘制不支持、或进程异常即停。

## 汇报
用 orchestration 的 status 汇报进展（Lead 会回复决策）；只有 Lead 明确要求时才发 worker_done。描述保持中性：设备模型 / 画面导出 / 按钮模拟 / 兼容性。
