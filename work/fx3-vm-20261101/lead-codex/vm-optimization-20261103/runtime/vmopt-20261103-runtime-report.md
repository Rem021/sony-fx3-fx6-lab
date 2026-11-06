# AP105 实跑：vmopt-20261103-ap105-baseline-45d987f9

- 原候选 SHA `0c4fd429c0c506c285895bdad87fd2bff78babd0db89b597932525b869f7ed7c`，性能 SO SHA `30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4`。仅新 runtime 内复制 runner，状态/预检/runs 改写入新目录；原双锁、QEMU、候选、控制与 20 秒收尾逻辑保留。
- 4 核 MTTCG、无 icount、1200 秒请求，实测 1204.816 秒含收尾。原种子及全部输入 SHA 未变。QEMU PID 69779 退出 0 且 reaped、PID 消失；两把锁非阻塞 flock 回读均可取得。
- 首帧为原拍摄待机；MENU 后原生 Principal 完整菜单；Setup > Área/Data 的 Idioma 弹窗完整显示；第 9 键 English 焦点、第 10 键 ENTER 后 UI 显示 Language English。全部 24 次单键决定见 `runs/vmopt-20261103-ap105-baseline-45d987f9/vmopt-visual-decisions.jsonl`；第 24 键 MENU 的按下/释放 guest 日志出现，但到 1200 秒界限无逐步截图，因此最终 MENU 已关闭及 60 秒静置均 **unknown/未验**。
- 日期页显示 2021-1-1，进入编辑后从年到秒只按 RIGHT、未改值；RIGHT 从秒回年，未找到 OK 焦点。第 22 键 MENU Cancel，日期原值确认未完成。
- 原生 `/setting/Backup.bin` 两次完整相同 O_RDONLY 读回有效：English 确认后 generation=2，SHA `be048e8557acc93208425687f823993fc70542036158adea77ae87db74dd53bd`；最终 generation=3，SHA `c5b52fe629f35b3f53ed6012af133ec37e93ea32d1203959eba8f2304b3de98e`。已审原字段 `0x8dd85` 从种子 0x20 变为最终 0x00，RAM 同字段为 0x00，UI English；最终文件与 English 即时文件并非逐字节相同，其他变化不推定日期已确认。原文件 cold boot 重载尚未验。
- 同一 guest user monotonic ns 配对分析：AP104 78 组完成最大 50011.503 ms（该轮在 417 秒复现 unfetched）；AP105 182 组完成最大 2839.466 ms、p95 1097.889 ms、没有配对超过原 5000 ms。此范围是成功 dynamic QID 返回到显式完成返回的保守上界，不是原 `ReceiveDrawComp` 入口直接计时；两轮绘制工作量、观测区间不同，不能给同任务倍数加速。AP105 未见 unfetched、-1018、新 GPE reject、guest exception/assert；82xx 命令数为日志计数，未过滤重复行。
- 保存与退出：原 API16 guest ack + 原字双核验通过，耗时 1.317 秒；原字 `000b00b4fd7bbba9fd030091f35301a9`，无 host 直接改原 guest code；QEMU 正常退出。
- 下一精确门：新独占运行中先在 Language English 后关闭 MENU，实际截图确认关闭，再原生 idle >=60 秒并对比同代 RAM/文件；另在可核对的原生 UI 路径完成日期原值 OK 和文件重载。当前 **不标 ready-for-TRY2**。

回执：`work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/runs/vmopt-20261103-ap105-baseline-45d987f9/receipt.json`；性能：`work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/vmopt-20261103-performance-comparison.json`。
