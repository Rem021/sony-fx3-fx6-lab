# r36 两诊断 helper 固定布局离线打包

结果：成功生成一个 N64 派生候选，两个 r35 release ELF 严格装入原 slot。已完成离线 ELF 加载语义、全档差分、manifest 保持及拒绝条件检查；没有运行 target、VM、网页、服务或设备，没有修改 runner 或部署入口。功能、时序及运行验收仍未完成。

## 输入与方法

卷 UUID 已核为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。任务授权的两个原始 ELF 在处理前后均保持指定 SHA，原件保留在 r35，另在本目录 [raw/](raw/) 留证据副本：

| helper | 原始字节数 | 原始 SHA-256 |
|---|---:|---|
| UI | 72656 | `8fbad11e585a88ba55fc657785b6bc132bd12ee20ac3a31f23c603b1b1b322d1` |
| OSD | 119544 | `1a0761b8c73fb04502406686499ff01f3683bcc767ce1503fae3e6bbb996bf21` |

原 N64 candidate SHA 为 `96666a719b1a4cf576e4d2d7ec461e10f5ce1143650450719e5273d75d970672`；源 CPIO 前后 SHA 均为 `aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9`。[INPUTS.json](INPUTS.json)、[PACKAGE-COMPLETE.json](PACKAGE-COMPLETE.json) 记录核验，实际 newc 全部头见 [source-index.json](source-index.json)，未只信任务给出的 offset。

本机无独立 LLVM objcopy/strip；r15 已有 Zig objcopy 的 ELF unimplemented 失败证据，因此未重试该失败路径。复用 r16 已验证方法：**原 Zig cc 命令仅增加 `-Wl,--strip-debug` 并改输出路径**，不改源码、优化参数及其他链接参数；这是基于原只读源的精简重新链接，不是声称在原 ELF 上执行了 objcopy。协调端 msg_d0073edba2ce 明确确认该方法可用；本次仅此一种方式就适配，无需 strip-all。

Zig 版本 0.17.0，二进制 SHA `1c5f706db0ed6d55451940f31dc05a6177d05696bc1fa5d853696d04c718b523`；身份和显式缓存/临时目录环境在 [TOOL.json](TOOL.json)。两条完整新旧命令、所有发现的源/头/库输入前后 hash 及 exit=0，在 [UI 命令回执](receipts/ui-release-command.json) 和 [OSD 命令回执](receipts/osd-release-command.json)。缓存与临时输出均定向本目录。

r35 最终输入门已按协调端 msg_a9774da2cd5d 记为闭合：协调端核验 158 项交付，SHA256SUMS 文件 SHA 为 `c7aee1bf7a35320e3c8d08eec03214957832008197741feb971433f19c524a71`，29 项 SOURCE-FREEZE 文件 SHA 为 `dd4f8a2045220a045c32b8a0a686227f08e4e8c2edc7adca8964a12ddedc66e4`。本任务核了这两个清单文件及精确 ELF，没有重复声称独立复核全部 158 项。

## Release 与 ELF 等价证据

| helper | release 大小 | 原 slot | 精确零尾 | release SHA-256 |
|---|---:|---:|---:|---|
| UI | 23400 | 58856 | 35456 | `87267da03bbc5f05b81aa559a4a1c713d1e7462bdb4602a571405dc048bba4fe` |
| OSD | 34960 | 109000 | 74040 | `51685bf707f7c1947c81936de03a0694b2228228792e732ee177c788acd09837` |

[ui-ELF-AUDIT.json](ui-ELF-AUDIT.json)、[osd-ELF-AUDIT.json](osd-ELF-AUDIT.json) 复用固定 SHA 的 r15 auditor，再补充所有段内容、ALLOC 节链接身份/初值及真实 ELF 头字节差分检查：

- 全部程序头字节一致，入口均为 0；PT_LOAD 地址、offset、filesz/memsz、对齐和保护位不变，BSS/TLS 布局和零初值合同不变。
- UI 的 20 个、OSD 的 21 个 SHF_ALLOC 节集合、布局、初值与链接身份一致；包括 .dynsym、.dynstr、GNU 版本/哈希、.rela.dyn/.rela.plt、.text/.plt、.dynamic、GOT、初始化数组等。所有机器指令及装载数据字节一致，只有下列 ELF 节表元数据字节明确例外。
- **没有宣称整个首 PT_LOAD 字节相同**。两 ELF 都仅在文件 offset **40、41、42、60、62** 改变，即 e_shoff、e_shnum、e_shstrndx 的实际变化字节；其余装载字节逐个比较一致，全部非 LOAD 段也检查。PT_LOAD 全字节一致标志如实为 false。
- UI 的 e_shoff 为 70608→21928，e_shnum 32→23，e_shstrndx 30→22；OSD 分别为 117496→33424、32→24、30→23。变化只说明节表的非运行元数据位置/数量调整，没有无条件忽略整个 ELF 头或任何段。
- 移除的仅是 .debug* 与非装载 .symtab/.strtab；静态调试信息留在 raw 原件中。动态导出/导入完整一致：UI 5 个导出、14 个非空未定义符号，OSD 6 个导出、23 个非空未定义符号；没有裁功能来凑大小。

