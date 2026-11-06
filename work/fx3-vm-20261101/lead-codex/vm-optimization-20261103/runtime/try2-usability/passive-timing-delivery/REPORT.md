# FX3 v21 被动同钟采样与宿主有限等待回执

2026-11-03。**交付独立候选并完成一次有界 FX3 内部运行，尚未交付默认网页入口。** 本轮三键 MENU、LEFT、DOWN 均为实际看图后单次提交；每键原生 down/up/done 齐全，完整 Setup 菜单及两次焦点移动已由 PNG 实看。QEMU 正常退出、API16 原字节经 guest ack 恢复、输入原件哈希不变、双锁释放。软件 `health_pass=true` 只覆盖本轮，浏览器与 guest 联动、31/32 键、长期稳定性仍未验证。

## 冻结源码和构建边界

固定 v19 runner SHA `761a6edf…` 的前写关机复核保留在 [v21 runner](run_trial_v21_final_timing.py)；原先 v20 误继承旧 v3 网页协议的问题已在独立 v21 修复，v20 历史文件保留。[web-v5-to-v21.diff](web-v5-to-v21.diff) 只增加 `visual_state`、`input_received`、`visual_change_observed` 三个状态字段与一句提示；v5 的 8 秒 fetch/body/图片解码期限、丢按键 ACK 后不重发且锁住七键、最终结果先显示再确认、30 秒最终确认窗口不变。[host-v19-to-v21.diff](host-v19-to-v21.diff) 与 [host-v20-to-v21.diff](host-v20-to-v21.diff) 分别给出全部宿主变化及 v20 回退修复。

| 冻结件 | SHA256 |
| --- | --- |
| `run_trial_v21_final_timing.py` | `ab24b979453791f64df3a4a2dab310f47fac7af2e699e52e5167709d8d720a47` |
| `trial_web_v21_final_timing.py` | `b2dc6b3a61e884c4e2ace56651eafb6e75455e693b02fb1082884fb69816d804` |
| `pending_visual_v20.py` | `e26aced25589fb10e509cbacb028b8cae7d25d71286752a5d57964efa6205fc3` |
| [candidate.json](vmopt-20261103-try2-passive-timing-v4/candidate.json) | `90adc5fda97a4b26293e4763da1ed3d5eec22eaf2f0115292c1b720c5049e9aa` |
| `guest.cpio` / `guest.dtb` | `e0f05f36e7da388d452508ba0d2cc85c2ae43e1884757632ef752b807849fd76` / `ffcc274affaefd49186c1bfd1f227485dbf6703985add3610d1b5ab4f6db5fd8` |

[构建器](build_candidate.py)只从 SHA 固定的 MSSv3 FX3 候选派生，将 RM/AP/OSD 三份已编译的被动时钟 SO 替换进新 CPIO；[逐成员回执](vmopt-20261103-try2-passive-timing-v4/build-receipt.json)证明 1140 个成员仅三份载荷改变，其余载荷、顺序和 mode 不变，DTB 仅 `linux,initrd-end` 改变。[CPIO audit](vmopt-20261103-try2-passive-timing-v4/cpio-audit.json)的 20 个原基线 ELF 全保持，父目录顺序通过。原 FX3 kernel、QEMU/CPU/RAM/GIC/机型与 English generation4 Backup 种子未改，固定 FX6 基线未触碰；三份源码与 SO 的原/新 SHA、原字 guard 在此前 `mss-all-key-contrast/passive-timing-next` 的 `source-receipt.json`、`build-receipt.json` 和 `PASSIVE-TIMING-PLAN.md`，本次 [冻结回执](V21-FREEZE.json)固定实际文件。

RM 接收 wrapper 在每次 key queue `0x807a0020` 的 `fn` 调用前取 `wait_enter_ns`，即使当时 `key_step=0`；分别记录进入/返回 step。调用前恢复原 errno，`fn` 返回立即保存返回值和原生 errno，随后先取 `wait_return_ns` 再执行 `nz/ng/dprintf`，最后恢复原生 errno。原接收函数返回值不变；`clock_id=1` 为 guest `CLOCK_MONOTONIC`。11 个纯宿主状态/源码顺序 fixture、15 个 Node 浏览器脚本 fixture、6 个真实 loopback HTTP 断言、3 个启动早退回执用精确 v21 源通过；这些均不是 guest 通过。三轮 Orca 真实浏览器历史画面 fixture：正常 1 个 key/最终 ACK；9 秒图片 body 故障在 **8.410 秒**重新取图且 0 个 key；丢已接受 key 的 ACK 后仅 1 个 key，七键禁用而结束可用，最终 ACK 有效。证据见 [浏览器回执](v21-browser-verified.json)及各轮截图；所有 fixture 服务线程退出，原用户 8765 标签未碰。

## 唯一 FX3 运行

[run](../runs/try2passivetiming-internal-v21-2383af57) 实际命令为 `--internal-hoststep --max-minutes 15 --max-steps 4096 --port 0`，内部人工门另限 **12** 键且预留 240 秒清理；本轮只用了 3 键、376.623 host 秒。启动前 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、两锁 free、无其他 QEMU；运行由一个 runner 持两锁。第 1 个已看图请求因闪动造成 `stale_no_guest_write`，没有消耗键；重新实际查看新 PNG 后提出新请求，才发送 MENU。未自动重发，也未预排后续键。

