# AP91：六步原输入接收成功，警告未关闭、菜单反馈未完成

**六步12条合成物理键均被原I-InputRecv接收并转换，状态缓存按下1/抬起0，原EventThread也收到12条事件；画面仍是槽1存储卡读取警告。** 不能把发送成功、缓存更新或EventThread接收写成应用回调执行或菜单输入反馈通过。

## 实现与宿主检查

完整读取key-input审计README和proof，使用只读--check复算31项原指令、565个ELF和126个模块；proof SHA256：`9c171c3e8bcf19e930802e67053480b30b0bbdd3b5eff4e3134d258d9a35e136`。采用方案1：同im进程中原OSAL分配20B物理消息，目标807a0020、来源00410025；字段为key/subkey/status/exinfo/from_type的5个LE32。成功发送交接原缓冲，失败按原API回收；不构造28B内部事件、不调用remote包装或直接UI。

脚本按原open_screen观察器捕获2c7后5秒、原I-InputRecv已进入等待、原配置表包含六步键的条件启动。顺序为确定1ac、MENU1ab、下30、下30、右1af、MENU1ab；每键下/上，目标按住100ms，键间间隔4秒。新screen观察器只导出已有开屏时间和目标，原6点与ASM保留。Cache通过LibObj原全局实例/配置表/状态表只读读取，不调用GetInstance，不改抑制状态。

ASan/UBSan覆盖精确字节、6步12事件、5s/100ms/4s目标时序、时钟/地址边界、原分配所有权与发送失败释放、接收参数/结果/errno和内部被动观测。screen上下文状态保留、逐步QMP导出器的像素/PNG/哈希检查通过。CAPID协议原源去除新增脚本include和两个调用后与v44逐字相同；GPE v16r2、Backup回放和CP协议模型不变。

首轮`ap91keys-bcec857c`在11.331秒、注入前被实现就绪门停止：首次OSAL调用早于libObj装入，NOLOAD返回空。exit0/reaped/inputs_unchanged、双锁FREE；未发键，13个后续required marker缺失、无末次im maps，如实保留。新capid46/脚本v2等待原库自然装入（实际9次50ms等待），不主动装新原模块；45/v1和原失败run冻结。

## AP91-r2 原运行结果

run **ap91r2keys-9d3939d7**，请求300秒，实际303.224秒，无提前停止。exit0 / process_reaped / inputs_unchanged；独立PID缺席、两把锁FREE；receipt与combined required missing均空。无symbol lookup error、fatal、unknown key、invalid from_type或新GPE拒绝。im PID228末次完整maps uptime295.94，仍含im.elf。

| 步骤 | InfraInput键 | 物理接收 / 原内部发送 / EventThread接收 | 实测按住ms | 读回与目视内容 |
|---|---|---|---:|---|
| 1 确定 | 0x1ac | 2 / 2 / 2 | 179.719 | [步骤1 PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap91r2keys-9d3939d7/ap91-step-01-key-1ac.png)：槽1读取警告 |
| 2 MENU | 0x1ab | 2 / 2 / 2 | 129.909 | [步骤2 PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap91r2keys-9d3939d7/ap91-step-02-key-1ab.png)：槽1读取警告 |
| 3 下 | 0x30 | 2 / 2 / 2 | 131.778 | [步骤3 PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap91r2keys-9d3939d7/ap91-step-03-key-030.png)：槽1读取警告 |
| 4 下 | 0x30 | 2 / 2 / 2 | 129.851 | [步骤4 PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap91r2keys-9d3939d7/ap91-step-04-key-030.png)：槽1读取警告 |
| 5 右 | 0x1af | 2 / 2 / 2 | 165.420 | [步骤5 PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap91r2keys-9d3939d7/ap91-step-05-key-1af.png)：槽1读取警告 |
| 6 MENU | 0x1ab | 2 / 2 / 2 | 160.701 | [步骤6 PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap91r2keys-9d3939d7/ap91-step-06-key-1ab.png)：槽1读取警告 |

每条物理接收的20B都与对应本次发送逐字匹配，来源410025/from_type1；每步两条原28B到7a804c，及两条来自原EventThread返回点libObj+c8fc8的32B接收。每步cache的before_up为1、after_up_50ms为0。EventThread后实际应用callback入口未直接观测，marker明确callback_dispatch_unproven=1。

