# FX3 网页按键操作上下文：独立只读审查

结论：**显示帧身份和一次输入许可应当分开建模，但现存信号不足以生成可信的操作上下文 ID，不能据此放宽 server gate。当前更小、可证实的候选是：保留原门，在新的独立验证合同中允许“本次明确未入队 → 亲看新图 → 新的人工点击”。** 它能避免一次正常拒绝必然结束整轮，却不保证消除刷新竞争或首 MENU 必然成功。

2026-11-04；卷 UUID 已核对为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。Mac 根目录不是 Git 仓库；仅在本审查目录新增文件，未启动 VM、浏览器或 fixture，未改现有源码、平台、固件、入口或 helper。下文“反例”均为协议推演，不能充当真实 FX3 行为证据。

## 1. 已知事实及边界

- `RUN/web-key-rejections.json:8–36`：唯一拒绝在 `steps=0, phase=ready, busy=false, pending=0, review=false`；observed `116/gen24/291427…`，current `124/gen25/e0140…`；失败项仅 SHA、generation。源代码 W18:135–170 的此分支在 `pending.append` 前返回，所以这次请求没有入队；不是原生 MENU 处理失败。
- `R19/evidence/pixel-difference.json` 与两份原字节 SHA 已复核：885 像素，bbox `[364,7,448,27)`；新图来自历史同 SHA 原件，**不是本轮现场另存**。协调端已亲看，差异仅 NO CARD 有无；本审查没有重新目视验图。两个静态样本不能证明时间闪烁、变化的原生原因或所有小变化均可忽略。
- 本轮 `osd-ring-readback.json` 同时保留 116、124 元数据：116 的 token=`0x401`, target=`kind2/epoch1/object=0x7f74001200`；124 为 `0x402`, `kind1/epoch2/object=0`，FB 相同但 bitmap、allocation、config_hash 不同。这排除了“只需拿单个栅格指针当操作 ID”的捷径；也不能反过来宣称资源切换就一定换菜单。
- W18:62–76 的 `content_generation` 由宿主**采到并 publish 的 PNG SHA**变化递增；它不是 guest 操作事务号，也不能覆盖两次采样之间未看到的 A→B→A。W18:144–156 当前允许同 SHA、同代际的不同 sequence，并非单纯要求 sequence 永远最新。
- r19 的改动限定在点击预检与固定点击时 SHA/gen（W19:452–503）；服务器门未变。它能把已在预检看出的变化变成未 POST，但 GET 后至 POST 的变化仍可得到 409。57 项交付和 14 个离线 fixture 的核验沿用协调端结论；本审查没有重跑。

## 2. 优先候选：明确未送达后，允许新的人工尝试

**可评估，且比新增 native context 小得多；不需要改变原 server gate。** 产品文案本已要求拒绝后看新画面、自行决定，不自动重发（W19:367–371）。旧测试“遇任何 409 必须 End”是既定单轮验收合同，不能在原轮临时取消；下述只适用于另立并冻结的新合同。

| 本次尝试的可核结果 | 可结束该未送达尝试的 alarm？ | 后续 |
|---|---|---|
| 点击预检明确终结，证明未创建 `/api/key` POST | 满足归属及安全条件时可以 | 等新图加载、亲看后显式新点击 |
| 本次 POST 收到原 server 的完整明确拒绝，锁内分支证明未入队 | 满足归属及安全条件时可以 | 同上；原门再次独立检查 |
| 202 accepted；或 guest 已写入/接收 | 不适用“未送达恢复” | 原 accepted 键的 20 秒看图确认合同完整保留 |
| 5xx、网络超时/断开、响应解析失败或回执不完整 | 不可以 | 送达未知，保持锁定 End；不自动重试 |

恢复至少要有：`run/launch + document incarnation + attempt_id + alarm_nonce + expected_step + key + 点击时 frame身份` 的对应关系；本次结果已终结且证明未入队；无在途 mutation、无其他已接受但未结清的键；本次 `steps` 未增长只是佐证；原生无错误/关机、未停止、无 review/unknown；当前 ready，当前有效图已完整加载并符合原帧门。此后是人亲看后发起**新尝试**，不是把旧点击改绑到新图。

