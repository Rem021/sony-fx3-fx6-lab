# FX3 首次设置持久化：AP95 → AP96

**结论：AP96 的 RAM 回放确已生效；导出的状态本身仍保留“强制设置时钟”标志。** 语言实际键 `02cf0000` 已为英文 `00`，UUD 版本原读值为 `4/4`；但 `clock_force_settled` 的实际键 `02cf0014` 及原 setter 的镜像 `01070140` 都仍为 `01`。boot 用 `date187==2 OR force1098` 判断设置入口，并在产品 feature `270` 路径选择 `fa / scr0099_0001`。这给出重复语言流程的直接存储侧解释 **B 强**；AP96 在判定瞬间的 `date187/1098` 寄存器未保存，不能升级为逐指令运行因果证明。（AP `2ec0564..56c、2ebfd1c..2c、2a6b564..5e8、2380464..488、2380628..648`；Backup 文件偏移 `8dd85、8eb51、6e7ac`；AP96 serial LF **1139–1140、13501–13513**。）

**最小诚实方案是补齐原日期事务及其后台持久化回执，再导出和回放。** 原成功路径会把 live `1098` 清零，原回调将其排为 daemon 类型 `5`，最后原 `Backup_write` 写上述两个键。当前 AP95 保存回执只证明设置页面已导航至 `screen0` 请求，明确保留“Creators App 说明帧、待机未证实”；它没有证明日期事务成功、回调消费或 force 两键已归零。尚未定位到这几者中具体丢失的一环，不能承诺“关机一次”或“改 checksum”便解决。（AP `2d7e6ec..740、2a69a68..aa0、2ab9028..50、2b2372c..34、2ebfd30..88`；AP95 serial LF **160579–160617**；`ap95-backup-after-setup.json`。）

## 边界与复现

2026-11-02，只读原件、既有 RAM 导出与日志；仅写本目录三个文件。未启动 QEMU、调用客体 API、执行固件、改 runtime/STATE/锁/种子或操作相机。目录不是 Git 仓库，未做 Git 变更。A=原字节/保存输入/直接观测，B=受约束推断，U=未证实；AP VA 为 `appFw.so` ELF image VA，本文涉及的 AP 文件偏移恰与 VA 相同。`backup.ko` 为 ET_REL，`.text+offset` 的文件偏移为 `offset+68`，不是加载 VA；每个 proof 代码窗口另存完整 raw、文件偏移及反汇编。

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/first-setup-persistence/audit_first_setup.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/first-setup-persistence/audit_first_setup.py --check
```

第一条退出 0 重建 [first-setup-proof.json](first-setup-proof.json)，第二条独立重提取并逐字比较、不写文件。脚本核卷 UUID、原库 SHA、47 条指令断言、语言的 34 项转换、daemon 跳表、原 RTTI/映射表、两个 BK4、20 项参数差异和 AP96 双重 SHA 回执；反事实只操作 Python bytearray，不生成修改后的 Backup。AP95/96 serial 分别只纳入前 **160625 / 13520** 个 LF 行，后续追加不影响复建；行号直接按字节 LF 计算，与某些旧 review 的 `splitlines()` 行号可能相差数行。

只读查询例：`audit_first_setup.py dis ap 2380464 28`、`dis backup.ko 6540 d4`、`xref ap 2ab9028`。不会执行被反汇编的指令。

| 原件 / 输入 | 固定 SHA256 |
|---|---|
| appFw.so | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| libbackup.so | `6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d` |
| backup.ko | `8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d` |
| 原种子 | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` |
| AP95 启动输入（AP88 导出） | `38cf44637c44d3f47d7b8541dddf7ecc443e262f40dec3aec59f7b94d5b8b38f` |
| AP95 设置后导出 / AP96 开机前物理读回 | `191924ef39d996171ae06ab4ca85e249b655b16db6b68fd1e2ddea45efc60bdc` |

`proof.sources` 保存完整真实路径、长度、SHA 和日志截断范围。AP95 启动输入来自 `runs/ap88cpr4-e71668cb/backup-after-shutdown.bin`，设置后来自 `runs/ap95v6r3ui600-3715c225/backup-after-setup.bin`；AP96 固定为 `runs/ap96v1replaydiag-0f72a1e0`。

## 1. 开机是否进入首次设置由谁判定

