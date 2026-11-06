# FX6 Backup_nread 读取契约（修正版）与 92fe 生产链

- Task：`task_c325ed9e8329`
- Dispatch：`ctx_e375bfccafeb`
- 状态：**读取实现/生产链已核；FX6 正常启动/菜单仍未证明。**
- 卷：`/Volumes/KAFU2T` UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。
- 只读；未启动 VM/browser/server/QMP/guest/live-process，未触碰 camera/USB/SD，未改平台/包/候选/旧审计/协调账本。
- 只写本目录；输入 18 项前后 hash 不变；初版快照 `superseded/initial-20261105/`。

## 0. 修正结论

1. **CCMP 分支已按 Arm 语义修正。** inner：
   - `0x79c cmp w22,w24`
   - `0x7a4 ccmp w23,#1,#0,gt`
   - `0x7a8 b.eq 0x848`
   当 `actual==capacity` 时 `GT=false`，CCMP 将 NZCV 置 0（Z=0），`b.eq` **不跳**；只有 `actual>capacity && w23==1` 才进入 `0x848`。outer `0x1ef8 w3=1`，但 target 的两键 actual=4=capacity=4，**不会**走 `0x848`/既有 skip 分支。旧报告“4==4 进入诊断/既有 skip”结论撤回。
2. **有宿主 CCMP 实测。** Apple arm64 上用 clang 编译有限整数 `cmp/ccmp/b.eq` 测试（`tests/ccmp_test.s` + 最小 driver），覆盖 actual 0/1/4/5、capacity 4、flag 0/1；唯一 `b.eq=1` 是 actual=5,flag=1；actual=4 的两种情况均为 0。回执 `receipts/ccmp-host-test.json`，不是硬编码 JSON。
3. **读取长度使用 actual size，不是 capacity。** inner 以 `w22=Data_GetSize`，`w19=w22`，`0x7c4 uxth w2,w19`，复制长度=actual。capacity 只参与上面 CCMP 分支。
4. **`Backup_nread` 有两条目标指针路径，不能一概当 `memcpy`：**
   - `x20 <= 0x7fffffffff` → `0x7f0`：`Data_GetDataPt`，做用户范围/access 检查；检查失败 `cbz x4,0x7d0` **直接返回 actual 而不拷贝**；检查通过 `0x824 __arch_copy_to_user`，但 **copy 返回值未被检查**，`0x82c` 仍返回 actual。
   - `x20 > 0x7fffffffff` → `0x7bc`：`Data_GetDataPt`，`0x7cc memcpy`，返回 actual。
   - 因此 **返回 actual 不等于实际写入 actual 字节**；user path 的 access 失败/短拷贝都能返回 actual。appFw buffer 的实际指针/路径未在运行中抓取，**不能宣称本次一定走 kernel memcpy**。
5. **逐项读取行为：**
   - capacity4, len1：actual=1 <4；CCMP 条件假 → 0x7ac；copy 长度 1；成功写低 1 字节，高 3 字节保留；返回 1。
   - capacity4, len4：actual=4==capacity；GT 假 → CCMP NZCV=0 → b.eq 不跳 → 0x7ac；copy 长度 4；成功覆写四字节；返回 4；**不进入 0x848**。
   - missing：`Data_SearchId=0` → 0x868 w22=-1 → 返回 -1，buffer 不写；调用者初始 4 字节 1 保留。
   - len0：actual=0<4 → 0x7ac；copy 0；返回0；buffer不变。
   - actual>capacity, flag=1：进 0x848（诊断/`0x6d8`），随后到 0x7ac；w19 仍是 actual，**没有安全截断证据**；target 不触发。
   - actual>capacity, flag=0：CCMP 条件真但 w23(0)≠1 → Z=0 → 0x7ac；copy 超过 capacity；target 不触发。
