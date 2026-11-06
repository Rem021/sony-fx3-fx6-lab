# FX3 原 UIPC 模块与应用运行边界

## 原模块加载顺序与成功案例是否一致

### Takeaway
已经沿公开 A7C II 成功菜单案例和 FX3 原 initrc 装入三个原模块；guest 中三项 insmod 返回 0，模块 Live，devtmpfs 自然建立 `/dev/uipc`。此前最小包的缺节点问题已修复，没有伪造 ioctl 或 mmap 成功。

### Cited Findings
- A7C II 成功案例的 guest 环境文档明确使用 devno→osal_utm→osal_uipc，再加载 utimer／Backup 等。具体源码先 devtmpfs，三模块后直接 `ls /dev/uipc`，自然菜单 profile 不依赖额外 `echo set`。— [固定成功案例](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/03-guest-environment.md)、[实际 setup](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py)
- FX3 原 `/sbin/initrc/insmod_drv1` 先装同包 nflasha7 的 devno，`insmod_drv2` 中 osal_utm 在 osal_uipc 前。两脚本的原 inode/SHA 与字节已保存，未执行完整脚本。— [本轮原成员清单](../../original-uipc/original-module-probe01.json)
- 三个原模块 vermagic 均为 `4.9.337-scel+ SMP preempt mod_unload aarch64`；uipc 的 47 个静态未定义符号已有同包内核44项、osal_utm两项、devno一项闭合来源。新 metadata 与旧核验相同，实际加载由下条单列。— [本轮原模块元数据](../../original-uipc/original-module-probe01.json)、[先前静态提供者](../../../../sony-firmware-20261024/stage63-resource-message-boundary/additional-provider-audit.json)
- `uipc02-bcaa02bd` 实际运行：三项 RC0、`/proc/modules` 中三模块 Live、`/proc/devices` 显示 `251 uipc`，devtmpfs 自动建立 character 251:207 的 `/dev/uipc`。原模块与内核未改，原 errno ENOENT 消失；原 im 进入真实 UIPC 操作并产生逻辑服务返回。— [独立读回](../../original-uipc/uipc02-independent-readback.json)、[同次串口](../../runtime/runs/uipc02-bcaa02bd/serial.log)
- candidate01 的模块成员先于新增父目录，造成 Linux initramfs 未保存这些文件；insmod ENOENT 属本轮包布局错误，不能当驱动不兼容。candidate02 保留旧失败，只修成员排序和 devtmpfs。— [修复记录](../../original-uipc/original-module-probe02.json)、[独立坏包审查](../../runtime/candidate01-unpack-order-failure.json)

### Inferences
- 原 kernel+原 UIPC 驱动可以直接运行，当前不需要以成功 ioctl 替身绕过驱动。
- 保留原模块和真实 devtmpfs 比创建空文件或未注册节点更能验证原初始化路径。

### Gaps
- 当前只验证三个 IPC 底座模块；utimer、Backup、DMM、UPM 和显示服务没有因此成为已完成。

## 设备节点与 ioctl 映射合同是什么

### Takeaway
原 UIPC 驱动的设备号、16字节 ioctl 外层记录、2MiB 用户映射和进程归属均有原字节依据。已从真实原 ioctl 捕获 op5 和三个目标；Backup、ulogio 和原 im 自身实例探测分别闭合，详见下方实测增量。

### Cited Findings
- 原 uipc `.data+0x1a8` 对 `udif_devnodes` 的唯一 ABS64 重定位加数112，指向 devno 原表第7项；原 GPL UDIF_DEVNODE 布局解为 char／major251／minor207／count1。— [字节与表项证明](../../original-uipc/original-uipc-devnode-proof.json)
- 原 dispatcher `.text+0x4d8` 将 request 去掉bit31后限制0..16；arg为16字节记录，record+0 u32供 handler 第一个参数，+8 u64供第二参数。普通操作要求 opener mm 与当前 task mm 一致且 userbase 非零；init16可在映射前使用。原 mmap 要求恰2MiB。— [原指令](../../original-uipc/original-uipc-return-code-proof.json)、[相同原模块的既有指针映射研究](../../../../sony-firmware-20261024/stage113-native-uipc-mapping-guards/README.md)
- 原用户库 `.init_array` 重定位包含 `u_osal_init`；其调用 `u_uipc_init`／`do_init`，后者调用原 open→ioctl→fcntl→mmap→fblock/lock初始化。错误可发生在 main 前，不应凭 exec 参数推断 qemu 分支已执行。— [原库初始化与 PLT 证据](../../original-uipc/original-libosal-uipc-init-proof.json)
- 本次45个-1020和TERM后5个-1021来自真实原模块，不是主机替身。原-1020只见于同步发送/finish callback的队列查找失败或 callback/state 指针为空；参数/mm守卫返回-22或-1024。-1021可由 callback等待或消息／信号量等待在 schedule 后检查当前task flags bit0的退出分支产生；原 timeout 分支是-1022。— [返回分支原字节](../../original-uipc/original-uipc-return-code-proof.json)、[日志计数](../../original-uipc/uipc02-independent-readback.json)

