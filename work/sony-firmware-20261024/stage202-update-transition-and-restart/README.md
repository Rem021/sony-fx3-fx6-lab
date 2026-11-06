# FX3 模式准备、重启请求与历史恢复分区的重启程序

2026-10-29。**已把当前7.02的hot/cold重启请求追到同一包中的UPM接收线程和关机状态处理函数；也找到了历史p1重启工具向Darwin发送的`0x11/3`帧。两者都需要AP软件环境先运行，尚未解决MAIN无法启动时怎样独立选择p1。**

本轮为宿主静态分析，18份原件切片（含数据表）、11项原始编码核对。未执行Sony程序、脚本、模块或guest；没有相机、USB、root、管理员、Windows、UU、驱动或GUI操作。持续目标、16项要求和全部授权保留；`goal_complete=false`、`persistent_write_release=false`。

## 当前主系统的重启请求送到哪里

来源是已验证7.02 `nflasha15.img`。`libObj.so` SHA256为 `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae`；重新提取的 `upm.ko` 为453896字节，SHA256 `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e`。地址均为来源ELF VA或模块节偏移，未取得机身PC。

`libObj` 中带有 `reboot hot`／`reboot cold` 日志的两个包装器，分别在 `0xCE4BC`、`0xCE530`。它们都尾调用 `0xCDBBC`，后者在输入条件通过、16字节消息分配成功后：

- 向queue `0x80920021` 发送消息，首word为 `0x00920141`。
- hot路径的另两个固定word是 `0x8C`、`0x1B`；cold路径是7、`0x1C`。末word来自调用者，公共构造函数要求该参数及另外两个入参非零。这里仅登记原字段，不将这些数值另行解释为p1/p3编号。
- 当前 `UPM.text+0x378` 的线程明确阻塞接收同一queue，并在 `+0x3E4` 调用重定位指向的 `k_upm_api_off_factor_async`。
- 该API接受首word `0x00920141`，随后调用 `k_upm_off_factor_handler`。后者按既有运行状态分派到active、inacting_app、inacting_im、inacting_cp等处理函数；选中active路径还有无限等待参数的信号量调用。

因此，已找到的源代码链是“**请求入队→UPM接收→按状态处理**”。发送成功只说明局部入队结果，不证明AP已复位、下一次启动选了哪个分区或故障时状态机一定推进。没有向该队列发送消息，也没有把它接入可运行设备后端。[完整来源与18份切片](restart-route-proof.json)、[公共消息构造](pins/AP-power-message.txt)、[真实UPM接收线程](pins/UPM-queue21-thread.txt)。

这里还纠正了一个探索性误读：`.rodata+0x2C8` 的 `0x00920141` 后指针重定位到 `.rodata.str1.8` 中的 `UPM_CMD_OFF_FACTOR` 名称，不是函数表。真正接收者由上述线程和调用重定位确定；探索文件中对 `.text+0x10E8` 的反汇编不作为处理函数证据。[纠正记录](analysis-corrections.json)。

## 设置模式与要求重启是分开的

当前 `libObj+0xEDC44` 的0x0604组分派，用22项有界16位相对表选择命令。命令1进入模式设置，命令5通过 `0xEDFEC→0xED4A8` 调用 `stm_system`，请求执行 `/usr/bin/us_reboot.sh`。

但本轮核对的7.02 p15、p3 initrd、p7 rootfs和Ubody文件清单中没有该脚本；历史2.04／2.05 p1中有。这个结果只覆盖已检查的公开包文件系统，不能断言实机运行时、其他存储或临时部署中绝对没有它。**不能仅凭当前库里的路径字符串，就把命令5列成当前主系统已验证可用的重启接口。** [分派与包装](pins/SEN604-dispatch.txt)、[命令5](pins/SEN604-command5.txt)、[脚本可用性核对](reboot-script-availability.json)。

当前 `libupdatercorecommon.so` 的 `CurrentFirmware::SwitchModeToUpdater` 主函数可见挂载、创建模式标志及卸载操作。本轮没有把函数名中的“Switch”解释为已完成硬件重启，也没有证明固件更新调用者必然调用上述hot/cold包装器。[原函数](pins/Core-switch-updater.txt)。

## 历史p1重启工具通过机内控制器工作

历史2.04／2.05 `us_reboot.sh` 全字节相同，共230字节；顺序调用 `ud_pd_firmup.elf b` 和 `ud_reboot.elf`，两步都写有错误分支。PD工具自带用法将b列为reset，本轮不从用法字符串推定完整驱动副作用。没有执行脚本或两个工具。[两版脚本来源](historical-reboot-scripts.json)。

2.05 `ud_reboot.elf` 为14432字节，SHA256 `314725816b8a251500eb38b001ab8bd8449f6560753db4090658086331586d7a`。从ELF入口的原LDR字面量和 `__libc_start_main` 调用绑定主函数 `0x400D30`；它按 `get_power_IC_type()` 结果分派。type7的源分支从 `0x401030` 开始，读取Backup里的通道/引脚参数，打开机内SIO和GPIO，清零128字节缓冲并把前两byte设为 **`[0x11,3]`**；后续原代码有校验、128字节SIO写入及GPIO操作。

这与199／200轮的Darwin更新请求 `[0x11,4]` 分开。**这是历史恢复环境中发出重启请求的程序证据，不是当前机身电源IC身份、实际MCU收帧、复位完成或恢复分区装载的证据。** 它依赖已运行的AP Linux、动态库、Backup配置和机内驱动，不能单独引导已无法运行的AP。[历史工具清单](historical-reboot-helpers.json)、[原构帧](pins/old-reboot-frame11-3.txt)、[SIO写入](pins/old-reboot-SIO-write.txt)。

Sony公开的[FX3 Ver7.00 GPL页面](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)对应参考内核源码。其 `pm_core.c` 登记平台reset钩子并使用GPIO复位请求；本轮未把它与7.02实际二进制/运行配置绑定，也未把GPIO代码转成操作步骤或Fastboot入口。当前内核的WFI过滤只是定位尝试，不能证明复位实现不存在。[参考源码定位](vendor-source-restart-locators.json)。

## 社区方案的适用范围没有扩大

重新阅读的[A7 IV SD恢复说明](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/main/methods/00-sd-recovery/README.md)仍要求相机已能进入Fastboot、匹配的更新环境，以及独立机内验收。它的设置写入和普通重启不能替FX3提供前置入口。A7 IV启动区文档也只对应其v2.00原件，不能把相同加载地址当成FX3启动区身份。GitHub API本次出现TLS／超时错误，没有取得新HEAD/树；失败结果没有被当作仓库未更新或文件不存在的证据。[联网复核范围](web-source-review.json)、[API结果](upstream-current-state.json)。

下一项转向**公开包里是否还有可还原的AP早期装载原件**：先按WBI格式核对物理内存范围，判断它是否保存相关启动代码，再决定需要哪份原机来源。当前普通Linux重启和历史p1重启链已分别定位，不再把它们当成尚未找到的通用救砖入口重复查。

0.4适配工具、native10与195固定方案均未修改。195仅主机root01的具体回答仍待用户；未重问、未创建或启动固定作业。实际同机备份、独立逆写/冷恢复和目标HEVC主录验收继续保留。
