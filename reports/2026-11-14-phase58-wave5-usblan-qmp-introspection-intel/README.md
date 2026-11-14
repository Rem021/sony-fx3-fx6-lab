# Phase 58 — Wave-5 Global Sony USB-C Ethernet (`CDC-NCM`/`RNDIS`), `Monitor & Control` & QEMU Non-Intrusive Guest Introspection (`QMP` / `libqemu-plugin` / `GDB RSP`) Sync + Stage 7 Tracer

# 第 58 阶段 — Wave-5 全球索尼 USB-C 以太网（`CDC-NCM`/`RNDIS`）、`Monitor & Control` 与 QEMU 非侵入式客体自省情报同步暨 Stage 7 追踪器

**Date / 日期**: `2026-11-14`  
**Owner / 负责代理**: Hydrogen-51 (`antigravity`, isolated child worktree)  
**Target Module / 目标模块**: [`outputs/fx3-vm/qmp_guest_introspection_tracer.py`](../../outputs/fx3-vm/qmp_guest_introspection_tracer.py)  
**Suite Orchestrator / 联合编排器**: [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`Stage 7`, `--skip-phase58`)  
**Machine-Readable Matrix / 结构化矩阵**: [`wave5_alignment_matrix.json`](./wave5_alignment_matrix.json)  
**Unit Tests / 单元测试**: [`outputs/fx3-vm/tests/test_qmp_guest_introspection_tracer.py`](../../outputs/fx3-vm/tests/test_qmp_guest_introspection_tracer.py) (`28` dual-mode tests; `183` total tests in `outputs/fx3-vm/tests/`)  
**Hard Safety Redlines / 硬性安全红线**: `nop_count == 0`, `guest_code_modification_bytes == 0`, `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `nvram_persistent_writes == 0`, `physical_device_writes == 0`, `guest_text_sw_breakpoints == 0`, `os.O_RDONLY` only.

---

## 1. Executive Summary / 阶段总览

**English**:  
Phase 58 synchronizes current public technical documentation across two critical engineering axes and integrates them as **Stage 7** (`stage7_phase58_qmp_introspection`) of [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py):
1. **Wired USB-C Ethernet (`USB-LAN` `CDC-NCM`) & `Monitor & Control` / `PTP-IP` (`TCP 15740`) under `P12` Airplane-Mode**: Demonstrating how wired `1 Gbps` `CDC-NCM` adapters (`RTL8153` / original `AX88179`) keep **Monitor & Control**, **Content Browser Mobile**, and **Camera Remote SDK** fully operational over `eth0` (false color, waveform, focus map, touch focus, SSH/TLS Access Authentication) while Wi-Fi (`wlan.ko`) and Bluetooth (`/dev/ttyAMA3`) stay **100% isolated (`0` HCI TX packets, immune to Sony Notice `00342260` `WF-12`)**.
2. **Non-Intrusive QEMU Guest Introspection (`QMP` / `HMP` / `TCG Plugins` / `GDB RSP`)**: Building a clean-room QMP JSON-RPC protocol client/simulator (`qmp_capabilities`, `query-status`, `query-cpus-fast`, `human-monitor-command xp`/`gva2gpa`/`info registers`, `pmemsave mem://`) plus `libqemu-plugin` and `Qqemu.PhyMemMode:1` hardware watchpoint specs to inspect `KEY_MB_PHYS` (`0x41DF00000`), `CTRL_MB_PHYS` (`0x41E000E00`), `GPE0_PHYS` (`0x41E001000`), and `MHLX` (`0xF0800000` / `0x41DF01000`) with **zero guest code modification** (`nop_count == 0`, `cp_mutation_bytes == 0`).