**A：语言是否为英文/日文不是 boot 选择 `fa` 的直接条件。** `scr0039_boot_controller` 的 `30072` handler 调 `237fe28`，读取日期、force、启动信息等，先处理 UUD 和特殊启动，再执行下表的普通选择。`fa` 的名表记录为 `scr0099_0001`；其原 RTTI/header `45761d8/45764c0` 的 init slot `+10` 为 `23af5d4`。该 init 初始化设置页相关模型、显示许可及订阅，所选范围没有重新从文件加载一个“first_setup_done”位。（AP `2380778..7a8、237fe28..2380774、23af5d4..730`；RTTI 字符串 `313aed8`；`proof.metadata/screen_names/code`。）

| 顺序 | 原条件与结果 | 原 VA / 文件偏移 |
|---|---|---|
| 入口 | 内部事件 `30072`；必要时等待原 boot future，之后读 boot information、`187`、cancel `185`、force `1098` | `2380778..7a8、237fe28..238017c` |
| 前置退出 | 特殊启动、电源/外部模式等分支可提前退出；不是单一首次设置位 | `238017c..2380308、237fc44..fd90` |
| UUD | `02cf1841 < 02cf1842` 时调度 reset，boot 提前 return；`4/4` 时继续 | `2827290..7348、238030c..334` |
| 特殊首屏 | `237fd0c` 还检查原启动信息、getter `294349c`、`16f0c60` 与接口 feature `22`；命中选择 `193` 等专用首屏 | `237fd0c..fd90、238039c..404` |
| 核心门 | `187==2` 生成布尔，与 `1098` 做 OR；结果 **0 → `2380620` 选择 `2e1 rep_boot`** | `2380464..474` |
| 产品例外 | 核心门非零时，`237fd94` 检查原 boot 信息两个字段 `==3/==2` 及 getter `293a8c8==0`；命中仍到 rep | `237fd94..fde8、2380478..484` |
| force 建立 | 非例外且原 force 为 0 时，原程序把 `1098` 设 1，再进入后续设置分支 | `2380488..4ec` |
| 后续产品状态 | getters `294ae94/294aebc` 可设置 `137e`；getter `294e134==2` 时还处理 `2938f00`、`293a580` 及 `27a8510`，最终 `w24!=0` 走 rep | `23804ec..628` |
| 语言页选择 | 余下路径调用 `1dcb654(270)`；为真时选择 **`fa`**，否则检查 feature `358` 及后续产品状态选择 `192/178/18e` | `2380628..6d0` |

这里 `feature270/358/22` 按原整数保留，没有用相同数字的 model 参数或猜测的机身模式给它们补名字。`rep_boot` 自身还会处理地区、引导等后续流程；`2324800..582c` 保存在 proof，但未穷举所有产品组合，不能把“走 rep”直接写成“已到拍摄待机”。（AP `1dcb654..680、237fd0c..fd90、2324800..582c`。）

`187` 枚举为 0 MANUALLY、1 FORCIBLY、2 NOT_SET、3 UNKNOWN；原 boot 还从 udate 当前时间类型重算它，type0/1 → 0、type2 → 2、type3 → 3。因此 RAM 中 `02cf01b4=0` 既不能单独证明用户完成日期事务，也不能代替 `1098`。AP95 与 AP96 都先用原 BY_BOOT API 初始化虚拟时钟并读回 type0。（AP `41359e0、2b63908..39b8、2b63c2c..c40`；两 run serial LF **1117–1122**；`helpers/seed-date-clock-v3.c`。）

## 2. 实际存储键、bank 与原写入者

**A：本次直接相关值全部在 AP primary bank，第二 BK4 中没有这些键。** 主 bank 位于导出文件 `+0`、物理 `404000000`，data `+35840`、总长 `d172c`；第二 bank 起点为 `round_up(d172c,1000)=d2000`，长度 `14e5ec`。原 `backupfile_get_cp_data` 使用 `Data_getAdrs(root,1)` 作为 CP 数据 DMA 的 AP 端目的区，所以把第二块称为“AP 中的 CP snapshot”有原码依据；它仍不是本轮已运行的 CP primary，不能据同样的 header 地址字 `04000000` 推导相同 backing。（backup `.text+5988..59e0、7030..70bc`，文件 `59f0..5a48、7098..7124`；`proof.backups`。）

