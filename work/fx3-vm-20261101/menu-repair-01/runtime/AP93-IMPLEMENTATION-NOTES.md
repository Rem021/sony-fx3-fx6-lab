# AP93恢复入口（2026-11-02）

唯一运行链，未worker_done。Lead合同msg_3600e62b68bd，原审计 rm-media-service proof SHA79eb7a80cfa7d57027bf4d934c1d5a76430320d5bb21f7af0ccf7e8a31da3bc7，--check 37blocks/42instructions PASS。

候选ap93-rm-empty-gated-input/candidate.json，从AP90r2健康基线；capid44/GPEv16r2/Backup不改。新增helpers/fx3-rm-empty-provider-v1.c/.so + rm-empty-core-v1.h（112B原配置、cmd3缓存7B02000007000000、source=currentnotifyID、原OSAL分配/所有权、取消、未知80000003）+ rm-key-gate-v1.inc。provider在原dlopen(MediaDetect)前检查原80d9016e absent再reg_cb，单worker串行处理原callback收到request。使用过的版本不得改，修复另起版本。

被动观测复用media-observe-v1.so（AP92冻结），preset新v4-lastscreen仅额外导出原最后开屏时间，不改原语义。ASan/UBSan core测长度/配置/重复注册每次回放一次/取消/未知/alloc-send故障/只free一次通过；gate_host_check通过5合法3非法，只允许新增41df00000/64KiB页+8的8B主机命令，FDT+memrsv已检查不重叠。

run_candidate93.py运行300s/4A35/MTTCG。本轮最初run=ap93empty-9b0fd885；启动session37066，若重启先读STATE/receipt/ps，不重复。命令中新增纯本机Unix GDB g，run目录0700，QMP q。gate_input93.py只在QMP stop时通过Qqemu.PhyMemMode:1写软件页的seq/key，读回验证；不写原参数/回调。guest keyworker使用原OSAL807a0020/src410025发20Bdown/up，保持AP91表只读/receiver观察/NOLOAD门控。

阶段A要求：D原state2两次、notify1000/1010均仅0；FRONT原回调实际收到；原free7/136/28；无ThreadInit110/无Mount/无MOUNT_ERR；最后原开屏后至少host10s；先ap93-phaseA.json/PNG，然后仅MENU。两秒后ap93-step-01-key-1ab.png供实际目视。只有确实看到菜单后，才在新run内创建ALLOW_MENU_NAVIGATION，精确内容AP93_MENU_CONFIRMED，再由driver放行下/下/右/确定，每步PNG。未看到菜单绝不创建这个文件。遇RM未知/REJECT、state1/timeout/Mount/GPE新拒绝/致命即自动stop，取证escalation。

完成后跑新review（还未创建），更新STATE/中文报告/索引并向Lead发status。当前仍未验收空槽/UI。AP92r2仅构建从未运行，勿误启动。Heartbeat80723预计17:07UTC到期，持续工作时核对并新版本重启，不重复启动存活者。

## 16:49 UTC续记

首轮ap93empty-9b0fd885：15.184s/REJECT安全停，错误为回复动态ID被误要求stat+4非零，已封存review，13marker未到不算验收。Lead msg_4b9aaf398be5同意v2移除回复额外stat，保留原valloc/send校验与通知ID检查。

r2 ap93r2empty-77c94f2c：302.709s健康完整，missing[]，原空槽链state2/mask4&2/status0，无110/Mount/MOUNT_ERR，72GPE全0。阶段A原语言页；MENU两包接收0，PNG与阶段A相同SHA2485079b...708e。review_rm93.py已跑，独立报告JSON+最终PNG已生成，勿无条件重跑PNG断言。

Lead msg_f063a6eaccba授权r3：同协议，语言页下30/上3/确定1ac逐步PNG，之后每新页目视再默认确定最多12步；待机后MENU，菜单后下/下/右/确定。不得在r2再灌键；r2未创建ALLOW标志。

