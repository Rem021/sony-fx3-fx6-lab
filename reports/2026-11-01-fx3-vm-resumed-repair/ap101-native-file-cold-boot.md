# AP101 原生文件冷启动与English（普通保存待触发）

**最新r4完整600秒health通过，原生文件冷启动直接待机，UUD4/4与force0核实，菜单Language已改为English且原AP RAM键已变0。最终原生文件仍为旧语言32，持久化尚未通过；不直接flush，等待原保存触发审计与AP102。**

详见[AP101-r4完整报告](ap101-r4-english-ram-save-pending.md)、runtime/ap101-r4-runtime-evidence-v1.json。以下是保留的历轮回执和修正来源。

## 首轮preAP观察门失败（历史）

**原文件已由原 backup 模块加载并逐字吻合，但本轮未执行600秒，也未启动AP/UI。** 新观察门错误依赖guest BusyBox的sha256sum applet，而该applet不存在；这是worker新增校验代码的问题，不能归因原固件。

基线AP100，CPIO仅替换`/setting/Backup.bin`与init，移除模拟RAM回放binary及raw input，其他模型/原ELF逐字不变。源文件2229740B，SHA `552fd5f8b422f855aecbe0c3918b56f83f60fb76ea9a3b6fc7a0291c26035d9e`，AP/CP两段原checksum复核通过。

`ap101v1nativefile600-7c9e5597`：原backup.ko native insmod0；AP启动前QMP读回AP段857900B、CP段1369580B，二者与源文件各自逐字节相同、两段checksum有效；原两force键为0。旧固定date偏移0x9100c读到0，日期服务是否已设置及原UUD4/4还没有AP运行证据，不据此下结论。

该轮5.051秒受控停止，QEMU0/reaped/PIDabsent，输入SHA重新核验一致，双锁free，零按钮/PNG/原assert。严格health=false，原因是preAP新门早停，未完成600秒。运行内存pcidma绑定已生效，但文件观察器/退出控制尚未启动，故该早停轮**没有API解绑/恢复证据**；QEMU退出已销毁运行内存，未改原Image/ko。r2已改为preAP前先启动现有O_RDONLY文件观察与退出控制，再由QMP核实际文件SHA，避免再依赖不存在的applet及遗漏早停恢复。

还有明确的构造状态差异：原loader完整保留原厂保存的CP头，CPbank相较旧CP fixture仅offset9（SuspendComp 0→1）及offset0x20（native checksum +1）两字节变化。其余1369578B逐字相同。旧模型cp_setup首次初始化硬固定factory FNV `9c88411e0172b013` / Suspend0；新原生文件CP FNV `ee5c1a03bd34104f` / Suspend1。若保持旧初始pin，新文件上首次CP同步必被拒绝，不能靠重置bank或静默放宽校验解决。

已生成仅供review的v5-native101：初始CP数据pin改为确切原生文件CP SHA `b76c2f6c8caf62aa4dd11d0466575f38e12e9b6288d2d003ce326ce5530212e8` / FNV；首次payload初始化时读取实际SuspendComp1。没有改变lock/DMA/unlock、地址域、callback、reset、日期或业务参数算法。原保存CP bank跑全套backend/原F1F4回归ASan/UBSan通过，含失败回滚和API恢复。由于Lead原指令要求“其余模型不变”，尚未将该构造适配打包/运行，等待Lead明确选择。

证据：`runtime/ap101-first-load-evidence-v1.json`、`ap101-r2-review-proposal-v1.json`、`helpers/check-native101-backend-v1.log`；原run保持不改写。

菜单语言预备路径来自[Sony FX3官方Language帮助](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000845207.html)：MENU → Setup → Area/Date → Language，待本轮实际PNG核对，不把文档路径当运行成功。


## r2：原文件直接开机到待机，MENU新clip阻塞

Lead msg_554068dbc450批准“模型初始状态跟随原 loader 实际加载内容”：v5只把初始CP bank pin换成上述原生文件精确SHA/FNV，并首次读取真实SuspendComp1。两字节差异来自原save置SuspendComp1和对应checksum；所有原有lock/DMA/unlock/地址域/callback/reset/date算法不变。r2先起O_RDONLY文件导出与退出控制，再做preAP校验。

`ap101r2nativefile600-425d4d97`：原loader返回模块init0，实际guest文件SHA552fd5f8…由O_RDONLY/QMP核过，AP/CP整段逐字吻合、原checksum正确。零按键直接进入HD / Fixed-59,94fps、+0.0/---待机OSD，[phaseA PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r2nativefile600-425d4d97/ap101-phaseA-before-SETUP.png)。没有进入首次语言/设置流程，Lead msg_60dd62839249已验收直接待机。

UUD原键由bank原索引只读解码：02cf1841/02cf1842在offset9ce74/9ce78均u32=4，两force键均0。最初把UUD判定观察点mode1431/option1450误当成这两个Backup键；Lead已澄清该判定是正常开机非UUD路径，不是4/4合同差异。日期原键02cf01b4=0，原cache current/next也0，报告保留数值，不将缺少单独枚举证据的0擅称MANUALLY。已设状态仍需按原定义解释。

实际只执行step01 MENU（2个原生down/up事件），出现[葡语MENU首帧](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r2nativefile600-425d4d97/ap101-step-01-key-1ab.png)，Principal > Tx. quadros grav. 2/59，59.94p/ISO100/PP11。随后原seq712 BitBlit在规划stage=plan被新GPE_BOUNDS拒绝：源6×32、目的6×42，目标起点(501,432)，clip(501,426,136,1)为426..427高度条，交集为空。首报把目的宽度笔误成96，原144B重解码已更正为6。原seq711同基址6×6成功，拒绝未到资源/lifetime阶段。旧backend-v6对空交集统一返回bounds；后续12个错误含Flush sticky传播，未绕过。

