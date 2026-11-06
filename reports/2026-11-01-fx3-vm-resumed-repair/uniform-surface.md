# 原生清屏请求的软件执行与独立读回

原厂菜单仍不可用。AP60已实际执行原应用发出的640×480纯色清屏请求，向原DMM目标写入614,400字节，并调用原厂 `SendDrawComp` 发送4字节零状态。QMP独立读回一致，但这是黑色清屏面，尚无文字、图形或可操作菜单，不能当成原UI交付。

## 最新解析：监看 LUT 与释放限制已越过

AP66–69继续推进原启动链，仍无菜单文字或图形。监看LUT的mode0设置和空闲状态下的释放限制开关已由原应用消费回复，下一处为音量设置及系统提示音缓冲区地址查询。

|运行|窗口|实际结果|
|---|---:|---|
|AP66 / ap66lut-ed5764ad|80秒|软件保存监看LUT mode0/0和pending f029计数；原1161状态0回复消费、释放0；随后发出403d|
|AP67 / ap67release-838492df|80秒|只读捕获403d完整16字节请求及调用栈，未改变其处理|
|AP68 / ap68idle-e5d17096|85秒|空闲软件后端完成7次释放限制掩码开/关；原回复全部消费、释放0；随后出现032e/033d|
|AP69 / ap69audio-1cbbef9f|80秒|上述两项再次通过；只读定位032e/033d调用者，没有给未实现的音频请求添加回复|

[监看LUT原协议](../../work/fx3-vm-20261101/menu-repair-01/runtime/monitor-lut-original-proof.json)绑定了AP0161、CP桥接19c95c/19ea38、旧VDF011d/111d和AP1161。旧VDF投递f029配置后即返回，不等待显示帧。当前软件模型仅接受观测到的mode0，保存双输出模式0/0、更新次数及待处理配置数，返回原12字节1161/8001/status0；不处理其他模式，也不声称物理LUT已编程或活动色彩转换完成。原CP的其他显示状态还可能覆盖模式，本模型限定在明确的非活动软件显示条件下。

[释放限制原协议](../../work/fx3-vm-20261101/menu-repair-01/runtime/release-inhibit-original-proof.json)使用本机FX3地址重新核对，未照搬上游其他机型偏移：98c8ea处理type5/403d，先更新reason掩码；reason8000且活动释放标志为1时保留token并延后回复，否则98f66a构造type1/403d/token/status f000的12字节回复。当前软件模型仅支持无活动拍摄释放、source80020002、mask8000的开/关。active分支明确拒绝，未实现拍摄或排队完成。与前面的VDF请求不同，403d原请求仍归AP调用方释放，服务只管理自己分配的回复。

[集成ASan/UBSan检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/release-inhibit-transport-host-check.json)通过：LUT非法模式/保留字拒绝、分配和发送失败回滚、原回复格式与租约释放；释放限制开/关、token回显、调用方请求所有权、活动释放不应答、非法标志拒绝；以及8线程24000次临界区检查。[四次运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/monitor-release-run-summary.json)中host退出0、回收、输入未变、观察器无错误、异常标记为空；这不代表guest正常关机或UI验收。

当前两条新请求已由[原始调用栈和AP代码](../../work/fx3-vm-20261101/menu-repair-01/runtime/adf-boot-waits-proof.json)定位：032e是 `sequence_boot::adf_set_volume_i()`，观测到音量值8；033d是 `adf_sys_get_system_sound_address`，AP期待24字节回复，status在+8、64位物理地址在+16。系统提示音源文件到CP缓冲区的布局、容量和所有权尚未绑定，未用零地址或任意地址代替。此前VDF0118面板输出请求也仍待查。

## 此前解析：CEC 与时间码设置已越过

