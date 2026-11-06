# FX3 原应用更新入口和旧上传路径

2026-10-29。**已把 7.02 原应用的三种更新请求接到原接收回调，在限定离线环境中复现分派；目前仍不能正常刷入 FX5 或 VENICE 色彩替换固件。** 机身文件更新与旧文件解包是不同路径，包装函数的成功返回也不代表更新已获准或已执行。

本轮接续[当前 AP 旧文件链](../ap-input-20261029/README.md)。材料来自官方 7.02 包的原 AP 分区及此前封存的原库；“7.02 原代码”不表示用户机身的实时读回。相机、USB、更新模式、机身文件和另一 agent 的 HEVC／恢复工作均未操作。

## 三种原更新请求

原 `appFw.so` 的 `execute_update` 位于 `0x2eae880`，通过原同步消息包装函数 `0x2eacf18` 向服务 `0x004b0233` 发送 8 字节请求。原 `libupdaterufp.so` 的接收片段位于 `0x3034`。

| 应用输入值 | 内部命令 | 原接收回调的动作 |
|---|---|---|
| 0 | 3 | 请求 `up.sh user`；版本跳过标志为 1 时改为 `up.sh ver` |
| 1 | 9 | 准备 `BODYDATA.DAT` 信息、保存更新介质路径，通常请求 `up.sh ms` |
| 2 | 12 | 准备 `LENSDATA.DAT`，调用镜头文件处理函数；后者请求旧 `crypter.elf`，再处理 `ACCYFIRM.BIN` |

原应用先经另一条消息初始化模块。离线实验明确提供了成功的注册回复，未执行真实注册服务；它没有证明普通 UI 或外部请求满足全部前置条件。[原入口及调用片段](entry-static-results.json)

九组检查在同一 Unicorn 实例中执行原应用包装、原消息复制和原 UFP 回调指令。注册、文件准备、备份、进程启动和后续系统动作均为显式替身，只记录请求，不运行 Sony 程序。三种分派、版本标志、准备失败、备份失败和镜头处理失败结果符合原分支。

其中一组令 `stm_system` 替身返回失败，原机身更新分支仍向应用返回成功。该分支没有把进程返回值作为最终结果，因此日志中的 `GO_UPDATE` 或类型结果 0 不能代替固件准入、进程完成或刷写回执。[九组原指令结果](execute-update-guest-results.json)

原 AP 的 `up.sh ms` 设置下次启动的 mode5 标志。此前取得的 2.04／2.05 更新环境在该模式运行带签名检查的 SD 更新引擎；当前机身重启后的引擎没有实时读回，不能把历史库身份直接当作当前机身事实。[历史 SD 引擎和尾签名证据](../input-20261028/README.md)

## 镜头暂存路径的实际长度限制

原 `udtr_write_firm_from_media` 位于 `0x3bcc`，先调用原 `udtr_cmd_search_chank`（`0x3a00`）查找 FDAT，然后拒绝大于 2,097,152 字节的 FDAT。它是镜头／介质文件处理 helper，不是上述机身 mode5 路径，也不是另一条 MSC 上传回调。

将完整官方 7.02 原包以只读文件接口提供给这两个原函数，原解析器读到 FDAT 长度 **811,876,624 字节**，返回错误 3；未请求载荷读取，更未到达 mount、write 或 crypter。另以两个仅 16 字节的长度前缀检查边界：2 MiB 到达载荷读取边界即停止，2 MiB 加 1 字节被拒绝。边界前缀没有载荷、签名或完整容器，不能称为有效更新包。空输入也返回错误 3。[四组原解析与长度检查](media-length-guest-results.json)

这排除了“把完整当前 BODYDATA 直接塞入镜头暂存 helper”这一直接方案。它不证明小型替代容器可以加载，不证明其他上传路径具有相同大小限制，也不改变前轮发现的旧 AES 格式与现代 CBC 整包格式差异。

## 另一条上传链和动态库入口

