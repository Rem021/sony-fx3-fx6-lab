# FX3 普通设置：RAM、空闲子系统保存与正常关机保存

**语言改值已经写入 RAM；不能把“没有 op30 / Backup_sync_all”解释为原厂只在关机保存。** AP101-r4 最终 RAM 的 `02cf0000@8dd85=00`，最终 `/setting/Backup.bin` 仍为 `20`；前者 English、后者 Portug.(Brasil)。原厂另有 **队列空闲约 2 秒 → `Backup_sync_subsystem(2cf)` → 读取旧文件、合并该子系统、保存文件** 的路径，不走 op30。当前缺口应优先定位这条路径的门控、独立 DMM 临时区申请与真实返回值。（AP `2a69974、2ab90a4、2b23750、2ec0784..790、2b22b24..2b22cc4、2ebf650`；backup `.text+2ea0/2ed8、2ca0、3f0..6b4`；保存原件见第 1 节。）

**`execute_sync_all_if_necessary` 不是普通改值的通用 dirty flush。** 它只在 `8e5dc38!=0` 时清该位、排 type14 并等待；置位函数 `2ab8470` 的 8 个直接调用点都在 boot/clock 链，语言回调不调用它。正常关机另有 AP 业务收尾、UPM/CP 通知和内核 shutdown 保存步骤（与显式 suspend-save 分开）；完整电源开关输入尚未闭合，所以本审计不给一个猜测的关机包，也不把直接注入 `3002c` 当正常电源操作。（AP `2b04738..480c、2ab8470..84a4`；全部直接调用点见第 3 节；backup `.text+28..58、3138..31cc`；UPM `.text+7040、7ba8、8178、b270`。）

