# FX3 MSSv3 单键对照回执（2026-11-03）

## 结论与边界

本轮唯一 QEMU 运行 `try2mssallinternal-keycontrast-06db37ef` 在 551.249 秒主动 Ctrl-C 收尾，实际只发 MENU、LEFT、DOWN 三键；每键均先看固定 PNG，再单次提交。三键的原生 `FX3_KEY_INPUT_RECV` down/up 各一条且结果 0，三次操作最终各有可辨原生画面：English 待机→Setup/Area/Date 明细→左侧 Area/Date 类别焦点→Reset/Save Settings 类别焦点。本轮是内部 InputGate/PNG 证据，**不是浏览器试用通过**；31/32 边界也未测。无相机、USB 或物理 SD 操作。

MSS 注入观察器只在 appFw.so 现有发送路径普通指令处记录 QID `0x80924220`：入口 `0x2eaf294`、返回 `0x2eaf308`。56 条连续记录中，52 条构成 26 个同 TID、同 cmd、同 source 的入口/返回对；另 4 条是原序列标记。MENU 后见 `920119→920118→920202` 三次发送，LEFT 后同样三次，DOWN 后直到本轮退出未见该队列新发送。新增 call #21..26 都是 TID 592、source 元数据 `0x81cf6198`、返回 `x0=0`，入口至返回 guest 间隔依次为 6.868/4.440/7.926/3.405/1.711/1.209 ms。所有 26 次 `raw_ok=0`，仅能称寄存器/源元数据，不是线包读回；返回 `x0=0` 也不能证明内核已消费，更不能证明计时器复位。没有 `FX3_MSS_ORIGINAL_PATH_OVERFLOW` 标记，序号 1..56 连续；这只是本轮可见 ring 记录，不能外推长期无溢出。`920204` 仅在启动期 call 10/11 两次，本轮三键之后未见。静态 display-contract v3 手写分派表与固定 ELF 有不符，未用于更改探针或解释内核行为；本结论只用本轮原日志与已审过的 v8 指令挂点。

## 固定环境与离线检查

- 卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；启动前确认双锁 free、无其他 QEMU，复用既有 VM。候选 `vmopt-20261103-try2-mss-all-v3/candidate.json` SHA256 `2382063eacb5f185e8553c2596be2c644654efe7234adc1e4578f7464ab99a05`；CPIO `fb6aea623f158f49852fedd9a12ad8ecd9c13e8b19aeb59fb6c3f82b0f9676e9`、DTB `450e14bc76e07034a185eea0f008a15a6bb16cde6cb2db4a48221ccba6551408`。English generation4 Backup 固定副本 SHA256 `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f`。无 hybrid CPIO，原 FX3 内核/CPU/RAM/GIC/模型配置、原件、种子及既有 TRY2 入口未动；候选差分见上一级 `mss-all-commands-v8/preflight.json`、`build-receipt.json`。
- 独立 runner `run_trial_v17_mss_key_contrast.py` SHA256 `4918eaec03f512656b0170558c4491e9c3fdccc96b9ffc93b436fd9c277766c7`，源差分见 `runner.diff`。`offline-receipt.json` 验证底层 InputGate 容量 32 与本轮人工上限 12 分离、900 秒总 host/240 秒清理预留、启动早退及缺 serial 回执、原生接收缺失截止。实际 CLI 使用 `--internal-hoststep --max-minutes 15 --max-steps 32`；保留每次单 pending、100 ms 和原像素身份检查。
- 串口原件 `serial.log` SHA256 `863195a375445b53dc847f6790a441ef882f66e91dca18b327b27dae94933b34`，21,563,383 字节；`osd-ring-readback.json` SHA256 `16baf2b31d995b8cb651594b861a19062d1bbf0b8e866ba1528aab20003111b4`；`trial-input-events.jsonl` SHA256 `76c44ca8c3197c7f4cef87cef7a5ccc0ea9a910a1a2767268381e54f7f5fec36`。运行 `python3 -B analyze_key_contrast.py` 可从原件重建 `key-contrast-analysis.json`，含串口行号、26 对 MSS 发送、原生键时间、screen-open 顺序和固定帧身份。

## 三键时间线

以下 guest ns 只与 guest ns 相减；host 秒只从 host monotonic 的发送时刻及 ring 取样计算，**不跨时钟换算**。`FX3_AP89_SCREEN_OPEN_ENTER` 是注入 adapter 的入口观察，不含 guest ns，也不等于页面创建完成。全部截图均由图像工具实看，`PNG_sha256` 为固定文件身份。

| 键 | 发送前所见、理由 | guest down/up（秒） | MSS 同队列发送入口（guest 秒、call） | ring 首次不同像素与完整所见（相对 host 发送） | 实际所见 |
|---|---|---:|---|---|---|
| 1 MENU `0x1ab` | English 待机，NO CARD 与状态图标；打开原生菜单 | 155.088704 / 157.417632 | 248.724626 `920119` #21；248.737851 `920118` #22；248.753899 `920202` #23，三对返回均 `x0=0` | 首变化 seq78 +192.236s；完整菜单像素 seq80 +197.468s | [待机取样 PNG](../runs/try2mssallinternal-keycontrast-06db37ef/trial-step-01-key-1ab.png) 仍为 seq77 SHA `2914275c…`；随后实际看 [菜单 PNG](../runs/try2mssallinternal-keycontrast-06db37ef/view-step-02-seq-434-60e9acccbc46.png) SHA `60e9accc…`，Setup > Area/Date 45/59、English、橙色焦点。 |
| 2 LEFT `0x15` | 菜单明细橙色焦点；只切左侧类别焦点 | 429.836434 / 429.996450 | 458.975677 `920119` #24；458.982669 `920118` #25；458.988200 `920202` #26，三对返回均 `x0=0` | 首变化 seq435 +28.103s；完整左侧焦点像素 seq437 +31.991s | [即时取样 PNG](../runs/try2mssallinternal-keycontrast-06db37ef/trial-step-02-key-015.png) 仍为明细；随后实际看 [左焦点 PNG](../runs/try2mssallinternal-keycontrast-06db37ef/view-step-03-seq-605-15cb5b958cf6.png) SHA `15cb5b95…`，Area/Date 类别橙色，右侧变灰。 |
| 3 DOWN `0x30` | 左侧 Area/Date 类别橙色；只移动一类 | 495.644931 / 495.832886 | 无；MSS 最后记录 #26 的 guest 458.989409 秒，至收尾无新记录 | 首变化 seq691 +2.599s | 实际看 [类别移动 PNG](../runs/try2mssallinternal-keycontrast-06db37ef/trial-step-03-key-030.png) SHA `3d071654…`，左焦点 Reset/Save Settings，页码 46/59；未进入设置。 |

