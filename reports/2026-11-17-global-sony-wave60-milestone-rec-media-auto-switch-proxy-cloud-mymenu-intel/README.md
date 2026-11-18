# 全球 Sony 实机情报 Wave 60 里程碑（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Rec. Media Settings]` 并发/分类/自动切换媒体与 `VPG200/VPG400` 速率门禁、`[Proxy Settings]` `XAVC HS/S HD` 与 `M4ROOT/SUB` 禁用边界、`[Creators' Cloud]`/`[C3 Portal]`/`[Cnct. while Power OFF]` 零射频危害，以及 `[My Menu]` 42 槽位 vs FX6 20 项 `User Menu` 锁机）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Rec. Media Settings (still image/movie): Recording Media / Auto Switch Media*、*Memory cards that can be used*、*File Format (still image)*、*Proxy Settings*、*Importing images to the computer*、*Select on Cam & Send*、*Cloud Connection (Creators' Cloud)*、*C3 Portal*、*Smartphone Connection*、*Cnct. while Power OFF*、*My Menu (Add Item / Sort Item / Delete Item / Delete Page / Delete All / Display From My Menu)*、*Setting Reset / Reset Network Set. / List of default setting values*），官方 Sony `ILME-FX3` `Ver. 4.00` / `5.00` / `6.00` / `6.02` / `7.00` / `7.02` 固件更新说明，Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *Relay Recording p. 54*、*Proxy Recording p. 60*、*Monitor & Control p. 67*、*C3 Portal & File Transfer pp. 76–78*、*User Menu / User Menu Only / User Menu with Lock pp. 88–89*、*Simul Rec p. 99*、*Cloud All File pp. 132–133*）；并严格对照 `os.O_RDONLY` 本地 donor 实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so` 与 `FX6 string_english.uxc` / `_2.uxc`）。
- **硬件安全态势**：严格只读本地 donor 分析（`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*` 符号、SHA-256 账本与官方文档条目）与 **`推断`**（含 Tier-0 只读保险库与 Stage-B 护栏设计）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[Rec. Media Settings]`、`VPG200/VPG400` 速率门禁与 Tier-0 保险库溢出陷阱）**：
   - **实测事实（架构演进纠偏：FX3 Ver. 2.00+–7.02 已将 `[Prioritize Rec. Media]` 合并为 `[Recording Media]`）**：尽管 `_f.uxc` 中仍沉淀有休眠的旧 Alpha 字符串 `[Prioritize Rec. Media]`（`_f 0x719e`）及 `Sort(RAW/JPEG)`（`_f 0x710d`）/ `Sort(JPEG/RAW)`（`_f 0x765b`），但 `FX3 appFw.so` 中 `prioritize` 为 **`0` 命中**，且官方 `ilc/2210` 确认 FX3（Ver. 2.00 起至 Ver. 7.02）已将存储槽配置重构为独立拆分的 **`[Recording Media]`**（Still 静态照片：`BKID_APP_setting_still_recording_media` = `Slot 1 [默认]` / `Slot 2` / `Simult. Recording` / `Sort Recording`；Movie 动态影像：`BKID_APP_setting_movie_recording_media` = `Slot 1 [默认]` / `Slot 2` / `Simult. Recording`，**无视频分类录制**）与 **`[Auto Switch Media]`**（`_f 0x6dd9`，`BKID_APP_setting_relay_rec` = `Off [默认]` / `On`）。两者**均不支持 `[Camera Settings Reset]` 重置**（必须 `[Initialize]`）。
   - **实测事实（`VPG200/VPG400` 与 `V60/V90` 速率门禁）**：正常录制 `XAVC HS 4K` / `XAVC S 4K`（最大 280 Mbps）需 `SDXC V60+` 或 `CFexpress Type A (VPG200+)`；`XAVC S-I 4K` / `XAVC S-I DCI 4K`（最大 600 Mbps）需 `SDXC V90+` 或 `CFexpress Type A (VPG200+)`；而进入 **`S&Q Motion`**（如 `XAVC S-I 4K` 达 1200 Mbps、`XAVC S-I HD` 240fps/200fps 达 890 Mbps）时，必须使用 **`CFexpress Type A (VPG200+)`**，且 `FX3 base.uxc` 实测同时存在 **`CFexpress VPG200`**（`0xe228`）与 **`CFexpress VPG400`**（`0xe224` / `0xe93f` / `0xe9aa`）双层告警门禁——当高码率叠加同时录制 Proxy 时，系统明确提示可通过关闭 `[Proxy Recording]` 来放行录制。
   - **推断（CRITICAL Tier-0 保险库溢出陷阱）**：若试验台将主录槽设为 `Slot 2`（即 Ver. 7.02 `[Recording Media] = Slot 2`，或旧菜单等效 `[Prioritize Rec. Media = Slot 2]`），一旦 **`[Auto Switch Media] = On`**（`RELAY_REC_ON`），当 `Slot 2` 写满、无卡或发生可切换异常时，FX3 固件将**静默把录制流接力滚入 `Slot 1`**！加之 `[Auto Switch Media]` **抗 `[Camera Settings Reset]`**，单纯设置复位无法消除历史残留的 `On` 状态。因此 Tier-0 保险库必须双保险锁定：① NVRAM/策略层强制 `Auto Switch Media = Off`；② `Slot 1` 内核与 UIPC 层严格 fail-closed，利用 `PRM_HAITA_setting_relay_rec_*_media_read_only_state_slot1` 只读状态并在底层扇区写入前返回 **`EROFS (errno 30)`**。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18` pp. 54, 99）使用 **`Project > Simul Rec`**（`BKID_APP_SETTING_SIMUL_REC`）与手柄/机身独立 **`Rec Button Set`**（支持 `Slot A` / `Slot B` 各自独立启停），以及自动 **`Relay Rec`**（Slot A/B 无缝接力）；但 `FX6` 的 `Simul Rec` 与 **`3840x2160P` 特定网络模式、`Wired/Wireless LAN`、`Modem`、`Streaming`、`Proxy Rec` 及 `Auto Upload (Proxy): Chunk`** 存在硬互斥（`FX6_2 0x41ee..0x41f7`）。

