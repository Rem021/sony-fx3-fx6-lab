# Sony FX3 / FX5 / FX6 System Research & Emulator Lab (`FX3｜FX5 & FX6 系统研究`)

## 1. Project Identity & Scope
- **Orca Project Name**: `FX3｜FX5 & FX6 系统研究` (Workspace prefix: `FX3｜<具体主题>`)
- **Repository Root**: `/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab`
- **GitHub Remote**: `https://github.com/Rem021/sony-fx3-fx6-lab.git` (`main`)
- **External Volume Guard**: Must run on `/Volumes/KAFU2T` (Volume UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`). Abort immediately if `/Volumes/KAFU2T` is unmounted or UUID mismatches.

## 2. Directory & Categorization Architecture
All FX3, FX5, and FX6 system research, QEMU emulator harnesses, CP/CapID/GRM/GPE shims, and categorized Orca conversation archives are organized here and synced to GitHub in real time:
- `outputs/fx3-vm/`: Interactive FX3 Web UI Emulator (`http://127.0.0.1:8765/`) & 8-step menu runner
- `outputs/fx3-vm-trial/`: Standalone FX3 trial bundle (`start-fx3-vm-trial.sh`)
- `outputs/fx3-firmware-lab/`: Firmware unpacker, `ldec` LZ77 decoder, resource & partition analysis tools
- `outputs/fx3-recovery-adapter/` & `outputs/fx3-safety/`: Hardware safety guards and recovery research
- `work/fx3-vm-20261101/fx6-port-01/`: FX6 v5.00 (`ILME-FX6V`) on FX3 QEMU VM harness (`run_fx6_on_fx3_vm.py`, `fx3-capid-v31.c`)
- `work/fx3-vm-20261101/menu-repair-01/`: FX3 v7.00 AP + CP shim (`fx3-capid-v28.c`), GPE software renderer (`fx3-gpe-observe-v19.c`), OSD/VDF/SKD audits
- `work/fx3-color-port-20261027/`: FX5 / VENICE / FX6 cinema menu & color science porting research
- `work/sony-firmware-20261024/`: Stage 1–4 firmware extraction & verification scripts
- `reports/`: All FX3, FX5, FX6, and VENICE audit reports & compatibility matrices
- `conversations/`: Categorized archives of all 85+ Orca research conversations across 5 tracks:
  1. `01-fx6-system-porting` (`FX3｜FX6 系统移植与跨机型总览`)
  2. `02-fx5-unpack-and-cinema-color` (`FX3｜FX5 固件解包与电影菜单色彩移植`)
  3. `03-fx3-firmware-re-and-h265` (`FX3｜固件逆向与 H.265 编码研究`)
  4. `04-fx3-vm-menu-and-gpe` (`FX3｜虚拟机主屏菜单与 GPE 渲染修复`)
  5. `05-fx3-flash-safety-and-recovery` (`FX3｜真机刷机安全与变砖恢复研究`)

## 3. Hard Safety & Open-Source Rules
- **BYOF (Bring Your Own Firmware)**: Never commit proprietary Sony firmware images (`nflasha*`, `.cpio`, `appFw.so`, `cpapp-b.bin`), `.qcow2`/`.img` disks, or files > 50 MiB to Git.
- **Original Runtime Preservation**: Live QEMU scripts reference donor binaries in `/Volumes/KAFU2T/AI/Projects/Mac/work/...`; never delete or move those donor files.
- **Hardware Flashing Prohibition**: Full-partition cross-flashing of FX6 onto physical FX3 hardware is strictly **BLOCKED / NO-GO**. Never run USB/SD flashing against physical cameras.
- **Milestone-Driven GitHub Sync (大节点主动同步机制)**: Do **NOT** run high-frequency background polling (such as 60-second timers). Instead, whenever an Agent completes a **major milestone / significant engineering checkpoint (做出一个大节点 / 阶段性成果)**, the Agent must run:
  ```bash
  python3 /Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/scripts/realtime_github_sync.py
  ```
  to export the latest categorized Orca conversations, sync newly generated reports/code, and push the milestone commit to `https://github.com/Rem021/sony-fx3-fx6-lab.git` (`main`).
