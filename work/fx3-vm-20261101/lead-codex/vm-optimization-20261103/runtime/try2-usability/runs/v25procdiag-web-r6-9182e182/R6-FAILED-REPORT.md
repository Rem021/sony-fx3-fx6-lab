# FX3 v25-r6 单次网页运行：失败回执

## 结果

- 本轮仅启动一次，真实 Chrome 点击 Start，启动 QMP greeting/capabilities/id1 共 1.447314 秒；runner PID 26105，QEMU PID 26345，URL `http://127.0.0.1:63432`。持续 507.931 秒，首帧始终未提交，实际按键 0，未触碰省电配置或 Backup 源文件。网页最终显示“收尾检查未全部通过”，`trial-web-final-receipt.json` 记载 ACK=true；没有可保存的 guest PNG 或逐键浏览器截图。此轮未达到菜单、31/32 键或正常退出验收。
- 首错为 `QmpDeadline('QMP recv deadline expired; partial line preserved')`。`qmp.json` 中 id1043 的 256B OSD 环头 `pmemsave` 有返回，id1044 在 host elapsed 453.872 秒发出相同读取后无返回；异常记录的 host monotonic 为 390167.515。`host-first-exception.json` **不存在**：写该文件也报 `FileNotFoundError(2, 'No such file or directory')`，完整 traceback 仅保存在 `qmp.json` 的 `host_first_exception_write_error` 项。随后 query-status、stop、诊断读回和 quit 均没有 QMP 回复，不能称取得一致的暂停态环、帧、任务或 vCPU 快照。
- 协调端只读宿主日志核查（`msg_293e59cdfc25`）显示本地 07:34:40.386 `disk7 media is not present`，系统卸载 KAFU2T；07:34:40.389 事务未完成 `err6`；07:34:41.632/42.939 不洁卸载后重载；07:34:42.958 重挂完成。串口最后 mtime 15:34:35.824Z，首错以 wall/monotonic 偏移估算约 15:34:41.847Z，落在掉线窗口附近。可确认路径 ENOENT 与真实卷掉线同时发生，不能把该 QMP 超时归因于纯 guest 死锁；卷掉线原因及掉线前零帧原因仍未知。当前卷 UUID 再查为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，只说明已重挂。

## 静态及历史对照

| 轮次 | guest/宿主差异 | 画面与结局 |
| --- | --- | --- |
| r3 `v25diag-web-r3-91001f82` | r3 CPIO `31ce79e9…`；同 FX3 kernel、QEMU、4核 MTTCG、RAM、DTB、模型环境 | serial 1787 条 `FX3_GPE_DRAW_INTERVAL`、72 条 `FX3_OSD_FRAME_TARGET_VALID`；待机有帧，16 键后 health failure，API16 未恢复。 |
| r4e `v25procdiag-web-r4e-6274aabb` | r4e CPIO `439f9089…` 相对 r3 仅 `/init` 与新增 `simulation/fx3-procdiag-v1` 内容不同，成员 1140→1141（见候选构建审计）；同 DTB/Backup/硬件命令。 | serial 无上述两种绘图/目标 marker；有 KEY96_READY、GPE104 bind、8 条 AP89_SCREEN_CREATE；该历史轮缺最终 `receipt.json`，仅有 emergency cleanup，不能作正常生命周期对照。 |
| 本 r6 | 与 r4e 同 CPIO、DTB、Backup、QEMU 参数和环境；宿主 runner 加 r6 15 秒总额 QMP 启动握手，未改 guest 5000ms 门。 | 首帧前 0 键；serial 无上述绘图/目标 marker，有 KEY96_READY、GPE104 bind、8 条 AP89_SCREEN_CREATE；507.931 秒后外盘掉线窗口遇 QMP 截止。 |

源 r3→r4e 的 CPIO 成员差异由 `v25-r4-postmortem-host/REPORT.md` 与其 build receipt 支持；它不是零帧原因证明。三轮 `command.json` 的 CPU/GIC/RAM/MTTCG、QEMU 二进制、DTB 与模型环境一致，CPIO 差异如表；r6 相对 r4e 的启动传输变更属于 host。r6 启动握手成功仅排除本轮 r5 的 prelaunch 首错，不证明 guest 绘制健康。

## 收尾与资源

- `receipt.json`: `stop_cause=host_error`、`health_pass=false`、`lifecycle_pass=false`、`diagnostic_readback_pass=false`、`API16_restored=false`、`quit_sent=false`；QEMU exit=-9、已 wait/reap，runner 退出码 2。此处 -9 是宿主资源 guard 最终回收，不是正常 guest 关机。
- `resource-guard-receipt.json` 记录 QEMU PID26345 已回收且双锁在回收后释放；独立 `ps` 无 PID26105/26345，非阻塞独占锁核验两把均 free。原 14 个输入依 `receipt.json` 逐项重新 SHA256，全部匹配；r6 runner、startup、SOURCE-FREEZE 也分别匹配 `2101edb5…`、`efba2c33…`、`99d8a29d…`。
- Chrome AX 最终页已实际读到“本轮已结束／收尾检查未全部通过／按键 0/4096／最后提交帧 无”；`trial-web-final-receipt.json` 的 ACK=true 仅为网页最终回执送达，不表示 API16 或退出通过。由于首帧缺失，没有 guest 截图；用户持续切换 Chrome 当前标签，独立截图命令捕获了其他标签并**未保存为本轮证据**。

## 下一门

先由协调端保留并复核近时段 kernel I/O 事件，查外盘掉线原因；另需独立解释 r4e/r6 在掉线前都没有 GPE 绘图 marker，而 r3 曾有。此次不修盘、不改固件/超时/定时器，不启动第二轮；只有存储稳定和零帧原因可检验后才适合再安排真实网页验收。
