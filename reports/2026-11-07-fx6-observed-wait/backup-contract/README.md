# FX6 Backup 四键契约与最小候选（2026-11-07）

**结论：295 的 `Backup_read` 空成功不正确；不能用调用时的 `w2` 清零输出。可以离线确定四个 UI 启动相关键均为 8 字节，并给出只覆盖 `fa0191/fa0192` 的自有内存候选。`fa01a3/fa01a4` 缺少有效映射能力，不能从全 `ff` 默认值推出 `0x429100000/0x100000`。** 此目录没有集成或运行 VM。

## 原件与调用契约

可重跑的 [inspect_contract.py](inspect_contract.py) 校验实际供体哈希、ELF VA→文件段转换、原厂导出、appFw PLT 重定位、指令和固定默认模板。结果在 [contract-evidence.json](contract-evidence.json)。不使用旧的 81 MB 错误 appFw。

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| 实际 FX6 appFw.so | 50,520,424 | a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067 |
| 实际 FX6 libbackup.so | 14,232 | e003e2d8a1f42fdf629dda012a01f225940c016b2ab4dbf482a761378e8d286f |
| CHAPLIN/CX95898_NTSC.bin | 2,253,333 | e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e |

原厂 `Backup_read` VA `0x1e14` 在函数入口覆盖 `w2=-1`，把 `id`/`buf` 移入 `w4`/`x5`，再用 `op=3`、参数数目 2 发送消息；输出状态在栈中先置 `-1`，返回时读取该栈槽。**原厂此接口没有使用调用者的第三寄存器作为长度。** 这已足以否定 294 的任意长度 `memset`。函数返回 0 的意义须由原远端处理与调用方判定；不能因惯例替它指定语义。

`Backup_nread` VA `0x252c` 才将调用者 `w2` 符号扩展到 `x6`，发送 `op=31`、三个参数。`Backup_get_datasize` VA `0x1d5c` 通过另一个原远端操作取长度。因此不能混用两种接口，也不能由 `nread` 的第三参数推广到 `read`。

`backup_sync_msg` VA `0x1a50` 自身最终返回 0，但只在 `osal_snd_sync_msg` 返回 0 后把消息 `+4` 的业务结果写入传入状态指针。申请消息或发送失败时状态保持调用者的初值。**把 `*ret` 固定写 0 不是原实现的等价替代；仅恢复 `Backup_read` 而保留假的 `backup_sync_msg` 仍无法恢复这条契约。** 未闭合原远端全部成功/失败码，本候选故意使用独立状态枚举。

appFw 四处已由 `.rela.plt` 绑定到 `Backup_read_8Byte` 的 PLT `0xb19370`：`0xc0b294→fa0191`、`0xc0b2f4→fa0192`、`0x1395d00→fa01a3`、`0x1395d18→fa01a4`。前两处保留 64 位地址与容量，随后比较描述符要求；后两处用于地址余数、对齐区间等计算。**类型证明为 64 位标量与 8 字节记录，不等于运行期地址有效性的证明。** `Backup_read_8Byte` 自身预清零 8 字节结果，远端操作 5 结束后从结果槽返回 X0；没有向调用者暴露独立状态。

## 四键默认值

复用已有 `backup-state-binding/parse_bk4.py`，逐文件哈希、两份 BK4 校验和、所有表/属性边界、零填充均通过；本轮核对五份 FX6 CHAPLIN 地区模板的四键，每记录结果一致。每键 `length=max_length=8`，属性 0。

| ID | 记录 0（默认 AP） | 记录 1 | 解释边界 |
|---|---|---|---|
| fa0191 | 0x410524000 | 0x80918d000 | 固件默认绝对地址，不能直接当当前进程指针 |
| fa0192 | 0x01900000（25 MiB） | 0x00300000（3 MiB） | 与相同记录的地址成对 |
| fa01a3 | 0xffffffffffffffff | 相同 | 全一哨兵；没有有效物理窗口证明 |
| fa01a4 | 0xffffffffffffffff | 相同 | 同上 |

“默认 AP 查首记录”的依据复用已有 `backup-state-binding/README.md` 对原 `backup.ko` 的 `Data_init` 分析，不将它外推为当前机身或 VM 的实时值。本轮不重新执行原内核代码。精确数据文件偏移保存在 JSON 中。

