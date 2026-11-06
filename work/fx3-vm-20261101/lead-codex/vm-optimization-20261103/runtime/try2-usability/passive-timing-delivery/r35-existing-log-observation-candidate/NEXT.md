# 后续范围（未授权在本轮执行）

1. 独立release包装：原slot UI58856B/OSD109000B，当前调试UI72656B/OSD119544B；只验证必要release ELF的可装入性和源/ABI/字节差异。不得扩硬件、改DTB/QEMU/kernel或重打完整runtime凑空间。
2. 固定runner依赖审查：当前r30仍固定原N64 manifest；未来只能经审查绑定两成员候选与host run/唯一claim/hook合同，不把本轮交叉编译视作可直接启动。
3. 另行授权VM时才观察实际pub/send/bind状态和日志机会；原180秒/20秒及所有输入门/pin/confirm/recovery/End策略保持。当前原故障轮、r33 failed、r34 unknown和所有历史菜单失败不改判。

未闭合项：guest调度/日志额外字节/实时getpid造成的时序影响；原事件后可能无选中UI日志；UI export争用可能没有后续导出；初始化之前、丢失/截断/身份不明或End末尾仍unknown。该first-captured诊断不包含所有事件或全阶段生产消费关联，也不提供FX6可运行结论。
