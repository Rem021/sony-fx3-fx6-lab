# Observer runner v2：Unix GDB gate 配置修复

已修复独立 runner 的重复 GDB 端点配置，并用同一 QEMU 完成无 Sony guest 的真实 Unix RSP smoke。未改冻结的 observer candidate，未运行 Sony VM，未获取共享锁，未使用 TCP 端点。

## 改动

[run_observer_once.py](run_observer_once.py) 从旧 runner 复制后修改，完整差异见 [runner-v2.diff](runner-v2.diff)：

- 运行 argv 仅删除末尾重复 `-s`，保留 `-chardev socket,path=g,server=on,wait=off,id=keygate93`、`-gdb chardev:keygate93` 和原有串口路径重定向。异常的非末尾/重复 `-s`、其他 GDB 配置会被拒绝。
- manifest 仍按传入的完整 SHA 校验，允许新的 observer manifest，也接受其 argv 已经去掉重复 `-s`。其余冻结的 295 kernel/DTB/Backup/model/平台/成员差异检查保持。运行使用 `.started-<manifest_sha>` 的 `O_CREAT|O_EXCL` 标记，保留禁止同一 manifest 重跑机制。
- `observed_page` 改为 `native-screen-unverified`，reason 为 `bounded diagnostic key sequence; no verified native menu`。成功记录仅表示软件 gate 写入/回读；guest 消费与原厂 UI 响应均明确未证实。
- 键异常写入 `key_attempts: delivery=unknown`，设置 `key_failed` 后停止后续步骤，既不重发本步骤，也不跳过顺序门。既有 InputGate 的 previous/done/magic/result 与写入回读检查未改。软件 gate 返回不视为 keyworker 完成 ack。

输入标识和未知状态记录属于 host 证据修正；没有变更键序列、hold、deadline、guest 初始化、CP/队列或绘制行为。

## 验证

[test_runner_qmp.py](test_runner_qmp.py) 沿用旧 QMP 单读者/事件/错误/断流测试；[test_runner_argv.py](test_runner_argv.py) 单独断言只去掉末尾 `-s`、仅重定向 serial、保留 Unix endpoint、原输入 argv 不变，并拒绝异常配置。4 个测试通过。

[smoke_unix_gdb.py](smoke_unix_gdb.py) 使用原运行同一 QEMU，只有最小 `virt`、TCG、1 CPU、64 MiB、`-S` 和 Unix `g`，没有 kernel、DTB、CPIO、Backup、loader 或 Sony 模型环境。CPU 全程保持停止，没有发送 continue/step。

[unix-gdb-smoke.json](unix-gdb-smoke.json) 记录实际 argv、QEMU 指纹与结果：Unix socket 创建成功；按 InputGate 同样的运行目录相对 `g` 连接；`qSupported` 返回能力；`?` 返回停止状态。自有 QEMU 已回收，自有临时目录已清理，冻结 candidate 的 manifest、CPIO、launcher、init 前后指纹不变。另对一个新 SHA、已去掉 `-s` 的临时 manifest 完成 `check()`，没有调用 execute。

同一 QEMU 的 `-help` 确认 `-s` 是 `-gdb tcp::1234` 简写；本次未执行原重复配置。[validation-record.json](validation-record.json) 保存该原文、测试结果、来源及文件指纹。[QEMU 官方说明](https://www.qemu.org/docs/master/system/invocation.html) 也定义同一语义。

## 使用边界

下一次 Sony 运行归主 agent：先生成并核对新的候选 manifest，再用 v2 `--manifest <新路径> --manifest-sha <完整SHA> --check`。本目录没有启动任何 Sony 候选；原 `observer-004ab971f4` 的同 SHA `.started-…` 标记仍保留，不可用 v2 重跑它。

Unix 协议 smoke 只证明 host 端点修复，不证明软件键被 guest 消费、原厂菜单响应或任何实机行为。原运行的线程/空帧结论见 [observer-run-review.md](../observer-review/observer-run-review.md)。
