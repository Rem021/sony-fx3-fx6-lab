# AP97-r2 常量透明度与原菜单导航

2026-11-02。**拍摄待机、MENU打开、DOWN×2/RIGHT/ENTER导航及Picture Profile页面已由逐步PNG证实；600秒生命周期已完成，严格回执见下。** 日期事务与force持久化仍未验收，不将界面前进视为原日期服务成功。

## 实现与验证

Lead `msg_155b0cf9b5b7`批准：新GPE20/backend6将既有`straight_over_v1`扩至selector1 BitBlit fmt0→0与fmt2/op14→0的K0..255；同尺寸及已有nearest几何保持，Fill selector0 K<255同式近似，K255保持原exact replacement。公式、量化、资源/边界/未知字段及sticky raster_failed/Flush保护不变；逐条标记approx_blend、formula与const_alpha。不是Sony硬件精度等价验收。

独立Python Fraction参考：40项fmt0/fmt1数学、35项A8数学；K0/65/128/254/255的seq998/999原144B命令几何整图FNV、source不变、目标padding/邻居不变、nearest与Fill。真实backend ASan/UBSan通过；原73FNV回归全部保持。两份新交叉库构建成功。Preset3在8处原字核验点只读观察日期return/force前后/回调/type5 daemon/两次Backup_write return；80900141原sync请求前后按原所有权记录，host mock实测args/result/errno、边界/event cap与请求无额外写。运行时原ASM GPR31/SIMD32/NZCV/SP自检及14点绑定通过。

新候选基于AP97-v1，仅两份simulation成员body变更（GPE与Preset），DTB仅initrd-end；capid48/panel2、OSD6、provider7、RAM191924ef与独立进程观测init均逐成员不变。原件与旧runs未修改。

## 逐步截图

运行：`ap97r2alpha600-cd3c48f7`；每个下一按钮均在工具查看前一PNG后写入12B软件控制页。完整路径、SHA、原ring匹配与理由保存在`runtime/ap97r2alpha600-cd3c48f7-ui-readback.json`和`-visual-decisions.json`。

|步|本步键|读回PNG|实际画面|下一键理由|
|---:|---|---|---|---|
|0|无|[phaseA-before-SETUP](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-phaseA-before-SETUP.png)|Language，English/日本語/Français/Deutsch/Italiano；English为首项。|ENTER确认English。|
|1|ENTER|[step-01-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-01-key-1ac.png)|Creators App手机初始化提示；底部删除/C4 Set on the camera。|DELETE/C4按屏幕提示进入本机设置。|
|2|DELETE/C4|[step-02-key-1f8](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-02-key-1f8.png)|Set Area/Date/Time，Enter/Cancel。|ENTER进入区域设置。|
|3|ENTER|[step-03-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-03-key-1ac.png)|早期帧仍为上页（与step2 SHA一致）；area-late补图实见Tokyo/Seoul、GMT+9与OK。|看完补图后ENTER确认区域。|
|4|ENTER|[step-04-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-04-key-1ac.png)|Date Format：Y-M-D/M(English)-D-Y/M-D-Y/D-M-Y。|ENTER确认当前格式。|
|5|ENTER|[step-05-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-05-key-1ac.png)|Date/Time：2021-1-1 12:00:00 AM，OK。|ENTER提交日期；事务成功需单独证据。|
|6|ENTER|[step-06-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-06-key-1ac.png)|Auto Power OFF Temp High说明，Set now/Set later。|DOWN选择Set later。|
|7|DOWN|[step-07-key-030](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-07-key-030.png)|同温度提示；PNG和set-later-late均与step6 SHA一致，无可辨高亮。|DOWN已原生接收，ENTER确认，通过下一页验证选择。|
|8|ENTER|[step-08-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-08-key-1ac.png)|HOME设置提示，Set now/Set later。|ENTER确认当前项并继续。|
|9|ENTER|[step-09-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-09-key-1ac.png)|Creators App图片传输/遥控拍摄说明，MENU地球Smartphone Connection路径。|ENTER关闭说明。|
|10|ENTER|[step-10-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-10-key-1ac.png)|实际拍摄待机OSD：HD59.94p、+0.0、---；无传感器画面，standby-before-menu复核一致。|MENU打开菜单，之前先只读保存原RAM。|
|11|MENU|[step-11-key-1ab](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-11-key-1ab.png)|Main > Rec Frame Rate，2/59，Main1/Main2、59.94p、ISO100、PP11，底部Page/帮助/MENU Close。|DOWN浏览下一条目。|
|12|DOWN|[step-12-key-030](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-12-key-030.png)|标题变为Main > Main1 > Av Auto/Manual Switch，2/59；网格、59.94p、ISO100、PP11。|第二次DOWN继续浏览。|
|13|DOWN|[step-13-key-030](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-13-key-030.png)|标题变为Main > White Balance，2/59，白平衡图标。|RIGHT验证横向切换。|
|14|RIGHT|[step-14-key-1af](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-14-key-1af.png)|标题变为Main > Main1 > Picture Profile，2/59，PP11保持。|ENTER打开Picture Profile页面。|
|15|ENTER|[step-15-key-1ac](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-step-15-key-1ac.png)|Picture Profile页面，橙色PP11，MENU Cancel和圆键OK；picture-profile-late复核一致。|不再改设置，保持页面等600秒收尾。|

