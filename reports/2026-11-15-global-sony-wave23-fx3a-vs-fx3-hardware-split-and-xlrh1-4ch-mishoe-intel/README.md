# Wave-23 索尼 BIONZ XR 全球真机情报：`ILME-FX3` vs `ILME-FX3A` 硬件代际分支隔离红线与 `XLR-H1` MI 热靴 4 声道 24-bit 数字音频覆盖机制

## 结论先行（实测与公开文献交叉印证）

本轮真机风险排查锁定了两项极易在实际片场与刷机台架上引发事故的物理级差异：

1. **`ILME-FX3`（`Ver. 7.02`）与 `ILME-FX3A`（`Ver. 2.02`，2025 硬件改款）严禁跨机混刷（同名 `BODYDATA.DAT` 分支隔离）**：
   - 索尼于 2025 年中期因原厂背屏停产推出硬件改款 **`ILME-FX3A`**，外观与传感器（`IMX510` + BIONZ XR）几乎完全一致，但存在 **3 项底层硬件级删改**：
     1. **背屏面板与显示驱动**：`ILME-FX3` 为 `3.0"` **`1,440,000` 点**；`ILME-FX3A` 更换为 `3.0"` **`2,359,296` 点 XGA 面板**（与 FX30 同级）；
     2. **NFC 芯片与机身标识**：`ILME-FX3` 具备硬件 NFC；`ILME-FX3A` **物理移除 NFC 控制器**；
     3. **红外（IR）遥控接收器**：`ILME-FX3` 具备前置红外接收窗；`ILME-FX3A` **物理移除 IR 接收硬件**。
   - **固件分支完全独立**：2026 年 3 月同步维护版本中，`ILME-FX3` 为 **`Ver. 7.02`**，而 `ILME-FX3A` 为 **`Ver. 2.02`**（两者功能对齐 BIG6、HDMI BRAW、C2PA，但内核显示/外设驱动、Model ID、`BODYDATA.DAT` 签名包头及 SD 卡导出的 **`CAMSET` 相机设置文件** 均**互不兼容**）。
   - **真机硬红线**：本实验室当前 donor 与 Stage-A/Stage-B 垫片严格绑定原版 **`ILME-FX3`（`0x91030080` / `Ver. 7.02` / `1.44M` LCD）**；若检测到 `ILME-FX3A`（`2.36M` XGA 面板 / 无 NFC-IR 设备树节点 / `Ver. 2.02` 固件树），Stage-A 与主机预检必须 `<50 µs` **Fail-Closed 拒绝挂载并回退原厂系统**，严禁跨代加载显示垫片或混用 `BODYDATA.DAT` / `CAMSET`。

2. **`XLR-H1` 多接口（MI）数字热靴 `48 kHz / 24-bit 4ch` LPCM 路由与机身 `3.5mm` 物理抢占陷阱**：
   - FX3 通过顶部 MI 数字热靴连接 **`XLR-H1` 手柄**（内置 A/D 与 DSP，从未发布独立手柄固件包）原生支持 **`48kHz/24bit 4ch`、`48kHz/24bit 2ch`、`48kHz/16bit 2ch`** 三档数字音频（`INPUT 1/2` XLR 映射 `CH1/CH2`，手柄 `INPUT 3` 3.5mm 立体声映射 `CH3/CH4`，耳机监听支持 `CH1/2`、`CH3/4`、`CH1+3/CH2+4` 矩阵）。
   - **物理抢占与重置陷阱**：
     - 一旦向 **机身内置 3.5mm 麦克风孔** 插入插头，硬件检测开关会自动强制切断 MI 热靴音频并灰显锁定 `[MI Shoe Audio Set.]`；
     - `S&Q` 升格模式下强制静音关闭 MI 热靴录音；
     - 大版本官方 `BODYDATA.DAT` 升级会将 `[MI Shoe Audio Set.]` 重置回默认 `48kHz/16bit 2ch`。

---

## 实测事实 vs 未执行物理动作声明

- **已验证事实**：索尼官方 `ILME-FX3 Ver. 7.02` / `ILME-FX3A Ver. 2.02` 硬件规格表、`XLR-H1` MI 热靴路由规范与本地只读镜像参数一致。
- **物理红线状态**：未连接任何真实物理相机，`persistent_emmc_writes_authorized = False`，`spi_nor_write_authorized = False`，`physical_usb_packets_emitted = 0`。
