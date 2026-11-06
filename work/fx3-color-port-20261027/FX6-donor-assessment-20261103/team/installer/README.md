# FX3 7.02 文件级安装路线：只读准入审计

**结论：本阶段只通过本地原件识别，不具备安装准入。** `preflight.py` 对 FX3 AP/CP 原件分别做完整 SHA256，并核对原 `fstab` 与两个 AP 启动程序。基线 7 项通过；错误机型和错误 AP 摘要两项反例均拒绝。没有目标补丁窗口、修改后双摘要、实机文件读回、重启装载与恢复证据。脚本没有写入、设备访问或安装功能；`--model` 是调用者声明，不能证明当前相机身份。

## 来源与迁移边界

固定原代码：[installer.c](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/fl23/native/installer.c)、[workflow.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/fl23/workflow.py)、[wbi.c](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/fl23/native/wbi.c)。父目录 `a7c2-native-review.json` 和 `a7c2-source-review.json` 给出源码 SHA 与定位。本阶段只读源代码，没有执行、移植或保存第三方安装器。

| A7C II 源码合同 | FX3 可核证事实 | 适配差距 |
|---|---|---|
| `installer.c` 37, 83–98, 110–118, 129–143：AP/CP 路径、完整原 hash + fixed window、写后完整 hash；`BYTE_WINDOWS_ONLY` 构建仅窗口检查，主机需完整读回 | FX3 镜像提取 `/usr/lib/appFw.so` SHA `545c5053…58290f`，`/cp/cpapp-b.bin` SHA `c90d00d8…cba`；本地脚本逐字节读取完整文件计算摘要 | 这是离线原件，非当前机身双文件读回；FX3 patch window、原字节、最终摘要均未知，不得套用 A7C 偏移 |
| `installer.c` 66–82, 137–158：先认 `/dev/nflasha15 /usr ext2 ro`，写后尝试恢复只读 | FX3 原 `fstab` 字节：`/dev/nflasha15 /usr ext2 ro`；另有 `/dev/nflasha8 /cp vfat rw`。AP/CP 跨不同文件系统 | A7C 的 `/usr` remount 与 `mounted_rw` 逻辑不能代表 CP vfat 的掉电一致性；FX3 当前 mount 状态、权限和写后 ro 回读未知 |
| `installer.c` 100–108, 142–147：反向窗口回退、fsync、窗口与 hash 复验 | 本地无可应用 FX3 窗口，脚本输出 `patch_windows=[]` | 失败时部分写、断电中断、独立原文件回退未验证；进程内回退不等于断电恢复 |
| `workflow.py` 289–349：机身备份、完整读回、WBI、写入、正常关机取电池重开、再读盘与内存 span；350–389 独立备份还原 | FX3 原 `/sbin/initrc/fstab` 与 `/bin/bootin.elf`、`/bin/im.elf` 从原镜像提取且 SHA 核对；历史 VM 仅启动到受限 AP 入口 | 冷启动执行哪份 AP/CP、运行内存与盘一致、菜单及 RAW/ISP 行为均未知 |
| `wbi.c` 30–67：要求 `image_mode=2`、`image_dev=*wbi4`，`image_drop=1` 后 `image_mode=0` 并查新日志 | 本地无 FX3 对应 sysfs 原件/运行证据 | 不能将 A7C 的 WBI 节点、值或清除操作套到 FX3 |

`stage285` 是 FX3 7.02 真机通信 `SERVICE` read0 与 USB 归还成功（[回执](../../../../sony-firmware-20261024/stage285-service-access-communication05-execution/README.md)）；没有读写 AP/CP 文件。`stage286` 用 FX3 原 `libsencore.so`/`libJiritsu.so` 指令证明 `AdjustControl 0x40` 命令帧与 `SET_FILE2` 的 `/tmp/jbusy` 条件（[回执](../../../../sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/README.md)）；该阶段是**静态/CPU**，没有实机安装器加载。文件系统 `fstab`、AP ELF、CP ARM/Thumb 证据来自 [FX3 VM 原件审计](../../../../fx3-vm-20261101/fx3-audit/asset-audit.json) 与 [载荷审计](../../../../fx3-vm-20261101/fx3-audit/coprocessor-artifacts.json)。[AP 暂存投影](../../../AP-staging-record-routing-20261030/README.md)只证明原参考分支和地址角色，不证明当前机身装载；[VM AP 入口](../../../../fx3-vm-20261101/fx3-audit/p12-ap-entry-independent-proof.json)到 `im.elf` 的 `/dev/uipc` 缺失退出，不是完整 UI/加载验收。

## 可复核产物

- [脚本](preflight.py)：仅打开项目根内非符号链接普通文件，`O_RDONLY`；读文件做固定 SHA、检查 `fstab` 两行；JSON 到标准输出。既不构造可刷包，也没有目标字节或写入代码。
- [基线回执](baseline.json)：7 项本地检查通过，`installation_ready=false`，unknown 保留。
- [错误机型](wrong-model.json)：`ILME-FX6` 返回 2。
- [错误摘要](wrong-ap-digest.json)：把 CP 原件作为 AP 输入返回 2。

## 追加：路径边界修复与加载链

`Path.absolute()` 不消除 `..`，原先的 `is_relative_to` 是词法判断，确有项目根外读取漏洞。现在先 `resolve(strict=False)` 再核真实根归属，并拒绝任何 `..`、路径分量符号链接、非普通文件；打开时仍用 `O_RDONLY|O_NOFOLLOW|O_NONBLOCK`。这不是并发抗替换保证：检查和 `open` 之间仍有竞态，不能用作对抗性目录中的安全读取器。已知有效原件输入均在受控本地目录。

精确复现：在本项目根执行 `python3 work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/test_paths.py > work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/path-regressions.json`，实际 suite exit `0`；回执内有每个子进程完整命令与 exit。四个自建无敏感 fixture：项目内普通文件通过路径门控但因非 FX3 原件摘要而 exit `2`；`../` 越界（只构造路径，不打开目标）、符号链接和目录均 exit `2` 且是路径/类型拒绝。临时 fixture 在测试结束后删除。

[加载链静态脚本](loader-binding/audit_loader.py)对原 `init2`、`fstab`、`bootin.elf`、`im.elf`、`appFw.so`、`cpapp-b.bin` 和 `loader_spi.bin` 全 SHA 重新核验；[回执](loader-binding/receipt.json)以原脚本行和 SPI 指令字节记录：`init2` 在 mode 非 0 时挂载后调用 `/usr/bin/bootin.elf &`；bootin 原二进制两处含 `/usr/bin/im.elf`；原 `pformat_config.txt` 对 CP 的 load 为 `0x00108000`，SPI 原 `+0x5AAC/+0x5AB0` 两条 MOV 编码以及 `+0x3CD8` ERET 与前阶段边界证明一致。AP 在 p15 原文件系统 `/lib/appFw.so` 的 inode、SHA 已绑定，但这批字节没有绑定实际 `dlopen` 读取者；CP 的地址交接与配置相符，精确文件读取者及活动槽仍未知。`im.elf` 的 VM 受限入口不能证明完整 AP 加载；WBI 与冷启动身份仍未知。复现命令：`python3 work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/loader-binding/audit_loader.py > work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/loader-binding/receipt.json`，实际 exit `0`。

下一精确动作：可继续**离线**定位 FX3 专属 patch window 和 AP/CP 文件读取者，明确候选对象与版本；实际设备写入须先取得当前机身原件双摘要、可验证的独立恢复路径及相应授权。本阶段没有修改包和设备动作。
