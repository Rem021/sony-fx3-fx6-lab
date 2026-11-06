# Sony FX3 与 ZV E1 官方编码能力和安全替代方案

核查日期：2026-10-24（America/Los_Angeles；抓取时 UTC 已为 2026-10-25）。本笔记仅依据官方公开网页；未连接相机、未更新、未录制样片、未下载固件本体。用户已告知FX3固件为“最新”，因此可以7.02对应官方帮助指南作为研究基线，但未读回机身版本号。

## FX3 能否获得 1080p30 H265

### Takeaway

**FX3 已有原生 1920×1080 HEVC/H.265 编码，但开放在 XAVC HS HD 代理录制中；没有独立的 HD HEVC 主录菜单。** 不能简单回答“做不到”，也不能把代理录制说成已解锁独立主片。所谓 30p 通常指 29.97p，用户若要求数学意义上的 30.000fps，必须另外确认。

### Cited Findings

- 原版 ILME-FX3 的旧版帮助指南（2035，面向 Ver.2 前）已列出 XAVC HS HD 代理：1920×1080、16Mbps 或 9Mbps、4:2:0 10bit、HEVC/H.265，最高 60p/50p。故这不是 FX3A 独占，也不能说必须升级到最新固件才能有。旧版菜单名称是 Shooting → Image Quality → Proxy Settings。[原 FX3 旧帮助指南](https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000282137.html)
- 原版 FX3 Ver.2+ 帮助指南（2210）继续列相同代理编码，最高帧率精确写作 59.94p/50p。新版菜单：MENU → Shooting → Image Quality/Rec → Proxy Settings；Proxy Recording=On，Proxy File Format=XAVC HS HD，Proxy Rec. Settings=16M 4:2:0 10bit 或9M。[FX3 Ver.2+ 代理设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)
- 主录文件格式仅列 XAVC HS 4K、XAVC S 4K、XAVC S HD、XAVC S-I 4K、XAVC S-I HD，以及 Ver.3+ 的 XAVC S-I DCI 4K，没有独立 XAVC HS HD。[主录格式](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868279.html)
- XAVC S/S-I HD 使用 AVC/H.264；XAVC HS 4K 使用 HEVC/H.265。日本官方原 FX3 规格另明确代理音频为 AAC-LC 128kbps、2ch。[原 FX3 官方规格](https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html)
- 一个易误解点：FX3 的 **XAVC HS 4K 主录没有29.97p/25p**，表格列59.94/50、23.98（NTSC）、119.88/100；XAVC S HD/4K 和 S-I HD/4K 则有29.97/25。XAVC S HD 29.97p/25p 可选50Mbps 4:2:2 10bit、50Mbps 4:2:0 8bit、16Mbps 4:2:0 8bit。[FX3 录制设置完整表](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html)

### Inferences

- 为目标1080p约30fps HEVC，最合理的零刷机试验是主录选 XAVC S HD 29.97p（NTSC），同时开 XAVC HS HD 16M代理。优先用50M 4:2:2 10bit主录，避免把8bit主录和10bit代理的实际信号关系当作已知。主录也可用4K AVC29.97p，但用户不需要4K时会增加空间。
- 代理无独立帧率设置；通常应随主录帧率。因此29.97主录→29.97代理是预期行为，**本次尚未实拍验证**。不要拿59.94主录假定自动生成29.97代理，也不要拿PAL25p冒充30p；50/59.94代理不应视作已自动降帧。
- 已有1080 HEVC代理，说明这台相机有一条实际工作的HD HEVC编码管线；它不证明能安全改成独立主录、不证明4:2:2或任意码率可用、更不证明只改菜单就能完整工作。

### Gaps

- 官方代理页面只写“最高帧率”，没有逐一列出各主录→代理帧率映射。需用户机身拍10–20秒正常视频，读取代理的codec_name、width/height、r_frame_rate、avg_frame_rate、pix_fmt、bit_rate，并检查声画同步，才可确认本机结果。
- 用户自述机身已是最新固件，但尚未读回明确版本号；地区、NTSC/PAL状态，以及30p是否要求30.000也未知。这些不影响离线研究，但会影响具体设置和最终验收。

## 代理能否单独使用以及代价

### Takeaway

