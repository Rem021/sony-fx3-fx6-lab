# FX3 RM 服务、FRONT 首包与诚实空槽合同

**`0x80d9016e` 是 AP Linux 内核 `mcmn_drv.ko` 注册的 RM 请求服务，不是 CP 服务。原 CP 经 `0x8028017c` 发布独立的 7B FRONT 状态，AP 内核缓存并向 MediaDetect 回放。两条链已定位；配置与首包必须同时提供，才能让原 `StartInOut` 进入 state2、只通知 status0。** 这是原字节与 AP92 封存日志的静态审计，未实现后端、未启动 QEMU，未验收 NO CARD 画面或 MENU 交互。

## 复现、边界与证据索引

交付为 [audit_rm_media.py](audit_rm_media.py)、[rm-media-proof.json](rm-media-proof.json) 和本 README。脚本核对卷 UUID、固定原件 SHA，重读原 ELF/Thumb 指令、内核重定位、原 Backup 配置与 AP92 串口；仅生成同目录 proof，`--check` 在内存重建后逐字节比较，不改任何输入。

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python \
  work/fx3-vm-20261101/lead-claude/audits/rm-media-service/audit_rm_media.py
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python \
  work/fx3-vm-20261101/lead-claude/audits/rm-media-service/audit_rm_media.py --check
