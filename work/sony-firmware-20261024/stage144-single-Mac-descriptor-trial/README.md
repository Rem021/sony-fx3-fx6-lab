# FX3：一次获准的 Mac USB 描述符实测

2026-10-27。**已按用户“允许，仅一次 USB 描述符读取”的明确授权完成一次实机元数据读取，进程正常结束。临时放行随后关闭，单次凭据保留，未重试。** 本轮不是认证、刷写、备份或救砖测试。

执行前核验目标卷 UUID、阶段142全部451个已封存成员及工具 SHA，使用已审核的 [单次方案](../stage142-Mac-USB-transport-candidate/first-descriptor-trial-plan.json)。授权只覆盖缓存选中的 `054C:0DA1` 及固定位置；普通主动查询、驱动变更、认证、切模式、相机文件和刷写权限均保持关闭。

## 实际读取结果

| 项目 | 返回值 |
|---|---|
| VID / PID | `054C / 0DA1` |
| USB bcdUSB | `0x0210` |
| 当前配置 / 配置总长 | `1 / 32` 字节 |
| 接口 / alternate | `0 / 0` |
| class / subclass / protocol | `08 / 06 / 50`，MSC SCSI Bulk-Only |
| 第一描述符端点 | `0x81`，Bulk IN，最大包长512字节 |
| 第二描述符端点 | `0x02`，Bulk OUT，最大包长512字节 |

完整记录见 [descriptor-probe-result.json](descriptor-probe-result.json)，执行及授权消耗见 [execution-and-consumption.json](execution-and-consumption.json)。工具在选定目标上初始化了私有 USB 库，执行标准设备描述符读取和配置/接口元数据 API。主机进程终止于退出码0。没有调用设备打开/抢占、接口 claim、驱动 detach/attach、Sony认证、模式切换、读卡、设置或固件操作。

一次调用与一次显式设备描述符请求额度已区分：没有总线抓包，不保证操作系统内部全部元数据 API 只产生一个 USB 包。返回的端点是本次 MSC 描述符事实，不能据此证明其认证角色或未来服务 PID 的端点。

## 读取后的缓存检查

[复核缓存](post-trial-cache-reviewed.json)仍显示固定位置一台 `IOUSBHostDevice`，接口为 `08/06/50`，其后可见 MassStorage/SCSI/BlockStorage 驱动链。此检查只查询已授权的 IORegistry 缓存，不加载 USB 库；它证明缓存链仍在，不能证明相机物理健康、录制/回放或同机身份。

首次后置采集器把继承同一 VID/PID/位置的嵌套驱动节点也计入，得到3条节点记录，不能称为3台设备。已限定实际 `IOUSBHostDevice` 类并复核，得到1台；原记录与源代码保留在 [attempt-nested-cache-nodes](attempt-nested-cache-nodes)。修改时一项本地夹具因浅拷贝形成递归，在查询缓存前失败；该源版本和错误分类也已保留，修正后四项清洗夹具通过。没有因此重跑主动描述符读取。

## 下一步实际缺口

初始 MSC 和服务 PID 的认证摘要分支需要先闭合。[固定 PMCA 源](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py)对两种 PID 使用不同摘要输入。阶段141原函数测试证明服务校验算法与材料相符，但其六轮仿真把相同服务校验器用于两种模式；其中标为MSC的三轮不能证明真实初始MSC认证。此处明确收紧该证据的适用范围，保留原始记录，不把“六轮通过”充双模式认证可用。

此前阶段143刚开始的离线核对目录仍保留，未认证或加载任何相机模块。后续应先验证初始 MSC 的原路径与正确摘要分派，继续完善传输超时/取消与显式驱动接管归还，再提出新的具体测试方案。此次一次描述符授权不覆盖这些操作。

同机完整健康备份与恢复、独立救援、1080p29.97 HEVC MAIN实录、音画同步、长录/热、冷启动等16项要求全部保持；目标未完成，持久刷写未放行。
