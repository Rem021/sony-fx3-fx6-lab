# 社区刷坏回退的实际范围与 FX3 适用边界

## A7C II 的恢复成功究竟证明了什么

### Takeaway

核查日期2026-10-29。A7C II 有真实故障后恢复开机的本人后续，但保留下来的录像启动路径是关键；它不是主应用完全失效后的 BootROM 救砖。其代码的备份／恢复范围可精确借鉴，不能照搬为经典 ILME-FX3 7.02 的全机恢复承诺。

### Cited Findings

- #31首帖（2026-10-23）报告改动后拔电池再开机失败，访问灯2-3-5循环、USB出现054C:0D68 HID；10月25日另一操作者提出从 Movie／P 模式启动，10月26日有人确认恢复，10月27日首帖作者称经录像档启动再切回拍照档后可正常再次启动、原FL23仍保留。维护者确认该项目修改图片相关逻辑。它是多人一手反馈，不是我们独立实物复验；帖子中“拆芯片重写”和维修报价只是机主转述，未见相应芯片作业、完整dump和回读记录。— [原帖与全部后续](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)，重点为[模式绕行](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6399306736)、[首帖作者10月27日后续](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6442900646)。
- 当前GitHub API树的HEAD仍为`ef7db116e13e37be91e9af20360dc9bba8d64a9b`，与本地151轮固定提交相同。项目限制型号ILCE-7CM2、固件2.01；入口仍为正常USB型号检查→认证→0336→再次认证→机身绑定。— [固定开发指南](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/docs/en/development.md)，[当前树元数据](https://api.github.com/repos/QAQLeonard/a7c2-fl23-research/git/trees/HEAD?recursive=1)。
- 实读`checkpoint.py:15–21`：`PROGRAM_PATHS`仅为`/usr/lib/appFw.so`和`/cp/cpapp-b.bin`；`inventory()`再加RAM／已存设置和项目名称资源。`capture()`读取这些文件，未将av-cam.bin、内核、BootROM、boot0／boot1或原始分区列入该检查点清单。`read_legacy()`还明确旧FL23备份只有当时运行设置，没有另外保存历史闪存设置快照。— [固定 checkpoint.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/checkpoint.py)。
- `checkpointjob.Rollback.capture()`读当前两程序／设置／名称；`run()`先留本次before检查点，再构造恢复，完整程序回读；冷重启后检查AP运行片段，源码仍将CP RAM与实际拍摄行为留给后续验收。`factoryrecover.py`主要处理待恢复事务、原／目标窗口一致性和旧执行报告，不提供独立冷启动入口。— [checkpointjob.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/checkpointjob.py)，[factoryrecover.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/factoryrecover.py)。
- 新桌面“原厂恢复”的内置参考是本项目改动窗口的通用原厂字节，不包含完整固件或机身数据。`direct.plan(factory_reset)`从当前两程序重建目标，`run_direct()`调用限定窗口工作器后完整比较程序文件；`verify_direct()`再核对新的boot_id和磁盘／运行片段。它支持“从当前状态构造逆修改”，不要求所有局部功能都先持有全盘镜像。— [direct.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/direct.py)，[窗口参考范围说明](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/docs/en/development.md#core-flows)。

### Inferences

- 可以借鉴其“精确修改窗口＋当前字节核对＋原字节逆修改＋全目标文件回读＋新启动加载核对”的方法，分别适配FX3目标文件；不能把A7C II的偏移、机身设置号、CP文件或Movie拨杆恢复步骤直接搬过去。
- #31成功且FL23仍在，至少说明该个案无需重写整个闪存即可恢复；它没有证明损坏的任意程序或启动区可以靠同一模式切换修复。FX3要改录像逻辑，尤其不能把“录像启动仍健全”当作天然保留的后门。

### Gaps

- 未找到公开、可核对到经典FX3 7.02的“修改MAIN／av-cam后无法启动→独立入口→恢复原字节→回读→正常拍摄”的完整一手证据。
- 未取得#31错误机身的失败文件、冷启动日志及程序差分，无法从灯序或HID身份确定根因。本文没有执行诊断附件或恢复工具。

## A7 IV 的 Fastboot 触发 SD 恢复有哪些可借鉴的实作

### Takeaway

新增的重点线索是 Erlla 的限定范围 MODE5 恢复触发器：它确实给出不经正常拍摄界面、在已进入 Fastboot 后准备SD更新的代码。但当前只接纳A7 IV和一个精确的已修改更新器配置，且先要有硬件BootROM／RAM Fastboot入口；不是普通USB连接后的通用Sony强刷器。

### Cited Findings

- 2026-10-29经GitHub API读取，`Erlla/sony-a7m4-custom-firmware` HEAD为`0bfeee4f961610434588dc89c2cd3bc658816a3d`（提交日期2026-10-28T18:19:05Z）。本轮实读固定`a7m4/sd_recovery.py`，SHA-256为`79a9597a783e466e6a3b66cbbf5760c18502ec1695f659b55c2162444afed7a1`，与其发布验证记录一致。— [固定源码](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/a7m4/sd_recovery.py)，[验证记录](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/methods/00-sd-recovery/validation.md)。

| 实读函数／数据 | 实际覆盖 | 明确限制 |
|---|---|---|
| `BACKUP_NAMES`（第17行）、`recover`（264–356） | 本次新读`nflashaB0/B1/1/2/8/13`；写前重核分区表及B0／B1／2内容 | 六分区，不是全eMMC，也不包括物理CP NOR |
| `make_trigger`（158–227） | 对20MiB的nflasha2 FAT候选，仅把`updater/dat4`两字节BCD置0.00，并在既有空槽准备空`MODE`、`MODE5`目录项；核对其他文件和`Backup.bin`不变 | 仅接受版本0或6.x、特定FAT布局；不重建文件系统；与FX3 7.02没有自动兼容性 |
| `inspect_sd_environment`（230–240） | nflasha1内`boot/initrd.img`的p1chksum MD5＋配置SHA-256 | 不是仅看版本号；白名单只有精确的修改版更新器 |
| `RecoveryTransport.command`／`write_settings`（58–105） | 持久命令仅`flash nflasha2`，候选路径／哈希绑定，一次写入许可在调用前消耗 | 不是任意分区写入器，不自动重试 |
| `recover`写后阶段（335–348） | 写本次设置候选、完整20MiB读回，再一次普通reboot | `update_completed=false`保留；主机只证明触发，机内更新另验 |

以上表格均来自[固定 sd_recovery.py](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/a7m4/sd_recovery.py)。表中列出的函数名／存储布局不是建议在FX3上执行的指令。

- 配置只接纳initrd SHA-256 `bd81714ed85b175ad6da41947adcb80b7b3deb965c23aab04c84901c99e52d98`，注释明确是此前验证过的修改版SD updater，不是通用原厂profile。触发器本身不替换密钥或`verifyKey`；原有更新器仍处理DAT的签名、机型与其他准入。因此不能简写为“已验证原厂签名更新器总能同版重装”。— [固定 profile](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/a7m4/profiles/sd-recovery.json)，[方法说明](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/methods/00-sd-recovery/README.md)。
- 方法要求ILCE-7M4、已经通过Multi接口／RP2040-Zero进入Fastboot；本脚本不进入Fastboot。更新器、SD链或更早启动层已损坏时可能无法使用。公开适配版验证是离线模拟，维护者称历史同机有NOR更新日志、回读和正常取景，但原始机身证据保留本地未公开；应标为维护者经验，不能冒充本轮或公开版新的实机救砖。— [入口与适用条件](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/README.md)，[实机与离线证据区分](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/methods/00-sd-recovery/validation.md)。
- DavidBuchanan314 的 A7 IV 研究提供了串行BootROM→自制RAM Fastboot→eMMC备份／恢复的更早入口，明确boot0的透明密码处理未实现。ZV-E10新工具也明确区分“Linux服务备份”和“Pico注入后、Linux之前的分区恢复”，两者都说明服务活着与独立早期入口是不同能力；它们都没有在所读页面声明FX3适配。— [A7 IV原始研究](https://github.com/DavidBuchanan314/ILCE-7M4-RE)，[ZV-E10项目，当前树bd2b4ac03af71bd397f8b88162db1ec1671e222a](https://github.com/dino2048/zv-e10-toolkit/tree/bd2b4ac03af71bd397f8b88162db1ec1671e222a)。

### Inferences

- 对FX3最有价值的移植对象是“独立入口可达后，受限设置标志驱动原SD更新器”的恢复设计。应先对照FX3原启动代码是否识别对应模式、数据在哪个分区、从哪层启动选择到updater，再核对7.02自己的更新器准入；不应先移植A7 IV的20MiB镜像或标志偏移。
- 已经在MAIN之外能启动的原厂更新器，可以成为局部应用失败后的恢复候选；但“更新器分区里有程序”与“MAIN坏了仍能选中并启动该程序”必须分别证明。

### Gaps

- 未见该A7 IV恢复器公开支持FX3；本轮未读取任何用户机身分区，也未下载或运行硬件payload。
- 用户现有Mac／Windows能做离线解析与主机软件准备；上述已公开的独立BootROM路线仍需要相应桥板、接线及目标机身适配。不能承诺增加一台电脑就能代替这些条件。

## 如何按改动范围建立退路，而不把全盘备份当作所有试验的前提

### Takeaway

应把“修改什么、写到哪里、失败会损坏哪条启动路径”作为恢复设计输入。局部文件与RAM实验可以建立较小而可复核的退路；涉及早期启动和更新器本身时，需要更早、更独立的恢复能力。下表是根据已读项目实现作出的FX3研究建议，尚非FX3实机放行结论。

### Cited Findings

- A7C II把检查点限定为两程序／设置／资源，把恢复内置参考限定为项目改动窗口；A7 IV则明确区分六分区触发备份、全部eMMC备份和独立CP NOR，且物理CP修改要另备份NOR。已有项目本身就不把各种“backup”当成同一覆盖范围。— [A7C II检查点清单](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/checkpoint.py)，[A7 IV备份范围](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/README.md#%E5%A4%87%E4%BB%BD%E8%8C%83%E5%9B%B4%E4%B8%8E%E6%81%A2%E5%A4%8D%E6%9D%A1%E4%BB%B6)。
- PMCA HEAD经API重核仍为`a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`（2022-08-18）；FX3A #715机主在2026年6月报告服务认证问题及后续设置操作，是FX3A而非经典FX3 7.02。该线程不构成MAIN损坏后的恢复记录。A6700本轮API请求失败，不能把旧固定HEAD `d5bb9485…`写成已再次实时核验；当前可见README仍标明A6700 2.00／Pico已知范围备份，刷写与全盘恢复待验证。— [PMCA提交API](https://api.github.com/repos/ma1co/Sony-PMCA-RE/commits/HEAD)，[FX3A线程](https://github.com/ma1co/Sony-PMCA-RE/issues/715)，[A6700维护者说明](https://github.com/xyzhangxin/sony-a6700-powerful)。

### Inferences

| 拟改范围 | 首先准备什么 | 什么情况下不能只靠这些材料恢复 |
|---|---|---|
| 纯运行时／RAM最小实验 | 精确的RAM改动与原值、生命周期与撤销顺序；先证明不写回持久设置、文件或更新标志；验证退出／断电重启回原状态 | 若实验还改持久设置、触发flash或伤及硬件，不能再称纯RAM可逆；无需为真正纯RAM实验一律先备全eMMC |
| 仅appFw.so内限定窗口 | 本机完整原文件＋哈希和长度、精确改动窗口、相关设置原值；一个不会被拟改窗口破坏的恢复入口；受限逆写＋完整目标文件回读＋冷启动加载核对 | 若同一文件损坏会使正常应用／服务一起起不来，备份文件本身不能提供进入机身的通道；不能假定FX3也有A7C II的Movie绕行 |
| av-cam／编码器程序，或独立CP程序／NOR | 先确定真实存储介质和依赖，把拟改文件／镜像、必要配置及涉及的本机校准原件纳入备份；文件恢复和物理NOR恢复分别设计 | A7C II清单不含av-cam；eMMC备份不能自动覆盖独立CP NOR。程序崩溃会否连带服务／电源控制尚须FX3证据 |
| boot／updater／签名校验／模式选择本身 | 更早的型号专用BootROM／外部编程入口，以及对应boot区、分区布局、更新器、设置与个体数据；先核对恢复器能覆盖所有拟改介质 | 修改恢复链本身后，原服务或SD更新器可能不再可达；这时局部应用备份或六分区触发备份不能替代更早入口 |

- 下一轮可立即离线推进：以固定A7 IV函数为对照，在FX3原启动材料里追完整的updater选择条件；列出每个候选补丁实际触碰的文件／RAM／持久设置，生成“原值、修改值、最小逆修改、独立入口依赖”四列表，而不是先做全系统跨刷。
- 恢复验证不必以故意把主力机变砖为起点。可在健康机身、相应具体授权与退出方案具备后，验证独立入口是否可达和受限读回；只有相应证明成立，才把该入口列为某个改动范围的退路。

### Gaps

- 以上是基于源码范围的研究方案，不是已完成的FX3恢复实验。没有新的相机查询、Sony认证、文件读写、管理员操作、Windows／UU动作或固件执行。
- “REA”等AI研究工具可以帮助追代码和生成受限修改，但工具名称不会补出缺失的BootROM入口、硬件映射、签名条件或同机原件。实际可恢复范围仍需由目标机身证据确认。
