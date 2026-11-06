# FX3原厂SERVICE串号与三种速度配置

2026年11月1日UTC。**发现了258候选在上机后可能停住的具体不兼容条件，因此258不能因接机后就直接放行。** 原厂7.02库的SERVICE路径默认不发布USB串号，当前候选却要求MSC与SERVICE都提供同一非空串号。串号不满足时，候选会在MSC切换后返回SHAPE并保留原实例，没有机会走SERVICE结束请求。此轮没有实际认证、USB接口访问、root或Terminal操作。

## 来自原厂库的证据

[静态审查](original-service-descriptors-and-identity.json)核对原`libInfraUsbCmn.so`完整摘要、相关函数、27条指定原指令及指针重定位：

- `make_gadget_desc_table`将`sen_speed_desc_hs/lsfs/ss`复制到`func_tbl+0x260`；`ptbl_did[13]`指向此表。SEN原VID/PID是054C:0336。
- DID13条目`+0x29`为0，默认`sen_serial_number_str`也为0。`CUsbSvc::createGadget`在条目标志为0时，把START ioctl参数里的serial指针和长度清空。对应普通storage条目的开关为1。不是只看变量名推测串号关闭。
- SEN与storage默认BOS表的container-ID指针均为0，尚无可直接替代串号的唯一container ID证据。
- 原默认SERVICE有一个接口、alt0、四个bulk端点，顺序81/02/83/04。FS包长64，HS为512，SS为1024且每端点有零字段SS companion。前两套派生配置46B，SS派生配置70B。

字段布局使用Sony GPL7.00头文件作参照，并与7.02原库的偏移/原指令核对。没有执行Sony指令、加载原内核或运行厂商程序。派生wire文件是由静态表转换的数据，不是真机抓到的描述符；当前运行时若有其它覆盖或不同路径，仍须另证。原码开关与默认表不构成实际机身已切换的证明。

## 已修复的配置识别

[C策略](descriptor_policy.c)补齐64/512/1024B三种固定策略；1024B要求每个端点后立即跟随一个6B、零burst/streams/interval字段的SS companion。混合包长、缺失/重复companion和其它格式仍拒绝。保持128B总界限、单配置、单vendor接口和实际IOKit管道核对，不主动改速度、配置或alternate。

[父端解码](flow_receiver.py)独立检查记录中的原始布局和所声称的profile一致。[三个针对性检查](speed-policy-test-receipt.json)通过：原厂表派生的三速解析与负例，以及FS/SS人工回调子进程整合。两条人工链的80帧与子进程日志一致，子进程已退出；这些链仍人工提供身份和USB回复，没有解决真实SERVICE身份。未重放258已完成的普通正常链。

[构建](build-receipt.json)包含关闭状态的native候选与无IOKit的自写测试程序。新候选grant命名独立，native release为0，渲染和factory继续拒绝；无新live包、暂存或管理员请求。258原文件、旧许可及回执不改写。另纠正258固定方案的一处文件模式说明：实际`private-flow.bin`创建模式为0400，原说明写成0600；未发生实际root日志创建。

## 下一项怎样解决

需要单独设计跨模式关联：保留已确认MSC的机身标签，连续观察其固定物理USB端口从原节点变为预期SERVICE节点，再观察退出后的MSC串号是否恢复一致。还要核对父端口对象、唯一新节点、期限和相关设备事件。这样的证据只能称为“受控端口切换关联”，不能冒充SERVICE串号或密码学机身认证；不能直接把MSC标签填入没有串号的SERVICE节点。

或者定位一个能独立读取机身身份的已审查服务接口。当前尚未选定并实现上述替代路径，不开放Sony诊断。接机暂不再是唯一阻断点，这一轮无需为测试专门连接相机。仍保留用户整体继续授权，不需要重复批准同一研究范围。

所有16项目标、MAIN1080p H.265、同机备份与独立恢复要求保持，首刷未放行。这里的SERVICE识别不是BootROM救援，也不能保证刷坏可救。

[完整原函数](original-functions.json) · [源差异](source-changes.diff) · [准入结论](admission-decision.json) · [实施路线](../../../outputs/fx3-recovery-adapter/ROADMAP.md)。公开来源：[Sony FX3 GPL7.00](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)，7.02原件来源沿用已封存的183清单与本轮摘要核对。
