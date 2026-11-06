# 完整控制器接入SERVICE获取子步骤

271的C写入器／v4解码器已接入完整helper、流编排、RCPT5私有回执和观察器。全量候选编译通过；8组普通用户进程／模拟设备流程及5组针对性集成检查通过。**native入口仍关闭、目标未绑定，没有新的上机包、管理员、USB请求或相机操作。**

正常模拟通信、恢复凭据、五秒空闲退出和错误缓存拒绝继续通过。新增两组真实普通用户helper／IPC分别携带203设备打开、210接口打开的同一独占错误：观察器准确区分，保留HELD、无未返回调用，不继续SERVICE认证／read0／STOP。只有人工fixture有退出gate，不能将其当作真机协作退出。

获取结果在返回后被绑定，后续帧换步骤被拒绝；旧v3读者拒绝新v4；native授权、render、command及bootstrap入口全部保持关闭。共享帧另用schema8／SVC6的离线范围，不能重用已消费许可。

[完整流程](test-receipt.json) · [新增集成检查](acquisition-integration-check.json) · [编译记录](build-receipt.json) · [来源](source-origins.json)。真实Mac进程、内核peer、文件和fsync与人工机身／缓存响应分开记录；不是FX3 SERVICE能力或录像证明。

本轮同时核查本机Apple SDK和[固定libusb源码](https://github.com/libusb/libusb/blob/987c1170d0018ba82557823a98ae443e8335e11b/libusb/os/darwin_usb.c)：设备独占打开、接口独占打开和默认管道请求是不同能力。SDK允许部分未独占打开设备的控制请求，但改变USB设备状态的标准请求仍可能需要独占打开。libusb容忍设备层ExclusiveAccess并不等于接口已取得；我们的原控制回调还要求device_open，单改返回码分支也不够。

因此下一项须将设备打开结果、接口归属和限定控制能力一起建模，避免把接口冲突当成可继续，也不增加抢占、重置、配置切换或任意控制请求。本轮尚未改变原生打开策略。

271及270执行目录原final-manifest存在自引用错误，原件保留；各自`seal-correction.json`与`final-manifest-corrected.json`已复核。仅清单自身不一致，其他成员及已批准270的13成员包均未改变。此错误不改写原清理结果。

相机继续保持USB断开。270主机收尾已完成，269历史HELD／UNKNOWN及全部G01至G16保持；完整备份、独立恢复、主录HEVC、音画长录和首刷仍未通过。
