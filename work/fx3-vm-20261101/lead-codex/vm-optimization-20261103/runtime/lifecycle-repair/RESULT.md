# FX3 AP105 lifecycle repair：两次有界 guest 回执（2026-11-03）

## 结论与边界

在已核验 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 的 KAFU2T 上，复用原 QEMU/4 核 MTTCG、无 icount，顺序运行一次 1561.36s 修复验证和一次 263.99s generation4 冷启动。两次 guest 都有 UI、原生文件、性能、API16 恢复及退出回执；首轮 20 键、冷启 2 键，均逐键看实际 PNG 后决定下一键。修复的是注入 OSD lifetime observer 的**错误计时起点**；原厂 5000ms、guest 完成/像素门、runner 停机门均未延长或放松。当前证据不等于实机或无限期稳定，不提升 preferred/TRY2/STATE 默认入口，不发布网页。

- 旧 AP105 停机事件的 `FX3_OSD_ALLOC_DEADLINE_EVIDENCE_END` 由注入 `fx3-osd-lifetime-v2.c` watcher 输出，**非原厂内核**。原厂内核输出的是 `free_dynamic_msgq_id: QID[808261c0] M=1 C=0 S=0 A=1`。旧报告误称前者为“original”，以 [lifecycle-timeline.md](lifecycle-timeline.md) 的源码/栈/串口行时间线更正。
- 旧 observer 在原生 `osal_valloc_msg_wait` 之前登记 active 计时，再自己 `dprintf` 到串口；现场 tid838 栈在 `tty_write`，所以其 2.026s 包含自身日志阻塞，不能称原 allocator 已阻塞2s。新源码只把登记移到 BEGIN 日志与 watcher 启动之后、原 allocator 调用之前，保留 2s watcher 截止及原 runner 检测。旧现场原 allocator 最终 result0/errno0，后续 free/ACK/信号正常。
- 旧 QID c0 在同代 seq7545 的保守分配→显式完成返回上界为 5650.999ms，之后原内核释放报错；452 个“完成/释放”是外层 API 配对计数，不是内核无错证明。原 `ReceiveDrawComp` 入口/返回未直接计时，`M/C/S/A` 内核字段含义未由源码证实；既有 host 压力与 >5s 上界相关，不能单独推定是 kernel free 的唯一成因。

## 改动与定向验证

- [lifecycle-osd-v2-to-v3.patch](lifecycle-osd-v2-to-v3.patch) SHA256 `3f788d060f15af74f0d25e5de5109fff0d1e9725abd7efc5a8e19d54b5439e6a`；新 C 源 SHA `6719d72da84b37c73936d5a2dcaede956c9eb93ea2eaf00df4d4e446f4ba8453`，新 SO SHA `267629249407e7d3f319647330d45a0db73c5be0fae3b6fa302594b044f8f468`。模拟 BEGIN `dprintf` 耗时 3s 的定向 C harness：旧源码 exit134，新源码通过；新完整 wrapper host harness 通过原参数/返回/errno/send/free 检查。新候选 [build-receipt.json](vmopt-20261103-lifecycle-v1/build-receipt.json) 的 CPIO diff 仅 `simulation/fx3-osd-lifetime-v2.so`，init 逐字节相等，DTB 仅 initrd-end，CPIO 安全审计通过。原 SO/原固件未改。
- [lifecycle-runner-vs-save1800.patch](lifecycle-runner-vs-save1800.patch) SHA256 `12937d712b71c915563015d4e9115a6d83f6951e178ca8b667b9d2e86178e09c`；新 runner SHA `6c63f26a6cc30f0310c0eb6d5848530f65db288b6c621f4f5e28fd7c42a9985d`。它复用先前离线验证的非均匀扫描、增量串口和 guarded regex 候选，保留原 regex 可能命中时的完整兜底判定、错误顺序与所有 gate，并增补原内核 `free_dynamic_msgq_id` 首错停机。源 patch SHA 依次为 `5e29a27534b7c23caef6e8260f5b701f698c98229b7bfe58633c8278c218c7a6`、`1c1d6bee8053f554f311bac253a85aa0619609b7332c2ae70a2319eec37c96d3`、`801aee51037e86d74e0ad419197df60c4f858f8fcf541fc6eea0baea9fd281a4`；本地原型测试通过。`SerialSnapshot` 适用条件是此 run 的全新 QEMU 独占追加 `serial.log`；它仍保留全文，不能处理同 inode/同尾锚点原位篡改的通用情形。
- 旧 81.3MB 固定日志离线：两条原全文 re.I 检查约 3828ms，新 guarded 候选约 249ms；这只是 host 谓词测量。首轮运行的 `host-timing.json` 实录 1376 次正常主循环样本，增量读累计 123,030,123B / 9433.6ms wall，guarded 谓词累计 246933.99ms wall、单次最大 2439.267ms，`ps` 累计 9156.86ms，QMP 2397 次累计 16538.17ms。退出期新增串口字节未计入主循环读数；这些 host monotonic wall 段不可与 guest `ns` 或内核 printk 混减。