2. **子系统 2（`[Proxy Settings]`：`XAVC HS HD` vs `XAVC S HD`、互斥边界与 `M4ROOT/SUB/*S03.MP4`）**：
   - **实测事实（FX3 Ver. 7.02 菜单真值与码率规格）**：路径 `MENU -> (Shooting) -> [Image Quality/Rec] -> [Proxy Settings]`（`_f 0x6e3f`），包含 **`[Proxy Recording]`**（默认 `Off`，支持 `Camera Settings Reset`）、**`[Proxy File Format]`**（默认 `XAVC S HD`：`1280x720` MPEG-4 AVC/H.264，固定 **`6M 4:2:0 8bit`**；可选 `XAVC HS HD`：`1920x1080` MPEG-H HEVC/H.265，提供 **`16M 4:2:0 10bit`** 与 **`9M 4:2:0 10bit [该格式默认]`**，最高 59.94p/50p）。`FX3 appFw.so` 中实际符号全部以 **`sq_proxy`** 命名（`BKID_APP_setting_sq_proxy_{recording,file_format,record_setting}`），且没有任何 `PRM_HAITA_*proxy*` 跨模块静态字符串，互斥主要在 `convert2MovieMainParams` 与 `CAUTION_ID_PROXY_*` 速率表中执行。
   - **实测事实（精确禁用条件纠偏：`100p/120p` 禁用，而 `XAVC S-I DCI 4K` 允许但受高卡速门禁约束）**：`ilc/2210` 明确仅列明两类完全不可用条件——**正常录像 `[Rec Frame Rate] = 119.88p / 100p`**，以及 **S&Q `[Rec Frame Rate] = 119.88p / 100p` 或 `[Frame Rate] = 120fps / 100fps`**。**`XAVC S-I DCI 4K`（Ver. 3.00+，最高 59.94p/50p）并不在禁录列表内**（`ilc/2210` 在该模式页面明确关联 *Proxy Settings*，且自身也不开放 `120fps/100fps`），但在 600Mbps 下叠开 Proxy 可能触发 `base.uxc` `CFexpress VPG200/VPG400` 卡速降档拦截。
   - **实测事实 + 推断（`M4ROOT/SUB/*S03.MP4`、`Simult. Recording` 与 Slot-1 防火墙）**：Proxy 文件以 `<原片名>S03.MP4` 写入 **`/PRIVATE/M4ROOT/SUB/`**（SDXC）或 **`/M4ROOT/SUB/`**（CFexpress Type A），**不可在机内回放**（仅在母片缩略图显示 `(proxy)` 标识），删除或保护母片会**连带删除/保护对应 Proxy**。当处于 `Simult. Recording` 时，母片与 Proxy 同步双写至 Slot 1 与 Slot 2（且要求双卡同为 `exFAT` 或同为 `FAT32`）；因此 Slot 1 挂载 Tier-0 保险库时，Proxy 子流与连带删除/保护路径**必须同步纳入 `EROFS=30` 写防火墙拦截**。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18` p. 60）实机录制的 `XAVC Proxy` 规格为 **`1920x1080` AVC/H.264 High Profile 4:2:0 Long GOP 9 Mbps**（音频 AAC-LC 128 kbps 2ch，`.mp4` 封装，`FX6_1 0x2000..0x2002` 亦含 `1280x720(9M)/(6M)`）；且 FX6 支持 **`Chunk` 分段 Proxy（`30s/1min/2min` 写入 Slot B）**，但启用后与 `Relay Rec` 及 2 槽 `Simul Rec` 严格互斥，且 `Proxy Rec` 与 `S&Q Motion` / `Interval Rec` 互斥。

3. **子系统 3（`[Creators' Cloud]` / `[C3 Portal]` 与 `[Cnct. while Power OFF]` 零射频与功耗危害）**：
   - **实测事实（Ver. 4.00..7.02 演进与抗复位机制）**：`Ver. 4.00` 引入 **`C3 Portal`**（通过 *Creators' App for enterprise* 同步相机配置与 LUT、`Monitor & Control`）；`Ver. 5.00` 引入 **`[Creators' Cloud]` -> `[Cloud Connection]`**（直接传片上云）；`Ver. 6.00` 加入断点续传/差异传输与网络流媒体；`Ver. 7.00/7.02` 支持按 **`Clip Flag`（`OK/NG/KEEP`）** 筛选直传。关键持久性事实：在 `ilc/2210` 中 **`Cloud Connection *` 与 `Cloud Information *` 带有星号 `*`，连 `[Initialize]` 都不重置**（需在 `Cloud Information` 手动清除账号或执行专用注销）；而 **`[Cnct. while Power OFF]`**（`BKID_APP_extern_menu_cnct_while_power_off`，`_f 0x6ab3`，默认 `Off`）位于 `Network -> [Cnct./Remote Sht.]`，**不可通过 `[Camera Settings Reset]` 重置**（需 `[Reset Network Set.]` 或 `[Initialize]`）。
   - **实测事实 + 推断（物理关机后 BLE 常驻供电与零射频危害）**：当 `[Cnct. while Power OFF] = On` 且手机配对完成后，**即便把 FX3 物理电源开关拨至 `OFF`，`Bluetooth Low Energy`（`UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER`）仍保持通电监听广播**，以便 *Creators' App* 远程唤醒相机并经 Wi-Fi 导片，持续消耗 `NP-FZ100` 电池（直到主动关掉该开关、取消配对、开启 `[Airplane Mode] = On` 或拔除电池）。因此，**Zero-RF 暗室/测试台架必须同时强制 `[Airplane Mode] = On` 且 `[Cnct. while Power OFF] = Off`（`ALWAYS_CONNECTED_OFF`）**，严禁仅凭"物理电源开关 = OFF"假定射频静默。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01` **无蓝牙硬件**，因而根本不存在 BLE 关机驻留唤醒；其云端与遥控流转依赖 **USB-C 有线共享网络 / Wi-Fi / 有线 LAN** 配合 *Creators' App for enterprise*（`C3 Portal` / `Ci Media Cloud`、`All File > Load from Cloud(Private/Share)`）及 *Monitor & Control*，并支持基于 Chunk Proxy 的边录边传（`Auto Upload (Proxy): Chunk`）。

