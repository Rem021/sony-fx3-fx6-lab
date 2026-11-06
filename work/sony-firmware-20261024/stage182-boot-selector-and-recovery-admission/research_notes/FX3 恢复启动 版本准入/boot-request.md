# 经典 ILME-FX3 7.02 的启动请求、消息接收边界与 mode5

## 7.02 原 helper 实际改变什么，0／2／5 如何编码

### Takeaway

7.02 的 `/bin/up.sh` 同时操作两层状态：`/setting/updater/mode*` 持久文件，以及可选的一次 OSAL 消息。原 `ud_send_lsi.elf` 本身不写启动分区或设置文件；它先读一个 Backup 项，只在首字节为 1 或 2 时把 argv 数值原样作为 4 字节消息交给 `0x804b0376`。**helper 返回 0 既不证明发送过请求，也不证明收到完成应答。**[7.02原脚本](../../evidence/boot-request/originals/bin/up.sh)；[helper完整原反汇编](../../evidence/boot-request/disassembly/ud_send_lsi.elf.txt)

### Cited Findings

本次从 SHA-256 `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5` 的官方 7.02 AP ext2 原映像只读提取，未挂载映像、未执行 Sony 代码。工具为本证据目录隔离 Python 环境中的 Capstone 5.0.9、pyelftools 0.33；路径、工具版本、操作边界另记。[来源清单](../../evidence/boot-request/source-manifest.json)；[工具与边界](../../evidence/boot-request/static-tools-and-scope.json)

| 7.02 原成员 | 字节 | SHA-256 | 本轮用途 |
|---|---:|---|---|
| `/bin/up.sh` | 6572 | `c774320a0ab92c13b467b9219e1f60262a1effa0b551ba3b713514a36dadc402` | 文件状态和 helper 调用 |
| `/bin/ud_send_lsi.elf` | 10248 | `5fbcdb8d9795828febbf6ce9cb966aec2adeff6311577184e4fb8abecfd163e7` | 原 main 请求／返回值 |
| `/lib/libbackup.so` | 14232 | `6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d` | Backup_read 包装 |
| `/lib/libosal_uipc.so` | 43752 | `09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3` | 消息到设备 ioctl |
| `/kmod/osal_uipc.ko` | 76168 | `6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38` | 原内核接收、队列、回调 |
| `/kmod/upm.ko` | 453896 | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` | 已启动后 loader mode 对照；不充请求接收者 |

表中每份文件来自当前版本官方 AP，非当前相机读回。12 个关键函数／片段的原字节 SHA、节区、起止地址另存，模块地址全部是节内偏移，重定位尚未应用，不能当作实机 VA。[来源清单](../../evidence/boot-request/source-manifest.json)；[原指令片段指纹](../../evidence/boot-request/function-slices.json)

| `up.sh` 分支 | 先改的文件 | 最终 argv |
|---|---|---:|
| 无参数，原 `mode` 存在 | 删除 `mode*`，sync | 0 |
| `user` | 删除旧 `mode*`，新建 `mode`，sync | 2 |
| `ms` | 删除旧 `mode*`，新建 `mode` 和 `mode5`，sync | 5 |
| `verskip` | 删除旧 `mode*`，新建 `mode` 和 `mode6`，sync | 6 |

以上分支末尾先检查 `/root/IAMUPDATER`：存在就 exit 0；不存在才执行 `ud_send_lsi.elf $mode_num`。**verskip 确实发送 6，不发送 5。**当前官方 mount 计划把 `/setting` 映射到 nflasha2 vfat，因此这些文件是计划中的持久存储状态；本轮未读当前相机实际挂载。脚本额外存在 debug/consoff 条件，可改 p1 的 console 配置，应与只看 mode 文件的简化模型区分。[7.02 up.sh 行15–71、282–367](../../evidence/boot-request/originals/bin/up.sh)；[7.02 mount.conf](../../current-updater-evidence/tar-selected/0100_config/mount.conf)

原 helper 的 `main` 由入口 `_start` 的 main 指针定位为 `0x400990`，关键指令是：

| VA | 原指令／导入 | 可以直接确认的行为 |
|---|---|---|
| `0x400994–0x4009a8` | `cmp w0,#2`，否则 `exit(1)` | 严格要求一个 argv 参数 |
| `0x4009b0–0x4009d4` | `Backup_read(0x004b0000, &stack_byte)`；返回 <=0 则记录错误、exit 1 | 先读 Backup 项，非先发消息 |
| `0x4009d8–0x4009ec` | `ldrb`、减1、`uxtb`、与1比较，高于1跳退出 | 只允许原字节 1 或2；其他值返回已置0，不发送 |
| `0x4009f0–0x400a04` | `osal_valloc_msg_wait(0x804b0376, &msg, 4, 1)` | 4 字节载荷分配 |
| `0x400a38–0x400a44` | `osal_set_msg_src(msg,0x004b0379)` | 设置回复来源 ID |
| `0x400a48–0x400a64` | `atoi(argv[1]); str w0,[msg]; osal_snd_msg(0x804b0376,msg)` | 0／2／5／6 等数值原样送出；无模式枚举或改写 |
| `0x400a9c–0x400aac` | `osal_rcv_msg_tmo(0x004b0379,&msg,0xbb8)` | 一次 timeout 参数3000的接收调用 |
| `0x400ab0–0x400ac0` | 比较接收结果0和`-0x3fe`（-1022），两者均跳清理 | 发送已成功时，这两条路径均保留最终返回0 |
| `0x400a88–0x400a98` | `osal_free_msg(0x004b0379,msg)` | 清理；没有检查回复正文 |