| 用途 | 实际键 | AP bank 文件偏移 / 物理地址 | AP95 启动输入 → 设置后 / AP96 前 | 原码绑定 |
|---|---|---|---|---|
| 已选语言，模型 `54e` | `02cf0000` | `8dd85 / 40408dd85` | `01 → 00 / 00`，日文 → 英文 | `2ec0548..590、2ec0784..790、2a6be40..bec0` |
| 强制设置时钟，模型 `1098` | `02cf0014` | `8eb51 / 40408eb51` | **`01 → 01 / 01`** | `2ebfd1c..2c、2a6b564..5e8` |
| 上项原 setter 同时写的镜像 | `01070140` | `6e7ac / 40406e7ac` | **`01 → 01 / 01`** | `2ebfd30..88` |
| 日期状态，模型 `187` | `02cf01b4` | `9100c / 40409100c` | `02 → 00 / 00` | 映射表 `40f92c8..92e8` |
| UUD 当前/要求版本 | `02cf1841 / 02cf1842` | `9ce74 / 9ce78` | `4/4 → 4/4 / 4/4` | `2827290..7348` |
| 独立键，不能代 force | `02cf1840` | `9ce72` | `00 → 00 / 00` | 原单独 getter `2ebfd8c..9c` |

**A：不能按 `BKID_APP_setting_language=3fe` 构造真实语言键。** 名称表行 `414a6f0` 的确叫该名字，但原手写语言 getter/setter 明确传 `02cf0000`。脚本还对 getter 的 34 项跳表全部解码：raw0 → model0 ENGLISH，raw1 → model1 JAPANESE，其余到33保持对应。`02cf03fe` 在本次前后均为 `00`，不是选择语言所写的位置。（AP `414a6f0、3bca597、2ec0564..590、39a5ac8、2ec0784..790`；文件 `9187d`；`proof.language_conversion`。）

**A：force 不是只能关机时写入的状态。** 原回调登记表 `46e3468` 的参数 ID 为 `1098`、函数指针 `46e3478=2a69a68`。回调读取 live `1098`，调用 `2ab9028`，把当前布尔值存进类型 `5` 的后台队列记录；daemon 跳表 `3806ad8` 对应 `2b2372c`，随后调用 `2ebfd30`，经原 `Backup_write(2cf,02cf0014,...)` 及 `Backup_write(107,01070140,...)` 写两份。语言另走类型 `8` → `2b23750` → `2ec0744`；因此“语言已持久化”不能证明 force 的独立回调也消费了。（AP 上述 VA；switch base `2b22cf0`、type8 槽 `3806ade`；`libbackup+1ff0..2034`。）

原日期设置序列只有在 `2d7e6f4` 接到成功 return 0 后，才执行 live `force1098=0` 与 `date187=0`。原非零结果跳 `2d7e658`，不会越过这段写入；后面仍要通过模型通知/回调/daemon 才成为 Backup 两键的实际字节。当前保存资料没有该 return、live writes 或 type5 消费的专门探针，不能仅凭 UI 翻页判定它们发生过。（AP `2d7e618..634、2d7e6ec..798`；force current/next `8365c90/8365c91`，date current/next `8227358/822735c`；`proof.code`。）

**A：本链的持久文件是 `/setting/Backup.bin`，所定位的语言/force getter 不直接读取 `/usr/data` 文件。** 原 `Backup_pri_file` 与 `Backup_sec_file` 均为 `.data+480/+440` 的这个路径；`backupfile_init` 从文件头取地址字，经 `arch_p32_to_p64/arch_phys_to_cache` 得到 AP backing 并调用 `Data_init`。`Backup_write` 修改当前数据，后台 sync 路径与原 `Backup_sync_all` / `backupfile_save` 另有磁盘步骤；这证明 RAM 写与文件保存是不同回执，不证明本次有 flash 写入。（backup `.text+6540..6610、3010..311c、6800..6a60`，文件偏移分别 `65a8..6678、3078..3184、6868..6ac8`；`proof.native_Backup_files` 给出字符串实际文件偏移。）

当前 profile 明确 `Backup_load=1 Backup_save=0`，本次没有原文件 save/readback 成功回执；不把该配置单独解释成“任何显式 sync API 都不可能写文件”。也未穷举隐私、手机、HOME 等全部独立持久状态，不能据这条 getter 链宣布这些流程绝无其他文件依赖。（AP96 init 行 **102、256、264**；backup `.text+3010..311c、6800..6a60`；`proof.init_order/unproven`。）

