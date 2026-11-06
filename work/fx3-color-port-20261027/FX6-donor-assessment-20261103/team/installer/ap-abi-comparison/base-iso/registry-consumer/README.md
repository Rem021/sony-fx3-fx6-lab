# Base ISO 注册表与 FX3 原件对照

**结论：固定 FX6 原件的 `.init_array` 构造表没有模型 ID `0x3662`，因此在该构造完成且未发生后续插入时，`0x113469C` 查询走未注册分支；运行时后续插入尚未排除。** 未得到该 ID 的后继 ID，也没有闭合 `0x15370E4` 的运行时目标、IPC 字段/长度或下游消费者。此回执是 FX6/FX3 文件静态证据，不升级为 VM、冷启动或相机证据。

## 原件、方法与回执

输入为供体 `team/donor/nflasha15-files/lib/appFw.so`，SHA256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`；FX3 7.02 原 `work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so`，SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`。两者均由 ELF `PT_LOAD` 将本报告所列代码/表 VA 映射为同值文件偏移；脚本逐点核对映射及字节。[audit.py](audit.py) 只读固定原件，先验 SHA 不符即拒绝。[receipt.json](receipt.json) 包含 23 条初始记录原六个 32 位字段、15 处原指令、6 条 BL 原字节、11 个注册表指针引用及 FX3 对照。

项目根复现：

```sh
python3 work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/ap-abi-comparison/base-iso/registry-consumer/audit.py > work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/ap-abi-comparison/base-iso/registry-consumer/receipt.json
echo "audit exit=$?"
```

实际 `audit exit=0`。局部反汇编可用 `xcrun llvm-objdump -d --start-address=0xb75000 --stop-address=0xb750b4 <FX6 appFw.so>`、`--start-address=0x1ad25bc --stop-address=0x1ad2770`、`--start-address=0x1134678 --stop-address=0x1134758` 分别复核构造、哈希插入和查询分支。原件不运行，供体及 FX3 原件均未修改。

## 注册来源和字段

FX6 `.init_array` 槽 VA `0x29113A8`（文件偏移 `0x29013A8`）的原 8 字节指向构造入口 `0xB74FFC`；`0xB75000` 把 X1 设为表首 VA `0x253E9C0`（文件偏移相同），`0xB75008` 以 `ADD X2,X1,#0x228` 设尾 VA `0x253EBE8`；`0xB75030` 从全局槽 VA `0x2EEB528` 取 X26，`0xB75068`（原字节 `55 75 3d 94`）调用 `0x1AD25BC`，将 X0=注册表、X1=表首、X2=表尾传入。`0x1AD2604–0x1AD261C` 用尾首之差除以 24 计算记录数；`0x1AD2664 LDR W4,[X21]` 把每条第一个 32 位字段作为哈希键，`0x1AD2768 ADD X21,X21,#0x18` 迭代。初始表恰为 23 条、键唯一，键范围和全部六字段在回执中；**没有 `0x3662`**。其最高键 `0x1B87`，也小于 `0x3662`，不能借邻近 ID 推断注册。

初始记录的排列可由构造与查询相互印证：每条 24 字节的第 1 个 u32 是查找键，后继候选在第 3、4 个 u32；第 5 个 u32 的低字节是过滤启用位，第 6 个 u32 供过滤谓词使用。对应 `0x11346A4 ADD X19,X0,#0xC` 后，`0x11346B4 LDRB W0,[X19,#0xC]` 看启用位，`0x11346BC LDR W0,[X19,#0x10]` 传给 `0x1AD25AC` 检查，`0x11346CC LDR W0,[X19,#4]` 取第一后继，`0x1134744 LDR W0,[X19,#8]` 取第二后继。因为固定初始表没有 `0x3662`，**不能给 Base ISO 指派某条现有记录的后继和过滤条件**。

`0x1134690/98` 从同一全局槽取表，`0x113469C`（`49 08 ff 97`）调用 `0x10F67C0` 以 W0=`0x3662` 查询，`0x11346A0 CBZ X0,0x11346F8` 区分未注册。该初始构造后的未注册分支 `0x11346FC` 调 `0x1537058`：已核的 ID `0x3662` 表 `+0` 槽指向返回零的 `0x1476CDC`；`0x1134730` 继而以 W0=`0x3662`, W1=1 调 `0x10F5A88`，它设置本地 dirty 位。这不是日志，也不是已证实的序列化/传输。

若运行时有后续插入而查询命中，`0x11346AC` 经已解析的 `+0x20` 槽读取 Base ISO 本地值；`0x11346CC` 的后继 ID 源自动态记录，`0x11346D4` 调 `0x15370C8`，其中 `0x15370DC LDR X2,[X0,#0x10]`、`0x15370E4 BR X2` 才是第一处无法指定目标的间接边。现有原件仅证明初始构造和条件分派，不证明运行时插入不存在；因此 **IPC 字段、长度和消费者仍 unknown**。

## 覆盖边界与 FX3 兼容性

脚本按 AArch64 `ADRP` 解出全代码范围内指向页 `0x2EEB000`、后续八条指令内 `LDR +0x528` 的直接引用，共 11 处，列出 VA/文件偏移；其中 `0xB7501C/30` 是初始化，`0x1134690/98` 是本链查询，其他包含遍历/查询。这个索引**不覆盖**把全局指针传给未知函数后的间接改写、由另一全局别名访问或启动后动态插入；不能据此断言所有状态都未注册。下一可执行静态动作：以 `0x1AD25BC` 的哈希插入实现和 `0x2EEB528` 的所有写入/别名为种子，枚举写入者及其 X1 输入，找是否能产生键 `0x3662`；只有确立注册项后才能解 `0x15370E4` 的后继槽，再追序列化 API 的长度、字段及消费者读取。

FX3 原 `appFw.so` 中确有 `BASE_ISO_LOW_800`、`BASE_ISO_HIGH_2500`、`BASE_ISO_HIGH_12800` 字符串（文件偏移 `0x2FA343B/44C/45F`），说明有同主题的命名资源；不能据字符串认定 FX6 模型链兼容。FX3 的 `0x1824124` 原指令 `MOV W0,#0x3662` 处于模型注册序列；`0x19F8728` 同样装入 `0x3662`，但紧接 `0x19F8730 MOVK W0,#1,LSL#16`，实际复合 ID 为 `0x13662`。FX3 全原件没有 FX6 的 `extern_BKID_APP_EXTERN_BASE_ISO` 诊断/回调名；这构成具体入口结构差异，FX3 同数字 ID 与 Base ISO 语义是否绑定尚未核实。不能把 FX6 的 VA、表槽或 800/4000/12800 分派直接套到 FX3。
