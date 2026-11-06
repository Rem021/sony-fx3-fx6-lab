# FX6 在固定 FX3 虚拟机上开机：三条路线与当前门槛

**结论：本轮没有取得 FX6 开机或可用菜单；目标仍未完成。** 现有三条路线分别被提供方安全拒绝、固定 helper 地址冲突、以及固定平台缺少块设备/启动参数所阻断。没有可安全执行的下一步；继续推进需要用户/协调器先解除或重新授权其中一条路线。本轮只做只读证据核对，没有启动 VM、QEMU、guest、浏览器、服务或设备。

## 1. 最近一次 FX6 上层的实际停点

- 运行：`team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/runs/guest-veneer-33d090b1`
- `stop=unknown_loader_return`，host 时间 38.577654 s，`qemu_exit=0`，`qemu_reaped=true`，双锁 free，`inputs_unchanged=true`。
- `cleanup.API16_restored=false`，原因 `diagnostic_no_guest_resume_after_Z1_removal` / `API16_restore_skipped_to_preserve_fault_stop=true`；`lifecycle_healthy=false`，`diagnostic_captured=false`。
- 记录：vCPU 03 在 `appFw.so / Application_System_Init` dispatch；vCPU 02 在 `im` dlsym 返回 `pc=0x405f10`，`x0=0x7f0377d044`，TLS 同为 `0x7f837ff740`；观察器把该行标为 `not_same_im_record_tls`，但没有记录 dlsym 时的 x22，`mapping.ap=null`、`gate_installed=false`。
- 这只能说明旧观察器拒绝归属；**不能**据此说 guest loader 实际成功或失败，也不能把非零 x0 当作 AP/bridge 执行证明。

## 2. 三条路线

### A. FX3 内核 + FX6 上层（guest veneer / 精确装载）

**阻断：提供方安全拒绝 + 当前源码身份不一致。**

- 提供方消息 `msg_chaterr_5a1b17d63a36b951f0927f33`：`This content was flagged for possible cybersecurity risk`；任务 `task_32e1aa43202b` 仍为 dispatched，未完成，未重试，未换模型/未绕过。
- 当前封存 33 项中 30 项匹配；不一致：`guest_probe.py`、`run_guest_once.py`、`test_guest_host.py`，另有未封存 `test_im_inherited.py`。
- 实际摘要三方不同：
  - runner 常量 `GUEST_PROBE_SHA=6f40e30e62fde9eddd74d547da8d6f3ab0d13be59413204632a232bc1d449aec`
  - 当前 `guest_probe.py` 实际 `f10defaad641b3565d49c78225e84c9bcc4d60dabe4e7fdc70a82883de7c0842`
  - 历史运行/旧测试 probe `bb5c5e18b98cced5f86d4a57ff5487138d9cbc62ef7d98e4dfb4a1164db27921`
- `run_guest_once.py` 第 97–98 行要求旧测试回执与当前 probe 都等于 `6f40…`；该条件当前静态为假，因此当前候选不能通过自身身份门。当前 `guest_probe.py` 新增了 `record_x22`/TLS 门，但未重新封存，也没有新的宿主/真实运行回执。
- 结论：在提供方阻塞解除并重新封存、重跑宿主回归之前，不能执行该候选；本轮没有修复、重封存或重试。

### B. FX6 原内核 + 固定 FX3 CPIO/Userspace

**阻断：固定 FX3 CP helper 硬编码 FX3 `pcidma_transfer_async` 地址，与 FX6 内核布局冲突。**

