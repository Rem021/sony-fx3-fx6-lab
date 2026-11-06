# FX3物理端口关联诊断01执行记录

2026年11月1日UTC。**这次已执行真实MSC通信，但停在SERVICE切换等待后的HELD状态，正常退出尚未完成。** 用户已完成原生验证，无需再次验证。原helper与观察器保留；没有固件上传或刷写，不启动新诊断。

已验证root helper PID85066的内核身份和自身映像，原观察器PID82324继续观察同一次试验。MSC七次OUT/IN交换均返回，旧USB对象已释放。限定2秒/20次窗口内未找到SERVICE，程序进入OWNER_RETAINED；稍后独立缓存看到同一物理锚点上的054C:0336。没有SERVICE认证、88字节读取或STOP；不能把节点出现计为完整认证和退出通过。

## 新的屏幕观察

用户报告“现在显示拍摄界面”。同轮UID501的IORegistry缓存仍显示原SERVICE节点054C:0336/4295926235，只有USB接口相关类别，未见MSC存储驱动。因此屏幕恢复是单独的积极迹象，不能等同于MSC归还或冷启动/拍摄健康已通过。[屏幕与缓存记录](screen-shooting-ui-and-still-SERVICE-cache.json)。已询问存储卡访问灯及有无更新/保存提示；尚待反馈，不立即拔线、抽电池或发新命令。

## 当前优先项

先取得用户对FX3屏幕及存储卡访问灯的只观察反馈，再审查一次具体的普通模式恢复动作。当前保持连接，不重试、不强杀、不重置、不绕过软件锁。程序的HELD分支没有协作退出；持续等待不会自行完成退出。实现中的2秒窗口也比固定上游约5秒短，这两个缺陷已记录，当前不修改原进程或封存包。

- [本次故障、实现缺陷与恢复路线](recovery-review.md)
- [实际诊断摘要](held-diagnosis.json) · [原始56帧及回执索引](held-evidence/snapshot-manifest.json)
- [后见SERVICE的缓存证据](later-service-port-cache.json) · [运行边界复核](held-runtime-review.json)
- [固定261包及副作用范围](../stage261-fixed-port-association-diagnostic01/README.md)

批准包SHA256：`8a4cde7317b8cd747113f366bcedbc236a56ae5a3a6e890e7e4ccacb5522de69`；实际helper映像SHA256：`677866f6ff8bb06bd0cfb0d5ec78343943088400eb3063513fadf5a23abdbc58`。单次标记已消耗，不再调用工厂或重新提交。

## 历史与验收边界

[06:41尚未进入helper的历史页面](README-pending-entry-historical.md)和[当时快照](pending-entry-observation.json)保留；它们不再代表当前状态。[暂存回执](staging-receipt.json)只证明启动前检查，不代替真实执行记录。

本目录仍为运行中的执行账本，未封为正常完成。完整同机备份、独立恢复、MAIN H.265目标与首刷门槛均未通过。原始回执、主机程序退出、缓存/驱动、屏幕、正常拍摄仍需分别核对。

## 正常关机恢复的第一步

用户补充确认访问灯已熄灭、没有更新/保存提示。已安排一次手动将机身电源拨OFF、保持USB连接，约10秒后反馈屏幕/访问灯；尚未收到执行结果。不取电池、不反复切电，不启动主机新USB操作。[具体范围与判定](manual-normal-OFF-step.json)。屏幕熄灭不单独证明USB或固件已恢复。

## OFF后的新缓存与待澄清灯态

用户选择“出现报错或访问灯亮起／闪烁”，该合并选项尚未确定有实际报错。普通用户缓存已不见0336，转为同逻辑位置054C:0D68、USB Bus-powered Device，原root和观察器仍在。可能是关机后的USB充电；已核对Sony说明并询问橙色充电灯/红色访问灯、屏幕和原文。当前保持OFF和连接，不追加断电、重试或Sony命令。[新缓存与推断边界](normal-OFF-new-USB-power-node.json)。

## 机身物理断开与基本操作恢复

先前仅菜单正常的答复未确认实际拔线，后续用户明确说明仍接USB；因此不把那次回答计为独立开机。再次操作后，用户已明确确认“已拔下相机侧USB-C，界面和菜单仍正常”。此处只关闭机身侧物理断开/电池界面菜单的观察项；录制未测，原主机helper/观察器仍保留，试验仍为HELD。[用户观察记录](user-physical-disconnect-and-menu-normal.json)。

## 经批准的主机强制清理已完成

265单次例外已执行，旧helper及观察器均已确认不存在，原观察会话结束；原journal不变，历史HELD和全部回执保留。相机未连接/未访问。此后无需再轮询原会话，也不能重建旧活连接或改判正常归还。[实际主机清理](../stage265-retained-host-cleanup-plan/runs/execution01/README.md)。
