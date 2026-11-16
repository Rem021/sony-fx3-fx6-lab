# Wave-18 Global Public Intelligence Report: Sony `054C:0336` / `054C:0DA1` Service USB Transport, `ilc32g12m-ipsxmp` BIONZ XR `libmpr.so` / `Avbbc` / `DMM` Pools, and Linux `4.9` AArch64 `ld-2.25.so` `PT_LOAD` Alignment

- **日期**：2026-11-15
- **任务**：Task H155 — Phase 145（Wave-18 全球公开情报 + VM Stage 25 Real-HW `appFw.so -> Stock FX3 libmpr.so / DmmCfg.bin` 录像协同仿真）
- **信息分层原则**：严格区分 **公开互联网实证（Web Search）**、**本地只读供体实测（`os.O_RDONLY`）** 与 **未执行项（物理真机实拍未接驳）**。

---

## 1. 结论先行（3 条核心情报）

1. **Sony `054C:0336` vs `054C:0DA1` 服务模式 USB 传输**：公开生态确认 `054C:0336` 是索尼相机经 *Senser* 握手从 Mass Storage（如 FX3 `054C:0DA3`、A7 IV `054C:0DA5`、A7C II `054C:0E8A`）切入 **Service / Updater 模式** 的标准 USB PID（Vendor-Specific `0xFF/0x00/0x00`），且卡在 `/setting/updater/mode1` 时会直接黑屏枚举 `054C:0336`；而 **`054C:0DA1` 在公开 USB ID 库（`usb.ids`、`libgphoto2`、`Sony-PMCA-RE`、Windows 驱动库）中无任何索尼相机记录**（不可假定为已知 FX3/FX6 公开 PID）。
2. **`ilc32g12m-ipsxmp` / `libmpr.so` / `Avbbc` / `DMM` 内存池**：公开社区（`Erlla/sony-a7m4-custom-firmware`、`DavidBuchanan314/ILCE-7M4-RE`、`Hearts-Ace/sony-a7r5-custom-firmware`、`cokeenet/zve10-qemu`、`ma1co/OpenMemories-Tweak`）证实 `libmpr.so`（Media Processing Runtime）与 `libInfraAvbbc` 属于 Sony AP Linux 音视频/媒体录制核心中间件，配合 `appFw.so` 与 Cortex-R5 `CPAPP-B.BIN` 协同工作；但 **`ilc32g12m-ipsxmp`、`ilc8g8g-ipsxcp` 与 `DmmCfg.bin` 20 个共享 MAIN DMM 单元编号在公开网络零命中**，完全来自本地 `os.O_RDONLY` 只读二进制实测。
3. **Linux `4.9` AArch64 `ld-2.25.so` `dlopen` / `LD_PRELOAD` `PT_LOAD` 页对齐**：glibc 2.25 `elf/dl-load.c` 强制校验 `(ph->p_align & (GLRO(dl_pagesize) - 1)) == 0` 与 `((ph->p_vaddr - ph->p_offset) & (ph->p_align - 1)) == 0`，否则触发 `"ELF load command alignment not page-aligned"`。本地实测 FX3 `7.02` 原机 `ld-2.25.so`（`120,616 B`）、`libmpr.so`、`libsecvlt.so` 与 `im.elf` **全部采用 `PT_LOAD p_align = 0x10000`（64 KiB）**；任何用于 Stage-B 的 `LD_PRELOAD` `.so` 垫片必须使用 `-Wl,-z,max-page-size=65536` 链接。

---

## 2. 主题 A：Sony `054C:0336` 与 `054C:0DA1` Service USB 传输情报

