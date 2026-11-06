# FX3 / FX6 `mpr::Init` 深度静态核查：`+0x1f2` (`780`/`1440`) 消费者、回调签名抽查与翻译层可行性判定

## 0. 结论先行

1. **任务 1（`+0x1f2` / `+0x28a` 的 `780` vs `1440` 语义与消费者）：已完全静态查明，该字段为单段连续录制时长上限 `recordableTime`（单位：分钟），在 `mpr::Init` 阶段 `780` 与 `1440` 可安全互换（若对齐 FX3 原生与 FX6 XAVC S 实际行为，应取 `780` = `0x030c`）。**
   - FX6 `libmpr.so` 在 `0x151580..0x151598` 读取 `MovieRecInfo + 0x1454`（即 `+0x28a` 的存储目标）并传入 `printf`，对应 `.rodata` `0xcc9eb9` 格式化字符串为 **`"recordableTime: %u\n"`**。它既不是缓冲区大小，也不是表项上限或模式枚举。
   - 在固定 FX3 `libmpr.so` 中，`0x11975c`（`XavcsMovieWriter` 初始化）在 `0x119798` 读取 `[x1, #0x18]`（即 `+0x1f2` `u16`），于 `0x1197a8` 写入 16B 日志包 `[x29, #0xa4]` 调 `0x115a2c` 发出（`0x115a2c` 仅原样 `memcpy` 16B 到 OSAL 日志消息，不对字段值做任何分支或分配计算），随后在 `0x1197c8..0x1197cc` 将其存入 `XavcsMovieWriter` 成员 `[x19, #0x24]`。
   - 在整个固定 FX3 `libmpr.so` 中，`[XavcsMovieWriter + 0x24]` 的**唯一读取点**位于 `_ZN16XavcsMovieWriter33CreateFreeBoxHeaderInStreamBufferEPN3mpr10RingBufferEj` 的 `0x11fac8: ldrh w2, [x25, #0x24]`，经 `0x11facc..0x11fad4: umaddl x0, w0, w2, x1` 计算秒数阈值 `60 * w2 - 60 = 60 * (w2 - 1)`，与当前已编码视频帧秒数 `frame_counter / fps` 比较（`0x11fae0: fcmpe s1, s0; 0x11fae4: b.lt 0x11fb48`），达到时长上限前 1 分钟时触发自动停录。
   - 在 FX6 `libmpr.so` 中，`EnterRec` (`0x157960..0x157a20`) 将 `MovieRecInfo + 0x1454` (`1440`) 传给 `MxfMovieWriter` 与 `XavcsMovieWriter` 的初始化虚函数：`MxfMovieWriter` (`0x194124..0x194128`) 保留传入的 `1440`（24 小时）存入 `[this + 0x78]`；而 **FX6 的 `XavcsMovieWriter` (`0x1b0f44: mov w0, #0x30c; 0x1b0f48: strh w0, [x19, #0x74]`) 忽略传入的 `1440`，强制硬编码覆写为 `780`（13 小时）**。

2. **任务 2（关键回调签名抽查）：优先抽查的 3 个回调（`gp_evtPowerOnFinishedFunc`、`gp_evtPowerOffFinishedFunc`、`gp_evtRecPbTimeFunc`）在 FX3 与 FX6 之间签名与载荷字段偏移 100% 一致；但扩展核查 `SendIssueEvent` 全表发现 8 个共有回调的载荷结构体大小不同，其中 `+0x60` (`gp_evtMovieWriteFinishedFunc`) 与 `+0x78` (`gp_evtMovieRecAutoDividedFunc`) 存在 ~1.88 KB 的堆越界读取风险。**
   - 固定 FX3 `libmpr.so` 在 `_ZN3mpr14SendIssueEventENS_5EVTIDEm` (`0xb442c..0xb4e70`) 中统一发起全部 `gp_evt*Func` 间接调用：调用前仅设置 `x0 = x19`（堆上分配的事件参数结构体指针），`x1` 为目标函数指针，`x2..x3` 不传参；返回后在 `0xb4488..0xb4494` 调用 `free(x19)`。
   - `gp_evtPowerOnFinishedFunc`（12B 载荷：读取 `+0x0`, `+0x4`, `+0x8` 三个 `u32`）、`gp_evtPowerOffFinishedFunc`（12B 载荷：读取 `+0x0`, `+0x4`, `+0x8` 三个 `u32`）、`gp_evtRecPbTimeFunc`（读取 `+0x4` `u8`, `+0x8..+0x10` 3×`u32`, `+0x14` `u8`, `+0x18..+0x20` 3×`u32`）在 FX3 `appFw.so` 与 FX6 `appFw.so` 中的参数读取宽度和偏移完全一致。
   - **关键反证发现**：横向比对 FX3 与 FX6 `SendIssueEvent` 的 57 个共有回调可见，有 **8 个共有回调在 FX3 与 FX6 中传入 `x0` 的载荷大小不一致**。最严重的是 `+0x60` `gp_evtMovieWriteFinishedFunc`（FX3 分配 `0x20 = 32B`，FX6 分配 `0x788 = 1,928B`）与 `+0x78` `gp_evtMovieRecAutoDividedFunc`（FX3 分配 `0x20 = 32B`，FX6 分配 `0x780 = 1,920B`）：FX6 `appFw.so` 的 `gp_evtMovieWriteFinishedFunc` (`0x213ca24`) 会无条件执行 `0x213caa0: ldrb w3, [x19, #0x770]` 与 `0x213caec: ldr x0, [x19, #0x778]`，并在 `[x19, #0x770] != 0` 时于 `0x213cb20..0x213cb30` 执行 `memcpy(sp+0x50, x19+0x14, 0x75c)`——若直接将 FX6 回调指针交给固定 FX3 `libmpr.so` 调用，一旦触发该事件将从 32 字节堆块越界读取达 1,880 字节。

