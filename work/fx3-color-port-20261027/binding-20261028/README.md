# FX3 色彩移植：原配置生产者、VFX 申请与同对象色彩提交

承接[原 SDK 与 DMA 链](../resource-20261028/README.md)。本轮恢复了对象 `+0x10d0` 的 acquire ID 生产路径，并继续上溯到生成资源配置号的原 `ImageParam_Sync.cpp` 指令。先前预填所有者 ID 的边界，已改为原资源选择器、代理和分配器实际执行。**正常拍摄模式的参数来源和主录像素归属仍未确认，尚无可正常刷入的修改固件。**

这里使用 FX3 7.02 的原 CP 镜像，SHA-256：
`c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`。
地址标为 `file` 时是文件偏移；所测 CP 代码地址采用 `VA = file + 0x108000`。全部执行在 Mac 上的隔离 Unicorn guest 内，无相机／USB／手机操作，无实际 MMIO、DMA 或完整固件修改。

## 已恢复的生产与消费关系

```text
声明的 ImageParam 参数对象 +0x900、+0x908 / 全局 VA 0x147d018
  → 原 ImageParam 同步片段（file 0x3004ca…）
  → 同一个处理对象 +0x1214：资源配置号
  → 原申请调用片段（file 0x302724…0x3027c6）
  → 原 helper（file 0x8d1308…）请求 kind 15
  → 原 wrapper（file 0x2bf574…）
  → 原配置选择器（file 0x8ad4f4…）和文件内默认资源表
  → 原 broker（file 0x2fbe30…）
  → 原 AcquireVfx（file 0x3259bc…）
  → 原可用性检查与所有权分配（file 0x37fa74 / 0x37fbe0）
  → 写所有权表 VA 0x13eaff8，并回填同对象 +0x10d0
  → 原色彩调用片段（file 0x8cb474…0x8cb484）
  → 原 SetVfxMlutParam / SDK：读取 +0x10d0，使用 +0x10d8 参数
  → 构造 look 22 和实际资源组合的原核心命令
```

**参数对象 `+0x900/+0x908` 和处理对象 `+0x1214` 属于不同对象。** 当前仅恢复原代码的字段传播和申请行为，未把它们的裸枚举擅自命名为主录、监看、静态拍照或某个视频格式。

色彩参数中的 look 22 仍是明确输入的实验条件。正常菜单选择不会因资源分配恢复就自动选择它；此前[新增选择原型 V2](../route-20261028/README.md)及[采集字段／元数据复核](../consumer-20261028/README.md)的开放问题继续保留。

## 默认资源表与实际分配编号

原 getter VA `0x3c7294` 返回 25 行、每行 108 字节的配置表。原选择器将配置号展开为一个或多个节点，仅收集 flag 为 1 的资源项。10 个配置号、25 个 kind，共 250 组原指令查询，与原文件表一致。

| 配置号 raw | 选取节点 | kind 15 资源 ID／原名 | wrapper 偏好值 | 实际 SDK 组合编号 |
|---:|---|---|---:|---:|
| 1 | 1 | 22 / `GRP05_VFX` | 0 | 0 |
| 2 | 2 | 29 / `GRP06_VFX` | 1 | 1 |
| 3 | 3 | 36 / `GRP07_VFX` | 2 | 2 |
| 4 | 4 | 43 / `GRP08_VFX` | 3 | 3 |
| 5 | 1–2 | 22、29 | 4 | 5 |
| 6 | 3–4 | 36、43 | 5 | 6 |
| 7 | 1–4 | 22、29、36、43 | 6 | 4 |
| 8 | 8 | 无启用项 | 0 | 未申请 |
| 9 | 9 | 无启用项 | 1 | 未申请 |
| 10 | 8–9 | 无启用项 | 4 | 未申请 |

组合配置的 wrapper 偏好值与最终 SDK 组合编号不是同一枚举。原分配器在全空所有权表条件下自行生成句柄：`0x80000001 | (实际组合编号 << 16)`，再由原解析器复核其资源槽组合。没有把旧的声明 ID 42 填进所有权表。

节点 8／9 的启用资源含 `HEAD_LV`、`LNS_LV`、`DEV_LV` 等名称；节点 1 有 `HEAD_0`、`DEV_0` 以及 `DST_MOV_ESRAM`、`MBL_MOV_ESRAM`。名称提供进一步追踪线索，**不能据此断言当前机身主录／监看正在使用哪个节点，或断言所有 LV 路径都不使用任何其他色彩处理**。这里只证明这些文件内默认表的 kind 15 请求结果。

配置 8／9／10 的三个原 wrapper 反例均返回 0、不调用所有权分配器，并保留输出槽哨兵值。因此不能将这三个配置当作已有 VFX 所有者继续送入色彩 SDK。

特别区分两个数值 22：资源 ID 22 的原名是 `GRP05_VFX`；外观 look ID 22 的原名是 `MLUT_LOOKNAME_SL3SG3_TO_ACESREC709`。它们属于不同编号空间，相同整数不表示两者绑定，更不表示完整 VENICE ISP 已移植。

## 配置号的原生产者

同步函数的原错误诊断引用 `ImageParam_Sync.cpp`。本轮执行 file `0x3004ca..0x300696`，保留其原分支到 `0x3007c2..0x30082c`；参数向量、头部及其他字段为声明输入。得到：

