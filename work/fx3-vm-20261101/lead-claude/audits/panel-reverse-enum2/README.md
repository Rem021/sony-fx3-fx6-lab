# FX3 panel reverse enum2：来源、显示域、触摸与完成合同

结论：AP80b2 的原包确实是 **enum2＝hrev1/vrev1/osdRev0**，不是 identity。enum2 来自 AP 的面板翻转角状态参数 `0x243`；原厂 `REVERSE_CLOSE` 分支会生成它，不能称为“所有 FX3 每次开机必然为2”或单凭此包称为固定的面板安装补偿。h/v 被 CP 转为独立面板控制值 **3**，osdRev 被保存在另一状态并可传入显示布局控制；**没有证据要求把 AP/GPE framebuffer 原地旋转，也没有证据允许把 osdRev0 解释为 OSD 永远不受面板扫描方向影响**。AP 的触摸库另有方向状态，启动用同一个 enum 发送 TP direction；enum2 对应 false/false，两轴在 libObj 的校准后坐标阶段反向。依据：AP `2c210f8..2c21100/2932154..2932164/2823acc..2823bbc/2eabfd0..2eac0c8`，CP `607514..607648/1e54fc..1e5534/1e08d8..1e0948`，libObj `d5548..d5590/d6ac4..d6b0c`。

**可诚实集成的是限定的 virtual-panel-config 完成**：只接收本次捕获28B，独立 f02e 等价 consumer 安装并读回 `{hrev=1,vrev=1,osdRev=0,control=3}`，再回1119/status0；标记 `hardware_driver_executed=0, framebuffer_modified=0`。这只完成软件面板控制，不等于原厂物理扫描或菜单像素已显示。若要把它升级成面板视觉等价，必须补齐最终 scanout、OSD组合与面板安装基准；不能把“整帧180°”先当原机视觉事实。原完成在 CP 控制调用返回后，且部分下层分支仅保存 orientation shadow（`1c35ba..1c35d2→5ded9c→1c37bc→1c4098→1c77dc→5e6058`），支持控制层和物理显示验收分开。建议软件实现的队列、generation、lease 与宿主投影规则不是原厂 ABI 字段。

本目录只产出 [audit_panel_reverse_enum2.py](audit_panel_reverse_enum2.py)、[panel-reverse-enum2-proof.json](panel-reverse-enum2-proof.json)、本文。未改原件、runtime、STATE、运行锁或 Git，未启动 QEMU，未操作相机。AP80b2 是读取既有捕获；这里没有新的 guest 回包消费或画面验收。

## 复现与输入身份

项目根执行：

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/panel-reverse-enum2/audit_panel_reverse_enum2.py
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/panel-reverse-enum2/audit_panel_reverse_enum2.py --check
```

第一条重建 proof，第二条重新提取并逐字节比对；均须退出0。脚本核对卷 UUID、六份输入 SHA256、74处原指令、56段字节/反汇编、六种 orientation、五种 TP direction、CP queue/TBB/vtable 和 libObj PLT；31个包变体不满足精确白名单。`ap:VA:LEN` / `cp:VA:LEN` / `obj:VA:LEN` 可只读打印指定十六进制范围。长 Thumb 范围包含 literal/TBB 数据，控制流以独立锚点和表项计算为准；单独反汇编 IT 内指令可能显示 movs，proof 同时固定前面的 IT 和连续范围。

| 输入 | SHA256 | 地址域 |
|---|---|---|
| 原 appFw.so | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | ELF VA |
| 原 cpapp-b.bin | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` | Thumb VA，文件偏移＝VA−108000 |
| 原 libObj.so | `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae` | ELF VA |
| 实际28B | `19e2db159542cfaba7ca1209be58106580765dc4b960301a3b7cc040f76935e6` | `runtime/ap80b2-frozen-orientation.bin` |
| 捕获JSON | `b4b292fe417be751ce63f3cdf156cb97ac691250dc0ad24144ab9d394b0fdbfe` | `runtime/ap80b2-orientation-capture.json` |
| A7C2参考代码 | `578dd4e3ca46d272fd60a361da6d53c78af772cf30c82ea590c6578becc6613e` | 固定副本的 C 行号；不是 FX3 VA |

