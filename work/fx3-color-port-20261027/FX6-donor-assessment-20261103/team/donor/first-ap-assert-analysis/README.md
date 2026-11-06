# FX6 AP 首断言：发送失败，等待回复尚未开始

本阶段只做固定输入的原字节反汇编和既有串口对照，没有启动 QEMU、改 helper 或生成可运行补丁。`python3 analyze.py` 重算输入 SHA、ELF `PT_LOAD` VA→文件偏移、指令机器字、串口行范围与旧 FX3 参照顺序，输出 `receipt.json` 和九份小段反汇编；当前 `PASS_STATIC`。此处的“发送失败”是 **AP 原指令对 `osal_snd_msg` 返回非零的检测**，非零的确切整数尚无运行态读回。

## 固定证据与第一故障

| 输入 | SHA256 |
|---|---|
| FX6 6.01 原 `appFw.so` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| FX3 7.02 原 `appFw.so` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| 本次客体 CAPID `/simulation/fx3-capid-v1.so` 与本地同 SHA 二进制 | `cd51ea7b3347ccb8bd8d0cdd72b096936f0a226c142575f41a24cc018948156e` |
| 三入口 CPIO | `bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02` |
| 唯一三入口运行串口 | `7fd297d60c72a1211fa44a0103ae69fabec0c72c422be6c34519c2636db3a43f` |
| 旧 FX3 参照串口（仅引用，未重跑） | `c493986a68c7dc4d8f05e24167c9eee3808e99a2087a01d92f370921b7306d8e` |

`receipt.json` 还固定了本地 CAPID C 源 `8d65d690…`、音频格式源 `5192b2dc…` 和 `capid-service.c` `45b787c1…` 的完整 SHA。C 源与二进制的可重建同一性**未证明**；下述关键分支同时取自实际 `.so` 指令，而非只凭源码。

FX6 AP 首个 `PT_LOAD` 为 `p_offset=p_vaddr=0`，下列 AP VA 等于原文件偏移；CAPID 的代码段是 `p_offset=0x5164, p_vaddr=0x15164`，故 CAPID 指令文件偏移为所示 VA 减 `0x10000`。`receipt.json` 给出各点完整段映射与原机器字：

| 原指令 VA（文件偏移） | 小端机器字 | 原码意义 |
|---|---|---|
| FX6 `0x20f15b0`（同 VA） | `a1658052` | 造请求 command `0x32d`；`0x20f15a0` 设 `0x200d`，后续造 10B。 |
| FX6 `0x20f15f4..0x20f1608` | `w0=0x92840747, w2=10, w4=12`；末指令 `fff7ff97` | 调 `0x20ef604`，输入10B、预期输出缓冲12B。 |
| FX6 `0x20ef79c`（同 VA） | `61aaa897` | `bl osal_snd_msg@plt`。 |
| FX6 `0x20ef7a0`（同 VA） | `e0000034` | `cbz w0,0x20ef7bc`：只有发送返回0才跳过断言。 |
| FX6 `0x20ef7b4/0x20ef7b8` | `61868052` / `f3df0194` | `w1=1075`，调用断言报告；与串口 `infra_wrapper_bb_procam_chaplin_base.cpp:1075` 对上。 |
| FX6 `0x20ef7c8`（同 VA） | `bea9a897` | `bl osal_rcv_msg_tmo@plt`，在成功发送分支之后；这次断言发生在它之前。 |
| FX3 `0x2de7260/0x2de7264`（同 VA） | `2caf9e97` / `80040034` | 同一语义的原发送和零返回分支。 |

串口原字节 `1970240..1970482` 记录 TID716 动态 QID `0x81cf6196` 可取得；`1971713..1971849` 记录同线程 `destination=0x92840747 source=0x81cf6196 bytes=10 raw=0d202d030a0001800000`；紧接 `1971849..1971906` 是断言。这里日志邻接与 AP 分支相互校验：确认的是 **发送非零**，不是 `recv` 超时、缺应答或回复字段错误。请求日志在 CAPID 拦截的观察点输出，`dispatch_pending=1` 不代表已经发到目标队列。源码 `osal_snd_msg` 的观察日志位于模型分派前；其后是否进入哪个分支须另行证明。

## 实际 CAPID 二进制与 FX3 参照

