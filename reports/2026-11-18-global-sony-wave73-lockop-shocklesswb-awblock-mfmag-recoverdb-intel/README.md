# 全球 Sony 实机情报 Wave 73（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Lock Operation Parts]` 与 `MENU+Fn` 5 秒全局锁定、`[Shockless WB]`/`[Priority Set in AWB]`/`[Shutter AWB Lock]` 与 `AWB Lock`、`[Focus Assistant]` 四子项与休眠 `[Focus Ring Rotate]` 辟谣，以及 `[Delete confirm.]`/`[Protect]`/`[Display Media Info.]`/`[Recover Image DB]` `AVF_INFO` 引导陷阱与 `Slot 1` `EROFS=30` 防火墙深度审计）

- **日期**：`2026-11-18`
- **任务 / 波次**：`H427` · **Global Sony Real-Hardware Empirical Intelligence Wave 73**（`73rd Wave`）
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **承接与互补声明**：
  - 本报告在 [Wave 34（Recover Image DB）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/reports/2026-11-15-global-sony-wave34-recover-imagedb-battery-vault-monitor-flip-playback-af-shift-sens-interval-intel/README.md)、[Wave 38（Lock Operation Parts）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/reports/2026-11-15-global-sony-wave38-lock-op-parts-menu-fn-5s-audio-out-timing-audio-signals-exp-step-shutter-angle-intel/README.md)、[Wave 45（Focus Assistant）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/reports/2026-11-15-global-sony-wave45-milestone-focus-magnifier-auto-mag-mf-area-datetime-video-light-hdmi-res-intel/README.md)、[Wave 46（Delete confirm.）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/reports/2026-11-17-global-sony-wave46-power-save-by-monitor-language-volume-delete-confirm-intel/README.md)、[Wave 47（Protect）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/reports/2026-11-17-global-sony-wave47-usb-connection-mode-hdmi-info-protect-reset-network-intel/README.md)、[Wave 48（White Balance）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/reports/2026-11-17-global-sony-wave48-picture-profile-scinetone-creative-look-dro-wb-metering-intel/README.md) 与 [Wave 56（Dial Customize）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/reports/2026-11-17-global-sony-wave56-dial-wheel-setup-mydial-fn-menu-liveview-lut-embed-intel/README.md) 的基础上，结合官方 `ILME-FX3` Help Guide（`ilc/2210`）、`ILME-FX6` Operating Instructions（`5-024-458-18` Ver. 6.0）以及本地 `os.O_RDONLY` 只读 donor 二进制取证，对四组关键操作安全与控制子系统进行跨机身纵深收口与若干重要纠偏（包括 `[Lock Operation Parts]` 真实一级路径纠偏、`[Shutter AWB Lock]` 选项字面与复位持久性纠偏、`[Initial Focus Mag.]` 全画幅 `x2.1`/`x4.1` 步进拆解、`[Focus Ring Rotate]` 休眠 UXC 辟谣、`[Protect]` 无全局 `Cancel All Images` 实证，以及 `FX6` `Key Lock` 休眠串 / `Warm Cool` 内部转换器 / `Restore Media` 提示串取证）。
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Lock Operation Parts / My Dial Settings / White Balance / Priority Set in AWB / Shockless WB / Shutter AWB Lock / Focus Magnifier / Auto Magnifier in MF / Initial Focus Mag. (still image / movie) / AF in Focus Mag. / Deleting multiple selected images (Delete) / Delete confirm. / Protecting recorded images (Protect) / Proxy Settings / Display Media Info. / Number of recordable images / Recover Image DB / Warning messages / List of default setting values*）
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *Technical > HOLD Switch Setting / Technical > Menu Settings (`User Menu Only`, `User Menu with Lock`) / Shooting > White / Shooting > White Setting (`ATW Speed`, `Shockless White`) / Shooting > Focus (`AF Assist`, `PUSH AUTO`, `Push AF/Push MF`) / Monitoring > Focus Magnifier (`Focus Mag Button Target`) / TC/Media (`Update Media`) / Thumbnail (`Lock/Unlock Clip`, `Delete Clip`)*）
  - 严格只读（`os.O_RDONLY`）本地 donor 二进制实证：[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so)、[`FX3 libmpr.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so)、[`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc)、[`FX3-CX95900_ALLLANG-Backup.bin`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin)、[`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) 与 [`FX6 string_english.uxc` / `_2.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc)
  - 仓内安全守卫交叉对照：[`G87` Recover Image DB 与 `Slot 1` 防火墙](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py)、[`G95` `[Lock Operation Parts]` 与 `MENU+Fn` 5s](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py)、[`G109` `[Focus Assistant]` 守卫](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)、[`G112` `[Delete confirm.]` 守卫](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_power_save_monitor_language_volume_delete_and_112gate_guard.py)、[`G114` `[Protect]` 守卫](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py) 与 [`G116` `[White Balance]` 守卫](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py)
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、SHA-256 账本、Reset/Initialize 持久性与官方 `ilc/2210` / `5-024-458-18` 条目）与 **`推断`**（Tier-0 `Slot 1` `EROFS=30` 防护逻辑与台架操作边界判断）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[Lock Operation Parts]`、`MENU+Fn` 5 秒全锁定 vs `ILME-FX6` 物理 `HOLD` / 菜单锁）**：
   - **实测事实（菜单路径纠偏与双层锁定机制）**：`ILME-FX3 Ver. 7.02` 中 `[Lock Operation Parts]` 位于 **`Setup -> [Dial Customize] -> [Lock Operation Parts]`**（**并非** `[Operation Customize]`，二者共享同一 `Setup` 图标组）；真实 4 项枚举为 **`Off`（默认）** / **`Multi-Selector Only`** / **`Dial + Wheel`** / **`All`**（`VAL_setting_device_lock_DEVICE_LOCK_{OFF,MULTISELECTOR,DIAL_WHEEL,ALL}`），Setup 归属使其 **`Not available` 于 `[Camera Settings Reset]`**（仅 `[Initialize]` 恢复 `Off`）。激活方式**不是 Custom Key**，而是**长按机身 `Fn` 键**至屏幕弹出 `"Locked."`（再长按 `Fn` 解锁；若 `[AF Area Registration] = On` 则被强制固定为 `Off`）。
   - **控制面覆盖与 Alpha 休眠对比**：`Fn` 长按仅按枚举锁定 `Multi-Selector`、前拨盘（Front Dial）、后拨盘（Rear Dial）与控制拨轮（Control Wheel），`My Dial 1..3` 召回时临时解锁；而**同时按住 `MENU + Fn` 5 秒**（`_g 0x610a`）会锁死**除 Shutter 快门键之外的所有物理按键、拨盘与拨轮**（再按住 5 秒解锁），触控则始终由独立的 `[Touch Operation]` 管控。FX3 机身**无**物理 `IRIS/ISO` 拨盘及硬件 `LOCK` 拨杆；`FX3 appFw.so` 与 `_f.uxc` 中残留的 `UIBIZ_SLIKEY_LOCK`、`MODEL_EVENT_FUNC_HARDWARE_LOCK`、`FUNC_toggle_{aperture,iso,shutter_speed}_manual_lock` 与 `_f 0x737b`（`Dial Lock`）/`0x7acd`（`Wheel Lock`）均为高端 Alpha 共享休眠符号。
   - **对比 `ILME-FX6 Ver. 6.01`**：采用**双物理 `HOLD` 拨杆**（机身侧边 REC 旁 + 顶部 Smart Handle，无 LCD 物理 `HOLD` 开关，触控由 `Technical > Touch Operation` 控制）+ **`Technical > HOLD Switch Setting`**（`with Rec Button`、`with Hand Grip Remote`、`Handle HOLD Switch: Normal / Rec Button Only`）+ **`Technical > Menu Settings`**（`User Menu Only` 长按 `MENU` 激活；`User Menu with Lock` 需同时长按 `Multi-Function Dial + MENU` 并支持 `0000`–`9999` 四位密码锁）。另外在 [`FX6 string_english.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc) 中保留有 `ns1 0x339d/0x33a1/0x33b2`（`<USER> + <MENU>` 1 秒 `Key Lock`）遗留串。