4. **子系统 4（`[My Menu]` 实证 6 页 × 7 项 = 42 槽位 vs FX6 20 项 `User Menu` 锁机）**：
   - **实测事实（关键纠偏：FX3 `[My Menu]` 真实容量为 `6 × 7 = 42` 项，而非 36 或 30 项）**：`ilc/2210`（*Add Item*）明确规定 FX3 可向 `(My Menu)` 添加最多 **`42` 个菜单项**（区别于 `ILCE-7M3` 等老菜单机的 30 项，也非误传的 36 项）；`FX3 appFw.so` 实测精确对应 **`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`** 共 **42 个 NVRAM 槽位**（6 页 × 每页 7 格，`group0`/`group7`/`list7` 均 `0` 命中）。管理项含 `Add Item`、`Sort Item`、`Delete Item`、`Delete Page`、`Delete All`、`Display From My Menu`（默认 `Off`），**不支持 `(Playback)` 菜单项**，且**全部不被 `[Camera Settings Reset]` 清除**（须 `[Initialize]` 或 `[Delete All]`）。
   - **实测事实（FX6 `User Menu` 与租赁行 `User Menu with Lock` 锁机）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18` pp. 88–89）的 **`User Menu`** 最多容纳 **`20` 项**（可经 `All File` 存读 SD 卡，但不入 `Scene File`），并提供两级现场防误触锁：① **`User Menu Only`**（长按 `MENU` 键进入 `Technical > Menu Settings > User Menu Only = On`，屏蔽完整菜单与状态屏编辑，随 `All File` 保存）；② **`User Menu with Lock`**（须**同时按住多功能拨盘与 `MENU` 键**方可在 `Technical > Menu Settings` 中显露并解锁，强制输入 **4 位数字密码 `0000`–`9999`**，默认 `0000`，**不随 `All File` 或 `Scene File` 导出**），构成 FX3 所完全不具备的租赁行/片场硬锁机制。

---

## 1. 子系统 1：`[Rec. Media Settings]`、存储卡速率门禁（CFexpress VPG200/VPG400 vs SDXC V60/V90）与 Tier-0 保险库溢出陷阱

### 1.1 `ILME-FX3 Ver. 7.02` 真值矩阵、UI 合并演进与 Reset 边界（`实测事实`）

| 菜单项 / 路径（`ilc/2210`） | `FX3 Ver. 7.02` 实机真值与出厂默认 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证与架构演进细节（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Prioritize Rec. Media]`**（旧 Alpha 名称） | **在 FX3 Ver. 2.00+–7.02 中已合并取消独立菜单** | — | `_f 0x719e` `'Prioritize Rec. Media'`（简中 `优先摄像媒体` / 繁中 `優先錄製插槽` / 日文 `優先記録メディア`）属**休眠历史字符串**；`FX3 appFw.so` 对 `prioritize` **`0` 命中** |
| **`[Recording Media]`（Still 静态照片）**<br>（`Shooting -> Media -> Rec. Media Settings -> Recording Media`） | **`Slot 1`**（**默认**） / `Slot 2` / `Simult. Recording` / `Sort Recording` | **Not available**<br>*（需 `[Initialize]`）* | `_f 0x749d` / `0x78be` / `0x7505` / `0x7916`；`BKID_APP_setting_still_recording_media`；`VAL_setting_still_recording_media_STILL_RECORDING_MEDIA_{SLOT_1,SLOT_2,SIMULTANEOUS_RECORDING,SORT_RECORDING}` |
| **`[Recording Media]`（Movie 动态影像）**<br>（`Shooting -> Media -> Rec. Media Settings -> Recording Media`） | **`Slot 1`**（**默认**） / `Slot 2` / `Simult. Recording`<br>*（无 `Sort Recording`）* | **Not available**<br>*（需 `[Initialize]`）* | `BKID_APP_setting_movie_recording_media`；`VAL_setting_movie_recording_media_MOVIE_RECORDING_MEDIA_{SLOT_1,SLOT_2,SIMULTANEOUS_RECORDING}`；`Simult. Recording` 强制 Slot 1 与 Slot 2 **文件系统一致**（不可混用 `exFAT` 与 `FAT32`） |
| **`[Sort Recording]` 细分规则**<br>（仅 Still 静态照片生效） | 按 `[File Format]` 将 **RAW** 与 **JPEG/HEIF** 分别写入 Slot 1 / Slot 2 | **Not available**<br>*（需 `[Initialize]`）* | `FX3 appFw.so` `No348..No353` / `No486..No492` 专设 `SortRecSlot1` 与 `SortRecSlot2`；`ilc/2210` 限制：**JPEG/HEIF Quality、Image Size 与 RAW File Type 仍由两卡槽共享同一设定** |
| **`[Auto Switch Media]`**<br>（`Shooting -> Media -> Rec. Media Settings -> Auto Switch Media`） | **`Off`**（**默认**） / `On` | **Not available**<br>*（需 `[Initialize]`）* | `_f 0x6dd9`（简中 `自动切换摄像媒体` / 繁中 `自動切換記憶卡錄製` / 日文 `記録ﾒﾃﾞｨｱ自動切換`）；`BKID_APP_setting_relay_rec`；`VAL_setting_relay_rec_RELAY_REC_{OFF,ON}`；Ver. 7.00 起录制时同时显示双卡剩余容量 |

### 1.2 Tier-0 保险库溢出陷阱证明与 Fail-Closed `EROFS=30` 护栏（`实测事实` + `推断`）

1. **`[Auto Switch Media] = On` 在单卡与双卡模式下的真实切换逻辑（`实测事实`）**：
   - 根据 `ilc/2210`（*Rec. Media Settings: Auto Switch Media*）与 `FX3 appFw.so` `PRM_HAITA_setting_relay_rec_*`：
     - **单卡模式（例如 `[Recording Media] = Slot 2` + `[Auto Switch Media] = On`）**：当 `Slot 2` 存满、或 `Slot 2` 未插卡时，相机**自动将 `[Recording Media]` 切换至 `Slot 1` 继续录制**；若 `Slot 1` 也满且 `Slot 2` 已换入空卡，则会再次切回 `Slot 2`。
     - **分类模式（`Sort Recording` + `[Auto Switch Media] = On`）**：当任意一槽存满时，相机会把 RAW 与 JPEG/HEIF **同时写入另一张未满卡**，直到满卡被替换。
     - **双卡同时录制（`Simult. Recording` + `[Auto Switch Media] = On`）**：当一槽存满时，自动降级为向**另一张剩余卡单槽继续录制**，并在更换满卡后自动恢复同时录制。
2. **为什么这是 Tier-0 保险库的致命风险（`推断`）**：
   - 在本实验室架构中，**Slot 1 承载 Tier-0 只读恢复保险库/恢复引导分区镜像**，实验素材与试录只能落在 **Slot 2**。
   - **陷阱一（主槽满溢自动回滚 Slot 1）**：若操作员或前置配置将主录设为 `Slot 2`，但遗漏关闭 `[Auto Switch Media]`（保持了 `On`），则在 S&Q 高码率或长时间连续录制耗尽 `Slot 2` 后，固件状态机 `setting_relay_rec` 会**静默切换目标卡槽并向 Slot 1 发起 `DCIM/` / `M4ROOT/` / `AVF_INFO` 扇区写入**，瞬间污染或毁损 Tier-0 恢复保险库。
   - **陷阱二（`Camera Settings Reset` 免疫性）**：`ilc/2210` 实证 `[Recording Media]` 与 `[Auto Switch Media]` **均无法被 `[Camera Settings Reset]` 复位**。若测试机从外部环境借调且曾开启 `Auto Switch Media = On`，常规拍摄设置重置不会将其清回 `Off`。
   - **双层 Fail-Closed 护栏设计**：`FX3 appFw.so` 的 `PRM_HAITA_setting_relay_rec_movie_setting_movie_recording_media_media_read_only_state_slot1` 与 `media_locked_state_slot1` 已经证明上层互斥表本身会检测 Slot 1 只读/写保护状态。因此 Stage-B 运行态必须执行：① **配置锁死**：NVRAM 强制校验 `BKID_APP_setting_relay_rec == RELAY_REC_OFF` 与 `BKID_APP_setting_{movie,still}_recording_media == SLOT_2`；② **VFS/块设备硬防火墙**：Slot 1 底层挂载严格置于硬件/内核只读保护下，任何来自 `setting_relay_rec`、Still/Movie 录制或数据库重建（`AVF_INFO`）的写扇区请求必须在首字节落盘前 fail-closed 拦截并返回 **`EROFS (errno 30)`**（确保 `slot1_data_sector_writes == 0`）。

### 1.3 `ILME-FX3 Ver. 7.02` 存储卡速度等级门禁全表（`实测事实`）

