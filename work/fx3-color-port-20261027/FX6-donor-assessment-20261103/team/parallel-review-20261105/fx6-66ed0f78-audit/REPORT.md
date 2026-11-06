# FX6 cp-bind-66ed0f78 独立只读审查

- Task：`task_a43e50d89605`
- Dispatch：`ctx_732d01695498`
- 状态：**审查完成；本轮正常启动/可用性未通过或未证明，菜单未通过。** 这不是“绝对永远不可启动”的断言。
- 卷：`/Volumes/KAFU2T` UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。
- 只读审查既有产物；无 VM/browser/server/QMP/guest、无 live process、无 source/package/platform/old-sealed 修改、无 camera/USB/SD、无外部 agent 进程操作；未继承其他 terminal 的 broad approval。
- 唯一写入：本 audit 目录；原始输入 26+13+新增基线 6 项 hash 前后不变（`receipts/input-seal-compare.json`）。
- 初版报告/manifest/回执快照：`superseded/initial-20261105/`（保留不改）。

## 0. 结论

1. **目标运行仍失败在已知首次故障附近，且 receipt 的“无 fault”是检测器盲区。** 目标 serial 有 4 条 `assert at`：
   - `model_api.cpp:3147`（line 11688）
   - `model_api.cpp:3176`（line 11738）
   - `infra_wrapper_bb_procam_chaplin_base.cpp:1075`（line 14502 和 14734）

   其中 `1075` 正是基线 `cp-bind-6e83a14a` 的已知首次 CAPID/media 断言（baseline line 10976）。目标没有“越过已知故障并完成初始化”，而是改换输入/补丁后在后续路径再次命中同一断言，并新增 model_api 断言。`run-receipt.serial_observation.fault_markers=[]` 只检测 Kernel panic/Oops/Unable/Internal/SError，**不含 assert**；不能据此说无 fault。
2. **没有 screen/menu/render/input 证据。** 目标 marker：`FX3_AP89_SCREEN_CREATE=0`、`FX3_AP89_UUD_DECISION=0`、`FX3_MENU=0`；`FX3_MEDIA_START_BRANCH=2`、`FX3_PROFILE_FRAME=294`、`FX3_PROVIDER_CALLER=7`、`FX3_AP_IM_ENDMAPS=473` 只说明 appFw/media/AP 有执行，不是菜单/绘图/按键完成。`FX3_KEY=1105`/`FX3_UI_GATE=1` 也不是 menu/input/render 验收。marker 缺失不能独立证明“从未绘制任何像素”；只能证明没有保留的 screen/framebuffer/visual 证据。
3. **补丁影响的是返回/路径，不是功能初始化证明。**
   - appFw `future::get`：目标 member `b1fe2274…` 与 donor `a1c58b69…`；offset `0x2159c50` 目标字节 `00008052c0035fd6`（`mov w0,#0; ret`），修改字节确实存在。
   - upm：目标 `5be2aa0b…` 等于 `upm-callsite-skip.ko`；claim 为 `upm_senser_dfs_measurement+0x4a0 blr x2 -> mov w0,#0`；只验证了文件 hash/provenance，offset-level disassembly 未做。
   - backup：目标 `6ae178d5…` 等于 `backup-bug-skip.ko`；claim 的 `0x75c` 是 **.text 段内偏移**，不是文件偏移。独立 ELF64 解析得 `.text sh_offset=0x68, sh_addr=0`；文件位置 0x7c4；target `e9ffff17` 解码为 `b` 到段内 `0x700`，source `007d20d4` 是 `brk #0x3e8`。**claim 与目标字节/段内目标一致**；初版把 0x75c 当文件偏移的比较错误，已撤回。
   - helper：target `7e8d859e…` 等于本地 `fx6-cp-backup-sync100-agnostic-g0.ko`，serial 明确 `synthetic_cp_backup_sync=1 original_CP=0`、`software_CP_executed=0`，是仿真辅助层，不是 FX6 原 CP。
