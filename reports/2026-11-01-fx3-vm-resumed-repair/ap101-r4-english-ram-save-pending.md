# AP101-r4 原生冷启动、English 与待保存状态

**完整600秒健康；原厂保存文件冷启动直接到待机，UUD键4/4、force两键0、日期type0有效，MENU中已实际改为English。English已写入原AP RAM，最终原生文件仍保留旧语言32，持久化验收待原厂保存触发。** 未调用额外flush或改变保存时机，按Lead msg_229943504517等待`audits/backup-save-trigger`后确定AP102。

## 输入、模型与原生冷启动

输入是AP100原厂写出的2229740B `Backup-native-file-before-menu.bin`，SHA `552fd5f8b422f855aecbe0c3918b56f83f60fb76ea9a3b6fc7a0291c26035d9e`。CPIO的`/setting/Backup.bin`完整替换；RAM回放helper与raw input不再打包/执行。原backup.ko在Backup_load=1下native insmod0，preAP独立O_RDONLY双读/QMP SHA确认真实文件，原加载后AP857900B、CP1369580B与文件各自逐字相同且原checksum正确。

原加载AP bank按其完整索引解码：02cf1841/1842在9ce74/9ce78均u32=4；02cf0014/01070140在8eb51/6e7ac均0。`native_update_return0/mode1431/option1450`是正常非UUD开机路径，不是上述两Backup键。日期02cf01b4和原cache type0，对应有效civil/local，2才未设；既有原BYBOOT初始化仍运行并读回进位，不把这个枚举称为MANUALLY或真实RTC恢复。

CP-v5仅依批准把初始精确pin跟随原loader加载的原生CP bank，并读取实际SuspendComp1；旧fixture与新CP bank仅offset9及20h两字节不同，来自原save置SuspendComp及原checksum+1。同步/复制/回调/reset/date算法不改。相对AP101-r3只换GPE-v22/backend-v8，其他模型与原ELF逐字不变，DTB只更新initrd-end，runner与r3逐字一致。

## GPE新增受限语义

原cf2c/bbcc/c878指令与隔离描述符重放证明了空clip照常提交，以及P74=1源x/y折入物理基址、power-of-two源mask及大图元维持的生成行为；它们不是硬件像素oracle。依Lead msg_a13ef691c862/msg_a9a7efb598c7，v8仅fmt0→0、selector1/K255、P73=1/P74exact1、其余flags0、精确unity float及源宽高2的幂，按repeat_mask_v1候选取样再使用既有straight_over_v1。sourceXY只折入一次，clip偏移参与mask，非pow2/scale/K/flags/format/rotation仍拒绝。

空交集只验证完整源crop、目标实际clip在stride/extent内、原目标物理base属于同一owner；允许逻辑dst在clip/屏外。成功不读写任何像素，保留原lease/callback/status/Flush与错误传播。实际屏外seq713/718/720/723/725与PROT_NONE页测试、七组独立完整buffer mask参考、所有拒绝与旧alpha/73原参数回归均ASan/UBSan通过。

本轮实际tile成功marker **18**、emptyclip no-op成功 **5**，GPE拒绝0。原有fmt2、straight-over与nearest仍标近似；菜单某些文字重叠和高亮不可见仍是显示限制，不作像素保真或硬件触摸/liveview结论。

## 逐图按钮

|步|键|发键前实际观察截图与描述|选键理由|
|---|---|---|
|1|`0x1ab`|[ap101-phaseA-before-SETUP.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-phaseA-before-SETUP.png)：零键冷启动已直接拍摄待机：HD / Fixed-59,94fps，底部+0.0/---，中央黑底。|按MENU开始本轮菜单语言验证。|
|2|`0x15`|[ap101-menu-stable.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-menu-stable.png)：本轮补拍MENU稳定帧：Principal > Principal1 > Tx. quadros grav.，2/59，59.94p/ISO100/PP11。|按左键返回菜单分组层。|
|3|`0x15`|[ap101-step-02-key-015.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-02-key-015.png)：Principal1/Principal2分组列更完整，当前仍在Principal菜单，2/59。|再按左键返回类别层。|
|4|`0x3`|[ap101-step-03-key-015.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-03-key-015.png)：页眉仅Principal，分组列和网格位置改变，已退类别层。|按上键切到前一类别，定位Setup。|
|5|`0x3`|[ap101-step-04-key-003.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-04-key-003.png)：已到Meu Menu类别，1/59，右侧是自定义我的菜单条目。|再按上键切到Setup类别。|
|6|`0x1af`|[ap101-step-05-key-003.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-05-key-003.png)：Configur.类别45/59，Área/Data第一分组，右侧Idioma、区域日期时间及NTSC/PAL项目。|按右键进入Área/Data分组。|
|7|`0x1af`|[ap101-step-06-key-1af.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-06-key-1af.png)：Área/Data分组列完整，Idioma位于右侧第一项，45/59。|按右键选择Idioma项目，验证原先P74与屏外空clip绘制组合能完成。|
|8|`0x1ac`|[ap101-step-07-key-1af.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-07-key-1af.png)：当前面包屑Configur. > Área/Data，Idioma右侧明确为Portug. (Brasil)，下面区域时间与NTSC/PAL有橙色箭头；局部仍有过渡重叠。|按确定打开Idioma语言列表。|
|9|`0x30`|[ap101-step-08-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-08-key-1ac.png)：Idioma弹出语言列表，末页可见Tiếng Việt、한국어、ภาษาไทย、Bahasa Melayu、हिंदी、Portug. (Brasil)；背景当前值也是Portug. (Brasil)。|当前值是列表末项，按下键尝试回卷到首项English，并用读回列表确认。|
|10|`0x1ac`|[ap101-step-09-key-030.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-09-key-030.png)：下键后语言列表实际回卷首屏，English在首行，下面日本語、Français、Deutsch、Italiano、Español；选中高亮仍不可见。|列表回卷与末项DOWN动作一致，按确定选择首项English；随后必须以菜单文字变化核实实际设置结果。|
|11|`0x1ab`|[ap101-step-10-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-10-key-1ac.png)：菜单已实际变为English：Setup > Area/Date，右侧Language=English，Area/Date/Time Setting、NTSC/PAL Selector及MENU Close均为英文，45/59。|按页面MENU Close正常退出设置并返回待机，随后观察原厂Backup同步与实际文件保存。|

