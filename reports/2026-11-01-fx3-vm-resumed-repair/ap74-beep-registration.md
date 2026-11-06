# AP74 提示音描述符注册

240秒运行`ap74beep-6da60e1e`宿主收尾正常（qemu_exit=0/process_reaped=true/宿主PID消失/inputs_unchanged=true/两锁实际重取释放），但guest进入exception monitor，**本轮业务验收失败，四任务屏障未越过**。missing_markers=[FX3_GPE_CMD]，末次snapshot3未完成，不能通过健康主进程存活验收；无新symbol lookup error。

capid v27仅新增静音327/32a描述符和音量保存，校验已绑定64KiB物理区、长度/填充/注册字段/priority、同kind冲突，支持注销及kind0音量更新。冲突/音量越界只拒绝并记录原状态e004/e002，不发送伪成功或主动错误回复。宿主ASan/UBSan正例、重复相同描述符、冲突、越界、index6注销、音量、发送回滚及所有权检查通过。既有v26/v12未修改；GPE仍v13，未处理libObj帧握手。

前9轮327/32a共18个实际请求均有native free result0：

| kind | phys | size | volume | 327/32a lease | free result |
|---|---|---:|---:|---|---|
| 1 | 0x41da00000 | 256 | 7 | 29/30 | 0/0 |
| 2 | 0x41da00100 | 2944 | 7 | 31/32 | 0/0 |
| 3 | 0x41da00c80 | 2944 | 7 | 33/34 | 0/0 |
| 8 | 0x41da06380 | 5568 | 7 | 35/36 | 0/0 |
| 7 | 0x41da05840 | 2880 | 7 | 37/38 | 0/0 |
| 9 | 0x41da07940 | 2880 | 7 | 39/40 | 0/0 |
| 4 | 0x41da01800 | 3712 | 5 | 41/42 | 0/0 |
| 5 | 0x41da02680 | 3456 | 6 | 43/44 | 0/0 |
| 6 | 0x41da03400 | 9280 | 6 | 45/46 | 0/0 |

本轮kind4走注册（register=1）；条件注销仅宿主覆盖，未冒称guest执行。后4项未发327/32a，不能报告26包全通过。

首个文件分支serial13914到9061003c发送40B：

`200000001708070000000000ffffffff000000000000010000000000000000000000000000000000`

caller为appFw+0x2e4f0e4，source81cf61c1。既有remoteDMM仅支持unit63a，serial13916对unit70817返回status=-3/handleffffffff/address0，此回复亦按既有lease释放。随后14156..14158 assert，16165 Abort，16170 Entering exception monitor。原异常FP链`7f17c2c5d0→7f2ca00c54`归一appFw+0x2b60c54、下一帧+0x2b61de4，和静态文件DMM失败分支一致；故障链依据请求、回复和异常栈关联，不是把无日志等同成功。未新增DMM单元或伪造后4项成功。

| 四任务项 | 已有证据 | 完成句柄/屏障状态 |
|---|---|---|
| 音量adf_set_volume_i | 032e回复消费并free0 | 业务调用已返回；匹配完成句柄未直接证明 |
| 提示音regist_beep_signals_i | 9轮18包free0，后4项文件DMM失败后assert | 未完成，不能贡献成功屏障计数 |
| license_get_i | 三种id的HasPublicKey/PrivateKey六次均原厂0 | 完成句柄未证实 |
| adf_get_func_i | 未捕获325/8B或1325/28B | 未证实，不能把32d当作325 |

5503e0原包/TID/调用栈仅被动记录，未找到可可靠归属四项的匹配完成句柄；未补造屏障计数，因此不提供“屏障之后”的时间线。0x11a之后本轮trace输出的全部发送证据及异常原始栈在[完整JSON回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap74-review.json)，trace仍有原有去重/预算边界。

已向Lead升级；Lead安排adf-beep-file-dmm审计，明确要求完成本轮回执后待下一份合同，当前无QEMU。没有菜单、声音、像素或实机验收。
