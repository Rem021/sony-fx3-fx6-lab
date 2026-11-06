# FX3 `mpr::Init` 返回 3 独立复核与 `0x1f8` / `0x290` 布局比对报告

## 0. 结论先行

1. **Part A（独立复核 `w0=3` 根因）：同意（Agree）主协调端判读。**
   - 固定 FX3 `libmpr.so` 中 `_ZN3mpr4InitERKNS_11initInParamE` 位于 `0xb6844`，大小 `0x884`（范围 `0xb6844..0xb70c8`）。
   - 函数入口在 `0xb6870` 执行 `ldr w0, [x19, #0x1d0]`，在 `0xb6874` 执行 `cmp w0, #0x4`，在 `0xb6878` 执行 `b.ls 0xb68e0`。当无符号 `w0 > 4` 时，进入 `0xb687c..0xb68ac` 分支，于 `0xb6898` 执行 `mov w19, #0x3`，随后经 `0xb68b0` 公共出口块在 `0xb68c8` 执行 `mov w0, w19`，并于全函数唯一返回指令 `0xb68dc: ret` 返回 `w0=3`。
   - 全函数 `0xb6844..0xb70c8` 内仅有两处给返回值寄存器 `w19` 赋值：`0xb6898`（`mov w19, #0x3`）和正常路径末尾 `0xb7090`（`mov w19, #0x0`）。因此 **`u32([x19 + 0x1d0]) > 4` 是该函数返回 `3` 的唯一路径**。
   - `mpr-ro-b22ccc48` 捕获的 FX6 `0x290` 记录在 `+0x1d0..+0x1d7` 存放的是 64 位回调指针 `0x7ee3fb3de0`（原始字节 `e03dfbe37e000000`，低 32 位 `0xe3fb3de0 = 3,824,893,408 > 4`），而 FX6 真实 `count=2` 位于 `+0x268..+0x26b`（原始字节 `02000000`）。FX3 `mpr::Init` 在入口保护处即因把回调指针低 32 位误读为 `count` 而直接返回 `3`，未进入 `0xb68e0` 之后的正常初始化路径。

2. **Part B（`0x1f8` / `0x290` 最小适配静态可行性）：按“把 `count=2` 放到 `+0x1d0`、条目区由 FX6 数据转换、其他字段原样或显式零填充”的最小适配方案静态不可行；应明确停止，不做猜测性填充。**
   - **静态阻断 1（`+0x130..+0x1c8` 的 20 个回调指针槽位发生结构性错位）**：FX3 `0x1f8`（504B）与 FX6 `0x290`（656B）仅在 `+0x08..+0x128`（前 37 个回调指针）偏移与目标符号完全一致。FX6 在 `+0x130..+0x160` 插入了 7 个 FX3 不存在的音频编解码回调槽（共 `0x38` 字节，本轮值全为 `0`），导致 FX3 `+0x130..+0x198` 的 14 个回调在 FX6 中整体后移 `+0x38` 至 `+0x168..+0x1d0`；之后 FX6 在 `+0x1d8..+0x220` 又插入 10 个槽位，使 FX3 `+0x1a0..+0x1c8` 的 6 个回调在 FX6 中移至 `+0x228..+0x250` 且内部顺序重排。因此对于 `+0x130..+0x1c8`：
     - 若**保持 FX6 原样**：FX3 `+0x130..+0x160`（含 `gp_evtPowerOffFinishedFunc`、`gp_evtPowerOnFinishedFunc`）被填 `0`，而 `+0x168..+0x1c8` 的 13 个全局回调槽会被写入**错误的 FX6 事件回调函数地址**（例如把 `gp_evtPowerOnFinishedFunc` 写进 FX3 的 `gp_evtStillTransferDataBuiltFunc`）。
     - 若**显式零填充**：FX3 `+0x130..+0x1c8` 的 20 个事件回调（含 PowerOn / PowerOff / Edit / Repair / Recovery / ClipStatus 等）全部变为 `NULL`。
   - **静态阻断 2（`+0x1e4..+0x1f3` 尾部非指针参数区重叠在 FX6 指针区上，原样或零填充均破坏语义）**：FX3 尾部 40 字节控制块 `+0x1d0..+0x1f7` 与 FX6 尾部 40 字节控制块 `+0x268..+0x28f` 一一对应（整体平移 `+0x98`）。若仅改 `+0x1d0`（`count`）和 `+0x1d4..+0x1e3`（条目区），而对 `+0x1e4..+0x1f3`：
     - 若**保持 FX6 原样**：FX3 会把 FX6 `+0x1e0`、`+0x1e8`、`+0x1f0` 三个回调指针的半字碎片当作 `+0x1e4`（读出 `0x7e`，原值应为 `0xffff`）、`+0x1e8` `UmidMatNoGenMethod`（读出 `0xe3fb3c3c`，原值应为 `1`）、`+0x1ec..+0x1f1` 6B 设备节点 ID（读出 `7e0000006808`，原值应为 `ffffffffffff`）和 `+0x1f2` `u16`（读出 `0xe3fa = 58,362`）。
     - 若**显式零填充**：`+0x1e4` 由 `0xffff` 变为 `0`（在 `IntegRecordMovieInit` 中该值参与槽位跳过比较 `cmp w1, #0xffff; ccmp w0, w1, #4, ne`），`+0x1e8` 变为 `0`，`+0x1ec..+0x1f1` 变为全 `0`，`+0x1f2` 变为 `0`。
   - **静态阻断 3（即便做跨偏移重排，仍存在 `+0x1f2`/`+0x28a` 780 vs 1440 语义未知及 FX6 10 个非空新增回调丢失问题）**：FX3 `appFw.so` 在 `+0x1f2` 固定写入 `0x030c`（`780`），FX3 `IntegRecordMovieInit` 立即用它初始化两个 `XavcsMovieWriter` 实例；FX6 `appFw.so` 在 `+0x28a` 写入 `0x05a0`（`1440`），FX6 `IntegRecordMovieInit` 仅将其存入 `MovieRecInfo+0x1454`。`780` 与 `1440` 在固定 FX3 `libmpr.so` 内部路径的语义兼容性未知（`unknown`），且 FX6 `0x290` 中另有 10 个非空回调指针在 FX3 `libmpr.so` 中根本不存在对应全局变量。

---

## 1. Part A：独立复核证据

### 1.1 复核输入与 SHA256