| USB VID:PID | 公开检索状态 | 协议/角色细节 | 实务约束与风险 |
|---|---|---|---|
| `054C:0336` | **已确认**（Windows Driver DB / Sony Seus / `Sony-PMCA-RE` / `a7c2-tools`） | `USB\VID_054C&PID_0336`，Class `0xFF` / Subclass `0x00` / Protocol `0x00`（"Sony USB Device"）。相机在普通 `MSC` PID 上完成 Sony *Senser* challenge-response 握手后重枚举为此 PID 进入 Service / Updater 模式。 | 1. Windows 需针对 `MSC` PID 与 `054C:0336` 分别绑定 `libusb-win32`（社区实测 Zadig 2.8 较稳，Zadig 2.9 / `libusbK` 在旧冻结工具上偶发超时）；Linux 需 `udev` `054c:0336` 权限。<br>2. 若 `/setting/updater/mode*` 残留，机身会黑屏直进 `054C:0336`，常规官方固件升级包会报 `"Invalid model"`，必须通过服务模式清除模式标志或依赖冷备恢复。 |
| `054C:0DA1` | **公开零索引** | `usb.ids`、`libgphoto2`、`Sony-PMCA-RE` 与 Windows 驱动库均无 `054C:0DA1` 记录（独立 USB 厂商表中 `0DA1` 是 *Suzhou Peter's Precise Industrial* 的 VID）。 | 相邻已确认索尼相机 PID：`054C:0DA3`（`ILME-FX3`）、`054C:0DA5`（`ILCE-7M4` Mass Storage）、`054C:0E8A`（`ILCE-7CM2`）。严禁将 `054C:0DA1` 误当作 FX3 通用公开标识。 |

---

## 3. 主题 B：`ilc32g12m-ipsxmp` BIONZ XR `libmpr.so` / `Avbbc` / `DMM` 内存池

### 3.1 公开开源社区已证实信息
- **`CXD90057` (`Mira`) AP + `CXD90058` CP 双核拓扑**：AP 为 4 核 64-bit ARM Cortex-A35 运行 SCEL Linux `4.9` 与单体 `/lib/appFw.so`；CP 为 32-bit ARM Cortex-R5 运行 TOPPERS/FMP RTOS (`CPAPP-B.BIN`)，承载实时 ISP、传感器读出与 3D 色彩网格（参考 `DavidBuchanan314/ILCE-7M4-RE`、`Hearts-Ace/sony-a7r5-custom-firmware`）。
- **`libmpr.so`（Media Processing Runtime）**：在 BIONZ X（`cokeenet/zve10-qemu`、`ma1co/OpenMemories-Tweak` Issue #130）与 BIONZ XR（`Erlla/sony-a7m4-custom-firmware` `fs/lib/libmpr.so`）中均作为核心媒体处理动态库运行，负责录制控制（`REC_LIMIT_TIME`、编码启动/停止调度）与音频/EXIF 等媒体服务。
- **`libInfraAvbbc`**：在公开逆向文档（`cokeenet/zve10-qemu` `GEN1_SYSTEM_STRUCTURE.md`）中归属音视频（`Avbbc`）中间件层，与 `libIMDB.so`、`libMWF.so`、`appFw.so`、`codec_drv.ko` 协同完成 `ParameterControl` 与编码管线控制。
- **公开空白边界**：`"ilc32g12m"`、`"ipsxmp"` 与 `DmmCfg.bin` 具体内存池单元表在公开互联网 **无任何命中**。

### 3.2 本地 `os.O_RDONLY` 只读供体实证（非公开情报，严格隔离）
- **Stock FX3 `7.02` vs FX6 `6.01` `libmpr.so`**：FX3 `3,517,008 B`（`3,541` 导出，依赖 `libsecvlt.so` `10,216 B` / `9` 导出）vs FX6 `28,921,824 B`（`4,271` 导出，无 `libsecvlt.so`）。FX6 `appFw.so` 导入的 `89` 个 `libmpr.so` 符号中，**`74` 个核心录制符号直通兼容**，**`15` 个 FX6 专属符号需 `LD_PRELOAD` 垫片拦截**。
- **`DmmCfg.bin` 尾戳与单元表**：
  - Stock FX3 AP `DmmCfg.bin`（`66,796 B`）：`603` units / `290` rules，尾戳 `"for ilc32g12m-ipsxmp     2025/06/20 15:43:19"`。
  - FX6 AP `DmmCfg.bin`（`59,364 B`）：`556` units / `259` rules，尾戳 `"for ilc32g12m-ipsxmp     2025/10/02 12:16:04"`。
  - Stock FX3 CP `DmmCfg.bin`（`43,320 B`）：`348` units / `164` rules，尾戳 `"for ilc8g8g-ipsxcp       2025/02/10 10:35:08"`。
  - **20 个共享 `MAIN` DMM 单元 ID**（`700..528413`）在双机身 AP 表中均为 `1` extent（远小于 `GetDmmExtList` `0xa8` 上限 `8`）。

