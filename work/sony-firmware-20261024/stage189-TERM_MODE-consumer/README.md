# FX3 7.02 TERM_MODE与固定库装载入口复核

2026-10-29。原 ARM64 指令的 **30组局部检查符合预期**，其中24组 TERM_MODE 在发送消息前返回 `0x80`；两组对照分别停在 OSAL 分配和 testcmd 初始化前；四组固定库装载前缀核对了真实挂载参数和拒绝分支。所有固件代码只在 Unicorn 的 guest 内存中运行，mount／文件操作／IPC／dlopen／USB 均没有实际调用。未证明机身启动、备份、写回或独立救砖。

持续目标仍为“持续研究，直到可以正常刷入”，原生状态已[重新读取为active](native-goal-observed.json)。早先 STOPPED 是助手误读旧清除事件的记录，已被[恢复回执](RESUMED.json)取代；原记录保留，不代表当前停止。设备权限、16项目标要求和恢复优先顺序不变。

## TERM_MODE原分派

[532个AP ELF盘点](AP-terminal-inventory.json)已核对原件哈希。`libsencore.so` 中记录名 TERM_MODE 的命令为 `0601:801f`，不能把名称或目的字段 `0x003d025f` 当作可用终端证明。

原 `AdjustControlFunc` 调用 `SubsystemCommunicationCommand::TransactionStart`。后者在命令表匹配后于 `0xfe10` 检测到表项的 `0x8000` 分类，跳到 `0xfbc8` 设置不可用分支，最终在 `0x10174`／`0xfff8` 返回 `0x80`。用户通常发送的 `0601:001f` 和原表值 `0601:801f` 均受阻。此拒绝在本分支中发生于认证级别细分及 IPC 前，未执行目的字段所指的处理端。

[原指令结果](dispatch-guest-results.json)：两种命令值×三种载荷0/1/2×四个级别0/1/2/3，共24组均原样返回128；原指令和表不改动。两组 `FCT_MODE` 对照分别到达 OSAL 分配／testcmd 初始化边界后停止，未虚构成功回复。输入是已解码请求，Serialize／memset／日志为明确夹具；不代表完整 USB 或认证运行。

PMCA 当前 master 的[维护者源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L1031)在 `setTerminalEnable` 中忽略 ADJUST 异常。调用未抛异常不能确认 TERM_MODE 已开启。原 ProductInfo 的 ACK1 与这个下游拒绝是两项结果，不能互相代替。源码仅保存为[文本](pmca-sony-source.txt)，[提交与哈希](public-client-review.json)已固定，未导入或执行客户端。

## 固定FIFO与固定库入口

[797个AP普通文件扫描](fifo-route-review.json)中，完整 `sen_host_req/res` 路径字面值仅见于 `libsencore.so`。另两个内核模块的 `host_reset/resume` 为宽匹配命中。原 HostCommunicationCommand 由 TestMode 构造，与 ADJUST TERM_MODE 分支分开；目前没有从这些路径字面值识别出接收进程。动态拼接、其他分区或运行时接收端仍未排除。

[固定库装载前缀的四组原指令检查](fixed-loader-prefix-results.json)进一步确认：原 `adj_cmd_set_file` 会经过 `sys_mount`、`CFileAccess::mount` 和 `selection_mount`，在任何库写入／装载前，尝试：

```text
mount source=/dev/nflasha6 target=/tmp/jiritsu type=vfat
flags=0xc0ed0490 data=NULL；未设置MS_RDONLY
```

试验停在原 libc mount 调用之前，没有给它伪造成功返回，也没有查询当前机身挂载状态。故 `/tmp/jiritsu/libJit.so` 不能被当作已证的纯 RAM 入口。后续正常写入的 `0x241` 标志含 WRONLY／CREAT／TRUNC，缺少 EXCL／NOFOLLOW；成功 dlopen 也不证明构造函数中的工作器成功。

`set_file2` 的普通 operation0／area2 会先拒绝，status为 `0x10000201`，本组停在后续 close 前；其他模式不被这项结果概括。旧 `set_file` 的不支持操作也会外层返回0、内层status报错，必须保留双层结果。

## 验证、保留项与下一步

[交叉核对回执](verification-receipt.json)独立核对14个 PLT 符号、原函数来源和30组结果；0.4源码与不可变源码包仍相同，未把上一轮47项测试算作本轮新测试。本轮未生成新的上机模块或修改固件。初次描述符前缀长度断言失败的[完整脚本与错误](dispatch-guest-initial-failure.json)保留；修正17字节长度后才执行 guest。

工具仍为[0.4](../../../outputs/fx3-recovery-adapter/README.md)：自写 ARM64 读取工作器只在假内核中完成383块，不是 Sony/Linux 装载或真实机身备份证明。当前7.02机身p1读回和 MAIN 失效后的独立恢复仍缺实证。

下一步优先追其他已存在的独立进程／RAM装载路径及其原接收端，核对初始化、文件所在文件系统、等待／退出和失败副作用；同时继续当前 updater 选择与回写范围。已排除的 TERM_MODE 和普通固定 libJit 路线不作为现成启动入口，不通过修改命令表或忽略错误来伪造可用。没有新增设备动作。
