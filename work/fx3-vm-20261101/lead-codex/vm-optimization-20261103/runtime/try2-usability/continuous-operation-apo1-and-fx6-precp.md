# 连续菜单操作 APO1 与 FX6 pre-CP 短轮（2026-11-03）

## 结论

FX3 原生菜单实际显示 `Power Save Start Time = 5 Min`，未修改设置。27 次逐键查看 PNG 的菜单操作均获原输入队列 down/up 和 guest step done，但原 `appFw.so` 在最后一次 DOWN 释放后 **11.870847008 guest monotonic 秒**收到 `OFF_BY_APO1` 对象。该次不是最后一键后无操作五分钟；原物理键到 UPM/MSS 活动计时复位的消息合同仍未闭合，因此暂停 31/32 键和下一轮 FX3，不注入臆测的 reset、不改计时值或屏蔽电源机制。FX6 Image-only 短轮只到固定 FX3 CP helper 的已知绑定拒绝，未通过 FX6 CP/AP/AV。

## FX3 同钟时间与可见画面

- 完整可复现提取器为 `src/analyze_27key_apo.py`；结果 `continuous-27key-apo1-evidence.json` 逐项保存 27 键、原生接收、guest 发送时刻、截图 SHA、宿主发送到取图间隔、决策文件、原 hook 与资源回执。原 serial 为 `runs/try2powerinternal-71ffcdef/serial.log`，80,977,079 B，SHA256 `143421ac90476b9032f5de4331df48c046d7abeab4e72c590198b4283b737e6f`。运行候选 SHA `d53363f076f5d0129c68e7489d407b0baab300bec62f487decf96a73e29d90a6`；v10 runner SHA `a1072dc1456c67bcd376c57fe6c17e622c6882d2410de25f4dd111cc147be4dd`。
- 前 10 键从待机打开 Setup，逐图进入 `Power Setting Option`；`runs/try2powerinternal-71ffcdef/internal-preview-11.png` SHA `5c3394a262559b4b4331a97979660e45ce06325ee3447cf57c92780aa90638ac` 清楚显示 `Power Save Start Time 5 Min`、`Auto Power OFF Temp. Standard`。第 11 键 MENU 取消，第 12 键重新打开，随后类别导航至 Shooting 的 `TC/UB`，未进入设置值编辑。第 27 键后图为 `trial-step-27-key-030.png`。每一键之前均有图像工具实看前一 PNG，手工记录当前页及理由；没有预排导航。
- 27 键均为合成 20B 到原 UI 队列 `0x807a0020`，每键一次 status 1、一次 status 0，`FX3_KEY_INPUT_RECV` 各一次、`FX3_KEY95_STEP_DONE` 各一次；这只证原 UI 接收/步序，不证真实物理键活动链。最后 up 的原 `FX3_SYNTH_KEY` 为 guest ns `751888634000`；原 appFw hook seq1 为 guest ns `763759481008`，同钟差 11.870847008 秒，raw12 `520000001100000002000000`，factor `0x11` 经原表对应 `OFF_BY_APO1`。seq2 在 ns `763771785008`，同一对象。第 13 键 LEFT up 为 guest ns `461599402000`，到 hook 为 302.160079008 秒；该相近 5 分钟关系提示检查活动复位条件，**不能作为独占根因证明**。host monotonic 与 guest monotonic 不相减，内核 printk 秒亦不混入上述差值。
- 第 28 键只有在查看前图后写入待处理请求，原生 APO1 在 runner 消费之前被发现；无 step28 发送或接收。过期截图请求曾被 v10 拒绝，未计入按键；新请求按当时图像重看后才发送。当前轮 `key_steps=27`，31/32 guest 边界未通过。
- 原 runner 首错立即停，`receipt.json` 为 `health_failure/native_model_power_off_observed`。QEMU PID 74946 exit 0/reaped/absent，API16 1.557 秒内 guest ack 并核验原字节恢复，输入源 hash 未变，两锁释放；停止在黑屏之前的 render 非全黑状态，**不是长期可用通过**。真实浏览器 host 本轮一次恢复探测返回 `The browser access host is unavailable`，无网页逐键/按钮解锁验收。

## 原生静态路径与尚缺的合同

