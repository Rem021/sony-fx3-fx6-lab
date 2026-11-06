# FX3 受控启动器与启动前镜像核验

2026-10-30；经典ILME-FX3 7.02；Mac离线构建、自己的ARM64代码和明确的假Linux内核。

**已把父端的镜像完整SHA核验、clone两个分支、子端FD清理、exec切换、静态程序入口和完成判定连成一条模型路径。8项检查、20组场景通过。** 本轮执行了自己的父端和子端机器码，所有Linux进程/内核行为仍由模型提供；真实相机启动、完整备份、独立救砖和首次刷写均未通过。

## 启动顺序

[parent_module.c](parent_module.c)保留显式submit/poll两个导出和仅写内存的初始化函数。新的submit只接受child=0、fd=-1及child PID为0的handoff模板；不再接受外部注册的PID/借入通道作为正常启动入口。

[launch_support.inc](launch_support.inc)按以下顺序执行自己的C代码：

1. 核对参考im身份、请求和模板，取得原固定全局父会话；既有目录仍阻止新实例，不能按PID消失或旧记录回收。
2. 在固定RAM根打开`fx3-boot-worker-223.elf`，要求root/0500/单链接/只读/非O_PATH，读取完整262,144字节、EOF和前后元数据，匹配第223轮静态程序完整SHA。
3. 初次以O_EXCL创建两个0600输入文件，保留自己的读写FD。其它旧输入文件会使本轮拒绝，不覆盖或删除。后续窗口只能由同一存活父端复用这些保留FD，写前核对身份和稳定元数据；写满、同步并核对新长度。
4. 创建带CLOEXEC的UNIX DGRAM socketpair，以原始clone(220)、flags=17(SIGCHLD)、空child stack创建子分支，不共享VM、FD表或线程组。实际Linux是否接受这一合同仍未测试。
5. 子分支枚举`/proc/self/fd`，只对自己的FD表设置CLOEXEC；清除镜像、根目录、子端通道三种角色的CLOEXEC，其它FD须在exec关闭。再核对镜像身份，使用`/proc/self/fd/<image-fd>`和空环境执行固定静态程序。exec失败只退出，不切换shell、备用路径、重试或preload。
6. 父端用clone返回的PID完成handoff及CRC，通过原保留输入FD写满请求和handoff、同步；关闭本端不需要的副本。只有这些步骤成功，才按原协议发送GRANT。父端自己的描述符标志不因子端白名单处理而改变。
7. READY后才发GO；DONE、指定子进程正常退出0、RAM输出复读/CRC/绑定/关闭/期限共同满足才回到IDLE。失败或不确定仍为HELD/UNKNOWN，原wait4观察和无自动回收政策保留。

输入文件在fork后写入，但它们的创建和所有写入均发生于取得全局会话之后。子端在收到GRANT前不会读取这些输入，在GO前不会读取源。任一写入或同步失败均不发GRANT；已经创建的原子进程仍被观察，不强杀、复位或换一个任务重试。失败状态可能保留少量父端FD和RAM占用，当前没有清理/接替接口。

## 验证与边界

[最终回执](runs-final/receipt/results.json)：8项检查、20组场景、全部模型线程终止。父端262,936字节，SHA256 `c3e1d45b55fb8c4c228e7fe4b78cbe702ef81fcd2406f882fe374310198c93dd`；343处代码链接处理。第223轮静态子端逐字节未改，SHA256 `e40d068d43123f8f86eba5c46a1428e02e5e16c84df2211174c578d4cd273d7d`。[构建回执](runs-final/built/build.json)

- 正常路径从父端C创建模型子进程；子分支从clone返回点继续执行自己的机器码，设置FD标志并调用exec。模型在exec成功时关闭CLOEXEC FD、替换映射，从原第223轮`_start`运行至退出，再由父端判定完成。
- 改坏镜像一个字节、可写镜像、错误UID或元数据变化均在clone之前拒绝；socketpair/clone失败不发GRANT。
- FD设置失败、畸形目录项、fork后镜像身份改变、exec失败分别到达90/90/91/93退出码，源读取0。子进程可能在父端首次观察前退出，因此submit可能直接返回HELD；这与先返回RUNNING再由poll判失败等价，不能强求一次中间状态。
- 请求短写/同步失败不发GRANT；模型原子端在同一次等待结束后返回57，源读取0。只释放自写模型的等待门，不是目标设备超时或硬件退出证明。
- 旧输入字节保留，新父实例不能接替旧会话。同一存活父端完成boot1四窗口128/128/128/126块，33,423,360字节人工源组装SHA完全一致；两个输入文件各只创建一次。[组装回执](runs-final/assembled/complete.json)
- exec只剩三个角色FD，含0/1/2和900在内的其它继承FD已由模型关闭，父端原标志保留。正常DONE和退出0后改坏输出块，父端仍保持HELD。

普通Mac夹具文件的O_EXCL、pwrite、fsync、读写和组装是真实本地操作；root/tmpfs、进程身份、clone的地址空间/FD复制、信号、socket凭据、exec、CLOEXEC关闭、wait4和目标时钟全部是声明的模型行为。没有运行Linux内核、Sony im、BusyBox或glibc，没有创建真实Linux子进程。原厂im只作为数据核对SHA；模型中的im文件身份不证明相机实际加载上下文可信。

首轮使用旧handoff生成器直接传PID0而被夹具拒绝；后续修正模板生成、模型协议名称、缓存目录重名，以及对exec未使用寄存器的错误约束。所有失败回执和匹配源码保留；最后完整四窗口和输出损坏回归通过，没有把早期“表面拒绝”混入通过项。[源码及模型派生](source-derivation.json)

[Linux clone手册](https://man7.org/linux/man-pages/man2/clone.2.html)、[execve手册](https://man7.org/linux/man-pages/man2/execve.2.html)和已保存Linux4.9 UAPI用于核对原始调用、无CLONE_FILES时的描述符表、CLOEXEC与exec的语义；这些参考不证明目标内核支持或机内挂载执行策略。[ABI核查](kernel-and-link-ABI-review.json)

## 尚不能刷入的原因

这仍不是已安装到FX3的启动器。真实模块加载/调用入口、参考父身份、root域、RAM挂载执行策略、Linux clone/exec/FD行为和实际USB传输均待验证；没有安装、上传、改变挂载或权限。原始clone时的信号继承、真实父进程的SIGCHLD处理与其它waiter、实际加载上下文及其它调用覆盖也未验，不能把此模型当作机内全局监管证明。

下一步先把启动镜像与请求的暂存、父端动态加载/调用及结果传输接到同一受控主机任务合同，继续限定为自写代码与假对象；同时核对信号/退出竞争及加载上下文，不能只凭本轮创建了模型child就扩大实机范围。

全部16项要求保持：MAIN1080p29.97 HEVC42010约16Mbps、exact30单列、实际编码器/文件/音画/长录验收、同机健康完整备份、数据视图与硬件访问归还、逆写冷启动和独立AP救砖均未由本轮证明。195仅主机root01仍待具体批准且未启动，0.4/0.5正式包与23源码未改。用户已将原生目标恢复active，本轮只观察未修改；无USB/缓存查询、管理员、认证、上传、目标执行或持久写入。目标未完成，首次刷写未放行。

[实施范围](implementation-review.json) · [核查回执](verification-receipt.json) · [封存清单](final-receipt.json)
