# FX3：认证摘要按模式分派、STALL与事件边界

2026-10-27。**修正了后续传输准备中的一个实质问题：MSC 与服务模式必须显式选择摘要输入，不能把阶段141同一服务校验器的六轮夹具当作双模式认证证明。** 新提供者已接阶段140控制器并离线检查；初始 MSC 的 FX3 原验证者仍未定位，没有放行实机认证。

阶段144一次真实描述符读取及其20个封存成员已复核。该授权已经消耗并关闭，本轮没有新增 USB、相机、驱动或 Windows 操作；完整 HEVC 主录与恢复目标及16项验收要求保持。

## 可运行的 CPU 提供者

[mode_digest_provider.py](mode_digest_provider.py) 只计算摘要，没有 USB 加载器、认证请求或相机命令行。它先核对阶段141封存清单和服务提供者 SHA；公开常量仍由原提供者验证并作为 AST literal读取。

| 显式模式 / PID | 挑战码 | 本轮实现 | 当前证据 |
|---|---|---|---|
| MSC / 0DA1 | 2 | 挑战前4B的 SHA-1 | 固定 PMCA 参考分支；不是 FX3 初始验证者证明 |
| MSC / 0DA1 | 8 | 挑战前4B的 SHA-256 | 同上 |
| SERVICE / 0336 | 8 | 完整512B挑战加该轮512B材料的 SHA-256 | 原 FX3 `libsencore::xxstep` 与公开材料、guest校验 |
| SERVICE / 0336 | 2 | 拒绝 | 当前固定 FX3 服务原验证者只证明挑战8 |

模式、VID/PID、挑战类型/长度及轮编号都显式检查。绑定惰性摘要任务时，要求它仍是控制器当前 pending 对象，并与 `AUTH_MSC` 或 `AUTH_SERVICE`、轮号、挑战内容及时间窗口一致；已消费任务和超过六个任务拒绝。摘要计算与 USB 操作仍分离。

固定 [PMCA源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py) 的模式分支已用 AST核对，没有执行下载文件。其 `sha1_faulty()` 仅将长度计数改为 `len & 31`；MSC分支输入恰为4B，`4 & 31 == 4`，故此处可使用正常SHA-1，不需要运行下载的完整旧算法。**这不说明本台FX3初始MSC实际会返回码2或码8，也不说明其真实验证者一定使用这条参考分支。**

## 验证结果

[test_mode_digest.py](test_mode_digest.py) 与 [执行回执](run-mode-tests/results.json) 将证据分开记录：

| 检查 | 结果 |
|---|---|
| MSC两类摘要 × 三轮 × 八组声明输入 | 48项参考对照通过；改变后508B或轮材料不改变摘要 |
| SERVICE原函数校验 | 12项接受正确服务摘要；12项拒绝错误套用MSC摘要 |
| 无效模式、PID、类型、长度、轮号或挑战码 | 11项拒绝 |
| 错误模式/恢复阶段/时限、非pending副本及重复任务 | 20项拒绝 |
| 控制器两条完整惰性流程 | MSC参考族2→SERVICE原族8、MSC参考族8→SERVICE原族8，各三轮 |

两条流程的MSC三轮分别对照公开参考，SERVICE三轮分别调用原服务验证器。总计120次原 AArch64 函数进入；SHA摘要与C内存操作仍使用已声明的CPU桥，没有运行相机自己的OpenSSL原生二进制。USB身份、驱动接管/归还、模式变化、最终认证接受和物理正常操作全部是夹具。原输入/输出边界、寄存器/SP等检查由固定原验证器夹具执行。

阶段141原记录保留；其标为MSC的三轮只说明服务验证器接受了同一种服务摘要，不能用来声称初始MSC认证已验证。后续应采用本轮显式模式提供者，并继续保留初始MSC证据缺口。

## 模式控制请求的报错可能晚于副作用

[原模块与参考分派审查](mode-and-vendor-boundary-review.json)重新核对7.02固件内 `usbg_sen.ko` 的原 `.text[0..0xc8)`：匹配控制头后先调用 `usb_gadgetcore_stop_other_driver`，尝试投递事件，未检查投递返回值，然后仍返回常数2。

从 [Sony官方FX3 7.00开源包](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)选取21个USB core源码文件，保存原字节与SHA，没有构建或加载。参考宏 `USB_GADGETCORE_THRU=2`、`STALL=1`；对于Device/Other接收者，参考分派器遍历所有注册vendor回调。如果全部返回THRU，最终返回 `-EINVAL`；即使此前某个回调已尝试排队，也可能走到这个错误分支。请求本身还经过延后工作队列，传输返回与用户态线程完成是不同事件。

因此不能把已完成的STALL当作“没有生效”，也不能自动补发START/STOP。与此同时，不能笼统吞掉任何USB异常：已完成STALL、传输仍在途、超时、设备消失和身份不明需要各自记录。阶段140通用START错误路径目前转向清理；本轮没有悄悄把STALL改为认证成功或擅自改变控制器语义。真实后端须先补这条分类及实际结束判据。

这份GPL对应7.00，并非精确7.02内核的全部构建证明；注册顺序、后续回调是否返回0，以及本机实际USB返回值都未观测。故本轮只证明“存在该错误/副作用边界”，不声称本机每次模式请求都会STALL或事件必然成功排队。

## 原7.02内核入口与未闭合路径

复用了已提取且固定SHA的7.02原kernel Image，无需重拆209MB WBI。用精确名称、导出值/名称记录及排序邻居定位三项静态导出候选：`usb_gadgetcore_stop_other_driver`、`register_driver`、`unregister_driver`；保存每项0x120B前缀及SHA，见 [native-kernel-usb-exports.json](native-kernel-usb-exports.json)。没有执行原内核，仍未恢复其完整静态 `setup_vendor_specific`。

阶段143三项原候选的提取清单、脚本、README及文件共六个外部证据pin已采用；原目录和旧快照保留。`usbg_storage.ko`、`libUsbControl.so`、`libusbcmd.so`的符号扫描未找到初始摘要验证者，这不是其不存在的证据。对原 `appFw.so` 另定位六个直接SHA256 PLT调用、两个局部调用组及一项SENSER日志引用，搜索范围和局限保存在本目录JSON；这些局部搜索尚未建立到初始MSC认证的完整调用链。

下一步从三项原内核入口及SEN注册/回调继续追踪初始MSC处理者，补完整传输后端的端点角色、已完成STALL/取消/超时与驱动归还。没有新的上机认证方案或放行；同机健康备份与恢复、独立救援、HEVC主录/音画同步/长录/冷启动等仍未通过。
