# FX3 两轮 APO1 现有证据差分（2026-11-03）

**结论：已将可能决定五分钟截止的最后可见事件缩小到 27 键轮第 13 键 LEFT 及其后原 app 的 20B 消息；还不能断言该消息使 UPM 定时器复位。** 第 14–27 键全是 DOWN，均获原输入队列接收、原 app 队列发键及画面反馈，但原生 `OFF_BY_APO1` 对象在第 27 键释放后 11.870847008 guest 秒出现。两 MENU 轮的完整 serial 未记录该 20B 消息，仍在末次 MENU 释放后 300.198700992 guest 秒关机，表明不能把 20B 消息当唯一复位通道。本任务未运行 QEMU，未注入 `0x00920204`，未改 Backup、超时、原件、旧候选或 TRY2 入口。

## 输入、时钟与复现

- 在本目录执行 `python3 analyze_existing_runs.py` 可只读重生 `existing-runs-differential.json`：生成器校验两条原 serial SHA，重新核对每键一次 down/up、原 receive 各一次、done 一次、PNG SHA，再从原串口提取 app 队列发送、MSS 与电源通知；仅输出文件会被重写。第 27 键轮 serial SHA256 `143421ac90476b9032f5de4331df48c046d7abeab4e72c590198b4283b737e6f`（80,977,079B）；两 MENU 轮 serial SHA256 `cab0891be83fa46d2f16096ba2d7f354609289357d21b5e2d70fde2f4d594ada`（40,898,502B）。
- 两轮固定 English generation4 Backup SHA256 `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f`。27 键候选 SHA256 `d53363f076f5d0129c68e7489d407b0baab300bec62f487decf96a73e29d90a6`；两 MENU 候选 SHA256 `6dd9fee185c4ea1a8859a70cca19a3af7f5c6d8d0280f849fc60afd21eba30b4`，后者 CPIO 仅换被动 MSS observer so，init/seed不变、DTB 只调 initrd end。两轮都用4核 MTTCG、无 icount；诊断 so 差异及运行负载意味着不能把两轮当严格同代码 A/B 计时实验。
- `FX3_SYNTH_KEY`、`FX3_KEY96_POLL` 与 `FX3_POWER_NATIVE_NOTIFY` 的 `ns` 均来自 guest `CLOCK_MONOTONIC`，仅这类值相减。20B boot 消息本身没有 ns；其附近同钟 poll 只是**串口输出顺序的邻近样本**，不能升级为精确发送时刻或严格界限。第13键后相邻 poll 到 power hook 分别相差 301.150051008/300.140225008 秒，数值上与五分钟相容，却没有原消息的真实时间戳或 UPM consumer 证明。宿主运行时长与 guest ns 不互减；内核 printk 时间单列。

复现器 SHA256 `393e5aae256d9a718b7a24dd6b75a486c83e17cbd1aa5cd46ddf1c31ff0ab29a`；当前生成 JSON SHA256 `23900be3e83bd18e82e36c074602a62a554a0a3f193f7537a5605d76b76f7016`。原指令摘录 SHA256 `851a0c897716391ab02d86c99ff641a6e553ef2179601b5704a208a7519ed991`，vtable 原字节证据 SHA256 `af77db49313f605c11b81a822a45e250e2fcc2256a064afc6e5e36cc12876ae5`。

## 最后可见候选事件

| 轮次 | 最后相关原生 UI 操作/候选 | guest 同钟比较 | 范围 |
|---|---|---:|---|
| 27 键 `try2powerinternal-71ffcdef` | 第13键 LEFT，up `461599402000` ns；从 `Setup > Power Setting Option` 右侧 `Power Save Start Time 5 Min` 橙焦点退到左侧类别栏 | 到首个 power hook `763759481008` ns：**302.160079008 秒** | 第2键 LEFT 在 `Setup > Area/Date` 做相同右→左焦点转移；两次 LEFT 后各有一条相同的 20B app→boot 消息。 |
| 同轮 | 第13键后 20B `0100150001000000050000000000000000000000`，源 `0x830128`、目标 `0x5503e0`、原 app 调用返回点 `0x16f12ec` | 附近 guest poll `462609430000` / `463619256000` ns；不能把此区间当原消息精确时戳 | 该消息是最后一种在 14–27 中没有重复出现的已捕获事件；是否触发 UPM 仍未知。 |
| 同轮 | 第14–27键均 DOWN，从 Setup/Sound 经 My Menu、Main 到 Shooting/TC/UB；第27键 up `751888634000` ns | 到 power hook仅 **11.870847008 秒**；14键跨 262 秒，最大相邻键空档 **50.821067008 秒** | 所有 DOWN 都到原 UI，非 host 未发送/未消费；省电计时是否把这些 DOWN 视为活动未知。 |
| 2 MENU `try2mssinternal-a1d8f68a` | 第2键 MENU 关闭英文 Setup、回待机；up `131782332000` ns | 到首个 power hook `431981032992` ns：**300.198700992 秒** | 本轮 serial 未记录上述 20B 消息；原 app MSS 序列只在启动约44.4秒执行两次，MENU期间未再执行该已挂点序列。 |

