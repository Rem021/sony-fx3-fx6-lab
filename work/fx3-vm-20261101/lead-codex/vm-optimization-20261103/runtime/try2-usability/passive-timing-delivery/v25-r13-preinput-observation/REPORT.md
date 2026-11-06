# FX3 r13 指定步预输入只读观察候选（离线）

**结论：已实现默认关闭、仅显式指定一个合法 step 才执行的宿主观察；离线 mock/实际 runner AST 控制流验证通过。未运行 QEMU、浏览器 guest 验证或部署。** 这不是画面停更根因修复，也不更改原 FX3 guest、硬件、定时器、5000ms、API16 20s、按键/像素/健康门。

## 动机与范围

先读 [r12 停帧离线报告](../r12-frame-stall-offline/REPORT.md) 和 r12 `run_trial_v25_diag_r3.py` 输入路径。真实 r12 run `v25diag-web-r6-49f9bf9d` 最后已记录 OSD commit65 比第二键 UP down 早 **11.293614 guest id1 秒**；UP 原生接收成立，但没有足够区间状态证明某个 UI gate 分支是唯一原因。结束 bank 的 skip 3852/3918 与 a18=786 是全轮累计，不等于按键前后差分。故只在下一次经批准的运行里增加一个按键前读点，与保留的结束快照比较；不能将本观察称为修复。

## 实现与失败门

- 新参数 `--pre-input-snapshot-step N` 默认 `None`，在启动 VM 前校验 `1 <= N <= max_steps`。例如选第2键须显式传 `--pre-input-snapshot-step 2`；同一轮只选一个 step，不在别的 step 增加 QMP 命令。
- 接线位于**既有**合法输入的 `qmp('stop')` 之后、`host_step += 1` 和 `InputGate.command` 之前。选中时核既有 stop ACK，再以共用 `QmpLineTransport` 顺序 `query-status`，只接受 `running=false,status=paused`；随后先读 FDT 声明 `0x41dc00000/0x10000` UI gate，再读 `osd_ring93_v4.RingReader.poll()` 已使用的 `BASE=0x41e000000`、长度 `0x100` OSD 全局头。原 OSD reservation `0x1000000` 仅用于身份核对，**不读16MiB**。两份原始文件以 step 唯一命名，receipt 含原 stop/status/pmemsave 响应、地址、字节数、SHA256、host monotonic 起止及失败原因；不把读回的单帧或 bank 跨字段镜像称事务一致。
- 观察共用**2秒绝对预算**；每次 QMP 命令显式传剩余时间（不超过默认3秒）。宿主文件系统调用无法硬中断，前后检查预算；若原始文件或 receipt 写入耗时超预算也失败，不继续 guest 键。receipt 内的 `host_monotonic_end` 是**原始采集及预写检查结束**，成功读取两文件时磁盘 receipt 的状态刻意为 `pending_postwrite_gate_no_guest_write`；它不能自证自己的落盘耗时。只有写入返回后再次核 deadline/End/send_unknown 成功，helper 才把内存结果标 `complete` 并由 runner 记入 QMP journal；写后失败保留该待核 receipt 与原始 host first-exception，不把待核文件当成功。既有输入 stop/cont 外无额外 stop/cont，helper 不写 guest RAM、计数或原代码。
- stop 失败、send_unknown、状态非 paused、FDT 声明不匹配、QMP error/timeout、文件缺失/长度错、超预算、证据路径重复或 receipt 保存失败都在 `host_step` 增加及键写入**之前**失败。捕获中 End/信号置 `trial.stop` 后返回 `cancelled_no_guest_write`；runner 在真实 `InputGate.command` 前再检查 stop 并进入原 `finally` 清理，不额外 cont。transport 已 `send_unknown` 时仍受原有恢复保护，不能把“进入 cleanup”误写成“API16 必然成功”。
- 默认关闭时保持原 stop→InputGate.command→cont 的 QMP 命令序列。r12 PAGE 字节完全相同，除 runner 外其余21份 r12 宿主源逐字节相同；新增 helper 纳入 runner 的 `observer-source` 归档列表和本目录源冻结。

[QEMU 官方 QMP 参考](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html) 描述 `query-status` 的 `running` 与 `status`；[官方 Monitor 参考](https://www.qemu.org/docs/master/system/monitor.html) 将 `pmemsave` 定义为物理地址范围到文件的保存。具体超时、响应 ID、未知发送保护仍以本项目已固定的 `qmp_line_transport.py` 为准，HMP 通道并非长期稳定接口。

## 离线验证

`python3 -m unittest discover -s tests -p 'test_pre_input_observation.py' -v`：**5 test methods PASS**，其中失败子例覆盖 stop ACK 错/未知发送、query 错/timeout/running、HMP 错/timeout/宿主保存异常、坏长度、捕获中未知发送及绝对预算。测试从实际 runner AST 抽取输入块执行，断言默认只有 stop/cont；选中时只有 stop→query-status→两个 pmemsave→原 cont，且每条诊断 QMP timeout≤2s。两 raw 文件长度 65536/256、SHA与待核 receipt 相符；第二 step 不重采、同名重复采被拒绝。慢 receipt 写入越过2秒，以及落盘期间 End 到达均故障注入到实际输入块：无 `InputGate.command`/额外 cont，可展开至原 cleanup；捕获期间 End 也无键。AST 同时核实际输入块处于含 `restore_native_api`/`qmp('quit')` 的 `finally`；**这不代替真实 API16/进程回收验收**。[测试输出](tests/TEST-RESULT.txt)。无效 step 的 CLI 拒绝和帮助文本分别见 [回执](tests/CLI-INVALID.txt)、[帮助](tests/CLI-HELP.txt)。

## 复核与下一门

[最小差异](r12-to-r13.diff) 只有 runner 接线及新 helper；[SOURCE-FREEZE.json](SOURCE-FREEZE.json)、[DELIVERY-FREEZE.json](DELIVERY-FREEZE.json)、[SHA256SUMS](SHA256SUMS) 固定源码与交付哈希。若下一任务批准真实运行，应固定原 r12 guest/平台和浏览器输入合同，仅对选定 step 取得预输入两文件、结束两区，并按同一时钟域分别比较；第一次错误立即停键，按原 API16/quit/reap/双锁收尾。额外 QMP 读会延长既有暂停窗口，可能扰动调度；差分即使明显也不能单凭一次运行确立唯一因果。