2026-11-02，只读静态审计；仅写本目录三文件，未启动 QEMU、执行 ARM 指令、发送输入、改 runtime/STATE/锁或操作相机。A=原字节/固定保存资料，B=受约束推断，U=未证实。AP/用户库地址为对应 ELF image VA；backup/upm 是 ET_REL，本文 `.text+offset` 是节偏移，**不是固定运行 VA**。proof 保存文件偏移、连续原字节、Capstone 指令、重定位、表与输入 SHA。

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/backup-save-trigger/audit_save_trigger.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/backup-save-trigger/audit_save_trigger.py --check
```

第一条退出 0 重建 [save-trigger-proof.json](save-trigger-proof.json)，第二条重新提取后逐字比较、不写文件。脚本核 UUID、7 份原 ELF/module、35 条关键指令、11 条重定位、daemon/产品跳表、全 `.text` 直接调用者、固定 RAM/文件与 30 份文件读回；不把离线 PASS 当成运行修复完成。[audit_save_trigger.py](audit_save_trigger.py) 还支持 `dis ap 2b22a6c 380`、`dis backup 3f0 2e8`、`dis upm 7ba8 598`。

## 1. AP101-r4 保存资料独立复核

来源固定为 `runtime/runs/ap101r4tile600-be9996d0/`。脚本独立解析 BK4 索引与 checksum；所有文件读回均核真实 bin 的 SHA，未只信 JSON。语言 raw/model 的对应来自原 getter `2ec0548..570` 的 34 项转换、原 setter `2ec0744..930`；`00=English、20=Portug.(Brasil)`。（proof `AP101_saved_language_RAM_vs_file`、`file_readbacks`、`verified_file_readbacks`；原键写入 `2ec0788`。）

| 保存物 | SHA256 | 语言字节 / AP checksum |
|---|---|---|
| 原文件、原模块加载前保存 `Backup-native-file-native-load-before-AP.bin` | `552fd5f8b422f855aecbe0c3918b56f83f60fb76ea9a3b6fc7a0291c26035d9e` | `20` / 有效 |
| 最终原文件 `Backup-native-file-final-before-shutdown.bin` | `eb70e888c27766b52d4e27f4353bc73d63fac325c6bb545d478bd156f588b26e` | **`20` / 有效** |
| 最终 RAM `backup-reserved-ram.bin` | `a20f0c92a790c0f911c443fab1eee204316f443ddb764d75e19d97eeea992fd6` | **`00` / RAM 当前和与旧头不符** |

`periodic-01` 已出现原文件 gen2，时间早于第一步 MENU；其后包括语言确认、MENU 关闭与最终读回一直是相同 gen2/SHA。这里 gen 是只读观测器的内容代次，不是厂商头部的 count 字段。因此不能写“整个 run 完全没写过文件”，准确结论是“已观测的改语言之后未保存该新值”。RAM checksum 不符符合修改数据而尚未重新制备存储头，不能据此修 checksum 或宣称 RAM 写被拒。（proof `verified_file_readbacks`；原保存重算 checksum：backup `.text+6888/6894、68f0/68fc`。）

**计时范围要分开：** 任务描述给出约 450 秒；本轮保存的宿主 gate/readback 时间可独立计算为：step10 确认输入发送 `242075.010826333` → 最终文件读回 `242348.790909833`，约 **273.78 秒**；step11 已看到 English、发送 MENU `242141.354516375` → 最终读回约 **207.44 秒**。这是宿主单调时钟，既不是精确参数提交时间，也不能与 guest printk 的秒数等同；本审计不独立认定 450 秒墙钟。（proof `host_input_timing`、真实 `ap101-host-input-gate.json`/`ap101-native-file-readbacks.json`；无 VA，因为这里是保存观测。）

## 2. 语言：参数 setter → model callback → type8 → RAM

| 步骤 | 原指令证据与结论 |
|---|---|
| 参数事务 | `29390e0/29390f4` 给语言 current/next；例如原事务片段 `2af9598..95d8` 建 ID `54e`、调 `2ac0ec0`，随后变更时调 `275aadc`。这个片段证明 setter 合同，不声称已恢复本次菜单每个 controller 的精确 PC。 |
| setter | `2ac0ec0..0f10` 调通用 `2f6e7ac`，将结果写 next/current，置事务 changed `+14=1`。注册记录 `46e34c8` 的参数 `54e`、callback 指针槽 `46e34d8=2a69974`。 |
| 模型回调 | `2a69974..99ac` 在原模型锁下读取 `29390f4` 的 live 值，`2a69998→2ab90a4`；后者构造 12B 记录 `{type=8,value,0}`，`2ab90bc→2ab8e04` 入队并 notify。原批处理回调消费器 `2a6dc04..dc40` 调有 dirty 标记的函数指针；`2739610` 调它。 |
| daemon | `2b22cc8..2b22cec` 查 `3806ad0`，type8→`2b23750`，取记录值，`2b23754→2ec0744`。 |
| 写 Backup RAM | setter 转换模型枚举后在 `2ec0788` 固定键 `02cf0000`、`2ec078c` 子系统 `2cf`，`2ec0790→Backup_write`。libbackup `1ff0..2034` 到原 kernel；kernel `Backup_write .text+2728→d8`，查索引/取数据指针，`.text+244..254` 走 memcpy 或 `.text+258..264` copy_from_user，再解锁返回长度。该函数不调用文件 save。 |

**A：不是在 UI setter 同一栈立即写 RAM，而是异步 type8 消费后写。** 一旦 daemon 消费到 `2ec0790`，原 `Backup_write` 在本次调用返回前复制字节；AP101 最终 RAM 为 00 已补上数据端的实际结果。没有逐点保存本 run setter/callback/type8 的返回 PC，不能把静态顺序说成逐步运行捕获。（上述 VA；最终 RAM 文件偏移 `8dd85`。）

## 3. 全量同步请求位：只查到 boot/clock 直接置位

`2b04738` 读取 **`8e5dc38`**；零则直接 `ret@2b0480c`。非零在 `2b0474c` 先清位，再 drain 当前设置、排 `{type14,wait=1}`，busy `8e29f20=1`，在 `8e31a60` 条件变量等待。daemon type14 `2b23820→2ebf66c→Backup_sync_all`，收尾清 busy/notify；返回 0 或 notify 本身不替代原文件读回。（AP `2b04738..480c、2b23804..3824、2b237b4..37f8、2ebf66c..680`。）

原置位函数是 **`2ab8470`**，在模型锁下 `strb 1,[8e5dc38]@2ab8490`。全 appFw 可执行节的立即 `B/BL` 调用者只有以下 8 个：

| 置位调用 VA | 所属已绑定路径 |
|---|---|
| `23804e8` | boot 在日期/force 门要求建立 force 后 |
| `2b7270c、2b72894、2b72a18、2b72eb0、2b73198、2b734a0` | 原 clock/date sequence 的写后阶段；例如成功初始日期分支 `2b726d8..2728` |
| `2d7e7c8` | 原日期/force 成功收尾；`2d7e6f4` 返回 0 后才进入 `2d7e6ec..7d8` |

`27395e8..9634` 的原模型批处理收尾（回调→设置 drain→`2739620`）是 `execute_sync_all_if_necessary` 唯一立即 `B/BL` 调用者。语言/普通参数变更只走常规模型 dirty，不自动把这个独立全量同步请求位置 1；这与 AP100 日期/force 后发生 full sync 一致。**范围限制：这是直接调用全量扫描，不声称排除所有任意间接写/指针调用。**（proof `direct_branch_xrefs`；`2a69974/2ab90a4` 对照。）

`sync_and_wait_comp@2b04674` 是 type13 子系统同步；不是 type14。其直接调用者还包括 `16fd00c` 特定远程命令、`2b7d268` 的 `sequence_cube_file_backup_sync`、`2dcef98` 的专用序列。非等待 type13 `2b04634` 在 `2773c8c` 被调用。不可把这些专用操作当成所有 MENU/模式/媒体事件的通用保存回调。（AP 上述 VA；proof 对应窗口与 xrefs。）

## 4. 真正的普通自动保存：空闲约 2 秒，局部文件合并

**A：定时/空闲保存存在；不是每隔固定时间无条件全量保存。** daemon `2b22b24..b80` 在队列为空时取 `system_clock::now`，加 `0x77359400=2,000,000,000ns`，转成秒/纳秒后调 `pthread_cond_timedwait`；收到新工作会继续消费，只有持续空队列超时才走后段。（AP `2b22b24..2b22bb0`。）

超时后还须 **`8e29f24==0`、原局部 dirty `w19!=0`、`16f0bd0()==0`**，才在 `2b22cc0` 调 `2ebf650→Backup_sync_subsystem(2cf)`。type8 处理后走 `2b22d9c` 更新该工作标记；idle 尝试后会清本轮 `w19`，不是永远重试失败保存。（AP `2b22c70..2b22cc4、2b23750..758、2b22d9c`。）

- daemon type15 `2b23828..384c` 清 `8e29f24`；type16 `2b23850..3874` 置 1。原 `2b03ffc` 检查 getter `292d6a8` 与缓存 `8e31a58`：值转到 1 时排 type16，离开 1 时排 type15。这里只保留原字段和值，未把它猜命名为“正在录像/菜单打开”。（AP `2b04034..4098、2b04130..416c`。）
- 产品门 `16f0bd0` 使用 `47ce0a8` 作 `2f99f88` 的索引。原产品 enum `PRODUCT_MODEL_ALCIN_UUD=4`（表 `4174850`）经 `16f0a20`/跳表 `2f99ab0` 映射成 index6，该表值为 **0**，所以正常 ALCIN_UUD 映射下产品门允许空闲同步。没有本 run 的实际 index/f24/w19 探针，不能据此宣称这一次已调用成功。（AP `16f0a20..ac4、16f0bd0..be4`；proof `product_sync_gate`。）

原文件局部合并完整主链：

```text
AP 2ebf650：Backup_sync_subsystem(2cf)
  → backup .text+2ea0 → __backup_sync_subsystem_mp .text+2ca0
  → lock_load_and_save → .text+3f0(sid=2cf, bank=0, option=0)
  → backup_senser_malloc(request_capacity=400000)
  → backupfile_get_filename(0) → backupfile_load_file 到独立临时区
  → Temporary_Data_init(当前RAM bank0)、Overwrite_Data_init(临时旧文件 bank0)
  → 按 sid=2cf 的索引/长度，从当前RAM逐项复制到临时旧文件
  → backupfile_save_file(0, temporary_image, original_size) → free → unlock
