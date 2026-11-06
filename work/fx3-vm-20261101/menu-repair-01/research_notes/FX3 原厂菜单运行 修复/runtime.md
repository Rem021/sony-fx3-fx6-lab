# FX3 原厂菜单运行修复：Mac runtime 实证记录

## 1. 可复用的已验证路径是什么？

旧 `outputs/fx3-vm` 19成员封包于本轮开始逐一通过原SHA核对，QEMU仍为 `78e36d4060aa4aae5a802c69cbd45beab3c69c47746371897e229e1c1eeb7e93`。旧lock空闲、无QEMU进程。新候选只读引用原QEMU与原FX3 4.9.337-scel+ kernel；旧封包/报告不变。

继续采用TCG、Cortex-A35、单核、2GiB高DDR backing、4KiB原SMP mailbox backing、GICD iomap与公开七项未建模initcall排除。它目前只证明core/userland/loader可运行，不是相机UI。

新观察器 `runtime/run_candidate.py` 对候选SHA及冻结基线复核，持有原运行包协调锁及新runtime锁；无网、USB、宿主磁盘。QMP用run目录内相对Unix socket避免Mac地址长度限制，保留serial、原printk ring、寄存器、RSS及退出回执。首轮20s观察；长程instruction trace默认关闭，可限定前缀时段。

## 2. 当前实际阻塞与候选是什么？

上轮原im入口实报缺少 `/dev/uipc`。新兄弟依据FX3同包原模块闭合链准备 `devno.ko → osal_utm.ko → osal_uipc.ko`，原devno表记录字符设备c251:207。不是空普通文件或ioctl成功替身。

`original-uipc/candidate01.json` 已只读审查：raw CPIO44项、三原ko SHA及/init字节与元数据匹配；DTB只改initrd-end。/init仅挂guest proc/sys、真实insmod、打印RC/modules/devices/UDM，模块实际载入后建字符节点，然后原im target=qemu两秒观察。原完整init2包含格式化分支，故没有执行；其原序列明确先 `echo set > /proc/udm/drivers` 再insmod_drv2，本候选先不写set以保留行为差分。

详细预检见 `runtime/candidate01-preflight.json`。此刻尚未执行候选，先等待upstream给已成功案例的UIPC/服务/显示路径，按父协调要求避免盲造注册成功。

## 3. 下一次实证如何判定？

预备命令：Python3 `runtime/run_candidate.py --candidate original-uipc/candidate01.json --seconds 20 --label uipc01`（命令中路径运行时使用绝对值）。首要证据是原模块真实insmod和cdev注册、原im对/dev/uipc消费之后的真实新阻塞；退出0和自写marker不作为菜单证明。

本轮最终目标是原厂首设/菜单真实出帧、主要按键/拨盘可交互、稳定数分钟、正常退出及再次启动。图像/录像另行验收，不以终端日志代替UI。


首轮实际记录（uipc01-1c9ec368）：CPIO三份模块虽有原字节，但父目录条目排在文件之后，kernel解包时未创建它们；三insmod ENOENT/254，且缺/dev/null影响shell重定向。是候选包错误，不归因于原模块/ABI。错误包保留，独立结构证据candidate01-unpack-order-failure.json。新CPIO gate已检查父目录顺序及20原ELF逐字身份。

第二轮（uipc02-bcaa02bd）：成功案例固定b3d7c1f的真实原模块链经文档/源码核对后执行；三原ko insmod全0、/proc/modules全Live、/proc/devices注册251 uipc，devtmpfs自然产生字符251:207。原im越过缺节点并真实调用原UIPC ioctl，返回-1020与终止前-1021，语义待原driver分支核对；未改回包、未写UDIF set。guest原im按两秒界限TERM，wait143；无kernel异常、原ring完整解码、20s host后QEMU干净回收且输入SHA不变。此步只证明真实UIPC调用，仍未证明菜单、CP服务、mmap链或稳定UI。


第三轮（uipc03-e36a7cf9）仅新增原proc状态采集：原im五线程睡眠，maps含实际2MiB `/dev/uipc` rw-s，尚无appFw/libMWF/BusPower；原OSAL4.2 proc统计可读。完整serial/860条kernel ring保留，0异常/输入不变/已回收。当前-1020不能直接认作上游BusPower同因。

用于下一轮透明观测的Mac交叉工具已局部准备：Zig官方0.17.0 ARM64 Mac archive，固定SHA b607e9b9234790a008116ae5bdb71c6243b84b9fb42a53a9e70fde41c06c536a，工具cache不改系统。`ioctl-trace-v3.so` 显式链接四份原glibc2.25依赖并禁用outline atomics，不链接bundled libc；只调用原ioctl/mmap并记录其真实return/errno，safe self-read原16B record及已核op4/5/6消息布局。v1/v2构建记录保留但不用于guest；v3经original-owner复核后才打包04，仍需guest原ld/实际调用验证。来源见toolchains/zig-toolchain-receipt.json和helpers/compile-attempt03.json。


第四轮（uipc04-3dab0077）原ld verify/list、preloaded BusyBox true全0；透明helper实际调用原mmap/ioctl，45个op5同步send真实返回-1/errno1020。self process_vm_readv不可用，读取失败的零初值不作ID解释。original owner独立核syscall270/271都是原sys_ni_syscall，非指针/driver错误。

第五轮（uipc05-e2ffb306）仅改/proc/self/mem安全读后端：156条外层16B record及op5嵌套24B record读取成功，真实arg0目标8f013a(42)、3e014d(2)、94016a(1)。真实body在原/dev/uipc两MiB PFNMAP内，pread返回EIO5，不能据此否定CPU可读性。成功案例代码已命中前两者为ulogio/Backup，当前不是BusPower那例；第三个尚未命名。下一仅在已真实mmap登记且未被munmap/mremap/mprotect失效、完整范围/溢出校验下取16B当前body快照，原操作/返回保持。模块/seed追加需下一独立候选。


第六轮（uipc06-9f4ba70e）v7在已真实登记的原UIPC二MiB VMA内取46个当前消息的16B，逐条边界/epoch复核通过；此前pread EIO仍留存。3e014d两条原body为09000000000000000300000000000000；94016a是e1009400000000000000000000000000，原im已发现其本地注册，不能当未知外部服务制造receiver；8f013a为日志。上游关于3e014d的历史CP-side/本地名称有冲突，行动以原FX3注册及实际运行验证，不启旧泛ACK。

第七轮（backup07b）独立FDT预检确认只改initrd-end及新增memreserve0x404000000+0x221000，保留linear map，原Image装载区/新initrd不重叠。同机seed2229740B/SHA bf3a9d85…首物理p32 header经原arch转换后位于该区。原backup.ko load1/save0初始化RC0、原module日志NO SAVE MODE、sysfs原参数可读；两条同原selector9同步请求的原ioctl实际由-1/1020变为0。此为真实原callback接收差分，尚无内层Backup_write返回、bank语义/同步持久化/重启验收，也没有菜单。没有CP或状态0替身。详backup07b-preflight.json、backup07b-layout-proof.json及backup07b-observed-summary.json。