## 独立候选与所有权

[typed_backup_reader.c](typed_backup_reader.c) / [.h](typed_backup_reader.h) 提供两个有意分开的接口，均不导出 Sony 函数名：

- `fx6_template_read_u64` 接受已校验的某一明确记录，四键白名单、全部长度恰为 8、无重复键后才复制一个标量。保留全一原始哨兵，无地址解引用。它是元数据读取，不是运行态替身。
- `fx6_arena_create` 先验证非零 `required<=capacity` 与算术边界，再申请零填充的完整 backing。构造失败没有“可用容量”。`fx6_arena_read_u64` 只从同一个不可变对象返回 `fa0191` 地址和 `fa0192` 容量；`fa01a3/a4` 返回 `NO_CAPABILITY`，未知键返回 `NOT_HANDLED`，所有失败均不改输出。调用者必须将未知键交还原厂实现或明确失败，不能转成成功。

调用者在开始消费者线程前创建一次 arena；地址和容量不可分别初始化或调整。`required_bytes` 必须来自已证明的消费者描述符；本候选没有把任意 `w2`、模板容量或某次成功路径当作需求长度。对象持有 backing 的所有权；外部消费者只借用，所有线程及保留引用结束后才可销毁。此版本没有重新创建、缩容或跨线程销毁策略。

对 `fa0191/fa0192` 的这种覆写是**明确的虚拟机适配策略**，不是把 32 MiB 伪称为原厂模板值。现有 295 的 arena 成功分配才可提供容量；单独返回 `0x2000000` 而不验证分配成功是具体缺陷。物理窗口必须另有已验证的宿主/客体映射、长度和生命周期，当前候选不创建它。

## 给主 agent 的最小改动边界

1. 停止 295 的 `Backup_read` 空成功路径。恢复原 `Backup_read` 和 `backup_sync_msg` 整条调用链；原实现不可用时使用该接口已观察到的失败初值 `-1`，并保留输出，不自造成功。不要将本 helper 的枚举数值当 Sony 返回码。
2. 停止 generic `Backup_nread` 用任意请求长度清零后成功。未知 ID、未知原返回约定继续原路径；缺失原服务的失败应显式记录。
3. 只在已验证消费者范围内接入自有 arena 的 8 字节标量候选。generic `Backup_read(id,buf)` 缺少可依赖的输出容量参数，**不能仅凭 ID 就把 helper 包成任意调用者的安全 memcpy**；调用点的对象大小仍需证明。
4. `fa01a3/a4` 的假物理窗口不由本证据支持。原厂默认哨兵可以被运行态写入更新，当前工作不证明应永远返回哨兵；应保留原查询或明确“不具备映射能力”。由 observer 实测决定下一候选，不预先扩展其它 Backup ID。

## 离线验证与局限

执行 `python3 -B run_offline_checks.py` 会先核对外盘 UUID，所有写入都在本目录内。最新 [test-results.json](test-results.json) 为 **PASS**：

- C：97 项检查，`-Wall -Wextra -Werror -pedantic`，ASan + UBSan；覆盖两个分配步骤的确定失败、非法容量/需求、未知 ID、非法/重复记录、哨兵、未对齐输出、各错误长度与输出守卫、实际 backing 首尾读写。
- BYOF → C：140 项检查，实际两条记录 × 四键，保持真实默认值，包含错误长度 `0x77ffd4e0`、未知键和输出前后守卫。共享库只是本机 helper，未执行供体函数。
- 真实输入检查同时绑定原 ELF 哈希、PLT 调用目标、关键指令及五份地区默认记录。没有改动任何供体或共享脚本；没有 VM、相机、Git 写入。

这是一个离线可测试的最小构件，**不证明原 Backup 远端服务、VM 启动、菜单或渲染恢复**。ABI 寄存器解释核对了 Arm 维护者的 [AAPCS64](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst)（页面版本 2026Q3，2026-11-03；2026-11-07 查阅）。公开 ABI 只支撑参数/返回寄存器规则；Sony 私有 ID、长度、操作号与模板值全部绑定本地原件，未借公开文档推定。
