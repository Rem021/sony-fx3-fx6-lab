# Display-Ready & UPM/MSS Contract (Static Evidence v3 — Errata & Byte-Level Verification)

## 0. Historical Receipts & Artifact Inventory

All v1, v2, and v3 receipts are preserved in `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/`:

| Version | Files | SHA-256 Receipts |
| :--- | :--- | :--- |
| **v1 (Preserved)** | `README-v1.md`, `verify_display_contract.py`, `display-contract-evidence.json`, `display-contract-fixture.json` | `display-contract-evidence.json`: `eb3bb3cc22db431e21445bf52e5c57da6ec70d3948d59a473eb082141748b2ef`<br>`display-contract-fixture.json`: `7ba11552495412894b81b9e638651071f8fa8753411220266a9cf66d7946529a` |
| **v2 (Preserved)** | `README-v2.md`, `verify_display_contract_v2.py`, `display-contract-evidence-v2.json`, `display-contract-fixture-v2.json` | `display-contract-evidence-v2.json`: `790a240c16cca6f52a599f81597265c9b2c56e8220a9f4bd5a8a9d73d946b8ea`<br>`display-contract-fixture-v2.json`: `d521212cf7da0efa67a4b6564c17f4545df4e3d3c3ed2c942ff0d15e5bf023d0` |
| **v3 (Current)** | `README.md`, `verify_display_contract_v3.py`, `display-contract-evidence-v3.json`, `display-contract-fixture-v3.json` | `display-contract-evidence-v3.json`: `f3198f583b9fb0404704afd517970bb62bdbea9b2f0825161f0bb2d787182b59`<br>`display-contract-fixture-v3.json`: `34b211c3427684e280bcc08a21960c24942b7d2e6e2573532ed48e38e1f1d414` |

### Fixed-SHA Input Binaries Verified

