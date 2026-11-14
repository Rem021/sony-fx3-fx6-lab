# Sony FX3 / FX5 / FX6 System Research & Emulator Lab (`FX3｜FX5 & FX6 系统研究`)

## 1. Project Identity & Scope
- **Orca Project Name**: `FX3｜FX5 & FX6 系统研究` (Workspace prefix: `FX3｜<具体主题>`)
- **Repository Root**: `~/AI-Workspace/AI/Projects/Mac/outputs/sony-fx3-fx6-lab`
- **GitHub Remote**: `https://github.com/Rem021/sony-fx3-fx6-lab.git` (`main`)
- **Storage Mode**: Hosted on internal SSD (`~/AI-Workspace/AI/Projects/Mac/outputs/sony-fx3-fx6-lab`), independent of external volumes.

## 2. Directory Layout
- `outputs/fx3-vm/`: Interactive FX3 Web UI Emulator (`http://127.0.0.1:8765/`) & menu runner
- `outputs/fx3-vm-trial/`: Standalone FX3 trial bundle (`start-fx3-vm-trial.sh`) + FX6 Ver. 6.01 (`ILME-FX6V`, `0x91040086`) live `gpe0` (`0x41e001000`) 128-page Web UI console (`run_fx6_menu_trial.py`, `build_live700.py`, `Makefile`)
- `outputs/fx3-firmware-lab/`: Firmware unpacker, `ldec` LZ77 decoder, resource & partition analysis tools
- `outputs/fx3-recovery-adapter/` & `outputs/fx3-safety/`: Hardware safety guards and recovery research (66 offline unit + ARM64 Unicorn tests)
- `work/fx3-vm-20261101/`: FX6-on-FX3 QEMU VM harness (`fx6-port-01`) and FX3 v7.00 AP + CP/GPE renderer (`menu-repair-01`)
- `work/fx3-color-port-20261027/` & `work/sony-firmware-20261024/`: Cinema color science porting & firmware extraction scripts
- `reports/` & `conversations/`: Audit reports, compatibility matrices, and categorized Orca research archives

## 3. Safety & Open-Source Rules
- **BYOF (Bring Your Own Firmware)**: Never commit proprietary Sony firmware images (`nflasha*`, `.cpio`, `appFw.so`, `cpapp-b.bin`), `.qcow2`/`.img` disks, or files > 50 MiB to Git.
- **Donor Binary Preservation**: Live QEMU harnesses reference local donor binaries under `~/AI-Workspace/AI/Projects/Mac/work/...`; keep referenced donor files intact.
- **Hardware Flashing Prohibition**: Full-partition cross-flashing of FX6 onto physical FX3 hardware is **BLOCKED / NO-GO**. Never run USB/SD flashing against physical cameras.
- **Milestone GitHub Sync**: Do not run background timer polling. When completing a major milestone, run `python3 scripts/realtime_github_sync.py` from this repo root if exporting updated reports/conversations to `main`.