此前将 `909c015b` 关联到 CameraProfile 是错误的：SID低16位不是IMDB模块编号。原CP RTTI `CEC::OSALUIPC<2426143067>` 的完整常量就是 `909c015b`，原AP调用者日志为 `sequence_hdmi_ctrl / Send CEC SET_POWER`。[原代码和调用栈证据](../../work/fx3-vm-20261101/menu-repair-01/runtime/cec-power-original-proof.json)已取代旧分类。

消息flags=1也不代表此调用无需回复。AP `2de72f4` 明确调用 `osal_rcv_msg_tmo(...,-1)`，随后复制、释放回复；CEC请求的预期是16字节 `0000/8101/0010/0001`，status32和power8回显。本文解析过程中一度由flags推断非阻塞，继续追到该等待后已纠正，没有据此修改调用方或省略等待。

|运行|窗口|实际结果|
|---|---:|---|
|AP62 / ap62stack-66a538bb|75秒|只读捕获CEC、VDF0118的9层frame链，原传输及失败保留|
|AP63 / ap63cec-77413a1b|80秒|软件CEC保存power=1，原8101回复被消费、释放0；原应用随后发送HDMI0109|
|AP64 / ap64tc-e0ed5826|80秒|软件HDMI保存TC输出关闭状态，原8109回复被消费、释放0；随后发出VDF0161|
|AP65 / ap65vdf161-e83cf01f|80秒|CEC和TC再次消费/释放0；0161调用栈定位到Gamma Display Assist的监看LUT设置|

CEC软件后端仅保留电源请求，HPD维持0，不产生CEC线路消息；原CP成功路径本来还依赖驱动，当前没有声称运行该CP路径。HDMI0109在原CP的名称为 `ApiHandler::handle_set_tc_output`；默认非活动输出分支经selector A写profile+7c，返回12字节 `2500/8109` 状态。软件后端只支持本次观测到的TC关闭值0，启用TC仍拒绝，不产生HDMI帧。[TC原代码审计](../../work/fx3-vm-20261101/menu-repair-01/runtime/fx3-hdmi-tc-proof.json)保留默认与活动状态的差异。

[集成ASan/UBSan检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/hdmi-tc-transport-host-check.json)覆盖CEC开/关、回显、非法值、分配失败、发送失败回滚、原请求所有权与回复释放，及TC关闭/拒绝启用；8线程24000次临界区检查通过。[四次原生运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/cec-tc-run-summary.json)确认host退出0、回收、输入未变、观察器无错误、异常标记为空；仍非guest正常关机或UI验收。

当时请求 `0d2061010a0001800000` 来自原 `sequence_set_gamma_disp_assist::run()`，日志名为 `vdf_disp_set_monitor_lut`，线上的mode值为0。[调用者证据](../../work/fx3-vm-20261101/menu-repair-01/runtime/vdf161-caller-proof.json)保留；AP66以后对该配置队列的有限软件处理和原回复消费见上节。另一条VDF0118面板输出请求仍待查，不能把CEC和TC的通过等同于菜单即将可用。

## 实现与原代码依据

同机 `libgpe.so` 的 `c60c/b1f4` 确认偏移 `(y*stride+x)*bpp`，format0为2Bpp，format1为4Bpp；`c3fc` 确认format0的RGBA4444量化。`c458/c50c` 为不透明覆盖分支。`a158` 与 `d6b0` 绑定回调结构和原完成消息分配、复制、发送及失败释放。完整指令和原件摘要见[原代码审计](../../work/fx3-vm-20261101/menu-repair-01/runtime/gpe-uniform-original-proof.json)。

参考了维护者固定提交的[纯色填充实现](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/gpe-raster.c)，FX3字段、地址和函数入口以本机同型号原件为准。

软件模型只接受各颜色通道相等、不透明覆盖、无回调、GPE0/core0/source0的填充；目标限定原生DMM type545区段 `43feb5000/140000` 内，从原首面 `43feb5100` 起。写前写后读取当前DMM表校验，执行同步CPU写入后才允许原FIFO中的零参数flush调用原 `SendDrawComp`。任何不支持的操作使后续flush保持失败；BitBlit、混合和回调尚未实现。此模型依赖原FIFO待完成请求的生命周期，没有声称获得独立分配器pin或物理GPE等价。

