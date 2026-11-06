# PowerOnFinished：事件键需1026→102d，局部字节合同已闭合

2026-11-03。**固定FX3 PowerOnFinished的12字节输入，可在已定位的回调边界把首字0x1026转换为0x102d、保持其余8字节不变，交给FX6原回调；这能在已注册且有效的FX6 PowerOn等待上下文中保持原对象更新和通知行为。** 原码已经给出双方producer、等待键、匹配回显、结果码、promise/future生命周期；不再把它们统称unknown。未转换直传时，FX6 PowerOn注册的是102d，原1026不能匹配该项，故不能通知这个等待者；若1026另有并发项，更不能假设安全忽略。

仅交付离线模型，不是可装入firmware，不是完整mpr::Init adapter通过，也没有运行到PowerOn的实测。当前运行已知仍停在更早发送断言，不能把本项静态问题说成当次已发生死锁。只写本目录，固定AP/MPR/helper、callback-contracts旧报告及平台全部保持。

## 复核入口

- [receipt.json](receipt.json)：固定SHA、所有原指令VA→fileoff/机器字、旧报告完整性、产物哈希、RTTI字符串及结果表原字。
- [vtables.json](vtables.json)、[resolved-relocations.json](resolved-relocations.json)：实际GOT重定位、虚表成员与通知目标；不是相邻符号猜测。
- [offline.py](offline.py)、[test_offline.py](test_offline.py)、[offline-receipt.json](offline-receipt.json)：严格12B转换和有界状态模型；事件常量从固定二进制MOVZ解码，四组echo操作数为符号化测试值，**不是运行捕获包**。
- 原码片段按二进制名和入口VA命名；反汇编显示`Application_System_Init+...`只是strip后最近符号标签，不据此命名私有函数。

## 双方输入合同：首字是事件键，+4不是结果码

| 项 | FX3原MPR | FX6供体MPR/原AP |
|---|---|---|
| PowerOn API | b58f4 | 12a19c |
| PowerOnMain | b55f8..b5628 | 129ec0..129ef0 |
| payload大小 | 12，b5600 | 12，129ec8 |
| +0 u32 | 1026，b55fc `528204c3` | 102d，129ec4 `528205a3` |
| +4 u32 | context+15d0，b5608 | context+15e0，129ed0 |
| +8 u32 | 原STR WZR，b5618 `b9001bbf` | 原STR WZR，129ee0 `b9001bbf` |
| AP等待注册 | 2e779a4=1026 | 2144678=102d |
| AP回调 | 2e6d1dc | 213c064 |

PowerOn API读取其输入+4，FX3 b594c→b5950写到局部context+15d0，FX6 12a1f4→12a1f8写context+15e0；请求AP又分别在2e779d0/21446a4将其调用者输入[0]复制到该API输入+4。最终AP在2e77ac4/2144724读回对象+3e4，与原调用者输入[0]比较。故+4是**必须逐位保留的请求回显值**；无需猜测其业务枚举，不能改为固定0，也不能把它当成功状态。

+8在这两条完整PowerOnMain函数中恒由原码写0，随后成为对象+8并经AP结果表转换；FX6表0x2622138[0]=0，FX3表0x39899b0[0]=0。一般结果转换域不同：FX3≤11查12字节表、否则2；FX6≤17查18字节表、否则205。**因此本原型只接受此producer确实生成的result=0；未知非零结果直接拒绝，绝不改零。** 这与人为伪造成功不同：只保留已有输入0，并验证原producer写零的机器字。

## FX3从请求到分配、排队、实际回调、释放

1. b5958从GOT 2fade0取PowerOnMain（重定位明确符号/VA b55f8），context+15d8保存它；b5964将context交0x942d0。常规队列分支94378/37c复制回显+15d0，94380/384复制回调+15d8；队列条目尺寸15e0。完整广播消费片段946e8..94898中x22指向队列条目，94828加载[x22+15d8]，94830 x0=x22，94834 BLR。原码连接了回调指针来源和实参，不仅是邻近常量。
2. PowerOnMain在栈+10构造{1026,echo,0}，b561c SetIssueEvent(event,stack,12)。SetIssueEvent b4168..417c设置kind=1并调用SetEventParam。
3. SetEventParam b3f70..b3f8c执行malloc(12)，x23保存返回p，memcpy(p,stack,12)；b3fc0/3fc4把{kind,event,p}写入队列，b3fdc signal。扩容分支b40bc/40c0写同样三字段。栈payload与heap p严格区分。
4. GetEventParam b42e8/b42ec取kind/event/p，b42f0/f4/b4300分别输出，推进队列。GetIssueEvent b4420调用它；IntegEventMain b5290/b5294从输出槽装event和**同一p**，b5298调用SendIssueEvent。
5. SendIssueEvent b4440保存p到x19；1026分支b4b70通过GOT2f9ce0取得gp_evtPowerOnFinishedFunc存储地址，b4b74取函数指针，b4b78空保护；b4b88重新读回调，b4b8c x0=p，b4b90 BLR；回调返回后b4488 x0=p、b4494 free(p)。复制到诊断消息的0xb3a78不会更换原p。由分配到释放的身份链已闭合，运行是否实际走到这条链仍未观测。

未来桥接只能在这个**语义明确的PowerOn回调边界**制作12B临时副本，改副本首字后调用FX6原回调；不能全局把所有1026事件改102d，更不能对全部枚举统一加7。原p的释放仍属于FX3 dispatcher，FX6回调没有取得其所有权。此处只是适配设计，没有生成可运行桥接代码。

## AP查找、更新和通知：对象首字段不是虚表

