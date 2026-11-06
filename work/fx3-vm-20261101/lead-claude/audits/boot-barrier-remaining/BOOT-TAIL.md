# 四任务屏障之后：panel单任务、boot事件与AP80c异常

后续AP81已用精确硬件不可用合同越过本篇SKD异常，健康运行并产生黑色首清屏；新的option6/IMAGING pin缺口见[AP81续查](AP81-PIN.md)。本文固定保留AP80b2/AP80c的原始结论。

**启动等待链已经实证解除，当前阻断已转到后续SKD异常。** AP80c 的真实0119消费、panel自然完成handle4、原单句柄匹配返回0、同一boot事件置位/notify、AppFw协作等待返回和外层继续均存在（serial23246–23274）。随后23332出现external abort，异常任务为SeqQueueNetwork、PC按映射落到libInfraSKD+63fc0（23398、25015）；本轮仍是失败运行、menu_verified=false。不能把QEMU退出0或本审计PASS当作guest健康。

本续查只读原件、既有运行文件和软件后端源码；仅写本目录。未启动QEMU、未拿运行锁、未读guest实时内存、未改runtime/STATE、未操作设备。原四任务结论保留在[README](README.md)和[boot-barrier-proof.json](boot-barrier-proof.json)；新增[audit_boot_tail.py](audit_boot_tail.py)重建[boot-tail-proof.json](boot-tail-proof.json)。下文AP80b2=`runtime/runs/ap80b2digital-bd9672cf/serial.log`，AP80c=`ap80cpanel-5dd371e5/serial.log`；均按原始LF计行，保留NUL。VA为image VA。

## 1. AP80c的正向完成证据

本轮sequence=`7fa8184180`、event=`7f62c2b3e8`、cv=`7f62c2b3f0`。8247/8249已将构造器保存的事件与AppFw等待的future绑定为同一对象（原保存点`2c20d20`、原等待`285e42c`）。完成链如下：

| 阶段 | 原serial行 | 可复核的字段/原VA |
|---|---|---|
| 单任务等待入口 | 23214 | `2b63718`，TID327，x0=sequence、w1=**4** |
| 实际panel enum | 23215 | TID324，同sequence，enum2；业务入口`2b5fc68` |
| consumer先应用控制 | 23246 | generation1、transaction108、control3、osd0；logical framebuffer unchanged、hardware0 |
| 精确1119发送 | 23247/23248 | 回本次source81cf61c0，12B、lease108、status0 |
| 原接收/释放完成 | 23250/23251 | 原free result0；generation1/transaction108消费 |
| 原任务自然完成 | 23253 | `2b634dc`，TID324，x0同sequence、w1=**4** |
| 单句柄正常返回 | 23254 | `2b637d4`，w0=0、w26=4、[FP+5c]=4 |
| boot主体已返回 | 23256/23257 | `2b68374`，同sequence取出同event |
| 原signal调用 | 23258–23261 | `2b6838c→2aa1668`，caller=`2b68390`，同event |
| 置位并通知同cv | 23262/23263 | `2aa16ac`，cv=event+8、donebyte=1 |
| AppFw原wait返回 | 23270 | TID289，caller=`2aa23a8`，同event/cv、donebyte=1 |
| 外层继续 | 23273/23274 | `285e430`，同event；此时原wait已清donebyte为0 |

这里的内部完成字节严格是handle4的 **`04000000`**，由原worker回调投递；1119是独立服务协议，不能替代该4B队列记录。回包与控制含义沿用[enum2审计](../panel-reverse-enum2/README.md)：完整请求为

```text
0d2019011c0001800101000000000000000000000000000000000000
```

成功回复为

```text
0d2019110c00018000000000
```

完成的是虚拟面板控制 `{hrev1,vrev1,osdRev0,control3}`，没有改AP framebuffer字节，不声称最终物理扫描/多plane等价；TP的方向只是该profile元数据，原libObj消费仍未证实。依据：AP80c23246/23248、部署v36源`fx3-capid-v36.c:504–515`；CP`60751e..607542/1e54fc..1e5534`。

**`run_i`是void函数。** 23256记录的original_result/x0=0只是一份返回现场，不能作为它的业务成功码；原函数名字符串与调用者无返回值判定说明这一点（`2b638f4`、`2b68370..838c`）。本次正常路径的依据是前面的真实服务完成、真实句柄匹配及后续原事件链，而不是这个0。

## 2. 单句柄屏障的准确合同

