# FX3 原厂按键输入审计

结论：**首个 MENU 注入应复用现有 capid 所在的同一 `im.elf` 进程，调用原生 OSAL，把 20B 原厂物理键记录送到 `0x807a0020`；MENU 的 InfraInput 键码是 `0x1ab`，按下值 1，抬起值 0。** 这条路径不需要调用缺失的 remote 包装函数，也不需要先实现 GPIO 中断。它仍经过原 `InfraInput` 的键表、来源过滤、抑制、重复和回调；本审计没有发送事件，不能声称菜单已打开。

已重建原指令/原表证据，扫查完整投影的 565 个 ELF、126 个模块，remote 符号的动态导出提供者为 0。只读分析；未启动 QEMU、未改原件、未拿运行锁，输出仅本目录三个文件。

## 复现与证据定位

在项目根 `/Volumes/KAFU2T/AI/Projects/Mac` 执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python \
  work/fx3-vm-20261101/lead-claude/audits/key-input/audit_key_input.py

# 独立重建后逐字节比较现有 proof，不写文件
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python \
  work/fx3-vm-20261101/lead-claude/audits/key-input/audit_key_input.py --check
```

脚本核验目标卷 UUID、六份原件 SHA-256、31 条关键原指令、模块重定位、模板 BK4 校验和及键表边界；反汇编用 Capstone，不执行 ARM/Thumb 代码。`--check` 的通过仅是静态审计可复现性，不是注入或 UI 验收。

下文简称，完整路径和哈希均在 [key-input-proof.json](key-input-proof.json) 的 `sources` 中：

| 简称 | 原件/证据 |
|---|---|
| A | `menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so`，SHA `545c5053…` |
| O | 同目录 `libObj.so`，SHA `c4681d20…` |
| K | `full-v5/projection-manifest-full-v5.json` 将 guest `/usr/kmod/input.ko` 指向 `full-v4/payloads/d9fcf59b62f9960878f5ea433d350112f4a03fb9c6cd9d30154fb3e3ff54a057` |
| C | `work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin`，SHA `c90d00d8…`，Thumb VA＝文件偏移＋`0x108000` |
| B | `original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin`，SHA `bf3a9d85…` |
| L | 既有 `runtime/runs/ap66lut-ed5764ad/serial.log`；脚本未读取活动运行来当终验 |

A/O 的地址为 ELF VA，相当于装载基址加偏移；K 是 ET_REL，必须写作 **`.text+偏移` 或 `.init.text+偏移`**，不是运行时绝对 VA。B 的地址都是**文件偏移**。

## 1. 实际链路与硬件来源

这是厂商自己的 input/OSAL 链路，不能把 Linux `KEY_MENU` 数值代入：

```text
GPIO / ADC / FRONT / VGRIP 等物理来源
  → 原 AP input.ko 或 CP 键处理器
  → OSAL 20B InfraInputPhyKeyData，目标 0x807a0020
  → libObj InfraInput::RecvThread
  → 28B InputPhyKeyInternal，目标 0x007a804c
  → 状态缓存 / 抑制 / 重复 / 原 EventThread
  → appFw 注册的 InfraInput 回调与 UI 键映射
  → UI 是否切菜单仍由启动完成、当前场景及显示链路决定