6. **“单字节 00/01 仍合法”仅在限定条件下成立。** appFw 在 `0x11f675c-0x11f6768` 将 `[b4..c8]` 每个 4 字节槽初始化为 1（高3=00）；只有 1 字节 **成功复制**（或 access skip 且低字节仍 0/1）时，读后才是合法 0/1。未初始化高3、user copy 失败/部分失败、或任意值都不能保证；不是通用读取契约。
7. **target 4B `16/19` 的结论只能是有限推断。** 若 user copy 成功，4 字节会覆写 `[b4]/[c4]` 为非法值并触发 3147/3176；若 access 检查失败或 copy 失败，buffer 仍为 1，断言可能不触发。serial 有这两条 assert，支持“非法值到达检查”，但本任务没有运行时寄存器/指针/copy 成功计数，**不能证明实际写了几字节**。
8. **92fe 生产链：** `setting/Backup.bin`（2,229,740 B，SHA `92fe4031…`）在固定 FX3 base `guest.cpio`、`guest-three-entry`、`guest-cp-helper`、hybrid、`grmreal21/41/46` 全同。构建脚本只替换命名 member（simulation helper/appFw/backup.ko/upm.ko），**没有改写 setting/Backup.bin**；它是 base 镜像逐字节复制的静态文件。`Backup-generation4-fixed.bin` 同 hash，但 target QEMU command 不直接 load 它。
9. **实际导入/初始化：** initramfs `init` 只 `ls`/`sha256sum /setting/Backup.bin`，再 `insmod /usr/kmod/backup.ko Backup_load=1 Backup_save=0`；没有 cp/dd/重定向写。serial `FX3_FILE100_OBSERVER_READY ... O_RDONLY=1 no_native_data_writes=1`、`FX3_BACKUP_INSMOD_RC=0` 一致。**运行时写者/创建者未观测；上游生成 92fe 的步骤未闭合。**
10. **FX3 共享消费者未闭合。** FX3 appFw `545c…` 无 `set_model_for_boot_screen` 字符串；`model_api.cpp` 1 次、`Backup_nread` 字符串 3 次；两个 ID 的静态常量匹配弱（`0x2cf0214` 仅 BE=1；`0x2cf0218` 无），不能确认直接消费者，也不能排除间接/共享语义。因此不做数据迁移；migration dry-run 仅给出 12 字节窗口+checksum 范围且 blocked。
11. **无 VM/菜单通过。** 本任务仅读契约、生产链、离线/宿主整数测试；未实现任何 patch/veneer/return0/断言绕过，未修改候选或运行策略。

## 1. 实际实现位置

target CPIO `usr/kmod/backup.ko` SHA `6ae178d5…`；本地 `grm-fbinit/backup-bug-skip.ko` 与 target member 逐字节一致（脚本验证）。`.text` sh_offset=`0x68`。

| 项 | 地址/文件 | 证据 |
|---|---|---|
| `Backup_nread` | `.text+0x1eb8` / file `0x1f20` | `nm` 符号；`0x1ee8 down_read`、`0x1f08 up_read` 重定位 |
| inner helper | `.text+0x760` / file `0x7c8` | `0x788 Data_SearchId`、`0x794 Data_GetSize`、`0x7c4` copy 长度 |
| data ptr (kernel path) | `0x7bc` / `0x7cc` | `Data_GetDataPt` / `memcpy` 重定位 |
| data ptr (user path) | `0x7f0` / `0x824` | `Data_GetDataPt` / `__arch_copy_to_user` 重定位 |
| branch | `0x79c/0x7a4/0x7a8` | cmp / ccmp / b.eq |
| appFw init | `0x11f675c-0x11f6768` | `[b0]=0`; `[b4..c8]` 4-byte slots = 1 |

详细：`receipts/reader-semantics.json`、`disasm-backup-nread-outer.txt`、`disasm-backup-nread-inner.txt`、`relocs-backup-nread.txt`、`ccmp-host-test.json`。

## 2. CCMP host 测试

| actual | cap | flag | b.eq taken |
|---:|---:|---:|---:|
| 0 | 4 | 0 | 0 |
| 0 | 4 | 1 | 0 |
| 1 | 4 | 0/1 | 0 |
| 4 | 4 | 0/1 | **0** |
| 5 | 4 | 0 | 0 |
| 5 | 4 | 1 | **1** |

指令：`cmp w0,w1; ccmp w2,#1,#0,gt; b.eq`；编译器 Apple clang；纯整数、无固件/系统寄存器/VM。回执包含 source/binary hash、命令和输出。

## 3. 读取结果表

| 输入 | 分支 | 实际 copy 长度 | 写入/返回 |
|---|---|---|---|
| cap4,len1 | 0x7ac | 1 | 成功写1/高3保留/返回1；user access失败可0写入但仍返回1 |
| cap4,len4 | 0x7ac（**非0x848**） | 4 | 成功写4/覆盖/返回4；失败可0写入但仍返回4 |
| missing | 0x868→0x7d0 | 0 | 不写/返回 -1 |
| len0 | 0x7ac | 0 | 不写/返回0 |
| cap4,len5,flag1 | 0x848→0x7ac | actual 5（无截断证据） | 非 target；不推断安全 |
| cap4,len5,flag0 | 0x7ac | actual 5（无截断） | 非 target |

## 4. “单字节00/01合法”的准确范围