### Inferences
- -1020与队列或接收者尚未注册的逻辑状态相容，不能当 UIPC 驱动或 ABI 不兼容。
- TERM后-1021与被打断的等待相容，但未取得 op/SID 时不指定唯一来源，也不替换返回码。

### Gaps
- 现已取得请求号、实际目标、16B 原消息头；没有任意栈访问或精确运行 PC 采样。
- candidate03已实际跑出2MiB原共享映射和5线程；candidate04–09增量见下。— [独立03读回](../../original-uipc/uipc03-independent-readback.json)

## 下一层原服务应如何按成功案例验证

### Takeaway
优先匹配已成功案例中的实际请求族，再启动相应原服务；不先叠加定时器、Backup或远端 ACK。

### Cited Findings
- A7C II 原菜单同类-1020曾由 BusPower同步消息未有receiver引起，修复使用原 `libBusPower.so` + `BusPower_Init`，并在 appFw／MWF 映射后启动，过早 constructor dlopen 曾失败。— [固定观察器](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/menu-observe.c)
- FX3 原 `libBusPower.so` 同样导出 BusPower_Init、preProcessCateBusPower、funcOsalSyncCb，原 MWF 也有 MWF_Init；文件与 ELF依赖已只读提取，未执行这些入口。— [FX3原服务候选](../../original-uipc/original-buspower-candidate-metadata.json)
- 原 `utimer.ko` 依赖 osal_uipc 并调用 Sony hwtimer_*；原 backup 还用 pcidma/cache/CP，stream 主要依赖内核页映射与 devno，upm 依赖更重。元数据不能当这些设备已初始化。— [追加原模块元数据](../../original-uipc/additional-original-module-metadata.json)

### Inferences
- 若实际请求属于 BusPower族，应优先在原程序正确加载时点接原 BusPower入口，避免统一假成功。
- 若实际请求是计时器、Backup或远端公共SID，则分别追原模块与sender协议，不能混用 BusPower修复。

### Gaps
- 原菜单出帧、输入、设置保存、CP与成像均未验收，当前仍需依据真实请求推进。


## 真实请求、原服务及启动合同（2026-11-01 更新）

### Takeaway
原 UIPC、Backup、ulogio 和真实 cpuset 已分别在同一原 FX3 内核上运行。当前两类原服务同步传输成功；一次原 im 自身存在探测的 -1020 由原代码正常容忍。尚未输出原菜单画面，下一步是用完整原资源和原 bootin 的 stage 参数自然启动。

