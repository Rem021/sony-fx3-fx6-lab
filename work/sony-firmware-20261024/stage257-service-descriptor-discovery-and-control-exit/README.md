# FX3 SERVICE描述符识别与控制退出分支

2026年10月31日。补齐了上一阶段的SERVICE配置发现与不匹配分支，原生候选编译和五组有针对性的离线检查完成；没有运行管理员程序或实际USB后端，没有发送Sony命令。

[描述符策略](descriptor_policy.c)只支持单配置、单个vendor接口、alt0、2或4个唯一bulk端点及512B包长。最多保存128B配置；从实际描述符顺序选择首个IN/OUT，再核对IOKit接口和管道，未填写猜测端点，未改配置或alternate setting。

[原生发现](iokit_adapter.c)先核对新SERVICE节点的同机HMAC标签，再访问设备对象。符合策略才继续固定通信；不匹配时不发送SERVICE START、认证或读取，改走一次独立控制STOP，然后观察MSC。API失败或超时保留UNKNOWN，不以策略不匹配掩盖调用错误。[控制退出原码检查](control-exit-source-review.json)只支持将其列为试验候选：没有证明真机在未START时一定可退出，也没有证明线程完成或能救砖。

[验证回执](discovery-test-receipt.json)覆盖原生解析器的截断与变异、匹配分支、不匹配分支、SERVICE失败及认证中途停止。完整人工分支收到80帧，不匹配分支44帧且没有SERVICE认证/读取；失败保留原实例。实际运行的是普通用户自写子进程和人工USB回调，不能充作相机模拟成功。[静态检查](analysis-receipt.json)六个单元无诊断。新协议为schema5/SVC3、FX3FLOW2和FX3RCPT3；原12号授权未复用。

[Mac缓存](current-host-storage-cache.json)曾看到经典FX3在0x01100000、MSC驱动和一个挂载卷。查询只读系统缓存与挂载表，没有打开设备或媒体；缓存有时效性，不是新鲜上机前置，也不证明机身健康。没有推出卷。

下一步是固定新目标、nonce、隐私材料和单次许可，形成完整Sony通信诊断包。目前native入口与渲染仍关闭。用户新增“持续研究，不要停止，我全部同意”的整体继续授权已记录；不复用任何消耗过的单次许可。首次诊断应明示认证可能更新历史、模式及机内文件，不能称为零写入或单纯USB查询。固件写入仍未放行。

真实SERVICE端点、跨模式身份连续性、认证接受、机内线程退出与恢复仍未验证。完整同机备份、独立恢复、MAIN1080p H.265及持久化准入也未完成。全部G01至G16保持，[实施路线](../../../outputs/fx3-recovery-adapter/ROADMAP.md)仍处于第2项。

[差异](source-changes.diff) · [构建](build-receipt.json) · [准入结论](admission-decision.json)。公开参考为[固定PMCA维护者源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L890)与[Apple IOUSBLib](https://github.com/apple-oss-distributions/IOUSBFamily/blob/main/IOUSBFamily/Headers/IOUSBLib.h)。公开实现不等于FX3 7.02实机兼容。
