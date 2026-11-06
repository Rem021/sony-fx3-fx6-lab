# FX3 恢复包版本准入原代码证据

核查日期：2026-10-29。只读静态分析原 ELF／脚本；未执行任何 Sony 程序、脚本、guest 或模拟器，无相机、USB、管理员、Windows、UU、GUI 或设备状态写入。卷 UUID 已核对为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。本笔记最重要的新结论是：**旧 `sauu` 确有同版失败续行与显式 `-s` 放行分支；旧 SD 入口另有严格大于比较。当前7.02 body能证明 dat4／comp 的写入先后，尚不能证明当前p1选择哪条准入分支。**

## dat2 dat3 dat4 实际从哪里来 怎样比较

### Takeaway

旧2.04／2.05 SD更新器的版本来自 nflasha2 的 `updater/dat4`，机型／地区来自 nflasha1 的 `dat2/dat3`；不以 MAIN 是否还能拍摄作为这些字段的来源。版本比较是两字节拆开的无符号字典序，完整同版在这条 SD 条件函数里返回0。[原静态工件与全部哈希](../../version-admission/static-admission-evidence.json)

### Cited Findings

来源用下列简称。完整路径都在 `work/fx3-color-port-20261027/` 下；旧库根为 `input-20261028/engine-rootfs/2.05/`，当前body根为 `package-20261028/updaterfs/`。本轮逐字节重核：旧2.04与2.05下表前六项完全相同；当前body所附 `usr/lib/libupdatercommon.so` 又与旧表的 common 库完全相同。**未取得当前7.02 p1的 SD条件库。** [15份来源及6对字节比较](../../version-admission/static-admission-evidence.json)

| 简称／来源 | 字节数 | SHA256 |
|---|---:|---|
| SD：旧`usr/lib/libsdfileinputupdaterapi.so` | 60584 | `257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2` |
| common：旧`usr/lib/libupdatercommon.so` | 56032 | `537d4dc66029fed9bc413e8adc6ade638f1068716cf801536fd5476108a3b797` |
| core：旧`usr/lib/libupdatercorecommon.so` | 72864 | `b2b066b963a42d96556f811a773579eb16a0358de1b3a9206a1845c0df99bb74` |
| api：旧`usr/lib/libupdaterapi.so` | 105984 | `2c2915ecb998e2dfc1cbe90400b469db7a1aefa9669eb03e7f062591b022b2a7` |
| 旧`usr/bin/sdfileinput.elf` | 10296 | `19a505750d18bee713e9794dd203219c4201ce2ef4c950b2187415878d09f67e` |
| 旧`usr/bin/sauu` | 43728 | `c508baac1c5d46117b32a4d689d69bdd30d269eb0d64c47100c8160d070c6c00` |
| 当前7.02 `bodylib/libupdaterbody.so` | 143168 | `6582eba530025d17fab81420050433cd998714c922aa4c16fd4d5cdc5a378ee9` |

本轮33份原地址片段都保留原机器码、原文件SHA256、VA起止与该原字节窗口SHA256；虚槽结论来自ELF重定位，未根据函数名猜测。[原片段索引和7组虚表](../../version-admission/static-admission-evidence.json)

