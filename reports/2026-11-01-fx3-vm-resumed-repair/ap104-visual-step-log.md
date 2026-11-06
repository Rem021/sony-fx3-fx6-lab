# AP104 逐步画面与选键记录

从运行时外层冻结的visual-decisions.json汇总，共6轮34键。每行列出决定该键前实际查看的PNG、当时画面描述及理由；SHA逐项与文件复核。末列为该键的自动读回文件，不以文件存在本身声称终态已经目视确认。导航由当轮画面逐步选择，未批量预排。既有runs和ledger均未改写。

## ap104v5trace600-65c08de2

[原始决策与SHA](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104v5trace600-65c08de2-visual-decisions.json)；[冻结回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v5trace600-65c08de2/receipt.json)。

| 步骤 / 键 | 已查看画面及路径 | 选键理由 | 自动读回 |
|---|---|---|---|
| 1 / MENU (0x1ab), 100ms | [ap102-phaseA-before-SETUP.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v5trace600-65c08de2/ap102-phaseA-before-SETUP.png)<br>实际查看：黑底拍摄待机，HD Fixed-59,94fps，橙色NO CARD，AF-C，D-R OFF及测光图标；无首次设置弹窗。 | 原厂待机已确认，发送一次MENU打开原生菜单，观察完成队列生命周期；全部30探针已安装，不改设置。 | [ap102-step-01-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v5trace600-65c08de2/ap102-step-01-settled.png) |

## ap104v6bretrace600-45dfde57

[原始决策与SHA](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104v6bretrace600-45dfde57-visual-decisions.json)；[冻结回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v6bretrace600-45dfde57/receipt.json)。

| 步骤 / 键 | 已查看画面及路径 | 选键理由 | 自动读回 |
|---|---|---|---|
| 1 / MENU (0x1ab), 100ms | [ap102-phaseA-before-SETUP.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v6bretrace600-45dfde57/ap102-phaseA-before-SETUP.png)<br>实际查看：黑底待机，HD Fixed-59,94fps、AF-C、D-R OFF、NFC与测光图标，无首次设置弹窗；NO CARD闪烁本帧未显。 | 待机已目视，29探针装齐，按一次MENU进入原菜单，观测真实完成队列领取/释放与回调，不改设置。 | [ap102-step-01-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v6bretrace600-45dfde57/ap102-step-01-settled.png) |
| 2 / LEFT (0x15), 100ms | [ap102-menu-step01-later.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v6bretrace600-45dfde57/ap102-menu-step01-later.png)<br>实际查看：Principal > Principal1 > Tx. quadros grav.，2/59；59.94p橙色瓦片，ISO100、AWB、PP11、XAVC S、Assist图标与灰面板完整。 | 菜单完整可见，按一次LEFT移向左侧组列，复现既有最小导航路径并观察原始owner/完成调用，不改设置。 | [ap102-step-02-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v6bretrace600-45dfde57/ap102-step-02-settled.png) |

## ap104v7trace600-da26dd55

[原始决策与SHA](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104v7trace600-da26dd55-visual-decisions.json)；[冻结回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v7trace600-da26dd55/receipt.json)。

| 步骤 / 键 | 已查看画面及路径 | 选键理由 | 自动读回 |
|---|---|---|---|
| 1 / MENU (0x1ab), 100ms | [ap102-phaseA-before-SETUP.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v7trace600-da26dd55/ap102-phaseA-before-SETUP.png)<br>实际查看：HD Fixed-59,94fps黑底拍摄待机，AF-C、D-R OFF、NFC与测光图标；没有首次设置弹窗。 | 29探针装齐且待机已目视，一次MENU打开原厂菜单，最小复现路径，新的异常PC持久化与清理格式已通过宿主负例，原PC门保持严格。 | [ap102-step-01-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v7trace600-da26dd55/ap102-step-01-settled.png) |
| 2 / LEFT (0x15), 100ms | [ap102-menu-step01-reviewed.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v7trace600-da26dd55/ap102-menu-step01-reviewed.png)<br>实际查看：Principal > Principal1 > Tx. quadros grav. 2/59，59.94p橙色瓦片，ISO100/AWB/PP11与完整图标、灰色面板。 | 已确认当前原菜单完整，LEFT从瓦片向左侧组列移动；保存真实完成队列逐代事件，下一键仍等实际读回。 | [ap102-step-02-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v7trace600-da26dd55/ap102-step-02-settled.png) |
| 3 / LEFT (0x15), 100ms | [ap102-group-step02-reviewed.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v7trace600-da26dd55/ap102-group-step02-reviewed.png)<br>实际查看：Principal1组列展开，橙色Principal1高亮，Principal2在下，右侧原59.94p/ISO100/AWB/PP11瓦片仍可见。 | 已目视确认第一LEFT到组列，现在再按一次LEFT移向最左分类栏，完成本轮最小复现路径，继续观察原始完成而不改设置。 | [ap102-step-03-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v7trace600-da26dd55/ap102-step-03-settled.png) |

