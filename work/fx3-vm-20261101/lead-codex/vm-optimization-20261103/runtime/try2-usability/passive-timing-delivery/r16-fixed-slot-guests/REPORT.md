# r16 两份固定槽位 guest：离线生成完成

2026-11-04。**N1、N64 真实 CPIO 已依次生成并通过完整静态校验；未启动 VM、未操作网页、未部署，也未更新 host/runner pin。** 本任务只生成两份新镜像，原 r3/r14/r15、封存打包工具、DTB/kernel/platform、入口和旧结论均未改。r16 host 由协调端另行管理，本目录没有复制或修改它。

## 输入与来源

写前及生成时核卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；新目录和适配清单均 exclusive 创建。已核 r15 的 31 source、54 delivery、4 prior input，并在最后再次复核一致。冻结工具原样使用，SHA `b5b9bf75763b193575a007074e6701d1a1541ba9d3658ae32a164fc350eca8bc`，其交付清单 SHA `311f686f87797e320347819ac6a3731eb4edb6d6fea5234ddb88fb2400f453bb`。

r15 `SOURCE-FREEZE.json` SHA `4737db8f89660c6bb41993b37f8aa9c8f9761a1e26be1e2fbbfa7a73db760d4b`；全交付清单 SHA `215d1f432ed7fd135e902418de71bc80871aa9b67b42d26ae953a3c064ed92f3`。按该 JSON.files 原顺序精确生成 DEL 根的 `r16-r15-guest-SOURCE-SHA256SUMS`，每行 `hash  v25-r15-snapshot-tail/filename`，31 项，SHA **`05aded60ec6ecabb67381eca1f9ea8b3311599725c9d8e2cbb022db72b077d7d`**；绑定和逐项路径见 `SOURCE-ADAPTATION.json`。未复制源码、未使用 `../`、未写旧冻结目录。

## 最终候选与 SHA

各 CPIO 均 **453,213,884 B**。以下路径相对本目录；完整绝对路径在 `VERIFICATION.json` / `MANIFEST.json`。

| 变体 | candidate | candidate SHA256 | CPIO SHA256 |
|---|---|---|---|
| N1 | [guest-N1/candidate.json](guest-N1/candidate.json) | `ce047a951a5e7af08d19312d4e9d6440080e159c857e41edf90ce66607a31563` | `77081424fa73f9737434b7d0c5d2f6dc2b21215ffcc9cb3a95281dac9d4b521c` |
| N64 | [guest-N64/candidate.json](guest-N64/candidate.json) | `96666a719b1a4cf576e4d2d7ec461e10f5ce1143650450719e5273d75d970672` | `aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9` |

| 变体 | 最终小 SO SHA256 | 大小 | 补零 | 完整 58856B 槽位 SHA256 |
|---|---|---:|---:|---|
| N1 | `da4eef557353223542cfab4d0e9f9b91a42a3c77a886f42f791867d0e2a45d92` | 22048 B | 36808 B | `26f338bc21d32a7b5d1deac70260ec25da747f0b0d38f91604eef11ca92a1148` |
| N64 | `3ea77f9bc94ca3f4c5edb863b20bbe1245ebde1d868e61243bf0b0d8cc3511b2` | 22160 B | 36696 B | `6673b9beaf8a2adfbc2c68dc7337df369e484bd58ede10edff3519dcf8d258df` |

## 实际验证

- **ELF passed**：按原 r15 BUILD 各 variant 的原 command，仅新增一个 `-Wl,--strip-debug` 并改独立输出；两次 exit0。源码、BUILD、原 debug ELF、工具链与 SDK 输入 hash 均绑定。原 debug N1 `5faeb996c4c7386383a9e07ab5cc9f65c5e9e80217e5e777f15df7d26b9c8dbc`、N64 `ea47aa2d2b437700f00e64d8f3c0db7cf164c2c81f90bdedfb528a0430784574` 保留且 hash 未变。
- **运行内容审计 passed**：每份 ELF 为 AArch64/ELF64 LE/ET_DYN，19 个 SHF_ALLOC 节的地址、大小、flags/type/offset/align/entsize 与数据、全部 PHDR、动态依赖及动态符号保持。移除 debug 和经批准的非运行时 `.symtab/.strtab`；没有用 strip-all。ELF section table header 差异单列：N1 e_shoff 64848→20640、N64 64912→20752；两者 e_shnum 31→22、e_shstrndx 29→21。首 PT_LOAD 仅文件 offset 40/41/60/62 有差异，其余三个 PT_LOAD 字节一致；不宣称整个 PT_LOAD 原始字节相等。完整数据见 `samples/*-ELF-AUDIT.json`。
- **实际写出 passed**：先 N1 的 plan/review/write 完成，再 N64；不并发大文件操作。各 write 创建前完整源 SHA、复制中源 SHA、输出总长、槽位内容、完整索引及许可跨度外每字节比较全部通过。唯一替换是 `simulation/fx3-ui-gate-v1.so` 的 `[451339648,451398504)`，58856B；header 从 451339508 开始，mode `0100755`。所有 header/name/order/size/offset、其他 payload 与 padding 不变，1140 个非 trailer 成员，trailer 精确结束 EOF。
- **平台/DTB passed**：两份 candidate 除 `initrd.path/sha256` 与新增 `fixed_layout_diagnostic_contract` 外，r3 全部字段逐项一致；仍引用原 DTB，未复制/重编码或改 initrd-end。原 DTB SHA 最后复核仍为 **`5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b`**。原 candidate SHA `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`，原 CPIO 最后独立完整 hash 仍为 `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`。
- **最终交付核验 passed**：独立按 source→N1→N64 顺序核完整 SHA，另核两份输出索引/目标槽位和 candidate 全部字段；31 source/54 delivery/4 prior inputs 与封存工具再次通过。详见 `VERIFICATION.json`、`VERIFY.log`。未重复原 40 项 fixture 测试。

`guest-N*/COMPLETE.json` 为成功静态回执；`INCOMPLETE.json` 是按封存工具政策保留的起始历史标记，已由 COMPLETE 明确 supersede；没有 FAILED 回执。计划原文仍标 seek-only 未全 hash，但各最终 COMPLETE 已记录随后真实 write 的完整源 SHA 校验，不能混淆这两个阶段。

新增 diagnostic 合同引用最终 r15 REPORT 与 SOURCE-FREEZE hash，记录 v5 request `+0x3000..3040`、ready/ACK `+0x3040..3100`、98Q payload `+0x3100..3410`。`snapshot_is_end_state=false`，逐原子字段镜像不宣称事务一致，额外诊断 cont 不属于首帧/性能窗口。**协议 runtime、渲染、生命周期和 host 接线仍未运行验证；这两份镜像不能据此宣称已部署或 VM 通过。**

交付清单见 `MANIFEST.json`，所有本目录工件（含两幅真实 CPIO）的 SHA 见 `SHA256SUMS`，校验回执见 `HASH-CHECK.txt`。除明确授权的 DEL 根适配清单外，本任务输出均在本目录。
