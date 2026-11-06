# 第176轮：05号实际接口诊断与归还

2026-10-29。用户换端口并保持MSC、推出相机卷后，缓存预检回到固定02100000且通过。沿用第174轮已有单次批准，执行原第173轮固定程序一次。05已结束、已耗，不重试。

## 已得到的实机证据

实际root helper PID34992的UID0、微秒出生时间及固定root私有路径由独立内核查询核对，父ACK通过。root早期GUI/audit检查通过后才进入共享帧/设备流程。原生共享结果SHA验证一致、native_return=0、接口本次确实打开；接口枚举、插件创建、QueryInterface、接口/alternate/端点元数据、USBInterfaceOpen和两次GetPipeProperties均返回0。

| 接口元数据 | 实测 |
|---|---|
| interface / alternate | 0 / 0 |
| Bulk IN / OUT | 0x81 / 0x02 |
| 端点数 / 最大包长 | 2 / 512B |

接口关闭、设备归还和设备关闭均返回0，无在途原生调用、无清理错误。共享最终快照先见一次NotFound，随后成功；本轮未测量完整归还延迟。实际helper随后经内核查询确认不存在，命令完成记录返回0。

一次独立的后置主机缓存观察，也确认同机匿名标签、MSC以及全部原存储驱动类别恢复。该观察说明缓存关联恢复，不证明实际读写、录像、冷启动、完整健康或救砖。

[实际结果与边界](actual-trial-result.json) · [SHA验证的共享结果观察](native-result-observation.json) · [接口和前后元数据](native-metadata-profile.json) · [独立缓存比较](independent-cache-comparison.json)。共享原文件及隐私键没有复制或输出。

## 正式UNKNOWN保留及汇总脚本缺陷

原控制器输出是 `UNKNOWN_TERMINAL_RECEIPT_MISMATCH`，保留原样。它完成root身份核对和设备过程后，无法读取root在私有用户目录里创建的relay stdout/stderr：两者为UID0、0600，用户501实测open返回EACCES13。stdout文件586B仍留原位置，未提权读取、改变权限或复制。

这是第173轮日志归档设计漏掉的跨用户属主条件。此前夹具均以同一用户运行，未暴露它；本轮不把正式UNKNOWN改写为完整通过。已另外从用户拥有的共享结果验证native状态和SHA，再独立核对驱动缓存，因此可以单独报告接口检查进展。

[原因及既有172对照](receipt-delivery-cause.json)：172的实际root结果由外层普通用户shell重定向sudo stdout，原结果文件UID501/0600，内部记录UID0。后续可离线复用这个输出通道设计；不需要为了修归档再接管一次相机。

## 当前边界

程序只进行了已授权的接管、接口元数据检查和归还；共享结果中的persistent/vendor command计数为0，固定源中没有Sony认证、读卡/相机文件或刷写路径。相机01—04和主机对照01记录均保留，05单次授权已耗。

已请求用户只观察相机是否正常USB/MSC、无报错或黑屏；本次屏幕确认仍待回复，不要求拔线、录制或切模式。目标1080p29.97 HEVC主录、完整同机备份恢复、独立救砖和安全刷写仍未验收，未放行持久写入。
