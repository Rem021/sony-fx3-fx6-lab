# 恢复候选实施前精确缺失项（未实施）

1. 沿实际 `usr/lib/libObj.so` 的 native resource open（现有 hook offset0x1031b0）到原 `usr/kmod/dmm.ko` 对应申请/导入/别名/显式物理区域路径，说明产生 type403/state10/phys/bytes 的每个入口及所有边界；必须能证明 UI64KiB 保留区不会成为该 GPE native-open 可写 parent。需要实际成员 SHA、原 kernel memrsv 处理与 DMM extent/resource 管理的对应证据；仅 `/proc/cmdline` 字符串、当前四个注册地址、或“memrsv大概排除allocator”不足。已有 CPIO 带这些成员，不需要先开 VM，下一步可以只读反汇编补证明。若发现原ABI允许显式映射 observer reserve，则须协调员决定独立隔离方案；本任务不能擅改GPE、DMM、硬件预留或放宽门禁。
2. 全 writer 排除闭合后，才设计跨模块普通BSS collector：process PID + 模块装入epoch + UI初始化状态，early pending与unknown区分；证明无UC原子、无独立initializer、无晚清零损失，最多一个exporter。宿主run/launch绑定沿用已有run目录/command/paused-readback身份，不把PID当全局运行ID。最早publication先于UI就绪时要保留“尚无可核验导出”而非0次。
3. 根据原4个剩余probe槽选择缩减观测。producer原STR前意向、已越过STR、alloc返回、send进入/返回和consumer推进要逐项列可证/不可证；不增加未证明的尾调用包装或ABI猜测。消息地址与alloc观察代数/有限寿命绑定，丢失/乱序/地址复用都可unknown，绝不计数回滚/丢合并消息。
4. 上述两类准入补齐后，才实施和测量每hook≤1clock、≤4atomic64（普通RAM）/1bounded-tryclaim、≤2KiB额外export。可完全不加clock/I/O而保留时间样本缺口，不能把host基准称guest零扰动。需要完整publication/delegate/bind失败分支、未初始化、跨进程/root、复用/漏序/并发drop/覆盖/回绕、截断/跨chunk/End等候选测试、实际交叉编译、源码与固定成员绑定，再提交运行前审查。

本交付没有请求或授权 VM。没有最小行为修复建议，没有增加Start、键、180秒/20秒预算，也不改变r30 ready/PAGE/pin/confirm/recovery/退出流程或FX6 provider对照。
