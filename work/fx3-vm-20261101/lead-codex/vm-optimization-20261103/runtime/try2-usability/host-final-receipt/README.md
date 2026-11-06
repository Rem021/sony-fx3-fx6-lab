# 网页最终回执交付修复候选

2026-11-03。**修复退出结果被短暂服务窗口丢失，以及重复结束请求使终态倒退的问题。** 这是宿主侧候选；未启动 QEMU、未替换用户默认入口；随后已完成[真实浏览器宿主验收](BROWSER-RESULT.md)，使用历史画面和人工会话状态，尚未与固件联动。沿用 v13 的固件/平台/Backup，原省电活动缺口仍待运行诊断。

## 问题与行为

旧 v13 在保存退出回执并发布 `phase=finished` 后只等待 2 秒就关闭 HTTP 服务。网页一次状态请求、图片请求及图片解码分别最多等待 8 秒，故可能尚未完成当前轮询就失去获取最终回执的机会。另在真实 loopback HTTP 上复现：v4 的迟到 `/api/stop` 会把 `finished` 改回 `stopping`。

新 v14/v5 在原 VM 收尾及双锁释放逻辑之后才进入最终结果交付：

- 页面先显示服务端最终状态，再携带该轮回执 ID 发送认证确认；这只是“已收到结果”，不是重新判定清理成功。检查未通过仍原样显示。
- 服务端等待确认，最长 30 秒；网页关闭或网络断开不造成无限等待。收到任一该会话页面的有效确认可提前结束等待。
- 迟到或重复的结束请求保持 `finished` 与原结果不变。未完成会话、错误回执 ID、未认证请求不能确认结果。
- 已完成收尾后按 Ctrl-C/SIGTERM 可以结束等待，记录 `local_exit`，不伪造浏览器确认，也不退回 `stopping`。正常运行时的信号清理保持原路径。
- 独立 `trial-web-final-receipt.json` 记录确认是否收到、等待时长和退出原因；原 `receipt.json` 的生命周期和固件验收结果不被改写。

30 秒是宿主网页交付窗口，**不是新固件超时或省电设置**。它给一次有界轮询留下余量，不保证持续网络故障下浏览器一定拿到结果；终端和文件回执仍是复核途径。

## 文件与复现

- [build.py](build.py)：从固定 SHA 的 v4/v13 生成候选，来源版本变化即拒绝；不启动 VM。
- [web.diff](web.diff)、[runner.diff](runner.diff)：完整差分。
- [trial_web_v5_final_receipt.py](../trial_web_v5_final_receipt.py)、[run_trial_v14_final_receipt.py](../run_trial_v14_final_receipt.py)：候选模块和入口，独立状态文件及运行标签。
- [build-receipt.json](build-receipt.json)：来源与候选哈希。

```sh
node test_final_receipt.cjs
python3 -B test_delivery.py
```

[js-test-receipt.json](js-test-receipt.json)：15 项 Node VM 测试，包括前版请求超时/按键歧义保护，以及最终状态先显示、确认丢失不重试或改结果。使用模拟 DOM/网络，不是浏览器渲染证据。

[http-test-receipt.json](http-test-receipt.json)：9 项真实 loopback/宿主线程检查，包括旧版终态倒退复现、越过旧 2 秒窗口仍可读取、错误确认拒绝、正确确认提前结束等待、关闭网页的有界超时及本地退出。测试仅人工会话状态，服务线程均已回收。

候选 `--help` 导入通过。真实浏览器宿主交互另见 [BROWSER-RESULT.md](BROWSER-RESULT.md)。剩余仍是与固件联动、实际 VM 退出资源回收和 Finder 入口验收；没有用宿主测试替代这些门槛。

后续发现并独立修复了 HTTP 绑定／进程创建／早退时丢失最终回执的缺陷，见[启动失败回执候选](../host-startup-receipt/README.md)。本目录 v14 历史版本及测试回执保留；后续联动应同时审查该修正。