本轮153.802/600秒按首个新GPE拒绝停止，strict health=false。LEFT指令尝试时run已结束，门在任何写入前拒绝，未发送；English尚未更改。QEMU0/reaped/PIDabsent，输入SHA/双锁free，RM lease均一次free0，原assert0。原API16B恢复后QMP核回000b00b4fd7bbba9fd030091f35301a9，退出控制result0。缺DATE98_TRACE_BOUND是已设置冷启动没有32B日期set同步的条件marker，不是assert。

原文件观察到后台generation2、SHA eb70e888c27766b52d4e27f4353bc73d63fac325c6bb545d478bd156f588b26e，两bank checksum仍正确；此轮没有Backup_sync_all用户调用记录，不把该后台保存说成语言更改后保存。

Lead msg_b4d68a13192e要求先审原码再受限no-op。原libgpe固定SHA36387968…的cf2c/bbcc/c878路径，经9个原144B及空/非空边界向量的隔离原AArch64规划重放，都进入af30提交，在模拟接受transport0后原入口return0；selector2负控不提交且返回错误。该证据证明原命令规划接受空clip，未执行硬件像素，不冒充硬件oracle。完整proof在runtime/ap101-empty-clip-original-proof-v2.json。

已新建backend-v7/observer-v21：仅既有selector1/format/flags子集、源与目的完整自身几何和extent/lifetime/overlap校验通过、唯一差异为clip交集为空时，无任何像素读写，保留callback/status/Flush。测试用PROT_NONE像素页证明无访问，并覆盖seq712、九边界、bounds/stride/format/flags/stale/overlap拒绝、原callback先于status一次及lease退休、Flush旧错误传播；ASan/UBSan和原alpha/73原参数回归通过。下一轮只换GPE，重跑600秒并继续English菜单。

r2汇总：runtime/ap101-r2-runtime-evidence-v1.json；原run不改写。


## r3：已找到Idioma，新P74与屏外空clip契约

`ap101r3emptyclip600-49610a67`只换v21/backend-v7。零键直接待机仍复现；逐图MENU→LEFT→LEFT→UP（Meu Menu）→UP（Configur. Setup）→RIGHT到Área/Data，实际[第5步PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap101r3emptyclip600-49610a67/ap101-step-05-key-003.png)已显示45/59右侧Idioma。第7步RIGHT真实发送并接收，但绘制被新组合阻断，无该步完整PNG；不算完成选中/语言修改。实际7步14事件，前6步有完整QMP截图；记录在runtime/ap101r3emptyclip600-49610a67-visual-decisions.json与review-v4.json。

新seq712是另一条原参数，不是r2同参数：fmt0→0、selector1/K255、P73=1/P74=1，其余flags0、float1.0/1.0，dst(240,95,458,2)、src(16,0,32,2)、clip(224,95,416,2)，源码按未知P74返回GPE_UNSUPPORTED。原bbcc证据：源(16,0)折入texture基址（低32地址1093d500→1093d520），纹理坐标归零，reg474=001f0001；源为2的幂时保留大图元458×2，非2幂时原sprite会退到源尺寸，后者不在新准入内。原描述符程序与候选平铺采样分开：repeat_mask_v1依旧标approx，不称硬件像素oracle。

同批seq713/718/723为P74=0的dst x698/w16、clip截止x640；seq720/725为fmt2 dst x682/w32/height34、有效clip截止640。它们真实交集为空，但v7因完整名义dst要求x+w≤stride而bounds失败。Lead msg_a9a7efb598c7澄清：空交集只需源完整crop、目标实际clip在stride/extent内、原dst物理base属于同一owner，允许逻辑dst在屏外；像素零访问/lease/callback/status/Flush不变。非空只写交集。

r3在295.394/600秒自动停，strict health=false，原assert0，GPE拒绝是实际阻塞；empty_clip_noop实际marker数0，故只把v7列为宿主验证，不伪称本轮执行过空clip成功。QEMU0/reaped/PIDabsent/输入SHA/双锁free、RM一次free0、原设备API16B恢复核回。缺DATE99_CONSUMER_BOUND marker保持如实记录，不将其改成原assert或放宽健康。原文件后台generation2仍SHA eb70e888…，未改English。

v8/v22按msg_a13ef691c862与msg_a9a7efb598c7构建：仅P74exact1、fmt0→0、selector1/K255/P73=1、其他flags0、精确unity float、源宽高2的幂，源原x/y折入物理基址一次，目标相对坐标按sw−1/sh−1 AND取样，再用既有straight_over_v1；marker approx_tile=repeat_mask_v1。非2幂/非unity/K/flags/format/rotation仍拒绝。空clip按上述实际clip与原base校验。真实seq713/718/720/723/725加保护页无像素访问测试、七组完整buffer独立mask参考、源起点/坐标校正/clip、负控、原alpha及73参数回归均ASan/UBSan通过。下一轮仅换GPE继续。

日期值补充：date-service-set审计第66行定义native type0=civil/local、2=未设；第87行说明原BYBOOT seed使date187变0并真实读回进位。因此本轮原键与cache type0是有效civil时间，不是未设，也不应命名为MANUALLY。既有BYBOOT软件初始化仍在，不能冒称物理RTC持久化或无需初始化的时间恢复。force0与不再首次设置是独立实测。

r3完整汇总：runtime/ap101-r3-runtime-evidence-v1.json；原P74证明runtime/ap101-P74-original-proof-v1.json。旧run/helper保持不变。