| 原函数／地址 | 输入与分支 | 已证明结果／原证据 |
|---|---|---|
| core `CurrentFirmware::GetInformation` `0xc060` | 临时挂载点字符串`0xda29=/tmp_updater/updater/current`；`0xc108`挂`/dev/nflasha2`，`0xc19c`调用getVersion；卸载后`0xc220`挂`/dev/nflasha1`，`0xc2a0`调用getModelAndRegion | 版本与机型来源是实际分区；不是 `/ramdsk` 复制件。[片段](../../version-admission/fragments/libupdatercorecommon.so-current-information.txt) |
| core `getVersion` `0xcdfc`；common `VersionFile` `0x768c`，`getDataSize` `0x72a4` | 基路径加`updater/dat4`；长度严格2；common `GetValue 0x72dc`按每字节左移`8*i`合并 | 读取2字节LE；`0xce34`取高字节作major，低字节作minor。没有就地BCD到十进制转换。[字段](../../version-admission/fragments/libupdatercorecommon.so-current-fields.txt)、[路径](../../version-admission/fragments/libupdatercommon.so-metadata-paths.txt)、[长度与读值](../../version-admission/fragments/libupdatercommon.so-metadata-read.txt) |
| core `getModelAndRegion` `0xcd30`；common ModelFile／RegionFile `0x76c4/0x76fc`，size `0x72ac` | 同一基路径分别加`dat2/dat3`；各4字节LE | dat2=model，dat3=region；读失败、长度不等会抛异常，没有本函数自动改成零的分支。[字段](../../version-admission/fragments/libupdatercorecommon.so-current-fields.txt)、[路径](../../version-admission/fragments/libupdatercommon.so-metadata-paths.txt)、[读取](../../version-admission/fragments/libupdatercommon.so-metadata-read.txt) |
| SD `getUpdateFirmwareInfo` `0xa3fc` | 打开包，虚槽`0x58=searchFDAT`定位后读`0x20c`字节；`0xa560–0xa57c`每16字节调用`SDDecryptorModule::DecScrambleWrapper`，后者`0x9270`跳`Dec_Scramble` | 变换后局部buffer`x29+0x60`：`+0x2d`到new.major，`+0x2c`到new.minor，`+0x30`到new.model，`+0x34`到new.region。这是旧读包函数，未拿7.02原包执行它。[读包](../../version-admission/fragments/libsdfileinputupdaterapi.so-sd-update-information.txt)、[虚槽](../../version-admission/static-admission-evidence.json) |
| SD `getFirmwareInformation` `0xa054` | current写信息结构`+0x0`，update写`+0x18` | current.major/minor/model/region分别`+4/+8/+0xc/+0x10`；update分别`+0x1c/+0x20/+0x24/+0x28`。[片段](../../version-admission/fragments/libsdfileinputupdaterapi.so-sd-get-information.txt) |
| SD `isVersionOK` `0x9fd4–0xa000` | `0x9fe0`比较new.major与current.major；低则0，高则1；相等后`0x9ff8`比minor，`0x9ffc cset hi` | `new.major>old.major || (major相等 && new.minor>old.minor)`；完整相等=0。[原分支](../../version-admission/fragments/libsdfileinputupdaterapi.so-sd-condition-comparisons.txt) |

- `execute_ufp.sh:7–15`的复制函数确从nflasha1取dat2/dat3、nflasha2取dat4到`/ramdsk/`，但只有`MODE_VERSKIP`分支调用它；`MODE_MSCRYPT=5`直接启动`sdfileinput.elf`。不能把MODE6备份／恢复元数据的作用挪到MODE5。[原脚本](../../../../fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/execute_ufp.sh)
- 当前7.02解密后UDTR头偏移`0x20`原字节为`02 07`，即minor=2、major=7；model=`0x91030080`、region=0。512字节头SHA256=`b1e8964250a2c45dc2928b4de99bb9dd9ded4c572cf8b378667361a9eade53c8`。这是原包头，不是机身dat4读回；也不是旧checker处理当前包的测试。[静态头回执](../../version-admission/static-admission-evidence.json)

### Inferences

- 若旧SD比较收到current=(7,2)、new=(7,2)，局部结果必为0；current低于(7,2)才通过版本子条件。这是按原分支推导，不充当前7.02 p1运行结果。[比较原件](../../version-admission/fragments/libsdfileinputupdaterapi.so-sd-condition-comparisons.txt)

### Gaps

- dat4在当前机身上的实际内容未读取；不能从机身菜单或包头推定个体分区现值。本轮也未继续解释所有版本号的BCD显示约定；同版字节相等结论不依赖该约定。

## 正常准入 失败续行与 MODE6 是否真的不同

### Takeaway

**可以证明原代码存在不同版本策略，不能证明当前7.02官方续行一定选其中哪条。** 旧 `sauu` 的同版放行依赖`!IsCurrentFirmwareValid`，显式`-s`则直接放行版本；旧`sdfileinput`调用严格比较时不消费这个有效标志。[sauu原分支](../../version-admission/fragments/sauu-sauu-version-admission.txt)、[SD main](../../version-admission/fragments/sdfileinput.elf-sd-main.txt)

### Cited Findings

以下表格以“未触发额外外部override predicate、读元数据成功”为前提；`sauu 0x4058ac`是另一份外部override逻辑，本轮保留原代码但不展开或将其当恢复入口。表中同版仅讨论版本子条件，仍有机型／地区及后续数据验证。[原版本代码](../../version-admission/fragments/sauu-sauu-version-admission.txt)

