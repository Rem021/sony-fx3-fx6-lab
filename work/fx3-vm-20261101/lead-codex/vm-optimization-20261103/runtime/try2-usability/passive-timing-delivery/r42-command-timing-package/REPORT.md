# r42｜固定单槽计时包

**离线封装与文件审计通过；未运行 VM、未部署，未证明菜单可靠性或性能改善。** FX6 被拒实现未重试。

以已验收 r36 `guest.cpio` 为基础，重新解析实际 newc：1141 项含 trailer，GPE `simulation/fx3-gpe-observe-v7.so` 的 payload 位于 **451447396**，原槽 **276984B**、原 SHA `30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4`。替换为封存 r41 `build/gpe-r41-fixed-slot.so` **129600B**，SHA `19ca7deaf570eeb68fda0036bb75dec740ab30f404f9f91bd208fd3d53c06a39`，加 **147384B 全零尾**。未使用超槽 raw ELF，也未重新编译。

输出仍为 **453213884B**；完整顺序比较证明槽外 **452936900B** 每个字节相同，全部头、名称、顺序、mode、尺寸、偏移和 trailer 相同。只有 GPE body 的162664字节变化，UI/OSD、原 init 和其余成员不变。`ARCHIVE-DIFF.json` 和1141项 `member-comparison.json` 为实际回执。

新 CPIO SHA：`59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63`。新 candidate SHA：`857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806`。candidate 只改变 `initrd` 和新增 r42 来源合同；历史 ap105 的旧 GPE 引用明确保留为基线来源，当前 body/slot 分开记录。

`ELF-AUDIT.json` 再次验证 r41 raw→fixed-slot 的 ALLOC、PHDR、装载内容及动态身份；唯一动态依赖仍为 libc.so.6/libdl.so.2，其实际 CPIO 链与底层成员均与 r36 相同，见 `SOURCE-BINDING.json`。源文件直接引用 r41 封存的 v26_perf 和返回观测头；backend-v9 是原实现，非本轮新增优化。

固定 QEMU/kernel/DTB 的原路径与 SHA 在 runner 的 `INPUTS-PLATFORM.json` 实际核验，4×cortex-a35、5120MiB、MTTCG/noicount、initrd **0x440000000**、DTB **0x400002000** 保持。初始 pin 对已读文本仅称首次观察；新增二进制/源码观察与模块导入后 pin 均另列时点，没有把继承验收当本轮全量重测。最终只核实际用到技术材料，不扫描11915/1398项历史集合。

本包只能配合同级 `r42-command-timing-runner` 的精确选择器；未调用任何 target main、QMP、guest 或设备动作。r41 的 host/解析/成本结论沿用正式验收，本轮没有重测或声称 guest 时序零扰动；零首帧根因、连续菜单、FX6开机仍未解决。

封存前首次复核发现APFS大小写别名导致摘要覆盖实际条目索引；已改用独立 `SOURCE-BINDING.json` 并从实际输出CPIO重建索引，其SHA与覆盖前pin完全一致。包/候选字节未变；首版脚本、原metadata输出与失败stderr保留于receipts，最终以冻结清单为准。

最终必要技术 pin 去重 **122项**，其中外部原技术输入 **99项**、本轮产物依赖 **23项**；结束复核全部一致。时点口径见各观察清单及 `INPUTS-AFTER.json`。