| 对象 | 路径 | SHA256 / 关键属性 |
|---|---|---|
| 固定 FX3 `libmpr.so` | [`libmpr.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so) | `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` |
| 供体 FX6 `appFw.so` | [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| 观察记录 | [`mpr-observation.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/runs/mpr-ro-b22ccc48/mpr-observation.json) | `records[2].parameter_0x290_sha256` = `585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1`（656 字节） |
| 供体 FX6 `libmpr.so`（静态对照） | [`libmpr.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so) | `_ZN3mpr4InitERKNS_11initInParamE` @ `0x12b3dc`，大小 `0x9a4` |
| 固定 FX3 `appFw.so`（静态对照） | [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so) | `mpr::Init` 调用方位于 `0x2e58b98..0x2e58f68`（调用点 `0x2e58f3c`） |

### 1.2 函数边界与唯一返回 3 路径核对

通过 `objdump -T` 与 `objdump -d` 复核固定 FX3 [`libmpr.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so)：

```text
00000000000b6844 g    DF .text	0000000000000884              _ZN3mpr4InitERKNS_11initInParamE
```

- **函数起止**：`0xb6844` 至 `0xb70c8`（`0xb6844 + 0x884 = 0xb70c8`，末条指令为 `0xb70c4: 17ffff64 b 0xb6e54`）。
- **入口与错误返回指令序列（`0xb6844..0xb68e0`）**：

```text
   b6844: a9b27bfd     	stp	x29, x30, [sp, #-0xe0]!
   b6848: 52803f01     	mov	w1, #0x1f8              // =504 (FX3 initInParam 大小)
   b684c: 910003fd     	mov	x29, sp
   b6850: a90153f3     	stp	x19, x20, [sp, #0x10]
   b6854: aa0003f3     	mov	x19, x0                 // x19 = &initInParam
   b6858: a9025bf5     	stp	x21, x22, [sp, #0x20]
   b685c: a90363f7     	stp	x23, x24, [sp, #0x30]
   b6860: f90023f9     	str	x25, [sp, #0x40]
   b6864: 97fffba2     	bl	0xb56ec                 // trace/log 拷贝 0x1f8 字节
   b6868: aa1303e0     	mov	x0, x19
   b686c: 97ff2f75     	bl	0x82640 <_ZNK3mpr11initInParam8DbgPrintEv@plt> // 0xa7600: ret
   b6870: b941d260     	ldr	w0, [x19, #0x1d0]       // 读取 +0x1d0 处 u32 count
   b6874: 7100101f     	cmp	w0, #0x4                // 与 4 比较
   b6878: 54000349     	b.ls	0xb68e0                 // 无符号 <= 4 则进入正常路径 0xb68e0
   b687c: 52800061     	mov	w1, #0x3
   b6880: b90083a0     	str	w0, [x29, #0x80]
   ...
   b6898: 52800073     	mov	w19, #0x3               // 唯一将返回值 w19 置为 3 的指令
   ...
   b68ac: 97fffb90     	bl	0xb56ec
   b68b0: 52800020     	mov	w0, #0x1                // 公共收尾块 (0xb70b0 亦跳转至此)
   b68b4: 52800101     	mov	w1, #0x8
   b68b8: 290f7fa0     	stp	w0, wzr, [x29, #0x78]
   b68bc: 9101e3a0     	add	x0, x29, #0x78
   b68c0: 97fffb8b     	bl	0xb56ec
   b68c4: f94023f9     	ldr	x25, [sp, #0x40]
   b68c8: 2a1303e0     	mov	w0, w19                 // w0 = w19
   b68cc: a94153f3     	ldp	x19, x20, [sp, #0x10]
   b68d0: a9425bf5     	ldp	x21, x22, [sp, #0x20]
   b68d4: a94363f7     	ldp	x23, x24, [sp, #0x30]
   b68d8: a8ce7bfd     	ldp	x29, x30, [sp], #0xe0
   b68dc: d65f03c0     	ret                     // 全函数唯一 ret
```

- **唯一性证明**：遍历 `0xb6844..0xb70c8` 全部指令，仅有 `0xb68dc` 一条 `ret` 指令；`w0` 在 `0xb68c8` 由 `w19` 赋值；`x19`/`w19` 在 `0xb6854` 保存 `x0` 后，仅在 `0xb6898: mov w19, #0x3`（`w0 > 4` 保护分支）和 `0xb7090: mov w19, #0x0`（正常初始化路径末尾，`0xb70b0: b 0xb68b0` 之前）被改写。正常路径内所有子调用均不早退或改写 `w19`。故 `w0=3` 只能来自 `0xb6870..0xb6878` 的 `u32([x19 + 0x1d0]) > 4` 分支。

### 1.3 原始字节核对（`mpr-ro-b22ccc48`）

