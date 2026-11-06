# v25 r6 启动 QMP 握手候选（仅宿主离线）

## 真实轮边界

r5 唯一 Chrome+FX3 轮详见 `../../runs/v25procdiag-web-r5-1db74605/MANUAL-BROWSER-DIAGNOSTIC-FAILED.md`。`qmp_capabilities` id1 在 elapsed 1.346s 发出，原 3s 运行期 QMP 默认接收预算届满；收尾请求 id2 之后才读取 id1 成功答复。`query-status=prelaunch,running=false` 且未发 `cont`，所以 8.459s、0 键、无首帧是**宿主启动握手失败**，不属于 guest MENU 或 5Min 省电行为。真实轮 QEMU exit0/reaped、双锁 free、输入 SHA 不变、浏览器 final ACK=true；API16/环/任务不适用且未通过。未运行第二轮。

## r6 宿主改动

- 新 `startup_qmp_v1.py` 为 greeting + `qmp_capabilities` 共用 **15s 绝对预算**，仅在此启动阶段使用。id1 发送一次，保留 transport 已有的部分 JSON、异步事件与同 ID 匹配语义；超时/EOF/错误/发送结果未知均明确失败，绝不重发或把未知判成功。原 guest 5000ms、运行期按键、原 API16 20s 和 QMP 默认 3s 不变。
- 在启动连接、greeting、capabilities 三阶段记录耗时；`startup-qmp-timing.json` 写预算、请求/回复 ID、缓冲字节数、send_unknown、异常类型和完整 traceback。内层 host 首错另写 `host-first-exception.json`，即使 transport 仍为 None 也能记录原异常，不遮蔽首次失败。源快照新增启动模块。
- 清理前只读 `query-status`；仅在明确 `status=prelaunch,running=false` 时标记环与 API16 为 `not_applicable_prelaunch`，仍发 QMP quit/回收。其他状态走既有全环、任务/vCPU、API16/退出程序；不可由无帧或早期错误推定成功。r5 守护器及双锁持有逻辑原字复制，guest CPIO/DTB/Backup、QEMU硬件、默认入口均不变。

## 宿主定向验证

- `test_startup_qmp_v1.py`：真实 socketpair 4.1s 延迟答复（覆盖 r5 >3s 情形），事件+分片后同 id1 成功且仅一次请求；独立部分包超时、event、EOF、QMP error、send_unknown 反例。prelaunch 仅精确状态匹配。真实缺失 QMP socket 和不存在的 Popen 可执行文件，在 transport=None 的首错写入仍保留原 FileNotFoundError，guard 回收已登记子进程和锁。
- `test_qmp_line_transport.py`、`test_resource_guard.py`、`test_runner_lifecycle.py`、`python3 -m py_compile *.py`、`--help` 全通过。测试是宿主离线证明，不是 r6 运行通过。
- 代码差异 `r5-to-r6-runner.diff`，新增模块和测试、全部 `.py` SHA 在 `SOURCE-FREEZE.json`；`OFFLINE-TEST-RECEIPT.json` 固定命令、exit code 和输出。真实下一轮须另获授权，不能因本次 host fixture 通过而更换默认入口。

## 未知与下一轮最小验证

id1 迟到是 QEMU 初始化期间调度/宿主负载或其他因素所致，现无因果证据。下一次仅一次真实 Chrome Start：核 startup 三阶段与同 id 答复，在首帧前无 `cont` 时故障即停；若首帧完整才逐键画面确认并按既有门继续，最终分别核 API16、QEMU reap、双锁、SHA 和网页 ACK。
