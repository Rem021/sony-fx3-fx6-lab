# FX3 Mac管理员身份与回执实测

2026年10月30日。**195号固定方案已按本次授权实际执行：两个root程序分别完成试验与回读，可信本地连接接收两份结果，两原进程已退出，启动链返回0。** 路线第2项的主机前置通过一项；相机没有参与，第2项整体仍未完成。

## 实测通过的范围

| 核对内容 | 实际结果 |
|---|---|
| 固定程序与方案 | 批准包及30成员摘要一致，未重新编译或换程序 |
| 管理员程序身份 | 两个实际helper的UID均为0，PID及出生时间由主机内核观察并绑定 |
| 登录归属 | 两份结果均记录audit UID501，图形/TTY标志通过，非远程登录属性 |
| 程序自读与连接 | 普通用户不能直接读root0500程序；原监督器通过核验过的连接接受程序自读摘要HELLO并确认后继续 |
| 本机工作与归档 | trial处理64字节本机内存，在受保护目录保存256字节HOST_ONLY回执 |
| 独立回读 | 第二个root进程以不同nonce回读原回执，384字节回读记录中的原件SHA与第一份逐字相同 |
| 结束 | 两数据页completed=1、result=0；两原进程已消失，shell启动链返回0；无自动重试 |

实际trial PID49237、readback PID49276。首次观察及结束后再次检查均保留了出生时间边界，未将数字PID复用当作原进程仍在。原监督器返回HOST_TRIAL_AND_READBACK_COMPLETE后正常退出；之后只做已有回执的完整性解析与主机进程元数据复核，没有第三次helper调用。[实测核验](actual-verification.json)

## 可复核的结果

- [本次用户授权](authorization-receipt.json)：固定HOST_ONLY方案fx3-host-root-20261029-01，最多两次helper，批准包SHA为00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0。
- [原监督器完成记录](host-evidence/host-live-summary.json)与[启动链返回](host-evidence/relay-marker.json)。启动链返回0本身不是可信回执，结论同时依赖原监督器当时的连接及内核身份核验。
- [试验结果](host-evidence/trial-live-record.json)与[回读结果](host-evidence/readback-live-record.json)。trial原件SHA为39dc3302fdc2b0f21ecbb6f0041bd8e0d843a33c527f5737967dc2f75390b439，回读中内嵌原件对应同一摘要。
- 固定程序原件及代码仍在[195号方案](../stage195-root-host-validation-plan/README.md)。它是执行前的封存说明，未覆盖其中历史的“未执行”状态；当前实际结果以本目录为准。

原始作业留在/private/tmp/fx3-host-root-20261029-01，root私有程序与单次记录留在/private/var/root/fx3-host-validation/fx3-host-root-20261029-01。没有删除或重新使用单次记录。已消费本次授权，不能再用它启动新试验。

项目内归档是便于复核的用户可读副本，不等于root保护边界，也不能在重启后仅凭其中transport_authenticated字段重建原本的存活连接证明。此处证明的是当时已完成的限定主机试验，不是任意root程序、断电持久性或APFS故障恢复。

## 对下一步的影响

此前“root与用户501之间的实际身份、自读摘要及受保护回执”缺口已有本次实测依据。下一步先离线整合这一主机链路与现有原生MSC拥有者代码；必须保留原生入口关闭，核对端点角色、请求作用域、在途调用和驱动归还，不能只将release标志改成1。

本次不释放USB、Sony认证、相机模块、文件读取或刷写范围。244文件回传和245不切状态通信候选仍不放行；相机暂不需要连接。完整同机备份、独立恢复和H.265实际成片等原16项仍未完成，首刷前第2至6项共5个里程碑未通过。[路线表](../../../outputs/fx3-recovery-adapter/ROADMAP.md)

本次无IOKit/USB/Sony/驱动/固件操作，无新的隐私权限变化，也没有重建自动目标或重复运行旧模型测试。
