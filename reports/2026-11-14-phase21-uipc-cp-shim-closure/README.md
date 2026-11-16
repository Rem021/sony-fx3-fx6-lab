# Phase 21（P11）AP 侧双阻塞 UIPC 队列合成器与 Cine EI / 3D LUT / IBIS 桥接验真报告

- **任务代号**：`Hydrogen-7`｜Phase 21（`P11` AP-Side UIPC-CP Shim）
- **架构红线**：Stage-A `U2` 原厂 Stock-CP 红线与 BYOF 洁净室锁定
  - `p8_cp_mutation_forbidden = True`、`cp_mutation_bytes = 0`
  - `persistent_emmc_writes_authorized = False`、`persistent_write_release = False`
  - 全部本地 Donor 镜像均通过 [`donor_paths.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/donor_paths.py) 以严格 `O_RDONLY` 只读方式访问
- **验证器源码**：[`uipc_cp_shim_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/uipc_cp_shim_verifier.py)
- **单元测试集**：[`test_phase21_uipc_cp_shim.py`](../../outputs/fx6-on-fx3-closure/tests/test_phase21_uipc_cp_shim.py)（20 项单元测试，本地只读 Donor 模式 + `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室模式双全绿通过）

---

## 一、全量结论摘要

| 验证维度 | 核心实证结论 | 状态 |
|---|---|---|
| **1. 双阻塞 FX6 独占队列识别与消除** | 在真实 FX6 6.01 `appFw.so` / `cpapp-b.bin` 与 FX3 7.02 `cpapp-b.bin` 对比中精确锁定唯一 2 个在 FX3 Stock-CP 中零命中的阻塞队列：**`0x92d2091c`**（外置 RTC 服务）与 **`0x91db059b`**（Smart Handle 智能手柄）。`UipcCpShimRuntime` 在 AP 侧完成拦截合成应答，彻底消除 `std::future<bool>::wait()` 永久挂起与 `0x2167784` 断言崩溃。 | **已验真闭合** |
| **2. Queue 1 (`0x92d2091c`) `/dev/rtc0` → `udate` 转换与 Unicorn 证明** | 反汇编 FX6 `appFw.so` `infra_wrapper_rtc_procam_chaplin_base.cpp`（`0x2159840` / `0x2159b4c` / `0x2159c50`）与 `infra_wrapper_udate`（`0x215bf70`），完成 Linux `/dev/rtc0` `struct rtc_time` → 44B `OSAL_DATECHG_NOTIFY` `udate` → 2B `[0x03, status]` 合成器。Unicorn AArch64 实跑真实 FX6 `appFw.so` 证明：未拦截时挂起于 `0x1ca0878`；注入合成应答 `[0x03, 0x00]`（`msg_src=0x92d2091c`）后 `0x2159b4c` 设置 `std::promise<bool>(1)` 并释放消息，主流程返回 `rc=0`。 | **Unicorn 实证通过** |
| **3. Queue 2 (`0x91db059b`) Smart Handle 脱离回执与 XLR-H1 音频共存** | 反汇编 FX6 `appFw.so` `infra_wrapper_handle_procam_chaplin_base.cpp`（`0x2107b74` / `0x2107be4` / `0x2107c6c`），捕获 12B `<III(0x81000001, 0, cb_qid)` / `0x81000002` 注册与注销报文。Unicorn AArch64 证明：未拦截失败触发 `0x2167784`（行 `123 = 0x7b`）断言；合成脱离态 ACK（`<III(0x81000001, 0, cb_qid)`）及 `0x88000002`（事件 `551`）后零断言完成，同时真实 `libInfraHotshoe.so::WaitRecvCompMsgFromHotshoeRsrc`（`0x5d90`）与 `EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_ON/OFF`、`0x92840747` `0x032d`（`P5`）100% 正常共存。 | **Unicorn 实证通过** |
| **4. `developing_mode_FHD` 桥接与 Cine EI / 33³ 3D LUT DMA 状态机** | 将 FX6 `PID_SET_DEVELOPING_MODE`（`0x0362 -> 0x10c1`、`developing_mode_FHD`）转译至 FX3 Stock-CP `mov_size_req` / `frate_req` / `e_set_img_frame_size` / `SetDevelopParam` 与受支持的 `0x92840747` 命令（`0x0416`, `0x0169`, `0x016a`, `0x0165`, `0x0166`, `0x0152`）。验证 164B `mpr::SetLutData`、`0x6a1b9 = 434,617 B` `.cube` 缓冲区、超过 `0xbb80 = 48,000 B` 阈值时 `33^3` 3D LUT（`107,812 B` 8-bit / `215,622 B` 16-bit）经由 `0x0165`（36B DMA）+ `0x0166`（10B 使能）及双原生 ISO（`800` / `12800` EI）状态机闭环。 | **ABI + Unicorn 双通过** |
| **5. FX3 五轴 IBIS 稳像遥测桥接契约** | 基于 FX3 7.02 `cpapp-b.bin`（`LiroSeq: Restore.`、`HallPIDOUT_0`、`GyroPIDOUT_0`、`PWMOUT_0`、`FWCP-isRetract`、`CheckSetSteadyShotAdvancedMovie`、`steadyshot_body_axis_movie`）与 FX6 `appFw.so::set_tc_on_movie_i`（`0x211019c`）/ `set_tc_mode_i`（`0x21101ec`）建立 `Off` / `Standard` / `Active` 遥测桥接契约，证明全模式均保持物理音圈平台通电居中锁止（`floating_sensor_hazard = False`）。 | **安全契约闭合** |

---

## 二、Queue 1（`0x92d2091c` 外置 RTC 服务）协议反汇编与 Unicorn 证明

### 2.1 FX6 `appFw.so` 反汇编拓扑（注：模块编译于 `appFw.so`，不存在独立 `libInfraClock.so`）

| 例程 / 地址 | 职责与反汇编实证 |
|---|---|
| `register_callback` @ `0x2159840` | 通过 `0x215c8bc`（`osal_reg_msg_queue_cb`）在回复队列 **`0x81d705bd`** 上注册回调 `0x2159b4c`；注册失败触发 `0x2167784` 行 `145`（`0x91`）断言。 |
| `get_rtc_status` @ `0x2159c50` | 在 `0x6082500` 构造 `std::promise<bool>`（`0x2159988`），通过 `send_sync_msg`（`0x215c38c`）向 **`0x92d2091c`** 发送 2B 报文 `b"\x03\x00"`（`cmd=0x03`, `arg=0x00`），随后调用 `std::future<bool>::wait()`（`0x1ca0878`）与 `future::get()`（`0x2159bb0`）。返回值经 `csinc w0, #2, wzr, ne` 映射为 `true -> 0`、`false -> 2`。 |
| `reply_callback` @ `0x2159b4c` | 调用 `osal_get_msg_src@plt`（`0xb18560`）校验 `src == 0x92d2091c`；若匹配则读取 `uint8 msg[1]`，按 `msg[1] == 0x00 -> true` 写入 `std::promise<bool>::set_value`（`0x2159a24`），最后恒定调用 `osal_free_msg(0x81d705bd, msg)`（`0xb19d40`）。 |

