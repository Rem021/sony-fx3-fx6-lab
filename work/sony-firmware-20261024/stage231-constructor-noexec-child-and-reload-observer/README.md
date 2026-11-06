# FX3 构造启动器与再次加载时的退出观察

2026-10-30。**已实现自写空操作候选的构造启动、父模块卸载后子进程继续运行，以及下一次构造加载时核对退出。14项检查、22个模拟场景通过，重复构建字节一致。仍未形成可投放相机的诊断方案，也不能据此刷写。**

本轮接续[230的实际直接加载入口](../stage230-constructor-child-entry-portability/README.md)，不要求与此分支无关的完整脚本对象接口。只在 Mac 编译自写程序并在 Unicorn 中执行自写 ARM64；Linux、文件、凭据、进程和调度均为明确的内存模型，没有创建 Linux 子进程，也没有执行 Sony、glibc、BusyBox、Linux 或公开相机载荷。

## 实现和实际范围

[entry.c](entry.c)的构造函数只接受固定256字节计划，purpose=1固定为空操作。检查保存的im程序完整SHA、当前库文件SHA、已加载只读字节，以及RAM文件类型、权限、长度、稳定性、CRC和期限。若未来部署，这会读取相机上的程序文件和proc元数据；不能描述成“不读任何机身文件”。本轮这些文件读取全部在内存模型内。

START先创建不可复用的全局目录及pending记录，再固定创建线程的proc目录FD、私有数据报通道和请求关联信息。仅在创建线程临时屏蔽可屏蔽信号；不改父进程的信号处理函数。子进程使用clone(flags=0)，不共享地址空间、FD表或信号处理表，也不exec；只在子进程内重置信号处理并关闭继承的其他FD。

子进程必须收到匹配凭据和请求的私有GO才会执行空操作。未收到时最多100轮非阻塞接收与10毫秒休眠，并检查任务期限和两秒单调时钟上限；错误则退出70。这里是程序的限次和期限约束，不是对真实内核调用延迟的硬实时保证。

下一次相同程序加载时使用OBSERVE计划。它必须来自同一进程、**同一仍存活的创建线程**：除数字TID，还比较保留proc目录FD与当前线程proc目录的dev/inode。观察期间临时屏蔽信号，使用`WNOHANG|__WCLONE|__WNOTHREAD`，只有私有DONE、精确wait4退出0及控制/线程锚FD关闭共同满足，才标记已观察。

`entry.result`只记录上述观察，不证明写完结果后的RAM目录FD已关闭、USB已归还或相机可录制。全局目录和观察次数不会自动回收；未知状态不重试、不根据PID消失判成功。完成本次观察也不证明重启后可重建完成状态。

## 两个实际跑出的旧版本反例及修复

| 反例 | 保存的旧结果 | 当前处理 |
|---|---|---|
| 原子进程DONE后退出被别处取走，其他im线程创建了同编号新子进程 | 旧观察器错误接受新子进程的exit0，见[PID反例](PID-reuse-before-fix.json) | 同一活线程proc锚、信号屏蔽和`__WNOTHREAD`；当前故障场景保持未完成 |
| 父模块已卸载、子进程尚未获得调度，原库文件映射变得不可访问 | 旧自写二进制取指失败，见[文件映射反例](file-backing-before-fix.json) | 先将固定自写PIC镜像复制到匿名内存，从匿名副本内执行clone，确保子进程第一次恢复执行已在副本中 |

第二个模型主动撤掉了原ELF映射，用于检验是否仍依赖文件页，并没有运行真实Linux的截断/SIGBUS流程。匿名副本先RW复制，再分段设置R/RX/RW，拒绝RWX；父端在返回前解除自己的副本映射。当前所有已创建子进程的场景，都在子进程首次执行前撤掉它的原库映射。

## 验证及源码依据

以[runs-bounded-verified/receipt.json](runs-bounded-verified/receipt.json)为当前结果；旧的`runs-final`、`runs-release-checked`等目录是保留的中间版本，不能作为当前发布结果。最终ELF为131864字节，SHA256为`c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec`；[第二次构建](reproducible-bounded-summary.json)完全一致。没有导入、DT_NEEDED、通用shell或机身传输后端。

22个场景涵盖正常、待结束、外部`__WALL`回收、DONE后关闭失败、坏计划/库文件/已加载字节、错误凭据、SCM_RIGHTS及短包权利清理、FD复用、父端信号掩码归还失败、期限、其他/复用线程、PID复用、观察端掩码失败、拒绝源读取purpose，以及匿名分配或RX权限失败。异常没有被当成安全完成；父端失败未发GO时，子进程限次退出。

[内核合同](kernel-contract-review.json)固定Linux v4.9的clone退出信号、等待线程范围和proc inode实现。[缓存合同](cache-contract-review.json)另固定AArch64页表、mprotect、通用提交及缓存同步源码：参考实现将可执行用户页接入缓存同步。参见[上游页表实现](https://github.com/torvalds/linux/blob/v4.9/arch/arm64/include/asm/pgtable.h)、[缓存实现](https://github.com/torvalds/linux/blob/v4.9/arch/arm64/mm/flush.c)和[保护变更实现](https://github.com/torvalds/linux/blob/v4.9/mm/mprotect.c)。这是源码依据，**没有验证当前Sony内核、实际缓存一致性或硬件执行**；Unicorn不模拟真实指令缓存。

## 上机前尚缺什么

[provisioning-gaps.json](provisioning-gaps.json)列出具体条件：安全投放root0600 RAM计划的路线、取得目标单调时钟、两次直接加载是否保持同一活线程和认证会话、真实同机身份、传输长度与分帧、ELF/页大小/匿名执行权限、内核信号与等待行为，以及完整资源归还。不能为迁就未知写入器而放宽计划权限，或把关联字段当作授权和身份认证。

当前没有集成完整boot备份工作程序，没有取得真实健康机完整备份，也没有独立AP恢复、逆写及冷启动证明。下一步优先解决计划投放与同线程加载合同，再接入有界备份流程。仍保留全部16项要求，包括MAIN 1080p29.97 HEVC420 10bit约16Mbps、exact30单列、原片音画长录、回退和恢复；空操作启动测试不替代这些要求。

本轮相机、USB/缓存查询、管理员、认证、上传、固件/WBI写入均为0。195仅主机root01仍未批准、未启动；正式0.4/0.5及23份源码不变。目标active，首次刷写未放行。[封存回执](final-receipt.json)。
