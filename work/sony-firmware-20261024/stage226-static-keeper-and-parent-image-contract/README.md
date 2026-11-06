# FX3 自写静态看护进程与新版父镜像合同

2026-10-30；经典ILME-FX3 7.02；Mac离线构建及自己的ARM64/假Linux联测。无相机操作。

**独立看护进程候选已实现，7项检查、11组场景通过。** 两个静态程序都从自己的`_start`运行至退出；同一存活看护进程完成四窗口人工源采集，原厂im回收器在模型中不能直接回收其工作子进程。新的父镜像完整SHA、继承FD与私有交接绑定一起验证；尚未实现真实加载入口适配、认证上传或机内运行，不能放行首次刷写。

## 两个程序及哈希关系

[程序对清单](artifact-manifest.json)固定两份262,144字节的静态AArch64 ELF。它们没有动态加载器、运行时导入、构造函数、可执行栈或RWX段；段仍为64KiB对齐，ADRP按4KiB计算。

| 角色 | 实际入口 | SHA256 |
|---|---|---|
| [看护进程](keeper/keeper.c) | `_start → fx3_keeper_run` | `93bcd77751550c7079a38dfe532272ecf71d849f906c4b05d5515267fa888581` |
| [工作程序](worker/worker.c) | `_start → fx3_boot_read_window` | `349115672da2bc494e073472446004ee476c77ecc716756351cfe50a395b66e7` |

先构建工作程序，看护进程内固定其完整SHA。主机任务包携带两份完整程序SHA，看护进程从自身执行文件计算自己的SHA并与任务包比较；工作程序从私有handoff取得该父镜像SHA，再对`/proc/<父PID>/exe`完整哈希。工作程序没有内嵌看护进程SHA，因此没有父子程序互相内嵌哈希的循环依赖。两份初次构建与最终构建二进制逐字节相同。

这些哈希和内核凭据建立程序/任务关联，**不代表用户批准、完整进程代码证明或安全启动认证**。实际主机必须独立核验固定程序对并通过可信的启动交接建立通道；本轮尚未实现该真实bootstrap。

## 看护进程的职责

[启动身份检查](keeper/keeper_identity.inc)要求独立主线程、root、规范的三角色参数、RAM镜像/root目录的身份关联，及参考im父程序的完整文件指纹。参数为：

```
fx3-boot-keeper --fds-v1 <keeper-image-fd> <root-directory-fd> <control-fd>
```

它通过134号`rt_sigaction`只在**自身进程**将SIGCHLD设置为SIG_DFL、清除NOCLDWAIT等标志，随后回查；每次提交工作前再检查。没有更改原厂im的处理器，也没有用clone信号0或`__WCLONE`规避第225轮发现的问题。模拟的原厂im仍有`0x402f4c`处理器，看护进程与它属于不同进程。

[私有主机控制](keeper/host_control.inc)在继承的未命名UNIX DGRAM通道核对创建者与逐消息凭据，要求参考im父PID及root UID/GID。512字节JOB包含严格序号、256字节handoff、128字节请求及两程序SHA，末尾CRC；FINISH必须空请求/交接。完整JOB的SHA随私有结果返回，以绑定本次任务。错误凭据、错误看护镜像SHA或序号在创建工作进程前拒绝。[独立编解码器](protocol.py)

原第224轮父端监管、固定全局会话、输入O_EXCL/保留FD复用、镜像启动前哈希、clone、输出复读及失败保持政策保留。全局会话目录和nonce/窗口占用名沿用旧命名空间，不能通过协议升级逃避已有占用。输入handoff改为`fx3-boot-handoff-v2.bin`；请求和内层读取器未变。

看护进程只在指定工作子进程退出0、私有DONE和全部RAM输出核对都成立时报告该窗口成功。异常时报告HELD后继续观察同一个原子进程；不因回复失败、超时或公开文件而重启/接替。若无法取得原子进程退出证明，仍可能持续保持UNKNOWN，未提供强杀、复位或自动回收接口。

## 工作程序新版合同

工作程序只接受四个不同的规范十进制继承FD：

```
fx3-boot-worker --fds-v2 <worker-image-fd> <root-directory-fd> <private-socket-fd> <keeper-image-fd>
```

新[父镜像检查](worker/parent_image.inc)要求父镜像FD为root/0500/单链接/只读RAM普通文件，并与`/proc/<父PID>/exe`后端身份一致。通过私有GRANT后，还要读取整个父文件，匹配v2 handoff中的SHA（偏移188、32字节）与长度（偏移220、4字节），并复查元数据/继承FD；然后才进入请求绑定及占用。PID、逐消息凭据、私有通道及源读取前的GO条件继续保留。