第13键前图 `runs/try2powerinternal-71ffcdef/internal-observe-13.png` 清楚显示右侧 `Power Save Start Time 5 Min`；后图 `trial-step-13-key-015.png` 显示左侧 `Power Setting Option` 橙焦点。第2键前/后 `internal-observe-02.png`、`trial-step-02-key-015.png` 显示同类右→左转移。第14键后 `trial-step-14-key-030.png` 已到 `Sound Option`；第27键后 `trial-step-27-key-030.png` 为 `Shooting > TC/UB`。这些 PNG 均已实际用图像工具查看；没有改设置。两 MENU 轮 `trial-step-01/02-key-1ab.png` 分别显示打开 Setup 与回待机，原先定向轮亦逐图查看。

第 13 键的原始记录为 `key=0x015/LEFT`、`down=461452201008 ns`、`up=461599402000 ns`，按键前为右侧 `Power Save Start Time = 5 Min`，按键后为左侧 `Power Setting Option`。下表的间隔只以同轮 guest monotonic 的**上一键 up 到本键 down**计算；“前→后”来自逐键 PNG/下一键前观察，完整原始页面文字、截图 SHA 与 `FX3_KEY_INPUT_RECV` 对数见 JSON。每一行均是当前适配发出的 `src=0x00410025` 20B DOWN down/up，原 `libObj.so` 接收各一次、step done 一次，且有实际 PNG；14 张后图与各自上一张 SHA 均不同，不是物理 CP/FRONT 输入。原 app 32B DOWN 消息在整个 27 键轮合计 42 条，对应 21 个 DOWN 的 down/up 总量；异步串口输出在相邻键边界有交错，**不能把每键的两条 32B 严格逐一归属**。

| 键 | 与上一键间隔 guest 秒 | 原生菜单焦点前→后 |
|---:|---:|---|
| 14 | 28.074 | Setup / Power Setting Option → Sound Option |
| 15 | 13.961 | Setup / Sound Option → USB |
| 16 | 11.910 | Setup / USB → External Output |
| 17 | 12.974 | Setup / External Output → Setup Option |
| 18 | 13.434 | Setup / Setup Option → My Menu Setting |
| 19 | 28.506 | My Menu Setting → Main1 |
| 20 | 31.529 | Main1 → Main2 |
| 21 | 50.821 | Main2 → Shooting / Image Quality/Rec |
| 22 | 26.998 | Shooting / Image Quality/Rec → Media |
| 23 | 12.753 | Shooting / Media → File |
| 24 | 13.904 | Shooting / File → Shooting Mode |
| 25 | 19.779 | Shooting / Shooting Mode → Shutter/Silent |
| 26 | 12.485 | Shooting / Shutter/Silent → Audio Recording |
| 27 | 11.388 | Shooting / Audio Recording → TC/UB |

## 输入来源与原 consumer 的确切界线

