# FX6 AP 三入口包：唯一零键真实观察（2026-11-03）

**结果：首个真实故障，未通过。** 固定 FX3 QEMU 平台上，`FX3_TRACE_ABI_VERIFY_RC`、`LIST_RC`、`TRUE_RC` 均为 0；四条精确 FX3 原地址观察器拒绝按合同单列，不作为本轮首故障。此后串口在 `FX3_PROVIDER_REQUEST destination=0x92840747` 紧接着出现 `assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075` 和 `send_and_wait_cmp_i(...)`，host 分类器在原日志第 15598 行立即停轮。不能据 loader 0、`im.elf` 映射或 appFw 栈帧声称 FX6 AP ABI、菜单或系统迁移成功；请求未见有效 reply，导致 assert 的确切 ABI/队列原因尚未知。

## 固定输入与运行边界

- 启动前卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、无其他 QEMU、原两把锁 free；独立调用 runner `verify()` 成功重算完整 1,140 成员，只容许 `bootin.elf`、`im.elf`、`appFw.so` 三项固定 SHA/长度差异，其余 1,137 项一致。runner SHA `aaa9ca518d580fde7ca9fdbf2c33bebe78545d96876f997168643f33bdf4a24a`，三入口 CPIO SHA `bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02`。
- [command.json](command.json) 固定 34 个 QEMU 参数，只在 index 20 将 serial 指向本轮新文件、index 31 将 initrd 指向本三入口 CPIO；原 `/init`、DTB、内核、FX3 模型、环境、Backup、17 helpers 未变。观察阶段零按键、零 `FX3_SYNTH_KEY`、零人为 IPC，无新 probe/keepalive；收尾的 API16 恢复请求单独列证。未操作相机、USB 或物理 SD。
- [serial.log](serial.log) 1,980,840 字节，SHA256 `7fd297d60c72a1211fa44a0103ae69fabec0c72c422be6c34519c2636db3a43f`。[analyze_fault.py](analyze_fault.py) 只读重算 [fault-context.json](fault-context.json) 的字节范围与分类。

## 原串口次序与归属

| 顺序 | 原字节范围（半开） | 观察 |
|---|---:|---|
| loader verify/list/true | `84978..85003`、`86536..86559`、`86561..86584` | 三项 RC 都为 0；后续非零仍会被门截停。 |
| 原生进程/映射 | `FX3_AP_NATURAL_BOOTIN_BEGIN` `97267..97294`；`im.elf` 映射始于 `138946` | 只证明 bootin 及映射阶段。 |
| 四条旧 FX3 观察器拒绝 | 原日志行 7358、7359、7361、7363 | `MEDIA` getter code、`UI_GATE` instruction、`TIMER` prefix、`PRESET_CONTEXT` original word；仅四条精确文本被允许作为“未绑定”诊断。 |
| appFw 路径 | profile stack begin `1970482..1970574`、end `1971602..1971648` | TID716 栈内有 `/usr/lib/appFw.so` 相对地址；供体 `appFw.so` 含该 assert 源字符串，但这不证明完整 AP 入口合同。 |
| adapter 捕获请求 | `1971713..1971849` | `FX3_PROVIDER_REQUEST destination=0x92840747 bytes=10 source=0x81cf6196 raw=0d202d030a0001800000 dispatch_pending=1`。这是既有 CAPID helper 观察日志，不是内核消费/回复。 |
| **首故障** | `1971849..1971906`，函数行 `1971906..1972014` | `assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075`；`send_and_wait_cmp_i(OSAL_ID, const void*, int32_t, void*, int32_t)`。紧邻请求但不能只凭邻接断定因果或缺失的具体 reply。 |

`fault-context.json` 保存完整原行、byte offsets；`receipt.json` 的 `serial_health_failure` 明记 line 15598、kind `real_fault_or_unproven_guard`。四条旧观察器拒绝与真实 assert 分开，未宽泛忽略 `FAIL`/`REJECT`。`FX3_BOOT_QUEUE_SEND` 和通用 GPE/OSD 标记也没有被拿来认定 FX6 AP 成功。下一定向工作应静态追 `0x92840747` 请求所属原生服务/expected reply、供体 `send_and_wait_cmp_i` 断言条件与 FX3 helper 的拦截边界；尚不能改队列、伪造应答或降低健康门。

## 收尾和未验

[receipt.json](receipt.json) 记总 host 42.734s（观察限 120s、全程限 180s）、`stop_cause=first_health_fault`、`host_error=null`。guest stop 后 20s API16 规则内 1.312s 收到 ack 并读回原 16 字节 `000b00b4fd7bbba9fd030091f35301a9`；QEMU PID48937 exit0、reaped/absent，原平台及输入 SHA 未变，两把锁在回执与独立 flock 中均 free。当前没有 QEMU 留占锁；本轮不重试，不改原件/种子/用户入口。FX6 AP 完整装载、ABI、菜单、IPC 回复、FX6 系统及实机功能仍未验。