[CONSTRUCTOR-PROOF.json](CONSTRUCTOR-PROOF.json) 进一步解出 .init_array 的 R_AARCH64_RELATIVE 重定位：UI 指向 `r35_ui_init`（VA 73540、172B），OSD 指向 `r35_init`（VA 74140、192B），原/新代码完全相同；DT_INIT_ARRAY 地址/长度、数组内容和原重定位字节相同。没有把重定位前数组中的 0 当成“无构造器”。

依赖分别仍为 UI 的 libc.so.6/libdl.so.2，OSD 的 libc.so.6/libdl.so.2/libpthread.so.0；SONAME 保持 fx3-ui-r35.so / fx3-osd-r35.so，RPATH/RUNPATH 均为空。[DEPENDENCIES.json](DEPENDENCIES.json) 从实际 CPIO init 确认原 LD_LIBRARY_PATH/两条 preload 路径未变，并逐个解析归档内的依赖符号链接至原 ELF。它只证明离线存在和路径关系，不冒充动态装载成功。

LLVM 的[原文说明](https://llvm.org/docs/CommandGuide/llvm-objcopy.html)用于核对元数据处理概念；本次可接受性由上述实际语义审计决定，而不是仅凭“strip”名称或 .text hash 推断。

## 固定 slot 与全档结果

唯一候选：[guest.cpio](guest.cpio)，453213884B，SHA-256：

`49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff`

| 成员 | data offset | slot 长度 | 实际改变字节 |
|---|---:|---:|---:|
| simulation/fx3-ui-gate-v1.so | 451339648 | 58856 | 17883 |
| simulation/fx3-osd-headless-v5.so | 452021916 | 109000 | 69997 |

[ARCHIVE-DIFF.json](ARCHIVE-DIFF.json) 和 [member-comparison.json](member-comparison.json) 记录全部 1140 个成员（不含 trailer）的核验：每个 header、路径、顺序、权限、长度和 offset 相同；只有上述两个 body hash 改变；两个 slot 都严格等于 release ELF 加指定长度零尾。独立的全档顺序字节对比确认两个 span 之外每一字节相同，trailer 结束仍在 453213884，未增尾、重排或压缩整包。

init 的 20733B 未变，SHA `8ad0be3aec240977060e25ba1193ad80f6ef596ffe47392e3d5b5b79c0ee4a05`；全部 FX3 原件、其他 helper 和 Backup 内容均由全成员对比覆盖。

[candidate.json](candidate.json) 相对原 N64 只改变 `initrd` 和新增客观 `r36_fixed_slot_diagnostic_contract`。旧诊断合同保留为基线来源，新字段明确哪两项当前载荷引用被更新。DTB 继续引用原路径及 SHA `5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b`，memory=5120、load=0x440000000、markers/ready/Backup/输入/平台等所有其余字段深比较不变；没有复制 DTB、完整 runtime 或构造 N1 候选。

## 工具验证与写入范围

[TESTS.json](TESTS.json) 的 9 项宿主拒绝测试均通过：过大 UI slot、错误原 hash、输出越权、路径穿越、错成员、错 slot offset，以及机器指令、程序头、入口变化。测试只触发校验拒绝，不在外部目标创建文件，不执行 target。

[package_r36.py](package_r36.py) 的输出入口拒绝任何不位于本任务目录的路径，并拒绝所有现有路径分量中的符号链接；源通过 O_RDONLY/O_NOFOLLOW 打开。CPIO 独占创建前写 PACKAGE.INCOMPLETE.json，release 操作前亦各留 INCOMPLETE 标记；成功后的 PACKAGE-COMPLETE.json/RELEASE-COMPLETE.json 明确覆盖这些保留的历史标记，未删除失败或中间证据。命令、cache/temp 环境和输出清单在 EXECUTION.json/WRITE-SCOPE.json；这是受控任务写入路径审计，没有把它描述为整台主机的系统调用追踪。

## 验收边界与下一步

本轮已完成**离线包装**。r35 最终来源/测试/构建输入门已由协调端关闭；包装可复核性不等于功能或稳定性通过。

原 r30 runner 仍硬编码旧 N64，未修改、未导入或执行。本候选的 runner_bound/runtime_validated/VM_authorized 均为 false；后续须单独绑定新候选，复核原 ready、180s/20s、输入、退出恢复与 cleanup 政策，再另行取得运行授权。本任务不推进被拒 FX6 实现，不改变固定 FX3 的 CPU、内存、DTB、内核、时间或 QEMU 配置。

