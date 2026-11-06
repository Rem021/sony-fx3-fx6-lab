# FX3 卡槽状态与挂载警告审计

**最确定的修正是：AP91 的键已进入应用原转发回调，不能把无画面变化归因为 `EventThread` 未分派或 `inh` 抑制。** 十二包在应用侧均为 `from_type=1, inh=0`。卡槽应在原 FRONT/RM 检测边界诚实报告“槽存在、没有介质”，但本次尚未闭合完整封套、运行中挂载返回值及警告 `0x213` 的全部退出条件，**没有可直接集成的无卡报文合同**。详见下文 A/B/U 分级及未证实清单。

## 交付与复现

- [audit_media_slot.py](audit_media_slot.py)：只读重建，唯一生成文件为同目录 proof。
- [media-slot-proof.json](media-slot-proof.json)：五份原库 SHA、36 组原反汇编、19 条关键指令断言、原表、AP90/AP91 串口行及 AP91 六次读回哈希。
- 本 README 是本审计入口；仅写本目录，没有修改公共计划、runtime、原件或 Git，没有启动 QEMU 或取得运行锁。

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python \
  work/fx3-vm-20261101/lead-claude/audits/media-slot-dialog/audit_media_slot.py
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python \
  work/fx3-vm-20261101/lead-claude/audits/media-slot-dialog/audit_media_slot.py --check
```

脚本核对卷 UUID，固定五份原库哈希，重读原指令和封存运行证据；`--check` 不写文件，逐字节比较重建 proof。退出 0 表示静态证据可复现，不表示无卡后端、对话框退出或 VM 菜单已验收。

### 简称与等级

| 简称 | 原件/证据，路径详见 proof.sources |
|---|---|
| A | `original-uipc/ap-projection/regular-files/usr/lib/appFw.so`，SHA `545c5053…` |
| O | 同目录 `libObj.so`，SHA `c4681d20…` |
| D | `libInfraMediaDetect.so`，SHA `4c1dbb30…` |
| M | `libInfraMediaMount.so`，SHA `33b4c61c…` |
| C | `libInfraMediaCommon.so`，SHA `1ddec7e4…` |
| L90 | `runtime/runs/ap90r2parent-f5c66d0b/serial.log` |
| L91 | `runtime/runs/ap91r2keys-9d3939d7/serial.log` |

地址均为原 ELF VA/库内偏移，运行时须加该次真实装载基址。**A-static** 是原指令/表直接证据；**A-runtime** 是封存运行直接观测；**B** 是明确条件下的推导；**U** 是未证实。原字符串命名不单独证明实际执行。

## 1. 已闭合的卡槽检测与挂载分层

原链可分为以下几段；虚线跨越本次尚未绑定的环节：

```text
物理卡检测 / CP FRONT 发送者（GPIO、极性、SD 控制器归属未闭合）
  ... FRONT RMDATA 原消息
  → D CallbackPointFromFront → ParseInternalMessage
  → D 的 RM1/RM2/RM3 enable / hold / port_state / RemoveCnt 缓存
  → D Update / GetInOutStatus / NotifyInOutEvent
  ... 应用媒体事件及状态更新
  → M Mount → 本地媒体公共服务 0x80cf016d → mcmn_drv_open / getinfo
  ... 应用媒体错误参数及自动警告谓词
  → Caution 0x213 → dlg_dbl021_base（screen 0x2c7）
