# AP71 原厂 iCrypt 加载修正

80秒运行 `ap71crypt-68d9c419` 通过：qemu_exit=0、process_reaped=true、宿主PID消失、inputs_unchanged=true、missing_markers=[]，两把锁已实际重取确认释放。末次完整snapshot3含im.elf映射；无symbol lookup error。

仅在启动preload末尾增加被动观测库及原厂libInfraCrypt.so，未调用iCrypt_init。license_get_i的三种id（0x20300001..3）各调用HasPublicKey/HasPrivateKey，六次原厂返回均0（serial 14412..14521）。运行窗口无具名libInfraCrypt.so的IMDB dlopen事件；其缺失原因仍未证实，preload映射不代表IMDB第86项执行。

[完整回执与0x11a后请求时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap71-review.json)。原始输入及既有runs不变，仍无可操作菜单或声音验收。LD_PRELOAD的列表与从左至右加载语义参照[Linux ld.so手册](https://man7.org/linux/man-pages/man8/ld.so.8.html)，实际版本与行为以本轮guest证据为准。

时间线为现有轻量trace在本运行中输出的全部发送记录（含去重/计数上限），不构成未记录命令不存在的证明。进程存活证据精确限于末次快照；宿主收尾exit0不代表guest正常关机。
