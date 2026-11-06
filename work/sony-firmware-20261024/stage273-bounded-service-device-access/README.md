# SERVICE设备打开能力的受限兼容候选

**已接入完整控制器并通过离线检查；native入口仍关闭、目标未绑定，不是可直接上机的包。** 本轮没有管理员、USB、Sony认证或真实journal操作，相机一直保持断开。

## 具体修改

原SERVICE代码在`USBDeviceOpen`返回任意非零值时停止，控制回调也只接受device_open。依据本机Apple SDK与[固定libusb实现](https://github.com/libusb/libusb/blob/987c1170d0018ba82557823a98ae443e8335e11b/libusb/os/darwin_usb.c#L1939)，现在只将设备层`kIOReturnExclusiveAccess`分类为“没有取得设备独占打开”，允许继续检查配置元数据及尝试原来的接口独占打开。其他打开错误仍停止，不抢占或重试。

该分支只有在接口确已打开、完整描述符和管道检查匹配后，才赋予私有的受限控制能力。控制回调仍要求root、有效设备对象，并只接受原有固定START／STOP八字节请求。接口未取得、匹配未完成、任意标准SET_CONFIGURATION或其他vendor请求均不能借这条路径执行。设备本来已独占打开的正常MSC／SERVICE路径保持原用途。

描述符不匹配时，若没有设备独占打开，本候选直接拒绝控制退出，不在未取得接口的状态下尝试STOP。对象销毁仍只关闭本实例实际打开过的device／interface；没有把共享情形伪装成device_open成功。

协议升级为`FX3FLOW5`／schema5，在步骤和该步骤原码之外增加设备打开分类与设备打开原码。它们记录**获取当时的结果**，不证明对象此后仍持有。完整观察器绑定四项记录，拒绝互相矛盾的分类／原码、后续改写及旧协议。共享入口帧使用新的离线schema9／SVC7，无新许可或机身目标。

## 检查及边界

- [策略检查](device-policy-check.json)：实际执行生产adapter和模拟管道共同使用的C策略，核对SDK错误常量、普通错误拒绝、接口条件和固定请求白名单；没有IOKit调用。
- [八组完整流程](test-receipt.json)：恢复准入、正常模拟返回、空闲退出及拒绝条件重新通过。
- [五组获取回执检查](acquisition-integration-check.json)：普通用户真实helper／IPC及私有RCPT5验证步骤和错误；获取失败不进入SERVICE认证、读0或STOP，旧读者拒绝新格式，native入口全部关闭。
- [共享能力场景](shared-access-check.json)：模拟共享设备且接口取得时完成固定通信；共享但描述符不匹配、接口冲突时保留HELD并阻止后续命令；能力记录伪造拒绝。

上述进程、peer、文件、fsync和退出为真实Mac行为，设备／驱动／缓存响应为人工数据。不能据此宣布真实接口可用、认证成功、正常退出或救砖。native backend已全量编译，但没有执行。

[具体原生差分](native-adapter.diff) · [构建](build-receipt.json) · [来源](source-origins.json)。源码核查确认SERVICE分支未新增Seize、重枚举、reset、配置或alternate setter；原来正常MSC归还的重枚举调用保留。初始检查的测试脚本语法错误和“全文件不得出现重枚举”的错误断言均在[更正记录](precheck-corrections.json)保留，未启动设备试验。

## 下一次真机试验前仍需完成

269的真实失败只有复合获取错误，不能追认其子步骤。本候选是对一种有源码依据的设备层冲突进行受限适配；若实际失败发生在plugin或接口层，仍可能失败。另有device userclient存在时，接口独占不等于所有默认管道流量独占，当前未证明其他应用完全无并发流量；不自动关闭应用。

必须先取得恢复后同机MSC缓存，更新指向269及270实际证据的人工恢复绑定，再固定新目标、scope、许可、程序和一次操作范围。当前保留的旧历史policy及零目标不能作为新机身准入材料，不重用268／270单次授权。下一次操作仍需独立批准。

全部G01至G16保留。健康备份、独立恢复／写回、MAIN1080p HEVC编码成片、音画与长录、持久化准入及首次刷写均未通过。
