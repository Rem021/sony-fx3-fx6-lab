# FX6 Backup_nread 读取契约与 92fe 生产链

- Task：`task_c325ed9e8329`
- Dispatch：`ctx_e375bfccafeb`
- 状态：**读取实现与生产链已核；FX6 正常启动/菜单仍未证明。**
- 卷：`/Volumes/KAFU2T` UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。
- 只读使用 target CPIO 实际 member、冻结 serial、FX6/FX3 模板、既有 BK4 parser/index；未启动 VM/browser/server/QMP/guest/live-process，未触碰 camera/USB/SD，未改平台/包/候选/旧审计/协调账本。
- 只写本目录；18 项输入前后 hash 不变（`receipts/input-seal-compare.json`）。

## 0. 结论

1. **实际 `Backup_nread` 不是按容量 4 固定拷贝。** target CPIO 实际成员 `usr/kmod/backup.ko` SHA `6ae178d5…`；`Backup_nread` 位于 `.text+0x1eb8`（file `0x1f20`），内部读取 helper 位于 `.text+0x760`（file `0x7c8`）。helper 由 `Data_SearchId`/`Data_GetSize` 取得实际记录长度，`memcpy` 长度使用 **actual size（w19=w22）**，不是 capacity（w24=w2）。
2. **capacity=4、record length=1 的实际行为：**
   - `Data_GetSize` 返回 1；1 < 4，走 `0x7ac` 拷贝路径；
   - `memcpy(buf, data, 1)` **只写 1 字节**；
   - 返回 `w0=1`；
   - 高 3 字节**不被写入**，保留调用者原值。
3. **原报告“单字节 00/01 读取仍合法”在本 appFw 调用点上成立，但不是通用保证。** `set_model_for_boot_screen` 在 `0x11f6760-0x11f6768` 将 `[b4..c8]` 每个 **4 字节槽**初始化为 1（little-endian bytes `01 00 00 00`），所以单字节 `00/01` 写入低字节后仍为 `0/1`，高 3 字节保持 00。若调用者没有初始化高 3 字节，或记录值不是 0/1，则该结论不成立。
4. **capacity=4、record length=4：** actual=4 == capacity；走 `0x848` 的诊断/检查路径（该路径调用 `.text+0x6d8`，其中包含本案 backup-bug-skip 的既有分支修改），随后仍到 `0x7ac`；`memcpy` 长度 4，四字节全覆写，返回 4。target 的 `16/19` 4 字节值正是这条路径，导致 appFw 的 3147/3176 断言输入非法。
5. **缺失/失败：**
   - `Data_SearchId` 返回 0 → `0x868` 将 `w22=-1`，跳 `0x7d0` 返回 **-1**，**buffer 完全不写**；调用者的 4 字节 1 保留。
   - `Data_GetSize=0` 的静态路径可拷贝 0 字节并返回 0；未在 target 键上观测。
   - `actual > capacity` 路径未被本任务执行；静态显示会走 `0x848` 后仍以 `w19=actual` 拷贝，**不推断安全截断**。
   - appFw thunk **忽略 `Backup_nread` 返回值**；因此返回 -1/0 不会被 appFw 判错，buffer 保持初始 1。
