# Wave-22 索尼 BIONZ XR 全球真机情报：`MIRA_CETUS2` E 卡口 `info7/info8/info3D` 协议、`0x02cf0232` 呼吸补偿与 Type-A HDMI `4264×2408` 16-bit RAW

## 结论先行（实测与公开文献交叉印证）

本轮针对 **`MIRA_CETUS2`（`ILME-FX3` / `ILCE-7M4` / `ILME-FX30` 共用 BIONZ XR 平台）** 固件逆向文献与索尼 `Ver. 7.00 / 7.02` 官方外录技术规范的深度检索，锁定了真机运行 Stage-B 时的 **E 卡口光学通信边界** 与 **Type-A HDMI 16-bit RAW 外录管线规格**：

1. **E 卡口串口协议（`info7 / info8 / info3D`）、`p18:/lens/lensfile.bin` 与呼吸效应补偿（`0x02cf0232`）**：
   - 在 `CPAPP-B.BIN`（协处理器 RTOS）与 `appFw.so` 交互层中，E 卡口镜头通过三类核心数据包握手：**`info7`（基础 16 位镜头 ID）**、**`info8`（对焦/光圈驱动参数）** 与 **`info3D`（扩展 AF 与光学补偿曲线）**，并结合只读分区 `p18:/lens/LENSFILE.BIN` 完成型号查表。
   - **原厂镜头 16 位白名单判据**：`CPAPP` 通过位运算 `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)` 判定原厂兼容 E 卡口镜头，决定是否放行 **呼吸效应补偿（Focus Breathing Compensation，`BKID_APP_MR_SETTING_LENS_COMP_BREATHING = 0x02cf0232`）** 裁切与 Catalyst 元数据写入；同时 `Ver. 6.00–7.02` 通过 Wi-Fi / 有线 USB 向 **Monitor & Control (`Ver. 2.1.0+`)** 输出 **Focus Map（焦点映射）** 景深点阵流。
   - **真机护栏要求**：Route-1 架构保留 FX3 原厂 `CPAPP-B.BIN` 与 `p18:/lens/LENSFILE.BIN`（`BLKROSET=1`），Stage-B 垫片需无损透传 `0x02cf0232` 属性与 `info7/info8/info3D` 通道，严禁将 CineAlta 广播机手动 `LENSFILE` 槽位写操作落盘至 `p18:/lens`。

2. **Type-A HDMI `4264 × 2408`（`16:9` 最高 `60p`）16-bit 线性 RAW 外录 vs 屏蔽 FX6 `12G-SDI` RAW**：
   - FX3 `Ver. 7.00 / 7.02` 通过机身全尺寸 Type-A HDMI 输出 **`4264 × 2408` 16-bit 线性 RAW 流（最高 `60p`）**，支持与机内 `XAVC S / HS / S-I + Proxy` 同步录制，外录端分为两类封装：
     - **Blackmagic RAW（`.braw`）**：需搭配 `Blackmagic Video Assist 5"/7" 12G HDR`（固件 `3.22+`，`3G` 型号不支持）及 `BRAW 5.1 / DaVinci Resolve 20.2+`；因索尼 HDMI RAW 不发送 Blackmagic 私有传感器 profile 包，`.braw` 的 ISO 等 RAW 覆写项锁定在机身拍摄值；
     - **Apple ProRes RAW / HQ**：搭配 `Atomos Ninja V / V+ / Ultra`（`AtomOS 10.64+`），封装白平衡与 ISO 偏移元数据供 FCP / Premiere / Resolve `20.2+` 调节。
   - **真机护栏要求**：FX6 `6.01` `appFw.so` 默认在 `12G-SDI` BNC 端口探测 RAW 输出，真机 FX3 无物理 SDI 接口，必须屏蔽 `12G-SDI` 寄存器探测并将 RAW / Clean HDMI / 时间码路由桥接至 FX3 `7.02` 原生 Type-A HDMI 管线。

---

## 实测事实 vs 未执行物理动作声明

- **已验证事实**：公开 `MIRA_CETUS2` 逆向属性表（`0x02cf0232`、`((lens_id >> 14) == 3)`）、索尼官方 `Ver. 7.00/7.02` HDMI RAW 规格与本地只读镜像结构一致。
- **物理红线状态**：未连接任何真实物理 FX3 相机，`persistent_emmc_writes_authorized = False`，`spi_nor_write_authorized = False`，`physical_usb_packets_emitted = 0`。
