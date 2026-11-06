# CAPID共享表与地址转换继续修复

2026-11-01。AP41–45新增五次原生QEMU运行，均host QMP退出0、reaped、输入SHA未变、无guest异常。**AP45已走通CAPID初始化与一条SA地址转换，当前停在原VDF032d请求，尚无GPE绘图或原UI帧。** AP44中途回退等待的反例保留。

## 原CAPID接口与独立内存

在FX3原libmpr.so（SHA9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c）定位19个capidtbl导出函数。SendCapIdTblCommand为13133c：目的9004015e，分配/复制24B请求；1000的回复在+8读取64位表地址；1001/1002为访问开始/结束；1003无完成回复。Mmap、MakeCapIdTbl、ResumeCapIdTblSync等原字节分别保留，未复制A7C2私有偏移。

复用固定提交的[CAPID存储核心](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/capid-service.c)作为明确软件模型，无capture生产者。表为0x4014B，含5个u32头与1024×16B条目。独立选41d800000/64KiB，对照本机FX3所有原memrsv和FDT reservation无重叠；新FDT reservation与原内核memrsv参数同时排除Linux分配，不采用上游4102e0000。原内核日志实际确认memrsv10000@41d800000，原进程有对应/dev/mem映射。

只在第一次目标请求上初始化，guest内使用O_EXCL/NOFOLLOW、0600的/tmp/fx3-capid.claim与PID所有权，防止bootin父进程或后续进程重复清表。v2起，已租用回复的释放也检查PID。请求只在成功提交后交原release；发送失败回滚表/锁状态、释放自己分配的回复并保留原请求。没有在发送后继续读取已转交的消息内容。

核心及传输host ASan/UBSan覆盖owner、环形边界、非法参数、分配/发送失败、回滚、无回复完成、原请求/回复租约与跨PID释放。Darwin初次链接缺Linux errno accessor，后由独立测试harness提供errno存储；native ABI未因此改变。

## 真实原AP消费与独立读回

AP41/42/43/45均实际完成以下序列：

1. 1000取地址→原AP释放16B回复0。
2. 1001开始访问→原AP释放8B回复0。
3. 92850750同步op1→真实原AP写入header=1024/1023/1023/1023/0，释放24B回复0。
4. 1002结束访问→原AP释放8B回复0。
5. 1003初始化完成→无回复，模型initialized=1。

QMP暂停后独立读回64KiB物理RAM，表头与日志相符，1024条目均零。AP41/42的RAM完整SHA均为2bde59e9a95f1dea99311cea8330e866b17ce3654158dbbbe226c9ef13df57e1。它证明当前软件存储确有字节，不证明原CP运行或拍摄记录生产。

## SA范围转换及证据边界

原SeqQueueCommon随后发00930101/b850。FX3 av-cam原件中336370/336390/3363b0三个32B记录的前三u64与[参考SA转换模型](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/sa-address-service.c)的范围一致：AP4G→CP0、AP5G→CP4G各4GiB，以及fe000000→3fe000000/6c0000。

这**尚未闭合原FX3 b850消费者到记录的函数引用**。source-ranges-v1是明确的虚拟范围转换合同，只计算地址，不宣称执行原CP处理器；未覆盖地址回复显式错误。80B边界、源队列、原分配/发送/释放与回复租期保留，host检查含正向转换与发送失败归还。

AP43/45实际输入为原DMM分配中的43fffa000，转换输出3fffa000，status0/detail0；原等待队列803c6186收取并释放回复0。未向该DMM缓冲写像素或虚构捕获状态。

## 保留的回退及修复

AP42将CP更新器不可用限制收紧为原libupdaterufp+1984、精确8B、命令4。AP44新增最外层被动观察后，编译器未维持中间tailcall，内层看到的caller变为观察库，严格校验未匹配，原CP4于是被委派后等待；未走到CAPID/SA。该run无异常但不计初始化通过。

AP45把严格校验移到最外层入口，并在模型锁外调用dladdr，不再依赖中间tailcall。host的正确调用者/错误库/错误长度/错误命令测试通过，native再次实际拒绝原8B命令4且保留原错误处理。没有放宽为任意成功或跳过原释放。日志FX3_CP_VERSION_UNAVAILABLE沿用旧名，语义仍为更新器控制不可用，不是CP版本读回。

## 当前阻塞与下一步

AP45被动记录：92840747、10B，原始字节0d202d030a0001800000，即frame200d/cmd032d/length10/flags8001/payload0000；source81cf6186。实际caller按本run映射绑定原appFw.so+2de7264。只观察并委派，未添加VDF回复。

已取得的显示尺寸参考函数只接受016a，并不匹配032d。下一步应从[vdf032d原请求与原指令](../../work/fx3-vm-20261101/menu-repair-01/runtime/vdf032d-request-proof.json)追FX3处理状态及完成格式，不能把不同命令套成成功或写死显示尺寸。GPE仍为有界请求观测/不写像素的诊断，原UI、Lz77/bitmap租期、键到新帧、长期运行、guest关机和capture均未验。

## 可复核入口

- [五次运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/capid-sa-run-summary.json)、[当前状态](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)。各run保留serial/printk、QMP、RAM和receipt。
- [原libmpr完整证明](../../work/fx3-vm-20261101/menu-repair-01/runtime/capid-mpr-full-proof.json)、[保留区排除检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap41-capid-storage/exclusive-reservation.json)、[SA数据候选限定](../../work/fx3-vm-20261101/menu-repair-01/runtime/sa-address-table-candidates.json)。
- [核心host检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/capid-host-check.json)、[最终传输/所有权/调用点检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/capid-sa-outer-host-check.json)。
- [五份CPIO中实际helper字节核验](../../work/fx3-vm-20261101/menu-repair-01/runtime/capid-helper-provenance.json)：guest旧路径fx3-capid-v1.so实际最终为编译v5，HDMI旧路径实际v3；部分继承build描述文字陈旧，以实际CPIO摘要及这份逐字节检查为准。历史候选/收据未改写。

外盘身份已核；项目目录非Git。所有更改在任务work和阶段回执中，原固件/冻结runtime保留。无物理相机、USB、网络设备或主机磁盘透传，无残留QEMU。
