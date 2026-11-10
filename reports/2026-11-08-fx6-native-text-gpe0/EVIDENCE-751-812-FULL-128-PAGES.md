# FX6 Native `gpe0` (`0x41e001000`) Evidence Report — Rounds `751`–`812` (100% Full 128-Page Descriptor Coverage)

## 1. Milestone Summary

With Rounds **`751`–`812`** (62 pages), **100% of all 128 native Sony FX6 v5.00 (`ILME-FX6V`) page descriptor tables (`fx6_all_pages[0..127]`, 2,249 total widget rows in `appFw.so` at offsets `0x02e90cf8 .. 0x02eba260`)** have been rendered in-guest by ARM64 `appFw.so` + `libuxengine.so` + `libgemini-grm.so` into physical framebuffer `0x41e001000` (`gpe0`, `1024×540` RGBA32) with **`nz > 0` and `segv = 0` across all 128 pages**.

- **Interactive Web Console (`http://127.0.0.1:8768/`)**:
  - Added `case 24:` **Universal Descriptor Table Mode** in [fx6_live_guest.c](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx3-vm-trial/src/fx6_live_guest.c) (`cell_vals[0..3] = {table_off, table_rows, table_off2, table_rows2}` via `0x41e000e00` mailbox).
  - Added `/api/pages128` and the `#all128-select` 128-page dropdown selector (`Page 000 .. Page 127` + `◀ 上一页` / `下一页 ▶`) in [run_fx6_menu_trial.py](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx3-vm-trial/run_fx6_menu_trial.py), alongside the 24 main preset buttons (`0..23`) and 11 Three-Layer Menu category buttons.
- **Repacked Rootfs CPIO**:
  - [guest-hybrid-fx6kernel-capid-grmreal-live700.cpio](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx3-vm-trial/guest-hybrid-fx6kernel-capid-grmreal-live700.cpio) (`416,873,248` bytes, `sha256: fdda9edd711d4e98807a542873c103d0a1107bb3b6030c1118f5891ae01c9850`)
  - [vm-candidate-gpecap25-live700.json](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx3-vm-trial/vm-candidate-gpecap25-live700.json)

---

## 2. Rounds `751`–`812` Framebuffer Metrics (`0x41e001000` `gpe0`)

