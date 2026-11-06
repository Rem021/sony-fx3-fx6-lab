# A7C II 社区项目的实际回退、救启动与整包路线

## 哪些失败确实恢复了，恢复者究竟做了什么？

### Takeaway

A7C II 有故障后恢复启动的一手后续，也有精确逆修改后恢复录像表现的实机报告；不能把这些说成主应用、内核或启动区全坏后的通用救砖。尤其要区分 QAQLeonard 的 FL23／外观功能修改、YuuLuo 的 DAT 整包安装、以及 stage151 的 HEVC 25／29.97 演示，三者没有已建立的同工具关系。

### Cited Findings

- 本轮 2026-10-29 实时 API 核查 #31 全部20条评论。首帖机主 lipu0324 报告按流程改后第二次拔电池即无法启动，灯2-3-5循环、USB为054C:0D68。CRAZYShimakaze 于10月25日提出关机、拔USB／电池／SD卡、Still/Movie/S&Q切Movie、曝光P后启动，再使用仓库恢复功能。dt-nb 次日反馈已恢复，但没有明确区分其是否执行了后半段恢复功能。— [首帖](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)，[提出方法](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6399306736)，[dt-nb反馈](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6407606480)。
- **lipu0324 于10月27日明确报告可以不运行恢复功能：录像档启动后拨回拍照，再关机重开即正常，已装功能仍在。**这是其本人对所采取操作的说明，不应仅从FL23仍在推断是否发生过写入。维护者随后认可模式绕行有用，说明项目主要改图片逻辑。— [机主明确后续](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6442900646)，[维护者10月27日回复](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6451942771)。
- #31中机主转述官方建议换主板约3000元、第三方拆芯片重写报价数百元；没有公开维修完工单、被换板／芯片、编程器dump、写后回读。因此它们是询价／送修经历，不是已证实必须换板或拆芯片救活的案例。— [lipu0324转述](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6410065948)，[HaoDingg转述](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6410296832)。
- #28原机主报告部分竖屏修改完成后，FL23在appFw.so `0x3528804`冲突停止，相机仍能拍照／回放；维护者指出FAILED不代表之前改动自动回退，需日志后判断。10月27日因未回复关闭，不能计作恢复成功。10月28日另一用户报告同报错源于其机身实为2.00，升2.01后安装成功；不能倒推原楼主也必然是该原因。— [#28](https://github.com/QAQLeonard/a7c2-fl23-research/issues/28)，[新增10月28日反馈](https://github.com/QAQLeonard/a7c2-fl23-research/issues/28#issuecomment-6476759509)。
- #44机主报告factory/reset等流程因自变化设置检查停止，自己放宽遥测字段检查后称恢复和重装完成；对应PR#59本轮仍open。这是修改后工具的一手功能恢复反馈，不能标作原版3.0.3已解决。#57则是在曾换主板的机身上，认证／服务连接成功，但读appFw.so固定返回`0x10000004`，尚未写入、相机功能正常；“换板导致分区变化”仅机主猜测。— [#44](https://github.com/QAQLeonard/a7c2-fl23-research/issues/44)，[PR#59](https://github.com/QAQLeonard/a7c2-fl23-research/pull/59)，[#57](https://github.com/QAQLeonard/a7c2-fl23-research/issues/57)。
- PR#25记录另一类较强证据：S35视频横纹在一台2.01机身上，通过把CP文件`0x13553a`的4字节强制跳转改回原生指令，完整程序读回确认其余字节／六槽／名称保持，再做冷启、照片、NC 4K60视频和导出片段检查。作者明确完整集成安装包、全部格式／机身和CP运行内存尚未全验。这是健康服务可用时的最小逆修改，不是启动救砖。— [PR#25原始技术与实机记录](https://github.com/QAQLeonard/a7c2-fl23-research/pull/25)。
- stage151已取得的HEVC演示是[@liulingyue 2026-10-24原帖](https://x.com/liulingyue/status/2113872045637279779)及[菜单后续](https://x.com/liulingyue/status/2114013688042524892)：4K25／约29.97、422 10bit的机内回放与播放器截图。原帖未给公开补丁、失败文件或恢复流水；当前所读QAQ与YuuLuo项目功能文档均不能把该演示绑定到其恢复实现。复用stage151原始元数据／六张图的证据，不把FL23的Movie绕行扩展成HEVC修改的退路。— [QAQ范围](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/docs/en/development.md)，[YuuLuo范围](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/README.zh-CN.md)。

### Inferences

- #31的个案更符合“保留的工作模式能绕过出错路径后重新建立可启动状态”，未确定具体故障字节／设置或灯序根因。用户要求修改录像链时，应专门证明另一条启动／服务路径不受影响；不能把录像档天然视为后门。
- 判断社区方法应看明确动作、所用版本和回读／实物检查；“非官方”本身既不否定真实成功，也不能填补未公开恢复层的缺口。

### Gaps

- 本轮未见A7C II这些项目给出“MAIN／内核／p1损坏无法跑服务→不依赖该层的新入口→重写同机原件→完整回读→正常拍摄”的公开流水。
- HEVC演示与“小山重叠金明灭”账号、上述GitHub维护者、确切工具／固件版本之间，现有材料不足以建立同一身份／实现关系；没有原始MP4或救砖记录供独立复核。

## 源码里的Recovery与YuuLuo整包更新实际读写什么，依赖哪一层？

### Takeaway

QAQ提供局部功能的文件／设置回退；YuuLuo确实提供改DAT后经机身菜单整包安装的路线，并临时修改p1中的更新环境。两者均有细致备份和恢复代码，但恢复执行本身依赖仍可工作的Linux／USB服务／Jiritsu／动态加载子进程，尚无此处可用的独立BootROM入口。

### Cited Findings

本轮API实时确认主线固定提交：QAQ `ef7db116e13e37be91e9af20360dc9bba8d64a9b`（2026-10-25），YuuLuo camera-tools `f124d87c26110a82db54775bfa64a0843ff21410`（2026-10-19），service-preload `1619f938663a36d41e72302a8cfee89a0f6acd1a`（2026-10-15）；均与stage151固定文本相同。最新fork列表只抽查kyralo一份，其tree HEAD与QAQ同SHA，没有凭推送日期宣称存在新恢复实现。— [QAQ提交API](https://api.github.com/repos/QAQLeonard/a7c2-fl23-research/commits/HEAD)，[YuuLuo提交API](https://api.github.com/repos/YuuLuo/a7c2-camera-tools/commits/HEAD)，[preload提交API](https://api.github.com/repos/YuuLuo/a7c2-service-preload/commits/HEAD)，[抽查fork](https://api.github.com/repos/kyralo/a7c2-fl23-research/git/trees/HEAD?recursive=1)。

| 实现 | 备份／恢复内容与验证 | 执行依赖／边界 |
|---|---|---|
| QAQ `checkpoint.py`／`checkpointjob.py` | 两个完整文件`/usr/lib/appFw.so`、`/cp/cpapp-b.bin`；RAM／已存设置；68名称资源。回退先存当前`before.private.zip`，从目标生成受限工作器，回读完整两程序／名称，按所管设置写回并比对 | 同机序列摘要绑定；不是全文件系统／全flash／校准复原；旧backup2仅有当时live设置，没有另外历史saved快照。Legacy verify核对AP运行片段和已保存设置，明确CP RAM／实际行为要用户验收 |
| QAQ桌面 `direct_factory_reset` | 当前字节构建逆修改；内置JSON只有项目涉及窗口的通用原字节，无完整固件／个体资料。程序完整回读；新boot_id、已加载AP片段、保存／live设置及只读挂载另验 | `factoryrecover`解决旧事务／临时文件，不建立早期启动器；已有未知preload会停止。此处“独立Recovery”指不依赖旧LUT工作目录，不代表脱离机身服务独立开机 |
| YuuLuo p1备份 | `windows_p1_capture.py`经三次有界窗口采集`cnflasha1`，总25,100,288字节，窗口、块、整文件hash；再核对FAT、initrd、p1chksum与本机绑定 | 只覆盖p1及另采的两份BK4，不是全eMMC、boot0/1或CP NOR备份 |

表格来源：[checkpoint.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/checkpoint.py)，[checkpointjob.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/checkpointjob.py)，[direct.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/direct.py)，[factoryrecover.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/factoryrecover.py)，[p1采集](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/windows_p1_capture.py)。

- QAQ源码真实CLI是`python recovery.py restore BACKUP --firmware-version 2.01 --battery-percent N`，完成并重启后`python recovery.py verify WORK --accept-photos`；`inspect BACKUP`为离线范围查看。执行依赖64-bit Python、同机服务、编译／固定工作器等；`transport.Session`由普通0E8A型号校验→认证→0336→再认证→机身绑定。工作器通过Jiritsu临时文件／libJit触发；不是黑屏HID 0D68刷写协议。这里只记录命令，未运行，也不适用于FX3。— [recovery.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/recovery.py)，[transport.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py)，[devicesession.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/devicesession.py)。

**YuuLuo整包路线的关键细节（不能缩写成“只改几个设置”）：**

1. **DAT确有重新封包。**`fl23_windows.py`从精确hash的2.01原件解密，在p15/AP改86个字节、p5/WBI2改4字节、p8中CP改155字节；更新这三个成员的CRC、FDAT头版本2.01→2.00及头CRC，再重加密payload、更新外层DEND CRC，逐字节完整解密回读校验。`encrypt_from`先复制原件并保留原`0x110` trailer，未生成新的RSA签名；报告`camera_side_gates_in_DAT=False`。音效选择另有声音登记／资源修改。— [fl23_windows.py](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/release/fl23_windows.py)，[feature_package_200.py](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/release/feature_package_200.py)。
2. **p1有持久窗口修改，不只有RAM版号。**`build_p1_gate_200.py`从本机原p1定位两段精确hash的压缩片段，dual 45,172字节、triple 37,542字节；解压后修改两库共4处指令，压回原长度并更新105字节p1chksum。dual的库内`0xA0CC`改为返回1、`0xACE8`改为返回0；triple的`0xD208`／`0xD27C`改为W19=0。不得只看README就称所有门控仅为版本检查。— [p1构建器](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/core/build_p1_gate_200.py)。
3. **triple已做完整SHA级语义标定，dual仍有缺口。**triple声明的库SHA `b2b066b963a42d96556f811a773579eb16a0358de1b3a9206a1845c0df99bb74`、长度72864，与本项目既有FX3旧2.04/2.05原`libupdatercorecommon.so`完全匹配。只读反汇编确认两偏移位于`Updater::RVchk4PI::chkFirmInfo_before`，原先分别设置-1及在版本比较后CSETM LE，改成0。对应本地证据`legacy-library-size-hash-comparison.json`及`exact-shared-triple-corecommon-disassembly.txt`。**dual库是60600字节／SHA `1a6a3226…`，本地旧FX3 SD库60584字节／不同SHA，不能借同偏移赋予符号。**缺A7CII原库时，不把dual具体标成签名、机型或版本中的某一项；DAT改密文保留尾部也不能被写成“重新签名成功”。— [公开精确原库指纹与补丁](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/core/build_p1_gate_200.py)，[原本地库提取与原签名校验的前阶段入口](../../../../fx3-color-port-20261027/input-20261028/README.md)。
4. **机身MENU版号还有单独RAM门。**`update_code_hold_200.c`找运行中的`/usr/bin/im.elf`、其`libupdaterufp.so`映射，在`+0x1888`临时写4字节，把2.01版号返回改成1.99，保持600秒后试图还原。仍核对持久`/setting/updater/dat4==0x0201`，没有在这一步把dat4落盘改成1.99。主流程要求机身确认页1.99→2.00并在时限内更新；随后回到USB读dat4=2.00，再恢复p1。— [RAM门原C](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/native/source/update_code_hold_200.c)，[主流程](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/a7c2_200_windows.py)。
5. **“仅恢复原始p1”只撤临时更新环境。**UI的restore-only需已验证p1_installed记录，最终调用`windows_p1_200.py --serial SERIAL --manifest MANIFEST --action restore --execute`。精确顺序是triple `verify_patch→restore→verify_orig`，再dual相同3步；不回刷所有DAT成员或恢复全部颜色设置。manifest绑定本机、源p1／候选hash及工作器衍生，未知／半损坏的窗口会先拒绝。每步依然经MSC／0336／root子进程运行；MAIN或更早启动失效而无法建立这条服务链时，此源码没有另一路写回。— [CLI执行与状态](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/windows_p1_200.py)，[6步定义](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/core/p1_gate_generic_200.py)。
6. **p1工作器有本步回滚，不是断电自救。**C代码写前把本次原fragment和checksum留RAM；写目标、fsync、读回CRC/FNV及checksum。不成功则尝试逆写本次原值并再读回，phase8为rollback_verified、phase9为失败。它恢复本步调用前状态；例如dual已完成后triple失败，不能据此说整段p1自动回原厂。电源断开／进程无法继续时该回滚逻辑不能运行。控制器遇到`in_progress`未清或证据不完整会停止，不盲目续写。自动restore逐步验证的是窗口／checksum；README另声称研究机做过完整p1回读，两者须分开陈述。— [p1原C](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/native/source/p1_triple_gate_200.c)，[控制器](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/windows_p1_200.py)，[维护者实测范围](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/README.zh-CN.md)。
7. **BK4是颜色属性的持久双副本，不是双启动固件。**备份`/setting/Backup.bin`和`.bak`各2,390,264字节，检查两记录校验；FL23需要先改CP运行颜色，再检查两份BK4的`0x02A40001` 8192字节属性是否为目标。需要时仅写该属性及第二记录checksum、fsync并重算整个第二记录；出错尝试两文件原属性／checksum逆写。之后另做BK4快照、冷启CP／BK4读回；仅音效不改这些颜色属性。该错误回滚也依赖当前进程继续运行，双副本不是整机救援分区。— [BK4原C](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/native/source/bk4_commit_200.c)，[Windows前置与回执](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/windows_bk4_commit_200.py)，[主流程](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/a7c2_200_windows.py)。

### Inferences

- YuuLuo保留2.00标号以便正常机身之后接受官方2.01，是一种有价值的“保留将来更新路径”设计；不等于修改失败导致服务／菜单都不可达时还可重装，也不等于官方更新会复原BK4的全部历史设置。
- 局部文件备份与整包DAT可各自有用；“有原件”和“失败后有办法把原件送回存储介质”是两件事。对p1本身的修改尤其要先证明更早入口，而不把健康状态下的restore-only当作独立救砖。

### Gaps

- 未取得YuuLuo公开的“p1写入中断／更新中断后无法启动→独立救回”实机流水；文档有正常安装与应用／恢复验证陈述，但不是此类事故验收。
- 尚缺dual片段中的A7CII原库／带符号映射，不能确定这两处常量返回是否覆盖签名、机型或其他检查；本轮没有下载整包或编译／运行该项目。

## 哪些社区做法能迁到经典FX3 7.02，下一步应具体做什么？

### Takeaway

可以直接迁的是证据与事务设计：固定来源、同机备份、精确逆修改、实际目标回读及启动后检查；不能迁的是A7CII偏移／分区、Movie恢复步骤和整包准入承诺。现有Mac＋Windows11 x86可继续离线追查，不需要把换主机系统等同于增加独立恢复入口。

### Cited Findings

- QAQ `backupstore.py`按同机摘要分库，用1MiB分块、SHA-256命名、压缩基础块／XOR delta、原子保存与读回重建核对；delta直接指基础块，不依赖一串旧job。需区分：`checkpoint.private.zip`本身主要用ZIP CRC及直接字节核对，不是另加固件hash白名单；机身serial摘要也不证明固件相容。— [backupstore.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/backupstore.py)，[checkpoint.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/checkpoint.py)。
- MDHan适配仓库当前tree SHA `41950d3eab53e0b801f315af07505a2d0d3f76af`，README明确实际恢复尚未测试，备份不保证救回；已有的是升级／首次重试安装及工具验证个案。cjryrx当前SHA `e48c6fb7dde724df8e8f07f54d96d5780aa1930f`只把单AP按钮属性的before值写回并saveBackup；它不是固件补丁或整机恢复。— [MDHan固定README](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/README.md)，[按钮项目](https://github.com/cjryrx/a7c2-research-modification/blob/e48c6fb7dde724df8e8f07f54d96d5780aa1930f/README.md)。
- chocotan QEMU项目当前SHA `36c62208efc1e0e94ff24c75cb3ed05a0e4d83c0`允许虚拟覆盖原程序来研究，README明确未由原程序拍下并保存JPG／MP4，不是实体相机救援程序。`plateworks-shutterlock`当前SHA `9cf79b8a6d635f419228dcc6c1ae3c77e0be532f`的charter标为2026-10-15 parked，写前原厂设置备份／恢复只是门槛，读取机身清单／启用与恢复里程碑未完成，代码门控需第二机身或已证明A7SIII恢复路径。不能把它当作现成A7SIII／FX3救砖方案。— [QEMU固定README](https://github.com/chocotan/a7c2-qemu/blob/36c62208efc1e0e94ff24c75cb3ed05a0e4d83c0/README.md)，[ShutterLock charter](https://github.com/domalhambra/plateworks-shutterlock/blob/9cf79b8a6d635f419228dcc6c1ae3c77e0be532f/PROJECT_CHARTER.md)。

### Inferences

下一项离线工作应建立具体补丁的恢复依赖表，而不是先做跨机整包：

| 拟改对象 | 可以借鉴／现在可做 | 放行前独立缺项 |
|---|---|---|
| FX3 RAM／设置最小试验 | 记录旧值、目标值、生命周期、保存行为、最小逆命令与同机receipt；先证不落盘再称纯RAM | 重启／服务退出是否足以回原；涉及硬件的影响不能从内存可逆推断 |
| appFw／av-cam／CP功能窗口 | 原件长度与hash、具体窗口原／目标字节、不同设置状态、逆patch；保存before与候选关系，完整目标文件回读；参照PR#25单点A/B | 所改程序失效时，Linux服务／sen进程／动态加载器是否还独立可达；需目标FX3证据。QAQ备份清单根本不含av-cam |
| FX3 updater／p1版本及输入门 | 对照YuuLuo的两层门控：当前7.02自己的库hash／符号／分派、保存标志、签名与机型准入逐一标定；仅完全同SHA才复用旧库语义 | p1本身半写或MAIN损坏后可用的更早入口；旧2.04／2.05 corecommon完全同hash不证明当前7.02机内p1相同 |
| 真正救砖 | 把先前官方研究追到的独立updater／sen，继续证明启动选择、看护依赖、可接受受限恢复请求、实际可覆盖的文件／分区 | 未发现这些A7CII源码在现有纯USB条件下提供不依赖故障层的启动器；Windows电脑本身不填补该缺项 |

### Gaps

- 没有FX3 7.02已完成的相机恢复回执；上述是可执行的离线研究任务，不是给用户的刷机步骤。
- 本轮只读网络／本地源码并生成本阶段笔记与小证据；未查询设备、USB、服务认证、管理员、GUI、Windows、UU、固件或下载代码执行；未安装依赖／未新clone。外盘UUID已核对为指定目标，Mac项目入口确认不是Git仓库。旧阶段、原件、canonical、README及memory没有改动。