| 参数 `+0x908` raw | 参数 `+0x900` raw | 全局 `0x147d018` | 对象 `[+1210,+1214,+1218,+121c]` |
|---|---|---|---|
| 0 | 0–4 | 0／1 | `[0,0,0,0]` |
| 1、5、6、7 | 0–4 | 0 | `[8,8,1,1]` |
| 1、5、6、7 | 0–4 | 1 | `[8,10,1,2]` |
| 2、3、4 | 0 | 0／1 | `[1,1,1,1]` |
| 2、3、4 | 1 | 0／1 | `[1,5,1,2]` |
| 2、3、4 | 2 | 0／1 | `[5,1,2,1]` |
| 2、3、4 | 3 | 0／1 | `[5,5,2,2]` |
| 2、3、4 | 4 | 0／1 | `[5,7,2,4]` |

80 组输入全部通过。其中 30 组产生配置号 1／5／7，在**不重置该对象、不再手工写配置号**的条件下，直接执行原申请片段，再进入原色彩调用／SDK，分别生成组合 0／5／4 的 look 22 命令。

这进一步减少了 guest 的替身范围，但这两个参数字段和全局标志仍由实验声明，没有恢复上层正常场景如何设置它们。本轮未执行整个同步函数或整个录像流程，也未运行应用进程与 CP 的完整 IPC 往返。

## 验证结果与边界

| 脚本 | 本轮结果 | 原指令执行数 |
|---|---|---:|
| `resource_binding_guest.py` | 250 组选择；7 组原 broker／申请／分配／解析 | 20,919 |
| `caller_binding_guest.py` | 7 配置 × 2 caller flag：同对象原生产／消费片段；pending 重复调用和人工成功回调 | 28,374 |
| `context_binding_guest.py` | 80 组配置生产；30 组接入申请与色彩命令；3 组无 VFX 反例 | 65,341 |
| `owner_boundaries_guest.py` | 112 组空闲／占用槽检查；56 组命名空间、标志和代次句柄分配／解析 | 11,262 |
| `static_inventory.py` | 33 份原片段哈希／反汇编；250 行默认资源节点记录 | 不计 |

所有权测试在指定资源槽已占用时得到原可用性函数返回 3，且不改变所有权表；空闲时才得到原组合编号。另以旧代次 0／41、两个命名空间、两个原标志验证新句柄及所有行写入。分配器本身不独立替代前置可用性检查。没有验证并发竞争、锁的实际调度或完整计数器回绕。

完整函数调用检查保存寄存器和 SP；片段执行检查停止点、SP 和栈哨兵，不冒充完整函数 ABI 验证。未映射访问和未声明代码均中止。初期将可选位图参数误填为 2 时触发未映射写，检查原参数合同后修正为明确的空指针；没有通过映射错误地址绕过失败。

本轮另外修正了两处实验预期：原分支用的是参数 `+0x900`，不是较早加载的 `+0x8fc`；raw 值 2 分支跳入尾部后保留 r1=1，所以 `+0x121c` 为 1。修正来自重新复核原指令，没有修改原镜像。初始失败说明保存在 [development-notes.json](development-notes.json)。

仍明确保留的外部边界：

- 资源窗口、自由 broker 记录及依赖、参数对象和 caller 活跃寄存器均为声明 fixture，未取得相机当前 RAM。
- 资源同步／配置、事件、AIC、初始化和申请后处理由 `resource_binding_guest.py` 的具名边界返回 0；同步原语和上下文查询为声明返回值。
- 同束 kind 16 请求只声明返回 1，没有执行 STP 的真正申请；本轮执行的是 kind 15 的原分配路径。
- SDK 前置准备、EI、资源忙碌探测、实际命令排队与完成到达仍按脚本声明。成功回调由 host 输入，再执行原回调代码。
- look 22 的三个运行时选择字、硬件信号域、原资源／像素绑定、传感器 RAW 标定、去马赛克／降噪、记录元数据及签名封包／启动链仍未闭合。本轮没有生成或验证可刷写包。

官方 [FX3 7.02 更新说明](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)仍是原版本依据；Sony 的 [Display LUT 说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888936.html)和 [Picture Profile 说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000876510.html)界定正常功能用法，不能替代这里尚缺的底层路由及像素证据。关键后续追踪点已收敛到参数 `+0x900/+0x908` 的正常生产者，以及 MLUT 前后资源与最终录像编码输入的连接。

## 复现与材料

在项目根使用现有环境，依次运行这五个脚本。脚本只写本目录新结果，导入旧轮次代码时不运行旧 main：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/binding-20261028/resource_binding_guest.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/binding-20261028/caller_binding_guest.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/binding-20261028/context_binding_guest.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/binding-20261028/owner_boundaries_guest.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/binding-20261028/static_inventory.py
```

主要结果：[资源选择／原分配](resource-binding-results.json)、[同对象申请／消费](caller-binding-results.json)、[配置生产／集成](context-binding-results.json)、[占用与代次边界](owner-boundaries-results.json)、[源表清单](static-inventory-results.json)、[节点 CSV](graph-node-resources.csv)、[最终运行记录](validation-results.json)、[封存回执](final-receipt.json)。旧的四轮封存材料逐项核验不变。
