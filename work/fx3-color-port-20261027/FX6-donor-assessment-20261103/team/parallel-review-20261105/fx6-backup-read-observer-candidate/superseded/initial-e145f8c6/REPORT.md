# FX6 AppFw two-key Backup read observer candidate

- Task：`task_e0f4f68af4d4`
- Dispatch：`ctx_1ffa7ba88ade`
- Status：**HOST_ONLY_CANDIDATE_READY_NOT_RUN**
- 只写本目录；未启动/连接任何 VM、browser、server、QMP、guest 或现存进程；未修改固件/平台/Backup/CPIO/辅助库/旧 observer/运行政策。
- 本目录是新候选，不复用旧授权或旧 run；旧 `first-ap-readonly-observer` 只读参考。
- 输入 10 项前后 hash 不变（`receipts/input-compare.json`）。

## 1. 目标与精确地址

目标候选固定为当前 target `grmreal46` CPIO（SHA `3a08f89d89cfc6db8b12158a0a1147410e42d98713c445c3c38c07eefad8d03b`），AppFw `appFw-future-skip.so` SHA `b1fe2274e19d50b6d7ee12886dc233a742358772383f5cf79523de15cf0b55be`，serial `377142e9dcee7f4f7728db6e9fcb822a9f3e501e61da7f719761d4d506f5050e`。

当前已封存 ELF/反汇编重新核实的两个 key thunk/callsite：

| key | thunk VA | exact return VA | frame slot | capacity |
|---|---:|---:|---:|---:|
| `0x02cf0214` | `0x2169784` | `0x11f67d4` | `x29+0xb4` | 4 |
| `0x02cf0218` | `0x21697d4` | `0x11f67f4` | `x29+0xc4` | 4 |

- thunk 原文：`e10300aa`（`mov x1,x0`）；随后 key/size 设置并 tail `b Backup_nread@plt`。
- 当前 target serial 的完整 epoch5 map（fixture）给出 bias `0x7ed3ccc000`；这是**当前观测值**，candidate 每个未来 run 必须从**该 run 的完整 early maps**重新计算，绝不复用该值或旧 ASLR。
- 旧 observer 的 CAPID/AP 地址 `0x1e730`/`0x20ef7a0`、历史 bias 均不进入本候选成功条件。

## 2. 两阶段身份与只读合同

1. **Stage 1（当前 serial）**：只接受完整 `FX3_AP_EARLY_MAPS_<pid>_<epoch>_BEGIN/END` 块，且同一 block 中 `/usr/lib/appFw.so` 的每个原 ELF PT_LOAD 都有对应 inode/页对齐 offset/start；取最新完整块，计算 bias。没有完整块/多 bias/混合 inode -> unknown 停止。
2. **Stage 2（live CPU）**：首个 entry hit 前从当前 vCPU 地址空间读取 AppFw ELF header（64B）、完整 PHDR、四处原机器字（两个 thunk + 两个 return）；必须逐字等于 pinned target ELF；否则 unknown，不读数据。
3. entry hit 要求：
   - `PC == bias+thunk_va`；
   - `x0 == x29+slot_off`（buffer 就是该 key 的 4B 局部槽）；
   - `x30 == bias+return_va`（精确 callsite，不接受 thunk 的其他调用者）；
   - TID/stop 为严格 `T05thread:...`；TLS 由只读 sysreg reader 提供，不可得则 unknown。
4. 记录 entry 前 4B；把该 thunk 的 `Z1` 替换为 exact return 的 `Z1`（最多两个同时断点）。
5. return hit 要求同 TID/TLS/`x29`、`PC==exact return`、return 原机器字匹配；记录 `w0`（有符号/hex）和 after 4B；删除 return `Z1`。
6. 只允许 `g/p/m`、`Qqemu.PhyMemMode:0/1`、`Hg/Hc`、`Z1/z1`；禁止 `Z0`、`M/G/P`、软件单步、写寄存器/内存/指令、keys、patch/stub/veneer/断言删除。
7. cleanup：QMP stop -> 对残余地址逐个 `z1` -> 关闭 RSP -> 只停/退/回收自有 QEMU；若任一 `z1` 失败，保持暂停、保留 residual、退自有 QEMU，`API16_restored=false`，绝不带残余断点恢复执行。本候选**不执行**旧 observer 的 API16 8B 清理写，因为本 observer 不修改 guest 代码；`z1` 即可移除硬件断点。

## 3. Baseline 逐项绑定

`observer/baseline_binding.py` 读既有 frozen baseline SHA `854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669`：