任务描述中的“.bin”真实文件名为 `ap80b2-frozen-orientation.bin`，脚本直接读它，并核对 JSON `full_raw`、`enum=2` 与 `identity_reply_enabled=false`。捕获请求来自 `81cf61c0`，目标 `92840747`，28B完整值为：

```text
0d2019011c0001800101000000000000000000000000000000000000
```

头是 LE16 `200d/0119/28/8001`，+8/+9/+10＝1/1/0，+11..27全零；捕获栈含 AP `2dec0f0→2dd08c0→2b5fcb8`。原 worker 在 `2b5fca4` 读 `sequence+304`，父后段 `2b681e4` 等它的真实句柄；没有1119时该 worker 保留同步等待（AP `2dec0ec..2dec100/2de7264..2de7314`），不能补造任务完成或 notify。

## 1. sequence+304 从哪里来，原机是否常态为2

sequence_boot 构造器 `2c20ce8` 在 `2c20d08..2c20d14` 安装与原析构器 `2b63188` 相同的 vtable（GOT `47a8a70→46e4fd0`）。**它没有直接写常数2**：`2c210f8` 调 `2932154`，`2c210fc` 读返回指针的 u32，再由 `2c21100` 存到 `this+304`。getter 算出的地址为 **822c71c**；相邻 getter `2932168` 返回 **822c720**。原参数绑定表 `40a14e0` 是 `(40c0580,243)`，`40c0580` 又指向 `822c718`，所以这是参数243当前/下一状态的启动快照，不是直接读取某个硬件寄存器或从此函数读取 Backup。

参数生产者之一为原名 **`model::update_params_for_panel_vali_angle_status()`**（字符串 `37a5cc0`，函数 `2823890`）。它读取 vertical/horizontal/close/sideway 状态（日志格式 `379c118`，getter `2943334/294330c/294335c/2943384`），还按机型相关 getter `16f0ca8` 分支。`2823acc..2823adc` 明确打印 `PANEL_VALI_ANGLE_STATUS_REVERSE_CLOSE @379c1ba`，`2823aec` 选择状态类别2，`2823b20` 设置最终方向 enum2；`2823b80..2823bbc` 比较旧值并以参数ID243交 `2811bf8`，后者 `2811c24..2811c34` 同时写当前/下一槽。

因此“反向闭合”是原厂正常铰链状态中的一个分支；**只有运行时参数确实为该值才会生成本包**。其他分支可生成0/3/4等（`2823f90..2823fac` NORMAL_CLOSE、`2823d48..2823d6c` REVERSE_OPEN、`2823e1c..2823e58` SELF_SHOOTING），本机捕获2不能证明用户原机当前面板位置，更不能证明全机通用默认2。参数还有恢复/设置路径，如 `29810d0..2981168` 从参数map读取243并存两槽、`2811c4c..2811ca0` 显式setter；**本轮没有把这些map或快照继续绑定到某一有效 Backup property、模板默认值或机型物理安装角**。这三项保持未证实，不能将未找到的 Backup 绑定写成“绝不持久化”。

原 AP switch（表3963654，代码2dec094..2dec128）仍有六种编码：

| enum | h/v/osd | enum | h/v/osd |
|---:|---|---:|---|
| 0 | 0/0/0 | 3 | 0/1/0 |
| 1 | 0/1/1 | 4 | 1/0/1 |
| **2** | **1/1/0** | 5 | 0/0/1 |

## 2. h/v 与 osdRev 分属两条控制路径

完整业务绑定沿用并重读 [0119先例](../boot-deferred-0119-0328-digital/README.md)：wire119→internal24→CP `1b3e74` 转旧 `2001/0101/20B/1`；`VdfDisplayCmdSetPanelReverse::Execute 5f4910..5f4986` 把12B body放入 `2001/f02e/20B/1`，`5f497c` 调 `1e8298` 排队，**这里不发成功**。mask表 `b81088` 首项 `(9,90590819)`；f02e对象 `011cda18`、vtable `b80724`、ID函数 `607232`、Activate `607242`、Execute `60742c` 固定绑定到独立设备消费者，而不是同名字符串推测。

