# boot 尾段：0328、digital level、0119 的完成语义

结论：三项均可在明确的软件配置内建立诚实的完成条件，但不能把“收到请求”统一当成功。**0328 是保存系统提示音 path 的控制完成；digital op3 是通知控制的同步 callback 返回，禁用传感器时原代码允许成功且不产生样本；0119 必须由软件 orientation consumer 先安装显示/输入变换，再回复。** AP enum0 确实编码为 `hrev/vrev/osdRev=0/0/0`，所以捕获并确认 enum0 后，可在完成 identity 状态提交后回成功；**本轮没有证据证明实际 boot 输入一定为0**。依据：CP `185860..1858a6`、`5ad926..5ad9a6`、`4c8da4..4c8e38`、`607242..607654`；AP `2dec070..2dec128`，自动提取见 proof。

失败后果不同：0328 的非0本地状态致命；digital 的非0本地状态同样致命，但这份 AP wrapper **读的是输入槽+16，回复中的失败状态本身被漏读**；0119 失败仅日志后返回，原 worker 仍能自然完成。三者没有回复都会留下无限等待；不能伪造内部 worker token/notify。依据：AP `2b67aa8/2b67ce4..2b67d8c`、`2df2fc0/2b67b34/2b67e14..2b67ebc`、`2b5fcbc..2b5fcfc`、`2de72fc..2de7314`。

仅写本目录三文件；原 AP/CP、runtime、STATE、运行锁、QEMU、相机和 Git 均未改动或操作。[audit_boot_deferred.py](audit_boot_deferred.py) 固定两份输入 SHA256，保存68段原字节/Capstone 反汇编，断言64处关键指令，并自动读回 dispatch/vtable/六种 orientation。完整证据在 [boot-deferred-proof.json](boot-deferred-proof.json)。AP 为 ELF VA；CP Thumb VA=文件偏移+`108000`。长 Thumb 区间可含 literal/TBB 数据，proof 已标明；控制流结论用独立锚点和真实表绑定，不采用数据的偶然译码。

## 0328：原链不等声音播放完成

1. AP `2b67a88..2b67aa0` 将 `sequence+1e4/+1ec` 交 `2dee6f0`。若第二参数0，path=0；为1且第一参数0..2，path=3；为1且第一参数3，path=1。构造10B `200d/0328/10/8001`，+8 path、+9零；`2dee798` 同步等12B，`2dee79c..2dee7a0` 转换 reply+8 状态。CP `1b1a8c..1b1b0c` 构造旧 `2004/0202/12/1`，body首byte=`path&7`，发往 `9058003f`。
2. ADF dispatcher `1853bc..185426` 用 `cmd-0201` 索引 `1853d0` 的TBB；0202槽落 `1853ec`，取得 `5ad9b4` singleton，再由 `1853f6` 尾调 **`185860`**。它读消息+10hex的 path，调用 `5ad926`，随后**同一次调用中**将返回值0转status0，任何非0转 `e002`，调用 `1858e4` 发送8202；不存在等待后续播放事件的分支（`18588a..1858a2`）。
3. `5ad926` 维护 singleton+4 的完整 path。path=0 且旧path非0，会调用 `5adb70/5aea42`，可能挂控制回调或调用 `18580c`；0→非0 时可能经 `45df60` 的接口投递控制127；非0但低三位全零返回 `e002`。正常分支在 `5ad99c..5ad99e` 返回0并保存新path。**副作用不等于物理静音/扬声器路由验收**：这些分支没有把8202延后到播放、DMA或DAC事件；其调用结果也没有作为另一 completion 状态等待（`5ad934..5ad99e`、`18580c..185848`、`185892..18589e`）。
4. `1858e4..185968` 构造旧 `2004/8202/12/1`，status32位于+8，按原请求sender路由；`5bbaa4..5bbb8c` 分配本地消息、复制、设置source metadata、发送，发送失败释放自身分配。BB `1adc88..1adc8e/1adcde` 将旧状态 OR `580000`，`5ca218..5ca268` 原样复制到 AP1328 的+8；`1aef1c..1aefa4` 按原事务查回接收者，source metadata=`92840747`，不是写死某次 `81cf61c*`。

