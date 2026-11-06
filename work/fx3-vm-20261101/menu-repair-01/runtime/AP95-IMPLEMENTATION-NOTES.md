# AP95 恢复点（2026-11-02）

仍同一唯一运行持有者 task_bf4f4211be76 / ctx_ee4f6943c8d7，worker6cbe29fd-fb24-4199-bba8-b8ad99383477。未发送worker_done，整条运行链仍由Lead调度。

Lead msg_8162589b2b22要求AP95宿主逐步白名单计划v2，最多30步，软件41df控制页step/key/hold，逐步实际查看PNG后自主选六个已审计键；删除(C4)等独立key-delete-c4审计。AP94-r4已全300s封存，详见AP94-IMPLEMENTATION-NOTES和报告。

已创建：
- helpers/fx3-input95-hoststep-v1.h：30步、6键+调用者受控可选delete参数、50..200ms hold、准确原20B包。
- helpers/fx3-rm-key-gate-v4-hoststep.inc：真实keyworker只在新step时发送一次down/up，显式hold，done回执；HP95_DELETE_KEY默认0。保持原cache只读、native OSAL ownership。
- helpers/fx3-rm-empty-provider-v5-hoststep.c/.so/-build.json：RM corev2不改，仅新输入协议；交叉编译通过，delete禁用，尚未打入候选/未运行。
- gate_input95.py：同本地UnixGDB物理模式，只写控制页+8的12B命令，必须读回/guestdone；最多30步、六键、50..200ms，记录每步画面描述和理由。
- key_readback95.py：仅PNG前缀ap95，原current-frame/tuple/nativeSHA规则不变。
- run_candidate95.py：同原bounded驱动，改新ready/phaseA/step文件协议；取消自动首次UP，完全读取本run ap95-next-key.json人工放行（authorization msg_8162589b2b22，step/key字符串/hold_ms整数/observed_page/reason非空），每步+2s物理PNG，间隔>=4s。30步上限，unknown/新拒绝/fatal即正常QMP退出。尚未运行。
- helpers/check-hoststep95-core.c/.log：ASan/UBSan六键/30步/时长/未知/待审计delete拒绝通过。
- helpers/check-hoststep95-worker.c/.log：真实新keyworker在宿主fake控制页/native OSAL下执行，无命令不发送/重复不重放/两命令4 send/exact20B source/原receiverfree一次/未知第三命令零发送停止，ASan/UBSan通过。
- test_hoststep95.py，ap95-hoststep-host-test.json：mock GDB30步、strictdone、zero-write rejects、唯一12B新RAM。fixture ap95-hoststep-fixture 已存在，不盲目重跑断言创建脚本。
- ap95-hoststep-preparation.json，报告reports/.../ap95-host-step-input.md（已索引）。

当前没有QEMU，双锁已复核FREE。STATE current_candidate仍AP94-r4/last_run ap94r4object-37305ab2；准备完待在STATE标AP95等待审计。当前heartbeat PID14269仍运行、约19:01UTC到期，若后续活跃越过需新版本重启，不重复起两个。

删除审计到位后：完整读README+固定proof并重放--check（按审计脚本实际接口），核对批准码/原配置/source/UI路由；新建provider v6（不要改v5已测试源）显式HP95_DELETE_KEY，新guest/host测试加入delete但其他unknown仍拒绝。host gate InputGate构造接收delete_key参数，driver从candidate.host_step_contract.delete_key解析，最终manifest固定0x1f8或审计实际批准值。新建AP95 candidate从AP94-r4，替换simulation/fx3-rm-empty-provider-v3-setup.so成员body，GPE19r4/backend5/OSDv6/init快照skip均不变；required marker KEY93_READY改KEY95_READY。input control memrsv沿用，FDT仅initrd-end。实际运行前再检查消息和UUID/锁/无遗留QEMU。

AP95每步控制文件：ap95-next-key.json，含 step, key(如0x3), hold_ms:100, observed_page(实际PNG内容), reason(选择此键原因), authorization:msg_8162589b2b22。先等phaseA PNG实际查看再放行UP，随后Language图→ENTER→隐私ENTER→手机引导应按经审计删除键Set on the camera，避免ENTER进入QR循环；后续逐页真实看图选择。目标首次设置→拍摄待机→MENU→DOWN/DOWN/RIGHT/ENTER，各步PNG。最多30，遇新绘制/未知/致命立即封存+escalation。不能伪造运行中的旧plan状态。