- 当前适配 `fx3-rm-key-gate-v6-long-use.inc` 用 OSAL 分配/发送同样的 20B `<key,sub,status,ex,from>`，`dst=0x807a0020`、`src=0x00410025`，每次 down/up 各一次、100ms，日志明确 `synthetic_input=1 original_cp_key_detection=0`。27 键原 `osal_rcv_msg_tmo` 包装器在原调用成功后记录 `FX3_KEY_INPUT_RECV` 各27次 down/up，`FX3_KEY95_STEP_DONE` 各一次；两 MENU 各2次。原 `libObj.so` 在 `0xcb640..0xcb7a0` 接收 20B、`0xcbb40..0xcbb5c` 转发内部记录，`0xc90b8..0xc9140` 进入原 EventThread；原 `appFw.so` `0x16ef2a0..0x16ef334` 注册回调。原 app 送 `0x5503e0` 的 32B 键事件在27轮计数为 MENU 6、LEFT 4、RIGHT 2、DOWN 42，恰与各键 down/up 数吻合；2MENU轮有 MENU 4。这些 `FX3_BOOT_QUEUE_SEND`、`FX3_KEY_INPUT_RECV` 文字**由注入的只读 OSAL wrapper 打印**，观察对象是原调用/缓冲，不能称原厂日志。画面变化另证 UI 确实处理输入。
- 原 `input.ko` `.text+0x12f0..0x13e0` 与原 CP `cpapp-b.bin` `0x49b920..0x49b94a` 为两个物理生产者；前者以 `0x00410025` 发送原格式消息，未定义符号包含 OSAL 发送但没有直接 `upm`/`mss` 符号。当前软件适配从 OSAL 20B 处进入，**绕过** CP/FRONT/ADC 原物理取样；因此 UI 收键不能证明原物理活动复位链走全。证据文件 `original-input-chain-disassembly.txt`，并复用 `lead-claude/audits/key-input/key-input-proof.json` 的固定原件 SHA/重定位/CP Thumb 原址；后者是先前离线审计，本轮仅定向复核相关原指令。
- 两条特殊 20B `FX3_BOOT_QUEUE_SEND` 只在第2/13 LEFT 后出现，均从 TID368、source `0x830128` 到 `0x5503e0`；原 `appFw.so` `0x16f11e8` 分配20B、`0x16f12b8..0x16f12c8` 拷贝调用者内容、`0x16f12cc..0x16f12e8` 设置 source 并调用原 `osal_snd_msg`。该 wrapper 是**泛型发送器**，日志没有它的 guest 时间、下游消费或 UPM timer 更新。2MENU 轮 serial 未记录相同 20B，故不可能凭这两轮称其为唯一必要的活动通知。
- 原 ELF `.data.rel.ro` 中 vtable VA `0x41cc480` 的 RTTI 指针为 `0x41cc438`，其 name 指向 `.rodata` VA `0x2f9a2c0`、mangled `3App`；slot VA `0x41cc4a8` 指向上述 `0x16f11e8`。这把发方精确归于原 `App` 类的虚方法，不提供 `0x00150001` 事件的业务含义。复现时须按各 ELF section 的 VA/文件偏移换算：`.data.rel.ro` 偏移为 VA−`0x10000`，`.rodata` 偏移与 VA 相同。逐地址原字节读数见 `original-app-vtable-evidence.txt`。
- 原 `upm.ko` 静态存在 `0x80924220` MSS 队列、`0x00920204` 条件 reload 分派、`k_mss_reload_timer_nr` `.text+0x1608`，另有 add/del request/stopper 与 power save/API 路径。两 MENU 轮只读探针在启动时见原 `sequence_mss_reload::run` 两次，MENU 没有新增该 app 序列；这**不排除**原 CP、boot 队列或 UPM 内部的其他更新路径。`0x00920204` 的实际 UPM consume/状态门、其他 timer 更新 API 及 20B `0x00150001` 下游归属待 Gemini 独立原指令核对，本轮不生成行为补丁或猜测注入。

## 关机类型与验收门

| 轮次 | 原生事件 | runner/工具动作 | 解释边界 |
|---|---|---|---|
| 27键 | 原 app 电源对象 raw12 `520000001100000002000000`，第2处 hook同对象；原表 factor `0x11` 映射 `OFF_BY_APO1`，原 screen 自然进入 `scr0039_shutdown`，并有原 28B power-off queue send | `stop_cause=health_failure/native_model_power_off_observed`，宿主 **770.133s < 1800s** 上限；第28请求尚未被消费，实际仅27键；QEMU PID74946 exit0/reaped/absent、API16恢复、输入SHA未变、双锁释放 | 原因不是工具主动到时；对用户连续导航而言是**未预期中断**，但是否违反原省电判定仍未证，不能叫渲染崩溃。该轮 `render_pass=true` 仅因早停取到非黑帧。 |
| 2MENU | 同 raw12 与原 shutdown/queue 事件 | `health_failure/native_model_power_off_observed`，宿主 **437.766s < 1200s** 上限；实际2键；QEMU PID86695 exit0/reaped/absent、API16恢复、输入SHA未变、双锁释放 | 最后 MENU 后约300s且无进一步输入，**符合自然闲置省电的可能性**；仍没有计时器内部证明。该轮 `render_pass=false` 是关机期黑帧结果，不能单以它诊断独立绘制故障。 |

Sony [原版 FX3 帮助](https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000267857.html)说明 `Power Save Start Time` 的选项包含 `5 Min`，并以“未进行操作”描述省电条件；它没有逐一规定菜单方向键如何计入活动。可见页面值、原 power factor、工具健康门是三种不同证据。**下一可验证最小差异**是只读对照 MENU、右→左 LEFT、类别 DOWN 在原 app/boot/UPM 的实际消费与计时更新，不在用户操作时发送未经证实的 `0x00920204`，也不改变原厂时限。若原生静态/运行合同最后证明某些键本来就不延时，应在试用说明中明确 5 Min 省电与可通过设置页自然选择原厂选项，而不是伪装画面常亮；本轮没有作出这个判定。
