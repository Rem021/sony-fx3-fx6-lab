# lifecycle-v1 顺序按键与图像判读

运行：`runs/vmopt-20261103-lifecycle-guest18-1da10e34`。每次仅在当下 PNG 目视后写下一条白名单命令，等待该键的 PNG 再判断；上限30键，预留最后240秒退出。

- Phase A `ap102-phaseA-before-SETUP.png`：原拍摄待机，顶部 HD/Fixed-59,94fps/NO CARD，右 AF-C，下 D-R OFF 与 AWB，没有设置弹窗。下一键选择 MENU `0x1ab` 打开设置。
- Step 1 `ap102-step-01-key-1ab.png`：葡语 Principal 菜单出现，右侧 59.94p、ISO100、AWB、PP11 瓦片与底部 `Fechar` 可见，焦点在内容区。下一键 LEFT `0x15` 移向分类列。
- Step 2 `ap102-step-02-key-015.png`：Principal1/Principal2 组列展开，59.94p 瓦片仍高亮；焦点还未到最左图标列。下一键 LEFT `0x15`。
- Step 3 `ap102-step-03-key-015.png`：左侧 home 分类图标白底焦点，右侧 Principal1 瓦片。下一键 UP `0x3` 到星标分类。
- Step 4 `ap102-step-04-key-003.png`：Meu Menu 星标焦点，顶部 1/59，右侧自定义列表。下一键 UP `0x3` 从顶部环回 Setup 工具箱。
- Step 5 `ap102-step-05-key-003.png`：Configur. 45/59，工具箱焦点，Área/Data 与 Idioma 可见。下一键 RIGHT `0x1af` 进入 Área/Data 组列。
- Step 6 `ap102-step-06-key-1af.png`：Área/Data 组列橙色焦点，Idioma 位于右侧第一项。下一键 RIGHT `0x1af` 到 Idioma 项。
- Step 7 `ap102-step-07-key-1af.png`：Idioma 项橙色焦点，当前 `Portug. (Brasil)`。下一键中心 ENTER `0x1ac` 打开语言列表。
- Step 8 `ap102-step-08-key-1ac.png`：语言弹窗完整，底部 `Portug. (Brasil)` 橙色选中且滚动条到底。下一键 DOWN `0x30` 尝试环回首项，先看是否 English 焦点。
- Step 9 `ap102-step-09-key-030.png`：按键完成回执先于重绘，首图仍为葡语末项。只读迟到截图 `ap102-language-step9-late.png` 显示 English 首项橙色焦点、圆点未选；下一键中心 ENTER `0x1ac` 自然提交 English。
- Step 10 `ap102-step-10-key-1ac.png`：语言弹窗关闭，英文 Setup → Area/Date，Language 行显示 English；这是 UI 生效证据。先只读 RAM/Backup 原文件，再决定 MENU 关闭。
- Step 10 readback `ap102-language-english-open-state.json`：UI English 与 RAM `0x8dd85=0` 已对应；原生 Backup O_RDONLY snapshot generation2，但文件 `0x8dd85=0x20` 仍旧值，表示此刻尚无自然文件语义保存。下一键 MENU `0x1ab` 关闭菜单，随后 idle≥60s 再读。
- Step 11 `ap102-step-11-key-1ab.png`：菜单真实关闭，拍摄待机正常。距 step11 host 输入 73.979s 后只读 `ap102-english-closed-idle60.png` 仍为稳定待机，`ap102-english-closed-idle60-state.json` RAM language=0，原生文件 generation3、有效、文件 language `0x8dd85=0`，SHA `29cde2080c5101ccc461ae88ad1d9fae2236ea89db450815e762f5539525c0ae`。下一键 MENU `0x1ab` 再入设置以确认日期原值。
- Step 12 `ap102-step-12-key-1ab.png`：重新进入 English Setup → Area/Date，Language=English 焦点，下一行 Area/Date/Time Setting。下一键 DOWN `0x30` 到日期设置。
- Step 13 `ap102-step-13-key-030.png`：Area/Date/Time Setting 橙色焦点，Language=English仍在上方。下一键中心 ENTER `0x1ac` 打开该设置。
- Step 14 `ap102-step-14-key-1ac.png`：Area/Date/Time Setting 内 Area Setting 焦点；Daylight Savings=Off、Date/Time 行可见，显示原值 2021-1-1 12:09:03 AM、GMT+9.0。下一键 DOWN `0x30` 到 Daylight Savings 行，不改值。
- Step 15 `ap102-step-15-key-030.png`：Daylight Savings 行橙色焦点，仍 Off；下方 Date/Time 行，时钟自然前进至 12:09:30 AM。下一键 DOWN `0x30` 到 Date/Time。
- Step 16 `ap102-step-16-key-030.png`：Date/Time 行橙色焦点，原值 2021-1-1 12:09:54 AM；未改数值。下一键中心 ENTER `0x1ac` 打开编辑页并目视底部确认控制。
- Step 17 `ap102-step-17-key-1ac.png`：Date/Time 编辑页原值显示 2021-1-1 12:10:15 AM，年框焦点，右下为圆形中心键 `● OK`，左下 MENU Cancel。下一键中心 ENTER `0x1ac` 按原值确认，不变更任何数字。
- Step 18 `ap102-step-18-key-1ac.png`：编辑页返回 Area/Date/Time Setting，Date/Time 行焦点，日期仍 2021-1-1；时钟自然到 12:10:48 AM。UI 确认通过，文件 generation 和日期字节另核对，不把时钟前进算作编辑。
- Step 18 readback `ap102-date-confirm-open-state.json`：原生文件仍 generation3、SHA 与 English idle 时相同，date 字节 `0x9100c=0`；同值确认不预设会改变日期字段。下一键 MENU `0x1ab` 离开日期页，再观察自然保存。
- Step 19 `ap102-step-19-key-1ab.png`：从日期子页回到 English Setup → Area/Date，Area/Date/Time Setting 焦点，底部 `MENU Close`。下一键 MENU `0x1ab` 关闭菜单。
- Step 20 `ap102-step-20-key-1ab.png`：菜单关闭回到待机。距 step20 输入 76.980s 后只读 `ap102-date-closed-idle60.png` 仍稳定；`ap102-date-closed-idle60-state.json` 原生 Backup generation4、有效、SHA `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f`，RAM/file language=0，两 bank checksum 有效。与 generation3 文件仅 `0x20,0x2c,0x9b2ac` 三字节不同，`0x9100c` 日期字段仍0；这是原值确认的自然保存代次，不是日期语义变化。此后不再按键，观察性能/错误并预留收尾。

原生控制契约：Sony [Using the control wheel](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867591.html) 明示菜单中中心按压确认选择；Sony [Area/Date/Time Setting](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000843992.html) 给出本轮 MENU→Setup→Area/Date→Area/Date/Time Setting 路径。上述是 FX3 Ver.2+ 官方帮助；本轮具体 UI/虚拟按键结果仍由逐帧截图与 guest 回执单独证明。
