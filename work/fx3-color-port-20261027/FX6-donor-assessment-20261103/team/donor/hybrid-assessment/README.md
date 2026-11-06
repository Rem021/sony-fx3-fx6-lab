# FX3 内核 + FX6 上层：冻结 CPIO 纠正预检

2026-11-03。**纠正：首轮“FX3 客体缺 `libopus.so.0`/`libSoundTouch.so.1`”是错误结论。** 首轮用了不完整的目录投影；固定 `guest.cpio` 中两库和 SONAME 符号链接都存在。旧 [README-v1-projection.md](README-v1-projection.md)、`preflight-receipt.json`、`migration-manifest.json` 和 [preflight_projection_v1.py](preflight_projection_v1.py) 保留为**已否定的历史回执**，不得再用于候选判断。现在 [preflight.py](preflight.py) 委托实际 CPIO 工具 [actual_cpio_preflight.py](actual_cpio_preflight.py)。本轮只读固件与客体原件；没有构建、执行或部署混合候选。

## 复现与原件

在项目根运行 `python3 -B work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/hybrid-assessment/preflight.py`。工具固定 CPIO SHA `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d`，独立核对全部 **1,140** 成员哈希，按客体 `LD_LIBRARY_PATH=/simulation:/usr/lib:/lib` 解析真实符号链接，解析 AArch64 ELF 动态导入、GNU version need/def 与每个强导入的版本要求，递归沿实际客体库追四个 FX6 根。复用的只读 newc 解析器 `coordinator-hybrid-review/audit.py` SHA `9b231574d229f375f99023157a48b344a14a0bc67eae7375b37e5833a8c7ca41`，其独立回执 SHA `367a584d11935cfaaac594be78b424184657b61ea8f18568732d3de91553ee03`；本工具另对每个动态符号建版本绑定，不执行目标程序。

当前逐项结果在 [actual-cpio-receipt.json](actual-cpio-receipt.json)（SHA `96742cf3ba840bd5f76d37dd76364371b2f150167e0f367de8396940f1c5c647`）；修订的[只读迁移 manifest](migration-manifest-v2.json) SHA `a3bc2d9d535c8745796dfb74ec8217672451764689a9a9178108005c2cce042d`。工具本体 SHA `e5dd8763a84a9aea27fda56e356c7c4557bf0b6e04bdab176f8a8943cb3d320a`。manifest 的次序仅声明候选边界；`appFw`/`libmpr` 的自然装载次序尚未由运行态证明。原 FX3 kernel、QEMU、完整 DTB、env、CPIO、Backup 和 helper 均保持冻结。

| 实际 FX3 CPIO 请求路径 | 链接解析实体 | 实体 SHA256 | 结论 |
| --- | --- | --- | --- |
| `/usr/lib/libopus.so.0` | `libopus.so.0.8.0` | `473c7182bfd47bbbcce4e377015bc9d6bbef554c4eda287ba6a31ecc34f4579a` | **存在** |
| `/usr/lib/libSoundTouch.so.1` | `libSoundTouch.so.1.0.0` | `d4abdc58ae1857d46791b7f8d3ebf0d822f03c5a8d343f3d975a98f0ff40522e` | **存在** |
| `/usr/lib/libObj.so` | 同名实体 | `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae` | FX3 后端存在，FX6 IM 运行 ABI 未证 |
| `/usr/lib/libstdc++.so.6` | `libstdc++.so.6.0.22` | `28f2d082aea5206c42ba15664f39e2eaf7febed8f6264305e7e16aa44c878389` | 路径/要求的符号版本可静态匹配 |
| `/lib/libc.so.6` | `libc-2.25.so` | `f9104526eb7e5d2ea533c1a209bb0b83e69367f569e4c966895c8e106e6382c9` | 路径/要求的符号版本可静态匹配 |

## 根与递归库：逐符号版本结果

`actual-cpio-receipt.json` 为**每个强导入**记录符号、请求版本、`verneed` 所指 SONAME、实际导出库及状态；弱导入单列计数。比如 FX6 IM 的 `_ZdlPvm@CXXABI_1.3.9` 明确要求 `libstdc++.so.6`，实际 FX3 `libstdc++.so.6.0.22` 导出同版本，`llvm-objdump -T` 另独立核对该例。无版本的 `Backup_read`/`osal_snd_sync_msg` 有 FX3 实体导出，但预载库会插入同名符号，**静态名称命中不能保证实际绑定对象、调用约定或行为**。