三入口 `/init` 原文字节 SHA、环境值写入回执：`FX3_CAPID_STORAGE=reserved-v1`、`FX3_HDMI_AUDIO=inactive-format-v1`、`FX3_VDF_OBSERVE=1`。客体 CAPID 二进制在 VA `0x183a4`（file `0x83a4`）取 `FX3_HDMI_AUDIO`，核对 `inactive-format-v1`、目标和消息头；`0x18400` 比较 `0x032d200d`，`0x1840c`（file `0x840c`, `c9180094`）调用 `audio_dispatch`，`0x18410` 保存返回值，`0x1986c` 返回给 AP。`audio_dispatch` VA `0x1e754`（file `0xe754`, `807f8012`）先置 `w0=-1021`；`0x1e764`（file `0xe764`, `08c14bb9`）读模型的 `initialized` 字段 VA `0x45bc0`，`0x1e768` 为零则直接到返回。该字段位于 `model` BSS VA `0x45ba8` + `0x18`，唯一已定位的置1代码为 `cap_control(0x1003)` VA `0x245d0`（file `0x145d0`, `091900b9`）。FX6 本轮完整串口没有 `FX3_CAPID_BIND`、`FX3_CAPID_COMMIT`、`FX3_HDMI_AUDIO_COMMIT` 或发往 `0x92840747` 的原生发送回执；但未直接采样 `0x45bc0` 和发送返回寄存器。固定 `/init` 的赋值不等于直接读过故障进程的 `getenv`。

10B 实值逐字符合实际 CAPID 二进制 `fx3_audio_format_apply` VA `0x15164..0x15220` 的十个字节检查：`0d 20 2d 03 0a 00 01 80 00 00`，其 `p[8]=0` 合法；`source=0x81cf6196` 也满足 helper `local()` 的高4位8与非零低28位条件。若模型初始化、owner、消息分配及返回发送全部满足，helper 原只读常量 VA/file `0xcf8` 给出 12B 回复 `0d202d130c00018000005800`（`0x132d`、状态 `0x580000`）；这是**预期合同**，本次没有实际回复。

旧 FX3 固定参照串口先后出现 `CAPID_BIND`、`0x1000 GetTblAddr`、`0x1001 StartAccess`、表头写入、`0x1002 StopAccess`、`0x1003 InitEnd initialized=1`（行 16208），然后同样原请求 `0d202d030a0001800000` 和 `HDMI_AUDIO_COMMIT completion=0x132d format=0`（行 16572）。此参照证明 FX3 软件模型曾处理该布局，**不证明** FX6 的自然初始化顺序或物理 HDMI 输出；原日志明确 `active_output=0 audio_frames=0 CP_executed=0`。

## 故障归因边界与下一最小实验

| 假设 | 本轮判定 |
|---|---|
| FX6 10B 请求布局与 FX3 helper 不合 | 对这条请求已排除：实际二进制逐字校验接受；但尚未进入该校验的运行态分支。 |
| reply 超时/字段错 | 对本次断言已排除：AP 在发送非零时即断言，未调用 `osal_rcv_msg_tmo`。 |
| 本地源 QID 无效 | 已有动态 QID 可取得，且 `local()` 位掩码通过；不等于目标服务必在。 |
| FX3 CAPID 模型尚未初始化 | 最强且可检验的解释：FX6 本轮无绑定/初始化回执，而 FX3 参照在音频前完成 `0x1003`。若原 helper 的 audio 分支确已进入且该字段为0，原机器码立即返回 `-1021`；**本轮只实测非零，不能把 -1021 填成实测值**。 |
| 目标队列不存在 / helper 环境丢失 / owner 或 allocation 拒绝 | 尚无实际返回寄存器与分支读回，保留为备选；当前不以日志缺少原生发送回执证明队列不存在。 |

下一次由既有 runtime owner 执行**一次只读观测**，继续用冻结三入口与平台，先记录故障进程中 CAPID `osal_snd_msg` VA `0x183a4..0x18414` 的分支选择、`audio_dispatch` 入口的 `model+0x18`/owner、返回 `w0`，以及 AP `0x20ef7a0` 的 `w0`；如现有只读设施不能取得这四项，先停在静态结论，不改变 helper 门、`/init`、QEMU 配置或伪造回复。观察后的第一件**软件侧适配**才是核对 FX6 原 AP 的 CAPID 初始化调用和表布局，判断能否在其自身启动次序中先完成与 FX3 本地驱动合同一致的 GetTblAddr→StartAccess→表设置→StopAccess→InitEnd，再执行 `0x32d`。不得直接手填 `initialized=1`、全返回0或注入 `0x132d`；若 FX6 表合同不同，应在 FX6 上层做字段级转换并另行验证，而不是改固定 FX3 平台。

当前交付是原字节静态定位与旧运行回执对照；FX6 AP 菜单、HDMI、CP、色彩链和整机启动均未通过。