| 状态 | 旧CP精确完成 | AP精确完成（OSAL payload） | AP结果 |
|---|---|---|---|
| setter接受0 | `042002820c00010000000000` | **`0d2028130c00018000005800`** | `580000→0`，`2de45b0..2de46cc` |
| setter错误e002 | `042002820c00010002e00000` | `0d2028130c00018002e05800` | `58e002→7b`，`2de45d8..2de45e8`；父进入致命路径 |

两种状态字节由 `1858ea..18591a`、`1adc88..1adcde`、`5ca236..5ca258` 得出。经 `path&7` 后，boot合法0/1/3不会触发“非0且低三位全0”这一错误；不能凭此把任意 wire/pad、非法path或未实现音频播放一概成功。

**最小静音合同**：只准入目的92840747、10B完整头、path0/1/3与零pad；保存 `system_sound_path`，与既有注册表、音量和 backing 生命周期同属静音profile；保持 `playback_enabled=false`，不产生音频、不启用实体输出。只有保存成功、原事务/source绑定有效且reply发送接受，才提交一次1328；分配/发送失败不得提交成功。这里的“path设置成功”指软件静音sink的逻辑控制，符合原 setter 完成层级；不要求等待本模型不存在的声音播放事件（原完成层级依据 `18588e..18589e`、`5ad99e`）。这是对 [静音后端既定选择](../adf-032e-033d/README.md) 和 [只保存注册描述符的先例](../adf-beep-regist/README.md) 的续接，不扩大到原厂音频功能。

## digital level op3：callback 返回后的自动传输完成

**没有200d头、没有另一条reply opcode。** AP `2df2f60..2df2fbc` 清零24B，true→op32=3（false→4），发往 `912f0335`，同步期待24B。CP `4c897a..4c8988` 注册 callback `4c8ee0` 与 context `01197a48`；`4c8ee0..4c8f06` 把原payload与context交 `145330`。TBB `14534e` 的op3和op4槽均落到 `14535a→4c8da4`，返回值经 `1454a6` 写回**原payload+16**，然后返回。

原状态和硬件依赖如下（`4c8db6..4c8e38`）：

| CP对象状态 | 行为 | payload+16 |
|---|---|---|
| +0==2 且 +4==0 | `4c8dbe→4c8e00`，记录未启用，不向sensor发送；没有取角度/加速度 | **0** |
| +0!=2 | `4c8dea..4c8dfe`，本地状态不合 | **2** |
| +0==2 且 +4!=0 | 构造20B op3/4，发往 `90a3035b`；分配/发送失败→2，发送接受→0 | **0或2** |

启用分支的 `4c8e60..4c8ec6` 只分配、复制20B并send，无sensor回复接收；发送失败释放本地消息并返回2。成功后还可能向对象+d8提供的接收者发控制消息（`4c8e18..4c8e34`），本路径仍不等待角度样本。因此这里的0是**通知控制接受**，不是“IMU已经测得水平”；不需要且不应填造角度数据。

自动回复不是 `4c8ee0` 里面再次调用send。完整生命周期是：