**中文摘要**:  
第 58 阶段同步了两项核心公开技术情报，并将其作为 **Stage 7**（`stage7_phase58_qmp_introspection`）向后兼容地接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（支持 `--skip-phase58`）：
1. **有线 USB-C 以太网（`USB-LAN` `CDC-NCM`）与 `P12` 飞行模式下的 `Monitor & Control` / `PTP-IP`（`TCP 15740`）**：证明通过 `1 Gbps` `CDC-NCM` 网卡（`RTL8153` / 原版 `AX88179`），相机可在 `P12` 飞行模式完全关闭 Wi-Fi 与蓝牙（`0` 条 HCI TX、彻底免疫索尼 `00342260` / `WF-12` 死循环）的前提下，经由 `eth0` 持续提供假色、波形图、对焦图、触控对焦与 SSH/TLS Access Authentication 远程监看控制，同时在 `TCP 15740` 上对固件刷写/NVRAM/校准操作码实施失效关闭拦截。
2. **非侵入式 QEMU 客体自省（`QMP` / `HMP` / `libqemu-plugin` / `GDB RSP`）**：在不修改任何客体指令字节（`nop_count == 0`、`cp_mutation_bytes == 0`、`guest_text_sw_breakpoints == 0`）的情况下，完整实现 `QMP` JSON-RPC 协商与物理内存只读解码（`KEY_MB_PHYS` `SRM3KYE5`、`CTRL_MB_PHYS` `0x4658364C` `'FX6L'`、`GPE0_PHYS` `fx6_px` `0xFFF08018` 与 `MHLX` 环形槽位）。全套 `make verify-coemulation` 7 阶段耗时 **`1.167s`**（本地供体）/ **`0.329s`**（洁净室），`outputs/fx3-vm/tests/` 全部 **`183` 项**双模式单测 100% 通过。

---

## 2. Wave-5 Live Intelligence Sync / Wave-5 公开情报同步

### 2.1 Sony FX3 / FX6 Wired USB-LAN (`CDC-NCM` vs `RNDIS`) & `Monitor & Control` / `PTP-IP` (`TCP 15740`)

| Topic / 维度 | `ILME-FX3` (`Ver. 4.00+` / `v7.02`) | `ILME-FX6` (`Ver. 4.00+` / `v6.02`) | FX3/FX6 Lab Enforced Invariant / 实验室强制不变量 |
| :--- | :--- | :--- | :--- |
| **Menu Enablement / 菜单开启路径** | `(Network) -> [USB-LAN/Tethering] -> [USB-LAN Connection] -> [On]` | `[Network] -> [Access Authentication]` (User / Generate Password) + `[Wired LAN] -> [Setting] -> [On]` + `[Camera Remote Control] -> [Enable]` | Verified in FX6 donor `libNetServiceEther.so` (`EN_STATE_USB_CONNECTED_USB_ETHER_DEVICE`, `eth0.dhcp`). |
| **USB Gadget Class / USB 以太网协议** | Embedded Linux **`CDC-NCM`** (`cdc_ncm.ko` `0x02/0x0D`) | Embedded Linux **`CDC-NCM`** (`cdc_ncm.ko` `0x02/0x0D`); `rndis_host.ko` exists for host-side tethering | Enforces `USB_CLASS_CDC_NCM`; rejects `RNDIS` / `CDC-ECM` on USB-LAN interface. |
| **Adapter Chipset / 网卡芯片兼容性** | `1 Gbps` **`RTL8153`** or original **`ASIX AX88179`**; `AX88179A/B` and `2.5G/5G/10G` adapters fail | `1 Gbps` **`RTL8153`** or original **`AX88179`** | Rejects `AX88179A`, `AX88179B`, `RTL8156_2.5G`, `AQC111U_5G`, `10GBASE_T`, or `link_speed_mbps != 1000`. |
| **IPv4 Manual Gateway Trap / 手动网关陷阱** | `[Manual]` static IP **requires** a valid `Default Gateway` inside the same IPv4 subnet | Standard Wired LAN DHCP / Manual IPv4 | `evaluate_usblan_link_under_p12()` rejects blank or off-subnet gateways (`MISCONFIGURED_MISSING_SAME_SUBNET_GATEWAY`). |
| **Host OS Constraint / 宿主机限制** | iOS/iPadOS/macOS (`Monitor & Control` / `Camera Remote SDK` v2.02.00) support direct & router LAN; Android rejects direct wired / switching-hub USB-LAN | iOS/iPadOS/macOS/Linux/Windows (`Monitor & Control`, `Content Browser Mobile`, `Camera Remote SDK`) | Documented in FX3/FX6 operator guidance & matrix. |
| **Monitoring & Ports / 监看能力与端口** | Focus map, EL Zone, False Color (SDR/S-Log3), waveform, touch focus; **PTP-IP `TCP 15740`**, SSDP `UDP 1900`, SSH `22` / `80` / `8080` / `60152` / `64321` | Same + `Content Browser Mobile` | Whitelists read-only/safe touch-focus telemetry on `TCP 15740`; hard-blocks `0x9280..0x9282` FW update & `0x92F0..0x92F2` NVRAM/calibration opcodes. |
| **`P12` Airplane-Mode Immunity / `WF-12` 免疫** | `BK4\0` shadow `0x019e0012=00, 0x01a20002=00` disables Wi-Fi & BT (`0` HCI TX); **Sony Notice `00342260` (`WF-12`) neutralized** while `eth0` telemetry stays live | Same `BK4\0` + `libWlanResource.so 0x70d4` degraded isolation | `wf12_00342260_immune == True`, `wlan_disabled == True`, `bt_disabled == True`, `wdt_resets == 0`. |

