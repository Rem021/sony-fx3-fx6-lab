# AP100 原生首次设置与 CP Backup 同步

**本轮600秒健康，原厂首次设置完成，manual force两键自然清0并独立读回0，实际待机OSD与MENU打开/向下浏览已验证。** Lead在msg_ebab9bedf83a验收AP100并授权AP101使用本轮原厂写出的真实Backup.bin开机。未把黑底OSD说成实时视频或硬件完成。

## 实现与验证

基线AP99-r2，独立新版本capid49-touch100、CP-backup-v4-sync100、preset-context-v5-sync100、Backup-return-v4-sync100。0146只接受完整10B `0d2046010a0001800100`，用原native source/12B owned reply `0d2046110c00018000005900`，同ON1独立事务可重复；源/线程/issued generation/transaction/owned reply逐次约束，分配发送失败回滚，原request保持caller所有权，原AP自然free回复。配置ON/pending_hardware，未造f02f硬件完成或触摸样本。

CP仍唯一public owner。operation30只接受40B精确lock(3,1)/unlock(0,1)、actual sourceQ/chip/header/page/scalar/pointer/subsystem字段；Lock把当前CP软件bank的SuspendComp置1，冻结1369580B完整快照，再投独立native4096B reply/source003e0811/+32mode1；unlock mode0不清SuspendComp。数值Q可在原动态分配释放后合法重用。软件尾4056B清0，明确区别原opaque尾。

pcidma仅原backupfile_get_cp_data调用点和精确40B已定义描述符生效：CP remote404000000映射当前软件CP backing4040d2000，AP目标同4040d2000，故source_alias_destination=1；先冻结真实当前bank，实际copy到目标、全字节验证，再调用原backupfile_cb_getcp(0,0)一次。不是直接signal sem或只回成功。非目标调用者经精确relocated原API继续原行为；目标错误返回错误，无callback，失败unlock不掩盖DMA失败。标synthetic_cp_backup_sync=1/original_CP=0。

原kernel无kprobes，确认kallsyms及aarch64_insn_patch_text原4.9 ABI；只在运行内存以原同步patch API绑定设备API首16B，原Image/backup.ko不改。原word `b4000b00 a9bb7bfd 910003fd a90153f3` →绑定绝对跳转；结束后在接受窗口外停止本轮AP，由驻留解绑helper恢复原16B并QMP独立核回，主module不卸载，避免内核栈悬空。

ASan/UBSan测试覆盖精确包与逐字节变异、源/长度/线程/进程/lease、重复ON1、同数值Q重用、原CP88 F1/F4、锁解锁顺序、4096B回复所有权、真实目的字节恢复、复制后模拟校验失败回滚、回调仅一次、分配/发送失败、payload完整性/原生checksum刷新、非目标转原API、绑定失败及恢复。原kernel/七个新增被动user点静态guard见[绑定原码证明](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap100-original-binding-proof-v1.json)。

## 原生关键证据

- 原0146 source81cf61c3、lease113/generation1：commit→原nativefree0→CONSUMED；原2d9e764 touch_return0。原807b002b先行no-wait请求未补回复。
- CP同步epoch1 Q803e61c3、epoch2 Q803e61c0，均lock→完整真实copy→原callback一次→unlock native send0/free0；首epoch复制FNV399f17e80ec509b8一致。原AppBackupDaemon的Backup_sync_all两次return0，原2b237f8 notify在busy0，原sync_and_wait_comp完成点2b047fc已返回，未手清busy或通知。
- 手动日期原2b725c8→2b72680→**2b72684 w0=0**；32B原同步第二次before/after return0，原内容未被observer改写。两个原Backup_write value0/native_return1（成功字节数）；两个原Backup_nread(key,buffer,1) return1/value0。boot option1的先前value1与后续manual0分别保留。
- CP99软件clock最终generation3、UTC有效/errors0、type4count2；AP阶段原44B/type2往返和32B同步有QMP独立保存。不是Sony CP原执行或真实RTC写入。

## 每步实际画面与选键理由

选择类界面需借标题/页面变化推断光标：选中高亮不可见；一些即时QMP截图处于空白或局部绘制阶段，用本轮后续原始ring帧补充并实际查看。第2步最初误记English高亮，现明确纠正：只有Language标题，无选中证据，实际进入葡萄牙语；English选择不算通过。Lead允许继续本轮核心验收。

