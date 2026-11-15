# Wave-21 索尼 BIONZ XR 全球真机情报：SCEL `ssboot` / `WBI2` 快照启动陷阱与 FX3 `Ver. 7.02` 官方升级 / C2PA 硬件约束

## 结论先行（实测与公开文献交叉印证）

本轮全球公开固件研究与官方技术通告检索锁定了两项直接决定 **ILME-FX3（`Ver. 7.02` / `CXD90057`）真机刷入与零残留回退** 成败的底层硬件机制：

1. **SCEL `ssboot` / `WBI2` 引导层绕过陷阱（“The WBI Trap”，分区 `nflasha5`）**：
   - 索尼 BIONZ XR（64 位 `CXD90057` Cortex-A35，Sony CE Linux `4.9.337-scel+`）并非使用消费级桌面 `swsusp` 或第三方 Lineo `hibdrv` 分区实现 0.5 秒瞬时开机，而是采用索尼自研 **Snapshot Boot（`ssboot`，CELF 公开架构）+ `liro.ko` + `/proc/udm/*`**，将 **LZO 压缩的只读持久化内存快照（`prsv-img`）** 存储在 **`/dev/nflasha5`（`/wbi`，约 `232.5 MiB`，8 字节魔数 `WBI2\x00\x00\x00\x00` = `57 42 49 32 00 00 00 00`）**。
   - **真机关键影响**：只要 `nflasha5` 首扇区保留有效 `WBI2` 魔数，Bootloader 上电后会**直接把 LZO 快照解压回物理 DRAM 原地址并跳入内核唤醒入口，完全绕过 `/sbin/init`、`bootin.elf`、`im.elf` 以及 `/usr`（`nflasha15`）挂载流程**；拔电池静置 30 秒以上亦不会清除非易失 eMMC 上的 `nflasha5`。
   - **护栏闭环要求**：
     - **Tier-0 冷备（`FX3RCPT1`）** 必须完整备份 `nflasha5` 首 `512 B` `WBI2` 头部及全分区 SHA-256 基线（`H0`）；
     - **Stage-B 运行期（`H1/H2`）** 必须对 `/dev/nflasha5` 与 `/dev/pnflasha5` 施加 `BLKROSET=1` 只读锁并拦截 `PM_SUSPEND_DISK` / `/proc/udm` 写快照请求，严禁把 FX6 Stage-B 内存态写回 `nflasha5`（否则退卡回原厂 FX3 时会唤醒异构内存态导致崩溃）；
     - **冷启动进入 Stage-A 与一键无痕卸载（`H2 -> H3`）** 必须保证退出双系统后 `nflasha5` 的 `WBI2` 首扇区与全分区哈希 `100%` 恢复至 `H0`（`H0 == H3`），完整保留原厂 FX3 的 0.5 秒瞬时热启动能力。

2. **ILME-FX3 `Ver. 7.00 / 7.02` 官方 `BODYDATA.DAT` 升级与 C2PA 硬件级红线**：
   - 官方 `Ver. 7.02`（2026-03-17 发布，累积包含 `Ver. 7.00` BIG6 主界面、HDMI Blackmagic RAW 输出与 C2PA 数字签名，`BODYDATA.DAT` 精确字节数 **`811,876,768 B`**，`\x89UFU\r\n\x1a\n` 封装）：
     - **强制前置版本下限（`>= Ver. 2.04`）**：若机身固件 `<= Ver. 2.02` 直接刷入 `7.00 / 7.02` `BODYDATA.DAT`，硬件会拒绝升级并触发 **7 长闪 + 7 短闪（`7L + 7S`）LED 故障码**；
     - **Slot-1 根目录唯一文件约束**：`BODYDATA.DAT` 与 C2PA 数字签名升级许可证/证书均**必须置于卡槽 1（Slot 1）根目录**，且严禁同目录残留 `BODYDATA (1).DAT` 等重命名副本；
     - **C2PA 单包 100 许可证硬件上限**：`ILME-FX3 / FX3A / FX30` 单文件最多解析 **`100` 个许可证**（超限拒绝导入），导入后落盘于 `p12:/cert/RQ_LIC.DAT`（Stage-B 期间全程 `EROFS` 只读保护）；
     - **无线安全协议基线升级**：`Ver. 7.00+` 已废弃不安全的 `WEP / WPA1 / IPsec`，仅允许 `WPA2 / WPA3` 与 Access Authentication。

---

## 工程落点映射

| 领域 | 模块路径 | 落地动作 |
| :--- | :--- | :--- |
| 固件静态审计（#36） | [outputs/fx3-firmware-lab](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/oarfish/outputs/fx3-firmware-lab) | Phase 174 第 36 号审计器验证 `p5:/wbi`（`WBI2`）分区隔离与零写入锁 |
| 恢复与掉电护栏（Pillar 23） | [outputs/fx3-recovery-adapter](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/oarfish/outputs/fx3-recovery-adapter) | Phase 176 Pillar 23 验证跨模式快照防污染、突发拔电池与 100 次切换 `H0 == H3` |
| 硬件安全门禁（G59–G60） | [outputs/fx3-safety](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/oarfish/outputs/fx3-safety) | Phase 177 新增 `G59`（`ssboot/WBI2/liro.ko` 门禁）与 `G60`（`7.02` `>=2.04` 版本下限 + Slot-1 C2PA `<=100` 门禁），达成 `60/60` `verify-60-gates` |

## 实测事实 vs 未执行物理动作声明

- **已验证事实**：公开 SCEL `ssboot`/`WBI2` 规范、索尼官方 ILME-FX3 `Ver. 7.00/7.02` 升级技术参数与本地只读（`O_RDONLY`）镜像参数一致。
- **物理红线状态**：未连接任何真实物理 FX3 相机，`persistent_emmc_writes_authorized = False`，`spi_nor_write_authorized = False`，`physical_usb_packets_emitted = 0`。