1. OSAL callback注册 `49ef00` 将包装器 `a874e3` 存入记录+8，callback/context存+14hex/+18hex（`49ef74..49ef84`）。同步分派 `49f368..49f598` 从注册记录调用该包装器；`a874e2..a8750c` 解锁，传入 `envelope+18hex` 的payload及记录context，调用原callback，再加锁，返回0。callback错误由业务payload+16承载，包装器返回0本身不能代表业务成功。
2. 跨芯片接收器 `4a5c30..4a5c78` 从传输头分别取payload长度@+8、destination@+12、原source/返回路由@+16；对端发送器在 `4a5024..4a503c` 从 `a878d8` 取得metadata source并写入该+16字段。`4a5d72..4a5d8a` 申请本地副本，并通过 `a878d2` 把原source存入 `payload-12` metadata。
3. **原返回路由非0**时，`4a5ed4..4a5ee8` 进入 `a878ca→49f368` 的同步callback路径；callback返回后，`4a6018..4a602a` 保存OSAL分派结果到传输头+20，`4a602e..4a6030` 把修改后的本地payload复制回原传输payload，`4a6034..4a6078→a89f96` 提交传输复制/完成。`4a6080..4a6084` 最后用原destination释放本地消息；原共享事务在 `4a614c..4a6222` 更新消费/完成信息。这里复用的是原请求的传输事务与返回路由，不另造业务opcode，也不把 callback 的返回0充作样本。
4. 返回路由为0的分支用 `49f140` 异步发送（`4a5f30..4a5f3a`）；它不走上述同步payload回拷。AP公共helper先建立动态source、设置请求source再发送并接收（`2de70a8..2de7320`），所以软件后端必须绑定**本次原source**，不能把两个分支混用。

| 业务状态 | 精确24B OSAL payload |
|---|---|
| op3、成功0 | **`030000000000000000000000000000000000000000000000`** |
| op3、失败2 | `030000000000000000000000000000000200000000000000` |

字段依据是 AP清零构造 `2df2f88..2df2fb8`、CP原消息状态写 `1454a6`；不包含角度样本。VM拦截器若直接建立OSAL reply，应独立分配24B，保留op3及零body，把metadata source设为 `912f0335`，目的设本次原source；发送失败只释放自己分配的reply，不释放调用者request、不复制CP指针/句柄，也不能再发一条重复完成。这是替代缺失CP传输的模型实现选择；原CP机制是上述事务回拷。

**最小无IMU合同**：明确建立 `service_state=2, sensor_enabled=false`，保存 `notify_requested=true` 的shadow，计数 `samples_emitted=0`；仅接受24B `LE32(3)+20B零`。状态提交后，按原source返回上表成功0。原不启用分支就是立即返回0，因此不需要模拟90a3035b或等待硬件事件（`4c8dbe/4c8e00`）。其他op/非零body、未ready的服务、需要实际样本的请求拒绝；不要通过AP漏读状态来假称IMU存在。

**AP失败细节**：`2df2fa4` 输入在FP+40hex，回复槽在FP+58hex；但 `2df2fc0` 读取 **FP+50hex，即输入+16**，恒为此前清零值。转换表在 `3963ac8`，`2df303c` 写out，父 `2b67b34` 本地非0转致命 `2b67e14→2b66ba8→2b63bf0→2b63c08`（致命处理`2ebf3b0`）。因此**仅回业务status2并不会使这份AP的本地out变非0**，不是一个可靠失败控制手段；helper的分配/发送/接收异常仍有自身assert处理，且没有reply会一直等（`2de70a8..2de7320`）。本审计没有修补该AP行为，也不把它作为成功准入依据。

## 0119：谁消费 f02e，以及何时1101→1119

AP `2b5fca4..2b5fcb4` 从 `sequence+304` 读enum，`2dec02c` 构造 **28B** `200d/0119/28/8001`：+8 hrev、+9 vrev、+10 osdRev，其余17B零。`3963654` 的6字节jump表和 `2dec094..2dec128` 自动提取如下；CP日志明确称hrev/vrev/osdRev（字符串 `d87811/d87828/d8783f`，加载于 `1b408a..1b40dc`）。

| AP enum | hrev/vrev/osdRev | switch目标 |
|---:|---|---|
| 0 | **0/0/0** | `2dec0b0` |
| 1 | 0/1/1 | `2dec094` |
| 2 | 1/1/0 | `2dec0a4` |
| 3 | 0/1/0 | `2dec110` |
| 4 | 1/0/1 | `2dec118` |
| 5 | 0/0/1 | `2dec124` |