## 3. checksum / flags 会不会使回放被拒绝

**A：该导出确实不是已校验的存储文件。** 原种子的两个 checksum 都有效；AP95 设置后 AP bank 保存的 checksum 仍为 `018adbdb`，对当前 RAM 重算为 `018ae2b9`，不同；CP snapshot 仍为 `09443bb1`，有效且与原种子逐字节相同。AP95 启动输入的 AP checksum 原先也已不匹配，计算值 `018ae230`，所以不能把“本次首次出现 mismatch”当作失败原因。（文件 header `+20`、bank0 `0..d172c`、bank1 `d2000..2205ec`；`proof.backups/CP_snapshot_unchanged_from_seed`。）

原 checksum 规则是暂存 `header+20`，将该 u32 清零，逐字节加和指定长度，恢复旧值并返回 u32 和；和为 0、fffffffe、ffffffff 时返回 1。save 再以 `Data_SetChecksum` 写入真实结果，且有 cookie、count、完成字段及双文件选择逻辑，不能只改 checksum 就声称是原正常保存。（backup `.text+5938..5980、5920..28、5ab8..5c7c、6800..6a60`，文件 `59a0..59e8、5988..5990、5b20..5ce4、6868..6ac8`。）

header `+8..b` 的值 `00000100` 也不应笼统叫“坏 flags”：按字节实际为 `WriteComp(+8)=0、SuspendComp(+9)=1`，有独立原 getter/setter。它们与文件选择/保存协议相关，不能无原事务把整个 word 清零。（backup `.text+58a8..58ec`，文件 `5910..5954`；`proof.backups`。）

**A：当前回放时机已经晚于原 backup 模块加载，普通读路径不在每次读值时校验全块 checksum。** AP96 init 行102先加载原 module，行256回放，行264才准备启动 AP；原 `Backup_nread` → `760` → `Data_SearchId/Data_GetDataPt` 直接从注册的 primary 指针取值，没有全块 checksum 重算或拒绝分支。AP96 原 UUD getter随即读到4/4，标题为英文，符合这条路径。（backup `.text+1eb8..1f20、760..868、4ef8..4f54、5350..539c`；AP96 serial LF **13501–13513**；[AP96 设置前 PNG](../../../menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/ap96-phaseA-before-SETUP.png)。）

因此 **B 强**：现有回放没有因 checksum/flags 而整体退回种子；重复首次设置可由导出中未清除的 force 标志解释。脚本另做只修 checksum 的内存反事实，force仍1、设置门仍真，不能解决这条条件。若改成“文件输入，在原模块初始化前加载”，将进入文件/头选择与加载路径，需另外满足原合同；本审计没有实施，也没有建议对当前 live RAM 盲修 checksum。（AP `2380464..488`；backup `.text+6540..6610、66a8..6798`；`proof.checksum_only_counterfactual`。）

## 4. AP95 差异与 AP96 实际观测的证据边界

脚本从两个真实 bin 独立重算 AP 全部有效条目，并核对 `runtime/ap95v6r3ui600-3715c225-backup-after-setup-keys.json`，得到相同 **20 项变化**。比较的“前”是 AP95 启动时使用的 AP88 导出，包含 AP95 boot 与 UI 设置全部期间，不能把所有差异归到某次点击。（输入 SHA 见开头；`proof.AP95_parameter_diff_recomputed/AP95_before_origin`。）

20 项 key 为 `0090000d、01070000、01070001、01a1000f、02cf0000、02cf0007、02cf0073、02cf00d3、02cf00dd、02cf00e2、02cf0104、02cf0105、02cf013c、02cf01b4、02cf0233、02cf1464、02cf1465、02cf14a5、02cf14a6、02cf14a7`。完整 attr、前后 raw、文件偏移在 proof；除已由原码绑定的语言/日期外，不按相似名称给其他键补产品语义。**关键的 `02cf0014/01070140` 不在变化集合中，两者仍1。**（两个 bin 的原索引/数据条目；force 原 setter `2ebfd30..88`。）

