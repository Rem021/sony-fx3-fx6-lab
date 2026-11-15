# Phase 216 实机拍摄与监看准备度预检器报告（`preflight-hdmi-proxy-desqueeze-and-simult` / Waves 27–29）

## 1. 核心结论（Conclusion-First）

1. **5 项物理台架与双卡介质预检清单（`S1..S5`）全部闭环**：在 `outputs/fx6-on-fx3-closure/` 中新增只读预检器 [`realhw_hdmi_proxy_desqueeze_and_simult_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_hdmi_proxy_desqueeze_and_simult_verifier.py)（Schema `phase216_realhw_hdmi_proxy_desqueeze_and_simult_preflight_v1`，版本 `216.0.0`），将物理操作员台架预检链路扩展为 `preflight-card-insert` → `preflight-bench-cable-fan-slot1` → `preflight-hdmi-proxy-desqueeze-and-simult`，完整覆盖 Sony Waves 27–29 实机手册与固件行为边界。
2. **双模式 56 项单元测试与里程碑回归 100% 通过**：新增 [`test_realhw_hdmi_proxy_desqueeze_and_simult_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_hdmi_proxy_desqueeze_and_simult_verifier.py) 共 **56** 项双模式单测，在本地只读 donor 模式（`LOCAL_DONOR_O_RDONLY`，耗时 **`0.027s`**）与无固件洁净室模式（`FX3_FX6_FORCE_CLEAN_ROOM=1` / `CLEAN_ROOM_SYNTHETIC`，耗时 **`0.021s`**）下均 `100%` 通过（远低于 `< 2.0s` 预算），同时保持 `preflight-card-insert`、`preflight-bench-cable-fan-slot1`、`verify-milestone-175`、`verify-milestone-193` 与 `make verify-milestone-209` 全绿。
3. **安全硬锁与离线默认阻断 100% 保持**：离线默认返回 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`（模拟演练 `--simulate-bench-dry-run` 返回 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`），全程无条件锁死 `hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0` 及 `16/16` 存储面 `SHA256(H0) == SHA256(H3)`。

---

## 2. 五大物理台架与介质准备度清单（`S1 .. S5`）

