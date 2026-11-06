# AP77：UI 主循环门控与四任务启动观测

正常时钟 AP77a `ap77agate-f63dd39e`（240 秒）通过观测件客体自检，主循环和初始化均进入。曾命中一次 a18 积压跳过，但随后第二条出队消息 `0x30072/src830128` 后不再回到门控；AppFw 末次线程快照在 futex 等待。不能据此把无首绘仅归因时钟或积压。

## 运行回执

|项目|AP77a 正常时钟|AP77b 探索性 icount0|
|---|---|---|
|run|`ap77agate-f63dd39e`|`ap77bcount0-b9abfcab`|
|候选|AP76 v30 + 被动 gate v1|原 AP76 v30，不加新 hook|
|时长|240 秒|240 秒|
|qemu_exit / reaped / inputs_unchanged|0 / True / True|0 / True / True|
|missing_markers|`[]`|`[]`|
|宿主 PID 消失 / 两锁重新取得|True / True|True / True|
|im.elf 末次快照存活|True|True|
|致命事件|0|0|
|ADF 327/32a / native free0|26 / 26|26 / 26|
|ICDT completion consumed|4|4|
|GPE_CMD|0|0|

退出0是有界观察后 QMP quit 和回收成功；不是 guest 正常关机。存活证据是末次 `/proc/<pid>/maps` 的 im.elf 映射，不是停止瞬间进程取样。两轮 guest 候选不同，按 Lead 调序执行，仅作为探索比较，不能称为严格同候选 A/B。icount0 实际参数为 `shift=0,align=off,sleep=off`；单独切换该参数未激活首绘。AP77b printk 单调时间代理差值与 AP76 比较见时钟比较 JSON，不能冒称直接 /proc/uptime。

## 观测完整性

新增 `fx3-ui-gate-v1.so`，保留 AP76 所有既有 simulation helper 字节与原 ELF；init 仅追加 preload 和在既有 proc 快照中读取 uptime，sleep 语句仍为13条。只用 mmap 提示寻找近端空页，不使用 MAP_FIXED。31处逐字核对原指令后，以单条 B 跳入小岛，重放原指令；CBNZ 和 BL 显式保留原分支目标、fallthrough 与 LR。原始文件不改。

绑定前在 guest 运行 NOP、CBNZ 两方向、BL 自检，31 GPR、32 SIMD、NZCV、FPCR/FPSR、SP 均验证；自检失败禁止绑定原应用。实际 SELFTEST_PASS 与 BOUND 均出现。观察不改寄存器输出或原生返回值，不补发1004/325、不调用 iCrypt_init、不新增 sleep。每点只记前50次与每1000次日志；计数保留所有到达。

独立 guest RAM `0x41dc00000/64KiB` 同时通过 FDT reserve map 与原生 memrsv 排除，已核对与原保留区及41d8/41d9/41da/41db无交叠。停机后 QMP 读回 `ui-gate-counters.bin`，magic/version2有效；双 bank 发布序号 11408，boot 记录 16/64、overflow 0。统计是最后完成发布的 bank；若暂停在观测回调中可略滞后，不称为停机瞬间原子 BSS。探针会增加执行开销，结果适用于本有界观测候选。

旧 UIPC 统计末次为 seen=20707、emitted=200、dedup=20507、capacity_drop=0、lock_drop=0、stats_write_drop=60。最后一项是旧统计文件写快照失败次数，不应写成所有观测零丢失；新 gate RAM mirror_skip=0，boot overflow=0。完整0x11a后已捕获请求时间线保存在回执，但不把去重日志当作逐次原始全流量。

AP77a 直接 `/proc/uptime` 三次为13.83/25.96/38.16秒；gate CLOCK_BOOTTIME 首次8.427696992秒、最后采样232.224060000秒。原 printk 时间尺度与直接 uptime 不同，AP77b 的9821秒代理值不能当作实际客体 uptime，不能用它证明时钟比例或排除纯时序问题。AP77b 没有直接 uptime/BOOTTIME测量。