2. **子系统 2（`[Shockless WB]`、`[Priority Set in AWB]`、`[Shutter AWB Lock]` / `AWB Lock` vs `ILME-FX6` `WHT BAL` / `ATW 1..5`）**：
   - **实测事实（FX3 Ver. 7.02 三项 WB 控制与 Reset 分化）**：全部位于 **`Exposure/Color -> [White Balance]`** 下：
     - **`[Shockless WB]`**：`Off` / **`1 (Fast)`（默认）** / `2` / `3 (Slow)`（`MOVIE_SHOCKLESS_WB_{OFF,1,2,3}`），**仅 Movie / `S&Q` 有效**（Still 禁用），`Can be reset`。在录像切换 `[White Balance]` 预设或 `[Priority Set in AWB]` 时平滑过渡，**不影响 `[Auto]` / `[Underwater Auto]` 的自动跟踪速度**，且 `[C.Temp./Filter]` 与色温微调立即生效；在 `[Log Shooting] = Cine EI / Cine EI Quick` 下虽然禁用 `[Auto]`/`[Underwater Auto]`，但保留色温/预设切换行为。
     - **`[Priority Set in AWB]`**：**`Standard`（默认）** / **`Ambience`** / **`White`**，`Can be reset`。在 `Cine EI / Cine EI Quick` 下因 `[Auto]` 与 `[Underwater Auto]` 被禁用而无从生效（`Flexible ISO` 下正常可用）。
     - **`[Shutter AWB Lock]`**（**仅 Still 拍照有效！**）：`FX3 appFw.so` 与 `_f.uxc` 实测选项字面为 **`Shutter Half Press`**（`..._AWB_LOCK_W_S1`）、**`Cont. Shooting`**（`..._DURING_CONT_SHOOTING`）与 **`Off`（默认）**（`..._DO_NOT_LOCK_W_SHUTTER`），而非旧代简写 `"Shut. Halfway"`；且 `ilc/2210` 实证其 **`Not available` 于 `[Camera Settings Reset]`**（与同组另两项相反，仅 `[Initialize]` 归位 `Off`！）。视频录像中如需锁定 AWB，必须通过 Custom Key 指派 **`[AWB Lock Hold]`**（`_f 0x65f8`）或 **`[AWB Lock Toggle]`**（`_f 0x67cc`）。
   - **对比 `ILME-FX6 Ver. 6.01`**：采用机身物理三段 **`WHT BAL`（`B / A / PRESET`）拨杆** + `WHT BAL` 键（`Custom`: `3200K/4300K/5600K/6300K`；`Cine EI`: `3200K/4300K/5500K`）；`Shooting > White Setting` 提供 `White Switch <B>`（`Memory / ATW`）、**`ATW Speed`（`1..5`**, 1 最快，`Cine EI` 下禁用）、**`Shockless White`（`Off / 1 / 2 / 3`）** 及可指派 **`ATW`** / **`ATW Hold`**。`Shooting > White` 暴露 `Color Temp <A>/<B>`、`Tint <A>/<B>`、`R Gain <A>/<B>` 与 `B Gain <A>/<B>`（`-99.0..+99.0`）；二进制实证显示 `FX6 appFw.so` 内部通过 `diadem_pro_settings_converter` 将 `BKID_APP_SETTING_WARM_COOL_{A,B,ATW}` / `WARM_COOL_BALANCE_*` 映射为色温/偏移模型，而非在 `5-024-458-18` UI 直接显示 `"Warm Cool"` 菜单项。

3. **子系统 3（`[Focus Assistant]` 四子项、休眠 `[Focus Ring Rotate]` 辟谣 vs `ILME-FX6` `AF Assist` / `PUSH AUTO` / 放大倍率）**：
   - **实测事实（Reset 不可复位性与 Still/Movie 劈裂）**：`Shooting -> [Focus] -> [Focus Assistant]` 下全部放大辅助子项（`[Auto Magnifier in MF]`、`[Focus Magnif. Time]`、`[Initial Focus Mag.]`、`[AF in Focus Mag.]`）在 `Ver. 2.00..7.02` 中均 **`Not available` 于 `[Camera Settings Reset]`**（需 `[Initialize]` 才复位，不同于 `Ver. 1.x`）：
     - **`[Auto Magnifier in MF]`**：**`On`（默认）** / `Off`，**仅 Still（`MF`/`DMF`）可用**，Movie 与转接环下禁用；
     - **`[Focus Magnif. Time]`**：`2 Sec` / `5 Sec` / **`No Limit`（默认）**，Still & Movie 通用；
     - **`[Initial Focus Mag.]`**：**Still FF = `x1.0`（默认） / `x2.1`**（二次按中键才进入 `x4.1`；**`x4.1` 并非 Still 初始倍率选项**！）；**Still APS-C = `x1.0`（默认） / `x1.5`**（循环至 `x3.0`）；**Movie / `S&Q` = `x1.0`（默认） / `x4.0`**（`MOV_INIT_RATIO_FOCUS_MAGNIF_{X1_0,X4_0}`）；
     - **`[AF in Focus Mag.]`**：**`On`（默认）** / `Off`，**仅 Still 可用**（Movie、AF-C、PASM 以外的 AF-A、连拍及转接环均禁用）。
   - **休眠 `[Focus Ring Rotate]` 辟谣**：[`FX3 string_english_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc) 确含 `_f 0x7b28` `'Focus Ring Rotate'`（中/繁/日三语齐全），但 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中 `BKID_APP_setting_focus_ring_rotate`、`FOCUS_RING_ROTATE_*` 与线性/非线性 MF 响应枚举数**全为 `0`**，`ilc/2210` 亦**完全不存在**此菜单（对比 `FX6 appFw.so` 确编译有 `setting_focus_ring_rotate_t` 与 `FOCUS_RING_ROTATE_{LEFT_F_RIGHT_N,RIGHT_F_LEFT_N}`）。
   - **对比 `ILME-FX6 Ver. 6.01`**：`Shooting > Focus > AF Assist`（`On/Off`）允许在 AF 期间转动对焦环临时人工微调（失焦/切 MF/启动追踪或按 `Push AF/Push MF` 退出）；配备独立物理 **`PUSH AUTO`**（或指派 `Push AF/Push MF` + `Push AF Mode`）；放大倍率在 VF/LCD 为 **`×3 / ×6`**（默认可指派 `ASSIGN 4`/`7`，且支持录影中保持放大），**Ver. 6.0+ 新增 `Monitoring > Focus Magnifier > Focus Mag Button Target` 支持 `HDMI Focus Mag ×2 / ×4`**。

4. **子系统 4（`[Delete]` / `[Delete confirm.]`、`[Protect]`、`[Display Media Info.]`、`[Recover Image DB]` `AVF_INFO` 陷阱 vs `Slot 1` `EROFS=30` & `FX6`）**：
   - **实测事实（FX3 Playback 持久化、Proxy 强绑定与 `AVF_INFO` 扇区写风险）**：
     - **`[Delete]` & `[Delete confirm.]`**：`Playback -> [Delete] -> [Delete]` 含 5 项批量模式（`All Other Than This Img.`、`All Images in This Group`、`Multiple Img.`、`All in this Folder`、`All with this date`）；`[Delete confirm.]` 默认 **`"Cancel" first`**（vs `"Delete" first`），配合 `[Delete pressing twice]`（默认 `Off`）。受保护影像不可被 `[Delete]` 删除（仅 `[Format]` 可清除）。Playback 菜单项**全部不受 `[Camera Settings Reset]` 影响**（需 `[Initialize]` 复位）。
     - **`[Protect]`**：`Playback -> [Selection/Memo] -> [Protect]` 含 7 项（`Multiple Img.`、`All in this Folder`、`Cancel All in this Folder`、`All with this date`、`Cancel All with this date`、`All Images in This Group`、`Cancel All in This Group`），**不存在**全局 `"Cancel All Images"` 选项。含 Proxy 视频时，**删除或保护操作同时作用于原片与 `*S03.MP4` 代理文件**，不可单独操作其一；`[Copy]` 会剥离保护标记。
     - **`[Display Media Info.]`**：只读（`Playback`/`Shooting -> [Media]`），显示卡内剩余可拍张数与可录时长（机内总张数上限 `40 000`，实时取景上限显示 `9999`）。
     - **`[Recover Image DB]`**：`Shooting -> [Media] -> [Recover Image DB]`（选 Slot 1/2 执行，**双免疫**于 `[Camera Settings Reset]` 与 `[Initialize]`），在电量充足前提下对 `/AVF_INFO` 下的 **`AVIN0001.INP` / `AVIN0001.BNP` / `AVIN0001.INT`**（[`FX3 libmpr.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so) 实证）执行**不删原片**的索引修复，同时会重置 FTP/传输结果信息（`_g 0x63b7` / `base 0xea13`）。
   - **推断（`Slot 1` Tier-0 恢复金库开机/插卡自动提示陷阱与 `EROFS=30` 防火墙）**：非相机写入或插卡校验不一致时，FX3 在 `base 0xe836 / 0xea12 / 0xea23 / 0xea24` 会在屏幕直接弹窗提示 `Preparing Image Database File` / `Image Database File error. Recover?` / `Create?`——一旦用户在台架 `Slot 1` 插入未经离线 SHA-256 校验的金卡时误按确认，将直接改写 `AVF_INFO` 扇区并销毁金卡镜像一致性！因此必须强制执行 [`G87`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py) / `Slot 1` **`EROFS=30` 只读防火墙**。
   - **对比 `ILME-FX6 Ver. 6.01`**：采用 `XDROOT` 目录树（`MEDIAPRO.XML`），菜单仅暴露 **`TC/Media > Update Media`（`Media(A)/(B)`）** 手动刷新管理文件；而 **`Media Needs to be Restored -> Restore Media(A)/(B)`**（`fx6_ns1 0x2691..0x2699`, `fx6_ns2 0x40db..0x40dd`）在 FX6 固件中作为挂载异常自动弹窗与防写保护检测存在（遇到物理 WP 锁会拒绝恢复并提示 `"Please Unprotect and Reinsert Media"`）；缩略图锁档使用 **`Thumbnail > Clip > Lock/Unlock Clip`**。

