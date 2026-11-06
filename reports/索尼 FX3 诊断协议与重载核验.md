# 核准 FX3 的诊断协议与重载边界

核查日期：2026-10-25。**适配依据进一步增强：FX3 7.02 的内部文件命令已逐项映射，WBI 内核接口及操作顺序也找到原厂实现。** 本轮仍未闭合外部 USB 会话到处理器再到回复的完整链路，也没有验证实机诊断或故障恢复。当前真实机身依据仍限于人工菜单7.02和普通 MSC 缓存 `054C:0DA1`；程序哈希、同机绑定及主动访问均未新增。

## 内部15–18命令已映射 外层入口仍未闭合

已从 FX3 原厂跳表、BL／PLT 重定位和真实符号核准：15为选路径，16为写文件，17为读文件，18为 `cmd_file_delete2`；旧 `cmd_file_delete` 属命令9。注册回调、消息ID及 core 连续命令记录也相互对应，关闭了此前仅凭 A7C II 方法名推测的缺口。([逐项命令表](../work/sony-firmware-20261024/stage9-protocol/jiritsu/command-handler-table.json)、[注册证据](../work/sony-firmware-20261024/stage9-protocol/jiritsu/gate-and-registration.json))

内部记录的 `400F／4011` 与线上命令不是同一个字段；core 有归一为低8位命令的静态桥接证据。尚未将具体记录绑定到当前活跃外层查找表，最终 USB 回复序列化也未追完。读写还经过 DMM 缓冲及多阶段状态机，内部状态和结构偏移不能直接当作线上返回码或字段。故 **`TARGET_ROUTE_VERIFIED=False` 继续保留**，不能宣布整个命令通道已打通。([内部记录与桥接](../work/sony-firmware-20261024/stage9-protocol/jiritsu/parse-and-command-records.json)、[阶段与收尾](../work/sony-firmware-20261024/stage9-protocol/jiritsu/dispatch-raw.json))

## 主机候选字节已固定 测试只覆盖本地解析

公开主机实现的外头是12字节小端 `<IHHBBBB>`；Jiritsu 族、命令和参数位于线上偏移12、14、16。它与设备内部结构的偏移不同。当前源码更新到 `ef7db116…`，相对上轮只改免责声明，通信代码哈希不变，没有新增恢复能力。([固定版封包](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L822-L851)、[固定版内层请求](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py#L404-L423)、[提交比较](https://github.com/QAQLeonard/a7c2-fl23-research/compare/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d...ef7db116e13e37be91e9af20360dc9bba8d64a9b))

已交付自写纯 bytes codec，只编码候选选路径／读取并解析已组装的单帧，拒绝错误长度、序列、状态及危险路径。19项合成 fixture 全部通过，协调端独立检查并复跑亦为19项通过。它没有 backend、收包、认证、native 或写入接口；64KiB是本地策略上限，不是 FX3 协议上限，也未发送给相机。**这些测试不能替代真实回包、分块及结束包验证。**([自写 codec](../work/sony-firmware-20261024/stage9-protocol/host/offline_codec.py)、[fixture 与限制](../work/sony-firmware-20261024/stage9-protocol/host/offline-fixtures.json)、[独立复核及来源收据](../work/sony-firmware-20261024/stage9-protocol/host/source-receipt.json))

## WBI 接口已有原厂语义 当前状态仍未读回

官方 WBI2 快照中已核准 `image_dev／image_mode／image_drop` 的真实0644属性及 show／store 处理器。`image_dev` 遍历 backend，以星号标记选中项；快照保存 mode2，但尚未把选中节点映射成 `*wbi4`，更不能把包内状态当作用户机身当前值。([属性、原字节与坐标](../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-attribute-audit.json))

`image_drop` 可经选中 backend 写512字节全零头并输出 `dropped wbi`；mode 已为0时却会跳过底层 drop。因而先 drop 再 mode0 获得 FX3 原厂静态语义支持，反序存在表面成功而未实际失效的风险。这条内核路径与 `libsencore` 向 nflasha5 写 `invl` 的分支必须分列：尚未证明它们对应同一介质范围。日志也不能单独证明冷启动加载了新程序。([drop／mode 原始处理链](../work/sony-firmware-20261024/stage9-protocol/wbi/sysfs-handler-disassembly.txt)、[来源与操作边界](../work/sony-firmware-20261024/stage9-protocol/wbi/source-receipt.json))

## 下一步缺的是外层证据与对应故障验收

离线下一步是闭合活跃路由、最终回复包装及 backend 到介质的映射；随后才有依据审计最小主动诊断。实机阶段仍需分别验证身份与原程序、认证和退出、当前 WBI 状态、文件完整读回，以及拟改范围的原字节恢复与冷启动一致性。主应用失效后能否独立建立入口、loader 如何处理无效 WBI，仍无证据；正常服务或离线 fixture 不能替代救砖验收。

本轮减少了协议和重载适配的不确定项，没有生成刷写工具、修改固件或执行硬件／native 操作，当前相机授权仍仅缓存 PnP。HD29.97 HEVC 主录保持既有离线参数链结论，硬件编码、成片及 ZV-E1 跨刷均未验证。([详细研究笔记](<../research_notes/索尼 FX3 诊断协议与重载核验/jiritsu_route.md>)、[本轮哈希与能力收据](../work/sony-firmware-20261024/stage9-protocol/final-receipt.json))