4. **provenance 不是“全是 FX6 原版”，但来源仍未闭合。** donor appFw `a1c58…` 与 CPIO baseline 一致；donor upm `34d5…` 与 CPIO source `ba0c…` 不同，donor backup `0fe5…`（alternate `5619…`）与 CPIO source `8a8d…` 不同。目标 upm/backup 是在这两个非 donor baseline 上再修改；不能把目标 `5be2/6ae1` 说成 FX6 原版。但差异只能证明来源未闭合，**不能排除 FX3 兼容/替代模块**；标为 unknown，不作错误来源断言。
5. **CPIO 替换链可复核：** `grmreal46` 从 `grmreal41` 只替换 `usr/kmod/upm.ko`（其余 1157 成员不变）；`grmreal41` 从 `grmreal21` 只替换 appFw；`grmreal20` 从 `grmreal19` 只替换 backup。目标 member hash 与 build JSON/预构建文件一致；CPIO 总长 453,184,500，target 3a08…。
6. **cleanup 无独立证据。** run 目录只有 5 个文件（command、host stdout/stderr、run-receipt、serial），没有 RESULT/RUN-SHA256SUMS/cleanup receipt；serial 在 179.53/`447 (SeqQueueInd` 处截断；elapsed 180.166 > maximum 180；reason 仍是 `ap_guard_observed_continue`，与 timeout/termination 不一致。guest graceful End/stop marker 未见；`qemu_exit=0/process_reaped/locks_released` 是 host run-receipt 自报，不是独立观察。**这不是“任何 QMP 退出都不算 clean”的政策**；只指出本 run 缺 guest graceful 与独立 cleanup 证据。
7. **基线选择（2 轮）：**
   - `cp-bind-6e83a14a`：已知 `1075` assert；FX6 donor kernel `bc4925…` + hybrid CPIO `1cc4…` + 无 skip；目标为 FX3 kernel `da4a…` + CPIO `3a08…` + 三个 skip。输入不同，不能把差异归因于 skip。
   - `cp-bind-9d22099a`：FX6 donor kernel + FX3 CPIO `11ad…` + FX3 appFw `545c…`，有 8 个 `FX3_AP89_SCREEN_CREATE`、1 个 UUD，但无 menu；与目标的 FX6 appFw/CPIO/内核均不同。它只证明“另一配置能到 screen marker”，不证明目标改善或回退。
   - 追加且仅追加 `cp-bind-84db17c2`：**同 FX3 kernel `da4a66…`、同 QEMU/DTB/platform**；CPIO `grmreal45` `b68c…`；upm thofs-skip；backup/appfw skips；60s。首个 fault 是 `assert at model_api.cpp:3147`（line 11597），后续 `Internal error: Oops`（line 16408）；screen/UUD/menu=0，media start 1。与目标相比，CPIO/upm patch 与 60s vs180s 不同，**非单变量**；不能因果归因，不再追加运行。
8. **成功仅指本次只读审查完成，不是 FX6 可开机。** 固定 FX3 平台的输入/命令约束成立，但功能/菜单验收不成立；mainline 不满足 FX6 可用目标。

## 1. 输入与验证

- 目标 candidate `d3181026…`；command manifest、run-receipt manifest 与 candidate 三者一致。
- 目标 kernel `da4a66fa…`（固定 FX3 official）、DTB `b6f9f4…`、CPIO `3a08f89d…`、serial `377142e9…`；host stdout SHA `e3b0c442…`（空）、host stderr `697e732f…`。
- 所有 target member hash 与 refresh/独立 CPIO 解析一致：appFw `b1fe…`、upm `5be2…`、backup `6ae1…`、helper `7e8d…`。
- 输入封存：target/read-only 26 项 + provenance 13 项，前后 `changed=[]`，`unchanged=true`。
- 详细：`receipts/hash-audit.json`、`cpio-member-audit.json`、`patch-bytes-audit.json`、`serial-evidence.json`。

## 2. 证据分层矩阵（摘要）

完整表见 `EVIDENCE-MATRIX.md`。