- 唯一短轮：`fx6-boot-readiness/early-kernel/runs/fixed-fx3-4571c53b`，receipt `eb3990eb…4830`，serial `dfd0ef29…2be8`。
- 实际边界：`FX3_DEVTMPFS_RC=0`、首模块 `devno.ko=0`、LDEC 自检和 FILE100 ready 之后，CP helper 两次 `binding_failure` / `init_module -7`，`insmod` RC7，未进入 AP。
- 原因（现有静态合同）：固定 helper 要求 `pcidma_transfer_async` 链接地址恰为 FX3 `0xffffff80083220c8`；FX6 原 Image 的该导出在 `0xffffff8008322f70`，而 `0xffffff80083220c8` 在 FX6 中落在 `watchdog_touch_exception` 代码。helper 还有两处 FX3 绝对 fallback 地址，分别与 FX6 `subsys_new_mm`、`watchdog_touch_exception` 冲突；直接改一处会留下错误跳转/破坏 watchdog 的风险。
- 现有 README 记录：最小 firmware diff `minimal_firmware_diff_feasible_now=false`；需要独立兼容函数、重布局、恢复语义与完整 DMA/CP 合同，已超出有界单点修改。
- 结论：这条路线若要继续，必须另行授权一个新的 firmware/helper 候选；本轮没有生成 patch 或 CPIO。

### C. FX6 自带 initrd/rootfs 直接装入固定平台

**新核对结论：不能直接替代固定 CPIO；需要块设备/启动参数变更。**

- FX6 供体自带：
  - `fat-files/nflasha3/initrd.img`：ext2，5,661,696 B，SHA `fc97d08139b9ec20a1a511e608f6ed4f55d71f204472467463fdc181d2973da6`
  - `fat-files/nflasha1/boot/initrd.img`：Squashfs，6,914,048 B，SHA `5032fc777296e3e1f1b3bb6c7f2f249f18ee135f3c2424f83b7b6fff1e5831c0`
  - `fat-files/nflasha3/vmlinux.bin`：FX6 Image，SHA `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9`
- 解出的 FX6 initrd：`nested-files/nflasha3-initrd/sbin/init`（735 B，SHA `c83de1ab…ac5e`）挂载并依赖 `/dev/nflasha2/3/7/8/10/11/12/15/18`、`/setting`、`/system`、`/cp`、`/usr`；`insmod_drv1/2` 加载 FX6 `devno/dma330/emmc/pcieatu/ldec/osal_utm/osal_uipc/backup/...` 模块。
- 固定运行命令（已验证的 `fixed-fx3-4571c53b/command.json`）只有 `-kernel FX6 Image`、`-device loader, guest.cpio`、`-device loader, guest.dtb`；**没有 `-drive`、没有 `-initrd`、没有 `-append`**。固定 DTB 的 bootargs 为 `rdinit=/init init=/init ...`，`linux,initrd-start/end` 指向 loader 的 CPIO 区域。
- 因此 FX6 的 ext2/Squashfs initrd 不能作为现有 loader 的 CPIO 直接启动。即使把解出的 FX6 rootfs 重新打包成 CPIO，`/init` 仍明确依赖 `/dev/nflasha*`、`/setting`、`/system`、`/usr` 等块设备挂载；固定 QEMU 没有对应的块设备/驱动，按原脚本无法在无改动的情况下成立。本轮没有实际运行这个候选，因此这里只判定“不能在固定平台无改动直接启动”，不声称已观察到某个具体挂载错误。要让它运行必须加块设备/改 DTB 或改 FX6 init/rootfs，这已改变当前“固定 FX3 平台”的边界，不能算本轮可用的无变更路线。

## 3. 决策与下一步

- 三条路线中，**A 是唯一保留 FX3 内核 + FX6 上层目标的路线的执行候选**，但被提供方安全拒绝和当前源码身份不一致双重阻断。
- B 需要一个明确授权的 firmware/helper 新候选；现有固定 helper 无法安全适配，不能靠单点改地址。
- C 需要平台/启动参数或 FX6 rootfs 软件改动，不能作为“固定平台直接启动”的捷径。
- **本轮没有可安全执行且能改变“未开机”结论的动作。** 下一步需要用户/协调器选择：
  1. 按提供方要求处理安全审查/授权（不是技术重试，也不是换模型绕过）；
  2. 或明确授权 B 的新 firmware/helper 候选（含 CPIO/恢复策略）；
  3. 或明确放宽固定平台边界，允许 C 的块设备/DTB/rootfs 变更。

目标保持 active，未完成；本轮没有启动 VM、部署、设备或修改任何共享候选/历史回执。证据索引见 `EVIDENCE.json`，`SHA256SUMS` 封存本目录。