[完整原 helper 指令及 PLT 导入](../../evidence/boot-request/disassembly/ud_send_lsi.elf.txt)；[12片段指纹](../../evidence/boot-request/function-slices.json)。此处只把 -1022 当作原返回数值，未凭名称擅自指定它的错误含义；“3000”是原 API 参数，未实测等待时间。

`libbackup.so::Backup_read` 位于 `0x1dd4`，通过 `backup_sync_msg` 请求 `0x003e014d`，不是 helper 直接打开设置设备；当前证据未给 Backup ID `0x004b0000` 完整持久化合同。脚本虽声明 `LSI_MAIN=1`、`LSI_SUB=2`，不能只凭未被调用的脚本常量给该 Backup 字节增加硬件语义。[Backup_read原包装](../../evidence/boot-request/disassembly/libbackup.so.txt)；[脚本常量](../../evidence/boot-request/originals/bin/up.sh)

### Inferences

- 已确认持久化动作来自 shell 的文件写入＋sync；已确认 helper 动作为读取 Backup 状态＋分配／发送／接收／释放消息。它是否还会经实际接收者改变寄存器、CP状态或下一次启动存储，须继续追下面的动态回调，不能从程序名补全。
- 把 helper 的 0 返回当作“进入恢复器成功”会造成假阳性：Backup 字节不符合时完全不发送；实际发送后接收0或-1022均可返回0，而且正文未经检查。只读取脚本返回码不足以作启动验收。

### Gaps

- Backup 项 `0x004b0000` 的当前实际值、产生者、存储介质和跨掉电语义未取；没有新的相机查询。
- 旧 2.04／2.05 helper 的 SHA 都是 `9fb4bd02b3434bd9fe8fb49fcf4359f7720b292506960ae0d9894332d3453c80`，与 7.02 不同。up.sh相同不允许把旧 helper 实现冒作当前实现。[历史2.05原件](../../../../fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/ud_send_lsi.elf)；[来源清单](../../evidence/boot-request/source-manifest.json)

## 请求经过哪个设备、ioctl 与内核接收路径

### Takeaway

当前 7.02 请求已追到原内核动态回调调用点：`/dev/uipc` → ioctl低32位 `0x80000004` → `osal_uipc.ko` 分派 → 共享消息地址转换 →队列 `0x376` → 回调节点 `+0x10` 的函数指针，在 `.text+0x3644` 用 `blr x3` 调用。**本轮并未解析出这个队列实际登记者及最终回调函数地址；到达此处不等于到达LSI或bootloader。**[原用户库](../../evidence/boot-request/disassembly/libosal_uipc.so.txt)；[含原重定位的内核全文](../../evidence/boot-request/disassembly/osal_uipc.ko-full-text.txt)

