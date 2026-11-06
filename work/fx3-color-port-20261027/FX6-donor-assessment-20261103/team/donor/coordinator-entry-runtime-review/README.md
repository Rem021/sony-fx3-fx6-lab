# FX6 入口在固定 FX3 平台的首次有界运行复核

2026-11-03。**接受 `fx6entry-a39715a8` 的有限入口执行和清理证据，尚未运行真正 FX6 主程序。** 本包仅替换 FX6 `bootin.elf` 与 `im.elf`，IM 可执行段与 FX3 原件相同，其余为既有 FX3 系统。

协调者直接复核 [receipt.json](receipt.json)：34 项 argv 中只有 serial 路径索引 20 与 CPIO 文件路径索引 31 改变，加载地址／选项、完整 DTB、FX3 内核、QEMU、CPU/RAM/GIC 参数和五项模型环境保持冻结；对基线全部固定文件和候选重新计算 SHA。串口 SHA 与回执一致，六段首证原文字节范围逐段吻合，复核时双锁可独占取得并立即释放。

该轮 32.38 秒内观察到：loader verify/list/BusyBox true 三 RC 均为 0，原 init 自然启动 `bootin`，`/usr/bin/im.elf` 可执行映射，随后现有 FX3 AP 的第一条可见队列发送。收到入口证据即按预算结束；QEMU exit 0/reaped，API16 获 guest 确认并核验原字，实际键输入为 0。

首条 IPC 是发送侧标记，不证明接收、完成或功能闭环。包内没有 FX6 `appFw.so`、AV 或 CP，因此不证明 FX6 菜单、拍摄或完整系统开机。下一步是实际 FX6 AP 的依赖与辅助接口适配，FX3 原固件的持续菜单可用性另行验证。

此前 `fx6entry-b3256731` 在 `-S` 初始暂停状态因宿主 AF_UNIX 绝对路径过长失败、串口 0 字节；该历史失败保留。修正相对 socket 连接后只进行了这一次获准补测，不将前次失败算作固件拒绝。
