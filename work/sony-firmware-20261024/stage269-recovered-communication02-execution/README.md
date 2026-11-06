# FX3恢复后通信02：实际运行记录

2026-11-01。用户批准268固定包并确认所有相机卷已安全推出后，唯一新helper已执行。**本次停在SERVICE获取阶段，未正常返回；原helper及观察器保留，不重试。未上传程序或写固件。**

批准包SHA256：`6fd06531682f9a34c53626bd9bbc5b7ce7f50c6d35ae4b6a182cefe9747ae8e0`。启动前90成员和411封存文件核对通过；固定MSC节点、物理端口及已卸载状态一致，两个旧PID不存在。原生验证已由用户完成。

可信活连接已核对root helper PID34474、出生时间1793523718.860262、固定路径和HELLO映像摘要。原观察器PID34391、工具会话48683仍保留；保存文件本身不能重新建立活连接来源证明。

- 私有RCPT5显示人工恢复事务stage2：固定旧journal尾部已匹配，恢复记录及本次OWNED已追加。旧历史不改为CLEAN。
- MSC完成7次OUT及7次IN，旧MSC对象释放返回；本次在限定窗口内关联到同物理端口的SERVICE节点4296004479（054C:0336）。
- 共取得46条流帧。SERVICE复合获取操作11已返回，原码`0xe00002c5`，本机SDK定义为`kIOReturnExclusiveAccess`。没有未返回设备调用，wire_pending=0。
- **具体失败子步骤没有序列化到流回执，不能断言必为USBDeviceOpen。** 尚未取得有效配置策略，没有SERVICE START、SERVICE认证、read0或STOP，也没有helper退出／同机MSC归还证据。

[实际派生核对](actual-runtime-review.json) · [单次批准](authorization-receipt.json) · [启动前缓存及暂存](staging-receipt.json)。原始私有帧仍存内置盘本次job及root私有目录；项目记录引用其路径和摘要。

后续缓存看到ChatGPT、Google Chrome及本helper的device userclient同时存在。[缓存记录](cached-service-clients.json)只证明客户端存在，不证明哪一个持有独占访问。未关闭或向这些应用发信号。

通过新安装的Scrapling取得并固定[libusb Darwin源码](https://github.com/libusb/libusb/blob/987c1170d0018ba82557823a98ae443e8335e11b/libusb/os/darwin_usb.c#L1939)：其设备层独占失败与后续可操作能力分开处理。这是下一轮接口适配的参考，尚不能据此放宽本次程序或重试。当前需先等待用户屏幕及访问灯反馈，完成机身恢复收尾；本次授权不包含强杀或重置。

原G01至G16、完整健康备份、独立恢复、MAIN1080p HEVC实录和首刷门槛均保留。本次新增证据只覆盖恢复准入和MSC→SERVICE关联，不能标记完整通信或救砖通过。

## 后续屏幕核对

用户已确认正常拍摄界面；同期独立缓存仍为SERVICE0336，原helper和观察器仍在。已提交有访问灯／处理提示前提的正常OFF观察步骤，尚未收到关机结果；未将拍摄界面当作MSC归还或录像验收。见[user-shooting-screen-service-cache.json](user-shooting-screen-service-cache.json)。

用户随后确认拔线后的电池界面／菜单正常，但澄清检查后又接回USB、尚未选择模式；这解释了随后新Sony节点的时序。已要求再次拔下全部USB数据线并保持断开。270只准备了固定主机收尾包，须新的单次例外批准，尚无信号或新管理员操作。
