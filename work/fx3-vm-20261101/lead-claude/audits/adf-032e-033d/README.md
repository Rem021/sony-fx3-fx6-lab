# ADF 0x032e / 0x033d 启动审计

结论：**0x033d 是正常 boot 完成屏障上的实际阻塞项，0x032e 也是。** 两者虽在独立线程中运行，主 boot 会等待其完成；但尚未追通屏障到最终菜单绘制通知的全部路径，不能将“回复两条命令”当作菜单恢复充分条件。决定性证据是 AP `0x2b66dc8..0x2b66e04` 启动两子任务、`0x2b67a60..0x2b67a6c` 汇入四任务屏障，以及 `0x2b635b8..0x2b63678` 无期限等待并计满四次匹配完成。

本次仅静态读取原 AP/CP、旧 proof/script 和 AP69 捕获；只写本目录，不改 runtime、STATE、原固件，不启动 QEMU，不访问相机。VA 均为 image VA（AP 可加运行时基址，CP file offset = VA − `0x108000`）。可复核的逐指令原始字节、文件 SHA256、捕获行号在 [proof](adf-032e-033d-proof.json)。

## AP 请求、调用链和失败

| 项 | 0x032e | 0x033d |
|---|---|---|
| sequence | `sequence_boot::adf_set_volume_i`，入口 `0x2b5fae4`，函数名字符串 `0x391a5f0` | `sequence_boot::regist_beep_signals_i`，入口 `0x2b61a90`，字符串 `0x391a678` |
| 日志 | `Send adf_set_volume`，字符串 `0x3917e31`；调用 `0x2b5fb1c` | `Send adf_sys_get_system_sound_address`，字符串 `0x39184f4`；调用 `0x2b61d80` |
| wrapper | `0x2b5fb30 → 0x2dd0ed4 → 0x2ded154` | `0x2b61d8c → 0x2dd0fd4 → 0x2deea08` |
| 原请求 | `0d202e030a0001800800`，10B，+8 u8=8，+9=0 | `0d203d0308000180`，8B，无载荷 |
| envelope | 两者均 LE u16 type `0x200d`、cmd、total length、flags `0x8001`；目的 `0x92840747`，构造 VA `0x2ded164..0x2ded1f4` | 构造 VA `0x2deea0c..0x2deea5c` |
| 同步等待 | `0x2ded1f4 → 0x2de70a8`；reply count=12 | `0x2deea5c → 0x2de70a8`；reply count=24 |
| 状态消费 | reply+8 u32，`0x2ded1f8..0x2ded208` 经 `0x2de4574` 转成本地状态 | reply+8 u32；reply+16 u64 地址复制到 out+8，`0x2deea60..0x2deea70` |
| 捕获线程 | TID 319，source `0x81cf61c3`，serial 行20288–20302 | TID 320，source `0x81cf61c4`，serial 行20304–20319 |

共同 send/wait helper 在 `0x2de725c` 发送，`0x2de72fc` 设置 timeout=-1，`0x2de7300` 接收，`0x2de7304..0x2de7314` 固定长度复制。该 wrapper 本身没有额外检查收到的 cmd/length；其下层 UIPC 是否还检查相关字段，本审计未证实，软件模型仍须严格匹配。状态0经 `0x2de45c4 → 0x2de46cc` 转0。

两条捕获栈都是 `send helper → adf wrapper → API wrapper → boot子函数 → 0x2dcb9c0 → 0x2f71ba0 → libosal_utm+0x1184 → pthread`；helper 返回地址分别 `0x2ded1f8` / `0x2deea60`，AP69 发送 caller 为 `appFw+0x2de7264`。不回复会一直等，且 worker 完成回调位于 `0x2dcb9c0..0x2dcba04`，必须业务调用返回后才执行。

0x032e 的本地状态非0在 `0x2b5fb38 → 0x2b5fb64` 进入 Failure 日志、断言/致命处理（最终 `0x2b5fc34..0x2b5fc38`）；0x033d 非0在 `0x2b61d94 → 0x2b61dfc` 同样进入致命路径（`0x2b61ecc..0x2b61ed0`），不是可随意回复错误后忽略的可选功能。

## 四任务屏障与显示关系

| 栈保存句柄 | GOT VA → 子函数 | 创建位置 |
|---|---|---|
| +0x70 | `0x472c3c0 → 0x2b61efc`，`license_get_i`（字符串 `0x391a590`） | `0x2b638b8..0x2b63904` |
| +0x6c | `0x472b2d0 → 0x2b5fae4`，音量 | `0x2b66dc8..0x2b66de4` |
| +0x68 | `0x474f098 → 0x2b61a90`，提示音注册 | `0x2b66de8..0x2b66e04` |
| +0x64 | `0x47a6698 → 0x2b60208`，`adf_get_func_i`（字符串 `0x391a5c0`） | `0x2b6765c..0x2b67678` |

