# Hydrogen-15｜`outputs/fx3-firmware-lab/` 洁净室 `UFU`/`FDAT`/`UDTRFIRM` 审计、`ALCIN_UUD` vs `CHAPLIN` `HAITA`/`BK4` 门控分析与无硬件 `.uxc`/`LDEC` 解码交付报告

> **任务**：`Hydrogen-15`（Wave 3+）  
> **交付包**：[`outputs/fx3-firmware-lab/`](../../outputs/fx3-firmware-lab/README.md)  
> **基线对齐**：[`reports/2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md`](../2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md)（§1.2 / §1.3 / §2.1 / §4）

---

## 1. 洁净室与 BYOF 合规红线（Clean-Room Compliance）

- **零专有密钥**：全包严格禁止写入、硬编码或派生任何索尼专有 AES 密钥（如 `CXD90057_k8`）或厂商 RSA 私钥；仅使用公开容器魔数（`\x89UFU\r\n\x1a\n`、`FDAT`、`UDTRFIRM`、`SDM2` `8246` `2.00`）、公开数学常量（`hashlib.sha256(b"").digest()[:16]`）、1024B `<HH` 帧校验及调用方外部传入 BYOF 回调。
- **严格只读访问**：本地供体 ELF 与 `.uxc` 资产全部通过 `os.open(..., os.O_RDONLY)` 读取，零修改、零拷贝专有二进制进仓库。
- **双模运行**：自动识别本地只读供体（`LOCAL_DONOR_VERIFIED`），并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` / `--clean-room` 下切换确定性合成洁净室夹具（`CLEAN_ROOM_SYNTHETIC_VERIFIED`）。

---

## 2. 三大核心审计器与实证结果

### 2.1 `ufu_container_auditor.py` — 无密钥 `UFU` / `FDAT` / `UDTRFIRM` & `SDM2` 结构审计器
- **信封与尾标几何校验**：校验 `\x89UFU\r\n\x1a\n` 头部、`FDAT` 块载荷与尾标 `0x110`（272 字节 = `16B IV` + `256B RSA-2048` 签名）对齐与非退化检查。
- **`5L+6S` 跨机型防砖门控**：校验 `Model ID = 0x91030080`（`ILME-FX3`），当检测到 `0x91030082`（`ILME-FX3A`）等跨机型包时立即返回 `5L+6S_MODEL_ID_MISMATCH_BRICK_GUARD`。
- **1024B `<HH` 分块帧与 `UDTRFIRM` 清单**：校验每 1024 字节块首 4 字节 `<HH`（u16 校验和 + 载荷长度/`0x8000` 终结标志），并逐条校验 `UDTRFIRM` 分区（`nflasha3` / `nflasha7` / `nflasha15`）SHA-256 摘要。
- **`SDM2`（`8246` / `2.00`）分区表**：解析 30 项 `<IIII` 分区描述符，精确识别 `type == 5 and (flag & 1)` 的 AES-XTS-256 加密分区（`/dev/cnflasha3,7,8,12,15`）与明文分区（`p1,p2,p5,p6,p18,p30`），校验零扇区重叠与 LBA `< 0x80` 冲突。

### 2.2 `haita_bk4_feature_analyzer.py` — FX3 v7.02 `ALCIN_UUD` vs FX6 v6.01 `HAITA`/`BK4` 差异与防砖证明
使用 C 级 `bytes.find` / 字节正则扫描本地只读 `appFw.so`（总耗时 `< 0.25s`）：

| 维度 | FX3 v7.02 `appFw.so` (`79,015,712 B`) | FX6 v6.01 `appFw.so` (`50,520,424 B`) |
| :--- | :--- | :--- |
| **`PRODUCT_MODEL_*` 类别数** | **`9`**（`ALCIN_UUD`, `DZ`, `GL`, `GS`, `LAX`, `LS`, `SA`, `YS`, `YT`） | **`28`**（含 `CHAPLIN`, `ALCIN_UUD`, `ALCIN2`, `OT_UUD`, `TK_UUD` 等） |
| **`TYPE_MENU_ITEM_*` 裁剪表** | **`13`** 项（显式按 `ALCIN_UUD`/`LAX`/`LS` 裁剪） | `0`（Cinema Line 原生菜单表） |
| **`*HAITA*` 互斥/门控符号** | **`7,643`**（含 `6` 项 `PRM_HAITA_*`） | **`3,329`**（含 `3` 项 `PRM_HAITA_*`） |
| **`*FEATURE_MANAGER*` / `BKID_*`** | `98` / `72` | `85` / `5,534` |
| **Open-Gate 字符串** | `False`（均缺失） | `True`（含 `IMAGER_SCANMODE_FF_5K_3_2`、`VIDEO_FORMAT_5016x3344P`、`SELECT_CODEC_X_OCN_LT`） |
| **`BK4` u32 表命中** | `0x02cf00d7`: `2` | `0x02cf1443`: `3` · `0x02cf1453`: `3` · `0x02cf00d7`: `2` |

- **数学防砖证明（`BLOCKED_PRODUCT_MODEL_NVRAM_HAZARD`）**：直接篡改 FX3 `Backup.bin` 中的 `PRODUCT_MODEL` 会联动切换 `feature_manager::update_product_model()` 索引的 `IMX510` 传感器、机械快门、EVF/LCD 与散热曲线表，引发硬件/校准失配变砖风险；而仅改 `0x02cf00d7` 亦因缺乏 AVC/HEVC 编码配置文件与 Remote SDK `0x9203` 描述符无法激活 Open Gate。相比之下，Stage-A/B 运行 FX6 `appFw.so` + 内存态 RAM-Shadow `BK4\0` 实现 `flash_mutation_bytes = 0` 且 100% 保持原厂硬件校准安全。

### 2.3 `uxc_ldec_inspector.py` — `.uxc`/`uxd\x07` 资源容器与无 `/dev/ldec` 纯 CPU 解码器
- **容器实证（FX6 `share/app`，`62` 个 `.uxc` 包）**：
  - `image_00_169.uxc`（`3,941,000 B`，魔数 `uxd\x07`，`ns=0`）：`1,614` 索引槽、`1,610` 枚非空精灵（含 `22` 枚 9-patch 复合精灵，记录类型 `0x1a`），通过 `payload_offset = record_offset + 4 + rel_offset` 与 `((w + 15) & ~15)` 对齐步距精确提取。
  - `string_english_2.uxc`（`ns=2`，`5,915` 条 UTF-8 字符串，`0x1e`）、`string_english.uxc`（`ns=1`，`5,044` 条）、`color_cmn.uxc`（`ns=6`，`27` 项，`0x3a`）、`lang_cmn.uxc`（`ns=5`，`47` 项）、`style_cmn.uxc`（`ns=3`，`64` 项）。
- **纯 CPU Sony LDEC/LZ77 解码与像素转换**：完整实现 `0x0F`（raw 块）与 `0xF0`（LZ77 位标志 + `3..64` 长度查找表）边界安全解码（完全无需 `/dev/ldec` 内核驱动），并验证 `RGBA4444` / `RGBA8888` / `ARGB4444` / `A8` -> `ARGB8888` 像素转换一致性。

---

## 3. 验证记录

1. **CLI 确定性输出**：
   - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all` → `all_checks_passed: true`（`1.13s`）
   - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --clean-room` → `all_checks_passed: true`（`0.07s`）
2. **28 项单元测试（双模式全过）**：
   - Local Donor 模式：`Ran 28 tests in 1.275s — OK`
   - `FX3_FX6_FORCE_CLEAN_ROOM=1` 模式：`Ran 28 tests in 0.152s — OK`