## ap104light4menu600-c115023e

[原始决策与SHA](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104light4menu600-c115023e-visual-decisions.json)；[冻结回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/receipt.json)。

| 步骤 / 键 | 已查看画面及路径 | 选键理由 | 自动读回 |
|---|---|---|---|
| 1 / MENU (0x1ab), 100ms | [ap102-phaseA-before-SETUP.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-phaseA-before-SETUP.png)<br>实际查看：HD Fixed-59,94fps拍摄待机，橙色NO CARD、AF-C、D-R OFF、NFC/测光等图标，无首次设置弹窗。 | 轻量无断点候选已验证既有CP版本caller guard恢复；从真实待机按一次MENU打开原菜单，观察完成/分配/发送日志。 | [ap102-step-01-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-01-settled.png) |
| 2 / LEFT (0x15), 100ms | [ap102-step-01-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-01-settled.png)<br>实际查看：原菜单Principal / Tx. quadros grav. 2/59，59.94p、ISO100、AWB、PP11等瓦片已出现；高亮/面板仍在绘制过渡，不把此帧算完整菜单终态。 | 已可识别原菜单与左侧分类层级，按一次LEFT向组列浏览；记录原绘制并发下完成投递，不改任何设置值。 | [ap102-step-02-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-02-settled.png) |
| 3 / LEFT (0x15), 100ms | [ap102-step-02-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-02-settled.png)<br>实际查看：左侧Principal1橙色组列，Principal2在下，右侧59.94p/ISO100/AWB/PP11瓦片和图标可见。 | 组列焦点已确认，再按一次LEFT移到最左分类栏，随后依实际画面选择Setup方向。 | [ap102-step-03-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-03-settled.png) |
| 4 / UP (0x3), 100ms | [ap102-step-03-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-03-settled.png)<br>实际查看：最左home/Principal分类白色背景选中，Principal1/2组列及右侧参数瓦片完整。 | 当前最左分类已确认，按一次UP到其上方星标MeuMenu，再看画面选择下一键。 | [ap102-step-04-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-04-settled.png) |
| 5 / UP (0x3), 100ms | [ap102-step-04-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-04-settled.png)<br>实际查看：Meu Menu 1/59，星标分类白底选中，Conf. Meu Menu以及Adicionar item/Classificar item/Excluir等列表可见。 | 当前在最上星标分类，按UP环回最下黄色工具箱Setup分类，准备查看语言项，不执行任何删除菜单项。 | [ap102-step-05-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-05-settled.png) |
| 6 / RIGHT (0x1af), 100ms | [ap102-step-05-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-05-settled.png)<br>实际查看：Configur. 45/59，黄色工具箱分类选中；组1 Área/Data，右侧Idioma、Conf área/data/hora、Seletor NTSC/PAL可见。 | Setup分类与Área/Data已确认，RIGHT进入组列，随后按真实焦点选择Idioma语言项。 | [ap102-step-06-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-06-settled.png) |
| 7 / RIGHT (0x1af), 100ms | [ap102-step-06-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-06-settled.png)<br>实际查看：Configur. 45/59，Área/Data组橙色高亮，右侧Idioma/Conf área/data/hora/Seletor NTSC/PAL三项。 | 橙色焦点位于Área/Data组，RIGHT进入右侧第一项Idioma；只导航，不确认日期或修改其他设置。 | [ap102-step-07-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-07-settled.png) |
| 8 / ENTER (0x1ac), 100ms | [ap102-step-07-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-07-settled.png)<br>实际查看：Configur. > Área/Data 45/59，Idioma橙色整行高亮，当前值Portug. (Brasil)，下有日期时间和NTSC/PAL。 | Idioma真实焦点已确认，ENTER仅打开语言列表弹窗以复现完成队列路径，不确认改语言。 | [ap102-step-08-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-08-settled.png) |
| 9 / DOWN (0x30), 100ms | [ap102-step-08-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-08-settled.png)<br>实际查看：Idioma语言弹窗，列出Tiếng Việt、한국어、ภาษาไทย、Bahasa Melayu、हिंदी；底部Portug. (Brasil)橙色高亮且单选圈选中，MENU返回图标。 | 语言弹窗已实际打开，按一次DOWN仅移动候选焦点/测试列表环回，不按ENTER提交；随后将按图取消弹窗。 | [ap102-step-09-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-09-settled.png) |

## ap104light4bmenu600-09dcd746

