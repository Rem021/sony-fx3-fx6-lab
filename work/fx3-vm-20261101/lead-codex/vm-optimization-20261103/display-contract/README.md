# Display-Ready & UPM/MSS Contract (Static Evidence v4 — Machine-Generated Disassembly & Post-Generation Verification)

## 0. Historical Receipts & Canonical Input Binaries

All historical artifacts (`v1`, `v2`, `v3`, and `coordinator-v3-review/`) are preserved in [`display-contract/`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract):

| Version | Artifact | SHA-256 Digest (Verified on Disk) |
| :--- | :--- | :--- |
| `v1` | [`README-v1.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/README-v1.md) | `1b1b8a17a31a85278e30c2bf976392de33ce224d58cc612f224f4d08096b785f` |
| `v1` | [`verify_display_contract.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/verify_display_contract.py) | `2d717dd2fac0c556005acae29bdfd9eca1f88a53e6a15482b021496cb2fa710a` |
| `v1` | [`display-contract-evidence.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-evidence.json) | `0778a129bf10768d5784f5bed991799411c1d459e6e62073c23ac97f630511fb` |
| `v1` | [`display-contract-fixture.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-fixture.json) | `b4dedaf32382c94c92562cf82aee63c76b8bc4874c75b866fad6f418fff4312b` |
| `v2` | [`README-v2.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/README-v2.md) | `3bbc02caf4c7793faad31f9029cd9dfffc99323a9925e93e80cefe85b7d9fd94` |
| `v2` | [`verify_display_contract_v2.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/verify_display_contract_v2.py) | `371e7e254cab0215a50ec804753c3c262eae77b96bd9d51c4098d53f8faad5c6` |
| `v2` | [`display-contract-evidence-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-evidence-v2.json) | `790a240c16cca6f52a599f81597265c9b2c56e8220a9f4bd5a8a9d73d946b8ea` |
| `v2` | [`display-contract-fixture-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-fixture-v2.json) | `d521212cf7da0efa67a4b6564c17f4545df4e3d3c3ed2c942ff0d15e5bf023d0` |
| `v3` | [`README-v3.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/README-v3.md) | `cb328ad84d3e5687b6b84c4206738bffc0f3c1f363a7274dde414a46bdee403b` |
| `v3` | [`verify_display_contract_v3.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/verify_display_contract_v3.py) | `1ef173bca9902d152b62f9ea5c581f3a03cc304dd653eb956b6a89ff26ec3eac` |
| `v3` | [`display-contract-evidence-v3.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-evidence-v3.json) | `f3198f583b9fb0404704afd517970bb62bdbea9b2f0825161f0bb2d787182b59` |
| `v3` | [`display-contract-fixture-v3.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-fixture-v3.json) | `34b211c3427684e280bcc08a21960c24942b7d2e6e2573532ed48e38e1f1d414` |
| `v3-review` | [`coordinator-v3-review/receipt.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/coordinator-v3-review/receipt.json) | `fe743b2728d5cf3ec2606643766b9a41bf7962cf585497ebfca42be2d97246ac` |
| `v3-review` | [`coordinator-v3-review/actual-app-helper-disassembly.txt`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/coordinator-v3-review/actual-app-helper-disassembly.txt) | `dffe062ffca55cf294921e4e1d5910f6315da1aa6e1918f2358a4f5a17314427` |
| `v4` | [`verify_display_contract_v4.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/verify_display_contract_v4.py) | `a63b5e2057031ce3ea98ab3883701f58e8a61cef9f90e092e4478c2c7ba2696a` |
| `v4` | [`v3-to-v4-diff-inventory.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/v3-to-v4-diff-inventory.json) | `49fcdee40c512c3982fb9fd1caf9d0a9e4a21535447175c6b9d5bb258a539458` |
| `v4` | [`display-contract-evidence-v4.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-evidence-v4.json) | `94a2182fa3bdff92d1aebcff47e6b61a10c726be2384e221216c19e6e0444e1a` |
| `v4` | [`display-contract-fixture-v4.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-fixture-v4.json) | `d2794188427e7536302147ebcfb2219618494c0b1b1eb0500a724fce39889fec` |

### Canonical Fixed-SHA Binaries & Runtime Artifacts Verified

| Key | File | Canonical Workspace Path | SHA-256 Digest |
| :--- | :--- | :--- | :--- |
| `appFw.so` | [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| `libObj.so` | [`libObj.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/libObj.so) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/libObj.so` | `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae` |
| `av-cam.bin` | [`av-cam.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin) | `/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin` | `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf` |
| `upm.ko` | [`upm.ko`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko` | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` |
| `cpapp-b.bin` | [`cpapp-b.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin) | `/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin` | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` |
| `try2_70588c4c_serial` | [`serial.log`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/runs/try2-70588c4c/serial.log) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/runs/try2-70588c4c/serial.log` | `6a025dca9a6144a7695d01099fce1fe62cbe77586f063cdc93bb699dcf256402` |
| `internal_47e2924a_serial` | [`serial.log`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2gapinternal-47e2924a/serial.log) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2gapinternal-47e2924a/serial.log` | `8157737391d2d8e3acf46790312826b0084539bda82e2bbe228bc1f1d6f1d16b` |
| `trial_ring_slot_live` | [`trial-ring-slot-live.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/runs/try2-70588c4c/trial-ring-slot-live.bin) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/runs/try2-70588c4c/trial-ring-slot-live.bin` | `fef2a2a7712faaa861d1dcca1ced21b123aaaf744f18e33b381e1bda55acea0c` |
| `try2powerinternal_71ffcdef_serial` | [`serial.log`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2powerinternal-71ffcdef/serial.log) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2powerinternal-71ffcdef/serial.log` | `143421ac90476b9032f5de4331df48c046d7abeab4e72c590198b4283b737e6f` |
| `try2mssinternal_a1d8f68a_serial` | [`serial.log`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2mssinternal-a1d8f68a/serial.log) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2mssinternal-a1d8f68a/serial.log` | `cab0891be83fa46d2f16096ba2d7f354609289357d21b5e2d70fde2f4d594ada` |
| `apo_differential_json` | [`existing-runs-differential.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/apo-differential/existing-runs-differential.json) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/apo-differential/existing-runs-differential.json` | `23900be3e83bd18e82e36c074602a62a554a0a3f193f7537a5605d76b76f7016` |
| `v7_mss_observer_src` | [`fx3-media-observe-v7-mss-safe.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/src/fx3-media-observe-v7-mss-safe.c) | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/src/fx3-media-observe-v7-mss-safe.c` | `c5de178004eac532832e0f166eecee8ebf250becae1c8099f849b5047d26e653` |

---

## 1. v3 Audit & Complete Errata Inventory (`README-v3.md` -> `README.md` v4)

Why `README-v3.md` (`SHA256=cb328ad84d3e5687b6b84c4206738bffc0f3c1f363a7274dde414a46bdee403b`) failed independent `llvm-objdump` verification:
- While [`verify_display_contract_v3.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/verify_display_contract_v3.py) asserted a subset of instruction words and wrote machine-disassembled JSON into [`display-contract-evidence-v3.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-evidence-v3.json), [`README-v3.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/README-v3.md) itself was hand-typed rather than machine-generated from the ELF binaries. Partial assertions in a script do **not** validate a hand-written markdown document.
- In v4, **every instruction table in this document is machine-generated directly from fixed-SHA ELF parsing + `/usr/bin/objdump`**, and [`verify_display_contract_v4.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/verify_display_contract_v4.py) parses the final generated [`README.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/README.md) from disk to verify **every column** (`Binary`, `Section`, `VA`, `File Offset`, `Raw Bytes (LE)`, `U32 Word`, `Objdump Disassembly`, and `Relocation`) against an independent ELF64 section header + `objdump -d -r` oracle, plus executes 11 negative tamper tests (emitting [`readme-v4-verification-receipt.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/readme-v4-verification-receipt.json)).

### 1.1 All 23 Instruction-Word Mismatches in `README-v3.md` `appFw.so` `0x2eaf294..0x2eaf33c` Table

Cross-checked against [`coordinator-v3-review/receipt.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/coordinator-v3-review/receipt.json) and [`coordinator-v3-review/actual-app-helper-disassembly.txt`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/coordinator-v3-review/actual-app-helper-disassembly.txt):

| # | VA | File Offset | `README-v3.md` Word (Wrong) | Actual ELF Word | `README-v3.md` Disassembly (Wrong) | Actual `objdump` Disassembly |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `0x2eaf2a0` | `0x2eaf2a0` | `a9025bf5` | `12807ff4` | `stp x21, x22, [sp, #0x20]` | `mov w20, #-0x400 // =-1024` |
| 2 | `0x2eaf2a4` | `0x2eaf2a4` | `a90363f7` | `a9025bf5` | `stp x23, x24, [sp, #0x30]` | `stp x21, x22, [sp, #0x20]` |
| 3 | `0x2eaf2a8` | `0x2eaf2a8` | `a9046bf9` | `a90363f7` | `stp x25, x26, [sp, #0x40]` | `stp x23, x24, [sp, #0x30]` |
| 4 | `0x2eaf2ac` | `0x2eaf2ac` | `d000e6a0` | `a9046bf9` | `adrp x0, 0x4b85000` | `stp x25, x26, [sp, #0x40]` |
| 5 | `0x2eaf2b0` | `0x2eaf2b0` | `f9467c14` | `34000480` | `ldr x20, [x0, #0xcf8]` | `cbz w0, 0x2eaf340 <Application_System_Init+0x17bf7b0>` |
| 6 | `0x2eaf2c4` | `0x2eaf2c4` | `f9400280` | `52800023` | `ldr x0, [x20]` | `mov w3, #0x1 // =1` |
| 7 | `0x2eaf2c8` | `0x2eaf2c8` | `f9002ba0` | `52800202` | `str x0, [x29, #0x50]` | `mov w2, #0x10 // =16` |
| 8 | `0x2eaf2dc` | `0x2eaf2dc` | `979b9169` | `979b9391` | `bl 0x1593880 <osal_valloc_msg_wait@plt>` | `bl 0x1594120 <osal_valloc_msg_wait@plt>` |
| 9 | `0x2eaf2e0` | `0x2eaf2e0` | `7100001f` | `2a0003f4` | `cmp w0, #0x0` | `mov w20, w0` |
| 10 | `0x2eaf2e4` | `0x2eaf2e4` | `54000360` | `350002e0` | `b.eq 0x2eaf350` | `cbnz w0, 0x2eaf340 <Application_System_Init+0x17bf7b0>` |
| 11 | `0x2eaf2f0` | `0x2eaf2f0` | `979b8ffc` | `979b8ac4` | `bl 0x15932e0 <osal_set_msg_src@plt>` | `bl 0x1591e00 <osal_set_msg_src@plt>` |
| 12 | `0x2eaf30c` | `0x2eaf30c` | `540001c1` | `fa400a64` | `b.ne 0x2eaf344` | `ccmp x19, #0x0, #0x4, eq` |
| 13 | `0x2eaf310` | `0x2eaf310` | `f9402fa0` | `2a0003f4` | `ldr x0, [x29, #0x58]` | `mov w20, w0` |
| 14 | `0x2eaf314` | `0x2eaf314` | `b40001b3` | `54000100` | `cbz x19, 0x2eaf348` | `b.eq 0x2eaf334 <Application_System_Init+0x17bf7a4>` |
| 15 | `0x2eaf318` | `0x2eaf318` | `b9400018` | `f9402fa0` | `ldr w24, [x0]` | `ldr x0, [x29, #0x58]` |
| 16 | `0x2eaf31c` | `0x2eaf31c` | `b9000278` | `b9400001` | `str w24, [x19]` | `ldr w1, [x0]` |
| 17 | `0x2eaf320` | `0x2eaf320` | `b9400418` | `b9000261` | `ldr w24, [x0, #0x4]` | `str w1, [x19]` |
| 18 | `0x2eaf324` | `0x2eaf324` | `b9000678` | `b9400401` | `str w24, [x19, #0x4]` | `ldr w1, [x0, #0x4]` |
| 19 | `0x2eaf328` | `0x2eaf328` | `b9400818` | `b9000661` | `ldr w24, [x0, #0x8]` | `str w1, [x19, #0x4]` |
| 20 | `0x2eaf32c` | `0x2eaf32c` | `b9000a78` | `29410001` | `str w24, [x19, #0x8]` | `ldp w1, w0, [x0, #0x8]` |
| 21 | `0x2eaf330` | `0x2eaf330` | `b9400c18` | `29010261` | `ldr w24, [x0, #0xc]` | `stp w1, w0, [x19, #0x8]` |
| 22 | `0x2eaf334` | `0x2eaf334` | `b9000e78` | `f9402fa1` | `str w24, [x19, #0xc]` | `ldr x1, [x29, #0x58]` |
| 23 | `0x2eaf338` | `0x2eaf338` | `2a1f03f4` | `2a1503e0` | `mov w20, wzr` | `mov w0, w21` |

Additional `0x2eaf294..0x2eaf358` errors in `README-v3.md` corrected in v4:
1. **Post-send `msg_ptr` reload offset**: `ldr x0, [x29, #0x58]` (`f9402fa0`) is at **`0x2eaf318`**, NOT `0x2eaf310` (`0x2eaf310` is `2a0003f4` `mov w20, w0`, preceded by `0x2eaf30c` `fa400a64` `ccmp x19, #0x0, #0x4, eq` and followed by `0x2eaf314` `54000100` `b.eq 0x2eaf334`).
2. **Reply-copy instructions (`0x2eaf31c..0x2eaf330`)**: Uses `w1` for `+0x0` (`0x2eaf31c` `b9400001` `ldr w1, [x0]`; `0x2eaf320` `b9000261` `str w1, [x19]`) and `+0x4` (`0x2eaf324` `b9400401` `ldr w1, [x0, #0x4]`; `0x2eaf328` `b9000661` `str w1, [x19, #0x4]`), and `ldp/stp w1, w0` for `+0x8..+0xf` (`0x2eaf32c` `29410001` `ldp w1, w0, [x0, #0x8]`; `0x2eaf330` `29010261` `stp w1, w0, [x19, #0x8]`), NOT `w24`.
3. **`osal_free_msg` argument setup (`0x2eaf334..0x2eaf33c`) and epilogue (`0x2eaf340..0x2eaf358`)**: `0x2eaf334` reloads `x1 = [x29, #0x58]` (`f9402fa1`), `0x2eaf338` sets `w0 = w21` (`2a1503e0`), `0x2eaf33c` calls `osal_free_msg@plt` (`979b9425` -> `0x15943d0`), and `0x2eaf340..0x2eaf358` restores `w0 = w20` (`2a1403e0`) and `x19..x30` before `ret` (`d65f03c0`).

### 1.2 Other Structural & Prose Errata in `README-v3.md` Corrected in v4

1. **`upm.ko` `.text+0xaa44` file offset, `.text` section size, and destination (`w0`) vs source (`word1` / `osal_set_msg_src`) QIDs**:
   - In [`upm.ko`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko), ELF section `[2] .text` has `sh_addr = 0x0`, `sh_offset = 0x68`, and `sh_size = 0x2d978` (NOT `0xbd68`). Therefore `.text+0xaa44` has file offset `0x68 + 0xaa44 = 0xaaac` (NOT `0xaab0`, which is `.text+0xaa48` `2a0003f3` `mov w19, w0`).
   - Across all of `upm.ko` `.text`, there are **53 total `R_AARCH64_CALL26 osal_snd_sync_msg` relocations**, of which **12 set destination QID `w0 = 0x80924220`** (the other 41 send to other UPM/OSAL queues).
   - All hand-typed QID setup bytes (`00 44 22 52` / `00 12 90 72`) and fabricated stopper/factor arguments (`id=0x110`, `id=0x120`, `arg=1`, `arg=0`) in `README-v3.md` have been removed and replaced by the exact machine-disassembled instruction windows in §2.
   - In `k_upm_off_factor_handler_init` (`.text+0x6d38`), both site 7 (`.text+0x6ed4`) and site 8 (`.text+0x700c`) set **destination QID `w0 = 0x80924220`** (`0x6ec0`/`0x6ec4` and `0x6ff8`/`0x6ffc`: `52884400 mov w0, #0x4220; 72b01240 movk w0, #0x8092, lsl #16`), while site 7 sets **source/stopper ID `w19 = 0x80920021`** (`0x6ea0` `52800433` `mov w19, #0x21`; `0x6ea8` `72b01253` `movk w19, #0x8092, lsl #16`, passed to `osal_set_msg_src` at `0x6eb0` and stored to `[x1+0x04]` at `0x6ec8`) and site 8 sets **source/stopper ID `w20 = 0x80920196`** (`0x6fd8` `528032d4` `mov w20, #0x196`; `0x6fe0` `72b01254` `movk w20, #0x8092, lsl #16`, passed to `osal_set_msg_src` at `0x6fe8` and stored to `[x1+0x04]` at `0x7000`).
   - When disassembling relocatable [`upm.ko`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko), `--section=.text` is mandatory because `.text`, `.text.unlikely`, `.init.text`, and `.exit.text` all have section VMA `0x0`.
2. **`upm.ko` 5 async `upm_c3p_msg_async` call sites targeting `0x80924220` (out of 22 total in `.text`)**:
   - In relocatable `upm.ko`, all 5 `bl` instructions (`.text+0x08a8`, `0x24b4`, `0x2510`, `0x2680`, `0x2720`) have raw bytes `00 00 00 94` (`94000000`) with `.rela.text` relocation `R_AARCH64_CALL26 upm_c3p_msg_async` (NOT `ae ff ff 97` etc.).
3. **`upm.ko` `MSS_del_stopper` (`0x00920202`), `mss_state`, `request_list` node layout, and `k_mss_start_timer_nr`**:
   - Status check in dispatcher `.text+0x2180` is at `0x21dc` (`b9404e80` `ldr w0, [x20, #0x4c]`), `0x21e0..0x21e4` (`cmp w0, #0x2; b.eq 0x2368`), `0x21e8..0x21ec` (`cmp w0, #0x3; b.eq 0x2320`); when `status == 1`, `0x2214..0x2220` branches to `0x2300`, where `0x2300..0x230c` branches on `0x00920202` to `0x2598` (`k_mss_del_stopper` at `0x25b8`, jumping back to `0x2310`).
   - At `0x248c`, `2909069f` `stp wzr, w1, [x20, #0x48]` zeroes `elapsed_sec` (`[x20+0x48]`) and sets `status = 2` (`[x20+0x4c]`) in one instruction.
   - In `k_mss_add_request_nr` (`.text+0x1220..0x12d8`), each 28B (`0x1c`) request node stores `next` at `+0x00`, `cmd` (`0x00920118`) at `+0x08`, `req_id` at `+0x0c`, `timeout_sec` at `+0x10`, `src_id` at `+0x14`, and `state` (`1`=active, `3`=expired) at `+0x18`.
   - In `k_mss_start_timer_nr` (`.text+0x1008..0x1098`), `0x1038` stores `active_req` (`x6`) to `[x20, #0x38]`, `0x103c` loads `timeout_sec` from `[x6, #0x10]`, `0x1044` loads `elapsed_sec` from `[x20, #0x48]`, `0x1054` computes `w19 = timeout_sec - elapsed_sec`, `0x106c` multiplies by `w5 = 0x000f4240` (`1,000,000` us/sec), and `0x1094` calls `osal_snd_sync_direct` (`w0 = 0x00910040`).
4. **`appFw.so` `App::got_display_update_event` (`0x16f11e8`) and downstream boundary**:
   - Removed unverified symbol names (`fw::ConcreteEvent::get_parameter`, `App::request_ChangeTo Standby/Sleep`, `0x2eafb30..0x2eb0108`). `0x16f11e8..0x16f1350` only allocates a 20B OSAL message (`0x16f1214`), copies 20B from `[x19]` (`0x16f12bc..0x16f12c8`), sets source `0x00830128` (`0x16f12d8`), and sends to QID `0x005503e0` (`0x16f12e8`). In the `0x005503e0` consumer classifier, `0x16f38c8..0x16f38d0` sets `[x19, #0x8] = 5` and branches to `0x16f4748`. What downstream UI/presenter/screen callbacks execute after event type 5 is dispatched is **not statically proven to be free of MSS calls (`UNKNOWN_STATICALLY` without runtime trace)**.

---

## 2. Machine-Generated Disassembly: `upm.ko` Internal Senders to Destination `QID = 0x80924220` (12 Sync + 5 Async)

### 2.1 Summary of All 12 Synchronous `osal_snd_sync_msg` Call Sites Targeting `w0 = 0x80924220` (Out of 53 Total in `upm.ko` `.text`)

| # | `.text` VA | File Offset (`0x68 + VA`) | Raw Bytes (LE) | U32 Word | Relocation | Function | Machine-Verified Destination (`w0`) & Payload/Source Setup in Window |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `0x130` | `0x198` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `upm_msg_forward_thread (.text+0x0070)` | dst `w0=w19=0x80924220` (`0x0080`/`0x0090`/`0x0120`), forwards `[w24, w21, w23, w22]` received from QID `0x80920865` |
| 2 | `0xe38` | `0xea0` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_init_mss (.text+0x0d58)` | dst `w0=w22=0x80924220` (`0x0da8`/`0x0db0`/`0x0e24`), sends `[0x00920118, 0xfff, 0xbbf81e00, 0x80924220]` (v2 cited `0x0f04` which is trailing `nop`) |
| 3 | `0xfd8` | `0x1040` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_exit_mss (.text+0x0f30)` | dst `w0=w20=0x80924220` (`0x0f4c`/`0x0f54`/`0x0fc8`), sends `[0x00920119, w21(handle), 0, 0x80924220]` |
| 4 | `0x614c` | `0x61b4` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_init_off_factor (.text+0x5fb8)` | dst `w0=0x80924220` (`0x6138`/`0x613c`), src/word1 `w19=0x80920196` (`0x6118`/`0x6120`), sends `[0x00920203, 0x80920196, 0, 0]` |
| 5 | `0x69f4` | `0x6a5c` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_off_factor_handler_active (.text+0x6698, site 1)` | dst `w0=0x80924220` (`0x69e0`/`0x69e4`), src/word1 `w20=0x80920196` (`0x69c0`/`0x69c8`), sends `[0x00920203, 0x80920196, 0, 0]` |
| 6 | `0x6acc` | `0x6b34` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_off_factor_handler_active (.text+0x6698, site 2)` | dst `w0=0x80924220` (`0x6ab8`/`0x6abc`), src/word1 `w22=0x80920196` (`0x6a98`/`0x6aa0`), sends `[0x00920203, 0x80920196, 0, 0]` |
| 7 | `0x6ed4` | `0x6f3c` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_off_factor_handler_init (.text+0x6d38, site 1)` | dst `w0=0x80924220` (`0x6ec0`/`0x6ec4`), src/word1 `w19=0x80920021` (`0x6ea0`/`0x6ea8`), sends `[0x00920202, 0x80920021, 0, 0]` |
| 8 | `0x700c` | `0x7074` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_off_factor_handler_init (.text+0x6d38, site 2)` | dst `w0=0x80924220` (`0x6ff8`/`0x6ffc`), src/word1 `w20=0x80920196` (`0x6fd8`/`0x6fe0`), sends `[0x00920202, 0x80920196, 0, 0]` |
| 9 | `0x7164` | `0x71cc` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_off_factor_handler_acting_app (.text+0x7040)` | dst `w0=0x80924220` (`0x7150`/`0x7154`), src/word1 `w19=0x80920196` (`0x7130`/`0x7138`), sends `[0x00920202, 0x80920196, 0, 0]` |
| 10 | `0x88c4` | `0x892c` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_off_factor_handler_res (.text+0x85b0)` | dst `w0=0x80924220` (`0x88b0`/`0x88b4`), src/word1 `w19=0x80920196` (`0x8890`/`0x8898`), sends `[0x00920202, 0x80920196, 0, 0]` |
| 11 | `0xa2d0` | `0xa338` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `power_status_factor_cb (.text+0xa248)` | dst `w0=0x80924220` (`0xa2bc`/`0xa2c0`), src/word1 `w20=0x80920021` (`0xa29c`/`0xa2a4`), sends `[0x00920204, 0x80920021, 0, 0]` |
| 12 | `0xaa44` | `0xaaac` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 osal_snd_sync_msg` | `k_upm_init_power_status (.text+0xa968)` | dst `w0=0x80924220` (`0xaa30`/`0xaa34`), src/word1 `w19=0x80920021` (`0xaa10`/`0xaa18`), sends `[0x00920203, 0x80920021, 0, 0]` |

### 2.2 Per-Site Machine-Disassembled Instruction Windows (12 Synchronous Sites to `0x80924220`)

#### Sync Site 1: `0x130` (File `0x198`) in `upm_msg_forward_thread (.text+0x0070)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x7c` | `0xe4` | `b4 0c 81 52` | `52810cb4` | `mov w20, #0x865 // =2149` | - |  |
| `upm.ko` | `.text` | `0x80` | `0xe8` | `13 44 88 52` | `52884413` | `mov w19, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x84` | `0xec` | `f5 5b 02 a9` | `a9025bf5` | `stp x21, x22, [sp, #0x20]` | - |  |
| `upm.ko` | `.text` | `0x88` | `0xf0` | `f7 63 03 a9` | `a90363f7` | `stp x23, x24, [sp, #0x30]` | - |  |
| `upm.ko` | `.text` | `0x8c` | `0xf4` | `54 12 b0 72` | `72b01254` | `movk w20, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x90` | `0xf8` | `53 12 b0 72` | `72b01253` | `movk w19, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x94` | `0xfc` | `a1 03 01 91` | `910103a1` | `add x1, x29, #0x40` | - |  |
| `upm.ko` | `.text` | `0x98` | `0x100` | `a0 0c 81 52` | `52810ca0` | `mov w0, #0x865 // =2149` | - |  |
| `upm.ko` | `.text` | `0x9c` | `0x104` | `02 00 80 12` | `12800002` | `mov w2, #-0x1 // =-1` | - |  |
| `upm.ko` | `.text` | `0xa0` | `0x108` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xa4` | `0x10c` | `00 00 00 94` | `94000000` | `bl 0xa4 <.text+0xa4>` | `R_AARCH64_CALL26 osal_rcv_msg_tmo` |  |
| `upm.ko` | `.text` | `0xa8` | `0x110` | `e6 03 00 2a` | `2a0003e6` | `mov w6, w0` | - |  |
| `upm.ko` | `.text` | `0xac` | `0x114` | `a1 23 01 91` | `910123a1` | `add x1, x29, #0x48` | - |  |
| `upm.ko` | `.text` | `0xb0` | `0x118` | `e0 03 13 2a` | `2a1303e0` | `mov w0, w19` | - |  |
| `upm.ko` | `.text` | `0xb4` | `0x11c` | `e4 03 01 aa` | `aa0103e4` | `mov x4, x1` | - |  |
| `upm.ko` | `.text` | `0xb8` | `0x120` | `23 00 80 52` | `52800023` | `mov w3, #0x1 // =1` | - |  |
| `upm.ko` | `.text` | `0xbc` | `0x124` | `02 02 80 52` | `52800202` | `mov w2, #0x10 // =16` | - |  |
| `upm.ko` | `.text` | `0xc0` | `0x128` | `05 01 80 52` | `52800105` | `mov w5, #0x8 // =8` | - |  |
| `upm.ko` | `.text` | `0xc4` | `0x12c` | `26 01 00 34` | `34000126` | `cbz w6, 0xe8 <.text+0xe8>` | - |  |
| `upm.ko` | `.text` | `0xc8` | `0x130` | `03 33 80 52` | `52803303` | `mov w3, #0x198 // =408` | - |  |
| `upm.ko` | `.text` | `0xcc` | `0x134` | `62 02 80 52` | `52800262` | `mov w2, #0x13 // =19` | - |  |
| `upm.ko` | `.text` | `0xd0` | `0x138` | `41 00 80 52` | `52800041` | `mov w1, #0x2 // =2` | - |  |
| `upm.ko` | `.text` | `0xd4` | `0x13c` | `00 00 80 52` | `52800000` | `mov w0, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0xd8` | `0x140` | `b4 1b 09 29` | `29091bb4` | `stp w20, w6, [x29, #0x48]` | - |  |
| `upm.ko` | `.text` | `0xdc` | `0x144` | `00 00 00 94` | `94000000` | `bl 0xdc <.text+0xdc>` | `R_AARCH64_CALL26 upm_blog_writeonce` |  |
| `upm.ko` | `.text` | `0xe0` | `0x148` | `ed ff ff 17` | `17ffffed` | `b 0x94 <.text+0x94>` | - |  |
| `upm.ko` | `.text` | `0xe4` | `0x14c` | `1f 20 03 d5` | `d503201f` | `nop` | - |  |
| `upm.ko` | `.text` | `0xe8` | `0x150` | `a4 23 40 f9` | `f94023a4` | `ldr x4, [x29, #0x40]` | - |  |
| `upm.ko` | `.text` | `0xec` | `0x154` | `98 54 40 29` | `29405498` | `ldp w24, w21, [x4]` | - |  |
| `upm.ko` | `.text` | `0xf0` | `0x158` | `97 58 41 29` | `29415897` | `ldp w23, w22, [x4, #0x8]` | - |  |
| `upm.ko` | `.text` | `0xf4` | `0x15c` | `00 00 00 94` | `94000000` | `bl 0xf4 <.text+0xf4>` | `R_AARCH64_CALL26 osal_valloc_msg_wait` |  |
| `upm.ko` | `.text` | `0xf8` | `0x160` | `c0 00 00 34` | `340000c0` | `cbz w0, 0x110 <.text+0x110>` | - |  |
| `upm.ko` | `.text` | `0xfc` | `0x164` | `a1 23 40 f9` | `f94023a1` | `ldr x1, [x29, #0x40]` | - |  |
| `upm.ko` | `.text` | `0x100` | `0x168` | `e0 03 14 2a` | `2a1403e0` | `mov w0, w20` | - |  |
| `upm.ko` | `.text` | `0x104` | `0x16c` | `00 00 00 94` | `94000000` | `bl 0x104 <.text+0x104>` | `R_AARCH64_CALL26 osal_free_msg` |  |
| `upm.ko` | `.text` | `0x108` | `0x170` | `e3 ff ff 17` | `17ffffe3` | `b 0x94 <.text+0x94>` | - |  |
| `upm.ko` | `.text` | `0x10c` | `0x174` | `1f 20 03 d5` | `d503201f` | `nop` | - |  |
| `upm.ko` | `.text` | `0x110` | `0x178` | `a0 27 40 f9` | `f94027a0` | `ldr x0, [x29, #0x48]` | - |  |
| `upm.ko` | `.text` | `0x114` | `0x17c` | `e1 03 15 2a` | `2a1503e1` | `mov w1, w21` | - |  |
| `upm.ko` | `.text` | `0x118` | `0x180` | `00 00 00 94` | `94000000` | `bl 0x118 <.text+0x118>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0x11c` | `0x184` | `a1 27 40 f9` | `f94027a1` | `ldr x1, [x29, #0x48]` | - |  |
| `upm.ko` | `.text` | `0x120` | `0x188` | `e0 03 13 2a` | `2a1303e0` | `mov w0, w19` | - |  |
| `upm.ko` | `.text` | `0x124` | `0x18c` | `38 54 00 29` | `29005438` | `stp w24, w21, [x1]` | - |  |
| `upm.ko` | `.text` | `0x128` | `0x190` | `37 58 01 29` | `29015837` | `stp w23, w22, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0x12c` | `0x194` | `a1 27 40 f9` | `f94027a1` | `ldr x1, [x29, #0x48]` | - |  |
| `upm.ko` | `.text` | `0x130` | `0x198` | `00 00 00 94` | `94000000` | `bl 0x130 <.text+0x130>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0x134` | `0x19c` | `a1 27 40 f9` | `f94027a1` | `ldr x1, [x29, #0x48]` | - |  |
| `upm.ko` | `.text` | `0x138` | `0x1a0` | `e0 03 13 2a` | `2a1303e0` | `mov w0, w19` | - |  |
| `upm.ko` | `.text` | `0x13c` | `0x1a4` | `00 00 00 94` | `94000000` | `bl 0x13c <.text+0x13c>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 2: `0xe38` (File `0xea0`) in `k_upm_init_mss (.text+0x0d58)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0xda8` | `0xe10` | `16 44 88 52` | `52884416` | `mov w22, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0xdac` | `0xe14` | `a2 0b 00 58` | `58000ba2` | `ldr x2, 0xf20 <k_upm_init_mss+0x1c8>` | - |  |
| `upm.ko` | `.text` | `0xdb0` | `0xe18` | `56 12 b0 72` | `72b01256` | `movk w22, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xdb4` | `0xe1c` | `e1 03 14 aa` | `aa1403e1` | `mov x1, x20` | - |  |
| `upm.ko` | `.text` | `0xdb8` | `0xe20` | `e0 03 16 2a` | `2a1603e0` | `mov w0, w22` | - |  |
| `upm.ko` | `.text` | `0xdbc` | `0xe24` | `03 00 80 d2` | `d2800003` | `mov x3, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0xdc0` | `0xe28` | `00 00 00 94` | `94000000` | `bl 0xdc0 <k_upm_init_mss+0x68>` | `R_AARCH64_CALL26 osal_reg_sync_msg_queue_cb` |  |
| `upm.ko` | `.text` | `0xdc4` | `0xe2c` | `a0 37 00 b9` | `b90037a0` | `str w0, [x29, #0x34]` | - |  |
| `upm.ko` | `.text` | `0xdc8` | `0xe30` | `00 06 00 35` | `35000600` | `cbnz w0, 0xe88 <k_upm_init_mss+0x130>` | - |  |
| `upm.ko` | `.text` | `0xdcc` | `0xe34` | `e1 0a 00 58` | `58000ae1` | `ldr x1, 0xf28 <k_upm_init_mss+0x1d0>` | - |  |
| `upm.ko` | `.text` | `0xdd0` | `0xe38` | `e0 00 80 52` | `528000e0` | `mov w0, #0x7 // =7` | - |  |
| `upm.ko` | `.text` | `0xdd4` | `0xe3c` | `00 00 00 94` | `94000000` | `bl 0xdd4 <k_upm_init_mss+0x7c>` | `R_AARCH64_CALL26 k_upm_framework_core_reg_factor_cb_init` |  |
| `upm.ko` | `.text` | `0xdd8` | `0xe40` | `a0 37 00 b9` | `b90037a0` | `str w0, [x29, #0x34]` | - |  |
| `upm.ko` | `.text` | `0xddc` | `0xe44` | `a0 03 00 35` | `350003a0` | `cbnz w0, 0xe50 <k_upm_init_mss+0xf8>` | - |  |
| `upm.ko` | `.text` | `0xde0` | `0xe48` | `34 00 80 52` | `52800034` | `mov w20, #0x1 // =1` | - |  |
| `upm.ko` | `.text` | `0xde4` | `0xe4c` | `b4 4e 00 b9` | `b9004eb4` | `str w20, [x21, #0x4c]` | - |  |
| `upm.ko` | `.text` | `0xde8` | `0xe50` | `00 00 00 94` | `94000000` | `bl 0xde8 <k_upm_init_mss+0x90>` | `R_AARCH64_CALL26 k_upm_Backup_read_mss` |  |
| `upm.ko` | `.text` | `0xdec` | `0xe54` | `e3 03 14 2a` | `2a1403e3` | `mov w3, w20` | - |  |
| `upm.ko` | `.text` | `0xdf0` | `0xe58` | `a1 e3 00 91` | `9100e3a1` | `add x1, x29, #0x38` | - |  |
| `upm.ko` | `.text` | `0xdf4` | `0xe5c` | `e0 03 16 2a` | `2a1603e0` | `mov w0, w22` | - |  |
| `upm.ko` | `.text` | `0xdf8` | `0xe60` | `02 02 80 52` | `52800202` | `mov w2, #0x10 // =16` | - |  |
| `upm.ko` | `.text` | `0xdfc` | `0xe64` | `00 00 00 94` | `94000000` | `bl 0xdfc <k_upm_init_mss+0xa4>` | `R_AARCH64_CALL26 osal_valloc_msg_wait` |  |
| `upm.ko` | `.text` | `0xe00` | `0xe68` | `80 fc ff 35` | `35fffc80` | `cbnz w0, 0xd90 <k_upm_init_mss+0x38>` | - |  |
| `upm.ko` | `.text` | `0xe04` | `0xe6c` | `a0 1f 40 f9` | `f9401fa0` | `ldr x0, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0xe08` | `0xe70` | `e1 03 16 2a` | `2a1603e1` | `mov w1, w22` | - |  |
| `upm.ko` | `.text` | `0xe0c` | `0xe74` | `00 00 00 94` | `94000000` | `bl 0xe0c <k_upm_init_mss+0xb4>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0xe10` | `0xe78` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0xe14` | `0xe7c` | `04 23 80 52` | `52802304` | `mov w4, #0x118 // =280` | - |  |
| `upm.ko` | `.text` | `0xe18` | `0xe80` | `44 12 a0 72` | `72a01244` | `movk w4, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xe1c` | `0xe84` | `e3 ff 81 52` | `5281ffe3` | `mov w3, #0xfff // =4095` | - |  |
| `upm.ko` | `.text` | `0xe20` | `0xe88` | `02 c0 83 52` | `5283c002` | `mov w2, #0x1e00 // =7680` | - |  |
| `upm.ko` | `.text` | `0xe24` | `0xe8c` | `e0 03 16 2a` | `2a1603e0` | `mov w0, w22` | - |  |
| `upm.ko` | `.text` | `0xe28` | `0xe90` | `02 7f b7 72` | `72b77f02` | `movk w2, #0xbbf8, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xe2c` | `0xe94` | `24 0c 00 29` | `29000c24` | `stp w4, w3, [x1]` | - |  |
| `upm.ko` | `.text` | `0xe30` | `0xe98` | `22 58 01 29` | `29015822` | `stp w2, w22, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0xe34` | `0xe9c` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0xe38` | `0xea0` | `00 00 00 94` | `94000000` | `bl 0xe38 <k_upm_init_mss+0xe0>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0xe3c` | `0xea4` | `20 05 00 34` | `34000520` | `cbz w0, 0xee0 <k_upm_init_mss+0x188>` | - |  |
| `upm.ko` | `.text` | `0xe40` | `0xea8` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0xe44` | `0xeac` | `e0 03 16 2a` | `2a1603e0` | `mov w0, w22` | - |  |
| `upm.ko` | `.text` | `0xe48` | `0xeb0` | `00 00 00 94` | `94000000` | `bl 0xe48 <k_upm_init_mss+0xf0>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 3: `0xfd8` (File `0x1040`) in `k_upm_exit_mss (.text+0x0f30)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0xf4c` | `0xfb4` | `14 44 88 52` | `52884414` | `mov w20, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0xf50` | `0xfb8` | `a1 e3 00 91` | `9100e3a1` | `add x1, x29, #0x38` | - |  |
| `upm.ko` | `.text` | `0xf54` | `0xfbc` | `54 12 b0 72` | `72b01254` | `movk w20, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xf58` | `0xfc0` | `23 00 80 52` | `52800023` | `mov w3, #0x1 // =1` | - |  |
| `upm.ko` | `.text` | `0xf5c` | `0xfc4` | `e0 03 14 2a` | `2a1403e0` | `mov w0, w20` | - |  |
| `upm.ko` | `.text` | `0xf60` | `0xfc8` | `02 02 80 52` | `52800202` | `mov w2, #0x10 // =16` | - |  |
| `upm.ko` | `.text` | `0xf64` | `0xfcc` | `00 00 00 94` | `94000000` | `bl 0xf64 <k_upm_exit_mss+0x34>` | `R_AARCH64_CALL26 osal_valloc_msg_wait` |  |
| `upm.ko` | `.text` | `0xf68` | `0xfd0` | `40 02 00 34` | `34000240` | `cbz w0, 0xfb0 <k_upm_exit_mss+0x80>` | - |  |
| `upm.ko` | `.text` | `0xf6c` | `0xfd4` | `7f 2e 00 f9` | `f9002e7f` | `str xzr, [x19, #0x58]` | - |  |
| `upm.ko` | `.text` | `0xf70` | `0xfd8` | `00 00 00 94` | `94000000` | `bl 0xf70 <k_upm_exit_mss+0x40>` | `R_AARCH64_CALL26 k_mss_exit_timer` |  |
| `upm.ko` | `.text` | `0xf74` | `0xfdc` | `21 04 00 58` | `58000421` | `ldr x1, 0xff8 <k_upm_exit_mss+0xc8>` | - |  |
| `upm.ko` | `.text` | `0xf78` | `0xfe0` | `22 00 80 52` | `52800022` | `mov w2, #0x1 // =1` | - |  |
| `upm.ko` | `.text` | `0xf7c` | `0xfe4` | `e0 00 80 52` | `528000e0` | `mov w0, #0x7 // =7` | - |  |
| `upm.ko` | `.text` | `0xf80` | `0xfe8` | `62 4e 00 b9` | `b9004e62` | `str w2, [x19, #0x4c]` | - |  |
| `upm.ko` | `.text` | `0xf84` | `0xfec` | `00 00 00 94` | `94000000` | `bl 0xf84 <k_upm_exit_mss+0x54>` | `R_AARCH64_CALL26 k_upm_framework_core_unreg_factor_cb` |  |
| `upm.ko` | `.text` | `0xf88` | `0xff0` | `c1 03 00 58` | `580003c1` | `ldr x1, 0x1000 <k_upm_exit_mss+0xd0>` | - |  |
| `upm.ko` | `.text` | `0xf8c` | `0xff4` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0xf90` | `0xff8` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xf94` | `0xffc` | `21 00 40 f9` | `f9400021` | `ldr x1, [x1]` | - |  |
| `upm.ko` | `.text` | `0xf98` | `0x1000` | `00 00 00 94` | `94000000` | `bl 0xf98 <k_upm_exit_mss+0x68>` | `R_AARCH64_CALL26 osal_unreg_msg_queue_cb` |  |
| `upm.ko` | `.text` | `0xf9c` | `0x1004` | `f5 13 40 f9` | `f94013f5` | `ldr x21, [sp, #0x20]` | - |  |
| `upm.ko` | `.text` | `0xfa0` | `0x1008` | `f3 53 41 a9` | `a94153f3` | `ldp x19, x20, [sp, #0x10]` | - |  |
| `upm.ko` | `.text` | `0xfa4` | `0x100c` | `00 00 80 52` | `52800000` | `mov w0, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0xfa8` | `0x1010` | `fd 7b c4 a8` | `a8c47bfd` | `ldp x29, x30, [sp], #0x40` | - |  |
| `upm.ko` | `.text` | `0xfac` | `0x1014` | `c0 03 5f d6` | `d65f03c0` | `ret` | - |  |
| `upm.ko` | `.text` | `0xfb0` | `0x1018` | `a0 1f 40 f9` | `f9401fa0` | `ldr x0, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0xfb4` | `0x101c` | `e1 03 14 2a` | `2a1403e1` | `mov w1, w20` | - |  |
| `upm.ko` | `.text` | `0xfb8` | `0x1020` | `00 00 00 94` | `94000000` | `bl 0xfb8 <k_upm_exit_mss+0x88>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0xfbc` | `0x1024` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0xfc0` | `0x1028` | `22 23 80 52` | `52802322` | `mov w2, #0x119 // =281` | - |  |
| `upm.ko` | `.text` | `0xfc4` | `0x102c` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xfc8` | `0x1030` | `e0 03 14 2a` | `2a1403e0` | `mov w0, w20` | - |  |
| `upm.ko` | `.text` | `0xfcc` | `0x1034` | `22 54 00 29` | `29005422` | `stp w2, w21, [x1]` | - |  |
| `upm.ko` | `.text` | `0xfd0` | `0x1038` | `3f 50 01 29` | `2901503f` | `stp wzr, w20, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0xfd4` | `0x103c` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0xfd8` | `0x1040` | `00 00 00 94` | `94000000` | `bl 0xfd8 <k_upm_exit_mss+0xa8>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0xfdc` | `0x1044` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0xfe0` | `0x1048` | `e0 03 14 2a` | `2a1403e0` | `mov w0, w20` | - |  |
| `upm.ko` | `.text` | `0xfe4` | `0x104c` | `00 00 00 94` | `94000000` | `bl 0xfe4 <k_upm_exit_mss+0xb4>` | `R_AARCH64_CALL26 osal_free_msg` |  |
| `upm.ko` | `.text` | `0xfe8` | `0x1050` | `e1 ff ff 17` | `17ffffe1` | `b 0xf6c <k_upm_exit_mss+0x3c>` | - |  |
#### Sync Site 4: `0x614c` (File `0x61b4`) in `k_upm_init_off_factor (.text+0x5fb8)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x6118` | `0x6180` | `d3 32 80 52` | `528032d3` | `mov w19, #0x196 // =406` | - |  |
| `upm.ko` | `.text` | `0x611c` | `0x6184` | `a0 1f 40 f9` | `f9401fa0` | `ldr x0, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x6120` | `0x6188` | `53 12 b0 72` | `72b01253` | `movk w19, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6124` | `0x618c` | `e1 03 13 2a` | `2a1303e1` | `mov w1, w19` | - |  |
| `upm.ko` | `.text` | `0x6128` | `0x6190` | `00 00 00 94` | `94000000` | `bl 0x6128 <k_upm_init_off_factor+0x170>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0x612c` | `0x6194` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x6130` | `0x6198` | `62 40 80 52` | `52804062` | `mov w2, #0x203 // =515` | - |  |
| `upm.ko` | `.text` | `0x6134` | `0x619c` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6138` | `0x61a0` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x613c` | `0x61a4` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6140` | `0x61a8` | `22 4c 00 29` | `29004c22` | `stp w2, w19, [x1]` | - |  |
| `upm.ko` | `.text` | `0x6144` | `0x61ac` | `3f 7c 01 29` | `29017c3f` | `stp wzr, wzr, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0x6148` | `0x61b0` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x614c` | `0x61b4` | `00 00 00 94` | `94000000` | `bl 0x614c <k_upm_init_off_factor+0x194>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0x6150` | `0x61b8` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x6154` | `0x61bc` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x6158` | `0x61c0` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x615c` | `0x61c4` | `00 00 00 94` | `94000000` | `bl 0x615c <k_upm_init_off_factor+0x1a4>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 5: `0x69f4` (File `0x6a5c`) in `k_upm_off_factor_handler_active (.text+0x6698, site 1)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x69c0` | `0x6a28` | `d4 32 80 52` | `528032d4` | `mov w20, #0x196 // =406` | - |  |
| `upm.ko` | `.text` | `0x69c4` | `0x6a2c` | `a0 1f 40 f9` | `f9401fa0` | `ldr x0, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x69c8` | `0x6a30` | `54 12 b0 72` | `72b01254` | `movk w20, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x69cc` | `0x6a34` | `e1 03 14 2a` | `2a1403e1` | `mov w1, w20` | - |  |
| `upm.ko` | `.text` | `0x69d0` | `0x6a38` | `00 00 00 94` | `94000000` | `bl 0x69d0 <k_upm_off_factor_handler_active+0x338>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0x69d4` | `0x6a3c` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x69d8` | `0x6a40` | `62 40 80 52` | `52804062` | `mov w2, #0x203 // =515` | - |  |
| `upm.ko` | `.text` | `0x69dc` | `0x6a44` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x69e0` | `0x6a48` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x69e4` | `0x6a4c` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x69e8` | `0x6a50` | `22 50 00 29` | `29005022` | `stp w2, w20, [x1]` | - |  |
| `upm.ko` | `.text` | `0x69ec` | `0x6a54` | `3f 7c 01 29` | `29017c3f` | `stp wzr, wzr, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0x69f0` | `0x6a58` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x69f4` | `0x6a5c` | `00 00 00 94` | `94000000` | `bl 0x69f4 <k_upm_off_factor_handler_active+0x35c>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0x69f8` | `0x6a60` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x69fc` | `0x6a64` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x6a00` | `0x6a68` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6a04` | `0x6a6c` | `00 00 00 94` | `94000000` | `bl 0x6a04 <k_upm_off_factor_handler_active+0x36c>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 6: `0x6acc` (File `0x6b34`) in `k_upm_off_factor_handler_active (.text+0x6698, site 2)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x6a98` | `0x6b00` | `d6 32 80 52` | `528032d6` | `mov w22, #0x196 // =406` | - |  |
| `upm.ko` | `.text` | `0x6a9c` | `0x6b04` | `a0 1f 40 f9` | `f9401fa0` | `ldr x0, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x6aa0` | `0x6b08` | `56 12 b0 72` | `72b01256` | `movk w22, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6aa4` | `0x6b0c` | `e1 03 16 2a` | `2a1603e1` | `mov w1, w22` | - |  |
| `upm.ko` | `.text` | `0x6aa8` | `0x6b10` | `00 00 00 94` | `94000000` | `bl 0x6aa8 <k_upm_off_factor_handler_active+0x410>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0x6aac` | `0x6b14` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x6ab0` | `0x6b18` | `62 40 80 52` | `52804062` | `mov w2, #0x203 // =515` | - |  |
| `upm.ko` | `.text` | `0x6ab4` | `0x6b1c` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6ab8` | `0x6b20` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x6abc` | `0x6b24` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6ac0` | `0x6b28` | `22 58 00 29` | `29005822` | `stp w2, w22, [x1]` | - |  |
| `upm.ko` | `.text` | `0x6ac4` | `0x6b2c` | `3f 7c 01 29` | `29017c3f` | `stp wzr, wzr, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0x6ac8` | `0x6b30` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x6acc` | `0x6b34` | `00 00 00 94` | `94000000` | `bl 0x6acc <k_upm_off_factor_handler_active+0x434>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0x6ad0` | `0x6b38` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x6ad4` | `0x6b3c` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x6ad8` | `0x6b40` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6adc` | `0x6b44` | `00 00 00 94` | `94000000` | `bl 0x6adc <k_upm_off_factor_handler_active+0x444>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 7: `0x6ed4` (File `0x6f3c`) in `k_upm_off_factor_handler_init (.text+0x6d38, site 1)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x6ea0` | `0x6f08` | `33 04 80 52` | `52800433` | `mov w19, #0x21 // =33` | - |  |
| `upm.ko` | `.text` | `0x6ea4` | `0x6f0c` | `a0 17 40 f9` | `f94017a0` | `ldr x0, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x6ea8` | `0x6f10` | `53 12 b0 72` | `72b01253` | `movk w19, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6eac` | `0x6f14` | `e1 03 13 2a` | `2a1303e1` | `mov w1, w19` | - |  |
| `upm.ko` | `.text` | `0x6eb0` | `0x6f18` | `00 00 00 94` | `94000000` | `bl 0x6eb0 <k_upm_off_factor_handler_init+0x178>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0x6eb4` | `0x6f1c` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x6eb8` | `0x6f20` | `42 40 80 52` | `52804042` | `mov w2, #0x202 // =514` | - |  |
| `upm.ko` | `.text` | `0x6ebc` | `0x6f24` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6ec0` | `0x6f28` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x6ec4` | `0x6f2c` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6ec8` | `0x6f30` | `22 4c 00 29` | `29004c22` | `stp w2, w19, [x1]` | - |  |
| `upm.ko` | `.text` | `0x6ecc` | `0x6f34` | `3f 7c 01 29` | `29017c3f` | `stp wzr, wzr, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0x6ed0` | `0x6f38` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x6ed4` | `0x6f3c` | `00 00 00 94` | `94000000` | `bl 0x6ed4 <k_upm_off_factor_handler_init+0x19c>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0x6ed8` | `0x6f40` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x6edc` | `0x6f44` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x6ee0` | `0x6f48` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6ee4` | `0x6f4c` | `00 00 00 94` | `94000000` | `bl 0x6ee4 <k_upm_off_factor_handler_init+0x1ac>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 8: `0x700c` (File `0x7074`) in `k_upm_off_factor_handler_init (.text+0x6d38, site 2)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x6fd8` | `0x7040` | `d4 32 80 52` | `528032d4` | `mov w20, #0x196 // =406` | - |  |
| `upm.ko` | `.text` | `0x6fdc` | `0x7044` | `a0 17 40 f9` | `f94017a0` | `ldr x0, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x6fe0` | `0x7048` | `54 12 b0 72` | `72b01254` | `movk w20, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6fe4` | `0x704c` | `e1 03 14 2a` | `2a1403e1` | `mov w1, w20` | - |  |
| `upm.ko` | `.text` | `0x6fe8` | `0x7050` | `00 00 00 94` | `94000000` | `bl 0x6fe8 <k_upm_off_factor_handler_init+0x2b0>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0x6fec` | `0x7054` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x6ff0` | `0x7058` | `42 40 80 52` | `52804042` | `mov w2, #0x202 // =514` | - |  |
| `upm.ko` | `.text` | `0x6ff4` | `0x705c` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x6ff8` | `0x7060` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x6ffc` | `0x7064` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x7000` | `0x7068` | `22 50 00 29` | `29005022` | `stp w2, w20, [x1]` | - |  |
| `upm.ko` | `.text` | `0x7004` | `0x706c` | `3f 7c 01 29` | `29017c3f` | `stp wzr, wzr, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0x7008` | `0x7070` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x700c` | `0x7074` | `00 00 00 94` | `94000000` | `bl 0x700c <k_upm_off_factor_handler_init+0x2d4>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0x7010` | `0x7078` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x7014` | `0x707c` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x7018` | `0x7080` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x701c` | `0x7084` | `00 00 00 94` | `94000000` | `bl 0x701c <k_upm_off_factor_handler_init+0x2e4>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 9: `0x7164` (File `0x71cc`) in `k_upm_off_factor_handler_acting_app (.text+0x7040)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x7130` | `0x7198` | `d3 32 80 52` | `528032d3` | `mov w19, #0x196 // =406` | - |  |
| `upm.ko` | `.text` | `0x7134` | `0x719c` | `a0 17 40 f9` | `f94017a0` | `ldr x0, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x7138` | `0x71a0` | `53 12 b0 72` | `72b01253` | `movk w19, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x713c` | `0x71a4` | `e1 03 13 2a` | `2a1303e1` | `mov w1, w19` | - |  |
| `upm.ko` | `.text` | `0x7140` | `0x71a8` | `00 00 00 94` | `94000000` | `bl 0x7140 <k_upm_off_factor_handler_acting_app+0x100>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0x7144` | `0x71ac` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x7148` | `0x71b0` | `42 40 80 52` | `52804042` | `mov w2, #0x202 // =514` | - |  |
| `upm.ko` | `.text` | `0x714c` | `0x71b4` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x7150` | `0x71b8` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x7154` | `0x71bc` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x7158` | `0x71c0` | `22 4c 00 29` | `29004c22` | `stp w2, w19, [x1]` | - |  |
| `upm.ko` | `.text` | `0x715c` | `0x71c4` | `3f 7c 01 29` | `29017c3f` | `stp wzr, wzr, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0x7160` | `0x71c8` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x7164` | `0x71cc` | `00 00 00 94` | `94000000` | `bl 0x7164 <k_upm_off_factor_handler_acting_app+0x124>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0x7168` | `0x71d0` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x716c` | `0x71d4` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x7170` | `0x71d8` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x7174` | `0x71dc` | `00 00 00 94` | `94000000` | `bl 0x7174 <k_upm_off_factor_handler_acting_app+0x134>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 10: `0x88c4` (File `0x892c`) in `k_upm_off_factor_handler_res (.text+0x85b0)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x8890` | `0x88f8` | `d3 32 80 52` | `528032d3` | `mov w19, #0x196 // =406` | - |  |
| `upm.ko` | `.text` | `0x8894` | `0x88fc` | `a0 1f 40 f9` | `f9401fa0` | `ldr x0, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x8898` | `0x8900` | `53 12 b0 72` | `72b01253` | `movk w19, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x889c` | `0x8904` | `e1 03 13 2a` | `2a1303e1` | `mov w1, w19` | - |  |
| `upm.ko` | `.text` | `0x88a0` | `0x8908` | `00 00 00 94` | `94000000` | `bl 0x88a0 <k_upm_off_factor_handler_res+0x2f0>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0x88a4` | `0x890c` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x88a8` | `0x8910` | `42 40 80 52` | `52804042` | `mov w2, #0x202 // =514` | - |  |
| `upm.ko` | `.text` | `0x88ac` | `0x8914` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x88b0` | `0x8918` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x88b4` | `0x891c` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x88b8` | `0x8920` | `22 4c 00 29` | `29004c22` | `stp w2, w19, [x1]` | - |  |
| `upm.ko` | `.text` | `0x88bc` | `0x8924` | `3f 7c 01 29` | `29017c3f` | `stp wzr, wzr, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0x88c0` | `0x8928` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x88c4` | `0x892c` | `00 00 00 94` | `94000000` | `bl 0x88c4 <k_upm_off_factor_handler_res+0x314>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0x88c8` | `0x8930` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x88cc` | `0x8934` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x88d0` | `0x8938` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x88d4` | `0x893c` | `00 00 00 94` | `94000000` | `bl 0x88d4 <k_upm_off_factor_handler_res+0x324>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 11: `0xa2d0` (File `0xa338`) in `power_status_factor_cb (.text+0xa248)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0xa29c` | `0xa304` | `34 04 80 52` | `52800434` | `mov w20, #0x21 // =33` | - |  |
| `upm.ko` | `.text` | `0xa2a0` | `0xa308` | `a0 17 40 f9` | `f94017a0` | `ldr x0, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0xa2a4` | `0xa30c` | `54 12 b0 72` | `72b01254` | `movk w20, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xa2a8` | `0xa310` | `e1 03 14 2a` | `2a1403e1` | `mov w1, w20` | - |  |
| `upm.ko` | `.text` | `0xa2ac` | `0xa314` | `00 00 00 94` | `94000000` | `bl 0xa2ac <k_upm_api_off_factor_async+0xc84>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0xa2b0` | `0xa318` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0xa2b4` | `0xa31c` | `82 40 80 52` | `52804082` | `mov w2, #0x204 // =516` | - |  |
| `upm.ko` | `.text` | `0xa2b8` | `0xa320` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xa2bc` | `0xa324` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0xa2c0` | `0xa328` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xa2c4` | `0xa32c` | `22 50 00 29` | `29005022` | `stp w2, w20, [x1]` | - |  |
| `upm.ko` | `.text` | `0xa2c8` | `0xa330` | `3f 7c 01 29` | `29017c3f` | `stp wzr, wzr, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0xa2cc` | `0xa334` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0xa2d0` | `0xa338` | `00 00 00 94` | `94000000` | `bl 0xa2d0 <k_upm_api_off_factor_async+0xca8>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0xa2d4` | `0xa33c` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0xa2d8` | `0xa340` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0xa2dc` | `0xa344` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xa2e0` | `0xa348` | `00 00 00 94` | `94000000` | `bl 0xa2e0 <k_upm_api_off_factor_async+0xcb8>` | `R_AARCH64_CALL26 osal_free_msg` |  |
#### Sync Site 12: `0xaa44` (File `0xaaac`) in `k_upm_init_power_status (.text+0xa968)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0xaa10` | `0xaa78` | `33 04 80 52` | `52800433` | `mov w19, #0x21 // =33` | - |  |
| `upm.ko` | `.text` | `0xaa14` | `0xaa7c` | `a0 17 40 f9` | `f94017a0` | `ldr x0, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0xaa18` | `0xaa80` | `53 12 b0 72` | `72b01253` | `movk w19, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xaa1c` | `0xaa84` | `e1 03 13 2a` | `2a1303e1` | `mov w1, w19` | - |  |
| `upm.ko` | `.text` | `0xaa20` | `0xaa88` | `00 00 00 94` | `94000000` | `bl 0xaa20 <k_upm_init_power_status+0xb8>` | `R_AARCH64_CALL26 osal_set_msg_src` |  |
| `upm.ko` | `.text` | `0xaa24` | `0xaa8c` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0xaa28` | `0xaa90` | `62 40 80 52` | `52804062` | `mov w2, #0x203 // =515` | - |  |
| `upm.ko` | `.text` | `0xaa2c` | `0xaa94` | `42 12 a0 72` | `72a01242` | `movk w2, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xaa30` | `0xaa98` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0xaa34` | `0xaa9c` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xaa38` | `0xaaa0` | `22 4c 00 29` | `29004c22` | `stp w2, w19, [x1]` | - |  |
| `upm.ko` | `.text` | `0xaa3c` | `0xaaa4` | `3f 7c 01 29` | `29017c3f` | `stp wzr, wzr, [x1, #0x8]` | - |  |
| `upm.ko` | `.text` | `0xaa40` | `0xaaa8` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0xaa44` | `0xaaac` | `00 00 00 94` | `94000000` | `bl 0xaa44 <k_upm_init_power_status+0xdc>` | `R_AARCH64_CALL26 osal_snd_sync_msg` |  |
| `upm.ko` | `.text` | `0xaa48` | `0xaab0` | `f3 03 00 2a` | `2a0003f3` | `mov w19, w0` | - |  |
| `upm.ko` | `.text` | `0xaa4c` | `0xaab4` | `a1 17 40 f9` | `f94017a1` | `ldr x1, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0xaa50` | `0xaab8` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0xaa54` | `0xaabc` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0xaa58` | `0xaac0` | `00 00 00 94` | `94000000` | `bl 0xaa58 <k_upm_init_power_status+0xf0>` | `R_AARCH64_CALL26 osal_free_msg` |  |

#### Proof that `.text+0x0f04` (Cited in v2) is the Trailing `nop` of `k_upm_init_mss`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0xee0` | `0xf48` | `a2 1f 40 f9` | `f9401fa2` | `ldr x2, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0xee4` | `0xf4c` | `e0 03 16 2a` | `2a1603e0` | `mov w0, w22` | - |  |
| `upm.ko` | `.text` | `0xee8` | `0xf50` | `e1 03 02 aa` | `aa0203e1` | `mov x1, x2` | - |  |
| `upm.ko` | `.text` | `0xeec` | `0xf54` | `56 d0 40 29` | `2940d056` | `ldp w22, w20, [x2, #0x4]` | - |  |
| `upm.ko` | `.text` | `0xef0` | `0xf58` | `00 00 00 94` | `94000000` | `bl 0xef0 <k_upm_init_mss+0x198>` | `R_AARCH64_CALL26 osal_free_msg` |  |
| `upm.ko` | `.text` | `0xef4` | `0xf5c` | `f6 f4 ff 35` | `35fff4f6` | `cbnz w22, 0xd90 <k_upm_init_mss+0x38>` | - |  |
| `upm.ko` | `.text` | `0xef8` | `0xf60` | `f4 03 14 2a` | `2a1403f4` | `mov w20, w20` | - |  |
| `upm.ko` | `.text` | `0xefc` | `0xf64` | `b4 2e 00 f9` | `f9002eb4` | `str x20, [x21, #0x58]` | - |  |
| `upm.ko` | `.text` | `0xf00` | `0xf68` | `a4 ff ff 17` | `17ffffa4` | `b 0xd90 <k_upm_init_mss+0x38>` | - |  |
| `upm.ko` | `.text` | `0xf04` | `0xf6c` | `1f 20 03 d5` | `d503201f` | `nop` | - |  |

### 2.3 Summary & Per-Site Disassembly of All 5 Asynchronous `upm_c3p_msg_async` Sites Targeting `w0 = 0x80924220` (Out of 22 Total in `upm.ko` `.text`)

| # | `.text` VA | File Offset (`0x68 + VA`) | Raw Bytes (LE) | U32 Word | Relocation | Function | Machine-Verified Destination (`w0`) & Arguments Setup in Window |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `0x8a8` | `0x910` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 upm_c3p_msg_async` | `k_mss_fire_all_expired_nr (.text+0x0828)` | dst `w0=w22=0x80924220` (`0x085c`/`0x086c`/`0x089c`), `w1=w23=0x00920205` (`0x0858`/`0x0868`/`0x0894`), `w2=0x8000|[req+0xc]`, `w3=[active_req+0x10]`, `w4=[req+0x14]` |
| 2 | `0x24b4` | `0x251c` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 upm_c3p_msg_async` | `mss_queue_dispatcher (.text+0x2180, status 1->2 start branch)` | dst `w0=0x80924220` (`0x24a0`/`0x24b0`), `w1=0x00920204` (`0x249c`/`0x24ac`), `w2=0x7fffffff` (`0x24a8`), `w3=[x19+#4]` (`0x2494`), `w4=0` (`0x24a4`) |
| 3 | `0x2510` | `0x2578` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 upm_c3p_msg_async` | `mss_queue_dispatcher (.text+0x2180, status==2 reload branch)` | dst `w0=0x80924220` (`0x2500`/`0x250c`), `w1=w21=0x00920204` (`0x23ac..0x23b4`/`0x24fc`), `w2=0x7fffffff` (`0x2508`), `w3=[x19+#4]` (`0x24f8`), `w4=0` (`0x2504`) |
| 4 | `0x2680` | `0x26e8` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 upm_c3p_msg_async` | `mss_queue_dispatcher (.text+0x2180, status==2 0x00920119 del_request branch)` | dst `w0=0x80924220` (`0x2668`/`0x267c`), `w1=0x00920203` (`0x2664`/`0x2678`), `w2=0x7fffffff` (`0x2674`), `w3=[x19+#4]` (`0x266c`), `w4=0` (`0x2670`) |
| 5 | `0x2720` | `0x2788` | `00 00 00 94` | `94000000` | `R_AARCH64_CALL26 upm_c3p_msg_async` | `mss_queue_dispatcher (.text+0x2180, status==2 0x00920203 add_stopper branch)` | dst `w0=0x80924220` (`0x2708`/`0x2714`), `w1=w21=0x00920203` (`0x239c..0x23a4`/`0x2704`), `w2=0x7fffffff` (`0x2718`), `w3=[x19+#4]` (`0x271c`), `w4=0` (`0x270c`) |

#### Async Site 1: `0x8a8` (File `0x910`) in `k_mss_fire_all_expired_nr (.text+0x0828)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x858` | `0x8c0` | `b7 40 80 52` | `528040b7` | `mov w23, #0x205 // =517` | - |  |
| `upm.ko` | `.text` | `0x85c` | `0x8c4` | `16 44 88 52` | `52884416` | `mov w22, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x860` | `0x8c8` | `f4 03 00 aa` | `aa0003f4` | `mov x20, x0` | - |  |
| `upm.ko` | `.text` | `0x864` | `0x8cc` | `78 00 80 52` | `52800078` | `mov w24, #0x3 // =3` | - |  |
| `upm.ko` | `.text` | `0x868` | `0x8d0` | `57 12 a0 72` | `72a01257` | `movk w23, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x86c` | `0x8d4` | `56 12 b0 72` | `72b01256` | `movk w22, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x870` | `0x8d8` | `04 00 00 14` | `14000004` | `b 0x880 <k_mss_fire_all_expired_nr+0x58>` | - |  |
| `upm.ko` | `.text` | `0x874` | `0x8dc` | `1f 20 03 d5` | `d503201f` | `nop` | - |  |
| `upm.ko` | `.text` | `0x878` | `0x8e0` | `73 02 40 f9` | `f9400273` | `ldr x19, [x19]` | - |  |
| `upm.ko` | `.text` | `0x87c` | `0x8e4` | `d3 01 00 b4` | `b40001d3` | `cbz x19, 0x8b4 <k_mss_fire_all_expired_nr+0x8c>` | - |  |
| `upm.ko` | `.text` | `0x880` | `0x8e8` | `61 12 40 b9` | `b9401261` | `ldr w1, [x19, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x884` | `0x8ec` | `83 12 40 b9` | `b9401283` | `ldr w3, [x20, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x888` | `0x8f0` | `7f 00 01 6b` | `6b01007f` | `cmp w3, w1` | - |  |
| `upm.ko` | `.text` | `0x88c` | `0x8f4` | `61 ff ff 54` | `54ffff61` | `b.ne 0x878 <k_mss_fire_all_expired_nr+0x50>` | - |  |
| `upm.ko` | `.text` | `0x890` | `0x8f8` | `62 0e 40 b9` | `b9400e62` | `ldr w2, [x19, #0xc]` | - |  |
| `upm.ko` | `.text` | `0x894` | `0x8fc` | `e1 03 17 2a` | `2a1703e1` | `mov w1, w23` | - |  |
| `upm.ko` | `.text` | `0x898` | `0x900` | `64 16 40 b9` | `b9401664` | `ldr w4, [x19, #0x14]` | - |  |
| `upm.ko` | `.text` | `0x89c` | `0x904` | `e0 03 16 2a` | `2a1603e0` | `mov w0, w22` | - |  |
| `upm.ko` | `.text` | `0x8a0` | `0x908` | `a2 02 02 2a` | `2a0202a2` | `orr w2, w21, w2` | - |  |
| `upm.ko` | `.text` | `0x8a4` | `0x90c` | `78 1a 00 b9` | `b9001a78` | `str w24, [x19, #0x18]` | - |  |
| `upm.ko` | `.text` | `0x8a8` | `0x910` | `00 00 00 94` | `94000000` | `bl 0x8a8 <k_mss_fire_all_expired_nr+0x80>` | `R_AARCH64_CALL26 upm_c3p_msg_async` |  |
| `upm.ko` | `.text` | `0x8ac` | `0x914` | `73 02 40 f9` | `f9400273` | `ldr x19, [x19]` | - |  |
| `upm.ko` | `.text` | `0x8b0` | `0x918` | `93 fe ff b5` | `b5fffe93` | `cbnz x19, 0x880 <k_mss_fire_all_expired_nr+0x58>` | - |  |
#### Async Site 2: `0x24b4` (File `0x251c`) in `mss_queue_dispatcher (.text+0x2180, status 1->2 start branch)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x2494` | `0x24fc` | `63 06 40 b9` | `b9400663` | `ldr w3, [x19, #0x4]` | - |  |
| `upm.ko` | `.text` | `0x2498` | `0x2500` | `f4 03 00 2a` | `2a0003f4` | `mov w20, w0` | - |  |
| `upm.ko` | `.text` | `0x249c` | `0x2504` | `81 40 80 52` | `52804081` | `mov w1, #0x204 // =516` | - |  |
| `upm.ko` | `.text` | `0x24a0` | `0x2508` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x24a4` | `0x250c` | `04 00 80 52` | `52800004` | `mov w4, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x24a8` | `0x2510` | `02 00 b0 12` | `12b00002` | `mov w2, #0x7fffffff // =2147483647` | - |  |
| `upm.ko` | `.text` | `0x24ac` | `0x2514` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x24b0` | `0x2518` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x24b4` | `0x251c` | `00 00 00 94` | `94000000` | `bl 0x24b4 <k_mss_dump_all+0x35c>` | `R_AARCH64_CALL26 upm_c3p_msg_async` |  |
| `upm.ko` | `.text` | `0x24b8` | `0x2520` | `e0 03 14 2a` | `2a1403e0` | `mov w0, w20` | - |  |
#### Async Site 3: `0x2510` (File `0x2578`) in `mss_queue_dispatcher (.text+0x2180, status==2 reload branch)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x24f8` | `0x2560` | `63 06 40 b9` | `b9400663` | `ldr w3, [x19, #0x4]` | - |  |
| `upm.ko` | `.text` | `0x24fc` | `0x2564` | `e1 03 15 2a` | `2a1503e1` | `mov w1, w21` | - |  |
| `upm.ko` | `.text` | `0x2500` | `0x2568` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x2504` | `0x256c` | `04 00 80 52` | `52800004` | `mov w4, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x2508` | `0x2570` | `02 00 b0 12` | `12b00002` | `mov w2, #0x7fffffff // =2147483647` | - |  |
| `upm.ko` | `.text` | `0x250c` | `0x2574` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x2510` | `0x2578` | `00 00 00 94` | `94000000` | `bl 0x2510 <k_mss_dump_all+0x3b8>` | `R_AARCH64_CALL26 upm_c3p_msg_async` |  |
| `upm.ko` | `.text` | `0x2514` | `0x257c` | `7f 06 00 b9` | `b900067f` | `str wzr, [x19, #0x4]` | - |  |
#### Async Site 4: `0x2680` (File `0x26e8`) in `mss_queue_dispatcher (.text+0x2180, status==2 0x00920119 del_request branch)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x2664` | `0x26cc` | `61 40 80 52` | `52804061` | `mov w1, #0x203 // =515` | - |  |
| `upm.ko` | `.text` | `0x2668` | `0x26d0` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x266c` | `0x26d4` | `63 06 40 b9` | `b9400663` | `ldr w3, [x19, #0x4]` | - |  |
| `upm.ko` | `.text` | `0x2670` | `0x26d8` | `04 00 80 52` | `52800004` | `mov w4, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x2674` | `0x26dc` | `02 00 b0 12` | `12b00002` | `mov w2, #0x7fffffff // =2147483647` | - |  |
| `upm.ko` | `.text` | `0x2678` | `0x26e0` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x267c` | `0x26e4` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x2680` | `0x26e8` | `00 00 00 94` | `94000000` | `bl 0x2680 <k_mss_dump_all+0x528>` | `R_AARCH64_CALL26 upm_c3p_msg_async` |  |
#### Async Site 5: `0x2720` (File `0x2788`) in `mss_queue_dispatcher (.text+0x2180, status==2 0x00920203 add_stopper branch)`

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x2700` | `0x2768` | `22 00 80 52` | `52800022` | `mov w2, #0x1 // =1` | - |  |
| `upm.ko` | `.text` | `0x2704` | `0x276c` | `e1 03 15 2a` | `2a1503e1` | `mov w1, w21` | - |  |
| `upm.ko` | `.text` | `0x2708` | `0x2770` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x270c` | `0x2774` | `04 00 80 52` | `52800004` | `mov w4, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x2710` | `0x2778` | `9f 0a 09 29` | `29090a9f` | `stp wzr, w2, [x20, #0x48]` | - |  |
| `upm.ko` | `.text` | `0x2714` | `0x277c` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x2718` | `0x2780` | `02 00 b0 12` | `12b00002` | `mov w2, #0x7fffffff // =2147483647` | - |  |
| `upm.ko` | `.text` | `0x271c` | `0x2784` | `63 06 40 b9` | `b9400663` | `ldr w3, [x19, #0x4]` | - |  |
| `upm.ko` | `.text` | `0x2720` | `0x2788` | `00 00 00 94` | `94000000` | `bl 0x2720 <k_mss_dump_all+0x5c8>` | `R_AARCH64_CALL26 upm_c3p_msg_async` |  |

---

## 3. Machine-Generated Disassembly: `appFw.so` `0x2eaf294..0x2eaf358` (`upm_osal_snd_sync_msg_helper`)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `appFw.so` | `.text` | `0x2eaf294` | `0x2eaf294` | `fd 7b ba a9` | `a9ba7bfd` | `stp x29, x30, [sp, #-0x60]!` | - | Function entry (`upm_osal_snd_sync_msg_helper`) |
| `appFw.so` | `.text` | `0x2eaf298` | `0x2eaf298` | `fd 03 00 91` | `910003fd` | `mov x29, sp` | - |  |
| `appFw.so` | `.text` | `0x2eaf29c` | `0x2eaf29c` | `f3 53 01 a9` | `a90153f3` | `stp x19, x20, [sp, #0x10]` | - |  |
| `appFw.so` | `.text` | `0x2eaf2a0` | `0x2eaf2a0` | `f4 7f 80 12` | `12807ff4` | `mov w20, #-0x400 // =-1024` | - | Default error return `w20 = -0x400` (`-1024`) |
| `appFw.so` | `.text` | `0x2eaf2a4` | `0x2eaf2a4` | `f5 5b 02 a9` | `a9025bf5` | `stp x21, x22, [sp, #0x20]` | - |  |
| `appFw.so` | `.text` | `0x2eaf2a8` | `0x2eaf2a8` | `f7 63 03 a9` | `a90363f7` | `stp x23, x24, [sp, #0x30]` | - |  |
| `appFw.so` | `.text` | `0x2eaf2ac` | `0x2eaf2ac` | `f9 6b 04 a9` | `a9046bf9` | `stp x25, x26, [sp, #0x40]` | - |  |
| `appFw.so` | `.text` | `0x2eaf2b0` | `0x2eaf2b0` | `80 04 00 34` | `34000480` | `cbz w0, 0x2eaf340 <Application_System_Init+0x17bf7b0>` | - | If `w0 (dst_qid) == 0`, branch to `0x2eaf340` and return `-0x400` |
| `appFw.so` | `.text` | `0x2eaf2b4` | `0x2eaf2b4` | `f9 03 01 2a` | `2a0103f9` | `mov w25, w1` | - | Save entry `w1` (`word0` = `cmd_id`) into `w25` |
| `appFw.so` | `.text` | `0x2eaf2b8` | `0x2eaf2b8` | `a1 63 01 91` | `910163a1` | `add x1, x29, #0x58` | - | `x1 = x29 + 0x58` (`&msg_ptr` stack slot) |
| `appFw.so` | `.text` | `0x2eaf2bc` | `0x2eaf2bc` | `f7 03 03 2a` | `2a0303f7` | `mov w23, w3` | - | Save entry `w3` (`word2` = `arg1`) into `w23` |
| `appFw.so` | `.text` | `0x2eaf2c0` | `0x2eaf2c0` | `f8 03 02 2a` | `2a0203f8` | `mov w24, w2` | - | Save entry `w2` (`word1` = `arg0`) into `w24` |
| `appFw.so` | `.text` | `0x2eaf2c4` | `0x2eaf2c4` | `23 00 80 52` | `52800023` | `mov w3, #0x1 // =1` | - | `w3 = 1` (`wait` arg for `osal_valloc_msg_wait`) |
| `appFw.so` | `.text` | `0x2eaf2c8` | `0x2eaf2c8` | `02 02 80 52` | `52800202` | `mov w2, #0x10 // =16` | - | `w2 = 0x10` (`16B` size arg for `osal_valloc_msg_wait`) |
| `appFw.so` | `.text` | `0x2eaf2cc` | `0x2eaf2cc` | `f5 03 00 2a` | `2a0003f5` | `mov w21, w0` | - | Save entry `w0` (`dst_qid`) into `w21` |
| `appFw.so` | `.text` | `0x2eaf2d0` | `0x2eaf2d0` | `fa 03 06 2a` | `2a0603fa` | `mov w26, w6` | - | Save entry `w6` (`src_id` header metadata) into `w26` |
| `appFw.so` | `.text` | `0x2eaf2d4` | `0x2eaf2d4` | `f3 03 05 aa` | `aa0503f3` | `mov x19, x5` | - | Save entry `x5` (optional 16B `reply_out_ptr`) into `x19` |
| `appFw.so` | `.text` | `0x2eaf2d8` | `0x2eaf2d8` | `f6 03 04 2a` | `2a0403f6` | `mov w22, w4` | - | Save entry `w4` (`word3` = `arg2`) into `w22` |
| `appFw.so` | `.text` | `0x2eaf2dc` | `0x2eaf2dc` | `91 93 9b 97` | `979b9391` | `bl 0x1594120 <osal_valloc_msg_wait@plt>` | - | Allocate 16B OSAL msg buffer into `*[x29+0x58]` |
| `appFw.so` | `.text` | `0x2eaf2e0` | `0x2eaf2e0` | `f4 03 00 2a` | `2a0003f4` | `mov w20, w0` | - | Save allocation return status `w0` into `w20` |
| `appFw.so` | `.text` | `0x2eaf2e4` | `0x2eaf2e4` | `e0 02 00 35` | `350002e0` | `cbnz w0, 0x2eaf340 <Application_System_Init+0x17bf7b0>` | - | If allocation failed (`w0 != 0`), branch to `0x2eaf340` |
| `appFw.so` | `.text` | `0x2eaf2e8` | `0x2eaf2e8` | `a0 2f 40 f9` | `f9402fa0` | `ldr x0, [x29, #0x58]` | - | Load allocated `msg_ptr` into `x0` |
| `appFw.so` | `.text` | `0x2eaf2ec` | `0x2eaf2ec` | `e1 03 1a 2a` | `2a1a03e1` | `mov w1, w26` | - | `w1 = w26` (`src_id`) |
| `appFw.so` | `.text` | `0x2eaf2f0` | `0x2eaf2f0` | `c4 8a 9b 97` | `979b8ac4` | `bl 0x1591e00 <osal_set_msg_src@plt>` | - | Set OSAL header source ID (`osal_set_msg_src`) |
| `appFw.so` | `.text` | `0x2eaf2f4` | `0x2eaf2f4` | `a1 2f 40 f9` | `f9402fa1` | `ldr x1, [x29, #0x58]` | - | Load `x1 = msg_ptr` (`[x29+0x58]`) |
| `appFw.so` | `.text` | `0x2eaf2f8` | `0x2eaf2f8` | `e0 03 15 2a` | `2a1503e0` | `mov w0, w21` | - | `w0 = w21` (`dst_qid`) |
| `appFw.so` | `.text` | `0x2eaf2fc` | `0x2eaf2fc` | `39 60 00 29` | `29006039` | `stp w25, w24, [x1]` | - | Write wire `[x1+0x00]=w25 (entry w1)`, `[x1+0x04]=w24 (entry w2)` |
| `appFw.so` | `.text` | `0x2eaf300` | `0x2eaf300` | `37 58 01 29` | `29015837` | `stp w23, w22, [x1, #0x8]` | - | Write wire `[x1+0x08]=w23 (entry w3)`, `[x1+0x0c]=w22 (entry w4)` |
| `appFw.so` | `.text` | `0x2eaf304` | `0x2eaf304` | `b7 92 9b 97` | `979b92b7` | `bl 0x1593de0 <osal_snd_sync_msg@plt>` | - | Pre-send call site: `osal_snd_sync_msg(w0=dst_qid, x1=msg_ptr)` |
| `appFw.so` | `.text` | `0x2eaf308` | `0x2eaf308` | `1f 00 00 71` | `7100001f` | `cmp w0, #0x0` | - | Post-send check: `cmp w0, #0x0` |
| `appFw.so` | `.text` | `0x2eaf30c` | `0x2eaf30c` | `64 0a 40 fa` | `fa400a64` | `ccmp x19, #0x0, #0x4, eq` | - | If `w0 == 0`, test `x19 != 0` (`ccmp x19, #0x0, #0x4, eq`) |
| `appFw.so` | `.text` | `0x2eaf310` | `0x2eaf310` | `f4 03 00 2a` | `2a0003f4` | `mov w20, w0` | - | Save `osal_snd_sync_msg` return code `w0` into `w20` |
| `appFw.so` | `.text` | `0x2eaf314` | `0x2eaf314` | `00 01 00 54` | `54000100` | `b.eq 0x2eaf334 <Application_System_Init+0x17bf7a4>` | - | Skip reply copy if `w0 != 0` or `x19 == 0` -> `0x2eaf334` |
| `appFw.so` | `.text` | `0x2eaf318` | `0x2eaf318` | `a0 2f 40 f9` | `f9402fa0` | `ldr x0, [x29, #0x58]` | - | Post-send reload of `msg_ptr`: `ldr x0, [x29, #0x58]` |
| `appFw.so` | `.text` | `0x2eaf31c` | `0x2eaf31c` | `01 00 40 b9` | `b9400001` | `ldr w1, [x0]` | - | Read post-send `[msg_ptr+0x00]` into `w1` |
| `appFw.so` | `.text` | `0x2eaf320` | `0x2eaf320` | `61 02 00 b9` | `b9000261` | `str w1, [x19]` | - | Store `w1` to `[x19+0x00]` |
| `appFw.so` | `.text` | `0x2eaf324` | `0x2eaf324` | `01 04 40 b9` | `b9400401` | `ldr w1, [x0, #0x4]` | - | Read post-send `[msg_ptr+0x04]` into `w1` |
| `appFw.so` | `.text` | `0x2eaf328` | `0x2eaf328` | `61 06 00 b9` | `b9000661` | `str w1, [x19, #0x4]` | - | Store `w1` to `[x19+0x04]` |
| `appFw.so` | `.text` | `0x2eaf32c` | `0x2eaf32c` | `01 00 41 29` | `29410001` | `ldp w1, w0, [x0, #0x8]` | - | Read post-send `[msg_ptr+0x08..0x0f]` into `w1, w0` |
| `appFw.so` | `.text` | `0x2eaf330` | `0x2eaf330` | `61 02 01 29` | `29010261` | `stp w1, w0, [x19, #0x8]` | - | Store `w1, w0` to `[x19+0x08..0x0f]` |
| `appFw.so` | `.text` | `0x2eaf334` | `0x2eaf334` | `a1 2f 40 f9` | `f9402fa1` | `ldr x1, [x29, #0x58]` | - | Reload `x1 = msg_ptr` (`[x29+0x58]`) for `osal_free_msg` |
| `appFw.so` | `.text` | `0x2eaf338` | `0x2eaf338` | `e0 03 15 2a` | `2a1503e0` | `mov w0, w21` | - | `w0 = w21` (`dst_qid`) for `osal_free_msg` |
| `appFw.so` | `.text` | `0x2eaf33c` | `0x2eaf33c` | `25 94 9b 97` | `979b9425` | `bl 0x15943d0 <osal_free_msg@plt>` | - | Free `msg_ptr` (`osal_free_msg(dst_qid, msg_ptr)`) |
| `appFw.so` | `.text` | `0x2eaf340` | `0x2eaf340` | `e0 03 14 2a` | `2a1403e0` | `mov w0, w20` | - | Move return status `w20` into `w0` |
| `appFw.so` | `.text` | `0x2eaf344` | `0x2eaf344` | `f3 53 41 a9` | `a94153f3` | `ldp x19, x20, [sp, #0x10]` | - |  |
| `appFw.so` | `.text` | `0x2eaf348` | `0x2eaf348` | `f5 5b 42 a9` | `a9425bf5` | `ldp x21, x22, [sp, #0x20]` | - |  |
| `appFw.so` | `.text` | `0x2eaf34c` | `0x2eaf34c` | `f7 63 43 a9` | `a94363f7` | `ldp x23, x24, [sp, #0x30]` | - |  |
| `appFw.so` | `.text` | `0x2eaf350` | `0x2eaf350` | `f9 6b 44 a9` | `a9446bf9` | `ldp x25, x26, [sp, #0x40]` | - |  |
| `appFw.so` | `.text` | `0x2eaf354` | `0x2eaf354` | `fd 7b c6 a8` | `a8c67bfd` | `ldp x29, x30, [sp], #0x60` | - |  |
| `appFw.so` | `.text` | `0x2eaf358` | `0x2eaf358` | `c0 03 5f d6` | `d65f03c0` | `ret` | - | Return to caller |

### 3.1 Exact Distinction: Entry Register Reconstruction (`0x2eaf294`) vs Pre-Send Wire Buffer (`0x2eaf304`) vs Post-Send Buffer (`0x2eaf308`)

1. **Function Entry (`0x2eaf294`, word `a9ba7bfd`) — Caller-Register Reconstruction (Before Allocation)**:
   - At `0x2eaf294`, `osal_valloc_msg_wait@plt` (`0x2eaf2dc`, word `979b9391`) has not executed yet.
   - Caller arguments in registers map to the 16B wire payload and OSAL header as follows:
     - `w0` -> saved in `w21` at `0x2eaf2cc` (`2a0003f5`): `dst_qid` (`0x80924220`).
     - `w1` -> saved in `w25` at `0x2eaf2b4` (`2a0103f9`): wire `word0` (`[x1+0x00]`, command ID).
     - `w2` -> saved in `w24` at `0x2eaf2c0` (`2a0203f8`): wire `word1` (`[x1+0x04]`).
     - `w3` -> saved in `w23` at `0x2eaf2bc` (`2a0303f7`): wire `word2` (`[x1+0x08]`).
     - `w4` -> saved in `w22` at `0x2eaf2d8` (`2a0403f6`): wire `word3` (`[x1+0x0c]`).
     - `x5` -> saved in `x19` at `0x2eaf2d4` (`aa0503f3`): optional 16B caller reply buffer pointer (`reply_out_ptr`).
     - `w6` -> saved in `w26` at `0x2eaf2d0` (`2a0603fa`): OSAL message header `src_id`, passed as `w1` to `osal_set_msg_src@plt` at `0x2eaf2ec..0x2eaf2f0` (`2a1a03e1`, `979b8ac4`).
2. **Pre-Send Call Site (`0x2eaf304`, word `979b92b7`) — Allocated & Populated 16B Wire Buffer**:
   - At `0x2eaf2f4` (`f9402fa1`), `x1` is loaded from `[x29, #0x58]`. At `0x2eaf2fc` (`29006039` `stp w25, w24, [x1]`) and `0x2eaf300` (`29015837` `stp w23, w22, [x1, #0x8]`), the 4 payload words `[w25, w24, w23, w22]` are written into `[x1+0x00..0x0f]`.
   - Immediately before `bl 0x1593de0 <osal_snd_sync_msg@plt>` at `0x2eaf304`, `w0` is `dst_qid` (`w21`) and `x1` points to the exact 16B pre-send wire buffer.
3. **Post-Send Check (`0x2eaf308`, word `7100001f`) & Reply Copy (`0x2eaf318..0x2eaf330`)**:
   - At `0x2eaf308` (`cmp w0, #0x0`), `osal_snd_sync_msg@plt` has returned; `w0` is the return status (saved to `w20` at `0x2eaf310` `2a0003f4`), and the synchronous receiver (`upm.ko` `.text+0x2180`) has already processed the message and may have modified `[msg_ptr+0x00..0x0f]` in-place.
   - If `w0 == 0` and `x19 != 0` (`0x2eaf30c` `fa400a64` `ccmp x19, #0x0, #0x4, eq`; `0x2eaf314` `54000100` `b.eq 0x2eaf334`), `0x2eaf318` (`f9402fa0`) reloads `x0 = [x29, #0x58]` and `0x2eaf31c..0x2eaf330` copies the 16B post-send buffer `[x0+0x00..0x0f]` into `[x19+0x00..0x0f]` before `0x2eaf334..0x2eaf33c` (`f9402fa1`, `2a1503e0`, `979b9425`) frees `[x29, #0x58]` via `osal_free_msg@plt`.

---

## 4. Machine-Generated Disassembly: `upm.ko` `0x00920202` (`MSS_del_stopper`), Request List Layout, and Timer Start

### 4.1 Dispatcher Status Precondition & `0x00920202` Entry (`.text+0x21c8..0x2240`, `.text+0x2300..0x231c`, `.text+0x2598..0x25bc`, `.text+0x26c4..0x26dc`)

- **Precondition 1 (`mss_state.status == 1` `STOPPED`)**: At `0x21dc` (`b9404e80` `ldr w0, [x20, #0x4c]`), if `w0 == 2` (`RUNNING`, `0x21e0..0x21e4`), execution branches to `0x2368`, where `0x00920202` (`0x238c..0x2398`) branches to `0x26c4` (logging `w3 = 0x108` via `upm_blog_writeonce` and returning without deleting any stopper or touching the timer). If `w0 == 3` (`0x21e8..0x21ec`), it branches to `0x2320` (error `-0x400`). Only when `status` is neither `2` nor `3` (i.e. `status == 1` `STOPPED`) does `0x2214..0x2220` (`sub/sub/tst w1, #0xfffffffd`) branch to `0x2300`, which dispatches `0x00920202` to `0x2598` (`k_mss_del_stopper` at `0x25b8`) and jumps back to `0x2310`.
- **Precondition 2 (`stopper_list == NULL` after deletion)**: At `0x2310` (`f9402280` `ldr x0, [x20, #0x40]`) and `0x2314` (`b4000aa0` `cbz x0, 0x2468`), the timer-start block `0x2468` is entered **only** if `stopper_list` (`[x20+0x40]`) is now `NULL` (`0`).

#### `.text+0x21c8..0x2240` (Status Gate & `status == 1` Command Dispatch)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x21c8` | `0x2230` | `20 44 80 52` | `52804420` | `mov w0, #0x221 // =545` | - |  |
| `upm.ko` | `.text` | `0x21cc` | `0x2234` | `01 00 80 12` | `12800001` | `mov w1, #-0x1 // =-1` | - |  |
| `upm.ko` | `.text` | `0x21d0` | `0x2238` | `40 12 a0 72` | `72a01240` | `movk w0, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x21d4` | `0x223c` | `00 00 00 94` | `94000000` | `bl 0x21d4 <k_mss_dump_all+0x7c>` | `R_AARCH64_CALL26 osal_wai_sem_tmo` |  |
| `upm.ko` | `.text` | `0x21d8` | `0x2240` | `14 2b 00 58` | `58002b14` | `ldr x20, 0x2738 <k_mss_dump_all+0x5e0>` | - |  |
| `upm.ko` | `.text` | `0x21dc` | `0x2244` | `80 4e 40 b9` | `b9404e80` | `ldr w0, [x20, #0x4c]` | - |  |
| `upm.ko` | `.text` | `0x21e0` | `0x2248` | `1f 08 00 71` | `7100081f` | `cmp w0, #0x2` | - |  |
| `upm.ko` | `.text` | `0x21e4` | `0x224c` | `20 0c 00 54` | `54000c20` | `b.eq 0x2368 <k_mss_dump_all+0x210>` | - |  |
| `upm.ko` | `.text` | `0x21e8` | `0x2250` | `1f 0c 00 71` | `71000c1f` | `cmp w0, #0x3` | - |  |
| `upm.ko` | `.text` | `0x21ec` | `0x2254` | `a0 09 00 54` | `540009a0` | `b.eq 0x2320 <k_mss_dump_all+0x1c8>` | - |  |
| `upm.ko` | `.text` | `0x21f0` | `0x2258` | `01 23 80 52` | `52802301` | `mov w1, #0x118 // =280` | - |  |
| `upm.ko` | `.text` | `0x21f4` | `0x225c` | `60 02 40 b9` | `b9400260` | `ldr w0, [x19]` | - |  |
| `upm.ko` | `.text` | `0x21f8` | `0x2260` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x21fc` | `0x2264` | `1f 00 01 6b` | `6b01001f` | `cmp w0, w1` | - |  |
| `upm.ko` | `.text` | `0x2200` | `0x2268` | `80 10 00 54` | `54001080` | `b.eq 0x2410 <k_mss_dump_all+0x2b8>` | - |  |
| `upm.ko` | `.text` | `0x2204` | `0x226c` | `21 23 80 52` | `52802321` | `mov w1, #0x119 // =281` | - |  |
| `upm.ko` | `.text` | `0x2208` | `0x2270` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x220c` | `0x2274` | `1f 00 01 6b` | `6b01001f` | `cmp w0, w1` | - |  |
| `upm.ko` | `.text` | `0x2210` | `0x2278` | `80 19 00 54` | `54001980` | `b.eq 0x2540 <k_mss_dump_all+0x3e8>` | - |  |
| `upm.ko` | `.text` | `0x2214` | `0x227c` | `01 80 64 51` | `51648001` | `sub w1, w0, #0x920, lsl #12 // =0x920000` | - |  |
| `upm.ko` | `.text` | `0x2218` | `0x2280` | `21 08 08 51` | `51080821` | `sub w1, w1, #0x202` | - |  |
| `upm.ko` | `.text` | `0x221c` | `0x2284` | `3f 78 1e 72` | `721e783f` | `tst w1, #0xfffffffd` | - |  |
| `upm.ko` | `.text` | `0x2220` | `0x2288` | `00 07 00 54` | `54000700` | `b.eq 0x2300 <k_mss_dump_all+0x1a8>` | - |  |
| `upm.ko` | `.text` | `0x2224` | `0x228c` | `61 40 80 52` | `52804061` | `mov w1, #0x203 // =515` | - |  |
| `upm.ko` | `.text` | `0x2228` | `0x2290` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x222c` | `0x2294` | `1f 00 01 6b` | `6b01001f` | `cmp w0, w1` | - |  |
| `upm.ko` | `.text` | `0x2230` | `0x2298` | `80 1c 00 54` | `54001c80` | `b.eq 0x25c0 <k_mss_dump_all+0x468>` | - |  |
| `upm.ko` | `.text` | `0x2234` | `0x229c` | `a1 40 80 52` | `528040a1` | `mov w1, #0x205 // =517` | - |  |
| `upm.ko` | `.text` | `0x2238` | `0x22a0` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x223c` | `0x22a4` | `1f 00 01 6b` | `6b01001f` | `cmp w0, w1` | - |  |
| `upm.ko` | `.text` | `0x2240` | `0x22a8` | `80 19 00 54` | `54001980` | `b.eq 0x2570 <k_mss_dump_all+0x418>` | - |  |

#### `.text+0x2300..0x231c` (`0x00920202` Branch & `stopper_list == NULL` Check)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x2300` | `0x2368` | `41 40 80 52` | `52804041` | `mov w1, #0x202 // =514` | - |  |
| `upm.ko` | `.text` | `0x2304` | `0x236c` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x2308` | `0x2370` | `1f 00 01 6b` | `6b01001f` | `cmp w0, w1` | - |  |
| `upm.ko` | `.text` | `0x230c` | `0x2374` | `60 14 00 54` | `54001460` | `b.eq 0x2598 <k_mss_dump_all+0x440>` | - |  |
| `upm.ko` | `.text` | `0x2310` | `0x2378` | `80 22 40 f9` | `f9402280` | `ldr x0, [x20, #0x40]` | - |  |
| `upm.ko` | `.text` | `0x2314` | `0x237c` | `a0 0a 00 b4` | `b4000aa0` | `cbz x0, 0x2468 <k_mss_dump_all+0x310>` | - |  |
| `upm.ko` | `.text` | `0x2318` | `0x2380` | `00 00 80 52` | `52800000` | `mov w0, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x231c` | `0x2384` | `d9 ff ff 17` | `17ffffd9` | `b 0x2280 <k_mss_dump_all+0x128>` | - |  |

#### `.text+0x2598..0x25bc` (`0x00920202` `k_mss_del_stopper` Call when `status == 1`)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x2598` | `0x2600` | `64 12 00 91` | `91001264` | `add x4, x19, #0x4` | - |  |
| `upm.ko` | `.text` | `0x259c` | `0x2604` | `85 00 80 52` | `52800085` | `mov w5, #0x4 // =4` | - |  |
| `upm.ko` | `.text` | `0x25a0` | `0x2608` | `43 20 80 52` | `52802043` | `mov w3, #0x102 // =258` | - |  |
| `upm.ko` | `.text` | `0x25a4` | `0x260c` | `42 01 80 52` | `52800142` | `mov w2, #0xa // =10` | - |  |
| `upm.ko` | `.text` | `0x25a8` | `0x2610` | `01 00 80 52` | `52800001` | `mov w1, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x25ac` | `0x2614` | `40 00 80 52` | `52800040` | `mov w0, #0x2 // =2` | - |  |
| `upm.ko` | `.text` | `0x25b0` | `0x2618` | `00 00 00 94` | `94000000` | `bl 0x25b0 <k_mss_dump_all+0x458>` | `R_AARCH64_CALL26 upm_blog_writeonce` |  |
| `upm.ko` | `.text` | `0x25b4` | `0x261c` | `e0 03 13 aa` | `aa1303e0` | `mov x0, x19` | - |  |
| `upm.ko` | `.text` | `0x25b8` | `0x2620` | `00 00 00 94` | `94000000` | `bl 0x25b8 <k_mss_dump_all+0x460>` | `R_AARCH64_CALL26 k_mss_del_stopper` |  |
| `upm.ko` | `.text` | `0x25bc` | `0x2624` | `55 ff ff 17` | `17ffff55` | `b 0x2310 <k_mss_dump_all+0x1b8>` | - |  |

#### `.text+0x2368..0x23b8` & `.text+0x26c4..0x26dc` (`status == 2` Rejects `0x00920202` with Log `0x108`)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x2368` | `0x23d0` | `01 23 80 52` | `52802301` | `mov w1, #0x118 // =280` | - |  |
| `upm.ko` | `.text` | `0x236c` | `0x23d4` | `75 02 40 b9` | `b9400275` | `ldr w21, [x19]` | - |  |
| `upm.ko` | `.text` | `0x2370` | `0x23d8` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x2374` | `0x23dc` | `bf 02 01 6b` | `6b0102bf` | `cmp w21, w1` | - |  |
| `upm.ko` | `.text` | `0x2378` | `0x23e0` | `00 14 00 54` | `54001400` | `b.eq 0x25f8 <k_mss_dump_all+0x4a0>` | - |  |
| `upm.ko` | `.text` | `0x237c` | `0x23e4` | `21 23 80 52` | `52802321` | `mov w1, #0x119 // =281` | - |  |
| `upm.ko` | `.text` | `0x2380` | `0x23e8` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x2384` | `0x23ec` | `bf 02 01 6b` | `6b0102bf` | `cmp w21, w1` | - |  |
| `upm.ko` | `.text` | `0x2388` | `0x23f0` | `c0 15 00 54` | `540015c0` | `b.eq 0x2640 <k_mss_dump_all+0x4e8>` | - |  |
| `upm.ko` | `.text` | `0x238c` | `0x23f4` | `41 40 80 52` | `52804041` | `mov w1, #0x202 // =514` | - |  |
| `upm.ko` | `.text` | `0x2390` | `0x23f8` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x2394` | `0x23fc` | `bf 02 01 6b` | `6b0102bf` | `cmp w21, w1` | - |  |
| `upm.ko` | `.text` | `0x2398` | `0x2400` | `60 19 00 54` | `54001960` | `b.eq 0x26c4 <k_mss_dump_all+0x56c>` | - |  |
| `upm.ko` | `.text` | `0x239c` | `0x2404` | `61 40 80 52` | `52804061` | `mov w1, #0x203 // =515` | - |  |
| `upm.ko` | `.text` | `0x23a0` | `0x2408` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x23a4` | `0x240c` | `bf 02 01 6b` | `6b0102bf` | `cmp w21, w1` | - |  |
| `upm.ko` | `.text` | `0x23a8` | `0x2410` | `c0 19 00 54` | `540019c0` | `b.eq 0x26e0 <k_mss_dump_all+0x588>` | - |  |
| `upm.ko` | `.text` | `0x23ac` | `0x2414` | `81 40 80 52` | `52804081` | `mov w1, #0x204 // =516` | - |  |
| `upm.ko` | `.text` | `0x23b0` | `0x2418` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x23b4` | `0x241c` | `bf 02 01 6b` | `6b0102bf` | `cmp w21, w1` | - |  |
| `upm.ko` | `.text` | `0x23b8` | `0x2420` | `c0 08 00 54` | `540008c0` | `b.eq 0x24d0 <k_mss_dump_all+0x378>` | - |  |

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x26c4` | `0x272c` | `64 12 00 91` | `91001264` | `add x4, x19, #0x4` | - |  |
| `upm.ko` | `.text` | `0x26c8` | `0x2730` | `85 00 80 52` | `52800085` | `mov w5, #0x4 // =4` | - |  |
| `upm.ko` | `.text` | `0x26cc` | `0x2734` | `03 21 80 52` | `52802103` | `mov w3, #0x108 // =264` | - |  |
| `upm.ko` | `.text` | `0x26d0` | `0x2738` | `42 01 80 52` | `52800142` | `mov w2, #0xa // =10` | - |  |
| `upm.ko` | `.text` | `0x26d4` | `0x273c` | `01 00 80 52` | `52800001` | `mov w1, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x26d8` | `0x2740` | `00 00 00 94` | `94000000` | `bl 0x26d8 <k_mss_dump_all+0x580>` | `R_AARCH64_CALL26 upm_blog_writeonce` |  |
| `upm.ko` | `.text` | `0x26dc` | `0x2744` | `ea fe ff 17` | `17fffeea` | `b 0x2284 <k_mss_dump_all+0x12c>` | - |  |

### 4.2 Minimum-Request Selection & Timer Start (`.text+0x2468..0x24bc`, `.text+0x1558..0x15f8`, `.text+0x1008..0x1098`, `.text+0x1220..0x12d8`)

- When `stopper_list` becomes `NULL` (`0x2314` `cbz x0, 0x2468`), `.text+0x2468..0x247c` resets `[node+0x18] = 1` for every node in `request_list` (`[x20+0x30]`), calls `k_mss_find_min_request` (`0x2480`), sets `elapsed_sec = 0` (`[x20+0x48]`) and `status = 2` (`[x20+0x4c]`) via `0x248c` (`2909069f` `stp wzr, w1, [x20, #0x48]`), and calls `k_mss_start_timer_nr(min_req)` (`0x2490`).
- In `k_mss_start_timer_nr` (`.text+0x1008..0x1098`), the scheduled duration in microseconds (`x19`) is `([min_req+0x10] - [mss_state+0x48]) * 1,000,000` (`0x103c` `ldr w19, [x6, #0x10]`; `0x1044` `ldr w2, [x20, #0x48]`; `0x1054` `sub w19, w19, w2`; `0x106c` `umull x19, w19, w5` with `w5 = 0x000f4240`).
- Because `0x248c` zeroes `elapsed_sec` (`[x20+0x48] = 0`), `0x00920202` (`MSS_del_stopper`) starts the **full period of the current minimum registered request (`min_req->timeout_sec` at `[min_req+0x10]`)**; by contrast, when `k_mss_timer_cb` (`.text+0x1670..0x1704`) chains to the next un-expired request at `0x16b8..0x16c8` after setting `elapsed_sec = expired_req->timeout_sec` (`0x16a8..0x16b0`), `k_mss_start_timer_nr` schedules the **remaining period (`next_req->timeout_sec - elapsed_sec`)**. Neither path is hardcoded to 300s unless the selected request's `timeout_sec` (`[req+0x10]`) is 300s (or `next_req->timeout_sec - elapsed_sec == 300`).

#### `.text+0x2468..0x24bc` (Reset Request States, Find Min Request, Zero `elapsed_sec`, Start Timer)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x2468` | `0x24d0` | `80 1a 40 f9` | `f9401a80` | `ldr x0, [x20, #0x30]` | - |  |
| `upm.ko` | `.text` | `0x246c` | `0x24d4` | `21 00 80 52` | `52800021` | `mov w1, #0x1 // =1` | - |  |
| `upm.ko` | `.text` | `0x2470` | `0x24d8` | `80 00 00 b4` | `b4000080` | `cbz x0, 0x2480 <k_mss_dump_all+0x328>` | - |  |
| `upm.ko` | `.text` | `0x2474` | `0x24dc` | `01 18 00 b9` | `b9001801` | `str w1, [x0, #0x18]` | - |  |
| `upm.ko` | `.text` | `0x2478` | `0x24e0` | `00 00 40 f9` | `f9400000` | `ldr x0, [x0]` | - |  |
| `upm.ko` | `.text` | `0x247c` | `0x24e4` | `c0 ff ff b5` | `b5ffffc0` | `cbnz x0, 0x2474 <k_mss_dump_all+0x31c>` | - |  |
| `upm.ko` | `.text` | `0x2480` | `0x24e8` | `00 00 00 94` | `94000000` | `bl 0x2480 <k_mss_dump_all+0x328>` | `R_AARCH64_CALL26 k_mss_find_min_request` |  |
| `upm.ko` | `.text` | `0x2484` | `0x24ec` | `a0 f4 ff b4` | `b4fff4a0` | `cbz x0, 0x2318 <k_mss_dump_all+0x1c0>` | - |  |
| `upm.ko` | `.text` | `0x2488` | `0x24f0` | `41 00 80 52` | `52800041` | `mov w1, #0x2 // =2` | - |  |
| `upm.ko` | `.text` | `0x248c` | `0x24f4` | `9f 06 09 29` | `2909069f` | `stp wzr, w1, [x20, #0x48]` | - |  |
| `upm.ko` | `.text` | `0x2490` | `0x24f8` | `00 00 00 94` | `94000000` | `bl 0x2490 <k_mss_dump_all+0x338>` | `R_AARCH64_CALL26 k_mss_start_timer_nr` |  |
| `upm.ko` | `.text` | `0x2494` | `0x24fc` | `63 06 40 b9` | `b9400663` | `ldr w3, [x19, #0x4]` | - |  |
| `upm.ko` | `.text` | `0x2498` | `0x2500` | `f4 03 00 2a` | `2a0003f4` | `mov w20, w0` | - |  |
| `upm.ko` | `.text` | `0x249c` | `0x2504` | `81 40 80 52` | `52804081` | `mov w1, #0x204 // =516` | - |  |
| `upm.ko` | `.text` | `0x24a0` | `0x2508` | `00 44 88 52` | `52884400` | `mov w0, #0x4220 // =16928` | - |  |
| `upm.ko` | `.text` | `0x24a4` | `0x250c` | `04 00 80 52` | `52800004` | `mov w4, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x24a8` | `0x2510` | `02 00 b0 12` | `12b00002` | `mov w2, #0x7fffffff // =2147483647` | - |  |
| `upm.ko` | `.text` | `0x24ac` | `0x2514` | `41 12 a0 72` | `72a01241` | `movk w1, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x24b0` | `0x2518` | `40 12 b0 72` | `72b01240` | `movk w0, #0x8092, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x24b4` | `0x251c` | `00 00 00 94` | `94000000` | `bl 0x24b4 <k_mss_dump_all+0x35c>` | `R_AARCH64_CALL26 upm_c3p_msg_async` |  |
| `upm.ko` | `.text` | `0x24b8` | `0x2520` | `e0 03 14 2a` | `2a1403e0` | `mov w0, w20` | - |  |
| `upm.ko` | `.text` | `0x24bc` | `0x2524` | `71 ff ff 17` | `17ffff71` | `b 0x2280 <k_mss_dump_all+0x128>` | - |  |

#### `.text+0x1220..0x12d8` (`k_mss_add_request_nr` — Proves 28B Request Node Layout: `+0x00=next`, `+0x08=cmd`, `+0x0c=req_id`, `+0x10=timeout_sec`, `+0x14=src_id`, `+0x18=state`)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x1220` | `0x1288` | `fd 7b bd a9` | `a9bd7bfd` | `stp x29, x30, [sp, #-0x30]!` | - |  |
| `upm.ko` | `.text` | `0x1224` | `0x128c` | `fd 03 00 91` | `910003fd` | `mov x29, sp` | - |  |
| `upm.ko` | `.text` | `0x1228` | `0x1290` | `f3 53 01 a9` | `a90153f3` | `stp x19, x20, [sp, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x122c` | `0x1294` | `f4 0a 00 58` | `58000af4` | `ldr x20, 0x1388 <k_mss_add_request_nr+0x168>` | - |  |
| `upm.ko` | `.text` | `0x1230` | `0x1298` | `f5 13 00 f9` | `f90013f5` | `str x21, [sp, #0x20]` | - |  |
| `upm.ko` | `.text` | `0x1234` | `0x129c` | `f5 03 00 aa` | `aa0003f5` | `mov x21, x0` | - |  |
| `upm.ko` | `.text` | `0x1238` | `0x12a0` | `e0 03 14 aa` | `aa1403e0` | `mov x0, x20` | - |  |
| `upm.ko` | `.text` | `0x123c` | `0x12a4` | `93 1a 40 f9` | `f9401a93` | `ldr x19, [x20, #0x30]` | - |  |
| `upm.ko` | `.text` | `0x1240` | `0x12a8` | `00 00 00 94` | `94000000` | `bl 0x1240 <k_mss_add_request_nr+0x20>` | `R_AARCH64_CALL26 mutex_lock` |  |
| `upm.ko` | `.text` | `0x1244` | `0x12ac` | `93 01 00 b4` | `b4000193` | `cbz x19, 0x1274 <k_mss_add_request_nr+0x54>` | - |  |
| `upm.ko` | `.text` | `0x1248` | `0x12b0` | `60 0e 40 b9` | `b9400e60` | `ldr w0, [x19, #0xc]` | - |  |
| `upm.ko` | `.text` | `0x124c` | `0x12b4` | `a1 06 40 b9` | `b94006a1` | `ldr w1, [x21, #0x4]` | - |  |
| `upm.ko` | `.text` | `0x1250` | `0x12b8` | `1f 00 01 6b` | `6b01001f` | `cmp w0, w1` | - |  |
| `upm.ko` | `.text` | `0x1254` | `0x12bc` | `c1 00 00 54` | `540000c1` | `b.ne 0x126c <k_mss_add_request_nr+0x4c>` | - |  |
| `upm.ko` | `.text` | `0x1258` | `0x12c0` | `2e 00 00 14` | `1400002e` | `b 0x1310 <k_mss_add_request_nr+0xf0>` | - |  |
| `upm.ko` | `.text` | `0x125c` | `0x12c4` | `1f 20 03 d5` | `d503201f` | `nop` | - |  |
| `upm.ko` | `.text` | `0x1260` | `0x12c8` | `60 0e 40 b9` | `b9400e60` | `ldr w0, [x19, #0xc]` | - |  |
| `upm.ko` | `.text` | `0x1264` | `0x12cc` | `1f 00 01 6b` | `6b01001f` | `cmp w0, w1` | - |  |
| `upm.ko` | `.text` | `0x1268` | `0x12d0` | `40 05 00 54` | `54000540` | `b.eq 0x1310 <k_mss_add_request_nr+0xf0>` | - |  |
| `upm.ko` | `.text` | `0x126c` | `0x12d4` | `73 02 40 f9` | `f9400273` | `ldr x19, [x19]` | - |  |
| `upm.ko` | `.text` | `0x1270` | `0x12d8` | `93 ff ff b5` | `b5ffff93` | `cbnz x19, 0x1260 <k_mss_add_request_nr+0x40>` | - |  |
| `upm.ko` | `.text` | `0x1274` | `0x12dc` | `e0 08 00 58` | `580008e0` | `ldr x0, 0x1390 <k_mss_add_request_nr+0x170>` | - |  |
| `upm.ko` | `.text` | `0x1278` | `0x12e0` | `00 00 40 b9` | `b9400000` | `ldr w0, [x0]` | - |  |
| `upm.ko` | `.text` | `0x127c` | `0x12e4` | `20 03 00 34` | `34000320` | `cbz w0, 0x12e0 <k_mss_add_request_nr+0xc0>` | - |  |
| `upm.ko` | `.text` | `0x1280` | `0x12e8` | `c0 08 00 58` | `580008c0` | `ldr x0, 0x1398 <k_mss_add_request_nr+0x178>` | - |  |
| `upm.ko` | `.text` | `0x1284` | `0x12ec` | `02 18 80 52` | `52801802` | `mov w2, #0xc0 // =192` | - |  |
| `upm.ko` | `.text` | `0x1288` | `0x12f0` | `02 48 a0 72` | `72a04802` | `movk w2, #0x240, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x128c` | `0x12f4` | `81 03 80 52` | `52800381` | `mov w1, #0x1c // =28` | - |  |
| `upm.ko` | `.text` | `0x1290` | `0x12f8` | `00 00 00 94` | `94000000` | `bl 0x1290 <k_mss_add_request_nr+0x70>` | `R_AARCH64_CALL26 __udif_kmalloc` |  |
| `upm.ko` | `.text` | `0x1294` | `0x12fc` | `f3 03 00 aa` | `aa0003f3` | `mov x19, x0` | - |  |
| `upm.ko` | `.text` | `0x1298` | `0x1300` | `93 06 00 b4` | `b4000693` | `cbz x19, 0x1368 <k_mss_add_request_nr+0x148>` | - |  |
| `upm.ko` | `.text` | `0x129c` | `0x1304` | `61 22 00 91` | `91002261` | `add x1, x19, #0x8` | - |  |
| `upm.ko` | `.text` | `0x12a0` | `0x1308` | `20 00 80 52` | `52800020` | `mov w0, #0x1 // =1` | - |  |
| `upm.ko` | `.text` | `0x12a4` | `0x130c` | `a2 0e 40 a9` | `a9400ea2` | `ldp x2, x3, [x21]` | - |  |
| `upm.ko` | `.text` | `0x12a8` | `0x1310` | `15 00 80 52` | `52800015` | `mov w21, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x12ac` | `0x1314` | `22 0c 00 a9` | `a9000c22` | `stp x2, x3, [x1]` | - |  |
| `upm.ko` | `.text` | `0x12b0` | `0x1318` | `60 1a 00 b9` | `b9001a60` | `str w0, [x19, #0x18]` | - |  |
| `upm.ko` | `.text` | `0x12b4` | `0x131c` | `80 1a 40 f9` | `f9401a80` | `ldr x0, [x20, #0x30]` | - |  |
| `upm.ko` | `.text` | `0x12b8` | `0x1320` | `60 02 00 f9` | `f9000260` | `str x0, [x19]` | - |  |
| `upm.ko` | `.text` | `0x12bc` | `0x1324` | `e0 03 14 aa` | `aa1403e0` | `mov x0, x20` | - |  |
| `upm.ko` | `.text` | `0x12c0` | `0x1328` | `93 1a 00 f9` | `f9001a93` | `str x19, [x20, #0x30]` | - |  |
| `upm.ko` | `.text` | `0x12c4` | `0x132c` | `00 00 00 94` | `94000000` | `bl 0x12c4 <k_mss_add_request_nr+0xa4>` | `R_AARCH64_CALL26 mutex_unlock` |  |
| `upm.ko` | `.text` | `0x12c8` | `0x1330` | `e0 03 15 2a` | `2a1503e0` | `mov w0, w21` | - |  |
| `upm.ko` | `.text` | `0x12cc` | `0x1334` | `f5 13 40 f9` | `f94013f5` | `ldr x21, [sp, #0x20]` | - |  |
| `upm.ko` | `.text` | `0x12d0` | `0x1338` | `f3 53 41 a9` | `a94153f3` | `ldp x19, x20, [sp, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x12d4` | `0x133c` | `fd 7b c3 a8` | `a8c37bfd` | `ldp x29, x30, [sp], #0x30` | - |  |
| `upm.ko` | `.text` | `0x12d8` | `0x1340` | `c0 03 5f d6` | `d65f03c0` | `ret` | - |  |

#### `.text+0x1558..0x15f8` (`k_mss_find_min_request` — Scans `[x20+0x30]` for Minimum `[node+0x10]` with `[node+0x18] != 3`)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x1558` | `0x15c0` | `fd 7b be a9` | `a9be7bfd` | `stp x29, x30, [sp, #-0x20]!` | - |  |
| `upm.ko` | `.text` | `0x155c` | `0x15c4` | `fd 03 00 91` | `910003fd` | `mov x29, sp` | - |  |
| `upm.ko` | `.text` | `0x1560` | `0x15c8` | `f3 53 01 a9` | `a90153f3` | `stp x19, x20, [sp, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x1564` | `0x15cc` | `f4 04 00 58` | `580004f4` | `ldr x20, 0x1600 <k_mss_find_min_request+0xa8>` | - |  |
| `upm.ko` | `.text` | `0x1568` | `0x15d0` | `e0 03 14 aa` | `aa1403e0` | `mov x0, x20` | - |  |
| `upm.ko` | `.text` | `0x156c` | `0x15d4` | `00 00 00 94` | `94000000` | `bl 0x156c <k_mss_find_min_request+0x14>` | `R_AARCH64_CALL26 mutex_lock` |  |
| `upm.ko` | `.text` | `0x1570` | `0x15d8` | `81 1a 40 f9` | `f9401a81` | `ldr x1, [x20, #0x30]` | - |  |
| `upm.ko` | `.text` | `0x1574` | `0x15dc` | `01 02 00 b4` | `b4000201` | `cbz x1, 0x15b4 <k_mss_find_min_request+0x5c>` | - |  |
| `upm.ko` | `.text` | `0x1578` | `0x15e0` | `20 00 40 f9` | `f9400020` | `ldr x0, [x1]` | - |  |
| `upm.ko` | `.text` | `0x157c` | `0x15e4` | `e0 02 00 b4` | `b40002e0` | `cbz x0, 0x15d8 <k_mss_find_min_request+0x80>` | - |  |
| `upm.ko` | `.text` | `0x1580` | `0x15e8` | `13 00 80 d2` | `d2800013` | `mov x19, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x1584` | `0x15ec` | `22 18 40 b9` | `b9401822` | `ldr w2, [x1, #0x18]` | - |  |
| `upm.ko` | `.text` | `0x1588` | `0x15f0` | `5f 0c 00 71` | `71000c5f` | `cmp w2, #0x3` | - |  |
| `upm.ko` | `.text` | `0x158c` | `0x15f4` | `c0 00 00 54` | `540000c0` | `b.eq 0x15a4 <k_mss_find_min_request+0x4c>` | - |  |
| `upm.ko` | `.text` | `0x1590` | `0x15f8` | `13 02 00 b4` | `b4000213` | `cbz x19, 0x15d0 <k_mss_find_min_request+0x78>` | - |  |
| `upm.ko` | `.text` | `0x1594` | `0x15fc` | `63 12 40 b9` | `b9401263` | `ldr w3, [x19, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x1598` | `0x1600` | `22 10 40 b9` | `b9401022` | `ldr w2, [x1, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x159c` | `0x1604` | `7f 00 02 6b` | `6b02007f` | `cmp w3, w2` | - |  |
| `upm.ko` | `.text` | `0x15a0` | `0x1608` | `73 92 81 9a` | `9a819273` | `csel x19, x19, x1, ls` | - |  |
| `upm.ko` | `.text` | `0x15a4` | `0x160c` | `a0 00 00 b4` | `b40000a0` | `cbz x0, 0x15b8 <k_mss_find_min_request+0x60>` | - |  |
| `upm.ko` | `.text` | `0x15a8` | `0x1610` | `e1 03 00 aa` | `aa0003e1` | `mov x1, x0` | - |  |
| `upm.ko` | `.text` | `0x15ac` | `0x1614` | `00 00 40 f9` | `f9400000` | `ldr x0, [x0]` | - |  |
| `upm.ko` | `.text` | `0x15b0` | `0x1618` | `f5 ff ff 17` | `17fffff5` | `b 0x1584 <k_mss_find_min_request+0x2c>` | - |  |
| `upm.ko` | `.text` | `0x15b4` | `0x161c` | `13 00 80 d2` | `d2800013` | `mov x19, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x15b8` | `0x1620` | `e0 03 14 aa` | `aa1403e0` | `mov x0, x20` | - |  |
| `upm.ko` | `.text` | `0x15bc` | `0x1624` | `00 00 00 94` | `94000000` | `bl 0x15bc <k_mss_find_min_request+0x64>` | `R_AARCH64_CALL26 mutex_unlock` |  |
| `upm.ko` | `.text` | `0x15c0` | `0x1628` | `e0 03 13 aa` | `aa1303e0` | `mov x0, x19` | - |  |
| `upm.ko` | `.text` | `0x15c4` | `0x162c` | `f3 53 41 a9` | `a94153f3` | `ldp x19, x20, [sp, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x15c8` | `0x1630` | `fd 7b c2 a8` | `a8c27bfd` | `ldp x29, x30, [sp], #0x20` | - |  |
| `upm.ko` | `.text` | `0x15cc` | `0x1634` | `c0 03 5f d6` | `d65f03c0` | `ret` | - |  |
| `upm.ko` | `.text` | `0x15d0` | `0x1638` | `f3 03 01 aa` | `aa0103f3` | `mov x19, x1` | - |  |
| `upm.ko` | `.text` | `0x15d4` | `0x163c` | `f4 ff ff 17` | `17fffff4` | `b 0x15a4 <k_mss_find_min_request+0x4c>` | - |  |
| `upm.ko` | `.text` | `0x15d8` | `0x1640` | `20 18 40 b9` | `b9401820` | `ldr w0, [x1, #0x18]` | - |  |
| `upm.ko` | `.text` | `0x15dc` | `0x1644` | `1f 0c 00 71` | `71000c1f` | `cmp w0, #0x3` | - |  |
| `upm.ko` | `.text` | `0x15e0` | `0x1648` | `e0 03 14 aa` | `aa1403e0` | `mov x0, x20` | - |  |
| `upm.ko` | `.text` | `0x15e4` | `0x164c` | `33 10 9f 9a` | `9a9f1033` | `csel x19, x1, xzr, ne` | - |  |
| `upm.ko` | `.text` | `0x15e8` | `0x1650` | `00 00 00 94` | `94000000` | `bl 0x15e8 <k_mss_find_min_request+0x90>` | `R_AARCH64_CALL26 mutex_unlock` |  |
| `upm.ko` | `.text` | `0x15ec` | `0x1654` | `e0 03 13 aa` | `aa1303e0` | `mov x0, x19` | - |  |
| `upm.ko` | `.text` | `0x15f0` | `0x1658` | `f3 53 41 a9` | `a94153f3` | `ldp x19, x20, [sp, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x15f4` | `0x165c` | `fd 7b c2 a8` | `a8c27bfd` | `ldp x29, x30, [sp], #0x20` | - |  |
| `upm.ko` | `.text` | `0x15f8` | `0x1660` | `c0 03 5f d6` | `d65f03c0` | `ret` | - |  |

#### `.text+0x1008..0x1098` (`k_mss_start_timer_nr` — Computes `([x6+0x10] - [x20+0x48]) * 0x000f4240` us and Calls `osal_snd_sync_direct`)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x1008` | `0x1070` | `c0 07 00 b4` | `b40007c0` | `cbz x0, 0x1100 <k_mss_start_timer_nr+0xf8>` | - |  |
| `upm.ko` | `.text` | `0x100c` | `0x1074` | `fd 7b ba a9` | `a9ba7bfd` | `stp x29, x30, [sp, #-0x60]!` | - |  |
| `upm.ko` | `.text` | `0x1010` | `0x1078` | `e6 03 00 aa` | `aa0003e6` | `mov x6, x0` | - |  |
| `upm.ko` | `.text` | `0x1014` | `0x107c` | `05 00 80 52` | `52800005` | `mov w5, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x1018` | `0x1080` | `04 00 80 d2` | `d2800004` | `mov x4, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x101c` | `0x1084` | `fd 03 00 91` | `910003fd` | `mov x29, sp` | - |  |
| `upm.ko` | `.text` | `0x1020` | `0x1088` | `f3 53 01 a9` | `a90153f3` | `stp x19, x20, [sp, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x1024` | `0x108c` | `63 22 80 52` | `52802263` | `mov w3, #0x113 // =275` | - |  |
| `upm.ko` | `.text` | `0x1028` | `0x1090` | `14 07 00 58` | `58000714` | `ldr x20, 0x1108 <k_mss_start_timer_nr+0x100>` | - |  |
| `upm.ko` | `.text` | `0x102c` | `0x1094` | `42 01 80 52` | `52800142` | `mov w2, #0xa // =10` | - |  |
| `upm.ko` | `.text` | `0x1030` | `0x1098` | `01 00 80 52` | `52800001` | `mov w1, #0x0 // =0` | - |  |
| `upm.ko` | `.text` | `0x1034` | `0x109c` | `40 00 80 52` | `52800040` | `mov w0, #0x2 // =2` | - |  |
| `upm.ko` | `.text` | `0x1038` | `0x10a0` | `86 1e 00 f9` | `f9001e86` | `str x6, [x20, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x103c` | `0x10a4` | `d3 10 40 b9` | `b94010d3` | `ldr w19, [x6, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x1040` | `0x10a8` | `00 00 00 94` | `94000000` | `bl 0x1040 <k_mss_start_timer_nr+0x38>` | `R_AARCH64_CALL26 upm_blog_writeonce` |  |
| `upm.ko` | `.text` | `0x1044` | `0x10ac` | `82 4a 40 b9` | `b9404a82` | `ldr w2, [x20, #0x48]` | - |  |
| `upm.ko` | `.text` | `0x1048` | `0x10b0` | `05 48 88 52` | `52884805` | `mov w5, #0x4240 // =16960` | - |  |
| `upm.ko` | `.text` | `0x104c` | `0x10b4` | `e5 01 a0 72` | `72a001e5` | `movk w5, #0xf, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x1050` | `0x10b8` | `a1 a3 00 91` | `9100a3a1` | `add x1, x29, #0x28` | - |  |
| `upm.ko` | `.text` | `0x1054` | `0x10bc` | `73 02 02 4b` | `4b020273` | `sub w19, w19, w2` | - |  |
| `upm.ko` | `.text` | `0x1058` | `0x10c0` | `a6 e3 00 91` | `9100e3a6` | `add x6, x29, #0x38` | - |  |
| `upm.ko` | `.text` | `0x105c` | `0x10c4` | `82 16 40 f9` | `f9401682` | `ldr x2, [x20, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x1060` | `0x10c8` | `00 08 80 52` | `52800800` | `mov w0, #0x40 // =64` | - |  |
| `upm.ko` | `.text` | `0x1064` | `0x10cc` | `04 07 80 52` | `52800704` | `mov w4, #0x38 // =56` | - |  |
| `upm.ko` | `.text` | `0x1068` | `0x10d0` | `43 00 80 52` | `52800043` | `mov w3, #0x2 // =2` | - |  |
| `upm.ko` | `.text` | `0x106c` | `0x10d4` | `73 7e a5 9b` | `9ba57e73` | `umull x19, w19, w5` | - |  |
| `upm.ko` | `.text` | `0x1070` | `0x10d8` | `a5 23 01 91` | `910123a5` | `add x5, x29, #0x48` | - |  |
| `upm.ko` | `.text` | `0x1074` | `0x10dc` | `20 12 a0 72` | `72a01220` | `movk w0, #0x91, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x1078` | `0x10e0` | `3f 7c 00 a9` | `a9007c3f` | `stp xzr, xzr, [x1]` | - |  |
| `upm.ko` | `.text` | `0x107c` | `0x10e4` | `df 7c 00 a9` | `a9007cdf` | `stp xzr, xzr, [x6]` | - |  |
| `upm.ko` | `.text` | `0x1080` | `0x10e8` | `bf 7c 00 a9` | `a9007cbf` | `stp xzr, xzr, [x5]` | - |  |
| `upm.ko` | `.text` | `0x1084` | `0x10ec` | `a4 2b 00 b9` | `b9002ba4` | `str w4, [x29, #0x28]` | - |  |
| `upm.ko` | `.text` | `0x1088` | `0x10f0` | `a3 3b 00 b9` | `b9003ba3` | `str w3, [x29, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x108c` | `0x10f4` | `a2 4f 04 a9` | `a9044fa2` | `stp x2, x19, [x29, #0x40]` | - |  |
| `upm.ko` | `.text` | `0x1090` | `0x10f8` | `bf 2f 00 f9` | `f9002fbf` | `str xzr, [x29, #0x58]` | - |  |
| `upm.ko` | `.text` | `0x1094` | `0x10fc` | `00 00 00 94` | `94000000` | `bl 0x1094 <k_mss_start_timer_nr+0x8c>` | `R_AARCH64_CALL26 osal_snd_sync_direct` |  |
| `upm.ko` | `.text` | `0x1098` | `0x1100` | `80 02 00 34` | `34000280` | `cbz w0, 0x10e8 <k_mss_start_timer_nr+0xe0>` | - |  |

#### `.text+0x1670..0x1704` (`k_mss_timer_cb` — Updates `elapsed_sec = [active_req+0x10]` and Chains Remaining Period)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `upm.ko` | `.text` | `0x1670` | `0x16d8` | `fd 7b be a9` | `a9be7bfd` | `stp x29, x30, [sp, #-0x20]!` | - |  |
| `upm.ko` | `.text` | `0x1674` | `0x16dc` | `fd 03 00 91` | `910003fd` | `mov x29, sp` | - |  |
| `upm.ko` | `.text` | `0x1678` | `0x16e0` | `f3 53 01 a9` | `a90153f3` | `stp x19, x20, [sp, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x167c` | `0x16e4` | `60 04 00 b4` | `b4000460` | `cbz x0, 0x1708 <k_mss_timer_cb+0x98>` | - |  |
| `upm.ko` | `.text` | `0x1680` | `0x16e8` | `20 44 80 52` | `52804420` | `mov w0, #0x221 // =545` | - |  |
| `upm.ko` | `.text` | `0x1684` | `0x16ec` | `01 00 80 12` | `12800001` | `mov w1, #-0x1 // =-1` | - |  |
| `upm.ko` | `.text` | `0x1688` | `0x16f0` | `40 12 a0 72` | `72a01240` | `movk w0, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x168c` | `0x16f4` | `00 00 00 94` | `94000000` | `bl 0x168c <k_mss_timer_cb+0x1c>` | `R_AARCH64_CALL26 osal_wai_sem_tmo` |  |
| `upm.ko` | `.text` | `0x1690` | `0x16f8` | `93 04 00 58` | `58000493` | `ldr x19, 0x1720 <k_mss_timer_cb+0xb0>` | - |  |
| `upm.ko` | `.text` | `0x1694` | `0x16fc` | `74 1e 40 f9` | `f9401e74` | `ldr x20, [x19, #0x38]` | - |  |
| `upm.ko` | `.text` | `0x1698` | `0x1700` | `d4 02 00 b4` | `b40002d4` | `cbz x20, 0x16f0 <k_mss_timer_cb+0x80>` | - |  |
| `upm.ko` | `.text` | `0x169c` | `0x1704` | `60 00 80 52` | `52800060` | `mov w0, #0x3 // =3` | - |  |
| `upm.ko` | `.text` | `0x16a0` | `0x1708` | `60 4e 00 b9` | `b9004e60` | `str w0, [x19, #0x4c]` | - |  |
| `upm.ko` | `.text` | `0x16a4` | `0x170c` | `00 00 00 94` | `94000000` | `bl 0x16a4 <k_mss_timer_cb+0x34>` | `R_AARCH64_CALL26 k_mss_stop_timer_nr` |  |
| `upm.ko` | `.text` | `0x16a8` | `0x1710` | `81 12 40 b9` | `b9401281` | `ldr w1, [x20, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x16ac` | `0x1714` | `e0 03 14 aa` | `aa1403e0` | `mov x0, x20` | - |  |
| `upm.ko` | `.text` | `0x16b0` | `0x1718` | `61 4a 00 b9` | `b9004a61` | `str w1, [x19, #0x48]` | - |  |
| `upm.ko` | `.text` | `0x16b4` | `0x171c` | `00 00 00 94` | `94000000` | `bl 0x16b4 <k_mss_timer_cb+0x44>` | `R_AARCH64_CALL26 k_mss_fire_all_expired_nr` |  |
| `upm.ko` | `.text` | `0x16b8` | `0x1720` | `00 00 00 94` | `94000000` | `bl 0x16b8 <k_mss_timer_cb+0x48>` | `R_AARCH64_CALL26 k_mss_find_min_request` |  |
| `upm.ko` | `.text` | `0x16bc` | `0x1724` | `a0 00 00 b4` | `b40000a0` | `cbz x0, 0x16d0 <k_mss_timer_cb+0x60>` | - |  |
| `upm.ko` | `.text` | `0x16c0` | `0x1728` | `41 00 80 52` | `52800041` | `mov w1, #0x2 // =2` | - |  |
| `upm.ko` | `.text` | `0x16c4` | `0x172c` | `61 4e 00 b9` | `b9004e61` | `str w1, [x19, #0x4c]` | - |  |
| `upm.ko` | `.text` | `0x16c8` | `0x1730` | `00 00 00 94` | `94000000` | `bl 0x16c8 <k_mss_timer_cb+0x58>` | `R_AARCH64_CALL26 k_mss_start_timer_nr` |  |
| `upm.ko` | `.text` | `0x16cc` | `0x1734` | `20 01 00 34` | `34000120` | `cbz w0, 0x16f0 <k_mss_timer_cb+0x80>` | - |  |
| `upm.ko` | `.text` | `0x16d0` | `0x1738` | `60 1a 40 f9` | `f9401a60` | `ldr x0, [x19, #0x30]` | - |  |
| `upm.ko` | `.text` | `0x16d4` | `0x173c` | `21 00 80 52` | `52800021` | `mov w1, #0x1 // =1` | - |  |
| `upm.ko` | `.text` | `0x16d8` | `0x1740` | `80 00 00 b4` | `b4000080` | `cbz x0, 0x16e8 <k_mss_timer_cb+0x78>` | - |  |
| `upm.ko` | `.text` | `0x16dc` | `0x1744` | `01 18 00 b9` | `b9001801` | `str w1, [x0, #0x18]` | - |  |
| `upm.ko` | `.text` | `0x16e0` | `0x1748` | `00 00 40 f9` | `f9400000` | `ldr x0, [x0]` | - |  |
| `upm.ko` | `.text` | `0x16e4` | `0x174c` | `c0 ff ff b5` | `b5ffffc0` | `cbnz x0, 0x16dc <k_mss_timer_cb+0x6c>` | - |  |
| `upm.ko` | `.text` | `0x16e8` | `0x1750` | `20 00 80 52` | `52800020` | `mov w0, #0x1 // =1` | - |  |
| `upm.ko` | `.text` | `0x16ec` | `0x1754` | `7f 02 09 29` | `2909027f` | `stp wzr, w0, [x19, #0x48]` | - |  |
| `upm.ko` | `.text` | `0x16f0` | `0x1758` | `20 44 80 52` | `52804420` | `mov w0, #0x221 // =545` | - |  |
| `upm.ko` | `.text` | `0x16f4` | `0x175c` | `40 12 a0 72` | `72a01240` | `movk w0, #0x92, lsl #16` | - |  |
| `upm.ko` | `.text` | `0x16f8` | `0x1760` | `00 00 00 94` | `94000000` | `bl 0x16f8 <k_mss_timer_cb+0x88>` | `R_AARCH64_CALL26 osal_sig_sem` |  |
| `upm.ko` | `.text` | `0x16fc` | `0x1764` | `f3 53 41 a9` | `a94153f3` | `ldp x19, x20, [sp, #0x10]` | - |  |
| `upm.ko` | `.text` | `0x1700` | `0x1768` | `fd 7b c2 a8` | `a8c27bfd` | `ldp x29, x30, [sp], #0x20` | - |  |
| `upm.ko` | `.text` | `0x1704` | `0x176c` | `c0 03 5f d6` | `d65f03c0` | `ret` | - |  |

---

## 5. Machine-Generated Disassembly: `appFw.so` `App::got_display_update_event` (`0x16f11e8`) & Narrowed Downstream Boundary

- **What is statically proven (`STATIC_ORIGINAL_CODE`)**:
  1. `App::got_display_update_event(const ds_display_update_event&)` (`0x16f11e8..0x16f1350`, `.rodata` string at `0x2f9e978`) allocates a 20B (`0x14`) message via `osal_valloc_msg_wait@plt` (`0x16f1214`), copies 20 bytes from `[x19]` into `[x0]` (`0x16f12bc..0x16f12c8`), sets source `0x00830128` via `osal_set_msg_src@plt` (`0x16f12d8`), and sends asynchronously to QID `0x005503e0` via `osal_snd_msg@plt` (`0x16f12e8`, return check at `0x16f12ec`). It contains no call to `0x2eaf294` or any `0x80924220` sender.
  2. In the `0x005503e0` classifier (`0x16f3750..0x16f3900`), `0x16f38c8..0x16f38d0` writes `w0 = 5` to `[x19, #0x8]` (`528000a0` `mov w0, #0x5`; `b9000a60` `str w0, [x19, #0x8]`) and branches to `0x16f4748`.
- **What is NOT statically proven (`UNKNOWN_STATICALLY` without runtime trace)**:
  - Static inspection of `0x16f11e8..0x16f1350` and `0x16f3750..0x16f3900` does **not** prove that downstream UI/presenter/screen handlers invoked after the `0x005503e0` event loop dispatches event type `5` can never call `upm_mss_*` wrappers (`0x2de0254..0x2de057c` -> `0x2eb4f24..0x2eb74d8` -> `0x2eaf294`). Whether downstream handlers trigger any `0x80924220` message during `MENU`/`LEFT`/`DOWN` must be determined empirically by widening the read-only observation filter at `0x2eaf294`.

#### `0x16f11e8..0x16f1218` & `0x16f12a8..0x16f12ec` (`App::got_display_update_event` Allocation & Send Path)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `appFw.so` | `.text` | `0x16f11e8` | `0x16f11e8` | `fd 7b bc a9` | `a9bc7bfd` | `stp x29, x30, [sp, #-0x40]!` | - |  |
| `appFw.so` | `.text` | `0x16f11ec` | `0x16f11ec` | `00 7c 80 52` | `52807c00` | `mov w0, #0x3e0 // =992` | - |  |
| `appFw.so` | `.text` | `0x16f11f0` | `0x16f11f0` | `23 00 80 52` | `52800023` | `mov w3, #0x1 // =1` | - |  |
| `appFw.so` | `.text` | `0x16f11f4` | `0x16f11f4` | `82 02 80 52` | `52800282` | `mov w2, #0x14 // =20` | - |  |
| `appFw.so` | `.text` | `0x16f11f8` | `0x16f11f8` | `fd 03 00 91` | `910003fd` | `mov x29, sp` | - |  |
| `appFw.so` | `.text` | `0x16f11fc` | `0x16f11fc` | `f3 53 01 a9` | `a90153f3` | `stp x19, x20, [sp, #0x10]` | - |  |
| `appFw.so` | `.text` | `0x16f1200` | `0x16f1200` | `f3 03 01 aa` | `aa0103f3` | `mov x19, x1` | - |  |
| `appFw.so` | `.text` | `0x16f1204` | `0x16f1204` | `a1 03 01 91` | `910103a1` | `add x1, x29, #0x40` | - |  |
| `appFw.so` | `.text` | `0x16f1208` | `0x16f1208` | `f5 5b 02 a9` | `a9025bf5` | `stp x21, x22, [sp, #0x20]` | - |  |
| `appFw.so` | `.text` | `0x16f120c` | `0x16f120c` | `a0 0a a0 72` | `72a00aa0` | `movk w0, #0x55, lsl #16` | - |  |
| `appFw.so` | `.text` | `0x16f1210` | `0x16f1210` | `3f 8c 1f f8` | `f81f8c3f` | `str xzr, [x1, #-0x8]!` | - |  |
| `appFw.so` | `.text` | `0x16f1214` | `0x16f1214` | `c3 8b fa 97` | `97fa8bc3` | `bl 0x1594120 <osal_valloc_msg_wait@plt>` | - |  |
| `appFw.so` | `.text` | `0x16f1218` | `0x16f1218` | `00 05 00 34` | `34000500` | `cbz w0, 0x16f12b8 <Application_System_Init+0x1728>` | - |  |

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `appFw.so` | `.text` | `0x16f12a8` | `0x16f12a8` | `f3 53 41 a9` | `a94153f3` | `ldp x19, x20, [sp, #0x10]` | - |  |
| `appFw.so` | `.text` | `0x16f12ac` | `0x16f12ac` | `f5 5b 42 a9` | `a9425bf5` | `ldp x21, x22, [sp, #0x20]` | - |  |
| `appFw.so` | `.text` | `0x16f12b0` | `0x16f12b0` | `fd 7b c4 a8` | `a8c47bfd` | `ldp x29, x30, [sp], #0x40` | - |  |
| `appFw.so` | `.text` | `0x16f12b4` | `0x16f12b4` | `c0 03 5f d6` | `d65f03c0` | `ret` | - |  |
| `appFw.so` | `.text` | `0x16f12b8` | `0x16f12b8` | `a0 1f 40 f9` | `f9401fa0` | `ldr x0, [x29, #0x38]` | - |  |
| `appFw.so` | `.text` | `0x16f12bc` | `0x16f12bc` | `62 0e 40 a9` | `a9400e62` | `ldp x2, x3, [x19]` | - |  |
| `appFw.so` | `.text` | `0x16f12c0` | `0x16f12c0` | `02 0c 00 a9` | `a9000c02` | `stp x2, x3, [x0]` | - |  |
| `appFw.so` | `.text` | `0x16f12c4` | `0x16f12c4` | `61 12 40 b9` | `b9401261` | `ldr w1, [x19, #0x10]` | - |  |
| `appFw.so` | `.text` | `0x16f12c8` | `0x16f12c8` | `01 10 00 b9` | `b9001001` | `str w1, [x0, #0x10]` | - |  |
| `appFw.so` | `.text` | `0x16f12cc` | `0x16f12cc` | `01 25 80 52` | `52802501` | `mov w1, #0x128 // =296` | - |  |
| `appFw.so` | `.text` | `0x16f12d0` | `0x16f12d0` | `a0 1f 40 f9` | `f9401fa0` | `ldr x0, [x29, #0x38]` | - |  |
| `appFw.so` | `.text` | `0x16f12d4` | `0x16f12d4` | `61 10 a0 72` | `72a01061` | `movk w1, #0x83, lsl #16` | - |  |
| `appFw.so` | `.text` | `0x16f12d8` | `0x16f12d8` | `ca 82 fa 97` | `97fa82ca` | `bl 0x1591e00 <osal_set_msg_src@plt>` | - |  |
| `appFw.so` | `.text` | `0x16f12dc` | `0x16f12dc` | `a1 1f 40 f9` | `f9401fa1` | `ldr x1, [x29, #0x38]` | - |  |
| `appFw.so` | `.text` | `0x16f12e0` | `0x16f12e0` | `00 7c 80 52` | `52807c00` | `mov w0, #0x3e0 // =992` | - |  |
| `appFw.so` | `.text` | `0x16f12e4` | `0x16f12e4` | `a0 0a a0 72` | `72a00aa0` | `movk w0, #0x55, lsl #16` | - |  |
| `appFw.so` | `.text` | `0x16f12e8` | `0x16f12e8` | `0a 87 fa 97` | `97fa870a` | `bl 0x1592f10 <osal_snd_msg@plt>` | - |  |
| `appFw.so` | `.text` | `0x16f12ec` | `0x16f12ec` | `e0 fd ff 34` | `34fffde0` | `cbz w0, 0x16f12a8 <Application_System_Init+0x1718>` | - |  |

#### `0x16f38b4..0x16f38d0` (`0x005503e0` Classifier Setting Event Type `5`)

| Binary | Section | VA | File Offset | Raw Bytes (LE) | U32 Word | Objdump Disassembly | Relocation | Verified Role / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `appFw.so` | `.text` | `0x16f38b4` | `0x16f38b4` | `e1 83 0f 32` | `320f83e1` | `mov w1, #0x20002 // =131074` | - |  |
| `appFw.so` | `.text` | `0x16f38b8` | `0x16f38b8` | `1f 00 01 6b` | `6b01001f` | `cmp w0, w1` | - |  |
| `appFw.so` | `.text` | `0x16f38bc` | `0x16f38bc` | `69 00 00 54` | `54000069` | `b.ls 0x16f38c8 <Application_System_Init+0x3d38>` | - |  |
| `appFw.so` | `.text` | `0x16f38c0` | `0x16f38c0` | `1f 80 41 71` | `7141801f` | `cmp w0, #0x60, lsl #12 // =0x60000` | - |  |
| `appFw.so` | `.text` | `0x16f38c4` | `0x16f38c4` | `21 74 00 54` | `54007421` | `b.ne 0x16f4748 <Application_System_Init+0x4bb8>` | - |  |
| `appFw.so` | `.text` | `0x16f38c8` | `0x16f38c8` | `a0 00 80 52` | `528000a0` | `mov w0, #0x5 // =5` | - |  |
| `appFw.so` | `.text` | `0x16f38cc` | `0x16f38cc` | `60 0a 00 b9` | `b9000a60` | `str w0, [x19, #0x8]` | - |  |
| `appFw.so` | `.text` | `0x16f38d0` | `0x16f38d0` | `9e 03 00 14` | `1400039e` | `b 0x16f4748 <Application_System_Init+0x4bb8>` | - |  |

---

## 6. Reproducible Generation & Post-Generation Document Verification

Run in [`display-contract/`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract):

```bash
python3 verify_display_contract_v4.py
```