## UI 门控计数（QMP RAM）

|点|次数|
|---|---:|
|主循环入口 / 返回|1 / 0|
|初始化入口 / 返回|1 / 1|
|processSystemMessage 返回 / false|2 / 0|
|a18>2 判定点 / a12 判定点|1 / 1|
|积压跳过（a18>2 且 !a12）|1|
|时间判定 / <=0x62f4 跳过 / 通过|0 / 0 / 0|
|实际 UI 调用 BL16f2640→16f1998|0|
|timer 生产递增 / 消费递减|11381 / 1|
|5503e0 原生接收成功 / timer消息|2 / 1|
|a18 生产/消费峰值 / 门控峰值|11380 / 4|
|a12非0 / a13非0（各点采样）|0 / 0|

直方图区间依次为0、1、2、3..10、11..100、>100：生产/消费/门控采样合计 `[1, 2, 1, 9, 90, 11280]`；真实门控 `[0, 0, 0, 1, 0, 0]`。最后观测对象 `0x7f483dce80`，a18=11379、a12=0、a13=0。这不是均匀时间采样直方图。

两条出队分别150000与30072，source均830128；timer只消费一次。门控只到达一次且积压跳过，时间判定从未到达，所以本轮无法评价 elapsed 阈值行为。之后主循环未返回/退出，AppFw tid289快照在 futex 等待；不能只根据不断增长的 a18 推断循环持续被该门控跳过。

## 四任务与屏障

|任务|创建句柄|业务入口 TID|自然完成状态|
|---|---|---|---|
|license|0|[323]|completed_native_enqueue / completion返回[0]|
|volume|1|[324]|completed_native_enqueue / completion返回[0]|
|beep|2|[325]|completed_native_enqueue / completion返回[0]|
|get-func|None|[]|not_created / completion返回[]|

句柄0是有效创建结果；拒绝值是0x1000。前三个任务的自然完成通知分别带原句柄0/1/2，内部原生入队函数返回0；没有将入队当作屏障消费。get-func 创建前、创建返回、业务入口、trace通过、325发送前均0；屏障入口、token匹配、remaining判定、屏障返回均0。结论是本轮未创建第四任务且未进入屏障，四句柄匹配/remaining0验收未通过，特殊token2000路径亦未发生。

创建线程 SeqQueueCommon tid327 在第三次创建后最后独特发送为 `target9059000e/op4/tag1=81cf61c0/tag2=a0a0a0a0`，相邻内核日志为 `No snd_msg registered ...0xe`；末次快照在 `osal_rcv_msg_tmo` 等待。该时间关系是后续静态定位线索，未在本轮伪造回复或直接认定其请求语义。

## 绘制与开放项

本轮无 GPE 命令，统计表为空；不存在 result0 绘制可触发物理面首帧读回，因此没有 PNG。runner 已具备首个 result0 FillRect/BitBlit 立即停机→QMP读545→导出→恢复的分支，但本轮未执行该分支，不算显示验收。旧 uniform flush 本轮也未发生，不能声称动态无回归已证实。

下一步须沿原请求查明 SeqQueueCommon 等待与30072处理后的 futex 来源；保持四任务屏障、UI首绘、PNG及菜单/按键/物理显示验收开放。

## 复核入口

- [AP77a逐项回执与完整0x11a后请求时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap77a-review.json)
- [QMP计数及原始boot记录解码](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap77a-gate-readback.json)
- [AP77b探索回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap77b_icount0-review.json)
- [时钟代理比较](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap77b-clock-comparison.json)
- [CPIO helper逐成员一致性](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap77-helper-provenance.json)
- [构建与非重叠保留区回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap77-ui-gate-observe/build-receipt.json)
- [当前状态](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)
- [AP77a原始serial](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap77agate-f63dd39e/serial.log)；[receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap77agate-f63dd39e/receipt.json)；[原始计数RAM](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap77agate-f63dd39e/ui-gate-counters.bin)。