---

## 1. 子系统 1：`[Lock Operation Parts]` 与 `MENU+Fn` 5s 全局锁定 vs `ILME-FX6` 物理 `HOLD` / 菜单锁

### 1.1 `ILME-FX3 Ver. 7.02` 双层锁定架构与真值边界（`实测事实`）

> [!IMPORTANT]
> **菜单一级路径纠偏（`实测事实`）**：虽然早期口头常将按键与拨盘锁定并归于 `[Operation Customize]`，但在 Sony `ILME-FX3 Ver. 7.02` 官方 Help Guide（`ilc/2210` *Lock Operation Parts*）及本地实机菜单树中，`[Lock Operation Parts]` 的唯一精确路径是 **`MENU -> (Setup) -> [Dial Customize] -> [Lock Operation Parts]`**（与 `[Operation Customize]` 同处 Setup 组）。

1. **枚举真值、默认状态与激活机制（`ilc/2210` + `FX3 appFw.so` + `_f.uxc`）**：
   - **ELF 参数与枚举**：[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中对应 `BKID_APP_setting_device_lock`（`PRM_setting_device_lock`），其仅有的 4 个运行态枚举值为：
     - **`Off`**（**默认**，`VAL_setting_device_lock_DEVICE_LOCK_OFF`）：长按 `Fn` 不锁定任何控件；
     - **`Multi-Selector Only`**（`DEVICE_LOCK_MULTISELECTOR`，`_f 0x686b`）：仅锁定机身背面的多功能选择器（摇杆）；
     - **`Dial + Wheel`**（`DEVICE_LOCK_DIAL_WHEEL`，`_f 0x61bb`）：锁定前拨盘（Front Dial）、后拨盘（Rear Dial）与控制拨轮（Control Wheel）；
     - **`All`**（`DEVICE_LOCK_ALL`，`_f 0x75a8`）：同时锁定上述全部 4 个部件（多功能选择器 + 前拨盘 + 后拨盘 + 控制拨轮）。
   - **激活 / 解除方式（`Fn` 长按 vs 非 Custom Key）**：`[Lock Operation Parts]` **不是**可分配给 `Custom Key` 的功能；它固定绑定 **`Fn`（Function）键长按**——当配置为非 `Off` 时，长按 `Fn` 直至监视器显示 **`"Locked."`**（`base 0xe354`）即激活锁定，再次长按 `Fn` 解锁。
   - **重要互斥与临时解锁边界**：
     - **与 `[AF Area Registration]` 互斥**：当 `Focus -> [AF/MF] -> [AF Area Registration]` 设为 `On` 时，`[Lock Operation Parts]` 被强制固定为 **`Off`**（因两者冲突占用 `Fn` 长按交互）。
     - **与 `My Dial` 的临时穿透**：即使拨盘/拨轮已处于 `[Lock Operation Parts]` 锁定状态，通过自定义按键召回 **`My Dial 1 / 2 / 3`** 期间，已指派功能的拨盘/拨轮会**临时解锁**（*My Dial Settings*），退出 `My Dial` 后恢复锁定。
   - **Reset 持久性**：因位于 `Setup` 分支，**`Not available` 于 `[Camera Settings Reset]`**，仅执行 `[Initialize]` 后恢复为 `Off`。

2. **两级锁定控制面矩阵与 Alpha 休眠锁定符号拆解（`实测事实`）**：

| 控制部件 / 按键 | 方式 A：`Fn` 键长按（依 `[Lock Operation Parts]` 设置） | 方式 B：`MENU + Fn` 同时长按 **5 秒**（`_g 0x610a`） | 底层机制与硬件事实核查（`实测事实`） |
| :--- | :---: | :---: | :--- |
| **Multi-Selector（多功能选择器）** | `Multi-Selector Only` / `All` 时**锁定** | **锁定** | 由 `BKID_APP_setting_device_lock` 策略分发 |
| **Front Dial / Rear Dial（前/后拨盘）** | `Dial + Wheel` / `All` 时**锁定** | **锁定** | `My Dial` 召回期间可临时解锁方式 A |
| **Control Wheel（控制拨轮）** | `Dial + Wheel` / `All` 时**锁定** | **锁定** | 含拨轮旋转及方向点按 |
| **专用物理 `IRIS` / `ISO` 拨盘** | *（FX3 机身无此物理硬件）* | *（FX3 机身无此物理硬件）* | FX3 机身无独立物理 `IRIS` 环拨盘或专用曝光补偿/ISO 实体转盘 |
| **`MOVIE` 录像键与其他自定义键** | **保持活跃可用** | **全部锁定** | `ilc/2210` 明确方式 B 锁定除 Shutter 键外的**所有按键、拨盘与拨轮**；解锁需按住 `MENU` 的同时长按 `Fn` 5 秒（`_g 0x610a`） |
| **快门键（`SHUTTER`）** | **保持活跃可用** | **保持活跃可用（唯一例外）** | `ilc/2210` 明确：*all buttons, dials, and wheels (except the shutter button)* |
| **LCD 触摸屏操作（Touch）** | **保持独立（由 `[Touch Operation]` 控制）** | **保持独立（不归 `[Lock Operation Parts]` 管辖）** | 触摸启停严格由 `Setup -> [Touch Operation]`（`On / On: Playback Only / Off`）单独管控 |

> [!NOTE]
> **休眠 Alpha 平台锁 Symbols 核验（`实测事实`）**：[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中编译保留了多组共享 Alpha 平台硬件锁符号，在无物理锁开关的 `ILME-FX3`（`ALCIN_UUD`）上均属**休眠死代码**：
> - `UIBIZ_SLIKEY_LOCK` / `UIBIZ_SLIKEY_LOCK_2ND` 与 `VAL_hardware_lock_state_HARDWARE_LOCK_STATE_{LOCKED,UNLOCKED}`、`process_MODEL_EVENT_FUNC_HARDWARE_LOCK`（对应带实体 `LOCK` 滑块开关的高端机身，如 A7S III / A1 等的拨盘锁按钮）；
> - `FUNC_toggle_{aperture,shutter_speed,iso}_manual_lock`（`PRM_{aperture,shutter_speed,iso}_manual_lock_state`，用于带锁定式 M 档拨盘的电影/旗舰机）；
> - `_f 0x737b`（`Dial Lock`）与 `_f 0x7acd`（`Wheel Lock`）、`base 0xe352`（`Dial / Wheel Lock`）在 FX3 上合并收编为统一 `[Lock Operation Parts]` 四选项。

### 1.2 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 锁定架构横向对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 ELF`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 ELF/UXC`） |
| :--- | :--- | :--- |
| **物理 `HOLD` 开关数量与位置** | **0 个物理 `HOLD` 开关**（仅电源拨杆与软件按键组合） | **2 个物理 `HOLD` 开关**：<br>1. **机身侧边 `HOLD` 开关**（紧邻侧边 `REC` 键）<br>2. **顶部 Smart Handle `HOLD` 开关**（含 Handle REC / 变焦推杆）<br>*(注：FX6 LCD 监视器本身**无**物理 `HOLD` 开关，触控启停走 `Technical > Touch Operation`)* |
| **菜单锁定精细粒度配置** | `Setup -> [Dial Customize] -> [Lock Operation Parts]`（`Off` / `Multi-Selector Only` / `Dial + Wheel` / `All`） | **`Technical > HOLD Switch Setting`**（`FX6 appFw.so` `BKID_APP_SETTING_HOLD_SWITCH_SETTING_*`）：<br>• **`with Rec Button`**（`On / Off`）：决定机身 `HOLD` 拨动时是否一并锁定 `REC` 键<br>• **`with Hand Grip Remote`**（`On / Off`）：决定是否一并锁定制动握把遥控手柄按键<br>• **`Handle HOLD Switch`**（`Normal` / `Rec Button Only`）：设为 `Rec Button Only` 时，即便手柄 `HOLD` 拨上，仍仅锁手柄 `REC` 键而放行变焦拨杆 |
| **菜单访问与参数锁定（Kiosk / 租借锁）** | 无四位密码菜单锁，仅全机按键锁（`MENU+Fn` 5 秒） | **`Technical > Menu Settings`**（`FX6 appFw.so` + `fx6_ns2`）：<br>• **`User Menu Only`**（`On / Off`，`fx6_ns2 0x4ee2`）：长按 `MENU` 仅显示 User Menu 精简表并禁止在状态屏改参<br>• **`User Menu with Lock`**（`On / Off`，`fx6_ns2 0x55f3`）：**同时长按 `Multi-Function Dial + MENU`** 激活并需要 **4 位数字密码**（`0000`–`9999`，默认 `0000`，`BKID_APP_USER_MENU_WITH_LOCK_PASSCODE`）解锁完整菜单 |
| **遗留休眠按键锁串** | `UIBIZ_SLIKEY_LOCK` 等（休眠） | `fx6_ns1 0x339d`（`Key Lock`）、`0x33a1` / `0x33b2`（`<USER> + <MENU>` 长按 1 秒锁键提示）与 `EVENT_REMOTE_BODY_KEY_LOCK_STATUS`（继承自 PXW/FS 系列 UI 框架；`5-024-458-18` 以双物理 `HOLD` + `User Menu Only / with Lock` 为主） |

---

## 2. 子系统 2：`[Shockless WB]`、`[Priority Set in AWB]`、`[Shutter AWB Lock]` 与 `AWB Lock` vs `ILME-FX6` `WHT BAL` / `ATW`

### 2.1 `ILME-FX3 Ver. 7.02` 曝光/色彩白平衡子项全剖析（`实测事实`）

以下三项均位于 **`MENU -> (Exposure/Color) -> [White Balance]`** 下（与主项 `[White Balance]` 处同一一级分支，参见 [Wave 48 报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/reports/2026-11-17-global-sony-wave48-picture-profile-scinetone-creative-look-dro-wb-metering-intel/README.md)）：

| 子项名称 | `FX3 Ver. 7.02` 精确枚举与出厂默认（`ilc/2210` + `FX3 appFw.so`） | 适用模式与互斥锁定条件（`实测事实`） | `[Camera Settings Reset]` | UXC `resid16` / ELF 符号实证 |
| :--- | :--- | :--- | :---: | :--- |
| **`[Shockless WB]`** | • `Off`<br>• **`1 (Fast)`（默认）**<br>• `2`<br>• `3 (Slow)` | • **仅 Movie 与 `S&Q` 有效**（Still 模式灰显不可用）<br>• 平滑录影中切换 `[White Balance]` 预设或切换 `[Priority Set in AWB]` 时的色温过渡<br>• **不改变 `[Auto]` / `[Underwater Auto]` 自动追踪本身的速度**<br>• `[C.Temp./Filter]` 色温调整及微调坐标（A-B/G-M）**立即生效，不受平滑速度延迟**<br>• `Cine EI / Cine EI Quick` 下禁用 AWB（`[Auto]`/`[Underwater Auto]` 锁死），但各固定色温预设间切换仍可应用 | **`Can be reset`** *(复位为 `1 (Fast)`)* | `_f 0x62fe`, `_f 0x6649`, `_f 0x6ef1`, `_f 0x785f`；`BKID_APP_setting_movie_shockless_wb`、`MOVIE_SHOCKLESS_WB_{OFF,1,2,3}`、`set_wb_change_speed_i` |
| **`[Priority Set in AWB]`** | • **`Standard`（默认）**<br>• `Ambience`<br>• `White` | • 仅在 `[White Balance] = [Auto]` 时生效（分别在屏幕上显示为 `AWB` / `AWB A` / `AWB W`）<br>• 在 **`[Log Shooting] = [Cine EI]` 或 `[Cine EI Quick]`** 时，因 `[Auto]` 与 `[Underwater Auto]` 被强制禁用，此项虽属 `Exposure/Color` 组但在实拍中**无效果/不可调**；在 **`[Flexible ISO]`** 下 `[Auto]` 可用故本项正常生效 | **`Can be reset`** *(复位为 `Standard`)* | `_f 0x67a7`, `_f 0x6748`, `_f 0x609c`, `_f 0x749f`, `base 0xe651`/`0xe883`；`BKID_APP_setting_priority_set_in_awb`、`PRIORITY_SET_IN_AWB_{STANDARD,AMBIENCE,WHITE}` |
| **`[Shutter AWB Lock]`** | • `Shutter Half Press`<br>• `Cont. Shooting`<br>• **`Off`（默认）** | • **仅 Still 拍照模式有效！（Movie / `S&Q` 完全不适用）**<br>• 仅当 `[White Balance]` 为 `[Auto]` 或 `[Underwater Auto]` 时起效：<br>  - `Shutter Half Press`：半按快门及连拍期间锁定白平衡<br>  - `Cont. Shooting`：仅连拍第一张锁定并保持至连拍结束<br>• 使用外接闪光灯时锁定 AWB 会导致色偏，官方建议设 `Off` / `Cont. Shooting` 或切至 `[Flash]` | **`Not available`** *(实证抗常规 Reset！仅 `[Initialize]` 恢复 `Off`)* | `_f 0x66db` / `0x6ace`、`_f 0x6373`（`Shutter Half Press`）、`_f 0x6a32`（`Cont. Shooting`）；`BKID_APP_setting_stl_awb_lock_with_shutter`、`STL_AWB_LOCK_WITH_SHUTTER_{AWB_LOCK_W_S1,DURING_CONT_SHOOTING,DO_NOT_LOCK_W_SHUTTER}` |

> [!WARNING]
> **两项关键实证纠偏（`实测事实`）**：
> 1. **字面纠偏**：`FX3 Ver. 7.02` 中 `[Shutter AWB Lock]` 的官方菜单选项是 **`Shutter Half Press`** 与 **`Cont. Shooting`**，而非旧 Alpha 文档曾用的 `"Shut. Halfway"` / `"Cont."` 缩写。
> 2. **Reset 持久性劈裂**：尽管同在 `[White Balance]` 分组下，**`[Shockless WB]` 与 `[Priority Set in AWB]` 属于 `Can be reset`**，但 **`[Shutter AWB Lock]` 在 `ilc/2210` *List of default setting values* 中明确标注为 `Not available`（耐受 `[Camera Settings Reset]`）**，台架恢复标准白平衡基线时不可假设复位一次就能清零 `[Shutter AWB Lock]`。
> 3. **电影模式唯一的 AWB 锁定途径（`Custom Key` `AWB Lock`）**：因 `[Shutter AWB Lock]` 仅限 Still（`stl_awb_lock_with_shutter`），在 **Movie 拍摄**中使用 `[Auto]` WB（例如 `Flexible ISO` 下记录）且需要在运镜过场中锁定当前色温时，唯一途径是通过 `Setup -> [Operation Customize] -> [Custom Key Setting]` 指派 **`[AWB Lock Hold]`**（`_f 0x65f8`）或 **`[AWB Lock Toggle]`**（`_f 0x67cc`）（`FX3 appFw.so`: `PRM_hold_awb_lock_state`、`PRM_toggle_awb_lock_state`、`set_awblock_i`）。

### 2.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 白平衡控制与 `Warm Cool` 内部映射对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 ELF`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 ELF/UXC`） |
| :--- | :--- | :--- |
| **物理切换硬件与记忆槽** | 无物理 `WHT BAL` 三段拨杆；菜单内 `Custom 1 / 2 / 3` + 10 组固定预设 + `C.Temp./Filter`（`2500K..9900K`） | 机身左侧物理三段 **`WHT BAL` 开关（`B / A / PRESET`）** + 前置 **`WHT BAL` 触发键**：<br>• `PRESET`：快速拨盘 `100K` 步进或菜单 `Preset White Select`（`Custom`: `3200K/4300K/5600K/6300K`；`Cine EI`: `3200K/4300K/5500K`）<br>• `A / B`：独立白平衡记忆库（支持一键 WB 采样保存） |
| **自动白平衡与平滑控制** | `[White Balance] = Auto` + `[Priority Set in AWB]`（`Standard/Ambience/White`）+ `[Shockless WB]`（`Off / 1 / 2 / 3`，**不作用于 AWB 追踪速度**）+ Custom Key `AWB Lock Hold/Toggle` | `Shooting > White Setting`：<br>• **`White Switch <B>`**：`Memory` / **`ATW`**（将物理 `B` 档切换为自动追踪白平衡）<br>• **`ATW Speed`**：**`1..5`**（`1` 最快，`5` 最慢；`Cine EI` 模式下不可用）<br>• **`Shockless White`**：**`Off / 1 / 2 / 3`**（`fx6_ns2 0x4404`，对应 `extern_BKID_APP_EXTERN_WHITESHOCKLESSWHITE()`）<br>• 可指派键：**`ATW`** 与 **`ATW Hold`**（暂停自动追踪） |
| **通道增益、微调与 `Warm Cool` 实证** | 统一二维微调盘：`A-B`（琥珀-蓝）与 `G-M`（绿-品红），各 `±7` 步（无直接 `R/B Gain` 单独菜单项） | `Shooting > White` 暴露工程级调节：<br>• **`Color Temp <A>/<B>`**：`2000K..15000K`（默认 `3200K`）与 `Offset Color Temp<ATW>`<br>• **`Tint <A>/<B>`**：`-99..+99`（默认 `±0`）与 `Offset Tint<ATW>`<br>• **`R Gain <A>/<B>/<P>` & `B Gain <A>/<B>/<P>`**：`-99.0..+99.0`（默认 `±0.0`，`fx6_ns2 0x4e22..0x4e2d`）<br>• **二进制底层实证**：`FX6 appFw.so` 包含 `diadem_pro_settings_converter::load_setting_warm_cool_{a,b}` 与 `BKID_APP_SETTING_WARM_COOL_{A,B,ATW}` / `WARM_COOL_BALANCE_*`（`fx6_ns2 0x4e0e..0x4f4b`），在 Procam `diadem_pro` 层将 Warm-Cool / Balance 内部坐标换算为 UI 侧的色温与 Tint 偏移（`5-024-458-18` 正文菜单以 `Color Temp` / `Tint` / `R Gain` / `B Gain` 呈现） |

---

## 3. 子系统 3：`[Focus Assistant]` 四子项、休眠 `[Focus Ring Rotate]` 辟谣 vs `ILME-FX6` `AF Assist` / `PUSH AUTO`

### 3.1 `ILME-FX3 Ver. 7.02` `[Focus Assistant]` 五项全真值与 Still/Movie 劈裂（`实测事实`）

`MENU -> (Focus) -> [Focus Assistant]` 下与放大对焦直接相关的全部项在 `ILME-FX3 Ver. 7.02` 中的精确边界如下（承接并细化 [Wave 45 报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/reports/2026-11-15-global-sony-wave45-milestone-focus-magnifier-auto-mag-mf-area-datetime-video-light-hdmi-res-intel/README.md)）：

| 菜单项 | `FX3 Ver. 7.02` 精确枚举与默认 | Still vs Movie / `S&Q` 可用性与步进真相 | `[Camera Settings Reset]` | UXC `resid16` & `FX3 appFw.so` 实证（`实测事实`） |
| :--- | :--- | :--- | :---: | :--- |
| **`[Focus Magnifier]`** | 执行命令（非持久开关） | Still & Movie 通用；中心键放大/切倍率，十字键挪动放大框；**可通过 Custom Key（原出厂默认如 `Custom Button 5` 等）或触屏双击一键触发** | *（动作项不适用）* | `base 0xe226`/`0xe6a9`；`VAL_focus_magnification_mode_FOCUS_MAGNIFICATION_MODE_{OFF,ON_MAG0,ON_MAG1,ON_MAG2,ON_AUTO}` |
| **`[Auto Magnifier in MF]`** | • **`On`（默认）**<br>• `Off` | • **仅 Still（`MF` 或 `DMF`）可用**：转动对焦环自动弹出放大框<br>• **Movie / `S&Q` 与使用 Mount Adaptor（卡口适配器）时完全禁用**（需手动触发 `[Focus Magnifier]`） | **`Not available`** *(Ver. 2.00+ 不随常规 Reset 复位！)* | `_f 0x7110`；`BKID_APP_setting_mf_assist`、`VAL_setting_mf_assist_MF_ASSIST_{ON,OFF}` |
| **`[Focus Magnif. Time]`** | • `2 Sec`<br>• `5 Sec`<br>• **`No Limit`（默认）** | • Still 与 Movie 均独立/同步提供该三档；`No Limit` 下保持放大直至半按快门（`Still`）或再次取消 | **`Not available`** *(需 `[Initialize]` 复位)* | `_f 0x692c` / `0x7b1c`、`base 0xe207`/`0xe208`、`_f 0x6b66`；`BKID_APP_setting_focus_magnification_time`、`..._time_still` |
| **`[Initial Focus Mag.]`** | • Still 全画幅：**`x1.0`（默认）** / **`x2.1`**<br>• Still APS-C：**`x1.0`（默认）** / **`x1.5`**<br>• Movie / `S&Q`：**`x1.0`（默认）** / **`x4.0`** | **关键拆解**：<br>• Still 全画幅初始仅可选 **`x1.0`** 或 **`x2.1`**（再次按中心键才切换到二级倍率 **`x4.1`**，即 `x1.0 -> x2.1 -> x4.1`；**`x4.1` 并非 `[Initial Focus Mag.]` 的菜单选项**！）<br>• Still APS-C：`x1.0 -> x1.5 -> x3.0`<br>• Movie / `S&Q`：初始即支持直跳 **`x4.0`**（`MOV_INIT_RATIO_FOCUS_MAGNIF_{X1_0,X4_0}`） | **`Not available`** *(需 `[Initialize]` 复位)* | `_f 0x72ae`/`0x77ad`/`0x7b25`、`_f 0x7a8b`/`0x6558`/`0x7a8f`/`0x691d`；`BKID_APP_setting_{stl,mov}_init_ratio_focus_magnif` *(注：ELF 含休眠高像素枚举 `x1.6/2.7/3.1/3.6/3.7/4.2/4.7/5.3/5.5/6.1`，FX3 12MP 仅取 `x2.1`/`x1.5`/`x4.0`)* |
| **`[AF in Focus Mag.]`** | • **`On`（默认）**<br>• `Off` | • **仅 Still 可用**：设为 `On` 时，放大期间半按快门可在放大区域精确对焦；设为 `Off` 则半按快门退出放大<br>• **在 Movie、`AF-C`、PASM 以外的 `AF-A`、连拍及 Mount Adaptor 下禁用** | **`Not available`** *(需 `[Initialize]` 复位)* | `_f 0x72e0`；`BKID_APP_setting_stl_af_in_focus_mag`、`VAL_setting_stl_af_in_focus_mag_STL_AF_IN_FOCUS_MAG_{ON,OFF}` |

> [!CAUTION]
> **休眠 `[Focus Ring Rotate]` / 线性对焦响应辟谣（`实测事实`）**：
> 1. 社区常有人猜测 FX3 菜单包含可切换 `Clockwise / Counterclockwise` 或 `Linear / Non-Linear` 的 `[Focus Ring Rotate]`（类似 A7 IV / A7R V / A1）。经本地双边只读取证：
>    - [`FX3 string_english_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc) 确实因多机共用 UI 字符串包而携带 `_f 0x7b28` **`Focus Ring Rotate`**（中 `对焦环旋转` / 繁 `對焦環旋轉` / 日 `ﾌｫｰｶｽﾘﾝｸﾞ操作方向`）及 `_f 0x7b2c` **`Previous Mag.`**；
>    - 但在 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中搜索 `focus_ring_rotate` / `LINEAR_MF` / `FocusRingRotate`，**命中数严格为 `0`**（仅有底层的 `UIBIZ_KEY_LENS_FOCUS_RING` 与 `MODEL_FOCUS_RING_OPE_{START,END}` 硬件事件，无任何旋转方向或线性响应设置 `BKID_APP_*`）；官方 `ilc/2210` 亦**完全未提供 `[Focus Ring Rotate]`**。
>    - 反观 [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) 则真实编译有 `N5model27setting_focus_ring_rotate_tE` 与 `FOCUS_RING_ROTATE_{LEFT_F_RIGHT_N,RIGHT_F_LEFT_N}`。

### 3.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 手动辅助对焦与放大控制对照（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 ELF/UXC`） |
| :--- | :--- | :--- |
| **AF 中手拧对焦环接管（`AF Assist`）** | `Focus -> [AF/MF] -> [AF Assist]`（`On / Off`，默认 `Off`）：Movie 下转动对焦环临时接管焦点，停止转动后切回 AF | **`Shooting > Focus > AF Assist`**（`On / Off`，`VAL_setting_af_assist_AF_ASSIST_{ON,OFF}`）：AF 期间扭动对焦环强制转移对焦位置；当目标移出画面、切 MF、开启追踪 AF 或按 **`Push AF/Push MF`** 时终止 AF Assist 状态 |
| **物理一键对焦 / AF-MF 切换键** | 无专用标注 `PUSH AUTO` 实体键；依赖自定义键（`AF On` / `AF/MF Ctrl Hold/Toggle`） | 机身手柄前/侧配有专用 **`PUSH AUTO`**（或 `PUSH AUTO FOCUS`）硬按键及 **`AUTO/MAN`** 开关；可选 `Push AF/Push MF` 与 `Push AF Mode`（`AF` / `Single-shot AF(AF-S)`） |
| **放大对焦倍率与 HDMI 分离（Ver. 6.0+）** | 固定 **Clean HDMI 隔离**：放大框仅在机身 LCD 显示（不随 Clean HDMI 输出）；Movie 初始 `x1.0 / x4.0`（无双路独立倍率切换） | • VF/LCD 放大：**`×3` / `×6`**（`fx6_ns1 0x2fb7/0x2fcf/0x2fc5`，`VF Focus Mag ×3/×6`；支持 `CONTINUE_FOCUS_MAGNIFIER` 在 `REC` 中持续放大）<br>• **Ver. 6.0+ 新增 `Monitoring > Focus Magnifier > Focus Mag Button Target`**：可将放大按键目标切换至外接输出 **`HDMI Focus Mag ×2 / ×4`**（`fx6_ns1 0x2fcc/0x2fd1`、`FOCUS_MAG_BUTTON_TARGET_{LCD_MONITOR,OUTPUT}`） |

---

## 4. 子系统 4：`[Delete]` / `[Delete confirm.]`、`[Protect]`、`[Display Media Info.]` 与 `[Recover Image DB]` `AVF_INFO` 陷阱 vs `Slot 1` `EROFS=30`

### 4.1 `ILME-FX3 Ver. 7.02` 回放删护与媒体诊断体系（`实测事实`）

| 菜单项（`ilc/2210` 精确路径） | 真实全量选项与默认（`实测事实`） | Proxy 耦合、受保护约束与 Reset 持久性 | UXC `resid16` / ELF 实证 |
| :--- | :--- | :--- | :--- |
| **`Playback -> [Delete] -> [Delete]`** | 5 种批量删除作用域：<br>1. `All Other Than This Img.`<br>2. `All Images in This Group`<br>3. `Multiple Img.`<br>4. `All in this Folder`<br>5. `All with this date` | • **Proxy 强耦合**：删除含 Proxy 的电影时，**同时删除原片与 `*S03.MP4` 代理文件**（无法单独删其一）<br>• **保护约束**：已保护文件**无法被 `[Delete]` 删除**（仅 `[Format]` 可强制全盘清除） | `base 0xe7f3` / `0xe826` / `0xe2ca`；`DELETE_ALL_{BUT_THIS_IMAGE,IN_THIS_GROUP,IN_THIS_FOLDER,WITH_THIS_DATE}` |
| **`Playback -> [Delete] -> [Delete confirm.]`** | • **`"Cancel" first`（默认）**<br>• `"Delete" first` | • 另有 `[Delete pressing twice]`（默认 `Off` / `On`）控制单键连按删除<br>• **Reset 行为**：Playback 分类**不受 `[Camera Settings Reset]` 影响**，需 `[Initialize]` 复位 | `base 0xe721` / `0xe724` / `0xe725`、`_f 0x6a5e` / `0x6e0a` / `0x74db`；`BKID_APP_setting_delete_confirm`、`BKID_APP_setting_delete_by_delete_twice` |
| **`Playback -> [Selection/Memo] -> [Protect]`** | **精确 7 项**（依 `[View Mode]` 变化）：<br>1. `Multiple Img.`<br>2. `All in this Folder`<br>3. `Cancel All in this Folder`<br>4. `All with this date`<br>5. `Cancel All with this date`<br>6. `All Images in This Group`<br>7. `Cancel All in This Group` | • **纠偏实证**：**不存在 `"Cancel All Images"` 全卡一键取消选项**<br>• **Proxy 强耦合**：保护/取消保护时**同步作用于原片与 Proxy**（无法单保其一）；`[Copy]` 复制出的副本不继承保护标记<br>• 可通过 Custom Key 指派单按保护（`_g 0x6362`/`0x6133`） | `base 0xe2c9`/`0xe2ca`/`0xe553`/`0xe826`、`_f 0x6848`/`0x72d9`/`0x69f7`/`0x7339`；`VAL_launch_protect_*` |
| **`Shooting/Playback -> [Media] -> [Display Media Info.]`** | 选 Slot 1 / Slot 2 查看（纯只读查询） | • 显示对应卡槽的**剩余可拍静态张数**与**剩余可录动态时长**<br>• **40 000 张物理上限**：每张卡最多记录 `40 000` 张静态照片（机内实时取景余量最高显示 `9999`） | `base 0xea2a`、`_f 0x6a98`；`VAL_media_info_displaying_state_MEDIA_INFO_DISPLAYING_STATE_DISPLAYING` |
| **`Shooting -> [Media] -> [Recover Image DB]`** | 选 Slot 1 / Slot 2 执行重建修复（非持久参数，动作项） | • **不删除原片**，仅重建/修复媒体数据库索引（`AVF_INFO`）<br>• **双免疫**：**不受 `[Camera Settings Reset]` 与 `[Initialize]` 重置**<br>• **副作用**：会清除/重置 FTP 传输结果状态（`_g 0x63b7` / `base 0xea13`）；电量极低时直接拒绝执行 | `base 0xe918` / `0xea12` / `0xea13` / `0xea23` / `0xea24`、`_f 0x711b`、`_g 0x63b7`；`SYSTEM_MODE_OPTION_RECOVER_DB`、`start_recover_db` |

### 4.2 `[Recover Image DB]` `AVF_INFO` 自动弹窗陷阱与 Tier-0 `Slot 1` `EROFS=30` 防火墙（`实测事实` + `推断`）

1. **数据库落盘实体实证（`实测事实`）**：
   - 经对 [`FX3 libmpr.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so) 只读扫描，Sony α/FX3 媒体数据库在卡根目录维护 **`/AVF_INFO`** 文件夹及三大核心文件：**`AVIN0001.INP`**、**`AVIN0001.BNP`** 与 **`AVIN0001.INT`**（同时视频目录配合 `/M4ROOT/MEDIAPRO.XML`）。
   - 在 [`FX3 string_english.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc) 中存在一组开机/插卡挂载态自动触发的交互提示：
     - `base 0xe836`：`Preparing Image Database File.\nPlease wait...`
     - `base 0xea23`：`Image Database File not found.\nCreate?\nRequired time: ${v1:02}:${v2:02}:${v3:02}`
     - `base 0xea24`：`Image Database File needs\nupdate. Update?\nRequired time: ${v1:02}:${v2:02}:${v3:02}`
     - `base 0xea12` / `_g 0x63b7`：`Image Database File error.\n...Recover?`

2. **台架 Tier-0 `Slot 1` 扇区写危害与 `EROFS=30` 铁律（`推断`）**：
   - 当一张存储卡经过宿主机电脑修改、删除文件，或作为 Tier-0 镜像载体插入未完成离线校验的机身 `Slot 1` 时，若卡内 `AVF_INFO` 索引缺失或与真实文件列表出现微小偏差，**相机在挂载阶段就会主动弹出上述 `Create? / Update? / Recover?` 对话框**。一旦操作员误点确认，固件便会在存储卡 FAT/exFAT 分区执行目录与 `AVIN0001.*` 扇区改写，直接破坏 `Slot 1` 金卡的原始哈希快照！
   - 因此，任何实验室台架流程必须在 [`G87`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py) 下严格执行 **`Slot 1` `EROFS=30` 只读防火墙**：未经离线全量 SHA-256 校验的金卡不得允许机身对其 `AVF_INFO` 发起任何创建、更新或修复写操作；当物理 SD 卡带有 `WP` 写保护滑块时，固件主动返回 `base 0xe967`（`Memory card locked.\nSlot 1`）并硬阻断扇区写入。

### 4.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 媒体恢复与锁档对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `libmpr.so`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 ELF/UXC`） |
| :--- | :--- | :--- |
| **目录与数据库架构** | `DCIM/` + `M4ROOT/` + **`/AVF_INFO/AVIN0001.{INP,BNP,INT}`** | 专业 **`XDROOT/`** 目录树 + `MEDIAPRO.XML`（`Clip` 级 MXF 封装） |
| **手动 / 自动媒体恢复** | 菜单 **`Shooting -> [Media] -> [Recover Image DB]`**；缺省/损坏弹窗 `Create? / Update? / Recover?` | • 菜单显式暴露 **`TC/Media > Update Media`（`Media(A)` / `Media(B)`）** 手动更新管理文件<br>• **`Media Needs to be Restored -> Restore Media(A)/(B)`**：虽不作为常规闲置菜单项在 `5-024-458-18` 目录列出，但在 [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so)（`procam_msg_confirm_restore_media_{a,b}_controller`、`CAUTION_ID_FACTOR_MEDIA_NEEDS_TO_BE_RESTORED`）与 `fx6_ns1 0x2691..0x2699` / `fx6_ns2 0x40db..0x40dd` 中作为**挂载异常自动修复提示**真实存在，且带硬件写保护防呆（`..._ng_write_protected` -> `"Please Unprotect and Reinsert Media"`） |
| **剪辑保护与删除流程** | `Playback -> [Selection/Memo] -> [Protect]`（7 项）/ `[Delete]`（5 项 + `[Delete confirm.]` `"Cancel" first`） | **`Thumbnail > Clip`** 右键/菜单操作：**`Lock/Unlock Clip`**（`fx6_ns2 0x42af`/`0x4fb7`/`0x4fe0`，含 `Select Clip / Lock All Clips / Unlock All Clips`）与 **`Delete Clip`**（`fx6_ns2 0x4092/0x4093/0x4fdd`） |

---

## 5. 严格只读（`os.O_RDONLY`）Donor 校验账本与 4 语 UXC 实证表

### 5.1 本地 Donor SHA-256 校验账本（`实测事实`：`raw_firmware_bytes_leaked = 0`）

| Donor 文件名 | 实测字节数（Bytes） | SHA-256（`os.O_RDONLY` 全量哈希） | 本波次关键取证贡献 |
| :--- | :---: | :--- | :--- |
| `FX3 appFw.so`（`Ver. 7.02`） | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_device_lock`（`DEVICE_LOCK_{OFF,MULTISELECTOR,DIAL_WHEEL,ALL}`）、休眠 `UIBIZ_SLIKEY_LOCK` / `toggle_*_manual_lock`、`MOVIE_SHOCKLESS_WB_*`、`STL_AWB_LOCK_WITH_SHUTTER_*`、`PRIORITY_SET_IN_AWB_*`、`setting_mf_assist` / `stl_af_in_focus_mag` / `{stl,mov}_init_ratio_focus_magnif`、`BKID_APP_setting_delete_confirm`、`SYSTEM_MODE_OPTION_RECOVER_DB` 及 `focus_ring_rotate` 零命中实证 |
| `FX3 libmpr.so` | `3,517,008` | `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` | `:/AVF_INFO`、`/AVIN0001.INP`、`/AVIN0001.BNP`、`/AVIN0001.INT` 与 `/M4ROOT/MEDIAPRO.XML` 路径实证 |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 全语种出厂设置种子校验基线 |
| `FX3 string_{english,simplifiedchinese,traditionalchinese,japanese}.uxc`（`ns=39`, `2692` slots） | `165,740` / `149,064` / `151,908` / `208,564` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | `base 0xe354` (`Locked.`)、`0xe721/0xe724/0xe725` (`Delete confirm.`)、`0xe2c9/0xe2ca/0xe553/0xe7f3/0xe826` (`Protect/Delete`)、`0xea2a` (`Display Media Info.`)、`0xe918/0xe836/0xea12/0xea13/0xea23/0xea24` (`AVF_INFO`) |
| `FX3 string_{english,simplifiedchinese,traditionalchinese,japanese}_f.uxc`（`ns=227`, `hdr_flag=15`） | `373,820` / `322,652` / `324,148` / `447,840` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` / `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | 全 4 语 `_f` 扩展串表：`Lock Operation Parts` / `Shockless WB` / `Shutter AWB Lock` / `Auto Magnifier in MF` / `AF in Focus Mag.` / 休眠 `Focus Ring Rotate` |
| `FX3 string_{english,simplifiedchinese,traditionalchinese,japanese}_g.uxc`（`ns=3`, `1402` slots, `1390` strs） | `69,600` / `61,296` / `61,372` / `89,428` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | `_g 0x610a` (`MENU + Fn` 锁定提示)、`_g 0x6133/0x6362` (Custom Key Protect)、`_g 0x63b7` (DB Recovery FTP reset 提示) |
| `FX6 appFw.so`（`Ver. 6.01`） | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_SETTING_HOLD_SWITCH_SETTING_*`、`USER_MENU_ONLY` / `USER_MENU_WITH_LOCK_PASSCODE`、`EXTERN_WHITESHOCKLESSWHITE` / `WHITEATWSPEED`、`WARM_COOL_*`、`setting_focus_ring_rotate_t`、`FOCUS_MAG_BUTTON_TARGET_*`、`procam_msg_confirm_restore_media_{a,b}_controller` |
| `FX6 string_english.uxc` / `string_english_2.uxc`（`ns=1`, `5044` strs / `ns=2`, `5915` strs） | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `ns1 0x2691..0x2699` & `ns2 0x40db..0x40dd` (`Media Needs to be Restored` / `Restore Media(A)/(B)`)、`ns1 0x339d/0x33a1/0x33b2` (`Key Lock`)、`ns2 0x4e0e..0x4f4b` (`Warm Cool` / `R/B Gain`) |

### 5.2 FX3 核心 4 语 UXC `resid16` 实证对照表（`实测事实`）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f 0x6904` / `0x686b` / `0x61bb` / `0x75a8` | `Lock Operation Parts` / `Multi-Selector Only` / `Dial + Wheel` / `All` | `锁定操作的部件` / `仅多功能选择器` / `转盘 + 拨轮` / `全部` | `操作鈕鎖定` / `僅多重選擇器` / `轉盤 + 滾輪` / `全部` | `操作部のロック` / `ﾏﾙﾁｾﾚｸﾀｰのみ` / `ﾀﾞｲﾔﾙ＋ﾎｲｰﾙ` / `全て` | **活跃**（位于 `Setup -> [Dial Customize]`，抗 Reset；`Fn` 长按触发 `base 0xe354` `Locked.`） |
| `_g 0x610a` | `The operation parts of the camera are\nlocked. Long press the Fn button while\npressing the Menu button to unlock.` | `拍摄装置操作的部件\n被锁定。长按Fn按钮，同时\n按Menu按钮以解除锁定。` | `拍攝裝置的操作鈕已鎖定。\n長按Fn按鈕，同時\n按下Menu按鈕即可解除。` | `カメラ本体の操作部がロックされています\nロックを解除するにはMenuボタンを押し\nながらFnボタンを長押ししてください` | **活跃**（`MENU + Fn` 5s 全局锁：锁除 Shutter 外全部按键拨盘） |
| `_f 0x737b` / `0x7acd` | `Dial Lock` / `Wheel Lock` | `转盘锁定` / `拨轮锁定` | `轉盤鎖` / `滾輪鎖` | `ダイヤルロック` / `ホイールロック` | **FX3 休眠**（多机共享包；FX3 合并入 `Dial + Wheel`） |
| `_f 0x62fe` / `0x6649` / `0x6ef1` | `Shockless WB` / `1 (Fast)` / `3 (Slow)` | `减震WB` / `1(高速)` / `3(低速)` | `減震WB` / `1(快)` / `3(慢)` | `ショックレスWB` / `1(高速)` / `3(低速)` | **活跃**（仅 Movie/`S&Q`，默认 `1 (Fast)`，可被 `Camera Settings Reset` 复位） |
| `_f 0x67a7` / `0x749f` / `0x6748` / `0x609c` | `Priority Set in AWB` / `Ambience` / `Auto: Ambience` / `Auto: White` | `AWB优先级设置` / `环境` / `自动: 环境` / `自动: 白` | `AWB優先順序設定` / `環境` / `自動: 環境` / `自動: 白` | `AWB時の優先設定` / `雰囲気優先` / `ｵｰﾄ: 雰囲気優先` / `オート: ホワイト優先` | **活跃**（默认 `Standard`，可被 Reset；`Cine EI` 锁死 AWB 故不生效） |
| `_f 0x66db` / `0x6373` / `0x6a32` | `Shutter AWB Lock` / `Shutter Half Press` / `Cont. Shooting` | `快门AWB锁定` / `快门半路向下` / `连拍` | `快門AWB鎖` / `半按快門` / `連拍` | `ｼｬｯﾀｰAWBﾛｯｸ` / `シャッター半押し` / `連続撮影` | **活跃**（**仅 Still**，默认 `Off`，**抗 `Camera Settings Reset`**！） |
| `_f 0x65f8` / `0x67cc` | `AWB Lock Hold` / `AWB Lock Toggle` | `AWB锁定保持` / `AWB锁定切换` | `AWB鎖固定` / `AWB鎖切換` | `押す間AWBロック` / `再押しAWBロック` | **活跃**（Custom Key 指派；**Movie 模式唯一可用 AWB 锁**） |
| `_f 0x7110` / `0x7b1c` / `0x6b66` | `Auto Magnifier in MF` / `Focus Magnif. Time` / `No Limit` | `MF中自动放大对焦` / `对焦放大时间` / `无限制` | `MF自動對焦放大鏡` / `對焦放大時間` / `無限制` | `MF時自動ﾋﾟﾝﾄ拡大` / `ピント拡大時間` / `無制限` | **活跃**（`Auto Magnifier in MF` 仅 Still；全组抗 `Camera Settings Reset`） |
| `_f 0x7b25` / `0x7a8b` / `0x6558` / `0x691d` / `0x72e0` | `\ue381Initial Focus Mag.` / `x1.0` / `x2.1` / `x4.0` / `AF in Focus Mag.` | `\ue381初始对焦放大倍率` / `x1.0` / `x2.1` / `x4.0` / `放大对焦中AF` | `\ue381初始對焦放大率` / `x1.0` / `x2.1` / `x4.0` / `對焦放大鏡中對焦` | `\ue381ﾋﾟﾝﾄ拡大初期倍率` / `x1.0` / `x2.1` / `x4.0` / `ピント拡大中のAF` | **活跃**（Still 初始 `x1.0`/`x2.1`；Movie 初始 `x1.0`/`x4.0`；`AF in Focus Mag.` 仅 Still；均抗 Reset） |
| `_f 0x7b28` | `Focus Ring Rotate` | `对焦环旋转` | `對焦環旋轉` | `ﾌｫｰｶｽﾘﾝｸﾞ操作方向` | **FX3 100% 休眠**（`FX3 appFw.so` `0` 个枚举与 `BKID_APP_*` 实现） |
| `base 0xe721` / `0xe724` / `0xe725` / `_f 0x74db` | `Delete confirm.` / `"Cancel" first` / `"Delete" first` / `\ue5d0Delete pressing twice` | `删除确认画面` / `默认为"取消"` / `默认为"删除"` / `\ue5d0按两次删除` | `刪除確認` / `"取消"優先` / `"刪除"優先` / `\ue5d0按兩次刪除` | `削除確認画面` / `「キャンセル」が先` / `「削除」が先` / `\ue5d02度押しで削除` | **活跃**（默认 `"Cancel" first` 与 `Off`，均属 Playback 抗常规 Reset） |
| `base 0xe2c9` / `0xe2ca` / `_f 0x6848` / `0x72d9` / `0x69f7` / `0x7339` / `base 0xe826` / `0xe553` | `Protect` / `Multiple Img.` / `All in this Folder` / `Cancel All in this Folder` / `All with this date` / `Cancel All with this date` / `All Images in This Group` / `Cancel All in This Group` | `保护` / `多个影像` / `该文件夹内的全部影像` / `取消该文件夹内全部保护` / `该日期的全部影像` / `取消该日期的全部保护` / `该组内的所有影像` / `取消该组中的所有影像` | `保護` / `多個影像` / `此資料夾中的所有影像` / `取消此資料夾中所有保護` / `此日期的所有影像` / `取消此日期的所有保護` / `此群組中的所有影像` / `取消此群組中的所有影像` | `プロテクト` / `画像選択` / `このフォルダーの全画像` / `このﾌｫﾙﾀﾞｰを全て解除` / `この日付の全画像` / `この日付を全て解除` / `このグループの全画像` / `このｸﾞﾙｰﾌﾟ画像全て解除` | **活跃精确 7 项**（无 `Cancel All Images`；含 Proxy 时与原片耦合保护） |
| `base 0xea2a` / `0xe918` / `0xea12` / `_g 0x63b7` | `Display Media Info.` / `Recover Image DB` / `Image Database File error.\nRecover?` / `Image Database File error.\nImage transfer result info. will be reset if\nrecovered. Recover?` | `显示媒体信息` / `修复影像数据库` / `影像数据库文件错误。\n要修复吗？` / `影像数据库文件错误。\n如果修复，将重置影像传输结果信息。\n要修复吗?` | `顯示記憶卡資訊` / `還原影像資料庫` / `影像資料庫檔案錯誤。\n要還原?` / `影像資料庫檔案錯誤。\n如果還原，影像傳輸結果資訊將會重設。\n要還原?` | `メディア残量表示` / `管理ファイル修復` / `管理ファイルに不整合が見つかりました\n修復しますか？` / `管理ファイルに不整合が見つかりました\n修復すると画像の転送結果情報がﾘｾｯﾄ\nされます。修復しますか？` | **活跃**（`Recover Image DB` 双免疫 Reset/Init；写 `AVF_INFO` 需受 `Slot 1` `EROFS=30` 防火墙硬阻断） |

---

## 6. `fx3-safety` 安全门控对齐与 Wave 73 收口

| 本波次核心实体 / 规则 | 对应 `fx3-safety` 门控与台架约束 |
| :--- | :--- |
| `[Lock Operation Parts]` 位于 `Dial Customize`、`Fn` 长按 vs `MENU + Fn` 5s 锁除 Shutter 外全部实体键、`My Dial` 临时解锁与休眠 `UIBIZ_SLIKEY_LOCK` | [`G95`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py)（强校四选项、`Setup` 抗 Reset、与 `AF Area Registration` 互斥及区分 `MENU+Delete` 2s 破坏性双键格式化） |
| `[Shockless WB]`、`[Priority Set in AWB]`、`[Shutter AWB Lock]` 抗 Reset 与 Movie Custom Key `AWB Lock` | [`G116`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py)（校验 `Cine EI` 下 AWB 锁定、`[Shutter AWB Lock]` Still 独占 + 抗 `Camera Settings Reset` 与正确选项字面） |
| `[Auto Magnifier in MF]`、`[Focus Magnif. Time]`、`[Initial Focus Mag.]`（`x1.0`/`x2.1` vs `x4.0`）、`[AF in Focus Mag.]` 与休眠 `[Focus Ring Rotate]` 拒绝 | [`G109`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)（强校 Ver. 2.00+ 全组抗 Reset、Still/Movie 倍率拆分及拒绝虚假 `Focus Ring Rotate` 写入） |
| `[Delete confirm.]` `"Cancel" first`、`[Protect]` 7 项 + Proxy 耦合、`[Display Media Info.]` 与 `[Recover Image DB]` `AVF_INFO` 引导扇区写防火墙 | [`G87`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py) + [`G112`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_power_save_monitor_language_volume_delete_and_112gate_guard.py) + [`G114`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h427-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py)（严禁在未经离线 SHA-256 校验的 `Slot 1` 金卡上响应 `AVF_INFO` 自动重建弹窗或执行 `Recover Image DB`，硬锁 `EROFS=30`） |

- **Wave 73（`H427`）交付状态**：`READY_FOR_COMMIT`（纯文档只读实证取证交付；零代码侵入；零 `.pyc`；零临时文件；零专有固件字节外泄）。
