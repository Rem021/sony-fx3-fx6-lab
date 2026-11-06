# FX6 AppFw two-key observer — r5 host-only closure

- Task：`task_ed9c75658665`
- Dispatch：`ctx_65b7325e226f`
- Status：**HOST_ONLY_R6_CORRECTED; RUNTIME_CLEANUP_BLOCKED; NOT RUN**
- 保留 `superseded/pre-r5-1e6b85c6/` 及更早 snapshot；固定平台、3a08 CPIO、b1fe appFw、其他输入、旧 observer、运行政策未改。
- 无 VM/guest/QMP live/browser/server/live-process；无 camera/USB/SD；UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 已核。
- r4 实际四stop组件、prelaunch、quit-before-wait 保留，不重做大范围实现。

## 1. r6 三项失败路径修复

1. **UUID/所有权失败不写根**：`run_stop_only` 的异常 fallback `mkdir/write` 已删除；CLI 不创建目录/不覆盖 receipt，只报告。HostRunner 只在 preflight UUID 成功、独占创建 run root/command、且拥有本轮 run 后写 receipt。UUID false/不存在 root/已有 receipt/已有其他文件/deps 构造异常均不写、不 launch；fake 测试验证 root 不存在/既有字节不变/其他文件不新增。
2. **cleanup phase 顺序**：pause/query 确认后，在 `observer.cleanup()` 之前把实际底层 RSP 切到 `cleanup` phase；observation 150s 耗尽而 total 仍有 30s 时 z1 使用 total 预算真实发出；total 耗尽时 RSP 在 send 前拒绝 z1，只可走自有进程终止/回收，不 resume。测试用 fake/socketpair 覆盖 phase 顺序、expired observation + remaining total、expired total 无业务 IO。
3. **成功条件**：stop-only rc0 还要求 `input_unchanged_after is True`、`postflight.error is None`、`verification_failed is False`；hash drift/error/unknown 时 rc非0，但 receipt 保留 `two_keys_observed`/`host_cleanup_complete` 原证据和 `verification_failed`，不改输入。

## 2. stop-only 真正入口

`observer/run_stop_only.py` 不再打印 READY 占位：

- 通过 `HostRunner(real_deps(run_root), stop_only=True)` 执行；真实 deps 只在默认禁用门后注入，测试使用 `deps_factory` fake。
- 保留 token `APPROVE_GRMREAL46_TWO_KEYS_STOP_ONLY` + `--new-run-approval` + fresh `--run-root`；无 token/错 token/缺 approval/复用 root 均不 launch。
- 无 inherited callback；不写 guest 控制/代码/数据。cleanup：确认 pause、删可确认 Z1、关 RSP、QMP quit→bounded wait/reap→锁释放；残余/stop 不确认只退出自有 QEMU 并标异常，绝不 resume。
- 序列化 receipt 到 run root；退出码 0 仅当 `two_keys_observed && host_cleanup_complete`（且 `guest_restore_status=unknown_not_attempted`、`boot_menu_passed=false`）。
- 字段独立：`two_keys_observed` / `host_cleanup_complete` / `guest_restore_status` / `boot_menu_passed`；`clean` 仍为 full-clean 策略，stop-only 不偷换、不叫 Guest End/API16 成功。
- fake main E2E 覆盖：无 token/错 token/缺 approval/root reuse 不 launch；正确 fake deps 只 launch 一次，四 stop、零 guest writes、quit/reap/lock，失败不假成功。

## 2. RSP absolute deadline

- `RSP` 不再每次新建 1s/2s：`_remaining` 按 phase 区分 `remaining_observation`/`remaining_total`；connect、command、send_continue、virtual_read、XML/p、Z1/z1、poll_stop 全部使用 absolute remaining。
- `poll_stop` 不再 `_one(time.monotonic()+1.0)`；改为 `time.monotonic()+min(timeout, remaining)`，部分 `$T05` 无尾部在 50ms 预算下实测 bounded（<0.5s），不会等到 1.02s。
- 所有 sendall 前设置对应 timeout 并检查 expiry；deadline 耗尽时不再因 `max(.001,0)` 发业务命令；过期只能走已允许的自有进程终止/回收，不恢复 guest。
- RSP connect 失败关闭自身 socket 并有限重试；QMP/RSP constructor 失败关闭已打开 socket。清除 `_qcall`/factory 的 TypeError 重发 fallback；真/fake 同一显式签名，内部 TypeError 不会被当接口不支持而重发有副作用命令。
- 测试：真实 socketpair 的碎片/迟到/无响应/已耗尽/部分包；QMP 缺 capabilities；实际 Observer 四stop `continued=4` 正例保留。

## 3. preflight/postflight 与 receipt

- `HostRunner.run` 在创建 180s Deadline **之前**做 host preflight：UUID、frozen artifact、target/app hash+size；preflight 不占 launch→own child reap 的 180s。
- 运行后 postflight 重算 target/app hash 并写 receipt：`preflight`/`postflight`/`hash_source`/`input_unchanged_after`；fake 注入 hash 时明确 `hash_source=fake_injected`、`runtime_evidence=false`，真实 deps 标 `actual`。
- receipt 落盘到新 run 的 `receipt.json`，关联 command SHA、target/app/serial hash、qemu_exit、lock；失败为 error/unknown，不把磁盘 preflight 伪称 guest evidence。
- `self.possibly` 初始化；observer 未 arm 为 0；partial arm 取 observer.possibly；stop 未确认不删断点/不调用 inherited。

## 4. 当前组件与剩余

- 实际 Observer/QMP/RSP/Sysregs 四stop组件（r4）保留；当前仍无 VM 证据。
- 完整 clean 需 inherited API16 合同；3a08 上旧 `restore_api103_v2` 控制合同**未建立**；target helper 仍有 `fx3_sync100_shutdown`/`sync100_restore`、`FX3_SYNC100_SHUTDOWN original16_verified` 标记，不能因缺 `F100FILE` 推断无机制。未虚构 callback、未改 CPIO/helper。
- stop-only 仅作为未来一次观察终止方式的候选；本消息未授权运行，不改变现行策略。

## 5. 测试

- `tests/test_host.py` 16/16。
- `tests/test_rsp_host.py` 7/7。
- `tests/test_adapter.py` 5/5。
- `tests/test_runner.py` 16/16（含 stop-only main UUID/hash失败）。
- `tests/test_stateful_transport.py` 8/8（QMP caps/greeting、RSP c/T05、partial/expired total z1）。
- `tests/test_e2e_stateful.py` 1/1：实际 Observer/QMP/RSP/Sysregs 四stop，`continued=4`。
- 合计 **53**；全部 fake/socketpair，无真实 QEMU。

## 6. 运行模板（待单独授权）

见 `RUN-PLAN.md`；固定一次 Start、零键、<=150s 观察/<=180s 总，preflight 在预算外，launch→reap 在预算内；rc0 需两key观察+host cleanup+input unchanged+postflight无错。真实动作未执行，本目录不是授权。