| 入口／输入 | 原地址与调用 | 版本结果 |
|---|---|---|
| 旧MODE5 → `sdfileinput.elf`，current=new，comp存在或缺失 | main `0x400a6c`经manager虚槽`0x30=VerifyUUDCondition`；通过才在`0x400a94`经`0x28=BurnFirmware`；checker版本函数没有comp参数或读取 | 同版均拒绝；没有在这条已读取路径找到comp缺失绕过。[main](../../version-admission/fragments/sdfileinput.elf-sd-main.txt)、[虚表](../../version-admission/static-admission-evidence.json)、[条件](../../version-admission/fragments/libsdfileinputupdaterapi.so-sd-condition-order.txt) |
| 旧普通 `sauu`，new比current低 | `0x405b80–0x405ba0`依次比较major/minor | 0，拒绝。[原件](../../version-admission/fragments/sauu-sauu-version-admission.txt) |
| 旧普通 `sauu`，new比current高 | `0x405b90`到`0x405c5c`或`0x405ba8` | 1，版本通过。[原件](../../version-admission/fragments/sauu-sauu-version-admission.txt) |
| 旧普通 `sauu`，同版且不是`-m` | `0x405bac`之后调用manager虚槽`0x40=IsCurrentFirmwareValid(bool*)`；API返回0才在`0x405c4c–0x405c54`返回`!valid` | current valid=true时0；valid=false时1；API报错时保持0。[版本](../../version-admission/fragments/sauu-sauu-version-admission.txt)、[API](../../version-admission/fragments/libupdaterapi.so-current-valid-api.txt)、[虚表](../../version-admission/static-admission-evidence.json) |
| 旧 `sauu -m`，同版 | 参数`-m`设对象`+0x28=1`；同版时`0x405bac–0x405bb0`直接返回该1 | 版本通过；这是Minor参数支路，未作当前恢复方案。[选项](../../version-admission/fragments/sauu-sauu-options.txt)、[版本](../../version-admission/fragments/sauu-sauu-version-admission.txt) |
| 旧MODE6 → `sauu -s`，任意新旧或相等版本 | 原字符串`0x408294="-s"`；`0x405888–0x4058a0`设对象`+0x29=1`；`0x405b78–0x405b7c`读该字节，非零到`0x405c38`返回1 | **原代码确实跳过版本比较，不只凭VERSKIP名字。** `0x405380–0x40538c`还选GetVersionSkipUpdater，后者传action enum7。[选项](../../version-admission/fragments/sauu-sauu-options.txt)、[版本](../../version-admission/fragments/sauu-sauu-version-admission.txt)、[工厂](../../version-admission/fragments/sauu-sauu-factory-selection.txt)、[action](../../version-admission/fragments/libupdaterapi.so-verskip-factory.txt) |

