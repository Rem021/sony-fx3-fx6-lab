# AP105 性能候选离线准备

候选已生成，尚未启动guest；当前用户TRY1持有运行窗口，须等Lead明确恢复。准备期间不获取运行锁、不改STATE、不修改TRY1入口/网页/候选或既有runs。

Lead授权：msg_719755e33697要求AP103-r2软件LDEC基线只替换GPE性能件；msg_4e88c7b0d2b2允许1200秒、完成/超时及停止条件不变。候选为[ap105-v1-gpe-perf/candidate.json](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap105-v1-gpe-perf/candidate.json)。CPIO只改变 `simulation/fx3-gpe-observe-v7.so`，其他成员含init、软件LDEC与原关机脚本逐字不变；DTB仅更新initrd-end，CPIO安全审计和sh -n通过，见[构建回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap105-v1-gpe-perf/build-receipt.json)。

性能二进制SHA `30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4`，精确复制Lead接受的v26-perf/backend-v9。对象/epoch映射缓存与对象权威验证启用，生产纹理观察默认0，callback缓存默认0；原5000ms接收预算、像素数学、准入拒绝和完成语义保留。本工人的v26-profile104是独立测量件，未叠加。Lead宿主回执证明v8/v9逐字节等价，不能替代QEMU验收。

恢复后的运行命令（**当前未执行**）：

```sh
python3 -B work/fx3-vm-20261101/menu-repair-01/runtime/run_candidate105_v1.py \
  --candidate work/fx3-vm-20261101/menu-repair-01/runtime/ap105-v1-gpe-perf/candidate.json \
  --seconds 1200 --smp 4 --tcg-thread multi --label ap105v1perf1200
```

脚本AST已解析，候选输入和性能原件共6项SHA复核一致，见[离线核验回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap105-offline-review-v1.json)；模块未执行。runner保留两把原锁、源SHA、原厂种子/原loader、LDEC实际ioctl自检、逐步截图读回及20秒guest ack/API16双核验。无GDB断点/寄存器读，不设置icount。保留同一guest最多30键，每键100ms；白名单UP/DOWN/LEFT/RIGHT/ENTER/MENU/DELETE分别为0x3/0x30/0x15/0x1af/0x1ac/0x1ab/0x1f8。宿主一次只放行一键，实际查看输出PNG后再决定下一键，未预排导航序列。

运行验收依次要求：

1. 原厂待机、MENU与Setup语言弹窗实际截图；橙色高亮、图标和面板可见。每步保存实际读图、画面描述和选键理由。
2. 对同步绘制批次，用同代QID领取到完成返回作保守上界核对原5000ms预算；不与printk时钟混算，不把它冒充ReceiveDrawComp入口计时。匹配缺失、释放先于完成、unfetched/断言/新绘制拒绝任一出现即保留现场并停。
3. English确认后关MENU，目视待机并空闲至少60秒，读回RAM语言及原厂Backup.bin代次、语言与AP/CP bank校验；随后逐图确认原日期值，观察原全量同步与文件变化。无额外flush、无RAM注入。
4. 收尾分别核对QEMU退出码0、reaped/PID消失、输入不变、guest确认和API原16字节、两锁独立释放；guest业务通过与宿主收尾通过分开报告。

候选遵守只换GPE，所以保留AP103-r2原init。20秒还原helper已覆盖未绑定且原字节未变时不恢复执行；绑定后、file observer尚未启动的早停窗口不能由AP105正常收尾自动关闭。TRY2需在另一个新候选中复用readiness-before-CP-bind，再做启动/正常结束/Ctrl-C实际回执，详见[TRY2方案](try2-ldec-performance-plan.md)。

当前AP105 guest计时/长轮、English与日期保存、TRY2网页及早停测试均待执行。既有首选AP101-r4未提升，用户试用状态及原始数据未改。