11步均有原生STEP_DONE与QMP raw/PNG SHA复核，并与原native committed ring匹配；共22 send/22 receive。step01即时图为绘制阶段空白，补拍`ap101-menu-stable.png`后实际查看再进行下一键，没有借旧run图。语言列表选中高亮不可见，以末页→DOWN→English首屏的实际回卷及ENTER后的英文标题/Language值验证，未把光标推断当最终成功。

关键图：[零键直接待机](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-phaseA-before-SETUP.png)、[Setup类别/Área/Data/Idioma](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-05-key-003.png)、[当前Portug.(Brasil)](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-07-key-1af.png)、[语言列表末页](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-08-key-1ac.png)、[DOWN回卷English首屏](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-09-key-030.png)、[Language=English与英文菜单](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-10-key-1ac.png)、[MENU正常返回待机](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-11-key-1ab.png)。

## RAM与文件明确分开

|来源|语言02cf0000（offset8dd85）|SHA256|存储checksum|
|---|---|---|---|
|原输入file|32|`552fd5f8b422f855aecbe0c3918b56f83f60fb76ea9a3b6fc7a0291c26035d9e`|AP/CP均有效|
|最终原生file generation2|32|`eb70e888c27766b52d4e27f4353bc73d63fac325c6bb545d478bd156f588b26e`|AP/CP均有效|
|最终原AP RAM|0（English）|`a20f0c92a790c0f911c443fab1eee204316f443ddb764d75e19d97eeea992fd6`|AP dirty，CP有效；不当存储文件|

原输入语言32对应本轮实际Portug.(Brasil)，原AP RAM改为0同时UI显示English，证明UI修改已写RAM。最终file仍32，因此不能宣称English已持久化。两UUD键保持4/4，两个force保持0，date type0。最终RAM与file原索引表逐字相同，逐一比较发现8个已存在键不同，其中02cf0000和02cf03fe都由20h变00h；其余计数/设置值保留原key编号，不臆定名称。完整逐键差异：[比较JSON](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap101r4tile600-be9996d0-all-indexed-keys-RAM-file-diff-v1.json)。

真实guest file通过O_RDONLY完整读两次相同后写入新软件观察区，再QMP核FNV和宿主SHA。generation1是输入文件，generation2是启动后台写出，发生在语言修改前；改语言及正常MENU关闭后无新代次、无Backup_sync_all用户观察记录。额外API flush、改Backup_save、参数/RAM注入均未执行。最终导出：[原生文件](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/Backup-native-file-final-before-shutdown.bin)，2229740B，保留两bank正确checksum；[原RAM](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/backup-reserved-ram.bin)，2232320B，作为dirty liveRAM证据。

“正常待机/关菜单尚未观察到同步”是本轮事实；普通设置的原厂保存触发机理还需新审计。现有启动期全task栈不冒充语言修改后的当前栈。没有通过人为flush制造持久化回执，也未把结束时用于回收的SIGSTOP当作相机原生关机序列。

## 完整窗口与收尾

请求600秒，回执607.718秒（含最终证据/恢复），early_stop=None；独立health_pass=true、missing=[]、原assert0、GPE nonzero0、完整GPE记录1851。QEMUexit0/reaped/PIDabsent、输入SHA全部复核一致、双锁free、RM lease全部原nativefree一次0。接受窗口前T(stopped)文本数0。

结束后软件退出控制停止本轮guest AP，仅为收尾，原deviceAPI16B恢复后QMP核回`000b00b4fd7bbba9fd030091f35301a9`；恢复helper/control均0，主module保持驻留直到QEMU退出。恢复后O_RDONLY文件SHA与窗口末相同。原件、旧run和冻结helper均未改写，无git、实机、清理废纸篓操作。

汇总：[ap101-r4-runtime-evidence-v1.json](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap101-r4-runtime-evidence-v1.json)；[独立review](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap101r4tile600-be9996d0-review-v4.json)；[语言/RAM/文件逐键回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap101r4tile600-be9996d0-language-RAM-file-key-comparison-v1.json)。历史失败轮及契约来源保留于[AP101阶段报告](ap101-native-file-cold-boot.md)。

Sony官方语言路径：[MENU → Setup → Area/Date → Language](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000845207.html)，本轮已经由原厂实际PNG逐步核对；私有结构、键与设备语义均来自固定本地原件和审计。
