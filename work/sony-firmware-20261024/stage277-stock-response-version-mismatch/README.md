# 原厂响应头版本不一致：定位、修正与完整离线整合

276仅主机收尾已实际完成：两个旧实例退出，journal字节未变，原通信03的HELD/UNKNOWN及81帧保留。随后本轮全部离线；没有新增管理员、USB或相机命令。

## 找到的具体不一致

固定官方样本`libsencore.so` SHA256 `a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410`中，`SendResponse`的`0xb4d0`加载常数3，`0xb4e0`写到包头偏移8，即version字段；两个发送分支都把该包头缓冲区传给Serialize。完整原函数、序列化器和SenserIfSend的原字节/反汇编见[原厂生产者证据](original-response-producer.json)，原Sony指令均未执行。

| 字段 | 已用Mac接收器 | 原厂生产者/修正候选 |
|---|---|---|
| 请求version | 0 | 保持0 |
| 响应version（偏移8） | 只接受0 | 只接受3 |
| 数据体大小 | 88B | 保持88B上限与固定长度 |
| 命令/参数 | ProductInfo001F/参数0 | 保持不变，不含0x80重置 |

[PMCA固定维护者源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L847)的包头字段布局与偏移对应；它检查响应序号，并由ProductInfo调用者检查响应码，没有要求响应version等于请求version。这里没有因此放宽其他字段或扩大读取。

275真机已经走到固定read0写入和12B头读取返回后停止，但未保存原始响应头或语义失败码。因此已确认的是原厂样本生产者与旧接收器存在不一致；尚不能确认用户机身返回的12B正是该版本差异，亦不能把样本当作同机健康备份。

## 已完成的修正与验证

C接收器和纯CPU Python codec的响应version改为3，请求、长度上限、身份、许可、认证和STOP策略保持。人工设备回复同步改成原厂version3，避免人工回复继续迎合错误的version0假设。完整源码相对273仅stream.c、flow_fixture.c及测试目录绑定entry_target.h有差异，见[最终核查](final-review.json)。

[组件反事实检查](component-check.json)使用同一个人工version3响应：旧C接收器拒绝，新接收器接受并在人工后端完成分段88B及一次STOP；另核对旧version0、错误长度/pFunc/序号/标记/响应码及短头仍拒绝。11例均为自写普通用户后端，原厂函数没有被执行，人工HMAC不是实机数据。

完整普通用户helper/私有IPC整合的[8组流程](test-receipt.json)、[5组获取检查](acquisition-integration-check.json)及[4组共享边界](shared-access-check.json)通过；真实进程和内核peer检查不代表真实USB。生产程序仅编译，native入口保持关闭；没有固定新节点、生成新许可或上机包，不能直接运行。

整合初次因沿用273的fixture目录而在seed启动前被拒绝，两个空失败目录和当时构建已归档；仅修正fixture目录后重建复核，见[更正记录](fixture-path-correction.json)。许可证来源预检错误也已保留，并从274批准包核对原MIT许可证；没有重复或追加实机操作。

## 下一步与边界

先补不含原始HASP/认证载荷的响应头失败定位，再以275实际来源、276收尾结果及新的同机MSC缓存固定后续单次方案。当前全部旧单次授权已消耗，原root journal仍保留UNKNOWN；本目录的历史恢复policy与target0不能作为新的实际准入。原错误退出保留策略未改，不能把修正版本字段当作已经验证正常STOP或救砖。

相机可以继续断开。需要固定节点时只做此前授权的Mac缓存查询；新管理员/Sony操作另以具体包批准。完整健康备份、独立恢复/写回、目标MAIN1080p HEVC、持久化准入及首刷仍未通过，G01至G16保持。