```

退出0表示证据重建一致。端口配置和分支结果是 **B 级指令推导**，没有把 Python 投影称为执行原固件。写入范围仅本目录；未改 runtime、STATE.json、公共计划、原件、Git，未取得运行锁。

本次重建及`--check`均退出0，37个代码块、42条关键指令断言通过；112B配置与136B/28B回复长度核对通过。proof SHA256为`79eb7a80cfa7d57027bf4d934c1d5a76430320d5bb21f7af0ccf7e8a31da3bc7`，没有运行或UI验收。

| 简称 | 原件与寻址方式 | SHA256 前缀 |
|---|---|---|
| D | `original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaDetect.so`；ELF VA | `4c1dbb303cf9` |
| M / C | 同目录 `libInfraMediaMount.so` / `libInfraMediaCommon.so`；ELF VA | `33b4c61c39f7` / `1ddec7e4d903` |
| A | 同目录 `appFw.so`；ELF VA | `545c5053a74e` |
| K | `work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha15/kmod/mcmn_drv.ko`；**ET_REL 的 section+offset** | `da4596fe04a1` |
| P | `work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin`；Thumb VA，文件偏移=VA−`0x108000` | `c90d00d80787` |
| L92 | `menu-repair-01/runtime/runs/ap92media-9e1c3a07/serial.log`；**按 LF 分行、1起算** | `0fb5e9749828` |
| B / R92 | 原 `FX3-CX95900_ALLLANG-Backup.bin` / AP92 `backup-reserved-ram.bin` | `bf3a9d851f98` / `249e2d085c33` |

完整路径和 SHA 在 proof.sources。**A-static** 为原指令/重定位/原表直接证据，**A-runtime** 为既有日志直接观测，**B** 为明确条件下的推导，**U** 为未证实。K 的地址不能当作加载后绝对 VA；其他 DSO 地址也需要该次实际基址。

## 1. 原服务归属与24B请求/回复

**A-static：服务由 AP 内核模块注册，服务线程名为 `RMCMND-UIPC`。** K `.init.text+0x30/0x3c/0x40` 依次经重定位调用 `mcmnd_rmcfg_init`、`mcmnd_core_init`、`mcmnd_uipc_init`。后者 `.text+0x1e68..0x1ed4` 建立动态工作队列/线程，`0x1ebc/0x1ec4` 合成 `0x80d9016e`，`0x1ec8` 的重定位为 `osal_reg_msg_queue_cb`；literal `0x1ef0 → .text+0x1a38` 是回调，`0x1ee0 → .text+0x1ac8` 是服务线程。回调把收到的消息转交动态队列，线程处理命令并回 caller queue。因此无需寻找一个独立 AP 用户进程来注册此队列，也不能把它作为缺失 CP 的 VDF 类服务处理。见 proof.blocks.kernel_init / kernel_uipc_init / kernel_uipc_callback / kernel_uipc_thread。

**A-runtime：AP92 的两次 header 如下，服务缺席使 helper 在发送前返回 `0x80000004`。** L92 **5778 / 5805 / 5807 / 5817** 为 command9；**6640 / 6684 / 6685 / 6687** 为 command3。D `0xf1e4..0xf334` 先 `osal_stat_msgq(0x80d9016e)`，queue状态中的 `+4` 为0时经 `0xf32c` 返回该码；这不是“无卡”的成功回复，也未发生正常 request/reply 往返。

```text
cmd9 header24: 09000000 0100 7000 5f61af80 00000000 0000000000000000
cmd3 header24: 03000000 0100 0400 5f61af80 00000000 0000000000000000
cmd3 payload4: 8061af80     # AP92 实际通知目的队列0x80af6180
```

| Header 偏移 | 字节数 | 请求/回复语义 | 依据 |
|---:|---:|---|---|
| +0 | 4 | command；reply保留原值 | D `0xfd78/0xfe0c`；K `0x1b2c..0x1b50` |
| +4 | 2 | caller写1；server保留 | D `0xfd80..0xfd84/0xfe38`；K `0x1c98..0x1ca8` |
| +6 | 2 | **payload**长度，cmd9=`0x70`、cmd3=4 | D `0xfd88..0xfd8c/0xfe3c..0xfe44` |
| +8 | 4 | 动态回复队列，本次为`0x80af615f` | D `0xfd90..0xfd9c/0xfe14..0xfe28` |
| +12 | 4 | 原生处理结果；配置查询/注册成功为0 | D `0xf2fc`；K `0x1cc4/0x1cd8` |
| +16 | 8 | caller清零、server复制保留；正式字段名 **U** | D `0xfd68..0xfd74/0xfe40`；K `0x1c98..0x1ca8` |

这是**24B头+payload**：cmd9总长136B，cmd3总长28B，不能只发送24B。D `0xf218..0xf274` 按头+6分配并复制；发送成功后 `0xf294..0xf2a8` 在头+8指定队列以 `timeout=-1` 等待。回复要求分配大小至少24B、回复payload不超过请求长度（`0xf2b0..0xf2d0`），复制头/负载后读取+12并释放回复（`0xf2d4..0xf308`）。helper此处未验证command/version对应关系，软件端仍须严格绑定当前请求，不能利用这个宽松点混配回复。

**A-static：原服务成功回复沿用原command/头与同长度payload，状态写0；没有“无卡错误”的特殊头。** K `.rodata+0x40` 的13项命令表把cmd9绑到 `.text+0x1918`、最小总长136B，把cmd3绑到 `0x19e0`、最小总长28B。`0x1918..0x1978` 固定调用 `mcmnd_rmcfg_getinfoptr(1)`，复制112B并返回0；`0x19e0..0x19f4` 用payload第一个u32调用 `mcmnd_core_setosalidformedianotify`。服务线程 `0x1c94..0x1cfc` 复制请求、释放原请求、调用handler、写+12、另分配reply并发往头+8。**卡是否在场不改变配置查询的成功结果；在场字段属于第3节的FRONT包。**

**A-static/B：最小provider只闭合cmd9与cmd3的成功语义，不能把整个RM服务桩成全成功。** proof.kernel_commands保留全部13项命令/handler/最小长度。原server对未知command经 K `0x1b60..0x1be0` 返回`0x80000003`、24B头、payload长度0；软件遇到未实现的电源/PCI/检查介质命令应如实拒绝并记录，待运行中按原代码补齐，不能推测这两条命令已覆盖全部后续需求。接收时须核对真实分配长度、声明长度和表要求，再复制。

## 2. 配置回复：三个兼容RM端口，两个实际槽

**A-static+B：cmd9的112B是 `4+3×36` 配置，首u32为1，不能称为端口数1。** K `0x10928..0x10940` 接受配置view 0/1，步长`0x70`；`0x10b48..0x10e2c` 初始化两份记录，view1起始字为1。本文把0/1解释为physical/logical view是 **B**，原结构字段正式名称未恢复；**三个端口、每项36B、每项中的mask用途由原循环直接可证**。D `0x10124..0x10328` 每36B读取+4 mask并合入对应媒体记录`+0x14`，固定循环3项。

原表 K `.rodata+0x4e0` 配合 B/R92 的字节得到：

| Backup key | 值 | 原表目标/关系 | 依据 |
|---|---:|---|---|
| `d90141` | 1 | MS0 `0x10 → RM1` | K `0x10698..0x10738`，原表第0行 |
| `d9013e` / `d9013f` / `d90140` | 2 / 3 / 0 | MMC0 `0x20 → RM2`；MMC1 `0x21 → RM3`；MMC2关闭 | 同上，第1–3行 |
| `d90142` / `d90143` | 2 / 3 | PCIe0 `0xb0 → RM2`；PCIe1 `0xb1 → RM3` | 同上，第4–5行 |
| `d90144` / `d90145` | 0 / 0 | other目标`0xa0/0xa1`未分配 | 同上，第6–7行 |
| `d90182` / `d90183` / `d90184` | 1 / 2 / 3 | physical RM1/2/3到logical RM1/2/3为恒等映射 | K `0x1073c..0x107ec`、`0x10c84..0x10cb0` |

B 和 R92 这些字节一致；proof.backup_port_config保存原偏移、值与表。**B：按原函数投影，尚未执行PCI更新时，cmd9 payload精确为下列小端字节**（去空白即112B；完整hex亦在 proof.configuration_projection / reply_fixtures）：

```text
01000000
00000000 01000000 01000000 10000000 00000000 00000000 00000000 00000000 00000000
01000000 02000000 06000000 00000000 20000000 b0000000 00000000 00000000 00000000
02000000 04000000 06000000 00000000 21000000 b1000000 00000000 00000000 00000000
```

每个36B record依次为：u32 index、u32 physical-port mask、u32 support bitmap、四个u32目标ID（MS/MMC/PCIe/other）、8B PCI附加信息。support bitmap 1/2/4/8由 K `0x10d0c..0x10e58` 原表分派；**这是支持类型，不是在场卡类型**。末8B在初始化后为0，K `0x108b8..0x1091c` 可由PCI枚举写入u16 bus信息、u8设备/功能信息及u32附加信息；完整正式字段名与原机实时值 **U**。无PCI的软件模型可保留初始化0，但不能声称它是FX3实机PCI枚举结果。上述112B没有容量、扇区、分区或文件系统字段。

**A-runtime+A-static+B：当前冻结配置的槽映射如下，不把RM编号当槽号。**

| 机身槽 | 应用媒体ID | MediaCommon返回路径 | logical/physical RM | D应得mask | 类型支持 |
|---|---|---|---|---:|---|
| slot1 | `0x1000` | `/nondev/rm3` | RM3 / RM3 | 4 | MMC1 `0x21`、PCIe1 `0xb1` |
| slot2 | `0x1010` | `/nondev/rm2` | RM2 / RM2 | 2 | MMC0 `0x20`、PCIe0 `0xb0` |

L92 **18308 / 18321–18330** 和 **18817 / 18831–18840** 直接绑定媒体ID、有效配置路径、open失败；A `0x4171670..0x41716c8` 的原事件名称表区分slot1/2。路径尾号和RM record由 C `0x39020..0x39058` 及路径表 `0x71d00..0x71d10` 关联；physical/logical恒等取自上表原Backup。RM1是本套固件保留的MS兼容项，**不是证据中的第三个FX3物理卡槽**。

## 3. FRONT原发送者、7B格式和初始顺序

**A-static：已找到CP原发送函数，payload恰为7B，没有额外VDF式封套。** P `0xab28a8..0xab2978`：`0xab28b2/0xab28ca` 合成目的`0x8028017c`，`0xab28be` 长度7，调用 `0x49f80c` 分配；`0xab2904..0xab290c` 将前3B写为 **`02 00 00`**；`0xab2910..0xab2934` 写入4B RM状态；`0xab293a → 0x49f140` 发送，失败走 `0xab2948 → 0x49f908` 释放。OSAL传输元数据另计，不能在7B前再拼一个猜测的24B头。

| 7B偏移 | 语义 | 证据 |
|---:|---|---|
| +0 | 固定type2 | P `0xab2904..0xab2906`；D `0x109b8..0x109c0` |
| +1 / +2 | 原发送器明确写0；不能解释成长度或状态码 | P `0xab2908..0xab290c` |
| +3 bits0/1/2 | RM1/RM2/RM3 enable | D `0x10cb8..0x10d08` |
| +4 / +5 / +6 bit0 | 对应RM hold | D `0x10cc4..0x10d20` |
| 同字节bit1 | 对应RM port_state，0空、1在场 | D `0xfb90..0xfbc4` 与 `0xfc28..0xfccc` |
| 同字节bits4..7 | 对应RM RemoveCnt | D `0x10cd8..0x10d30` |
| 同字节bits2..3 | 本接收器不消费；本模型清0，不推定硬件语义 | D上述解位；P `0xab2774..0xab2796`比较掩码 |

**A-static：CP发布时机有初始发送和变化发送，精确墙钟时点/上游硬件首采样仍U。** P `0xab27a6..0xab2806` 把输入结构`+0x10..+0x13`的使能与端口位写到缓存 `0x013f8158`；`0xab2858..0xab287c` 在内部发布state2时无条件发送并清状态，`0xab2880..0xab289c` 对state1发送，`0xab2808..0xab2856` 在state3比较有效位后变化才发。`0xab274e..0xab27a4` 是比较器，`0xab485a..0xab4870` 读内部发布状态。这些state1/2/3是**CP发布器内部状态，不能当D媒体state2的同一枚举**。尚未把上游采样周期/开机状态转移全链命名，不伪造“上电后固定N毫秒”。

**A-static：AP的`RMCMND-RM`线程缓存首包，并在通知注册时回放。** K `.text+0x1000..0x123c` 从`0x8028017c`接收，检查长度>6，缓存7B，首次置标志、唤醒等待者；原日志字符串为 `First Event From Front`（`.rodata.str1.8+0xd8`）。若通知ID非零，经`0x1120..0x1134`把原消息转发，否则释放。`mcmnd_rm_setosalidformedianotify@0x1258` 在已有缓存且新通知ID非零时分配**7B新副本**，复制缓存，**`0x1308..0x130c`把OSAL source显式设为这个通知目的ID**，再发往该ID。原始直通CP包的source由分配/传输层产生，本审计没有闭合具体数值；**回放路径source已闭合，不能因直通source未知就随意冒充某个CP ID**。

**A-static：D的ThreadInit等的是首个FRONT回调条件变量，不是cmd9/cmd3回复。** D constructor `0x10410..0x1043c` 建动态reply/notify ID并先Init；`0x10484..0x104a8` 注册原FRONT回调后执行cmd3；`0x104d0..0x104dc` 才启动检测线程。FRONT callback `0xe6dc..0xe8f0` 将完整OSAL包复制成内部 `0x80000005` / param`0x1005`；首次置对象`+0x2a0`并 `pthread_cond_signal(+0x2e8)`（`0xe824..0xe870`）。ThreadInit `0xe93c..0xe9d4` 等这个标志，绝对deadline取当前时间约+10秒；唤醒后 `0xe970..0xe9a0` 消费保存的ObjMsg并由Parse/Update建立媒体状态。**条件变量只保证曾有回调，7B/type2合法性仍需后续decoder验证，不能用空通知唤醒冒充有效首包。**

**A-runtime：AP92并无FRONT首包。** L92 **10978–10983** 显示 `pthread_cond_timedwait` 返回110并走 `0xe9e0`；**10986–11020** 的内部类型是 **`0x80000006`**，分别为三个fallback默认端口更新，**`FRONT_DECODE_AFTER_PORTS`这个观测标签不表示真的收到FRONT包**。没有 `FX3_MEDIA_FRONT` 或 `FRONT_FULL_BODY`。D `0xe9e0..0xec38` 的fallback会创建三个内部对象，不能把该路径当真实CP的空槽初始化。

## 4. 最小诚实的软件合同与StartInOut结果

**B（可实施的软件边界，未运行）：在原AP RM服务/缓存回放边界提供稳定空状态。** 本审计选用兼容配置中的三个RM项全部enabled且空，实际两个槽RM2/RM3保持enabled。重置为一次明确的synthetic boot epoch：

```text
FRONT body7 = 02 00 00 07 00 00 00
              type    En RM1 RM2 RM3