[原始决策与SHA](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104light4bmenu600-09dcd746-visual-decisions.json)；[冻结回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/receipt.json)。

| 步骤 / 键 | 已查看画面及路径 | 选键理由 | 自动读回 |
|---|---|---|---|
| 1 / MENU (0x1ab), 100ms | [ap102-phaseA-before-SETUP.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-phaseA-before-SETUP.png)<br>实际查看：HD Fixed-59,94fps待机，橙色NO CARD，AF-C及D-R OFF等图标。 | 按MENU打开原设置界面；本轮按Lead msg_157c8eaf5a9b确认English并验证原厂保存，不写任何参数或强制flush。 | [ap102-step-01-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-01-settled.png) |
| 2 / LEFT (0x15), 100ms | [ap102-step-01-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-01-settled.png)<br>实际查看：Principal > Principal1 > Tx. quadros grav.，59.94p橙色瓦片，ISO100/AWB/PP11。 | 完整菜单可见，LEFT移至组列，准备按已确认的设置层级进入语言项。 | [ap102-step-02-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-02-settled.png) |
| 3 / LEFT (0x15), 100ms | [ap102-step-02-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-02-settled.png)<br>实际查看：仍是Principal参数瓦片画面，59.94p橙色；前次LEFT收发已完成，但此帧未呈现组列变化。 | 当前明确在菜单，继续一次LEFT向最左分类方向导航；不把过渡帧推断为已切组，下一步以实际焦点决定。 | [ap102-step-03-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-03-settled.png) |
| 4 / LEFT (0x15), 100ms | [ap102-category-step03-current.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-category-step03-current.png)<br>实际查看：仍在Principal > Principal1 > Tx. quadros grav.参数瓦片，59.94p橙色，前两次LEFT后画面没有改变。 | 当前仍明确位于瓦片，原GPE绘制已推进到Flush502；重新按一次LEFT向组列导航，按结果重新判断，不假定此前导航生效。 | [ap102-step-04-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-04-settled.png) |
| 5 / UP (0x3), 100ms | [ap102-step-04-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-04-settled.png)<br>实际查看：最左home/Principal分类白底选中，Principal1/2组列及右侧参数完整，焦点已在分类栏。 | 分类焦点已实际确认，UP到星标MeuMenu，为Setup方向导航。 | [ap102-step-05-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-05-settled.png) |
| 6 / UP (0x3), 100ms | [ap102-step-05-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-05-settled.png)<br>实际查看：MeuMenu星标白底焦点，1/59，Conf. Meu Menu与添加/删除等菜单条目。 | UP从最上星标环回最下工具箱Setup；只移动分类焦点。 | [ap102-step-06-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-06-settled.png) |
| 7 / RIGHT (0x1af), 100ms | [ap102-step-06-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-06-settled.png)<br>实际查看：Configur.45/59，工具箱白色图标焦点，Área/Data组及Idioma/日期时间/NTSC/PAL列可见。 | RIGHT进入Área/Data组列，准备选择语言项。 | [ap102-step-07-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-07-settled.png) |
| 8 / RIGHT (0x1af), 100ms | [ap102-step-07-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-07-settled.png)<br>实际查看：Área/Data橙色组列，右侧Idioma/Conf área data hora/Seletor NTSC/PAL。 | RIGHT进入右侧第一项Idioma，依实际高亮再打开弹窗。 | [ap102-step-08-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-08-settled.png) |
| 9 / ENTER (0x1ac), 100ms | [ap102-step-08-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-08-settled.png)<br>实际查看：Idioma整行橙色，当前Portug.(Brasil)；Setup Área/Data页面45/59。 | ENTER打开语言列表；本轮已有Lead授权确认English后观察原厂保存。 | [ap102-step-09-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-09-settled.png) |
| 10 / DOWN (0x30), 100ms | [ap102-step-09-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-09-settled.png)<br>实际查看：Idioma弹窗底部Portug.(Brasil)橙色且单选圈选中，前有Tiếng Việt/한국어/ไทย/Melayu/Hindi。 | DOWN从末项环回首屏，以实际English橙色焦点作为确认依据。 | [ap102-step-10-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-10-settled.png) |
| 11 / ENTER (0x1ac), 100ms | [ap102-step-10-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-10-settled.png)<br>实际查看：语言弹窗English首行橙色高亮，下有日本語/Français/Deutsch/Italiano/Español；English单选圈待确认。 | English焦点已实际确认，按ENTER依Lead msg_157c8eaf5a9b提交语言，再验证UI/RAM/原厂文件，而非推测持久化。 | [ap102-step-11-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-11-settled.png) |

## ap104light4save1200-2e5d177c