```

**A-static：插拔检测不是挂载是否成功的同一个字段。** D `0xe6dc..0xe8f0` 接收原 FRONT 队列回调，封成内部 `0x80000005` 消息；D `0x1091c..0x10d38` 检查 body type 2、最小长度 7，然后分别读写三个检测端口的 enable/hold/port_state/remove counter。M `0x9c98..0x9f74` 另行查询媒体公共服务、打开设备、获取信息，并保留错误返回。proof 的 `media_detect_front_*`、`media_mount` 均含连续原指令。

**A-static：FRONT 状态 body 可证的位语义如下，不是 GPIO 寄存器表。** D `0x109b8..0x109d4` 检查 type/长度，`0x10cb8..0x10d30` 解位并写状态；原日志标签 D `0x128ef/0x12921/0x12953/0x12985/0x129b7/0x129e9/0x12a1b/0x12a4d` 对应 `RM1Enable`、`RM2Enable`、`RM3Enable`、`rm1.hold`、`rm1.port_state`、`rm1.RemoveCnt` 等。不能把逻辑 RM 编号直接当机身卡槽号。

| body 偏移 | 原语义 | 原指令 |
|---:|---|---|
| +0 | 消息 type，接收分支要求 2 | D `0x109b8..0x109c0` |
| +1..+2 | 本次未闭合，须保留原封套/状态含义 | 不提供猜测值 |
| +3 bit0/1/2 | RM1/RM2/RM3 enable | D `0x10cb8..0x10cc0`、`0x10ce4..0x10d08` |
| +4 bit0 | RM1 hold | D `0x10cc4..0x10cd0` |
| +4 bit1 | RM1 port_state | D `0x10ccc/0x10cd4` |
| +4 bits4..7 | RM1 RemoveCnt | D `0x10cd8..0x10ce0` |
| +5 / +6 | RM2 / RM3 同型字段 | D `0x10cf0..0x10d30` |

**A-static：启用检测端口与介质在场需要分别提供。** D `Update@0xfb48..0xfd48` 先检查 `+0x268` 起各 24B 端口记录的 enable，再检查同记录 `+2` 的 port_state；没有满足的在场端口时选 index 3，并维护媒体记录状态 2。由在场转为该状态的通知参数取 0（`0xfca4..0xfccc`）；在场通知取 1（`0xfc38..0xfc68`）。因此可证这条路径中 **NotifyInOutEvent 的 status 0 表示移出/无卡，1 表示插入**；这是媒体通知值，不是 MMC ioctl 错误码。另需防止误读：D `GetInOutStatus@0xf380..0xf484` 首字节从配置候选端口的 `+0x268` enable 生成（`0xf46c..0xf480`），不能单独把该字节当作卡在场值；完整6B输出和实际通知应一起采样。

**A-static：D 发出的原通知和 RM 同步查询不是一类报文。** `NotifyInOutEvent@0xd40c..0xd58c` 构造原头 `u32 0x00081001, u16 1, u16 0x10`，将 media ID 写 +8、status 写 +24（发送 payload 的首字节）、hold 写 +25、removeCount 写 +28，经原 EventWrapper 发送。RM 同步 helper D `0xf1e4..0xf334` 使用队列 **`0x80d9016e`**，24B 头、长度取头 +6、返回状态取 +12；无已注册队列时返回 `0x80000004`。`GetRMConfigInfo@0xfd4c..0xfe04` 使用 command 9、payload `0x70`；`SetOsalIdForMediaNotify@0xfe08..0xfe80` 使用 command 3、payload 4。**这些是 AP RM 层合同，不是已闭合的 CP FRONT wire schema。**

**A-static：原 D 的初始/兜底行为会影响时序。** D `StartInOut@0xf92c..0xfa50` 在当前媒体状态为 2 时可直接通知 status 0；其他初始状态存在发送 status 1 的分支，受请求 +4/+5 和既有通知计数影响（`0xf9f8..0xfa3c`）。D `ThreadInit@0xe8f4..0xecfc` 还有条件等待超时后构造内部更新的路径。不能只在 UI 已弹错误后补一个 GPIO 值，就假定最初的插入/挂载动作从未发生；也不能把未知初值视为“未插卡”。

**A-static：挂载错误的直接执行模块是 M，但 L90 没给出该次具体返回。** M `0x9d80..0x9dc4` 向本地 **`0x80cf016d`** 查询命令 `0x1000`，body `0xcc`；`0x9e40` 检查回复存在/有效字段；`0x9e14` 调原 `mcmn_drv_open`，失败经 `0x9e20..0x9e3c` 转错；成功后 `0x9e9c/0x9ea8` 调 setowner/getinfo。原错误传播和恢复在 `0x9ef8..0x9f44`。C 另有原 RM 初始化 `0x3c7a8..0x3cabc`。本审计没有取得 L90 对应请求的完整回复、设备路径和 native return，**不能宣称具体是 open 失败、无设备、分区失败或文件系统错误**。

## 2. AP90-r2 实际证明到哪里

**A-runtime：模型命令未挂任何卡设备，模块快照也未加载存储卡模块。** 封存 `command.json` 使用 `-nodefaults`，仅两个 loader 设备，没有 drive/blockdev/存储控制器设备参数；L90 **881–884** 的模块清单仅 `osal_uipc/osal_utm/devno`。原厂 `insmod_drv2:39–44` 则包括 `mcmn_drv/nvme-core/nvme/ms_drv/mmc_drv/sata_drv`（精确行号见 proof.original_storage_module_loads），完整 full-v5 投影也确实有这些原件。**这不能证明某个 GPIO 被读为插卡，更不能用标准 SDHCI `PRESENT_STATE` 的位定义填补私有驱动证据。**

**A-runtime + A-static：原应用层确实收到过两个“插入”事件，并完成过挂载/卸载 sequence。** 名称与事件号来自 A `0x4171670..0x41716a8` 和 `0x4172600..0x4172638`；L90 对应原始 28B 消息如下，均由 `appFw+0x2eacd4c` 送到 UI 消息链。

| L90 行 | 原始消息开头 | 原事件名 |
|---:|---|---|
| 10892 | `0200010000000000…` | `0x10002 MODEL_MEDIA_INSERTED_SLOT1` |
| 10908 | `0300010000000000…` | `0x10003 MODEL_MEDIA_INSERTED_SLOT2` |
| 18121 | `f000030000000000…` | `0x300f0 MODEL_MEDIA_UNMOUNTCMP_SLOT1` |
| 18403 | `ee00030000000000…` | `0x300ee MODEL_MEDIA_MOUNTCMP_SLOT1` |
| 18522 | `f100030000000000…` | `0x300f1 MODEL_MEDIA_UNMOUNTCMP_SLOT2` |
| 18821 | `ef00030000000000…` | `0x300ef MODEL_MEDIA_MOUNTCMP_SLOT2` |

以上**完成事件不是成功返回码**：原消息余下字段为零，警告可能是 sequence 完成后的错误呈现。原模型适配段 A `0x2a7a7a4..0x2a7a864` 对 slot0/1 和 initial 标志选择 `0x10000/10002`、`0x10001/10003`，所以仅凭 `0x10002` 也不能反推 CP 原始 pin/寄存器值。proof 保存全部所列消息。

**A-runtime：警告与开屏直接吻合。** L90 **18519** 为 `Caution [MOUNT_ERR_EXTMEDIA_SLOT1_FOR_AUTO_TRIGGER] appears`，**18521** 为 `scr0099_0001 -> dlg_dbl021_base`，**18525** 的 screen ID 为 `0xfa -> 0x2c7`。A 名称表 `0x415e9d0` 将该警告绑定为 **`0x213`**，槽2为 `0x214`；描述表基址 `0x41dc7c8`、步长 200，槽1行 **`0x41f66a0`**，行 +`0x2c` 为 `0x2c7`。原打印在 A `0x179bf88..0x179bf9c`。**UI 显示挂载错误已证实，底层“卡已插入”的物理判定源仍未证实。**

## 3. 诚实无卡的最小方向与限制

**A-static：原厂有独立的无卡状态，不能用“挂载成功、容量零”代替。** D 上述 `port_state=0 → status0` 合同提供插拔层证据；应用注册表另分 `media_mount_state_slot1/2`（A `0x417eda8/0x417edc0`，ID `0x6db/6dc`）、`media_error_slot1/2`（`0x417ee68/0x417ee80`，`0x6e3/6e4`）、`media_filesystem_mount_state_slot1/2`（`0x417f1e0/0x417f1f8`，`0x708/709`），以及 `media_mount_error_slot1/2`（`0x418f968/0x418f980`，`0x1203/1204`）。这些**参数 ID 不是状态枚举值，也不是可写修复点**。

**B：最小、语义诚实的候选是原 FRONT/RM 服务边界的双空槽模型。** 保留原槽配置和路由，两个实际槽关联的 RM 端口保持 enable=1、port_state=0、hold=0，remove counter 按原协议初始化/变化；在原 `StartInOut` 前提供可读的稳定检测状态，使原 D 发 status0、原 M 不因未知初值尝试挂载。依据 D `0x10cb8..0x10d38`、`0xfb48..0xfd48`、`0xf92c..0xfa50`。原槽1/槽2到 RM1/2/3 的配置映射、FRONT +1/+2 和完整封套、合法 CP 发送来源**尚未闭合**，因此这里给的是模型设计边界，**不提供任意7B包或寄存器写值**。

**B/U：UI 应能显示 NO CARD，但“无卡绝无任何阻塞框”未证实。** Sony 原 FX3 [图标说明](https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000285248.html)明确列有 NO CARD；[Ver.2 或更高版本静态拍摄图标说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888864.html)提供相应版本背景（2026-11-02 查阅）。这些官方材料不保证 7.02 在所有模式、录制/回放操作和设置下都不弹框。对当前正常开机空槽模型，**预期**应消除本次“读取错误”自动触发条件；只有原参数传播、新开屏/原始像素读回和 MENU 交互能完成运行验收。

## 4. AP91 按键：应用回调已经执行

**A-static：O 的 `EventThread` 有回调列表级门控，但并非检查每包 `inh/from_type` 后才调用。** O `0xc90d4..0xc9120` 把原事件存入登记的状态缓存；`0xc9124..0xc9130` 读 callback record `+0x30` 和实例 `+0x3c`，可能跳过本回调；放行后 **`0xc9140 → 0xc8dec`**。后者在 `0xc8e1c..0xc8e2c` 取 record `+0x30` 回调指针，以 `x0=callback_id, x1=event*` 调用。O `0xc8ee0/0xc8f00` 分别日志读取事件 `+24 from_type`、`+28 inh`。不能把 record `+0x30` 与 event `+28` 当同一个字段。

**A-static + A-runtime：应用原回调将32B事件发给 `0x005503e0`，AP91 每次均走到了它。** A `0x16f0fc0..0x16f0ff0` 原分配32B；`0x16f1090..0x16f10b0` 原样复制两组16B并调用 `osal_snd_msg`；封存日志 `caller_relative=0x16f10b4` 就是该调用返回地址。注册路径 A `0x16ef2a0..0x16ef334` 使用原 InfraInput SetCallback/SetEventKeyList。下表列的是**应用回调输出**，比“EventThread 已取到包”更进一层。

| 步骤/键 | down / up 的 L91 行 | 32B raw 解出的 from_type / inh |
|---|---|---|
| 1 ENTER `0x1ac` | 28935 / 28960 | 1 / 0 |
| 2 MENU `0x1ab` | 31273 / 31333 | 1 / 0 |
| 3 DOWN `0x30` | 33742 / 33803 | 1 / 0 |
| 4 DOWN `0x30` | 39006 / 39112 | 1 / 0 |
| 5 RIGHT `0x1af` | 45077 / 45236 | 1 / 0 |
| 6 MENU `0x1ab` | 52227 / 52380 | 1 / 0 |

首包示例 L91 28935：

```text
ac010000 00000000 01000000 ffffff7f 00000000 00000000 01000000 00000000
key=1ac             status=1 prev=7fffffff             from_type=1 inh=0
```

L91 的 `FX3_KEY_EVENT_THREAD_RECV` 摘要打印 `prev_status=0`，而原应用转发 raw 中首按 prev 为 `0x7fffffff`、抬起 prev 为 1；本审计以原32B字节为依据，不用摘要覆盖 raw。没有证据支持把 `from_type` 改为别值或强制清 `inh`。

**A-runtime：六次读回画面完全相同，但不能说完全没发生绘制。** `ap91-step-readbacks.json` 的六份 raw SHA 均为 `fba3e9413bd407b9f113d0792706af6d263319b42286e5ddd1f101239b05b460`，脚本重读六份 `.bin` 验证。其 `latest_native_committed_sequence` 持续变化，故准确表述是“采样像素未变”；L91 最后开屏为 **18144/18148** 的警告，晚于键注入没有新开屏。**应用队列 dequeue、键到 ds_event 的转换和当前 controller 最终动作尚未观测**。

## 5. 对话框处理：已定位部分，不能编造关闭键

**A-static：`dlg_dbl021_base` 是可复用 controller，存在动作门控，不能只靠名字推定 ENTER 必然关闭。** A RTTI 字符串 `0x3035b40`、typeinfo `0x42b6a20`、主 vtable `0x42b6d18` 绑定到原方法。`0x1c9bc88..0x1c9bc9c` 从实例 `+0x110b8/+0x110c0` 取得策略对象/当前上下文并调用策略 vtable `+0x28`；若干默认方法 `0x1c97258..0x1c972ac` 返回0。**未建立各 virtual slot 的正式方法名与该次对象值，不能据此断言当前输入被抑制。**

**A-static：已发现的是内部事件/action，不是关闭键表。** A `0x19f0398..0x19f0484` 将内部 `0x1336e/0x13372` 绑定到 `0x1c980fc/0x1c9828c`；前者按实例上下文及模型值选择后续 screen，后者还读模型门控。`0x1c9753c..0x1c975ac` 处理 `0x30226/0x30227`；`0x1c97698..0x1c976d0` 是倒计数动作。**本审计没有闭合“哪个物理键→哪个 ds_event→哪个内部 action”，不得将这些内部号当作可注入物理键。**

**A-static：自动触发警告具备原条件函数，完整退出语义尚未闭合。** 槽1描述行 `0x41f66a0` 的 `+0x10` 指向 A `0x1799794`：首先要求 `getter0x293c010` 返回值2，再要求 `getter0x293c150` 返回值1，之后还有模式/设置条件（`0x17997e8..0x17998c4`）。getter VA 已记录，但其具体参数身份没有独立绑定；行 `+0x40` 指向 `0x179b1f0 → 0x178fc3c`，行 `+0x50` 指向恒0函数 `0x1789350`。**这些字段的完整角色、何时重新评估、条件消失是否自动关闭，以及 MENU/ENTER 是否允许 dismiss，均未证实。**

因此本次能给出的按键结论为：**在 AP91 的这一个警告状态下，ENTER/MENU/DOWN/RIGHT 六步没有使采样像素或 screen 改变；原因不能定位为未进入应用原回调，也尚不能定位为具体 controller 吞键。** 这同时保留自动警告持续条件、UI dequeue/转换、策略动作三个待区分位置，原证据见上文 VA 与 L91 行。

## 6. 推荐运行修正顺序与观测点

以下仅供 Lead 后续受控运行，本审计没有执行；先补被动证据，再决定最小 provider。

1. **检测来源。** 在 D `0xe6dc` 记录真实 FRONT 来源、长度与完整 body；在 `0xf1e4` 记录发往 `0x80d9016e` 的完整24B头/返回；在 `0xf380` 记录6B status 输出，在 `0xf8d8/0xd40c` 记录 media ID、status、hold、RemoveCnt。由原 config 确认槽1/2↔RM端口映射，禁止猜 GPIO bank/极性。
2. **挂载失败因果。** M `0x9c98` 入口和返回保留 media ID/native rc；原 `0x80cf016d` 查询回复完整读回；`0x9e14` 记录原设备路径和 `mcmn_drv_open` 返回。对照 A 原参数 ID `0x6db/6dc/6e3/6e4/708/709/1203/1204` 与 first-notify `0x13e/13f`，只读采样，不写模型参数“修复”。
3. **双空槽 provider。** 只有完整原 FRONT/RM 封套与初始顺序闭合后，使用持久状态的空槽模型；真实配置中的槽仍 enable、port_state0，保留原通知/所有权/来源，日志声明 synthetic empty-slot provider / original_CP=0。没有卡的设备不回复挂载成功，也不构造容量或文件系统。
4. **输入与退出。** 已有 A `0x16f10b0` 转发后，继续观测 UI `0x5503e0` dequeue、原键映射、ds_event/controller/策略 `+0x28`；记录 `0x1799794` 实际返回及所有 getter 值、警告0x213是否仍选中。不能先清抑制、直接调用 callback 或强制关屏。
5. **最终观测。** 原无卡通知被消费、挂载错误条件解除、新 screen/原图标绘制、独立帧读回；再按原 MENU down/up 检查菜单图形和方向/ENTER 使结果画面改变。六次相同 PNG、消息发送0或静态脚本0均不能代替此项。

## 未证实项与结项状态

- CP FRONT 原发送者、完整封套/source、RM配置与物理槽映射、卡检测GPIO及极性、MMC/SD/NVMe真正检测寄存器：**U**。
- L90 本次原挂载具体返回、设备路径以及从该返回到警告条件参数的逐环绑定：**U**；已经定位 M 的原挂载失败分支和应用警告表。
- `0x213` 准确关闭键、完整自动关闭/重触发条件、该次策略对象状态：**U**。
- AP91 应用转发回调未执行：**已被 A-runtime + A-static 反证**；UI后续 dequeue/action 仍待观察。
- 空槽模型消除警告、NO CARD正常画面、MENU可交互：**未运行验收**。

本审计为**可复现的部分审计**；脚本0不掩盖以上缺口。完整请求中“可直接实施的最小原协议空槽方案”和“对话框全部退出语义”尚未达到闭合，因此向协调者按 partial / failed 报告，供其安排下一轮被动观测。
