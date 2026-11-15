# Wave-24 全球索尼真机情报同步：`ILME-FX3` (`Ver. 7.02`) 原生 UVC 缺失红线、`USB-PD / DC-C1` (`>=65W / 5A`) 供电铁律、SD vs CFexpress-A User LUT (`.cube`) 路径不对称与 `RMT-P1BT` 蓝牙互斥

## 1. 结论先行

基于索尼官方 `ILME-FX3` (`Ver. 7.00 / 7.02`) 帮助指南、`Monitor & Control` (`Ver. 2.4.0+`) / `Creators' App` (`Ver. 3.1.0+`) 技术文档与 `DC-C1` 假电池供电规范，同步 **Wave-24 四项关键物理真机边界**（直接合入 `G65/G66` 安全门禁、后续固件审计器、VM Stage 与 QEMU 预演）：

1. **`ILME-FX3` / `ILME-FX3A` 硬件与内核级无原生 `[USB Streaming]` (`UVC/UAC`) 模式**：
   - 与后续机型（`ILME-FX30`、`ILME-FX2`）不同，`ILME-FX3` (`0x91030080`) 与 `ILME-FX3A` **不支持原生 UVC 连接**；`[USB Connection Mode]` 仅提供 `Sel. When Connect`、`MassStorage(MSC)`、`MTP` 与 `Remote Shooting` 四种模式（旧版 PC `Imaging Edge Webcam` 走 `Remote Shooting` 仅限 `1024×576` 无音频）。
   - `FX3 Ver. 7.02` 的 4K 推流走 **Network Streaming (`RTMP/RTMPS/SRT` 最高 `3840×2160 59.94p 38Mbps` HEVC/AVC)**、开机自动重连 **USB-LAN (`RNDIS` / `CDC-NCM`)** 或 **Type-A HDMI 采集卡**。
   - **Stage-B 桥接护栏**：严禁向 Stock FX3 `4.9.337-scel+` 内核 USB Gadget 控制器下发不存在的 UVC/UAC composite 配置描述符，防止触发 USB PHY 挂起或枚举死锁。
2. **真机供电双路径电气红线（机身直插 `USB Power Supply` 必插 `NP-FZ100` vs 官方 `DC-C1` 假电池 `>=65W + 5A` e-Marked 线缆）**：
   - **机身 Type-C `USB Power Supply = On`**：物理上**必须同时在电池仓内插入一颗 `NP-FZ100` 真电池**方可激活 USB-PD 供电（运行期间暂停内部充电，关机后恢复充电；Micro-USB 口不支持供电）。若拔出 `NP-FZ100` 仅靠机身 Type-C 供电，真机会立即断电关机！
   - **官方 `DC-C1` 直流耦合器（释放机身 Type-C 口用于 `USB-LAN` / `Creators' App`）**：前端必须接入 **`>=65W` USB-PD 电源适配器 + 带 e-Marker 芯片的 `5A` USB-C 线缆**；功率或线缆电流不足将导致 `DC-C1` 电源指示灯闪烁告警甚至高负载录制掉电，且接入 `DC-C1` 时机身可能强制锁定 LCD 最大亮度档位。
3. **双卡槽 User 3D LUT (`.cube`) 目录路径不对称与 `Cine EI` 双原生 ISO (`800 / 12800`) 规范**：
   - 支持 **17-point (`LUT_3D_SIZE 17`)** 与 **33-point (`LUT_3D_SIZE 33`)** `.cube` 文件，文件名（含 `.cube` 后缀）严格 `<= 63` 单字节字母数字字符，机内 `p2:/setting` 最多登记 `16` 组（`User1`..`User16`，支持 `0EV..+2EV` 1/3 档 AE Level Offset）。
   - **真机目录路径非对称陷阱**：
     - **SD / SDXC 卡**：`/Private/Sony/PRO/LUT/`
     - **CFexpress Type A 卡**：`/Sony/PRO/LUT/`（无 `/Private` 前缀！）
   - **`Cine EI` 高感基准 `ISO 12800`**：传感器增益锁死在 `ISO 800` 或 `ISO 12800`，在 `Base ISO 12800` 下有效 `EI` 索引范围为 **`3200 EI .. 51200 EI` (`±2 EV`)**，仅改变监看 LUT 亮度与 MXF/XML 元数据而不污染 CMOS 模拟增益。
4. **`RMT-P1BT` (`Bluetooth 4.2`) 遥控器与红外接收器 / 手机位置共享物理互斥**：
   - 当 `MENU -> Network -> [Bluetooth] -> [Bluetooth Rmt Ctrl] = On` 时，真机自动**禁用机身红外（IR）遥控接收**与智能手机 GPS 位置信息联动（且在 `ILME-FX3A` 上物理移除了 IR 与 NFC 硬件）。

## 2. 工程落地映射

- **安全门禁 (`outputs/fx3-safety/` Gate `G65` & `G66`)**：拦截 Stage-B 非法 UVC gadget 激活请求、校验冷备份/预演前供电拓扑（`NP-FZ100` 在位性或 `DC-C1 >=65W/5A` 预算）、校验双介质 `.cube` 路径路由（`/Private/Sony/PRO/LUT/` vs `/Sony/PRO/LUT/`、`17/33pt`、`<=63B`）及 `RMT-P1BT` 蓝牙/IR 互斥状态。
- **固件审计、VM HIL 与 QEMU 真内核闭环**：同步验证 `Cine EI` `800 / 12800` (`3200..51200 EI`) 元数据传递与 `Creators' Cloud` `OK/NG/KEEP` Clip Flag 过滤无持久层污染（`H0 == H3`）。
