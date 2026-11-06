# Stage 286 — 通信 05 真机 `COMPLETE` 后的 `AdjustControlFunc (0x40)` 线协议与会话独占合同核对

## 结论先行
- **通信 05（Stage 285）真机全闭环已完成**：在机身 USB 连接模式固定为 **Mass Storage** 并由用户确认界面正常（[`user-screen-confirmation.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage285-service-access-communication05-execution/user-screen-confirmation.json)）后，Stage 285（[`actual-runtime-review.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage285-service-access-communication05-execution/actual-runtime-review.json) / [`private-record.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage285-service-access-communication05-execution/private-record.json)）已在真机完成 **MSC 7 轮握手 $\to$ 同物理端口切换 `SERVICE`（`054C:0336`）独占打开与 7 轮认证 $\to$ `read0` 12B 请求 + 12B 响应头（`version = 3, reason = 1`）+ 88B 响应体 $\to$ `STOP`（`0336:7`）与对象释放（`0336:8`） $\to$ 同口 `054C:0DA1` 自动重枚举归还 $\to$ `0da1:9` 释放系统驱动 $\to$ `COMPLETE`（124 帧，`native_return = 0`）**。这标志着实施路线表第 2 项前半段（**“先诊断通信”**）及 Stage 244 第 1 项准入前提（受限原生控制会话与同机认证身份）与第 3 项 `SERVICE` 退出/USB 归还证据已真机闭环。
- **本阶段（Stage 286）推进到第 2 项后半段（“再评估仅固定 RAM 空任务”）的离线线协议与会话状态机核对**：
  1. 通过 [`audit_adjust_control_contract.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/audit_adjust_control_contract.py) 对官方 7.02 `libsencore.so` 与 `libJiritsu.so` 的 **22 个函数/代码范围、53 处关键指令及 19 条 `0x016f0480` 队列命令记录** 完成了静态核对，输出 [`adjust-control-wire-and-session-contract.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/adjust-control-wire-and-session-contract.json) 与 [`captured-functions.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/captured-functions.json)。
  2. 完成了 [`adjust_wire_codec.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/adjust_wire_codec.py) 与 [`test_adjust_wire_codec.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/test_adjust_wire_codec.py) 的纯 CPU 线协议编解码与 12 类反例拒绝验证（[`codec-test-receipt.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/codec-test-receipt.json)）。
  3. **本阶段完全离线**，无任何 USB、管理员或相机操作。

---

## 1. `AdjustControlFunc (0x40)` 完整线协议与三阶段 OSAL/DMM 生命周期

### 1.1 `pFunc = 0x0040` 表准入与认证级别门控
- 在 `libsencore.so` 中，`pFunc = 0x0040`（[`_Z17AdjustControlFuncPK12SenserPacket`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/captured-functions.json) `0x10344`）同时存在于 `pFunc_level_A`（`0x6b848`）、`pFunc_level_B`（`0x6b8b8`）与 `pFunc_level_C`（`0x6b8f8`）。
- 在 [`SubsystemCommunicationCommand::TransactionStart`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/captured-functions.json)（`0xfb0c`）的命令表查找（`0x17698`，共 19 条指向队列 `0x016f0480` 的 `0x1001` 类别记录）中，`flags` 高位为 `0x4000`（`0x4001..0x4013`）：
  - `0xfe20..0xfe4c` 检查当前会话认证级别（`*0x6aee0`）：由于 `flags & 0xe000 == 0x4000 != 0` 且第 15 位（`0x8000`）为 `0`，**认证级别 2（表 B）与级别 3（表 A）均获准通过**，仅级别 1（表 C）在 `0xfe48` 被拒绝。
  - Stage 285 真机已成功执行仅存在于表 A/B 的 `pFunc = 0x0010`（`ProductInfoFunc` `read0`），证明当前 7 轮 `SERVICE` 认证在真机上已达到 **级别 2 或 3（表 A/B）**，满足 `0x1001` 类别命令的认证级别门控。

### 1.2 请求与响应帧外层包头（`SenserPacket`）
| 方向 | 12B 外层头 `<IHHBBBB` | 紧随其后的负载结构 | 关键原件依据 |
|---|---|---|---|
| 主机 $\to$ 相机请求 | `size = 4 + len(inner)`，`pFunc = 0x0040`，`seq`，`version = 2`，`flag = 0`，`reserved = 0`，`res = 0` | 4B 选择子 `<HH`（`category = 0x1001, command`）+ `inner` 字节流 | `AdjustControlFunc`（`0x10348..0x1036c`）先读 4B 选择子，`TransactionStart`（`0xfc6c..0xfc8c`）再读 `min(size - 4, 0x124)` 字节入内联缓冲 `this+0x40` |
| 相机 $\to$ 主机响应 | `size = 4 + len(data)`，`pFunc = 0x0040`，`seq`，`version = 3`，`flag = 0`，`reserved = 0`，`res = 1` | 4B 业务状态字 `<I`（`0` 为正常）+ 可选响应数据 | `SendResponse`（`0xb4d0..0xb4e0`）固定写 `version = 3`；`DoExecute`（`0xf9a4..0xf9c4`）通过 `MemoryData` 返回 `[msg+0x18]` 字节 |

### 1.3 单次命令内部的 Phase 1 $\to$ Phase 4 $\to$ Phase 16 闭环
1. **并发互斥锁**：`AdjustControlFunc`（`0x103b4`）在进入 `TransactionStart` 前调用 `_ZN12Inconcurrent10resource_t4lockEPK12SenserPacket`（`0xdd00`）获取互斥锁，并在命令对象析构函数 `~SubsystemCommunicationCommand`（`0xfa7c`）中调用 `unlock`（`0xdd7c`）。当 Mac 端 root helper 以 `USBDeviceOpenSeize` 独占持有 `054C:0336` 并严格串行收发时，两个 `SenserThread` 工作线程不会发生来自 USB 端的 `AdjustControlFunc` 并发交错。
2. **三阶段 OSAL/DMM 转换**：
   - **Phase 1（`TransactionStart` `0xff9c..0x10038`，`msg[0] = 1`）**：`libJiritsu.so` 创建 `DmmMgr` 并存入 `*0x46bd0`，返回 `0x10` $\to$ `packet_set_process_req_raw_data`（`0x8494`，置 `msg[0] = 2`） $\to$ `ReceiveOsalMessage`（`0xf1d0..0xf454`）分配/映射 DMM 并将内联参数拷入 DMM，置下一阶段 `[this+0x180] = 4`；若 `size - 4 > 0x124`，`TransactionStart`（`0x10044..0x100b0`）构造 `MemoryData` 供 `SenserThread` 读取剩余请求字节。
   - **Phase 4（`DoExecute` `0xf9f0..0xf9c8`，`msg[0] = 4`）**：
     - 对发送类命令（`15 = SET_FILE_PATH`、`16 = SET_FILE2`）：执行命令后将 4B 状态字写入 `[msg+0x1c]`，当场调用 `dmm_free()` 并析构清空 `*0x46bd0`（`0xac68..0xac88`），返回 `0` $\to$ `packet_set_process_end`（`0x8424`，置 `msg[0] = 8, size = 4`）。
     - 对读取类命令（`17 = GET_FILE2`）：分配响应 DMM 并填入 `4B status + payload`，返回 `0x11` $\to$ `packet_set_process_res_raw_data`（`0x844c`，置 `msg[0] = 8, dmm_addr, size`） $\to$ `ReceiveOsalMessage`（`0xf784..0xf800`）将下一阶段置为 `0x10`（16），由 `DoExecute` 包装为 `MemoryData` 发回主机。
   - **Phase 16（`~SubsystemCommunicationCommand` `0xfaa4..0xfad4`，`msg[0] = 0x10`）**：在 `SendResponse` 发送完响应后，命令对象析构时若阶段为 `0x10`，自动向 `0x016f0480` 发送 `msg[0] = 0x10` $\to$ `cmd_high_capacity_get_file`（`0xb214..0xb240`）释放 DMM、析构并清空 `*0x46bd0`，随后释放 OSAL 消息并解锁 `Inconcurrent::resource_t`。

---

## 2. `SET_FILE2 (16)` / `GET_FILE2 (17)` 三种内部操作模式（`offset 0x28`）边界对比

| 内部首字节 `op`（`[x19, #0x28]`） | 挂载与文件系统行为 | 是否依赖全局选中路径 `*0x467c8` | 适用性与风险边界 |
|---|---|---|---|
| `0x00`（文件系统模式） | **调用 `sys_mount("/dev/nflasha6", "/tmp/jiritsu")`（`0x95bc` / `0x9f18`）**；`SET_FILE2` 还会调用 `sys_get_dir_size`、`sys_dir_create2`、`CFileAccess::open/write/fsync/close` | **是**（通过 `get_access_filename` 读取，退出前 `free` 并清空 `*0x467c8`） | 仅当解析路径等于 `/tmp/jiritsu/libJit.so` **且 `/tmp/jbusy` 存在**（`0x9754..0x977c`）时，`SET_FILE2` 才会在写入后调用 `dlopen("/tmp/jiritsu/libJit.so", RTLD_LAZY)` 与 `dlclose`（`0x9900..0x9928`）；若 `/tmp/jbusy` 不存在则直接返回状态 `0x10000011`（`0x9944`）。包含挂载与目录/文件操作，不能归为纯内存零副作用操作。 |
| `0x01`（存储卡 `/mnt` 模式） | `GET_FILE2` 调用 `sys_media_mount(0)`（`0x9f34`），根路径固定为 `/mnt` | **是** | 涉及机身存储卡挂载与文件读写，排除在通信/内存诊断之外。 |
| `0xFF`（纯内存缓存槽模式） | **不调用 `sys_mount`、不触碰任何文件系统或 `/mnt`、不调用 `dlopen`** | **不用于路径解析**（仅按 `slot = [x19, #0x29]` 索引 `jiritsu_init` 在 `*0x46bd8` 分配的内存槽表；退出尾声仍会清理非空的 `*0x467c8`） | `SET_FILE2`（`0x9608..0x96dc`）在 `size <= 5 MiB` 且 `mode <= 0x11` 时通过 `operator new[]` + `memcpy` 写入内存槽 `(*0x46bd8)`；`GET_FILE2`（`0x9f6c..0x9fd4`）直接从同一内存槽 `memcpy` 读回 `4B status(mode) + data`。 |

---

## 3. 下一步决策（[`decision.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/decision.json)）
1. **第 2 项前半段（受控 `SERVICE` 通信与 `read0` 闭环 + 同口 MSC 自动归还 + 屏幕正常确认）已在 Stage 285 真机通过**。
2. **第 2 项后半段（评估仅固定 RAM 空任务）发现了两条截然不同的技术分支**：
   - **分支 A（不触碰文件系统/挂载的 `AdjustControl 0x40` 纯内存槽 `op = 0xFF` 闭环验证）**：可在单次独占 `SERVICE` 会话中验证 `pFunc = 0x40`（`category = 0x1001`）的 DMM Phase 1/4/16 状态机与内存槽读写回传，完全不调用 `sys_mount`；但它只读写 `*0x46bd8` 内存缓冲，不触发 `dlopen`。
   - **分支 B（`SET_FILE2 op = 0x00` 触发 `dlopen("/tmp/jiritsu/libJit.so")` 的前置条件核查）**：`adj_cmd_set_file2`（`0x9754..0x977c`）在写入 `/tmp/jiritsu/libJit.so` 前强制检查 `sys_file_chk_exist("/tmp/jbusy")`（`0x30ef5`），若 `/tmp/jbusy` 不存在则拒绝写入并返回错误码 `0x10000011`！因此，在尝试任何 `libJit.so` 自写空任务加载之前，必须先静态定位固件中**哪条原厂命令负责创建 `/tmp/jbusy` 以及挂载 `/tmp/jiritsu` 的精确生命周期**（Stage 287）。