| FX6 根 | 实际 FX3 闭包节点 | 缺 `DT_NEEDED` 路径 | 强导入逐项静态匹配 | 未版本化且当前闭包/预载范围未闭合 | 版本化强导入未匹配 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `bootin.elf` | 12 | 0 | 428（根 54） | 0 | 0 |
| `im.elf` | 17 | 0 | 1,107（根 80） | 0 | 0 |
| `appFw.so` | 16 | 0 | 845（根 343） | 557（根 557） | 0 |
| `libmpr.so` | 10 | 0 | 667（根 349） | 141（根 141） | 0 |

计数含各根的递归客体库，根之间有重复，不可相加为独立符号数。`MATCHED_SYMBOL_VERSION_STATIC` 对无版本导入表示找到可见同名导出；对有版本导入另核对指定 SONAME 与版本。`appFw` 的 557 项（例如 `Fsys_Open`）及 `libmpr` 的 141 项没有在**各自独立** `DT_NEEDED` 闭包加 17 个预载中闭合，不能因此判实际链接失败：进程全局对象与后续 `dlopen` 未知。若假设 `appFw` 与 FX6 IM 同进程且 IM 依赖全局可见，原来 557 项中的 69 项有 IM 闭包候选（例如 `Backup_read`）；这一假设尚无自然装载回执。以上全是静态符号/版本证据，**不是 ABI、重定位、初始化或 AP 运行通过**。

## 实际 `LD_PRELOAD`、原字节守卫与运行器

固定 CPIO `/init` 第 288 行给 `bootin.elf` 配置 **17 个**预载库（完整有序路径、实际 SHA、已匹配构建来源和直接依赖在回执）；其直接 `DT_NEEDED` 路径均存在。仅凭文件名会认错版本：第 2 个 `fx3-capid-v1.so` 实为源码 `fx3-capid-v49-touch100.c`（SHA `8d65d6907c38e0f6767f7127e74de29e703e927aa0dc0be08deb9081d36bb7e7`）；第 3 个 `fx3-osd-headless-v5.so` 实为 v7-observe102；第 5 个 `fx3-preset-context-v2-screen.so` 实为 v6-save102；第 13 个 `fx3-ui-gate-v1.so` 实为 v11。其余未由本地构建回执绑定的源版本保持未知；所有 17 个**客体字节 SHA**均已记录。

| 顺序/角色 | 原码与固定输入 | 对 FX6 上层的界限 |
| --- | --- | --- |
| 首个功能性预载：`fx3-skd-hw-unavailable-v1.so` | 固定构建源码 SHA `2d0a30d5a1e56ca3cd1956c7c24af51d07ffd660832e635ff8d9ffb2a03669e8`：只在 `FX3_SKD_HW=unavailable-rom-v1`、调用者 `/usr/lib/libInfraSKD.so` 相对 `0x645ec`、`/dev/mem` 偏移 `0xffffb000` 等条件同时成立时回 ENODEV；固定 `/init` 第 288 行设此环境。 | 这是 FX3 硬件缺席模型的**条件功能路径**，并非已见 FX6 故障。沿用 FX3 `libInfraSKD` 可复用原调用点，但 FX6 AP 是否要求同一 SKD 能力未证；不能把软件缺硬件反馈当 FX6 功能正常。 |
| 首个通用 IPC 软件后端：`fx3-capid-v1.so` | 实字节 SHA `cd51ea7b3347ccb8bd8d0cdd72b096936f0a226c142575f41a24cc018948156e`；对应 v49 源码第 40–42、604–605 行在第一次 `osal_snd_msg` 时解析六个 FX3 OSAL 函数，缺任一项会 `_exit(126)`。六个函数在固定 FX3 `libosal_uipc.so` 的动态导出可找到；`FX3_CAPID_STORAGE=reserved-v1` 打开保留 RAM 模型。 | **函数存在不等于消息协议兼容**。FX6 首个实际请求的 dst/type/长度/返回必须只读观测并与 FX3 模型契约核对；偏差即停，不合成成功回复。 |
| 首个有确定原字失配的诊断探针：`fx3-preset-context-v2-screen.so` | 实字节 SHA `eb55680196806fb86958d632c6aed939eae91aa1ef928690a4a7d21d6a76c170`；源码第 43–47 行先检查 48 个 FX3 `appFw` 指令字。FX3 48/48、FX6 0/48；首个相对 VA `0x2dca610`、预期 `0xa9bb7bfd`，FX6 PT_LOAD 文件 `0x2dba610` 实值 `0x00000255`。 | 若 FX6 `appFw` 到达该 `dlopen` 包装器且 `FX3_DISPLAY_OBSERVE=passive-v1`，将**条件性**打印 `FX3_PRESET_CONTEXT_BIND_REJECT` 并跳过观察探针；不会据此认定 AP 退出。未有 FX6 guest 日志。 |
| 另一只读观察器：`fx3-ui-gate-v1.so` | 实为源码 v11 SHA `bb6650761764f2990650243b9e81ef7f4434c165faef8701afa1033cb961261c`；第 106–114 行在安装 60 个点前逐字比对，FX3 60/60、FX6 2/60；首点相对 VA/文件 `0x16f2220`，预期 `0xd10cc3ff`，FX6 `0xf9400bf3`。 | 其原码失配会条件性 `FX3_UI_GATE_BIND_FAIL` 并不安装观察点；源码标记 `observed_only=1`，不是 FX6 UI 功能失败的证据。 |

