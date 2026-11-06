# AP94 恢复点（2026-11-02）

唯一运行链 worker：6cbe29fd-fb24-4199-bba8-b8ad99383477；task_bf4f4211be76 / ctx_ee4f6943c8d7。合同 msg_fd22adc6ac57；基线 AP93-r5，原 AP93 文件/运行记录保持。

- 完整读取 offscreen-subblock README 185行。审计脚本隔离运行并截获最终 write_text（不落盘）；重算 JSON SHA 精确等于 `331cd0acab44d79634d297d7662cf0f46af0304add1f4071c2ee31455febb4a6`，12项人工模型向量重放通过。
- 新 GPE v19 / backend v4 / resource v4 child：原 malloc103550 成功返回记录 parent对象/epoch、logical、phys、requested bytes/align、child epoch；free10364c入口撤销，close/重开/父身份失效撤销全部 child。离屏目标每行同时匹配唯一父和活跃子区间；保留原545/native403路径与 frame_target 契约。
- 原 native free 先在生命周期锁内撤销 child，再解锁调用原 free 一次，防止外部锁等待原函数而潜在自锁；errno/结果原样返回。宿主验证 free 等待正在绘制的生命周期租约结束，且 native free 入口已不持该锁。
- flags0/selector0/K255/fmt0/rotation0、所有coordinate/adjust/float=0、完整clip、等比整数4倍专支：nearest_v1 原16bit替换，approx_blend=0。不改原参数 selector/P73，原完成顺序保留。
- compaction入口150b9c/103a40/103760/103804/1039a8/efd0c/efde8，16B字节核验，原入口探针保存GPR（ABI scratch x16除外）、32 SIMD、NZCV/FPCR/FPSR/SP/LR，仅原子事件计数与日志，不取生命周期锁/不阻断。七项隔离Unicorn重放通过；不等于真实compaction通过。
- bitmap命令绑定/引用锁、排队ABA、compaction保护仍未覆盖，明确marker；地址复用的新child epoch只能观测，未绑定原FIFO参数，不虚称旧排队命令被拦截。
- ASan/UBSan：两组完整13456像素覆写（含alpha0非零RGB）、各2784B目标padding和源/邻块不变；十项实际子块准入、九项零写拒绝、旧545/native403/OSD frame target/完成/FIFO/生命周期回归。旧73条参数输出与独立FNV参考完全一致。
- RM core v2不改；provider v4仅更换输入plan。host/guest顺序 UP3→ENTER1ac→最多12次逐页ENTER默认→MENU1ab→DOWN30/DOWN30/RIGHT1af/ENTER1ac，总上限19。先自动UP，之后每步需实际PNG复核+`ap94-next-key.json`，≥4s间隔。C plan sanitizer与host plan验证通过。
- 候选 `ap94-child-stretch/candidate.json`：仅替换既有CPIO两成员的body（GPE、RM provider）；init不变，FDT仅initrd-end。build-receipt记录所有新helper哈希。
- 当前 run `runs/ap94child-ad25d7a1`，driver `run_candidate94.py`，300秒/4A35/MTTCG，工具会话60784。运行未结束时勿并行取锁/改STATE。查看STATE/回执确认最后状态。

后续逐页截图：driver输出 `ap94-step-readbacks.json`，PNG文件名仍兼容 `ap93-step-NN-key-xxx.png`。每次实际查看PNG后写本run `ap94-next-key.json`，含step、key、observed_page、authorization=msg_fd22adc6ac57。新不支持绘制/致命路径立即证据封存+escalation，不盲加按键。

## 第一轮结论 / 诊断续轮
第一轮 ap94child-ad25d7a1 在39.837481s因seq86 GPE_STALE停止；qemu_exit0/reaped/PIDabsent/inputsunchanged/双锁FREE/missing[]，im228完整maps36.65。UP仅down/up两事件，无UP后PNG、无ENTER。目标native403已登记且未更换，新增source child门仅offscreen_child时执行，因此不是Lead最初猜测的源child缺失。相同原144B宿主v18/v19都通过（无sourcechild）。原始失败行src_fmt=0i被串口交织，统计器列入incomplete；不能将complete96条全0解释为无失败。已发送escalation msg_298bb40cb2f0/msg_9b47306a5806。
Lead msg_49124d89bac2授权被动stage/errno/父字段/proc诊断重跑，不改判定。新v19r2-diag + screen-v2-diag，backend/resource/输入/OSD不变；ASan/UBSan通过。候选ap94-r2-guard-diagnostics，同一run_candidate94.py，300s。

第二轮 ap94r2diag-4f9de767实际123.881124s，所有健康/锁/原件/missing/im存活检查通过；seq86不复现，新增stage未观测到screenfail。step1 Language，2隐私，3手机引导，4 Bluetooth On中提示，各独立QMP SHA匹配且已打开PNG复核。seq217/219原4×覆写成功。新seq402/406 49×49→103×116 planner拒绝，已停并escalation msg_1976199ed23b。
Lead msg_c030a5a3da12授权nearest_v2像素中心任意正尺寸，保留所有其他门；GPE19r3/backend5宿主新6组全像素与旧73FNV通过。候选ap94-r3-nearest-v2，第三轮已用同一driver300s启动（工具2397），按STATE找currentrun；逐页真实查看PNG再发同合同手动命令。

第三轮 ap94r3center-f3bba0ba实际39.930069s，首次UP后seq93 screen_recheck GPE_STALE；proc code3普通id2行38419B读中重复（所有其他code3条件宿主重放均通过，条件排除推断重复；未保存全proc），父字段正常。健康/双锁/im37.44通过，missing nearest_v2 因功能未到达。已escalation msg_aa8ad0f1f046。
Lead msg_4f0238f1bb4d明确对象112B+epoch/state/close-release权威、proc辅助且有界重读一次fallback，OSD共享，去除快照竞争读。GPE19r4-parent-source/resource5/screen3实现并通过ASan/UBSan，source仅parent策略按7e5澄清落实。最终候选ap94-r4-object-source-policy；中间ap94-r4-object-authority未运行。第四轮同driver300s工具会话86571，按STATE找run；不要并行取锁。

第四轮 ap94r4object-37305ab2自然完成300s（实际302.103312；STOP请求晚于窗口，early_stop_reason=null，不误称早停）。所有健康/锁/inputs/missing[]/im228 maps294.84通过。完整GPE328全0+20交织不完整；nearest_v2 49→103x116成功，无proc失败/authorityreject/compaction事件。六步PNG实际查看：Language、隐私、手机引导、BluetoothOn、QR（ENTER不推进）、MENU返回手机引导；15 leases原free0一次。review_ap94.py在provider136B坏hex失败，新增review_ap94_v2.py改以完整原接收者owned副本匹配，不修包；已复核成功。STATE/报告/来源账本已同步。
Lead新合同msg_8162589b2b22：AP95宿主逐步planv2，白名单UP3/DOWN30/LEFT15/RIGHT1af/ENTER1ac/MENU1ab，删除待审计（Lead已派key-delete-c4），最多30步，软件41df控制页step/key/hold_ms，每步PNG实际查看后自主选择下一键。实现和宿主测试可先做，审计到位后才运行AP95。原生手机引导页底部删除图标Set oncamera；我只读旧ELF名称/表静态补充找到TACT_DELETE UI23→Infra1f8，R/ap94-delete-key-static-supplement.json，未注入，独立审计仍等Lead。当前无QEMU/双锁空，AP95尚未构建/运行。
