# r3 有绘图、r4e/r6 零帧：离线对照

## 结论与边界

已完成冻结 CPIO 的逐成员字节核对及三份原始串口的有界解析，**未启动 VM，也未修改 guest、平台或旧候选**。最早可比的时序差异出现在首个 GPE dynamic 调用之前或附近；相同原生 screen open 路径都完成至 screen ID 0，但 r3 后续出现 UI queue 下一条发送、FillRect、GPE 返回和 OSD `0x1003` 提交，r6 在 screen ID 0 presenter 返回后的 guest 同钟约 220.216 秒内均未见这些标记。r4e 在相同节点后只观察约 1.652 秒便因外盘掉线失去日志，不能拿它证明长期零帧。r6 外盘掉线同样解释末端 QMP/路径错误，**不能倒推解释掉线前的零帧**。

原生 `FillRect` 是否完全未调用，仍不能从注入日志的缺席作绝对断言。相同 `.so` 的绑定标记存在，而 UI_FILL、GPE_CMD、GPE_RETURN、OSD commit、有效 target 同时缺席，且串口持续记录 KEY96 poll，因此“只漏掉一个绘图标记”不足以解释现象；可确认的是**观察链没有捕获到绘图调用及提交**。原生 UI 线程具体停在哪个调用、为何迟迟未生成下一条 UI 消息，仍未知。

## 可复核产物和来源

- [`compare_zero_frame.py`](compare_zero_frame.py) 流式解析两份 newc（每次读取最多 1 MiB/member），逐字节比较共同成员，扫描 marker 所属成员并抽取三份串口的 guest `ns`；输出 [`COMPARISON.json`](COMPARISON.json)。脚本 SHA256 `edc4cf592ef813d921b5c975de9ed38446dd3f10093281c9e1a04abe40361cd6`，JSON SHA256 `e895cf874ff2f0314d93b8f09c45dd878cd5c5d800ee3d48acedfbd42c38f186`；`py_compile` 与实际运行 exit 0。协调端另以原始串口独立核对相关 marker 的 raw 次数与匹配行数相同，未见同标记粘行漏计（`msg_b759aa866a5e`）。
- 输入为既有 `runs/v25diag-web-r3-91001f82/serial.log`、`runs/v25procdiag-web-r4e-6274aabb/serial.log`、`runs/v25procdiag-web-r6-9182e182/serial.log`，以及 r3 CPIO SHA `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`、r4e/r6 CPIO SHA `439f9089d3e36b6a5ee0d3f16a170a608761f315a4a2169d1d859cb0f66952db`。所有比较均是现存文件；不同轮次的 guest monotonic 不与 host 时钟相减，串口字节偏移仅用来证明顺序。

## CPIO 的实际字节差异

r3 1140 成员，r4e 1141 成员；1139 个共同成员 payload **逐字节相等**，共同成员的 newc header 字段仅 `init` 有变化。原 `init` 20733B/SHA `8ad0be3a…`，新 `init` 20840B/SHA `d8a00f8c…`；共同前缀 17071B、后缀 3662B，中间只插入以下 **107 个字节**，没有删除原字节：

```sh
 echo "$!" > /tmp/fx3-proc97-observer.identity
 /simulation/fx3-procdiag-v1 &
 echo FX3_PROCDIAG_V1_PID=$!
```

唯一新增成员 `simulation/fx3-procdiag-v1` 为 40128B ELF/SHA `057249b011acfd22a7f49885e9c6f802147099ee85dad0488f653a57dc28473a`。原 kernel、DTB、Backup、QEMU 参数与模型环境在三轮 `command.json` 对照中保持一致。原 `init` 观察者后台进程之后，这三行先保存其 PID，再后台启动 helper，最后打印 helper PID；未改变原有 shell 分支或显式等待。r4e/r6 串口分别打印 helper PID 230/229，只证明 shell 发起了后台启动。

`fx3-procdiag-v1.c:242-259` 显示 helper 打开并映射 KEY93 物理区 `0x41df00000` 的 64 KiB，每 200 ms 查看 step/done；只有 `step!=0 && step!=done` 时才采集 `/proc` 并写其保留的 `+0x9000..+0x10000` 诊断区。两轮均为 0 键，串口无 `PCDIAG_BEGIN`，因此源码路径不支持“采样写入直接覆盖绘图状态”的说法；但创建额外进程、`/dev/mem` 映射、轮询及 107B shell 启动动作可改变线程调度和启动时序，这是**未实测的机制假设**。仅凭 PID 与源码不能证明 helper 实际持续运行、无其他副作用，或它就是零帧原因。

## guest 同钟阶段和最早分歧

下表单位为 guest `CLOCK_MONOTONIC` 秒，值来自带 `clock_id=1/ns=` 或 `ns=` 的原日志；各轮内部区间可比，跨轮绝对起点和 host 时间不能混用。

| 可比观测点 | r3 | r4e | r6 |
| --- | ---: | ---: | ---: |
| GPE dynamic event 1 入口，随后原调用返回 | 16.020 | 62.038 | 24.526 |
| KEY96 首次 poll（step 0） | 20.885 | 81.274 | 45.270 |
| 原生 screen open：`0x407→0x2ae` | 31.096 | 179.975 | 157.728 |
| KEY poll 到首次 screen open 的同轮区间 | 10.211 | 98.701 | 112.458 |
| 后续 screen open ID `0x2e1`,`0x2dd`,`0` | 全部有 | 全部有 | 全部有 |
| screen ID 0 presenter factory 返回 | 38.806 | 214.876 | 220.174 |
| 首次 GPE 命令返回（r3 seq 0 FillRect） | 43.713 | 无记录 | 无记录 |
| 首次 OSD `0x1003` commit | 46.872 | 无记录 | 无记录 |
| 最后带 guest ns 的 KEY96 poll | 492.005 | 216.528 | 440.390 |

