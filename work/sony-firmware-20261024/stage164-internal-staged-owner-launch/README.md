# FX3 内置盘预复制的单次接管候选

2026-10-28。**修正版已编译并通过28项当前本地检查；真实管理员启动及USB接管未执行。** 163轮实际失败发生于管理员install无法读取外置盘程序，具体macOS权限政策未证。01号原记录与占用凭据保留；本候选02号需要新的单次确认。

## 具体改动与已验证范围

用户进程先从固定运行包读取精确SHA的程序，用O_EXCL/O_NOFOLLOW在内置盘0700私有目录创建0500副本；管理员命令只从该内置副本复制到root私有目录，复制后再次核对精确SHA。中继cwd固定为/，bootstrap也先cd /。共享文件、父ACK、PID/UID/出生时间/固定路径检查、独立入口租约、无强杀/reset/重试规则保留。10项设备核心/原生入口/ABI源码与156逐字节一致，仅重新绑定新编号及目录。

[11项预复制检查](internal-stage-tests.json) 实测私有目录、哈希、拒绝覆盖/符号链接/宽权限；将测试用外置源改名后，实际非IOKit fixture仍从内置副本启动，内核进程路径及lsof工作目录均核对，父ACK与终止回执成立。[12项启动检查](hardened-entry-tests.json) 与[5项观察检查](recorded-observer-tests.json) 通过；已逐一核对9个有验证记录的fixture PID不再存在。所有测试均为用户态自写fixture，无管理员提示、root执行、IOKit原生helper运行或相机操作。

/private/tmp对应的已有挂载为内置APFS Data卷且所有者检查启用。一次以任意目录直接查询diskutil不适用，失败记录保留，随后通过既有挂载映射查询卷元数据；没有探查root目录或相机。

安全文件创建和shell引用参考[Apple安全文件操作](https://developer.apple.com/library/archive/documentation/Security/Conceptual/SecureCodingGuide/Articles/RaceConditions.html)及[Apple命令行调用说明](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/CallCommandLineUtilities.html)。这些文档不证明本机管理员访问必然成功，也不证明相机兼容性。

## 下一次试验的完整范围

[候选方案](candidate-plan.json) · [固定运行包](release-bundle.json) · [源码/运行限制复核](local-source-and-runtime-review.json)。目标仍为经典ILME-FX3、用户确认7.02，054C:0DA1、location0x02100000。

- 编号：fx3-702-msc-owner-20261028-02。
- 运行包SHA-256：e36a8777d113300bf32cc5dd0721e69836bc7eea97648a01e0ce1b8b78b5d183。
- 原生helper SHA-256：1182295ad4405fc30773673467ae2d6b1bb8b3ca26343a6e02c76a1dc9fd9e0b。
- 用户目录：/private/tmp/fx3-702-msc-owner-20261028-02/；内置source-helper为0500，目录0700、共享帧0600。
- root目录：/private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-02/；目录0700、helper为root/0500。

先由用户手动推出FX3所有卷，保持开机、USB连接、MSC，再核对缓存唯一身份及卷无挂载。获得本构建单次确认后，只执行一次USB接管与归还；可能短暂断开MSC，管理员原生验证由用户完成。不新增完全磁盘访问、驱动或常驻服务；不进行Sony认证/服务、不读卡或机身文件、不上传模块、不读写WBI/设置/固件，不自动卸载、reset、强杀或重试。任何启动失败也占用本编号，未知保留UNKNOWN。

此前授权仅批准01一次且已提交，本次02目前authorized=false、released=false；旧授权不会继承到02。默认CLI实测只输出PLAN_ONLY。真实root读取内置副本、IOKit接管/归还及相机功能仍待验证。

这不是可刷固件。目标MAIN 1080/29.97 HEVC42010约16Mbps、完整健康备份/恢复回读、独立救援、长录/冷启动/音画同步要求不变；持久刷写继续关闭。
