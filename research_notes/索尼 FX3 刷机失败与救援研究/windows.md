# Windows 11 x64 补充核查

日期：2026-10-25。用户确认另有 Windows 11、Intel／AMD 电脑。此为用户提供的主机条件，不是远程盘点；Windows 的驱动、软件和已连接相机尚未读取。此前 environment.md 是 Mac 的实际盘点快照，其他硬件未确认不应解释为用户没有。

## 主机兼容性与机型兼容性分开

A7C2Tools v3.0.3 发布说明明确提供 Windows 10／11 x64 包；固定 main `b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d` 文档仍限定 ILCE-7CM2 2.01。Windows 11 Intel／AMD 满足这一主机要求，不等于 FX3 被该工具支持。

- [正式发布包及系统要求](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)
- [固定版支持范围及Windows双身份驱动流程](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/README.zh-CN.md)

主线文档区分普通 A7C II 的 `054C:0E8A` 和认证后的 `054C:0336`，并有只读稳定性测试。不得先假设 FX3 普通 PID 也为 0E8A，或将未知 0D68 认作可用服务。文档中的自动驱动安装会改变 Windows 驱动绑定并切换相机服务，和只读 PnP 查询不同。本轮没有执行这些操作。

## 两类恢复目标

`src/desktopapp/recovery.py` 的 restore_auto 选择同机身完整检查点；缺少检查点时拒绝。另一路原厂功能恢复使用内建区域参考，不能沿用“所有恢复都必须旧检查点”的概括。对应清单 schema 为 `a7c2-factory-regions/1`，model 为 ILCE-7CM2，version 为 2.01，scope 明确只含项目支持程序区域及 FL23 色彩单元子区，不含全固件或机身校准。这是范围核查，未执行其恢复代码或验证实机效果。

- [同机检查点选择与恢复](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/desktopapp/recovery.py)
- [内建原厂参考范围](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/assets/factory-regions-2.01.json)
- [恢复临时事务保护](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/factoryrecover.py)

这些机制是 FX3 适配参考，不是可直接在 FX3 运行的恢复器。一般 PMCA 的 service 模式同样要求匹配 USB 驱动；其旧 updater 注入路径不支持 CXD90057，不能因 Windows 可运行就套用旧 updater shell。[PMCA 原始说明](https://github.com/ma1co/Sony-PMCA-RE/blob/master/README.md)

## 官方更新器与只读识别

Sony 旧 FX3 Windows USB 过渡更新器支持 Windows 10／11、Intel／AMD，拒绝 ARM；适用旧机身版本，2.04 及以上应走最新卡更新。当前用户自述最新 FX3 不应据此尝试旧更新器救砖。[Sony 官方适用范围](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00280265)

当前可先做 Windows PnP 只读身份观察，命令见正式报告；Get-PnpDevice 用于返回 PnP 信息，PresentOnly 只选当前设备。查询不打开 Sony 服务接口，不执行安装器，不输出完整实例ID。空结果只表示这次未列出匹配设备，不证明相机无法恢复。[Microsoft 文档](https://learn.microsoft.com/en-us/powershell/module/pnpdevice/get-pnpdevice)

源码均只在内存中读取、解析，未保留第三方源文件，未执行其函数。URL、提交号、长度与SHA256保存在[来源回执](../../work/sony-firmware-20261024/stage3-recovery/windows/source-review-receipt.json)。本轮只完成资料和本地报告更新，未接管用户 Windows、安装驱动、认证相机或刷写。
