# FX3 / FX6 固件菜单本机试用

## 最新成果入口：FX6 固件在 FX3 虚拟机上的 Big6 菜单体验（2026-11-07）

双击 [FX6菜单.command](FX6菜单.command)（或在终端执行 `./FX6菜单.command`），将自动在浏览器打开本机地址 **`http://127.0.0.1:8768/`**：

- **即时体验 Big6 菜单交互**：页面打开即显示已通过 Candidate `255` 实机验证的 `1024×540` RGBA8888 FX6 Big6 HOME 菜单帧（18 次 `GRM_gpermFillrect` + 5 次 `GRM_gpermRectblit`、2560 帧 `0 SEGV`），支持网页 7 键（`MENU` `0x1ab`、`▲ 上` `0x3`、`▼ 下` `0x30`、`◀ 左/右列` `0x15`、`▶ 下一档` `0x1af`、`SET 切换值` `0x1ac`、`REC/C4` `0x1f8`）、点击 6 个 Big6 参数框或使用电脑键盘方向键实时切换 **FPS / Shutter / ISO / ND Filter / Base Look (S-Cinetone / S-Log3) / White Balance / STBY·REC**。
- **QEMU 实机后台会话（可选）**：点击页面右侧 **「启动 FX6-on-FX3 QEMU 实机运行」**，将在后台拉起 FX3 QEMU 虚拟机运行 FX6 固件，通过 GDB 物理内存门（`0x41df00000` `SRM3KYE5` 与 `0x41e000f00` `FX6M`）向客体 `libgrm-fbinit25.c` 注入按键，并通过 QMP `pmemsave 0x41e001000` 实时回读客体 GPE0 显存帧。

技术报告与逆向记录见 [2026-11-07 FX6 UXEngine 初始化与 Big6 菜单渲染报告](../../reports/2026-11-07-fx6-uxengine-init-assist/README.md) 及 [EVIDENCE-255-MENU.md](../../reports/2026-11-07-fx6-uxengine-init-assist/EVIDENCE-255-MENU.md)。

---

## FX3 原厂菜单入口（2026-11-04）

双击 [FX3菜单.command](FX3菜单.command)，打开终端打印的本机网址，再点击网页 **开始本轮模拟器**。端口每轮可能不同。每次按键后看清目标画面，网页提示时点击 **我已看清当前完整画面，继续**。结束时点击 **结束试用** 或在本轮终端按 **Ctrl-C**，等待回执输出。

新版默认 **4096 次按键／60 分钟**，已部署；已完成一轮真实浏览器 **32 键、约 11 分 14 秒**导航及独立的 Finder 启动／Ctrl-C 退出验收。

[完整使用说明](使用说明.md) · [新版验收记录](新版验收记录.md)

## 保留的 TRY2 入口与开发状态

[FX3菜单TRY2.command](FX3菜单TRY2.command) 保留原样，仍有 **30 键／15 分钟**限制。该限制来自旧宿主参数，不是 FX3 硬件限制。历史试用曾出现持续导航后的原生省电关机；增加新版上限不等于解决省电行为。旧入口与记录见 [TRY2 使用说明](TRY2-使用说明.md)，不作为新版启动入口。

## 旧 TRY1 入口

这是在 QEMU 中运行的 FX3 原厂菜单，复用已验证的 AP101-r4 模拟器。需要本机已挂载 KAFU2T 外盘，并使用现有 Python 3。每次启动都会从固定保存文件冷启动。

在终端运行，保持终端开启：

```sh
python3 -B /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/run_trial.py
```

打开 **[http://127.0.0.1:8765](http://127.0.0.1:8765)**。等待“固件已就绪”，再按 **MENU** 打开菜单；冷启动及首次打开菜单可能需要几分钟，请等画面更新再继续操作。网页约每 0.4 秒查看新帧，只有固件提交了新画面才更新。画面高亮可能不可见，建议每次只按一下并观察标题、页码和项目文字。

| 网页按钮 | 机身按钮模拟码 |
|---|---|
| 上 / 下 | `0x3` / `0x30` |
| 左 / 右 | `0x15` / `0x1af` |
| 确定 | `0x1ac` |
| MENU | `0x1ab` |
| 删除 / C4 | `0x1f8` |

每次按键持续 100ms，每轮最多 **30 次**。点击网页的 **“结束试用”**，或在启动终端按 **Ctrl-C**。等待终端显示回执及退出检查结果后即可关闭；关闭网页本身不会退出模拟器。默认最长 **60 分钟**，到时自动收尾。端口冲突时可用 `--port 8766`，并打开终端打印的新网址；也可用 `--max-minutes 10` 缩短上限。已有运行占用锁时会直接拒绝启动，避免互相干扰。

当前限制：**高亮可能不可见、部分底色缺失和文字叠印、无实时取景、语言修改暂未确认落盘、画面为近似混合**。下一轮仍从固定保存文件启动；画面和菜单试用不代表拍摄、录像或实体相机硬件已模拟完成。出现原厂断言、异常或当前模型不支持的请求时，网页会提示并停止接收按钮，随后退出和保存证据。

网页仅监听本机 `127.0.0.1`。原始固件和已完成的运行目录保持只读；每轮日志、按钮记录、提交帧证据和退出回执分别保存到新建的 `work/fx3-vm-20261101/menu-repair-01/runtime/runs/try1-*`。退出会核对原 API 16 字节恢复、QEMU 退出码、进程回收、输入 SHA 和锁释放。

技术参考：[QEMU 监视器](https://www.qemu.org/docs/master/system/monitor.html)、[Python 本地 HTTP 服务接口](https://docs.python.org/3/library/http.server.html)。这些接口仅用于宿主控制与观察，设备模型沿用冻结基线。

验证记录：[实际网页菜单截图与退出回执](../../reports/2026-11-01-fx3-vm-resumed-repair/try1-local-ui-trial.md)。已完成待机→MENU→菜单→网页结束，以及独立一轮Ctrl-C收尾；自测实例均已退出。

---

## 离线自动化单元测试（`tests/test_vm_trial.py`）

无需启动任何 QEMU 进程，也无需自备专有固件二进制，即可离线验证编译态 C 扫描线打包器（`fx6_pack_scanlines` 与纯 Python 参考实现逐位一致性）、RGBA PNG 编码与 IEEE CRC-32/IDAT 解压、SVR4 `cpio newc`（`070701`）确定性构建与 `mode/uid/gid` 保持、`src/fx6_live_guest.c` 内存/符号缓存/`DISP` 边界回归检查，以及 `outputs/fx3-vm` 补丁与重定位溯源（共 **16 项** 测试，已接入顶层 `make test`）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py" -v
```