3. **任务 3（完整翻译层是否还有必要继续）：应明确停止构建“仅转换 `mpr::Init` 入参 (`0x290 -> 0x1f8`) 的完整翻译层”。**
   - 仅重排 `mpr::Init` 的 `initInParam` 只能消除 `mpr::Init` 入口的偏移错位，无法解决：(a) 8 个共有回调在事件触发时的 `x0` 载荷结构体 ABI 裂变（需为不兼容回调编写二次转换载荷的 thunk 包装函数）；(b) FX6 新增的 10 个非空回调在 FX3 `libmpr.so` 中无挂载点；(c) 除 `mpr::Init` 外，`mpr::EnterRec` 等后续 API 的入参结构体（如 FX6 `enterRecInParam` 读取 `+0x27c` 等）同样存在跨代布局差异。

---

## 1. 任务 1：`+0x1f2` / `+0x28a` (`780` vs `1440`) 消费者静态追踪

### 1.1 字段定性：`recordableTime`（单段连续录制分钟数上限）

在供体 FX6 [`libmpr.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so) 中，`mpr::IntegRecordMovieInit` (`0x155d78`) 将第 4 参数 `w3`（由 `mpr::Init` `0x12bd30: ldrh w3, [x19, #0x28a]` 传入）存入 `MovieRecInfo + 0x1454`（`0x155de4: str w22, [x19, #0x1454]`）。

在调试打印函数 `0x15156c..0x151598` 中：

```text
  15156c: f9438694  ldr  x20, [x20, #0x708]      // x20 = g_movieRecInfo
  151570: 90005bc0  adrp x0, 0xcc9000
  151574: 913a9c00  add  x0, x0, #0xea7          // "enterRecMode: %u\n"
  151578: b953e281  ldr  w1, [x20, #0x13e0]
  15157c: 97fe7aed  bl   0xf0130 <printf@plt>
  151580: b9545681  ldr  w1, [x20, #0x1454]      // 读取 MovieRecInfo + 0x1454
  151584: 90005bc0  adrp x0, 0xcc9000
  151588: a9425bf5  ldp  x21, x22, [sp, #0x20]
  15158c: 913ae400  add  x0, x0, #0xeb9          // "recordableTime: %u\n"
  151590: a94153f3  ldp  x19, x20, [sp, #0x10]
  151594: a8c37bfd  ldp  x29, x30, [sp], #0x30
  151598: 17fe7ae6  b    0xf0130 <printf@plt>
```

直接读取 FX6 `libmpr.so` 文件偏移 `0xcc9ea7` 与 `0xcc9eb9` 处的 `.rodata` 字节：
- `0xcc9ea7`: `"enterRecMode: %u\n\0"`
- `0xcc9eb9`: **`"recordableTime: %u\n\0"`**

结合下文 `60 * w2 - 60` 的秒数换算指令，可 100% 证明该 `u16` 字段为**最大连续录制时间（单位：分钟）**：
- `780` (`0x030c`) = 780 分钟 = 13 小时；
- `1440` (`0x05a0`) = 1,440 分钟 = 24 小时。

### 1.2 固定 FX3 `libmpr.so` 中 `0x11975c`、`0x115a2c` 与 `[x19, #0x24]` 全路径

在固定 FX3 [`libmpr.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so) 中，从 `mpr::Init` 读取 `+0x1f2` 到最终消费的完整指令链如下：

#### 步骤 A：`mpr::Init` → `mpr::IntegRecordMovieInit` (`0xd6004..0xd613c`)

1. `0xb7080: 7943e663 ldrh w3, [x19, #0x1f2]` 读取 `u16` 并调用 `0xb7094: bl _ZN3mpr20IntegRecordMovieInitEjPKjjt@plt` (`0xd6004`)。
2. `IntegRecordMovieInit` 在 `0xd603c: 53003c79 uxth w25, w3` 保存 `w25 = recordableTime`：
   - **第一次写日志消息包**：在 `0xd6068: 29187fb9 stp w25, wzr, [x29, #0xc0]` 写入栈上 24 字节日志包 `[x29, #0xb0..#0xc7]`（消息头 `[x29, #0xb0]=0x2110`, `[x29, #0xb2]=0x170`, `[x29, #0xb4]=1`），于 `0xd606c: bl 0xc8c70` 发出。
   - **构造 8 个 `XavcsMovieWriter` 实例并传参**：在 `0xd608c..0xd613c` 的 4 次循环（`x28 = 1..4`）中，每次分配两个 `0x2c58`（11,352）字节的 `XavcsMovieWriter` 对象（`0xd60a8..0xd60b8` 与 `0xd60c8..0xd60d4`；构造函数 `0x11b9dc` 在 `0x11bb6c: 79004a7f strh wzr, [x19, #0x24]` 先将 `[this + 0x24]` 置 0），随后将 `w25` 存入栈上初始化参数结构 `init_arg` 的 `+0x18` 偏移：
     - 第 1 个实例（`x1 = x29 + 0x88`）：`0xd60e4: 790143b9 strh w25, [x29, #0xa0]`（`0x88 + 0x18 = 0xa0`），`0xd60f8: bl 0x11975c`；
     - 第 2 个实例（`x1 = x29 + 0xb0`）：`0xd6110: 790193b9 strh w25, [x29, #0xc8]`（`0xb0 + 0x18 = 0xc8`），`0xd6120: bl 0x11975c`。

#### 步骤 B：`0x11975c`（`XavcsMovieWriter` 初始化函数）与 `0x115a2c`

在 `0x11975c` 中，`x0`（`this`）保存在 `x19`（`0x11976c`），`x1`（`init_arg`）保存在 `x20`（`0x11977c`）：

```text
  119770: 52802400  mov  w0, #0x120              // =288 (sub-id)
  119778: 910263b5  add  x21, x29, #0x98         // x21 = 栈上 16B 日志包缓冲区
  11977c: aa0103f4  mov  x20, x1                 // x20 = init_arg
  119780: 790137a0  strh w0, [x29, #0x9a]
  119784: f9400420  ldr  x0, [x1, #0x8]
  11978c: 52800059  mov  w25, #0x2
  119790: b900a3a0  str  w0, [x29, #0xa0]
  119798: 79403020  ldrh w0, [x1, #0x18]         // 读取 init_arg + 0x18 (即 +0x1f2 u16)
  11979c: 52800201  mov  w1, #0x10               // 日志包长度 = 16 字节
  1197a4: 52846218  mov  w24, #0x2310            // 模块/消息 ID = 0x2310
  1197a8: b900a7a0  str  w0, [x29, #0xa4]        // 写入日志包 +0xc 偏移
  1197ac: aa1503e0  mov  x0, x21
  1197b0: 390273b9  strb w25, [x29, #0x9c]
  1197b4: 390277bf  strb wzr, [x29, #0x9d]
  1197b8: 39027bbf  strb wzr, [x29, #0x9e]
  1197bc: 39027fbf  strb wzr, [x29, #0x9f]
  1197c0: 790133b8  strh w24, [x29, #0x98]
  1197c4: 97fff09a  bl   0x115a2c                // 发送 16B 日志包
  1197c8: 79403280  ldrh w0, [x20, #0x18]        // 再次读取 init_arg + 0x18
  1197cc: 79004a60  strh w0, [x19, #0x24]        // 存入 XavcsMovieWriter + 0x24
```

- **`0x115a2c` 对该字段的处理**：`0x115a2c` (`0x115a2c..0x115b50`) 是通用 OSAL 日志发送函数（与 `0xb56ec` 同构）。它在 `0x115a30..0x115a4c` 仅检查长度参数 `0 < w1 <= 0xfe0` 且缓冲区指针 `x0 != 0`，调 `osal_valloc_msg_wait(0x8f013a, &msg, w1 + 0x20, 0)`，在 `0x115aa4..0x115aa8` 将 `[x29, #0x98..#0xa7]` 共 16 字节 `memcpy` 到 `msg + 0x18`，再调 `osal_snd_msg(0x8f013a, msg)`。**`0x115a2c` 完全不解析或比较 `[x29, #0xa4]` 处的 `recordableTime` 值**。
- **`0x11975c` 后续指令**：在 `0x1197cc` 写入 `[x19, #0x24]` 后，`0x11975c` 直至 `0x1199fc: ret` 再未读取 `[x20, #0x18]` 或 `[x19, #0x24]`（注：`0x1197f4`、`0x11980c`、`0x119824` 读取的是 `[x20, #0x1c]`/`#0x20`/`#0x24` 即 `IntegRecordMovieInit` 传入的固定常数 `10000, 10000, 100`，用于构造 3 个 `mpr::BaseList`）。

#### 步骤 C：`[XavcsMovieWriter + 0x24]` 的唯一读取与分支点 (`0x11fac8`)

扫描固定 FX3 `libmpr.so` 的 `XavcsMovieWriter` 代码段，对成员 `[this + 0x24]`（`u16`）的读取**全库仅有一处**，位于 `_ZN16XavcsMovieWriter33CreateFreeBoxHeaderInStreamBufferEPN3mpr10RingBufferEj` (`0x11cf84`) 内的 `0x11faa8..0x11fb3c`（`x25 = this`）：

```text
  11faa8: 97fd8d5a  bl     0x83010 <_ZN3mpr5Codec29GetEncStatusVideoFrameCounterEv@plt>
  11faac: b940f7a1  ldr    w1, [x29, #0xf4]
  11fab0: 350004c1  cbnz   w1, 0x11fb48          // 已触发过则跳过
  11fab4: b9444721  ldr    w1, [x25, #0x444]
  11fab8: 35000481  cbnz   w1, 0x11fb48
  11fabc: 1e202118  fcmpe  s8, #0.0              // s8 = 视频帧率 (fps)
  11fac0: 5400044d  b.le   0x11fb48
  11fac4: 1e230001  ucvtf  s1, w0                // s1 = (float)VideoFrameCounter
  11fac8: 79404b22  ldrh   w2, [x25, #0x24]      // w2 = this->recordableTime (即 +0x1f2 u16)
  11facc: 92800761  mov    x1, #-0x3c            // x1 = -60
  11fad0: 52800780  mov    w0, #0x3c             // w0 = 60
  11fad4: 9ba20400  umaddl x0, w0, w2, x1        // x0 = 60 * w2 - 60 = 60 * (w2 - 1) 秒
  11fad8: 1e281821  fdiv   s1, s1, s8            // s1 = 已录制秒数 (VideoFrameCounter / fps)
  11fadc: 9e230000  ucvtf  s0, x0                // s0 = (float)(60 * w2 - 60)
  11fae0: 1e202030  fcmpe  s1, s0                // 比较 已录制秒数 vs 60 * (w2 - 1)
  11fae4: 5400032b  b.lt   0x11fb48              // 若 < 阈值秒数，正常继续录制
  11fae8: 52800060  mov    w0, #0x3              // 若 >= 阈值秒数，封装 0x2310 / 0x238 日志包
  ...
  11fb1c: 97ffd7c4  bl     0x115a2c
  11fb20: a9438326  ldp    x6, x0, [x25, #0x38]  // 读取内部回调指针 [this+0x38] 与上下文 [this+0x40]
  11fb24: 528000a1  mov    w1, #0x5
  11fb28: f9402725  ldr    x5, [x25, #0x48]
  11fb2c: 52800004  mov    w4, #0x0
  11fb30: d2800003  mov    x3, #0x0
  11fb34: 52800002  mov    w2, #0x0
  11fb38: 72a80001  movk   w1, #0x4000, lsl #16  // w1 = 0x40000005 (超时停录事件码)
  11fb3c: d63f00c0  blr    x6                    // 触发停录回调
```

### 1.3 对照 FX6 `libmpr.so` 的消费者及 `780` vs `1440` 可替代性

在供体 FX6 `libmpr.so` 中，`MovieRecInfo + 0x1454` 除 `0x151580` 调试打印外，在 `_ZN3mpr8EnterRecERKNS_15enterRecInParamE` (`0x157960..0x157a20`) 中被读取：

1. `0x157960: ldr w0, [x22, #0x27c]; cmp w0, #0x8; b.ne 0x157808`：判断录制格式是否为 MXF (`8`)，分别构造 `MxfMovieWriter` (`0x199de4`) 或 `XavcsMovieWriter` (`0x1b3284`)。
2. `0x1579b8: ldrh w0, [x26, #0x1454]; strh w0, [x29, #0x98]` 与 `0x1579f0: ldrh w0, [x26, #0x1454]; strh w0, [x29, #0xc0]`：从 `MovieRecInfo + 0x1454` 读取 `1440` 放入 `init_arg + 0x18`，调用 writer 虚函数 `[vtable + 0x10]`：
   - **FX6 `MxfMovieWriter` (`0x1940b4`)**：`0x194124: ldrh w0, [x20, #0x18]` → `0x194128: strh w0, [x19, #0x78]` **保留传入的 `1440`**，并在 `0x199494: ldrh w2, [x19, #0x78]` 用于 `60 * w2 - 60`（86,340 秒 ≈ 24 小时）超时判断。
   - **FX6 `XavcsMovieWriter` (`0x1b0ed4`)**：`0x1b0f14: ldrh w0, [x1, #0x18]` 仅将其写入日志包，紧接着在 **`0x1b0f44: 52806180 mov w0, #0x30c` (`780`)、`0x1b0f48: 7900ea60 strh w0, [x19, #0x74]` 忽略传入的 `1440`，强制硬编码覆写为 `780`**，并在 `0x1b679c: ldrh w2, [x26, #0x74]` 用于 `60 * w2 - 60`（46,740 秒 ≈ 13 小时）超时判断。

**结论**：`780` 与 `1440` 的差异根源在于 FX6 需支持 MXF 24 小时（`1440` 分钟）录制，故在 `initInParam + 0x28a` 传入 `1440`，而在 FX6 `XavcsMovieWriter` 内部将其硬编码降回 `780` 分钟；固定 FX3 `libmpr.so` 仅有 `XavcsMovieWriter` 且直接采用 `+0x1f2` 传入值。因此**在 `mpr::Init` 及非超长录制（< 12 小时 59 分）下，`780` 与 `1440` 完全可互相替代且无任何初始化风险；若要与 FX3 原生及 FX6 XAVC S 实际阈值严格一致，应取 `780` (`0x030c`)**。

---

## 2. 任务 2：关键回调签名与载荷结构抽查

### 2.1 固定 FX3 `libmpr.so` 的统一回调分发机制 (`_ZN3mpr14SendIssueEventENS_5EVTIDEm`)

在固定 FX3 [`libmpr.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so) 中，所有 `gp_evt*Func` 全局指针均在 `_ZN3mpr14SendIssueEventENS_5EVTIDEm` (`0xb442c..0xb4e70`) 内被读取并调用：

- **入口与参数来源**：
  - 上游生产者调用 `_ZN3mpr13SetIssueEventENS_5EVTIDEPvm` (`0xb4164`, 参数 `w0 = EVTID, x1 = payload_ptr, x2 = payload_size`) → `_ZN3mpr13SetEventParamEjNS_5EVTIDEPvm` 将载荷拷贝到堆内存并投递至事件队列；
  - 事件线程取出后调用 `SendIssueEvent(w0 = EVTID, x1 = heap_payload_ptr)`；
  - `0xb4430: sub w0, w0, #0x1, lsl #12` (`w0 - 0x1000`)，`0xb4434: cmp w0, #0x38`，`0xb4440: mov x19, x1`（`x19` 保存堆上载荷结构体指针），按 `0x2cb3f8` 跳转表分发；
  - 各分支调用 `blr x1` 时，**统一仅设置 `x0 = x19`（事件载荷结构体指针）**，`x1` 为回调函数地址，`x2..x3` 未作为参数赋值（当分支调用了日志辅助函数 `0xb3a78(x0=x19, w1=payload_size)` 时，`x2..x3` 为 `0xb3a78` 返回后的残留值，回调函数体均不读取 `x1..x3`）；
  - 分发结束后统一跳回 `0xb4488: mov x0, x19; ... 0xb4494: b 0x7d630 <free@plt>` 释放堆块。

### 2.2 优先抽查的 3 个回调（签名与字段读取 100% 相同）

| 回调全局符号 | FX3 `libmpr.so` 调用点与 `x0..x3` 来源 | FX3 `appFw.so` 回调体读取的偏移/宽度 | FX6 `appFw.so` 回调体读取的偏移/宽度 | 比对结果 |
|---|---|---|---|---|
| `_ZN3mpr25gp_evtPowerOnFinishedFuncE`<br>FX3 `initInParam+0x150`<br>FX6 `initInParam+0x188`<br>FX3 GOT: `0x2f9ce0` | **载荷构造**：`PowerOnMain` (`0xb55f8..0xb561c`) 在栈 `[x29,#0x10..#0x1b]` 构造 `0xc` (12B)：`+0x0 = 0x1026` (`u32`)、`+0x4 = [arg+#0x15d0]` (`u32`)、`+0x8 = 0` (`u32`)。<br>**调用点 (`0xb4b6c..0xb4b90`)**：<br>`b4b6c: adrp x20, 0x2f9000`<br>`b4b70: ldr x20, [x20, #0xce0]`<br>`b4b7c: mov x0, x19`<br>`b4b80: mov w1, #0xc`<br>`b4b84: bl 0xb3a78`<br>`b4b88: ldr x1, [x20]`<br>`b4b8c: mov x0, x19` (`x0`=12B 载荷指针, `x2..x3` 无参)<br>`b4b90: blr x1` | 函数 @ `0x2e6d1dc..0x2e6d2a8`<br>(`0x2e6d1f4: mov x22, x0`)<br>- `+0x0` (`u32`): `0x2e6d224: ldr w7, [x22]`<br>- `+0x4` (`u32`): `0x2e6d250: ldr w1, [x22, #0x4]` → 写入 `[obj+#0x3e4]`<br>- `+0x8` (`u32`): `0x2e6d258: ldr w1, [x22, #0x8]` → 写入 `[obj+#0x8]`<br>不读 `x1..x3` | 函数 @ `0x213c064..0x213c0ec`<br>(`0x213c070: mov x20, x0`)<br>- `+0x0` (`u32`): `0x213c084: ldr w7, [x20]`<br>- `+0x4` (`u32`): `0x213c0b0: ldr w1, [x20, #0x4]` → 写入 `[obj+#0x3e4]`<br>- `+0x8` (`u32`): `0x213c0b8: ldr w1, [x20, #0x8]` → 写入 `[obj+#0x8]`<br>不读 `x1..x3` | **相同**（均为 `void(const u32[3]* x0)`，12B 载荷三字段偏移、宽度、写入目标偏移完全一致） |
| `_ZN3mpr26gp_evtPowerOffFinishedFuncE`<br>FX3 `initInParam+0x148`<br>FX6 `initInParam+0x180`<br>FX3 GOT: `0x2f93b8` | **载荷构造**：`PowerOffMain` (`0xb55c8..0xb55ec`) 在栈 `[x29,#0x10..#0x1b]` 构造 `0xc` (12B)：`+0x0 = 0x1025` (`u32`)、`+0x4 = [arg+#0x15d0]` (`u32`)、`+0x8 = 0` (`u32`)。<br>**调用点 (`0xb4b40..0xb4b64`)**：<br>`b4b40: adrp x20, 0x2f9000`<br>`b4b44: ldr x20, [x20, #0x3b8]`<br>`b4b50: mov x0, x19`<br>`b4b54: mov w1, #0xc`<br>`b4b58: bl 0xb3a78`<br>`b4b5c: ldr x1, [x20]`<br>`b4b60: mov x0, x19` (`x0`=12B 载荷指针, `x2..x3` 无参)<br>`b4b64: blr x1` | 函数 @ `0x2e6d2ac..0x2e6d378`<br>(`0x2e6d2c4: mov x22, x0`)<br>- `+0x0` (`u32`): `0x2e6d2f4: ldr w7, [x22]`<br>- `+0x4` (`u32`): `0x2e6d320: ldr w1, [x22, #0x4]` → 写入 `[obj+#0x3e4]`<br>- `+0x8` (`u32`): `0x2e6d328: ldr w1, [x22, #0x8]` → 写入 `[obj+#0x8]`<br>不读 `x1..x3` | 函数 @ `0x213c0f0..0x213c178`<br>(`0x213c0fc: mov x20, x0`)<br>- `+0x0` (`u32`): `0x213c110: ldr w7, [x20]`<br>- `+0x4` (`u32`): `0x213c13c: ldr w1, [x20, #0x4]` → 写入 `[obj+#0x3e4]`<br>- `+0x8` (`u32`): `0x213c144: ldr w1, [x20, #0x8]` → 写入 `[obj+#0x8]`<br>不读 `x1..x3` | **相同**（均为 `void(const u32[3]* x0)`，12B 载荷三字段偏移、宽度、写入目标偏移完全一致） |
| `_ZN3mpr19gp_evtRecPbTimeFuncE`<br>FX3 `initInParam+0x130`<br>FX6 `initInParam+0x168`<br>FX3 GOT: `0x2fa470` | **载荷构造**：`SetRecPbTimeEvent` (`0xb5010..0xb50ac`) 初始化 `evtRecPbTimeParam`（`+0x0 = 0x1022`，清零 `+0x4, +0x14, +0x24, +0x30` 标志字节并调子函数填充）。<br>**调用点 (`0xb4acc..0xb4ae0`)**：<br>`b4acc: adrp x0, 0x2fa000`<br>`b4ad0: ldr x0, [x0, #0x470]`<br>`b4ad4: ldr x1, [x0]`<br>`b4ad8: cbz x1, 0xb4488`<br>`b4adc: mov x0, x19` (`x0`=`evtRecPbTimeParam*`, `x2..x3` 无参)<br>`b4ae0: blr x1` | 函数 @ `0x2e51ce4..0x2e51ec8`<br>(`0x2e51cf4: mov x19, x0`)<br>- `+0x4` (`u8`): `0x2e51d24: ldrb w0, [x19, #0x4]`<br>- `+0x8..+0x10` (`3×u32`): `0x2e51d3c..0x2e51d4c: ldr w2, [x19, #0x8/#0xc/#0x10]`<br>- `+0x14` (`u8`): `0x2e51d58: ldrb w0, [x19, #0x14]`<br>- `+0x18..+0x20` (`3×u32`): `0x2e51d6c: ldp w26, w21, [x19, #0x18]`, `0x2e51e34: ldr w0, [x19, #0x1c]`, `0x2e51e40: ldr w0, [x19, #0x20]`<br>不读 `x1..x3` | 函数 @ `0x212b720..0x212b804`<br>(`0x212b72c: mov x19, x0`)<br>- `+0x4` (`u8`): `0x212b730: ldrb w0, [x0, #0x4]`<br>- `+0x8..+0x10` (`3×u32`): `0x212b74c..0x212b75c: ldr w2, [x19, #0x8/#0xc/#0x10]`<br>- `+0x14` (`u8`): `0x212b768: ldrb w0, [x19, #0x14]`<br>- `+0x18..+0x20` (`3×u32`): `0x212b77c: ldp w22, w21, [x19, #0x18]`, `0x212b7d8: ldr w0, [x19, #0x1c]`, `0x212b7e0: ldr w0, [x19, #0x20]`<br>不读 `x1..x3` | **相同**（读取的全部 8 个字段偏移与宽度完全一致） |

### 2.3 扩展核查：发现 8 个共有回调存在载荷结构体大小差异及 2 个严重堆越界读冲突

对比固定 FX3 `libmpr.so` (`0xb442c..0xb4e70`) 与供体 FX6 `libmpr.so` 的 `SendIssueEvent` 全表 57 个共有回调中传给 `0xb3a78` 的 `w1`（事件载荷字节数），49 个共有回调载荷大小相同，但以下 **8 个共有回调在 FX3 与 FX6 之间载荷结构体大小不同**：

| 回调全局符号 | FX3 `initInParam` 偏移 | FX6 `initInParam` 偏移 | FX3 载荷大小 (`w1`) | FX6 载荷大小 (`w1`) | 回调体参数读取差异（由指令直接证明） |
|---|---|---|---|---|---|
| `_ZN3mpr28gp_evtMovieWriteFinishedFuncE` | `+0x060` | `+0x060` | **`0x20` (32B)**<br>(`0xb4660`, `blr` @ `0xb4674`) | **`0x788` (1,928B)** | **严重不兼容（堆越界读）**：<br>- FX3 `appFw.so` (`0x2e52150`) 仅读 `+0x4`, `+0x8`, `+0xc` (`u32`) 与 **`+0x10` (`u64`, `0x2e521b4: ldr x0, [x19, #0x10]`)**；<br>- FX6 `appFw.so` (`0x213ca24`) 因结构体中间插入 `0x75c` (1,884B) 数据块，无条件执行 **`0x213caa0: ldrb w3, [x19, #0x770]`** 与 **`0x213caec: ldr x0, [x19, #0x778]`**（在 FX3 32B 堆块上越界读 `+0x770`/`+0x778`），且若 `[x19, #0x770] != 0` 则在 **`0x213cb20..0x213cb30` 执行 `memcpy(sp+0x50, x19+0x14, 0x75c)`** 越界拷贝 1,884 字节！ |
| `_ZN3mpr29gp_evtMovieRecAutoDividedFuncE` | `+0x078` | `+0x078` | **`0x20` (32B)**<br>(`0xb46e4`, `blr` @ `0xb46f8`) | **`0x780` (1,920B)** | **严重不兼容（堆越界读）**：<br>- FX3 `appFw.so` (`0x2e51fbc`) 仅读 `+0x4`, `+0x8` (`u32`) 与 **`+0x10` (`u64`, `0x2e52018: ldr x2, [x21, #0x10]`)**；<br>- FX6 `appFw.so` (`0x212d9fc`) 无条件执行 **`0x212da18: ldrb w3, [x0, #0x76c]`** 与 **`0x212da54: ldr x2, [x20, #0x770]`**，且若 `[x20, #0x76c] != 0` 则在 **`0x212da84..0x212da94` 执行 `memcpy(sp+0x40, x20+0x10, 0x75c)`** 越界拷贝 1,884 字节！ |
| `_ZN3mpr27gp_evtLoadMovieFinishedFuncE` | `+0x010` | `+0x010` | `0x14` (20B)<br>(`0xb44ac`, `blr` @ `0xb44bc`) | `0x11c` (284B) | 顶层回调体（FX3 `0x2e6e478` / FX6 `0x213cf38`）均只读 `+0x0` (`w7`) 与 `+0x8` (`w1`)，但后续是否经子调用访问扩展区 `unknown` |
| `_ZN3mpr31gp_evtMovieRecStatusChangedFuncE` | `+0x028` | `+0x028` | `0x10` (16B)<br>(`0xb4530`, `blr` @ `0xb4540`) | 无 `0xb3a78` 日志调用 | 需单独追踪载荷构造与接收端（`unknown`） |
| `_ZN3mpr32gp_evtReadStillImageFinishedFuncE` | `+0x0c0` | `+0x0c0` | `0xb78` (2,936B)<br>(`0xb47b8`, `blr` @ `0xb47cc`) | `0xb58` (2,904B) | 结构体大小相差 32B，内部字段偏移映射 `unknown` |
| `_ZN3mpr28gp_evtAudioWriteFinishedFuncE` | `+0x100` | `+0x100` | `0xc` (12B)<br>(`0xb49d8`, `blr` @ `0xb49e8`) | `0x10` (16B) | 结构体大小相差 4B，接收端读取差异 `unknown` |
| `_ZN3mpr22gp_evtEditProgressFuncE` | `+0x138` | `+0x170` | `0x14` (20B)<br>(`0xb4afc`, `blr` @ `0xb4b0c`) | `0x20` (32B) | 结构体大小相差 12B，接收端读取差异 `unknown` |
| `_ZN3mpr22gp_evtEditFinishedFuncE` | `+0x140` | `+0x178` | `0x14` (20B)<br>(`0xb4b28`, `blr` @ `0xb4b38`) | `0x1c` (28B) | 结构体大小相差 8B，接收端读取差异 `unknown` |
| `_ZN3mpr32gp_evtMovieRecFileNameUpdateFuncE` | `+0x1b8` | `+0x240` | `0x4` (4B)<br>(`0xb4d64`, `blr` @ `0xb4d74`) | `0xc` (12B) | **相同（无影响）**：FX3 (`0x2e51a0c`) 与 FX6 (`0x2129360`) 回调体均完全不读取 `x0` |

---

## 3. 任务 3：“完整翻译层”是否还有必要继续

### 3.1 判定结论：停止构建单纯的 `mpr::Init` (`0x290 -> 0x1f8`) 完整翻译层

综合上一份报告与本轮任务 1、任务 2 的指令级证据：

1. **为什么单纯的 `mpr::Init` 入参翻译层不可行（停止判据）**：
   - 即便编写完整入参重排层（保留 `+0x08..+0x128`、将 FX6 `+0x168..+0x1d0` 平移至 `+0x130..+0x198`、将 FX6 `+0x228..+0x250` 按符号重排至 `+0x1a0..+0x1c8`、将 FX6 `+0x268..+0x289` 迁至 `+0x1d0..+0x1f1`、并在 `+0x1f2` 填入 `780`），也**只能让 `mpr::Init` 自身跑完注册流程**。
   - 一旦进入实际录制/文件写入生命周期，固定 FX3 `libmpr.so` 的 `SendIssueEvent` 在触发 `+0x60` (`gp_evtMovieWriteFinishedFunc`) 或 `+0x78` (`gp_evtMovieRecAutoDividedFunc`) 时，只会分配 **32 字节**的 FX3 版事件载荷传给 FX6 `appFw.so` 回调，而 FX6 `appFw.so` 会按 **1,928 / 1,920 字节**的 FX6 版结构体去读 `+0x770`/`+0x778` 甚至 `memcpy` `0x75c` 字节，必然引发 **~1.88 KB 堆越界读取与内存破坏**。
   - 此外，FX6 `0x290` 中 10 个非空新增回调（如 `gp_evtRecClipNameFunc` `+0x1f8`、`gp_evtNextClipNameFunc` `+0x200`、`gp_evtMovieRecResumedFunc` `+0x258`、`gp_evtMovieRecPausedFunc` `+0x260` 等）在固定 FX3 `libmpr.so` 中根本没有事件源；且 FX6 `mpr::EnterRec` 等后续 API 的入参结构体（如 `0x157960: ldr w0, [x22, #0x27c]`）同样与 FX3 存在跨代结构体偏移差异。

2. **如果后续仍要推进（无论是仅做“窄范围开机/菜单观察”还是构建“带回调 Thunk 的全套 ABI 适配层”），必须先在静态阶段解决的最小未知清单（`unknown` 清单）**：
   - **`unknown-1`（开机至菜单阶段实际触发的回调集合）**：在仅开机进入菜单、不触发录制的窄窗口内，固定 FX3 `libmpr.so` 除 `gp_evtPowerOnFinishedFunc`（已证 12B 载荷兼容）外，是否还会触发 `gp_evtLoadStillFinishedFunc`、`gp_evtLoadMovieFinishedFunc`、`gp_evtLoadFinishedFunc`、`gp_evtStillRecStatusChangedFunc`、`gp_evtMovieRecStatusChangedFunc`、`gp_evtResetNecessityInfoFunc` 等回调，以及这些回调在 FX3 与 FX6 `appFw.so` 中的载荷字段偏移是否完全一致。
   - **`unknown-2`（其余 5 个载荷大小不同的共有回调接收端详情）**：`gp_evtLoadMovieFinishedFunc` (`20B` vs `284B`)、`gp_evtMovieRecStatusChangedFunc`、`gp_evtReadStillImageFinishedFunc` (`2936B` vs `2904B`)、`gp_evtAudioWriteFinishedFunc` (`12B` vs `16B`)、`gp_evtEditProgressFunc` (`20B` vs `32B`)、`gp_evtEditFinishedFunc` (`20B` vs `28B`) 在 FX6 `appFw.so` 及其子函数中的完整读取偏移，以及能否通过零扩展 thunk 安全桥接。
   - **`unknown-3`（FX6 `appFw.so` 导入的其他 `libmpr.so` 符号 ABI 兼容性）**：FX6 `appFw.so` 除 `_ZN3mpr4InitERKNS_11initInParamE` 外导入的全部 `mpr::*` 函数列表及其入参/出参结构体在固定 FX3 `libmpr.so` 与供体 FX6 `libmpr.so` 之间的大小与偏移差异（例如 `mpr::EnterRec`、`mpr::LoadMedia` 等）。
   - **`unknown-4`（`IntegStatusInit` 对 `+0x1d4` 槽位数组后两项 `0x0` vs `0xffff` 的下游影响）**：FX3 `InitStillStatus` (`0xf4270`) 与 `InitMovieStatus` (`0xf4338`) 不读 `count` 而直接遍历 4 个 `u32` 并与 `0xffff` 比较，FX6 传入 `[0x1000, 0x1010, 0, 0]` 时后两项 `0` 在 FX3 `libmpr.so` 中被标记为 active 槽位 `0` 是否会影响后续状态查询。

---

## 4. 复核命令记录

```sh
# 1. 验证 FX6 libmpr.so 中 MovieRecInfo+0x1454 的格式化字符串与 EnterRec / MovieWriter 消费者
python3 -c '
with open("/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so", "rb") as f:
    f.seek(0xcc9ea7); print(f.read(64))
'
objdump -d --start-address=0x15156c --stop-address=0x15159c \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so
objdump -d --start-address=0x157940 --stop-address=0x157a40 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so
objdump -d --start-address=0x1940b4 --stop-address=0x194140 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so
objdump -d --start-address=0x1b0ed4 --stop-address=0x1b0f60 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so

# 2. 验证 FX3 libmpr.so 中 0x11975c、0x115a2c 与 0x11fac8 (XavcsMovieWriter+0x24 唯一读取点)
objdump -d --start-address=0x11975c --stop-address=0x119840 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so
objdump -d --start-address=0x115a2c --stop-address=0x115b50 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so
objdump -d --start-address=0x11faa8 --stop-address=0x11fb48 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so

# 3. 验证 FX3 libmpr.so SendIssueEvent (0xb442c..0xb4e70) 与 FX3/FX6 appFw.so 回调体
objdump -d --start-address=0xb442c --stop-address=0xb4e74 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so
objdump -d --start-address=0x2e6d1dc --stop-address=0x2e6d37c \
  /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so
objdump -d --start-address=0x213c064 --stop-address=0x213c17c \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so
objdump -d --start-address=0x213ca24 --stop-address=0x213cbcc \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so
```
