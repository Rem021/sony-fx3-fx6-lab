# 第182轮：恢复启动请求与版本准入

2026-10-29。经典ILME-FX3 7.02的1080p29.97 HEVC主录目标继续，优先解决修改失败后的退回。

[综合报告](<reports/FX3 恢复启动 版本准入.md>) · [三份最终笔记](<research_notes/FX3 恢复启动 版本准入/>) · [来源与复核](provenance.json)。旧sauu同版comp缺失续行和-s跳版本已由原代码证明，旧SD仍严格比较；当前7.02 body先dat4后comp，不能预设失败后版本仍旧。完整7.02包未找到独立p1载荷，MAIN kernel/initrd和U-body不代作p1。

7.02请求经Backup门、/dev/uipc及ioctl到queue0x376间接回调；实际登记target未解，helper返回0不能证明发送或进入恢复。下一项仅从原登记节点+0x10和osal_reg_msg_queue_cb/reg_msg_queue_cb/WBI结构追真实消费者及selector，不重复泛查或执行设备方案。

全部16项状态、目标、授权、prepared与原research_priority原样保留；goal_complete=false、persistent_write_release=false。未新增相机/USB/admin/Windows/UU/GUI操作、测试或原固件执行，未触碰原生goal manager。

登记重验181清单13成员，canonical与181 after逐字相同；新鲜读取Mac入口并以CAS保留并发内容。最终清单覆盖实际分析脚本、反汇编、证据和回执，明确排除.venv、__pycache__与pip/依赖缓存，保留这些目录不删除。依赖位置及版本见[工具回执](evidence/boot-request/static-tools-and-scope.json)。封存见[final-receipt.json](final-receipt.json)。