**Verified Public Sony Citations / 已核验索尼公开参考链接**:
- Sony *Monitor & Control* Help Guide: <https://helpguide.sony.net/promobile/mc/v1/en/index.html>
- Supported Cameras (`ILME-FX3` Ver. 4.00+, `ILME-FX6` Ver. 4.00+/5.00+ Wired LAN): <https://helpguide.sony.net/promobile/mc/v1/en/contents/supported_camera.html>
- Connecting Camera via USB-LAN / Router (`ILME-FX3`/`FX3A`/`FX30` gateway & Android rules): <https://helpguide.sony.net/promobile/mc/v1/en/contents/connecting_router_ILCE-9M3.html>
- Connecting `ILME-FX6` via Wired LAN & Access Authentication: <https://helpguide.sony.net/promobile/mc/v1/en/contents/connecting_router.html>
- Shooting Assist Functions (False Color, Waveform, Focus Map, Touch Focus): <https://helpguide.sony.net/promobile/mc/v1/en/contents/shooting_assist_functions.html>
- Sony Camera Remote SDK (`v2.02.00` June 2026 — USB / Wired LAN / Wi-Fi): <https://www.sony.net/CameraRemoteSDK/>
- Sony Camera Remote Command (`ISO 15740` PTP / PTP-IP `TCP 15740`, SSDP `UDP 1900`, control ports): <https://www.sony.net/app/cameraremotecommand/en/index.html>

---

### 2.2 Non-Intrusive QEMU Guest Introspection (`QMP` / `HMP` / `libqemu-plugin` / `GDB RSP`)