|实际步|键|观察截图与描述|选键理由|
|---|---|---|---|
|1|`0x3`|[ap100-phaseA-before-SETUP.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-phaseA-before-SETUP.png)：phaseA PNG仅有Language标题和右下帮助图标；随后已查看本轮osd-frame-000006-format0-RGBA-opaque.png，完整列出English、日本語、Français、Deutsch、Italiano，未高亮。上键理由基于该后续原始帧。|按上键使语言列表选择English，随后读回本轮截图确认。|
|2|`0x1ac`|[ap100-step-01-key-003.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-01-key-003.png)：step01 QMP实际仅有Language标题和右下帮助，没有English橙色高亮；此前English选中描述属于未验证误读，不能作为English选择成功证据。step02读回已实际查看：葡萄牙语手机引导页。|English已明确选中，按确定进入下一原厂设置页。|
|3|`0x1f8`|[ap100-step-02-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-02-key-1ac.png)：葡萄牙语手机引导：可用smartphone和Creators App完成初始设置；底部删除/C4图标旁写Definir na câmara，右下MENU返回。|按照当前页面删除/C4旁的在相机上设置提示，进入相机内首次设置。|
|4|`0x1ac`|[ap100-step-03-key-1f8.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-03-key-1f8.png)：葡萄牙语提示Ajustar Área/Data/Hora，下方Enter和Cancelar，右下MENU返回；没有可见橙色选中条。|按确定尝试进入当前区域/日期/时间设置提示的Enter选项，并以随后截图验证实际结果。|
|5|`0x1ac`|[ap100-step-04-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-04-key-1ac.png)：区域设置Configur. da Área，Tóquio/Seul；底部2021-1-1 12:00:00 AM GMT+9.0，左右区域箭头，确定OK与MENU取消。上一提示残留在中间，属于早期绘制画面。|区域页面已切换到东京/首尔，按页面确定OK接受当前区域并继续日期时间步骤。|
|6|`0x1ac`|[ap100-step-05-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-05-key-1ac.png)：Formato de Data日期格式页，列出A-M-D、M (Portug)-D-A、M-D-A、D-M-A；没有可见选中条。|日期格式不影响本轮同步和force清除验证，按确定接受当前原生选项，随后以页面变化确认继续。|
|7|`0x1ac`|[ap100-step-06-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-06-key-1ac.png)：Data/Hora日期时间编辑页，显示2021-1-1 12:00:00 AM；底部MENU Cancelar和圆形确定OK。没有可见字段高亮。|按当前页面确定OK接受原生默认日期，触发首次设置的原生日时提交，并核查真实同步返回与force清除。|
|8|`0x30`|[ap100-step-07-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-07-key-1ac.png)：温度提示葡萄牙语：三脚架拍摄可把Temp. p/auto deslig.设为Alta以延长录像；选项Definir agora（现在设置）和Definir depois（稍后设置），无可见高亮。|按下键尝试选择第二项稍后设置，以继续首次设置；光标高亮不可见，下一步用页面变化验证。|
|9|`0x1ac`|[osd-frame-004890-format0-RGBA-opaque.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/osd-frame-004890-format0-RGBA-opaque.png)：温度提示仍完整显示Definir agora和Definir depois；step08即时及补拍仅有MENU图标，本轮后续ring4890 format0实际完整读回同一提示，高亮依然不可见。|上一步DOWN已发送并收回，按确定尝试确认移动后的选项；不声称已看见光标，以下一页面变化确认操作结果。|
|10|`0x30`|[ap100-step-09-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-09-key-1ac.png)：新提示Deseja configurar HOME para usar?（是否配置HOME），下方Definir agora与Definir depois，无可见高亮。|温度提示已通过；在新的HOME提示按下键尝试选择稍后设置，再以确认后的页面验证。|
|11|`0x1ac`|[osd-frame-005790-format0-RGBA-opaque.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/osd-frame-005790-format0-RGBA-opaque.png)：HOME配置提示在本轮后续完整ring5790中仍显示Definir agora/Definir depois；step10即时读回为空白，选择高亮不可见。|DOWN后按确定尝试确认当前HOME选项，并通过下个页面或待机实际画面验证退出提示。|
|12|`0x1ac`|[ap100-step-11-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-11-key-1ac.png)：Fixo/Variável（固定/可变）HOME分配页，说明HOME将分配给适合设置的按钮，显示Bot. Personalizado 4，底部右侧OK、左侧Con tecla/sel pers，MENU Cancelar；无可见高亮。|HOME提示实际进入了按钮分配确认页，先按确定尝试当前页面OK，以下一画面验证是否完成首次设置。|
|13|`0x1ac`|[ap100-step-12-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-12-key-1ac.png)：灰底Creators App说明页：可向手机传图和遥控，之后可通过MENU网络图标的Conex. smartphone设置连接；当前截图没有底部选项。|这是后续连接方法说明，按确定尝试确认并结束此提示，再查看是否进入拍摄待机。|
|14|`0x1ab`|[ap100-step-13-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-13-key-1ac.png)：拍摄待机OSD，HD / Fixed-59,94fps，底部+0.0与---；中央黑底，无实时视频。已保存preMENU v2 RAM并核验两force字节0，原生guest文件独立读回有效。|首次设置已实际退出到待机，按MENU打开原厂菜单并保存、查看菜单页。|
|15|`0x30`|[ap100-step-14-key-1ab.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-14-key-1ab.png)：MENU已打开，面包屑Principal > Principal1 > Tx. quadros grav.，2/59；网格中可见59.94p、ISO100和PP11，底部Página/帮助/MENU Fechar。部分标签与高亮缺失。|菜单已实际显示，按下键浏览下一项目，并核对页眉项目与页码变化。|
|16|`0x30`|[ap100-step-15-key-030.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-15-key-030.png)：菜单面包屑已由Tx. quadros grav.变为Alt Av Auto/Man.，仍为Principal > Principal1 2/59；网格仍含59.94p、ISO100、PP11。|原MENU下键已使当前项目变化，再按下键浏览同页下一项，验证连续菜单导航。|

