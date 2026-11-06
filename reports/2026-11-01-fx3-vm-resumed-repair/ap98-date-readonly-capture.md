# AP98 日期服务只读完整抓包

**原32B同步请求与内核44B分发已完整保存；确认日期后原调用仍等待，没有回复/return可供抓取。** 600秒窗口已完成，严格回执见收尾。 原参数force仍1，未添日期回复或改模型。

## 观测修正与宿主验证

Lead msg_de25f58b89eb批准只读抓包，msg_2c43f8a7ac82更正：2d7e6f4属于remote日期序列；首次设置应看sequence_clock::date_time_initial_setting的2b725c8入口、2b72680调用、2b72684成功判定。Preset4新增这些及共同sync/force清理点，合计29处原字核验；保留旧remote点但不再把它当首次设置成功判据。实际来往字节与kernel路径不预设成功。

用户态fresh-open /proc/self/mem，原API确认32B且调用者从send到return后free期间仍拥有缓冲时，若pread失败只读复制该32B；真实运行确认pread EIO5，直接只读复制成功。方法1=pread，2=原生caller-owned32只读复制，3=内核原sender持有体；errno只在读取失败时解释，live force_valid/date_mask才是读取有效性判据。原消息API/参数/返回/errno/所有权不变。

内核现有CP Backup publicsender保留原路由/返回/分配/释放算法，只对909005c5/44B复制观察，不回包、不free原消息。观察输出位于既有64K软件预留区的41df01000/6000，原输入与诊断前4K保持；driver只QMP读回。init独立读取实际日期tid的status/wchan/stack，不依赖被阻塞线程自行打印。

真实组件ASan/UBSan：早期未绑定、pread EIO、32B请求前后精确字节、fresh模型读取、errno/参数/返回/原消息和寄存器不变；内核44B无reply/free/体变更及原CP88全部回归；4生产者80事件、64槽16溢出、奇偶发布/输入4K与尾邻居守护。交叉构建/CPIO审计/init语法通过；仅Preset4、CPbackup2观察段和init独立日期tid读段变化，AP97-r2其余模型body逐成员一致。

## 实际原字节与等待

运行`ap98datecapture600-b6f825f4`。完整解码、所有原行/LF定位、线程栈与PNG SHA见`runtime/ap98datecapture600-b6f825f4-date-evidence.json`；每步及确认前后观察页由QMP只读保存。

80900141 原同步请求（32B）：

`00000000e50701010000000000000000000000001c0200000000000001000000`

pid228/tid427，原用户指针`0x7fa1f16100`，caller`0x7ef5711498`（app相对2f72498）。当前稳定记录state=entered_no_return_observed；before捕获完整，after/native_return为空，不能填0。调用前live force current/next1、date current/next0，force_valid与date_mask=3。

909005c5 内核原分发（44B）：

`0100000000000000000000000000000000000000000000000000000000000000000000000000000001000000`

内核原指针`0xffffffc11e5e8000`，source由串口原行记录为809005c5；末尾u32为1。publicsender沿用原fallback return0，宿主真实回归验证该分支保持0；内核观察点位于返回前，记录中0为原固定分支值，不宣称有独立return探针。**它不是CP完成或日期成功**，没有after回复体。模块初始化阶段另有一条完整44B原行，末尾u32为4，未把它命名成已收到完成消息。

内核初始化阶段的44B在provider初始化前出现，provider原有清空64K诊断页会清掉该早期副本，因此早期包保留串口完整88hex原行；AP阶段32B/44B在KEY_READY后由独立QMP副本验证，确认前后页SHA一致。没有修改provider的初始化逻辑来保留观察区。

tid427为SeqQueueCommon，状态S；实际核栈：`osal_wai_sem_tmo → udate_wait_for_distribution_done+0x74 → udate_get_localtime+0x28c → udate_set_date+0x260 → udate_proc_read_clock+0x4a0 → __osal_snd_sync_msg`。32B调用在语言页就已进入；日期OK前后仍同一个事件。首次设置入口2b725c8/call2b72680/result2b72684尚无命中；共同helper2f72354与send点2f72494有命中，无共同return2f72498及remote return。

事实：UI按OK后进入温度提示，原日期调用没返回、live force仍1，不能据UI跳页认定日期成功。推断：Common队列先被旧日期/本地时间等待阻塞，新的首次设置任务可能尚未开始；具体入队与最终类型语义须结合并行date-service-set审计，当前不补造完成。

## 逐图确认前后

|步|发送键|截图|实际画面与下一键理由|
|---:|---|---|---|
|0|无|[phaseA-before-SETUP](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap98datecapture600-b6f825f4/ap98-phaseA-before-SETUP.png)|Language页，English首项；日本语/Français/Deutsch/Italiano。 ENTER确认English。|
|1|ENTER|[step-01-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap98datecapture600-b6f825f4/ap98-step-01-key-1ac.png)|Creators App手机设置提示；删除/C4 Set on the camera。 DELETE/C4进入机身设置。|
|2|DELETE/C4|[step-02-key-1f8](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap98datecapture600-b6f825f4/ap98-step-02-key-1f8.png)|Set Area/Date/Time，Enter/Cancel。 ENTER进入区域设置。|
|3|ENTER|[step-03-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap98datecapture600-b6f825f4/ap98-step-03-key-1ac.png)|Area Setting，Tokyo/Seoul，2021-1-1 12:00 AM，GMT+9.0，OK。 ENTER确认当前模拟区域。|
|4|ENTER|[step-04-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap98datecapture600-b6f825f4/ap98-step-04-key-1ac.png)|Date Format，Y-M-D等四项。 ENTER确认当前格式。|
|5|ENTER|[step-05-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap98datecapture600-b6f825f4/ap98-step-05-key-1ac.png)|Date/Time，2021-1-1 12:00:00 AM，圆键OK/MENU Cancel。 额外date-before-confirm截图与原字节后，ENTER提交一次。|
|6|ENTER|[step-06-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap98datecapture600-b6f825f4/ap98-step-06-key-1ac.png)|Auto Power OFF Temp High提示，Set now/Set later。 额外date-after-confirm截图和原字节；不再发键，观察原日期调用能否返回。|

专门补图：[日期OK前](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap98datecapture600-b6f825f4/ap98-date-before-confirm.png) · [日期OK后](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap98datecapture600-b6f825f4/ap98-date-after-confirm.png)。没有更改日期数值，没有继续菜单或拍摄操作。

## 收尾

请求600秒，实际602.902秒；QEMU退出0，reaped=True，PIDabsent=True，输入SHA一致=True，双锁释放=True，missing=[]，early_stop=None。

原assert0，GPE拒绝0，严格health=True；6步/12send/12recv。原同步仍无after，force成功清零与日期请求回复验收未通过；有界观测结束不等于问题修复。

方法沿用[QEMU官方QMP文档](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html)的stop/pmemsave/cont/quit；私有日期协议及状态结论来自固定原件与本轮原字节，不以工具文档替代Sony原合同。
