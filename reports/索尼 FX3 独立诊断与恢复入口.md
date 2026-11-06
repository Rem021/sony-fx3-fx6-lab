# FX3 7.02 的独立诊断与恢复入口

核查日期：2026-10-25。**可以继续研究 HD29.97 HEVC 主录，但尚不能安全放行持久写入。** 新证据定位到原厂服务库的本地文件处理分支；服务在主应用失效后能否从外部建立，仍未闭合。

用户现已亲自查看相机版本菜单并确认 **7.02**，与离线官方样本一致。这是[人工菜单确认](../work/sony-firmware-20261024/stage7-entry/menu-version-confirmation.json)，未读回实机程序哈希，也未采集唯一机身绑定。此前[Windows 缓存盘点](../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/sony-pnp-inventory.json)确认 ILME-FX3、`054C:0DA1`、已签名 Microsoft USBSTOR、OK／错误码0；它没有打开相机接口或验证恢复能力。

## 现成的“只读检查”需要逐条审计

PMCA 的 `info` 会真实访问设备；其 ExtCmd 路径还调用 updater `INIT` 后读取版本。Windows MSC 驱动以读写权限打开句柄并发送 SCSI 透传。句柄权限不等于已写入介质，`INIT` 在 FX3 7.02 上的内部副作用也未获证明，因此两者均不能当作缓存查询直接执行。([固定版 info 实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L231-L272)、[Windows 实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/windows/msc.py#L97-L131))

`serviceshell` 包括认证、服务重枚举、再次认证及退出，并开放写操作；已超出当前只准缓存盘点的授权。`updatershell` 则会上传机型专用 custom FDAT；是否持久刷写取决于载荷和设备更新器，不能只凭 `writeFirmware` 方法名断言。当前没有理由先替换正常的 USBSTOR 驱动。([两条入口的完整调用链](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L350-L423)、[服务入口](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L656-L710))

A7C II 的 `usbcheck` 在计时前就建立服务会话，包含认证、模式切换及身份数据读取；目标锁定 ILCE-7CM2 2.01／普通 PID `0E8A`，与本机 `0DA1` 不符。删掉型号门禁不会补出 FX3 支持。usbcheck 本身不上传 native worker；另行运行 native 探针才会上传临时文件、模块并执行；失败会话的“rescue”只是重新退出服务，不能算救砖。([usbcheck](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/desktopapp/usbcheck.py)、[会话实现](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/transport.py))

## 本地文件路径已找到 启动独立性仍待证明

官方 7.02 的 `libsencore.so` 中已定位包分派到文件 helper 的调用，最终落到本地 `open/read/write/ioctl`。这条已观察的子链没有主应用 IPC 转发；但初始化、认证及完整退出是否依赖其他进程，尚未证明。另有明确的 Host／Subsystem IPC 命令，不能把它们推广成每次文件操作的必经路径。`/appfw_infra` 在所查路径中用于日志；缺失的 `libSnr.so` 对应可失败的 Sonar 分支，目前没有全局启动必需的证据。([原始指令与调用点](../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)、[运行时静态索引](../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json))

磁盘启动脚本的 `init2` 默认 MODE 为3，在相应条件下先检查 BIS，否则仅当 `/setting/sen/smode` 为 `UU` 才后台启动 Senser。它说明存在先于正常主应用的候选路径，未证明故障后能从外部建立 UU，也未闭合 WBI 恢复是否重走脚本。服务及多数库与 appFw 同在 `/usr`，因此研究范围应先限于 rootfs／usr 完好、主应用局部失效。BIS 另有格式化 log 的分支，不能用作诊断试探。([启动脚本原文](../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json))

另已确认显式命令分支可向 `/dev/nflasha5` 写512字节，特定条件下头四字节为 `invl`。外部 opcode 尚未反解，**没有证据将它等同于 `auth.stop` 或普通退出的自动动作**。这项写入必须单独隔离。([WBI 上层调用与原字节](../work/sony-firmware-20261024/stage7-entry/firmware/wbi-caller-static.json))

## 公开成功案例的覆盖范围很窄

PMCA #715 确有 FX3A 2.02 在 M2 Mac 上进入 serviceshell、切到 PAL 并重启保持的成功结局；准确实测提交号未公开，语言解锁没有实际执行。它证明这一机型和操作的可行性，不能替代经典 FX3 7.02 的文件恢复或刷写验收。当前公开材料仍缺“经典 FX3＋7.02＋工具固定提交＋所需操作＋恢复结果”的完整组合。A7IV 的 UART／BootROM 研究也尚未适配到本机。([#715 原线程](https://github.com/ma1co/Sony-PMCA-RE/issues/715)、[适用性笔记](<../research_notes/索尼 FX3 独立诊断与恢复入口/compatibility.md>))

## 下一步先闭合最小诊断 再谈功能写入

离线下一步是把文件读写、模式变更、WBI 失效和退出各自绑定到明确命令码，并追完服务核心初始化、必须回调及失败分支。若确需主动查询，再单独审计只选定一台 FX3、固定 SCSI INQUIRY、限制长度和超时的最小探针；不夹带 INIT、认证、自动重试或驱动替换。本轮没有执行该探针，服务认证和切模式仍属后续独立实验。

持久写入之前，仍需实机原程序完整哈希、同机可信健康检查点，以及对应故障范围内可达、能退出并完成原字节恢复的 FX3 通道。正常状态能进服务不等于主应用失效后仍可救回；原样 no-op 也不能替代恢复验收。

HD420 10bit、16Mbps、29.97fps 已通过原固件参数构造层，优先路线仍是这条现有管线；尚缺模型到真实 Start、编码器接受、可解码成片及长录证据。60fps 能编码 HEVC 支持继续调查，但不能自行证明 HD30 的整条主录链。应先确保工具只执行已审计动作，再逐步增加功能证据；当前没有可安全刷入的 FX3 补丁。([HD420 实验回执](../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/hd420-16m-chain.json)、[此前复核](<索尼 FX3 双机协作与HD HEVC仿真复核.md>))

本轮只做公开源码审阅与官方样本静态分析，没有相机、USB、驱动或 GUI 操作。[主机工具](<../research_notes/索尼 FX3 独立诊断与恢复入口/host.md>)、[固件路径](<../research_notes/索尼 FX3 独立诊断与恢复入口/firmware.md>)、[适用性](<../research_notes/索尼 FX3 独立诊断与恢复入口/compatibility.md>)笔记及[本轮哈希清单](../work/sony-firmware-20261024/stage7-entry/final-receipt.json)保留来源与证据层级；它们不构成实机恢复证明。