- `CurrentFirmware::IsValid 0xc9d4`挂nflasha2，在`0xca90/0xca98`检查`CompleteFlagFile`。common `CompleteFlagFile 0x9278`拼`updater/comp`，`BaseFlagFile::IsValid 0x908c`仅以stat成功为true。api `Firmware`构造时`0x116c8–0x116cc`缓存此结果，`IsCurrentValid 0x111ac`返回缓存，manager `0xfe54–0xfe60`将其交回上表。因此这里“valid”是**完成标记存在**，没有证明对appFw逐页验真。[有效性原件](../../version-admission/fragments/libupdatercorecommon.so-current-validity.txt)、[标记路径](../../version-admission/fragments/libupdatercommon.so-complete-flag-path.txt)、[stat](../../version-admission/fragments/libupdatercommon.so-flag-existence.txt)、[缓存](../../version-admission/fragments/libupdaterapi.so-cache-current-information.txt)、[返回](../../version-admission/fragments/libupdaterapi.so-cached-validity.txt)
- 旧SD bodyloader构造时也在`0x9d34`获取CurrentFirmware::IsValid并缓存到`+0x150`；但checker `GetCurrentFirmwareInfo 0x9cc0`只复制24字节信息，后续isVersionOK没有读有效性字节。这解释了同一份元数据为何可被两个入口区别对待。[SD bodyloader](../../version-admission/fragments/libsdfileinputupdaterapi.so-sd-bodyloader-current.txt)
- Sony官方FAQ将同版／旧版列为正常版本错误；该网页本身没有描述上述comp或sauu分支。本轮原页抓取超时，改以同URL官方搜索全文复核，不能用该正常UI文本否定代码中的失败续行分支。[Sony FAQ 00282342](https://support.sony.jp/electronics/support/compact-cameras-dsc-p-series/articles/00282342)

### Inferences

- **普通 `sauu` + dat4已经是目标版 + comp缺失** 是有原比较支撑的同版重装候选；**MODE6-s** 是另一个明确的版本准入候选。二者不是“当前FX3随便放官方同版包就恢复”的证明：选择器、当前p1程序、运输方式及其余门仍须接通。[sauu原分支](../../version-admission/fragments/sauu-sauu-version-admission.txt)
- 不能把MODE5、脚本MODE6、C++action enum6／7、发给CP的数值自动混成同一层。当前body endupdate脚本明确其action表为MSCRYPT=6、VERSKIP=7；旧common脚本却为MODE_MSCRYPT=5、MODE_VERSKIP=6。[body脚本](../../../../fx3-color-port-20261027/package-20261028/updaterfs/bin/endupdate.sh)、[旧common](../../../../fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/common.src)

### Gaps

- 精确未解问题：**当前7.02官方断电续行，若dat4已经新、comp仍缺失，实际经哪一个准入入口？** 旧sauu可放行，旧SD checker拒绝同版；当前p1的代码与上游选择者未取得，不能任选一条当当前保证。

## 当前7.02的写入时序 与签名机型门还约束什么

### Takeaway

当前7.02 body原件能证明“开始删除comp，完成阶段先写dat4，稍后才创建comp／删除mode”。因此dat4与comp不是一个原子成功状态；同时，绕过版本判断不会自动绕过机型、地区、签名或实际写入条件。[当前body原件](../../version-admission/fragments/libupdaterbody-7.02.so-body-start-flags.txt)、[完成原件](../../version-admission/fragments/libupdaterbody-7.02.so-body-complete-flags.txt)

### Cited Findings

| 层／真实原函数 | 地址／分支 | 能确认的顺序和条件 |
|---|---|---|
| **7.02 body** `UpdaterBody::Execute` | `0x124a4`调用StartUpdate，`0x124ac`才BuildInPlugin::StartUpdate；`0x128c8/0x12948`检查StopFlag／XmlConfigHandler::HasError，非停止且无XML错误后`0x12954`EndUpdate，再`0x12960`CompleteUpdate | 标记管理有实际caller，并非仅导出未使用函数。未执行实际更新。[执行caller](../../version-admission/fragments/libupdaterbody-7.02.so-body-execute.txt) |
| **7.02 body** `StartUpdate` `0x19bdc` | 跳表`0x1c25c`：action3→`0x19e24`，4→`0x19d5c`，5→`0x19d20`，6→`0x19d6c`，7→`0x19da4`；action6创建mode/mode5，7创建mode/mode6；随后`0x19d64`构CompleteFlag，`0x19e40–0x19e8c`存在则Delete | 在非accessory且挂载成功的上述body路径中，开始清comp。跳表原字节为`41 0f 00 13 21`，不是从enum名称猜分支。[StartUpdate](../../version-admission/fragments/libupdaterbody-7.02.so-body-start-flags.txt)、[虚表及跳表回执](../../version-admission/static-admission-evidence.json) |
| **7.02 body** `CompleteUpdate` `0x1a2f0` | 输入information.valid为真才在`0x1a534–0x1a544`组`(major<<8)|minor`，虚槽`0x40=setVersion` | `setVersion 0x19ad4`用同临时挂载基路径构VersionFile，`0x19b08`调用common::WriteValue；后者按2字节LE写dat4。[完成](../../version-admission/fragments/libupdaterbody-7.02.so-body-complete-flags.txt)、[setVersion](../../version-admission/fragments/libupdaterbody-7.02.so-body-version-write.txt)、[common写值](../../version-admission/fragments/libupdatercommon.so-metadata-write.txt) |
| **7.02 body** 完成标记 | 后面`0x1a9c4`才BaseFlagFile::Create(comp)；`0x1a9d8`Delete(mode)；再卸载 | dat4写入在comp创建之前。输入valid=false跳过版本写入，不能称每次调用都写dat4。[完整分支](../../version-admission/fragments/libupdaterbody-7.02.so-body-complete-flags.txt) |
| 7.02 body脚本 `us_crc32sum_appli.sh` | 检查`/ramdsk/dat4`存在后把dat2/dat3/dat4复制回各分区，并touch mode/mode6 | 与MODE6开始前保存dat4形成另一条“保留原版本元数据”的机制；无证据表明MODE5平时一定有该RAM文件。[原脚本](../../../../fx3-color-port-20261027/package-20261028/updaterfs/bin/us_crc32sum_appli.sh)、[保存调用](../../../../fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/execute_ufp.sh) |
| **旧SD门顺序** | `IsUUDConditionOK 0xa360`先getFirmwareInformation，然后虚槽`0x30`版本、`0x38`机型、`0x40`地区，前两者false即返回0；等式比较`0xa004/0xa018` | 版本→model精确相等→region精确相等；仅这些子门成功后main才调BurnFirmware。[门顺序](../../version-admission/fragments/libsdfileinputupdaterapi.so-sd-condition-order.txt)、[model/region](../../version-admission/fragments/libsdfileinputupdaterapi.so-sd-condition-comparisons.txt) |
| **旧SD后续签名层** | Burn后SDDecryptorModule::execWriteFirm `0x95b8`，`0x96b4`VerifySignature；返回非0抛`0x30002`，返回0才到`0x972c`后设置流解密参数并继续 | 前面的版本／机型门通过不是签名通过。该签名门位于SD管线的后续decryptor函数，不是前面的header字段比较。[签名调用与分支](../../version-admission/fragments/libsdfileinputupdaterapi.so-sd-signature-before-stream.txt) |
| **旧sauu机型／地区层** | `0x405e50`调用model helper，`0x405e70`调用region helper，`0x405e90`才version helper；前两者函数`0x405c64/0x405c9c`比较字段相等，没有`+0x29`的-s跳过 | -s跳版本不等于跳model/region。普通helper另外受外部override predicate约束；本轮不把那个override作为可用恢复操作。[helper](../../version-admission/fragments/sauu-sauu-model-region.txt)、[组合门](../../version-admission/fragments/sauu-sauu-guard-order.txt) |

### Inferences

- 在上述7.02 body完成路径中，存在“dat4已更新，comp尚未创建”的程序顺序窗口；断电是否恰好落入且持久落盘需另验，但**不能再假定所有更新失败后的dat4都仍是旧版本**。这正是恢复入口必须独立调查的原因。[写入到标记的原顺序](../../version-admission/fragments/libupdaterbody-7.02.so-body-complete-flags.txt)
- 完成标记存在与程序确实能启动、HEVC主录正常、任意修改可回退是不同证据；本轮只建立元数据／局部版本政策。没有生成修改包，也没有把缺少修改包用作阻止恢复研究的理由。[静态执行范围](../../version-admission/static-admission-evidence.json)

### Gaps

- **当前p1仍缺。** 其他研究员对完整7.02包的新审计没有发现0400_updater/nflasha1；当前U-body及MAIN的initrd不能冒充p1。此项使用同阶段独立研究员的来源回执，非本人重做整包枚举。[当前资产回执](../../current-updater-evidence/current-updater-asset-audit.json)
- 下一项最窄问题是：沿已定位的当前选择请求接收者，证明失败持久状态如何重入当前SD／普通UFP／其他分支，再取得或恢复**当前p1对应的 `sdfileinput main → VerifyUUDCondition/isVersionOK` 与 `sauu 0x405b54` 的版本对应代码**。在取得之前，旧2.04／2.05差异只用于构造可证伪恢复条件，不能承诺7.02同版强刷。
- 当前7.02整包签名／加密准入、当前p1所有模式的版本门、机身实际dat4／comp以及实际断电续行均未执行；7.02 body写点也不证明能从坏MAIN独立进入该body。

静态复核：`collect_static_admission.py`使用既有只读分析Python环境，生成15份来源指纹、33个精确原字节窗口、7组重定位虚表和6对旧版本全文件比较；所有6对完全相同。分析器和工件仅写在本stage的`version-admission/`，旧阶段未改。[复核脚本](../../version-admission/collect_static_admission.py)、[机器可读证据](../../version-admission/static-admission-evidence.json)