---

## 4. 主题 C：Linux `4.9` AArch64 `ld-2.25.so` `dlopen` `PT_LOAD` 页对齐行为

### 4.1 glibc 2.25 `elf/dl-load.c` 机制
在 Linux `4.9` AArch64 与 `glibc 2.25` 时代（早于 `glibc 2.35+` BZ #28688 / #28676 / #28838 修复），`ld-2.25.so` 在 `dlopen` / `LD_PRELOAD` 装载共享库时执行两项硬校验：
1. `(ph->p_align & (GLRO(dl_pagesize) - 1)) != 0` → 直接失败并报错 `"ELF load command alignment not page-aligned"`。
2. `((ph->p_vaddr - ph->p_offset) & (ph->p_align - 1)) != 0` → 直接失败并报错 `"ELF load command address/offset not properly aligned"`。

若目标内核配置为 `64 KiB` 页（`GLRO(dl_pagesize) == 0x10000`），而 `.so` 使用 `0x1000`（`4 KiB`）`PT_LOAD p_align`（例如旧版 `lld` 或未传 `--page-size=65536` 的 `patchelf`），则 `dlopen` / `LD_PRELOAD` 必定在映射阶段直接失败；且不同权限的 `PT_LOAD` 段若跨越同一 `64 KiB` 边界，无法仅靠 `patchelf` 事后修补，必须从目标文件重新链接。

### 4.2 本地 FX3 `7.02` 原机 ELF 验证
- `ld-2.25.so`（`120,616 B`）：`PT_LOAD` 段 `p_align = 0x10000`（`0x0/0x0` `R E`、`0x2bc20/0x1bc20` `RW`，`p_vaddr - p_offset = 0x10000`，模 `0x10000 == 0`），且二进制内置上述两句报错字符串与 `LD_PRELOAD` 解析逻辑。
- `libmpr.so`（FX3 `7.02` & FX6 `6.01`）、`libsecvlt.so`（FX3 `7.02`）、`im.elf`（FX3 `7.02`）：`PT_LOAD` 全部为 `p_align = 0x10000`（64 KiB 对齐）。
- **Stage-B 工程推论**：用于拦截 15 个 FX6 专属 `libmpr.so` 符号的 `LD_PRELOAD` 垫片 `.so` 在交叉编译链接时必须显式携带 `-Wl,-z,max-page-size=65536`（可选配 `-Wl,-z,common-page-size=65536`），并在打包前经 ELF64 `PT_LOAD` 门控校验。

---

## 5. 参考来源（Web Grounding）

- Sony Service USB (`054C:0336`) & `054C:0DA3` / `054C:0DA5`：`ma1co/Sony-PMCA-RE`、`a7c2-fl23-research` / `a7c2-tools`、Windows `USB\VID_054C&PID_0336` 驱动库、`usb.ids`
- BIONZ XR / `libmpr.so` / `Avbbc`：`Erlla/sony-a7m4-custom-firmware`、`DavidBuchanan314/ILCE-7M4-RE`、`Hearts-Ace/sony-a7r5-custom-firmware`、`leogenot/sony-a7iv-feature-research`、`cokeenet/zve10-qemu`、`ma1co/OpenMemories-Tweak`
- AArch64 `ld-2.25.so` `PT_LOAD` 对齐：glibc `elf/dl-load.c`、LLVM D25079、glibc BZ #28688 / #28676 / #28838、Debian/Fedora/openSUSE 64 KiB page-size 迁移文档
