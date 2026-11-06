# 受限非载荷响应头失败定位：协议升级、控制器整合与离线验证

承接[阶段277原厂响应头版本修正](../stage277-stock-response-version-mismatch/README.md)与`GOAL_STATUS.json`登记的下一项离线诊断动作：在不导出任何原始响应头、认证挑战/摘要或HASP载荷字节的前提下，为`read0`（`ProductInfo 0x001F` / 参数0）12字节响应头增加**受限类型化失败原因与字段位掩码定位**，保持88B读取上限与禁止自动重试，并将完整普通用户控制器私有回执协议升级至`FX3FLOW6`（`schema=6`、`FX3_ENTRY_SCHEMA=10`、`SVC8`）。本轮全部离线执行，没有新增管理员、USB或相机命令。

## 为什么需要受限类型化响应头定位

阶段275真机`communication03`已越过SERVICE接口获取与7轮认证握手，在发送固定17B `read0`请求并读取12B响应头返回后进入`HELD`（未进入88B数据体读取与STOP），但当时私有流仅记录`FX3_E_SERVICE_READ_HEADER (-72)`与`read0_reply_valid=0`，未记录具体是哪一个非载荷头字段不匹配。阶段277虽从官方`libsencore.so`静态定位并修正了`SendResponse`将响应头偏移8（`version`）固定写为`3`（旧主机端只接受`0`）的不一致，但仍需确保后续任何单次真机诊断若在12B响应头阶段再次返回失败，主机端能够在不保存原始敏感字节的条件下，精确区分**短读、`size`、`pFunc`、`version`、`sequence`、`flags`、`reserved`、`response`或多重字段不匹配**。

| 编号 / 掩码 | 类型化原因 (`read0_header_reason`) | 字段位掩码 (`read0_header_mask`) | 触发条件与边界 |
|---|---|---|---|
| `0` | `not_evaluated` | `0x00` | `op=5`传输I/O失败、尚未执行至`op=5, point=1`，或非`op=5`调用 |
| `1` | `ok` | `0x00` | 12B完整返回且7个头字段全部匹配（含`version==3`、`size==100`） |
| `2` | `short_count` | `0x00` | `op=5`传输返回0但`actual != 12` |
| `3` | `size_mismatch` | `0x01` (`FX3_HMASK_SIZE`) | 仅偏移`0..3` `size != 100` |
| `4` | `pfunc_mismatch` | `0x02` (`FX3_HMASK_PFUNC`) | 仅偏移`4..7` `pFunc != 0x00030001` |
| `5` | `version_mismatch` | `0x04` (`FX3_HMASK_VERSION`) | 仅偏移`8` `version != 3` |
| `6` | `sequence_mismatch` | `0x08` (`FX3_HMASK_SEQUENCE`) | 仅偏移`9` `sequence != expected_sequence` |
| `7` | `flags_mismatch` | `0x10` (`FX3_HMASK_FLAGS`) | 仅偏移`10` `flags != 0` |
| `8` | `reserved_mismatch` | `0x20` (`FX3_HMASK_RESERVED`) | 仅偏移`11` `reserved != 0` |
| `9` | `response_mismatch` | `0x40` (`FX3_HMASK_RESPONSE`) | 仅偏移`12..15` `response != 0` |
| `10` | `multiple_mismatch` | `popcount(mask) >= 2` | 两个及以上头字段同时不匹配，位掩码精确标出全部不匹配字段 |

## 已完成的实现与完整离线验证

1. **C端流与私有日志帧升级（`stream.h` / `stream.c` / `flow_journal.c`）**：
   - 在`stream.c`的`get()`函数中，当`op == 5`完成底层读取后、调用`returned(s, call, 5)`发出`op=5, point=1`帧之前，立即执行`classify_read0_header()`，使`op=5, point=1`与紧随其后的终态`op=51, point=3`（`HELD`）帧均携带一致的`read0_header_reason`与`read0_header_mask`。
   - `flow_journal.c`将672字节私有流帧升级为`FX3FLOW6`（`schema=6`），在偏移`212..215`写入`(reply_valid, read0_header_reason, read0_header_mask, reserved=0)`，完全避开偏移`252..448`在`op=11, point=1`锁定的描述符与设备打开回执区，且不导出任何原始响应头或HASP字节。
2. **Python纯CPU解码器与控制器接收器验证（`bounded_hasp_read.py` / `flow_receiver.py`）**：
   - `bounded_hasp_read.py`新增`classify_read0_reply_header()`，与C端分类器逐枚举、逐掩码对齐。
   - `flow_receiver.py`升级至`FX3FLOW6`，强制校验：`op=5, point=1`前原因与掩码必须为`0`；单字段原因（`3..9`）必须与对应单比特掩码严格一致；多重不匹配（`10`）必须满足`popcount(mask) >= 2`；`reason != 1`后严禁出现`op in (6, 7, 50)`或`read0_reply_valid != 0`；后续帧不得篡改已锁定的`read0_header`记录。
3. **组件与四套完整进程/私有IPC检查全部通过**：
   - [构建回执](build-receipt.json)：生产目标与测试夹具全部编译通过，`FX3_NATIVE_SERVICE_RELEASED=0`、`FX3_NATIVE_RELEASED=0`保持关闭。
   - [组件检查](component-check.json)：12例C单元测试与Python分类器对照全部通过（含原厂`version=3`通过、旧`version=0`报`version_mismatch`、其余6个单字段不匹配、多重字段不匹配、短读及`op=5`传输I/O错误）。
   - [人工恢复准入与8组主流程](test-receipt.json)、[5组SERVICE获取集成检查](acquisition-integration-check.json)（含拒绝旧v3/v5帧格式）、[4组受限共享打开检查](shared-access-check.json)全部通过。初次运行`attempt01`前因未预先创建`runs/`父目录在`mkdir`时报`FileNotFoundError`（未启动任何进程），创建`runs/`后全部通过，见[预检修正记录](precheck-correction.json)。
   - [11组响应头失败定位专项集成检查](header-localization-check.json)：覆盖10次真实普通用户helper/私有IPC完整运行（`short_count`、7种单字段不匹配、`multiple_mismatch`、`op=5` `FX3T_IO`）全部进入`HELD_EARLY_EXIT`且精确报告对应字段，外加15种伪造/篡改帧反例全部被`FlowReceiver`拦截。完整源码增改见[最终核查](final-review.json)与[文件清单](final-manifest.json)。

## 下一步与安全边界

- 当前仅完成离线诊断能力补齐，**尚未生成新的单次上机固定包或新授权**，旧单次授权均已消耗，原root journal保持未改动。
- 相机可继续保持物理断开；待需要制定下一次单次通信诊断固定包时，先在已授权的“仅查Mac USB缓存”范围内绑定重新连接后的同机MSC缓存与物理端口锚点，再单独提交固定方案审阅。
- 完整同机健康备份、独立恢复/写回、目标MAIN 1080p HEVC实录及安全首刷条件仍未满足，G01至G16状态保持不变。