### Cited Findings

| 层／地址 | 原证据与条件 | 后继 |
|---|---|---|
| libosal_uipc `do_init` `0x33e8` | `open("/dev/uipc",2)` 在 `0x3410`，保存fd，并mmap消息共享区 | 用户库fd与共享内存 |
| `osal_snd_msg` `0x5e60` | 检查ID；在 `0x5eb8` 按bit15选择；本ID bit15=0 | `0x6050` 调 `u_osal_snd_msg` |
| `u_osal_snd_msg` `0x3a10` | 栈结构首4B=目的ID，+8=消息指针；`0x3a48` 调ioctl | 请求低32位 `0x80000004` |
| osal_uipc.ko `.text+0x4d8` 未导出分派器 | 从cdev请求取command，`&0x7fffffff`；范围0..16；复制16B参数并核对所属进程 | `.rodata+0x340` 函数指针表的index4，即 `.rodata+0x360` |
| `.rela.rodata+0x360` | 原 `R_AARCH64_ABS64` 重定位指向 `.text+0x13c0` | send handler |
| send handler `.text+0x13c0` | 消息指针减进程共享映射基址，要求偏移 <=`0x1fffff`；加内核共享区基址；`0x13f4` 的原CALL26目标 `osal_snd_msg` | 内核 `.text+0x3bf8` |
| 内核 `osal_snd_msg` `.text+0x3bf8` | 本ID bit31=1，但`ID & 0x70000000=0`，所以不走 `0x3d94` 的另一远端函数指针；按低16位`0x376`查队列 | `.text+0x2938` radix lookup，未建时`0x2ee8` |
| radix lookup `.text+0x2938` | 从 `.bss+0x2640` 派生嵌套表查找，队列0x376分组索引 `1/5/6/6` | 原队列record（运行状态） |
| 内核send `0x3cbc–0x3d18` | 根据消息优先级链接队列；按queue flags选择执行 | `.text+0x36e8` |
| `.text+0x36e8` | 在queue flag bit0条件下移出消息，并调用 `.text+0x35b8` | callback walker |
| `.text+0x35b8` | 读取登记链节点；`0x3634`读节点+0x10函数指针；传消息/节点/队列 | **`.text+0x3644 blr x3`，实际target未解** |

[用户库全部原指令](../../evidence/boot-request/disassembly/libosal_uipc.so.txt)；[内核全部原指令与节区重定位注释](../../evidence/boot-request/disassembly/osal_uipc.ko-full-text.txt)；[内核符号、字符串及各原函数边界](../../evidence/boot-request/osal_uipc.ko.metadata.json)；[片段SHA及地址合同](../../evidence/boot-request/function-slices.json)

这条路径是具体进展：原 helper 并不直接调用一个“set_boot_mode”设备 ioctl；它用通用消息设备，内核把共享缓冲区地址转成内核地址后入队。已确认的最终代码只改变消息队列／回调 bookkeeping；尚未把请求连接到任何持久 boot selector 写入。[send handler与回调原指令](../../evidence/boot-request/disassembly/osal_uipc.ko-full-text.txt)

本轮静态扫描了 AP 的可见 ELF 指令立即数、原字节字面值以及内核符号名，留下完整候选记录；没有获得 queue0x376 回调登记地址。扫描只用于缩小范围，**不是对所有动态生成、其他处理器、WBI已装载模块或跳转表形式的穷尽排除证明**。[接收候选扫描](../../evidence/boot-request/receiver-candidates.json)；[含flags候选](../../evidence/boot-request/receiver-flags-candidates.json)；[内核候选](../../evidence/boot-request/kmod-symbol-candidates.json)

### Inferences

