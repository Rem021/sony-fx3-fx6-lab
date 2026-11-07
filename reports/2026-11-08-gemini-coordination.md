# Gemini 协调与进度记录（FX6 系统移植 FX3）

> 负责人：Gemini（Antigravity 会话 `dcd390ed-0f6f-437b-b32b-d44775431854`）
> 协同：DeepSeek（运行时实验线，候选 ~300，原生帧与 `0x28` mutex 崩溃）；GPT/Codex（并行静态分析线，MWF/Kikilog/屏幕状态机/队列契约）。
> 本文件持续追加，最新状态在最上方“当前状态”节。

## 0. 当前状态（随进度更新）

| 时间（PST） | 状态 |
|---|---|
| 2026-11-07 08:20 | 已读 init-assist README 与 EVIDENCE-259/270/271，native-lifecycle、queue-contract、parallel-native-ui 三份报告；选定方向并声明文件范围（见 §1–§2） |
| 2026-11-07 08:26 | **第 1 段完成**：[Big6 依赖闭包与 shim 审计](2026-11-08-gemini-big6-closure/README.md)。要点：① 296–301 三层掩码很可能同源于未执行 `MWF_Init`（附可证伪预测）；② 301 的 `ObjShLock::Lock→0` 是进程级锁失效；③ 原厂路线上 shim 会伪造颜色/图像，`nz_pixels` 不再可信；④ 预见下一处全零帧：GRM 帧触发源（N14）；⑤ donor 为 FX6 6.01、BIG6 随 Ver.6.00 引入，AGENTS.md 的 v5.00 过时 |
| 2026-11-07 08:30 | **第 2 段完成**：[忠实配置设计](2026-11-08-gemini-big6-closure/NATIVE-FAITHFUL-PROFILE.md)（原厂路线下 shim 逐函数规则 + 替换计数门禁 + MWF 补齐草案）与 [低成本到达图](2026-11-08-gemini-big6-closure/OBSERVATION-POINTS.md)（闭包节点→导入→期望 LR；帧触发回调透明跳板）。均为设计稿，未编译/未运行 |
| 待办 | GitHub 大节点同步：`realtime_github_sync.py` 需 shell，本会话被 hook 拒绝，**未同步**；留给有 shell 的线或用户会话执行 |

### 给另两线的提示（非指令，供取用）

- **DeepSeek**：建议下一轮改为“301 − {GetFlag 守卫, 空 mutex 桩, ObjShLock 补丁} + launcher 中执行一次 `MWF_Init`”的单变量实验；预测与否定条件见闭包报告 §2.2。执行前需先确认 `MWF_Init` 参数（Q1）。
- **Codex**：闭包报告 §7 的 Q1–Q5 需要反汇编能力，本线（shell 被拒）做不了；其中 Q2（ObjShLock service 来源）与 Q3（GRM 帧触发回调的调用者）对 HOME 路线最关键。

## 1. 选定方向：原厂 Big6（HOME, screen ID 10）依赖闭包与“跳过项”审计

**一句话**：把“当前已到达点（UI worker / `uxengine_init2` / 3 Arena 已过）”到“原厂 `procam_big6_menu_home_presenter` 由 screen manager 工厂构造并出帧”之间的**全部前置条件**排成一张依赖图，逐项标注 *已证实到达 / 被候选 NOP 或启动器跳过 / 未知*，并给出按原厂顺序恢复的最小补齐方案；同时用 Sony 官方 Help Guide 为“原厂 Big6 可见、可交互”写出可判定的验收规格。

### 为什么选这条（与另两线的互补性）

| 线 | 已在做 | 本线不做 | 本线补的空白 |
|---|---|---|---|
| DeepSeek（运行） | 跑候选、抓 gpe0、追 `0x28` mutex 崩溃 | 不跑 VM、不改其候选/脚本/shim | 给出“下一候选应恢复哪些原厂步骤、按什么顺序”的静态清单，供其挑选 |
| Codex（静态） | 单点定位：MWF_Init 缺口、Kikilog 契约、screen registry/工厂、队列等待者 | 不重复其反汇编结论，不交付可运行的观察 shim（只出设计稿） | 把单点结论串成 **HOME 专用依赖闭包**，并对照**实际候选源码**（launcher / shim 的 NOP、跳过、桩）找出所有被移除的前置项，不止 MWF |
| — | 271 为自建 Big6（AdjChkConfig 槽位 + 手写布局） | 不再优化自建布局 | 以官方资料定义“原厂 Big6”验收判据，防止自建画面被误认为原厂 |

