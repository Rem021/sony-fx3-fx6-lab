# FX6 boot-screen model_api 3147/3176 根因定位

- Task：`task_97919f2e6f0f`
- Dispatch：`ctx_a9695459fefe`
- 状态：**根因定位完成；FX6 正常启动/菜单仍未证明。**
- 卷：`/Volumes/KAFU2T` UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。
- 只读使用已有冻结日志、FX6 donor、target appFw、既有 Backup 分析；未启动 VM/browser/server/QMP/guest/live-process，未触碰 camera/USB/SD，未改平台/包/候选/默认入口/旧 audit/协调账本。
- 只写本目录；输入 16+11 项前后 hash 不变（`receipts/input-seal-compare.json`）。

## 0. 结论

1. **两个 assert 的直接输入是 Backup 的两个键。** `model::model_api::detail::set_model_for_boot_screen()` 在 `0x11f6188..0x11f79f8`（appFw `.text`，文件偏移同 VMA）先初始化本地槽 `[b4..c8]=1`，然后通过 thunk 调 `Backup_nread@plt` 读入 4 字节：
   - `[x29,#0xb4]` ← key `0x02cf0214`（thunk `0x2169784`）
   - `[x29,#0xc4]` ← key `0x02cf0218`（thunk `0x21697d4`）
2. **assert 条件精确为“值不在 {0,1}”：**
   - `0x11f7230`: `ldr w0,[x29,#0xb4]`；0 → mode1；1 → 继续；否则 `b.ne 0x11f72c8`；`0x11f72d8` 置 `w1=0xc4b`（3147），调日志函数 `0x2167784`，随后 `w20=0`，回到 `0x11f7288`。
   - `0x11f7288`: `ldr w1,[x29,#0xc4]`；0 → `0x11f72e8`；1 → `0x11f7320`；否则 `0x11f72a0` 置 `w1=0xc68`（3176），调同一日志函数，随后 `w0=0`，回到 `0x11f7320`。
   - 这说明 assert 的“条件”不是空指针/读失败，而是 **读到的枚举值不是 0/1**。
3. **目标 Backup.bin 正好给出非法 4 字节值。** 目标 CPIO 的 `setting/Backup.bin` SHA `92fe4031…`（与提供的 `Backup-generation4-fixed.bin` 相同）是 checksum 有效的 BK4：
   - ID `0x02cf0214`：length **4**，raw **`16161616`**，u32_le `370546198`，data offset `594516`；
   - ID `0x02cf0218`：length **4**，raw **`19191919`**，u32_le `421075225`，data offset `594530`。
   两者都不是 0/1，因而直接满足两个 assert 的条件。
4. **正常初始化契约由 FX6 默认模板给出 0/1。** 同一组 ID 在 FX6 `CHAPLIN/CX95898_NTSC.bin`（以及其余四个 CHAPLIN 模板）为：
   - `0x02cf0214`：length **1**，raw `00`；
   - `0x02cf0218`：length **1**，raw `01`。
   appFw 以 `w2=4` 读入 4 字节槽；FX6 的 1 字节 0/1 读入后仍是合法 0/1，目标 FX3 风格的 4 字节 `16/19` 则非法。
5. **目标 Backup 的这两个键值与 FX3 官方种子语义一致。** FX3 `FX3-CX95900_ALLLANG-Backup.bin` 同两个 ID 也是 length4 `16161616`/`19191919`；目标 `92fe…` 文件 hash 不同（可能是修复/重封装版本），但这几个键值相同。来源细节仍未闭合，不能仅凭 hash 差异断言具体生成者。
6. **84db 也有同一对 assert，因为它的 `setting/Backup.bin` 也是 `92fe…`、同两个值。** 84db 的 model asserts 在 line 11597/11644，之后 line 16408 才是 `Internal error: Oops`；目标 model asserts 在 11688/11738，之后 line 14502/14734 才是 CAPID `1075`。**不应先追后续 UPM Oops/CAPID；boot-screen 模型输入契约在这里已经失败。**
7. **assert 是非致命日志，不能直接断言 screen 被它阻断。** 日志函数 `0x2167784` 走 `printf`/`usleep` 后经 `0x2167780 ret` 返回；3147 路径置 `w20=0`，3176 路径置 `w0=0`，执行继续。因此：
   - 已有充分证据说明 **boot-screen 模型枚举契约未满足**；
   - 不能仅凭 assert 或 screen/menu marker 缺失证明“assert 直接阻断 screen”；后者需下游状态/真正 screen 调用证据。