- 下一具体切口不是重新搜“FX3救砖”，而是恢复 **queue0x376 的原登记节点及其 `+0x10` target**，对应 `osal_reg_msg_queue_cb`／`reg_msg_queue_cb` 的登记者，或可识别的官方WBI快照内同一数据结构。之后才可给0/2/5/6各自的boot请求效果命名。
- 当前只证明消息进入通用内核机制的可能调用链，不证明当前机身有该队列、已登记回调、消息实际消费或处理器切换。

### Gaps

- 未解的精确间接调用：`osal_uipc.ko SHA6aa0…` `.text+0x3644 blr x3`，指针来自 queue0x376 callback链节点+0x10。目标地址／所属原模块／登记时机尚无证据。
- callback target之后的LSI请求编码、寄存器／备份项／NOR或eMMC改变、跨掉电保持和下一次启动的消费者均不能填写为事实。这里既未到bootloader，也未证明MAIN损坏时能自行运行此发送链。

## mode5 是SD选择器还是更早启动触发，当前能下什么结论

### Takeaway

mode5 已证明是**历史2.04／2.05独立 updater内部的SD输入选择**；当前7.02又证明把5同时传给一个未解语义的消息消费者。因此不能断言“mode5只选SD且不影响早启”，也不能反过来宣布“发5就能独立强制启动updater”。本轮可靠结论是把文件选择、消息请求、已启动后的loader mode、bootloader选择分开。[7.02脚本与helper](../../evidence/boot-request/originals/bin/up.sh)；[历史2.05 UdtrMain](../../../../fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/UdtrMain.sh)

### Cited Findings

- **历史2.05** `UdtrMain.sh::getCurrentMode` 消费 `/setting/updater/mode*`，缺mode走production；mode5在多个其他模式之后判断，随后 `execute_ufp.sh` 5分支加载卡驱动、启动 `sdfileinput.elf`。这是原历史脚本控制流，不能替代当前7.02 p1脚本。[UdtrMain历史原件](../../../../fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/UdtrMain.sh)；[execute_ufp历史原件](../../../../fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/execute_ufp.sh)
- **当前7.02** MAIN init2从 `/proc/udm/upm_bootmode` 读“已经选中的”loader启动状态；AP `upm.ko` 有 `LDR_BOOT_MODE_UPDATER` 等原字符串，`k_upm_get_ldr_mode` `.text+0x34b8`只从全局读一个w值返回。它不是本轮已证明的queue0x376消费者，不能用相同的“mode”字眼把两者相连。[7.02 init2](../../current-updater-evidence/p3-initrd/sbin/init2)；[UPM符号及字符串](../../evidence/boot-request/upm.ko.metadata.json)；[get_ldr_mode原指令](../../evidence/boot-request/disassembly/upm.ko-k_upm_get_ldr_mode.txt)
- 当前官方7.02包有MAIN kernel/initrd与NOR loader成员，但不含规划中的nflasha1 payload；当前p1完整updater原件仍是缺件。NOR `loader_nor.bin` 为101888字节，SHA `4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942`；本轮仅核对身份和有限静态字符串，没有把它标成已解码的selector。[本轮资产核查](../../current-updater-evidence/current-updater-asset-audit.json)；[精确原件指纹](../../evidence/boot-request/source-manifest.json)

### Inferences

- 文件mode/mode5可以先于MAIN故障保留，但“已经存在”不证明更早引导必然读取它；当前脚本发送链又需要正常环境中的用户程序、Backup服务和消息接收者。MAIN完全坏后，尚没有独立进入这条链的证据。
- 若后续解析queue0x376回调只发现“选择处理器／重启”，还要追其后续请求与NOR/CP loader如何选择p1/p3；若发现持久selector写入，则须按真实写入介质继续查消费者和掉电合同。两种结果目前都未定。

### Gaps

本轮停在精确的内核间接调用，没有新增相机、USB、服务认证、管理员、Windows/UU/GUI、Pico／串口动作，没有执行原固件／原shell、没有生成可传相机的payload或固件。下一轮最小目标为**识别queue0x376的登记节点+0x10原函数**，并将它与0/2/5/6的真实效果关联；当前p1缺件及NOR selector尚未解码是另外明确的边界。[工具及操作边界回执](../../evidence/boot-request/static-tools-and-scope.json)