6. **当前 92fe Backup 生产链：** `setting/Backup.bin` 在固定 FX3 base `guest.cpio`、`guest-three-entry.cpio`、`guest-cp-helper-agnostic.cpio`、`guest-hybrid-fx6kernel.cpio`、`grmreal21/41/46` 中全部是同一 `92fe4031…`（2,229,740 B）。`build_cpio.py` 只替换 simulation helper；`build_hybrid_cpio.py` 只替换 appFw；`APPFWFUTURE/BACKUPBUG/UPMCALLSITE` 各只替换一个成员；**没有构建脚本改写 `setting/Backup.bin`**。它来自固定 FX3 基座镜像，`Backup-generation4-fixed.bin` 与它同 hash。
7. **实际导入/初始化：** initramfs `init` 只 `ls`/`sha256sum` `/setting/Backup.bin`，并以 `Backup_load=1 Backup_save=0` `insmod /usr/kmod/backup.ko`；serial 记录 `no_native_data_writes=1`、`FX3_BACKUP_INSMOD_RC=0`、`/setting/Backup.bin` 2229740 B。**没有观测到运行时导入/复制/写入该 Backup 的代码或写者**；它是 rootfs 中的静态文件，由 backup 模块只读加载。上游谁生成 92fe 这个基座文件，未在这些构建脚本中闭合。
8. **FX3 消费者与共享风险未闭合。** FX3 appFw `545c…` 中没有 `set_model_for_boot_screen` 字符串，却存在 `model_api.cpp` 一次、`Backup_nread` 字符串 3 次；两个 ID 的静态常量搜索不能证明直接消费（`0x2cf0214` 仅 BE=1 的孤立匹配，`0x2cf0218` 无匹配）。同一 `92fe` 文件的这些 ID 在 FX3 seed 中是 4B `16/19`。因此**不能排除 FX3 消费者对同一记录有不同语义/共享数据风险**；不做迁移。
9. **迁移 dry-run：** 只读算得若保持 record 长度和表项不变、仅改两个 4B 数据窗（`594516..594519`、`594530..594533`）及 record checksum（field `32..35`），最小 12 字节可保持其他字节不变；`record_bytes=857900`，checksum 覆盖 `[0,32)` + `[36,857900)`。但由于 FX3 consumer 未闭合，**没有选择值、没有生成/安装 Backup/CPIO**；`receipts/migration-dry-run.json` 状态 `blocked_by_unresolved_fx3_consumer_semantics`。
10. **不声明 VM/菜单通过。** 本任务仅读契约/生产链/离线证据；未实现任何新 patch/veneer/return0/断言绕过，未修改候选或运行策略。

## 1. 实际读取实现（target CPIO member）

`usr/kmod/backup.ko` target SHA `6ae178d5390f847415fcc57236b8d49e33c486f043e906598eb2af81f7fec11e`；本地 `grm-fbinit/backup-bug-skip.ko` 与之逐字节相同（脚本验证）。ELF `.text` sh_offset=`0x68`。

| 项 | 地址/文件 | 证据 |
|---|---|---|
| `Backup_nread` | `.text+0x1eb8` / file `0x1f20` | `nm` 符号 `Backup_nread`；外层的 `down_read/up_read` 重定位 `0x1ee8/0x1f08` |
| 内部读取 helper | `.text+0x760` / file `0x7c8` | `0x788 Data_SearchId`、`0x794 Data_GetSize`、`0x7cc memcpy` 重定位 |
| capacity | `w24=w2` | 外层把 `w2` 传成 4 |
| actual size | `w22=Data_GetSize` | `0x798 uxth w22,w0` |
| copy length | `w19=w22`; `0x7c4 uxth w2,w19`; `0x7cc memcpy` | **不是 w24** |
| return | `0x7d0 mov w0,w22` | 实际记录长度；缺失 `0x868 w22=-1` 后返回 -1 |
| appFw init | `0x11f675c-0x11f6768` | `[b0]=0`; `stp w0,w0` sets `[b4..c8]` 4-byte slots to 1 |

详细：`receipts/reader-semantics.json`、`disasm-backup-nread-outer.txt`、`disasm-backup-nread-inner.txt`、`relocs-backup-nread.txt`。

### 1.1 四种输入

| 输入 | actual | 复制字节 | 高 3 字节 | 返回 | buffer 结果 |
|---|---:|---:|---|---:|---|
| capacity4, len1 | 1 | 1 | 保留 | 1 | 低字节 00/01；高3保持调用者 |
| capacity4, len4 | 4 | 4 | 被覆盖 | 4 | 全部 4B 记录值 |
| missing ID | null | 0 | 保留 | -1 | 保持调用者原值 |
| len0（若出现） | 0 | 0 | 保留 | 0 | 保持调用者原值 |