原父流程 `2b680bc`从GOT **`47c5b68→2b5fc68`** 取得panel业务入口，`2b680c0`派发，`2b680c4`保存返回句柄到w24。中间原调用按ABI保留w24；`2b681dc`复制到w1，`2b681e4→2b63718`等待它。脚本直接读GOT并固定这些原指令，不把worker函数VA、UIPC source或旧TLS字段当句柄。

`2b63718`与前四任务屏障共享sequence内部的完成deque，不是另一个服务：

| 字段/动作 | 原VA与精确语义 |
|---|---|
| 入口 | x0=sequence、w1=expected；`2b6373c/740`保存x19/w26 |
| 队列/同步 | deque=sequence+a8，front=b8、end=d8，mutex=f8，condition_variable=128；空队列在`2b63798`等待 |
| 取完成 | `2b637a4/a8`读LE32并存[FP+5c]，`2b637b0`pop |
| 特殊退出 | token **0x2000**（LE32=`00200000`）在`2b637c8..7d0`返回w0=1，不是完成 |
| 匹配 | `2b637ec`比较token与w26；匹配则`2b6380c`回收到free deque+28，`2b63828`置w0=0 |
| 返回观测 | **`2b637d4`在恢复callee-saved之前**，可同时读w0、x19、w26、[FP+5c]；最终ret=`2b637e8`时x19/w26/FP已恢复 |
| 无free句柄 | 派发`2b6329c`返回 **0x1000**（不是十进制1000），不得视为真实任务 |

不匹配走诊断/错误路径（`2b63830..8b4`），不能把“函数最终可能继续”当精确匹配通过。父在`2b681e8`没有检查await的w0便走共同返回，所以**仅观察boot notify也无法排除0x2000特殊退出**。0119真失败同样只被panel业务记录后自然返回（`2b5fcbc→2b5fce8→2b5fcd4`）；“任务完成”和“面板设置成功”是两项判据。

### 避免旧TLS句柄误认

AP80b2的panel入口13997打印`completion_handle=1`，不能由此认定新panel句柄是1。gate v7在完成函数入口才更新线程局部completion字段，panel入口只是复用了该worker前一任务的值（v7源18–22、49行）。该历史轮没有记录新的派发返回/单await，故它的新句柄保持未证实。AP80c新探针23214直接证明等待4，23253/23254再证明真实完成/匹配4。

## 3. AP80b2三层等待现已分清

在历史AP80b2，sequence=`7f7c182da0`、event=`7f3d3743e8`、cv=`7f3d3743f0`。8775把event交给该sequence，8777把相同event/cv交给model_future；8779的实际condition wait caller是 **`2aa23a8`**，关闭了先前“简单等待还是协作等待”的分支缺证：实际走`2aa239c..23a4`的协作分支，等待的仍是这个event的cv。

| 层次 | 历史AP80b2观察 | 原代码与证据强度 |
|---|---|---|
| panel worker TID324 | 14011发0119，14097开始原收包；19357/32914/46245为ioctl接收等待 | 用户栈14001–14009到`2b5fcb8`，A：确在该0119同步链 |
| boot父TID327 | 19536/33093/46423 futex=`7f7c182ef0` | 等于sequence+128+28，吻合内部完成cv；B：没有该时刻用户栈，不能把地址拟合冒称直接PC捕获 |
| AppFw TID289 | 8779明确event cv等待；17342/30894/44225 futex=`7f3d374418` | 等于event+8+28，与原pthread首次group字段吻合；A：event绑定和wait caller直接捕获，futex字段拟合另存 |

原pthread `d50c/d548..d558`选择group并形成cv+28+4*g，`d5ec`执行futex syscall；本次捕获使用group0。futex值/地址不能解释为“某线程持有互斥锁”。协作分支在event wait返回后还可能经`2aa2464`等待线程调度cv，最终共用`2aa2298`清事件（原`2aa23a8..2518`）。因此只钉简单分支的调用后PC会漏掉真实wait返回；原wait wrapper记录caller/event/cv更直接。

脚本将本轮**全部45条**已发布RAM记录与serial逐值比对，SHA256=`79bc0aa68127b9b28360d36d021b37859a097f8f2ae44181a7404d0a09af3e0b`，overflow0。其中记录4/5（文件偏移4300/43c0）分别对应8775/8777事件传递，记录43（6040）对应13997 enum2入口。它是既有探针的另一保存路径，不是第二次独立执行，也不是本次实时RAM读取。AP80c早停没有宿主最终RAM二进制，本续查对它只使用串口和部署清单，**不把23255的QMP_SNAPSHOT guest marker当成宿主物理读回成功**。

## 4. v36/v9配对、软件完成与观察器寿命