代理是实际的小型视频文件，可拷贝到电脑后用兼容HEVC的软件验证；其定位是代理/传输文件。它没有独立录制开关，录制时仍需生成主片，因此不能直接节省拍摄时的总写卡空间。

### Cited Findings

- 官方把代理用途描述为手机传输、网站上传；相机内不能回放代理，播放界面显示的是主片。相机内删除/保护带代理的片段会同时处理主片和代理，不可只删除/保护主片。[FX3 代理设置与限制](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)
- 正常视频录制在119.88p/100p不能录代理；S&Q在录制帧率119.88p/100p或采集帧率120fps/100fps时不能录代理。不是“全部S&Q不能录”，也不应把4K120当作产生30p代理的方式。[同页](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)
- 官方说明可将卡内视频拷到电脑；目录为SD卡 `PRIVATE/M4ROOT/SUB`、CFexpress Type A卡 `M4ROOT/SUB`，其中SUB即代理、CLIP为主片。官方提醒不要在电脑上直接操作或删除相机卡内视频，以免破坏数据库或文件。[导入电脑](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868300.html)
- 代理视频是4:2:0 10bit、9或16Mbps；代理音频是AAC-LC 128kbps双声道。不能据此许诺主片的4:2:2采样、PCM多声道音频等同保留。[原 FX3 规格](https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html)

### Inferences

- 如果用户要的是便于传输/交付的1080 HEVC文件，官方代理可能已经满足；如果要“只录一个高质量1080p30 H265主片、不同时生成主片、任意码率、4:2:2或完整多声道”，代理不能等同达成目标。
- 计算值（视频本身、十进制GB、未计音频/封装）：16Mbps约7.2GB/小时，9Mbps约4.05GB/小时。16Mbps相对9Mbps有更多压缩余量，但不能仅凭码率保证复杂运动、暗部噪声、树叶、水面或强调色的可接受程度；需拍摄用户真实场景对比。
- 实际录制总空间是主片+代理：如50M主片+16M代理，视频总量约29.7GB/小时。独立导出的代理虽小，开代理会增加当次写卡数据。不要自动删除原片；应先复制完整素材，再在电脑副本上验证。
- 最稳妥的成片方案仍可用官方1080p29.97 AVC主录，再在电脑输出HEVC；精确30.000或自定义码率可由后期转码控制，但这是后期制作而非机内新增模式。若只是要30.000容器，必须决定如何处理29.97→30的时长/帧处理，不默认简单改标签。

### Gaps

- 本次未测试用户现有软件是否能解码该HEVC10bit代理、是否满足画质/音频/长录需求；未证实代理相对主片的色彩、LUT、元数据和音轨选择细节。应保留为验收项目。
- 没有可靠官方资料明确所有版本的代理文件命名规则，因此不写固定文件名；以SUB目录和实际编码检查识别。

## 当前官方固件和升级边界

### Takeaway

截至核查日公开下载页显示 FX3 7.02（2026-03-17）、ZV-E1 2.02（2025-11-11）。用户未授权实际升级，本研究也未执行；旧版已有HEVC代理，不能为了这个目标先盲目升级。

### Cited Findings