**现成 helper 不能凭现成提示直接安全取消 alarm：**

- D18:105–117 的 `cancel(nonce)` 只查页面身份、nonce、armed、期限；不验证输入结果。accepted 的约束来自调用方 E18:35、81–103，不能把 cancel 本身当作未入队证明。
- W19:456/486 设置拒绝提示，但仅在下一次 POST 成功后 W19:495 清除；故“尝试 A 已拒绝 → 尝试 B 正在 POST → A 的拒绝提示还在 → 用它取消 B alarm”是最小反例。W19:463–494 也说明 `steps` 可仍为 0 而 B 已在途。
- B18:59 见任意 `explicitRejection.kind=key` 就拒绝，提示没有 attempt ID；不能把旧 hint 当 B 的结果，也不能直接沿用旧 helper 的指纹假称新合同已验证。

受控、单文档、单操作者环境若有从点击前开始的完整独占 HTTP 记录，能把该次 POST/完整拒绝及 server 锁内记录唯一对应，并排除第二次在途请求，现有证据可供**一次人工审核**使用。仅靠网络记录中“没看见 POST”不足证明本地没有发送；本地预检需要对应 handler 终结点。若要产品化/工具化恢复，最小新增证据是只读、结构化的 `attempt outcome`（`preflight_not_sent / explicitly_rejected / accepted / delivery_unknown`，绑定 attempt、step、nonce、发送状态；server 拒绝最好回显 request ID），而非从提示文案猜测。没有这项归属证据就否决自动化 alarm 取消；不应因此去改上下文门。

## 3. 为什么 steps/ready 等协议会把旧点击发往新菜单

| 简化协议 | 最小反例；未增加 host steps |
|---|---|
| `steps相同 && ready` 就允许所有帧变化 | 人看菜单 A 点 OK；原生定时器弹出 B；`steps=0/ready=true` 仍成立；旧 OK 落到 B |
| `screen_id` 或最近 SCREEN_OPEN 不变 | 同屏焦点/选中值/模态层/键使能变化；旧 OK 选择另一个项目；没有 screen open |
| 同 FB/资源 tuple/epoch | 同一缓冲绘制 A、B；资源不换而操作对象换。反面也成立：当前 116→124 资源换但未证换菜单 |
| PNG 同 SHA 或两 SHA 白名单/bbox 掩码 | 原生接收目标已换，绘制尚未提交；旧 PNG 仍在。或掩掉的顶端区域恰含改变键语义的状态；像素位置不证明语义等价 |
| 只比 SHA，不比代际/上下文 incarnation | A→B→A；历史图相同，但旧许可不应复活。当前已观察的 A→B→A 由 W18 generation 拦截，不能删除 |
| 预检后改写 observed 为最新图 | 在 A 点击，预检得到 B，发送时把 B 身份填入；服务器正确匹配 B，执行的却是旧意图 |
| 只在 HTTP 入队时比上下文 | 入队时 A；原生异步转 B；runner 随后写键，旧点击仍到 B |
| 暂停 guest 读到 A 就算最终证明 | 恢复后已有原生转场消息先于键被处理；真正 UI handler 收键时已是 B |

后两条是候选必须解决的时序要求，不是声称本轮已发生误送。现有 runner 在 HTTP 之后 `take()`（R18:643），只再检查原生错误/退出（695–703），暂停后写新软件 gate（710–724）；没有菜单上下文复核。I18:41–52 检查顺序、done、result 和写回，不携带菜单 ID。即使现有 PNG 门也不能据此升级成“原生处理时必是人看到的菜单”的证明。

## 4. 现存信号：可以否决，但不能独立放行

