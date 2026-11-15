# Wave-26 全球索尼真机情报同步：`ILME-FX3` (`Ver. 7.02`) `BIG6` 主界面左下角 `[Aperture / ND Filter]` 无物理电子 ND 边界、`CAMSET` 仅限 Slot-1 双介质路径分裂与 `VMC-BNCM1` 仅机身 `TC IN`（禁手柄口 / 无 BNC `TC OUT`）硬件铁律

## 1. 结论先行

基于索尼官方 `ILME-FX3` (`Ver. 7.00 / 7.02`) 帮助指南（`helpguide.sony.net`）实测核验，提炼 **Wave-26 三项核心真机兼容与防砖边界**：

1. **`ILME-FX3` (`Ver. 7.00+`) `Home` (`BIG6`) 六宫格精确拓扑与无内置电子无级 ND 硬件护栏**：
   - 真机启用前提：`[Mode Settings] = [Fixed/Variable]` 且通过 `[Custom Key/Dial Set.]` 绑定 `[HOME]` 键。
   - 六宫格精确槽位：`1: FPS (Fixed/Variable)` · `2: ISO / Base ISO` · `3: Shutter speed / Shutter angle` · `4: Aperture（默认）或 ND Filter`（经 `MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)]` 切换）· `5: Picture Profile / Select LUT` · `6: White Balance`（另含第 7 状态栏区）。
   - **FX6 移植关键差异**：`ILME-FX6` 机身内置物理电机/液晶驱动的电子无级 ND（`1/4..1/128`），而 **`ILME-FX3` 机身无任何物理内置光学/电子 ND 硬件**。Stage-B 运行 `FX6` `BIG6` 时，严禁向 FX3 `CP` 总线发射 `FX6` 电子 ND 执行器控制帧（`e_nd_actuator_tx_count == 0`），左下角默认对齐 E 卡口镜头 `[Aperture]`，切至 `[ND Filter]` 时仅作纯软件元数据/参考指示处理。
2. **`[Save/Load Settings]` (`CAMSET01.DAT .. CAMSET10.DAT`) 仅限 Slot-1、SD vs CFexpress-A 根目录分裂与跨机型（`FX3` / `FX3A` / `FX6`）二进制隔离**：
   - **物理卡槽与模式锁**：仅支持 **Slot 1** 读写设置档案（不可切至 Slot 2），单卡上限 **10 个**（`CAMSET01.DAT .. CAMSET10.DAT`），处于 `MR`（`Recall Camera Setting`）模式时整项置灰禁用；且排除 `White Balance: Custom 1/2/3`、`FTP`、网络推流、IP/证书与日期时间等机器绑定项。
   - **双介质路径非对称**（与 `.cube` LUT 同源）：
     - **SD / SDHC / SDXC 卡**：`/PRIVATE/SONY/SETTING/FX3/CAMSET/`
     - **CFexpress Type A 卡**（省略顶层 `PRIVATE`）：`/SONY/SETTING/FX3/CAMSET/`
   - **跨机型/跨代防污染**：`ILME-FX3`、`ILME-FX3A` 与 `ILME-FX6` 的 `.DAT` 档案互不兼容；Stage-B `FX6` 配置读写必须沙箱化至 `/tmp/fx6_camset_overlay`，严禁覆写 Slot-1 真机 `FX3/CAMSET/` 目录或 `p2:/setting`（保持 `H0 == H3`）。
3. **`VMC-BNCM1` (`A-5051-506-A`) 时间码单向 `TC IN` 铁律、禁插 `XLR-H1` 手柄 Micro-USB 口与仅 HDMI 数字 `TC OUT`**：
   - **单向 `TC IN`（无 BNC `TC OUT`）**：不同于 `ILME-FX6` 独立可切换物理 BNC `TC IN / OUT` 接口，`ILME-FX3` 搭配 `VMC-BNCM1`（`0.2m`）在机身 **Multi/Micro USB 端子**上**仅支持 `TC IN` 外部时间码输入**（需切至 `[Movie]` + `[Time Code Make] = [Preset]` + `[Time Code Run] = [Free Run]`，持续约 `10s` 显示 `EXT-LK` 锁定；若切 `S&Q` 或改动 `TC Make/Run/Preset` 即刻失锁）。
   - **两大物理误插/方向陷阱**：
     - **严禁插入 `XLR-H1` 手柄侧面的 Micro-USB 口**：官方明确 `VMC-BNCM1` 仅限连接机身本体 Multi/Micro USB 口，接手柄 Micro-USB 口完全无效且属违规连接。
     - **严禁驱动 Multi/Micro USB 输出 LTC/BNC `TC OUT`**：Stage-B 必须屏蔽 `FX6` 的 BNC `TC OUT` 反向驱动请求（`EOPNOTSUPP`），将时间码输出严格路由至 **Type-A HDMI 数字通道**（`MENU -> Setup -> [External Output] -> [HDMI Output Settings] -> [Time Code Output] = [On]`，`S&Q` 下自动禁用）。

## 2. 工程映射

- **`outputs/fx3-firmware-lab/`**：审计 `BIG6` `[Home (Lower Left)]`（无物理 e-ND 执行器）、Slot-1 `CAMSET` 双介质路径分裂与 `VMC-BNCM1` 机身 `TC IN` / HDMI `TC OUT` 路由表。
- **`outputs/fx3-safety/` & `outputs/fx3-recovery-adapter/`**：建立无物理 e-ND 防误驱、`CAMSET` 跨机型防污染、`XLR-H1` 手柄 Micro-USB 误插 `VMC-BNCM1` 告警及 BNC `TC OUT` 阻断门禁。
- **`outputs/fx3-vm/` & `outputs/fx6-native-presenter-closure/`**：在 HIL 与真实 `FX3 7.02` (`4.9.337-scel+`) ARM64 QEMU 中闭环实测验证。