### 离线根因复现命令

从项目根执行以下已生成的定向 harness；旧版预期 exit134，新版预期输出 `LIFETIME_WRAPPER_PASS`：

```sh
D=work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/lifecycle-repair
ulimit -c 0
cc -O2 -I "$D" "$D/check-alloc-timer-origin-v2.c" -o "$D/check-alloc-timer-origin-v2"
"$D/check-alloc-timer-origin-v2"
cc -O2 -I "$D" "$D/check-alloc-timer-origin-v3.c" -o "$D/check-alloc-timer-origin-v3"
"$D/check-alloc-timer-origin-v3"
```

旧版有意触发 harness 的断言；不要把该 exit134 当 QEMU 或原固件崩溃。新候选的 CPIO/DTB 和 backup 成员差异可重跑 `prepare_lifecycle_v1.py`、`prepare_reload_v1.py` 的审计逻辑，但两个脚本拒绝覆盖现有候选目录，重跑前须在全新路径复刻脚本。

## 同源性能与运行结果

| 场景 | 实际 host 运行 | guest GPE module0x82 同代配对 | 分配返回→显式完成返回最大上界（guest 用户 monotonic） | ≥5000ms 上界 | 内核 free / unfetched / OSD marker |
|---|---:|---:|---:|---:|---:|
| 旧 AP105 save1800（失败基线） | 1415.585s 提前停机 | 452/452/452 | 5650.999ms（seq7545）；另 seq6329=5021.873ms | 2 | 1 / 0 / 1 |
| [lifecycle-v1](runs/vmopt-20261103-lifecycle-guest18-1da10e34/receipt.json) | 1561.363s（QMP 收尾 stop 于1559.803s，距1800s门限尚240.197s） | 819/819/819 | 1746.667ms | 0 | 0 / 0 / 0 |
| [generation4 冷启](runs/vmopt-20261103-reload-guest900-641917f7/receipt.json) | 263.994s，低于900s | 250/250/250 | 829.468ms | 0 | 0 / 0 / 0 |

三列“配对”是 alloc/explicit SendDrawComp return/outer release return；`performance-analysis.json` 是同一分析器从完整原串口重算，先在旧日志复现 452 与两个 >5s 上界，再计算新 run。两个新 run 的完成返回晚于外层释放返回均有 30 个同线程交错代次，但完成 **进入**已在对应释放前，且无新内核 free 错误；不把外层返回0提升为内核所有生命周期都正确。不同 run 的菜单/idle 负载与启动时刻不完全相同，表中同钟口径可比较测得区间，不是性能提升的单因果证明。原厂 `ReceiveDrawComp` 的真实入口→返回、队列内部占用与硬件路径仍 unknown。

## UI、保存与冷重载分项

