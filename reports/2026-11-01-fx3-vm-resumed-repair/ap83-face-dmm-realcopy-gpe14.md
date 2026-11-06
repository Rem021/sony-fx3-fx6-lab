# AP83：人脸DMM真实复制与GPE v14健康对照

**最终：AP83a-r4 `ap83ar4face-4cd8574a` 与 AP83b `ap83bgpe14-f83e3fc5` 均完成300秒观察，末次im存活、missing空、QEMU0/回收/原件未变/锁释放。** capidv41完成三次真实复制及4条DMM回复消费；v14与v13原清屏/Flush无回归，实际混合/HV请求0，仍只有黑清屏，菜单/输入未验收。前三次失败完整保留，见下文。

## AP83a 首轮失败，保留现场

`ap83aface-22d76bf2` 使用capid v38，计划300秒，23.28秒发现原assert后自动QMP暂停取RAM/寄存器并退出。qemu_exit=0、process_reaped、inputs_unchanged，宿主PID不存在、两锁重取通过，observer_error=None；missing为TIMER_END/UIPC_END/SKD_AUTH_RET，结尾im健康存活未成立。不能作为300秒健康、传输或UI验收。

三单元remote1d9/1da/1db分别分配8408/8409/840a，option0、opens0、无段，三回复均原生free0。独立FDT+memrsv为41dd00000/90000，原RAM及全部已有FDT/memrsv不重叠，QMP取得完整589824B backing。首条ICDT local40e→remote8408、length64000、mode1被−1024拒绝（无callback），原SeqQueueCommon进入lib_assert.cpp30；完整raw/stack/regs/maps与0x11a后请求时间线保留。

自有捕获接线存在两个限制：仅msg_size40；只接受8020/8021/802a，未处理原生local op24打开回复。原现场另有PIN_DUPLICATE_FREE_REJECT，指针被新原生消息复用。Lead授权新v39按24B无段分配与40B/8024段回复被动捕获，并对退休pin/panel指纹增加原消息长度门禁；原v38及run不变。该轮尚无真实face复制、GPE或PNG；不能声称注册成功。

宿主v38 ASan/UBSan覆盖三个独立40B金样、原生句柄生命周期、过期/错误域/越界、三块非均匀逐字节真实复制、失败回滚及旧beep相关性；原测试没有覆盖本次原生短回复和op24时序，新增v39时序回归后重跑。

[首轮失败review](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap83a-review.json)；[不可变receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap83aface-22d76bf2/receipt.json)；[预留非重叠核验](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap83a-face-dmm-realcopy/exclusive-reservation.json)。

## AP83a-r2：原始回复定位残留字段

`ap83ar2face-147481dc`/v39同样在首ICDT拒绝后原assert，21.99秒自动停机；qemu_exit0/reaped/inputs_unchanged/observer_errorNone、锁重取通过，三missing及im不健康同首轮。其精确原生raw纠正前述短回复假设：实际8020均40B，unit/handle正确，但allocate-only未定义的段数1、地址43fe2f400、容量bca0来自旧缓冲；v39错误使用残留几何而删掉活记录，8024到来已无记录。本地8024确认handle40e→424000000/64000、410→4350fb000/d100，回复unit字段同样可能残留1dc，应沿用分配时unit。v40只从allocate-only记录unit/fullhandle，几何仅由后续原生打开/查询登记，原回复完整保留。24B支持属于防御兼容，不能称本轮实际24B。

[第二轮失败review/全部原生回复raw](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap83ar2-review.json)；[不可变receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap83ar2face-147481dc/receipt.json)。

## AP83a-r3：真实复制闭合，op21接线需修正

`ap83ar3face-a5f66d08`/v40在22.65秒停机。三单元ICDT真实复制按1d9/1db/1da顺序：409600/53504/51200B，源原生物理424000000/4350fb000/424064000；三条逐字节equal、callback自然执行/原free0。独立QMP最终目标readback三份FNV均匹配复制marker：1d9=f66d4524e2280383、1db=619e14923a2fcf83、1da=36c1140ffd7f2d98；unique bytes分别1/1/61。前两块本轮源恰为均匀字节，第三块非均匀；不称有效人脸记录或识别结果。原本地分配/打开/关闭/临时释放不改，未清零替代face传输。

随后op21精确40B `21000000db0100000a84000000000000000000000000000000000000000000000000000000000000`，原AP2e4fd10..18明确把对象unit存入request+4。v40对所有非alloc要求unit0过严，拒绝−1024后原assert。v41按op21 unit必须等于已持有unit（此处1db），其余原边界保持；精确原请求/独立单段回复及错误unit金样回归后重跑。qemu_exit0/reaped/inputs_unchanged/锁释放，仍missing三项、im不健康，不能作为300秒验收；GPE尚0。

[第三轮失败review/目标物理读回](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap83ar3-review.json)；[不可变receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap83ar3face-a5f66d08/receipt.json)。

## AP83ar4：ap83ar4face-4cd8574a

窗口301.16秒（计划300秒）；健康观察=True，结尾im maps存活=True，missing=[]。qemu_exit0/reaped/inputs_unchanged、宿主PID不存在、两锁重取通过；observer_error=None。首四任务屏障=True，pin回复提交/消费=42/42，独立图QMP为28端点/14空队列边。原UUD来源证据保持，Backup最终1841/1842=[4, 4]。

face DMM回复提交/消费=4/4，真实ICDT提交/原生callback消费=3/3。独立QMP目的字节检验：