`/init` 第 202、205、208 行先以 9 个预载依次执行 loader `--verify`、`--list`、BusyBox `true`；第 211–214 行三者任一 RC 非零就进入 `FX3_TRACE_ABI_NOT_READY` 停止分支，**早于**第 288 行 `bootin.elf`。`trial_log_v4_mss.py` SHA `4d57629fc8bf1c8d158bfcf101915b9edd626f7bfb11c55fc78fe634ef7d6645` 把 `FX3_PRESET_CONTEXT_BIND_REJECT` 列为兼容保护/故障标记；对 FX6 appFw 的条件诊断拒绝不能误报为 AP 进程失败，也不能在固定运行器中静默忽略。已封存的 host `run_trial_v14_final_receipt.py` SHA `4404ef83cebe00b5f3598faadb020cc06798048a58c3c4c35fb1b6b153a7ad58` 第 26 行导入该监控器，第 378–379/535–536 行遇 `log_monitor.failure` 会早停；这说明若沿用这一 runner，诊断标记会影响实验判定，但不证明本轮有实际 guest 事件。原固定环境和 helper 不能改，本轮未运行 guest。

## 有界软件适配与下一确切观测

1. **先封闭装载门：** 若以后由独占 runtime owner 在获准的隔离候选中验证，仅替换 FX6 `bootin`/`im` 软件入口，先读第 202/205/208 三个 RC 与第 211 行是否停止；保留固定 FX3 kernel、DTB、QEMU、环境、Backup、helper。`LD_PRELOAD` 实际 17 项和逐项 SHA 必须一并核验。任何 loader 版本/强符号失败立即停；静态零缺口不能预写成功值。
2. **功能路径按实际第一条消息审：** 在不执行 FX6 AV/CP、也不伪造相机/像素的边界，若进入 FX6 IM/AP，就只读记录首个 `osal_snd_msg` 的调用来源、dst、type、长度、返回及是否命中 FX3 CAPID 模型；先由真实输入决定适配范围。保留 FX3 本地 OSAL 与 Backup，FX6 CHAPLIN 记录不得覆盖 FX3 Backup。`libObj`、资源、LIRO/AV 全局注册和自然装载仍未知。
3. **诊断点按版本隔离：** 对 FX6 appFw 不能套用 FX3 的 48/60 个硬编码 PC。后续若确需相同观测，应以 FX6 原指令、调用条件与受限只读输出另建版本化观察器并保留完整拒绝门；当前固定 helper/runner 不动。观察器拒绝与进程退出、菜单显示、电影 RAW/ISP 必须分列回执。

本轮修正的第一结论是**实际 CPIO 路径和版本化强符号未显出缺口**；第一确定的 FX6 原字失配是 FX3 观察探针，第一功能性风险是预载的 FX3 硬件/IPC 模型与 FX6 消息语义未知。需要下一次独占运行时，只验证 loader 三 RC 与首个真实软件消息，并在首故障处停止；本报告没有给出完整 FX6 启动或色彩移植通过结论。
