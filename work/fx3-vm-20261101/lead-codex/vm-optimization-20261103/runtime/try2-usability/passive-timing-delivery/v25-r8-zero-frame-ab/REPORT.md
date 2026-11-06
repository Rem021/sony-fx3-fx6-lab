# FX3 零帧 A/B 离线准备（r8 观察器 + r9 共用宿主）

2026-11-04。**仅完成宿主准备和离线验证；没有启动 QEMU，也没有得到 A/B 运行结论。** 外盘 UUID 已核验为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。原 r6/r7、guest、种子、DTB、kernel、默认入口与历史 run 均未修改。

## 唯一变量与固定源

两臂都使用同一目录 `../v25-r9-ab-host/run_trial_v25_diag_r3.py`，同一 QEMU/CPU/RAM/GIC/DTB/kernel/English Backup 和 20 分钟宿主预算；A 用 runner 默认原 r3 CPIO，B 仅增加 `--review-procdiag-r4e` 选择原 r4e CPIO。两个原 CPIO 均不重打包。`--max-steps 4096` 是既有 host 输入容量参数，本合同**实际零键**；不能将 4096 解读为本轮允许按键。

| 固定对象 | SHA-256 |
| --- | --- |
| r9 共用 runner（r6 加 r7 时钟补丁） | `902869ee48c1c80dbe770316d0515ac429a5679beb1af73971dfabf7be041126` |
| r9 异常时钟 helper | `5f133dd0c8f6d17b19cab87616b1efe725445829d75447ac0de71ceb99a083dc` |
| r9 `SOURCE-FREEZE.json` | `48b0b0abfd2f6ac633c6ac74f5c6ff912ece0290e938206b09c42163a77a5c36` |
| 原 r6 runner / r7 精确补丁 | `2101edb5eb9c7789faa5c753e206fe315df87307df0695d290a95e718fb4846c` / `66b48b09a53f2135bb0aa9f47b0fd1b2a0116b171d74516102b0d13f5384f532` |
| A r3 manifest / 原 CPIO | `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518` / `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83` |
| B r4e manifest / 原 CPIO | `ced1644fbcecc542c3d90f16be2a461876e7f3af92ff639c793742f090136d22` / `439f9089d3e36b6a5ee0d3f16a170a608761f315a4a2169d1d859cb0f66952db` |

r9 只复制了 r6 的 19 个运行时宿主 `.py` 与 r7 的一个 helper，没有镜像、Backup 或项目克隆。补丁使用 `patch --batch --fuzz=0 -p1` dry-run 和实际应用；结果 runner/helper 哈希与 r7 审核值相同。r9 与 r6 位于同一目录深度，runner 的 `parents[6]` 与 `parents[2]` 解析不变；r9 首次写入自己的 `STATE-v25-r3.json`，不会使用 r6 历史状态。r7 的 12 项故障测试回执与既有独立审阅可复用；本轮只测集成导入、`--help`、预检和 A/B 工具。

## 顺序执行合同（待协调端审核授权；现在不运行）

