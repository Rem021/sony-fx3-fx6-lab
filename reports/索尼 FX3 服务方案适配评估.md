# 把现有服务框架适配到 FX3

核查日期：2026-10-25。**可以借鉴 A7C II／REA／PMCA 的框架，重建经典 ILME-FX3 7.02 专用方案；现成安装器和 Recovery 不能直接使用，也尚未建立救砖保障。** 这次依据已从同系列推测推进到协议、实际 worker ELF 和 FX3 原厂加载分支的逐项对照。用户菜单确认7.02，Windows 缓存确认普通 MSC `054C:0DA1`；实机程序哈希、唯一机身绑定及服务入口仍未采集或验收。([菜单确认](../work/sony-firmware-20261024/stage7-entry/menu-version-confirmation.json)、[缓存盘点](../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/sony-pnp-inventory.json))

## 可复用机制 必须重建目标约束

| 层次 | 可复用的方法 | FX3 必须补齐的部分 |
|---|---|---|
| 主机通信 | 分层封包、解析、有界超时和错误停止 | 型号／身份、端点、认证、回包边界、退出语义 |
| 原生 worker | ELF 初始化、直接 syscall、请求／结果通道 | FX3 命令路由、ABI、权限、文件白名单及编译产物 |
| 检查点与文件恢复 | 健康原件、同机绑定、现场旧字节核对、完整读回 | 7.02 文件／设置范围、哈希、窗口和实际运行内容验证 |
| WBI 与重启 | 先查状态、限定接口、写后核对 | FX3 sysfs／分区映射、失效操作及冷启动条件 |

以上是[源码适配评估](<../research_notes/索尼 FX3 服务方案适配评估/host_portability.md>)，不是 FX3 实测通过清单。不能通过改 PID、删哈希门禁或放宽型号检查补出这些能力。

## 普通 MSC 与服务认证是两种传输能力

PMCA 的 Sony MSC 请求可经 SCSI 透传发送，Windows 原生 USBSTOR／SPTI 因而具有候选承载基础；服务认证另需 USB vendor control 和裸 bulk，现有原生 MSC 适配器不提供这些接口。现在不能为了普通诊断先换驱动，也不能把 SCSI 承载能力当作 Senser 已可用。([固定版 Sony 协议](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L83-L112)、[认证接口](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L890-L936))

入口名字还隐藏了额外操作：`MscDevice(driver).getDeviceInfo()` 正常路径是构造时一次 TEST UNIT READY，再两次 INQUIRY，共三条 SCSI 命令。A7C II 初始查询因两次构造及 Sony 查询，无重试基线已达六条；异常分支还须分别审计。OUT 请求不自动等于闪存写入，“info”也不自动等于一次无副作用查询。新的[声明式兼容契约](../work/sony-firmware-20261024/stage8-adaptation/host/compatibility-contract.json)因此保留所有主动能力为 false，未知服务参数为空。([构造与查询原文](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/__init__.py#L23-L64))

## 实际 ELF 支持重建 不代表现成模块能执行

本轮静态检查了上游实际 `installer.so` 和 `wbi.so`：均为 AArch64 共享 ELF，带 `DT_INIT`，没有动态外部导入；源码用直接 Linux syscall。FX3 原厂 `libJiritsu.so` 又确有特定 `libJit.so` 路径的标准 `dlopen(path,1)` 分支。**这支持加载模型相容的工程判断，尚未证明服务可达、模块获准加载或取得所需权限。** syscall、结构布局、外层命令15–18的完整映射仍需目标验证。([两侧原字节与 ELF 审计](../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)、[固定 worker 源码](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/installer.c))

现成 installer 内嵌 A7C II 原程序哈希，与 FX3 官方原件不符；runtime 探针也有 A7C II 固定偏移。正确方向是生成 FX3 专用 manifest、请求／结果 ABI 和最小 worker，保留拒绝未知现场的门禁。既有两文件 checkpoint 若未纳入日后实际拟改的库，便不覆盖该库；这不表示已确定必须改 `libmpr.so`。([二进制绑定收据](../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)、[固定 runtime](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/runtime.c))

## 回滚与检查点仍依赖可重新进入的通道

可迁移的核心是修改前健康原件、同机绑定、等长 current→target 差异、原位写后读回。现有 rollback 只反向处理当前 worker 的本批窗口；后续异常不会自动撤销此前全部批次和设置，fsync 也不是多文件断电原子提交。若服务或文件系统不可用，checkpoint 无法开始恢复。官方 DAT 可作版本参考，不能冒充这台机身的健康备份。([恢复拆批](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointworker.py#L5-L51)、[恢复阶段](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L180-L208))

A7C II WBI worker 检查 `image_mode=2`、`image_dev=*wbi4` 后才写 sysfs。FX3 已找到的 nflasha5／`invl` 分支与此尚未建立映射；这既不是兼容证明，也不是不兼容证明，不应猜改 guard 或替换为裸分区写入。#31 新增相似不可启动反馈仍无公开救回结局和共同根因，不能据此计算概率。([固定 WBI](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/camera_runtime/native/wbi.c)、[#31 原线程](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31))

## 先形成 FX3 诊断证据 再扩大恢复承诺

接下来可继续离线闭合命令与 ABI，审计单目标、固定白名单的最小诊断方案。实机阶段另需逐项验证普通查询、服务认证与退出、最小模块及文件读回；在任何持久修改前取得健康检查点，并证明拟改范围的真实原字节恢复、完整读回和冷启动一致。正常开机能进服务与主应用失效后仍可进入，必须分别验收，不能要求主力机先造砖来取证。

HD420 10bit、16Mbps、29.97fps 仍只有既有离线参数链证据，新适配审计没有证明硬件编码或成片；后续还需真实 Start、码流、音画时序和长录验收。ZV-E1 刷成 FX3 的原始设想也未获验证。当前交付是可复核的适配依据和禁用能力契约，没有生成刷写工具、原生执行或持久写入放行。([既有 HEVC 复核](<索尼 FX3 双机协作与HD HEVC仿真复核.md>)、[本轮收据](../work/sony-firmware-20261024/stage8-adaptation/final-receipt.json))