| 键 | 发键前真实 PNG 和理由 | 事后亲看/证据 |
| --- | --- | --- |
| 1 MENU | [待机](../runs/try2passivetiming-internal-v21-2383af57/internal-observe-01.png) SHA `e0140ea1…`，前一全图 SHA `2914275c…`；打开原生菜单，不改设置 | `trial-step-01` 的 `2914275c…` 仍是 **NO CARD 闪动待机帧**，不能当菜单；ring 首次已确认完整菜单 SHA `60e9accc…` 为 seq1999，随后 [人工固定菜单图](../runs/try2passivetiming-internal-v21-2383af57/internal-observe-02.png)见 Setup 45/59、English 与橙色焦点。 |
| 2 LEFT | 上述完整菜单图，焦点在右侧 Area/Date/Time Setting；只移到左类别 | 中间 `trial-step-02` 为部分切换；完整类别图 SHA `15cb5b95…` 先在 seq2953，随后 [人工固定](../runs/try2passivetiming-internal-v21-2383af57/internal-observe-03.png)见左侧 Area/Date 橙色焦点。 |
| 3 DOWN | 上述左类别图；只移动一类 | [人工固定](../runs/try2passivetiming-internal-v21-2383af57/internal-after-03.png)见 Setup 46/59，焦点落在 Reset/Save Settings；**未进入设置**。完整图 SHA `3d071654…` 首见 seq3648。 |

原生 receive 的下键/抬键各三条均 `native_result=0`，`FX3_KEY95_STEP_DONE` 1/2/3 齐全。runner 的 `visual_changed` 对第 1 键只是 `e0140e…→291427…` 的 NO CARD 源面切换；它不证明菜单完成。`receipt.menu_verified=false` 是 runner 保守的固定字段，不覆盖上述独立人工 PNG/ring 观察；也不能将一次像素变化视作该键下游处理结束。

## 同钟时间线与性能边界

所有下列 guest 数值仅相减 guest `CLOCK_MONOTONIC`，host 数值仅相减 host monotonic；原始行号、TID、screen ID、源 token/phys 见 [RUN-ANALYSIS.json](RUN-ANALYSIS.json)。内核 printk 时间没有被直接混进此表。

| 段 | guest 同钟间隔 | 证据与限制 |
| --- | ---: | --- |
| MENU down receive wait-enter→return | 185.792399 s | `wait_enter_step=0`、`wait_return_step=1`，线 181456；**主要包含发送前空闲**，不能称 AP 处理耗时。LEFT/DOWN 同类等待为 62.933793/47.519507 s，亦是键间空闲。 |
| MENU down receive→AP89 首个 screen-open | 0.176689 s | 线 181552，TID376，`0→0x2e0`；再 `0x2e0→0x275`，第二 presenter return 在 +0.286220 s；只表示 screen 创建挂点返回。 |
| MENU down receive→完整菜单源帧 OSD commit | 4.543356 s | token `0x402`、phys `0x43feb5100`、source seq1999，线 185502/185503/185513；validate→copy 5.097 ms，copy→commit 18.405 ms。AP89 最后 create 与此 commit 相隔约 4.257 s，但跨 TID、异步流程无明确因果边，不能直接指为 AP CPU 工作或 LDEC。 |
| LEFT down receive→screen-open/完整类别源 commit | 2.911862 / 4.324779 s | `0x275→0x274`、source seq2953；先前 source seq2951 是部分切换图。 |
| DOWN down receive→完整新类别源 commit | 0.924491 s | source seq3648；此键未见新的 AP89 screen-open。 |

按**同一个 host 时钟、同一观测点**比较“host `sent_monotonic`→ring 首次读到指定完整 UI PNG SHA”：旧 v17 三键依次 **197.468/31.991/2.599 s**，本轮 v21 为 **4.689/4.647/1.296 s**。v21 MENU 首次任意像素变化比完整菜单更早，且是 NO CARD 闪动；完整菜单同一 source seq1999 先在 guest +4.543 s commit、host +4.689 s 读到。两轮候选与运行条件并非受控重复样本，不能据此称探针修好了 192 秒卡顿或保证后续性能。旧轮缺 guest AP89/OSD ns，故旧轮内部阶段耗时保持 unknown。OSD 软件提交亦非原 CP 最终合成证明；MSS 发送成功不等于内核接收或 timer 复位。

## 会话限制与剩余阻塞

旧 TRY2 v4 的 [runner](../../try2-delivery/run_trial_v4_try2.py) 将 `--max-minutes` 默认和最大值写死为 15，`trial_web_try2.py` 的 `TrialState.max_steps=30`、提交拒绝和页面说明写死 30；这是旧宿主试用边界，不是相机的原生限制。新 FX3 guest `HP95_MAX_STEPS=4096`，InputGate 校验 31/32/4096 的宿主 fixture 已通过；**真实 guest 第 31/32 键仍未跑**。v21 候选 CLI 默认 60 分钟、4096 键，可配置 1..120 分钟与 32..4096 键；本次诊断显式压为 15 分钟，总量只用 3 键。原默认入口保持旧版，未切换。

本轮暴露的精确可用性缺口：单靠“PNG SHA 变化”会把 NO CARD 闪动或部分切换当作 `visual_changed`，提前放开网页按钮。v21 已把原生接收、画面待更新、无变化观察、未知 ACK、原生关机分别有限处理，但**仍缺内容语义上的完整菜单身份门**；下一版应以可复核 screen/source/完整图证据约束 MENU 等导航，保留 100ms、一次 pending、原像素身份与原生故障门，不自动重发。新实现和真实浏览器+guest 联动须另行审核，不应把本轮健康回执提升为默认入口。

[资源回执](RUN-RESOURCE-RECEIPT.json)：SIGINT 由本轮 runner 收尾，API16 在 20 秒规则内 1.573 s 得 guest ack 与原 16 字节回读；QEMU PID56293 exit0/reaped/absent，observer PID56291 已退出，双锁独立 `flock` 再核 free，原件输入 SHA 全不变，`serial.log`、三键输入及逐图文件各有 SHA。没有相机、USB、物理 SD、keepalive、920204 注入或 Backup 写入。