先核 UUID、无现存 QEMU/runner、两把运行锁空闲、r9 全源冻结 SHA、两臂 manifest/CPIO SHA；`ab_preflight.py` 对这些条件会失败即停。还须先确认外盘/宿主存储稳定。两臂**顺序**执行，A 完整 API16/quit/reap/锁回执结束且外盘窗口审查后才可开始 B；任一故障或掉盘即停止，不自动重试。

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac
PYTHONDONTWRITEBYTECODE=1 python3 work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/v25-r8-zero-frame-ab/ab_preflight.py
cd work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/v25-r9-ab-host
# A：只在获得新 VM 运行授权后
PYTHONDONTWRITEBYTECODE=1 python3 run_trial_v25_diag_r3.py --max-minutes 20 --max-steps 4096 --port 0
# B：仅在 A 完整退出并再次通过 preflight 后，在同一 r9 目录
PYTHONDONTWRITEBYTECODE=1 python3 run_trial_v25_diag_r3.py --review-procdiag-r4e --max-minutes 20 --max-steps 4096 --port 0
```

每一臂需在独立真实浏览器标签打开其随机 loopback URL，点击一次 Start；不发任何键。取该轮唯一 `runs/<label>` 路径（不能传旧 run），另开终端执行相应观察命令：

```sh
python3 /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/v25-r8-zero-frame-ab/ab_observer.py --arm A --run '<A_RUN>' --send-stop
python3 /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/v25-r8-zero-frame-ab/ab_observer.py --arm B --run '<B_RUN>' --send-stop
```

这两条是**分别执行**，绝不并行。观察器不接 QMP、不启动 guest、不写 guest；它只读 loopback `/api/status` 和串口追加字节。`--send-stop` 明确调用现有网页 End，并校验监听 PID、浏览器启动 ID、页面 token、run、候选及 CPIO 身份；End HTTP 回应只是停止请求，不是 API16 或退出通过。若网页未完成 Start、身份变化或页面不可用，停为 inconclusive 并人工按既有安全收尾处理。

## 观察与判定

观察器以 guest `clock_id=1 ns` 中 `screen_id=0 presenter_factory_return` 为起点，记录首次 `OSD102_COMMIT op=0x1003` 和最新 KEY96 poll。若宿主状态的 `ready && render_valid && frame` 首先成立，立即结束观察，分类 `first_host_verified_frame`。若屏幕创建后同一 guest 时钟走过 60 秒仍无该宿主帧，分别记录“已有 commit 但像素未验证”或“未见 commit/验证帧”；**没有串口 poll 推进就不能伪称满 60 guest 秒**。日志采用最大 8 MiB/次的增量读取，保留有限行尾，不每秒重读全文件。

宿主独立 monotonic 观察上限 960 秒，runner 总计 1200 秒，给原有 API16/QMP 清理至少 240 秒；status 的剩余时间到 240 秒也触发结束。截止时若仍有未处理的串口 backlog，直接归 inconclusive，不用部分日志断言 startup 未完成。未到 screen0 单列 `startup_incomplete`；已经到 screen0 却没有足够 guest 时间则 `observation_budget_exhausted`，结论 inconclusive。零键合同被破坏、status/serial 不可读、原生错误、掉盘、异常终态均单列且早停。即使首帧已出现，后续 API16 ACK/原字、quit、进程 reap、PID absent、输入 hash、两锁和网页 final ACK 仍各自以 `receipt.json` 等原始回执核验；不把首帧抹掉，也不把它当完整 lifecycle 通过。

A 的 procdiag **按候选不具备**，记 `not_available_by_candidate`；B 的 procdiag 仅在原有 pending-key 诊断路径条件满足时可能可用。两臂都必须走同一 runner 的原生 API16 恢复和健康门，缺 helper 不可跳过或称为绘图差异。`restore_api103_v2.py` 依赖独立 F100FILE identity，不依赖 r4e `/tmp/fx3-proc97-observer.identity`。

比较工具命令：

```sh
python3 /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/v25-r8-zero-frame-ab/ab_compare.py --a '<A_RUN>' --b '<B_RUN>'
```

它要求 `inputs_unchanged is True`、零实际键、receipt 与观察的 run/arm/候选/CPIO 身份匹配；否则 inconclusive。`paired_observation_mode_eligible` 只说明两轮观察分类可并列，`paired_observation_comparable` **固定 false**，直到协调端另外核验两段真实 USB/APFS 存储窗口；任何掉盘轮都不能进入因果对照。API16/进程/锁分别展示，不借此替代绘图判断。这样只能检验 r3/r4e 在相同宿主条件下的启动关联，不能直接证明新增三行 procdiag 的因果作用。

## 离线验证与仍缺的门

`ab_preflight.py` 实测 UUID、双锁 free、无 QEMU/runner、r9 的 20 个 `.py` 冻结 SHA 及 A/B 原候选和 CPIO SHA 通过。r9 runner `--help` 导入通过；`test_ab_observer.py` 通过 10 个状态分支、3 份历史串口的整读/增量一致性和真实本地 HTTP token/End fixture；`test_ab_compare.py` 通过缺失/变化输入、run、arm、候选、CPIO 不匹配与 storage 未验 gate。均为**宿主离线**证据，未验真实 VM 首帧、浏览器 Start/End、API16、进程退出、锁释放与存储稳定性。
