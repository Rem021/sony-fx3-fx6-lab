# A7C2 最新公开研究核查（2026-11-01 本地 / 11-02 UTC）

GitHub API 当次查询的 main HEAD 为 `b3d7c1fed349f1d918acc4259f1d2b3a7c52a500`，提交时间2026-10-31 18:58 UTC；最近两项为发布快门门控源码/验证和camera scope观测更新。它与本任务已固定上游版本相同，没有查到比该HEAD更新的公开main。没有clone、git操作、运行A7C2 VM或改FX3合同。

## 与当前FX3阻断直接有关的结果

|一手来源|核查结果|FX3应用边界|
|---|---|---|
|[timecode原生回执](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/report/vdf-timecode-native-proof.json)|原waiter消费free0后，下一等待同样是92840747/0165|与AP78b推进顺序独立吻合；A7C2地址/TID/queue不可搬用|
|[panel原生回执](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/report/vdf-panel-native-proof.json)|同一请求hex `0d2065010a0001800200`，回复`0d2065110c00018000005900`，请求及原waiter释放0；pixels_switched=false|提供候选状态域590000线索；须核FX3 CP转换/状态映射，不能直接回裸0或宣称显示|
|[vdf-device.c](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/device-models/vdf-device.c)|95..166为selector2/size0..2有限模型；单活跃请求、8租约、失败回滚；回复status带590000域，保留硬件pending|FX3需遵循本轮精确请求、自己的shadow/生命周期合同；目前未集成|
|[common boot join](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/report/common-boot-join.md)|四成员经原worker返回后投递内部句柄；全部join后才完成UI的boot future|机制与FX3原审计吻合；禁止合成token、移植VA或把三个完成凑成四个|
|[背景阻断研究](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/report/boot-cp-background-blocker.md)|初始boot future之后仍可能有背景服务/成像接口等待|即使notify/UI恢复，也需分开验收后续boot、首绘与相机功能|

## 最新进展的适用范围

[10月31维护者进度](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/2026-10-31-current-progress.md)记录原菜单和640×480 OSD已有运行证据；原固件照片/录像整链及物理ASIC仍未验证。冻结研究批次、公开包软件模型测试、原生run和独立像素/媒体读回各有单独范围，不用测试数量给FX3补证。

[启动文档](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/README.md)可用来逐层比对资产、模块顺序、原程序、软件profile与生命周期；本机Mac/FX3按自己的锁、原件与既有内核布局保留，不能整包照搬Linux/A7C2的机器参数。额外检索了QAQLeonard的FL23研究仓库，其桌面/实机功能方向不同，未把它当作FX3 VM启动合同来源。

## 本轮落点

AP78b `ap78bboot-537976cc` 已观察timecode规范36B消费free0；随后捕获上述相同0165完整raw和FX3栈并escalation。Lead已派`audits/boot-vdf-tail`核对到屏障/notify全部路径，本worker不自行追加0165回复。建议其优先复核590000域、selector/size shadow、原回包所有权，再按原流程推进，而不是用A7C2历史菜单成功代替FX3首绘验收。

[在线读取来源与SHA回执](online-source-check.json)保存当次固定HEAD、各文件URL/内容SHA；raw域一次SSL EOF后改用GitHub内容API并成功重读。没有保存第三方源码副本或外部运行输入。

## AP79 getpin 后续参考

公开的 [pin-registry-core.h](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/device-models/pin-registry-core.h) 已有每个owner的source/count/完整key策略、8个reply lease及Get退租状态；[Get精确key退租测试](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/test_pin_registry_key_retirement.py)列出12种成功/负例，包括低字节别名、错误目的、失败free、外国线程、发送失败和错误registry。它有可借鉴的生命周期结构，不能只摘出一段成功reply字节。

[HDMI pin adapter](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/device-models/hdmi-pin-device.c)只为其自己的两类key接入共享核心，并让2500配置消息继续交原配置owner；[VEF header](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/device-models/vef-device.h)声明的owner SID为905a0048，容量21。它们不是FX3当前9284074a实例身份的证据，也不能把这些对象数、虚拟ID、历史state直接移植。

FX3 AP79本轮已原生消费0165和HDMI八条新回复、325，四任务各自然完成，但父线程在change_mode首个9284074a/48B getpin等待，屏障未入。下一步仍需本轮真实endpoint与producer/consumer/buffer合同，由Lead静态审计闭合；本次补充只读，没有集成pin registry或回复。

## AP80b2 实测enum2后的在线复核

再次读取同一固定HEAD的[vdf-device.c第165..220行](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/device-models/vdf-device.c#L165-L220)：它已有0119的h/v布尔、osd0、其余零子集，记录虚拟panel控制消费后回1119/status0；marker明确hardware_driver_executed=0、pixels_flipped=0。这不证明FX3所有plane或输入坐标已翻转，不能代替本机实际enum2的软件显示/输入合同。FX3本轮实际包h1/v1/osd0，已冻结并escalation；未启用enum0候选，未借上游成功回包越过未闭合工作。GitHub目录读取失败，搜索结果无相关证据；不据此声称全仓库没有其他实现。
