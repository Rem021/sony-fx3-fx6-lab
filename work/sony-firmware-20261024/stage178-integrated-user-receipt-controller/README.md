# 第178轮：结果归档修复整合与服务读取边界

2026-10-29。**归档修复已接入完整控制器，77项本地检查通过；没有新增root、sudo、Terminal或相机操作。** 05号实际接口/归还证据、屏幕正常确认和原正式UNKNOWN均保留。新编译基准06未授权、未执行；不建议仅为了修复归档重复已完成的05接管。

## 已整合的修复

外层用户shell只重定向sudo stdout，由用户501以0600创建结果文件；原生helper自身stderr在exec处合并到该继承通道。sudo验证输入与stderr留在Terminal。源码不授予隐私权限、不修改旧root日志属主或权限。

控制器使用新的单文件描述符读取器：拒绝符号链接、错误UID/权限/链接数、空文件、超过16KiB、读取期间身份/大小变化、非JSON或非对象结果。文件错误会额外记录具体类别、errno及有限元数据；实际原生结果、句柄状态和驱动观察仍独立核对。无法读取或不一致继续保留UNKNOWN，不将缺失日志推成成功。

[固定编译基准](candidate-plan.json) · [运行包](release-bundle.json) · [本地源码及验证](local-source-and-runtime-review.json)。

- 编号：fx3-702-msc-owner-20261029-06，尚未授权/消耗。
- 运行包SHA-256：`831b56f4b2ed7c773bb9b72654128ed36c832f2901ae5b8af60b20c6ce85e2ff`。
- native SHA-256：`aea5b9c76d0c2a55f09d56706164e8ce6a5a413f9c0875cb6c30a93ea5015703`。
- 设备、共享ABI、登录检查和缓存等14个运行组件与05逐字节相同，原生编译差异来自新固定路径/编号；设备调用参数与顺序未增加。

## 当前验证范围

原有64项检查重新通过；新增13组将真实用户shell包装器、标记C夹具、独立内核身份、ACK、原生SHA和命令完成记录接通。包括open请求已返回而helper仍运行、用户501/0600结果被完整监管器消费、重复包装器不重入、坏安装哈希、缺失结果的具体errno、原05 root0600文件的属主拒绝、超限/坏权限/坏JSON/符号链接等情况。

新夹具均为用户501，不冒充新跨用户实测；正向跨用户依据仍是第172轮既有实际root输出进入用户拥有文件的记录。原05 root文件本轮仅检查元数据，未读取内容或改权限。默认CLI只输出计划，当前真实`--run-live`调用已验证在占用记录、缓存、共享帧及Terminal之前拒绝；06运行目录和外层claim均不存在。

## 到服务读取还差什么

[逐项核对](service-read-readiness-review.json) · [本轮一手来源核验](current-primary-source-review.json)。

1. **收发后端不同且进程不同。** 阶段147收发层绑定libusb API，参数要求`libusb_device_handle*`；05实际使用独立root进程里的IOKit650对象。不能把这类指针当libusb句柄，也不能让普通用户Python复用已退出root进程的地址。05结束时句柄已经关闭。下一步需要在拥有接口的原生进程内实现有界IOKit收发，再以带身份/代次的IPC交给控制器。[libusb官方接口契约](https://libusb.sourceforge.io/api-1.0/group__libusb__syncio.html)
2. **端点描述符不等于认证角色。** MSC 81/02/512B元数据已实测，但初始MSC完整认证路径、服务0336实际端点与真实传输时限尚未验证。原生超时返回、在途调用、相机接收和相机工作线程结束需要分别记录。
3. **认证不是零写入操作。** 原7.02库的最终认证应答早于条件历史/日志/模式文件尾部；已解析的分支包含88B历史、4096B日志和3B模式文件操作。它们是否在本机实际触发尚未查询；本轮没有发送认证，也不声称这些写入已发生。原启动配置中的`/tmp`位于nflasha10，不能按Mac临时目录理解为RAM。
4. **退出和完整备份仍缺实机闭合。** cancel请求不等于join，原等待/线程结束不具此处可见的有界保证。整文件读长度、短读、错误传播和前缀续读需要继续落实；两份小库读取草稿不能代替整机备份、同机恢复回读或独立救砖。

## 当前公开工具核查

本轮只读核对的PMCA HEAD仍为`a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`，与既有固定源码相同。重新做AST检查，stop仍吞掉GenericUsbException；671和698行的两次authenticate仍不受后面的stop-finally包围，故不能直接照搬为全部失败情况下的退出保证。[stop实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L906) · [调用和清理范围](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L656)

已再次读到[#715作者6月9日的FX3A 2.02成功报告](https://github.com/ma1co/Sony-PMCA-RE/issues/715)，属于另一型号/版本的本人经验，不替代经典FX3 7.02的恢复或主录证据。A6700/Pico参考项目HEAD也仍为既有d5bb9485版本；本轮没有执行帖子安装命令、下载运行载荷、创建VM或改依赖/权限。

服务认证、相机文件访问、模块、设置与固件写入继续保持未放行。后续工作的重点是同进程IOKit收发与严格退出证据，不能把05接口成功扩展成安全刷写保证。