- FX3当前官方固件7.02，2026-03-17，文件BODYDATA.DAT，811,876,768字节；7.02改善整体稳定性。当前版及历史更新内容未宣布新增独立HD HEVC主录。[美国官方更新详情](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)
- 从2.02或更旧版需先经2.04/2.05再升7.02；不得跳过中间版。升级用slot1，建议满电NP-FZ100，至少51%；更新时移除电池可能导致无法使用。以上为官方升级条件，不构成对第三方刷机的安全保证。[同页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)
- 1.01及更旧升级至现代版涉及设置初始化，旧保存设置不能再读取；S-Log2和NFC等功能也有变化。研究固件时不能视升级为完全可逆、零行为变化的步骤。[官方中间版本/升级说明](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00280265)
- ZV-E1官方列表显示2.02，2025-11-11；更新详情文件BODYDATA.DAT，1,060,230,584字节。[下载列表](https://www.sony.com/electronics/support/e-mount-body-zv-e-series/zv-e1/downloads)、[更新详情](https://www.sony.com/electronics/support/software/00296227)

### Inferences

- 不要把“下载到原厂固件”当作有可验证的回滚恢复路径；更新包不是整机包含校准/个体配置的完整备份。
- 文件同名BODYDATA.DAT不代表格式、目标硬件或型号可互换。官方FX3更新页的Applicable Model只列ILME-FX3；应按机型核对，不把FX3A自动混入。

### Gaps

- 本次未在官方FX3/ZV-E1当前升级说明找到面向用户的完整降级/救砖流程。旧型号社区的“不能降级”回复不能自动视作本机精确硬件机制；准确结论是**没有确认可用的回滚路径，不能承诺安全回退**。
- 可查询用户机身版本的官方菜单为MENU → Setup → Setup Option → Version → Body；用户自述“最新”，当前明确版本号未读回。

## ZV E1 与 FX3 是否同一硬件因而可直接刷系统

### Takeaway

官方规格支持两者是同类全画幅Exmor R/BIONZ XR平台相机，但“同一底”不等于整机同硬件、同固件目标。官方资料未公开足以确认具体同一传感器die及固件二进制兼容的信息。

### Cited Findings

- 原FX3采用35.6×23.8mm Exmor R CMOS，约12.1MP照片有效像素；ZV-E1官方同样列35.6×23.8mm Exmor R、照片12.1MP、视频10.1MP。分辨率接近只是规格事实，不是芯片料号相同的证明。[FX3官方规格](https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html)、[ZV-E1官方规格](https://www.sony.com/electronics/support/e-mount-body-zv-e-series/zv-e1/specifications)
- FX3主动散热、风扇和双CFexpress Type A/SD插槽在官方资料中有明确说明；原FX3日本规格列两槽，原FX3产品特点描述散热。[原FX3产品特点](https://www.sony.jp/pro-cam/products/ILME-FX3/feature_3.html)、[原FX3规格](https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html)。ZV-E1官方列单SD UHS-I/II槽、RAW输出为“-”，HDMI为Type-D；FX3提供HDMI RAW输出。[ZV-E1规格](https://www.sony.com/electronics/support/e-mount-body-zv-e-series/zv-e1/specifications)
- ZV-E1具AI识别主体（人物/动物/鸟/昆虫/汽车/火车/飞机）等专有功能，官方定位和外围硬件/控制也不同。[ZV-E1规格](https://www.sony.com/electronics/support/e-mount-body-zv-e-series/zv-e1/specifications)
- ZV-E1在官方High自动关机温度条件下，25°C、XAVC S 4K60p150M测试条件连续约30分钟；40°C约20分钟，条件包括关Wi-Fi及打开屏幕，不能泛化为所有拍摄情况。[ZV-E1热条件](https://helpguide.sony.net/ilc/2310/v1/en/contents/0601L_auto_power_off_temperature.html)
- ZV-E1本身也支持1080 HEVC10bit9/16Mbps代理，不需靠移植FX3获得这条编码管线。[ZV-E1代理设置](https://helpguide.sony.net/ilc/2310/v1/en/contents/0412M_proxy_rec.html)
- ZV-E1官方提供4K120p升级授权入口（下载列表标2023-06-28）。存在官方功能扩展不意味着FX3整套系统可以通刷。[官方支持下载列表](https://www.sony.com/electronics/support/e-mount-body-zv-e-series/zv-e1/downloads)

### Inferences

- 两机的存储控制、按钮/显示、散热与外围不同，直接跨刷需要解决硬件适配、机型识别、个体校准、引导/签名及恢复路径等问题；仅同传感器或同BIONZ品牌不能排除这些障碍。具体签名算法/安全启动实现应由另一研究方向确认，不能从官网规格推断。
- 刷入FX3固件不会物理增加风扇、CFexpress插槽和完整HDMI口；即使能移植部分UI/功能，仍需分别验证驱动、热保护、录制可靠性。单改热保护阈值不能等同安全提升连续工作能力。

### Gaps

- 本方向没有查得官方允许ZV-E1刷FX3系统或支持跨刷的路径；第三方是否成功需查原始代码/版本/机型证据，不能由规格表得出“绝对不能”或“保证能”。
- 未找到官方明确ZV-E1“无风扇”的文字页面，本笔记因此不以该点作独立已证事实；可由拆机原始证据补充，但目前热限制已经有官方可复核资料。
