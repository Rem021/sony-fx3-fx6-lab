# 第187轮：FX3 机身侧只读工作器候选 0.3

2026-10-29。**新增机身侧定长读取工作器C源码，并打通其保存格式到本地主机镜像工具。** [工具0.3](../../../outputs/fx3-recovery-adapter/README.md) · [工作器源码与边界](../../../outputs/fx3-recovery-adapter/native/README.md) · [源码包](../../../outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.3.0.zip)。目前只有Linux AArch64可重定位对象的编译证据，未链接成可运行模块，未在FX3上加载或执行。

## 实现与选择

原厂整文件读取尚无受控偏移续读证明；社区工作器的preload删除和加载路线有持久副作用。本轮实现独立显式函数入口`fx3_p1_read_window()`，没有构造函数、preload、USB／认证、源分区写入、删除或自动重试。只编译候选，不启用任何加载路线。

工作器固定O_RDONLY打开`/dev/cnflasha1`，从/proc/partitions核对唯一的pnflasha1／cnflasha1及容量，再核对真实块设备号和前后元数据。设备号来自内核记录，不套用A7C II的252:129；配置容量25,100,288字节仍需实机确认，任何不符或ioctl不支持即拒绝。

以显式pread64偏移读取每组最多128×65,536字节，检查真实返回数、保护区、调用前后时钟、固定范围和源身份；短读不补读、不填充。固定读取阶段预算60秒、块调用5秒不能打断阻塞syscall，也不能保证所有元数据／输出调用的结束时间。真实阻塞会保留在该调用内，不启动清理线程或替代请求。

输出固定到/tmp_wbshd，经打开目录的fstatfs确认tmpfs、可写及容量，使用新0700目录、独占0600文件。输入请求必须是该RAM目录下root所有、0600、单链接的64字节普通文件，检查完整范围、CRC和保留位。空间不足、负可用块数、同名目录或其他文件系统均拒绝。不自动挂载、删除残留或创建持久配置。

源分区关闭成功后才生成manifest，但manifest写入／关闭／目录同步仍会失败。因此解码器同时要求调用者提供正常返回0，不能把“完成文件存在”充作成功。返回码标记为调用者提供、未经相机独立观察，硬件／来源／救砖标志始终false。同进程生产入口只允许一次，没有fixture重置入口。

新增`worker.py`和`assemble-worker`：独立解析64字节请求、128字节块头及清单，核对每组capture ID、全局偏移、实际长度、设备号和CRC，拒绝混组／重排／缺块，再重组完整本地文件并回读。这个命令不加载C对象或运行相机代码；也不要求事先知道首次机身采集的全SHA。

## 当前验证

共**38项当前本地测试通过**：

- [11项编译工作器／解码测试](runs/worker-tests-ABI-final/test-receipt/results.json)：同一C算法在Mac构建中执行，Linux系统调用是自建夹具，源字节及输出为真实本地文件。覆盖请求／权限、tmpfs／空间、重复分区行、设备类型／编号、前后容量、短读、错误、越界缓冲、身份变化、时钟、部分写入、关闭／同步失败、入口重放和解码篡改。阻塞夹具由测试明确释放，没有强杀、重置或自动重试。
- [14项主机采集回归](runs/capture-tests-final/test-receipt/results.json)：保持0.2定长读取、日志、完整回读及未知状态拒绝。
- [13项原适配回归](runs/adapter-tests-final/test-receipt/results.json)：两份真实Sony 2.04／2.05参考载荷再次构建与精确还原，原件哈希不变。

三组C夹具输出完成383块完整组合→重新解析参考库→限定候选构建→精确还原；还原结果与输入合成文件逐字节相同，`assemble-worker`命令实际执行通过。完整输入是明确标记的Sony2.05载荷人工补0xff尾部，**不是本机7.02读回**。

AArch64对象检查确认ELF64／EM_AARCH64／ET_REL，没有未解析导入、初始化段或fixture重置入口。该对象未执行；Mac执行结果不证明AArch64系统调用ABI、真实tmpfs、Sony内核或块驱动支持。初编译对象与早先测试运行均保留，当前验收仅引用ABI-final工作器回执及两份final回归回执。

联网读取并保存Linux4.9 stat／statfs／unistd UAPI，核对12个系统调用号及statfs字段。复核发现可用块数为有符号字段，补负数拒绝后重跑全部11项工作器测试；Python源码未变，已通过的14／13项回归回执仍对应当前源码。[ABI参考与SHA](kernel-ABI-review.json) · [代码检查](implementation-review.json)。参考[statfs UAPI](https://github.com/torvalds/linux/blob/v4.9/include/uapi/asm-generic/statfs.h)与[pread语义](https://man7.org/linux/man-pages/man2/pread.2.html)不替代Sony实机验证。

## 发布与实际缺口

源码包51,251字节，SHA-256：`fa6b178b439013e2ac0a501ce2ef0a7fabc085b1612642b17eb277dc5b64c0b8`。16份源码／说明／测试文件，无Sony固件、编译二进制、原件或私有备份；0.1／0.2包保持保留。[发布回执](release-receipt.json)。

下一项是链接和受审查的显式启动／传输路径，优先寻找单个临时进程的受控入口，避免全局preload修改；同时补同机绑定与正常服务归还。现有MSC原生通道尚未接入真实root拥有者，SERVICE端点、认证尾部写入／线程退出等缺口并没有因工作器源码而消失。

分组间仍可能变化，尚无原子快照或独立一致性证明；p1仅是更新引擎分区，**不是完整eMMC、MAIN／设置／校准或硬砖恢复备份**。当前7.02 p1、实际写回、独立救援、DAT封装、菜单RAM门及1080p29.97 H.265主录均未验，不能据此开始首次刷入。

本轮新增相机／USB／管理员／Windows／GUI操作为0。16项要求、全部授权、prepared方案和恢复优先次序保持。`goal_complete=false`、`persistent_write_release=false`，原生目标管理器未改。
