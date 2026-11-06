# FX3 03号：实际接管尝试、接口失败与后置恢复观察

2026-10-28。**root身份和父ACK已通过，接管流程实际执行；接口申请失败，没有取得接口句柄。** 用户明确批准166轮一次；固定包和168项检查点材料重验，缓存唯一目标仍MSC，所有卷已推出。

## 真实结果

原生helper的PID/UID0/微秒出生/固定root路径由内核实际核对，父ACK=true；capture和reopen返回0，接口申请阶段返回0xe00002be（SDK命名kIOReturnNoResources）。接口未打开，profile仍零，没有进入Sony认证、控制或bulk传输。该总阶段包含多个IOKit子调用，03未记录具体失败子调用，不能认定是相机拒绝、配置错误或某一插件调用失败。

随后接口清理、设备归还、关闭均返回0，原生和父/中继进程终止经实际Popen/内核元数据核对，无在途调用。原生状态1表示工作中止后观察到基础存储驱动计数返回；它不是接口成功或完整恢复。原始独立缓存检查缺IOBlockStorageDriver和IOSCSIPeripheralDeviceType00，因此正式原回执为UNKNOWN_INDEPENDENT_DRIVER_ASSOCIATION，保留原样。

随后一次仅缓存观察中，同机HMAC、MSC和全部原驱动类别已重新出现（13:17:10 UTC采样）；它证明该时刻缓存关联已恢复，不能推断实际恢复完成用了多久。用户另外确认“正常显示 USB／MSC，无报错”。只读缓存、屏幕观察和实际I/O/相机健康分别验收，未读卡/录制来验证功能。

03编号已消耗，不重启、强杀、reset或自动重试。01和02记录保留。没有Sony认证/服务、卡内或机身文件访问、模块上传、WBI/设置/固件写入。

## 错误定位边界与离线下一步

[具体结果](actual-trial-result.json) · [原监督回执](runtime-supervisor-result.json) · [稍后完整缓存比较](settled-cache-comparison-01.json) · [用户屏幕观察](user-camera-display-observation.json) · [错误范围复核](claim-failure-scope-review.json)。

已有[libusb1.0.30官方源码](https://github.com/libusb/libusb/blob/v1.0.30/libusb/os/darwin_usb.c)的5段固定摘录重新按原审计格式验证，未执行或安装；新联网调用失败后复用本地已保存版本。其完整claim含配置切换等额外行为，不能直接整体套入本次受限方案。Mac当前缓存的正常interface0插件映射存在、接口08/06/50及两端点匹配，但这是归还后的状态，不是失败时现场。

本机SDK说明GetInterfaceNumber/GetAlternateSetting/GetNumEndpoints无需先打开接口，不能仅凭libusb调用顺序不同就盲目改顺序。下一候选仅增加固定子调用名称/原始返回码日志，不增加设备调用、配置切换、重试或新的Sony载荷。

一次参考摘录哈希因末尾换行处理与旧审计不同而失败，按原格式复核后5段一致；一次SDK头UTF8读取失败，改为ASCII兼容解码后核对注释。失败材料保留，运行包没有修改或重新执行。

目标MAIN 1080/29.97 HEVC、完整健康备份/恢复回读、独立救援、音画同步、长录和冷启动均仍未实现；本轮不构成可刷包或救砖保证。
