# FX3 7.02：服务退出、线程结束与主机异常处理

2026-10-27。用户现有设备为 Mac 与 Windows 电脑，没有 RP2040 或 USB 串口工具；Windows 沿用此前“暂不可用、先用 Mac”的指示。本轮仅静态分析已经取得的 FX3 7.02 原库及固定版本 PMCA 源码，没有再次枚举、打开相机或执行 Sony 代码。

**已找到正常的等待线程与退出路径，但尚未验证可以在真机上有界地退出并恢复普通模式。** 不把取消请求、USB 状态清零、主机函数返回或 “Done” 当作安全退出凭据。当前仍未进行服务认证、机身文件读取、载荷加载或刷写。

## 原固件里已核对的路径

静态解析原 `libsencore.so` 的 18 个完整函数，核对 32 个 PLT 调用、7 项事件跳表及 5 项 GOT 绑定。原库 SHA 为 `a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410`。完整地址、原字节及指令见 [service-exit-review.json](service-exit-review.json)；可复核脚本见 [audit_exit.py](audit_exit.py)。未运行这些原函数。

| 路径 | 原字节支持的结论 | 仍未证明的部分 |
|---|---|---|
| 认证完成事件 6 → `run_workers` | 启动命令处理线程前，先 join 对象偏移 +8 的认证线程 | join 返回值被忽略；实际线程、成功返回及 USB 到事件的完整绑定未验 |
| `WorkerThreadManager::cancel` | 向 +8、+16 两个线程发出 `pthread_cancel` 请求 | 请求返回不等于线程或历史写入已结束 |
| `WorkerThreadManager::join` | 两次普通 `pthread_join`，随后清理大数据处理器并卸载插件 | 返回值被忽略；没有此处可见的等待期限；清理函数内部与其他线程未全面闭合 |
| 两种 stop 回调 | 非零状态先记录日志，之后仍把 USB 状态清为 0；异步回调再推事件 3 | 状态 0 不证明 stop 成功；事件 3 处理中的 join 成功也未反馈给主机 |
| `finalize_usb_interface` | 等待状态、请求 stop、join、再次等待，随后关闭并销毁接口 | `spin_wait_while` 是 `usleep(10)` 重试，无截止时间；不能据此保证恢复 MSC 或冷启动 |
| `senser_stop` | 经 `SenserIfStop` 调用 finalize、移除处理器并关闭通道 | 不把库内导出函数与主机 vendor-stop 的全部固件分派链视为已接通 |

阶段136的“最终认证应答早于后续历史/模式文件分支”结论仍成立。本轮补充了正常命令启动路径上的 join：**只有对应 join 成功，才可能把认证尾部完成纳入时序保证**。原调用者忽略返回值，因此不能单凭主机收到认证应答或随后等待固定秒数作这种判断。

原线程代码也明确调用 `pthread_setcancelstate(0, …)`、`pthread_testcancel()`，再进入状态参数 1 的区段。按通常 Linux pthread 常量语义，这是可取消检查点和随后禁止取消的区段；这是基于静态代码和库契约的解释，本轮没有运行相机 libc 或测量 I/O 解阻塞。取消请求仅排队、完成需要另行确认，见 [Linux man-pages 维护者文档](https://raw.githubusercontent.com/mkerrisk/man-pages/master/man3/pthread_cancel.3)。不能认为主机超时会立即终止相机侧工作，也不能据此断言已出现卡死或损坏。

## 公开主机工具不能直接充当退出保证

对固定提交 `a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0` 的两个 PMCA 源文件只做 AST 解析，没有导入或执行：

- `SonySenserAuthDevice.stop()` 吞掉 `GenericUsbException`，没有读取线程完成状态或等待恢复普通接口。函数返回本身不能区分正常退出与 USB 失败。[原实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L906)
- `senserShellCommand()` 在第二次认证之后才进入带 `finally: dev.stop()` 的保护块；认证失败、首次 MSC 切换及重新枚举过程不在这个局部清理范围内。不能把该 finally 解释为所有失败都能正常退出。[原实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/commands/usb.py#L656)

这些是所审版本的结构事实，不是所有 PMCA 版本或每种机型的实际失败结果。阶段134/136已定位的条件 `.hasp`、`.etools` 和模式文件操作仍须纳入将来的认证方案；服务认证不能统称为零写入。

## 对下一次实机测试的具体影响

以后若形成并获准执行服务测试，主机应分别记录进入请求、认证、重枚举、命令可用、退出请求、接口恢复和相机正常使用的结果；异常清理范围需覆盖第一次进入请求，不能吞掉退出错误。主机超时只能记为结果未知，不自动重发认证、重启或刷写；失去通信时不能声称 stop 已完成。当前还须补齐实际 Mac 驱动归属/释放、完整 vendor-stop 分派、传输超时与退出后的可观测凭据，才有具体可执行的首次方案。

现有两台电脑足以继续主机侧研究和标准 Fastboot 识别。此前实际 `fastboot devices -l` 已返回空列表，前后均为 MSC，见[阶段135实测](../stage135-Fastboot-entry-discovery/README.md)。公开 [A7 IV 项目](https://github.com/DavidBuchanan314/ILCE-7M4-RE/tree/2328d18ce640e6c8cd9341efcf0043ce9042a135) 的串口 BootROM → RP2040 桥 → 自制 Fastboot 载荷，既缺当前硬件条件，也尚无 FX3 专用适配证据；补一块开发板本身不能消除这些缺口。没有在 FX3 上尝试外机型载荷或模式进入。

1080p29.97 HEVC MAIN、同机完整健康备份与恢复、独立救援、音画同步及长录/冷启动仍未完成实机验收。全部16项要求与现有授权保持，未放行持久刷写。