8. **9d 对照的限制明确。** 9d 无 model_api assert，且有 8 个 `FX3_AP89_SCREEN_CREATE`，但它使用 FX3 CPIO/appFw `545c…`，不是目标 FX6 appFw；不能把它当作同一路径的修复证据，也不能把目标 screen marker=0 直接归因给这两个 assert。
9. **下一步功能修复的最小契约已确定**：`setting/Backup.bin` 的 `0x02cf0214`、`0x02cf0218` 必须提供 FX6 语义的 0/1（FX6 默认 length1 `00/01`，或明确等价的格式/生产者转换）。修复应针对 Backup 数据/初始化生产者，而不是删除 assert、return0、手填成功或增加 veneer。**本次不实现任何修复，也不声称修复后能开机。**

## 1. 精确条件与证据位置

### 1.1 函数与 assert 位置

| 项 | 值 |
|---|---|
| appFw | target `grm-fbinit/appFw-future-skip.so`，SHA `b1fe2274…`；donor `a1c58b69…` |
| `.text` | VMA/file `0xb1a1f0` |
| `set_model_for_boot_screen` | `0x11f6188`（下一函数 `0x11f79f8`） |
| function region | target 与 donor **逐字节相同**：SHA `c802ebf53f6be40c9a17c89fd68e4bbc34134065d4ca555b38b25f381f77f6f0`；future::get 修改在 `0x2159c50`，不在该函数 |
| 3147 site | `0x11f72d8`，file `0x11f72d8`，`w1=0xc4b`；file string `0x24be0d8`，func string `0x24c1500`；`bl 0x2167784` |
| 3176 site | `0x11f72a0`，file `0x11f72a0`，`w1=0xc68`；同一 file/func/logger |
| assert logger | `0x2167784`：printf/usleep；尾 `b 0x2167780`（`ret`），非致命 |
| 反汇编 | `receipts/disasm-set_model_for_boot_screen.txt` |
| 条件契约 receipt | `receipts/boot-screen-contract.json` |

### 1.2 Backup 读入映射

| 本地槽 | Backup key | thunk | 读入容量 | target 值 |
|---|---:|---:|---:|---|
| `[x29,#0xb0]` | `0x02cf01af` | `0x2169770` | 4 | absent（槽保持 1） |
| `[x29,#0xb4]` | **`0x02cf0214`** | `0x2169784` | 4 | **`16161616`**，length4 |
| `[x29,#0xb8]` | `0x02cf0215` | `0x2169798` | 4 | `0a`，length1 |
| `[x29,#0xbc]` | `0x02cf0216` | `0x21697ac` | 4 | `0a0a0a0a`，length4 |
| `[x29,#0xc0]` | `0x02cf0217` | `0x21697c0` | 4 | `19`，length1 |
| `[x29,#0xc4]` | **`0x02cf0218`** | `0x21697d4` | 4 | **`19191919`**，length4 |
| `[x29,#0xc8]` | `0x02cf0219` | `0x21697e8` | 4 | `19`，length1 |

初始化：`0x11f675c` `[b0]=0`，`0x11f6760-0x11f6768` 将 `[b4..c8]` 置 1；因此读失败不写时仍是合法 1；target 的 4 字节读取会覆盖成非法值，assert 是“读成功但数据非法”，不是单纯缺失/读失败。

### 1.3 Backup 数据位置

| 数据源 | SHA256 | `0x02cf0214` | `0x02cf0218` |
|---|---|---|---|
| target `setting/Backup.bin`（CPIO member） | `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f` | length4 `16161616` | length4 `19191919` |
| 84db `setting/Backup.bin` | 同 `92fe…` | 同 | 同 |
| FX6 CHAPLIN `CX95898_NTSC.bin` | `e2eafd4e…` | length1 `00` | length1 `01` |
| FX6 其余四个 CHAPLIN 模板 | 同语义（00/01） | length1 `00` | length1 `01` |
| FX3 `FX3-CX95900_ALLLANG-Backup.bin` | `bf3a9d85…` | length4 `16161616` | length4 `19191919` |

target/84db 的 Backup 记录 checksum 均 true（由既有 `parse_bk4.py` 验证）；这不是“坏文件/随机损坏”，而是 **FX3 风格的 4 字节值进入了 FX6 appFw 的 0/1 枚举契约**。

## 2. serial/因果证据

| run | model 3147 | model 3176 | later fault | screen/UUD/menu |
|---|---:|---:|---|---|
| 66ed | line 11688 | line 11738 | CAPID 1075 line 14502/14734 | 0/0/0 |
| 84db | line 11597 | line 11644 | Oops line 16408 | 0/0/0 |
| 9d（限制对照） | none | none | none known | screen create 8, UUD 1, menu 0 |