**h/v 路径**：Execute `60751e..607542` 把字节严格等于1转成布尔，保存 `{0,h,v,...}` 属性（vtable+404→`60f8b4`，结构内+4/+8分别h/v；第四word在这段没有明确初始化，不拿它作软件字段）。`1e54fc..1e5526` 通过+400→`60f8ae` 读同一结构，压成 `control=2*h+v`，enum2得到3；`1e5534→60daa2` 给 **027d0728** 同步控制消息，+0＝`20000002`、+12 byte＝control，随后同步callback `a878ca`（`60db74..60db78`）。

本轮再向下绑定：`5dea6a` 所建 panel context 的 `+dc` 在 `5deb9e..5deba6` 安装 `5ded9d`，`5dec2e..5dec7a` 把端点027d0728注册到 callback `5dc14b`。`5dc14a→1c3394` 的 TBB `1c34d0` 第2项精确落 **1c35ba**，它从消息+12读control并存context+74，再调用context+dc（`1c35c0..1c35d0`）。`5ded9c→1c37bc` 的一条下层分支构造op3/28B并发送到context+12c（`1c37e8..1c3808`），另一条构造面板参数后调用 `1c4098`（`1c382c..1c388e`）。后者可继续到 `1c77dc`，再由 **5e6058** 把方向byte保存到 `01438e59` 或 `0143902c`（`1c784a/1c785e→5e6058..5e6076`）；还有后续读者 `1c7af4→5e6078`。这些是面板基础设施/方向缓存路径，未见对 AP framebuffer 的像素写入。

这已足够排除“0119收包函数必须令AP原地改绘图坐标”作为最小合同，也说明**h/v 的 setter 可以处于先保存面板控制、后续扫描再消费的层级**。但尚未闭合最终 panel/EVF driver 的寄存器位、面板轴安装关系及所有设备类型分支，不能严称“已经定位某LCD扫描寄存器”。`5e2f34` 是格式化并发送日志的路径（`5e2f34..5e305c`），不得误认其常量 `f0000404` 是面板 MMIO。

**osdRev 路径**：`607548` 从body+2独立取值；`607616→1e0848` 把它放入布局参数+24hex（局部sp+34hex，`1e08d8..1e08e6`），随后 `60cc44→a5df3a→a62d32` 转换并发送显示配置。`a62e9c..a62eaa` 将该布局参数的+24序列化，与矩形/plane等配置同处；不是像素buffer循环。Execute 还通过+40c→`60f8d2` 存单独状态索引0（`607628..607636`）。enum2使这个OSD独立控制值为0，**不等于在最终物理面板上“OSD层免翻转”**：h/v 的下游作用域是否覆盖整幅面板、osdRev是否作为某些场景的反向补偿，还缺最终scanout证明。本轮不给osdRev1任何像素保证。

AP 对该参数也有自身几何消费，例如 `16f06dc..16f0780` 按enum2分支做坐标/区域浮点计算；因此“AP全程完全不关心方向”也不成立。该函数不构成全局 framebuffer 预翻转的证据。原 [0147审计](../vdf0147-plane-scanout/README.md) 的配置表bank、真实像素bank、发布和plane顺序缺口仍然存在；本轮没有把0119变成OSD发布/flip协议。

## 3. 触摸：独立 TP direction，不能再重复翻转

原启动 `2b671bc` 读取同一sequence+304，`2b671cc→2ddfb74→2eabfd0` 构造发到 **807b002b** 的16B op0。表399ecb0与switch `2eac018/020/0c0` 的结果如下；enum2的x/y bool都为false，准确包为 **`00000000100000000000000000000000`**。这是no-wait发送，不是0119回复的一部分（`2eac044→2eace78`）。