- 成立：本 appFw 调用点，高3已为零，1 字节成功拷贝到低字节（或 access skip 后低字节仍 0/1）。
- 不成立：任意调用者/未初始化高3；user access 失败或短拷贝；任意非0/1记录值。
- target 是 len4 16/19；成功 copy 时四字节全覆写；失败时不写而保留1。因此 serial assert 支持成功路径，但没有运行时 pointer/copy 计数。

## 5. 92fe 生产链

| CPIO | CPIO SHA | setting/Backup.bin SHA |
|---|---|---|
| base `guest.cpio` | `eaef24b2…` | `92fe4031…` |
| `guest-three-entry.cpio` | `bb618bd2…` | `92fe4031…` |
| `guest-cp-helper-agnostic.cpio` | `11adfbce…` | `92fe4031…` |
| `guest-hybrid-fx6kernel.cpio` | `1cc4f88e…` | `92fe4031…` |
| `grmreal21` | `238ff1b7…` | `92fe4031…` |
| `grmreal41` | `c1f15473…` | `92fe4031…` |
| target `grmreal46` | `3a08f89d…` | `92fe4031…` |

- Build scope：base→cp-helper 只换 simulation helper；three-entry→hybrid 只换命名 appFw；appfwfuture 只换 appFw；backupbug 只换 backup.ko；upmcallsite 只换 upm.ko。**均不改 setting/Backup.bin**。
- `init` SHA `642ce1c6…`：只 `ls`/`sha256sum` `/setting/Backup.bin`，然后 `insmod backup.ko Backup_load=1 Backup_save=0`；`init_has_copy_or_write=false`。serial `FX3_FILE100_OBSERVER_READY ... O_RDONLY=1 no_native_data_writes=1`。
- 92fe 来自固定 FX3 base；上游生成者/导入脚本未闭合；`Backup-generation4-fixed.bin` 只证明同 hash 文件存在。

## 6. FX3 共享消费者

- FX3 appFw `545c5053…`：`set_model_for_boot_screen` 字符串不存在；`model_api.cpp` 1 次；`Backup_nread` 字符串 3 次；`0x2cf0214` LE0/BE1，`0x2cf0218` LE0/BE0。静态常量搜索不足以证明直接消费。
- 同一 92fe 文件在两个 ID 上的 FX3 seed 值是 4B 16/19；共享数据风险不能排除。**不能确认 FX3 语义相同或不同，也不能据此选择迁移值。**
- 9d 有 screen marker、无 model assert，但 appFw/CPIO 不同；只作限制对照，不作因果证据。

## 7. Migration dry-run（blocked）

- record 0：offset 0，record bytes `857900`；
- affected data：`594516..594519`（ID 0x02cf0214，当前 `16161616`）、`594530..594533`（ID 0x02cf0218，当前 `19191919`）；
- checksum field `32..35`；scope `[0,32)`+`[36,857900)`；
- 保持长度/table 时，最小 12 字节（两个 4B 数据窗 + 4B checksum）可保持其他字节不变；
- `candidate_values=null`、`file_written=false`、`cpio_written=false`；状态 `blocked_by_unresolved_fx3_consumer_semantics`。未生成或安装 Backup/CPIO；未猜值。

## 8. 已知/推断/未知

**已知：** 实际 inner 条件/CCMP 行为、copy 长度 actual、user/kernel 指针两路、user copy 返回不被检查、return 不等于写入、missing -1 不写、len1/len4 分支与 target 不进 0x848、92fe 在 base 全同且构建不改、init 只读加载、FX3 无同名函数/弱常量、migration scope 12B。

**推断：** target 4B 16/19 若 user copy 成功会使 b4/c4 非法并触发 assert；若 copy 失败则可能保留1；serial assert 支持成功路径，但无运行时指针/计数，不能证明写了几字节。FX6 1B 00/01 在该 appFw 高3初始化下应可合法，但未运行验证。

**未知/缺口：** appFw 实际 x20 路径与 user copy 成败/字节数；actual>capacity 安全语义；FX3 消费者共享语义；92fe 上游生成者；修好后是否 screen/menu；actual runtime values。

## 9. 边界与交付

- 未设计/执行任何新 patch/veneer/return0/断言删除；无 VM/运行授权。
- `REPORT.md`、`RESULT.json`、`SHA256SUMS`；`receipts/reader-semantics.json`、`producer-chain.json`、`migration-dry-run.json`、`ccmp-host-test.json`、`test-run.json`、输入 compare；反汇编/重定位；tests source/output。
- 输入 18 项前后 hash 不变；5/5 离线脚本通过。审查完成不等于 VM/菜单/FX6 可开机。
