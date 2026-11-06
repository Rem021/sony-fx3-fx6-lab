# 两轮待机帧切换离线复核（2026-11-03）

**结论：`2914275c…` 完整待机和 `e0140ea1…` 近黑画面是两种真实、不同的 guest OSD ring 像素，均由有效 native target 的新 `0x1003` 源提交产生，随后 `0x1005` 重复该源。** 两块物理目标交替使用，但完整／近黑状态不是某个 token 的固定属性：首轮通常 `0x402` 完整、`0x401` 近黑，补轮相反。现有资料不足以证明近黑是原厂有意隐藏、最终 CP 合成画面，也不足以排除宿主“取最新 OSD 源而非最终可见层”的选择问题；因此不改像素身份门，也不把非零像素或未关机当作正常性证明。

## 可复核材料与时钟边界

- 运行原件：`../../runs/try2mssallinternal-48a838e5/` 和 `../../runs/try2mssallinternal-c017e6ed/`。串口 SHA256 分别为 `4452b928c28f9c6cfbdad5380678cbb84219722e1efbc783a161e8f84bd331e0`、`4f7d1745806314521f43257eec20ac69581119181057ad1d191549afab3ceac0`。`rebuild_timeline.py` 只读原 `serial.log`/`osd-ring-readback.json`，重新生成 `timeline.json`，含帧 tuple、每条关联日志的 0-based 行号和原文；运行 `python3 rebuild_timeline.py` 可复现。
- GPE 行内 `ns` 是 guest monotonic；OSD `1003/1005` 提交日志没有可直接相减的 guest 时间。ring JSON 的 `host_monotonic` 只用于同一轮主机读帧间隔。内核 `[3273…]` 等 printk 时间是第三个域，不与前二者直接相减。两轮 ring 是抽样而非全帧保留，中间可有未采样序号。
- 本次用图像工具逐一查看首轮 `internal-observe-01.png`（近黑）与 `trial-frame.png`（完整）、补轮 `view-step-01-seq-240-2914275caea5.png`（完整）与 `internal-stale-01-f37ae114-current.png`（近黑）。近黑仍含右下图标；完整含 English 待机图标和橙色 `NO CARD`。PNG SHA 分别精确对应上述两个身份。

## 同轮时间线

| 轮次 | 原生绘制与源提交（guest 顺序；GPE ns） | 主机实际抽样（host monotonic 秒） |
|---|---|---|
| `48a838e5` | `FillRect 326`→`Flush 327`，最后 GPE return `104359850000`，`1003` 源帧 **542** `0x401 / 0x43ae96100`，无同批 BitBlit；其后 `FillRect 328`→`BitBlit 329`→`Flush 330`，最后 return `105013975008`，`1003` 源帧 **549** `0x402 / 0x43feb5100`。两组 GPE `result=0`。 | seq542 近黑 `305934.489772`；`1005` seq548 仍引用 542、近黑 `305934.996073`；`1005` seq551 引用 549、完整 `305935.409178`。**548→551 为 0.413105 秒**。首请求仍指向 seq548，但没有送键。 |
| `c017e6ed` | `FillRect 399`→`BitBlit 400`→`Flush 401`，最后 return `115215464992`，`1003` 源帧 **648** `0x401 / 0x43ae96100`；其后 `FillRect 402`→`Flush 403`，最后 return `115763448000`，`1003` 源帧 **656** `0x402 / 0x43feb5100`，无同批 BitBlit。两组 GPE `result=0`。 | seq648 完整 `306639.883405`；`1005` seq655 引用 648、完整 `306640.378770`；`1005` seq663 引用 656、近黑 `306640.897359`。**655→663 为 0.518589 秒**。人看过完整冻结 PNG，提交时像素仍同一 SHA，runner 再核验时已成近黑，故拒绝写 guest。 |

