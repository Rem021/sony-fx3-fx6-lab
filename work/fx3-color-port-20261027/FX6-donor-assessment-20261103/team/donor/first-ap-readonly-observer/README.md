# FX6 AP 首断言与 MPR Init：冻结平台的只读观察索引

**当前结果：第四次零键运行已捕获 CAPID model/owner=0 与 AP 同调用 `w0=-1021`，见 [第四轮回执](RUN-FOURTH-OBSERVATION.md)；随后 MPR 专项窗口捕获 FX6 AP 调用固定 FX3 MPR 返回 `w0=3`，见 [MPR 实测](mpr-init-candidate/RUN-OBSERVATION.md)。** 首轮错过早期映射，见 [`RUN-OBSERVATION.md`](RUN-OBSERVATION.md)；第二轮按动态 CAP 映射安装 `Z1`，但旧协议未回传 T05，见 [`RUN-SECOND-OBSERVATION.md`](RUN-SECOND-OBSERVATION.md)。后续有界 GDB `c` 和严格 `T05thread` 解析已在第三、四轮逐项验证；所有历史目录保持不动，授权窗口均已消耗。

下述“两阶段/最多两个断点”合同仅描述 CAPID/AP 首断言观察器；MPR 专项是另一个已完成的单轮合同，以其自己的 README、原始 run 和收尾回执为准。

## 冻结平台与源码

[`audit.py`](audit.py) 调既有 `run_ap_once.verify()`，核外盘 UUID、固定三入口 CPIO 的 1140 成员、仅 `bootin.elf`/`im.elf`/`appFw.so` 三项身份例外，以及 Image、DTB、QEMU、17 helpers 与环境的 SHA；还重读原 ELF `PT_LOAD`、指令 VA/文件偏移和机器字。两轮各自源码 SHA 与快照留在 run 目录；当前两阶段源码 SHA 与依赖见 [`audit.json`](audit.json) 和 [`host-tests.json`](host-tests.json)。固定 CPIO SHA `bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02`。冻结 34 项 QEMU argv 只改索引 20 为新私有串口、索引 31 为同一 CPIO 的绝对路径；QMP `unix:q`、GDB `g`、四 vCPU、virt 机型与全部模型环境保持原值。双锁拒绝占用，零键、观察上限 120 秒、总上限 180 秒、最多两个已识别断点；只回收自身 QEMU 与日志。

## 两阶段身份合同

第一阶段从固定 `/init` 真正输出的完整 `FX3_AP_EARLY_MAPS_<PID>_<轮>` 快照取得 CAPID VA：同 PID、`im.elf` 进程映射、CAPID 同 inode 全部 `PT_LOAD` 的页对齐 `p_vaddr` 与 `p_offset` 必须吻合。首轮 PID237 的前五轮 CAPID bias 均为 `0x7f816d4000`，第二轮新算 `0x7f973f0000`；两者均是**已消费 run 的地址，不能用于未来 run**。AP 当时尚无 VMA；`start-fileoff` 对旧 AP 第二段会错 `0x10000`。阶段一只允许对 CAPID `audio_dispatch` VA `0x1e730` 设 `Z1`，此时不读模型、不称 AP 身份已证。

第二阶段实际断点命中后要求 `T05thread`、当前 CPU 的 CAPID PC/原指令、精确 10B 请求与本轮同 TID/TLS/动态源 QID；CAPID helper 对该请求打印的完整 `dladdr` 栈须有至少两帧同一 AP 基址，且其 `caller` 等于该基址加原 AP 返回 VA `0x20ef7a0`。然后在**当前停住的 vCPU 地址空间**逐字验证 CAPID 和固定 FX6 AP 的 ELF64 AArch64 头、完整 PHDR、两镜像各四处原机器字；AP 的 `/proc` VMA 在早期快照中不可得，后置读回是独立身份门，绝不填历史 ASLR。最多 16 节点有界 frame-pointer 链还须出现保存 LR 指向该 AP 返回 VA 的帧，并与返回时 AP frame 一致。全部通过后才读取 CAPID `model+0x18`（VA `0x45bc0`）和 owner（VA `0x45b08`），先设 AP 返回 `Z1` 再删 CAP `z1`，继续校验同 TLS、帧、请求指针/原字节后读取 `w0` 与 `cbz` 分支。错 PID/base/ELF/PHDR/原字/TLS/帧链、无完整 profile 或未知 CPU 停顿，一律停止为 unknown。

本地 QEMU 11.1.2 TCG `accel/tcg/tcg-accel-ops.c` SHA `79a918ac…` 把 `GDB_BREAKPOINT_HW` 交 `cpu_breakpoint_insert(...,BP_GDB)`，不覆写客体代码；`gdbstub/system.c` SHA `196af474…` 的实际运行停顿包含 `thread:`。官方 [QEMU GDB 文档](https://www.qemu.org/docs/master/system/gdb.html)也说明 TCG 系统仿真的硬件辅助断点及多 CPU 调试限制。RSP 仅允许物理/虚拟模式切换、CPU 选择、只读寄存器/内存/XML、`Z1/z1`；禁 `Z0`、软件单步、写原寄存器/数据/指令和额外 keepalive。

## 收尾与复核

QMP 暂停全部 CPU 后增删断点，命中需与 QMP `debug` 一致。正常收尾先 QMP stop、逐个 `z1`、断开观察连接，再沿固定 runner 的既有软件 observer 8B shutdown 请求恢复原 API16 16B，并核 ack、原字、QEMU exit/reap、双锁 free。**8B 仅为既有软件观察器清理控制**，不写原代码；若任何断点未确认移除，保留残余集合、保持暂停、仅退出自己的 QEMU，明确 `API16_restored=false`，绝不带残余断点恢复执行。

历史主机门：`test_host.py` 的 [`host-tests.json`](host-tests.json)、`audit.py` 的 [`audit.json`](audit.json)、`mapping_failure_audit.py` 的 [`mapping-failure-audit.json`](mapping-failure-audit.json) 与第二轮 [`rsp-stop-audit.json`](rsp-stop-audit.json) 均保留原阶段标签；它们不能替代第四轮和 MPR 专项的实际 CPU 回执。MPR 后的 host-only 回调/载荷复核见 [callback-adapter-review](mpr-init-candidate/callback-adapter-review/README.md)。本阶段无未消耗的 VM 授权，不重跑；已捕获的 `w0` 只是 CPU/软件观察，不代表 CAPID 服务、HDMI、CP、菜单或 FX6 完整系统启动。