以下数据交叉核验自 `ilc/2210`（*Memory cards that can be used*）与 `FX3 base.uxc` 告警字符串表（`0xe224..0xea7b`）：

| 拍摄模式 | 视频格式（File Format） | 最高码率 | 官方最低卡速门禁（`ilc/2210`） | `FX3 base.uxc` 实证拦截阈值与降档提示 |
| :--- | :--- | :---: | :--- | :--- |
| **正常 Movie** | `XAVC HS 4K` / `XAVC S 4K` | `280 Mbps` | **CFexpress Type A (`VPG200+`)** 或 **SDXC `V60+`** *(注：≤200M 可用 `U3/V30`；≤60M 可用 `Class 10`)* | `base 0xe25a / 0xe28c / 0xe91f / 0xe934`（提示 `SDXC V60+` / `CFexpress VPG200+`，且可尝试关 `Proxy`） |
| **正常 Movie** | `XAVC S HD` | `100 Mbps` | **CFexpress Type A** 或 **SDHC/SDXC `U3+`** *(≤60M 可用 `Class 10`)* | `base 0xe238 / 0xe8fb / 0xe9a8`（提示 `SDXC U3/V30+` / `CFexpress VPG200+`） |
| **正常 Movie** | `XAVC S-I 4K` / **`XAVC S-I DCI 4K`** *(Ver. 3.00+)* | `600 Mbps` | **CFexpress Type A (`VPG200+`)** 或 **SDXC `V90+`** | `base 0xe23f / 0xe273 / 0xe279 / 0xe9ac / 0xea39`（提示 `SDXC V90+` / `CFexpress VPG200+`） |
| **正常 Movie** | `XAVC S-I HD` | `222 Mbps` | **CFexpress Type A (`VPG200+`)** 或 **SDXC `V90+`** | 同上（V90 / VPG200 档门禁） |
| **S&Q Motion** | `XAVC HS 4K` | `500 Mbps` | **CFexpress Type A (`VPG200+`)** 或 **SDXC `V60+`** *(`120fps/100fps` 可能需 **`V90`**)* | `base 0xe28c / 0xe9b3`（叠加 Proxy 时触发升卡或关 Proxy 提示） |
| **S&Q Motion** | `XAVC S 4K` | `560 Mbps` | **CFexpress Type A (`VPG200+`)** 或 **SDXC `V60+`** *(`120fps/100fps` 可能需 **`V90`**)* | 同上 |
| **S&Q Motion** | `XAVC S HD` | `500 Mbps` | **CFexpress Type A (`VPG200+`)** 或 **SDXC `V60+`** *(`240fps/200fps` 可能需 **`V90`**)* | `base 0xe96c / 0xe9b6` |
| **S&Q Motion** | **`XAVC S-I 4K`** | **`1200 Mbps`** | **强制 CFexpress Type A (`VPG200+`)**（S&Q 下 **SDXC 不可用**） | `base 0xe228`（`VPG200+`）及 **`0xe224 / 0xe93f / 0xe9aa / 0xea64 / 0xea78`（`CFexpress VPG400+`）**：S&Q `1200 Mbps` 实测写入需求高达 `150 MB/s`，UXC 层备有 **`CFexpress VPG400`** 最高级硬件速率门禁并提示可关 `Proxy Recording` 释放带宽 |
| **S&Q Motion** | **`XAVC S-I HD`** | `890 Mbps` | `240fps/200fps` 强制 **CFexpress Type A (`VPG200+`)**；其余可用 **SDXC `V90+`** | `base 0xe283 / 0xea20` |
| **S&Q Motion** | **`XAVC S-I DCI 4K`** *(Ver. 3.00+)* | `600 Mbps` | 慢动作强制 **CFexpress Type A (`VPG200+`)**（且不支持 `120fps/100fps`） | `base 0xea65 / 0xea6e` |

*(注：FX3 不支持 CFexpress Type B；SDHC ≤32GB 卡录制 XAVC S 会按 4 GB 自动分片。)*

### 1.4 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 双槽录制架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`, `5-024-458-18`) |
| :--- | :--- | :--- |
| **物理卡槽介质** | 双混合槽（各兼容 `CFexpress Type A` 或 `SDXC/SDHC UHS-I/II`） | 双混合槽 `Slot A / Slot B`（各兼容 `CFexpress Type A` 或 `SDXC UHS-II/I`） |
| **同时录制模式** | `Rec. Media Settings -> Recording Media = Simult. Recording`（Still/Movie 分别配置；两槽需同为 exFAT 或 FAT32） | **`Project > Simul Rec`**（`p. 99`，`BKID_APP_SETTING_SIMUL_REC`），配合 **`Rec Button Set`**（`FX6_1 0x221b..0x221d`）支持机身 `Rec` 键与手柄 `Handle Rec` 键**分别控制 Slot A 与 Slot B** |
| **接力/自动切换** | `[Auto Switch Media] = On/Off`（`BKID_APP_setting_relay_rec`，单卡/双卡/分类均支持自动接力） | **`Relay Rec`**（`p. 54`，当前槽余量为零自动切至另一槽；回放模式不支持跨槽连续播放单一片段或切卡） |
| **跨子系统硬互斥** | `Simult. Recording` 仅要求双卡同文件系统；`Movie` 无分类录制 | **`FX6_2 0x41ee..0x41f7`**：开启 `Simul Rec` **强制关闭 `Wired LAN`、`Wireless LAN`、`Modem`、`Proxy Rec` 与 `Streaming`**；且 `Auto Upload (Proxy) = Chunk` 占用 Slot B 时**禁止 `Relay Rec` 与 2 槽 `Simul Rec`**（`p. 54, 60`） |

---

## 2. 子系统 2：`[Proxy Settings]`（`XAVC HS HD` vs `XAVC S HD`）、互斥禁录边界与 `M4ROOT/SUB/*S03.MP4` 写卡防火墙

### 2.1 `ILME-FX3 Ver. 7.02` Proxy 菜单真值与码率规格（`实测事实`）

