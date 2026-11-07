# FX6 原厂启动 在线交叉验证

**在固定 FX3 QEMU 平台上，295 尚未证明 Sony FX6 原厂菜单启动，剩余阻塞也尚未绑定到具体接收调用。** 294 的直接故障已有证据：自编 `Backup_read` 把未经验证的 `w2` 当长度清零，随后在 `memset` 崩溃；295 取消该写入后，有限日志未匹配异常，两份采样仍全零。295 没有 293 的 TID225/receive 记录，不能继续沿用“225 卡在 BB 等待”的解释。公开 Sony 源码能核对 UDIF 框架，不能补出私有 OSAL 或 Backup 契约。下一轮应冻结 295 行为，仅增加有界观察及线程生命周期记录，先找到实际 caller/provider，再选择一项修复。宿主画面、无异常、GOT 汇总和离线链接均不构成原生菜单成功。([完成证据](<../research_notes/FX6 原厂启动 在线交叉验证/latest_candidates/evidence.json>))

## 294 暴露错误清零，295 尚无真实等待归属

294 的故障 PC=`libc+0x7a480`、LR=`shim+0x1881c`，落在实际 `Backup_read` 清零调用内，X2=`0x77ffd4e0`。原厂 `libbackup+0x1e14` 保存 `w0/x1` 后覆盖 `w2=-1`，不消费调用者 `w2` 作长度；结合 AAPCS64 的 caller-saved 参数寄存器约定，足以否定该桩的可靠长度假设，**不足以证明精确 C 原型只有两个参数**。295 只将此函数改成不写输出、返回 0，各 Backup ID 的类型、长度和成功语义仍未知。([源码与现场](<../research_notes/FX6 原厂启动 在线交叉验证/latest_candidates.md>))([Arm AAPCS64 2026Q3，2026-11-03](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst))