IPC魔数和版本改为v2，handoff魔数也为v2；224—251字节仍须为0。没有将旧im检查放宽为任意父进程，也没有保留旧im作为新版的备用父身份。父镜像字节损坏但元数据不变时返回44、源读取0；伪装回旧im父文件同样拒绝。旧handoff不会在新版看护进程里静默降级。

## 本轮验证

[最终7项检查](runs-final/receipt/results.json)覆盖11组场景、11个看护程序实例和8个工作子进程；两个角色确实执行自己的ARM64机器码。Linux进程、exec/FD继承、root/tmpfs、信号、凭据、wait4与目标时钟均是显式模型，普通Mac夹具文件的创建、同步、读写和组装是真实本地操作。原厂im只作为数据哈希，没有执行Sony、glibc或Linux内核。

- 正常看护进程/工作程序都退出0，窗口结果和准备结束结果到达；进入工作程序时只剩四个必需FD。原厂回收器的模型尝试看到worker的父PID为看护进程7001，而非im321，未取得其退出状态。
- 自身信号设置失败或回查仍为IGN/NOCLDWAIT时返回81，没有创建工作进程。所有信号修改目标均为看护进程，im处理器保持。
- 看护SHA、主机消息凭据或序号错误返回83，没有创建工作进程。父镜像内容不符、旧父文件分别使工作程序返回44、源读取0，看护进程保持失败并返回85。
- 同一存活看护进程完成boot1四窗口128/128/128/126块，共33,423,360字节，与人工源SHA完全相同；每窗口使用独立任务序号、nonce及私有结果。[组装回执](runs-final/assembled/complete.json)
- 旧handoff在新版入口拒绝；没有启动工作程序或读取源。
- 最后一条FINISH回复已经声明窗口IDLE，但关闭控制通道失败时，实际看护程序退出89。因此FINISH仅为**准备结束**，不能单独作为退出0的证明。编解码器明确标记`actual_keeper_exit_observed=false`；真正的bootstrap还需独立取得退出结果。

早期模型缺少新版文件路径/传输辅助方法、凭据辅助导入，失败记录及对应源码保留。随后6项检查在终端显示通过，但结果JSON中含bytes导致写回执失败；该轮不计正式验收，错误与源码保留。修正报告序列化、增加旧协议/父身份/序号拒绝检查后，当前7项/11场景完整回执通过。没有改C程序去迎合这些模型错误。[源文件派生及保留说明](source-derivation.json)

信号ABI对照Linux4.9 AArch64及通用UAPI：SIGCHLD17、SA_NOCLDWAIT2、64位sigset8字节、handler/flags/restorer/mask依次为0/8/16/24，共32字节；134号调用的sigsetsize为8。[原文捕获](signal-source-capture.json)及[Linux sigaction手册](https://man7.org/linux/man-pages/man2/sigaction.2.html)只作参考，不证明Sony4.9.337实际行为。[ABI核对](kernel-ABI-review.json)

## 仍缺的上机条件

真实原厂加载ABI适配器和im→看护进程bootstrap尚未实现。模型从看护进程自己的入口开始，明确提供已继承的三个FD和参考im父身份；没有在原厂加载器执行适配函数，也没有实际认证、暂存、上传或exec。下一项要完成显式加载入口适配、固定程序对/任务的启动交接和看护退出结果传输；不能靠dlopen、FINISH消息或PID消失补足证据。

实际Linux执行/信号/FD/父子关系、root私有域、挂载执行策略、原厂线程与加载上下文、孤儿收养/ptrace/其它等待者均未由本轮证明。`keeper/parent_module.c`是保留的224来源副本，非有效构建入口；实际看护源是`keeper/keeper.c`，构建器只编译固定有效源码。

全部16项要求、MAIN1080p29.97 HEVC42010约16Mbps、exact30单列、编码器/文件/音画/长录、同机健康完整备份、真实数据视图与访问归还、逆写冷启动及独立AP救砖继续保留。195仅主机root01仍待具体批准且未启动，正式0.4/0.5与23源码未改，旧候选和反例保留。目标active，未完成；无USB/缓存查询、管理员、认证、上传、相机执行或持久写入，首次刷写未放行。

[实施范围](implementation-review.json) · [核查回执](verification-receipt.json) · [封存清单](final-receipt.json)
