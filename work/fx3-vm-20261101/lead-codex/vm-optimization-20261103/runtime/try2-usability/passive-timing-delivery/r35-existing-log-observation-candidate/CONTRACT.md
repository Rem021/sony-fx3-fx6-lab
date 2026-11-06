# r35 普通 BSS 与原日志出口合同

状态：隔离离线候选；尚未集成到 N64/runner，不是运行准入或根因修复。原任务的“热路径零新增 syscall”已由协调端 msg_46c6a32261e9 精确修订为仅允许实时 getpid/TGID，见 COORDINATOR-REVISION.txt；不存在其他 I/O、映射、VM 或硬件授权。

## 来源与身份

- 原 OSD r3 源 → 原参数重编 `.text` → 冻结 ELF → N64 实际 CPIO 成员完全一致；UI r15 N64 同样逐段一致。见 ACTUAL-BINDING.json、BASELINE-REBUILD.json。
- CPIO init 的唯一 bootin launch 行同时 preload OSD 与 UI；四轮 startup 截止前的同一 im PID maps 中均有两个成员，且各仅一条 UI_GATE_BOUND。历史事实不保证未来日志调度。
- 每个新记录入口先执行实际 syscall(172)，再 acquire 读取初始化 owner；只有相同且非零 TGID 才可触碰记录、loss、claim 锁。snapshot 的外来 TGID 返回 3、保持 out 不变；UI 外来 TGID 输出空后缀且不改预算。token=0 的完成入口直接无操作。
- 同 TGID 多线程可竞争；raw fork/clone/vfork 复制的缓存 PID 不再是许可。CLONE_VM 共享 BSS 的不同 TGID 在宿主身份注入模型中全部拒绝，parent BSS 不变；另有真实宿主 fork 与 pthread 测试。未执行目标 AArch64 raw clone/vfork。
- 实时查询已替代先前草稿 atfork 注册；最终 ELF 不依赖新 `__register_atfork`，不把 libc fork 回调当身份安全依据。早期 owner=0 的入口不写状态；因此只能说 collector 初始化之后的首次捕获，初始化之前始终 unknown。
- 原 bind_ram 的全局 O_EXCL claim 成功发生在任何 probe install 之前。后续模块、新 exec、重载入口均不能再次成功安装；失败时没有第二条可产生日志的 probe 路径。即使首次安装中途失败，也只有已经取得该 claim 的一个实例可有部分 hook。原 claim 的保存、原 active preload 和原未卸载 hook 生命周期必须维持；不授权 unlink、reset、替换映射或手动调用 hidden callback。
- UI constructor 与 OSD constructor 均不在 owner 已提交后重置身份/记录/额度。UI 仅在初始化阶段 dlsym 一次；未解析不重试，输出 exporter-unbound。snapshot 校验 ABI、source ID、同 PID、非零 collector init instance；失败 unknown。
- wire PID、OSD CLOCK_MONOTONIC(1) 初始化值和 UI CLOCK_BOOTTIME(7) 初始化值是模块实例字段，不能相互相减或单独当全局 runID。离线 CLI 必须另给单一 host run ID、完整 serial SHA、原 End 字节截止；不合并多 run。