| Mechanism / 机制 | Official Protocol / API Surface / 官方接口 | FX3/FX6 Stage 7 Aperture Mapping / 实验室物理观测窗口 | Zero-Mutation Guarantee / 零修改保证 |
| :--- | :--- | :--- | :--- |
| **QMP JSON-RPC + OOB** | `{"QMP":{"capabilities":["oob"]}}` greeting -> `qmp_capabilities` negotiation -> `query-status`, `query-cpus-fast` (`CpuInfoFast`), `pmemsave`, `human-monitor-command` | `SimulatedQmpGuestTransport` + `QmpGuestIntrospectionClient` | Rejects pre-capability commands (`CommandNotFound`) and all mutating commands (`stop`, `cont`, `system_reset`, `quit`, disk `pmemsave`). |
| **HMP Physical Memory & VA Translation** | `info registers`, `gva2gpa <vaddr>`, `xp /<N>xw <paddr>` (physical memory examine without touching guest MMU) | Decodes `KEY_MB_PHYS` (`0x41DF00000` `'SRM3KYE5'`) and `CTRL_MB_PHYS` (`0x41E000E00` `0x4658364C` `'FX6L'`, `P4 ND=Clear`, `bk4_locked`) | Read-only physical bus inspection; `nop_count == 0`, `guest_code_modification_bytes == 0`. |
| **`pmemsave` RAM Ring Dump** | `pmemsave val=<paddr>, size=<bytes>, filename=<target>` | Captures `mem://gpe0_slice.bin` (`GPE0_PHYS` `0x41E001000`, verifying `fx6_px` `0xFFF08018` amber parity) and `mem://mhlx_mmio.bin` + `mem://mhlx_ring.bin` (`0xF0800000` / `0x41DF01000`, `0x0416`, `0x0400`) | Pure in-memory `mem://` URIs; `physical_device_writes == 0`, zero `.bin` files written to disk. |
| **QEMU TCG Plugins (`libqemu-plugin`)** | `include/plugins/qemu-plugin.h`, `QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION`, `qemu_plugin_install`, `qemu_plugin_register_vcpu_tb_trans_cb`, `qemu_plugin_register_vcpu_mem_cb(QEMU_PLUGIN_MEM_RW)`, `qemu_plugin_read_memory_hwaddr`, `-plugin contrib/plugins/libhotblocks.so` | Non-intrusive memory watch hooks on `KEY_MB_PHYS`, `CTRL_MB_PHYS`, `GPE0_PHYS`, `MHLX_PHYS` | Out-of-band TCG instrumentation; zero guest `.text` patching (`cp_mutation_bytes == 0`). |
| **QEMU GDB RSP (`gdbstub`)** | `-s`/`-S`/`-gdb`, TCG unlimited hardware watchpoints (`Z2,<phys>,4`), `Qqemu.PhyMemMode:1` / `qqemu.PhyMemMode` | Physical watchpoints on `KEY_MB_PHYS` (`41df00000`) & `CTRL_MB_PHYS` (`41e000e00`) | `guest_text_sw_breakpoints == 0` (no `BRK` / `EBREAK` software breakpoint injection). |

**Verified Public QEMU Citations / 已核验 QEMU 官方文档链接**:
- QEMU QMP Reference Manual (`qmp_capabilities`, `oob`, `query-status`, `query-cpus-fast`, `pmemsave`, `human-monitor-command`): <https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html>
- QEMU Human Monitor (`xp`, `x`, `gva2gpa`, `gpa2hva`, `info registers`): <https://www.qemu.org/docs/master/system/monitor.html>
- QEMU TCG Plugins API (`qemu-plugin.h`, `QEMU_PLUGIN_VERSION`, `libhotblocks.so`): <https://www.qemu.org/docs/master/devel/tcg-plugins.html>
- QEMU GDB Usage (`gdbstub`, TCG unlimited HW watchpoints, `Qqemu.PhyMemMode:1`): <https://www.qemu.org/docs/master/system/gdb.html>

---

## 3. Strictly Read-Only (`os.O_RDONLY`) FX6 Donor Artifact Receipts / 严格只读供体核验记录

