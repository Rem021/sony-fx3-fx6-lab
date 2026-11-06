# FX3 r31 唯一真实轮：failed；启动观测交付 passed

2026-11-04 PT（原始日志为2026-11-05 UTC）；task_22ac221f3da6 / ctx_e5c0b4fef828。规格SHA：fb6974b46be6e1b41d31c40a91b9308f785233dbc1a4c73559d120e003fae299。

**1 VM / 1 Start；0 attempt / 0 accepted / 0 postkey观察 / 0 pin / 0 confirm / 0恢复**。原180秒内未取得合格待机，启动wrapper原End，本轮菜单目标 **failed**，八步未进入；正常资源回收 **passed**，新增启动观测原件关联核验 **passed**。没有第二次Start或补键，诊断通过不改变原健康/菜单失败。

[RESULT](RESULT.json) · [启动时序](STARTUP-TIMELINE.json) · [新增观测原件审计](STARTUP-OBSERVATION-AUDIT.json) · [未执行步骤](STEP-EVIDENCE.json) · [SHA清单](SHA256SUMS)

| 启动边界 | 本轮原件 |
|---|---|
| 唯一Start POST | 04:42:44.081090816Z |
| 宿主首帧计时起点 | monotonic437449.545704541；原上限180秒 |
| 超时观察 | 04:45:44.518646Z，约180.462秒；first frame not ready by 180 seconds |
| 原End / stop POST | End_invoked=true；stop请求04:45:44.675332096Z |
| 运行总时长 | 184.496秒，低于480秒总预算 |
| 原网页状态 | HAR无ready=true，无带有效sequence的frame状态，结束lastStatus.frame=null |
| final ACK | 04:45:48.854192896Z请求起点，200 acknowledged |

180.462秒是原1秒poll节奏后的失败观察边界，不是放宽180秒资格期限。已实际亲看[End后整页PNG](ended-page.png)：黑色图区显示“本轮已结束”，0键、最后提交帧无、健康未通过；本轮没有合格待机、观察或固定菜单PNG，也没有把cleanup-only帧当启动成功。HAR请求起点、host收到/读取点、guest事件时钟及browser loaded是不同边界；不将fixture回放时间或最终状态倒填为早期成功。

## startup-observation 原件与验证

原生 [/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/v25gate-n64-r17-77e949cd/startup-observation.json](../../runs/v25gate-n64-r17-77e949cd/startup-observation.json) 原件成功写出；schema=fx3-startup-observation-r30-v1，flush_attempted=true、saved=true、errors={}，receipt写入状态一致。文件 **12,210字节 / 262,144字节上限**，serialization_truncated未置位，headers/ready/phases的evicted_transitions、first_kind_omitted与serialization_omitted_recent均0。headers最近48、ready最近32、phase最近8、每流首次类别32、marker白名单14和serial carry42的容量均核回。

[审计JSON](STARTUP-OBSERVATION-AUDIT.json)的65项字段/原件关联检查通过；这是本轮真实证据核验，未复跑43项离线矩阵。保留原startup-observation、receipt、serial与qmp，没有补造任何观察时刻或缺失字段。

**Header：399次均bad_magic。** QMP中对应399条原pmemsave header请求及匹配成功空回复，全部计数一致；保留头的首请求id5（before4/after5）与末请求id420（before419/after420）逐项关联原请求/回复及0x100读取路径。保留initial/last等记录的长度门均见256B，raw16Q全0、来源original_returned_header；最终osd-ring-header-live.bin前128B与last记录一致。中间每次导出的原文件会覆盖，不能独立声称399次所有字节都已另存；准确结论是bad_magic累计399、所保留头全0。QMP空成功不等于有效magic/version/正序号或可显示帧。

**Ready：2620次求值、3次状态变化，qualified始终false。** 原13项操作数保留true/false/not_evaluated；未求值不能补成false或根据末次marker补成true。

| 保留的host观察距Start秒数 | replay_input_verified | screen_open_observed | validated_ring_present | qualified |
|---:|---|---|---|---|
| 0.816827 | False | not_evaluated | not_evaluated | false |
| 9.097277 | True | False | not_evaluated | false |
| 116.660124 | True | True | False | false |
| 180.612018 | True | True | False | false |

phaseA_unobserved在这些记录为true。初始replay为false，screen及其后未求值；之后replay为true、screen为false，后续未求值；最后screen为true而validated_ring_present=false，**从screen_quiet_10s起的9项全为not_evaluated**，validated_ring_identity=null，ready_incomplete=null。marker“存在”与这里的短路结果分开保存。

**Serial marker：9项首次literal命中与原始字节oracle完全相符。** 最终serial恰为3,882,426B，观察consumed_offset与bytes均相等；累计2622个原读取chunk、尾缓存42B。每条首次byte_offset、chunk起止、token长度/原字节和LF收到时间均核回，原包含行hex留在审计JSON。