|unit|字节|FNV64|与最后复制标记相符|unique bytes|
|---|---:|---|---|---:|
|0x1d9|409600|0xf66d4524e2280383|True|1|
|0x1db|53504|0x619e14923a2fcf83|True|1|
|0x1da|51200|0x36c1140ffd7f2d98|True|61|

源目标逐字节相同由helper在真实复制时检查；QMP是独立最终目标读回，未把目标hash称独立源快照。保留原注册文件过滤路径，CP90060197的0207/0206仅记录/原发送，不伪造识别结果或传感器帧；没有据此验收人脸识别或CP处理。

GPE实际命令统计（地址列只核对基址在545 payload，完整跨度由adapter/原始参数核验）：

|op|fmt|flags|dst/src base in545|result|approx|
|---|---|---|---|---|---|
|FillRect|0|0xff|True/False|0|v13 no approx|
|Flush|0|0|False/False|0|v13 no approx|

本轮物理绘制读回1次，非均匀PNG=False；导出保持logical framebuffer，panel_control3/h1/v1/osd0不翻转主缓冲。物理545@43feb5100/12c000 SHA256=3630e065eb7b4540fbab11dbfd2619e8500f211b9c404380a1867fdc44b77c0c。

本轮没有非均匀画面时，只关闭健康启动/清屏回归，不关闭菜单文字、输入循环、近似混合像素或物理面板等价验收。

[完整review/0x11a后全捕获请求时间线/原生raw](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap83ar4-review.json)；[不可变receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap83ar4face-4cd8574a/receipt.json)；[GPEv14独立重建与四套宿主检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/gpe14-runtime-check/receipt.json)。

### AP83a UI门控读回与剩余绘制缺口

原init、outerfuture返回、单paneljoin、SKD auth return各1；UI实际更新2次，dequeue561（timer532），backlog_skip559、time_pass2、last_a18=12320、timer生产12853。mirror_skip0、72条boot记录/无溢出。AP81同类计数为dequeue495/timer466/backlog_skip493、time_pass2、last_a18=10816。两个窗口长度不同，不据计数多少判性能回归；原背压分支大量skip可解释本轮“进程存活但无进一步GPE请求”的并存现象，尚未证明全部因果。未改计时、限流、通知或门槛，也未宣称可操作输入循环。

## AP83b：ap83bgpe14-f83e3fc5

窗口301.27秒（计划300秒）；健康观察=True，结尾im maps存活=True，missing=[]。qemu_exit0/reaped/inputs_unchanged、宿主PID不存在、两锁重取通过；observer_error=None。首四任务屏障=True，pin回复提交/消费=42/42，独立图QMP为28端点/14空队列边。原UUD来源证据保持，Backup最终1841/1842=[4, 4]。

face DMM回复提交/消费=4/4，真实ICDT提交/原生callback消费=3/3。独立QMP目的字节检验：

|unit|字节|FNV64|与最后复制标记相符|unique bytes|
|---|---:|---|---|---:|
|0x1d9|409600|0xf66d4524e2280383|True|1|
|0x1db|53504|0x619e14923a2fcf83|True|1|
|0x1da|51200|0x36c1140ffd7f2d98|True|61|

源目标逐字节相同由helper在真实复制时检查；QMP是独立最终目标读回，未把目标hash称独立源快照。保留原注册文件过滤路径，CP90060197的0207/0206仅记录/原发送，不伪造识别结果或传感器帧；没有据此验收人脸识别或CP处理。

GPE实际命令统计（地址列只核对基址在545 payload，完整跨度由adapter/原始参数核验）：

|op|fmt|flags|dst/src base in545|result|approx|
|---|---|---|---|---|---|
|FillRect|0|0xff|True/False|0|0|
|Flush|0|0|False/False|0|0|

本轮物理绘制读回1次，非均匀PNG=False；导出保持logical framebuffer，panel_control3/h1/v1/osd0不翻转主缓冲。物理545@43feb5100/12c000 SHA256=3630e065eb7b4540fbab11dbfd2619e8500f211b9c404380a1867fdc44b77c0c。

本轮没有非均匀画面时，只关闭健康启动/清屏回归，不关闭菜单文字、输入循环、近似混合像素或物理面板等价验收。

[完整review/0x11a后全捕获请求时间线/原生raw](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap83b-review.json)；[不可变receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap83bgpe14-f83e3fc5/receipt.json)；[GPEv14独立重建与四套宿主检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/gpe14-runtime-check/receipt.json)。

## AP83最终对照与交接

两轮候选CPIO逐成员比对，仅`simulation/fx3-gpe-observe-v7.so`内容不同，init/LD_PRELOAD顺序等所有其他成员完全相同；DTB仅linux,initrd-end随CPIO长度调整，所有FDT reservation一致。v14 SHA836b78c4a290ece86d27d1e2a5d99097be570974ef2acdeee9a3c4314d6a41bb，runtime独立重建逐字节一致，四套ASan/UBSan通过。

实际approx_blend请求0、BitBlit/HV请求0、拒绝参数0；原FillRect640×480/fmt0/flagsff和Flush各result0，两轮物理readback SHA3630e065eb7b4540fbab11dbfd2619e8500f211b9c404380a1867fdc44b77c0c相同。Fill的src0与Flush的src/dst0是未使用字段，不属于越界绘制。没有用宿主混合测试冒充实际请求或硬件oracle。

[A/B完整比较/真实proc uptime样本](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap83-ab-comparison.json)；[只换一个CPIO成员核验](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap83b-gpe14-approx/single-change-verification.json)；[v41精确原请求与真实copy宿主回归](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/face-dmm-r4-host-check.json)。随后按Lead AP84合同核实原CPU拓扑并仅对照QEMU并发/时钟，不改原厂门槛。
