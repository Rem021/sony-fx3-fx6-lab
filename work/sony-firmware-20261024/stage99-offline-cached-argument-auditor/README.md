# FX3：现存缓存参数的离线审计工具

**已补齐只处理现存JSON的参数审计工具，18项合成边界测试通过。Mac现有资料仍不足以判定Windows零匹配的原因，结论保持UNKNOWN。** 没有重新查询设备、访问Windows/UU或打开相机接口。

Mac已有17:15 UTC CIM的脱敏摘要和更早的PnPUtil公开命令文字；当前根选择、最后一层实际argv及原始stdout/stderr仍未取回。JSON显示双反斜杠、WQL转义或一条手写命令，均不能直接证明实际参数有误。旧Present快照不能证明现在连接。

## 工具做什么

`audit_saved_arguments.py`只读取明确指定项目根目录内的三个普通JSON文件：CIM源、根选择源、实际调用回执；ID字段用显式JSON Pointer选择。它不会自动查找设备或遍历其他目录，不启动PnPUtil、PowerShell、CIM或任何子进程，也不访问网络。

输出仅含ID摘要、字符/UTF8长度、反斜杠数量/连续段、空白/字面引号情况及非唯一VID/PID；不输出原始ID、序列或命令行。原始输入不改，输出必须新建且不得覆盖。普通文件、项目路径、链接/reparse和大小检查已覆盖相应合成用例；不是通用安全沙箱或实际设备验收。

- JSON按标准UTF编码只解码一次，不二次“去转义”，不删除引号、空白或反斜杠。
- ASCII范围使用与本任务Windows ToUpperInvariant合同等价的大写UTF8 SHA256；非ASCII明确UNKNOWN，不用Python大小写行为冒充完整.NET兼容。
- 只比较已提供的原生argv记录；显示命令、WQL文字、shell包装、硬件ID过滤、参数歧义或额外未审查选项不能得到实例绑定MATCH。
- 即使三个字符串一致，也只标记`MATCH_WITHIN_PROVIDED_RECORDS`：它不证明回执真实性、进程确实收到这些argv、当前连接、相机型号/固件、同机备份或协议可用。

[微软原文](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/pnputil-command-syntax)区分两种格式：`/enum-devices`的`/instanceid`指定实例ID，`/deviceid`指定硬件/兼容ID；`/enum-devicetree`的根ID是位置参数，且该命令从Windows11 23H2起提供。用户只确认Windows11，具体版本尚未验证。本轮只核对保存的计划格式，没有运行这些命令。

## 输入合同与使用范围

这是供原Windows会话恢复后审查**已有文件**的可选工具；本轮不传输、不执行、不请求重新盘点。应保留原始文件，直接用JSON Pointer选原字段；不要手工重建“正确argv”来替代丢失证据。三个输入若不在同一已核验普通项目根内，应先停止并核对允许范围，不能把相机、磁盘/卷接口或重定向路径作为输入。

CIM与根JSON默认字段为`/instance_id`，也可指定已存在字段的位置。回执选择到的对象须包含`capture_kind`、`program`、`argv`；`argv`仅为参数数组，不含程序名。仅当来源确实记录了原生参数时，才可标注`capture_kind=native_argv`。这个标签是输入声明，工具不会把它当作独立进程观测证明。

入口参数：`--project-root`、`--cim`、`--selected-root`、`--receipt`、`--output`；可选`--cim-pointer`、`--root-pointer`、`--receipt-pointer`。仅运行Python脚本解析文件，输出为新JSON。文件或字段不满足合同会返回输入错误，不创建虚构缺失证据。stdout/stderr原字节、编码、退出原因及Shell最终解析仍须另按原离线任务审查；本工具未完成这些部分。

## 本轮已做的验证

18项合成测试覆盖：大小写/哈希合同、JSON单次解码、真实多余反斜杠、引号/空白、不一致源、非ASCII、显示文字/WQL不能冒充argv、shell程序、硬件ID与实例ID混淆、设备树根参数、重复/缺失参数、额外命令/选项、隐私输出、JSON Pointer、UTF16文件、源文件不变/输出不覆盖、链接和越界路径，以及无设备/进程/网络执行依赖。

这在Mac现有Python环境验证；没有Windows运行验收。测试中含有`pnputil.exe`等**数据字符串**，没有执行对应程序。临时合成文件只在本阶段创建并清理，历史材料保持。当前公开回执交给审计逻辑得到UNKNOWN，未伪造私有ID或argv来取得MATCH。

## 计时资料与下一步

本轮精确/限定域检索未获得适用于VCD `be0000ac`的原始寄存器规范，不采用其他设备搜索结果推断频率。原VCD前2MiB中找到307个“LUI be00后短窗口内LW ac”的候选指令对；这是未做完整寄存器存活分析的启发式清单，不是307处已证明MMIO访问，也不证明频率、位宽行为或跨CPU地址兼容。未注入计时值继续模式。

Windows恢复并有相应保存记录后，可先做此离线字符串审计，不必为它重问设备。现阶段继续Mac离线，真实实例参数错误、父子关系与物理连接原因均不下结论。全部16项要求和相机授权不变，实际1080p HEVC主录、音画/长录/冷启动及同机备份、受限恢复与独立救砖仍未验收。

- [工具](audit_saved_arguments.py) · [边界测试](test_saved_arguments.py) · [测试结果](synthetic-test-results.json)
- [Mac现存证据审计](available-records-review.json) · [计时研究范围](timer-research-scope.json)
- [复核](completed-evidence-review.json) · [封存](final-receipt.json) · [完整目标](goal-status-after.json)
