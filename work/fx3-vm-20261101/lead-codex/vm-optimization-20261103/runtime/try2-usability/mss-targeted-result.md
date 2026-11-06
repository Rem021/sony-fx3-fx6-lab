# FX3 原生 MSS 定向观察回执（2026-11-03）

**结果：局部证实，整体失败。** 本轮记录到原 `sequence_mss_reload::run` 在启动时两次进入原消息构造器；两次 MENU 开/关期间未再次进入这条序列。其后原生电源通知和关机页出现，健康门按预期早停。尚未观测 UPM 实际消费及计时器复位，不据此修补或提升 TRY2 入口。

## 固定输入与改动

- 原 `appFw.so` SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`；原 `upm.ko` SHA256 `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e`，均未修改。
- 基础 power-observe candidate SHA256 `d53363f076f5d0129c68e7489d407b0baab300bec62f487decf96a73e29d90a6`。新诊断 candidate `vmopt-20261103-try2-mss-safe-v2/candidate.json` SHA256 `6dd9fee185c4ea1a8859a70cca19a3af7f5c6d8d0280f849fc60afd21eba30b4`，CPIO 只替换 `simulation/fx3-media-observe-v3-uipc.so` 一项；init 脚本、seed 不变，DTB 只改 initrd end，详见 `build-receipt.json` 和 `cpio-audit.json`。未运行先前 v6 BL-hook 候选。
- 被动 v7 源 SHA256 `c5de178004eac532832e0f166eecee8ebf250becae1c8099f849b5047d26e653`，so SHA256 `3c5766284c0b4d8214bf7a031a74dc044703c58363d338129b2a1b887d3e3e35`，只在原 app 的 4 个非 PC 相对普通指令挂观察点，原指令字逐项核对；256 项预分配 ring，100ms 由采样线程输出，不在原回调中写日志，溢出为失败门。源码差异 `mss-safe-observer.diff` SHA256 `87c85942d6d8de872b470052b7545a0df11e6bd4ee6755962937df13813b9ead`。
- runner `run_trial_v12_mss_safe.py` SHA256 `b16e1e4e807fc0e94c3adb2ac5036715830b5089895a0eeb3fa68d1cc83d3aed`，保留原 100ms、一次 pending、原帧/健康/20s guest ack/API16 规则；差异 `mss-safe-runner.diff` SHA256 `5c2dae63f76996d9b9c2906a73422721c6870aa6eaa93da192c763bb1b06494d`。新增状态文件与唯一 run label，不覆盖旧轮。`py_compile` 通过；**这不替代运行结果**。

## 原生路径与实际同钟时间线

重现数据为 `mss-targeted-run-evidence.json`，生成器 `src/analyze_mss_targeted_run.py`。所有下列 ns 都是 guest monotonic，未与宿主或 kernel printk 时间相减。

| guest ns | 观察 | 限定含义 |
|---:|---|---|
| 44,426,468,000 / 44,462,972,000 | 原 `appFw.so` `sequence_mss_reload::run` VA `0x2d35168`，TID442，两次 | 真实原函数入口；属于启动阶段。 |
| 44,427,374,992 / 44,463,916,992 | 原 builder VA `0x2eaf294`，QID `0x80924220`、tag `0x00920204`、word1/source `0x81cf6198`、word2/3=0 | 原调用参数，观察点属注入被动 adapter，参数来自原函数。 |
| 44,428,864,000 / 44,468,196,992 | 原同步发送调用返回后的 VA `0x2eaf308`，x0=0 | 发送函数返回 0；**不是** UPM consume、timer reload 或效果证明。 |
| 81,945,418,000 / 82,054,992,000 | 第1键 MENU down/up；原接收各一次、done一次；图像实际显示英文 Setup | UI 收键及图像门通过；未观测新增上述 MSS 序列。 |
| 131,663,584,992 / 131,782,332,000 | 第2键 MENU down/up；原接收各一次、done一次；画面回待机 | 同上，未改变设置。 |
| 431,981,032,992 / 431,983,550,992 | 原 app 两处电源路径上的被动通知点，同一 TID381、对象 `0x7f94001ad0`，raw12 `520000001100000002000000` | 原表 factor `0x11` 对应 `OFF_BY_APO1`；随后原关机页与 power-off queue 消息，健康门停止。 |

第2键 up 到首个电源通知为 **300.198700992 guest 秒**；最后启动 MSS 点到该通知为 **387.512836 guest 秒**。这与读到的 UI `Power Save Start Time = 5 Min` 相近，提示应继续核验活动计时归属；它本身不证明 MENU 触发 MSS，也不证明定时器由该条消息复位。上一 27 键轮的最后 up 到通知仅 11.870847008 guest 秒，而第13键 LEFT up 到通知约 302.160079008 秒；两轮的关系提示输入种类/状态可能影响复位条件，仍需原 UPM 消费与其他活动路径的运行证据。

原 `appFw.so` 反汇编：wrapper `0x2eb4f24..0x2eb4f5c` 形成参数；builder `0x2eaf2f4..0x2eaf300` 在分配的 16B 中依次 `stp w25,w24`、`stp w23,w22`。因此仅**静态重构**本次参数若按该分支执行时的消息字节为 `040292009861cf810000000000000000`。v7 的 after-send 堆指针观察为 `readable=0`，**没有实际抓到 raw16**；不得把该重构当线上的原始 16B。原 UPM 队列 consume、reload 分支/状态门、内核定时器变化仍是 unknown。旧 256-signature UNIQUE 日志不作为缺失判断；本轮 v7 完整 256 ring 仅用 8 条且无 overflow，但只覆盖所列原 app 点。

只读原 `upm.ko` 指令在 `.text+0xd58` 注册该队列，`.text+0x2180` 起的分派识别 `0x00920204` 并有条件进入 `.text+0x1608` 的 reload 实现；这是静态合同，**本轮没有内核分派/消费运行态 hook**。原 app 对应三段指令的固定摘录见 `mss-original-app-disassembly.txt`（SHA256 `01c4eb1bf5da2f63df6ba53b5475c236f56db771d24081777ccccc4518416a32`）。

## 图像、退出与未通过项

- 唯一运行 `runs/try2mssinternal-a1d8f68a/`：最长1200秒、最多32键，实际 **2** 键；每键提交前用图像工具查看 `trial-frame.png`，理由与 SHA 写在 `internal-observe-01/02-decision.md`，随后查看 `trial-step-01-key-1ab.png`（Setup 过渡）和当前完整英文橙焦点 Setup 画面，再提交第2键；第2键 PNG 回到待机。第2键首次尝试引用第1键旧图时，提交脚本判 stale 并在写请求前拒绝；重新看新图后才发键。无网页源，不能称浏览器验收。
- receipt：宿主持续 `437.766416` 秒，`stop_cause=health_failure`，原因是原生 power-off 观察；QEMU PID86695 exit0/reaped/absent，guest 20秒 ack + 原 API16 字节恢复通过，输入 SHA 未变，双锁释放并实测 free。`health_pass=false`、`render_pass=false`，本轮不可称成功；不存在无人操作 guest。
- **下一阻塞**：需在不改原固件/超时/电源策略的条件下，核对不同键/状态到原 UPM 活动复位的来源与实际 consume/计时器更新；只读捕捉消息必须在原 buffer 释放前取得，或保留 unknown。现在无足以支持某个适配修复的首个因果异常，故未制成行为修复候选，也未做第二轮盲跑。浏览器/Finder、长会话、31/32 等较早开放门仍未由本轮补齐。