| 菜单项 / 路径（`ilc/2210`） | `FX3 Ver. 7.02` 可选项与出厂默认 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **入口路径**<br>`MENU -> (Shooting) -> [Image Quality/Rec] -> [Proxy Settings]` | — | **Can be reset** | `_f 0x6e3f` `\ue5cbProxy Settings` / `0x7aff` |
| **`[Proxy Recording]`** | **`Off`**（**默认**） / `On` | **Can be reset** | `_f 0x6f19` `\ue5cbProxy Recording` / `0x64e2` / `0x7845`；`BKID_APP_setting_sq_proxy_recording`；`VAL_setting_sq_proxy_recording_PROXY_RECORDING_{OFF,ON}` |
| **`[Proxy File Format]`** | **`XAVC S HD`**（**默认**，`1280×720`, H.264/AVC, Max 59.94p/50p） / **`XAVC HS HD`**（`1920×1080`, H.265/HEVC, Max 59.94p/50p） | **Can be reset** | `_f 0x6662` / `0x61f0` / `0x61c3` / `0x7659` / `0x66b2`；`BKID_APP_setting_sq_proxy_file_format`；`VAL_setting_sq_proxy_file_format_PROXY_FILE_FORMAT_{XAVC_HS_HD,XAVC_S_HD}` |
| **`[Proxy Rec. Settings]`** | 当 `XAVC HS HD`：**`9M 4:2:0 10bit`**（**默认**） / `16M 4:2:0 10bit`<br>当 `XAVC S HD`：**`6M 4:2:0 8bit`**（**默认且唯一**） | **Can be reset** | `_f 0x6aad` / `0x611c` (`9M 4:2:0 10bit`) / `0x62a6` (`16M 4:2:0 10bit`) / `0x764c` (`6M 4:2:0 8bit`)；`_f 0x6b8f` (`16M 4:2:0 8bit`) 与 `VAL_*_9M_420_8BIT` 为跨机型休眠枚举；`BKID_APP_setting_sq_proxy_record_setting` |
| **`[Send to Smartphone]` Proxy 筛选**<br>（`Select on Cam & Send -> Sending Target`） | `Proxy Only` / `Original Only` / `Proxy & Original` | 随传输设置 | `_f 0x7ae1` / `0x6bfa` / `0x61e9` / `0x67c2`；`BKID_APP_setting_send_to_smartphone_function_proxy_send_contents` |

### 2.2 Proxy 禁用模式实证与 `appFw.so` `sq_proxy` 符号剖析（`实测事实`）

1. **官方 `ilc/2210` 精确禁用条件（逐条实证纠偏）**：
   - **明确禁用条件 ①**：正常电影拍摄时，**`[Rec Frame Rate]` 设为 `119.88p` 或 `100p`**（此时无论主格式为 `XAVC HS 4K`、`XAVC S 4K` 或 `XAVC S HD`，均无法录制 Proxy）。
   - **明确禁用条件 ②**：`S&Q` 慢/快动作拍摄时，**`[Rec Frame Rate]` 设为 `119.88p` / `100p`**，**或 `[Frame Rate]`（传感器采集帧率）设为 `120fps` / `100fps`**。
   - **关键纠偏（`XAVC S-I DCI 4K` 并不被系统功能表直接禁用！）**：官方 `ilc/2210` *Proxy Settings* 页面**未将 `[XAVC S-I DCI 4K]` 列为 Proxy 禁用项**；相反，*Movie Settings (XAVC S-I DCI 4K)* 与 *File Format (movie)* 页面均将 *Proxy Settings* 列为有效关联项（因 `XAVC S-I DCI 4K` 仅提供 `23.98p/24.00p/25p/29.97p/50p/59.94p`，且 `S&Q` 下本就禁止选择 `120fps/100fps`）。**但是**，由于 `XAVC S-I DCI 4K` 在 59.94p 下主码率已达 `600 Mbps`，`ilc/2210` *Memory cards that can be used* 明确提示开启 Proxy 时可能需要更高速存储卡，否则将触发 `FX3 base.uxc` 速率告警（`0xe228` / `0xe224`）要求升卡或关闭 `[Proxy Recording]`。
2. **`FX3 appFw.so` 内部 `sq_proxy` 架构事实**：
   - `FX3 appFw.so` 中不存在名为 `PRM_HAITA_setting_proxy_*` 的独立互斥表字符串（`HAITA.*proxy` 为 **`0` 命中**）；全量 Proxy 设置均归口于 `BKID_APP_setting_sq_proxy_{recording,file_format,record_setting}`，并由 `infra_wrapper_mpr::detail::convert2MovieMainParams(...)` 在下发 MPR 编码管线参数时，连同 `setting_file_format_t` 与各格式帧率参数（含 `xavc_s_i_dci_4k_60p/50p/...`）联合校验，卡速不达标则由 `CAUTION_ID_PROXY_[SLOW_AND_QUICK_]XAVC_TRANSFER_RATE_DISABLE_UNDER_{100,200,400,600,1350}MBPS_MEDIA_*` 弹出对应槽位速率拦截。

### 2.3 `M4ROOT/SUB/*S03.MP4` 目录、`Simult. Recording` 行为与 Slot-1 写防火墙（`实测事实` + `推断`）

1. **目录结构、命名与生命周期绑定（`实测事实`）**：
   - `ilc/2210`（*Importing images to the computer*）与 Sony XAVC 规范确认：主视频写入 `CLIP/`，Proxy 写入 **`SUB/`**（SD/SDXC 卡为 `/PRIVATE/M4ROOT/SUB/`，CFexpress Type A 卡根为 `/M4ROOT/SUB/`）；文件命名遵循 **`<母片Clip名>S03.MP4`**（例如 `C0001.MP4` 对应 `C0001S03.MP4`，且内嵌与母片一致的时间码与自定义 `[File Name Format]` 前缀）。
   - **机内隔离与连带操作规则**：Proxy 文件**不会显示在相机单张或索引回放画面中**，亦**不可在机内直接回放**（有 Proxy 的母片仅在界面叠加 `(proxy)` 图标）；但对带有 Proxy 的母片执行 **`Delete`（删除）或 `Protect`（保护）时，会同时删除或保护对应的 Proxy 文件**，二者不可在机内拆开单独操作。
   - **与 `[Simult. Recording]` 叠加**：FX3 在 `[Recording Media] = Simult. Recording` + `[Proxy Recording] = On` 时，无独立的"仅单槽写 Proxy"开关（区别于 FX6 的 Proxy 分槽调度），会将**主片 `CLIP/` 与 Proxy `SUB/*S03.MP4` 同步写入 Slot 1 与 Slot 2**（并要求两卡文件系统完全一致）。
2. **Slot-1 Tier-0 保险库写防火墙（`推断`）**：
   - 任何开启 `Proxy Recording = On` 且允许流向 `Slot 1`（无论是 `Slot 1` 单录、`Simult. Recording` 还是 `Auto Switch Media` 溢流）的录制请求，以及针对 `Slot 1` 母片的 `Delete` / `Protect` 连带改写 `M4ROOT/SUB/*S03.MP4` 与 `AVF_INFO` 索引的操作，**必须在 VFS 与存储拦截层被 fail-closed 阻断并返回 `EROFS (errno 30)`**，确保 `Slot 1` 既不新增 `SUB/*S03.MP4` 也不被连带删改。

### 2.4 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` Proxy 体系对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18` p. 60 + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **编码规格与码率** | `XAVC HS HD`（HEVC `1920x1080` `16M`/`9M` 4:2:0 10-bit）或 `XAVC S HD`（AVC `1280x720` `6M` 4:2:0 8-bit） | **`XAVC Proxy`**：AVC/H.264 High Profile 4:2:0 Long GOP VBR **`1920×1080 (9 Mbps)`**（AAC-LC 128kbps 2ch `.mp4`）；`FX6_1 0x2000..0x2002` 与 `FX6 appFw.so` 亦含 `1280x720(9M)/(6M)` 枚举 |
| **目录与分片** | `M4ROOT/SUB/<Clip>S03.MP4`（仅完整文件随母片同步录制） | `XDROOT/Sub/`；支持 **`Proxy Rec > Chunk`**（`30s / 1min / 2min` 分段，配合 `Auto Upload (Proxy): Chunk` 专占 **Slot B** 边录边传） |
| **机内回放与 LUT** | 机内不可浏览/回放 Proxy；可随 `Monitor LUT` 嵌入或保持一致性 | 可设置 Proxy LUT（`BKID_APP_SETTING_LUT_SETTING_PROXY`）与音频通道（`CH1/CH2` 或 `CH3/CH4`） |
| **核心互斥差异** | 仅 `100p/120p` 与 S&Q `100/120fps` 禁用；可与 `Simult. Recording` 共存 | `Proxy Rec` 与 **`Simul Rec`、`S&Q Motion`、`Interval Rec`** 严格互斥；`Chunk` 模式下禁止 `Relay Rec` |

