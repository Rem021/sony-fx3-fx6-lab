# 下一轮同 guest 时钟观测与宿主交互合同（离线准备）

本文件是**源码与构建准备**，不含新 CPIO/DTB 或 QEMU 运行许可。当前已跑完的三键仍使用 v17 与原 `vmopt-20261103-try2-mss-all-v3`；本目录 `passive-timing-next/` 的 SO 仅离线编译，既有 TRY2/TRY1 入口和 FX6 基线均未修改。

## 先闭合的两段时序

现有同 guest `CLOCK_MONOTONIC` 数据能确定 key sender up 与 MSS 发送入口/返回，但 `FX3_KEY_INPUT_RECV` 只有串口顺序，AP89 screen-open/create 没有 ns，OSD owner/current/copy/commit 也没有 ns。MENU 首次 ring head 推进 +192.158 host s、LEFT +28.024 host s，是这两个宿主取样段的总量，不能直接归因 LDEC、CPU 或网页。新源码只在**已有**日志点增加 guest clock、TID 与已有对象 ID，不新设普通指令挂点。

| 段 | 新源码位置与已有事件 | 可关联字段 | 明确不代表 |
|---|---|---|---|
| native key queue wait | `fx3-rm-empty-provider-v8-long-use-timing.c` 的 `osal_rcv_msg_tmo` 成功返回日志，`wait_enter_ns` 在原接收调用前，`wait_return_ns` 在返回读取 errno 后立即取；`wait_enter_step` 与 `wait_return_step` 分开 | queue `0x807a0020`、step、key、down/up、TID | wait 长度不是 App 下游处理耗时；已有等待可能在 step=0 时开始，0 时戳不能相减 |
| screen creation | `fx3-preset-context-v6-save102-timing.c` 已有 AP89 id32、40、41 日志 | screen ID、TID、原生点、入口/控制器/呈现器返回；原 48 个 hook 位置不增不减 | ID 邻近不等于某键直接导致；factory return 不等于可见像素 |
| OSD 资源与提交 | `fx3-osd-headless-v7-observe102-timing.c` 已有 OWNER_CURRENT、VALIDATE、COPY、COMMIT 日志 | frame seq、pending op、source token/physical、TID、`clock_id=1` | OSD 软件提交不是原 CP 合成/屏幕最终显示；GPE/LDEC 消费不能仅靠邻近行号连接 |

三份源码由 `prepare_passive_timing.py` 从固定 SHA 原件重建，精确差分在 `passive-timing-next/src/*.diff`；`build_passive_timing.py` 用原构建参数在 `passive-timing-next/build/` 编译，结果在 `source-receipt.json` 与 `build-receipt.json`。实际源码 SHA（RM/AP/OSD）依次为 `7467449b4230f2636d10550a4727791689b897061db6f53216d7dcac62a98bc6`、`8b6d64e307dbfd8dc3ffd3b7ca961516bc0c2833450fc4e2bfb2ff970a5981ec`、`619d8a59a66b1de99fe6f9e6d8695e9a3fabe8967b070276ee67e0c9bc02e936`；三份离线 SO SHA 依次为 `ff38874e128d517147b1712588bf68d24412dae781a390eaa8bd7d230c3c1707`、`52ed3b5b2cdadc46e1c78c596a60d06a3fd865bb9bb5420a0bb5f2492df12392`、`8023300a7b02e69cb1ea39c1489214cabce403cc3cab39058ac00bf06cd2a636`。三次 Zig 编译均 exit0；`dprintf` 调用个数各保持 11/13/22，新增日志行数 0、新线程 0、动态分配 0、新指令 hook 0。RM 对 key queue 的每次 receive wait 新增一次 `clock_gettime`，OSD 仅在原日志点取时钟；仍可能有可测性能扰动，**编译通过不能当运行无扰动**。时戳函数保存/恢复 errno；RM 原接收前重置 saved errno，返回先取 native errno，立即取返回时戳，再恢复 native errno；与原 native 调用返回值及后续 errno 合同一致。时戳 0 按未知处理。

## 原字、CPIO 与撤销合同

