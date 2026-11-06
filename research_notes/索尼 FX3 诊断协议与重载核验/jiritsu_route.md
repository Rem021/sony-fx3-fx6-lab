# FX3 7.02 Jiritsu 命令15–18的真实路由与重载边界

## 1. 四个命令是否已绑定到真实 FX3 处理器？

### Takeaway
**内部命令到处理器的映射已静态闭合**：直接解出原厂两级跳表并核对 PLT 重定位及真实符号，而非根据函数名猜测。外部 USB 输入到活跃命令表、最终回复序列化仍是独立未完成层次。[完整命令表](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/command-handler-table.json)

### Cited Findings
- 输入固定为官方 FX3 7.02 `libJiritsu.so` SHA256 `bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9`、`libsencore.so` SHA256 `a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410`。本轮纯静态读取、解表和反汇编，没有执行固件或设备操作。[复核脚本与固定哈希](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/derive_routes.py)
- Jiritsu 匿名 dispatcher `0xb278` 在 `0xb290` 读取本机 packet+`0x26` 的16位命令，减1并限制在0–17；表 `0x11b2c` 为18个有符号字节，目标计算为 `0xb2b8 + sign_extend(table[cmd-1]) * 4`。完整表字节为 `00 10 17 1e 25 2c 33 36 3d 44 47 4a 4d 55 5d 60 63 66`。[原始指令和表](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/route-tables-and-caller.json)

| 命令 | 一级表字节→分支 | 二级路由及真实调用点 | 最终 FX3 处理器 |
|---|---|---|---|
| 15 | `5d → 0xb42c` | send wrapper `0xab88`；`0x11b14[15-6]=17`→`0xacac`；`0xacb4: BL 0x5fd0` | `adj_cmd_set_file_path @0x89b4` |
| 16 | `60 → 0xb438` | 同 wrapper；`0x11b14[16-6]=1b`→`0xacbc`；`0xacc4: BL 0x5f80` | `adj_cmd_set_file2 @0x9528` |
| 17 | `63 → 0xb444` | read wrapper `0xb0ac`；`0x11b20[17-8]=24`→`0xb1f8`；`0xb20c: BL 0x5bf0` | `adj_cmd_get_file2 @0x9e74` |
| 18 | `66 → 0xb450` | `0xb464: BL 0x6170` | `cmd_file_delete2 @0xa29c` |

以上每个表项、BL原始字节、PLT符号和真实入口已由脚本断言一致。**命令18是 delete2；旧 `cmd_file_delete @0x8c78` 属命令9，不能混用。**[机器可读表及断言结果](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/command-handler-table.json)、[CSV表](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/command-handler-table.csv)

- `jiritsu_init @0x6d74` 在 `0x6da4/0x6da8` 生成回调地址 `0xb278`，在 `0x6dac/0x6db4` 生成消息ID `0x016f0480`，然后于 `0x6dbc` 调用 `osal_reg_sync_msg_queue_cb` 注册。这解释了为何没有直接 BL 到匿名 dispatcher：入口通过 OSAL 回调。[注册指令原字节](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/gate-and-registration.json)
- core 的连续 `0x48` 字节记录 `0x31d94/0x31ddc/0x31e24/0x31e6c` 分别包含 `(message_id=0x016f0480, family=0x1001, internal_command=0x400f/0x4010/0x4011/0x4012)` 及对应 JIRITSU 名称。首条原始前8字节为 `80 04 6f 01 01 10 0f 40`；另有内容相同的副本。记录的消息ID与已证注册回调一致。[原始记录](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/parse-and-command-records.json)
- core `MakeOsalMessage @0xf038` 先复制本机消息，在 `0xf07c/0xf080` 执行 `ldrb w1,[x0,#0x26]`、`strh w1,[x0,#0x26]`，把该16位字段归一为低8位命令。这支持内部 `0x400f→15` 等桥接，但不是要求主机把 `0x400f` 写到线上。[桥接原字节](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/parse-and-command-records.json)

### Inferences
- 已关闭先前“15–18只是 A7C II alias、FX3 函数是否真正绑定未知”的核心缺口；原厂内部分派、注册和匹配记录提供了互相对应的独立证据。[路由总表](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/command-handler-table.json)
- 不应把内部记录 `0x400f` 与主机 wire 的“pFunc=0x40、inner cmd=15”混为同一字段。外层 framing 由主机子任务另行审计；本轮没有从 USB 接收器跟到内部记录的完整规范化步骤。[内部字段与归一化](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/parse-and-command-records.json)

### Gaps
- 本轮定向 `Parse` 检查读到了运行时函数注册表的间接调用，但尚未把上述两份命令记录中的具体一份，逐步绑定为当前活跃查找表。记录存在、callback注册及内部handler闭合，不等于外部会话可达已验收。
- 未验证相机认证、当前机身是否已调用该初始化函数、OSAL队列存活及正常/故障状态下的可达性。

## 2. 调用状态、返回值与输出长度究竟证明到哪一层？