enum0精确请求为 `0d2019011c0001800000000000000000000000000000000000000000`。这是**由原代码推得的候选**，尚非本轮捕获的实际包；不能据此把实际boot白名单默认为全零。

原CP完成链：

1. `1b3e74..1b4150` 将AP三个reverse字节和其他控制字段转换为旧 **2001/0101/20B/1**，发往 `9059000e`；普通boot body前3B对应h/v/osd，mode byte4清零。类 `VdfDisplayCmdSetPanelReverse` vtable=`b7e1f4`，Execute槽+14hex=`5f4911`；`5f4910..5f4986` 只把12B payload复制到 **2001/f02e/20B/1**，调用 `1e8298`，**没有在此发1101**。
2. `1e8298` 查表 `b81088`，mask1命中第一项 `(mask=9, ID=90590819)`；`1e80f4..1e81aa→611858→5bbaa4` 复制消息、保留source并发送到该设备控制队列。控制对象 `010660f0` 在 `606ff4..607030` 以ID `90590819` 构造，`5f0fd4` 保存ID至对象+8，运行入口 `606f5c..606f76` 将该对象交 `1e8cc0`。通用接收循环 `1e8d40..1e8de8` 收包并交 `610db4`；后者查command并经vtable+8分派（`610dd8..610e00`）。
3. 消费者是 **`DevPanelCmdSetPanelReverse`**，不是BB发送线程。其静态对象 `011cda18` 由 `606d92..606da4` 装入vtable `b80724`，对象表项在 `efedcc`，表getter=`606b16→efece4`。ID函数 `607232` 报 `2001/f02e`；vtable+8=`1e1ccc` 按accessor kind1/2分别调用 Activate=`607242` / Execute=`60742c`。`5f4ccc..5f4d20` 从这些ID函数建立命令匹配项，排除了“仅同名RTTI”的猜测。
4. Activate看payload+4模式（`607252..6072dc`）：0/1进入状态0并设目标帧计数=current+1；2进入状态2；3会处理已有f02e队列并设状态1；其他值立即用 **status1** 调 `6073b8`。清理被替代旧命令时也可发 **status0**（`6072e6..6073aa`、`607354..607356`），所以原status0本身也不证明真实面板翻转发生。
5. Execute=`60742c` 驱动状态0/1/2/10hex：先保存/比较帧计数（`60745e..607512`），尚未到目标时保留pending；达到后将h/v布尔值写到orientation结构（`607514..607542`，subsystem vtable+404=`60f8b5`，setter `60f8b4..60f8c4` 保存状态）。按当前输出/plane/geometry决定是否走 `1e0848` 显示控制（`607566..607626`）；随后更新osdRev相关状态并执行 `1e54e0` panel/EVF基础设施控制（`607628..60763e`）。两项非0 OR 后归一为 **5**，否则 **0**，在 **`607648→6073b8`** 发1101。
6. `6073b8..60742a` 构造旧 **2001/1101/12B/1/status32@+8**，按保留的原请求source发送。BB `1adbd4..1adcde` 加显示域590000，`1aeca0..1aed0a` **仅将590000归零**，构造AP1119/12B，其他错误保留；`1aed00→1aef1c` 回本次原source，metadata source92840747。

| 设备结果 | 旧CP完成 | AP完成 |
|---|---|---|
| 0 | `012001110c00010000000000` | **`0d2019110c00018000000000`** |
| 1（非法mode byte4） | `012001110c00010001000000` | `0d2019110c00018001005900` |
| 5（显示/infra返回非0） | `012001110c00010005000000` | `0d2019110c00018005005900` |

这些是 `6072d4..6072d8`、`607638..607648`、`6073e0..6073fa`、`1aecb0..1aecfa` 的精确值；不把通用Activate/Execute返回的流程控制值混入业务status。