| enum | x_direction/y_direction |
|---:|---|
| 0 | 1/1 |
| 1 | 0/0 |
| **2** | **0/0** |
| 3 | 1/0 |
| 4 | 1/1 |

原libObj接收线程 `d53bc..d5590` 等807b002b，op0在 `d5548..d5588` 把+8/+12各自与1比较，调用PLT57830；动态重定位精确绑定 **`InfraTp::SetTpDirection(bool,bool) @d2a3c`**。setter把x/y bool存实例+50/+51（`d2a94/d2a9c`）。触摸接收在校准后读这两个byte：false时分别做 `maxX-x`、`maxY-y`（`d6a7c..d6ae0`），再把超上界值夹到 `maxX-1/maxY-1`（`d6af0..d6b0c`）；**这是max−sample再夹界，并非在所有原始单位上直接639−x/479−y**。校准输入/实际max/原始触摸包格式本轮未闭合。校准流程另有同状态读者 `d4134..d415c`，不能脱离这些状态任意塞raw坐标。

所以 AP 侧输入库确实实施方向变换，但它读的是自己的TP状态，**没有证据说它去读CP的h/v缓存**。只添加1119控制后端不会自动实现缺失的TP服务；要观察先前TP发送已由原线程消费。注入坐标的入口决定是否需要变换：

| 注入/显示域 | 应用规则 |
|---|---|
| MENU/方向/确认物理键20B | 无坐标翻转，仍用 [key-input](../key-input/README.md) 原键码；MENU1ab、上3/左15/下30/右1af/确定1ac。依据libObj `cb640..cbb5c`；包内无xy |
| 逻辑UI坐标、已越过InfraTp | 逻辑framebuffer窗口点击直接用其xy；若窗口显示下面定义的虚拟扫描网格，先用该窗口变换的逆映射一次，再注入 |
| 原InfraTp之前的raw输入 | 保留原校准与false/false变换，不再预先套一次180°；需要先恢复raw包格式/单位。不能把后处理639−x当作raw协议 |

## 4. 原完成顺序、成功/失败和 AP 后果

Activate `607242..6072dc` 按body+4 mode设置状态与帧目标；本次mode0走状态0，目标为当前帧计数+1。Execute状态0/1/2最终进入10hex；`6074ce..607512` 未达目标就pending，达到才保存h/v、可选OSD布局控制、面板基础设施调用（`607514..60763e`）。两项错误OR后归一：非零为5，否则0，`607648→6073b8` 发旧1101。非法mode有status1（`6072d4..6072d8`）。Activate清理被替代命令也可能发status0（`607354..607356`），所以单个成功码不足以证明翻转发生，更不是物理LCD扫描验收。

| 结果 | 旧2001/1101 12B | BB后的200d/1119 12B | AP本地值 |
|---|---|---|---:|
| 成功0 | `012001110c00010000000000` | **`0d2019110c00018000000000`** | 0 |
| mode非法1 | `012001110c00010001000000` | `0d2019110c00018001005900` | 6a |
| 显示/infra非零→5 | `012001110c00010005000000` | `0d2019110c00018005005900` | 6e |

旧包构造在 `6073b8..60742a`。BB `1adbd4..1adcde` 加显示域590000；`1aecb0..1aecb6` **只将590000归零**，不吞掉590001/590005；`1aecd8..1aecfa` 构造1119，`1aed00→1aef1c` 回本次原事务source，metadata source＝92840747。AP转换 `2de4574/2de47dc/2de47e4` 得上述本地6a/6e。

AP worker非0在 `2b5fcbc→2b5fce8` 只记录Failure，`2b5fcfc` 回正常尾部；原worker随后可自然完成真实句柄（`2dcb9c0..2dcba04`）。**因此不能实现时可返回原有590005失败使其自然收尾，不能把失败改为成功，更不能伪造父屏障完成**。没有reply则worker仍在原同步helper等12B，父单任务屏障不结束（`2dec0ec..2dec100/2de70a8..2de7320/2b681e4`）。