### Cited Findings
- candidate04只增加透明 `ioctl/mmap` 观测。真实原 ioctl 仍执行，-1020已定位到op5；但原内核 `sys_process_vm_readv` 槽270指向 `sys_ni_syscall`，所以这版观测读失败不表示原指针坏。candidate05改为只读 `/proc/self/mem`，156个外层16B及op5嵌套24B记录读取成功；PFNMAP正文仍GUP EIO。candidate06只在实际原 `/dev/uipc` 2MiB mmap登记范围和已hook生命周期内，有限读取当前消息头16B；未知指针不解引用，原参数/调用/返回不改。— [内核syscall原字节](../../original-uipc/original-process-vm-readv-unavailable-proof.json)、[04–09独立读回](../../original-uipc/uipc04-to09-independent-readback.json)
- 06的45条原op5：`008f013a` 42次、`003e014d` 2次、`0094016a` 1次，均原return-1/errno1020。Backup两条正文首word9，参数数目3；日志正文是命令9和ASCII；实例查询正文是`009400e1/0/0/0`。不能把初版观测未读取时的arg0=0当真实目的。— [同次串口](../../runtime/runs/uipc06-9f4ba70e/serial.log)
- 原 FX3 `backup_osal_init` .text7920/24构造003e014d，7934真实注册同步callback。callback指向74e8，再派发到`backup_osal_call_func`。selector9跳表index10=237，7b1c+237*4=7ed0，7ee0的CALL26绑定原`Backup_write`，结果写消息+4。它不是CP远端903e0811，也不是上游selectorf保存实验。— [原注册](../../original-uipc/original-service-registration-proof.json)、[独立派发与依赖闭合v2](../../original-uipc/original-service-dispatch-proof-v2.json)
- 同机官方FDAT中 `CX95900_ALLLANG.bin` 2229740B/SHA bf3a9d85…及`0800_appli/setting/ulogio.bin` 2784B/SHA dd5a1729…已独立提取，原FDAT全SHA、tar头、Backup官方CRC及双bank求和均核。原Backup文件header p32 04000000经原内核转换为404000000；加载前新增FDT memreserve大小221000，保留原线性映射并避Linux分配。模板仅为隔离VM公开默认值，不是用户机身备份。— [种子来源](../../original-uipc/original-service-seed-provenance.json)、[07b准备范围](../../original-uipc/original-backup-probe07b.json)
- 07b原backup.ko RC0/NO SAVE MODE，两条selector9的原op5由-1/1020变return0。08再加载原osal_ulogio.ko+官方ulogio.bin，RC0，42条日志原op5均return0；原ulogio真实注册8f013a→handler8f0。09只补成功案例原cpuset setup，真实mount和7组mems/cpus全RC0，先前cpuset WARN消失。源件hash不变，guest退出回收；BusyBox确实缺sha256sum applet，所以没有宣称guest SHA通过。— [实测增量](../../original-uipc/uipc04-to09-independent-readback.json)、[09原始回执](../../runtime/runs/cpuset09-d7ff98be/receipt.json)、[成功cpuset源码](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py#L1119-L1120)
- 原im的4038d4精确构造94016a/009400e1查询；同步失败则free后返回false，成功才检查原receiver回填magic12345678。main402588只在存在旧receiver时转离启动，稍后402600注册自己的callback402e08。06真实seq38 op8/94016a/result0与原注册wrapper request80000008相符。op4 seq147则是另一异步消息80920021，不能当940注册。— [实例探测完整原流程](../../original-uipc/original-im-single-instance-probe-proof.json)、[真实注册API进度](../../original-uipc/original-uipc-main-registration-progress.json)
- 原bootin将dmode3正规化成`s g r u l i a `，拼接原im+debug+target+stage+lazy-global，再真实按空格拆token并fork/execve。原target argv不补空格，所以已核可用启动参数为`bootin.elf 'target=qemu ' dmode=3`。此前direct im target=qemu缺这些stage，不应以无appFw映射判断原应用不能运行。— [同机原字节启动合同](../../original-uipc/original-bootin-launch-contract.json)
- 原AP投影v3已提供332成员（302普通文件/21原链接/9父目录）、348740648B、90入口根和1356条DT_NEEDED边，未解析DT_NEEDED=0。含原appFw/libObj、完整/usr/share/app以及外层tmp/images字体；原IMDB225条entry/qemu mask2逐条保留。105泛IMDB名称没有同机独立文件，这只是原表名称与实体的区别，尚不将其称为必须文件缺失；成功import原样rdump，未为每个名字造.so。— [投影v3](../../original-uipc/ap-projection/projection-manifest-v3.json)

### Inferences
- 通过的原op5只证明真实callback传输。还没有透明采样原Backup消息回填+4，不能把ioctl0等同于Backup_write业务成功，更不能称文件保存/跨VM恢复成功。
- 94016a的单次失败是原容忍的无旧实例查询，现不需外接接收者或假回包。
- root已澄清允许隔离guest中原相关库正常idle初始化；投影v3已恢复原Jiritsu/updater库及依赖。没有运行独立载荷、更新工作流或真实传输；若出现实际更新流程应停下溯源，不能把NO_CP_UPDATER称为未执行初始化保证。
- 由原bootin自然拉im并验证真实stage/资源，比继续打磨观测器更接近菜单主线。

### Gaps
- 原菜单/OSD出帧、输入、正常服务链与成像没有通过；UIPC/Backup/ulogio成功不升级为整机VM正常运行。
- AP投影仅静态、未执行新库；原bootin启动及实际子进程argv/加载状态由host后续候选独立验。
- v1投影JSON曾发生ELF e_type覆盖CPIO type的元数据错误，未用它构建CPIO；v2已分离elf_type并重读全部SHA/成员类型/父目录，旧记录和修正保留。— [修正](../../original-uipc/ap-projection/projection-v1-serialization-correction.json)

- 投影v2的DT_NEEDED/IMDB根实际上未纳入原im硬编码动态路径libObj.so，先前消息声称包含它不准确。v3已补原libObj及递归依赖、全部payload重读SHA；host已在执行前获通知。此为提取清单修复，不是机型硬件问题。— [修正记录](../../original-uipc/ap-projection/projection-v3-loader-literal-addition.json)
- 原im两条loader在entry+0xe非零时，分别选择真实dlopen(NULL)或原/usr/lib/libObj.so；17个缺同名实体的表项有该字段，其中16个init符号在原libObj导出中实际存在。因此不能将全部105个表名字当必须同名文件，也没有造.so或虚拟handle。— [原loader分支与原导出](../../original-uipc/original-imdb-alias-loader-proof.json)


## 完整原文件投影 full-v4（主线更新）

### Takeaway
已改为成功importer的完整原文件策略，不再以DT_NEEDED/IMDB白名单充当完整资源树。full-v4只准备文件，尚未因此执行原rootinit、模块、库或脚本；host独占实际VM运行。

### Cited Findings
- 最新轻量入口为[latest-projection.json](../../original-uipc/latest-projection.json)，指向完整manifest并固定SHA `3e295b9f0b362754c46ec507abeb8a607aa328a166eb3b89e13a51672f91aa77`、源快照SHA、版本和生成状态。Manifest含每个guest path到真实host payload或原link bytes的索引，不能按guest路径猜host文件路径。
- 完整原nflasha15 `/usr` 为915节点/797普通文件/86链接/32目录/435648400普通字节；原nflasha7完整rootfs为153节点/50普通文件/70链接/33目录。逐项重走原ext2目录并与旧索引完全相同，保留原partition/inode/mode/uid/gid/time/nlink和原inode字节摘要。
- 完整原`0800_appli/`另35归档成员（24普通文件、1原链接、10目录），原tar头名称/类型/长度/checksum均核。经目录覆盖，最终1099成员=871普通文件/157原链接/71目录，448734061B。新c_ino为独立归档命名空间，原inode仍单列保留；原两文件系统没有常规文件硬链接，不静默扁平化链接。— [完整manifest](../../original-uipc/ap-projection/full-v4/projection-manifest-full-v4.json)
- 组装门发现原Linux xtables存在9对仅大小写不同的库，而host盘不区分大小写。初始路径镜像在写前断言停下，未输出manifest或运行guest；修正为内容SHA命名payload，精确guest大小写留在清单。另原索引去掉目录末尾斜杠，raw USTAR目录保留；只对type5规范化一个尾斜杠并保留原header名称。两次早停和局部文件均保留。— [大小写修复](../../original-uipc/ap-projection/full-v4/initial-path-collision-readback.json)、[目录名核对](../../original-uipc/ap-projection/full-v4/tar-directory-name-normalization.json)
- 完整树的126原.ko已建立同包内核/模块EXPORT_SYMBOL提供者目录，所有强未定义符号均有静态来源。原DMM需要Backup/UIPC/UTM，stream/stream2需要devno，grm_ma需要UIPC；静态来源不证明驱动初始化、硬件访问或菜单正常。— [126原模块目录](../../original-uipc/original-full-module-provider-catalog.json)

### Inferences
- 完整文件存在不等于自动加载或更新。后续只依实际AP首失败和原initrc/成功案例明确命令加载已审模块；相关原库idle初始化不应因泛名排除产生人工ENOENT。
- 原树文件与外层应用资源齐全后，仍需通过原bootin自然启动来区分入口/参数、服务依赖、硬件模型和真正原画面输出。

### Gaps
- full-v4尚未通过实际原应用/原菜单验收；AP候选由host另外封装、运行和记录。