原五个GOT观察槽保留。AP60新增对三个worker入口的同机16字节前缀校验和跳转，以覆盖直接调用及PLT调用。是否存在懒绑定覆盖是此前提出的假设，没有作为已证实根因；后续AP61虽安装相同入口，仍未捕获绘图请求，启动触发仍不稳定。

## 六次实际运行与保留的失败

|运行|窗口|结果|
|---|---:|---|
|AP56 / ap56surface-1da18185|75秒|探索 `GetDmmMemInfo(403)` 返回2，输出全零。进一步审计发现该接口会构造临时对象，不能当作纯查询或已持有分配句柄；后续候选不再调用它|
|AP57 / ap57uniform-d4dd4e69|90秒|初版过度拒绝通知标志38=1；主机捕获fixture检查失败，该版不具备通过证明，未执行成功绘制|
|AP58 / ap58uniform-0eb11d48|85秒|修正通知标志后主机检查通过；原fill/flush复现，但单次proc读取遗漏目标区段，绘制被拒绝|
|AP59 / ap59uniform-fb7cd65e|75秒|proc改为读至EOF；该窗口没有捕获GPE调用|
|AP60 / ap60entries-5611350a|85秒|同机worker入口绑定；实际614,400字节清屏成功，原完成消息发送成功；QMP独立读回通过|
|AP61 / ap61next-8db30dad|80秒|保留相同绘图模型，增加下一服务的被动观察；未捕获GPE调用，不能声称稳定复现|

AP57主机断言失败后，外层shell未设置遇错退出，后续构建/运行仍继续。这是本次执行顺序错误；该失败及guest原日志均保留，不计为主机通过。修正后的v2检查单独通过后才用于后续候选。

六次均host退出0、进程回收、输入摘要未变、观察器无错误、异常标记为空。该回执不代表guest正常关机。没有物理设备、主机磁盘或网络透传，原固件和历史候选保留。

## 验证与当前边界

- [ASan/UBSan纯色检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/gpe-uniform-v2-host-check.json)：捕获的640×480布局、614,400字节及前后保护区，白色量化、越界、回调、混合和不支持颜色的拒绝。
- [proc短读检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/gpe-proc-read-host-check.json)：模拟每次4096字节返回，9000字节之后的有效区段被找到，缺失及错误type被拒绝。
- [QMP独立读回](../../work/fx3-vm-20261101/menu-repair-01/runtime/gpe-uniform-native-readback.json)：整个1,310,720字节区段摘要 `439292e4…`；偏移256后的614,400字节全零，摘要 `34c69899…`。没有前态非零证据，不能仅凭全零快照证明字节发生变化；实际CPU写入依据受审代码和运行标记，快照验证最终内容。
- [v12编译与入口绑定](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-gpe-observe-v12-build.json)、[六次不可覆盖运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/uniform-surface-run-summary.json)。旧init中的request_capture和构建回执中的Aggregatev13文字为继承元数据，实际helper版本、源代码和CPIO摘要为准。

后续被动捕获 `909c015b` 的12字节包 `000001010c00010001000000`，发送者为 `appFw+2de7264` 的公共传输入口。最初将它与IMDB模块15b的CameraProfile库关联，后来已由完整CEC SID和原始调用者纠正；[旧证据文件](../../work/fx3-vm-20261101/menu-repair-01/runtime/camera-profile-next-wait-proof.json)标为已被取代，历史运行日志保持原样。

下一步核对ADF033d系统提示音缓冲区布局和源资源加载、ADF032e音量处理，以及VDF0118面板序列，并继续定位后续绘图触发。原菜单、图像资源拷贝、显示发布、按键交互、连续运行和正常退出均未验收。