- QEMU、kernel `vmlinux.bin`、DTB、CPU/memory/accel/model-env 及 baseline `sha256` 5 项逐项核验。
- 34 项 argv 中**只有 index 31**（initrd loader）从固定 baseline 的 guest CPIO 替换为 target `grmreal46`；其余 33 项逐字相同。
- 固定参数：`-machine virt,gic-version=2,secure=off`、`-cpu cortex-a35`、`-smp 4`、`-m 5120`、`-accel tcg,thread=multi`。
- 没有放宽旧 CPIO hash，也没有继承旧 three-entry `bb618bd2…`；target CPIO 是 `3a08f89d…`。
- 回执：`receipts/baseline-binding.json`。

## 4. 默认禁用入口与未来 RUN-PLAN

- 默认 `python3 observer/run_candidate.py` -> **DISABLED**，exit 2，不启动任何东西。
- `--plan --serial <new-serial>` -> 仅输出当前 map 派生的 breakpoint/预算计划，no VM。
- 只有显式 token `APPROVE_GRMREAL46_TWO_KEYS_0214_0218` **且新一轮运行单独批准**后，才允许审阅 future runner；本 host-only 候选**故意不包含 execution adapter**，不会自行 Start。协调器/用户批准后仍需接入已审 runner；本文件不是运行授权。
- 提议预算：一次 Start、零键、观察 <=150 s、总 <=180 s、最多 2 个同时 `Z1`、最多 4 个 entry/return hit、8 个 stop、16 次 4B 数据读、identity 读取 <=128 次 4B；任何预算/身份/TLS/读/return 不符 -> unknown 停止。
- 完整命令/清理/风险见 `RUN-PLAN.md`。

## 5. 离线验证

`tests/test_host.py` -> `PASS_NO_QEMU_FAKE_RSP`，12/12：

- 当前 epoch5 map（pid237/bias `0x7ed3ccc000`）与两个 key 的 entry/return 捕获（fixture 值）；
- 旧 ASLR fixture 在 live identity 下拒绝；
- 错误 ELF header/PHDR/原机器字拒绝；
- 错误 entry LR/PC、错误 return frame、错误 return TID、错误 return call 拒绝；
- read failure、time budget、残余 `Z1` cleanup 可见且 `guest_resumed=false`、无写。
- 明确标注：`fake RSP + target serial map + target appFw bytes; NOT real CPU/menu`。这些是离线测试，不是 CPU/菜单证据。

## 6. 与旧 observer 的差异

见 `DIFF-NOTES.md`。关键：旧 observer 用 three-entry `bb61…`/CAPID/AP、旧 appFw `a1c5…`；本候选用 target `3a08…`/`b1fe…`、两个 AppFw key thunks；旧 observer 收尾有 API16 8B 写，本候选**只 z1、不写 guest**；旧授权/旧 ASLR/旧 run 均不继承。

## 7. 可回答/不可回答

**可回答（若未来获准运行且通过身份）：**

- 两个 key 的 entry buffer 指针、capacity 4、entry 前 4B；
- 实际 return `w0`（signed/hex）、return 后 4B；
- 是否同 PID/TID/TLS/`x29`/精确 callsite 配对，两个 callsite 是否各命中一次；
- 是否出现 `w0` 非零/assert 输入等直接 CPU 证据。

**不可回答：**

- `0x3e014d` 的 receiver/OSAL callback 或 `92fe` 是否就是 appFw 来源；
- 数据语义、FX3 共享消费者、boot/menu、生产链责任；
- 任何迁移/修复是否有效；本任务不生成数据候选/Backup/CPIO。

## 8. 风险

- QEMU TCG 硬件断点行为/当前 QEMU 二进制需未来运行时重新核验；本轮回执不证明运行时可用。
- `x0`/`x29` 若不符合 slot 关系即 unknown；thunk 若被其他调用者共享，exact LR/return PC 过滤可避免误认，但也可能错过目标（unknown，不是成功）。
- TLS/sysreg 读取不可用 -> unknown；无法用 frame 猜测。
- 两 key 顺序/时序不假设；只命中一个即不完整。
- 未来 runner adapter 尚未接入；本任务不启动 VM，也不把 host tests 当运行证据。

## 9. 交付

- `REPORT.md`、`RESULT.json`、`SHA256SUMS`、`RUN-PLAN.md`、`DIFF-NOTES.md`、`CODE-DIFF.txt`。
- `observer/observer_core.py`、`observer/run_candidate.py`、`observer/baseline_binding.py`。
- `tests/test_host.py`、`tests/host-tests.json`、`receipts/baseline-binding.json`、`receipts/plan.json`、输入前后 seal/compare。
