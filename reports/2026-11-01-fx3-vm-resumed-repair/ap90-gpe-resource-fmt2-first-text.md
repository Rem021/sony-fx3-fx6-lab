# AP90：原厂槽1存储卡读取警告首次可见

AP90-r2 已从原应用资源绘制出日文警告：“メモリーカードが正しく読めません／メモリーカードを入れ直してください／スロット1”（无法正确读取存储卡，请重新插入，槽位1）。73条BitBlit和随后Flush均result0。300秒窗口结束，常规健康收尾检查通过；菜单按键闭环尚未验收。

## 宿主实现与依据

`lead-claude/audits/gpe-fmt2-resource-extents/`审计在runtime独立重建，73条原cf2c分派、16个人工向量与615条保存extent行逐字节复现，proof SHA256为4ec69375e9ae338c1d9bfa5ac730b936b67f0559087823091b49edb282d3cf2f。没有运行审计原脚本的写入分支，没有改变Lead交付。

新GPE v16保持v15的精确线程创建前绑定、原FIFO、回调后status和快照锁。四个libObj入口1031b0/103454/103550/10364c通过固定原16B前缀、绝对跳板包装；原函数各执行一次，参数、返回值与errno保留。Lead明确批准1031b0完整成功返回且state10时登记，替代内部1032a0点。四前缀Unicorn对照的栈和GPR一致，只有ABI scratch X16用于跳转。

资源登记基于原对象身份和本地epoch；源只读映射、目标采用真实extent id81/unit402/type545，完整解析原proc到EOF，拒绝重复/截断/身份不符。逐行源/目标span分别按bpp检查，映射页padding不成为绘制范围，目标+100头仍受保护。

明确近似：fmt0通用按既有straight_over_v1；fmt2/op14按原前景色×8bit覆盖度的a8_color_straight_over_v1_candidate；不同尺寸按nearest_v1。marker分别标记approx_fmt2、original_fmt2_semantics_unproven、approx_stretch。16数学向量和73份完整原参数的人工缓冲绘制经ASan/UBSan通过，独立Python参考73份像素哈希逐项一致；保留早绑定/回调/Flush/快照锁回归、资源释放串行与proc负例通过。它们是软件模型检查，不是硬件像素oracle。

## 首轮受控拒绝与补登记

首轮`ap90gpe16-e1fa5127`，请求300秒，在32.601秒由首个GPE拒绝门停止。两个FillRect成功；已保存6条完整BitBlit marker均result5/reason4(STALE)，最后一条raw参数在停止时不完整；不将其写作完整73条统计。只有两个屏幕open对象登记，三个资源堆已经走原malloc但没经过1031b0观察点。保持拒绝，最终QMP仍均匀黑。

该轮exit0/reaped/inputs_unchanged，host PID缺席、两把锁FREE，receipt与combined required missing均空；原im PID228末次完整maps在uptime30.41包含im.elf，无symbol lookup error或fatal。完整匹配的0x11a后请求保存在该run的post11a时间线，受原trace上限和串口交织限制。

Lead msg_226e5305f0c5批准仅从已guard的原malloc成功返回补登记缺失父对象：同原open对象vptr/类、精确资源日志tuple、字段和返回span自洽、与现有区间不重叠，四者同时满足；origin=malloc_parent_v1。据此新建v16r2/resource-v2，冻结首轮helpers，宿主正负例再通过。候选从AP89-r2只替换simulation/fx3-gpe-observe-v7.so及DTB initrd-end；原CP、Backup RAM回放、seed/module/init未变。

## 保护范围与尚未验收

Lead批准本轮为**分配区间级保护**：绘制窗口持共享生命周期锁，close在原释放前撤销登记；free与绘制串行，记录原malloc/free活动和native allocation count前后变化。**没有恢复bitmap子块完整生命周期、compaction入口或排队ABA保护**；没有这些事件的marker也不证明它们不会发生。

资源对象+38读值为0，+40呈30303030等ASCII样式；它是原字段观测值，未证明为真实DMM handle。按Lead msg_115dafacd91f继续使用object+本地epoch登记与引用，不使用这些值寻址；报告明确保留该缺口。

