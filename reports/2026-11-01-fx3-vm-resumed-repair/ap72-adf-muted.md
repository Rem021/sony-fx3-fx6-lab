# AP72 ADF 静音地址模型

80秒运行`ap72muted-f2a05842`：qemu_exit=0、process_reaped=true、宿主PID消失、inputs_unchanged=true、missing_markers=[]、两锁实际重取确认释放，末次snapshot3仍含im.elf映射，无symbol lookup error。

capid v26严格限定032e捕获body08 00与033d空body；reply分别132e/12B/status0、133d/24B/status0/+16物理64位地址。独立41da00000/64KiB经FDT+memrsv排除普通分配，已核对与既有预留不重叠，回复前清零并持续映射。marker明确muted=1/original_sound=0，不提供播放成功；原生声音内容与声音功能未验收。宿主ASan/UBSan严格包、原生reply lease、逐字节反例、发送失败回收和64位地址检查通过。

serial 13082绑定、13084/13086为033d提交/释放result0、13150/13152为032e提交/释放result0。**四任务屏障未越过**：提示音注册线程紧接着发0327/40B，serial13161原请求，13162原生Skip snd to747；未新增0327回复。Lead已安排后续注册链审计，因此不把两条成功回复当作整个注册完成。

[完整核验及0x11a后请求时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap72-review.json)。仍无可操作菜单、原声音或实机验收。

时间线为现有轻量trace在本运行中输出的全部发送记录（含去重/计数上限），不构成未记录命令不存在的证明。进程存活证据精确限于末次快照；宿主收尾exit0不代表guest正常关机。