| marker（末尾空格见原JSON） | 原serial byte_offset | host首次收到距Start秒数 |
|---|---:|---:|
| FX3_FILE103_READY_CONFIRMED | 80417 | 4.232324 |
| FX3_SYNC100_BACKEND_BOUND | 80907 | 4.232324 |
| FX3_BACKUP_INSMOD_RC=0 | 82403 | 4.286949 |
| FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN | 96716 | 8.674161 |
| FX3_AP_NATURAL_BOOTIN_BEGIN | 97275 | 17.109892 |
| FX3_KEY96_READY | 1049853 | 38.524577 |
| FX3_AP89_SCREEN_OPEN_ENTER | 2457422 | 116.658718 |
| FX3_AP89_SCREEN_CREATE | 2463166 | 116.831927 |
| FX3_UI_CONFIG_DONE | 3194349 | 145.530156 |

FX3_TIMER_ENTRY、FX3_UI_FILL_EXEC、FX3_OSD_HEADLESS_COPY、FX3_OSD_FRAME_TARGET_VALID、FX3_OSD102_COMMIT五个精确白名单token未在本轮已消费且完整保存的raw serial中出现；这不是“guest从未执行相关私有动作”的证明。首次完整token收到与LF收到分别保存，均不当作guest发生时间、完整记录语义或browser loaded；guest时钟只保留于原始行，不从host收到时刻反推。

阶段startup→cleanup→after_cleanup均保留。startup观察器在runner构造时即创建，初始phase早于Start；阶段结束点是原runner finally进入cleanup，因此startup标签尾部也可能晚于180秒/End请求。末次header/ready约在Start后180.612秒，不能算入180秒资格窗口或倒填成功；cleanup本轮没有可提升为startup ready的有效帧。原始阶段时间与serial offset完整保留。

## 资源、输入与未验项

正常清理全通过：API16原字节 **000b00b4fd7bbba9fd030091f35301a9**，guest restore_seen=1，**2.638524秒 / 原20秒预算**；所有原始header/API16读取和最终16字节留存。QMP quit id487返回{}，QEMU exit0/reaped；runner14327、QEMU14538、自有browser daemon14346均absent，双锁独立探测free，63982端口closed/lsof无监听，网页finalACK成功，浏览器close成功/session inactive。见[CLEANUP](CLEANUP.json)、[独立清理探测](INDEPENDENT-CLEANUP.json)及原生run下restore103-receipt、qmp、resource-guard、receipt、trial-web-final-receipt。

全部467条HTTP请求保存在[traffic.har](traffic.har)，[原POST body](HTTP-POST-ORIGINAL-BODIES.json)只有Start1、stop1、final-ack1；key/snapshot/confirm均0。拒绝导出原件304字节，total=0、truncated=0，SHA d7abb984034ce7a3b90576bf384bb885e5337c1ffece2ffc32d32373771194bc。完整serial.log保留；[按键原行导出](NATIVE-KEY-ORIGINAL-LINES.bin)故意为0字节，[索引](NATIVE-KEY-ORIGINAL-OFFSETS.json)绑定原serial SHA并说明本轮没有down/up/done。attempt/nonce/snapshot/confirm身份不存在，不虚构；launch与页面原字节保留。

Start前真实Node预绑定本r30 short_tool，并在下一独立工具确认函数存在、显示明确历史样本，证据[PRESTART-NODE-DISPLAY](PRESTART-NODE-DISPLAY.json)。新adapter/operate/core均实际import绑定r30；startup_observation、reader、monitor、PAGE来自r30，QMP/input/resource/restore来自冻结r21。因未到待机，未调用standby_review/任何按键动作，生产tool-return目录为0，原20秒alarm已安装但从未armed。没有解析截断stdout、旧current-return兜底、自动语义或动作重试。

前后冻结相同：100项交付、41生产源/36core、本轮运行前后94项原件复核；r30历史94项原采样时序仍按其原分组，不声称其全部在原任务起点采过。实际preflight原r21/r24/r25清单、source40、fixed14与真实QEMU均匹配，import前后路径/哈希一致。固定4×cortex-a35 /5120MiB/MTTCG/noicount，kernel da4a66fa…、DTB5aa2beac…、N64 CPIOaaf00661…、实际QEMUbf4d4648…不变。完整hash与依赖路径见INPUTS、SEALED-DELIVERY、ACTUAL-IMPORT前后记录及ACTUAL-DEPENDENCY-BINDING；实际argv来自runner command.json及trial-session PID，独立live ps argv采样未达原“合格待机后”采集点，额外采样为unknown，不伪造。

原健康/render_pass/standby_ready未通过；protocol/lifecycle回收结果分开保留。v5tail仍非事务，snapshot_is_end_state=false、post_snapshot_event_counts=unknown；模型收图/思考/调度不可分离仍unknown。未修底层backlog，完整八步及真实arm+5秒观察/pin/confirm/恢复链均未验；未部署、未改源码/平台/输入门/180或20秒、未写旧runtime自然输出或协调ledger，部署仍r10，历史失败保留。不泛化4096键/60分钟/所有菜单/录像/实机/FX6，本dispatch无第二Start权限。

原生run：/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/v25gate-n64-r17-77e949cd。任务入口：[README](README.md)。