`0x2b67a60` 取+6c/+70，`0x2b67a68` 取+64/+68，`0x2b67a6c` 调用 `0x2b6353c`；该函数 `0x2b6357c` 初始化剩余数4，`0x2b635d0` 等完成队列，`0x2b63628..0x2b63648` 匹配句柄并减1，`0x2b63678` 非0继续等。另有 `0x2000` 特殊提前退出分支（`0x2b63600..0x2b63624`），不应把它作为成功绕过策略。

**另外两项是许可证读取和 ADF 功能查询，四任务中没有 VDF 0x11a。** ADF 功能查询的 `0x2b60264 → 0x2dd0c94 → 0x2dec778` 是另一 ADF 命令，不是 VDF 显示请求；`0x2b67a70` 起的后续初始化位于屏障之后。对菜单/显示的判断是：正常启动推进确实被0x033d拦住，不能判为非关键后台等待；“最终菜单绘制只依赖这一个屏障”仍未证实。

## CP 旧命令与 completion

0x032e：桥接分支 `0x1ac0ae..0x1ac0ce` 调 `0x1b2574`，构造 `type=0x2004, cmd=0x0311, len=12, flags=1`，+8复制 u8 音量，余下清0（`0x1b2584..0x1b25b0`）。旧类 RTTI `AdfSetOutputVolume` 为 `0xb38890`，typeinfo 引用 `0xb6c9b4`，vtable 可定位 Execute `0x596cde`；该函数将 body 交 `0x162834`，其 `0x162858..0x16289a` 把 wire 1..16 映射为内部0..15，0为静音、>16钳到15，因此 wire8对应内部7。`0x596cf6..0x596d32` 构造旧回复 `2004/8311/12B/0001`、status32+8=0；这是控制接受，不是 DAC/扬声器实测。

AP 方向 `0x5ca404..0x5ca44a` 构造 `200d/132e/12B/8001`、status32+8（成功0），完整成功字节为 `0d202e130c00018000000000`。原请求8的合同可以严格限定为保存 wire8/internal7 的软件状态，再单次回复，不泛化到任意音量。

0x033d：提示的 `0x1b3634` **是 ERR_FATAL 字符串，不是函数**；实际 SendADF 位于 `0x1b35e4`，由 `0x1ac314` 调用，构造 `2004/020a/8B/0001`（`0x1b35ea..0x1b3604`）。RTTI 名 `35AdfSystemSoundGetSystemSoundAddress` 在 `0xb3b730`，typeinfo `0xb6ff0c`，vtable address point `0xb6ff04`；处理函数 `0x5ad786` 查参数 ID `0xfa01a0`（`0x5ad79a..0x5ad7a4`）。查到则读8个 LE 字节拼成64位地址、status=0；查不到则 status=`0xefff`、地址0（`0x5ad7a8..0x5ad7dc`）。参数目录记录在 `0xb6eccc`，offset=`0x12`、size=8；不是“音频缓冲区只有8字节”。目录初始化 `0x5a90a6..0x5a90da → 0x5a9154` 将条目映射到 runtime BSS 参数块 `0x1438cdd + offset`，其值不在 cpapp 文件内，不能当作已知原物理地址。

`0x5ad808..0x5ad852` 构造旧 completion `2004/820a/24B/0001`：+8 phys64、+16 status32、+20清0。向 AP 转换的 `0x5ca880..0x5ca8fa` 产生 `200d/133d/24B/8001`：+8 status32、+12清0、+16 phys64；`0x5ca8c4..0x5ca8cc` 仅在旧回复命令为0x820a时复制地址。异步旧发送函数 `0x5daac2` 本身只做消息发送，不能把其返回0误认成提示音已加载。

## 0x033d 地址到底指向什么

**它是内置提示音数据的 CP 物理基址，不是 AP 待写入全部 `.bin` 文件的通用缓冲区。** AP 注册表构造 `0x2b61a90..0x2b61d68` 建立13项；前9项有固定位移/长度，后4项提供文件名。helper `0x2b61798` 保存长度到记录+0x10（`0x2b61954`）、偏移到+0x18（`0x2b61994`）、文件名到+0x2c（`0x2b61a5c..0x2b61a60`）；取表 `0x2b609c8..0x2b609e4` 后，在 `0x2b60a0c..0x2b60a10` 按文件名字节是否为空分支。

| 内置索引 | 偏移 | 长度 | 构造调用 VA |
|---|---|---|---|
| 0 | 0 | 0x100 | 0x2b61ae0 |
| 1 | 0x100 | 0xb80 | 0x2b61b14 |
| 2 | 0xc80 | 0xb80 | 0x2b61b48 |
| 3 | 0x6380 | 0x15c0 | 0x2b61b7c |
| 4 | 0x5840 | 0xb40 | 0x2b61bb0 |
| 5 | 0x7940 | 0xb40 | 0x2b61be4 |
| 6 | 0x1800 | 0xe80 | 0x2b61c18 |
| 7 | 0x2680 | 0xd80 | 0x2b61c4c |
| 8 | 0x3400 | 0x2440 | 0x2b61c88 |