当前r3 ap93r3setup-d8c86a95，session78481，300秒4核MTTCG；driver run_candidate93_r3.py、候选ap93-r3-first-setup。新provider v3-setup仅key-gate-v2-setup/input93-plan-v1变化，RMcore仍冻结v2。observer v3-uipc仅原拥有且已由原osal_msg_size确认的FRONT回调和RM回复两个点有界直接copy（/dev/uipc映射pread失败原因已实证）；通用peek不改。新ASan/UBSan/最多20键步/最多12默认ENTER检查通过。运行前期两回复136/28和原FRONT7均readable1，完整raw闭合。

r3前3键自动下/上/确定，>=4秒间隔，各PNG在ap93-step-readbacks.json。其后必须实际看最新PNG，再写当前run/ap93-next-key.json：{"step":下一步整数,"key":"0x1ac","observed_page":"实际画面描述","authorization":"msg_f063a6eaccba"}；用MENU则key1ab，只在待机确认后；菜单出现后下30/30/右1af/确定1ac。host计划与guest计划均校验顺序/上限。旧控制json的step会被跳过，不需删除。若第三步ENTER后无画面/状态变化需立即取证escalation，不连发ENTER瞎试。

## 17:13 UTC续记：当前r5，唯一运行链继续

r3新目标已闭合已有原nativeOpen MA对象，ap93-new-target-original-proof.json记录L2592/type403/uhdl401/vptrlibObj+253a48/phys43ae96000/140000/epoch1，旧GPE仅within545导致首下键重绘被拒。Lead msg_4c95916cbc49授权修守卫，v17-native-target + registryv3只接受已原成功nativeOpen/type403/exactclass/livefields/epoch/perrow，sourceRO/同parent别名，lifecycle锁不变；ASAN/UBSAN完整旧suite与6类新目标拒绝回归PASS。无地址允许列表，双缓冲角色当时未证。

r4 ap93r4target-aa8bcce7，39.480s健康回收/missing[]，仅下键两包，新目标原绘制成功；138完整CMD全0，6交错/不完整（含src_fmt29是串口污染非真实支持格式）。原FB同7f58001140实际由bitmap7f5468ecb0/phys43feb5100/token402切至bitmap7f5468ead0/phys43ae96100/token401；OSD旧active545门拒绝capture，无ACK，driver安全停。review_rm93.py已跑，report ap93-empty-slots-first-setup.md已含r1-r4和STATE摘要，PNG文件已存在不能无条件rerun review。

Lead msg_91eda4ecac90/msg_781d1794767b授权OSD consumer与host导出按当前原FB/活跃bitmap/已登记原对象和epoch/state规则扩展，持原read_lease+raster_guard；hosttest旧epoch/FBswitch后重跑同输入脚本，无需再问。

新helpers：GPEv18-frame-target导出frame_target_acquire/recheck/release，必须已持snapshot guard，acquire同时持lifecycle锁贯穿copy；legacy545仍原proc/unit402/serial检查，nativeOpen403核对uhdl==原bitmaptoken/currentfields/localepoch/class；fulltuple10U。OSDv6-live-frame（corev4-frame）原bitmap lease/FB entry/size/fmt/stride/CPUmap checks不变，改用此tuple并前后重查/cleanup顺序target→raster→readlease。新ringV2 magic32474e495244534f，globalversion2，pixeloffset200/slotheader512，targettuple在d0..120，descriptor180..1a4，修正旧c0描述区覆盖map_end/offset字段的观测格式重叠。host osd_ring93_v4.py解析36U/metadata/CPU映射/epoch，key_readback93_v2_frame.py从最新验证帧phys独立QMP读回且SHA必须同nativelease已提交copy；PNG RGB透明度固定opaque与ring view一致，raw未改。不能把固定gpe-surface-545.bin称最终活跃帧；以逐步实际physicalPNG回执为准。

宿主：check-gpe93-frame-target + check-osd-core-v4-frame ASANUBSAN PASS，旧epoch/token/class/lifecycle拒绝、legacy545→native403切换、旧suite均保留；test_frame93_host.py验证36U/CPUmap/descriptor分离、任意已登记phys（非地址名单）、zeroepoch拒绝、QMP SHA同native且stalecontent拒绝。ap93-frame-export-host-check.json有完整回执。

