# FX3受限SERVICE访问通信05固定方案

本包针对280在完成SERVICE 7轮认证、固定`read0` 12字节请求、12字节响应头（`version=3, reason=1 ok`）、88字节响应体（`body_hmac = e54a4bfc...`）、`STOP`（`0336:7`）与对象释放（`0336:8`）后，在返回轮询窗口中因同口重枚举出`054C:096F`（`"USB Bus-powered Device"`，对应机身弹出“选择USB连接模式”菜单）被旧版`find_at()`判为`FX3T_DENIED`而停在`HELD`的实际结果，合并283已封板的post-`STOP` `054C:096F`过渡态兼容规则，并配合机身USB连接模式固定为大容量存储（Mass Storage），形成新的单次固定方案（`fx3-702-service-access-communication-20261101-05`）。**当前仅完成编译及离线检查，必须取得本包新单次批准后才能启动。不是固件包，不授权刷写。**

## 已固定的目标与恢复来源

经典ILME-FX3，用户确认固件7.02；当前MSC `054C:0DA1`，缓存节点`4296570640`、位置`0x01100000`，物理USB-C锚点`4294968654`（逻辑锚点`4294969719`）。新缓存与280真实基线在内存中的同机HMAC一致，未保存原串号或私有密钥。节点、线、端口变化则拒绝，不能批准后静默换绑。

用户已完成断开全部USB数据线后的电池拍摄界面及菜单检查；282单独批准的主机收尾已完成，原helper `37860`及观察器`36633`均已退出，原journal保持11条记录（2816字节）未变。此后用户将机身USB连接模式固定为Mass Storage并重接MSC。本包将这次实际证据、原HELD私有回执及新缓存固定为[五份恢复材料](fixed-prior-evidence.json)，不沿用旧policy。录像与独立救砖仍未验收。

新标识`fx3-702-service-access-communication-20261101-05`，共享帧schema10／SVC8、许可v3、流帧v6（`FX3FLOW6`）及RCPT5均独立固定；旧279通信及282收尾授权都已使用，不能复用。

## 本次具体操作

最多一个管理员helper；必要时由用户完成Terminal的sudo／Touch ID验证。程序、单次标记及记录存Mac内置盘私有目录`/private/tmp/fx3-702-service-access-communication-20261101-05`及`/private/var/root/fx3-owner-trials/fx3-702-service-access-communication-20261101-05`。

先核对缓存身份、旧实例已退出、当前驱动／IOMedia／内核挂载表及新鲜度。使用原`/private/var/root/fx3-owner-trials/global-fx3-owner.journal`，在同一锁内只追加人工恢复记录和本次OWNED，保留旧字节及旧UNKNOWN，不写旧CLEAN。部分追加后失败则保留阻止续接的尾部，不自动重试。

需用户先在Finder手动安全推出相机全部卷（当前`disk10s1`仍挂载），保持MSC、当前线和端口。随后暂时接管USB，完成最多七次MSC OUT／IN交换并释放旧对象；在最多5秒／50样本窗口内关联原物理端口的SERVICE候选。

SERVICE获取记录每个失败子步骤、该步骤原码及设备打开结果。**只对设备层ExclusiveAccess允许继续配置元数据和接口打开；接口必须实际独占打开、描述符和管道匹配，才允许原固定START／STOP。**

匹配后最多七次SERVICE认证交换，以及最多一条固定`read0`（12字节请求、12字节`version=3`响应头、最多88字节响应体），之后执行`STOP`（`0336:7`）与对象释放（`0336:8`）。在返回窗口（`mode=1 / FX3_W_RETURN_ARMED`）内：
- 若同口出现同串号HMAC、新`registry_id`的`054C:096F`（`"USB Bus-powered Device"`）过渡节点，按`FX3T_BUSY`（`status=2`）继续轮询，不做任何设备打开或I/O；
- 待同口、同串号HMAC、新`registry_id`的`054C:0DA1`（`ILME-FX3` MSC）返回后，完成`0da1:9`驱动归还、写入`CLEAN`并使helper正常退出。完整调用参数及程序摘要见[固定计划](fixed-plan.json)和[批准包](approval-bundle.json)。

## 影响与停止条件

Sony START／认证／STOP可能改变服务模式、历史或`.hasp`／`.etools`内部状态，不能宣称相机零写入。本包不读卡或机身文件、不上传模块或运行自写机内程序、不写固件、不初始化、不自动改隐私权限。

工作预算20秒、收尾30秒；阻塞或不明保留UNKNOWN和原实例，不强杀、重置或自动重试。

## 通过标准与当前边界

本次目标是可信SERVICE认证／固定88字节响应／STOP回执、`0da1:9`驱动归还、helper正常结束（`COMPLETE`）、独立同机MSC及存储驱动缓存恢复，以及用户正常屏幕确认。

[当前实际恢复绑定检查](current-binding-check.json)、[完整流程](test-receipt.json)、[获取失败检查](acquisition-integration-check.json)、[共享边界](shared-access-check.json)、[响应头定位检查](header-localization-check.json)、[post-STOP 096F过渡检查](post-stop-096f-check.json)和[固定材料检查](package-test-receipt.json)仅在普通用户真实进程／人工设备运行。native生产程序仅编译。

原G01至G16、健康完整备份、独立恢复／写回、MAIN1080p HEVC实录及音画长录、持久化准入与首刷要求全部保留。本次批准不覆盖任何固件写入。
