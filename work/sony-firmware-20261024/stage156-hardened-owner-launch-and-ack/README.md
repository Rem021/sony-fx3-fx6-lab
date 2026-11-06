# FX3 首次 USB 接管与归还候选：固定授权、root staging 与进程确认

2026-10-28。**已实现可供单独授权审阅的执行候选；本轮17项当前自写夹具检查通过。真实管理员程序、IOKit接管、相机认证/文件/固件操作均未执行，尚无可刷包或救砖验收。**

父检查点155全部69项原件已重验。原16项 MAIN 1080/29.97 HEVC42010约16Mbps、健康备份/恢复回读、独立救援及实录验收要求不变。此前描述符单次权限已消耗，不能用于本次操作。

## 候选固定身份

- 试验编号：`fx3-702-msc-owner-20261028-01`。
- 目标：经典 ILME-FX3，用户确认固件7.02；VID/PID `054C:0DA1`，location `0x02100000`。不查询固件版本，不将用户版本确认当作程序测量。
- [固定构建及源码](helper-build-receipt.json)、[运行包](release-bundle.json)、[本地复核和限制](local-source-and-lifetime-review.json)。运行包 SHA-256 为 `e099d58b73261c076491fc0c08c9b1b4b72f5a844fe3af22b3d8060110a956a4`。
- 原生可执行文件 SHA-256：`a68bbdd86a4894792864955c73461cfb04477715031835880bceb800cc4f9c73`。只编译未执行；仅链接系统框架，不加载用户 Python/DSO。

## 单独授权的具体范围

这次拟验证**一次主机 USB 接管与归还**，不是刷机：建立设备用户客户端，显式 `USBDeviceOpenSeize`、capture/release，限定接口0及已核对的bulk端点元数据。程序没有 Sony vendor 认证/服务、相机文件、模块上传、WBI、固件写入、USB reset、SetConfiguration或备用重试路线。

执行前须由用户在 Finder 手动推出 FX3 的所有卷，并保持相机开机与MSC连接。程序不自动卸载卷；C路径在接管前、claim前检查已挂载或未知介质，发现不满足就拒绝继续。本次不读卡内素材。

管理员操作还会创建以下**本机试验记录**：

- 用户私有共享目录：`/private/tmp/fx3-702-msc-owner-20261028-01/`，目录0700、共享文件0600；原生程序拒绝关闭所有者检查的文件系统。
- root私有目录：`/private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01/`，目录0700；固定helper复制后设为root所有/0500，核对精确SHA后才执行。
- 该root目录及 `entry.once` 分别构成启动端和C入口的固定单次记录。失败也不删除或自动重试；换一个共享文件不能复用本次编号。不安装常驻服务、驱动、登录项或通用root执行器。

授权必须同时绑定本次编号、目标和运行包SHA。当前主状态的设备/驱动/管理员试验授权与release仍为false，默认CLI仅显示计划。UU输入监控与Touch ID确认不覆盖这次动作。

## 执行与失败时的行为

[launch_policy.py](launch_policy.py) 生成固定内联AppleScript及shell文本；不从可变 `.scpt` 读取待执行逻辑，不在root下解释用户脚本。shell使用系统工具和清空后的环境，先复制到root私有目录，再核验复制件SHA。原生程序还检查自身路径、root目录/可执行权限，使用 `openat/O_NOFOLLOW` 和 `fstat` 校验已打开的共享文件。设计参考 [Apple文件竞态指南](https://developer.apple.com/library/archive/documentation/Security/Conceptual/SecureCodingGuide/Articles/RaceConditions.html)、[Apple命令行调用及引用规则](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/CallCommandLineUtilities.html)；本轮仅用 `osacompile` 解析过管理员源码，没有请求认证。

[owner_entry_main.c](owner_entry_main.c) 先发布真正helper的PID与出生时间，等待父监管器通过内核元数据确认UID、出生时间及固定可执行路径后ACK。ACK到达前不调用设备提供者。管理员中继进程存在不等于helper存在；进程元数据临时查询失败不能当作进程退出。PID存在性另用内核查询确认，没有发送进程信号。

原生工作期限在ACK后开始，采用CLOCK_MONOTONIC。看门线程观察原父进程身份及期限，仅设置协作停止标志；不能取消阻塞系统调用。调用在途时不杀进程、不reset、不重新打开，待返回后单次清理。主机函数返回、helper退出、独立缓存驱动关联和相机恢复分别验收，任何单项不代表其余完成。

SDK capture不保证终止MSC驱动。若驱动仍关联，程序在接口claim前终止工作并尝试归还；不能预先宣称接管一定成功。真实调用若卡住，状态保持UNKNOWN，需要保留现场；本方案尚不构成相机救砖保证。

[owner_supervisor.py](owner_supervisor.py) 默认不执行。获本次具体授权并绑定运行包后，才允许 `--run-live`。父监管器退出时，helper看门线程会请求停止；[记录观察器](owner_supervisor.py) 可重新核对原PID身份、实际缺席与结果一致性，但不创建进程、不ACK、不重试，也不把历史文件当当前存活证明。恢复观察结果本身不证明真实驱动功能。

## 实际完成的离线检查

- [12项当前启动检查](hardened-entry-tests.json)：真实复制/哈希核验、自写C fixture、实际PID身份与ACK、跨新文件启动/直接C入口重复拒绝、哈希不符不执行、无ACK零提供者调用、错路径/错机身、期限已过仍保留在途进程、单次清理、元数据观察失败、错误回执及当前真实授权拒绝。
- [5项记录观察检查](recorded-observer-tests.json)：实际在途fixture原PID再核对、出生时间错误拒绝、实际PID缺席与回执一致性分开；故意退出自写fixture的父进程，确认helper仍在、看门线程仅请求停止，释放夹具后单次归还/关闭，没有重启。
- 共9个当前启动fixture任务、1个直接重用反例进程、2个当前观察fixture helper和1个自写孤儿测试父进程；收尾检查未见这些helper继续运行。它们均不链接IOKit，不是原Sony程序或相机模拟器。
- C核心、原生IOKit提供者和目标参数ABI与155逐字节相同，可复用155的37项核心检查；本轮没有把旧检查充作新的实机验收。

`validated-first-launch-build` 保留先前12项通过的构建与结果。`attempt-build-owners-constant` 保留SDK宏名编译失败；公共名字已按本机SDK修正为 `MNT_IGNORE_OWNERSHIP`。`attempt-observer-lambda-order` 保留观察测试条件表达式错误及清理后两个fixture实际终止证据。失败材料未删除。

## 刷入仍未达到的条件

本候选只把下一次低层真机试验做具体。成功也不能证明完整备份、健康恢复与回读、独立救援、目标HEVC主录、音画同步、长录或冷启动。首次持久刷入仍无日期；没有可刷固件，`persistent_write_release=false`、目标保持进行中。
