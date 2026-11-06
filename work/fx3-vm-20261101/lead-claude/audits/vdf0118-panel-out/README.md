# VDF 0x0118：SetPanelOut 原件静态审计

结论：AP66 的 22B 请求是面板输出配置，AP 调用为 **no-wait**，不是等待回复超时的阻塞点。CP 旧命令是 `0x0100` / `VDF::VdfDisplayCmdSetPanelOut`，旧回复 `0x1100`，对 AP 回复为 `0x1118`、12B、status32；完整 CP 流程含设备状态和 sequencer，不等于纯软件回复就实现显示。（AP `0x2df3d08`、`0x2de66f4`；CP `0x5f3514`、`0x5f3524`、`0x5f3772`、`0x1aeb8c`。）

本目录为离线证据，不修改原件、runtime、STATE，不启动 QEMU，也没有设备操作。输入 SHA256、Capstone 指令与原始字节、表项、日志行、模型检查均在 [vdf0118-proof.json](vdf0118-proof.json)。地址记法：AP 为 appFw.so ELF VA/模块偏移；CP 为加载基址 `0x108000` 的 VA，文件偏移为 VA−`0x108000`。Capstone 使用方法参考[官方 Python 文档](https://www.capstone-engine.org/lang_python.html)，固件语义结论全部来自本地原件。

## 复跑

从项目根运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/vdf0118-panel-out/audit_vdf0118.py
```

脚本核验外盘 UUID，只读 AP/CP 与 AP66 日志；反汇编 5 段 AP、21 段 CP；检查 4 个 TBH 映射、命令/解析器注册与 RTTI/vtable；执行 1 正例、24 反例，再重新写本目录 JSON。指令字节覆盖检查与断言失败会非零退出。模型测试只检查受限软件契约，不证明原厂所有枚举或硬件行为。

## AP 调用与失败路径

- 实际 sequence 为 `model::sequence_display_setup::run()`：日志字符串 VA `0x3922b20`，`Send VDF SET_PANEL_OUT`=`0x391c861`、Success=`0x391c881`、Failure=`0x391c8a4`。调用在 `0x2b8bc50` → wrapper `0x2dd0094` → `infra_wrapper_bb::detail::vdf_set_panel_out`=`0x2df3d08`；后者函数签名字串 `0x3968198`。AP66 栈与原始请求保存在 JSON 的 `runtime_input_receipt`，日志起始行 7619。
- wrapper 构造 `200d/0118/0016/8001`（四个 LE16），载荷位于 +8；`0x2df3f54` 写 mask=3，`0x2df3e54` 写 +9=1，`0x2df3f58` 等将多数其余字段清零，`0x2df3f04` 和 `0x2df3fbc` 根据输入生成 +20，`0x2df3e60` 根据输入生成 +21。`0x2df3f90` 传请求首址、`0x2df3f94` 传长度22，`0x2df3f98` 调用 `0x2de66f4`。
- `0x2de66f4` 的日志函数签名（`0x396a958`）是 `send_no_wait_with_main_thread_i(OSAL_ID, const void*, int32_t)`。`0x2de672c` 调 `osal_valloc_msg_wait`，`0x2de6860` memcpy，`0x2de6870` 调 `osal_set_msg_src`，`0x2de6880` 调 `osal_snd_msg(0x92840747, msg)`。符号来自 ELF PLT 重定位，不凭函数名猜测。
- **发送后没有 `osal_rcv_msg_tmo`，回复超时值不适用，也没有本调用的回复字段检查。** `0x2de6884` 只检查发送 API 返回值；成功后到 `0x2de6914` 恢复栈并返回，`0x2df3fa4` 直接把 out 写0。因此 sequence 在 `0x2b8bc54` 所见的0仅证明请求被提交；`Success VDF SET_PANEL_OUT` 不是 CP 或帧完成回执。
- 分配失败、空消息、发送失败分别走 `0x2de6734`、`0x2de67c8`、`0x2de6888` 的日志/断言路径，包含 `usleep(100000)` 和 `0x2ebf3b0` 致命处理入口（末调用后仍有后续代码，不能仅从这里认定进程必定退出）。wrapper 输入无效也走 `0x2df3dbc`/`0x2df3e70` 的断言。sequence 非零结果走 `0x2b8bdbc` Failure 路径；这个 out 在正常提交路径固定为0。

## 请求字段

AP66 原文：`0d201801160001800301000000000000000000000100`。

命令/解析器注册表 CP `0xb71e14` 为 `(0x118, Thumb 0x1a8a91)`，解析器 `0x1a8a90` 读取下列字节并保存到基址 `0x019eafb8` 的状态。原厂日志名称由 `SendVDF_SetPanelOut`=`0x1a1590` 的 `0x1a1634–0x1a173a` 参数与字符串对应；表中名称是该层诊断名，不扩充成未经证实的硬件含义。

|偏移|本次值|语义/CP 状态偏移|指令依据|
|---|---:|---|---|
|0..1|0x200d|AP 消息族|AP 0x2df3d30|
|2..3|0x0118|SetPanelOut|AP 0x2df3d3c；CP 0xb71e14|
|4..5|22|长度|AP 0x2df3d44|
|6..7|0x8001|原始头字段，保留原值；位的完整定义未证实|AP 0x2df3d4c|
|8|3|更新 mask，bit0 LCD/panel 组、bit1 EVF 组；保存 +0x64b|CP 0x1a8a9a–0x1a8ab4、0x1a8ac8–0x1a8ae6|
|9|1|panel，+0x64c|CP 0x1a8ab6|
|10|0|evf，+0x650|CP 0x1a8ae6|
|11|0|projector，+0x654；无条件更新|CP 0x1a8aac|
|12|0|本解析器未读；保留/布局字节|CP 0x1a8a90–0x1a8b0e|
|13|0|LCD color mode，+0x2a0，受bit0控制|CP 0x1a8ac2；旧0x120前置命令 0x1a1a5e|
|14|0|本解析器未读；保留/布局字节|CP 0x1a8a90–0x1a8b0e|
|15|0|VF color mode，+0x298，受bit1控制|CP 0x1a8b06；0x1a1a6a|
|16|0|本解析器未读；保留/布局字节|CP 0x1a8a90–0x1a8b0e|
|17|0|evf_framerate，+0x658|CP 0x1a8aec → 0x1a1882 → 日志0xd81a6c|
|18|0|power_save，+0x65c，受bit0控制|CP 0x1a8abc → 0x1a1818 → 日志0x1a19c8|
|19|0|evf_fr_force_normal，+0x660|CP 0x1a8af2 → 0x1a18ac → 日志0x1a19e4|
|20|1|evf_priority，+0x664|CP 0x1a8afa → 0x1a18de → 日志0x1a1a08|
|21|0|evf_magnifier，+0x668|CP 0x1a8b00 → 0x1a190a → 日志0xd81a8a|

所以 `03 01` 不是枚举 `0x0301`，`01 00` 也不是整体 `0x0100`：它们分别是两个独立字段（CP 字节读取 `0x1a8a9a`/`0x1a8ab6`、`0x1a8afa`/`0x1a8b00`）。bit0未设时 panel/power_save/LCD color mode 保持旧值；bit1未设时 EVF组保持旧值；projector 无条件更新（CP `0x1a8aac–0x1a8b0e`）。本次 mask3 更新两组，不需要接受部分更新来满足 AP66。

## CP 处理、旧命令和回复

- BB 收到 AP 命令后：`0x1ac9ee` 读 command，TBH `0x1aca04` 的 index0x18、表项 VA `0x1aca38` 指向 `0x1accf6`，转内部 ID `0x73`，`0x1ad052` 将消息交给 `0x92840748`。原厂注册 `0xb71e14` 将0x118绑定字段解析器；内部分派 TBH `0x1a8f12` 的0x73项（VA `0x1a8ffc`）到 `0x1a9e2a`，请求调度 sequence `0x48`，经 `0x1aa5de` → `0x5cad6e`。
- sequence 回调注册 `0x194ee8–0x194f02` 形成 Thumb `0x5c3a6d`；`0x5c3a84` 调 `SendVDF_SetPanelOut(状态,1)`=`0x1a1590`，返回后 `0x5c3a8a` 将 AP command0x118和返回状态交 `0x5c68de`。该 sequence48到注册分支的全调度器每一条边尚未展开，保留为未证实的中间调度边，不能把相邻地址当作唯一调用证明。
- 旧 VDF 请求：`0x1a159e–0x1a15b8` 构造 `2001/0100/0010/0001`，8B载荷是 panel、evf、projector、evf_framerate、power_save、evf_fr_force_normal、evf_priority、evf_magnifier（对应装填在 `0x1a1814`、`0x1a187e`、`0x1a1970`、`0x1a18a8`、`0x1a1846`、`0x1a18da`、`0x1a1906`、`0x1a193c`）。此前 `0x1a15c2` 先发旧0x120 color mode命令；color mode仅接受0/1，见 `0x1a1a62`/`0x1a1a6e`。
- 旧命令类名字符串 `0xb3d200`=`N3VDF24VdfDisplayCmdSetPanelOutE`，typeinfo `0xb7e188`，vtable address-point `0xb7e170`。vtable+0xc→`0x5f3515`，去Thumb位后的 `0x5f3514` 明确回填消息族0x2001与命令0x100；vtable+0x10→`0x5f3525` 为 Activate。由构造常量与类虚表交叉证明，非仅靠字符串。
- 旧发送 `0x1a1756` 调 `0x5daac2`，成功后 `0x1a1796` 调 `0x5dab34` 收12B回复，栈上传递 timeout=`-1`（`0x1a178a–0x1a1792`，无限等待哨兵；其底层时间单位此处不适用）。此处只检查接收返回码和 +8 status32；没有看到对回复族、命令、长度的逐字段比较（`0x1a179a–0x1a17d2`）。这属于 **CP 内部等待**，不能移植成 AP 等待。
- 旧回复 `0x1100`：`0x5f3772` 的非内部源分支 `0x5f37b0–0x5f37c2` 发4B status；调用点 `0x5f3620–0x5f3624` 传0，`0x5f358a–0x5f358e` 的特殊早退传1；取消路径 `0x5f3c48–0x5f3c4c` 可传2。正常成功0在 `0x1a17c4–0x1a17f0` 返回0；status1在 `0x1a197e` 返回1，其余返回−1（`0x1a1984`）。因此这里不能笼统认为所有非零都是同一种硬件失败，也不能给所有请求强回0。
- Activate 并非无条件立即完成：`0x5f35d4` 调设备相关 helper，`0x5f35e2`/`0x5f35fc` 读子系统虚方法，`0x5f36aa` 设置后续状态，`0x5f372a–0x5f3770` 根据设备状态选择0x11/0x21/0x31/0x41/0x90等继续步骤。存在早退/直接回复分支（`0x5f3580–0x5f3592`、`0x5f3620`）；不能断言所有0x118必等物理帧，也没有证据能断言本次完整硬件路径已完成。
- 返回 AP：`0x5c68de` → `0x1ad1a4`，TBH `0x1ad22c` 的0x18项（`0x1ad260`）到 `0x1ad4f2`，生成内部0x274；TBH `0x1aab2c` 的0x74项（`0x1aac18`）到 `0x1ab3e0` → `0x1aeb5c`。`0x1aeb8c–0x1aebb4` 写 `200d/1118/000c/8001` 与未经改写的 status32，再交发送 helper `0x1aef1c`。正常软件成功回复字节为 `0d2018110c00018000000000`。

## 本次软件模型的最小契约（建议，尚未接入运行链）

只接受上述精确22B请求；保存 mask=3 和表中全部具名状态（两组更新、projector=0、panel=1、EVF=0、两个色彩模式0、framerate/power_save/force_normal=0、priority=1、magnifier=0），并保留原始请求和软件状态版本。原厂保存依据是 `0x1a8a90–0x1a8b0e`；将物理完成标记保持 false 是软件模型自身边界，并非原厂字段。

按调用源消息地址路由回复，不能把 AP66 临时源 `0x81cf6189` 硬编码为永久接收者（AP `0x2de6864–0x2de6870` 用运行时 main-thread source）。回复按 LE 编码：+0族0x200d、+2命令0x1118、+4长度12、+6头0x8001、+8 status32=0，依据 CP `0x1aeb8c–0x1aebb4`；精确字节 `0d2018110c00018000000000`。该成功仅承认模型保存配置，不能声称原厂 CP sequencer、LCD、帧完成已经实现。

拒绝：错误族/命令/长度/头、mask不是3、panel不是1、EVF/projector不是0、保留字节非0、color mode非0、priority不是1、其余具名字段非0、截短/多余字节。此拒绝集合是 **本轮软件模型范围**，不是“原厂全部非法值”；原厂已有多种其他合法分支（`0x1a1850–0x1a1978`）但没有必要在此扩展。对范围外请求不生成成功回复，返回模型的 unsupported/记录诊断；本审计没有编造原厂错误 status。

## 未证实项

1. AP全局 main-thread 对0x1118的异步消费/释放规则没有追完；本调用 no-wait 与不存在局部回复检查已证实（`0x2de6884–0x2de6928`），不能由此推断整个 AP 忽略所有回复。
2. sequence48到回调注册分支的所有调度边，以及设备虚方法对应的驱动/帧中断没有完全展开（`0x1a9e3a`、`0x194efa`、`0x5f35e2`）。尚无“必须等帧完成”或“本次无硬件依赖”的证明。
3. mask高位、保留字节、所有枚举的完整意义、evf_priority=1 的物理行为未证实；本轮精确白名单不代表原厂通用协议校验器（解析器 `0x1a8a90`，旧转换 `0x1a1812–0x1a1978`）。
4. 头0x8001的完整位定义、致命入口0x2ebf3b0的最终进程后果、当前运行中新回复能否恢复菜单均未证实；未运行 VM/实机验收。
