# AP73 GPE v13 集成观察

首轮80秒`ap73gpe-4dece24a`窗口不足，仅到snapshot1中段，missing_markers含ICRYPT_HAS/GPE_CMD。延长同候选240秒`ap73gpe240-6c2f3137`后：qemu_exit=0、process_reaped=true、宿主PID消失、inputs_unchanged=true、两锁实际重取释放，三个完整snapshot均保留im.elf映射；无symbol lookup error，但missing_markers仍为[FX3_GPE_CMD]。**动态绘制验收未完成。**

独立重跑v13 build_and_test退出0、ASan/UBSan无诊断，共享库SHA256为4e84b5e0fe5a3c2b3b3e2d8dd2a63a26b80c0efacb56dc4b1110ab34f7c61903；仅替换CPIO成员simulation/fx3-gpe-observe-v7.so，原v12未改。guest记录FX3_GPE_BOUND count=5 ... adapter=v13。

| op | 观测数 | fmt | flags | 地址在545内 | result |
|---|---:|---|---|---|---|
| FillRect | 0 | 无样本 | 无样本 | 无样本 | 无样本 |
| BitBlit | 0 | 无样本 | 无样本 | 无样本 | 无样本 |
| Flush | 0 | 无样本 | 无样本 | 无样本 | 无样本 |

AP72同样无uniform fill/flush记录，故未证明v13回归，也未通过原uniform flush无回归验收。无result0绘制，未导出像素PNG或把零内存冒称菜单。运行器现支持v13成功命令触发545物理读回；这两次运行均未触发。静音区QMP读回65536B全零，仅支持静音backing，非原声音。

[完整核验与0x11a后时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap73-review.json)。时间线保留现有trace输出的全部发送记录，但trace有去重/上限，不能作为全局否定证明。进程存活证据限于末次快照，宿主exit0是有界收尾。

032e/033d仍消费释放0；提示音注册推进到0327/40B后等待，四任务屏障未越过。Lead已指示等待adf-beep-regist审计合同后再做AP74；v13暂为观察候选，未声明可操作菜单、绘制/显示、播放或实机验收。