串口顺序中，MENU up 之后出现 AP89 screen-open `0→0x2e0`、`0x2e0→0x275`，再出现 MSS #21..23；LEFT up 后出现 `0x275→0x274`，再出现 #24..26；DOWN 后没有新的 AP89 screen-open 或 MSS 发送记录，但同 screen 内类别内容发生真实变化。DOWN up 为 guest 495.833s，最后 `FX3_KEY96_POLL` 为 544.776s，即约 48.943s 的后续可见窗口，不能外推该操作在其他状态永不发送。前 20 个 MSS call 都在 guest 44.983..49.854 秒启动区间；三键之后的两组三连是新增，不能混成启动背景。串口原行号和 call_id 可在 `key-contrast-analysis.json` 核对。没有新增 `920204` 不能单独推出省电倒计时未复位，因为观察点在 app 发送端，其他 timer 更新链与内核消费仍未闭合。

## 延迟、取样缺口和下一步

MENU 的 runner 在原有 180 秒 unchanged 等待后把 seq77 旧待机帧写进 `trial-step-01-key-1ab.*`；LEFT 的 6 秒 unchanged 等待同样先写旧明细帧。后续 ring 提交和人工冻结明确看到了两次真实页面变化，所以 `receipt.menu_verified=false` 是 runner 当时的取样结果，不代表人工最终菜单验收失败。独立读取 `osd-ring-readback.json` 的 613/142/111 次轮询：MENU/LEFT/DOWN 首次 head 推进约在 host 发送后 192.158/28.024/0.300 秒，首不同像素 192.236/28.103/2.599 秒；最大轮询间隔 1.991/0.552/0.698 秒。此轮无 HTTP 按键来源；页面慢已存在于观察到的 committed-ring head 推进之前，不能用网页 image 加载 Promise 单独解释，也还不能指认为 LDEC、CPU 或 host 压力。需区分 guest 输入消费、screen creation、资源解码/绘制、ring publish 各段；现有串口 screen-open 无 guest ns，原生 down/up 缺 host 到达戳，因此不能准确拆分其耗时。

下一最小可验证改进先修**宿主回执状态语义**：旧帧不能写作“画面已完成”。有变化时记录新帧并解除 pending；原生 down/up 完整而有界观察窗口内无变化时，记录 `input_received=true, visual_change_observed=false, visual_pending/unknown=true`，允许用户重新看当前固定 PNG 后决定下一键，不能永久占住 pending；迟到变化必须更新视觉状态，若用户基于旧 PNG 请求下一键，当前 SHA 门应拒绝且不写 guest。缺原生输入或发生 APO 时仍走既有健康停止/收尾，绝不重发。不能只延长 180 秒、放宽像素门或把合法 no-op 当故障；五种情况的可执行契约见 [PASSIVE-TIMING-PLAN.md](PASSIVE-TIMING-PLAN.md)。随后在独立候选中对既有原生 key receive、AP89 screen-open/create、资源检查/拷贝与 ring publish 增加被动同 guest 时钟戳，做一次短轮才能判定最慢段；发送端 MSS #21..26 不应被解释为内核已处理 timer。

协调者的前写关机复核已按固定 SHA 的 v17 另存为 `run_trial_v19_mss_key_contrast_preinput_stop.py`，仅离线构建/五个生产 AST 与真实增量日志 fixture 通过，详见 `host-v19.diff`、`host-v19-build-receipt.json`、`host-v19-test-receipt.json`；**没有用于本轮 QEMU，也不证明 APO 已修复**。同 guest 时钟的三份源码候选只在已有日志点增加字段，已在独立目录离线编译，但尚未装入 CPIO 或运行，见 [PASSIVE-TIMING-PLAN.md](PASSIVE-TIMING-PLAN.md)。

## 收尾与未验门

在三种目标输入已有可辨图像后，为避免无目的长等与保留清理预算，主动向 observer PID 37315 发 SIGINT，进入原有 Ctrl-C 清理。`receipt.json` SHA256 `dbe36cd0181ca51143dc06314d3e6f2675ae38fcd6b0e2cced4e43ea8d78a948`：总时长 551.249s＜900s，实际 3＜12 键，`host_observer_error=null`、未见 native shutdown/power-off、API16 20s 规则中 1.566s 得 guest ack 且原 16 字节 `000b00b4fd7bbba9fd030091f35301a9`，原输入 SHA 全相同；QEMU PID37320 exit0/reaped/absent，observer PID37315 已退出，两把 `.run.lock` 经回执和独立非阻塞 flock 均 free。`health_pass=true` 仅是本轮软件门，不等于浏览器、31/32、内核 timer 消费或无限稳定。