所有16步各自QMP raw/PNG SHA与原native committed ring匹配；本轮共32 send/32 receive，16 native STEP_DONE。每步操作后的实际PNG在[独立review](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap100v1sync600-8d0d69c0-review-v4.json)的captures中列全。第17步RIGHT只排队，截止前未进入hostgate，未发送，无readback，不能算浏览或子菜单。

待机图：[step13](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-13-key-1ac.png)，HD / Fixed-59,94fps，+0.0/---，中央黑底。MENU图：[step14](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-14-key-1ab.png)，Principal > Principal1 > Tx. quadros grav.，2/59，59.94p/ISO100/PP11；[step15](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-15-key-030.png)页眉Alt Av Auto/Man.；[step16](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/ap100-step-16-key-030.png)及[最终原始ring9390](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/osd-frame-009390-format0-RGBA-opaque.png)为Equilíbrio Branco。菜单部分标签缺失/重叠，高亮不可见，alpha/fmt2/stretch仍为已标近似软件绘制，不作像素保真结论。

## 两类备份严格分开

- MENU前原RAM：[backup-after-setup-v2.bin](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/backup-after-setup-v2.bin)，2232320B，SHA `159d1b7b7b46117fb520f2dfffaeb89c26d9b65aad514abe90ed3458fc0cdcf0`；两force字节0，QMP只读，尚未MENU。它是liveRAM快照，不称合法存储文件。
- MENU前原生guest文件：[Backup-native-file-before-menu.bin](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap100v1sync600-8d0d69c0/Backup-native-file-before-menu.bin)，2229740B，generation7，SHA `552fd5f8b422f855aecbe0c3918b56f83f60fb76ea9a3b6fc7a0291c26035d9e`。独立guest observer以O_RDONLY对`/setting/Backup.bin`完整读两次且逐字节一致，复制到新增观察区41d400000/300000；QMP核FNV一致，宿主独立SHA。AP段857900B、CP段1369580B原sum校验均正确；文件两个force字节也是0。原输入种子SHA bf3a9d85…不变，导出文件确实不同。
- 原保存链间接而强：原Backup_sync_all两次return0，静态原路径在真实CP同步后直接调用backupfile_save(1)，真实文件多次generation变化且两bank checksum有效。**backupfile_save内部返回点未单独探针**，不伪称直接捕获该内层return；Lead已基于完整证据验收AP100。

## 收尾

请求600秒，回执605.859秒（含结束保存与恢复）；strict health=True，missing=[]，原assert0、GPE nonzero0，完整GPE记录1386。QEMUexit0/reaped/PIDabsent，输入SHA复核全部一致，双锁均释放，RM lease均nativefree一次0。接受窗口前T(stopped)文本数0；截止后的主动停止AP明确属于控制收尾。恢复后原16B QMP核回`000b00b4fd7bbba9fd030091f35301a9`，unbind/helper/control均result0，active0，主module驻留直到QEMU退出。

汇总：[ap100-runtime-evidence-v1.json](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap100-runtime-evidence-v1.json)；完整原日志保持不改写。按Lead msg_ebab9bedf83a继续AP101：去掉RAM回放，由原backupfile_load加载本轮原厂导出文件，验证已完成设置的冷启动与语言菜单。

原生同步patch API方法参考[Linux v4.9 arm64 insn.c](https://raw.githubusercontent.com/torvalds/linux/v4.9/arch/arm64/kernel/insn.c)；具体地址/首字节以固定原kernel本地证明为准。私有契约来自[0146原码审计](../../work/fx3-vm-20261101/lead-claude/audits/vdf0146-common-tail/README.md)与[Backup同步原码审计](../../work/fx3-vm-20261101/lead-claude/audits/backup-sync-cp/README.md)，不从其他机型借用。
