# FX3 任务文件投放与命令线程合同核对

2026-10-30。**原件进一步解释了231候选为何尚不能上机：现有证据不支持普通写入器能直接生成root0600 RAM计划，也不支持同一个服务队列必定由同一活线程接收。** 本轮读取两个已保存原件，核对10个动态符号完整函数、1个原FDE完整回调、4段明确标注的静态切片和46项指令/调用；没有执行Sony或Linux代码。

当前结果是[contract-audit-final.json](contract-audit-final.json)，可用[audit_contract.py](audit_contract.py)重新进行只读解析。`contract-audit.json`是保留的41项中间记录。源文件仍为官方FX3 7.02保存的libJiritsu.so（SHA256 `bdef58b2…092f1d9`）和libosal_uipc.so（`09ebf598…a70ff3`），没有再次解包或查询相机。

## 文件权限不能猜测

旧setter在`0x8e38`明确设置创建mode为`0x1ed=0755`，flags为`0x241=WRONLY|CREAT|TRUNC`，没有EXCL或NOFOLLOW。0755是请求值；当前进程umask、默认ACL和实际挂载权限未知，因此既不能声称实机会创建0755，也不能声称一定无法得到0600。

新setter在`0x981c`把相同flags交给`CFileAccess::open`。其普通文件分支在`0xec80`和`0xed00`调用POSIX open之前，没有在前一外部调用之后明确设置x2/w2创建mode。不能把其他寄存器中的旧值当成已建立的权限合同。这也不证明每次实机调用必然产生坏权限；本轮没有执行该包装器或其libc。

[Linux open手册](https://man7.org/linux/man-pages/man2/open.2.html)说明创建标志需要mode，创建权限还受umask等条件影响；[Arm AAPCS64 2025Q1](https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst)规定参数寄存器及跨调用保留要求，支持上述调用边界分析。已有文件可能保留其权限，但这依赖正确对象已被安全预建，不能用来绕过首次创建问题。

## RAM路径不是直接透传

`get_access_filename`使用固定基目录。普通operation0以`/tmp/jiritsu`为基准，operation1强制selector=0xff并以`/mnt`为基准。selector=0xff时，已带基目录的路径可按原串格式化；其他绝对路径会拼接到基目录后，其他相对路径则加分隔符再拼接。

因此直接提交`/tmp_wbshd/fx3-entry-plan-v1.bin`不能据此证明访问了根目录下的RAM文件。`..`等祖先路径尚未经过完整转换、目录创建、挂载和对象核验，不能把字符串逃逸当成已验证的安全投放。普通operation0的flash挂载前置仍在；目录名以`/tmp`开头不证明无持久副作用。

下一版优先研究一个固定准备程序：将已固定工作程序SHA、nonce及关联字段包含在自身配置中，由它读取目标CLOCK_MONOTONIC，在核验过的RAM目录以EXCL/NOFOLLOW创建0600完整计划。这样不再依赖普通写入器创建RAM计划，也不必猜相机时钟。**目前仅确定设计方向，尚未实现。** START到OBSERVE的计划转换、准备程序自身完整性及主机回执读取也仍需解决；单纯创建空文件再由普通路径填充，不算完整路线。

## 同队列不等于已证同线程

`jiritsu_init`把队列`0x016f0480`注册到原回调`0xb278`。该回调经高容量发送分派进入实际setter，构造函数运行在调用链当前线程中。

此队列bit15为0，`osal_reg_sync_msg_queue_cb`走UIPC注册ioctl。注册后的辅助逻辑按计数与配置条件扩展接收线程；pthread创建点`0x2cd0`使用入口`0x3390`，后者进入`0x3260`。接收循环从共享设备FD做ioctl，并在`0x32f0`调用返回的回调地址，然后继续接收。

这证明存在受配置控制的接收线程机制，**没有测得当前机身的线程数，也没有审完内核对队列/线程索引的分配规则**。因此不能承诺同队列一定同TID，也不能反过来声称真机一定换线程。231对不同或复用创建线程返回HELD是正确保护，当前不删除它。后续优先追踪内核接收ioctl的分配合同；如需跨线程观察，必须另证精确退出身份，保留已发现的PID复用反例。

本轮前一目标轮归类为progress：231已封存125个成员和14项/22场景结果；本轮新增原件证据改变了下一版的投放与线程研究方向。并未重新运行未变的231测试。

全部16项要求、正式0.4/0.5及23份源码、195待批准未启动状态保留。当前没有完整真机备份、独立AP救砖/逆写冷启动或MAIN1080p29.97 HEVC实录证明。本轮相机/USB缓存、管理员、认证、上传、固件/WBI操作均为0；目标active，首刷未放行。[封存回执](final-receipt.json)。