`1005` 只是重复此前 `1003` 的 `pixel_source_seq`：不能拿 `1005` 次数解释重绘。两轮目标都为 640×480、16-bit 映射、span 614400；对应 `FX3_OSD_HEADLESS_VALIDATE result=0`、`COPY copied_equal=1 native_read_lease=1 shared_raster_guard=1`、`LEASE result=0`，ring 记录 target tuple 有效且 `guest_native_lease_released_before_ring_commit=true`。近黑并非 QMP 读取到失效物理页或并发撕裂的现有证据。`registered_target.kind` 在 `0x401` 为 2/epoch1、`0x402` 为 1/epoch2，两个物理地址在两轮相同；`kind` 和屏幕合成层角色尚无原厂语义证明。ring `CP_composition_panel_acceptance=false`，日志也明写 `native_plane_role_unproven=1`。

GPE 绘制日志均标 `screen_anchor_extent_id=0x81`、`screen_anchor_type=0x545`、`screen_serial=0x2`，目标 native `type=0x403`、相应 epoch/uhdl/phys 校验通过；这是同一个 GPE screen anchor 的证据，**不能等同原应用 `FX3_AP89_SCREEN_CREATE screen_id=0x2ae/0x2e1/…` 的 UI 页面 ID**，当前缺映射。完整源前的 `BitBlit` 有 `source_uhdl=0x30303030`、`source_epoch=3`、`source_phys=0x410924000`；近黑源同批只有 `FillRect`、`source_object=0`。这说明两类提交的 producer 绘制序列不同，但该 BitBlit 仅 96×26，整屏完整内容还依赖目标中此前的像素，不能据此证明有意隐藏整个界面。日志由注入 adapter 记录 GPE/OSD 观察，QMP 主机只读导出；不是原厂屏幕可见性的直接回执。

## stale 与下一轮最小手工方案

`c017e6ed` 的 `internal-stale-01-f37ae114.json` 明确 `stale_no_guest_write`、`next_step_unchanged=1`、`sent_steps_unchanged=0`，原生串口 `FX3_SYNTH_KEY` 计数 0，`trial-input-events.jsonl` 未产生。`test_stale_contract.py` 从该轮封存的 v15 runner **只抽取原 `classify_internal_review` 函数**，用原 PNG/JSON 离线重放，得到 `stale/current_committed_frame_changed`、`key_steps=0`。v15 主循环在 stale 分支仅归档旧请求和当前 PNG、标记旧视觉身份不可再用、要求新人工审阅；没有递增 `host_step` 或调用 `input_gate.command`，下一轮迭代仍能接受新看图请求。后来的 `STOP_FOR_REVIEW` 是操作员另写的停止文件，主循环将其映射为 `health_failure`；这不是 stale 分支自身的判定，且该停止文本“仅序号变化”与真实像素变化不符。离线函数测试不能代替后续真实主循环验收。

后续若获准再测：在有效锁和健康状态下，先冻结最新 PNG/JSON 并人工辨认完整或近黑；完整且目标键语义明确时只提交一个带当前 SHA 的请求；若得到 stale，**不自动重试键**，查看新 PNG，必要时等待下一完整源并重新冻结/人工决定；若出现原生故障、全黑、倒计时不足以预留 240 秒收尾或重复切换无法确定可见层，则停止并完整退出。首键拟用 MENU 打开原生菜单，再看实际 PNG 才决定 LEFT/DOWN；本轮不运行该方案。

## 未知与修正选择

当前不能确定双 buffer 是否代表原厂显示合成层、近黑是否原生待机隐藏信息、主机是否选错最终层；也没有 CP 最终可见面板回执。现有证据支持保持严格像素身份门，并把 stale 作为**待重新看图的非写入状态**；不支持跳过近黑帧、自动等到完整再补发、复用旧请求或将其算成正常渲染。故本次**没有行为补丁**，原 runner、候选、种子与历史运行均保留。协调者另发的 host-startup-receipt 修复不在本离线调查内整合。