`actual>capacity` 未执行，静态路径不做安全截断推断；`0x848` 诊断路径调用 `.text+0x6d8`（既有 backup-bug-skip 修改所在函数）后继续拷贝 actual bytes。target 两键均为 length4，不涉及 1B 上限。

## 2. “单字节 00/01 合法”核验

- **成立范围：** 仅针对 `set_model_for_boot_screen` 的 `[b4]/[c4]` 槽。该函数在读取前把每个槽作为 32-bit 值写 1；AArch64 little-endian 下 bytes 为 `01 00 00 00`。helper 对 len1 仅写低 1 字节，高 3 字节保持 00；所以 `00/01` 读后是合法 0/1。
- **不成立为通用契约：** 如果调用者传入未初始化/非零高 3 字节，读 1 字节后仍可能不是 0/1；如果记录本身是 4B `16/19`，会复制 4 字节并覆盖高 3 字节，assert 仍触发。
- 原报告把“单字节 00/01 仍合法”作为读取结论，方向正确但未限定**调用者高 3 字节已清零**这一条件；本报告补上条件。

## 3. 92fe 生产链与加载

| CPIO | CPIO SHA | `setting/Backup.bin` SHA |
|---|---|---|
| base `vmopt.../guest.cpio` | `eaef24b2…` | `92fe4031…` |
| `guest-three-entry.cpio` | `bb618bd2…` | `92fe4031…` |
| `guest-cp-helper-agnostic.cpio` | `11adfbce…` | `92fe4031…` |
| `guest-hybrid-fx6kernel.cpio` | `1cc4f88e…` | `92fe4031…` |
| `grmreal21` | `238ff1b7…` | `92fe4031…` |
| `grmreal41` | `c1f15473…` | `92fe4031…` |
| target `grmreal46` | `3a08f89d…` | `92fe4031…` |

- 构建脚本的替换范围：base→cp-helper 只换 simulation helper；three-entry→hybrid 只换指定 appFw；appfwfuture 只换 appFw；backupbug 只换 backup.ko；upmcallsite 只换 upm.ko。**均未改 `setting/Backup.bin`**；该文件由固定 FX3 base 逐字节复制。
- `Backup-generation4-fixed.bin`（2,229,740 B）SHA 也是 `92fe…`；这是 host 侧可见的同内容文件，但当前 target QEMU command 不直接加载它；target CPIO 内已有 `setting/Backup.bin`。
- initramfs `init`（SHA `642ce1c6…`）只执行 `ls`/`sha256sum /setting/Backup.bin`，然后 `insmod /usr/kmod/backup.ko Backup_load=1 Backup_save=0`；没有 `cp`/`dd`/重定向写 `/setting/Backup.bin`。serial 的 `FX3_FILE100_OBSERVER_READY ... O_RDONLY=1 no_native_data_writes=1` 和 `FX3_BACKUP_INSMOD_RC=0` 与之一致。
- **实际写者/初始化生产者：未观测。** 92fe 是静态 rootfs 文件；上游谁生成/导入到 base CPIO 未在这些构建脚本中闭合；`Backup-generation4-fixed.bin` 只证明同 hash 文件存在，不证明它就是被导入的那一步。详见 `receipts/producer-chain.json`。

## 4. FX3 消费者/共享风险

- FX3 appFw（`guest-cp-helper-agnostic.cpio` 的 `usr/lib/appFw.so`，SHA `545c5053…`）：
  - 不含 `set_model_for_boot_screen` 字符串；
  - 含 `model_api.cpp` 1 次、`Backup_nread` 字符串 3 次；
  - 两个 ID 的直接常量匹配：`0x2cf0214` 仅 BE=1 的孤立匹配，`0x2cf0218` 无匹配；
  - 这不足以证明 FX3 有同路径消费者，也不足以排除间接/计算式消费。
- 同一 `92fe` 文件在两个 ID 上的 FX3 seed 语义是 4B `16/19`；FX6 默认是 1B `00/01`。**共享数据风险未闭合**：修改共享记录可能影响 FX3 的其他读取者，当前无法给出安全迁移值。
- 因此本任务不生成迁移计划/修改版 Backup/CPIO；只保留 dry-run 影响范围。

