# FX3：资源回调失败、线程收尾与 Mac 驱动接管范围

2026-10-27。继续原 MAIN 1920×1080、30000/1001、HEVC42010 约16Mbps目标；全部16项要求保留。上一阶段151取得 A7C II 的作者演示材料，是实际进展。本轮补齐此前150留下的资源/线程失败分析，并核对首次上机所需的 Mac 驱动接管边界。

**新结论：内部回调返回0、线程标志1或内部状态4，都不能单独作为服务已就绪、旧线程已结束或恢复成功的依据。Mac libusb接管范围还必须按整台USB设备处理。** 本轮没有新增USB、相机、Windows、UU、驱动或权限操作，没有执行下载来的工具。

## 原指令核对与有界实验

固定 FX3 7.02 的原 `libObj.so` 和 `libMWF.so`。150提取的MWF原件由151保留回执核对，本轮不更改150的旧快照或未封存状态。静态读取10个Obj函数、5个MWF函数；14组有界CPU实验共102次原函数进入。

原Obj构造函数 `ea58c` 注册资源42、上下文this、回调 `ea9b4`；原重定位 `2616e0 -> ea9b4` 使该绑定可核对。MWF `SubCallbackProc` 真正执行消息key比较、pending计数读取/减一和原ParamStd读写；pending归零后经原 `SubCallback` 调用原Obj回调。ObjMsg复制、列表操作、资源用户表、所有pthread/信号量/加载器/日志调用仍为明确声明的CPU夹具，没有模拟真实系统调度成功。

| 条件 | 原指令得到的结果 | 不能外推的结论 |
| --- | --- | --- |
| key匹配、pending=1、线程创建夹具返回0 | pending归零，资源回调被调用，内部线程标志置1 | 不证明真实资源管理器送达、线程运行或USB模式切换 |
| 线程创建返回11，再给一次匹配回调 | 只尝试创建一次；失败后标志仍为1；第二次转向sem_post。该post返回22时，上层MWF回调仍可返回0 | 标志1和返回0不是资源线程存在或就绪的证明；夹具没有运行sem_init，不推断实际未初始化信号量的行为 |
| key不匹配／pending=2 | 不调用Obj回调；pending分别保持1／减为1 | 队列存在或收到某个回复不等于此请求完成 |
| pending=0／payload空／用户表插入返回7 | 分别得到错误返回1／1／7，均未进入Obj资源回调 | 不把早退当作成功 |
| 注册mode字段=1 | Obj回调可进入，但不创建线程、不置标志 | 仅是字段条件，不证明实机模式 |
| worker取消/等待夹具均返回3 | 原消费者不检查两个包装函数的失败返回，仍可启动后续normal worker，内部状态到4；旧token仍保留 | 状态4不是旧线程已退出的证明 |
| 显式loaded=1控制、join返回3、dlclose返回-1 | 仍调用dlclose；原包装器将加载器token清零，内部状态到4 | token清零不证明卸载成功；这是独立loaded控制，不声称149普通回调自然具有此标志 |
| normal worker创建失败，或第1/第2个sem_init失败 | 到清理分支、内部状态/线程标志清零，并停在pthread_exit夹具边界 | 没有运行真实pthread_exit，不能认定线程或相机已恢复 |

所有原函数代码保持不变，原指令和桥接写入都限制在声明的客体栈、arena及特定BSS对象范围；入口栈上方保护区保持。worker正常/等待失败两类在第二个sem_wait前停止，没有执行后续服务退出、资源Release、历史文件或完整NIN尾部。

见 [静态原件证据](original-resource-static.json)、[14组结果](run-original-resource/results.json)、[执行器](run_resource_failure.py)。这些结果证明特定原代码的失败分支，不能证明实际OS消息ABI、资源获取、系统线程、USB注册、初始MSC摘要算法或相机录像。

## Mac接管：接口参数不等于影响范围

读了固定提交的 [A7C II服务探针](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/macos/mac_service_readonly/sony-service-research/service_probe.py)：它明确要求先安全卸载相机的所有卷；open/close中有detach/attach接口0的调用。该源码没有在本机运行，其头部机型/版本也不等于FX3适用性证明。

随后另取 [libusb官方v1.0.30 Darwin源码](https://github.com/libusb/libusb/blob/v1.0.30/libusb/os/darwin_usb.c)，只作文本读取并保存哈希：

- 2900—2945行明确是整台设备capture，接口参数被忽略；权限路径可能要求相应entitlement授权或root。
- 2140—2244行必须区分两条路径：capture设置 `kUSBReEnumerateCaptureDeviceMask` 后走重开/restore分支，源码注明capture本身不做普通重新枚举；非capture路径才等待重新枚举。因此不能笼统称detach就是总线重置。
- 最后一次attach（2948—2965行）会走非capture的重新枚举路径。不能把恢复动作描述成只归还接口0。
- restore（2078—2138行）包含关闭/重开、条件性set_configuration及重claim；这些隐含操作也需纳入实际候选审核。
- 自动release（2979—2997行）会忽略attach失败并返回success。因此release成功不足以证明原驱动回归。

这里没有验证A7C II作者运行时使用的libusb版本，也没有将上游代码等同于阶段142的描述符专用私库。原件来源和逐段核对在 [来源回执](host-capture-source-receipt.json)、[接管审计](host-capture-audit.json)。

## 更新后的上机准备要求

后续真实owner必须把整设备接管、相机全部存储卷的安全卸载、重开后的身份/连接代次，以及最终驱动关联分开记录。卸载只需卷/设备元数据，不读取素材；接管、驱动操作和重新枚举仍需具体方案对应的授权。禁止默认auto-detach，禁止以一次release、STOP回复或内部状态值替代恢复观测。对不明在途I/O、未确认attach或线程结束的情况保持UNKNOWN，不自动重置或追加请求。

本轮只形成更准确的设计限制，没有声称真实owner、驱动接管/归还或完整首次服务试验已经可运行。下一步应针对固定Mac native后端实现真实owner及连接代次、显式capture/归还和工作进程生命周期；首先离线核查错误路径，再形成一次性可审阅方案。H.265演示的具体补丁/原片继续追查；本轮搜索没有获得新的实现来源，不将重复搜索当成解锁进展。

当前一次USB描述符读取授权已消耗，不重复执行。MAIN主录、同机健康完整备份/恢复/回读、独立救援、长录与冷启动仍未验收，没有可安全试刷包。
