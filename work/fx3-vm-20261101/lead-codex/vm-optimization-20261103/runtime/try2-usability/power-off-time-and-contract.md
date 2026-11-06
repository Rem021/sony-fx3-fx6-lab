# APO1 原生观察：时钟、输入及下一门

本页只针对 `runs/try2powerinternal-6a05c56b` 的一键运行，不将其因子套用到旧的用户轮或四键轮。只读 hook 与主机步进没有更改原省电时间，也没有周期性输入。

## 同一 host monotonic 时间轴（秒）

| 事件 | host monotonic | 相对 MENU 发送 | 证据与限度 |
|---|---:|---:|---|
| standby 第一份可验非黑像素 | 296746.045511 | -83.879140 | `trial-standby-ready.json`；尚非人工观察时间 |
| 人工观察前图并写选择理由 | 不可从 mtime 换算为 monotonic | — | `internal-observe-01-decision.md` 的文件时间 13:39:03.763 UTC；人工确实查看 `internal-observe-01.png` |
| host 发送 MENU 原生门命令 | 296829.924650 | 0 | `trial-input-events.jsonl`；100 ms 请求，单 pending |
| 已提交首个不同像素 PNG | 296830.270575 | +0.345925 | `trial-step-01-key-1ab.json`；这幅是过渡图，不是完整菜单；同循环 `busy=false`，无单独时间戳，故解锁只可界定在该证据写出附近 |
| 再次人工看稳定菜单 | 296874.521481 | +44.596830 | `post-menu-current.json/.png`；Setup > Area/Date，橙焦点和 English；`internal-step-01-result.md` 记录不发送第二键 |
| 关机前最后读帧 | 297132.442892 | +302.518242 | `trial-final.json`；非黑，因早停发生在原生关机通知之后；hook 的准确 host monotonic 未记，不能用该读帧时间冒充 |

UTC 文件 mtime 与 host monotonic 只各自使用，不跨钟直接相减。图片的提交与网页显示是不同层：本轮为内部 host-step，没有 HTTP 页面，网页 `image.onload` 及按钮解锁时延 unknown。此轮并无 host pending 占据余下约五分钟；看完稳定菜单后，验证者有下一键选择权但刻意不再发键以观察原生关机。原用户试用不等同本轮，不能据此归咎用户看图过慢。

## 同一 guest monotonic 时间轴（纳秒）

| 事件 | guest monotonic ns | 原始串口 byte offset |
|---|---:|---:|
| 注入 MENU down，原生队列发送返回 0 | 128235784000 | 12140999 |
| 原生 `FX3_KEY_INPUT_RECV status=1` | 未单列 ns | 12141461 |
| 原生 `FX3_KEY_INPUT_RECV status=0` | 未单列 ns | 12152443 |
| 注入 MENU up，原生队列发送返回 0 | 128359621008 | 12152797 |
| `FX3_KEY95_STEP_DONE`，一次 down/up | 未单列完成 ns | 12152981 |
| 首次 `FX3_KEY96_POLL done=1` | 128361852000 | 12153166 |
| 原 appFw.so 第一处只读 hook | 429229434000 | 43121412 |
| 原 appFw.so 第二处只读 hook | 429231484000 | 43121619 |
| 原 `MODEL_POWER_OFF` 发送 | 未单列 ns | 43121260 |
| 原 `scr0039_shutdown` 开屏 | 未单列 ns | 43144235 |

原 hook 对象前 12B `52 000000 11 000000 02 000000`；固件原表 `appFw.so` VA `0x41172f8` 第 17 项将 model factor `0x11` 对到 UPM factor `0x08`，名 `OFF_BY_APO1`。`done=1` 到第一 hook 为 **300.867582 guest 秒**，up 发送返回到第一 hook 为 **300.869812992 guest 秒**；后者也非真实物理键状态时间。原 UPM 16B 请求、对象 +12 字段、当前 `Power Save Start Time` 存储值、活动计时复位点均未捕获。串口 byte 顺序可能与只读 sampler 写入异步交错，因此不能靠 byte offset 为 hook 与 model send 排 guest 时间顺序。

## 原生合同及可验证使用路径

索尼 FX3 原版帮助给出 `MENU → Setup → Power Setting Option → Power Save Start Time`，项目为 `Off / 30 Min / 5 Min / 2 Min / 1 Min / 10 Sec`；无操作到期会进省电，半按快门等操作可返回。来源：[Sony FX3 Help Guide](https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000267857.html)。这是一条**自然 UI 可选设置路径**，本轮没有导航到该项、没有确认当前值、没有修改固定 English seed，也没有验证在 VM 中从 shutdown 唤醒。`Auto Power OFF Temp` 是另一设置，不能混用。

旧源码 `menu-repair-01/success-cases/source/runtime/analysis/inject-key.c:26-39` 另有手工 `--cancel-apo1` 请求，经 UPM queue `0x80920021` 发 `0x00920142/factor8`；这是历史实验注入，不是原物理键自然活动证明，当前候选未调用。旧 `menu-observe.c:4958-4990,5337-5341` 有 UPM callback 入口的观察思路，但当前源码另有缺失的 `power_notice_decode` 定义，不能直接当已可用 patch。现用 `fx3-rm-key-gate-v2-setup.inc` 把 down/up 送原 UI 队列 `0x807a0020`，自身日志明示 `original_cp_key_detection=0`。是否另需原物理键活动通知，必须先定位原生产者与消费者、消息对象及其时序；当前未证。

只读 `llvm-objdump -dr` 对原 `original-uipc/original-modules/upm.ko`（未修改）给出进一步静态候选：`k_upm_Backup_read_mss` 在 `0x688..0x6d0` 对 `Backup_read` 传 `0x00920000`、`0x0092002d`，分别存于模块 `.data+0x50/+0x54`；`k_upm_mss_apo_cb` 在 `0x730..0x800` 检查消息 `0x00920205` 与次字低 12 位 `2`，满足条件后向 `0x80920021` 发 16B `0x00920141,0x8,0x1a,0x21`。这说明原 UPM 存在独立 MSS/APO 定时链与 Backup 读点，**尚不能把两个 ID 直接等同于菜单 Power Save Start Time，也不能把该 callback 的前置条件等同本次真正发生的 UPM 请求**。`k_psave_api` 在 `0x11860..0x11a50` 另读 `Backup_read(0x00920085)` 并分派 `0x00920112/114/117/11a/11c/11f` 等命令；其具体活动复位语义尚未解出。下一步须把原设置 UI 与 Backup ID 对照，再审原物理键接收后的 UPM 命令/时间戳；仅有这些符号名及静态指令不构成活动复位证明。

原 `appFw.so` 的 rodata 另含 `sequence_mss_reload`、`Send UPM::mss_start()`、`Send UPM::mss_stop()`、`Send MSS_fakey_start(display)` 等字符串；这提供原生 App 参与 MSS 时序的静态入口线索，尚未确认各字符串的调用者和条件。所有上述离线反汇编/字符串证据与新轮真实 `OFF_BY_APO1` 对象分级存放；不能用静态名称代替本轮 UPM 命令实测。

**下一验证门：**先定位原固件活动计时复位调用和固定 Backup 对应参数 ID/当前 UI 读回；如需判定按键是否复位，用两次真正人工看图的单键，第二键在正常可见菜单且距前键不足既有期限时发，逐键保留原生事件、PNG 与同 guest clock 关机时间。不可用循环注入、人工取消 APO 或改原厂保护来制造持续可用。当前整体验收仍失败。
