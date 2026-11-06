# FX6 两个启动入口的等长软件候选

2026-11-03。**候选已生成并逐字核验，尚未启动。** 这一步仅把 FX6 `bootin.elf`、`im.elf` 放入原冻结 FX3 启动包，保留 FX3 上层主程序及全部其他文件；它是混合移植的最小装载实验，不是完整 FX6 上层系统。

FX6 两个文件恰好与对应 FX3 成员等长：`bootin.elf` 23,960 字节、`im.elf` 40,920 字节。因此直接在原 CPIO 副本的两个 payload 范围内替换，无需重新打包、改变头部/排列、修改 `/init`，也**不需要修改 DTB 的 initrd-end**。

| 项目 | 结果 |
| --- | --- |
| 原 CPIO SHA256 | eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d |
| 新 CPIO SHA256 | ff2f927de24b801d334ce9111fb486fb2af85d24c509ab20c43eda0a69ffdc40 |
| 两者大小 | 453,184,500 字节 |
| 成员数 | 1,140，顺序、元数据及各成员长度不变 |
| 变化成员 | 仅 `usr/bin/bootin.elf`、`usr/bin/im.elf`，分别精确匹配 FX6 原文件 SHA |
| 两段 payload 外所有字节 | 逐块比较一致，包括头部、符号链接、填充与 trailer |
| FX3 kernel/QEMU/DTB/Backup | 当前原件哈希与冻结 baseline 全部一致 |
| 模拟器硬件参数/环境 | 冻结基线原样记录；没有生成或执行新 QEMU 命令 |

[manifest.json](manifest.json) 保存两成员的 CPIO 偏移、前后 SHA、其余字节区间哈希、原平台参数和运行前核验要求。对应构建器为 [build.py](build.py)，只写本目录候选；已有候选再次调用仅验证，不覆盖原件。

```sh
python3 -B work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/hybrid-entry-candidate/build.py
```

现有“所有原 FX3 ELF 必须原样”检查应当报告这两个有意变化，不能靠删除原校验或全局忽略错误放行。运行前需要独立核对仅这两项 FX6 原 SHA 的精确允许清单，并保持所有其他成员、设备树和模型一致。正常客体日志/套接字必须使用全新运行目录，不能照抄冻结命令中的历史 serial 路径。

下一实验只观察原 `/init` loader `--verify`、`--list`、BusyBox 三个返回码和首次真实启动/IPC 路径，在首个失败或最小证据取得处停止并完整回收。FX6 AP/AV/CP 未被放入此候选，FX3 `appFw.so`、`libObj.so`、Backup、17 个预载辅助库和原驱动均保留。不得把保留 FX3 AP 后出现的界面称为 FX6 菜单。

本轮未运行 QEMU、未改日常入口、未接触相机。构建和字节一致性不等于 ABI、进程启动、菜单或影像功能通过。