| Round | Artifact PNG | `appFw.so` Page (`offset`, rows) | `text_ok` | `fill` | `icon` | `gpe0` Non-Zero (`nz`) | White Glyph Pixels (`>=200`) | `segv` |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `751` | [menu-751-page126r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-751-page126r7.png) | Page 126 (`0x02eba260`, 7r) | **4** | 2 | 1 | `435,024` | `1,003` | `0` |
| `752` | [menu-752-page105r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-752-page105r7.png) | Page 105 (`0x02eb5fc0`, 7r) | **4** | 2 | 1 | `435,024` | `1,003` | `0` |
| `753` | [menu-753-page091r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-753-page091r7.png) | Page 91 (`0x02eb46e0`, 7r) | **4** | 1 | 2 | `435,024` | `591` | `0` |
| `754` | [menu-754-page085r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-754-page085r7.png) | Page 85 (`0x02eb34b0`, 7r) | **0** | 5 | 0 | `369,200` | `0` | `0` |
| `755` | [menu-755-page080r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-755-page080r7.png) | Page 80 (`0x02eb2b68`, 7r) | **3** | 3 | 0 | `435,024` | `1,158` | `0` |
| `756` | [menu-756-page054r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-756-page054r7.png) | Page 54 (`0x02eaa150`, 7r) | **0** | 3 | 1 | `435,024` | `141` | `0` |
| `757` | [menu-757-page048r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-757-page048r7.png) | Page 48 (`0x02ea65f8`, 7r) | **1** | 4 | 0 | `552,960` | `94` | `0` |
| `758` | [menu-758-page038r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-758-page038r7.png) | Page 38 (`0x02ea4318`, 7r) | **2** | 3 | 1 | `435,024` | `358` | `0` |
| `759` | [menu-759-page037r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-759-page037r7.png) | Page 37 (`0x02ea4120`, 7r) | **2** | 3 | 1 | `435,024` | `264` | `0` |
| `760` | [menu-760-page000r7.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-760-page000r7.png) | Page 0 (`0x02e90cf8`, 7r) | **2** | 2 | 1 | `435,024` | `395` | `0` |
| `761` | [menu-761-page107r6.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-761-page107r6.png) | Page 107 (`0x02eb6258`, 6r) | **2** | 2 | 1 | `144,716` | `358` | `0` |
| `762` | [menu-762-page106r6.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-762-page106r6.png) | Page 106 (`0x02eb61b8`, 6r) | **2** | 2 | 1 | `144,716` | `358` | `0` |
| `763` | [menu-763-page051r6.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-763-page051r6.png) | Page 51 (`0x02ea7140`, 6r) | **2** | 2 | 0 | `435,024` | `347` | `0` |
| `764` | [menu-764-page020r6.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-764-page020r6.png) | Page 20 (`0x02e9dc28`, 6r) | **3** | 2 | 0 | `435,024` | `512` | `0` |
| `765` | [menu-765-page118r5.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-765-page118r5.png) | Page 118 (`0x02eb9308`, 5r) | **0** | 2 | 1 | `435,024` | `141` | `0` |
| `766` | [menu-766-page096r5.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-766-page096r5.png) | Page 96 (`0x02eb5160`, 5r) | **2** | 2 | 1 | `435,024` | `1,001` | `0` |
| `767` | [menu-767-page052r5.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-767-page052r5.png) | Page 52 (`0x02ea72f0`, 5r) | **2** | 2 | 0 | `435,024` | `370` | `0` |
| `768` | [menu-768-page026r5.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-768-page026r5.png) | Page 26 (`0x02ea2bc0`, 5r) | **1** | 3 | 0 | `552,960` | `94` | `0` |
| `769` | [menu-769-page125r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-769-page125r4.png) | Page 125 (`0x02eba188`, 4r) | **1** | 2 | 1 | `435,024` | `512` | `0` |
| `770` | [menu-770-page124r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-770-page124r4.png) | Page 124 (`0x02eba0b0`, 4r) | **1** | 1 | 1 | `59,696` | `475` | `0` |
| `771` | [menu-771-page123r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-771-page123r4.png) | Page 123 (`0x02eb9f00`, 4r) | **1** | 1 | 1 | `59,696` | `475` | `0` |
| `772` | [menu-772-page121r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-772-page121r4.png) | Page 121 (`0x02eb99f0`, 4r) | **1** | 2 | 1 | `435,024` | `512` | `0` |
| `773` | [menu-773-page115r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-773-page115r4.png) | Page 115 (`0x02eb8dd8`, 4r) | **0** | 2 | 1 | `435,024` | `59` | `0` |
| `774` | [menu-774-page104r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-774-page104r4.png) | Page 104 (`0x02eb5ee8`, 4r) | **1** | 2 | 1 | `435,024` | `512` | `0` |
| `775` | [menu-775-page099r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-775-page099r4.png) | Page 99 (`0x02eb57f8`, 4r) | **1** | 2 | 1 | `435,024` | `512` | `0` |
| `776` | [menu-776-page094r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-776-page094r4.png) | Page 94 (`0x02eb4dd0`, 4r) | **1** | 2 | 1 | `435,024` | `512` | `0` |
| `777` | [menu-777-page082r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-777-page082r4.png) | Page 82 (`0x02eb2ff8`, 4r) | **1** | 2 | 0 | `435,024` | `94` | `0` |
| `778` | [menu-778-page079r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-778-page079r4.png) | Page 79 (`0x02eb2a90`, 4r) | **1** | 2 | 0 | `435,024` | `94` | `0` |
| `779` | [menu-779-page075r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-779-page075r4.png) | Page 75 (`0x02eb1138`, 4r) | **1** | 2 | 1 | `435,024` | `1,000` | `0` |
| `780` | [menu-780-page060r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-780-page060r4.png) | Page 60 (`0x02eabc00`, 4r) | **1** | 2 | 1 | `435,024` | `512` | `0` |
| `781` | [menu-781-page040r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-781-page040r4.png) | Page 40 (`0x02ea45a0`, 4r) | **2** | 2 | 0 | `435,024` | `395` | `0` |
| `782` | [menu-782-page008r4.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-782-page008r4.png) | Page 8 (`0x02e95ba0`, 4r) | **0** | 0 | 2 | `676` | `460` | `0` |
| `783` | [menu-783-page127r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-783-page127r3.png) | Page 127 (`0x02eba430`, 3r) | **0** | 2 | 1 | `435,024` | `59` | `0` |
| `784` | [menu-784-page120r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-784-page120r3.png) | Page 120 (`0x02eb9918`, 3r) | **1** | 1 | 1 | `59,696` | `475` | `0` |
| `785` | [menu-785-page119r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-785-page119r3.png) | Page 119 (`0x02eb9470`, 3r) | **0** | 2 | 0 | `435,024` | `0` | `0` |
| `786` | [menu-786-page113r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-786-page113r3.png) | Page 113 (`0x02eb8a50`, 3r) | **1** | 2 | 0 | `435,024` | `94` | `0` |
| `787` | [menu-787-page101r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-787-page101r3.png) | Page 101 (`0x02eb59a8`, 3r) | **0** | 2 | 1 | `435,024` | `141` | `0` |
| `788` | [menu-788-page097r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-788-page097r3.png) | Page 97 (`0x02eb52c8`, 3r) | **0** | 2 | 1 | `435,024` | `59` | `0` |
| `789` | [menu-789-page090r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-789-page090r3.png) | Page 90 (`0x02eb43e0`, 3r) | **0** | 2 | 1 | `435,024` | `141` | `0` |
| `790` | [menu-790-page076r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-790-page076r3.png) | Page 76 (`0x02eb1458`, 3r) | **1** | 2 | 0 | `435,024` | `107` | `0` |
| `791` | [menu-791-page065r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-791-page065r3.png) | Page 65 (`0x02eacc58`, 3r) | **0** | 2 | 1 | `435,024` | `141` | `0` |
| `792` | [menu-792-page053r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-792-page053r3.png) | Page 53 (`0x02eaa078`, 3r) | **0** | 2 | 1 | `435,024` | `141` | `0` |
| `793` | [menu-793-page033r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-793-page033r3.png) | Page 33 (`0x02ea3b80`, 3r) | **1** | 2 | 0 | `435,024` | `94` | `0` |
| `794` | [menu-794-page024r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-794-page024r3.png) | Page 24 (`0x02ea0220`, 3r) | **0** | 2 | 0 | `435,024` | `0` | `0` |
| `795` | [menu-795-page014r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-795-page014r3.png) | Page 14 (`0x02e9c4d0`, 3r) | **0** | 1 | 1 | `99,852` | `0` | `0` |
| `796` | [menu-796-page114r3.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-796-page114r3.png) | Page 114 (`0x02eb8d00`, 3r) | **1** | 1 | 1 | `26,772` | `475` | `0` |
| `797` | [menu-797-page122r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-797-page122r2.png) | Page 122 (`0x02eb9b10`, 2r) | **0** | 2 | 0 | `435,024` | `0` | `0` |
| `798` | [menu-798-page117r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-798-page117r2.png) | Page 117 (`0x02eb9278`, 2r) | **0** | 2 | 0 | `435,024` | `0` | `0` |
| `799` | [menu-799-page098r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-799-page098r2.png) | Page 98 (`0x02eb5768`, 2r) | **0** | 2 | 0 | `435,024` | `0` | `0` |
| `800` | [menu-800-page071r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-800-page071r2.png) | Page 71 (`0x02eaf718`, 2r) | **0** | 2 | 0 | `435,024` | `0` | `0` |
| `801` | [menu-801-page042r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-801-page042r2.png) | Page 42 (`0x02ea54d0`, 2r) | **0** | 2 | 0 | `435,024` | `0` | `0` |
| `802` | [menu-802-page039r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-802-page039r2.png) | Page 39 (`0x02ea4510`, 2r) | **1** | 1 | 1 | `12,744` | `343` | `0` |
| `803` | [menu-803-page032r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-803-page032r2.png) | Page 32 (`0x02ea3af0`, 2r) | **0** | 1 | 1 | `99,852` | `0` | `0` |
| `804` | [menu-804-page022r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-804-page022r2.png) | Page 22 (`0x02e9fde8`, 2r) | **0** | 1 | 0 | `552,960` | `0` | `0` |
| `805` | [menu-805-page021r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-805-page021r2.png) | Page 21 (`0x02e9de20`, 2r) | **1** | 1 | 0 | `435,024` | `512` | `0` |
| `806` | [menu-806-page006r2.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-806-page006r2.png) | Page 6 (`0x02e95918`, 2r) | **1** | 0 | 1 | `15,355` | `134` | `0` |
| `807` | [menu-807-page111r1.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-807-page111r1.png) | Page 111 (`0x02eb8640`, 1r) | **0** | 1 | 0 | `552,960` | `0` | `0` |
| `808` | [menu-808-page100r1.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-808-page100r1.png) | Page 100 (`0x02eb5960`, 1r) | **0** | 1 | 0 | `435,024` | `0` | `0` |
| `809` | [menu-809-page084r1.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-809-page084r1.png) | Page 84 (`0x02eb3468`, 1r) | **0** | 1 | 0 | `552,960` | `0` | `0` |
| `810` | [menu-810-page059r1.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-810-page059r1.png) | Page 59 (`0x02eabbb8`, 1r) | **0** | 1 | 0 | `552,960` | `0` | `0` |
| `811` | [menu-811-page031r1.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-811-page031r1.png) | Page 31 (`0x02ea3aa8`, 1r) | **0** | 1 | 0 | `552,960` | `0` | `0` |
| `812` | [menu-812-page30r1.png](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/menu-812-page30r1.png) | Page 30 (`0x02ea3a60`, 1r) | **0** | 1 | 0 | `552,960` | `0` | `0` |

---

## 3. Complete 128-Page (`fx6_all_pages[0..127]`) Verification Matrix

- **Total Descriptor Tables in `appFw.so`**: `128` (`fx6_all_pages[0..127]`)
- **Total Descriptor Rows (`0x48` bytes each)**: `2,249`
- **Pages Verified on Live `gpe0` (`0x41e001000`) with `nz > 0` and `segv = 0`**: **`128 / 128` (`100%`)**
- **Evidence Reports**:
  - [EVIDENCE-700.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-700.md) (`menu-700-live-big6.png` .. `menu-714-subpage26.png`)
  - [EVIDENCE-715-722.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-715-722.md) (`menu-715-paintoverlay102.png` .. `menu-722-hudtrack20.png`)
  - [EVIDENCE-723-734.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-723-734.md) (`menu-723-hudmain253.png` .. `menu-734-mediagrid57.png`)
  - [EVIDENCE-735-750.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-735-750.md) (`menu-735-menugrid69.png` .. `menu-750-blockdlg19.png`)
  - [EVIDENCE-751-812-FULL-128-PAGES.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-751-812-FULL-128-PAGES.md) (`menu-751-page126r7.png` .. `menu-812-page30r1.png`)
