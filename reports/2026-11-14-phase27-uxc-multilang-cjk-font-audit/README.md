# Hydrogen-18｜Phase 27 全量 62 包 `.uxc` 多语言对齐、CJK/JP/EN 字体 `cmap` 覆盖与纯 CPU `LDEC` 全精灵校验报告

> **任务**：`Hydrogen-18`（Wave 3+）  
> **交付包**：[`outputs/fx3-firmware-lab/`](../../outputs/fx3-firmware-lab/README.md)  
> **新增模块**：[`uxc_multilang_and_font_verifier.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/uxc_multilang_and_font_verifier.py) · [`test_uxc_multilang_and_font.py`](../../outputs/fx3-firmware-lab/tests/test_uxc_multilang_and_font.py)

---

## 1. 全量 62 包 FX6 `.uxc` 多语言一致性实证（`O_RDONLY`）

在 FX6 v6.01 `nflasha15-files/share/app/` 全部 **`62` 个 `.uxc` 资源包** 中逐包只读解析并校验：

| 分组 | 包数量 | 命名空间 (`ns`) | 总槽位 (`slots`) | 有效字符串 / 记录 | 空槽 (`0xFFFF`) | UTF-8 严苛解码 | 相对 English 槽位 & `resid16` 错位 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`string_<lang>.uxc`**（29 语种） | `29` | `1` | `5,063` | **`5,044`** | `19` | **100% 通过**（0 截断/损坏） | **`0` 错位**（1:1 槽位对齐） |
| **`string_<lang>_2.uxc`**（29 语种） | `29` | `2` | `5,921` | **`5,915`** | `6` | **100% 通过**（0 截断/损坏） | **`0` 错位**（1:1 槽位对齐） |
| **公共配置包** (`color_cmn` / `lang_cmn` / `style_cmn`) | `3` | `6 / 5 / 3` | — | `27 / 47 / 64` | — | 有效 (`0x3a` 等记录) | — |
| **图像精灵集** (`image_00_169.uxc`) | `1` | `0` | `1,614` | **`1,610`**（含 `22` 枚 9-patch） | `4` | — | — |

重点语言样本（`string_*_2.uxc`, `ns=2`, `5,915` 条）：
- `string_english_2.uxc`：`NTSC/PAL Area Mismatch` / `Media Near Full`
- `string_simplifiedchinese_2.uxc`：`NTSC/PAL区域设置不匹配` / `媒体容量将满`
- `string_traditionalchinese_2.uxc`：`NTSC/PAL區域不符` / `媒體空間將滿`
- `string_japanese_2.uxc`：`NTSC/PAL Area Mismatch` / `メディア残量がわずかです`

---

## 2. FX6 vs FX3 `.uxc` 跨机身容器架构差异与隔离结论

同时只读审计本地已解包的 FX3 v7.02 `usr/share/app/`（共 **`121` 个 `.uxc` 包**）：

| 维度 | FX6 v6.01 (`PRODUCT_MODEL_CHAPLIN`) | FX3 v7.02 (`PRODUCT_MODEL_ALCIN_UUD`) |
| :--- | :--- | :--- |
| **总 `.uxc` 包数** | `62` | `121`（含 `LayoutMaster_*`, `master_*`, `_32`/`_43`/`_169` 精灵） |
| **语种数** | `29` | `34` |
| **字符串分片结构** | `ns=1` (`5,044`) + `ns=2` (`5,915`) | `ns=39` (`2,692`) + `_g` `ns=3` (`1,390`) + `34` 个 `_f` (`hdr_flag=15`) |
| **跨机身二进制兼容** | **`False`**（命名空间与槽位表完全不兼容） | **`False`** |
| **隔离裁决** | **`MOUNT_FX6_UXC_WITH_FX6_APPFW_ONLY`** | 严禁将 FX3 字符串包与 FX6 `appFw.so` 混挂 |

---

## 3. CJK / JP / EN 字体 `cmap`（Format 4 & 12）与全字形覆盖审计

纯 Python 解析 FX6 `share/app/` 中全部 6 个字体文件（识别 Monotype `LTT\n` 链接头中的 `embeddedoffset`/`embeddedsize` 内嵌 `sfnt` 表与 `Sony_DI_Icons.ttf`）：

| 字体文件 | 容器 | 内嵌 `sfnt` | `cmap` 格式 | 映射码点数 | BMP / 非 BMP |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `UniversOTS-SJ_wIcon.ltt` | `LTT` | `2` (`UniversOTS-SJ` + `DevanagariOTS`) | `(4,)` | `1,511` | `1,511 / 0` |
| `HeiseiKakuGothW5-SJ_wIcon.ltt` | `LTT` | `1` | `(4,)` | `7,137` | `7,137 / 0` |
| `MYingHeiC-GB18030-SJ_wIcon.ltt` | `LTT` | `1` | `(4, 12)` | **`28,825`** | `28,623 / 202` |
| `MYingHeiC-Big5HKSCS-SJ_wIcon.ltt` | `LTT` | `1` | `(4, 12)` | **`18,894`** | `17,181 / 1,713` |
| `MYingHeiC-KSX1001-SJ_wIcon.ltt` | `LTT` | `1` | `(4,)` | `8,331` | `8,331 / 0` |
| `Sony_DI_Icons.ttf` | `TTF` | `1` | `(4,)` | **`1,720`** | `1,720 / 0` |

### 四大核心语种 Unicode 码点覆盖实测
- **`ns=2`（`*_2.uxc` 5,915 条，含菜单核心与提示文案）**：
  - `english` (`122` 码点)、`simplifiedchinese` (`796` 码点)、`traditionalchinese` (`797` 码点)、`japanese` (`604` 码点) → **全量 `100.00%` 覆盖（`0` 缺失）**。
- **`ns=1`（`*.uxc` 5,044 条）**：
  - **标准 Unicode 文本码点**：`english` (`132`)、`simplifiedchinese` (`762`)、`traditionalchinese` (`769`)、`japanese` (`647`) → **`100.00%` 覆盖（`0` 缺失）**。
  - **私有区图标码点（PUA `U+E000..U+F8FF`）**：`121 / 123` 命中 `Sony_DI_Icons.ttf`，仅 `U+E6DA`、`U+E6DB`（`string_*.uxc` 槽位 `5042`/`5053` Key Lock 图标标记）未映射于 `Sony_DI_Icons.ttf` `cmap`。

---

## 4. 全量纯 CPU `LDEC` 精灵解压与 SHA-256 校验扫盘

无需 `/dev/ldec` 内核驱动，纯 CPU 切片加速 `fast_decode_ldec_lz77` 完成全量校验：
- **FX6 `image_00_169.uxc`**：全部 **`1,610 / 1,610`** 枚精灵（含 `22` 枚 9-patch）100% 解压通过，`0` 失败，总解压字节 **`51,972,736 B`**，确定性图集摘要 `9091dcc06a5aae9bc615e3834cd21697d07c20d837f68006c0a89294b57a687f`。
- **FX3 `image_00_169.uxc` / `image_01_169.uxc` / `image_02_169.uxc`**：前 16 枚采样全数解压通过（`16/16`），证明 `LDEC` 流格式跨机身一致且硬件完全可替代。
- **Clean-Room 合成夹具**：当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或 `--clean-room` 时，自动生成包含真实 `head` + `cmap`（Format 4 & Format 12 非 BMP `U+20000`）的合成 `.ttf`、对称 `ns=1/ns=2` 四语 `.uxc` 包与 `.uxd` 精灵包执行全链闭环验证。

---

## 5. 验证结果

1. **Local Donor 模式（`PYTHONDONTWRITEBYTECODE=1` + `/usr/bin/python3 -B`）**：
   - `outputs/fx3-firmware-lab/tests` 全部 **`51` 项单元测试在 `2.696s` 内全数通过（`OK`）**（`< 4s`）。
2. **`FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室模式**：
   - 全部 **`51` 项单元测试在 `0.321s` 内全数通过（`OK`）**。
3. **CLI 确定性输出**：
   - `python3 -B -m fx3_firmware_lab audit-multilang --clean-room` 两次调用输出完全一致 JSON，`all_checks_passed: true`, `hardware_ldec_required: false`。