| Key / 键名 | Donor Relative Path / 相对路径 | Size / 大小 | Verified SHA-256 / 核验校验和 | Verified Marker / 校验符号 |
| :--- | :--- | :---: | :--- | :--- |
| `fx6_cdc_ncm_ko` | `nflasha15-files/kmod/cdc_ncm.ko` | `32,208 B` | `8b992509f7a25f6c5d6ca6d27c22c6c2fa4539a25d1b3d405ea7dfc31fb843e2` | `cdc_ncm_rx_verify_nth16` |
| `fx6_rndis_host_ko` | `nflasha15-files/kmod/rndis_host.ko` | `14,064 B` | `f469d8d5624d0afd7a72734e4f651e6a63691c68ebf4cc63ea49df7821e035c4` | `RNDIS_MSG_QUERY` |
| `fx6_libnet_service_ether` | `nflasha15-files/lib/libNetServiceEther.so` | `175,376 B` | `5bc521ed8845a0be00be7d686b3519de478ca125d00731930624670c6f067dd0` | `EN_STATE_USB_CONNECTED_USB_ETHER_DEVICE` |
| `fx6_libinfra_ptp_control` | `nflasha15-files/lib/libInfraPtpControl.so` | `152,520 B` | `5af1afff957290bbd2519e237af5df761413e54193e149ee70189f32fe646a27` | `PTPT_EE_end_ip_remote` |
| `fx6_libptp` | `nflasha15-files/lib/libptp.so` | `77,408 B` | `21e212ae68a6d8fe1ae8fc4eb40bd3629e3f126a41ddfc1e00e750cd46a134aa` | `PTPT_open` |
| `fx6_libssh_infra_net` | `nflasha15-files/lib/libSshInfraNetworkCommon.so` | `14,568 B` | `ab57fe723a05171bc9bdaf4208147b5f7397a419b92c19624f389cde48a0ada4` | `InfraSshUtil` |

*(In `FX3_FX6_FORCE_CLEAN_ROOM=1` mode, local donor directories are blocked via sentinel path resolution and verified against pinned deterministic synthetic baselines.)*

---

## 4. Verification Receipts / 实测验证记录

1. **Standalone Phase 58 Tracer CLI (`qmp_guest_introspection_tracer.py`)**:
   - Local Donor (`O_RDONLY`): `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/qmp_guest_introspection_tracer.py --self-test --summary`  
     -> `[PASS] Phase 58 QMP Guest Introspection & USB-LAN Tracer | mode=LOCAL_DONOR_RDONLY nop=0 cp_mut=0 | ctrl=0x4658364c key=SRM3KYE5 mhlx_slots=2 | usblan=CDC-NCM/RTL8153(wf12_immune=True) ptpip_15740=5ok/4blocked | digest=74fc22811e3c` (**`0.070s`**).
   - Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/qmp_guest_introspection_tracer.py --self-test --summary`  
     -> `[PASS] Phase 58 QMP Guest Introspection & USB-LAN Tracer | mode=CLEAN_ROOM_SYNTHETIC nop=0 cp_mut=0 | ctrl=0x4658364c key=SRM3KYE5 mhlx_slots=2 | usblan=CDC-NCM/RTL8153(wf12_immune=True) ptpip_15740=5ok/4blocked | digest=9f5ec1809ffc` (**`0.067s`**).
2. **7-Stage Co-Emulation Suite (`make verify-coemulation`)**:
   - Local Donor (`O_RDONLY`): `make verify-coemulation` -> `rc=0`, `all_checks_passed=True`, **`1.167s`** (`< 2.5s` target).
   - Clean-Room: `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-coemulation` -> `rc=0`, `all_checks_passed=True`, **`0.329s`** (`< 2.5s` target).
3. **Unit Tests (`28` new Phase 58 tests + `183` total `outputs/fx3-vm/tests` dual-mode suite)**:
   - Phase 58 (`test_qmp_guest_introspection_tracer.py`): `28` passed in **`0.331s`** (Local Donor) / **`0.327s`** (Clean-Room).
   - Full `outputs/fx3-vm/tests/`: **`183` tests passed** in **`4.289s`** (Local Donor) / **`2.719s`** (Clean-Room) — both `< 4.5s`.
4. **Hygiene & Safety Audit (`make clean-audit`)**:
   - `[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.46s)` — zero `.bin`/`.pcap`/`.so`/`.elf`/`.ko`/`.cpio`/`.vfat`/`.pyc` or `__pycache__` artifacts.