| 可验证事实 | 等级与限制 | 定位 |
|---|---|---|
| AP96 guest remap SHA 与宿主 QMP 读回 SHA 均等于 AP95 导出 | A；回放 bytes确实一致 | serial LF1138–1140；`ap89-input-before-AP.bin`、`ap89-host-input-readback.json` |
| AP96 原 UUD 读取4/4、返回false | A；真正 AP 启动后的原 getter 观测 | LF13501、13503；原调用 `28272b4` |
| AP96 再次请求 `2ae → fa` | A；是入口记录，并非全局 screen 提交完成 | LF13513；原 `2380644 / 218fd0c` |
| AP96 PNG 标题为 Language | A 目视；支持语言恢复，不是1098寄存器回执 | `ap96-phaseA-before-SETUP.png`，SHA在sources |
| `force1098=1` 是本次 boot 分支原因 | B 强；存储1+原初始化链+实际fa吻合 | `02cf0014@8eb51`、`2a6b564..5e8、2380464..488` |
| AP96 在2380464瞬间 `date187=0/force1098=1` | U；没有保存该点寄存器或独立 live getter 返回 | 当前只有 pre-AP bytes 与 UUD原读，未伪造“实际读值” |
| AP95 真正完成原日期事务并持久化force0 | U；导出的两键仍1；保存说明保留待机未证实 | `ap95-backup-after-setup.json`；原 `2d7e6f4..798` |

AP95 的 `backup-after-shutdown.bin`、`backup-reserved-ram.bin` 此刻与 `backup-after-setup.bin` SHA相同；名称不能证明原 shutdown/save 完成。原始快照和历史回执保留，本审计没有为这些文件重新标注“正常关机后的有效存储”。（真实导出 SHA；AP95 保存回执；原 save路径 backup `.text+6800..6a60`。）

## 5. 运行链的最小下一步（本 worker 未实施）

1. **先补原事务证据。** 在 `2d7e6f4` 保存真实return，随后 `2d7e73c/740` 保存 live current/next `1098`，并采日期状态。失败则跟踪原 `80900141` 日期服务返回，不预先把“UI确定”当成功；没有该请求的完整捕获不能补猜成功包。（AP `2d7e618..740、2f72484..4c8`，后者原日期请求路径见既有首屏审计；本 proof 保存前者。）
2. **跟到原 AP Backup 字节。** 依次观察回调 `2a69a68`、队列生产 `2ab9028` 的类型5/实际值、daemon `2b23730`、setter两次原 `Backup_write` return，最终原 `Backup_nread` 读回 `02cf0014=0、01070140=0`。若原事务已成功而此处停住，修复原模型通知/daemon消费的真实等待，不直接调用 setter、清 flag 或造完成事件。（AP `46e3468..3478、2a69a68..aa0、2ab9028..50、2b2372c..34、2ebfd30..88`。）
3. **保持现有 RAM 回放时机。** 在原回调实际写完、相关值读回后保存同一预留区；下次仍在原 module load 后、AP 启动前回放。要求存储force0、日期实际为已设type、UUD4/4，且在 `2380464/2380644` 直接观察不再选语言页。该条件会先走rep等原流程；拍摄待机、MENU和可见像素另外验收。（AP `2380464..6d0、2324800..582c`；AP96 init顺序。）
4. **若要文件持久化，作为后续独立任务。** 走原 daemon drain / sync / shutdown save并保存真实返回、文件SHA与下一次加载读回；`Backup_sync_all` 先取 CP 数据，不能在CP合同缺失时直接假定成功。原 save有 checksum、count、cookie与完成字段的整套次序；RAM导出不改名冒充文件。正常关机可能补齐该路径，**是否能补上本次force0仍U**。（backup `.text+3010..311c、2ba8..2c90、6800..6a60`。）

**尚未证实：** AP95 日期调用的真实返回/live1098、后台type5是否执行和为何未写0；AP96判定点寄存器/后启动两键独立读回；全部rep/隐私/手机/HOME产品组合；有效持久文件或原正常关机保存；CP primary地址绑定；修正后连续开机、待机、MENU及实机效果。离线脚本 PASS 只表示本文字节与保存事实可以重建。（对应上节VA/文件偏移及 `proof.unproven`。）

方法于2026-11-02核对 [Capstone 官方 Python API](https://www.capstone-engine.org/lang_python.html)；工具文档仅支持反汇编方法，Sony私有状态语义均来自上述固定原件及运行保存材料。