三轮的四次 screen open ID、对应 controller/presenter 返回和 `FX3_OSD_ONOFF_ACCEPT` 都有记录；r4e/r6 不是连 screen create 都未到。`AP89_SCREEN_CREATE` 注入 marker 自称 `visible_pixels_unproven=1`，不能当实际首帧。r3 的首次 `FX3_UI_FILL_EXEC` 后有 `FX3_GPE_CMD op=FillRect seq=0`、`FX3_GPE104_CMD_RETURN ns=43713083008`，再有 `FX3_OSD102_COMMIT frame=1 op=0x1003 ns=46871950000`；r4e/r6 中上述 marker 与 `FX3_OSD_FRAME_TARGET_VALID` 均为 0。r3 的 `UI_WIRE` 为 11443 次，r4e/r6 各 63 次；r3 第 63 次为 `target=0x8280074d, tag1=0x1000`，第 64 次转为 `tag1=0x1004`，随后出现 FillRect；r4e/r6 均停在第 63 次 `0x1000`，无第 64 次。这是**所比对 UI 发送序列中最早清晰的后续路径分叉**，不是第 63 次已被消费者处理的证明。

`FX3_UIPC_RECV_BEGIN` 是原 ioctl *等待前*的 observer 标记，不是 receive 完成：三轮都有 ExternalOSDIF 对 `0x8288076c` 的 begin；仅 r3 另见对 `0x8280074d` 和 `0x8280084d` 的 begin。r4e/r6 缺 begin 不能单独证明消费者死锁（该 observer 的 trylock 可丢记录），但与缺第 64 次发送及整个绘图链缺席相符。发送 `result=0` 也不能代表消费、像素提交或 UI 可见。

## 第 9 条 UI_WIRE 的原始字节与归属

三轮第 9 条均是 `target=0x8280074d op=4 tag2=0 result=0`，`tag1` 分别为 r3 `0x1000`、r4e `0xe7641000`、r6 `0xe1de1000`；原始串口该整行的 ASCII/hex 在 `COMPARISON.json` 的 `ui_wire_ninth_raw_*`，不是串口粘行造成的伪值。它发生在各轮 screen ID 0 presenter 返回之前。低 16 位同为 `0x1000`，高 16 位不同；没有原厂消息 schema 与消费者读取证据，**不能称为 native 队列损坏，也不能称为因果根因**。

采集层已核：三份 CPIO 的 `simulation/ioctl-trace.so` 均为 SHA `f2799333…`，与本项目 `helpers/ioctl-trace-v12.so` 及 `ioctl-trace-v12-build.json` 输出 SHA 相同；构建回执的源 SHA `ccf1f723…` 也与现存 `ioctl-trace-v12.c` 匹配。该源码 `:152-185` 在原 ioctl **之前**把最多 16B body 读入本地 `message[16]`；`:193-195` 调用原 ioctl 后传该本地副本给 `send_unique`；`:39-44` 从副本读 `tag1/tag2` 并打印 UI_WIRE。`n==16` 是打印前的门，故此值是 observer 的调用前 16B 快照在原 ioctl 返回后显示；不是从已释放的原消息指针在返回后再读取。此来源仍不能替代内核消费回执或判定高 16 位的原生语义。

## 外盘事件与可否定的后续实验（**仅方案，未执行**）

协调端保存的 `host-storage-20261104/kernel-r4e-disconnect-window.txt` 显示 r4e 在 06:51:36 USB 端口掉线、APFS 06:51:36.920 卸载；`kernel-r6-mount-events.txt` 显示 r6 在 07:34:40.386 卸载、07:34:42.958 重挂。用户确认没有主动触碰连接。外部存储事件解释末端 ENOENT/日志截止，却不自动解释 r6 从 screen0 后持续约 220 秒没有绘图；r4e screen0 后观察过短，不能独立支持长期零帧。

在协调端确认卷稳定并另行批准 VM 后，可使用**同一个已固定宿主 runner/同一 FX3 QEMU、kernel、DTB、English generation4 Backup、4 核 MTTCG、无 icount、同一超时/健康门**，顺序、排他地只变换 guest CPIO：A=r3 SHA `31ce79e9…`，B=r4e SHA `439f9089…`。两轮都从同一固定 seed 的独立自然副本冷启动，0 键观察到首个完整 OSD `0x1003` 或同轮 guest monotonic 达到 screen0 后至少 60 秒（总 host 有界、预留清理），分别保存 AP89 open/create、UI_WIRE 第 63/64 条、ExternalOSDIF recv begin、UI_FILL/GPE/OSD、最终 API16/进程/锁；若 storage 再掉线，该轮无效且不凭缺标记下结论。若 A 也停在 63 条/零帧，则“新增 procdiag 是必要原因”被否定；若 B 产生第 64 条及完整首帧，则“r4e 必然阻断绘图”被否定。即便 A 有帧、B 无帧，单轮也只能支持候选关联，尚不能在原 init 三行与 helper 运行/调度之间定因；后续才考虑保持新 CPIO 布局、仅禁用 helper 启动的单变量拆分，须另审，不能改原件或自动重复。

本次没有复用旧的 `LIGHTWEIGHT_RUNNING` 或源码/host 测试当 guest 活性证据；未提出放松像素身份、原 5000ms、API16 或锁门的改动。