从 [`mpr-observation.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/runs/mpr-ro-b22ccc48/mpr-observation.json) 的 `records[2]`（`kind == "call"`，`ap_bias = 0x7ee1e78000`）提取关键偏移原始字节：

| 偏移 | 原始字节（hex） | 按小端解码 | FX6 `0x290` 语义 | FX3 `0x1f8` 在该偏移读取的语义 |
|---|---|---|---|---|
| `+0x1d0..+0x1d7` | `e03dfbe37e000000` | u64 = `0x0000007ee3fb3de0` (`AP+0x213bde0`)<br>低 32 位 (`+0x1d0..+0x1d3`) = `0xe3fb3de0` (`3,824,893,408`) | `gp_evtSetEssenceMarkInPlayFinishedFunc` 回调指针（由 FX6 `appFw.so` `0x212f698..0x212f6a0` 写入） | `u32 count`（`0xb6870`、`0xb6ccc`、`0xb7048`、`0xb708c` 四处读取），因 `0xe3fb3de0 > 4` 触发保护返回 `3` |
| `+0x1d4..+0x1e3` | `7e000000 00000000 00000000 383bfbe3` | 4 × u32 = `[0x7e, 0x0, 0x0, 0xe3fb3b38]` | `+0x1d0` 指针高 32 位、`+0x1d8` 空槽（8B `0`）、`+0x1e0` 回调指针低 32 位 | `u32[4]` 槽位/媒体 ID 条目数组 |
| `+0x1f2..+0x1f3` | `fae3` | u16 = `0xe3fa` (`58,362`) | `+0x1f0` 回调指针 `0x7ee3fa0868` 的第 `[2..3]` 字节 | `u16` 参数（`0xb7080: ldrh w3, [x19, #0x1f2]` 传给 `IntegRecordMovieInit`） |
| `+0x268..+0x26b` | `02000000` | u32 = `0x00000002` (`2`) | FX6 真实 `u32 count = 2`（由 FX6 `appFw.so` `0x212f74c..0x212f750` 写入） | 超出 FX3 `0x1f8`（504B）范围，FX3 不读取 |
| `+0x26c..+0x27b` | `00100000 10100000 00000000 00000000` | 4 × u32 = `[0x1000, 0x1010, 0x0, 0x0]` | FX6 真实 `u32[4]` 条目数组（由 FX6 `appFw.so` `0x212f794..0x212f7b0` 按 `count=2` 拷贝前两项） | 超出 FX3 `0x1f8` 范围，FX3 不读取 |
| `+0x28a..+0x28b` | `a005` | u16 = `0x05a0` (`1,440`) | FX6 传给 `IntegRecordMovieInit` 的 `u16` 参数（由 FX6 `appFw.so` `0x212f498..0x212f49c` 写入） | 超出 FX3 `0x1f8` 范围，FX3 不读取 |

---

## 2. Part B：FX3 `0x1f8` 与 FX6 `0x290` 逐字段布局比对

### 2.1 FX3 `mpr::Init` (`0x1f8` = 504B) 实际读取的全字段清单

以固定 FX3 [`libmpr.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so) 中 `mpr::Init` (`0xb6844..0xb70c8`) 的反汇编与 `.rela.dyn` 重定位表为唯一依据，FX3 对 `initInParam` (`x19`) 的全部读取如下（注：入口 `0xb6864: bl 0xb56ec` 另将 `[x19+0x0..+0x1f7]` 整块 `0x1f8` 字节 `memcpy` 到日志消息缓冲区）：

| FX3 偏移 | 宽度 | FX3 读取指令地址与汇编码 | FX3 内部可见用途 / 写入的全局符号（GOT 重定位） | 对应 FX6 `0x290` 同语义字段偏移 |
|---|---|---|---|---|
| `+0x000` | 8B | （未单独 `ldr`，仅 `0xb56ec` 整块拷贝） | 调用方 `memset` 置 `0`，`mpr::Init` 不使用 | `+0x000`（一致，均为 `0`） |
| `+0x008` | 8B | `0xb68e4: ldr x1, [x19, #0x8]` | 写入 `_ZN3mpr27gp_evtLoadStillFinishedFuncE` | `+0x008`（**对齐**，`AP+0x212954c`） |
| `+0x010` | 8B | `0xb690c: ldr x1, [x19, #0x10]` | 写入 `_ZN3mpr27gp_evtLoadMovieFinishedFuncE` | `+0x010`（**对齐**，`AP+0x213cf38`） |
| `+0x018` | 8B | `0xb691c: ldr x1, [x19, #0x18]` | 写入 `_ZN3mpr22gp_evtLoadFinishedFuncE` | `+0x018`（**对齐**，`AP+0x213ce24`） |
| `+0x020` | 8B | `0xb692c: ldr x1, [x19, #0x20]` | 写入 `_ZN3mpr24gp_evtUnloadFinishedFuncE` | `+0x020`（**对齐**，`AP+0x213cd74`） |
| `+0x028` | 8B | `0xb693c: ldr x1, [x19, #0x28]` | 写入 `_ZN3mpr31gp_evtMovieRecStatusChangedFuncE` | `+0x028`（**对齐**，`AP+0x214187c`） |
| `+0x030` | 8B | `0xb694c: ldr x1, [x19, #0x30]` | 写入 `_ZN3mpr31gp_evtStillRecStatusChangedFuncE` | `+0x030`（**对齐**，`AP+0x212952c`） |
| `+0x038` | 8B | `0xb695c: ldr x1, [x19, #0x38]` | 写入 `_ZN3mpr26gp_evtEnterRecFinishedFuncE` | `+0x038`（**对齐**，`AP+0x2139b24`） |
| `+0x040` | 8B | `0xb696c: ldr x1, [x19, #0x40]` | 写入 `_ZN3mpr25gp_evtExitRecFinishedFuncE` | `+0x040`（**对齐**，`AP+0x2139aa8`） |
| `+0x048` | 8B | `0xb697c: ldr x1, [x19, #0x48]` | 写入 `_ZN3mpr25gp_evtMovieRecStartedFuncE` | `+0x048`（**对齐**，`AP+0x213cca4`） |
| `+0x050` | 8B | `0xb698c: ldr x1, [x19, #0x50]` | 写入 `_ZN3mpr25gp_evtMovieRecStoppedFuncE` | `+0x050`（**对齐**，`AP+0x213cc0c`） |
| `+0x058` | 8B | `0xb699c: ldr x1, [x19, #0x58]` | 写入 `_ZN3mpr33gp_evtInternalMovieRecStoppedFuncE` | `+0x058`（**对齐**，`AP+0x2129658`） |
| `+0x060` | 8B | `0xb69ac: ldr x1, [x19, #0x60]` | 写入 `_ZN3mpr28gp_evtMovieWriteFinishedFuncE` | `+0x060`（**对齐**，`AP+0x213ca24`） |
| `+0x068` | 8B | `0xb69bc: ldr x1, [x19, #0x68]` | 写入 `_ZN3mpr31gp_evtAllMovieWriteFinishedFuncE` | `+0x068`（**对齐**，`AP+0x21294f8`） |
| `+0x070` | 8B | `0xb69cc: ldr x1, [x19, #0x70]` | 写入 `_ZN3mpr30gp_evtMovieRecMediaChangedFuncE` | `+0x070`（**对齐**，`AP+0x2129958`） |
| `+0x078` | 8B | `0xb69dc: ldr x1, [x19, #0x78]` | 写入 `_ZN3mpr29gp_evtMovieRecAutoDividedFuncE` | `+0x078`（**对齐**，`AP+0x212d9fc`） |
| `+0x080` | 8B | `0xb69ec: ldr x1, [x19, #0x80]` | 写入 `_ZN3mpr28gp_evtStillWriteFinishedFuncE` | `+0x080`（**对齐**，`AP+0x213c8d8`） |
| `+0x088` | 8B | `0xb69fc: ldr x1, [x19, #0x88]` | 写入 `_ZN3mpr29gp_evtStillWriteCountdownFuncE` | `+0x088`（**对齐**，`AP+0x213bce4`） |
| `+0x090` | 8B | `0xb6a0c: ldr x1, [x19, #0x90]` | 写入 `_ZN3mpr38gp_evtStillRecPriorityMediaChangedFuncE` | `+0x090`（**对齐**，`AP+0x21294bc`） |
| `+0x098` | 8B | `0xb6a1c: ldr x1, [x19, #0x98]` | 写入 `_ZN3mpr19gp_evtPbCamInfoFuncE` | `+0x098`（**对齐**，`AP+0x212a038`） |
| `+0x0a0` | 8B | `0xb6a2c: ldr x1, [x19, #0xa0]` | 写入 `_ZN3mpr19gp_evtPbGpsInfoFuncE` | `+0x0a0`（**对齐**，`AP+0x2128858`） |
| `+0x0a8` | 8B | `0xb6a3c: ldr x1, [x19, #0xa8]` | 写入 `_ZN3mpr26gp_evtPbChangedContentFuncE` | `+0x0a8`（**对齐**，`AP+0x212f278`） |
| `+0x0b0` | 8B | `0xb6a4c: ldr x1, [x19, #0xb0]` | 写入 `_ZN3mpr25gp_evtPbStartFinishedFuncE` | `+0x0b0`（**对齐**，`AP+0x213c854`） |
| `+0x0b8` | 8B | `0xb6a5c: ldr x1, [x19, #0xb8]` | 写入 `_ZN3mpr24gp_evtPbStopFinishedFuncE` | `+0x0b8`（**对齐**，`AP+0x213c7ac`） |
| `+0x0c0` | 8B | `0xb6a6c: ldr x1, [x19, #0xc0]` | 写入 `_ZN3mpr32gp_evtReadStillImageFinishedFuncE` | `+0x0c0`（**对齐**，`AP+0x213c408`） |
| `+0x0c8` | 8B | `0xb6a7c: ldr x1, [x19, #0xc8]` | 写入 `_ZN3mpr25gp_evtPbPauseFinishedFuncE` | `+0x0c8`（**对齐**，`AP+0x212885c`） |
| `+0x0d0` | 8B | `0xb6a8c: ldr x1, [x19, #0xd0]` | 写入 `_ZN3mpr32gp_evtPbPauseReleaseFinishedFuncE` | `+0x0d0`（**对齐**，`AP+0x2128860`） |
| `+0x0d8` | 8B | `0xb6a9c: ldr x1, [x19, #0xd8]` | 写入 `_ZN3mpr25gp_evtInternalPbPauseFuncE` | `+0x0d8`（**对齐**，`AP+0x212949c`） |
| `+0x0e0` | 8B | `0xb6aac: ldr x1, [x19, #0xe0]` | 写入 `_ZN3mpr24gp_evtInternalPbStopFuncE` | `+0x0e0`（**对齐**，`AP+0x2129468`） |
| `+0x0e8` | 8B | `0xb6abc: ldr x1, [x19, #0xe8]` | 写入 `_ZN3mpr25gp_evtAudioRecStartedFuncE` | `+0x0e8`（**对齐**，FX6 置 `0`） |
| `+0x0f0` | 8B | `0xb6acc: ldr x1, [x19, #0xf0]` | 写入 `_ZN3mpr25gp_evtAudioRecStoppedFuncE` | `+0x0f0`（**对齐**，FX6 置 `0`） |
| `+0x0f8` | 8B | `0xb6adc: ldr x1, [x19, #0xf8]` | 写入 `_ZN3mpr33gp_evtInternalAudioRecStoppedFuncE` | `+0x0f8`（**对齐**，FX6 置 `0`） |
| `+0x100` | 8B | `0xb6aec: ldr x1, [x19, #0x100]` | 写入 `_ZN3mpr28gp_evtAudioWriteFinishedFuncE` | `+0x100`（**对齐**，`AP+0x2128864`） |
| `+0x108` | 8B | `0xb6afc: ldr x1, [x19, #0x108]` | 写入 `_ZN3mpr30gp_evtAudioPbStartFinishedFuncE` | `+0x108`（**对齐**，FX6 置 `0`） |
| `+0x110` | 8B | `0xb6b0c: ldr x1, [x19, #0x110]` | 写入 `_ZN3mpr32gp_evtInternalAudioPbStoppedFuncE` | `+0x110`（**对齐**，FX6 置 `0`） |
| `+0x118` | 8B | `0xb6b1c: ldr x1, [x19, #0x118]` | 写入 `_ZN3mpr29gp_evtAudioPbStopFinishedFuncE` | `+0x118`（**对齐**，FX6 置 `0`） |
| `+0x120` | 8B | `0xb6b2c: ldr x1, [x19, #0x120]` | 写入 `_ZN3mpr30gp_evtAudioPbPauseFinishedFuncE` | `+0x120`（**对齐**，FX6 置 `0`） |
| `+0x128` | 8B | `0xb6b3c: ldr x1, [x19, #0x128]` | 写入 `_ZN3mpr37gp_evtAudioPbPauseReleaseFinishedFuncE` | `+0x128`（**对齐**，FX6 置 `0`） |
| `+0x130` | 8B | `0xb6b4c: ldr x1, [x19, #0x130]` | 写入 `_ZN3mpr19gp_evtRecPbTimeFuncE` | **冲突**：FX6 同符号在 `+0x168` (`AP+0x212b720`)；FX6 `+0x130` 为 `gp_evtAudioEncStartedFunc` (`0`) |
| `+0x138` | 8B | `0xb6b7c: ldr x1, [x19, #0x138]` | 写入 `_ZN3mpr22gp_evtEditProgressFuncE` | **冲突**：FX6 同符号在 `+0x170` (`AP+0x2129824`)；FX6 `+0x138` 为 `gp_evtAudioEncStoppedFunc` (`0`) |
| `+0x140` | 8B | `0xb6b8c: ldr x1, [x19, #0x140]` | 写入 `_ZN3mpr22gp_evtEditFinishedFuncE` | **冲突**：FX6 同符号在 `+0x178` (`AP+0x213c17c`)；FX6 `+0x140` 为 `gp_evtAudioDecStartedFunc` (`0`) |
| `+0x148` | 8B | `0xb6b5c: ldr x1, [x19, #0x148]` | 写入 `_ZN3mpr26gp_evtPowerOffFinishedFuncE` | **冲突**：FX6 同符号在 `+0x180` (`AP+0x213c0f0`)；FX6 `+0x148` 为 `gp_evtAudioDecStoppedFunc` (`0`) |
| `+0x150` | 8B | `0xb6b6c: ldr x1, [x19, #0x150]` | 写入 `_ZN3mpr25gp_evtPowerOnFinishedFuncE` | **冲突**：FX6 同符号在 `+0x188` (`AP+0x213c064`)；FX6 `+0x150` 为 `gp_evtInternalAudioEncStoppedFunc` (`0`) |
| `+0x158` | 8B | `0xb6b9c: ldr x1, [x19, #0x158]` | 写入 `_ZN3mpr31gp_evtGetRepairTimeFinishedFuncE` | **冲突**：FX6 同符号在 `+0x190` (`AP+0x213bfc0`)；FX6 `+0x158` 为 `gp_evtInternalAudioDecStoppedFunc` (`0`) |
| `+0x160` | 8B | `0xb6bac: ldr x1, [x19, #0x160]` | 写入 `_ZN3mpr24gp_evtRepairProgressFuncE` | **冲突**：FX6 同符号在 `+0x198` (`AP+0x212942c`)；FX6 `+0x160` 为 `gp_evtAudioReadFinishedFunc` (`0`) |
| `+0x168` | 8B | `0xb6bbc: ldr x1, [x19, #0x168]` | 写入 `_ZN3mpr24gp_evtRepairFinishedFuncE` | **冲突**：FX6 同符号在 `+0x1a0` (`AP+0x213bee8`)；FX6 `+0x168` 存的是 `gp_evtRecPbTimeFunc` |
| `+0x170` | 8B | `0xb6bcc: ldr x1, [x19, #0x170]` | 写入 `_ZN3mpr25gp_evtRecoveryStartedFuncE` | **冲突**：FX6 同符号在 `+0x1a8` (`AP+0x21293f8`)；FX6 `+0x170` 存的是 `gp_evtEditProgressFunc` |
| `+0x178` | 8B | `0xb6bdc: ldr x1, [x19, #0x178]` | 写入 `_ZN3mpr26gp_evtRecoveryFinishedFuncE` | **冲突**：FX6 同符号在 `+0x1b0` (`AP+0x21293bc`)；FX6 `+0x178` 存的是 `gp_evtEditFinishedFunc` |
| `+0x180` | 8B | `0xb6bec: ldr x1, [x19, #0x180]` | 写入 `_ZN3mpr28gp_evtResetNecessityInfoFuncE` | **冲突**：FX6 同符号在 `+0x1b8` (`AP+0x2129380`)；FX6 `+0x180` 存的是 `gp_evtPowerOffFinishedFunc` |
| `+0x188` | 8B | `0xb6bfc: ldr x1, [x19, #0x188]` | 写入 `_ZN3mpr32gp_evtStillTransferDataBuiltFuncE` | **冲突**：FX6 同符号在 `+0x1c0` (`AP+0x2139368`)；FX6 `+0x188` 存的是 `gp_evtPowerOnFinishedFunc` |
| `+0x190` | 8B | `0xb6c0c: ldr x1, [x19, #0x190]` | 写入 `_ZN3mpr37gp_evtSetEssenceMarkInRecFinishedFuncE` | **冲突**：FX6 同符号在 `+0x1c8` (`AP+0x213be64`)；FX6 `+0x190` 存的是 `gp_evtGetRepairTimeFinishedFunc` |
| `+0x198` | 8B | `0xb6c1c: ldr x1, [x19, #0x198]` | 写入 `_ZN3mpr38gp_evtSetEssenceMarkInPlayFinishedFuncE` | **冲突**：FX6 同符号在 **`+0x1d0`** (`AP+0x213bde0`)；FX6 `+0x198` 存的是 `gp_evtRepairProgressFunc` |
| `+0x1a0` | 8B | `0xb6c2c: ldr x1, [x19, #0x1a0]` | 写入 `_ZN3mpr30gp_evtMovieRecReelNoUpdateFuncE` | **冲突**：FX6 同符号在 `+0x238` (`0`)；FX6 `+0x1a0` 存的是 `gp_evtRepairFinishedFunc` |
| `+0x1a8` | 8B | `0xb6c6c: ldr x1, [x19, #0x1a8]` | 写入 `_ZN3mpr36gp_evtSetClipStatusInRecFinishedFuncE` | **冲突**：FX6 同符号在 `+0x228` (`AP+0x213ba30`)；FX6 `+0x1a8` 存的是 `gp_evtRecoveryStartedFunc` |
| `+0x1b0` | 8B | `0xb6c8c: ldr x1, [x19, #0x1b0]` | 写入 `_ZN3mpr37gp_evtSetClipStatusInPlayFinishedFuncE` | **冲突**：FX6 同符号在 `+0x230` (`AP+0x213bab4`)；FX6 `+0x1b0` 存的是 `gp_evtRecoveryFinishedFunc` |
| `+0x1b8` | 8B | `0xb6c3c: ldr x1, [x19, #0x1b8]` | 写入 `_ZN3mpr32gp_evtMovieRecFileNameUpdateFuncE` | **冲突**：FX6 同符号在 `+0x240` (`AP+0x2129360`)；FX6 `+0x1b8` 存的是 `gp_evtResetNecessityInfoFunc` |
| `+0x1c0` | 8B | `0xb6c4c: ldr x1, [x19, #0x1c0]` | 写入 `_ZN3mpr39gp_evtCheckDigitalSignatureFinishedFuncE` | **冲突**：FX6 同符号在 `+0x248` (`0`)；FX6 `+0x1c0` 存的是 `gp_evtStillTransferDataBuiltFunc` |
| `+0x1c8` | 8B | `0xb6c5c: ldr x1, [x19, #0x1c8]` | 写入 `_ZN3mpr49gp_evtGetDigitalSignatureInfoForMovieFinishedFuncE` | **冲突**：FX6 同符号在 `+0x250` (`0`)；FX6 `+0x1c8` 存的是 `gp_evtSetEssenceMarkInRecFinishedFunc` |
| `+0x1d0` | 4B (`u32`) | `0xb6870: ldr w0, [x19, #0x1d0]`<br>`0xb6ccc: ldr w0, [x19, #0x1d0]`<br>`0xb7048: ldr w0, [x19, #0x1d0]`<br>`0xb708c: ldr w0, [x19, #0x1d0]` | `count`（上限 `<= 4`）：控制 `msidconv::Set` 循环次数、传入 `0x137c1c` 栈结构首字、以及作为第 1 参数传给 `IntegRecordMovieInit(count, tbl, ...)` | **冲突**：FX6 同语义 `count` 在 **`+0x268`**（值 `2`）；FX6 `+0x1d0` 是回调指针 `0x7ee3fb3de0` 低 32 位 |
| `+0x1d4..+0x1e3` | 16B (`4 × u32`) | `0xb68ec: add x23, x19, #0x1d4`<br>`0xb6d10: ldr w1, [x23], #0x4`<br>`0xb705c: ldp x0, x1, [x22]`<br>`0xb7070: mov x0, x22` (`IntegStatusInit`)<br>`0xb7084: mov x1, x22` (`IntegRecordMovieInit`) | 最多 4 个槽位/媒体 ID 条目：<br>1) 前 `count` 项传给 `g_msidconv->Set(entry, 0, "", "")`，余项填 `0xffff`；<br>2) 整块 16B 拷入 `[x29, #0x7c..#0x8b]` 传给 `0x137c1c`；<br>3) 指针传给 `IntegStatusInit(const uint*)` → `InitStillStatus` / `InitMovieStatus`（**注意：这两个函数不读 `count`，直接遍历全部 4 个 `u32` 并与 `0xffff` 比较**）；<br>4) 指针传给 `IntegRecordMovieInit` | **冲突**：FX6 同语义 `4 × u32` 条目区在 **`+0x26c..+0x27b`**（值 `[0x1000, 0x1010, 0, 0]`）；FX6 `+0x1d4..+0x1e3` 是 `+0x1d0` 指针高半字、`+0x1d8` 空槽、`+0x1e0` 指针低半字 |
| `+0x1e4` | 4B (`u32`) | `0xb6e68: ldr w1, [x19, #0x1e4]`<br>`0xb7054: ldr w0, [x19, #0x1e4]`<br>`0xb7088: ldr w2, [x19, #0x1e4]` | 1) 存入 `0xfc` 分配对象的 `+0x0`；<br>2) 经 `[x29, #0x90]` 传给 `0x137c1c` 写入 `*GOT[0x2fa890]`；<br>3) 作为第 3 参数传给 `IntegRecordMovieInit`，在 `0xd634c..0xd6354` 中与 `tbl[i]` 比较（跳过等于 `0xffff` 或等于该值的条目） | **冲突**：FX6 同语义字段在 **`+0x27c`**（值 `0x0000ffff`）；FX6 `+0x1e4` 是 `+0x1e0` 回调指针高半字 `0x0000007e` |
| `+0x1e8` | 4B (`u32`) | `0xb6e6c: ldr w0, [x19, #0x1e8]`<br>`0xb6fac: ldr w1, [x19, #0x1e8]` | `mpr::UmidMatNoGenMethod`：存入 `0xfc` 对象 `+0x4`，并作为第 2 参数传给 `mpr::UMID::UMID(UmidMatNoGenMethod, const uint8_t*)` | **冲突**：FX6 同语义字段在 **`+0x280`**（值 `1`）；FX6 `+0x1e8` 是回调指针 `0x7ee3fb3c3c` 低半字 `0xe3fb3c3c` |
| `+0x1ec..+0x1f1` | 6B (`uint8_t[6]`) | `0xb6f94: add x20, x19, #0x1ec`<br>`0xb6fb0: mov x2, x20` (`UMID::UMID`)<br>`0xb6fd0: mov x2, x20` (`UniversalGroupId`) | 6 字节 DeviceNodeID（`UMID` 与 `UniversalGroupId` 构造函数内调用 `SetDeviceNodeID(x2, 6)`） | **冲突**：FX6 同语义 6B 字段在 **`+0x284..+0x289`**（值 `ffffffffffff`）；FX6 `+0x1ec..+0x1f1` 是指针字节 `7e0000006808` |
| `+0x1f2` | 2B (`u16`) | `0xb7080: ldrh w3, [x19, #0x1f2]` | 作为第 4 参数 (`uint16_t`) 传给 `IntegRecordMovieInit(uint, const uint*, uint, ushort)`，FX3 在其内立即用该值初始化 `XavcsMovieWriter`（FX3 `appFw.so` `0x2e58ee4` 固定写 `0x030c = 780`） | **冲突 + 值差异**：FX6 同位置字段在 **`+0x28a`**，但 FX6 `appFw.so` `0x212f498` 写入 `0x05a0 = 1440`；而 FX6 `+0x1f2` 是指针字节 `0xe3fa = 58,362` |
| `+0x1f4..+0x1f7` | 4B (`u32`) | （FX3 `mpr::Init` 未读取；仅 `0xb56ec` 整块拷贝） | FX3 `appFw.so` 在 `0x2e58ec4` 写入 `w1`（由输入结构 `+0x20` 转换：`0 -> 0`、`1 -> 1`、其他非零 -> `0xff`），但 FX3 `mpr::Init` 从未读取 | FX6 `appFw.so` 在 `0x212f774` 以完全相同逻辑写入 **`+0x28c`**（本轮值为 `0`），FX6 `mpr::Init` 同样未读取 |