| 层 | 代表对象 | 观察 | 判定 |
|---|---|---|---|
| FX6 原版 donor | appFw `a1c58…`、libgrm/libma/libgrm_bmp/libra/stella/remote/grm_ma/fbinit | target CPIO 含这些 libs；appFw profile 指向 `/usr/lib/appFw.so` | 有映射/部分执行；非所有初始化 |
| 修改版 | appFw `b1fe…`、upm `5be2…`、backup `6ae1…` | 字节/hash 修改存在；future/upm/backup 路径被改 | 不能证明原功能 |
| FX3 兼容 | kernel `da4a…`、DTB `b6f9…`、QEMU `bf4d…`、FX3 `/init`/rootfs | kernel boot、CPIO init、平台参数 | 固定平台输入成立 |
| 仿真辅助 | helper `7e8d…`、`simulation/fx3-*`、GPIO/SCU model env | `synthetic_cp_backup_sync=1 original_CP=0`、`software_CP_executed=0` | 仿真，不是 FX6 原 CP |
| 加载/映射 | boot/insmod/CP bind、appFw profile、AP/media markers | 有实际 marker | load/mapping 成立 |
| 功能初始化 | appFw future/upm/backup 真正 init | 只有 return0/skip/no fault | 未证明；assert 仍出现 |
| 菜单/绘图/输入 | screen/UUD/menu/key | screen=0/UUD=0/menu=0；KEY 计数非输入 | 缺失 |
| cleanup | End/stop/exit | guest graceful End/stop 未見；host qemu_exit/reaped/locks 自报；无独立 cleanup artifact | 独立证据不完整 |

## 3. serial/receipt 事实

- target serial 5,508,980 B、69,498 行；assert 行 11688/11738/14502/14734。
- receipt `fault_markers=[]`：检测器只看 panic/Oops/Unable/Internal/SError；assert 被漏掉。**没有 fault 标记不等于没有 assert，也不等于功能初始化成功。**
- `cp_helper_rc_line=null` 而 serial line 1029 有交织的 `FX3_BACKUP_CP_INSMOD_RC=0`；top-level `cp_helper_rc0=true` 来自 substring，不是严格整行。
- nested `pre_ap_guard=false` vs top-level true；receipt 自相矛盾。
- reason `ap_guard_observed_continue` 与 180.166s elapsed/截断 serial 不一致；实际是 timeout 后 quit。
- run 目录 5 文件；无 RESULT/RUN-SHA/cleanup；qemu_exit/reaped/locks 是 host self-report；guest graceful 与独立 cleanup 证据缺失，但不据此制定“所有 QMP 退出均不清”政策。

## 4. 已知首次故障 vs 本轮

**baseline 6e83a14a**（FX6 donor kernel `bc4925…`，hybrid CPIO `1cc4…`，appFw 原 `a1c58…`，upm `ba0c…`，backup `8a8d…`，无 skip；与目标内核不同）：
- `assert at …:1075` line 10976；`send_and_wait_cmp_i`；无 screen/menu。
- 目标：FX3 kernel `da4a…`、CPIO `3a08…`、appFw `b1fe…`、upm `5be2…`、backup `6ae1…`；仍在 14502/14734 命中 `1075`，并新增 model_api assert。
- 因此：**同一已知断言仍在；目标还多了断言；“无 fault”不能作为解决功能/菜单的证据。** 输入不同（kernel/CPIO/补丁），不能把无 fault 或无 screen 的差异单独归因给 skip。

**baseline 84db17c2（追加）**（同 FX3 kernel `da4a…`、同 QEMU/DTB/platform；CPIO `grmreal45`、upm thofs-skip、60s）：
- 首个 fault `assert at model_api.cpp:3147` line11597；后续 `Internal error: Oops` line16408；screen/UUD/menu 0，media start 1。
- 与目标差异：CPIO `grmreal45` vs `grmreal46`、upm thofs-skip vs callsite-skip、60s vs180s；**非单变量**，不能把 target 的 assert/no-menu 差异归因于单一 patch；不再追加运行。

**baseline 9d22099a**（FX6 donor kernel `bc4925…`，FX3 CPIO `11ad…`，FX3 appFw `545c…`，无 FX6 appFw，无 skip）：
- screen create 8、UUD 1、menu 0；说明另一配置能到 screen marker，但没有 menu；与目标的 FX6 appFw/CPIO/内核不同，不能证明目标改善/回退。
- 目标 screen create 0，比 9d 少，但输入不同，只能列为“不同输入下的缺失”，不能作因果结论。

## 5. 下一步验收条件（不提供新绕过实现）