| 信号与源码 | 已证明什么 | 缺少什么 |
|---|---|---|
| `steps/ready`；R18:565–587、722–731 | 首次启动门已成立；host 已提交几键 | ready 是首帧后保持的宿主标志；steps 在写 gate 后增长；没有当前接收目标、焦点、原生待处理转场 |
| `SCREEN_OPEN_ENTER`；RUN serial:11528、14732、15705、15901；R18:565–568 | 发现一次转场入口、manager、id 参数，可立即保守失效旧许可 | 日志自己声明 `creation_not_yet_complete=1`；无成功 commit、层栈/焦点修订、与某帧的原子绑定；“没新日志”不证明没变 |
| 原生 `open screen: A -> B`；RUN serial:14708、15700、15876；L18:90–94 | 文本转场、关机拒绝信号 | L18 不维护完整菜单状态；原始文本无完整有序无丢失合同，不能拿 host 收到时间当与帧的因果关系 |
| `KEY_INPUT_RECV down/up`、sender up/done；R18:592–625；V18:1–4、26–40 | 该键进入原生队列；可做有界观察 | `downstream_handler_completed=unknown`；无效果时明确保留未知；不能宣布菜单处理完成 |
| validated raster ring/registered target；T18:13–35、83–113 | 像素来自受生命周期及读 lease 保护的已提交软件 ring；排除 torn、错误地址/范围/FNV | 描述的是图形资源，不是 key recipient；lease 在 commit 前已释放；普通 buffer 轮换不得自行解释成操作状态同/不同 |
| v25 diagnostic；P18:16–19、25–43、74–84 | produce/receive/commit/wait/signal 的有限尾部身份及原返回值 | 不含菜单焦点/接收状态；本轮 accepted=1456、仅尾部1201…1456，虽 dropped=0/torn=0，仍 `absence_cannot_prove_no_guest_call=true` |

所以可以用已知转场、资源失效、错误、关机事件**收紧**输入；不能用这些事件未出现来证明任意两帧语义相同。零键本轮也不足验证同屏导航、弹窗、延迟处理的全部失效点。

## 5. 若继续研究操作上下文，最小可检验合同

以下为尚未具备的候选条件，**不是宿主现有字段的重命名**：

1. 原生 UI 接收方拥有单调、不复用的 `context_revision`，绑定 run/lifecycle incarnation。所有影响七键语义的变化——screen、模态层栈、焦点、选中参数、键使能、对象销毁/重绑及待完成转场——在同一个有序域使旧 revision 失效；transition 中为 unknown，不可发许可。静态 screen ID 或截断指针 hash 不够。
2. 每份可展示帧有同域的稳定上下文绑定；提交前后 revision 一致且无待转场，才建立 `frame F belongs to C`。前后原生序号/完整性/生命周期证据需可核；任一缺失、覆盖、跳代或 unknown 即失效，不能用 host 两个相近时间戳代替。装饰性变化要靠原生生产者与上下文语义审计证明，而非 bbox、两 SHA 或像素阈值。
3. 一次性许可绑定 `run/lifecycle/C/expected_next_step/nonce`，在同一锁内原子预留并仅入队一次；不因刷新重铸旧点击的许可。提交携带点击时真实已加载 F 的身份；当前存在有效帧且与该 F 均有可信 C 绑定，才可能允许跨 PNG 变化。历史确认仅证实那次看图；下一键仍须满足**当前可用帧、当前 C 和未消费许可**，不能沿用历史确认通行。
4. 最终比对点必须覆盖 **HTTP入队 → guest gate写入 → 原生UI消费**。可先研究现有原生序列化机制能否保证 C 检查与键分派之间没有转场；若不能，单加只读 observer 或 paused snapshot 不能建立原子准入。需要接收侧条件消费/等价序列化则已超出现固定平台的纯 host 修复范围，须另行设计，不能假称只读计数器已解决。

可检验顺序：先离线明确拥有者/字段/所有失效调用点，再取得同次自然运行的帧、原生上下文前后修订和最终键消费因果证据；反例覆盖定时弹窗、同屏换焦点、A→B→A、同像素异上下文、buffer轮换、销毁重建、多文档竞态、迟到 POST、unknown、停止。**只要存在一次未观察到的语义变化、revision 可复用、图与 C 无法绑定或最终消费竞态未封闭，就否决放宽。** 本任务不开展这类新运行。