当前运行：ap93r5frame-19bbfb81，session15462，driver run_candidate93_r5.py，candidate ap93-r5-current-frame-export/candidate.json，300秒4A35/MTTCG。截至17:12:55启动初期，无拒绝，未按键。前3步自动下30/上3/确定1ac、间隔>=4s、各PNG，之后必须实际看最新PNG并写当前run/ap93-next-key.json = {"step":下一步,"key":"0x1ac","observed_page":"实际内容","authorization":"msg_f063a6eaccba"} 来逐页默认确认（<=12次），待机后MENU，再菜单后下/下/右/确定。未知/新阻塞立刻取证escalation。不改协议/不写原参数/不直接调callback。

心跳已轮换：旧80723已正常退出；新PID14269，脚本orca_runtime_heartbeat_ap93.py，stopfile .heartbeat-stop-ctx_ee4f6943c8d7-ap93，log heartbeat-ap93.log，7200秒期限约19:01UTC。旧stop文件勿复用，新heartbeat存活勿重复创建。未worker_done，不结束运行链。

## r5完成：当前待offscreen-subblock审计，不自行启动下一轮

ap93r5frame-19bbfb81，50.704s遇新GPE目标/缩放子集拒绝主动停；exit0/reaped/PIDabsent/inputsunchanged/双锁FREE/missing[]，无guest致命，im228最后maps46.39s。review_rm93已跑，已有PNG勿无条件重跑；已enrich review将最终QMP545标为旧前台样本，逐步物理读回才是已验证当前帧。209完整CMD=206成功/3失败，10交错记录不计完整。RM state2/仅status0/无110/Mount/MOUNT_ERR，9个native OSAL消息lease均原free0，6输入事件均原接收。

已目视两步PNG：下30后ap93-step-01-key-030.png，physical43ae96100，SHA7766cd63f5c0d8639587f63c4fe6ddfc9b1ea50097b824dc7a85da8bdb3d1b43，标题Langue（法语）；上3后ap93-step-02-key-003.png，physical43feb5100，SHA2485079bdfe8c91590235540c1929a813f03a96b17cae33b32d53539e77e708e，回到言語。两个独立QMP均同原native lease snapshot，输入像素反馈已证。第三确定1ac原open_screen scr0099_0001→scr7248_0001，新页绘制失败，2s单步PNG未到；未发后续默认确认/MENU。

新失败：Heap2 object7f50691c00，native malloc src4109364c0 bytes780 align40（L37065），dst410936c80 bytes7400 align40（L37071）；FillRect216缓存32x29/stride32 result5 reason4，v18仅nativeOpen403目标门拒绝；BitBlit217 src29x29→dst116x116/flags0复制放大，legacy_plan同尺寸门reason2。同型第二组41093e0c0/41093e880。证据ap93-offscreen-subblock-runtime-evidence.json；不把Heap2父池升为任意可写，不开放未知缩放flags。

Lead msg_6732ee79a03e已派audits/offscreen-subblock，明确期间待命。下轮脚本改UP3→PNG（预期English标题）→ENTER1ac，再逐页实际观察/默认确认<=12、待机MENU/nav；当前guest/host plan固定DOWN_UP_ENTER，需新版本改UP_ENTER，RMcorev2不变。没有worker_done。

STATE=AP93_EMPTY_SLOTS_AND_LANGUAGE_INPUT_PIXEL_FEEDBACK_PROVEN_WAIT_OFFSCREEN_SUBBLOCK_AUDIT，current_run=null，currentcandidate ap93-r5-current-frame-export，last_run19bbfb81，lastfull300s=ap93r2empty77c94f2c。报告ap93-empty-slots-first-setup.md完整同步r1-r5/22有效链接/语言选择预期更正/未验收项，source ledger pin新helper和host代码。无QEMU，heartbeat14269，stopfile .heartbeat-stop-ctx_ee4f6943c8d7-ap93，约19:01UTC期限。