### 2.2 Linux `/dev/rtc0` → 44B `udate`（`OSAL_DATECHG_NOTIFY`）→ `0x92d2091c` 合成规则

通过 `appFw.so::infra_wrapper_udate`（`0x215bf70`）及共享 `libosal_udate.so` / `udate.ko` 验证 44 字节 `udate` 结构体布局（`+0x00 elm`, `+0x02 factor`, `+0x04 year`, `+0x06 month`, `+0x07 day`, `+0x08 hour`, `+0x09 min`, `+0x0a sec`, `+0x10 time_type (1=UTC, 2=LOCAL, 3=UNSET)`, `+0x14 tz_type`, `+0x16 td`, `+0x18 dst`）：

- 当 Linux `/dev/rtc0` `struct rtc_time` 校验通过（`2000 <= year <= 2099` 且日历合法，`time_type ∈ {1, 2}`）时，合成 `b"\x03\x00"`（`src = 0x92d2091c`）唤醒 `promise(1)` → `rc = 0`。
- 当 RTC 未设置（`1970` / `time_type=3` / 非法日期）时，合成 `b"\x03\x01"`（`src = 0x92d2091c`）设置 `promise(0)` → `rc = 2`，不挂起。

### 2.3 Unicorn AArch64 执行验证（真实 FX6 `appFw.so`）

| 用例 | 阻塞挂起 | `promise<bool>` | 预期返回值 `rc` | 释放消息 | `SP` 守恒 |
|---|---|---|---|---|---|
| `q1_unintercepted_future_wait_hang` | **`True`** | `None` | `2`（挂起捕获） | `False` | `True` |
| `q1_intercepted_send_sync_rtc0` | `False` | `None`（发出 `0300`） | `0` | `False` | `True` |
| `q1_reply_cb_valid_rtc0_unblocks` | `False` | **`1` (`true`)** | **`0`** | `True` | `True` |
| `q1_reply_cb_unset_rtc0_false` | `False` | **`0` (`false`)** | **`2`** | `True` | `True` |
| `q1_reply_cb_wrong_src_ignored` | `False` | `None`（跳过写入） | `2` | `True` | `True` |

---

## 三、Queue 2（`0x91db059b` Smart Handle 手柄）与 XLR-H1 MI 热靴音频共存

### 3.1 `infra_wrapper_handle_procam_chaplin_base.cpp` 线协议

- `register_callback` @ `0x2107c6c`：先投递事件 `0x227`（`551` = 手柄脱离），在 `cb_qid`（`[0x5c398a8]`）注册回调 `0x2107b74`，再经 `send_sync_msg`（`0x215c38c`）向 `0x91db059b` 发送 12B 小端报文 `<III(0x81000001, 0, cb_qid)`；若返回非 `0` 则在 `0x2167784` 触发行 **`123` (`0x7b`)** 断言。
- `unregister_callback` @ `0x2107be4`：发送 12B `<III(0x81000002, 0, cb_qid)`；若非 `0` 则触发行 **`141` (`0x8d`)** 断言。
- `callback` @ `0x2107b74`：解析 `uint32 cmd = [msg+0]`：`0x88000001` → 投递 `0x226`（`550` 已连接），`0x88000002` → 投递 `0x227`（`551` 已脱离），并调用 `osal_free_msg(cb_qid, msg)`。