- 固定原 appFw.so SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`。AP89 现有原字 guard 共 48 处，关键 id32 `0x218fd0c=0xa9b87bfd`、id40 `0x218ffe8=0xb94002a1`、id41 `0x218fff4=0xf834dae0`，仍由原 `bind()` 在安装前逐一核对并运行 GPR/SIMD/NZCV/SP 自检；新增时戳源码未改地址、期望字或安装数量。MSSv3 观察器原 guard `0x2d35168=0xa9bc7bfd`、`0x2eb4f58=0x72b01240`、`0x2eaf294=0xa9ba7bfd`、`0x2eaf308=0x7100001f` 保持原 SO，绝不按被否定的 display-contract v3 手写表改探针。RM 与 OSD 是现有符号包装/软件 ring，不新增原程序字节补丁。
- 固定 v3 CPIO 的三处拟替换成员及原 SHA：`simulation/fx3-rm-empty-provider-v3-setup.so` = `6acb0e52e610cb0d13721f38fcf1c7c27b0e5a48e687d7a4feda5fde9f9bcd14`；`simulation/fx3-preset-context-v2-screen.so` = `eb55680196806fb86958d632c6aed939eae91aa1ef928690a4a7d21d6a76c170`；`simulation/fx3-osd-headless-v5.so` = `816bbf9019ff422c2e24ca5a601a41dc144fa82e7baf39a563d638a55a841dbb`。下一步若获运行许可，构建器应先断言 v3 候选、三原成员及 English gen4 seed SHA，**只**替换这三成员，DTB 只更新 initrd-end，再做 CPIO 成员集/模式/其余哈希与 loader audit；任何不符即不生成可运行候选。当前尚未生成 CPIO/DTB。
- 撤销只需回选原 v3 candidate 与本轮 v17 runner；不能覆写原件、旧候选、原种子、preferred、STATE/TRY2 默认入口。未来运行若 bind 失败、时戳为 0、input missing、APO、全零帧、overflow 或源身份不符，停止并走原 20s guest ack/API16 恢复、QEMU reap、双锁释放；没有通过前不提升入口。

## 消息与资源未知

GPE104 用户态已有 ns，但必须用其 `seq`/source 与 OSD `copied_GPE_last` 等显式字段核对后才能关联；`FX3_LDEC103_IOCTL` 是内核 printk 时钟，不能直接与用户态 `clock_gettime(1)` 相减。LDEC 某请求属于哪一个 AP89 screen 或哪一帧尚无明确请求 ID，保持 unknown。MSS #21..26 的发送端关联同样不证明 upm.ko 消费或 timer 复位。若资源解码起止仍无同钟关联，下一步先做静态路径/原字复核，不能靠同一串口邻近行制造因果。宿主轮询峰值间隔不足 2s，只说明观察没有长时间停止，不证明 guest 工作段性能。

## 宿主五场景合同

| 场景 | 可见状态与下一动作 |
|---|---|
| 原生 down/up 完整且像素变化 | 用新的 immutable PNG/RGBA/SHA 与 ring epoch 身份记录 `visual_change_observed=true`；一键完成，下一键仍须人工看新图、单 pending。 |
| 合法无变化键 | 有界观察窗口到期只记 `input_received=true, visual_change_observed=false, visual_outcome=unknown/no_change_observed`，显示当前固定 PNG，可由人复看后提出新键；不能声称 guest 已完成绘制，也不永久锁住 pending。 |
| 迟到变化 | 观察期后到的新 frame 另记提交时间与 SHA；若尚未送下一键，旧 PNG 请求由当前像素门拒绝且不写 guest，重新看图；若已送下一键，两个动作对新帧的归因标 unknown，暂停后续输入供人复核。 |
| 输入证据缺失 | 原 12s 原生 down/up 证据门停止，本键不重发，保留 serial/QMP/ring 现场后做 API16/退出清理。 |
| APO 或原生 shutdown | 在当前循环和**紧贴发键前**二次 log poll 查新事件，命中即不再写 guest，记录原生事件与时间并正常收尾；不注入 keepalive、不改电源设定。 |

`run_trial_v19_mss_key_contrast_preinput_stop.py` 是从本轮 v17 固定 SHA 独立派生的**宿主**候选，只增加最后一项发键前关机复核与独立 label/STATE；`host-v19.diff`、`host-v19-build-receipt.json`、`host-v19-test-receipt.json` 记录五个生产 AST + 原 FullLogMonitor fixture、语法与 `--help` 离线通过。该补丁没有集成上表的无变化/迟到变化状态机，不可直接称下一版可用性闭环。