| 清单 ID | 预检域 | 关键校验规则与报错码 |
| :--- | :--- | :--- |
| **`S1_DESQUEEZE_165X_4LOCKS_AND_EXTERNAL_MC_FOCUS_MAP`** | 变形宽银幕反挤压（`1.6x=1.65x`）与外置 `M&C Focus Map` `<150fps` | 校验 `ILME-FX3`（`0x91030080`, `Ver. 7.02`）下 `Off / 1.3x / 1.5x / 1.6x(实际 1.65x) / 1.8x / 2.0x` 枚举、激活态 4 项功能锁（`Marker` / `FocusMag` / `AutoMagMF` / `FaceEyeAF`）、视频 `Initial Focus Mag.` 仅限 `x1.0/x4.0` 且与 `Bright Monitoring` 互斥、4 类自动抑制（`HDMI RAW` / `Off(HDMI Only)` / `Log Off` / `Remote`）、机内零原生 `[Focus Map]` 菜单，以及 `Monitor & Control` 外置对焦图 `< 150.0fps` 上限（保留 `1..6fps`，阻断 `>=150fps` 如 `200/240fps`）。 |
| **`S2_HDMI_LOG_1080P_DOWNSHIFT_VS_HDMIONLY_4K_AND_BLANK_LCD`** | HDMI `Log` `1080p` 降级、`[Off(HDMI Only)]` 禁内录防护与机内屏黑屏预警 | 阻断操作员为获取非 RAW `4K 10-bit` HDMI Log 而误开 `[Rec. Media dur HDMI Output] = [Off(HDMI Only)]` 导致双卡内录静默丢失（`S2_ERR_HDMI_ONLY_DISABLES_INTERNAL_CARD_REC`）；校验 `24.00p 10bit` 的 `DCI 4K 24p` 前置门控；验证内录开启且非 RAW 时 `Log Shooting` / `PPLUT1..4` 强制 HDMI 降至 `1080p`；在 `[HDMI Info. Display] = [On]` 时发出 `WARN_HDMI_INFO_DISPLAY_ON_BLANKS_BUILT_IN_LCD` 并默认阻断机内 LCD 黑屏误触。 |
| **`S3_DUAL_SLOT_SIMULT_AUTOSWITCH_AND_PX_PROXY_COUPLED_VAULT`** | 双卡 `Simult.` + `Auto Switch Media` 与 `Px` 代理耦合保险库 | 校验 Slot 1/2 双槽 `CFexpress-A` / `SDXC` exFAT 容量与速度等级（`V90` / `VPG200` / `VPG400`）对等，阻断 `SDHC` FAT32 混插；严格双卡 `1:1` 冗余模式下要求 `[Auto Switch Media] = [Off]` 防止单卡满后非冗余续录；校验 `XAVC HS HD` / `XAVC S HD` `Px` 代理 `< 100p` 与 `S&Q < 100fps` 截止线、禁止机内代理直放预期，以及 `M4ROOT/CLIP/` + `M4ROOT/SUB/` 原子级同步 Delete/Protect 配对。 |
| **`S4_FILE_SETTINGS_37CHAR_SHOTMARK_XML_AND_TC_REGENERATE_SLOT1`** | `37` 字符标题 / `Series` 计数 / `SDHC` 锁、`Shot Mark1/2` XML 与 Slot-1 `TC Regenerate` | 校验 5 种文件名格式、`<= 37` 位合法 ASCII 标题、`[File Number] = [Series]` 防撞号计数器、`SDHC` 插入强制锁定 `[Standard]` 文件名并禁自定义目录；校验 `Shot Mark1/2` 对应 `M4ROOT/CLIP/*M01.XML` NonRealTimeMeta 旁路元数据；校验 `[Time Code Make] = [Regenerate]` 仅从 **Slot 1** 读取尾帧 TC 并强制切换 `[Rec Run]`；当启用 `VMC-BNCM1` `EXT-LK` 时强制保持 `Movie + Preset + Free Run`（阻断 `S&Q` 或切换 `Regenerate` 导致失锁）。 |
| **`S5_REC_LAMP_COUPLED_TALLY_SHOCKLESS_WB_AND_TIER0_RECEIPT_GATE`** | 3 态物理 `REC Lamp` 耦合 Tally、`Shockless WB` `0` 帧跳变与 Tier-0 双盘回执门控 | 校验 `[REC Lamp]` 精确 3 态（`All On`、`Only Front Off` 灭前灯且后灯+顶键 `REC` 灯硬件锁步同亮、`All Off`），阻断独立关后灯误判；校验 `[Silent Mode] = [On]` 硬锁 `[Audio signals] = [Off]`；校验 `[Shockless WB]` 在手动调节色温（`2500K..9900K`）与 `A-B/G-M` 网格微调时为 **`0` 过渡帧**；验证 `16/16` 存储面 `H0 == H3` 与跨物理设备（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` Tier-0 冷备回执。 |

---

## 3. 交付文件清单与实测验证

### 3.1 严格归属的 6 个变更文件
1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_hdmi_proxy_desqueeze_and_simult_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_hdmi_proxy_desqueeze_and_simult_verifier.py)（新增）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（导出 Phase 216 公共符号）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（接入 `preflight-hdmi-proxy-desqueeze-and-simult` CLI）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（补充模块结构说明与 CLI `# 39` 示例）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_hdmi_proxy_desqueeze_and_simult_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_hdmi_proxy_desqueeze_and_simult_verifier.py)（新增 **56** 项双模式单测）
6. [`reports/2026-11-15-phase216-realhw-hdmi-proxy-desqueeze-and-simult-preflight/README.md`](./README.md)（本报告）

### 3.2 实测命令与结果摘要
- `LOCAL_DONOR_O_RDONLY` 单测：`56` 项全绿（`0.027s < 2.0s`），有界 `O_RDONLY` donor 头部校验 `< 0.15s`，`raw_firmware_bytes_leaked = 0`。
- `FX3_FX6_FORCE_CLEAN_ROOM=1` 单测：`56` 项全绿（`0.021s < 2.0s`）。
- CLI 预检序列回归：`preflight-card-insert`、`preflight-bench-cable-fan-slot1`、`preflight-hdmi-proxy-desqueeze-and-simult` 全部通过且离线默认阻断。
- 里程碑与仓库卫生：`verify-milestone-175`、`verify-milestone-193`、`make verify-milestone-209` 与 `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 全部通过（零 `.pyc`、零固件二进制泄露）。
