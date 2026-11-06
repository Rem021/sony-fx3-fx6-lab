# r41 入口计时观测候选

离线实现、5组成对全源码host seam、18组解析及AArch64构建/固定槽ELF等价核查通过；未VM、未部署、未证明菜单提速或FX6开机。

- [REPORT.md](REPORT.md)：改动、时钟含义、未知边界、成本和输入口径。
- [source.diff](source.diff)：仅主源入口与两返回点、现有头的同一日志行变化。
- `src/`：仅2个派生源码；其他实际依赖仍只读原路径，见 BINDING / DEPENDENCY-BINDING。
- `build/gpe-r41-candidate.so`：未strip原件277704B，不能直接装槽。
- `build/gpe-r41-fixed-slot.so`：链接期strip-debug，129600B；仅尺寸与运行内容等价成立，尚无CPIO包/runner准入。
- HOST-TESTS / PARSER-TESTS / COST / SOURCE-ELF-REVIEW / SLOT-ELF-REVIEW：当前通过证据；receipts含早期失败原流。
- [NEXT-MEASUREMENT.md](NEXT-MEASUREMENT.md)：后续单次测量审查点，不授予运行权限。

解析器只读单个明确run/截止文件：`python3 -B parse_command_timing.py SERIAL --run-id ACTUAL_RUN --cutoff-byte ACTUAL_CUTOFF --output NEW_JSON`。输出独占创建；缺字段/0值不补0耗时。不要把本轮旧serial首次观测pin称为读取前快照。

构建/分析脚本仅供在新获准离线目录复现，本封存目录及历史输入不应覆写。编译器缓存列入CACHE-SCOPE，不作为交付源；没有复制CPIO、DTB或完整runtime。
