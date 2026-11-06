# FX3 自写静态工作程序与描述符合同

2026-10-30；经典 ILME-FX3 7.02；Mac 离线构建与自写 ARM64 模型测试，无相机操作。

**独立程序的入口到退出已接通：8 项检查、25 组场景通过。** 子端由自己的 `_start` 调用读取函数，再以 Linux ARM64 的 93 号退出调用传回结果；不需要 BusyBox 构造函数、Sony 动态装载器或 glibc。第222轮父端二进制保持原样，与新子端按原私有协议联测。真实 fork/exec、描述符继承和机内运行仍未验证，不能据此放行首次刷写。

## 本轮实现

[worker.c](worker.c) 是独立静态 ELF，固定 262,144 字节，SHA256：

`e40d068d43123f8f86eba5c46a1428e02e5e16c84df2211174c578d4cd273d7d`

[构建器](static_build.py)只接受固定自写源码和两个对象文件；没有运行时导入、PT_INTERP、初始化数组或可执行栈，段不同时可写和可执行。段按64KiB对齐，ADRP指令仍按4KiB计算。局部增加受限的整数LDST32重定位285；正式elflink及0.4/0.5包未改。两次独立构建逐字节一致。[构建记录](runs-import-fixed/built/build.json)

[参数与镜像核对](roles_and_image.inc)接受以下固定参数合同，三种角色均为已继承的描述符，不接受任意文件路径：

```
fx3-boot-worker --fds-v1 <image-fd> <root-directory-fd> <private-socket-fd>
```

编号必须是不同的非负规范十进制整数，无前导零、溢出、尾随参数或缺失的NUL。不占用固定196—199号子端描述符，也不假定0/1/2保留给标准输入输出。

- 镜像描述符须指向root所有、0500、单链接、只读、非O_PATH的RAM普通文件；与`/proc/self/exe`的后端文件身份和稳定元数据一致。三个角色的CLOEXEC标志均必须清除。
- 根目录描述符须与固定`/tmp_wbshd`的设备号、inode、模式及UID一致。原读取器与handoff实现逐字节保留，跨窗口nonce及窗口占用名仍处于同一全局命名空间。
- IPC仍是第221轮v1：GRANT/READY/GO/DONE、逐消息凭据和完整handoff绑定不变，仅通道FD改为参数选定的角色。
- 获得GO后，镜像和目录的显式关闭错误会传到DONE及退出码；通道关闭失败也不能报告成功。早期拒绝的剩余FD由模型中的进程退出清理，记录与显式关闭分开。

镜像inode一致只说明文件关联，不能代替启动前完整SHA核对，也不能证明父进程代码可信或用户已经批准运行。父端启动前固定完整镜像SHA这一步尚未实现。

最初考虑过私有任务根目录和IPC v2；由于会把现有跨任务防重复状态隔开，本版未采用。草稿及[选择理由](compatibility-decision.json)保留，实际合同为固定根目录与IPC v1。[有效派生记录](source-derivation.json)

## 验证结果

[最终回执](runs-import-fixed/receipt/results.json)执行自己的子端静态ARM64和第222轮父端ARM64；Linux进程、时钟、root/tmpfs、socket、凭据、wait4及继承FD均由明确的假内核提供。普通Mac夹具文件的独占创建、数据读写及组装是真实本地操作。没有执行Sony、BusyBox、glibc或Linux内核。

- 正常路径以及角色编号0/1/2、181/182/183均完成；子端发送READY/DONE，父端发送GRANT/GO，子端显式关闭三种角色并退出0，父端复读输出后回到IDLE。
- 七组参数错误及六组镜像/根目录/标志错误在源读取前拒绝，父端保持HELD/UNKNOWN。
- 同一存活父端完成boot1四窗口，128/128/128/126块，共33,423,360字节；组装SHA与人工源完全一致。换nonce重放同一窗口仍拒绝，读取次数为0。[组装回执](runs-import-fixed/assembled/complete.json)
- 三种角色关闭错误分别保留失败；DONE和退出码都是0但输出块被破坏时，父端仍保持HELD。
- 所有模型线程已结束，未强杀、重置或自动重试。

首轮8项检查产生4失败和1错误；模型漏导入`sha256`/`zlib`，正常发送路径没有完成，不能算通过。失败回执及对应源码在[runs-first](runs-first/receipt/results.json)和其`source-snapshot/`保留。修正模型导入并增加失败详情记录后，8项全部通过；C源码与最终ELF未因这一修正改变。

[Linux execve手册](https://man7.org/linux/man-pages/man2/execve.2.html)和[fcntl手册](https://man7.org/linux/man-pages/man2/fcntl.2.html)用于核对继承与CLOEXEC语义；另保存Linux4.9的fcntl原始UAPI及既有unistd原件，核对fcntl=25、exit=93、F_GETFD=1、F_GETFL=3、FD_CLOEXEC=1、O_PATH=0x200000。这些参考不构成目标内核运行结果。[ABI记录](kernel-and-link-ABI-review.json)

## 距离上机仍缺什么

下一步继续写受控启动器：在启动前固定完整镜像SHA、准备不泄漏其它FD的继承集合、实际创建子进程、从同一受控入口exec，并把失败与退出观察交给原父端；先用自写代码和假内核核对。输入暂存必须在父端取得全局会话后完成，避免并发覆盖固定输入文件。独立任务目录只有在保留跨任务防重复及父子绑定时才可引入。

本轮只是已有父端与新静态子端的联测，模型预建队列与注册的child不是实际fork/exec证据。真实RAM挂载能否执行、机内root域、参考im身份、所有调用是否受监管，以及硬件访问归还均未验证；没有修改挂载或权限。单窗口软件完成不证明同机完整备份、逆写、冷启动或独立AP救砖。

全部16项要求、MAIN 1920×1080 30000/1001 HEVC42010约16Mbps、exact30单列及长录验收保留。195仅主机root01仍待具体批准且未启动；无USB或设备缓存查询、管理员、认证、上传、相机程序执行或固件写入。原生目标状态本轮只读观察为blocked，与第222轮记录的active不同；未由助手修改或重建目标，用户的继续指令下仍在推进离线研究。`goal_complete=false`、`persistent_write_release=false`。

[实施范围](implementation-review.json) · [核查回执](verification-receipt.json) · [封存清单](final-receipt.json)