FX3表全局0x968b120，FX6表全局0x5c3e888。2e57a90/212d524是按u32键取模bucket并比较node+8键的计数/存在性查询，不是根据编号返回设备对象。node结构可见next+0/key+8/value pointer+10；2e6c7a0/213b870寻找节点并返回node+10地址，不存在时可能插入零value（原回调前面的count在同锁范围内避免正常缺项进入此路径）。

原回调持锁：FX3锁0x968ba80，FX6锁0x5c3f478。以payload+0查count，0则直接解锁，无通知；有项则取node.value指向结果记录R，按以下顺序执行：

1. R+3e4 ← payload+4；R+8 ← payload+8，两代偏移完全相同。
2. 读取R+0得到promise记录P的指针，调用2e58088/212e994，把P的三个qword移到局部24B记录L，原P三个qword清零。**R[0]是promise指针，不是虚表地址，也没有在这里BLR其首项。**
3. 调用2bcce64/1d6d134通知L：经pthread_once和`__once_proxy`安装Result<void>，随后对shared-state+10原子交换ready=1，必要时futex notify。若未完成一次安装，原码抛future_error(2)；不吞重复完成错误。
4. 调用2bcd130/1ca0738销毁移出记录L，清理Result与shared_ptr引用，然后解锁。不存在保存payload原指针的操作；只拷贝两个u32并移出已有promise。

## 结果记录与真正虚表的生命周期

请求函数FX3 2e77910附近/FX6 21445fc先在栈上构造promise并获取future，清零结果记录R（FX3 0x520、FX6 0x3500），R[0]写promise地址；在锁内以1026/102d插入{key,&R}。FX6 213cfbc分配24B map节点；重复键会删除新节点并返回insert=false，**请求端未检查此标志，因此并发重复同key不是已证安全条件**。

请求随后调用原mpr::PowerOn、在future上等待：FX6 21446d8→2114c04→1d6d0a8。通知后读取R+8并用原FX6结果表转换；再比较R+3e4与原echo，不同则写0xbd（FX3对应0xb6），所以转换必须保留这个失败分支。然后2144744按key erase；21417f4只delete map节点，不delete栈上R；最后释放future引用、析构原promise，函数退栈才结束R生命周期。

两代构造函数2bccdc8/1ca03a8均分配48B shared-state控制块和16B `_Result<void>`。RTTI原字符串明确为`std::__future_base::_State_baseV2`与`_Result<void>`，不是业务结果类猜测：

| 实际虚表地址点 | FX3 | FX6 | 已核对成员 |
|---|---|---|---|
| shared state | 46e8ac8 | 2ec3168 | +10：2bccb0c / 1ca0144，均RET；等待前的virtual complete_async钩子无动作 |
| Result<void> | 46e8af8 | 2ec3198 | +0：2bccb18 / 1ca0150，间接转+10；+10：2bccb7c / 1ca01e4，删除16B结果 |
| shared control | 46e8b58 | 2ec3240 | +10：2bccba4 / 1ca0210，销毁内嵌state；+18：2bccb5c / 1ca020c，释放控制块 |

GOT、RELA原始24字节、VA和fileoff均见vtables.json；FX6 state实际是控制块+10，所以等待函数从state[0]再取虚表+10，目标是上表RET，而不是PowerOn业务虚方法。通知内部的`std::function`也已定位：FX6 GOT2ee6960→1ca07b4执行安装器，GOT2eeab68→1ca0988移出L+10 Result；2ee9c50→1ca015c为管理器；`__once_proxy`是外部符号，实际绑定未运行读回。FX3对应地址见fx3_ap-notification-relocs.json（本目录）。

## 离线原型与验收界限

`python3 test_offline.py`已通过：从b55fc/129ec4/2144678 MOVZ解码源/目标事件键，从STR WZR验证result原码0；四组符号echo验证转换后的12B与FX6 producer布局逐字节相等，原echo/result保持；原1026直传、错误事件、非零结果、负数位型、错误长度、可变buffer、重复通知和无等待键均拒绝。原始echo不匹配时模型仍给0xbd，没有把失败变成功。

模型只处理字节与显式状态字典，不执行ELF，不分配原生promise、不触碰文件镜像；不证明线程调度、实际allocator、外部C++绑定或广播队列已经运行。状态模型里的pending是测试前置条件，不是给真实程序写initialized。没有真实payload捕获，因此测试正反例准确标作**原指令导出的符号化fixture**。

## 尚需的精确观测点

本次局部合同不是“全部unknown”：键错位、12B布局、echo原样往返、result0、对象字段、promise搬移/通知/释放、待者校验和节点删除已有原码。仍不允许真实adapter集成的条件是：

- 在未来授权运行中确认FX3 b4b90确实调用到上层桥接/FX6 213c064，读取12B原p及当时事件键；当前首个发送断言没有这些证据。
- 读取FX6 global5c3e888的102d节点及value=&R、R[0]=P，验证请求线程21446d8等待与回调发生在R退栈前，且无重复key。观测点214468c注册后、213c090 count后、213c0c8搬移前、2144744 erase前。
- 外部pthread_once/__once_proxy与futex实际绑定、异常路径保留需集成验证；本次只解析固定ELF重定位。不能将这个门槛补成固定返回0。
- 更早的mpr::Init完整ABI、其他启动必需合同仍沿父报告未决；本次不扩大录制回调，也不以此宣称FX6在FX3平台启动成功。

固定FX3 kernel/DTB/17helpers/QEMU/env/seed/CPIO保持；只建议未来FX6上层在PowerOn callback边界做条件明确的局部转换。
