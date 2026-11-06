# FX3 跨实例排他与私有报告文件I/O

2026-10-29。本轮完成 **38项真实进程整合＋18项日志测试＝56项本地检查**。新增同一控制器体系的跨进程排他记录，并让管理员入口脱离用户文件的mmap backing。测试均使用自建假设备／普通文件，未启动原生设备候选、管理员验证或相机通信。

新候选标识 `fx3-702-global-owner-channel-20261029-08`，仍固定 `FX3_NATIVE_RELEASED=0`，原生路径另限制为observe/status/end。08未批准，旧05等一次授权未复用，07也未批准。owner ABI4、entry schema3保持不变。

## 跨实例排他

[global_guard.c](global_guard.c)在任何owner设备动作前取得同一受保护文件的非阻塞独占锁。Native预定位置是root私有目录；测试在项目内自己的普通文件上运行，不访问该root路径。

锁之外再使用256字节定长、SHA256前后链接的追加记录，最多2048条：

```text
OWNED → CLEAN    本次owner已完成已知清理，或私有返回值证明没有owner调用
OWNED → UNKNOWN 清理结果不明
OWNED           调用未返回、进程被中断或持有现场
```

只有末条为CLEAN才允许下一次开始。PID消失、内核锁被动释放不清除OWNED／UNKNOWN；没有自动清理、抹除或“旧进程死了就重试”的分支。新实例在锁忙或旧记录不明时，owner设备调用计数为0。记录损坏、断链、部分写入、错误类型／权限／链接数和容量不足均拒绝。

这是[合作进程之间的advisory lock](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/flock.2.html)，不能阻止不使用本协议的Sony或第三方工具。SHA链用于发现损坏及顺序错误，不是对控制本机管理员的数字签名。保护root目录和跨UID实证仍未做。

## 用户报告文件异常

[frame_io.c](frame_io.c)把4096字节输入复制到私有内存；[管理员入口](owner_entry_main.c)不再mmap用户文件。以后只以固定偏移读取ACK／停止意图，发布进度与结果。目标、预算、实际结果及句柄保留判断仍在私有内存。

发现文件被截断、链接数／身份改变或I/O失败时，保持失败标记并提出停止请求。它不会杀掉等待中的原生调用、解除owner或自动归还驱动。即使报告无法发布，原生调用和句柄寿命仍由私有状态控制。测试中的特殊gate只释放假调用，没有对应生产入口。

仍不能把共享报告或其completed标志单独作为可信完成回执；经核对的socket应承载最终私有结果，启动／监督器迁移也尚待完成。

## 构建与验证

- [最终整合构建](build-receipt-v2.json)：原生设备候选只编译／链接；假设备helper启用AddressSanitizer和UndefinedBehaviorSanitizer，无IOKit框架或libusb依赖。
- [38项整合结果](integration-results.json)：包含此前32项在新入口上的重跑，以及竞争实例、保留owner后新grant拒绝、清理UNKNOWN、空闲文件截断／硬链接和原生调用等待期间的文件截断。后者继续保留句柄，下一实例被拒，显式结束假测试时三项清理调用为0。
- [18项日志结果](guard-results.json)：运行当前Mac真实锁、真实并发进程及独立Python SHA256检查；不同grant在CLEAN之后可进入，OWNED／UNKNOWN、死PID、损坏记录、非普通文件、软硬链接和满额均被拒。
- [交叉核对回执](verification-receipt.json)：56项本轮检查通过；底层wire／session与191字节相同，复用其既有55项证据，没有计为本轮重跑。测试进程均已结束。

首轮32项中，零数据连接在新增日志同步窗口内提前关闭，安全地在owner前被拒；旧测试只接受“owner后中止”，已扩展为两种安全结果。增加不同grant测试时的helper文件名断言也已修正，失败发生在执行前。原脚本、首轮构建和执行记录均保留。

## 保留的实机缺口

[实施限制](implementation-review.json)仍列出固定Terminal/bootstrap、用户侧监督和认证最终回执的迁移。跨root／UID501、root私有日志、真实IOKit、MSC后续模式／身份、Sony鉴权退出与读取准入未验证。本轮不存在实机备份、写回、冷启动或救砖验收。

下一项完成可信完成回执和启动监督，然后才能形成有固定代码／SHA和具体范围的新增预检方案。原始16项目标要求、当前p1同机备份、受限ET_DYN、WBI／干净启动和独立恢复要求全部保留。[持续目标active](native-goal-observed.json)，goal_complete与persistent_write_release均false。
