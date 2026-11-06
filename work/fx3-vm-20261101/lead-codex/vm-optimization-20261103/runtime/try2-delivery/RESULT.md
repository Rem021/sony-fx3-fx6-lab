# TRY2 本机网页试用交付回执（2026-11-03）

## 结论

已提供 [中文双击入口](../../../../../../outputs/fx3-vm-trial/FX3菜单TRY2.command)和[使用说明](../../../../../../outputs/fx3-vm-trial/TRY2-使用说明.md)，引用本目录已实跑的 `run_trial_v4_try2.py`；旧 TRY1 入口、候选与历史运行未覆盖。实际 Orca 内置浏览器在新 TRY2 轮看到了待机画面，单次 MENU 后看到了完整彩色图标、橙色焦点和 `English`，再点网页“结束试用”，收尾通过。用户正在等待运行权，主协调要求交还双锁，因此独立标准 Ctrl-C 网页轮未另启；本回执不把全部退出路径或无限稳定性记为通过。

## 候选和精确差异

- 基线是已通过自然 English 保存与 generation 4 副本冷重载的 `lifecycle-repair/vmopt-20261103-reload-v1/candidate.json`，SHA256 `51ad68c282ad7e6adb88e31b25d714a55279dc35cd125dcbb1fd1a1c2e651687`。固定 Backup 副本 SHA256 `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f`；原种子未写。
- 新 [TRY2 候选](vmopt-20261103-try2-v1/candidate.json) SHA256 `c7691dcc0cb35fb9aabf471b3859da2b54c19bde4b77b9446e14d293d67d5487`，CPIO SHA256 `502f2be1b575d2031ba9ee999cc23698795a69110297768c3588efb6ccc64caa`。继承 OSD timer 修复、AP105 GPE perf、软件 LDEC、English 固定副本；没有改变原厂 5000 ms 接收预算。
- 复用历史 `prepare_candidate104_v2.py` 的 readiness-before-CP-bind 方案。相对 reload-v1，CPIO 仅修改 `init` 与新增 `simulation/fx3-file100-observer-v2`；旧 `fx3-file100-observer-v1` late startup 两行移除。新 `init` 在 `FX3_BACKUP_CP_INSMOD_BEGIN` 前启动 v2，并最多等待 200 × 50 ms，验证 `F100FILE_READY_V2`、匹配实际 PID 且进程仍存活后才继续 CP bind；失败保持可见错误。原 shutdown 脚本及其余 CPIO member 均相同，DTB 只更改 `linux,initrd-end`。详见 [构建回执](vmopt-20261103-try2-v1/build-receipt.json)与 `init-reviewed.sh`；CPIO 审计与 `/bin/sh -n` 通过。
- v2 observer SHA256 `044d08549217523c645035e02ae74b1e76b73db17a61d13b0ff4ecd05a3987e0`。本轮正常启动的 serial 同时出现 `FX3_FILE103_READY_CONFIRMED` 与 `FX3_SYNC100_BACKEND_BOUND`，新绑定未首帧退出轮实际核对了此顺序。

## 网页与退出实跑

| 运行 | 实际阶段与输入 | 结果 |
|---|---|
| [pre-bind](runs/try2-d33420b7/receipt.json) | QMP `cont` 后立即退出，serial 0 B，未绑定、无首帧；0 键、0.69 s | 原 API16/无待处理 request 直接核验；health/lifecycle true，QEMU exit 0、reaped、PID 消失、SHA 不变、双锁 free。 |
| [诊断 Ctrl-C](runs/try2-f32318fb/receipt.json) | 首版日志筛选遗漏 `FX3_SYNC100_BACKEND_BOUND`，虽然原 serial 已绑定且未首帧，phase 判定未命中；43.48 s，0 键 | 主动 Ctrl-C 后 guest ack/API16/退出/两锁通过，`lifecycle_pass=true`；按未命中指定阶段记 `health_pass=false`。已修日志筛选并复跑下一行，保留首错。此项不等于独立标准 Ctrl-C 网页轮。 |
| [bound-before-first-frame](runs/try2-42c11c0e/receipt.json) | serial 实见 readiness 和 backend bound，尚无 `trial-frame.png`；4.14 s，0 键 | `requested_exit_phase_hit=true`、guest ack/API16/退出/两锁通过，health/lifecycle true。 |
| [正常网页轮](runs/try2-d6ae624b/receipt.json) | 本机浏览器打开 `127.0.0.1:8766`，待机截图；实际看图后单次网页 MENU 100 ms；更新后截图；网页“结束试用”；89.72 s，1/30 键 | `health_pass=true`、`lifecycle_pass=true`、全部 required markers true；guest ack/API16、QEMU exit 0、reaped、PID 消失、输入 SHA 不变、两锁 free。 |

正常网页轮截图：[待机](runs/try2-d6ae624b/browser-standby.png)、[MENU 后 English/图标/焦点](runs/try2-d6ae624b/browser-menu-step1.png)。二图均为实际 Orca 浏览器页面截图并经图像工具目视检查。step 1 的原生提交帧为 sequence 201、epoch 1、FNV64 `0x19abb616faf34124`、PNG SHA256 `2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e`，见 [step readback](runs/try2-d6ae624b/trial-step-readbacks.json)；浏览器在稍后的 sequence 242 截图中可见橙色焦点和 English。原生 ring 身份、epoch、FNV 与非均匀像素 gate 保留；HTTP 线程只提交单个待处理键，不访问 QMP。七键白名单、100 ms、最多 30 键仍在 runner 与输入 gate 中执行。正常网页轮无 `unfetched`、OSD allocation deadline 或日志检测到的断言；这只覆盖该 89.72 s 区间。

正常结束后独立再次检查 QEMU/runner 进程均不存在，原两锁 `.run.lock` 均可非阻塞获取。浏览器测试页随后关闭；没有留下 guest 占锁。每轮 `receipt.json` 保存 QEMU PID、退出码、reap、API16、所有输入 hash 与两锁回执。

## 使用和限制

双击 `.command` 会在终端运行已经验收的 runner，默认 `http://127.0.0.1:8765`、15 分钟、30 键；本机 URL 只在会话运行时可用。网页结束按钮已验，Ctrl-C 收尾逻辑在诊断轮走通但独立标准网页轮未验；若出现异常应以当轮回执判断，不能仅凭源码宣称通过。锁占用时新 runner 提示“已有 FX3 试用或验证正在运行”，不抢锁、不杀进程。`.command` 通过 `zsh -n` 静态检查，未再启动 guest 做 Finder 双击轮，以便交还运行权。回退是保留的旧 [TRY1 说明](../../../../../../outputs/fx3-vm-trial/README.md#旧-try1-入口)。

已固定所有 runner/web/log/CPIO/seed/依赖 SHA 于 [交付清单](delivery-receipt.json)；正常网页轮 `observer-source/` 与当前依赖 SHA 再核对一致。先前测过的 `serial_snapshot.py`、`guarded_reject.py` 未额外换入本轮已验 web runner；该 runner 自身沿用增量 serial 完整检查及最新 ring slot 读取。没有提高 preferred、改原 STATE、宣称实体相机或拍摄功能通过。