本审计只读核对运行链已经构建/运行的版本：capid v36、gate v9。v36源码SHA256=`4637705441ed07d50262a73faaab9032df317f02cc5e9a3bd8fa9d6c5c281e0c`，ELF=`1c8f5d9daefbc1be0a10ad54ca142ba23d8877744a6bd039e7e0e2e2623df9f3`；v9源码=`73d6bda5b7c870e5512cda693929ea39426294c65a764022423df3929ffa091e`，ELF=`6453fe24de31fdaa47b0f5bbc55f5c6fd324b1f88c1192c534f4d903eee617f9`。run的CPIO成员对应这两个ELF；v9的48个预期原指令与原appFw一致，serial5247/5248的寄存器/分支自检与绑定通过。

v36的准入还需要 **`fx3_observed_reverse_context`** 返回enum2、本线程TID、非零sequence；v7只有enum接口，没有该context导出。脚本读源码和真实dynsym核对版本接口，防止将v36搭旧v7后不回复误归因于panel服务。v9明确增加了单await入口/返回点；v7只有46点。原fixture `panel-config-host-check.json`退出0、source SHA吻合，覆盖精确包、generation、consumer先于分配/回复、回滚及重复/外国线程free；**它是已有宿主桩检查，本审计未重跑，也不当guest证据**。实际guest消费依据AP80c23250/23251。

v36先enqueue/consume/readback控制，再分配和发送1119；发送失败恢复virtual state并回收自身reply（`fx3-capid-v36.c:509–515`）。`tp_axes_reversed=1`是控制元数据，原日志同时标`tp_native_consumption_unproven=1`；该consumer不调用libObj TP setter。不能把它说成原触摸已接通或另做一次像素180°旋转。

**boot事件的证据寿命截止首次285e430。** 原cv在`285e434`析构，事件属于AppFw栈。AP80c23273是本次boot返回；23323的后续旧绑定样本打印byte136，不能当这个boot事件第二次变更。随后相同栈地址即使被新future复用，也缺少新对象身份绑定，不能沿用boot标签。新脚本保留这些原记录，但将`line>23273`的同event记录排除在boot通过判据之外。建议运行观察器在该外层返回后撤销本次event绑定；本审计没有修改观察器，也没有将这项归因问题称为SKD异常的原因。

## 5. 后续失败的可确认边界

AP80c原计划240秒，因新增异常在105.13秒停止并正常回收QEMU；receipt的qemu_exit0/process_reaped/inputs_unchanged不代表guest通过。原serial **23332** 是external abort；23398给PC=`7fb6084fc0`，9629映射的SKD基址=`7fb6021000`，相减为 **63fc0**。25015标明SeqQueueNetwork、TID332，25020为signal7。此处行号按LF，可能不同于使用其他控制字符分行的既有报告。

访问VA=`7fb79b88eb`落在9780的`/dev/mem`映射`7fb79b8000..9000`、offset=`ffffb000`；2093也记录了该映射调用。由页内偏移8eb计算物理访问 **ffffb8eb**。这是映射推导，不是已解出的私有寄存器含义；dlopen handle也不是这个库的映射基址。

原文件`libInfraSKD.so` SHA256=`7d1fbd9a53794def916ca3ff2fc3a00f295268bb0f4ea7c07d0e8356d2840f9b`。文件同VA63fc0的24B为

```text
09e0d9c6be5d5dbe8d447907d555b57d2fc5b333f447bf43
```

Capstone从该原文件地址未解出有效首条A64指令；**不能把文件邻近偶然译码当作guest异常指令**。需要装载/解码后的代码证据才能继续确认确切load、寄存器与服务含义。此缺口由运行链另行审计SKD处理；本续查不填假设备数据、不跳过网络/安全调用，也不改原程序。

## 重建与验收边界

在项目根执行：

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/boot-barrier-remaining/audit_boot_tail.py
```

退出0重建proof：36处AP/CP锚点、panel GOT/句柄流、pthread原字节、v7/v9的46+48个原指令、AP80b2全部45条RAM/serial与六组futex地址拟合，以及AP80c六项启动链通过、guest异常、menu=false。`--run <已有已回收run名>`可换一轮只读评估，不启动或附加guest；默认固定AP80c，AP80b2参考始终保留。

审计PASS表示字节、对象身份与既有记录一致；本例输出同时保留`guest=FAILED_GUEST_EXCEPTION`。未关闭：SKD异常根因/修复、240秒健康运行、后续AppFw出队/真实GPE绘制、scanout/菜单图像与输入、原TP消费及实体设备效果。四任务、panel单任务和boot事件等待已由各自正向证据闭合，不再列为当前缺少的协议回复。