### 线内决策与理由

1. **不选“MWF_Init 单点补齐”作为主线**：Codex 已交付观察 shim 并明确“顺序/依赖未知”；单独做会与其重叠。本线将 MWF 作为闭包中的一个节点引用其结论，只补“它前后还缺什么”。
2. **不从 98 项描述符推坐标手摆控件**：并行复核已明确这会替代而非验证原厂结果；本线只用描述符做“原厂表是否被消费”的判据。
3. **工具约束（如实记录）**：本 Gemini 会话的 `run_command` 被 pre-tool hook 全部拒绝（含 `pwd`/`echo`），子代理同样受限。按边界规则不绕过；本线仅用**读文件 + 网页检索 + 写报告**完成，即只做源码级/已有 JSON 级静态核对，不做新的二进制反汇编。需要反汇编复核的点会列为“待运行线/Codex 线确认”。

## 2. 文件声明（只动这些）

- 新建/追加：`reports/2026-11-08-gemini-coordination.md`（本文件）
- 新建目录：`reports/2026-11-08-gemini-big6-closure/`（本线全部产出：README、依赖图、跳过项矩阵、官方验收规格）
- **不改动**：任何 `work/`、`/tmp`、`cp-helper-agnostic/` 下的候选 CPIO、manifest、`run_gpecap25_*.py`、`libgrm-fbinit25*.c`、`appfw-launch*.c`；`reports/2026-11-07-*` 下他人报告；`outputs/fx3-vm-trial/`。
- 不删除任何文件或工作树，不对外发布，不推送（GitHub 同步留给大节点并按 AGENTS.md 执行；本会话 shell 受限时如实注明未同步）。

## 3. 进度日志

- 08:16 卷与仓库入口确认：shell 被 hook 拒绝，无法执行 `diskutil` 校验卷 UUID；以 read_file 成功读取 `/Volumes/KAFU2T/...` 下仓库文件为挂载存在的弱证据，写入范围限于本仓库 `reports/`。
- 08:17–08:20 读完既有产出（见 §0）。关键事实摘要：
  - 269/270 原生 TextRM 文字上屏成立；271 为 25 路原生 `view_string` 组成的**自建** Big6（AdjChkConfig 22 槽 + 手写布局），非原厂 presenter。
  - 真 FX6 `appFw.so`（50,520,424 B，SHA `a1c58b69…`）：HOME presenter 构造 `+0xde10f4`，表 `+0x2e9e210` 98×0x48；registry `0x293bed8`，HOME = ID 10，工厂 `0xde1244`；manager 内嵌 `App+0xa40`，`manager::initialize +0xde31ac` 填 7 个 display-layer 池，池空则工厂返回 NULL。
  - 288–290 已过 UI worker/`uxengine_init2`/Arena；289/290 停在 `libMWF+0x3e908`（`smp_monErr==NULL`），launcher 只 dlopen 不调 `MWF_Init`。
  - 293：`+0x12d8254` NOP 跳过 70 项 infra 初始化，`+0xc09e50` NOP 跳过 `App::start_utimer`；帧全零。
- 08:21 子代理勘察（同样 shell 受限，仅凭读文件探测）：DeepSeek 最高候选为 301（`grmreal301-lock.cpio`），shim 源 `/tmp/libgrm-fbinit25-296…301.c`；296–301 的 run-id 未能定位（无法列 `runs/`）。
- 08:22 读到 [FX6 原厂启动 在线交叉验证](FX6%20原厂启动%20在线交叉验证.md)（GPT/Codex 侧 294/295 复核），其中记录 donor 为 FX6 6.01。
- 08:22–08:24 逐份读取 293/295/296/297/298/299/300/301 shim 末段与 301 全文、launcher 288/294；网页检索 FX6 Ver.6.00 BIG6 与 HOME 打开方式、静态 strace 方案。
- 08:26 写出闭包报告第 1 版。
