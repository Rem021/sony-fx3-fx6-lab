# AP79：VDF0165与HDMI启动设置

本轮新增8条回复全部被原消费者释放；325也被消费，四任务均自然完成入队。父线程仍在四任务屏障之前的Dataflow getpin等待；屏障、boot通知、UI恢复与GPE首绘未通过。

## 回执

`ap79tail-17293cc1`，正常时钟240秒，capid v32 + gate v5。qemu_exit=0、process_reaped=True、inputs_unchanged=True、宿主PID消失=True、两锁重取=True、missing_markers=`[]`、im末次映射存活=True，fatal=0。退出0是有界QMP收尾，不是guest正常关机；存活是末次proc快照证据。

[宿主ASan/UBSan](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/boot-tail-host-check.json)通过：精确字节、590000状态域、shadow/cache次序、010a status1、0101参数、五端口原顺序、静态rate/backup7、未知backup/非法rate/重放/错source/PID/active-output拒绝，分配/发送失败回滚与所有权、先前325/timecode、8线程24000次锁。观察件45点经原字逐一核对和全寄存器NOP/CBNZ/BL客体自检。

## 新回复消费

|请求|软件状态与精确回复|本轮消费|
|---|---|---|
|0165/10B `0d2065010a0001800200`|selector2/enum0独立shadow，pending_hardware=1；`0d2065110c00018000005900`；send成功后才提交cache|lease28/free0|
|HDMI010a/12B|disconnected definition0；`00250a810c00010001000000`，保留inactive status1|lease29/free0|
|HDMI0101/16B `00250101100001000000000006050000`|保存完整8B参数（原CP使用前5B）；`002501810c00010000000000`|lease30/free0|
|HDMI0117/12B×5|按port0..4逐包保存/配对；各回`002517810c00010000000000`|lease31..35各free0|

备份观测点2b6788c位于原Backup getter返回后，父帧+d0实际值8。它是原程序本次读到并使用的值，不是另行查询/修改备份。模型只通过被动getter读取该观测，先marker记录每条port/rate，再准入：0/0、1/0、2/17、3/17、4/0；backup非7走静态表。未知备份值观测或顺序/回显/字节不符均拒绝；backup7分支只在宿主验证，本轮未走。没有HPD或输出就绪通知，没有改变640×480 surface，也未证明enum0的物理像素含义。

每活跃请求只创建一个本次source对应lease；成功发送后释放原request，消费端自然free回复；失败恢复shadow/port游标/cache并回收自己的reply，原request保留。模型只在明确的软件640×480及disconnected/inactive profile内启用。BIND中沿用的timecode组件version31标签不代表本轮CPIO仍是v31；新增BOOT_TAIL_BOUND为32，实际v32由构建/CPIO SHA锁定。

## 四任务与屏障

325原8B请求进入既有v31合同，本轮1325/28B/status0/16个80能力字节回复已free0；随后原get-func的MPR/模型流程自然返回并入队，不合成完成token。

|任务|handle|业务TID|自然完成/函数返回|
|---|---:|---:|---|
|license|0|[323]|1次/[0]|
|volume|1|[324]|1次/[0]|
|beep|2|[325]|1次/[0]|
|get-func|3|[326]|1次/[0]|

四个句柄0/1/2/3不同且有效；每个完成闭包都是同一sequence的原入队过程，返回0。**入队不是屏障消费**：父线程先进入change_mode，当前屏障入口2b6353c=0、匹配2b63628=0、remaining2b63678=0、正常返回=0次；不能把四次完成写成屏障越过，`barrier_passed=false`。

## 新同步阻断与被动材料

change_mode调用点2b67a44完整输入24B：`010000000000000001000000000000000100000000000000`，六个LE32为[1,0,1,0,1,0]，保留原值，不擅自命名为未证实硬件模式。

2ebe188入口被动复制selected/current各50×24B到原有独立41dc观测RAM，QMP读回一组完整表。14行差异：`[1, 4, 5, 7, 10, 13, 14, 18, 20, 21, 22, 23, 24, 29]`；serial只打印前12行，JSON保存50行原字节和字段。当前表均为此入口时的只读副本，没有改表或endpoint。复制不承诺对其他线程原子一致，也不把runtime指针当有效pin/可用buffer证据。

首个后续Dataflow请求：

```text
destination=9284074a source=81cf61c0 op4 bytes48
c061cf81a0a0a0a001003000180000003000000000000000001000001800020000000000020000000100000000000000
```

封套reply_id/source相同、magic a0a0a0a0、count1、outerlen48/read24/write48/padding0；业务1000/cmd0/24B/flags2。栈：DF+33f20 ← appFw+2e10ab8 ← 2e10dec ← 2e1143c ← 2ebe410 ← 2ebeb40 ← 2de1fb0 ← 2b67a48 ← 2b68374。已escalation，**没有回复、没有伪造descriptor/连接/buffer owner**。原发送API返回0不证明CP消费；与该线程随后等待相符。

新增Dataflow只读日志实际捕获5条：两条早期805700f9、timecode52B、EVF温度40B、当前getpin48B；EVF温度仅观察，不继承timecode回复。所有这些完整raw和栈都保留；观察上限512、最大2048B，本轮未触发quota/truncation。0328、digital、0119的专门raw/栈观察已装配但本轮未到达，未新增回复；DMM op18实现仍保留−1024，本轮亦未到达该父流程位置。

## UI、读回及开放项

UI loop/init入口各1、init返回1；processSystemMessage返回2、false0；a18门控到达1、积压跳过1、时间门控0、实际UI调用0。timer生产11388、消费1、a18峰11387；出队仍150000/30072两条。目标boot主体返回、notify和CV_RETURN均0，事件继续等待。通用点36/37/38各1是非目标事件/线程，不当作本boot已通知。

ADF注册26/26 free0、ICDT4/4保持；GPE_CMD=0、176fb4c/1004=0、无result0绘制可触发读面/PNG，所以没有PNG；不能声称动态uniform flush无回归已验收。guest UI/菜单/真实声音/DMA/物理显示都未通过。

QMP gate发布11434，boot记录32/64、overflow0；mirror_skip0、topology_capture_drop=0。旧UIPC末次seen20750/emitted213/dedup20537，capacity_drop0/lock_drop0/stats_write_drop23；它仍是去重/统计文件观察，不是无损流量。快照bank为最后完成发布，可能略滞后于暂停中的回调。

[完整回执与0x11a后时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap79-review.json)；[QMP计数/两张50行表](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap79-gate-readback.json)；[serial](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap79tail-17293cc1/serial.log)；[receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap79tail-17293cc1/receipt.json)；[候选及构建](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap79-boot-vdf-hdmi-tail/candidate79.json)。

A7C2公开上游参考与FX3原CP审计共同约束了0165，但没有用其历史运行替代本轮消费证据；[网上研究摘要](../../work/fx3-vm-20261101/lead-claude/research/a7c2-latest/README.md)。下一步由Lead审计真实pin getter/endpoint与buffer生命周期，再决定软件后端；当前无QEMU且两锁释放。
