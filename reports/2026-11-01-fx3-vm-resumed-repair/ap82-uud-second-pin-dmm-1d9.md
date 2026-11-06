# AP82：第二拓扑与原UUD路径越过，DMM 1d9 assert失败

**本轮失败，不能作为300秒健康或菜单验收。** `ap82uud-9377b622`原计划300秒，新runner发现exception monitor立即QMP暂停、保存物理RAM/寄存器并退出，实际21.48秒。qemu_exit0/process_reaped/宿主PID不存在/inputs_unchanged，两锁重取通过，host_observer_error=None。guest进入原assert/exception；missing_markers=['FX3_TIMER_OBSERVER_END', 'FX3_UIPC_OBSERVER_END', 'FX3_SKD_ACCESS_AUTH_RETURN']，末次im健康存活不成立。AP81的240秒健康清屏基线及原回执保留。

## 28端点、14边与九包消费

capidv37使用新pin config/core v2，保留旧索引0..21与原11边，在同一受锁图追加6个断开端点/3条允许边；Imaging owner90050004只登记本次3个OUT。GET逐字段读取当前self/state，Imaging GET外层ReplyId=90050004，BB GET=9284074a，ADF GET=0；CONNECT外层0。OSAL回复始终source=实际provider、destination=本次活队列；本轮初始队列曾为81cf6183，第二阶段为81cf61c2，未写死历史source。

本轮实际42 GET/CONNECT回复全部自然free0（旧33+新9），没有DISCONNECT。新增三对为YC0/OUT2/index1→BB YC0/IN1/index1，RAW8/OUT2/index0→BB RAW8/IN1/index0，SYSND3/OUT2/index0→ADF SYSND3/IN1/index0。QMP在原face函数返回时读回图v2/3720B：ready1/fault0、serial42、queries28、connections14、disconnects0；28端点state0、peer互相匹配、generation2、reply/resource refs0；队列active1/capacity4/count0、所有handle0；16个buffer槽全未注册。旧22个endpoint/generation保持，pending_hardware=1/physical_output=0，不生成帧/0104 metadata/DMA/VSYNC。

宿主ASan/UBSan复跑旧33金样与新9金样，验证旧图不变、即时GET、正确outerSID、错误SID/完整键别名/未登记原生key、重复同边和重复free、外国线程/陈旧generation、分配/发送失败整事务回滚、仅原OSD owner/domain545可注册buffer。发送前图变更受同一锁保护，投递失败回滚未对外提交的双端状态，不能单边回滚已生效连接。

## 原UUD路径的动态证据

新增8个只读原指令探针，完整寄存器/flags/SIMD自检通过；没有预写Backup或参数。

|原位置/观察|实际结果|
|---|---|
|28272b8 原unsigned比较|1841=0、1842=4|
|27bec60 原参数144 store|先0，随后6；原存储目标8226db8|
|28272d4 原writer调用|调用2ebfdfc，写02cf1841的值4|
|28272d8 writer后|原调用返回0|
|2c245f4 原sequence快照|option6|
|2d11e4c 原change_mode输入|`020000000600000001000000000000000100000000000000`，mode2/option6由本次输入证实|
|enter_face_all_deletion_mode_proc|入口与原ret2d11e8c各1次|
|最终Backup物理RAM独立读回|offset9ce74/9ce78为4/4|

这关闭了此前只有静态链+前后值交叉印证的UUD来源缺口；本轮看到原调用/参数/返回及最终RAM相符。但face函数返回和4/4不代表所有异步reset副作用、完整mode transition或人脸数据实际清理已完成，后续DMM即失败。

## 新DMM失败与原异常

face函数返回后，TID327向9061003c发40B：

```text
20000000d901000000000000ffffffff000000000000000000000000000000000000000000000000
```

op20、unit1d9；旧远端DMM模型不支持此unit，准确返回status−3、handleffffffff/address0/bytes0，lease121被原应用free0。原调用栈appFw+2e4f0e4→2e4f4ac→2dda360→2d1b6a0→2d2fee0。随后原`lib::assert::notify_model_system_error()`在lib_assert.cpp:30对false触发assert；异常任务im.elf(SeqQueueCommon)/TID327，PC7f9ff4107c（原寄存器及完整stack/maps保留）。没有吞assert、把−3改0、补造DMM句柄/地址，Lead已派audits/dmm-unit-1d9。

旁支VDF0500/10B `0d2000050a0001800000`，TID339/source81cf6189，仍只记录/委派，不回包；不把其发送接受当消费或致命原因。

## GPE、图与本轮开放项

原v13 adapter仅在既有marker函数增加完整raw、selector/alpha/srcfmt/conversion/rotation日志，所有绘制/完成/拒绝分支未改；旧版本源与so保留，新增trace变体及原1100命令ASan/UBSan套件通过。本轮GPE_CMD=0、GPE_RAW=0，统计(op/fmt/flags/blend selector/alpha/地址/result)为空；原assert早于绘制，未产生PNG，不能据此判断v13像素路径回归或关闭P3。AP81已有清屏PNG不冒充AP82输出。

runner已具备后续成功绘制的持续QMP读回/双格式PNG，直到首个非均匀画面；本次未触发。图像继续按logical framebuffer原字节导出，panel_control3/osdRev0不导致主缓冲旋转。

gate mirror_skip=0、boot记录70/128、overflow=0。0x11a后捕获完整请求raw/FP-LR及原异常寄存器均入review；旧UIPC去重/文件统计限制仍在，不称全系统无损跟踪。

[完整失败回执/42包消费/UUD/raw/栈/原异常寄存器](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap82-review.json)；[QMP图v2、Backup与计数解码](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap82-gate-readback.json)；[不可变receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap82uud-9377b622/receipt.json)；[宿主图测试](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/pin2-transport-host-check.json)；[v13纯日志变体测试](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/gpe-v13-trace-host-check.json)；[候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap82-uud-second-pin-graph/candidate82.json)。
