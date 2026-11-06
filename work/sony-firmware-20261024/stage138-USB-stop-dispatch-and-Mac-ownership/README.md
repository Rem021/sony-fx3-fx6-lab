# FX3 7.02 USB 服务请求分派与 Mac 驱动归属

2026-10-27。**原 FX3 包已找到与公开工具一致的进入/退出控制请求头，以及匹配后投递事件的内核实现。仍未证明真机退出完成或独立救援。** 本轮只有原镜像/库/模块静态读取、公开源码下载和主机软件元数据读取，没有运行相机协议、再次枚举 Fastboot、认证、切模式、分离驱动或读写机身文件。

上一轮137的9个回执成员已逐一复核，属于有新退出时序证据的进展。本轮沿用 Mac，Windows/UU 继续延后；设备盘点仍为只有两台电脑，无 RP2040/串口桥。

## FX3 原件支持到哪一步

输入来源和 SHA 见 [inputs-receipt.json](inputs-receipt.json)。从已校验的7.02官方 `nflasha15.img` 离线提取 `usbg_sen.ko` 与 `usb_beets.ko`，没有加载模块。Sony FX3 7.00 GPL 内核包只作为源码参考，不把它当作已证明与7.02实机编译配置完全相同。新增选取11个普通源码文件，保留原始字节；旧编码注释只在展示时替换解码，未改原文件。

| 环节 | 已取得的原件证据 | 结论边界 |
|---|---|---|
| 请求头配置 | `libInfraUsbCmn.so` 的 VA `0x1d460` 保存两组8字节 setup：`4301ff37aad70000`、`430100c855280000`；创建服务 gadget 时复制16B并交给 probe ioctl | 与固定 PMCA 的 Start/Stop 参数逐字段相符；没有把这些字节发送到相机 |
| 原内核匹配 | `usbg_sen.ko` 的 `.text+0..0xc8` 连续代码对两组 setup 各做完整8B比较；匹配得到命令0或1 | 用 `$x/$d` 映射符分开代码与随后字面量池，未把数据误反汇编成代码 |
| 回调登记 | `.text+0x15c0` 从字面量池装入 `.text+0` 指针，存入 vendor 回调位置，随后注册 gadget driver | ABS64重定位、登记前缀和参考源赋值相互对应；未执行初始化 |
| 事件投递 | 匹配后先请求停止其他 gadget driver；该请求成功才投递4B命令号到事件7。投递后的返回值未在该片段中检查 | 它是异步分派，不能把主机控制传输结束等同于服务线程退出 |
| 用户态消费者 | `CUsbGadgetSen::proc_kevent` 对 common event7/subtype4 的命令0/1分别调用对象 `+f0/+f8` 回调，并传事件2/3 | 完整队列所有权、运行时回调登记、USB状态应答到137中 cancel/join 的全部关联仍未闭合；不能只按整数相同合并不同事件类型 |

完整6个原库函数、原内核匹配代码、登记前缀、命名的 `usbg_ldisc_stop` 函数及对应源段见 [vendor-dispatch-review.json](vendor-dispatch-review.json)。脚本 [audit_dispatch.py](audit_dispatch.py) 只解析字节和 AST，没有原生 Sony 代码运行或仿真实机结果。

原库 SHA 为 `6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396`；新提取 `usbg_sen.ko` 为 `1a7294dd9d3babde3f1e8cc2ac4aa12f54356f61995993bbc18ace095ed0cbf2`。`usb_beets.ko` 本轮仅提取/初步符号盘点，未认作 vendor 请求处理器，不凭名称给它赋予救援能力。

## 两个模式文件必须区分

原 `CUsbSvc::check_forced_senser_mode` 会以只读标志打开 `/setting/sen/smode`，最多读取3B并比较前2B `UU`。它不同于阶段136认证尾部涉及的 `/ramdsk/dev/mode` 与 `AA`。

官方启动配置把 `/setting` 放在可写闪存分区，但本轮没有验证机身上该文件是否存在、谁会修改它、当前内容或冷启动效果。不能因为发现检查函数就声称已被强制进入服务模式，也不能把另一文件的写入当成此文件的来源。任何“回到正常模式”验证以后都应分别记录这些状态，不能在本轮权限下尝试删除、改写或读出机身文件。

初次结果有一个字段名可能被误读成“已证明文件不存在”，已改为“实际存在/认证修改是否已验证=false”。初次输出和对应源码副本保留于 `attempt-initial-field-label/`；当前结果已重新静态生成，这不是设备失败或重新测试相机。

## Mac 端接管与恢复也是实际操作

审查固定 PMCA 提交 `a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0` 的 generic backend 和设备基类，以及 libusb `v1.0.30` 的 macOS 实现，均只作源码解析。详见 [Mac-driver-ownership-review.json](Mac-driver-ownership-review.json) 和 [audit_host.py](audit_host.py)。源段行号以本轮保存的原文为准。

- PMCA 构建设备对象会调用 reset；libusb backend 的 reset 在内核驱动活跃时尝试分离接口0。MSC reset 还发 SCSI 命令，CLI 列设备会继续做 Inquiry。因此其“列设备”不属于仅缓存读取，不能沿用现有缓存许可执行。[PMCA backend](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/driver/generic/libusb.py)
- 在所审 libusb macOS 分支，detach 面向整台设备，并可能重新枚举；源码按 entitlement/权限检查分支处理，attach 也会重新枚举。自动 release 路径即使重绑失败仍可能返回成功。PMCA 所审 backend 没有显式配对 attach，因此 dispose 不能单独作为恢复凭据。[libusb 原实现](https://github.com/libusb/libusb/blob/v1.0.30/libusb/os/darwin_usb.c)

上述是参考源码的能力和限制，未在本机尝试捕获、授权或分离设备。没有新增权限、root 调用或安装驱动。主机元数据为 macOS27.2/arm64；本研究 venv 未安装 PyUSB/libusb1，两个常规 Homebrew Cellar 路径未见 libusb，范围有限，不能当作整台 Mac 绝无其他副本。没有加载来源未知的已有库。

## 对首次上机方案的收敛

现阶段已能把控制请求头及内核异步匹配落到 FX3 自己的原件，而非只参考外机型。下一步需要把登记回调和消息消费者继续接到137的取消/等待链，再形成一个限定单机、明确超时和错误、能分别确认机身退出与主机重绑的方案。不能直接运行广泛列出所有 Sony 设备的旧 CLI，也不能把 host timeout、控制请求结束、callback状态0、dispose或 release 成功替代实际返回正常模式。

原有 [首次实机分阶段计划](../stage129-AP-DMM-config-and-device-trial-plan/DEVICE_TRIAL_PLAN.md) 继续适用。完整 MAIN 应用约79MB的同机健康备份、字节恢复和独立救援没有被两个小库读取草稿替代。1080p29.97 HEVC MAIN 的实际编码、音画同步、热/长录及冷启动均未验收；全部16项要求与授权保持，未放行持久刷写。