| Component | Path | SHA-256 |
| :--- | :--- | :--- |
| `appFw.so` | `/Volumes/KAFU2T/AI/Projects/Mac/extracted/mnt/app/lib/appFw.so` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| `upm.ko` | `/Volumes/KAFU2T/AI/Projects/Mac/extracted/mnt/app/module/upm.ko` | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` |
| `probe-mss300s-userspace.py` | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/probe-mss300s-userspace.py` | `5833339e5191019037d6b385b130f012d144a04aa8350368fa97cb8cbcd9d9db` |
| `probe-mss-timer-300s.py` | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/probe-mss-timer-300s.py` | `3da7df6045eb0b1e240415c9c5cc99d17dc5066bd505363060a908aa278ffac5` |
| `boot_warm.py` | `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/boot_warm.py` | `fd4b2b1091d8edcc0debc67a576369959fa46a64053a97468c8d718f1e61da8f` |

---

## 1. v3 Errata & Byte-Level Corrections Over v2

### Erratum 1: Exact Count & Offsets of `upm.ko` Internal Sends to `QID = 0x80924220`

- **v2 Error**: `README-v2.md` §1.2 and §3.1 prose wrote *"7处内核态自发调用点"* while listing 8 offsets (`0f04/614c/69f4/6acc/7164/88c4/a2d0/aa44`), and `.text+0x0f04` in that list was the trailing `nop` (`1f 20 03 d5`) of `k_upm_init_mss` rather than its `bl osal_snd_sync_msg` instruction (`.text+0x0e38`). Furthermore, the v2 list omitted `.text+0x0130`, `.text+0x0fd8`, `.text+0x6ed4`, and `.text+0x700c`.
- **v3 Byte-Verified Fact**: Scanning all `bl osal_snd_sync_msg` (relocation target symbol index `73`, `osal_snd_sync_msg`) and `bl upm_c3p_msg_async` (`.text+0x0760`) call sites in `upm.ko` (`.text` file offset `0x68`, size `0xbd68`) shows:
  - **12 synchronous `osal_snd_sync_msg(0x80924220, msg, timeout)` call sites** across 10 functions in `upm.ko`.
  - **5 asynchronous `upm_c3p_msg_async(0x80924220, ...)` broadcast call sites** across 2 functions in `upm.ko`.

#### Complete Table of 12 Synchronous `osal_snd_sync_msg` Call Sites to `0x80924220` in `upm.ko`

| # | `.text` Offset | File Offset | Function | Instruction Bytes (`bl`) | QID Setup Instruction | Sent Command (`word0`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `0x0130` | `0x0198` | `upm_msg_forward_thread` (`0x0070`) | `00 00 00 94` | `0x00a4`: `00 44 a2 52` + `0x00b4`: `00 12 90 72` (`w0=0x80924220`) | Forwards msg from `0x80920865` to `0x80924220` |
| 2 | `0x0e38` | `0x0ea0` | `k_upm_init_mss` (`0x0d58`) | `00 00 00 94` | `0x0e28`: `00 44 22 52` + `0x0e30`: `00 12 90 72` (`w0=0x80924220`) | `0x00920118` (`id=0xfff`, `timeout=0xbbf81e00`, `req_status=1`) |
| 3 | `0x0fd8` | `0x1040` | `k_upm_exit_mss` (`0x0f30`) | `00 00 00 94` | `0x0fc8`: `00 44 22 52` + `0x0fd0`: `00 12 90 72` (`w0=0x80924220`) | `0x00920119` (`id=0xfff`, `mode=1`) |
| 4 | `0x614c` | `0x61b4` | `k_upm_init_off_factor` (`0x5fb8`) | `00 00 00 94` | `0x6138`: `00 44 22 52` + `0x6144`: `00 12 90 72` (`w0=0x80924220`) | `0x00920203` (`MSS_notify_factor`, `arg=1`) |
| 5 | `0x69f4` | `0x6a5c` | `k_upm_off_factor_handler_active` (`0x6698`, site 1) | `00 00 00 94` | `0x69e0`: `00 44 22 52` + `0x69ec`: `00 12 90 72` (`w0=0x80924220`) | `0x00920203` (`MSS_notify_factor`, `arg=1`) |
| 6 | `0x6acc` | `0x6b34` | `k_upm_off_factor_handler_active` (`0x6698`, site 2) | `00 00 00 94` | `0x6ab4`: `00 44 22 52` + `0x6ac4`: `00 12 90 72` (`w0=0x80924220`) | `0x00920203` (`MSS_notify_factor`, `arg=0`) |
| 7 | `0x6ed4` | `0x6f3c` | `k_upm_off_factor_handler_init` (`0x6d38`, site 1) | `00 00 00 94` | `0x6ec8`: `00 44 22 52` + `0x6ecc`: `00 12 90 72` (`w0=0x80924220`) | `0x00920202` (`MSS_del_stopper`, `id=0x110`) |
| 8 | `0x700c` | `0x7074` | `k_upm_off_factor_handler_init` (`0x6d38`, site 2) | `00 00 00 94` | `0x7000`: `00 44 22 52` + `0x7004`: `00 12 90 72` (`w0=0x80924220`) | `0x00920202` (`MSS_del_stopper`, `id=0x110`) |
| 9 | `0x7164` | `0x71cc` | `k_upm_off_factor_handler_acting_app` (`0x7040`) | `00 00 00 94` | `0x7158`: `00 44 22 52` + `0x715c`: `00 12 90 72` (`w0=0x80924220`) | `0x00920202` (`MSS_del_stopper`, `id=0x120`) |
| 10 | `0x88c4` | `0x892c` | `k_upm_off_factor_handler_res` (`0x85b0`) | `00 00 00 94` | `0x88b4`: `00 44 22 52` + `0x88bc`: `00 12 90 72` (`w0=0x80924220`) | `0x00920202` (`MSS_del_stopper`, `id=0x120`) |
| 11 | `0xa2d0` | `0xa338` | `power_status_factor_cb` (`0xa248`) | `00 00 00 94` | `0xa2c0`: `00 44 22 52` + `0xa2c8`: `00 12 90 72` (`w0=0x80924220`) | `0x00920204` (`MSS_req_status`) |
| 12 | `0xaa44` | `0xaab0` | `k_upm_init_power_status` (`0xa968`) | `00 00 00 94` | `0xaa30`: `00 44 22 52` + `0xaa3c`: `00 12 90 72` (`w0=0x80924220`) | `0x00920203` (`MSS_notify_factor`, `arg=1`) |

#### Complete Table of 5 Asynchronous `upm_c3p_msg_async(0x80924220, ...)` Call Sites in `upm.ko`

| # | `.text` Offset | File Offset | Function | Instruction Bytes (`bl 0x760`) | Sent Command (`w1`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `0x08a8` | `0x0910` | `k_mss_timer_cb` (`0x0828`) | `ae ff ff 97` | `0x00920205` (`MSS_timeout` internal notification) |
| 2 | `0x24b4` | `0x251c` | `k_upm_mss_main_tsk` (`0x2180`, in `0x00920203` branch `arg==2`) | `ab f8 ff 97` | `0x00920204` (`id=0xfff, status=0`) |
| 3 | `0x2510` | `0x2578` | `k_upm_mss_main_tsk` (`0x2180`, in `0x00920203` branch `arg==1`) | `94 f8 ff 97` | `0x00920204` (`id=0xfff, status=1`) |
| 4 | `0x2680` | `0x26e8` | `k_upm_mss_main_tsk` (`0x2180`, in `0x00920205` branch) | `38 f8 ff 97` | `0x00920203` (`arg1=2, arg2=0`) |
| 5 | `0x2720` | `0x2788` | `k_upm_mss_main_tsk` (`0x2180`, in `0x00920205` branch) | `10 f8 ff 97` | `0x00920203` (`arg1=1, arg2=0`) |

---

### Erratum 2: `appFw.so` `0x2eaf294..0x2eaf354` Instruction-by-Instruction Register Mapping & Entry vs Wire Distinction

- **v2 Error**: `README-v2.md` §1.2 and §3.2 wrote `stp w22, w24, [x8]; stp w21, w20, [x8, #8]` for `0x2eaf2fc..0x2eaf300` and misassigned `w21/w22/w23/w25/w26` in the prose summary.
- **v3 Byte-Verified Fact**: Below is the complete, instruction-by-instruction disassembly of `0x2eaf294..0x2eaf354` from fixed-SHA `appFw.so` (`SHA256=545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`):

| VMA | Raw Bytes (LE) | U32 Hex | AArch64 Instruction | Role / Register State |
| :--- | :--- | :--- | :--- | :--- |
| `0x2eaf294` | `fd 7b ba a9` | `0xa9ba7bfd` | `stp x29, x30, [sp, #-0x60]!` | Function entry (`upm_osal_snd_sync_msg_helper`) |
| `0x2eaf298` | `fd 03 00 91` | `0x910003fd` | `mov x29, sp` | Frame pointer setup |
| `0x2eaf29c` | `f3 53 01 a9` | `0xa90153f3` | `stp x19, x20, [sp, #0x10]` | Callee-saved regs |
| `0x2eaf2a0` | `f5 5b 02 a9` | `0xa9025bf5` | `stp x21, x22, [sp, #0x20]` | Callee-saved regs |
| `0x2eaf2a4` | `f7 63 03 a9` | `0xa90363f7` | `stp x23, x24, [sp, #0x30]` | Callee-saved regs |
| `0x2eaf2a8` | `f9 6b 04 a9` | `0xa9046bf9` | `stp x25, x26, [sp, #0x40]` | Callee-saved regs |
| `0x2eaf2ac` | `a0 e6 00 d0` | `0xd000e6a0` | `adrp x0, 0x4b85000` | GOT page for `__stack_chk_guard` |
| `0x2eaf2b0` | `14 7c 46 f9` | `0xf9467c14` | `ldr x20, [x0, #0xcf8]` | `x20 = &__stack_chk_guard` |
| `0x2eaf2b4` | `f9 03 01 2a` | `0x2a0103f9` | `mov w25, w1` | **`w25 = w1` (`word0` = `cmd_id`, stored later at `[x1+0x00]`)** |
| `0x2eaf2b8` | `a1 63 01 91` | `0x910163a1` | `add x1, x29, #0x58` | `x1 = &msg_ptr` (stack slot `[x29+0x58]`) |
| `0x2eaf2bc` | `f7 03 03 2a` | `0x2a0303f7` | `mov w23, w3` | **`w23 = w3` (`word2` = `arg1`, stored later at `[x1+0x08]`)** |
| `0x2eaf2c0` | `f8 03 02 2a` | `0x2a0203f8` | `mov w24, w2` | **`w24 = w2` (`word1` = `arg0`, stored later at `[x1+0x04]`)** |
| `0x2eaf2c4` | `80 02 40 f9` | `0xf9400280` | `ldr x0, [x20]` | Load stack canary |
| `0x2eaf2c8` | `a0 53 05 f9` | `0xf9002ba0` | `str x0, [x29, #0x50]` | Store stack canary at `[x29+0x50]` |
| `0x2eaf2cc` | `f5 03 00 2a` | `0x2a0003f5` | `mov w21, w0` | **`w21 = w0` (`dst_qid`, e.g. `0x80924220`)** |
| `0x2eaf2d0` | `fa 03 06 2a` | `0x2a0603fa` | `mov w26, w6` | **`w26 = w6` (`src_id`, passed to `osal_set_msg_src`)** |
| `0x2eaf2d4` | `f3 03 05 aa` | `0xaa0503f3` | `mov x19, x5` | **`x19 = x5` (`reply_out_ptr`, optional 16B output buffer)** |
| `0x2eaf2d8` | `f6 03 04 2a` | `0x2a0403f6` | `mov w22, w4` | **`w22 = w4` (`word3` = `arg2`, stored later at `[x1+0x0c]`)** |
| `0x2eaf2dc` | `69 91 9b 97` | `0x979b9169` | `bl 0x1593880 <osal_valloc_msg_wait@plt>` | Allocate 16B OSAL msg buffer into `*[x29+0x58]` |
| `0x2eaf2e0` | `1f 00 00 71` | `0x7100001f` | `cmp w0, #0x0` | Check `osal_valloc_msg_wait` return status |
| `0x2eaf2e4` | `60 03 00 54` | `0x54000360` | `b.eq 0x2eaf350` | Return `-1` on allocation failure |
| `0x2eaf2e8` | `a0 2f 40 f9` | `0xf9402fa0` | `ldr x0, [x29, #0x58]` | `x0 = msg_ptr` |
| `0x2eaf2ec` | `e1 03 1a 2a` | `0x2a1a03e1` | `mov w1, w26` | `w1 = w26` (`src_id`) |
| `0x2eaf2f0` | `fc 8f 9b 97` | `0x979b8ffc` | `bl 0x15932e0 <osal_set_msg_src@plt>` | Set OSAL header `src_id` (outside 16B payload body) |
| `0x2eaf2f4` | `a1 2f 40 f9` | `0xf9402fa1` | `ldr x1, [x29, #0x58]` | **`x1 = msg_ptr` (16B wire buffer base)** |
| `0x2eaf2f8` | `e0 03 15 2a` | `0x2a1503e0` | `mov w0, w21` | **`w0 = w21` (`dst_qid`)** |
| `0x2eaf2fc` | `39 60 00 29` | `0x29006039` | **`stp w25, w24, [x1]`** | **Write `[x1+0x00]=w25 (w1)`, `[x1+0x04]=w24 (w2)`** |
| `0x2eaf300` | `37 58 01 29` | `0x29015837` | **`stp w23, w22, [x1, #0x8]`** | **Write `[x1+0x08]=w23 (w3)`, `[x1+0x0c]=w22 (w4)`** |
| `0x2eaf304` | `b7 92 9b 97` | `0x979b92b7` | **`bl 0x1593de0 <osal_snd_sync_msg@plt>`** | **Synchronous send (`w0=dst_qid`, `x1=msg_ptr`)** |
| `0x2eaf308` | `1f 00 00 71` | `0x7100001f` | **`cmp w0, #0x0`** | **Post-send return check (`probe-mss300s-userspace.py` hooks here!)** |
| `0x2eaf30c` | `c1 01 00 54` | `0x540001c1` | `b.ne 0x2eaf344` | Branch if `osal_snd_sync_msg != 0` |
| `0x2eaf310` | `a0 2f 40 f9` | `0xf9402fa0` | `ldr x0, [x29, #0x58]` | Reload `x0 = msg_ptr` |
| `0x2eaf314` | `b3 01 00 b4` | `0xb40001b3` | `cbz x19, 0x2eaf348` | Skip reply copy if `reply_out_ptr == NULL` |
| `0x2eaf318` | `18 00 40 b9` | `0xb9400018` | `ldr w24, [x0]` | Read post-send `[msg_ptr+0x00]` |
| `0x2eaf31c` | `78 02 00 b9` | `0xb9000278` | `str w24, [x19]` | Copy to `[reply_out_ptr+0x00]` |
| `0x2eaf320` | `18 04 40 b9` | `0xb9400418` | `ldr w24, [x0, #0x4]` | Read post-send `[msg_ptr+0x04]` |
| `0x2eaf324` | `78 06 00 b9` | `0xb9000678` | `str w24, [x19, #0x4]` | Copy to `[reply_out_ptr+0x04]` |
| `0x2eaf328` | `18 08 40 b9` | `0xb9400818` | `ldr w24, [x0, #0x8]` | Read post-send `[msg_ptr+0x08]` |
| `0x2eaf32c` | `78 0a 00 b9` | `0xb9000a78` | `str w24, [x19, #0x8]` | Copy to `[reply_out_ptr+0x08]` |
| `0x2eaf330` | `18 0c 40 b9` | `0xb9400c18` | `ldr w24, [x0, #0xc]` | Read post-send `[msg_ptr+0x0c]` |
| `0x2eaf334` | `78 0e 00 b9` | `0xb9000e78` | `str w24, [x19, #0xc]` | Copy to `[reply_out_ptr+0x0c]` |
| `0x2eaf338` | `f4 03 1f 2a` | `0x2a1f03f4` | `mov w20, wzr` | Return value `0` |
| `0x2eaf33c` | `25 94 9b 97` | `0x979b9425` | `bl 0x15943d0 <osal_free_msg@plt>` | Free `msg_ptr` |

#### Explicit Distinction: Entry Reconstruction (`0x2eaf294`) vs Pre-Send Wire Buffer (`0x2eaf304`) vs Post-Send Buffer (`0x2eaf308`)

1. **Function Entry (`0x2eaf294`) — Register Reconstruction Only (No Wire Buffer Exists Yet)**:
   - At `0x2eaf294`, `osal_valloc_msg_wait` (`0x2eaf2dc`) has **not** executed yet.
   - A probe at `0x2eaf294` reconstructs the intended 16B payload from caller registers:
     - `w0` = `dst_qid` (`0x80924220`)
     - `w1` -> saved in `w25` -> written to `msg_ptr+0x00` (`word0` = `cmd_id`)
     - `w2` -> saved in `w24` -> written to `msg_ptr+0x04` (`word1` = `arg0`)
     - `w3` -> saved in `w23` -> written to `msg_ptr+0x08` (`word2` = `arg1`)
     - `w4` -> saved in `w22` -> written to `msg_ptr+0x0c` (`word3` = `arg2`)
     - `x5` -> saved in `x19` -> optional 16B caller reply buffer pointer (`reply_out_ptr`)
     - `w6` -> saved in `w26` -> passed to `osal_set_msg_src(msg_ptr, w26)` (OSAL header metadata, **not** part of the 16B payload)
2. **Pre-Send Call Site (`0x2eaf304`) — True Pre-Send Wire Buffer**:
   - Immediately before `bl osal_snd_sync_msg@plt` at `0x2eaf304`:
     - `w0` holds `dst_qid` (`w21`),
     - `x1` (`[x29+0x58]`) points to the allocated and populated 16-byte OSAL message payload `[w25, w24, w23, w22]` in memory, **before** the kernel receiver (`k_upm_mss_main_tsk`) touches it.
3. **Post-Send Instruction (`0x2eaf308`) — Post-Reply In-Place Buffer (Broken in `probe-mss300s-userspace.py`)**:
   - `probe-mss300s-userspace.py:86-152` placed its breakpoint at `0x2eaf308` (`cmp w0, #0x0`), which executes **after** `osal_snd_sync_msg` returns.
   - At `0x2eaf308`:
     1. Register `w0` is the return status (`0` on success), **not** `dst_qid` (`w21` still holds `dst_qid`).
     2. Register `x1` is clobbered by `osal_snd_sync_msg@plt` (`[x29+0x58]` holds `msg_ptr`, reloaded into `x0` at `0x2eaf310`).
     3. Because `osal_snd_sync_msg` is synchronous, `k_upm_mss_main_tsk` (`upm.ko` `.text+0x2180`) has already run and may have mutated `[msg_ptr+0x00..0x0f]` in-place (which `0x2eaf318..0x2eaf334` copies out to `x19` before `0x2eaf33c` frees `msg_ptr`).

---

### Erratum 3: Exact Preconditions & Timeout Semantics of `0x00920202` (`MSS_del_stopper`)

- **v2 Error**: `README-v2.md` §2.2 summarized `0x00920202` (`MSS_del_stopper`) as starting the 300s countdown once `stopper_list` becomes empty, without stating the required `mss_state.status` precondition or that the timer duration is determined by the minimum currently registered request (`min_req->timeout_sec`), not a hardcoded 300s constant in `del_stopper`.
- **v3 Byte-Verified Fact (`upm.ko` `.text+0x22d8..0x2490`, `.text+0x1558..0x15a4`, `.text+0x1008..0x1068`)**:
  1. **`mss_state` Structure Layout (`x20 = &mss_state`)**:
     - `[x20 + 0x30]`: `request_list` head pointer (registered MSS timeout requests; each node has `id` at `+0x10`, `timeout_sec` at `+0x14`, `req_status` at `+0x18`).
     - `[x20 + 0x38]`: `request_count` (`u32`).
     - `[x20 + 0x40]`: `stopper_list` head pointer (active MSS stoppers; each node has `stopper_id` at `+0x10`).
     - `[x20 + 0x48]`: `elapsed_sec` (`u32`, reset to `0` at `.text+0x2484` `str wzr, [x20, #0x48]`).
     - `[x20 + 0x4c]`: `status` (`u32`: `1 = STOPPED`, `2 = RUNNING`, `3 = EXPIRED/OFF_FACTOR`).
  2. **Preconditions for `0x00920202` (`MSS_del_stopper`) to Start the Timer**:
     - At `.text+0x22d8`: loads `w0 = [x20, #0x4c]` (`mss_state.status`), subtracts `1` (`0x22e8: sub w0, w0, #0x1`), and checks `cbz w0, 0x22fc` (`0x22f0`).
       - **Precondition A**: `mss_state.status` **must** equal `1` (`STOPPED`). If `status` is `2` or `3` (`0x22ec..0x22f8`), it logs `"status Error(%d)"` and aborts without removing the stopper or starting any timer.
     - At `.text+0x22fc..0x230c`: removes the matching `stopper_id` from `stopper_list` (`[x20+0x40]`).
     - At `.text+0x2310..0x2314`: loads `x0 = [x20, #0x40]` (`ldr x0, [x20, #0x40]`) and executes `cbz x0, 0x2468`.
       - **Precondition B**: `stopper_list` (`[x20+0x40]`) **must** become `NULL` (all stoppers removed). If any stopper remains on `[x20+0x40]`, `cbz` does not branch and the timer is **not** started.
  3. **What Duration `0x00920202` Starts When Both Preconditions Hold (`.text+0x2468..0x2490`)**:
     - At `.text+0x2468..0x247c`: iterates all nodes in `request_list` (`[x20+0x30]`), setting each node's `req_status` (`[node+0x18]`) to `1`.
     - At `.text+0x2480`: calls `k_mss_find_min_request` (`.text+0x1558`), which scans `request_list` (`[x20+0x30]`) for the node with `req_status == 1` that has the **minimum `timeout_sec` (`[node+0x14]`)**.
     - At `.text+0x2484..0x248c`: sets `mss_state.elapsed_sec = 0` (`str wzr, [x20, #0x48]`) and `mss_state.status = 2` (`RUNNING`, `mov w1, #2; str w1, [x20, #0x4c]`).
     - At `.text+0x2490`: calls `k_mss_start_timer_nr(min_req)` (`.text+0x1008`), which computes `delta_sec = min_req->timeout_sec - mss_state.elapsed_sec` (`0x1018..0x1028`, where `elapsed_sec == 0` here, so `delta_sec = min_req->timeout_sec`) and arms the OSAL timer (`osal_StartTimer`) for `delta_sec * 1000` ms (`0x1040..0x104c`).
     - **Why 300s is Observed in Practice (Conditioned on Request List State)**:
       - At module init, `k_upm_init_mss` (`.text+0x0d58..0x0e38`) registers default request `id=0xfff` with `timeout_sec = 0xbbf81e00` (`3,153,600,000` sec).
       - A 300s (`0x12c`) timer is started by `MSS_del_stopper` **if and only if** a 300s request (e.g. `id=0x200, timeout_sec=300` from `upm_mss_add_request` `0x00920118` or `upm_mss_chg_time` `0x0092011a`) has already been registered into `request_list` (`[x20+0x30]`) and is currently the minimum request when the last stopper is deleted.
       - Note on remaining vs full period: `MSS_del_stopper` (`.text+0x2484`) resets `elapsed_sec = 0`, so it starts the **full** period of `min_req->timeout_sec`; by contrast, `k_mss_start_timer_nr` (`.text+0x1008`) when called from `k_mss_timer_cb` (`.text+0x0890`) while `elapsed_sec > 0` schedules the **remaining** period `min_req->timeout_sec - elapsed_sec`.

---

### Erratum 4: Narrowing Downstream Scope of `App::got_display_update_event` (`0x16f11e8`)

- **v2 Overstatement**: Parts of `README-v2.md` stated without qualification that `App::got_display_update_event` (`0x16f11e8`) has "zero coupling" to UPM/MSS (`0x80924220`).
- **v3 Narrowed Static Scope**:
  - **What is statically proven**:
    1. Neither `App::got_display_update_event(Ev_item const&)` (`0x16f11e8..0x16f14a0`) nor its helper classifier (`0x16f3750..0x16f3894`) calls `0x2eaf294` (`upm_osal_snd_sync_msg_helper`), `osal_snd_sync_msg`, or any `upm_mss_*` wrapper (`0x2eafb30..0x2eb0108`).
    2. Its direct callee `fw::ConcreteEvent::get_parameter` (`0x17d8a3c`) only reads `[x0+0x10]`, and its conditional direct callees `App::request_ChangeTo Standby/Sleep` (`0x16ee034..0x16ee280`) only enqueue internal framework events (`0x001a0004` / `0x001a0005`).
  - **What is NOT statically ruled out (Boundary Condition)**:
    - After `0x16f11e8` returns (or after `0x16ee034`/`0x16ee160` enqueues `0x001a0004`/`0x001a0005` into the framework event loop), **downstream UI presenters, screen controllers, or standby/sleep sequence handlers** that subsequently process the display update or power-state transition in later event-loop turns **can** invoke `upm_mss_*` wrappers (`0x2eafb30..0x2eb0108`) or power-state APIs.
    - Therefore, `0x16f11e8` is strictly a **user-space UI/display event-consumption checkpoint** that does **not directly** send to `0x80924220` within `0x16f11e8` / `0x16f3750`, rather than a proof that the entire downstream UI/power pipeline never touches MSS.

---

## 2. Summary of Verified Core Findings (Retained from v2 + Refined in v3)

1. **Three-Channel UPM/MSS Architecture**:
   - **Channel A (User-Space `appFw.so` -> `0x80924220`)**: 15 `upm_mss_*` / `upm_power_*` wrappers (`0x2eafb30..0x2eb0108`) call `0x2eaf294`, which populates `[w25, w24, w23, w22]` (`[w1, w2, w3, w4]`) into `[x1+0x00..0x0c]` at `0x2eaf2fc..0x2eaf300` and invokes `osal_snd_sync_msg(w0=dst_qid, x1=msg_ptr, x2=timeout)` at `0x2eaf304`.
   - **Channel B (Kernel-Internal `upm.ko` -> `0x80924220`)**: 12 synchronous `osal_snd_sync_msg` sites (`0x0130, 0x0e38, 0x0fd8, 0x614c, 0x69f4, 0x6acc, 0x6ed4, 0x700c, 0x7164, 0x88c4, 0xa2d0, 0xaa44`) and 5 asynchronous `upm_c3p_msg_async` sites (`0x08a8, 0x24b4, 0x2510, 0x2680, 0x2720`) inside `upm.ko` bypass user space completely.
   - **Channel C (Kernel Dispatcher `upm.ko` `.text+0x2180`)**: Single point of truth receiving every message on `0x80924220` via `osal_rcv_sync_msg` at `.text+0x21ec` (`x0` = 16B message buffer).
2. **Double Blind Spot in `probe-mss300s-userspace.py`**:
   - Hooks `0x2eaf308` (post-send `cmp w0, #0x0` instead of pre-send `0x2eaf304` or entry `0x2eaf294`), and filters on `w1 in (0x00920118, 0x0092011a, 0x00920201, 0x00920202)` where `w1` is clobbered and `0x00920203` (`MSS_notify_factor`) is excluded.
   - Completely misses all 12 sync + 5 async kernel-internal sends inside `upm.ko`.
3. **Reproducible Verification**:
   - Run `python3 verify_display_contract_v3.py` to verify all binary SHA-256 digests, all 12 sync + 5 async `upm.ko` internal sites, the exact `0x2eaf294..0x2eaf354` instruction words, the `MSS_del_stopper` preconditions, and the `0x16f11e8` call graph without starting QEMU.
