# FX3 原启动与 AP/CP 对象绑定：静态边界

[审计脚本](audit_loader.py)读取 FX3 官方 7.02 提取的原件，不启动程序。[回执](receipt.json)已用原文件 SHA 检查 `init2`、`fstab`、`bootin.elf`、`im.elf`、`appFw.so`、`cpapp-b.bin`、`loader_spi.bin` 和 `pformat_config.txt`；命令和实际退出码见上级 [审计报告](../README.md)。

- 原 `init2` 第 46 行用 `fstab` 挂载，第 55 行在 `MODE != 0` 时进入启动分支，第 64 行执行 `/usr/bin/bootin.elf &`。原 `fstab` 将 p15 只读 ext2 挂到 `/usr`、p8 可写 vfat 挂到 `/cp`；这是明确的**脚本调用链**，不证明每次冷启动都取此分支。
- 原 `bootin.elf` 在文件 `+0x399A`、`+0x3F48` 含 `/usr/bin/im.elf` 字符串；当前脚本未反编译调用点，所以仅登记路径引用。AP `appFw.so` 在 p15 `/lib` 的原 inode 95387、SHA 和 ELF 对象身份已核，但 `bootin/im` 中未找到 `appFw.so` 路径，实际 `dlopen`/装载者没有绑定。
- CP 原配置的 `cpapp-b.bin` 加载地址为 `0x00108000`。原 SPI 加载器 `+0x5AAC` 的指令字 `0x52900000` 为 `MOVZ W0,#0x8000`，`+0x5AB0` 的 `0x72A00200` 为 `MOVK W0,#0x10,LSL #16`，合成 `0x00108000`；`+0x3CD8` 为 `ERET`。这与[先前固定交接证明](../../../../../sony-firmware-20261024/stage198-AP-CP-loaders-and-partition-selection/fixed-handoff-proof.json)一致，是**原指令与配置地址一致性**；实际 CP 文件读取者、活动槽与运行时 PC 仍未知。

静态文件与原指令不能证明机身冷启动加载身份、WBI 快照选取、修改文件后的内存映像，也不能证明任何 RAW/ISP 移植。下一步沿 FX3 真实 AP 装载符号和 CP 文件读取调用者继续离线追踪。