synthetic_empty_slot_provider=1 original_CP=0
```

这里`07`是**声明的软件兼容端口策略**，并非捕获的FX3开机使能字节；它不表示机身有第三个槽。只启用实际双槽的`02 00 00 06 00 00 00`也会对RM2/3得到相同的空槽推导，但会关闭RM1兼容项，本文保留原3项兼容配置。**原机正常首包的enable mask和RemoveCnt历史没有实测，精确原机空槽原始包仍U**。本模型的counter0只定义新的软件epoch，状态不变不递增，不发合成插入，发生明确建模的移出才按4bit递增。位语义依据第3节VA；这个候选不是原机GPIO值。

**A-static+B：发送时机必须以原调用顺序和状态消费为准。**

1. 软件服务先于 D constructor注册`0x80d9016e`，通过原OSAL接收，cmd9按第2节拓扑回复136B（头+8取**本次请求**，+12为0）；先让D Init得到mask4/2。依据 D `0x10438..0x1043c`、`0x10120..0x10328`。
2. 在cmd3到来前缓存有效7B空状态。cmd3(payload=实际通知ID)执行时，按原K回放逻辑分配7B副本，source设为**该通知ID**，送到该ID；成功转交后再完成cmd3回复28B。AP92 ID为`0x80af6180`、reply ID为`0x80af615f`仅供对照，不能硬编码新运行。依据 K `0x1258..0x1360`、D `0x10484..0x104dc`。
3. 保留原callback→ObjMsg→ThreadInit→Parse→Update顺序，确认媒体记录state2后才接受StartInOut。不得直接改`+0x2a0`、媒体state、模型参数或调用回调。无需墙钟sleep；确认点是 D `0x10d38`调用Update完成、媒体`+0x38`为2。依据 D `0xe824..0xe870/0xe978..0xe99c/0xfb48..0xfd48`。
4. cmd3(0)取消通知；通知队列失效/换代即停止旧目的发送。对新有效注册按原方式回放一次最新缓存，空状态不周期伪造插拔。依据 K `0x1274..0x1280/0x131c`。原服务存在时不抢占或重复注册；不加载会访问真实硬件的`mcmn_drv.ko`来凑队列。

**A-static：所有权使用原OSAL规则。** 原K服务线程在有界复制后释放request（`0x1c98..0x1cb4`），另分配reply（`0x1cc8..0x1cf0`），发送成功移交（`0x1cfc..0x1d04`），失败释放（`0x1d08..0x1d10`）；D接收后释放reply（`0xf300..0xf308`）。首包回放另分配、复制缓存字节；成功send后sender不再free/reuse，失败只free一次并报告失败（K `0x12a0..0x1360`）。仅缓存自有字节，不能持有caller指针；由单一provider串行拥有注册ID、snapshot和generation。该合同不要求冒充原CP。

**A-static+B：在此先决条件下，两个槽只通知status0，不再执行status1赋值。** D Update对每个配置mask扫描enabled端口（`0xfb80..0xfc24`）；enabled且port_state0使“已采到空端口”标志成立，候选index为3。媒体初始state0经 `0xfbcc→0xfd0c/0xfd10` 设为state2，保留index3；StartInOut的 `0xf9fc` 先设w2=0，`0xfa00/0xfa04`发现state2，直接跳到`0xfa34→0xfa3c`发status0，**跳过**`0xfa24`额外status0和`0xfa30`的status1赋值。proof.empty_slot_branch_projection分别保存mask4、2的条件与结果。

| 路径 | 原生媒体state | Start结果 | 依据 |
|---|---:|---|---|
| AP92缺RM配置且超时 | 0、mask0 | 先status0，再status1 | L92 **11046–11051 / 11093**；**11174–11180 / 11223** |
| 配置正确且首空包消费 | 2、mask4/2 | status0一次 | D `0xfd0c..0xfd14/0xf9f8..0xfa3c`，B推导 |
| 只补配置，没有首包 | 未保证 | 仍可能超时fallback | D `0xe93c..0xec38` |
| 只补首包，mask仍0 | state0未推进 | 仍可能status0→1 | D `0xfb90..0xfc1c` 的无匹配跳过 |

**B/U：可消除本次假插入发起的Mount，不能声称所有MediaCommon调用消失。** A原事件适配分别有insert (`0x2a7a7a4..0x2a7a864`) 和eject (`0x2a7a868..0x2a7a97c`) 分支，原名称表区分`0x10000..3`插入与`0x10004..7`移出。按status0推进应不再触发本次由status1导致的自动挂载；**这条应用后续不调用Mount的结果还要运行观测**。D Init仍做原配置查询，Update仍可调用`mcmn_drv_reject(empty)`，不能把这些读配置/拒绝记账当挂载。M `0x9c98..0x9f74` 自身不先检查FRONT状态，若有其他调用者明确请求Mount仍会查询/尝试open，provider不得伪造成功。

**A-runtime：AP92错误链已确定到open层。** L92 **18321–18334 / 18831–18844** 为valid1配置→`/nondev/rm3`或`rm2`→`mcmn_drv_open=0x80000004`→Mount转换为`0x7fffffff`，并非文件系统损坏的独立证据；**18470–18474 / 18977–18981** 为`6db/6dc=2`、`6e3/6e4=1`、`1203/1204=0x28`，**18409** 开警告。参数ID和值保留原厂传播，不能直接清参数掩盖故障。

## 5. UI预期、验收与未证实项

**A-doc：Sony FX3 Ver.2或更高版本帮助明确列出 NO CARD 为未插存储卡状态；MENU可从拍摄画面进入菜单是原厂规定的操作。** 2026-11-02联网核对：[图标说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888864.html) 的“NO CARD / No memory card inserted”，以及[菜单操作](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867589.html)第1步。网页也注明显示随固件版本可能变化；**这两页不是7.02空槽时所有模式都绝无警告的保证**。

**B：正常开机双空槽的合理目标为原拍摄待机画面呈现NO CARD，MENU可进入。U：本VM是否已满足仍未验收。** 此次仅静态分析与AP92旧日志，不能声称已解除现有对话框、已生成真实传感器画面或已经可用菜单。Lead后续需要记录cmd9/cmd3原分配发送/释放、有效首包被原callback/ThreadInit消费、mask4/2与state2、两次原status0且无status1、该启动窗口没有本次错误Mount链、原参数变化、新screen与原始像素读回；再用原MENU down/up验证菜单出现和方向/ENTER造成新画面。不要在已产生插入/挂载错误后补包，就称原始启动时序已通过。

尚未证实的内容已直接保存在 proof.limitations：

- 原机CP开机enable mask、RemoveCnt历史、准确首次发送时刻、上游物理卡检测GPIO/极性；P `0xab27a6`以上采样/调度链未完全命名。7B格式与发送器已闭合，软件epoch与实机捕获明确分开。
- 原CP直通包source值；K缓存回放source=notify目的ID已闭合，可采用回放边界，无需虚构CP source。
- 配置record最后8B的完整正式字段名及实机PCI枚举值；本文只投影无PCI初始化值。
- 应用完整无卡→不Mount→警告条件解除、现有对话框自动退出语义、NO CARD绘制和MENU交互；均待运行，未把脚本0作为这些结果的回执。

本次结项是**可复现的协议审计与有标记的软件合同**。服务归属、请求/回复、7B发送器、缓存回放/首包等待、原配置投影和state2分支均有原地址证据；软件provider集成和运行/UI验收留给独占运行链。
