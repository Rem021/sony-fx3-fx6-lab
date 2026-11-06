# AP87 UUD 队列与首屏观测

**0402/0404、人脸删除和队列11项均已自然完成，尚无菜单。** AP87-r2完整300秒窗口后，AppFw的三轮实际快照仍在 `Backup_reset_all` 相关内核同步收包路径；未执行新的GPE绘制，不能把开屏入口参数当作已完成画面切换。

## 运行与边界

|轮次|run|实际耗时（含收尾）|结论|
|---|---|---:|---|
|初轮|`ap87uudqueue-7d78fa20`|103.658s|为修正被动标签/生命周期保护主动停止；协议已消费，缺显示marker|
|r2|`ap87r2native-51e93181`|301.317s|300s窗口完成；新原生Backup等待，首屏仍未验证|

两轮均qemu_exit0、process_reaped、inputs_unchanged、hostPID不存在、两锁独立释放核验通过，末尾 `/proc/222/maps` 含im.elf；r2最后实际uptime299.37秒。无新fatal/symbol或SYS配置拒绝。**r2 missing非空**：FX3_GPE_CMD、FX3_OSD_HEADLESS_BOUND、FX3_OSD_HEADLESS_ACK、FX3_OSD_NATIVE_SIGNAL、FX3_OSD_DRAW_WAIT_RETURN、FX3_OSD_LIFE_ALLOC_BEGIN、FX3_OSD_LIFE_ALLOC_RETURN、FX3_OSD_LIFE_SEND、FX3_OSD_OWNER_START、FX3_OSD_OWNER_CURRENT、FX3_OSD_OWNER_FREE、FX3_OSD_LIFE_USER_FREE、FX3_DISPLAY_WIDGET、FX3_DISPLAY_GRM_DIRTY。这些显示/OSD观测点没有到达，不能删除门槛或宣称完整菜单验收。首轮另有错误数值30386专用marker缺失，r2用真实raw30086替代；历史回执保留。

基线为Lead验收AP86Bv2，capid44只新增0402/0404配置设备模型；headless5/lifetime2/GPEv14guard等不变。display3→4只修被动解码、active-controller生命周期保护、1098字节读取和代理请求观测；原40点指令保护、ASM和协议件不变。宿主ASan/UBSan检查通过，guest GPR31/SIMD32/NZCV/FPCR/FPSR/SP及NOP/CBNZ/BL自测通过。原审计70块/12输入身份核对通过；原件、旧runs、旧helper未修改。

## 软件配置与原清理推进

0402原10B `0d2002040a0001800000`，独立12B `0d2002140c00018000000000`；0404先捕获完整12B `0d2004040c00018000000000`，与同线程活task的四个32位原字段均0、低8位逐字节一致后才回 `0d2004140c00018000000000`。两者都由本轮source81cf61c4原AP消费/free0，converted_result0并返回；没有跨run固定source。保存的counter后端仍pending，不代表物理timecode。独立分配/发送失败回滚、source/重复lease/thread/epoch/四字段不符拒绝已做宿主负例；原request始终caller owned。

原local DMM1dc动态handle0412实际完成20/24/25/23，不虚构固定handle；remote1db handle840a/活代次1 op21按本轮请求打开到opens2并消费/free0，已有字节区保持。原0206/24B登记更新继续no-wait，不补reply；捕获的reserved原字节不推定为固定0。清理任务实际返回，并自然送出删除完成事件。文件/物理CP功能不由这条软件消息单独验收。

**数值更正：完成事件是0x30086，不是审计文字30386。** 原2b8036c MOV86、370 MOVK3<<16、374 STR；r2 LF18476发送点读取原message_pointer首word30086，LF18477真实28B `86000300000000000000000000000000000000000000000000000000` /source830128/caller2eacd4c，LF20038原AppFw manager收到30086。没有合成事件。旧v3把发送点x0指针低32误标event，已改为pointer+读取word；capid44保留的30386专用被动标签不作验收依据。

0400检查点排队的11项已逐一补齐，按本轮真实pointer+run地址、LF顺序约束首个before_run→after_run→pre_completion→post_completion→queue_continue；后续同地址复用另行计数，不能冒充原实例完成。RTTI均从原ELF表独立解码，完整字段/行号见runtime/ap87r2-task-lifecycle.json。