295=`cp-bind-f56cfd5f` 的 1,571 行串口未匹配 assert/SEGV/Oops；两份 gpe 样本各 2,211,840 B、非零字节均为 0。采样仅记录 217 的 sleep 和 220–222 的 futex，没有 225、实际 LR 或 qid；线程未创建、已退出或未被捕获尚不能区分。GOT 的 `fixed=799` 也只统计赋值：真正选定槽为 `Backup_read +0x2ef22f8`、`Backup_nread +0x2ef2220`、receive `+0x2ef2868`，缺独立读回和 provider 归属。`dlsym(shim_handle, name)` 还会搜索依赖，不能把每个结果都叫作 shim 实现。([本轮复核](<../research_notes/FX6 原厂启动 在线交叉验证/latest_candidates/evidence.json>))([dlsym 维护者手册](https://man7.org/linux/man-pages/man3/dlsym.3.html))

## 原厂地址身份决定能否改变生命周期

下表均为绑定原件的模块相对 VMA；运行时必须取得实际 load bias。先前“普通等待、widget factory、presenter、20 秒等待”的名称应分别纠正为下列身份。([绑定解析](2026-11-07-fx6-queue-contract/queue-contract/README.md))([生产者与屏幕依赖](2026-11-07-fx6-queue-contract/queue-screen-dependency/REPORT.md))

| appFw 位置 | 已证实身份 | 对决策的影响 |
| --- | --- | --- |
| `+0x20efbb8`，返回 LR `+0x20efbbc` | BB finalize 终止请求/回执 | 接收后不检查 rc 就 free、删队列并 join 五个 worker，不能盲改 `-1` 为短超时 |
| `+0xc14dfc` | `adjust::senser` 同步回调注册 | 到达它不证明 widget factory 已执行 |
| `+0x1397450` | 封装 `model_start()` | 不证明 presenter 或 HOME 已打开 |
| `+0xc09e50` | 调用 `App::start_utimer` | NOP 删除真实事件生产链，未删除 sleep |

295 保留五处 NOP，其中 `+0x12d8254` 跳过 70 项 infrastructure 初始化，`+0xc09e50` 移除定时生产者；自报 `mprotect=0` 没有写后指令读回。timer 服务目的 qid=`0x910040`，回调实际向 App 队列 `0x5503e0` 发 `0x02010094`，不能混为 payload、开机完成事件或 App 接收 qid。因此“已删除生产链”是静态事实，“它就是当前唯一根因”仍是推测；九个 ScreenArea 也不能代替原厂模块生命周期、screen/model 到达证据。([NOP 与依赖](<../research_notes/FX6 原厂启动 在线交叉验证/latest_candidates.md>))([原厂生命周期](2026-11-07-fx6-native-lifecycle/README.md))

## Sony 公开包支持 UDIF，不能替代私有 OSAL 契约

2026-11-07 核验的 Sony 型号页是 **FX6 V6.00**，不能写成本机 6.01 donor 对应源码。主包与 `-u` 包分别为 Linux **4.9.337、4.9.186**，两份本地归档的长度及 Content-MD5 与官方 HEAD 一致；`-u` 不是用户态 OSAL。限定扫描 36,058/35,861 个相关文本文件及四个精确符号，未找到目标 OSAL/UIPC 实现。UDIF 仅证明 ioctl 转发、负值打印和自身等待封装，不能解释私有 `-1020/-1021/-1022`、消息所有权或错误后 out-slot。([Sony 型号页](https://oss.sony.net/Products/Linux/B2B/ILME-FX6V_Ver600.html))([主包](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel.tar.gz))([副包](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel-u.tar.gz))([核验记录](<../research_notes/FX6 原厂启动 在线交叉验证/sony_osal/public-source-verification.json>))

本机 FX3 参照归档既不匹配当前官方长度/MD5，也不匹配旧收据的 SHA；**来源尚未重新绑定，不是篡改证据**。即使内核版本相同，构建配置与私有模块 ABI 仍须单独核实。Linux 通用 timeout 和 ioctl 文档不提供把 BB 退出握手改成超时继续的依据。([适用边界](<../research_notes/FX6 原厂启动 在线交叉验证/sony_osal.md>))([Linux ioctl 官方说明](https://www.kernel.org/doc/html/latest/driver-api/ioctl.html))

## 只增观察，先取得 caller、provider 和线程生死

现有[自编接收观察器](2026-11-07-fx6-queue-contract/observer/observe_osal_queue.c) 已真正离线链接为 AArch64 **ET_DYN、5,400 B**，同时启用 `--no-undefined --no-allow-shlib-undefined`，只需 libc/libdl 的 `GLIBC_2.17`。293/295 的 libc、libdl、loader、libosal 四件冷输入逐件相同，故闭包约束适用于指定 295；这不证明 live maps、查找 scope 或拦截命中。冷 app 有 29 个接收 PLT 调用点，观察器只命名其中五个；`RTLD_NEXT` 仅取下一定义，须核最终目标是否为匹配 SHA 的 `libosal+0x6468`。([构建收据](<../research_notes/FX6 原厂启动 在线交叉验证/observability/build-result.json>))([四件闭包比较](<../research_notes/FX6 原厂启动 在线交叉验证/observability/baseline-closure-comparison.json>))([覆盖审计](<../research_notes/FX6 原厂启动 在线交叉验证/observability/interposition-result.json>))([GNU ld 规则](https://sourceware.org/binutils/docs/ld/Options.html))

候选仅存于 ignored work 的[本机共享库](../work/parallel-research-20261107/online-observability/libfx6-queue-observer.so)，SHA-256=`8e7f71167bb1619f933df622d5f41b6cb1b8439a6ea6b5b9d7bed2ac9ff016fc`；未装入 guest、未执行、未改 CPIO。现成代码只观察 receive，**线程创建/退出、Backup 与槽位读回仍是待集成方案**。下一轮冻结 295 的 kernel、init、五处 NOP、Backup 行为、模型环境、顺序和预算，只加诊断；先绑定 run-id、manifest、argv/PID/开始时间、maps 和专属 socket，再核 selected GOT 与 patch 字节。接收前保存 TID、入口 LR、caller DSO+offset、provider、uint32 qid、int32 timeout、out-slot 地址及序号，返回后原样记录 rc/errno；不解引用未确认消息。另关联 creator→child TID→入口→退出原因及已验证参数形状的 Backup ID/返回，输出日志上限与丢样计数。([冻结输入及验收方案](<../research_notes/FX6 原厂启动 在线交叉验证/latest_candidates/observer-plan.json>))

QEMU system gdbstub 的 thread 是 vCPU，不能当 Linux TID，也不能从睡眠后的寄存器反推接收入口。优先在真实 wait 前记录；若 loader 证明确有绕行，再由运行负责人评估 guest GDB/gdbserver。地址读取区分虚拟/物理，重定位槽按 load bias 加 VMA；QEMU master 是滚动说明，不证明本机 patched 版本。诊断有时序成本，不能据此声称性能改善。([QEMU 官方调试](https://www.qemu.org/docs/master/system/gdb.html))([ELF gABI 重定位](https://gabi.xinuos.com/elf/06-reloc.html))

## 结论：下一项修复应由观察结果选择

若命中 finalize LR，应追终止请求、ack 与队列销毁；若命中 App 事件接收，应查生产者；若没有 ENTER，应先区分线程未进入、已退出、装载/查找绕行和日志缺失。**观察完整、原厂生命周期到达、菜单可见/交互必须分别判定**：最终需同一 run 的原厂 screen/model、guest 原始帧及原生按键响应闭环，全零帧继续保留“菜单未证明”。本轮没有启动或控制 VM、调试端口或相机，也没有变更运行输入。([证据分流与判据](<../research_notes/FX6 原厂启动 在线交叉验证/latest_candidates/observer-plan.json>))

资料访问日期均为 **2026-11-07**；AAPCS64 main 当日为 2026Q3（2026-11-03），观察器审计另引用固定 2025Q1（2025-04-07），两者只用于相应 ABI 论证。Sony 包 URL 日期和 Blob 修改时间不作固件发布日期；完整来源与不确定项保留于[三份研究笔记](<../research_notes/FX6 原厂启动 在线交叉验证/sony_osal.md>)、[观察核验](<../research_notes/FX6 原厂启动 在线交叉验证/observability.md>)、[294/295 复核](<../research_notes/FX6 原厂启动 在线交叉验证/latest_candidates.md>)，交付指纹见[索引](<../research_notes/FX6 原厂启动 在线交叉验证/index/DELIVERY-FILES.json>)。