1. **原功能**：appFw `future::get`、upm sensor/DFS、backup 原路径必须真实执行并返回真实结果；禁止 stub/return0/branch skip；函数级 init/return/state 要有证据。
2. **无 assert**：serial 不得含 `assert at model_api.cpp:3147/3176`、`assert at …:1075`，也不得含 panic/Oops；receipt 的 fault 检测必须覆盖 assert。
3. **screen/render**：至少 `FX3_AP89_SCREEN_CREATE` + `FX3_AP89_UUD_DECISION`，真实 screen/presenter 返回、可见 framebuffer/PNG/render 证据；仅 `visible_pixels_unproven` 不算。
4. **menu**：明确 menu marker/菜单可见证据，不能把 IM/AP poll、media start 或 KEY init 计数当菜单。
5. **input**：菜单打开后真实 key 事件/ack/UI 响应；不能只凭 `FX3_KEY`/`FX3_UI_GATE` 计数。
6. **cleanup**：guest End/stop marker、完整 serial tail、guest 停止后的 QEMU exit、run RESULT/SHA/cleanup artifact；要区分 guest graceful、host reaped/lock release 自报与独立证据缺失，不能把任何 QMP 退出一概判为 unclean。
7. **receipt**：严格整行、nested/top-level 一致，reason 与 elapsed/termination 对应；不得再用 self-reported no-fault 覆盖 assert。
8. **provenance**：upm/backup 需证明使用 FX6 donor 原版或明确标注非 donor 修改；来源差异目前只证明 provenance 未闭合，不能排除 FX3 兼容/替代模块。backup 的 0x75c 是段内偏移、文件 0x7c4；target `e9ffff17` 解码为段内 `0x700`，source `007d20d4` 为 `brk #0x3e8`，claim 支持。

## 6. Fact / inference / unknown

**Fact：** 所有 target candidate/kernel/DTB/CPIO/serial/member hashes match；serial 有 4 个 assert（含 1075 两次）；screen/UUD/menu marker=0，但 marker 缺失不独立证明零像素；backup 0x75c 是段内偏移，文件 0x7c4，target 分支解码到段 0x700，claim 支持；run 目录 5 文件、serial 截断；26+13+6 输入 hash 不变；test 9/9 通过。

**Inference：** receipt `fault_markers=[]` 是检测器盲区，不是无 assert；目标仍命中已知 1075 并新增 model assert；appFw/media/AP 有执行但无功能/菜单；skip/return0 不能等于设备完成；cleanup 无独立证据；84db 与目标非单变量，不能因果归因。

**Unknown：** 被 patch 函数真实返回值/初始化状态；upm/backup baseline 是否为 FX3 兼容/替代模块（provenance 未闭合）；visible render/menu/input 行为；cleanup 是否干净；各 skip 的独立因果效果。没有新运行可补这些 unknown。

## 7. 交付

- `REPORT.md`、`RESULT.json`、`EVIDENCE-MATRIX.md`、`SHA256SUMS`。
- `receipts/serial-evidence.json`、`cpio-member-audit.json`、`hash-audit.json`、`patch-bytes-audit.json`、`test-run.json`、输入封存/对比、raw stdout/stderr。
- `scripts/analyze_serial.py`、`parse_cpio.py`、`verify_hashes.py`、`patch_bytes.py`、`input_seal.py`、`original_input_seal.py`、`run_all.py`。
- 未修改旧失败、平台、源码、包或旧封存；未启动任何 runtime。**审查完成不等于 FX6 可开机/菜单通过。**

## 8. 修正记录

- 初版错误地把 backup claim `0x75c` 当文件偏移；独立 ELF64 解析 `.text sh_offset=0x68, sh_addr=0`，文件偏移 `0x7c4`；target `e9ffff17` = B 到段内 `0x700`，source `007d20d4` = BRK `#0x3e8`。claim 支持；见 `receipts/backup-section-audit.json`。
- `normal boot/usable` 改为 **本轮未通过或未证明**，不作绝对不可启动断言；四 assert 仍成立。
- marker 缺失只表示无保留的 screen/framebuffer/visual 证据，不独立证明零像素。
- cleanup 区分 guest graceful、host reaped/lock release 自报、独立证据缺失；未制定任何 QMP 退出政策。
- 仅追加一个已完成基线 `cp-bind-84db17c2`；同 FX3 kernel/platform，但 CPIO/upm patch/timeout 不同，非单变量；不追加更多运行。
- upm/backup donor 与 CPIO source 不一致只说明 provenance 未闭合；不能排除 FX3 兼容模块，标 unknown。
- 初版快照：`superseded/initial-20261105/`。
