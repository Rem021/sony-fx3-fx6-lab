# r21/N64 八键真实 VM 验收：failed

唯一一次 VM 已运行；**实际 accepted 0/8、显式按钮点击 0、arm 0、恢复 0、确认 0**。本轮本地 wrapper 的 `operate.py:67` 在 `run_action` 之前引用未导入的 `sys.argv`，真实 CLI exit=1；随即执行原 End，没有补键或再次启动。失败原因在本轮操作工具，未得到 r21 菜单行为结论。

- run：`v25gate-n64-r17-29e7c98f`；真正源码是冻结 r21，目录标签 r17 不作版本依据。
- 固定命令和实际 argv：`RUNNER-LAUNCH.json`、`ACTUAL-ARGV-PREPARED.json`、`ACTUAL-RUNNING-ARGV.json`。实际 QEMU 为 `qemu-gpio5-bf4d46481998b8fb`，SHA256 `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`；4×cortex-a35、5120 MiB、tcg,thread=multi、noicount，kernel/DTB/N64 CPIO 未变。
- 启动健康：runner `health_pass=true`、`standby_ready=true`；从 Start 工具入口至合格待机图返回约 **43.233 秒**，小于180秒。操作员亲看 NO CARD、HD/Fixed-59.94fps 与待机图标；不是八键通过。看图接收/完成的模型时钟无仪器，仍记 unknown。
- 八项固定语义全部未执行，无 down/up/done、确认或逐键截图可交付；未建立 attempt/nonce/ledger。`RESULT.json` 逐项标 not_executed，不能用零拒绝或 HTTP202 冒充发键成功。
- 原始失败：`OPERATOR-CLI-FAILURE.json` 与 `.combined.txt` 保存实际 argv、exit1及工具返回的完整合并终端输出；没有单独重定向 stderr。`later_capture.py` 也有同类缺失导入，尚未执行；此前 host 检查调用导入后的 `run_action`，未覆盖实际 `__main__`。本轮失败源码保持冻结，没有修后重跑。
- End与回收：API16 原字节及 ACK 已核，原20秒恢复预算内用时 1.317364秒；QMP quit id=232 有 return ACK，exit0/reaped/双锁free/runner与QEMU PID absent/端口closed、网页finalACK、自有browser关闭均有证据。见 `FINAL-CLEANUP-VERIFICATION.json` 和 run 原始回执。
- 清理 wrapper 另有 None.get 记录：deadline从未armed，status.current=null；读取后误用 `.get`，未调用dispose，随后仍保存HAR并关闭自有browser。首次CLEANUP在runner最后正常退出前一瞬采样为alive/open，独立最终检查已确认关闭；保留两份原始记录，不覆盖。
- HTTP原件在 `traffic.har`，Start202/Stop202/finalACK200各一次，key/confirm POST均零；`HTTP-INDEX.json` 与 `raw-http/` 保存HAR中的原始body字节及hash。browser-ready发生在HAR开始前，其原始HTTP不在本轮HAR中。
- 原字节零拒绝导出304B，SHA256 `82cdc35a9631808d9a6e5b6a90c50d7b7e66216449fb3dc8d7a422082a77b8e8`；`web-key-rejections.raw.json` 与run原件一致。v5尾段为 `valid_nontransactional_tail_checkpoint`，明确不是事务结束快照，尾后事件计数unknown。
- 前后核回40项源码、145项交付、14项固定输入和实际QEMU；本地pre-Start源也未变。协调员 `msg_82796ff62714` 允许的preflight/STATE输出已记录生成状态并原字节复制到run的 `authorized-runner-outputs/`；无其他候选目录新增文件，冻结清单未改。

后续需单独派发修正两个CLI模块的直接导入并验证真实CLI入口；八键语义、连续菜单与恢复行为仍未验。本轮无物理相机、USB、SD、刷写或FX6操作。