## 5. 迁移 dry-run（只读，blocked）

`receipts/migration-dry-run.json`：

- record 0，`record_file_offset=0`，`record_bytes=857900`；
- 两个数据窗：`0x02cf0214` @ `594516..594519`；`0x02cf0218` @ `594530..594533`（当前 `16161616`/`19191919`，长度4）；
- checksum 字段 @ `32..35`；checksum 计算范围 `[0,32)` + `[36,857900)`；
- 同长度 4B 数据修改 + checksum 的最小 changed scope = 12 字节；其他字节可保持不变；表项/长度不变。
- `candidate_values=null`、`file_written=false`、`cpio_written=false`；状态 `blocked_by_unresolved_fx3_consumer_semantics`。**没有为让 assert 消失猜值。**
- 若要求 FX6 1B layout，则需要改表/长度/header，不只是 12 字节；本 dry-run 不覆盖，也不建议。

## 6. 已知/推断/未知

**已知：**

- 实际 target `Backup_nread` 代码路径、参数、copy length=actual、返回 actual/-1、buffer 不清零（静态反汇编 + 重定位）。
- capacity4/len1 写 1 字节、高3保留；len4 写4；missing 返回 -1 不写。
- appFw 槽初始为 4 字节 1；所以“len1 00/01 合法”成立但仅在该初始化条件下。
- target/84db `setting/Backup.bin` 92fe；两键 4B 16/19；FX6 模板 1B 00/01；target/84db 的模型 assert 相同。
- 生产链为固定 FX3 base 逐字节复制；init 只读加载；构建脚本不改该文件。
- FX3 appFw 不出现同名函数；直接 ID 常量匹配不强；共享风险未闭合。

**推断：**

- target 的 4B `16/19` 被 `memcpy 4` 写入 appFw 槽，故 3147/3176 条件成立；这与实际读代码、target 数据、assert 条件互证，但仍未直接抓取运行时寄存器。
- 若使用 FX6 1B `00/01`，由于 appFw 高3初始为零，读取应得到合法 0/1；**这是条件性推断，不是已运行验证**。
- 92fe 来自固定 FX3 base 的静态 rootfs，不是 target 构建时新写；上游生成者未知。

**未知/缺口：**

- FX3 是否消费同两个 ID、是否不同语义；共享数据风险。
- 92fe 的原始生成者/导入脚本（只闭合到 base CPIO 和同 hash 文件）。
- `actual>capacity` 安全语义；未在 target 键上观测更多尺寸。
- 运行时寄存器 b4/c4 的实际值（本任务只读静态 + Backup 数据）。
- 修好这两个 ID 是否会让 boot-screen/screen/menu 通过；仍需真实运行证据。

## 7. 是否支持下一步

- **支持**：当前已能精确说明“容量4读1B会写1B并保留高3、写4B会覆盖；missing 返回-1不写；target 两键是4B×16/19，所以读入非法；92fe 是静态 FX3 base 文件，构建链只复制”。这足以指导下一步在 Backup 数据/生产者层做**受控兼容验证**，并避免把模板1B误当4B成功。
- **不支持**：不能据此直接宣布迁移安全、不能生成/安装修改版 Backup/CPIO；FX3 消费者语义和 92fe 上游生产链未闭合，且没有运行时修复验证。
- 本任务未设计/执行任何新 patch、veneer、return0、断言删除或重试被拒绝实现；没有 VM/运行授权。

## 8. 交付

- `REPORT.md`、`RESULT.json`、`SHA256SUMS`。
- `receipts/reader-semantics.json`、`producer-chain.json`、`migration-dry-run.json`、`input-seal-compare.json`、`test-run.json`。
- 反汇编/重定位：`disasm-backup-nread-outer.txt`、`disasm-backup-nread-inner.txt`、`relocs-backup-nread.txt`。
- 输入 18 项前后 hash 不变；4/4 离线脚本通过。审查完成不等于 VM/菜单/FX6 可开机。
