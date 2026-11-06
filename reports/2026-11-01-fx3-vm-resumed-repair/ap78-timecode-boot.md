# AP78：timecode 与 boot 通知链

AP78a 已冻结抓包；AP78b 已验证 timecode 规范回复被消费，随后在新的 VDF0165 同步请求等待。0x325 的实现仅宿主测试通过，guest 尚未创建该任务；屏障、boot通知、UI恢复和首绘仍未通过。

- 正式 run：`ap78acapture2-39d22c97`，80秒；exit0、reaped、inputs_unchanged、宿主PID消失、两锁重新取得、缺marker空、im末次映射存活，无致命事件。
- 校准 run `ap78acapture-4be7adce` 同样收尾通过；整包相同，但首次输入探针错读 x1 输出槽，不作为输入证据。gate v3 改读原签名的 x0 输入，未改变原应用参数/返回值。
- 完整52B：`c061cf81a0a0a0a00100340018000000340000007f000000012005021c0001000100000000000000000000000000000000000000`。metadata source与outer reply_id均81cf61c0，magic=a0a0a0a0、count1、outerlen52/read24/write52；padding=7f000000，业务2001/0205/28B/flags1。
- wrapper输入8B=0100000000000000（in0=1/in1=0），body+16=0；栈绑定DF+33f20、appFw+2debc58/+2b66f2c。
- Lead `msg_1cc45f8e8432`确认准入：除reply_id与padding两处外44B精确匹配；reply_id非0且等于当前metadata source、通过local规则并绑定当前活跃request/lease；padding仅记录、不匹配，回复reserved清0。不能重放历史queue。

[完整抓包、栈、冻结白名单与回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap78a-timecode-proof.json)。[冻结52B](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap78a-frozen-request.bin)。

前三任务完成、第四尚未创建/屏障未进入、UI等待与无GPE仍延续AP77；本步骤不添加回复，不是timecode消费/boot/菜单验收。

## AP78b 实现与宿主检查

capid v31 按Lead确认的44字节白名单，只忽略当前动态reply_id及未初始化padding；reply_id必须非0、等于本次OSAL source并满足local规则，调用链必须同时命中dataflow+33f20、appFw+2debc58/+2b66f2c。padding原值以marker记录，回复reserved清零，不沿用历史queue。每活跃request关联唯一reply lease；成功发送后释放原request，原消费者自然free回复；分配/发送失败回收回复并保留原request，重复活跃请求拒绝。timecode仅为软件排队确认，不执行CP/物理timecode。

325只接受原8B精确请求，准备28B/1325/status0/16个80能力字节；LowCut=80。互补AP标志仍可能为真，不能把该字节表描述成所有功能false；后续播放仍拒绝。此handler本轮没有被guest调用，不是动态验收。

[ASan/UBSan回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/boot-reply-host-check.json)覆盖44B逐字节负例、长度、source/reply_id、调用链mask、任意padding、规范回复、重复活跃请求、分配失败/发送回滚、PID、325能力及8线程24000次锁检查。编译与检查实际包含最终v31源码，未用宿主测试替代原应用消费。

## AP78b 原生运行回执

`ap78bboot-537976cc`，正常时钟240秒，候选 [candidate78b](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap78b-timecode-getfunc/candidate78b.json)。qemu_exit=0、process_reaped=True、inputs_unchanged=True、宿主PID消失=True、两锁重取=True、missing_markers=`[]`、im末次快照存活=True，fatal=0。有界QMP退出与末次映射证据不是guest正常关机或停机瞬间进程快照。

42点GPR/SIMD/NZCV/FPCR/FPSR/SP与NOP/CBNZ/BL自检通过；近跳岛池扩为8KiB独立mmap，仍不MAP_FIXED。观测RAM沿用已保留41dc00000/64KiB，QMP发布序号11328，mirror_skip=0、boot记录21/64、overflow=0。计数为最后完整发布bank，可能略滞后于暂停在回调内的实际执行。

- timecode 36B：原 source81cf61c0，reply source9059000e，caller_mask7，原padding raw=7f000000（marker按小端整数打印0000007f）；lease27，request_free返回0，原waiter回复释放0。
- 之后原流程实际发出0142/015a/0145/011b/0160，再到0165：`destination92840747/source81cf61c0/10B/raw=0d2065010a0001800200`。FX3栈为2de7264←2debab4←2dd06c0←2b67388←2b68374。已escalation，未自造回复。
- ADF327/32a 26包，free0=26；ICDT completion消费4，原静音链保持。原声音/DMA未实现。
- license/volume/beep创建handle0/1/2，每个自然完成入队一次、completion函数返回0；get-func创建前/返回/业务入口/325发送前均0。屏障入口、匹配、remaining、屏障返回均0；`barrier_passed=false`，没有四句柄验收。

## 同一event的运行绑定

原sequence保存点2c20d20与wait前285e42c，均读到sequence=`7fa01851e0`、event=`7f5935c3e8`、cv=`7f5935c3f0`、完成字节0。原libstdc++条件等待转发wrapper记录同一cv和TID289，caller=`2aa23a8`，明确为协作等待分支；未改变等待/通知行为。

目标boot主体返回2b68374与通知调用2b6838c均0，未捕获该event的置位、notify、CV_RETURN或285e430返回。通用点36/37/38总计各1是未满足目标event/caller/TID过滤的其他调用，不能拿它们当boot通知或wait返回。16f2698两次发生在目标future等待之前，也不能称为30072业务处理完成。

UI：loop/init入口各1、init返回1、processSystemMessage返回2/false0；a18门控只到达1次（当时4），积压跳过1；时间门控0，实际UI调用0。timer生产11293、消费1、a18峰11292；出队两条150000/30072，仍无进一步timer消费。GPE_CMD=0、176fb4c/1004均0，没有 result0 绘制可触发PNG，因此没有导出图像；显示/菜单验收保持开放。

旧UIPC末次seen20620/emitted208/dedup20412，capacity_drop0/lock_drop0/stats_write_drop40；新gate的mirror_skip0。请求时间线包含完整已捕获0x11a后记录，并不把去重观察当无损原始全流量。候选scope继承早期历史文字，当前模型以init env、CPIO helper SHA及本报告为准：capidv31 + gatev4，不能把继承的AP78a“no reply”描述当作本轮行为。

## 网上最新研究对照与后续

按用户追加要求，已联网核实A7C2公开HEAD和原生回执。A7C2的timecode回执后也遇到相同0165；其panel proof甚至含相同10B请求与1165/590000域回复。该参考尚需FX3 CP路径独立核对，未直接搬用。[上游核查摘要](../../work/fx3-vm-20261101/lead-claude/research/a7c2-latest/README.md)及[在线来源SHA](../../work/fx3-vm-20261101/lead-claude/research/a7c2-latest/online-source-check.json)。Lead已安排boot-vdf-tail审计；当前无QEMU、两锁释放，等待后续合同。

[逐项回执、0x11a后时间线、事件和屏障判据](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap78b-review.json)；[QMP计数解码](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap78b-gate-readback.json)；[原serial](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap78bboot-537976cc/serial.log)；[receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap78bboot-537976cc/receipt.json)。