### 2.2 FX6 `0x290` 记录中无法映射到 FX3 `0x1f8` 的新增槽位

对照 FX6 [`libmpr.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so) 的 `mpr::Init` (`0x12b3dc..0x12bd80`) 与 [`mpr-observation.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/runs/mpr-ro-b22ccc48/mpr-observation.json)，FX6 `0x290` 比 FX3 `0x1f8` 多出的 `0x98` 字节（19 个 8B 槽位）分类如下：

1. **FX6 新增但本轮为 `NULL (0x0)` 的 9 个槽位**：
   - `+0x130` (`gp_evtAudioEncStartedFunc`)、`+0x138` (`gp_evtAudioEncStoppedFunc`)、`+0x140` (`gp_evtAudioDecStartedFunc`)、`+0x148` (`gp_evtAudioDecStoppedFunc`)、`+0x150` (`gp_evtInternalAudioEncStoppedFunc`)、`+0x158` (`gp_evtInternalAudioDecStoppedFunc`)、`+0x160` (`gp_evtAudioReadFinishedFunc`)：共 7 个音频回调槽，FX6 `appFw.so` 未赋值（保持 `memset` 的 `0`）。
   - `+0x1d8`：FX6 `appFw.so` 与 FX6 `mpr::Init` 均未读写（保持 `0`）。
   - `+0x218` (`gp_evtResumeSetFinishedFunc`)：FX6 `appFw.so` 未赋值（保持 `0`）。