### 3.2 Unicorn AArch64 证明与 FX3 XLR-H1 共存证据

- 未拦截（`send_sync_msg = -1`）精确命中行 `123` 断言；
- `P11` 合成脱离态 ACK `<III(0x82000001, 0, cb_qid)` 后零断言通过，事件队列保持 `551`（脱离），`0x88000002` / `0x88000001` 回调与注销均零异常；
- 同轮执行真实 FX6 `libInfraHotshoe.so::WaitRecvCompMsgFromHotshoeRsrc`（`0x5d90`）返回 `rc = 0`，`appFw.so` 保留 `EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_ON/OFF`，且 `0x92840747` `0x032d`（`P5` 音频/HDMI `0x00580000`）链路完全独立不受影响。

---

## 四、`developing_mode_FHD`、Cine EI / 33³ 3D LUT DMA 与五轴 IBIS 桥接

1. **`developing_mode_FHD` 转译**：FX6 `PID_SET_DEVELOPING_MODE`（`0x0362 -> 0x10c1` @ `0x2035688`）对应 FX6 CP 独有键 `developing_mode_FHD`（FX3 `cpapp-b.bin` 为 0 命中）。`translate_developing_mode_fhd()` 将其映射至 FX3 Stock-CP 原生 `DevelopController` / `SetDevelopParam` 及共享键 `mov_size_req`、`frate_req`、`e_set_img_frame_size`、`mov_aspect_req` 与 `0x92840747` 命令（`0x0416`, `0x0169`, `0x016a`, `0x0165`, `0x0166`, `0x0152`）。
2. **`33^3` 3D LUT DMA（`0x0165`/`0x0166`）与双原生 ISO（800 / 12800）**：
   - `33^3 = 35,937` 体素：8-bit RGB 为 `107,811 B`（4B 对齐 `107,812 B`），16-bit RGB 为 `215,622 B`，`libmpr.so` `.cube` 缓冲区固定分配 `0x6a1b9 = 434,617 B`，`mpr::SetLutData` 描述符布局为 `164 B`（`+0x04` enable、`+0x05..+0x1e` 26B 元数据、`+0x1f..+0x5e` 64B 路径）。
   - `appFw.so::video_set_lookname_procam`（`0x20f1c04`）与 `set_user_lut_binary_data_procam_i`（`0x2112b10`）在大于 `0xbb80 = 48,000 B` 时自动切换至 DRAM/SRAM+REG DMA 模式。Unicorn 直接运行真实 FX6 `0x20f1c04` 生成的 36B `0x0165` 报文（`0d206501240001800300000001000000000000000010000024a501000000020000040000`）与 `CineEiLutDmaStateMachine` 状态机输出逐字节一致，完整覆盖 `IDLE -> CUBE_STAGED -> DMA_0165_ARMED -> LOOKNAME_0166_ENABLED -> RESET_DISABLED` 及 `800 / 12800` 双原生 ISO 转换（`baseSensitivity`, `HyperGainMode`/`uc_HighGainMode`, `EIValue`/`ul_EIGainValue`）。
3. **FX3 五轴 IBIS 遥测桥接契约**：
   - FX3 Stock-CP 通过 `LiroSeq: Restore.`（`p2:/Backup.bin + p2:/psd.bin + p6:Jiritsu`）驱动 `HallPIDOUT_0` / `GyroPIDOUT_0` / `FusionOUT_0` / `AllPIDOUT_0` / `PWMOUT_0` 维持居中锁止（Center-Lock）。
   - Unicorn 验证真实 FX6 `set_tc_on_movie_i`（`0x211019c`）：`Standard -> is_on_movie=1`、`Off -> is_on_movie=0`；`Active` 模式在 Stage-A 下安全回落至通电居中 `Standard`（或经 `CheckSetSteadyShotAdvancedMovie` / `steadyshot_body_axis_movie` 扩展桥接），`floating_sensor_hazard = False`。

---

## 五、双模式实跑与洁净室审计记录

| 检查项 | 命令 | 结果 |
|---|---|---|
| 本地只读 Donor 模式 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m fx6_closure.uipc_cp_shim_verifier` | **`PASS (LOCAL_DONOR_VERIFIED)`，exit code `0`** |
| `FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m fx6_closure.uipc_cp_shim_verifier` | **`PASS (CLEAN_ROOM_SYNTHETIC_VERIFIED)`，exit code `0`** |
| Phase 21 单元测试（双模式各 20 项） | `unittest outputs/fx6-on-fx3-closure/tests/test_phase21_uipc_cp_shim.py -v`（Local + Clean-Room） | **20/20 PASS（exit code `0`）** |
| 洁净室二进制/字节码审计 | `make clean-audit` | **CLEAN（0 `.pyc`/`.so`/`.bin`/`.cpio` 残留）** |