---

## 3. 子系统 3：`[Creators' Cloud]` / `[C3 Portal]` 与 `[Cnct. while Power OFF]` 零射频与功耗危害

### 3.1 `Ver. 4.00..7.02` 云端演进、菜单真值与 Reset 抗性（`实测事实`）

| 功能项 / 菜单路径（`ilc/2210`） | 引入版本与可用规格（`FX3 Ver. 7.02`） | 复位边界（`Reset`） | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Cloud Connection]`** & **`[Cloud Information]`**<br>（`Network -> Creators' Cloud`） | **`Ver. 5.00+`**：经 *Creators' App*（2.3.0+）配对后直连 **Creators' Cloud** 上传；**`Ver. 7.00+`** 支持按 `Clip Flag (OK/NG/KEEP)` 筛选直传（默认 `Off`） | **`Camera Settings Reset` 不可重置**；`ilc/2210` 标 **`*`**（**连 `[Initialize]` 也不清除！** 须在 `Cloud Information` 手动删除账号） | `_f 0x6e63` / `0x624e` / `0x773e` / `0x7497` / `_g 0x62b5` / `0x646f`；`BKID_APP_setting_cloud_connection`；`PRM_HAITA_confirm_change_cloud_connection`（**`CLOUD_CONNECTION_ON_FTP_OFF` 与 FTP 互斥**）；`sequence_cloud_connection_reconnect_{mqtt,webrtc}` |
| **`[C3 Portal]`（企业云工作流）** | **`Ver. 4.00+`**：配合 ***Creators' App for enterprise***（须 C3 Portal / Ci Media Cloud 合同），云端下发配置文件与 **User LUT**（`Cloud(Private)` / `Cloud(Share)`） | 属网络/账户配置，不受 `Camera Settings Reset` 影响 | `_f 0x7c55` `Connect to Cloud(Private)` / `_f 0x7c52` `Connect to Cloud(Share)`；`N5model22cube_file_cloud_info_tE`、`N5model31save_load_settings_cloud_info_tE`、`C3P_PACKET*` |
| **`[Smartphone Connection]`**<br>（`Network -> Cnct./Remote Sht.`） | 配对 *Creators' App*（BLE + Wi-Fi）；`[Airplane Mode] = On` 时不可用；BLE 最多并发 2 设备 | **不受 `Camera Settings Reset` 影响**（须 `[Reset Network Set.]` 或 `[Initialize]`） | `_g 0x6471` / `0x6493` / `0x64a0`；`N5model31setting_smartphone_connection_tE`、`BLUETOOTH_PAIRING_LAUNCH_FUNCTION_CLOUD_CONNECTION` |
| **`[Cnct. while Power OFF]`**<br>（`Network -> Cnct./Remote Sht. -> Cnct. while Power OFF`） | **`Off`**（**默认**） / `On`；配对后即便关机也可被 *Creators' App* 唤醒浏览并导入卡内素材 | **不受 `Camera Settings Reset` 影响**（须 `[Reset Network Set.]`、`[Initialize]` 或取消配对/配对失败自动回 `Off`） | `_f 0x6ab3` `\ue59eCnct. while Power OFF`（简中 `关机时连接` / 繁中 `關閉電源時連線` / 日文 `電源OFF中の接続`）；`_f 0x6833` `\ue59eAlways Connected`；`_g 0x6498`；`BKID_APP_extern_menu_cnct_while_power_off`、`BKID_APP_setting_always_connected`、`UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER`、`sequence_set_bluetooth_remote_power_mode` |

*(注：在 `_g 0x6476` 中实测发现 Sony 原厂局部缺失：`EN='Bluetooth is required to connect to Creators\' Cloud. Set "Airplane Mode" to "Off“.'`，而 `SC=''` 与 `TC=''` 为空串，JP 完整。)*

### 3.2 `[Cnct. while Power OFF]` 零射频（Zero-RF）与功耗危害机制（`实测事实` + `推断`）

1. **物理电源关闭≠射频与供电归零（`实测事实`）**：
   - `ilc/2210`（*Cnct. while Power OFF*）与 `FX3 appFw.so`（`UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER`、`sequence_set_bluetooth_remote_power_mode`、`BLUETOOTH_PAIRING_LAUNCH_FUNCTION_SEND_AT_POWER_OFF`）共同证实：一旦 `[Cnct. while Power OFF]` 设为 `On` 且已完成蓝牙配对，将机身物理 `ON/OFF` 拨杆切至 **`OFF`** 时，**主 SoC 虽进入关机态，但 BLE 低功耗蓝牙芯片仍维持带电广播/监听状态**；只要手机端 *Creators' App* 发起 `[Import]`，即可通过 BLE 唤醒机身拉起 Wi-Fi 传输卡内文件。
   - **副作用**：`ilc/2210` 明确警告该模式下 **`NP-FZ100` 电池会在关机状态持续缓慢掉电**；开机则会终止手机传输并切回拍摄界面。
2. **台架 Zero-RF 与电量保全硬规程（`推断`）**：
   - 在电磁屏蔽暗室、射频合规测试或长期搁置台架上，**绝对不可认为"拨断电源开关 = Zero-RF"**。若先前启用了 `[Cnct. while Power OFF] = On`，即使执行 `[Camera Settings Reset]` 也不会将其关闭！
   - 必须执行三步清零：① 将 `[Cnct. while Power OFF]` 显式置 `Off`（`ALWAYS_CONNECTED_OFF`）并设置 `[Bluetooth Function] = Off`；② 将 **`[Airplane Mode]` 置 `On`**（`libInfraAirplaneMode.so`，且该开关可跨 `[Reset Network Set.]` 与 `[Initialize]` 持久化保留）；③ 如已绑定 `Cloud Connection`，须通过 `Cloud Information` 注销并执行 `[Reset Network Set.]`。