|队列索引|原RTTI|run VA|结果|
|---|---|---|---|
|0|29sequence_sys_set_timecode_run|0x2dca7fc|5阶段原生生命周期通过|
|1|32sequence_sys_set_timecode_preset|0x2dca610|5阶段原生生命周期通过|
|2|35sequence_delete_all_individual_face|0x2b7f8cc|5阶段原生生命周期通过|
|3|25sequence_set_release_lock|0x2d9ac90|5阶段原生生命周期通过|
|4|23sequence_set_off_factor|0x2d95774|5阶段原生生命周期通过|
|5|25sequence_set_release_lock|0x2d9ac90|5阶段原生生命周期通过|
|6|29sequence_high_speed_next_boot|0x2bb9974|5阶段原生生命周期通过|
|7|25sequence_set_release_lock|0x2d9ac90|5阶段原生生命周期通过|
|8|25sequence_set_release_lock|0x2d9ac90|5阶段原生生命周期通过|
|9|20sequence_set_af_area|0x2d74344|5阶段原生生命周期通过|
|10|25sequence_set_release_lock|0x2d9ac90|5阶段原生生命周期通过|

release任务包含原selector3/token80000033/额外字段3，沿已有空闲403d/f000合同或原引用计数省略提交返回；不因task名捏造wire token、40a5回复或lens-ready。

## 画面、GPE 与新等待

原表映射：2ae=`scr0039_boot`、2af=`scr0039_shutdown`、407=`SCREEN_NONE`。初始open_screen_ii参数407/2ae/407；30086接收后同manager第二次入口参数2ae/2af/2ae。**这是三参数请求组，不证明已切换到shutdown。** 最后开屏前活动controller为2ae/`23scr0039_boot_controller`，pending407、boot标志110c2/110c3=1/1，date187=0、force1098原byte1、mode143=2、option145=6，d22=MONITOR1、270=7、243=2。没有该创建调用完成后的新manager状态，不能伪造最终screen。

|GPE统计|结果|
|---|---|
|实际GPE命令总数|0|
|FillRect/BitBlit/Flush|0/0/0|
|v14近似混合/被拒参数|均未调用；无可列拒绝参数|
|新1003/1005/Widget/GRM dirty|未到达对应观测点|
|非均匀读回与PNG|无帧可读回；PNG数量0，未生成空白替代图|

此前AP86B的清屏/Flush不能借给本轮。OSD ring未初始化，display镜像依赖其magic，故本轮全零header表示**镜像不可用**，不等于零Widget/dirty计数；以实际serial入口证据为限。

三轮AppFw324实际/proc快照LF22896/37338/51781均为sleeping，fd3/ioctl80000005。原内核栈：`osal_rcv_msg_tmo+234 [osal_uipc] ← ffffff80004ea524 ← Backup_reset_all+48 [backup] ← backup_osal_call_func+354 ← backup_put_cp_wt_data+23c ← uipc_oom+88 ← __osal_snd_sync_msg+17c ← ioctl`。这是实际栈，符号外延/内部消息raw仍需原module审计；不能依据uipc_oom名字宣布内存耗尽。最终normal-vpool free83712/524288、waiter0。86f skip只证明背景tid249/318有未建模请求，未证其阻塞AppFw。已向Lead escalation，未回复未知请求、清flag或跳过原调用。

## 回执索引与开放项

runtime/ap87r2-review.json：完整退出/回收/输入/锁/末尾maps、协议、原消息/代理raw与栈；ap87r2-post11a-requests.json：11a之后全部实际捕获请求的LF时间线（底层capacity_drop182/lock_drop1，不能称全局无损）；ap87r2-task-lifecycle.json：11项身份/首个生命周期；ap87-screen-name-table.json：原screen名表。宿主检查分别为helpers/sys87-host-check.json、display-observer-v4-host-check.json、delegated87-host-check.json。

仍开放：Backup_reset_all内部同步设备合同、实际创建/画面切换返回、原可见Widget/资源/dirty、新GPE与非均匀像素、菜单输入反馈。STATE保留AP86Bv2为preferred健康基线，本轮只记录新设备合同已推进及新等待，不提升菜单/物理相机验收。

联网复核的[A7C2固定维护者进度](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/2026-10-31-current-progress.md)记录原界面已有证据、拍照录像仍未贯通；本轮只参考分层验收方式，没有移植地址、成功通知或用其菜单替FX3补证。