原屏幕创建和错误日志与可见警告一致；不屏蔽挂载错误、不补画UI、不声称完整菜单、拍摄预览或输入反馈已经完成。

## 首张原厂警告（QMP物理ring，逻辑fmt0）

![原厂存储卡槽1读取警告](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap90r2parent-f5c66d0b/osd-frame-000001-format0-RGBA-opaque.png)

## AP90-r2 最终运行回执

run **ap90r2parent-f5c66d0b**；请求300秒，含启动与收尾实际302.156秒，无提前停止。无symbol lookup error、guest fatal或GPE拒绝；receipt和combined required missing均空。QEMU exit0、process_reaped、inputs_unchanged；独立确认host PID缺席、两把锁FREE。原im PID228末次完整maps为guest uptime298.48，包含/usr/bin/im.elf。

原UUD返回0、mode143=1/option145=0，继续原正常开机路径。未注入按键或ready事件。三个父资源记录在第一次源绘制前补登记，另有两个屏幕对象；每条资源来源均有原成功事件、同类vptr和原对象字段。

73份完整144B原参数逐项与AP89审计输入完全一致，无缺失/不完整GPE_CMD marker。76次像素命令SCOPE均未观测到分配活动/native count变化；这不证明未覆盖的compaction/ABA不存在。

| op / 实际类 | dst/src格式 | flags | dst/src地址在屏幕extent | AP90 result/reason | 条数 | AP89 result |
|---|---|---|---|---|---:|---|
| FillRect | 0/— | ff | 是/— | 0/OK | 1 | 0 |
| FillRect | 0/— | 1ff | 是/— | 0/OK | 2 | 0 |
| BitBlit 同尺寸通用 | 0/0 | 1000000000001 | 是/否 | 0/OK | 28 | 5 |
| BitBlit 最近邻缩放 | 0/0 | 1000000000001 | 是/否 | 0/OK | 36 | 5 |
| BitBlit 文字蒙版 | 0/2 | 10000000e0001 | 是/否 | 0/OK | 9 | 5 |
| Flush | — | 0 | — | 0/OK | 1 | 5 |

地址列仅描述请求基址；完整逐行跨度和区间身份由SCOPE/registry验证，不以“地址在范围”替代安全检查。

独立最终QMP stop/pmemsave读取43feb5000/140000，payload+100、640×480、stride640、逻辑fmt0，614400B、14种像素值，SHA256：

`fba3e9413bd407b9f113d0792706af6d263319b42286e5ddd1f101239b05b460`

最终PNG经实际目视，与首帧同为槽1存储卡读取警告。物理ring另保留1214个验证通过快照，均同一像素SHA；102张ring解释PNG加1张最终QMP PNG。ring有明确sequence gaps，不称完整连续帧序列。此处展示逻辑缓冲，无面板旋转/显示器合成验收。

![最终独立QMP读回：原厂槽1存储卡读取警告](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap90r2parent-f5c66d0b/ap90-QMP-logical-fmt0.png)

## 复核入口

- runtime/ap90-host-check.json、ap90-r2-host-check.json、ap90-audit-replay-check.json、ap90-trampoline-host-check.json。
- runtime/ap90r2parent-f5c66d0b-review.json、同run的gpe-statistics.json（77完整marker/73完整raw）与post11a-requests.json（14102条保存匹配记录，受原trace上限/串口交织限制，不称全局无损）。
- runs/ap90r2parent-f5c66d0b/receipt.json、serial.log、printk-decoded.txt、ap89-host-input-readback.json、gpe-surface-545.bin、osd-ring-readback.json及PNG。
- 首轮失败回执与helpers保留，未改历史run。STATE同步到本轮可见警告/输入未验收状态。

参考[A7C II维护者研究进展](https://github.com/chocotan/a7c2-qemu/blob/master/docs/tech/2026-10-31-current-progress.md)，使用本轮已验收的本地FX3原指令合同；未复制其格式字段位置或宽地址放行规则，亦不借其菜单结果替代本轮QMP读回。

