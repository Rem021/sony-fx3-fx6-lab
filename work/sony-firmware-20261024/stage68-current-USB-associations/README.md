# FX3 当前缓存身份与标准查询处理范围（2026-10-26）

已取回 Windows 新的五件脱敏回执：在 17:15:31 UTC 的一次 CIM 缓存查询中，出现一个与此前 FX3 USB 根实例摘要相同的节点，以及三个 Sony DSC 磁盘节点。四者均为 `Present=True / Status=OK / ConfigManagerErrorCode=0`；该 USB 节点的实际缓存 VID/PID 为 `054C:0DA1`。这补充了“当前缓存中出现相关节点”的证据，没有读取机身型号、固件版本或协议响应。

## 已确认与尚未确认

- 根节点的描述仍是通用 USB 大容量存储设备；关联依据为完整实例 ID 的相同 SHA256，而非仅凭 VID/PID 猜测。磁盘节点自己的 VID/PID 缺失，未从根节点补填。
- 这是一个 USB 节点加三个磁盘节点的计数；物理相机台数没有通过本轮查询独立核定，三个磁盘节点不能理解为三台相机。
- 本轮 Windows 代理把三个磁盘节点视为“不唯一”后停止，没有调用 PnPUtil。当前父子关系、接口启用情况、Started、驱动 INF/版本/提供者/签名者仍是 UNKNOWN。
- 前一轮精确硬件 ID 筛选在更早时间返回零匹配。本轮 CIM 在较晚时间返回 Present=True。原因未查明，不删除旧结果，不声称筛选器故障、物理断线或模式自动变化。
- 后续任务仅澄清：USB 层根节点恰好唯一时，可以继续缓存父子关系查询；其全部磁盘子节点如实枚举。没有放宽“主动诊断必须绑定明确目标”的条件，不能任意挑一个磁盘接口。

[Microsoft PnPUtil 文档](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/pnputil-command-syntax)区分硬件/兼容 ID 的 `/deviceid` 与实例 ID 的 `/instanceid`，并提供以指定根为起点的设备树查询。[USBSTOR 标识说明](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/identifiers-generated-by-usbstor-sys)说明系统可以为每个逻辑单元建立设备对象，磁盘标识来自 SCSI inquiry 数据。因此，磁盘行数不能直接当作物理设备数；当前父子关系仍需新快照证明。两页于本轮重新核对。

## 标准查询的原字节离线核对

对固定哈希的官方 7.02 `usbg_storage.ko` 原始 `inquiry_std`（632 字节）进行了 40 组有指令及内存范围限制的 ARM64 仿真。仅在客体 RAM 中应用该函数唯一的 CALL26 重定位，调用同一原固件内核的原 `memcpy` 指令；没有用返回值适配器或复制函数替身。

输入为三份原始初始身份模板，以及声明的长度/容量/方向/页码/control 字段，均是人工 RAM 测试上下文。21 组返回命令状态 0，另外 19 组按预期返回长度或字段错误；所有指令和内存守卫通过。正常标准页仅复制 `min(请求长度, 配置模板长度)` 字节，并更新命令返回状态、传输长度和逐单元 sense RAM。这说明即使以后只发查询，也不能把它描述为“机内完全不变”。

范围从已分派的函数入口开始：没有运行 USB 命令分派、扩展命令处理、USB 传输、实际驱动实例或完整 Linux。没有读取真实 LUN、动态身份模板、存储卡，也没有检验实际 Windows 存储栈。原始模板的 revision 是 `1.00`，不能用普通 INQUIRY 证明机身固件为 `7.02`。本轮仿真不构成刷写安全、救砖或 H.265 主录验收。

## 后续缓存任务

`WINDOWS_ROOT_CLARIFICATION.txt` 已通过 UU 文件传输到 Windows 普通系统 C 盘的本轮结果根目录，界面确认发送成功、累计 61 件文件。由于远程键盘未把文字送入 Windows 输入框，已请求用户在原 FX3 Codex 会话发送读取指令；截至本阶段封存，尚未观察到新消息或后续执行结果。

目标输出另存 `C:/Users/owo/Documents/Codex/2026-10-16/rea-2/outputs/fx3-current-root-cache-20261026T172200Z/`，不得覆盖旧报告。任务限定按本次 CIM 私有根 ID 做 `/connected /instanceid` 和根设备树查询，再查询其当前磁盘子节点。最多 16 个相关节点；原始实例 ID、序列和接口路径留在 Windows private，公开结果仅含摘要与必要元数据。

## 文件与授权

- [Windows 当前身份回执](from-windows-presence/receipt.json)、[节点摘要](from-windows-presence/nodes.json)、[命令记录](from-windows-presence/commands.json)。私有原始文件只有 Windows 报告的哈希，未传回，不能声称已独立验证其内容。
- [受限原函数结果](inquiry-handler-emulation.json)、[复核脚本](review_stage68.py)、[完成证据复核](completed-evidence-review.json)。
- [后续任务原文](WINDOWS_ROOT_CLARIFICATION.txt)、[阶段封存](final-receipt.json)、[完整目标状态](goal-status-after.json)。后续结果不写回本阶段。

相机授权仍仅缓存 PnP：设备接口句柄和相机命令均为零；没有认证、切模式、驱动或权限变更、读卡素材、上传模块、WBI 或刷写。Windows 缓存盘点、原函数 RAM 仿真、实际协议响应、同机备份/恢复、H.265 主录分别验收。持续目标的全部 16 项要求保留，目标未完成，持久写入不放行。
