# r42 command 入口计时包

只完成离线固定槽封装；未启动 VM、网页、服务或部署。真实运行须另行调度。

- `candidate.json`：严格新包清单；原历史合同继续作为来源，当前 GPE payload 以新增 `r42_command_entry_timing_contract` 为准。
- `SOURCE-BINDING.json`：r41 源码与 ELF body、旧/新槽摘要、零尾、实际 CPIO 依赖链和平台绑定。
- `source-index.json`：实际解析的完整 newc 条目/头/偏移，保留 r36 格式。
- `ARCHIVE-DIFF.json`、`member-comparison.json`：全归档与逐成员审计；仅一个 GPE body 变化。
- `ELF-AUDIT.json`：复用已冻结纯文件审计器，比较原 r41 raw/fixed-slot 的装载内容、ALLOC、PHDR 和动态依赖；不装载目标 ELF。
- `INPUTS-INITIAL.json` 与后续观察清单：各自注明 pin 时点；最终去重复核在 `INPUTS-AFTER.json`。

`package_r42.py` 为独占写入脚本，产物已存在时拒绝覆盖。`finish_metadata.py` 只生成来源索引。没有重编译或复制 r41 源码，保留其原封存路径。`verify_frozen.py` 可只读复核两个 r42 清单与实际用到的外部技术输入，不启动任何运行路径。