原 `original-uipc/original-modules/upm.ko` 未修改。其 `k_upm_init_mss`（`.text+0xd58`）注册同步消息队列 `0x80924220` 并向该队列发初始化 `0x00920118`；紧邻 `k_mss_dump_all` 后的原分派（`.text+0x2180` 起）识别 `0x00920204`，符合特定状态条件时调用 `k_mss_reload_timer_nr`（`.text+0x1608`，stop、标记 request、find minimum、start）。这证明原 MSS 有复位入口及状态门，**尚未证明任何 UI 键自然发了该请求或本轮 consumer 运行时序**。本次 serial 的 `FX3_UIPC_SEND_UNIQUE` 只保留首见签名，见 `0x00920118` 和 `0x00920202`；不能据此断言其后没有重复消息。原 `appFw.so` 的 `sequence_mss_reload` 与 `UPM::mss_start/stop` 字符串是入口线索，不构成运行态调用证明。

进一步只读原 `appFw.so` 指令，`sequence_mss_reload::run()` 的日志字符串在 VA `0x39384a8`，函数入口约 `0x2d35168`；`0x2d35180 → 0x2de0294 → 0x2eb4f24` 原 call 链最终把目标 `0x80924220`、word0 `0x00920204`、word1 从原全局 `[0x9ab0c18]` 读取、word2/3 均 0 交给 `0x2eaf294`。后者原指令使用 `osal_valloc_msg_wait` 分配 16B、`osal_set_msg_src`、`osal_snd_sync_msg`、`osal_free_msg`；源 ID 参数也是该全局值。该链给出**原 sequence 的消息构造合同**，但还没有真实物理键触发该 sequence 的条件，也没有本轮逐键运行时调用回执。旧 `ioctl-trace-v12.c` 的 UNIQUE 观察器只有 256 项、会去重且可 capacity/lock drop，故其未打印 `0x00920204` 并不是运行态缺失的可靠负证据。`original-appfw-mss-string-xrefs.json` 仅记录原 ELF 精确 ADRP+ADD 字符串交叉引用搜索，零结果不代表函数不存在；上述调用关系由明确的原指令逐跳核对。

当前合成输入适配 `src/fx3-rm-key-gate-v6-long-use.inc` 自报 `synthetic_input=1 original_cp_key_detection=0`，发送至 `0x807a0020`，不承担原物理键通路已闭合之证明。下一步要从原 key 生产者、UPM/MSS 消费者及其消息状态门找出完整活动通知合同；用只读观察确认 27 键中的哪些事件实际到达复位入口及 timer 到期点。只有因果确定后，才在独立 FX3 修复候选中让一次真实用户键对应一次原生活动通知，并先做原指令/负例离线检查，再受控逐键复测。原 5000ms、自然 APO、像素及生命周期失败门保持。

## FX6 独立短轮

`early-kernel/fixed_runner.py` SHA `312f134f6774fcf8b818b4038ec5e2af2491be90dd5ac4f513e349de17a9dc29` 的 `--check` 通过完整固定平台 hash，唯一固件载荷变化为 FX3 原 kernel Image → FX6 原 Image。双锁 free 且无其他 QEMU 后，唯一运行 `early-kernel/runs/fixed-fx3-4571c53b` 以 `--mode pre-cp-first-result --seconds 180` 启动，实际 2.811 host 秒，PID 80035 exit 0/reaped/absent，serial 81,287 B SHA `dfd0ef290ff0ea0c07335682f3e5a68b0ee5f626d41034a927a7031342df2be8`。原 `devno/osal_utm/osal_uipc` 模块返回 0，LDEC103 guest exact/拒绝自检返回 0，FILE100 原文件 O_RDONLY 读取和 FILE103 observer ready；随后固定 **FX3** `fx3_cp_backup_sync100_v4` 两次 `FX3_SYNC100_DISABLED reason=binding_failure`、原 initcall `returned -7`，最终 `FX3_BACKUP_CP_INSMOD_RC=7`、`OWNER_FAILED`。轮询并非 CPU 断点；未见 kernel fault，但没有 CP/AP/AV、菜单或实机通过。完整命令、串口与收尾在该 run `run-receipt.json`。

FX6 run 后独立 `flock(LOCK_EX|LOCK_NB)` 检查两把原锁均 free，文件均 0B、SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`；`ps -p 80035` 无进程。没有后台 guest 占锁。FX6 原固件与固定 FX3 平台文件均未改，旧 TRY1/TRY2 用户入口未提升。