实际首键距原2c7开屏约5.249秒。100ms是调度目标，实测按住129.851–179.719ms，包含TCG调度和只读cache观测开销；键间实测4.031–4.069秒。**不是精确100ms实时验收。** Runner在成功up marker宿主首见后至少2秒触发QMP stop；含ring复核与PNG导出，回执完成时间为2.747–3.032秒，不冒称原guest事件后精确2秒。

六张步骤原始像素SHA完全一致，也分别匹配当次原已提交ring；目视第1/2/6图均为日文“无法正确读取存储卡／请重新插入存储卡／槽位1”，其余图逐字像素相同。每步PNG均已保存，未叠字或补画。脚本之后新增open_screen为0、新GPE命令为0；原开屏仍2ae→fa→2c7。是否被当前警告或输入抑制拦截尚未证实，已发escalation，未绕过对话框。

![第2步MENU后，仍为原厂槽1警告](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap91r2keys-9d3939d7/ap91-step-02-key-1ab.png)

## 绘制与最终读回

原77条完整GPE全部result0，与AP90一致：FillRect3、fmt0通用28、fmt0 nearest缩放36、fmt2文字9、Flush1；源基址不在屏幕extent，均沿已批准资源区间登记。无脚本后的新增绘制，不把旧77条算作按键响应。

最终独立QMP stop/pmemsave仍为43feb5100、640×480、stride640、逻辑fmt0，614400B、14种像素，SHA256 `fba3e9413bd407b9f113d0792706af6d263319b42286e5ddd1f101239b05b460`。最终PNG与步骤图一致，没有菜单画面。

沿用AP90所有限制：混合/文字/nearest为明确近似；资源+40不是已恢复真实DMM handle；分配区间锁不覆盖bitmap子块移动、compaction和排队ABA。本轮输入为synthetic_input=1/original_cp_key_detection=0，没有物理键或真实相机验收。

## 复核入口

- runtime/ap91-host-check.json、ap91-r2-host-check.json、helpers/screen91-host-check.json与对应build JSON。
- runtime/ap91r2keys-9d3939d7-review.json、key-review.json（逐步全证据）、gpe-statistics.json、post11a-requests.json。
- 同run的ap91-step-readbacks.json、六组原始bin/PNG/JSON、receipt、serial、printk、最终ap91-QMP-logical-fmt0.png；历史run保持不变。

0x11a后时间线保留13940条匹配记录，受原trace上限/串口交织限制；ring验证快照1110份，允许sequence gaps，不称全局无损。

2026-11-02再次联网核对[A7C II维护者README](https://github.com/chocotan/a7c2-qemu/blob/main/README.md)及[研究进展](https://github.com/chocotan/a7c2-qemu/blob/main/docs/tech/2026-10-31-current-progress.md)：其菜单、控制与虚拟卡已有成果，原拍照录像仍未验收。本轮只参考输入、显示、虚拟介质分别验收的方法，键码和私有结构仍用本机FX3原件合同，不借A7C2结果证明FX3菜单可操作。

补充核对[维护者存储笔记](https://github.com/chocotan/a7c2-qemu/blob/main/docs/tech/07-storage.md)：可复用的是原Fsys返回、RM业务消费、卷状态和独立内容读回分别验收；不能照搬其单槽拓扑、通知字节或物理导出地址。直接公开原文读取的内容哈希保存在runtime/ap91-a7c2-storage-reference.json；GitHub API因限流未确认最新commit，不冒称已核HEAD。此参考没有触发本机媒体状态修改。

## 后续审计更正（AP92前）

media-slot-dialog审计把本轮既有`FX3_BOOT_QUEUE_SEND`的原32B输出逐包绑定到`appFw+16f10b4`（原回调16f0fc0→osal_snd_msg），目标5503e0。运行链已按原LF逐包核对12条原行与raw，均from_type1/inh0。**原应用转发回调已执行**；上文“应用回调未证实”是当时观察范围，现由更强原字节/原调用点证据更新，不再作为阻断原因。下一缺口是应用队列dequeue、键到ds_event转换及controller动作。EventThread接收处prev_status摘要0不能覆盖稍后原应用32B raw中的首按7fffffff、抬起1；不改from_type/inh。STATE和review已同步补充，未改原run。
