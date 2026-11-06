# r36 两诊断 helper 固定布局离线包

离线打包完成：唯一 N64 派生 [candidate.json](candidate.json) 与 [guest.cpio](guest.cpio)，仅替换两个既有 helper slot，归档布局和总长保持。

- [结果、方法与验收边界](REPORT.md)
- [计划](PLAN.md) · [执行回执](EXECUTION.json) · [完成回执](PACKAGE-COMPLETE.json)
- [源/release 摘要](RELEASES.json) · [UI ELF 审计](ui-ELF-AUDIT.json) · [OSD ELF 审计](osd-ELF-AUDIT.json)
- [构造器](CONSTRUCTOR-PROOF.json) · [依赖路径](DEPENDENCIES.json) · [全档差分](ARCHIVE-DIFF.json) · [逐成员对比](member-comparison.json)
- [拒绝条件测试](TESTS.json) · [候选 manifest](MANIFEST.json) · [SHA256SUMS](SHA256SUMS)

CPIO SHA-256：`49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff`，453213884B。

只完成离线打包；未运行 VM/target、未修改 runner、未部署。r35 最终输入门已由协调端核验，但新候选仍须另行绑定 runner 和复核运行政策后才可申请运行。