### Takeaway
四个命令不是简单调用一个裸函数：大数据读写经过 DMM 缓冲与多阶段状态机。已确认本机结构内状态、长度和地址字段；**最终 USB 返回首4字节/线上头长等仍不能仅由这些结构偏移推出**。[状态机原始指令](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/dispatch-raw.json)

### Cited Findings
- send wrapper `0xab88` 对 packet首字节1分配/初始化DMM并返回内部控制值 `0x10`，对首字节4才经二级跳表调用实际选路径/写文件处理器，随后释放DMM；其他阶段走 packet error。read wrapper `0xb0ac` 分别处理阶段1、4、`0x10`，实际读在阶段4，后续阶段清理DMM并返回 `0x12`。[wrapper完整指令](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/dispatch-raw.json)
- dispatcher `0xb278` 默认结果长度为4，并根据handler返回的 `0x10/0x11/0x12/0` 分别调用 `packet_set_process_req_raw_data`、`packet_set_process_res_raw_data`、`packet_set_fin_del_data`、`packet_set_process_end`；其他非零值进入错误路径。它们是控制状态，不应直接解释成文件API错误码。[dispatcher收尾](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/dispatch-raw.json)
- `packet_set_process_end @0x8424` 将本机packet状态设为8、控制字节写+1、结果长度写+`0x18`；`packet_set_process_res_raw_data @0x844c` 从DMM取raw缓冲地址和长度。选路径等具体处理器把32位操作状态写入本机packet+`0x1c`。本轮未把这些字段映射到最终USB字节流。[packet builder原字节](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/route-tables-and-caller.json)、[选路径/读写处理器原字节](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)
- 本机结构中命令族、命令和命令参数分别从+`0x24/+0x26/+0x28`使用；不能将这些偏移直接替代主机 wire 中的+12/+14/+16。记录的数值解码依据源ELF小端属性，线上大小端/序列化仍需独立证据。[本机结构读取](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/route-tables-and-caller.json)、[输入ELF属性](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)

### Inferences
- 离线主机 codec 可以使用内部路由闭合来增强“候选FX3命令”的依据，但应继续把外层路由和回复序列化标为未经目标设备验收。单独发一个参数块，也不能省略既有协议所需的阶段和数据传输。[阶段门禁](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/dispatch-raw.json)

### Gaps
- 未追踪完整USB回复serializer，因此“线上首4字节必为LE status”、12字节头和响应总长度关系，在本轮设备端研究中仍未闭合。
- 未实测0长度、最大长度、DMM分配失败、短读/短写及异常清理；handler存在不等于这些边界通过。

## 3. 已选路径、libJit特殊加载及 jbusy 有什么不同边界？

### Takeaway
选路径/普通文件操作与精确 `libJit.so` 动态加载是不同分支。当前能证明这套候选通道具有特定路径下的原生重载行为，仍不能证明它是无主应用依赖的恢复入口。[原FX3文件/加载分支](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)

### Cited Findings
- `adj_cmd_set_file_path @0x89b4` 检查请求长度，保存选择路径到全局状态；后续 `get_access_filename @0x92e8` 支持选择器 `0xff` 使用此前已选路径。前轮已将 `00 ff 00` 的写入参数映射为 Work挂载、已选路径和原始文件写入。[相同源哈希的逐字节回执](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)
- `adj_cmd_set_file2 @0x9528` 对精确 `jit.log/history.txt` 有拒绝，对精确 `/tmp/jiritsu/libJit.so` 检查 `/tmp/jbusy`，并在写入、fsync、close后进入标准 `dlopen(path,1)`、dlclose 分支。它不是所有普通文件写入都会触发的动作。[处理器及PLT原始指令](../../work/sony-firmware-20261024/stage8-adaptation/device/device-abi-audit.json)、[路径/参数解释](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)
- 当前命令18真实处理器 `cmd_file_delete2 @0xa29c` 根据参数确定挂载/所选路径，对末尾为斜线的路径走rmdir，否则走文件删除，并清理保存的选择路径状态。这进一步说明它与旧命令9的删除处理器不等价。[delete2原始指令](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/dispatch-raw.json)

### Inferences
- `/tmp/jiritsu/` 的主机端路径限制不能未经证明升级成接收端的完整安全沙箱；本轮只确认已选路径机制和精确libJit特殊分支。[路径接收代码](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)
- 所见OSAL callback、DMM和路径全局状态需要已初始化的运行环境；内部命令链闭合没有关闭独立服务启动、特权加载、WBI刷新或真正救砖的缺口。[注册与分配状态](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/gate-and-registration.json)、[阶段控制](../../work/sony-firmware-20261024/stage9-protocol/jiritsu/dispatch-raw.json)

### Gaps
- 未证明接收端只允许 `/tmp`，未验证 jbusy 是否存在、加载实际权限或所选路径状态在故障后的可靠性。
- 本轮没有下载新的第三方参考文件，无需删除参考源码；既有固件、原件和历史证据均保留。没有认证、模块上传、相机文件访问、刷写或任何硬件操作。