### 3.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 云端与移动协同对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18` pp. 67, 76–78, 132–133) |
| :--- | :--- | :--- |
| **云平台与配套 App** | **Creators' Cloud**（*Creators' App*）+ **C3 Portal / Ci Media Cloud**（*Creators' App for enterprise*）+ ***Monitor & Control*** | **C3 Portal / Ci Media Cloud**（*Creators' App for enterprise*）+ ***Monitor & Control***（旧 *Content Browser Mobile* 已在 Ver. 5.00+ 退役；`5-024-458-18` 不面向个人版 Creators' Cloud） |
| **云端配置/LUT 下发** | 支持 C3 Portal 加载配置文件与 User LUT（`Ver. 4.00+`） | `All File > Load from Cloud(Private)` / `Load from Cloud(Share)`（`FX6_1 0x2632..0x2641`），支持将 `File Transfer` 设定由手机 USB-Tethering 扫码推送（根证书需手动配置） |
| **关机后蓝牙唤醒 (`Cnct. while Power OFF`)** | **存在**（`Bluetooth 5.0` 常驻供电，存在 Zero-RF 泄频与掉电风险） | **物理不存在**（FX6 无蓝牙硬件；`FX6 appFw.so` `BKID_APP_SETTING_BLUETOOTH_FUNCTION` 为休眠符号） |
| **边拍边传机制** | Ver. 6.00+ 支持拍摄中后台传至手机/平板；FTP/Cloud 支持按 `Clip Flag`/`Shot Mark` 筛选 | 支持 `File Transfer > Auto Upload / Auto Upload (Proxy)`，以及 **`Chunk` 分段 Proxy 边录边传**（Proxy 优先于原片上传） |

---

## 4. 子系统 4：`[My Menu]`（实证 6 页 × 7 项 = 42 槽位）vs FX6 `[User Menu]`（20 项 + `User Menu Only` / `User Menu with Lock`）

### 4.1 `ILME-FX3 Ver. 7.02` `[My Menu]` 结构、NVRAM 布局与 Reset 边界（`实测事实`）

| 菜单项 / 路径（`ilc/2210`） | `FX3 Ver. 7.02` 实机行为与默认 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **整体拓扑与容量上限**<br>`MENU -> (My Menu) -> [My Menu Setting]` | **最多 `42` 个项目**（6 页 × 每页 7 格）；**禁止添加 `(Playback)` 菜单项** | **Not available**<br>*（须 `[Initialize]` 或 `[Delete All]`）* | **`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`**（精确 `6 × 7 = 42` 个 NVRAM 槽位，`group0`/`group7`/`list7` 均 **`0` 命中**）；`_g 0x6232` / `0x6257` / `0x608d` |
| **`[Add Item]`** | 从菜单选取项目并指定目标页/格位插入 | **Not available** | `_f 0x7122` / `0x7248` / `0x7249` / `0x69e9`；`BKID_APP_mymenu_add_group_number` / `add_item_number`、`set_mymenu_setting_item(int, int, menu_item_id_t)` |
| **`[Sort Item]`** | 调整已注册 My Menu 项目的排列顺序 | **Not available** | `_f 0x7a11` / `0x61db` / `0x76f6` / `0x73f5`；`BKID_APP_mymenu_sort_{group_id,group_number,item_number,tab_number}` |
| **`[Delete Item]`** | 逐项删除指定位置的 My Menu 条目 | **Not available** | `_f 0x698d` / `0x6e58` |
| **`[Delete Page]`** | 按整页删除该页所有 My Menu 条目 | **Not available** | `_f 0x6b7c` / `0x7474`；`BKID_APP_mymenu_delete_group_number`、`delete_mymenu_page_item(int)` |
| **`[Delete All]`** | 一键清空全部 My Menu 注册项 | **Not available** | `_f 0x6226` `'Deletes all items added to My Menu.'`（简中 `删除添加至我的菜单的全部项目。`） |
| **`[Display From My Menu]`** | **`Off`**（**默认**，按 `MENU` 回到上次停留页） / `On`（按 `MENU` 优先打开 My Menu） | **Not available**<br>*（须 `[Initialize]`）* | `_f 0x64f6` / `0x658d` / `0x6119`；`BKID_APP_setting_display_from_mymenu`、`DISPLAY_FROM_MY_MENU_{OFF,ON}`、`EVENT_FUNC_CUSTOM_MY_MENU_{ON,OFF}`、`is_opened_menu_by_display_my_menu` |

### 4.2 关键实证纠偏：为什么 FX3 `[My Menu]` 是 `42` 槽位而非 `36` 或 `30` 槽位（`实测事实`）

- 早期 Sony Alpha 菜单架构（如 `ILCE-7M3`、`ILCE-6400`、`ZV-E10`）采用 **5 页 × 6 项 = 30 项**上限，部分工程文档也常误将新版竖向列表记为 `6 × 6 = 36` 槽位。
- 本次跨源实证彻底锁定真相：**官方 `helpguide.sony.net/ilc/2210/v1/en/`（*Add Item*）明确标定 `ILME-FX3` 上限为 `42` 项**（与 `ILCE-7M4`/`ILCE-7RM5`/`ILCE-6700`/`ZV-E1` 一致），而 `FX3 appFw.so` 中的 `BKID_APP_mymenu_group1_setting_list0` 至 `BKID_APP_mymenu_group6_setting_list6`（`group1..6` × `list0..6` = **`6 × 7 = 42`**）从二进制 NVRAM 键名层面给出了 1:1 结构证明。同时 `FX3` 中**不存在任何锁定完整菜单的 `User Menu Only` 或 PIN 锁功能**。