```

证据是 backup `.text+2ca0..2cf8、3f0..6b4`；实际复制 `.text+5ac`、保存 `.text+610` 为原 relocation。**这条路径不调 `backup_get_cp_data`，没有 op30 和 PCI DMA 是正常的。** 不应为“看到 op30”而强行增加一次 full sync。（与 full sync `.text+306c..3078` 对照。）

**新增前置依赖：独立 DMM 临时区。** `backup_senser_malloc .text+8fd8..9290` 创建本次动态 Q，以 `61003c` 发送 40B DMM op20、unit **`001a3917`**，检查回复 status、容量至少请求的 `400000` 后才返回物理地址；`.text+90dc` receive timeout 原值 `ea60`。调用者还检查物理地址的 cache 属性，失败即返回错误，未进入文件写。这与 AP100 full sync 的既有 bank/DMA 路径不同；本轮未捕获该 DMM 请求、实际返回或失败，**“它导致当前未保存”仅为候选，不是已证根因**。（backup `.text+40c..438、674..698、907c..90e0、9104..913c`。）

另有 **libbkdmn**：`bkdmn_write@27ec` 写 RAM 后置 dirty/排 timer；`bkdmn_timer_set@23cc` 用注册对象 `+20 ×1,000,000` 的配置延迟；`bkdmn_sync_sub@22c0` 对注册的 subsystem 调原 sync。语言 type8 直接调用 `Backup_write`，appFw dynsym 无 `bkdmn_*` 导入；未找到语言注册到该 daemon 的证据，不能把其配置计时器套到语言上。（libbkdmn `2814..2838、23cc..2468、22d0..22d8`；proof `external_timer_boundary`。）

## 5. MENU、模式、省电、电池/卡：逐项边界

| 事件 | 原代码能支持的结论 | 尚未证实 |
|---|---|---|
| MENU 关闭 | 普通模型收尾会到 `2739620`，但 `8e5dc38=0` 时不全量同步；空闲子系统保存仍按第 4 节的共同条件执行。 | 没有闭合每种菜单退出 handler；不把 MENU 无新代次归为设计上永不保存。 |
| 模式切换 | 同一普通 flush/daemon 门有效；另有 `2773c8c→2b04634` 的专用 type13 调用。 | 未穷举全部 mode transition；不承诺切模式必定保存语言。 |
| 拍摄待机的显示变暗/关屏 | 不能把显示控制与系统 suspend 等同。`sequence_start_power_save_state@2daeaa4→2dae7a0` 调原电源保存请求、VDF `2dcfbd4→2df5090`、SYS `2dd8a94`，窗口内无 Backup full sync。 | 上述 SYS/UPM 后续是否对当前配置真正进入内核 suspend，需要运行回执。 |
| 系统 suspend / 正常关机后段 | 原 backup shutdown callback `.text+28` 在 `Backup_bin_start!=0` 时调用 `backupfile_save(0)`；另一命令入口 `.text+7b78→Backup_sync_all_for_suspend@3138→backupfile_save(0)@3174`。保存使用当前两个 bank，不在这一步重新 op30 拉 CP。原 suspend 槽 `.data+3e0→.text+20` 本身只返回 0，不能把 suspend 等同保存。 | shutdown callback 到实际原内核 PM 的调用闭包、CP snapshot 最新程度、所有前置设备均成功仍未证。 |
| 电池事件 | 若原 off-factor 进入正常关机，则走 UPM 关机状态机；UPM `7040、7ba8、8178` 包含 APP/CP/GINF 收尾。 | 未闭合每种电池低电量、拔电池、紧急断电因子；不能承诺突然断电仍能保存。 |
| 存储卡插拔/挂载 | 有具体原 `libInfraMediaCommon+475ec/475f0` 调 `Backup_sync_subsystem(d5)`，说明媒体也有自己局部保存。 | 这是 `d5`，不是语言所在 `2cf`；未证卡事件会顺带保存 APP 语言。 |

表中“无直接调用”仅限已保存窗口/立即调用关系；没有把未穷举的回调图当成全程序否定结论。上述具体窗口与表均在 proof，不以别机源码补私有语义。

## 6. 正常关机链与还可能遇到的依赖

**AP `MODEL_POWER_OFF=3002c` 是通知结果，不能充当物理电源输入。** 既有 boot-screen 审计已绑 `InfraNotify` 的 `2a8aa10..aa20` 发布、boot handler `237fb50` → shutdown；本轮继续核对 shutdown init `2381bbc→2381a60` admission 后 `2381c50→285d238→285c658`。在正常 reset_type=0 下，不会去跑 UUD 专属 flags1/4 reset；type3 分支才在 `285d118/124` 做两次 reset。不能为普通语言保存重走 reset 或修改 UUD。（AP 上述 VA；[既有 boot-screen 审计](../boot-screen-controller/README.md)。）

AP 关机业务与内核存储保存不是同一回执。`sequence_power_off` 的 RTTI/虚表关联到 run `2d412ec`，其范围内先做 SYS 请求 `2d413d0→2dd6794→2e3a19c`（目的 `90030001`，cmd4022），再做蓝牙/音视频等回收与声音、面板及 HDMI 相关等待。`2d418dc..18e0` 等 system sound 完成；另有 panel 与 HDMI future/condition 的后段分支。备份模块的 `.text+28→6800` 和 `.text+3138→3174` 分别是 shutdown callback 与显式 suspend-save 命令，**本审计没有证明当前 VM 已自然走到这些点**。（AP `2d412ec..42c4c` 的保存窗口；backup `.text+28..58、3138..31cc`。）

在当前模型上应预留以下独立门，不能因第二次 `0x119` 已修就宣布正常关机无其他依赖：

| 门 | 证据及限制 |
|---|---|
| 重复面板控制与关屏 | AP88/95 已知重复 119 断言由协调者后续修复；本轮未运行复验。prepare_power_off `2d43c80→2dcfbd4→2df5090` 实际还会发 VDF **14e**（`2df52f8`）；随后 `2d43ce4→2dd0094→2df3d08` 构造 **118**（`2df3d3c`）。不把 14e 与 119 混为同一命令。 |
| 声音、panel/HDMI异步完成 | `2d418a8` 发系统声音请求、`2d418dc..18e0` 检查/等待；poweroff 后段有对应 mutex/condition 回路。当前具体请求、callback 身份与功能可用性需实际捕获，不能只造完成事件。 |
| UPM 的 CP/GINF 收尾 | UPM `k_upm_off_factor_handler_inacting_cp@7ba8` 等待指定通知（`7c68..7c78`），读取 CP Backup 配置后继续发送 CP/系统收尾；GINF 后段 `8178`。仅有 appFw 3002c 不提供这套依赖。 |
| 内核 suspend 各模块 | `k_upm_suspend@b270` 依次调用 fan、hours meter、heat、battery、MSS、PCIe、DFS、power_save、CP-comm 等原 hook。这里只列静态原调用，不声称它们每一个都是当前已知阻塞；是否进入、哪个失败需运行证据。 |
| 原文件与数据完整性 | `backupfile_save(0)` 仍需有效当前 bank、路径/权限、完整 `filp_open→vfs_write→close` 与头两阶段写入。CP 数据新鲜度和文件完整写入分别验收，最终关机/物理掉电另外验收。 |

**回调槽位已绑定，不能混用 shutdown 与 suspend。** 原模块 `.data+378` 指向 ops `.data+3c0`；Sony [FX3 7.00 GPL](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html) 的 `UDIF_DRIVER_OPS` 顺序为 init/exit/probe/remove/suspend/resume/shutdown，当前原 relocation 的 `+20`（`.data+3e0`）指向 `.text+20`（返回 0），`+30`（`.data+3f0`）指向 `.text+28`（save）。另由原 dispatcher 跳表确认 **op35→.text+7b70→Backup_sync_all_for_suspend**；它是软件 API 命令，不是可以代替电源开关的输入帧。GPL 仅作结构 ABI 参照，当前私有实现由模块字节/重定位绑定；完整平台调用仍 U。（proof `native_driver_ops`、`backup_command_dispatch`。）

**物理电源开关原输入尚 U。** UI 名表 `4164dc8` 的 `TACT_POWER=1` 在配对表 `2f8f8e0` 映射 InfraInput **2**，但它的名字是 tactile power，不足以证明 FX3 主电源滑动开关就是该消息。未恢复该滑动开关→CP/SysCon→UPM off-factor 的完整当前型号原帧，也没验证现 VM 接收者；因此不建议试发 `key2` 或直接伪造 `3002c`。正常电源方案应先补输入合同和实际捕获，保留由原 UPM 生成通知/收尾的次序。（原表与上述 UPM/APP VA；该表在 proof metadata 中复核。）

## 7. VM 中最小诚实下一步（未执行）

1. **首选：把已有普通保存路径的事实补齐。** 在下一轮原菜单改语言后，只读采 `2a69998→type8/2b23754→2ec0790` 的实际值/返回、RAM key；随后采 daemon 空队列、`f24/w19`、`16f0bd0` 与 `2b22cc0`。若进入 kernel，则采 `.text+2ea0/2ca0/428`、DMM unit1a3917 原包/真实返回、`.text+460/610`、`Backup_sync_subsystem` 返回。保留原错误，定位到哪一步再修哪一步，不直接补调 full sync。（第 2/4 节 VA。）
2. **可复用现模型的原厂 UI 候选：确认一次日期设置。** 语言留在 RAM 后，通过原 Setup > Area/Date > Area/Date/Time Setting 的日期确认走原 clock 事务；原成功路径会调用 `2ab8470` 置全量同步请求，再经 `2739620` 自然排 type14、op30/DMA/解锁/原文件 save。相比补整套电源开关链，这是目前静态有据且已具 AP100 相关后端的较小候选；相同日期是否走成功分支、界面导航与新文件结果仍需实际采样，不能把本建议称为已验收触发。（AP `2b7270c` 等六处、`2d7e7c8`；`2b04738/2b23820`；backup `.text+3070/30f0`。）
3. **正常关机作为独立完整验证。** 补原滑动开关/off-factor 输入后，观察原 InfraNotify→shutdown admission→设备收尾→UPM→backup shutdown/显式suspend-save保存；可在后续真实 GPIO/电源断言前停止 VM，但只有已读回原文件新 SHA、语言00、两 bank checksum/count及下次原 loader 读回，才算存储完成。当前没有可宣称闭合的“一条原电源包”。（第 6 节 VA；backup `.text+40/3174/6800`。）

**明确未证实：** AP101 空闲门的实际值、局部 sync 是否执行/为何失败；DMM1a3917 原请求/分配/释放；所有菜单/模式/电池/媒体间接事件图；完整主电源开关原输入；normal shutdown 到真实内核 shutdown callback/显式 suspend-save 的闭包及各设备/CP依赖；日期候选或关机候选实际保存语言；文件真实介质耐久性与相机效果。脚本仅证明原字节与已保存资料可复建。

方法于 2026-11-02 核对 [Capstone 官方 Python API](https://www.capstone-engine.org/lang_python.html)；它只支持反汇编方法，Sony 私有语义来自本地固定原件。已有 [Backup op30/DMA 审计](../backup-sync-cp/README.md) 与 [首次设置持久化审计](../first-setup-persistence/README.md) 作为上下文，本文新增结论均在自己的 proof 保留原字节。