2. **FX6 新增且本轮为非空（Non-NULL）函数指针、但 FX3 `libmpr.so` 无对应全局符号的 10 个槽位**：
   - `+0x1e0`: `0x7ee3fb3b38` (`AP+0x213bb38`) → `_ZN3mpr31gp_evtGetResumeInfoFinishedFuncE`
   - `+0x1e8`: `0x7ee3fb3c3c` (`AP+0x213bc3c`) → `_ZN3mpr36gp_evtGetMovieDetailInfoFinishedFuncE`
   - `+0x1f0`: `0x7ee3fa0868` (`AP+0x2128868`) → `_ZN3mpr27gp_evtNextThumbFinishedFuncE`
   - `+0x1f8`: `0x7ee3fa38bc` (`AP+0x212b8bc`) → `_ZN3mpr21gp_evtRecClipNameFuncE`
   - `+0x200`: `0x7ee3fa3854` (`AP+0x212b854`) → `_ZN3mpr22gp_evtNextClipNameFuncE`
   - `+0x208`: `0x7ee3fa66e4` (`AP+0x212e6e4`) → `_ZN3mpr27gp_evtPbMovieDetailInfoFuncE`
   - `+0x210`: `0x7ee3fa15d0` (`AP+0x21295d0`) → `_ZN3mpr31gp_evtRecordedClipTooShortParamE`
   - `+0x220`: `0x7ee3fa1590` (`AP+0x2129590`) → `_ZN3mpr30gp_evtMovieContentsChangedFuncE`
   - `+0x258`: `0x7ee3fb38f4` (`AP+0x213b8f4`) → `_ZN3mpr25gp_evtMovieRecResumedFuncE`
   - `+0x260`: `0x7ee3fb3998` (`AP+0x213b998`) → `_ZN3mpr24gp_evtMovieRecPausedFuncE`