原 UFP 另注册服务 `0x004b8290`，接收片段 `0x27c4` 处理上传协议。完成命令 `0x100` 内有 `crypter.elf /tmp_updater/Firm.dat` 进程请求；后续查找 `ACCYFIRM.BIN` 并走跨芯片传输。这里不能仅因后续文件属于附件，就把较早的解包和加载行为认定为仅能影响镜头；也不能仅因存在进程请求，就认定外部输入已经可以到达它。

原 UFP 通过 helper `0x1b40` 与服务 `0x00e18246` 交互。对 AP 的 532 个 ARM64 ELF 搜索该服务 ID 的精确 MOV 常量构造，得到 31 处候选；构造器和原调用关系将它定位到 `libInfraExtCmdSvc.so`。该服务经 `libusbcmd.so` 包装 USB 传输；包装函数创建操作码 `0x7a`，feature ID 来自上层参数，用户态库打开 `/dev/usb/usb_extcmd` 并使用 ioctl。

已保存原外部命令服务、USB 包装库和 `usb_extcmd.ko` 的相关片段。内核模块按 ET_REL 的节偏移和重定位解释，未把节偏移当成实机地址；`extcmd_user_access_ok` 是用户内存范围检查，不能按名字理解为固件认证。真实 USB 模式、驱动注册、协议顺序、前置认证和完整更新准入仍未建立。[服务候选](transport-service-constructor-results.json)、[用户态片段](external-command-static-results.json)、[内核片段](usb-extcmd-static-results.json)

在旧文件加载链内，原 `BaseBodyLoaderModule::checkChassis` 比较镜像内的 `config/chassis` 与 `/root/chassis`；打不开镜像内该配置时，这个 helper 返回真。原 `DllHandler::Open` 在该层直接调用 `dlopen`，失败则抛出错误。两个局部行为均不证明上层输入可达、完整容器通过或底层 loader／内核允许加载修改库。[原加载条件片段](loader-gates-selected-results.json)

另核对 `crypter` 的 FILE_CHUNK 全局位于 ELF 的 BSS，原件没有文件字节值。本轮没有执行其完整启动和参数解析，因此不以推定初值充当真实调用参数。

## 证据与复核

| 原件 | SHA 256 |
|---|---|
| `appFw.so` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| `libupdaterufp.so` | `f2e7d27602e3f7b236fc41dd93fccf53ba24f0793fd454e7fec171ae378beca7` |
| `libInfraExtCmdSvc.so` | `6ed99a632f6646e3313241b8d1aaef5a584444f81cf721c013fc403887774134` |
| `libusbcmd.so` | `17763f7d9bba369fc7ef6f5935ff1b15c5e8da9e180f291d920f284618a2d787` |
| `usb_extcmd.ko` | `9afdcb214058ff1d8be8c6a8b0bb72e861a1b0d92b7504310ac06b4ed56d92d7` |

官方页面仍列 7.02、811,876,768 字节的 BODYDATA.DAT，通过存储卡槽 1 和机身版本菜单更新。这是官方更新流程；这里的离线 helper 实验没有替代它的准入和完成条件。[Sony 原说明](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)

本轮执行 13 组有界原指令检查，另进行静态扫描、反汇编及来源校验。初次错误返回分支因未映射原只读跳转表失败，已补入相同原件的真实页面；失败现场保留。几处静态读取工具对 BSS 或无统一 `.rodata` 节的布局拒绝解析，修正记录见[开发记录](development-notes.json)。这些工具问题没有被计作固件拒绝。[验证记录](validation-results.json)、[本轮封存](final-receipt.json)

## 尚未达到停止条件

完整 FX5 专业菜单与专有依赖尚未取得，VENICE 实时 ISP 和 FX3 正常 MAIN 像素链也未恢复完整。即使旧加载候选路径最终获证，仍需完整目标色彩实现、有效修改包、真实入口准入和启动／恢复证据，才能称为可正常刷入。目前没有这样的包或回执，不能开始刷机。