```

证据：K `.text+0x12f0..0x13e0` 与 C `0x49b8c8..0x49b94a` 两个独立原发送者都构造同一 20B 记录；O `0xcb5e0..0xcbb60` 原接收/转换线程，A `0x16ef2a0..0x16ef334` 注册回调和键表。脚本中的 `driver_native_sender`、`cp_native_sender`、`obj_receiver`、`app_register` 保存连续指令及字节。

**AP 直连 GPIO 和 CP/前端来源共存。** K 的类别名重定位表 `.rodata+0x48` 起为 `0=[end], 1=ADC, 2=GPIO, 3=GPINT, 4=FRONT, 5=GPIRQ, 6=SIRCS, 7=VGRIP`。K `.text+0x1f74..0x1f80` 从配置读 bank/bit，再经重定位调用 `gpio_get_data_bit`；`.text+0x4520..0x4650` 创建/启动周期定时服务并注册 OSAL 回调，说明至少这条 GPIO 路径轮询，不以“加一个中断”自动产生事件。

同型号原厂默认模板 B 的 `0x01120000` 硬件配置有两个记录，**不是二者任选、混用或当作当前机身设置**：

| 记录/配置行 | 与本任务有关的内容 | 证据 |
|---|---|---|
| record0，property 文件 `0x71190`，表 12×64B | 中央确认/上/左/下/右来自 ADC 类别1、unit0，依次映射 `1ac/3/15/30/1af`；并有 GPIO bank17/bit18 的其他键 | B 行 `0x711a8/0x711e8/0x71228/0x71268/0x712a8/0x71468`；K `.init.text+0x38/0xb0` 读取 `0x01120000`，`+0x1dc` 用64B步长 |
| record1，property 文件 `0x13cdb4`，表39×64B | **MENU 为 FRONT 类别4、unit `0x6000`、bit2、active_level0、key `0x1ab`、on_value1** | B `0x13d48c`；原64B：`000000000400000000600000020000000000000000000000000000000a00000001000000ab010000010000000000000000000000000000000000000000000000` |

record0 的方向/确认是同一 ADC 通道的分压区间，依次 `0..0x5b`、`0x5c..0x111`、`0x112..0x1b7`、`0x1b8..0x257`、`0x258..0x304`，不是独立的 Linux GPIO 按键。原 K `.text+0..0xbc` 向 `0x00720018` 同步查询 ADC，消息 `+0=u32 0xfff1`、`+4=u8 0/1` 选择组，返回 `+6` 起12个 u16；需两组查询。此字段格式有原代码，ADC 服务的完整回复/前端状态模型本次没有闭合。

C `0x49bd6a/0x49bd94/0x49bdbe` 分别引用 ADC/GPIO/FRONT KeyConfig 原字符串；C `0x49b920..0x49b94a` 从 CP 发出 MENU 所属的同型物理键消息。结合原模板与原代码，**MENU 经 FRONT/CP 到 AP 的路径有静态依据**，并无证据支持它是 AP bank5 上的一个 bit。PCB 的实际连线、SysCon 具体器件、FRONT `unit0x6000` 到 CP 的完整帧格式/IRQ 仍未证实，不能把模板中的逻辑 unit 当作 MMIO 地址。

B 出自原包 `0110_backup/SYSIPSX-DSLR/ALCIN/CX95900_ALLLANG.bin`，封存来源见 `sources.seed_provenance` 和 `template_provenance`。它是公开同型号默认配置，不能代表真实相机此刻的校准/设置；本审计也没有重新证明原备份驱动在活动 VM 中的记录选择。

## 2. 键码表：UI 枚举与 InfraInput 码必须区分

A 的 `{u32 enum,u32 字符串长度,u64 字符串指针}` 名称表与 `0x2f8f8d8` 起的1114个 `<u32 UI,u32 InfraInput>` 配对表相互绑定。A `0x15948f8..0x159491c` 将该表建为映射，`0x16ee3b8..0x16ee3f0` 正向查询，`0x16ef140..0x16ef18c` 在读取物理状态前先做转换。以下两个数值不是 Linux evdev 键码。

| 键名（省略 `UIBIZ_KEY_`） | UI 枚举 | InfraInput 码 | A 名称表行 VA / 配对表 VA |
|---|---:|---:|---|
| TACT_MENU | `0x13` | **`0x1ab`** | `0x4164ee8` / `0x2f8f970` |
| TACT_UP | `0x2` | `0x3` | `0x4164dd8` / `0x2f8f8e8` |
| TACT_DOWN | `0x6` | `0x30` | `0x4164e18` / `0x2f8f908` |
| TACT_LEFT | `0x4` | `0x15` | `0x4164df8` / `0x2f8f8f8` |
| TACT_RIGHT | `0x16` | `0x1af` | `0x4164f18` / `0x2f8f988` |
| TACT_ENTER（中央确认） | `0x14` | `0x1ac` | `0x4164ef8` / `0x2f8f978` |
| DIAL_ASSIGN_REAR_DIAL | `0x2e3` | `0x10000013` | `0x4167be8` / `0x2f90ff0` |
| DIAL_ASSIGN_FRONT_DIAL | `0x2ed` | `0x1000001c` | `0x4167c88` / `0x2f91038` |
| DIAL_ASSIGN_CONTROL_WHEEL | `0x2ee` | `0x1000001d` | `0x4167c98` / `0x2f91040` |
| OTHER_KURU_LEFT / RIGHT | `0x2d1/0x2d2` | `0x10000000/01` | `0x4167ac8/0x4167ad8` / `0x2f90f60/68` |
| OTHER_WHEEL_LEFT / RIGHT | `0x2d3/0x2d4` | `0x10000003/04` | `0x4167ae8/0x4167af8` / `0x2f90f70/78` |
| OTHER_WHEEL | `0x2e6` | **本配对表无行，未证实** | 名称表 `0x4167c18` |
| OTHER_WHEEL2 / WHEEL3 | `0x2e8/0x2e9` | `0x10000017/18` | `0x4167c38/0x4167c48` / `0x2f91010/18` |
| DIAL_ASSIGN_REAR_DIAL2 | `0x2e7` | `0x1000ffff` | `0x4167c28` / `0x2f91008`；不能把此哨兵型值当作实装第二后拨盘 |

B `0x007a0001` 的首个 `BIN!` 子块 type2 为1112×48B物理配置；MENU 行文件 `0x538d0` 为 `infraName1/keyCode0x1ab/localCode0/repeat0=0/repeat=0/osalId0x00410025`。方向、确认分别在 `0x535d0/0x53630/0x53690/0x53900/0x53960`；拨盘配置 `0x5bfa0/0x5c150/0x5c180` 为 infraName `0x10`、localCode `0x13/0x1c/0x1d`。O `0xcd904..0xcdb60` 读取并按 type 选择该子块，O `0xcd4bc..0xcd4f0` 对 type2 用48B步长。完整选中行见 proof `logical_config.selected`。

**拨盘的名称/键码已证，转动 delta、方向符号、绕回以及机身具体轮子到物理来源的对应未闭合。** `I-InputRecv` 会将收到的物理消息 from_type 设为1（O `0xcb768/0xcb78c`）；不要把拨盘的 infraName16 与按键1混用。首轮仅注入 MENU/方向/确认；本审计没有给出拨盘可执行注入字节。

## 3. 内核模块、设备节点及用户态接收者

- 原启动脚本 `stage129-AP-DMM-config-and-device-trial-plan/inputs/insmod_drv2:17` 加载 `/usr/kmod/input.ko`。模块存在于**完整 full-v5 投影**，不在早期只含用户态依赖的 `regular-files/` 目录；只搜后者会漏报。
- K 的依赖包括 `Backup_read`、`gpio_get_data_bit`、`osal_*`、`udif_driver_register`、`udif_create_proc`；不含 `input_register_device` 或 `input_event`，没有把该物理路径注册为 Linux evdev 键盘的调用依据。完整未定义符号在 proof `input_kernel_undefined_symbols`。
- 同型号 GPL `cxd90057_set_defconfig`：`CONFIG_INPUT=y`、`CONFIG_INPUT_EVDEV=y`，但 `CONFIG_INPUT_KEYBOARD`、`CONFIG_INPUT_MISC`、`CONFIG_GPIOLIB` 关闭。完整投影无 `uinput.ko`。L 677–678 行也确实记录原内核 `evdev_init` 成功；这是 input 子系统存在的证据，不是 MENU 事件从 evdev 进入的证据。原 `vmlinux.bin` 没找到 `IKCFG_ST`，因此没有把公开 defconfig 冒称从当前内核内嵌配置提取。
- 静态投影没有 `/dev/input/*`/`/dev/uinput` 条目，但 devtmpfs 可动态建节点，**这不证明运行中节点不存在**。本次禁止操作 VM，没有实时枚举节点；也没有找到 A/O 打开 `/dev/input/event*` 的相机按键接收入口。已确认的入口是 O 的 OSAL 线程。
- L **1930行**：`FX3_UIPC_RECV_BEGIN ... name=I-InputRecv queue=0x807a0020 ... original_wait_follows=1`。这证明历史 AP66 的原接收线程确实等待该队列，不证明现有候选机已处理一次按键。

O `0xcb640..0xcb650` 调用 `osal_rcv_msg_tmo(0x807a0020,&msg,-1)`；`0xcb6d0..0xcb6e4` 检查来源，**来源等于目标队列 ID 的包被当作退出控制**，绝不能把 `src` 填成 `0x807a0020`。普通事件复制前16B并强制 from_type1，经键表/来源抑制等处理后变为28B内部记录，O `0xcbb40..0xcbb5c` 送到 `0x007a804c`。O `EventThread` 的 `0xc90b8..0xc9140` 再取32B事件，经 `0xc8dec` 分派到注册回调。A `0x16ef2a0..0x16ef334` 注册原回调与28行/1086行等键列表，原表的 status `0x7ffffffe` 为此处的筛选值，不是物理抬起值。

三种结构的边界为：20B物理记录是5个u32（下节完整列出）；28B内部记录在相同前20B后追加 `+20=u32 config_pos`、`+24=u32 internal_flag`（O `0xcbad4`、`0xcbb54`）；32B回调事件为 `+0=u32 event_code`、`+4=s16 tp_y`、`+6=s16 tp_x`、`+8=u32 status`、`+12=u32 prev_status`、`+16=u32 ex_info`、`+20=u32 repeat`、`+24=u32 from_type`、`+28=u8 inh`（余3B为对齐空间）。后者由 O `0xc8e50..0xc8f1c` 的逐字段原日志读取绑定；O `0xc8e1c..0xc8e2c` 取回调指针并以 `x0=callback_id,x1=event*` 调用。不要直接构造32B回调来绕过物理状态与抑制链。

## 4. `remote send_key_event@0x2ddf49c` 的性质

A `0x2ddf474..0x2ddf4b0` 是一个带追踪的包装函数：前后以 group `0x14`/operation `0x2d` 记账，保留传入的 x0/x1，再在 `0x2ddf49c` 调用 PLT `0x15933e0`。该槽重定位到：

```text
infra_wrapper_remote::detail::send_key_event_to_input_infra(
  send_key_event_to_input_infra_in_t const&,
  send_key_event_to_input_infra_out_t&)
```

它是强 `STB_GLOBAL` 未定义导入，不是此 VA 自己实现了键事件。脚本按 full-v5 清单逐份核验565个 ELF 后查动态导出，**无提供者**；这个结论只覆盖已投影原件，不能覆盖未取得的分区或未来 `dlopen`。该函数若经过惰性绑定被调用会面临 lookup 失败；启动是否即时报错取决于装载策略，不能推断已经调用。

它也不是菜单输入必经链：已在 A/O 找到无需该 remote 符号的 `InfraInput` 自然链路。x0/x1 结构布局/remote 服务 ID 在这个包装体中未出现，**不能用20B物理记录冒充这两个 C++ in/out 结构，更不能以成功桩隐藏缺失**。证据见 proof `app_remote`、`remote_import`。

## 5. 注入方案比较（按本 VM 的集成侵入性由低到高）

| 顺序/方案 | 精确可证合同 | 可用性、缺口与原证据 |
|---|---|---|
| **1：在现有 capid 同进程软件层发原生物理键记录（推荐）** | `dst=0x807a0020`、`src=0x00410025`、20B `<5I>`；下节给完整 MENU 序列 | K `.text+0x12f0..0x13e0`、C `0x49b8c8..0x49b94a`、O `0xcb640..0xcbb5c` 三端一致；无需再创建服务回复或改 AP 原码。必须用原分配器保留隐藏 OSAL 元数据，不能直接 `malloc` 后调用发送 |
| 2：原调试 SEND_EVENT 入口 | guest 内原测试协议 command2、其后五个 u32：`[2,key,sub,status,ex,from]`；MENU 按下24B为 `02000000ab01000000000000010000000000000001000000`。目标为日志指定 `0x007a018c` | O `0xd01e4..0xd0280` command2 跳转 `0xd05d8`；`0xd05d8..0xd0620` 从+4到+0x14复制五参数，经同一发送器 `0xcd79c` 发送。原用法字符串 O `0x1d5e37`：`sndcmd.elf --sync 0x007A018C cmd [params]`；此处会将 source 改为 `0x807a018c`，是原测试来源而非物理来源。命令行解析、测试入口启用、工具在当前 VM 的可用性未执行验证，不提供自动运行命令 |
| 3：在 CP/FRONT 服务层模拟硬件查询，继续让原驱动产键 | 已证 K `.text+0xc0..0xe8` 发往 `0x90280132` 的同步 FRONT 查询，先清 +0..+2，并检查回复 +2 status；默认 MENU 是 FRONT unit6000/bit2 active-low | **未闭合可执行报文合同**：24B前端结构的有效位/按键数组/源端更新、SysCon帧与CP端消费者未全部绑定。不得只把bit2塞到任意包里，也不得把 GPIO 地址冒充unit；比方案1需要更多模型和启动条件 |
| 4：guest `/dev/uinput` / 已有 `/dev/input/event*` | 标准 A64 Linux `input_event={s64 sec,s64 usec,u16 type,u16 code,s32 value}`，24B；MENU通常为 `EV_KEY=1,KEY_MENU=139,value1/0`，各配 `EV_SYN=0,SYN_REPORT=0,value0` | 该24B格式是 Linux 通用接口，**不是 FX3 的20B格式**。官方 uinput文档要求先用 ioctl 创建/启用虚拟设备；当前投影无uinput模块，GPL配置禁用INPUT_MISC，且没有相机AP监听evdev的证据。即使补模块产生event，也还需要evdev→原厂OSAL桥；直接写已有event节点不等于它在自然接收按键。不能作为当前最小路径 |
| 5：QEMU GPIO / 键矩阵 / 中断设备模型 | 现有 bank5仅允许32bit，group0/2/3/4 的 `+0x0/+0x4/+0x8` 为写值/set/clear；`+0x10` input寄存器直接 `MEMTX_ERROR`，没有IRQ线 | `qemu-display-build/.../hw/misc/fx3_gpio_bank5.c:1–26`；`virt.c:3176–3180` 映射到 `0xf1022000`。没有原MENU GPIO/IRQ合同，MENU模板又指向FRONT；需新增实际相关bank输入/轮询时序或前端/SysCon模型，不能复用bank5假装键盘。不给未证实的MENU寄存器序列 |

方案4仅用于排除通用路径，格式来源为 Linux 维护者的 [uinput 文档](https://docs.kernel.org/input/uinput.html)，键值取自 [Linux v4.9 UAPI 原头文件](https://raw.githubusercontent.com/torvalds/linux/v4.9/include/uapi/linux/input-event-codes.h)（本次查阅）；这些接口资料不证明目标 FX3 内核支持 uinput。方案1的软件键来源必须在日志中明确标为合成输入，不能称为原 CP 或实机键检测。

## 6. 推荐的最小 MENU 合同

**原厂物理事件 body，无 `0d20` 头、无command字段、无自动reply：**

| 偏移 | 类型 | MENU 按下 | MENU 抬起 | 依据 |
|---:|---|---:|---:|---|
| `+0` | u32 LE key_code | `0x1ab` | `0x1ab` | A 映射 `0x2f8f970`、K `+0x13d0` |
| `+4` | u32 LE sub_key_code | `0` | `0` | K `+0x13d0`、C `0x49b932/0x49b940` |
| `+8` | u32 LE status | `1` | `0` | K `+0x13d4`、B MENU硬件行 on_value1 |
| `+12` | u32 LE ex_info | `0` | `0` | K `+0x13d4`、B MENU硬件行ex0 |
| `+16` | u32 LE from_type | `1` | `1` | K `+0x13b4/0x13dc`、C `0x49b8e2/0x49b948`；O接收端也强制1 |

```text
按下：ab01000000000000010000000000000001000000
抬起：ab01000000000000000000000000000001000000
dst = 0x807a0020
src = 0x00410025       # 原发送者的来源ID，在原生OSAL元数据中设置
len = 20
```

最小实现顺序（仅供 Lead 之后集成，本审计未执行）：

```c
/* 在已有 im 进程内，与 capid 一样解析原 libosal 的函数。 */
osal_valloc_msg_wait(0x807a0020, &msg, 20, 1); /* 检查返回0 */
memcpy(msg, menu_down, 20);
osal_set_msg_src(msg, 0x00410025);
rc = osal_snd_msg(0x807a0020, msg);
/* rc==0: 所有权已交接，不再释放；rc!=0: 用原osal_free_msg回收。 */
/* 观察下述接收/缓存证据后，重新分配并发送menu_up。 */
```

O `0xcd7e8..0xcd8c8` 与 K `+0x132c/0x13b8/0x13e0/0x13f8` 为分配/来源/发送/失败释放原依据。不要把目标ID设为source（退出控制）、不要回收已成功发送的缓冲、不要复制隐藏头；也不要对20B物理记录加 VDF 风格8B头。MENU 在默认逻辑表 repeat0/repeat均0，按下和抬起各一包足够构成首个有界试验。

运行前条件：原启动屏障已完成、接收线程存活、键表包含 `0x1ab`、UI已可接受输入。不能在 AP74/75 的 fatal/异常监视状态中把“发送成功但无菜单”解释为码错；也不能通过补造显示完成/去抑制来让测试通过。

## 7. 运行验收应观察什么

依次取证，不能用 `osal_snd_msg=0` 代替菜单成功：

1. **消息到达**：给现有被动接收观察器增加定向记录（Lead 集成），`I-InputRecv` 的 `osal_rcv_msg_tmo` 返回0，body20B等于本次包、`src=0x00410025`。L 1930行目前只证明历史线程等待，未证明消费。
2. **原转换/缓存生效**：O `0xcb754` 开始处理，`0xcbb40..0xcbb5c` 原生发送28B到 `0x007a804c`。O `0xc8bcc` 的全局实例指针在 `libObj基址+0x2cde48`；实例 `+0x20` 是48B配置表、`+0x2c` 是行数、配置行 `+8` 为key；实例 `+0x38` 为44B状态表，同索引状态行 `+8` 必须由未知态变1再变0。读取必须经已有安全读取机制、真实装载基址及已初始化指针，不能写状态“帮助”测试。原状态读取函数为导出 `InfraInput::GetPhyKeyStatusCache(int, InfraInputPhyKeyData*)`，O `0xc9c08..0xc9c58`；要避免额外 `GetInstance` 引用计数泄漏。
3. **原日志/回调**：若该日志级别已开启，O `0x1d2a3d` 为 `received InputPhyKeyInternal`，`0x1d2abb/0x1d2b13` 打印key/status，O `0x1d2c6e` 的 `unknown key` 和 `0x1d2c32` 的 `invalid from_type` 都是明确失败证据。O `0x1d3182` 的 `InfraInput::SendAttachEvent, do send(...)`、`0x1d31db/0x1d3245` 记录event/status/prev_status；原 EventThread 最终走 O `0xc9140` 的回调分派。日志可能默认关闭，缺日志不构成未消费证明，应使用前两项。
4. **应用/可见菜单**：A 已注册回调实际收到匹配事件，随后出现新的原GPE绘制/状态切换，并由既有显示发布链拿到菜单文字图形。此项必须由运行链作截图/帧读回；本目录只有静态证据，**没有任何菜单打开或方向键可操作的验收**。

仍未证实：SysCon/FRONT 完整底层报文和中断；活动VM模块/节点实际清单；拨盘delta与物理布局；remote缺失函数实现；原启动屏障和菜单显示是否就绪。以上缺口不阻止方案1的静态实现合同，但都不能用此审计宣称完成。
