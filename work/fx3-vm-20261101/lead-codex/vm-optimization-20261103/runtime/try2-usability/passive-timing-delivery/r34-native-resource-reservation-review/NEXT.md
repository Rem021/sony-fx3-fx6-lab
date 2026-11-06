# 总判unknown所需的最小补证

1. **固定DmmCfg的545成功leaf归属，仅这一条相关链。** 以本轮实际dmm.ko为准，闭合unit403→extent545（两条rule均parent34）→`dmm_ext_ctrl_AllocExtent/textb5f0`→`textab08–b318`的成功返回与重用/child/split/合并支路，证明传给`dmm_unit_ctrl_Open`的node `+8/+10/+14`必保留root34祖先、正向范围及无回绕；或给出原始指令支持的反例。重点缺口是`af38`递归返回后、`adc8/ae34`既有node重用、`b054/b130`child/split写与合并的字段不变量，不是再查一遍root表或延长超时。已有完整相关反汇编，可以继续只读静态分析；无须先开VM、写helper或穷举其他固件功能。
2. **显式物理ABI若要称“实际writer”，补当前启动关联。** 已证`libObj1032f4`本地参数门允许UI、MA3不经DMM，但未证本轮原固件callsite真的传入UI，也未证该路径取得当前GPE的native_open登记。仅在结论需要把它算作当前writer时，补窄范围callsite/参数来源或既有原始记录；不能用r33合成resource、源码默认debug值、地址相等或四轮无重叠日志补空。没有这些数据就保留unknown，不主动扩成全固件显式映射/安全研究。

在上述结论经过协调端评审前，r33仍failed，7000–77ff仍无存储准入。本任务不设计或实现BSS collector，不改变GPE/DMM/DTB/内存预留、任何门、180秒/20秒或原退出政策；任何运行另行授权。
