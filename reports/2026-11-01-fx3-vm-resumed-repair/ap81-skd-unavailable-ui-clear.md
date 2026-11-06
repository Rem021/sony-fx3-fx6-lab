# AP81：SKD不可用降级后UI恢复与首清屏

本轮240秒`ap81skd-b9850378`通过健康运行回执：qemu_exit0、process_reaped/宿主PID不存在、inputs_unchanged、missing_markers=[]、末次/proc maps含im.elf，无新增external abort/symbol lookup/fatal，两锁释放后已重取核验。原启动链、UI future、timer与软件GPE首清屏均已出现；**尚无菜单内容或可操作验收**，后续新pin请求未扩展回复。

## 精确硬件不可用合同

保持AP80c capidv36全部模型，新增first-preload `fx3-skd-hw-unavailable-v1`。只在调用返回点`/usr/lib/libInfraSKD.so+645ec`（原BL+645e8）、addressNULL、offsetffffb000、len1000、prot1、flags1且fd readlink为`/dev/mem`时返回MAP_FAILED/ENODEV；其他mmap保持原参数、返回值及errno。没有ROM/零页/随机页、没有密钥/身份材料，没有改f340f000/f13b8000，没有强制CipherInit成功。宿主ASan/UBSan验证精确命中和相邻offset/len/prot/flags/fd/caller/模块/关闭profile原样转发。

实际只命中一次SKData_Init映射；原CipherInit两次返回−1020，data_encryption两次写status2并到原ret2eaa0d8，认证sequence到原ret2bcc544。原错误路径是非致命的；本轮只证明该路径运行，没有加密成功或认证功能验收。

gatev10保留原52个被动点的寄存器/指令检查与自检，新增CipherInit返回、data状态/返回、认证ret；在原boot future返回后停止观察旧event，避免AP80c所披露的对象生命周期后悬空字节读。统计count槽扩展64，原计数含义保留；QMP解码同步更新，未改原worker/notify。

## 启动、UI与GPE

四任务原屏障通过；panel单任务入口1次/公共返回1次，原返回0。QMP独立读回虚拟panel配置：{"ready": 1, "head": 1, "count": 0, "applied": 1, "hrev": 1, "vrev": 1, "osd_rev": 0, "control": 3, "tp_axes_reversed": 1, "generation": 1, "enqueued": 1, "consumed": 1, "readbacks": 1, "logical_framebuffer_unchanged": true, "physical_pixels_flipped": false, "TP_scope": "expected native false/false direction, consumption not proven"}。这与原1119消费、run_i0、notify→同event/cv首次返回的原记录互相支持；control3/osd0不修改逻辑framebuffer，原TP消费仍未证实。

QMP末次dequeue_total=495、timer_dequeue=466、last_a18=10816。176fb4c原timer与info/table/fill到达，1004、GPE清屏/Flush和8288076c发布事件见完整timer_events；这是原路径恢复，不是补发1004/强制清屏。所有计数只限本轮，不将AP72/73没有观测到绘制的旧回执追写成通过。

|op|fmt|flags|dst在545|src在545|result|次数|
|---|---|---|---|---|---|---|
|FillRect|0|0xff|True|None|0|1|
|Flush|0|0|None|None|0|1|

地址范围按v13原545合同`43feb5000+140000`；Flush没有像素地址，表中None表示不适用。首次FillRect后QMP暂停读`43feb5100/12c000`，SHA256为3630e065eb7b4540fbab11dbfd2619e8500f211b9c404380a1867fdc44b77c0c。format0-le16与format1-le32的640×480/stride640/RGBA/opaque假设各导出一张，均为均匀黑清屏（nonuniform=false），已查看图像。**两张都是logical framebuffer原字节解释，control3不导致导出旋转；不代表物理LCD/多plane最终scanout，不是菜单截图。**

![format0逻辑清屏](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap81skd-b9850378/osd-first-format0-le16-RGBA-opaque.png)

[format1逻辑清屏](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap81skd-b9850378/osd-first-format1-le32-RGBA-opaque.png)；[物理读回和两种格式假设](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap81skd-b9850378/osd-first-draw.json)。两者PNG哈希相同，仅说明当前均匀面在两种解释下一致，不验证未来非均匀图的格式/通道。

## 新等待与限制

后续TID327发Dataflow48B到90050004/source81cf61c2：`c261cf81a0a0a0a001003000180000003000000000000000001000001800020000000000020000000100000000000000`，GET type0/dir2/index1。该owner不在既有22endpoint合同，原样委派、未新增回复；已escalation。原栈DF+33f20→app2e10ab8→2e10dec→2e11180→2ebe5ec→2ebeb40→2de1fb0→2d11e50→2d2f40c。消息参数及14层FP/LR已冻结，终态QMP提供当前CPU寄存器，**未单独取得睡眠TID327的完整寄存器集**，不将其冒称为原线程寄存器。菜单/后续资源连接仍待Lead审计。

QMP gate mirror_skip=0、boot overflow=0；旧UIPC仍有去重/文件写统计丢弃，完整时间线指全部已捕获0x11a后raw/栈/unique序列，不是系统无损包流。末次bank为最后完成发布，可略滞后于暂停中的回调。

[完整回执/命令统计/0x11a后捕获时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap81-review.json)；[QMP计数/软件图/面板控制读回](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap81-gate-readback.json)；[新pin原包与栈](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap81-next-pin-capture.json)；[宿主检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/skd-hw-host-check.json)；[候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap81-skd-hardware-unavailable/candidate81.json)。

时序更正（AP82审计复核）：90050004新GET在原serial第23358行，先于FillRect26340/Flush26378；两者分属SeqQueueCommon与UI线程。因此不能把新pin先连通当作第一次清屏的前提，既有清屏证据也不证明该模式已收尾。