1. **UI English**：首轮逐步截图见 [key-decisions.md](key-decisions.md)，step10 原 UI `Setup → Area/Date`, `Language = English`；step11 MENU 关闭，73.979s 迟到帧仍待机。RAM `0x8dd85=0`；原生 O_RDONLY 文件在菜单打开时仍是旧 `0x20`，关闭/idle 后为 `0`，观察器 generation3、SHA `29cde2080c5101ccc461ae88ad1d9fae2236ea89db450815e762f5539525c0ae`。UI、RAM 和文件证据分别保存。
2. **日期原值确认**：step17 编辑页显示 `2021-1-1`、年框焦点及底部圆形 `● OK`；step18 单次中心 ENTER 返回设置页，未改数字。Sony [控制轮帮助](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867591.html) 规定菜单中心按压确认，[Area/Date/Time 帮助](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000843992.html) 给出导航路径。step20 MENU 关闭、76.980s idle 后，原生文件观察器 generation4、SHA `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f`，两个 bank checksum 有效；相对 generation3 仅偏移 `0x20,0x2c,0x9b2ac` 三字节不同，日期字段 `0x9100c` 仍0。因此 UI 确认与自然保存代次成立，**日期语义变化不成立且本来不要求**。这里 generation 是 file observer 读回序号，不冒称原生持久化版本号。
3. **固定副本冷重载**：[冷启构建回执](vmopt-20261103-reload-v1/build-receipt.json) 把首轮 guest 原生 O_RDONLY generation4 快照复制为 `Backup-generation4-fixed.bin`，SHA 固定 `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f`，只替换新 CPIO 中 `setting/Backup.bin`；原种子未覆盖，原 init 与其余成员逐字节不变。第二轮原 `backup.ko` 在 AP bootin 前 O_RDONLY 读取同 SHA，两个 bank 的 guest RAM 均与文件逐字节相等、checksum 有效，见 `ap102-native-load-readback.json`。没有 host 写 RAM 或伪造加载。
4. **重载后 UI/文件**：[reload-key-decisions.md](reload-key-decisions.md) 的逐键迟到帧显示 `Language = English`；同次 RAM 与原生文件 language=0。MENU 关闭后 70.280s 待机截图稳定；相对固定副本，启动后文件只在 `0x20,0x2c` 头部字节变化，两个 bank 校验仍有效，language/date 字段未变。文件 observer 读回序号为2，不能与首轮序号4当成跨启动版本倒退。

## 退出与下一精确边界

首轮 QEMU PID 97817、第二轮 PID 7532 均 exit0 且 reap 后 PID 不存在；各自 `restore103-receipt.json` 在20s 规则内取得 guest ack，并验证原 API16 字节 `000b00b4fd7bbba9fd030091f35301a9`（耗时1.569s/1.303s）。两轮 `inputs_unchanged=true`，guest exception 空，宿主错误空，输出锁和原 runtime 锁均经非阻塞独立获取验证空闲。两轮完整串口 SHA 分别 `446603b250ac689a775ffaad99829a362e0e2939d4fdcdf28e475c37d5e82484` 与 `f70be58c4cfe96f7dbf7c8563813204553b032b40e9288952110880da10f96a3`。无相机、USB、物理 SD 操作，无原件/历史 run 覆写。

本次允许范围内的实际阻塞已由 observer 计时修复并经更长同链运行不复现；**仍未直接观测原 `ReceiveDrawComp` 入口/返回及内核 QID `M/C/S/A` 内部状态**，所以不能宣称旧 `free_dynamic_msgq_id` 的唯一底层成因已被证明，也不能把本次有限样本当无限期或实机验收。更长运行的 guarded 全文谓词仍有 246.934s 累计 host wall 成本，若继续扩展压力测试，应在保留错误检测前提下对这一段再定向优化。主协调需审阅本目录源码/回执并决定后续 TRY2/网页验收；本工人未提升任何入口。
