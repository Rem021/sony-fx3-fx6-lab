# VDF 0x011a / 0x0159 原件审计

结论：**0x011a 是 LCD 亮度设置，同步等待完成；0x0159 是 OSD 开关位掩码，原路径不等待也不生成 AP 完成回复。不要为 0x0159 注入预想的 0x1159。** AP 关键证据分别为 `appFw+0x2dea398 → +0x2de70a8`、`+0x2de72f4..+0x2de7300` 与 `+0x2deb4f0 → +0x2de83b4`、`+0x2deb4f4`；CP 关键证据为 `0x1ae8f4` 的 0x111a 和 `0x1abbb6 → 0x5cbdd0 → 0x1abc14` 的无回复分支。

本次只读 AP appFw.so、CP cpapp-b.bin 和 AP66 日志，只写本目录；没有改 runtime、启动 QEMU 或操作相机。VA 规则：AP 为 ELF VA（亦即 appFw 相对地址）；CP 为 Thumb 加载 VA，文件偏移 = VA−0x108000。逐条字节、指令、原件与日志 SHA256 见 [proof](vdf011a-0159-proof.json)。

## 复现

在 Mac 项目根运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/vdf011a-0159/audit_vdf011a_0159.py
```

退出 0，重新生成 proof；验证 9 条决定性原指令、RTTI/虚表、两级 dispatch 表、两个模型正例及六个拒绝例。此验证是静态代码与有界软件合同验证，没有运行原 CP，也没有显示像素验收。

## 0x011a：AP 调用与阻塞

- AP66 请求为 `0d201a010e000180010e000e0600`，来源 `0x81cf61c1`、TID334 `SeqQueueDispSwi`，共同入口 caller `appFw+0x2de7264`。日志行号与邻接接收记录已写入 proof.runtime_receipts；该 caller 地址本身不能当作具体 sequence。
- 具体链：`sequence_set_lcd_brightness::run()` 入口 `+0x2d8c34c`（函数日志字符串 VA `0x3952188`，源码名 `0x395215e`），在 `+0x2d8c478..+0x2d8c4ac` 从 sequence 对象 `+0x1bc/+0x1c0/+0x1c8/+0x1cc/+0x1d0/+0x1d4` 搬输入，`+0x2d8c4b4` 调 `+0x2dcfd94`，其 `+0x2dcfdbc` 调包装器 `+0x2dea1d8`，最后 `+0x2dea398` 调 `send_and_wait_cmp_i(+0x2de70a8)`。包装器签名日志 VA `0x39694f8` 明写 `vdf_set_disp_brightness_lcd`。其他对 `+0x2dcfd94` 的静态调用还有 `+0x2b8b488`、`+0x2d26b68`，未全面展开，故本结果不是完整调用者清单或唯一动态栈证明。
- 字段：四个 LE16 为 `200d/011a/000e/8001`。payload `+8=01` 是 LCD selector bit0；`+9=0e`、`+10=00`、`+11=0e`、`+12=06`、`+13=00`。初始化与分支在 `+0x2dea1ec..+0x2dea224`、`+0x2dea2e4..+0x2dea374`；CP `0x1b41fa..0x1b422e` 对 selector bit0 只取 AP `+12`，故本例有效亮度为 **6**，不是 14。selector bit1/bit5 取 AP `+10`；另外三个 0e/00 字节的完整命名/枚举未证实，不能赋予额外物理含义。
- 发送后 `+0x2de72f4` 取本线程 queue，`+0x2de72fc` 设置 `w2=-1`，`+0x2de7300` 调导入 `osal_rcv_msg_tmo`；没有有限超时或重试分支。按 OSAL 常见 -1 语义为无期限等待，底层 OSAL 的实现本轮未展开。AP66 在未回复后确实进入同一 `SeqQueueDispSwi` 的接收等待，支持该线程被卡住；这不等于已证明全部菜单线程都阻塞。
- 回复返回后 `+0x2de7304..+0x2de7314` 盲拷贝 12B，`+0x2de7318..+0x2de7320` 释放消息；**共同包装器没有检查回复 command/header/实际长度，也未分支检查接收函数返回值**。`+0x2dea39c` 读取 status32（回复 +8），`+0x2dea3a0` 经 `+0x2de4574` 转换；0 和 0x580000 走成功分支 `+0x2de46cc`。sequence 在 `+0x2d8c4b8` 检查结果，失败日志 VA `0x39226fe`、成功日志 VA `0x392269d`；成功才继续到 `+0x2d8c67c` 的 BACK_LIGHT_MODE 后续设置。缺回复时这些后续步骤不能到达。

## 0x011a：CP 映射、处理与回复

- wire decoder `0x1ac9ee..0x1aca04` 按 command−0x100 查 TBH；0x011a 表项 **0x1aca3c → 0x1acd02**，转换为内部 **0x20**。第二级 decoder `0x1ab698..0x1ab6a2` 按 internal−0x1f 查表，表项 **0x1ab6a8 → 0x1ab850**。handler 在 `0x1ab852` 调 `0x1b41d8`。
- `0x1b41e2..0x1b41f6` 构造旧 VDF `2001/0102/000c/0001`，payload 四字节 `01 06 00 00`。selector 与亮度映射见 `0x1b41fa..0x1b422e`，发送在 `0x1b4284`。RTTI 名称 VA `0xb3d110` 为 `VdfDisplayCmdSetPanelBrightness`，typeinfo `0xb7e0ac`，虚表地址点 `0xb7e094`，ID 方法 `0x5f2dac` 明确为 0x0102。
- validate `0x5f2dce..0x5f2ddc` 要求 selector 非零、没有 mask0xdc 内的位（仅允许 0x01/0x02/0x20），亮度 `<16`；否则在 `0x5f2dfa` 回旧 **0x1102/status1**。本例 selector1、亮度6 满足验证。
- execute `0x5f2e52..0x5f2e5e` 调 subsystem vtable+0x15c，槽 VA `0xb81368` 指向 `0x60f134`；该函数将 selector1 的 valid/brightness 写状态 `+0x170/+0x171`，其他 selector 分别写 `+0x172/+0x173` 与 `+0x174/+0x175`（`0x60f134..0x60f172`）。后续按设备配置启动亮度动作并等待内部事件；`0x5f2f54..0x5f2fa0` 汇总 pending flags，归零后 `0x5f2fb8..0x5f2fc8` 回旧 **0x1102/status32**。因此原 CP 不是收到包就无条件成功。
- legacy 回复经过状态域转换（既有共享路由规则；本轮未重新全面审计该路由），BB 完成器 `0x1ae8bc` 在 `0x1ae8cc..0x1ae8d2` 把 **0x590000 归一为0**，`0x1ae8f4..0x1ae91c` 生成 AP **0x111a、12B、status32@+8**。内部异步结果 `0x221` 也由 `0x1ac628..0x1ac636` 路由到此完成器。成功字节为 `0d201a110c00018000000000`。桥接发送失败则 `0x1b4290` 返回−1，`0x1ab856..0x1ab872` 将失败送完成器；不是永远成功。

## 0x0159：AP/CP 与无回复语义

- AP `+0x2deb444` 读取输入 mask，`+0x2deb45c..+0x2deb478` 构造 `200d/0159/000a/8001`，`+0x2deb47c..+0x2deb4e4` 保留输入 bits0/1/2/3/5/6/7（不保留 bit4）。捕获 payload 为 `07 00`，意为启用三个低位的 OSD 开关掩码，**不是某个数值等级7**。
- 调用链示例 `+0x2bb92cc`、`+0x2db4f18` → `+0x2dd0014` → `+0x2deb444` → `+0x2deb4f0` → `send_no_wait_i(+0x2de83b4)`。其中 `+0x2db4ef0..+0x2db4f00` 选择 mask7 或3；该方法日志 VA `0x395d860` 为 `sequence_still_record::set_osd_on_off()`，成功日志 VA `0x392bacf` 为 `Success VDF SET_OSD_ON_OFF`。捕获那一次动态调用者没有独立栈，所以此处是静态调用者列表，不能把 still_record 冒充捕获帧已证唯一来源。
- `send_no_wait_i` 在 `+0x2de854c` 调 `osal_snd_msg`，`+0x2de8550` 检查发送返回码；失败走断言/致命处理路径（`+0x2de8554..+0x2de85dc`），正常直接 `+0x2de85e0` 收尾；**完全没有接收调用或回复状态检查、没有回复超时**。`+0x2deb4f4` 明确给 out 写0；这是发送接受成功，不是 OSD 物理完成。AP66 同来源 `0x81cf61c0` 发送后立即继续 0x014c 请求，证明无回复未卡住这个发送者。
- CP 第一级表项 **0x1acaba → 0x1ace6e** 转换内部 **0xa0**，第二级表项 **0x1ab7a8 → 0x1abbb6**，handler `0x1abbb8` 调 `0x5cbdd0`。它在 `0x5cbdd8..0x5cbdf6` 构造旧 `2001/0302/000c/0002`，`0x5cbdfe..0x5cbe3e` 映射位域；本例7得到 payload `07 00 00 00`。`0x5cbe7a` 发送，handler 直接经 `0x1abc14` 仅记失败日志，不调用完成器。
- RTTI `VdfInputCmdSetOsdOnOff`，ID 方法 `0x5f5862..0x5f5870` 确认旧 0x0302；validate `0x5f5872..0x5f5882` 未做值范围验证。execute `0x5f5884..0x5f58a8` 调 subsystem vtable+0x16c（槽 VA `0xb81378`，实现 `0x60f1b0`），将4B写到状态 **+0x14e..+0x151**，再 `0x5f58aa..0x5f5920` 构造内部 **0xf030/12B** 并 enqueue。这里没有旧0x1302或 AP0x1159 回复。**原路径成功状态是本地 return0/异步队列接受，不存在可报告的0x1159成功体。**

## 最小软件模型合同

脚本内 `minimum_model` 只是可复核的有限合同，未接入 runtime。

- 0x011a 只接受本次完整14B捕获值，保留原payload，记录 LCD selector1/brightness6 与 `pending_hardware=true`，再返回12B 0x111a/status0；该0表示软件后端接受状态，不声称原CP亮度动作或真实LCD完成。CP真实校验与状态写入证据为 `0x5f2dce..0x5f2ddc`、`0x60f134..0x60f14a`，完成格式证据为 `0x1ae8f4..0x1ae91c`。未建模其他亮度模式、selector或场景一律拒绝；生产模型如需支持，必须补状态生命周期与失败处理。
- 0x0159 最小接受完整10B、固定header、零padding、mask3或7（AP已确认实际构造值 `+0x2db4ef0..+0x2db4f00`），保存4B legacy payload 与 `pending_f030=true`，返回 **None**，不向AP queue投消息；依据 `0x5cbdd0`、`0x60f1b0`、`0x5f58cc`、`+0x2deb4f4`。非零padding、长度或header错、bit4、未审计的其他mask都拒绝，不能把原CP缺少范围检查扩展成软件模型无条件成功。
- 无回复阻塞判断：0x011a 可阻塞当前 `SeqQueueDispSwi`，依据 AP `+0x2de7300`、接收参数−1与日志；0x0159 无回复本来就是协议预期，依据 AP `+0x2de83b4..+0x2de85fc`、CP `0x1abbb6..0x1abbbc` 和后继日志。修复0x011a至多解除一个已定位等待点；不能据此宣称菜单已实现。

## 未证实项

- OSD 各bit具体对应 LCD/EVF/HDMI 等输出的完整枚举名称；本次只证明位保留、mask3/7、状态写与队列（AP `+0x2deb47c`、CP `0x5cbdfe`、`0x60f1b0`）。
- 捕获0x011a/0159的完整动态sequence栈；已有静态具体调用链与各自日志绑定，但未新增运行探针。
- OSAL底层对−1的精确实现、取消行为与共享queue上其他消息的匹配不变量；共同包装器明确没有有限timeout或自身回复头校验（AP `+0x2de72f4..+0x2de7320`）。
- 原CP硬件亮度完成、内部f030的真实消费者、活动OSD像素、菜单显示及整体VM验收（CP `0x5f2f54`、`0x5f58cc` 仅给出后续协议入口）。
- 非捕获0x011a所有模式/字段枚举与完整legacy1102错误映射；软件模型保持拒绝，本轮未扩大支持范围。