---

## 3. 最小适配可行性评估与停止判据

任务要求评估如下最小适配方案的静态可行性：
> “把 `count=2` 放到 `+0x1d0`、条目区由 FX6 数据转换，其他字段原样或显式零填充。若条目语义不匹配或字段用途不明，明确停止，不猜测填充。”

### 3.1 为什么“其他字段原样或显式零填充”在静态上直接不成立

1. **`+0x130..+0x1c8`（20 个回调指针槽）既不能原样保留，也不能零填充**：
   - 若**原样保留 FX6 `+0x130..+0x1c8`**：
     - FX3 `+0x130..+0x160` 的 7 个全局回调指针（包括 `_ZN3mpr26gp_evtPowerOffFinishedFuncE` 与 `_ZN3mpr25gp_evtPowerOnFinishedFuncE`）会被写成 `0x0`；
     - FX3 `+0x168..+0x1c8` 的 13 个全局回调指针会被错位绑定到 FX6 的其他事件回调（例如 FX3 `_ZN3mpr32gp_evtStillTransferDataBuiltFuncE` 收到 FX6 的 `gp_evtPowerOnFinishedFunc` `0x7ee3fb4064`），事件触发时将调用错误的 AP 回调函数。
   - 若**显式零填充 `+0x130..+0x1c8`**：
     - FX3 `+0x130..+0x1c8` 的 20 个回调（含 PowerOn/PowerOff 完成通知等核心回调）全部丢失为 `NULL`。
