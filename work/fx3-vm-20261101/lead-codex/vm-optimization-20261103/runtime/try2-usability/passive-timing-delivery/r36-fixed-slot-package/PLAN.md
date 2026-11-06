# r36 离线计划

1. 核对卷 UUID、指定 r35 两 ELF 哈希/大小、N64 candidate/CPIO/DTB 哈希；从实际 newc 头重走所有成员并确认两个固定 slot。
2. 原始 ELF 在本目录保留只读证据副本；复用 r16 已验证的原 Zig 命令仅增加 -Wl,--strip-debug 和更改输出路径，不更改源码、优化参数或其他链接参数。没有可用的独立 LLVM objcopy/strip；旧 Zig objcopy 的 unimplemented 失败记录仅作为既有工具限制，不重试该方式。
3. 复用固定哈希 r15 ELF 审计解析器，并补强所有段、SHF_ALLOC 索引语义、动态符号、构造器、BSS 检查。仅允许 ELF 头 e_shoff/e_shnum/e_shstrndx 的明确非加载节表元数据字节变化；拒绝任何代码、动态依赖/版本/重定位或段布局变化。若不适配 slot 则保留失败证据，停止。
4. 先运行有限负例，覆盖越界 slot、错误原 hash、错误路径/成员及代码/程序头变化；通过后在本目录独占创建唯一 guest.cpio，开始前留 INCOMPLETE 标志，仅替换原两个 slot 体并精确补零。
5. 独立验证全部成员头/顺序/权限/offset/长度及 body，证明全档只有两 slot 可变、原 init 和其它内容保持、总长不变；candidate 只更新 initrd 和客观 r36 来源声明。记录源档前后 hash，保留 INCOMPLETE 历史并用 COMPLETE 明确收尾。
6. 输出报告、执行回执、语义审计、差分、manifest/SHA。所有工具缓存和临时文件均限定本目录，不导入 runner、不执行 target、不启动 VM/服务/网页/设备、不改共享资料。r35 最终源/测试/构建链接受状态暂记 pending。

依据：r15-fixed-layout-packaging/fixed_layout.py（SHA b5b9bf75763b193575a007074e6701d1a1541ba9d3658ae32a164fc350eca8bc）、r16-fixed-slot-guests/prepare_r15_samples.py（SHA 2fa01e9244f32293212f880f022a931213d620f7a029a3b3492d77f51db1200a）与 VERIFICATION.json。LLVM 原文 https://llvm.org/docs/CommandGuide/llvm-objcopy.html 仅说明元数据处理选项，不替代本次逐字节加载语义核验。