**原机硬件依赖的准确边界**：原设备状态机需要CP队列被调度、帧计数到目标，活动输出分支调用 `60cc44→a5df3a`，panel/EVF控制走 `1e54e0→60daa2→60db3e`，后者会同步 `a878ca`（`60db74..60db84`）。所以在无原CP/显示driver的VM中，不能靠执行原handler就得到诚实硬件完成。另一方面，1101是在这些同步调用**返回后**发出；该片段没有再接收一个“物理LCD已扫描/画面已翻转”事件，也没有IMU读取；不能把它提升为物理显示验收。低层driver内部及帧事件生产者未完整审计，本报告不声称它们没有硬件等待（`6074ce..607648`、`60cc44..60cc98`、`1e54e0..1e5572`、`60daa2..60dba4`）。

## 640×480 软件 orientation 合同

最小实现先只允许**后续实际捕获并绑定的enum0完整28B请求**。模型维护 `desired_orientation`、`applied_orientation`、generation、原source/事务lease及一个f02e等价FIFO。接收时入队；真实软件consumer取出，确认640×480 surface及输入映射同属当前generation，安装 `hrev=vrev=osdRev=0` 的identity状态，提交 applied/generation，再单次回复1119/status0。没有物理面板或IMU时，此软件工作已经完成；**可以在保存并实际应用identity状态后完成，不必人为等待实体翻转事件**。不能只记录pending而没有consumer就发成功。原状态/完成顺序依据 `5f497c`、`607514..607542`、`607628..607648`；generation/lease/FIFO事务性是建议的软件约束，不冒称原厂字段。

如果以后支持非零orientation，至少要让所有可见plane与输入坐标一致：水平翻转采用 `x'=639-x`，垂直翻转采用 `y'=479-y`；输入从显示坐标回surface逻辑坐标用同一自反变换。尺寸仍640×480，不凭reverse改变宽高；OSD若为独立plane，必须按osdRev单独处理，不能把第三byte丢弃或一律等同整帧旋转。这是由hrev/vrev/osdRev字段和独立软件surface定义导出的模型方案（原字段 `1b409e..1b40dc`、`60751e..607548/607628..607636`）；**原多plane的osdRev最终像素语义未完全闭合，故最小白名单不放行非零模式**。proof只验证坐标变换及逆映射数学、identity入队后无reply/消费后才有reply；没有把这些Python检查算作渲染或输入运行验收。

AP `2dec0ec..2dec100` 等12B并转换reply+8；非0进入 `2b5fce8` 仅打印Failure，再跳回正常日志/返回尾部 `2b5fcd4`。因此0119真实失败**不致命**，原业务worker会自行发真实任务完成（`2dcb9c0..2dcba04`）；不回复则worker一直阻塞，父 `2b681e4` 的单句柄屏障不能结束。最小后端可对未支持的合法请求报告失败，但不可用“AP只日志”当成功证明，也不可主动发送屏障token。

## 复现、交付边界与尚未证实项

项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/boot-deferred-0119-0328-digital/audit_boot_deferred.py
```

退出0重建proof，当前输出：`PASS, instruction_checks=64, blocks=68, AP_orientation_enums=6, software_cases=9, guest_or_device_execution=false`。可用 `ap:2df2f60:f4 cp:607242:414` 等参数只读打印反汇编。输入固定哈希：AP `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`；CP `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`。

仍未证实：本次boot的0328/0119实际全包、动态source和sequence+304值；0119原低层显示driver的全部硬件完成行为、帧事件具体生产者、非零osdRev全部plane像素映射；新软件后端的实际实现/回包消费、orientation帧与输入读回、最终notify、菜单或实体相机效果。本文完成的是CP业务consumer/状态/回复传输的静态绑定与最小软件合同，不是guest验收；这些缺口不能用脚本PASS关闭。对应消费和硬件边界的VA见上文各节及proof的`unproven`。

本轮联网核对 [Capstone官方Python说明](https://www.capstone-engine.org/lang_python.html) 与 [Arm AAPCS64 2025Q1](https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst)（2026-11-01）。它们只支持反汇编API与参数ABI，Sony私有完成语义全部来自上述本地固定原件VA，不以公开相近机型实现代替FX3证据。