2. **`+0x1e4..+0x1f3`（尾部标量与节点 ID 区）既不能原样保留，也不能零填充**：
   - 若**原样保留 FX6 `+0x1e4..+0x1f3`**：
     - `+0x1e4` 读到 `0x7e`（而非 FX6 `+0x27c` 的 `0xffff`）；
     - `+0x1e8` (`UmidMatNoGenMethod`) 读到 `0xe3fb3c3c`（而非 FX6 `+0x280` 的 `1`）；
     - `+0x1ec..+0x1f1` (6B DeviceNodeID) 读到 `7e0000006808`（而非 FX6 `+0x284..+0x289` 的 `ffffffffffff`）；
     - `+0x1f2` (`u16`) 读到 `0xe3fa = 58,362`（传入 `IntegRecordMovieInit` 初始化 `XavcsMovieWriter`）。
   - 若**显式零填充 `+0x1e4..+0x1f3`**：
     - `+0x1e4` 变为 `0`（破坏 `0xffff` 哨兵值）、`+0x1e8` 变为 `0`、`+0x1ec..+0x1f1` 变为 `000000000000`、`+0x1f2` 变为 `0`。

### 3.2 即便扩展为“按符号/结构重排”，仍存在的静态未知与冲突项（触发停止条件）

即便超越“其他字段原样或零填充”，把 FX6 的 `+0x168..+0x1d0` 移回 `+0x130..+0x198`、把 `+0x228..+0x250` 按符号重排移回 `+0x1a0..+0x1c8`、把 `+0x268..+0x28f` 移回 `+0x1d0..+0x1f7`，静态分析仍暴露以下未解冲突与 `unknown` 项：

1. **`+0x1d4..+0x1e3` 条目区后两项 (`+0x1dc`, `+0x1e0`) 的 `0x0` vs `0xffff` 语义问题**：
   - 在 FX3 `mpr::Init` 内部：
     - `0xb6ccc..0xb6d2c` 循环和 `0x137c1c` 会根据 `count` (`+0x1d0`) 仅读取前 `count=2` 项（`0x1000`, `0x1010`），并将第 3、4 项显式按 `0xffff` 传给 `msidconv::Set`；
     - **但 `0xb7074: bl _ZN3mpr15IntegStatusInitEPKj` 只接收 `x22 = x19 + 0x1d4` 指针而不接收 `count`**，其子函数 `InitStillStatus` (`0xf42bc..0xf431c`) 与 `InitMovieStatus` (`0xf4358..0xf4394`) 均固定循环 4 次（偏移 `0, 4, 8, 12`），仅当条目值等于 `0xffff` 时才将该槽位标记为未启用（`InitMovieStatus` 置 `[slot]=0, [slot+4]=0xffff`），否则将其视为有效 ID 并置 `[slot]=1`！
     - 虽然 FX3 与 FX6 的 `appFw.so` 都在栈上先 `memset(..., 0, size)` 再按 `count` 拷贝前 `count` 项（导致未拷贝项在栈上为 `0`），但 FX3 输入源在真實机器上的 `count` 值与条目内容，以及 FX6 的 `[0x1000, 0x1010, 0, 0]` 传给固定 FX3 `libmpr.so` 后后续模块对 `0x1000`/`0x1010` 媒体类型编码的解释是否完全一致，静态上无法单独由 `mpr::Init` 证明（部分依赖外部 `Backup` / 槽位状态，标为 `unknown`）。