- 84db 与 66ed 的 `setting/Backup.bin` 完全同 hash，且都先命中同一对 model assert；这直接说明 model assert 的输入问题不依赖后续 CAPID/UPM 路径。
- profile 邻近行是跨线程/交错采样，**没有**被当作 assert 线程栈；条件来自静态调用点和 serial 精确行。
- assert logger 返回、serial 后续继续；**没有“assert 直接终止/直接阻断 screen”的代码边证据**。screen marker=0 只表示没有保留的 screen 证据，不能独立证明零像素或因果阻断。

## 3. 已知 / 推断 / 未知

**已知：**

- 函数 `set_model_for_boot_screen` 的 3147/3176 条件、buffer/offset、Backup key 和 thunk 地址（静态反汇编）。
- target/84db `setting/Backup.bin` 为 `92fe…`；`0x02cf0214=16161616`、`0x02cf0218=19191919`，length4，BK4 checksum true。
- FX6 模板同 ID 为 length1 `00/01`；FX3 seed 为 length4 `16/19`。
- target/84db 都先有 model asserts；84db 后 Oops、目标后 CAPID 1075。
- assert logger 返回；执行继续；appFw function region target=donor 逐字节相同。
- 9d 无 model assert、screen marker 8，但 appFw/CPIO 不同。

**推断（强但非直接运行时寄存器读取）：**

- target 的 4 字节 `16/19` 被 `Backup_nread` 写入 b4/c4，因此触发 3147/3176；该推断由直接读调用、target Backup 字节、assert 条件三者互证。
- 正常 boot-screen model 初始化要求这些 ID 为 FX6 语义 0/1；target 的 Backup 是 FX3 兼容格式/值，未满足契约。
- 后续 Oops/CAPID 与这两个 model assert 不是同一输入条件；不应先追后续 fault 作为根因。

**未知：**

- 谁在正常启动中应写/迁移这两个 ID（Backup 初始化生产者、顺序、版本）；只确认了读取路径和已加载镜像，未观测写入者。
- target `92fe…` Backup 的准确来源（是 FX3 seed 的修复/重封装还是其它 FX3 兼容镜像）；只能确认这些键值匹配 FX3 seed 语义。
- 修好这两个值是否足以让 boot-screen 继续并最终出现 screen/menu；是否还有其它 model assert/下游失败。
- 下游如何使用 3147/3176 的 fallback mode，以及它是否直接导致 screen 不创建；没有直接证据。
- 可见像素/菜单/输入行为；marker 缺失不证明零像素。

## 4. 最小未满足契约 / 是否足够支持下一步功能修复

**最小契约（针对这两个 assert）：**

1. `setting/Backup.bin` 中 ID `0x02cf0214` 与 `0x02cf0218` 必须提供 appFw 能解释为 `0/1` 的值（FX6 默认：length1 `00`、`01`；或明确等价的格式/生产者转换）。
2. 这两个值必须由正常的 Backup 初始化/迁移生产者提供；不能靠 appFw 侧删 assert、return0、手填成功、或新增 veneer。
3. 只有满足后，`set_model_for_boot_screen` 不会在 3147/3176 落 fallback；是否继续到 screen 仍需下游实证。

**是否足够支持下一步功能修复：**

- **足够定位**：条件、字段、key、target 数据、FX6 正常值、84db 共性都已闭合；可以据此选择一个针对 Backup 数据/初始化生产者的功能修复方向。
- **不足以宣告修复成功**：尚未观察到运行时 b4/c4 寄存器值（推断来自数据+静态条件）、未证明修复后 screen/menu；必须补原函数返回/下游状态、screen create/UUD、render/visible 像素、菜单/输入和 clean stop 证据。
- 因此本任务给出根因和验收条件，**不输出新 patch/绕过方案、不实现、不宣称开机**。

## 5. 边界与交付

- 未新开运行；未改 appFw/backup/候选/平台/包/旧 audit。
- 输入：core 16 项、root 11 项（Backup 镜像、5 个 FX6 模板、FX3 seed、parser/README/static receipt）；前后 hash 不变。
- 回执：`receipts/boot-screen-contract.json`、`disasm-set_model_for_boot_screen.txt`、`bk4-0x02cf0214.json`、`bk4-0x02cf0218.json`、`backup-key-values.txt`、`input-seal-compare.json`、`test-run.json`。
- `REPORT.md`、`RESULT.json`、`SHA256SUMS`。审查完成不等于 FX6 可开机/菜单通过。