内置分支 `0x2b61538..0x2b61544` 直接算 `physical = returned_base + record_offset`，不调用 mmap/fread，也不在这里写内置音频。最大末端 `0x7940+0xb40=0x8480` 是已证实 AP 访问范围下限；不能由此推出原 CP 分配总量。AP 最终将物理地址与长度等字段交 ADF set_table（`0x2b613ac..0x2b613f0`），再设该提示音音量（`0x2b61444..0x2b6145c`）。原内置数据应由 CP/平台事先提供，但具体写入者、原数据位置、采样率/通道/位深/压缩格式仍未证实，不能把它描述成确定的 PCM16/48k。

文件分支会申请 MIRA 和 CETUS DMM，`0x2b60a48`、`0x2b60aa8`（wrapper `0x2dda3b4`），`0x2b60cd4` 做 mmap（wrapper `0x2dda5b4`），`0x2b60e28 → 0x2dda634 → 0x2e50378` 用 fopen/fread 读入 AP 映射，`0x2b60fb0 → 0x2dd4734 → 0x2e15a18` 做 interchip_transfer_async，之后 munmap、两侧 close/free（`0x2b61120, 0x2b61254, 0x2b612a0`）。`0x2b61de0..0x2b61df4` 依次注册13项，因此0x033d解锁后还会遇到这些原协议，不能声称一次地址回复就实现整个音频服务。0x033d 基址消费链未见直接 `/dev/mem` 使用；软件模型可自行用 `/dev/mem` 建 backing，这与原 AP 消费方式是两回事。

## 最小模型合同及拒绝集合

建议以 **64KiB容量、64KiB基址对齐** 建一个独立 guest RAM 预留区；其容量大于 AP 已证实的0x8480，4KiB页向上取整最低0x9000。64KiB是保守模型选择，不是已证实原 CP 对齐要求。候选例如 `0x41da00000`，必须由 Lead 另行核对 guest RAM/iomem/其他预留、以 memrsv 真正保留并绑定进程生命周期后才能采用，**本次没有分配该地址**。AP69 serial 行20–21已记录 CAPID `0x41d800000/0x10000` 与 remote DMM `0x41d900000/0x100000` 的 memrsv 先例；不能挪用或覆盖它们。

按原语义提供成功0x033d，要求 backing 在回复前已含前9项正确原始内置声音数据，且 offset/length 全部可读、持续有效；AP不会替模型补写这些内置数据（`0x2b61538`）。目前未找到原字节，故**原生声音兼容的成功回复仍应关闭**。若 Lead 明确选取“静音、禁止播放的纯软件后端”，可用清0 backing 供逻辑注册，但只能声称地址/注册状态的模型，不得称原声音功能；后续播放命令仍拒绝，不能以清0替代原音频内容证明。

0x032e 最小允许集合：目的0x92840747、type200d、cmd032e、len10、flags8001、body `08 00`，保存wire8/internal7并向原source单次回复132e/12B/status0（AP `0x2ded174..0x2ded1f4`、CP `0x162858..0x16289a`、`0x5ca422..0x5ca444`）。0x033d 最小允许集合：同目的、type/flags、cmd033d、len8，无payload，按上述 backing/content 条件回复133d/24B/status0/+16有效phys64（AP `0x2deea0c..0x2deea70`、CP `0x5ca8a2..0x5ca8cc`）。

拒绝：错误目的/type/cmd/flags、声明长度与实际长度不等、032e值非8或pad非0、033d额外payload、未绑定source/重复完成、0或截断物理地址、区域重叠/未预留/寿命不明、容量小于0x8480、地址加法溢出、未满足映射对齐、没有原数据却宣称原生提示音、未经实现的播放/DMM/跨芯片传输。字段依据见上列 AP 构造和 CP completion VA；所有权、重复、溢出与内容门槛是建议的模型约束，不声称原 firmware 全部做同样校验。

内存原则参考 Linux 官方 [reserved-memory 说明](https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux-stable-rc/+/c125311d96b1bfcce0f5930a4f0fdfe39ea14f7c/Documentation/devicetree/bindings/reserved-memory/reserved-memory.txt)（2026-11-01查阅）：预留区应从普通分配排除。此链接仅支持通用原则，Sony 的 memrsv 私有实现和当前可用物理范围以本地原日志/运行链核验为准。

## 复现和未证实项

在 Mac 项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/adf-032e-033d/audit_adf_032e_033d.py
```

脚本检查固定 AP/CP SHA256、9处关键指令、四个任务指针、自动提取9个内置位移长度并断言末端0x8480、提取两份原始请求/等待栈，重建 proof 后退出0。可附参数 `ap VA:LENGTH` 或 `cp VA:LENGTH` 作只读反汇编。它不执行原固件业务逻辑，成功只代表静态审计重现。

仍未证实：原 CP 内置音频数据生产者/字节/格式、完整原生区域大小及对齐；boot完成到菜单绘制的直接依赖；提案回复被guest消费、DMM及文件加载后续、可用菜单和声音输出。以上缺口不得用“脚本PASS”关闭。