[原始决策与SHA](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104light4save1200-2e5d177c-visual-decisions.json)；[冻结回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/receipt.json)。

| 步骤 / 键 | 已查看画面及路径 | 选键理由 | 自动读回 |
|---|---|---|---|
| 1 / MENU (0x1ab), 100ms | [ap102-phaseA-before-SETUP.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-phaseA-before-SETUP.png)<br>实际查看：原厂HD/AF-C/NO CARD拍摄待机，D-R OFF/NFC等完整图标，非首次设置。 | 同一r4候选1200秒保存诊断，从待机MENU进入设置；按Lead授权验证English和原日期值原厂保存，不直接flush。 | [ap102-step-01-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-01-settled.png) |
| 2 / LEFT (0x15), 100ms | [ap102-menu-step01-reviewed.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-menu-step01-reviewed.png)<br>实际查看：Principal > Principal1 > Tx. quadros grav.完整菜单，59.94p橙色，ISO100/AWB/PP11。 | 菜单完整已确认，LEFT向组列；之后按实际焦点进入Setup语言项。 | [ap102-step-02-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-02-settled.png) |
| 3 / LEFT (0x15), 100ms | [ap102-step-02-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-02-settled.png)<br>实际查看：Principal1橙色组列，Principal2在下，右参数瓦片可见。 | 组列焦点已确认，LEFT进入最左分类栏。 | [ap102-step-03-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-03-settled.png) |
| 4 / UP (0x3), 100ms | [ap102-step-03-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-03-settled.png)<br>实际查看：home/Principal分类白底焦点，右侧Principal组/参数可见。 | UP移到其上星标分类，下一步按图进入Setup。 | [ap102-step-04-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-04-settled.png) |
| 5 / UP (0x3), 100ms | [ap102-step-04-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-04-settled.png)<br>实际查看：MeuMenu星标白底，Conf. Meu Menu列表。 | UP从星标环回底部Setup工具箱分类。 | [ap102-step-05-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-05-settled.png) |
| 6 / RIGHT (0x1af), 100ms | [ap102-step-05-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-05-settled.png)<br>实际查看：Configur.45/59黄色工具箱分类，Área/Data和Idioma等内容。 | RIGHT进入Área/Data组列。 | [ap102-step-06-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-06-settled.png) |
| 7 / RIGHT (0x1af), 100ms | [ap102-step-06-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-06-settled.png)<br>实际查看：Área/Data橙色组列，右侧Idioma、日期时间和NTSC/PAL。 | RIGHT进入Idioma语言行。 | [ap102-step-07-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-07-settled.png) |
| 8 / ENTER (0x1ac), 100ms | [ap102-step-07-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-07-settled.png)<br>实际查看：Idioma橙色高亮，当前Portug.(Brasil)，Setup Área/Data。 | ENTER打开语言弹窗，确认English后验证原保存。 | [ap102-step-08-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-step-08-settled.png) |

## 每轮最后实际查看结果

| 运行 | 截图 | 观察 |
|---|---|---|
| ap104v5trace600-65c08de2 | [ap102-menu-step01-late.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v5trace600-65c08de2/ap102-menu-step01-late.png) | 已查看：仍为部分待机OSD过渡，不算完整MENU。 |
| ap104v6bretrace600-45dfde57 | [ap102-group-step02-later.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v6bretrace600-45dfde57/ap102-group-step02-later.png) | 已查看：仍是参数瓦片；该轮第三键未发。 |
| ap104v7trace600-da26dd55 | [ap102-category-step03-reviewed.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v7trace600-da26dd55/ap102-category-step03-reviewed.png) | 已查看：最左分类焦点、组列和右侧菜单内容。 |
| ap104light4menu600-c115023e | [ap102-step-09-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4menu600-c115023e/ap102-step-09-settled.png) | 已查看：English焦点，尚未ENTER确认。 |
| ap104light4bmenu600-09dcd746 | [ap102-step-11-settled.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4bmenu600-09dcd746/ap102-step-11-settled.png) | 已查看：英文菜单，English实际提交到RAM；未证明落盘。 |
| ap104light4save1200-2e5d177c | [ap102-language-step08-reviewed.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/ap102-language-step08-reviewed.png) | 已查看：语言弹窗只部分画出Tiếng Việt/한국어，随后unfetched；第9键未发。 |

v6b另在停机后补看[osd-frame-000090-format0-RGBA-opaque.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104v6bretrace600-45dfde57/osd-frame-000090-format0-RGBA-opaque.png)，确见橙色Principal1组列；这是事后画面证据，未用于发送下一键。raw SHA与末次序97一致的核对见[主报告](ap104-passive-completion-trace.md)。

新性能AP105尚未运行，本表不含AP105或用户TRY1输入。
