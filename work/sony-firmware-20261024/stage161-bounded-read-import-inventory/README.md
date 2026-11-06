# FX3 有界读取组件与可达入口盘点

2026-10-28。**找到了原生分块组件与限量读开头的内部辅助函数，但尚未确认可用于完整同机备份的服务入口。** 不能仅凭出现read/seek名称，把它们当作可发送的备份命令。

本轮仅解析官方7.02 AP分区，执行原指令guest；没有运行管理员程序、设备接口、认证或相机文件服务。156单次接管授权已保留，最近缓存中FX3卷仍挂载，继续等待按原方案手动推出；次数尚未消耗，不重复请求授权。

## 全分区盘点

[盘点](AP-range-read-inventory.json) 从固定SHA的原nflasha15.img逐inode读取，重验148轮已有的全部532个ELF哈希。扩展到stdio/Fsys seek和ReadDeviceData后，共168个文件有匹配命名符号；第一轮较窄的153文件盘点保存在first-exact-primitive-pass，未删。

在这些AP命名符号中未发现pread/pread64；这不排除直接syscall、内联、其它分区/ROM或动态代码。ReadDeviceData仅在libsencore.so定义；未找到其它AP ELF对它的命名导入。

| 原组件 | 已确认的能力 | 仍缺的证据 |
| --- | --- | --- |
| ReadDeviceData | 以调用者给定容量建立缓冲，完整消费后再读一块；GetSize转DeviceIo.size | 本库构造器无直接调用者；本轮线性vtable候选仅构造/析构。实际实例化和服务命令绑定未证 |
| DeviceIo::read/lseek | 原read可接受64位count参数，lseek接口有64位offset参数 | read返回会截为32位；本库没有直接lseek调用者，不能据签名推出可续读协议 |
| 匿名文件辅助函数0x10994，operation1 | 清零调用者给定长度后，读min(请求长度,文件大小) | 没有offset参数或seek，只读普通文件开头；忽略read实际结果，未确认USB命令可达性 |
| DeviceIo::size | 普通文件64位大小；块设备ioctl0x1260取扇区再左移9位 | 失败也可得到0；未测量用户机身驱动是否支持或真实分区容量 |
| 当前FirmwareUpdateFunc | 原函数直接返回NULL | 不能因函数名就认为有可用的固件读写实现 |

[14个原函数、内部辅助函数及直接引用](original-read-route-review.json) 固定了每段原字节与调用地址。无直接调用者不等于永远不可达；这里没有排除间接表或动态扩展。

FirmwareUpdateFunc结论仅限此回调，官方升级器的其它入口须独立核对。

## 11组原限量前缀读取验证

[执行结果](run-original-prefix-read/results.json) 共1920次原指令/边界进入，连接原文件操作辅助函数与DeviceIo open/read/close/size/fstat/ioctl包装；系统调用、文件字节、容量及错误日志边界仍是显式自写提供者。

- 声明79MB文件、请求32字节或64KiB：原代码分别准备32或65536字节读取。
- 文件小于请求量：读取量取文件大小；缓冲剩余部分已清零。
- 声明短读31/32、read返回-1、块设备容量查询失败：辅助函数仍可return0；读取失败时模型缓冲全零。
- 文件大小超过4GiB、请求32字节：本辅助函数的size比较保留64位，仍准备32字节读取；它与157轮旧GET_FILE2的长度处理不同。

这里的64KiB是guest自己的约束，不是固件内置上限。原函数先执行memset(请求长度)，因此还必须证明实际目的缓冲至少同样大；不能将“read取最小值”充作分配安全证明。普通文件每次重新open且分支内没有seek，重复调用不能自动拼成完整文件。

POSIX提供的pread含offset/count、不会改变共享文件位置，但允许短读；lseek改变位置。它们的语义不能替代相机服务命令的身份、路径、缓冲容量和清理证据。[pread(2)](https://man7.org/linux/man-pages/man2/pread.2.html)、[lseek(2)](https://man7.org/linux/man-pages/man2/lseek.2.html)。

首轮guest在原__fxstat四指令小跳板前被观察器拒绝，保存于attempt-prefix-stat-thunk。补齐时曾填错分支字节常量，保存于attempt-stat-thunk-byte-constant；现按原件逐字节核对并只允许0x167c8..0x167d8，没有放开周围代码。

## 对下一步的影响

继续追踪命令表或动态模块如何选择这些读取组件，重点是有限缓冲、按块前进、真实字节计数、可核对的清理与固定目标身份。本轮限量前缀读取不具备完整备份所需的续读和错误传播，ReadDeviceData也尚未形成已验证的服务入口，因此不发布读取工具或发送新命令。

全部16项主录/恢复要求不变。MAIN 1080/29.97 HEVC42010约16Mbps、同机完整备份/恢复回读及独立救援仍需实际证据，没有可刷包或首次刷入日期。[汇总复核](bounded-read-scope-review.json)
