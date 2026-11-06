# FX5 与 VENICE 移植 FX3 证据索引

日期：2026-10-27。对象：经典FX3 7.02。覆盖公开固件可用性、缓存/DMA/RAW、FX5整套菜单与功能，以及FX5/VENICE完整色彩链。当前没有完整FX5机身包、整套移植实现或相机验收。

[完整研究报告](<../../reports/FX5 固件与 FX3 移植复核.md>)

| 主题 | 研究笔记 | 主要回执 |
|---|---|---|
| FX5公开整机包与访问缺口 | [public_package.md](public_package.md) | [页面抓取](public-http-refresh.json)、[补充抓取](public-http-supplement.json)、[检索范围](public-web-search-receipt.json)、[五包重哈希](existing-gpl-hash-recheck.json) |
| 平台、DMA、cache、完整菜单 | [platform_portability.md](platform_portability.md) | [59包分类](fx5-oss-components-classification.json)、[64,942项目录盘点](fx5-kernel-complete-member-inventory.json)、[163文件读取/18份源码证据](platform-gpl-static-review.json)、[源码](gpl_platform_sources/) |
| FX3原件与DMM/RAW控制 | [fx3_local_chain.md](fx3_local_chain.md) | [哈希/ELF/字符串](fx3-static-chain-receipt.json)、[检查脚本](inspect_fx3_static.py) |
| FX3原生色彩节点 | [fx3_local_chain.md末节](fx3_local_chain.md) | [三文件色彩扫描](fx3-color-static-receipt.json)、[扫描脚本](inspect_fx3_color.py) |
| FX5/VENICE色彩链、VENICE内层与PPLUT | [color_pipeline.md](color_pipeline.md) | [本地VENICE重验](color-local-evidence.json)、[官方页面](color-http-receipt.json)、[研究范围](color-research-receipt.json) |

上述64,942项是kernel归档目录清单，163个CXD文件才是逐个读取范围；五个开源组件不等于整机固件。源码和字符串用于定位，不等于算法、真实调用链或实机输出。PPLUT录制应用有当前官方文档依据，其最低引入版本和用户7.02机身/成片仍未验证。

本轮仅离线研究与公开HTTP读取，未接触相机、USB、Windows或手机，未运行下载的Sony代码或修改既有固件工具、旧阶段及VENICE工作树。原始公开页面保存在public-pages、color-pages和本目录HTML/TXT，详细来源、时间、状态、字节数与摘要以相应JSON为准。
