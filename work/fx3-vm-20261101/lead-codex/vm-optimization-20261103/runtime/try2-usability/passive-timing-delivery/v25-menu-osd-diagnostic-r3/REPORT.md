# FX3 v25-r3：诊断环并发修订与独立网页 runner（仅离线）

## 结论

r2 的 `v25_diag` 先递增全局 serial，后无互斥地清空/填写模 256 槽。宿主定向调度复现：A 预留 serial 1 并停在清槽后，B 写完 serial 2..257，A 再发布 serial 1，导致槽 0 的第 257 条被旧写者覆盖。此为**诊断实现缺陷**，没有证据证明它是 v24 第 12 键画面停住的原因。r3 用一次非阻塞 trylock 保护整个记录提交；竞争失败时不分配 serial，原子增加诊断头 word 5 的 `dropped_busy_writer_events`。锁内仅做原子操作和内存写，不持锁调用原生 `hwait/hsignal/hsend`、`own_lock`、日志或休眠；原调用返回、5000ms 时限和 AP 状态不变。

## 定向证据与边界

- `test_diag_concurrency.c` 同一调度的输出：`r2 reproduced: serial=257 slot0_serial=1 expected257=lost`；`r3 guarded: accepted=1 dropped=256 intact_serial=1`。这是抽出的同构写槽序列宿主复现，尚非 guest 多核压力回执。
- `parse_v25_diag_r3.py` 接受 schema 2，验证返回 `link<return`、同 TID、入口冻结的 id/op/committed/source/epoch/token 全一致及返回时钟不早于入口；同一入口只能被一次有效返回消费。不能满足的配对保留 fault，绝不计入有效耗时。测试覆盖九种字段/时钟/链接错误、重复返回、回绕、丢失、半写和截断。
- 被 busy trylock 丢掉的记录通过头 word 5 报告；槽 serial 不符报告 `overwritten` 或 `missing_or_torn`。若有丢失、无效槽或未证明静止，未配对入口归 `unknown_possible_lost_return`；只有无丢失且已静止的完整尾段才称 `unpaired_at_quiesced_snapshot`。回绕前的更早入口可能已覆盖，不能由尾段缺席推断没有原生调用。
- 原 ELF 偏移与机器字审计沿用 r2：`libObj.so` SHA `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae`；wait 调用 `0xf2224→0xfd354`，signal 调用 `0xf22cc→0xfd390`。MENU handler 地址仍未知，未添加猜测挂点。

## 候选及 runner

- r3 源 `src/fx3-osd-headless-v25-r3.c` SHA `1c4d2b420a40d006d22d2e60510df18d6dbbd7c51cd219735f1252f17c5956eb`；与 r2 的 diff 为 `src/r2-to-r3.diff`。SO SHA `67155b38fbbe23c3b6273c64ce8fc4676e59ad98da4a30a238508c26d9b5fba8`。新增动态未解析符号数 0。
- `vmopt-20261104-v25-menu-osd-diagnostic-r3/candidate.json` SHA `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`；CPIO SHA `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`；DTB SHA `5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b`。从 r2 候选仅替换 `simulation/fx3-osd-headless-v5.so`（108144→109000 bytes）；1140 个成员，其余内容/模式不变；DTB 只更新 initrd-end；原 English gen4 seed SHA `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f` 不变。
- 独立 `run_trial_v25_diag_r3.py` SHA `1a3af0b8fb6be5c79bf4e58548e622fec03263281badf147e0cff67dae7d3429`。复用 v24 网页 Start、100ms/单 pending/视觉确认、输入/健康门、End/Ctrl-C、20 秒 API16 恢复、QEMU 回收与双锁回执；源差异见 `v24-to-v25-r3-runner.diff`，固定依赖 SHA 列于 `FREEZE-r3.json`。入口没有修改默认/旧入口，未运行。
- 退出前 `quiesced_diag_readback.py` 要求 QMP `stop` 成功，再取 `query-status: running=false,status=paused`，然后 `pmemsave` 完整 `0x41e000000..0x41effffff` 的 16 MiB 到唯一 run 的 `osd-ring-final.bin`，检查长度、SHA 和 schema 2，另写 `osd-ring-final-diag.json` 与 readback receipt。不可证明暂停、QMP 错误、短文件或解析失败均不能标记一致；原有 `finally` 仍尝试 API16 恢复和 quit/reap，诊断读回失败使本轮 health 为 false。早期 QEMU 已退出时无法再取得一致环，报告明确缺失。

## 外部合同核对

GCC [原子内建函数说明](https://gcc.gnu.org/onlinedocs/gcc-12.1.0/gcc/_005f_005fatomic-Builtins.html)定义了 strong CAS 与 acquire/release 顺序；r3 使用 strong CAS，一次失败直接计数。QEMU [QMP 参考](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html)将 `paused` 定义为 `stop` 后的运行状态，且提供 `query-status`；[HMP 文档](https://www.qemu.org/docs/master/system/monitor)列出 `pmemsave`。这是接口设计核对；本地 QEMU 的实际暂停/读回仍须 guest 运行验证。

## 验证及下一轮

`verify_v25_r3.py` 结果 `verification-r3.json: offline_pass`；编译/链接、无新增 import、原 wait/signal/gate 文本计数、单成员 CPIO、原种子/DTB/SHA、解析器反例、暂停快照 mock、`--help` runner 导入均通过。没有 QEMU、网页或真实多核验收，`guest_validated=false`。

待协调端单独授权后，最小一轮应使用此固定候选与 runner，经双锁/卷 UUID/输入哈希复核启动本机网页；每键先看不可变 PNG，再一次输入并等 native down/up/done 与视觉确认，优先复现单次 MENU 对话框关闭。若出现无新帧，End 后取暂停态环，按同代 producer→receive→commit、wait→signal 的 entry/return 配对定位首个缺失；任何 busy 丢记录只能标未知。最后检查 API16 原字、PID/reap、双锁及输入 SHA。本轮未获 guest 放行，不能称 v24 菜单卡顿已修复。
