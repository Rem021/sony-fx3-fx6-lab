# r15 固定布局打包离线交付

2026-11-04。**离线任务完成：双 r14 样本 ELF 审计、真实 r3 seek-only dry-run、40 项 synthetic 生产代码测试通过。真实 CPIO 未生成，最终 r15 未集成，VM 未运行。**

## 输入与原件边界

写前通过 diskutil 核卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。Mac 项目不是 Git 根，已读项目入口和适用 AGENTS；仅写本目录，不改原 r3/r14、平台、guest、旧 run、默认入口、README 或 ledger；不参与 FX6。固定源、槽位及 DTB pin 见 `MANIFEST.json` / `INPUT-RECEIPT.json`。

真实 r3 只 seek 读 header/name 与目标 payload，没有本轮整幅 453 MB 重 hash，也没有遍历重算全部成员 payload。独立核 candidate、DTB、目标原 SO SHA；索引目标 header/payload 分别为 451339508 / 451339648，mode `0100755`，槽位 58,856 B；共有 1,140 个非 trailer 成员，trailer 结束 453213884，正好 EOF。完整结构/原 header 字节在 `dry-run-N*/index.json`。CPIO 完整 SHA 此处沿用协调端的冻结实测，计划明确未重算；未来真实写出前强制完整复核。

## 实现

`fixed_layout.py` 的 `make_plan` 固定 r3 candidate/CPIO/DTB/原 member pin，审计 release 版本与 ELF 来源，拒绝超长、hash 不符、缺/重复 member、异常路径、非 regular/hardlink target、错格式/长度/偏移/模式、尾 padding 和 symlink。默认计划模式只产生 `index.json/plan.json`。生产 CLI 不提供改 source pins/UUID 的选项。

`write_archive` 只在显式 write + acknowledge + 最终 r15 release 下工作，先重新计算计划并逐项比较，完整核源 CPIO SHA 后才创建 exclusive 新输出目录/文件，以 O_RDONLY 打开原件、流式复制，替换唯一固定槽位并补零。复制中再次核源 SHA/文件身份，写后完整比较许可槽位外每字节、槽位 padded hash、总长及完整索引；DTB 原件再次核 SHA。失败保留未完成工件和标记，不自动覆盖或清除历史。

`derive_manifest` 复制原 candidate，只改变新 initrd 路径/SHA，新增固定布局诊断合同；逐字段断言其余所有平台和既有合同相同。仍引用原 DTB，完全不调用旧 `build_candidate.py` 的 DTB 重编码/`initrd-end` 更新路径。当前没有生成可运行的新 candidate。

## 体积缩减与实际审计

指定 Zig objcopy 的帮助列出 `--strip-debug`，但实际 N1 命令 exit1，stderr `error: unimplemented`，留下 0 B 文件（完整保留，见 `OBJCOPY-FAILED.json`）。本地工具链源码 ELF 分支直接 fatal，不能把 help 当成实现验证。

协调端消息 `msg_b4a35376625d` 明确批准唯一替代：原冻结 BUILD 命令只加 `-Wl,--strip-debug` 并换输出，同时接受该 linker 删除非运行时 `.symtab/.strtab`；完整 debug 原 ELF 继续保留。`prepare_r14_samples.py` 在本目录各交叉编译一次 N1/N64，源码 manifest、BUILD、原 ELF、工具链及 SDK 输入 SHA 均绑定。不是下载新工具、手写删节器、strip-all 或修改 Sony ELF。

| 样本 | debug → 小 ELF | 补零 | 原 ELF SHA | 小 ELF SHA | padded slot SHA |
|---|---:|---:|---|---|---|
| N1 | 60544 → 20400 B | 38456 B | `71779256b68ccb97ff911bba30e84d906c5a6365575fbfb59f498f652a743993` | `f95d91c1c5f3ca41303edf0df9fa25b574f0c70f903f163b8aaef36c36a4b1b4` | `20abdb909082fd6abf1ceb16f6ea626cebb29f0dcd407b84179b875cefb81448` |
| N64 | 61624 → 20576 B | 38280 B | `ab9b9127805303c7936945cde6773b1defc457b2a2abfa204c606401f26c9871` | `54092d471ade3a599adbd563e75cb4c140ccc34b8e7245f65aeeba42aa6aa1fc` | `3bd77e615425bf095d7997d5b76decee98e43ed093327084c66588dd5d8e014c` |

两者都是 AArch64/ELF64 LE/ET_DYN，全部程序头逐字相同，19 个 SHF_ALLOC 节的地址、大小、flags、type、offset、align、entsize 和原数据相同，NOBITS 单列。动态依赖只有 libc/libdl，SONAME 保留对应版本，5 动态导出和 14 未定义符号相同。移除 7 个 debug 节及 `.symtab/.strtab`；原始 debug ELF hash 不变。

必要 ELF 头差异单列：N1 `e_shoff 58560→18992`，N64 `59640→19168`；两者 `e_shnum 31→22`、`e_shstrndx 29→21`。首 PT_LOAD 原始字节仅文件 offset 40/41/60/62 不同，另三 PT_LOAD 无差异。**整个 PT_LOAD 不逐字相等，代码/分配节与程序头逐字相同。** 见 `samples/N1-ELF-AUDIT.json` 和 `N64-ELF-AUDIT.json`。

## 验证结果与限制

最终 `TEST-REVIEW.log`：40 tests / 0 failure / 0 error。测试直接调用生产代码，覆盖固定长度替换与零填充、manifest 平台不变、ELF 分配节数据/地址/程序头/架构/非法头拒绝、批准的静态符号移除、strip-all 构建命令拒绝、源码/build/release 来源不符、r14 写出门、最终 r15 fixture 成功、超长、原成员 hash 错、整源 hash 错、重复/缺/非 regular/hardlink/异常路径、格式/trailer/截断、原 DTB/candidate 错、已有输出/symlink/UUID 错、旧计划、异常/篡改后保留未完成工件、区间外比较。测试执行了小型 synthetic CPIO 写出；没有执行任何真实 r3 CPIO 写出。

r14 N1/N64 真 ELF 的两份 seek-only 计划完成，均可容纳且 manifest 引用政策明确；最终 r15 的实际源码、build receipt、ELF 和诊断合同尚未输入本工具。因此本交付证明的是离线打包门与 r14 体积可行性，不能证明 r15 nonce 协议、运行行为、性能改善、VM 通过或部署。

`test-artifacts/`（34 项）、`test-artifacts-final/`（38 项）和失败 objcopy 产物按原样保留；最终使用 `test-artifacts-review/RESULT.json`（40 项）。没有后台服务/VM/守护进程。完整交付与证据 SHA 见 `SHA256SUMS`；复核结果见 `HASH-CHECK.txt`。

后续仅在最终 r15 release 与 hash 经协调端审查后，按 [README.md](README.md) 先生成新 dry-run 计划，再另行授权显式 write；本轮不更新硬编码 pin、不自动运行后续阶段。官方格式依据和读取日期见 README。