### 4.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 自定义菜单与租赁锁机对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`[My Menu]`) | `ILME-FX6 Ver. 6.01` (`[User Menu]`, `5-024-458-18` pp. 88–89) |
| :--- | :--- | :--- |
| **槽位容量上限** | **`42` 项**（6 页 × 7 格，`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`） | **`20` 项**（`Edit User Menu`，`FX6_2 0x4d4a`） |
| **进入/默认行为** | 设 `[Display From My Menu] = On` 后按 `MENU` 优先展示，但**左/右翻页即可自由切回完整菜单**，无法锁闭全菜单 | 支持常驻 `User Menu`，也可通过自定义键 `ASSIGNABLE_SWITCH_USER_MENU` 快速呼出 |
| **防误触与租赁行硬锁** | **无**（无 `Only` 模式，亦无 PIN 密码锁） | **两级硬锁机制**：<br>① **`User Menu Only`**（`BKID_APP_SETTING_USER_MENU_ONLY`，`FX6_2 0x4ee2`）：长按 `MENU` 打开完整菜单在 `Technical > Menu Settings` 开启，隐藏完整菜单并禁止状态屏改参（随 `All File` 保存，`Scene File` 不保存）；<br>② **`User Menu with Lock`**（`FX6_2 0x55f3`）：须**同时按住多功能拨盘与 `MENU` 键**才显露开关，启用时弹窗设 **4 位数字密码（`0000`–`9999`，默认 `0000`）**，全锁定状态屏与完整菜单，解锁须重复双键组合并校验密码（**不随 `All File` 或 `Scene File` 保存**） |
| **配置导出/重置** | 不被 `Camera Settings Reset` 重置；可随 `[Save/Load Settings]`（`CAMSET*.DAT`）迁移 | `User Menu` 与 `User Menu Only` 可随 `All File`（`Load/Save SD Card`）迁移；`User Menu with Lock` 密码锁独立留存机身防绕过 |

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 角色与实证范围 |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`nflasha15/lib/appFw.so`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `recording_media`、`relay_rec`、`sq_proxy`、`cloud_connection`、`cnct_while_power_off`、`mymenu_group{1..6}_setting_list{0..6}` |
| `FX6 appFw.so` (`FX6 .../lib/appFw.so`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `SIMUL_REC`、`PROXY_FORMAT`、`AUTO_UPLOAD_PROXY`、`USER_MENU_ONLY`、`USER_MENU_OPERATION` |
| `FX3-CX95900_ALLLANG-Backup.bin` (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失备份结构基线（`BK4\x00`） |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | FX3 `hdr_flag=15` 主菜单与提示英文包（`7,486` 槽位） |
| `FX3 string_english.uxc` | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | FX3 `hdr_flag=8` 基础菜单与 `VPG200/VPG400` 速率告警英文包（`2,692` 条） |
| `FX3 string_english_g.uxc` | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | FX3 `hdr_flag=8` 扩展提示与 `Creators' Cloud` 英文包（`1,390` 条） |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | 简体中文 `_f` 主菜单四语 `resid16` 精确映射 |
| `FX3 string_simplifiedchinese.uxc` / `_g.uxc` | `149,064` / `61,296` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文基础/扩展包 `resid16` 映射 |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | 繁體中文 `_f` 主菜单四语 `resid16` 精确映射 |
| `FX3 string_traditionalchinese.uxc` / `_g.uxc` | `151,908` / `61,372` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁體中文基础/扩展包 `resid16` 映射 |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | 日本語原厂 `_f` 主菜单四语 `resid16` 精确映射 |
| `FX3 string_japanese.uxc` / `_g.uxc` | `208,564` / `89,428` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本語原厂基础/扩展包 `resid16` 映射 |
| `FX6 string_english.uxc` | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | FX6 `XAVC Proxy` (`1920x1080(9M)` / `1280x720(6M)`) 与 Cloud 字符包 |
| `FX6 string_english_2.uxc` | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 `Simul Rec` 互斥、`User Menu Only`、`User Menu with Lock` 字符包 |

### 5.2 关键菜单项四语言 UXC `resid16` 校验矩阵（`实测事实`）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x734d` / `0x794a` | `Rec. Media Settings` | `摄像媒体设置` | `記憶卡槽錄製設定` | `記録メディア設定` | 活跃主菜单 |
| `_f` `0x749d` / `0x78be` | `Recording Media` | `摄像媒体` | `記憶卡錄製` | `記録メディア` | 活跃（Still/Movie 各自拆分） |
| `_f` `0x719e` | `Prioritize Rec. Media` | `优先摄像媒体` | `優先錄製插槽` | `優先記録メディア` | **休眠**（Ver. 2.00+ 已合并，ELF `0` 命中） |
| `_f` `0x7505` / `0x7916` | `Simult. Recording` / `Sort Recording` | `同时记录` / `分类记录` | `同步錄製` / `排序錄製` | `同時記録` / `振り分け` | 活跃（Movie 无 `Sort Recording`） |
| `_f` `0x6dd9` | `Auto Switch Media` | `自动切换摄像媒体` | `自動切換記憶卡錄製` | `記録ﾒﾃﾞｨｱ自動切換` | 活跃（`BKID_APP_setting_relay_rec`，**抗 Reset**） |
| `base` `0xe224` / `0xe228` | `CFexpress VPG400` / `CFexpress VPG200` + `Proxy Off` 提示 | `CFexpress VPG400/VPG200` + `Proxy关闭` | `CFexpress VPG400/VPG200` + `代理檔案關` | `CFexpress VPG400/VPG200` + `ﾌﾟﾛｷｼｰ切` | 活跃速率门禁告警 |
| `_f` `0x6e3f` / `0x6f19` | `Proxy Settings` / `Proxy Recording` | `Proxy设置` / `Proxy录制` | `代理檔案設定` / `代理檔案錄製` | `プロキシー設定` / `プロキシー記録` | 活跃（默认 `Off`） |
| `_f` `0x6662` / `0x61f0` / `0x7659` | `Proxy File Format` / `XAVC HS HD` / `XAVC S HD` | `Proxy文件格式` / `XAVC HS HD` / `XAVC S HD` | `代理檔案格式` / `XAVC HS HD` / `XAVC S HD` | `ﾌﾟﾛｷｼｰ記録方式` / `XAVC HS HD` / `XAVC S HD` | 活跃（默认 `XAVC S HD`） |
| `_f` `0x6aad` / `0x62a6` / `0x611c` / `0x764c` | `Proxy Rec. Settings` / `16M 4:2:0 10bit` / `9M 4:2:0 10bit` / `6M 4:2:0 8bit` | `Proxy记录设置` / `16M/9M 4:2:0 10bit` / `6M 4:2:0 8bit` | `代理檔案錄製設定` / 同左 | `ﾌﾟﾛｷｼｰ記録設定` / 同左 | 活跃（`0x6b8f 16M 8bit` 休眠） |
| `_f` `0x6e63` / `0x773e` / `_g 0x62b5` | `Cloud Connection` / `Cloud Information` / `Creators' Cloud` | `云连接` / `云信息` / `Creators' Cloud` | `雲連線` / `雲資訊` / `Creators' Cloud` | `クラウド接続` / `クラウド情報` / `Creators' Cloud` | 活跃（带 `*` 号，**抗 `[Initialize]`**） |
| `_f` `0x7c55` / `0x7c52` | `Connect to Cloud(Private)` / `(Share)` (*Creators' App for enterprise*) | `连接至云端(私有)` / `(共享)` | `連線至雲端(私有)` / `(共享)` | `クラウド(個人)` / `(共有)` | 活跃（C3 Portal 集成） |
| `_f` `0x6ab3` / `0x6833` / `_g 0x6498` | `Cnct. while Power OFF` / `Always Connected` | `关机时连接` / `始终连接` | `關閉電源時連線` / `永遠連線` | `電源OFF中の接続` / `常時接続` | 活跃（**物理关机保持 BLE 供电**；`_g 0x6476` SC/TC 为空） |
| `_g` `0x6232` / `_f` `0x64f6` | `My Menu` / `Display From My Menu` | `我的菜单` / `从我的菜单显示` | `我的選單` / `從我的選單顯示` | `マイメニュー` / `ﾏｲﾒﾆｭｰから表示` | 活跃（**实证 `6 × 7 = 42` 槽位**，抗 Reset） |
| `_f` `0x7122` / `0x7a11` / `0x698d` / `0x6b7c` / `0x6226` | `Add Item` / `Sort Item` / `Delete Item` / `Delete Page` / `Delete All` | `添加项目` / `排序项目` / `删除项目` / `删除页面` / `删除添加至我的菜单的全部项目。` | `新增項目` / `排序項目` / `刪除項目` / `刪除頁面` / `刪除新增至我的選單中的全部項目。` | `項目の追加` / `項目の並べ替え` / `項目の削除` / `ページの削除` / `マイメニューに追加した項目を全て削除します` | 活跃 My Menu 管理组 |