## 6. 不得丢失的保护

- 原生断言、panic、合同拒绝、OSD错误、原返回值、原超时均保留；不延长原生 receive 预算，不补 keepalive/replay。L18:4–15、81–86；输入证据 12 秒预算与视觉观察6/30秒也不能误当处理成功（V18:8–10、26–40）。
- End/Ctrl-C、native power-off/shutdown、全黑/无有效帧、会话终态优先，停止后不可借旧许可恢复；写键前错误/退出复查保留（R18:123–131、480–538、695–724）。API16恢复、QEMU退出/reap、双锁释放和浏览器final ACK分别留证，ACK只证结果送达（W19:251–257、407–415）。
- 5xx、超时/断连、不完整 mutation 回执保持送达未知并锁键，不因 ready/steps/新图推定没送达，不自动重发（W19:309–324、362–371、493–503）。
- 白名单、顺序、持续时间、键数上限、单个 pending/busy、一次入队及原生 down/up 合同全部保留（W18:135–170；I18:5–6、41–52）。server接受一次不等于原生效果完成。
- `confirm_visual` 只解除宿主 review，不入队不写 guest（W18:188–216）；精确历史确认回执可消除该确认的未知，但不能让旧图、旧上下文、旧许可授权未来键（W19:340–345、529–542）。
- run、页面、native receiver和资源各自的生命周期不混用；帧缓存缺失、invalid/torn、资源销毁/重建、context unknown 均 fail closed。保留 host/token/origin/请求格式保护（W19:563–618），不把公网内容或展示状态当授权。

## 7. 验证与外部参考

`python3 -B host_counterexamples.py`：13 个协议反例/正例 + 11 个人工恢复条件断言通过，详细 trace 在 `host-model-results.json`。`context_revision` 和完整性 oracle **是模型假设，未从 FX3 取得**；这些结果只验证逻辑反例和所需合同，不验证生产实现或 VM。

RFC 9110 §13.1.1（2022-06，2026-11-04回读）规定 If-Match 使用强比较，围绕目标资源的所选表示执行前置条件。由此不能直接得出 PNG 必然是本系统正确的操作并发对象；把“显示表示”和“操作许可”分开是本审查的设计推论，仍须以上原生语义及序列化证据。[官方原文](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.1)。目前 `/api/key` 使用自定义 observed_sequence 门，并非 HTTP If-Match 实现。

源码别名（均相对本目录；行号以 `SOURCE-INPUTS.json` 中 SHA 冻结的文件为准）：

- W18：[r18 TrialState/PAGE](../v25-r18-frame-admission/trial_web_v22_navigation_review.py)
- W19：[r19 TrialState/PAGE](../first-key-freshness-r19/trial_web_v22_navigation_review.py)
- R18：[runner](../v25-r18-frame-admission/run_trial_v25_diag_r3.py)
- L18：[完整日志监视器](../v25-r18-frame-admission/trial_log_v4_mss.py)
- T18：[已提交帧读取器](../v25-r18-frame-admission/trial_ring_cached.py)
- I18：[输入 gate](../v25-r18-frame-admission/gate_input_usability.py)
- V18：[输入/画面观察分类](../v25-r18-frame-admission/pending_visual_v20.py)
- P18：[诊断尾部解析器](../v25-r18-frame-admission/parse_v25_diag_r3.py)
- D18：[deadline](../v25-r18-frame-admission/operator-helpers/deadline.js)；B18：[bounded capture](../v25-r18-frame-admission/operator-helpers/bounded_capture.js)；E18：[explicit confirm](../v25-r18-frame-admission/operator-helpers/explicit_confirm.js)
- RUN：[本轮证据](../../runs/v25gate-n64-r17-65cecb63/)；R19：[r19交付](../first-key-freshness-r19/)

入口仅使用本目录 `README.md`；遵守本任务写入边界，未修改项目总索引。
