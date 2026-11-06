# FX3 当前 GPIO驱动与 SIO速率差异

2026-10-29；经典 ILME-FX3 7.02；离线官方原件分析。

**当前主系统 GPIO接口已对应到寄存器层；SIO速率仍存在尚未解释的差异。** 官方7.02 helper请求值为19（0x13），A7 IV参考恢复载荷使用3。历史FX3 p1驱动会将该请求写入速率寄存器，因此不能因208轮通道／引脚号一致，就直接认为参考载荷可用；也不能未经时钟分析就将3改成19。

## 当前 GPIO实现

本轮从已有官方7.02 p3 FAT镜像重新读取 `/vmlinux.bin`，6,610,952字节，SHA-256 `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`。它与47／146轮的原内核逐字节相同。复用已核对的只读符号解析器重新恢复41,269项，与既有目录一致，没有执行原符号展开函数或内核。[镜像绑定](kernel-source-binding.json)、[符号选择](current-kernel-symbol-selection.json)。

207轮只筛选了udif平台目录下GPIO片段；这轮扩展到 `drivers/char/gpio-sn.c`、`gpio-sn.h`、`include/linux/gpio/gpio.h`，取得了字符设备实现及公开结构定义。它们来自 [Sony FX3 Ver7.00开源归档](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)，仅作为参考；以下关键结论还逐项核对了7.02原内核字节，未将整个7.00源码称作精确7.02构建。

| 对应关系 | 原7.02内核证据 |
| --- | --- |
| ioctl `0xC0104702` | `gpio_ioctl`在偏移0x277738，命令归一化索引2跳到0x277878，再调用0x276520 |
| 16字节参数结构 | 原复制长度16；portid在+4、bitnum在+8、value在+12，吻合207轮库入参布局 |
| GPIO端口4资源 | 当前原资源表中 `gpio_p4` 物理基址为0xF1021000、长度0x1000，吻合参考公式 |
| 实际驱动绑定线索 | 原 `gpio_fops` 包含该 `gpio_ioctl` 指针；`gpio_probe`将资源的VA放入每端口96字节状态 |
| 模式9（GPIO＋OUTPUT_H） | 原码依次写 PORTSEL_SET+0x34、INEN_SET+0x24、WDATA_SET+0x44、DIR_SET+0x04，掩码为1左移位号 |

这里的地址是固件文件中的静态资源定义。没有查询机身当前映射、读取实际寄存器或测量引脚电平，也没有证明安装中的p1内核／提供库与这些主系统原件相同。

参考载荷的初始化次序是先写高电平，再设输出方向、切到GPIO，随后把端口4的0／1／3位复用回SIO；没有显式写 `INEN_SET`。两边对CS的最终复用／方向／高电平意图相符，但写入顺序及输入使能处理有差异。初始寄存器状态未知，不能据此宣称波形或瞬态等价。

## SIO请求与速率字段

当前官方7.02 `ud_darwin_firmup.elf` 的原指令：

- 0x401330—0x40133C：`ioctl(fd,0x40046742,0x13)`。
- 0x401374—0x401384：`ioctl(fd,0x40046741,0x1000)`。

历史官方2.05 p1 `sio.ko`，SHA-256 `a53bc267050ed81e3d81d99287a7ae541381ecea88d2f4f5948e29b45af02eb0`：

- 0x40046742分支将低32位参数存入通道结构+12；`sio_master_transfer`再将其低字节左移24写SIO+0x14，高字节左移到高位写SIO+0x18。
- 0x40046741分支把参数的低／高字节存入通道结构+8／+9，不能把0x1000直接称为频率。

固定提交的A7 IV参考 `darwin.c` 定义 `SIO_RATE=3`，同样写入+0x14/+0x18。因此在上述历史驱动解释下，当前helper的低速率寄存器字为0x13000000，参考载荷为0x03000000，二者有明确字值差异。

**这不是已测得的Hz差异或已确定的移植错误。** 当前安装7.02 p1的SIO模块身份未取得；早期载荷与Linux运行时的父时钟也未证明相同。需要继续查两种环境的时钟来源和分频公式，再决定FX3恢复载荷的速率配置。参考timer头里的4MHz也仍是参考声明，没有升级成FX3实测频率。

## 对第一次刷入的影响

本轮已把“默认引脚一致”推进到当前GPIO接口、资源地址及操作语义，同时找到了会影响真实链路的SIO配置差异。接下来核对SIO父时钟与分频，并保留独立AP启动、当前同机boot0/p1备份、逆写及故障后恢复验证。全部16项要求、1080p29.97 HEVC MAIN与长录验收保持原状态。

没有新增相机／USB／缓存查询、管理员／驱动操作、认证、机身文件访问、载荷上传或固件写入；只解析普通本机文件，没有运行Sony原代码或guest。195轮仅主机root01具体批准继续待答，未启动也未重问。工具0.4发行物未改变。

## 复核入口

[GPIO与SIO合同证明](GPIO-and-SIO-contract-proof.json)绑定16个原始范围（7个当前GPIO函数、4个当前数据区、2个当前helper范围、3个历史SIO范围），并保存7段源码行范围。GPIO原函数范围取下一更大kallsyms地址，不冒充DWARF函数长度。

[GPL捕获](GPIO-source-capture.json) · [当前GPIO函数](current-GPIO-function-capture.json) · [源码行片段](source-pins/) · [原始范围](pins/) · [行范围修正与保留原件](source-pin-refinement.json)

[核查回执](verification-receipt.json) · [实施边界](implementation-review.json) · [来源审查](web-source-review.json) · [封存清单](final-receipt.json) · [前轮记录角色](../stage208-Backup-record-routing/README.md)