2. **`+0x1f2` (`u16`) 的 `780` (`0x030c`) vs `1440` (`0x05a0`) 冲突**：
   - FX3 `appFw.so` (`0x2e58ee4`) 硬编码写入 `0x030c` (`780`)，FX3 `IntegRecordMovieInit` (`0xd60a8..0xd613c`) 在初始化阶段立即分配两个 `0x2c58` 字节对象并调用 `0x11975c` (`XavcsMovieWriter`) 将该 `u16` 存入 `[writer+0x24]` 及消息包；
   - FX6 `appFw.so` (`0x212f498`) 硬编码写入 `0x05a0` (`1440`)，而 FX6 `IntegRecordMovieInit` (`0x155de4`) 并不在此时构造 `XavcsMovieWriter`，仅将 `1440` 存入 `[MovieRecInfo+0x1454]`。
   - 既有 [`mpr-init-candidate/README.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/README.md) 已明确指出：“当前 FX6 Xavcs initializer 的 780/Mxf 保留 1440 是静态路径，实际模式与本次值未知，不能全局改 780。”因此 `+0x1f2` 究竟应填 `1440` 还是 `780` 属于不能猜测填充的关键字段。
3. **FX6 新增的 10 个非空回调在 FX3 `libmpr.so` 中无挂载点**：
   - 如 2.2 节所列，FX6 `0x290` 中有 10 个非空回调（`gp_evtGetResumeInfoFinishedFunc`、`gp_evtRecClipNameFunc`、`gp_evtMovieRecResumedFunc` 等）在 FX3 `libmpr.so` 中不存在，丢弃后 FX6 `appFw.so` 状态机是否会因缺少对应回调而挂起属 `unknown`。
4. **同名回调函数的调用签名/参数结构兼容性未知（`unknown`）**：
   - 57 个可通过符号名对应的 `gp_evt*Func` 回调仅证明了 `libmpr.so` 全局函数指针变量名相同，尚未逐一核对 FX3 `libmpr.so` 触发各回调时的参数布局与 FX6 `appFw.so` 接收端的读取布局是否一致。

**结论**：依据任务规则“若条目语义不匹配或字段用途不明，明确停止，不猜测填充”，当前**停止构造可运行最小适配候选，不申请 VM 窗口**。

---

## 4. 未证明项（`unknown`）

1. FX3 `IntegRecordMovieInit` -> `0x11975c` (`XavcsMovieWriter`) 在收到 `+0x1f2 = 1440 (0x05a0)` 时是否会报错或越界，以及 FX6 AP 在固定 FX3 `libmpr.so` 下使用 `780 (0x030c)` 是否与 FX6 期望的录制/封装模式冲突（`unknown`）。
2. FX6 传入的 `[0x1000, 0x1010]` 在固定 FX3 `libmpr.so` 的下游模块（`capidtbl::Init`、`IntegRecordStillInit`、`IntegRecordMovieInit`、`VpgManager::Init`）中是否与 FX3 平台硬件槽位定义及 `Backup` 数据完全兼容（`unknown`）。
3. FX6 `0x290` 中 10 个 FX3 不存在的非空事件回调被丢弃后，FX6 `appFw.so` 在初始化完成后的后续阶段是否依赖这些回调返回（`unknown`）。
4. FX3 `mpr::Init` 正常路径中访问的外部状态（如 `osal_dynamic_id`、`0xb5628`、硬编码物理地址 `0x424000000` 的 `dmac::memcpy2`、`Backup_read_8Byte(0xfa0028 / 0xfa005d)`、`capidtbl::Init`）在混合移植环境下的执行结果（本轮因在 `0xb6878` 提前返回 `3`，上述调用均未执行，`unknown`）。

---

## 5. 下一步最小验证建议（仅静态 host-only，不跑 VM）

1. **静态核对 `+0x1f2` (`780` vs `1440`) 的下游消费者**：
   - 在固定 FX3 `libmpr.so` 中静态追踪 `0x11975c` 及 `0x115a2c` 对 `[x1, #0x18]` / `[x19, #0x24]`（即 `+0x1f2` `u16`）的全部读取与分支判断，确认它是缓冲区大小、表项上限还是模式枚举，对比 FX6 `libmpr.so` 中 `[MovieRecInfo + 0x1454]` 的消费者。
2. **静态核对关键回调签名（优先 `gp_evtPowerOnFinishedFunc`）**：
   - 在固定 FX3 `libmpr.so` 中定位读取 `_ZN3mpr25gp_evtPowerOnFinishedFuncE`（GOT `0x2f9ce0`）并发起间接调用的指令点，比对 FX3 `appFw.so` (`0x2e6d1dc`) 与 FX6 `appFw.so` (`0x213c064`) 两个回调函数体的参数读取宽度与偏移是否一致。
3. **静态追踪 FX3 `appFw.so` 的 `0x2e58b98` 输入源**：
   - 在固定 FX3 `appFw.so` 中向上追踪 `0x2e58b98` 的调用点（`x0` 输入结构），确认 FX3 原生传入 `+0x1d0` (`count`)、`+0x1d4`（条目表）、`+0x1e4`、`+0x1e8` 的静态构造值，与 FX6 `0x212f470` 的输入源做精确对照。

---

## 6. 复核命令记录

```sh
# 1. 核对固定 FX3 libmpr.so 与供体 FX6 appFw.so 的 SHA256
shasum -a 256 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so

# 2. 复核 FX3 mpr::Init 符号边界与完整反汇编 (0xb6844 .. 0xb70c8)
objdump -T /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so | grep "_ZN3mpr4Init"
objdump -d --start-address=0xb6844 --stop-address=0xb70c8 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so

# 3. 复核 FX6 appFw.so 构造 0x290 记录并调用 mpr::Init 的完整函数 (0x212f470 .. 0x212f7c8)
objdump -d --start-address=0x212f470 --stop-address=0x212f7cc \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so

# 4. 对照 FX6 libmpr.so 的 mpr::Init (0x12b3dc .. 0x12bd80) 与 FX3 appFw.so 调用方 (0x2e58b98 .. 0x2e58f68)
objdump -d --start-address=0x12b3dc --stop-address=0x12bd80 \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so
objdump -d --start-address=0x2e58b98 --stop-address=0x2e58f6c \
  /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so
```