补图：[area-late](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-area-late.png) · [set-later-late](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-set-later-late.png) · [standby-before-menu](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-standby-before-menu.png) · [picture-profile-late](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap97r2alpha600-cd3c48f7/ap97r2-picture-profile-late.png)。相同SHA帧按相同图像描述，不把界面渲染器省略重复图像误读为黑屏。

## 原事务、绘制与持久化边界

第二次panel source81cf61c4/generation2/transaction112原1119消费free0。MENU时原先失败几何对应新seq806/807、865/866，fmt2 K128与fmt0 K65全部result0/reason0并标straight_over_v1；最终日志中10条完整K65/K128记录及3条完整Flush均result0；另有串口交错不完整记录保留，不宣称全局无损。未移除Flush保护。两次DOWN与RIGHT通过标题变化验证；ENTER进入橙色PP11页。未改变PP值，不声称所有菜单/控件视觉完整或传感器/拍摄工作。

预MENU原RAM：`backup-after-setup.bin`，2232320B，SHA `57982207d1a30964e2eb24764329b92267cca03d097839b5c6934e5b930edcd0`。准确键字节：语言02cf0000=0，force02cf0014=1、01070140=1，日期02cf01b4=0（一字节值，不能跨到相邻字段解u32）。是原liveRAM，不是有效持久文件；两force未归零，禁止把它当成已能跳过首次设置的输入。

日期观测只见启动期`FX3_DATE97_SYNC phase=before event=1 bytes=32 captured=0`，无return、8个日期成功路径点或两次Backup_write返回；`captured=0`不提供完整包，不能据此补猜日期成功模型。此缺失观测不影响已经独立验证的15步原输入与菜单像素。新增required marker `FX3_DATE97_POINT`未出现时，严格missing/health按原回执保留失败；不能把生命周期、无assert与完整观测通过混为一项。

## 收尾核验

请求600秒，实际602.855秒；QEMU退出0，reaped=True，PIDabsent=True，输入SHA复核=True，双锁释放=True；early_stop=None。

原assert条数0，GPE拒绝0；missing=['FX3_DATE97_POINT']，严格health=False。独立review-v4与acceptance已保存，旧run未改写。进程/输入/锁生命周期独立通过；43组原全线程快照均未见stopped，最后一组191线程，软件控制页最终done=control_step=15、failed=0、queue_exists=1。

方法：沿用[QEMU官方QMP文档](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html)的stop/pmemsave/cont/quit只读取证；初始化界面参考[Sony官方说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888870.html)，私有线协议和实际画面结论均来自固定原件及本轮回执。


AP98 路径更正（Lead msg_2c43f8a7ac82）：原2d7e6f4属于remote日期序列，不是首次设置的sequence_clock::date_time_initial_setting（2b725c8/2b72680/2b72684）。AP97-r2的missing按历史回执保留，但旧观测点未命中不能单独作为首次日期事务失败证据；force两键仍1是独立事实，具体等待由AP98原32B/内核44B及线程栈进一步取证。
