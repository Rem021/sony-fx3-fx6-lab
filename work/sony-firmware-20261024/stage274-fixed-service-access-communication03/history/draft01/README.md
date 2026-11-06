# FX3受限SERVICE访问通信03固定方案

本包针对269停在SERVICE获取时的独占访问错误，采用273的受限设备打开策略和完整v5回执。**当前仅编译及离线检查，必须取得本包新单次批准后才能启动。不是固件包，不授权刷写。**

## 已固定的目标与恢复来源

经典ILME-FX3，用户确认固件7.02；当前MSC `054C:0DA1`，缓存节点`4296064081`、位置`0x01100000`，物理USB-C锚点`4294968654`。新缓存与269真实基线在内存中的同机HMAC一致，未保存原串号。节点、线、端口变化则拒绝，不能批准后静默换绑。

用户已完成断开全部USB数据线后的电池拍摄界面及菜单检查；270单独批准的主机收尾已完成，原helper34474及观察器34391均退出，原journal未变。此后用户按要求重接MSC。本包将这次实际证据、原HELD私有回执及新缓存固定为[五份恢复材料](fixed-prior-evidence.json)，不沿用针对85066／82324的旧policy。录像与独立救砖仍未验收。

新标识`fx3-702-service-access-communication-20261101-03`，共享帧schema10／SVC8、许可v3、流帧v5及RCPT5均独立固定；旧268通信及270收尾授权都已使用，不能复用。

## 本次具体操作

最多一个管理员helper；必要时由用户完成Terminal的sudo／Touch ID验证。程序、单次标记及记录存Mac内置盘私有目录`/private/tmp/fx3-702-service-access-communication-20261101-03`及`/private/var/root/fx3-owner-trials/fx3-702-service-access-communication-20261101-03`。

先核对缓存身份、旧实例已退出、当前驱动／IOMedia／内核挂载表及新鲜度。使用原`/private/var/root/fx3-owner-trials/global-fx3-owner.journal`，在同一锁内只追加人工恢复记录和本次OWNED，保留旧字节及旧UNKNOWN，不写旧CLEAN。部分追加后失败则保留阻止续接的尾部，不自动重试。

需用户先在Finder手动安全推出相机全部卷，保持MSC、当前线和端口。随后暂时接管USB，完成最多七次MSC OUT／IN交换并释放旧对象；在最多5秒／50样本窗口内关联原物理端口的SERVICE候选。

SERVICE获取会记录每个失败子步骤、该步骤原码及设备打开结果。**只对设备层ExclusiveAccess允许继续配置元数据和接口打开；接口必须实际独占打开、描述符和管道匹配，才允许原固定START／STOP。** 其他错误不放行，不新增Seize、reset、配置或alternate setter，不关闭其他应用。设备未独占打开且描述符不匹配时，不尝试仅控制STOP。

匹配后最多七次SERVICE认证交换，以及最多一条固定read0、响应体上限88字节；只保存长度、结构和HMAC，不保存原始Hasp或认证内容。之后尝试STOP、对象释放及同机MSC／驱动返回，并分别观察helper真实退出。完整调用参数及程序摘要见[固定计划](fixed-plan.json)和[批准包](approval-bundle.json)。

## 影响与停止条件

Sony START／认证／STOP可能改变服务模式、历史或`.hasp`／`.etools`内部状态，不能宣称相机零写入。本包不读卡或机身文件、不上传模块或运行自写机内程序、不写固件、不初始化、不自动改隐私权限。

工作预算20秒、收尾30秒；有设备超时参数的单次请求目标最多1秒，但不能保证内核调用必定返回。阻塞或不明保留UNKNOWN和原实例，不强杀、重置或自动重试。仅在preSERVICE限定空闲条件满足时可协作退出；其余HELD不自动释放。单独主机清理例外不适用于本次。

269没有具体失败子步骤，不能追认就是device open。若真正失败在plugin或interface，此候选仍可能停止。接口独占不等于所有默认管道流量独占，其他device客户端并存时，本包不能证明它们完全无并发流量；试验期间应仅有这一项Sony USB任务，不自动关闭Chrome／ChatGPT。描述符不匹配时的已有控制退出仍属实验，不代表可靠救砖。

## 通过标准与当前边界

本次目标是可信SERVICE认证／固定响应／STOP回执、helper结束、独立同机MSC及存储驱动缓存恢复，以及用户正常屏幕确认。缺一项均单列未完成；名义主机归还后全局机身状态仍记UNKNOWN，不把USB重现或清理进程当成全部相机线程已结束。

[当前实际恢复绑定检查](current-binding-check.json)、[完整流程](test-receipt.json)、[获取失败检查](acquisition-integration-check.json)、[共享边界](shared-access-check.json)和[固定材料检查](package-test-receipt.json)仅在普通用户真实进程／人工设备运行。native生产程序仅编译。新上机包就绪也不代表实际兼容。

原G01至G16、健康完整备份、独立恢复／写回、MAIN1080p HEVC实录及音画长录、持久化准入与首刷要求全部保留。本次批准不覆盖任何固件写入。