## 5. 最小软件合同与宿主导出规范

只白名单本次完整28B与目标92840747；拒绝不同头/长度/保留字段、enum0或其他h/v组合、非零osdRev和未绑定source。捕获source81cf61c0仅用于本次证据，集成必须绑定实际请求的source/lease，不能长期写死。先保留请求身份、generation与f02e等价队列项；**独立consumer**消费后安装并读回control3和三个独立属性，提交applied generation，才由OSAL原分配器构造12B **`0d2019110c00018000000000`**，source metadata92840747，目的为该请求原source，发送接受只记录一次完成。分配/发送失败不提交成功；只回收自有未发送reply，request所有权沿现有拦截器合同，不复制CP指针/句柄或发worker token。原业务顺序依据 `5f497c/607514..607648/6073b8/1aef1c`；事务性规则是软件建议。

软件控制可以不改framebuffer原始字节；**必须给导出/显示和注入者明确坐标域**：

1. **逻辑framebuffer导出**：原AP/GPE bytes保持原样，输出元数据 `hrev1/vrev1/osdRev0/control3/generation`，图像标为logical framebuffer。此输出本身不声称模拟物理面板扫描，因此不需要无依据地将单个OSD dump旋转。原低层路径的非像素状态保存依据 `60f8b4/1c35c4/5e6074`；原多plane/scanout缺口仍按0147审计保留。
2. **明确定义的软件virtual-scan-grid视图**：可把软件面板安装基准显式定义为identity，完整可见plane组合完成后，再用 `T(x,y)=(W−1−x,H−1−y)`；640×480即 `(639−x,479−y)`。osdRev0额外OSD变换为identity，不能再单独把OSD旋转一遍。点击该视图先用自反的T回到逻辑坐标，然后在post-InfraTp入口注入。**这是可测试的软件投影定义，不是已恢复的Sony最终plane合成算法**；有buffer/plane域不明时仅做方案1。
3. **用户面对的真实面板视图**：还需要面板固定安装/初始扫描方向的外部基准。即使h/v都是1，也不能据此断言用户应看到倒置图像；安装基准可以抵消电气扫描方向。当前没有该基准，禁止把逻辑PNG或方案2称作“原机LCD等价画面”。依据是本轮仅闭合到 `5e6058/5e6078`，最终寄存器和物理安装未证实。

与 [A7C2参考副本](../../../menu-repair-01/success-cases/display-reuse/supplemental-source/runtime/analysis/device-models/vdf-device.c) 的165..226行比较：共同点是virtual panel config、osd0、control=`2*h+v`、1119/status0、显式hardware0/pixels0；FX3原地址和独立TP路径本轮重新核对，不能复用A7C2的VA。**差异**是参考接受任意h/v布尔组合，本合同只接受本次enum2捕获；参考在一个dispatch里直接消费状态，本合同要求能观察的独立consumer与applied读回。二者都不构成物理显示验收。

如果目标必须立即获得**原机多plane/真实面板等价**，本轮证据不足以诚实完成：保留pending继续审计，或回590005交由原worker正常失败收尾。可先交付logical framebuffer诊断图并标方向元数据；不能为得到菜单截图擅自改AP enum、强制identity、双重翻转或通知父屏障。

## 未证实项与本轮验收边界

未证实：参数243的具体有效Backup映射/模板默认及真实机身上电状态；最终面板扫描寄存器/安装基准；完整OSD/YUV合成和当前scanout绑定；全局AP绘图方向规则；raw触摸输入结构/实际校准单位/TP消息已消费；新软件consumer实际集成、1119消费、boot notify、菜单可见与输入可操作。各项对应上文VA链的停止点，proof的 `unproven` 同步列出；脚本通过不关闭这些运行/实机门槛。

本轮联网核对 [Capstone官方Python接口](https://www.capstone-engine.org/lang_python.html)（2026-11-01），仅支持反汇编API使用；Sony私有语义全部来自本地固定原件VA。未用相近机型、通用触屏反向经验或网页推断填补物理证据。