接口语义参考 Linux man-pages 的 [getpid(2)](https://man7.org/linux/man-pages/man2/getpid.2.html) 与 [gettid(2)](https://man7.org/linux/man-pages/man2/gettid.2.html)：TGID 与线程 TID 不同。这里同时绑定了实际 CPIO-identical libc `syscall` 的 `w0→w8; svc #0` 和固定 Image syscall table 的 172→sys_getpid、178→sys_gettid，不能仅用文档替代目标证据。

## 捕获范围与原语义

`src/r35-collector.inc` 只用普通 BSS。两个 first-captured 记录独立：publication phase 0/1/2、bind phase 0/1/2。phase 0 是截至该次快照未捕获，不能推出固件从未发生。

publication 仅复用原发送前 `copy[96]` 和原 `qo_publication` schema：启用 watch、原 source 0x8288076c、CONTROL 0x8280074d、12B、头 0x1002/其余前缀零、op 0x1003/0x1005。原 hsend 调用仍一次；原 rc/errno 先保存再记账；交接后不再读原消息。hsend 不存在的原早退没有 delegate attempt 记录。失配消息不新增 native 查询。

bind 在原 observer_ready 早退之后记录 entry；原 claim 失败 -1、cmdline 失败 -2、self mem 失败 -3、devmem/mmap 失败 -4 和原成功分支逐一记录。map 0=未到映射阶段，1=devmem open 失败，2=mmap 失败，3=mmap 原成功。成功 magic 字段是 owner/try-claim 后对原 ring 头的**一次 volatile 实际 load**，不是写入常量或 End 状态，亦不保证之后保持。

首次 bind 与首次 publication 不做未证的因果配对，尤其原 non-owner observe 允许 PIXELS/META 先触发 bind。没有消息地址身份字段，不会把同地址复用当同一消息。并发/递归若 claim 失败，普通 BSS 单调 loss=1；end 丢失可留下 phase1、原返回 unknown。记录只覆盖一次捕获，不能代表所有事件或 earliest 全序。loss 存在时最早事件归属也 unknown。

原 probe assembly、60 条 offsets/words/regs、native alloc/send/consume、原锁、hsend/hwait/hsignal、所有原失败处理和 errno 恢复不变。probe 机器指令除指向同名 C 函数的 BL 重定位外一致，保留原 GPR/SIMD/NZCV/FPCR/FPSR/SP 保存恢复；未执行 guest selftest。普通 C wrapper 保持 AAPCS 调用/返回及相同 native delegate，不宣称重编 ELF 的代码地址、LR 数值或 C 私有栈大小逐字节相同。新调用不插入 native appFw 的 trampoline、不增加 app probe，不改变原尾调用点。

## 输出与预算

只在原 `n<=50 || n%1000==0` 的 UI_GATE_SAMPLE 分支中追加 `%s`；原字段/值/顺序、原 now/gettid、单个原 dprintf 调用及其所在位置保留。没有额外日志调用、强制兜底或每消息输出。

后缀固定 ` r35v1=` + 22 个 8 位十六进制无符号 word + `;`，共 **184B**（不增加换行）。七个单调 obligation 位：首次 unknown、ready-empty、pub-entry、pub-return、bind-entry、bind-return、首次 loss。任何新位均可输出；一个快照同时覆盖所有已到达位，phase2 也覆盖 phase1。双方前进互不遮蔽，六种交错全部覆盖。每次输出至少消耗一个新位，故至多七条/**1288B 整轮上界**，严格小于 2048B。前置 unknown/empty 至多两条，不会吃掉后续四阶段和 loss 的份额。第七条带 budget-terminal 标志；后续不输出，但当前实现仍核 PID/快照，成本不隐去。

这个整轮上界依赖上面的实际唯一安装实例与原 claim 生命周期，不是将每模块上界直接改名。不同 TGID 不能消费或重置 parent 额度；新 exec/额外模块因原 claim 不获得第二个日志生产 hook。未授权的 claim 删除或 active module 卸载不在候选运行合同内，也没有替代保护。

word：0 ABI=0x35010058；1 source=0x52333501；2 collector PID；3 ready；4/5 collector init；6 pub phase；7 pub op；8 原 send rc（二补码）；9 bind phase；10 原 bind rc；11 map stage；12/13 实际 magic；14 loss；15 UI PID；16/17 UI init；18 ordinal；19 已分配后缀字节；20 status(1=coherent,2=unbound,3=unready,4=contended,5=identity-rejected)及 bit7 terminal；21 前21word按小端字节的 FNV32。FNV 只检测有限损坏，**不是密码学来源证明**；hash/source映射由本交付冻结。

UI formatter try-claim 争用可以整条不导出，不能增加 I/O 补发；若以后没有原日志机会，则无法再解释该瞬间的具体原因。snapshot 争用可在已有选中出口产生 status4。缺后缀、首 token、某一完整后缀和实际 End 状态是不同层次的证据。

## 解析与未验项

`parse_r35.py` 独立离线，不接 runtime/ready。接受完整原格式及 LF/CRLF，校验版本/source/范围/摘要/身份、ordinal 与单调阶段；阶段回退、覆盖首记录、乱序/重复、身份变更、坏 magic 均 unknown。允许 chunk 分割，绝不跨 End 拼接；>16384B 部分坏行丢弃到其换行，完整超长行也拒绝，后续新行可继续。无输出是 no_complete_export_unknown。budget-terminal、capture-loss、未完成 rc 和原失败分开报告。每条结果只截至该原日志点，不是 End 原子快照。

已有 opportunities 精确字段解析器会拒绝有后缀的那几条，不能直接沿用它宣称 r35 全量记录。实际 r32 GATE 是前缀正则，它仍捕获相同原字段；不是所有旧解析器都拒绝。r30 KEEP/FAILURES/MARKERS 在实际选中日志夹具上结果相同，原 consumer 源未改。新增字节会改变 serial offsets、占用原 byte limit，并可能扰动调度；不宣称运行时轨迹完全等价。

所有 native、physical mmap/claim cmdline fixture 为 mock；真实宿主 O_EXCL/fork/线程与目标 guest 验收分开。当前两个 debug 构建超原 slot，尚需独立 release 打包、两成员差分及固定 runner 绑定。未 VM、未部署，未证原启动/菜单通过；UI7000–77ff仍未存储准入，r33 failed 与 r34 unknown 不变。
