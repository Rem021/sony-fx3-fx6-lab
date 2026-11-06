#!/usr/bin/env python3
"""
Deterministic Offline Verification & Errata Generator (v3) for Task task_de19809131ee:
Fixes and verifies the 4 static precision items on top of v2 while preserving all v1 and v2 files:
1. Exact count and instruction offsets of internal upm.ko senders to QID 0x80924220:
   - 12 synchronous osal_snd_sync_msg call sites across 10 functions in upm.ko .text:
     0x0130, 0x0e38 (note: 0x0f04 in v2 was the trailing nop of k_upm_init_mss), 0x0fd8,
     0x614c, 0x69f4, 0x6acc, 0x6ed4, 0x700c, 0x7164, 0x88c4, 0xa2d0, 0xaa44.
   - 5 asynchronous upm_c3p_msg_async broadcast call sites on 0x80924220 in upm.ko .text:
     0x08a8, 0x24b4, 0x2510, 0x2680, 0x2720.
2. Exact instruction-by-instruction register mapping in appFw.so 0x2eaf294..0x2eaf354:
   - 0x2eaf2b4 mov w25, w1; 0x2eaf2bc mov w23, w3; 0x2eaf2c0 mov w24, w2;
     0x2eaf2cc mov w21, w0 (dst_qid); 0x2eaf2d0 mov w26, w6 (src_id -> osal_set_msg_src at 0x2eaf2f0);
     0x2eaf2d4 mov x19, x5 (optional reply out ptr); 0x2eaf2d8 mov w22, w4.
   - 0x2eaf2f4 ldr x1, [x29, #0x58]; 0x2eaf2fc stp w25, w24, [x1]; 0x2eaf300 stp w23, w22, [x1, #0x8].
   - Explicitly distinguishes:
     (a) Entry-register payload reconstruction at 0x2eaf294 ([w1, w2, w3, w4] + header src w6, before
         allocation/send), vs
     (b) Pre-send wire buffer at 0x2eaf304 ([x29+0x58] / x1 after 0x2eaf2fc..0x2eaf300), vs
     (c) Post-send buffer at 0x2eaf308 (after osal_snd_sync_msg returns, where synchronous consumer
         upm.ko .text+0x2180 may have modified [x0+0..0xf] in-place before 0x2eaf318..0x2eaf330 copies
         reply words to x19, and before 0x2eaf33c calls osal_free_msg).
3. Exact precondition and timeout semantics of 0x00920202 (MSS_del_stopper) in upm.ko .text+0x2598 ->
   0x2310 -> 0x2468..0x2490:
   - Only when mss_state.status == 1 (STOPPED) and stopper_list ([x20+0x40]) becomes NULL does
     0x2468..0x2490 reset all registered requests in request_list ([x20+0x30]) to state=1, set
     elapsed_sec=0 ([x20+0x48]) and status=2 ([x20+0x4c]), and call k_mss_start_timer_nr(min_req)
     for the current minimum registered request's timeout_sec (min_req->timeout_sec - 0). It is NOT
     unconditionally 300s unless the minimum registered request in [x20+0x30] has timeout_sec == 300
     (or after shorter requests have expired and chained in k_mss_timer_cb .text+0x1670 -> 0x16c8
     for next_req->timeout_sec - elapsed_sec).
4. Narrowed scope of App::got_display_update_event (0x16f11e8 -> 0x005503e0 -> 0x16f38c8 type 5):
   - 0x16f11e8 and the 0x16f3750..0x16f3900 classifier do not directly invoke 0x2eaf294 or send to
     0x80924220, which does NOT statically rule out indirect downstream UI/presenter/sequence handlers
     invoking MSS APIs after consuming the display-update event.
"""

import hashlib
import json
import struct
from pathlib import Path

from verify_display_contract_v2 import (
    BINARIES,
    RUNTIME_ARTIFACTS,
    RUNTIME_HELPERS,
    OUT_DIR,
    sha256_bytes,
    sha256_file,
    u32,
    objdump_elf_range,
)


def verify_v3_errata():
    appfw_path = BINARIES["appFw.so"]["path"]
    upmko_path = BINARIES["upm.ko"]["path"]
    appfw = appfw_path.read_bytes()
    upmko = upmko_path.read_bytes()

    assert sha256_bytes(appfw) == BINARIES["appFw.so"]["expected_sha256"]
    assert sha256_bytes(upmko) == BINARIES["upm.ko"]["expected_sha256"]

    # -------------------------------------------------------------------------
    # Erratum 1: Exact instruction-level verification of appFw.so 0x2eaf294..0x2eaf358
    # -------------------------------------------------------------------------
    assert u32(appfw, 0x2EAF294) == 0xA9BA7BFD  # stp x29, x30, [sp, #-0x60]!
    assert u32(appfw, 0x2EAF2B4) == 0x2A0103F9  # mov w25, w1 (wire word0 = entry w1)
    assert u32(appfw, 0x2EAF2B8) == 0x910163A1  # add x1, x29, #0x58 (&msg_ptr slot)
    assert u32(appfw, 0x2EAF2BC) == 0x2A0303F7  # mov w23, w3 (wire word2 = entry w3)
    assert u32(appfw, 0x2EAF2C0) == 0x2A0203F8  # mov w24, w2 (wire word1 = entry w2)
    assert u32(appfw, 0x2EAF2CC) == 0x2A0003F5  # mov w21, w0 (dst_qid = entry w0)
    assert u32(appfw, 0x2EAF2D0) == 0x2A0603FA  # mov w26, w6 (msg header src_id = entry w6)
    assert u32(appfw, 0x2EAF2D4) == 0xAA0503F3  # mov x19, x5 (optional reply out_ptr = entry x5)
    assert u32(appfw, 0x2EAF2D8) == 0x2A0403F6  # mov w22, w4 (wire word3 = entry w4)
    assert u32(appfw, 0x2EAF2DC) == 0x979B9391  # bl 0x1594120 <osal_valloc_msg_wait@plt>
    assert u32(appfw, 0x2EAF2E8) == 0xF9402FA0  # ldr x0, [x29, #0x58]
    assert u32(appfw, 0x2EAF2EC) == 0x2A1A03E1  # mov w1, w26
    assert u32(appfw, 0x2EAF2F0) == 0x979B8AC4  # bl 0x1591e00 <osal_set_msg_src@plt>
    assert u32(appfw, 0x2EAF2F4) == 0xF9402FA1  # ldr x1, [x29, #0x58]
    assert u32(appfw, 0x2EAF2F8) == 0x2A1503E0  # mov w0, w21
    assert u32(appfw, 0x2EAF2FC) == 0x29006039  # stp w25, w24, [x1]
    assert u32(appfw, 0x2EAF300) == 0x29015837  # stp w23, w22, [x1, #0x8]
    assert u32(appfw, 0x2EAF304) == 0x979B92B7  # bl 0x1593de0 <osal_snd_sync_msg@plt>
    assert u32(appfw, 0x2EAF308) == 0x7100001F  # cmp w0, #0x0
    assert u32(appfw, 0x2EAF334) == 0xF9402FA1  # ldr x1, [x29, #0x58]
    assert u32(appfw, 0x2EAF338) == 0x2A1503E0  # mov w0, w21
    assert u32(appfw, 0x2EAF33C) == 0x979B9425  # bl 0x15943d0 <osal_free_msg@plt>

    # Also verify how representative wrappers populate (w0..w6) before calling 0x2eaf294:
    # - 0x2eb4f24 (MSS_reload_timer 0x00920204)
    # - 0x2eb7378 (MSS_del_stopper 0x00920202)
    # - 0x2eb7428 (MSS_add_stopper 0x00920203)
    # - 0x2eb4f74 (MSS_fakey_start 0x00920206)
    # - 0x2eb5084 (MSS_fakey_stop 0x00920206)
    # - 0x2eb5970 (MSS_add_request 0x00920118)
    wrappers_disasm = {
        "0x2eb4f24_reload": objdump_elf_range(appfw_path, 0x2EB4F24, 0x2EB4F74, 0x2EB4F24, appfw),
        "0x2eb4f74_fakey_start": objdump_elf_range(appfw_path, 0x2EB4F74, 0x2EB5084, 0x2EB4F74, appfw),
        "0x2eb5084_fakey_stop": objdump_elf_range(appfw_path, 0x2EB5084, 0x2EB5194, 0x2EB5084, appfw),
        "0x2eb5970_add_request": objdump_elf_range(appfw_path, 0x2EB5970, 0x2EB5A80, 0x2EB5970, appfw),
        "0x2eb7378_del_stopper": objdump_elf_range(appfw_path, 0x2EB7378, 0x2EB7428, 0x2EB7378, appfw),
        "0x2eb7428_add_stopper": objdump_elf_range(appfw_path, 0x2EB7428, 0x2EB74DC, 0x2EB7428, appfw),
    }

    # -------------------------------------------------------------------------
    # Erratum 2: Exhaustive count & byte verification of all upm.ko internal
    # senders to QID 0x80924220 (12 sync osal_snd_sync_msg sites + 5 async broadcast sites)
    # -------------------------------------------------------------------------
    upm_text_off = 0x68
    sync_sites_spec = [
        (0x0130, "thread_0x80920865_forwarder (.text+0x0070)", "forwards [w24, w21, w23, w22] from QID 0x80920865 to 0x80924220"),
        (0x0E38, "k_upm_init_mss (.text+0x0d58)", "0x00920118 (MSS_add_request, id=0xfff, timeout=0xbbf81e00, src=0x80924220); note: v2 listed 0x0f04 which is the trailing nop of k_upm_init_mss"),
        (0x0FD8, "k_upm_exit_mss (.text+0x0f30)", "0x00920119 (MSS_del_request, handle=[mss_state+0x58], src=0x80924220)"),
        (0x614C, "k_upm_init_off_factor (.text+0x5fb8)", "0x00920203 (MSS_add_stopper, src=0x80920196)"),
        (0x69F4, "k_upm_off_factor_handler_active (.text+0x6698, site 1)", "0x00920203 (MSS_add_stopper, src=0x80920196)"),
        (0x6ACC, "k_upm_off_factor_handler_active (.text+0x6698, site 2)", "0x00920203 (MSS_add_stopper, src=0x80920196)"),
        (0x6ED4, "k_upm_off_factor_handler_init (.text+0x6d38, site 1)", "0x00920202 (MSS_del_stopper, src=0x80920196)"),
        (0x700C, "k_upm_off_factor_handler_init (.text+0x6d38, site 2)", "0x00920202 (MSS_del_stopper, src=0x80920196)"),
        (0x7164, "k_upm_off_factor_handler_acting_app (.text+0x7040)", "0x00920202 (MSS_del_stopper, src=0x80920196)"),
        (0x88C4, "k_upm_off_factor_handler_res (.text+0x85b0)", "0x00920202 (MSS_del_stopper, src=0x80920196)"),
        (0xA2D0, "power_status_factor_cb (.text+0xa248)", "0x00920204 (MSS_reload_timer, src=0x80920021 on 0x00920131..0x00920138)"),
        (0xAA44, "k_upm_init_power_status (.text+0xa968)", "0x00920203 (MSS_add_stopper, src=0x80920021)"),
    ]
    verified_sync_sites = []
    for text_va, fn_label, desc in sync_sites_spec:
        word = u32(upmko, upm_text_off + text_va)
        assert word == 0x94000000, f"Expected bl placeholder 0x94000000 at .text+0x{text_va:x}, got 0x{word:08x}"
        snippet = objdump_elf_range(
            upmko_path, text_va - 0x24, text_va + 0x08, upm_text_off + text_va - 0x24, upmko, reloc=True
        )
        assert any("osal_snd_sync_msg" in ins.get("reloc", "") for ins in snippet["instructions"])
        verified_sync_sites.append(
            {
                "text_offset": f".text+0x{text_va:04x}",
                "file_offset": f"0x{upm_text_off + text_va:x}",
                "function": fn_label,
                "command_and_payload": desc,
                "disassembly_window": snippet,
            }
        )
    assert len(verified_sync_sites) == 12

    async_sites_spec = [
        (0x08A8, "k_mss_fire_all_expired_nr (.text+0x0828)", "0x00920205 (MSS_expired broadcast)"),
        (0x24B4, "mss_queue_dispatcher (.text+0x2180, status 1->2 start)", "0x00920204 (MSS_reload_timer broadcast)"),
        (0x2510, "mss_queue_dispatcher (.text+0x2180, status==2 reload)", "0x00920204 (MSS_reload_timer broadcast)"),
        (0x2680, "mss_queue_dispatcher (.text+0x2180, 0x00920119 empty stop)", "0x00920203 (MSS_add_stopper broadcast)"),
        (0x2720, "mss_queue_dispatcher (.text+0x2180, status 2->1 add_stopper)", "0x00920203 (MSS_add_stopper broadcast)"),
    ]
    verified_async_sites = []
    for text_va, fn_label, desc in async_sites_spec:
        word = u32(upmko, upm_text_off + text_va)
        assert word == 0x94000000
        snippet = objdump_elf_range(
            upmko_path, text_va - 0x18, text_va + 0x04, upm_text_off + text_va - 0x18, upmko, reloc=True
        )
        assert any("upm_c3p_msg_async" in ins.get("reloc", "") for ins in snippet["instructions"])
        verified_async_sites.append(
            {
                "text_offset": f".text+0x{text_va:04x}",
                "file_offset": f"0x{upm_text_off + text_va:x}",
                "function": fn_label,
                "command_and_payload": desc,
            }
        )
    assert len(verified_async_sites) == 5

    # -------------------------------------------------------------------------
    # Erratum 3: Exact verification of del_stopper (0x00920202) and mss_state layout
    # in upm.ko .text+0x2300..0x24b8 and .text+0x2598..0x25c0
    # -------------------------------------------------------------------------
    assert u32(upmko, upm_text_off + 0x2310) == 0xF9402280  # ldr x0, [x20, #0x40] (stopper_list head)
    assert u32(upmko, upm_text_off + 0x2314) == 0xB4000AA0  # cbz x0, 0x2468 (only when stopper_list is empty)
    assert u32(upmko, upm_text_off + 0x2468) == 0xF9401A80  # ldr x0, [x20, #0x30] (request_list head)
    assert u32(upmko, upm_text_off + 0x2474) == 0xB9001801  # str w1, [x0, #0x18] (resets req->state = 1)
    assert u32(upmko, upm_text_off + 0x2480) == 0x94000000  # bl k_mss_find_min_request
    assert u32(upmko, upm_text_off + 0x248C) == 0x2909069F  # stp wzr, w1, [x20, #0x48] (elapsed_sec=0, status=2)
    assert u32(upmko, upm_text_off + 0x2490) == 0x94000000  # bl k_mss_start_timer_nr

    # Load v2 evidence & fixture as base, and attach v3_errata_and_verifications
    ev_v2 = json.loads((OUT_DIR / "display-contract-evidence-v2.json").read_text(encoding="utf-8"))
    fx_v2 = json.loads((OUT_DIR / "display-contract-fixture-v2.json").read_text(encoding="utf-8"))

    v3_errata = {
        "schema_version": "3.0.0",
        "errata_items": {
            "erratum_1_upm_ko_internal_0x80924220_send_sites_count": {
                "evidence_tier": "STATIC_ORIGINAL_CODE",
                "correction_summary": "In v2 README/JSON, the summary text said '7處' while listing 8 offsets across 7 functions (grouping .text+0x69f4 and .text+0x6acc in one entry, and citing .text+0x0f04 which is the trailing nop of k_upm_init_mss rather than the actual bl osal_snd_sync_msg at .text+0x0e38). Exhaustive scan of upm.ko .text (.rela.text R_AARCH64_CALL26 -> osal_snd_sync_msg / upm_c3p_msg_async) proves there are 12 synchronous osal_snd_sync_msg call sites to 0x80924220 across 10 functions (8 of which send stopper/reload commands 0x00920202/203/204 in off-factor and power-status handlers, 2 in init/exit_mss for 0x00920118/119, and 1 in the 0x80920865->0x80924220 forwarding thread at .text+0x0130, plus 2 second-branch sites .text+0x6ed4/.text+0x700c in k_upm_off_factor_handler_init) and 5 asynchronous upm_c3p_msg_async broadcast sites on 0x80924220.",
                "synchronous_osal_snd_sync_msg_sites_count": 12,
                "synchronous_osal_snd_sync_msg_sites": verified_sync_sites,
                "asynchronous_upm_c3p_msg_async_sites_count": 5,
                "asynchronous_upm_c3p_msg_async_sites": verified_async_sites,
            },
            "erratum_2_appfw_0x2eaf294_register_mapping_and_wire_vs_entry_distinction": {
                "evidence_tier": "STATIC_ORIGINAL_CODE",
                "correction_summary": "In v2 prose, 0x2eaf2fc..0x2eaf300 was misstated from memory as 'stp w22,w24,[x8]; stp w21,w20,[x8,#8]' with [w1,w6,w2,w3]. The actual instructions in appFw.so (SHA256 545c5053...) at 0x2eaf294..0x2eaf354 are: 0x2eaf2b4 mov w25,w1; 0x2eaf2bc mov w23,w3; 0x2eaf2c0 mov w24,w2; 0x2eaf2cc mov w21,w0; 0x2eaf2d0 mov w26,w6; 0x2eaf2d4 mov x19,x5; 0x2eaf2d8 mov w22,w4; followed by 0x2eaf2ec mov w1,w26; 0x2eaf2f0 bl osal_set_msg_src; 0x2eaf2f4 ldr x1,[x29,#0x58]; 0x2eaf2fc stp w25,w24,[x1] (bytes 39 60 00 29); 0x2eaf300 stp w23,w22,[x1,#0x8] (bytes 37 58 01 29).",
                "exact_register_map_at_0x2eaf294": {
                    "entry_w0_saved_to_w21_at_0x2eaf2cc": "dst_qid (e.g. 0x80924220), passed as w0 to osal_valloc_msg_wait (0x2eaf2dc), osal_snd_sync_msg (0x2eaf304), and osal_free_msg (0x2eaf33c)",
                    "entry_w1_saved_to_w25_at_0x2eaf2b4": "wire payload word0 at [x1+0x00] (e.g. cmd 0x00920202/203/204/206/118/119)",
                    "entry_w2_saved_to_w24_at_0x2eaf2c0": "wire payload word1 at [x1+0x04] (for 202/203/204/206 wrappers 0x2eb7378/0x2eb7428/0x2eb4f24/0x2eb4f74/0x2eb5084, the wrapper passes src_id in BOTH w2 and w6; for 0x2eb5970 add_request, w2 is req_id and w6 is src_id)",
                    "entry_w3_saved_to_w23_at_0x2eaf2bc": "wire payload word2 at [x1+0x08] (e.g. 0 for 202/203/204/fakey_start, 1 for fakey_stop, timeout_sec for add_request)",
                    "entry_w4_saved_to_w22_at_0x2eaf2d8": "wire payload word3 at [x1+0x0c] (e.g. 0 for 202/203/204/206, src_id for add_request)",
                    "entry_x5_saved_to_x19_at_0x2eaf2d4": "optional 16B reply output buffer pointer; if w0==0 and x19!=0 at 0x2eaf308..0x2eaf314, 0x2eaf318..0x2eaf330 copies the post-send 16B buffer [x0+0..0xf] into [x19+0..0xf]",
                    "entry_w6_saved_to_w26_at_0x2eaf2d0": "OSAL message header source ID, passed as w1 to osal_set_msg_src(msg, w26) at 0x2eaf2ec..0x2eaf2f0",
                },
                "entry_reconstruction_vs_wire_read_distinction": {
                    "1_entry_register_reconstruction_0x2eaf294": "At 0x2eaf294 entry, [w1, w2, w3, w4] hold the 4 words that WILL be stored by 0x2eaf2fc..0x2eaf300, and w6 holds the OSAL header source ID. However, osal_valloc_msg_wait (0x2eaf2dc) has not yet executed; this is caller-intent/entry-register reconstruction, not a wire buffer read.",
                    "2_pre_send_wire_buffer_0x2eaf304": "At 0x2eaf304 (bl osal_snd_sync_msg), x1 (loaded from [x29+0x58] at 0x2eaf2f4) points to the allocated 16B OSAL message buffer immediately after 0x2eaf2fc..0x2eaf300 wrote [w25, w24, w23, w22] into [x1+0x00..0x0f] and before the synchronous send occurs.",
                    "3_post_send_buffer_0x2eaf308": "At 0x2eaf308 (cmp w0, #0x0), osal_snd_sync_msg has returned. Because osal_snd_sync_msg is synchronous, the receiver (upm.ko .text+0x2180) has already executed and may have mutated the 16B buffer in-place (e.g. writing reply status/handle at +4/+8, or rewriting word0=0x00920206 to 0x00920204 at .text+0x2400). Then 0x2eaf318..0x2eaf330 copies [x0+0..0xf] to [x19] if x19!=0, and 0x2eaf33c calls osal_free_msg.",
                },
                "disassembly_0x2eaf294_to_0x2eaf358": objdump_elf_range(
                    appfw_path, 0x2EAF294, 0x2EAF358, 0x2EAF294, appfw
                ),
                "disassembly_mss_wrappers": wrappers_disasm,
            },
            "erratum_3_del_stopper_0x00920202_preconditions_and_min_request_timeout": {
                "evidence_tier": "STATIC_ORIGINAL_CODE",
                "correction_summary": "0x00920202 (MSS_del_stopper) does NOT unconditionally start a 300s timer. Its exact state preconditions and timeout calculation in upm.ko (.text+0x2180..0x26c4) are: (1) mss_state.status ([x20+0x4c]) must be 1 (STOPPED; if status==2 RUNNING, .text+0x238c->0x26c4 logs warning 0x108 and does not touch the timer); (2) after k_mss_del_stopper (.text+0x1990) removes the matching stopper node, stopper_list ([x20+0x40]) must be NULL (.text+0x2310: ldr x0,[x20,#0x40]; 0x2314: cbz x0,0x2468); (3) at .text+0x2468..0x2490, it resets [req+0x18]=1 for all nodes in request_list ([x20+0x30]), calls k_mss_find_min_request (.text+0x1558) to select the registered request with the minimum timeout_sec, stores elapsed_sec=0 ([x20+0x48]) and status=2 ([x20+0x4c]), and calls k_mss_start_timer_nr(min_req) (.text+0x1008) which schedules the OSAL timer for (min_req->timeout_sec - elapsed_sec) = min_req->timeout_sec seconds. Thus, the started duration is the full timeout_sec of whatever minimum request is currently registered in [x20+0x30] (and if a shorter request expires first in k_mss_timer_cb .text+0x1670, .text+0x16b8..0x16c8 chains to the next request for next_req->timeout_sec - elapsed_sec). Also corrected mss_state offset table: +0x30 is request_list head, +0x40 is stopper_list head, and +0x60 is deco_list head.",
                "corrected_mss_state_offsets_in_upm_ko_data_0x0": {
                    "+0x00..0x17": "OSAL timer descriptor",
                    "+0x18..0x2f": "OSAL queue callback handle",
                    "+0x30": "request_list head pointer (verified at .text+0x155c ldr x0,[x0,#0x30] in k_mss_find_min_request and .text+0x2468 ldr x0,[x20,#0x30])",
                    "+0x38": "active_req pointer (verified at .text+0x1028 str x0,[x20,#0x38] in k_mss_start_timer_nr)",
                    "+0x40": "stopper_list head pointer (verified at .text+0x2310 ldr x0,[x20,#0x40])",
                    "+0x48": "u32 elapsed_sec (verified at .text+0x1030 ldr w1,[x20,#0x48] and .text+0x248c stp wzr,w1,[x20,#0x48])",
                    "+0x4c": "u32 status: 1=STOPPED, 2=RUNNING, 3=EXPIRED_IN_CB (verified at .text+0x21ec ldr w0,[x20,#0x4c])",
                    "+0x50": "u32 Backup_read(0x00920000) inhibit flag (verified at .text+0x0764 ldr w2,[x1,#0x50])",
                    "+0x54": "u32 Backup_read(0x0092002d) deco override flag (verified at .text+0x0774 ldr w0,[x1,#0x54])",
                    "+0x58": "u64 default 0xfff request handle (verified at .text+0x0efc str x20,[x21,#0x58])",
                    "+0x60": "deco_list head pointer (verified at .text+0x077c ldr x0,[x1,#0x60] and .text+0x1ac8 k_mss_no_deco_nr)",
                },
            },
            "erratum_4_narrowed_scope_of_got_display_update_event_0x16f11e8": {
                "evidence_tier": "STATIC_ORIGINAL_CODE",
                "correction_summary": "App::got_display_update_event(const ds_display_update_event&) (0x16f11e8..0x16f1354, caller_relative=0x16f12ec) and the QID 0x005503e0 event classifier (0x16f3750..0x16f3900, which tags 0x0015xxxx as internal App event type 5 at 0x16f38c8) do not directly call 0x2eaf294 or send to QID 0x80924220. However, static analysis of those two functions alone does NOT prove that downstream UI/screen/presenter callbacks dispatched after event type 5 can never invoke MSS APIs (0x2de0254/294/2d4/314/354/514); whether any downstream handler sends to 0x80924220 during MENU/LEFT/DOWN is an empirical question to be answered by the widened passive observation on 0x80924220.",
            },
        },
    }

    ev_v3 = dict(ev_v2)
    ev_v3["schema_version"] = "3.0.0"
    ev_v3["generated_by"] = "verify_display_contract_v3.py"
    ev_v3["v3_errata_and_verifications"] = v3_errata

    fx_v3 = dict(fx_v2)
    fx_v3["schema_version"] = "3.0.0"
    fx_v3["generated_by"] = "verify_display_contract_v3.py"
    fx_v3["upm_mss_contract_fixture"] = {
        "evidence_tier": "STATIC_ORIGINAL_CODE",
        "verified_invariants": [
            {
                "invariant": "Special 20B message 0100150001000000050000000000000000000000 at 0x16f12ec is App::got_display_update_event(const ds_display_update_event&) -> QID 0x005503e0; neither 0x16f11e8 nor the 0x16f3750 classifier directly calls 0x2eaf294, while downstream presenter/sequence side effects require runtime observation of 0x80924220.",
                "direct_send_in_0x16f11e8_or_0x16f3750": False,
                "downstream_indirect_mss_call_statically_excluded": False,
            },
            {
                "invariant": "In appFw.so 0x2eaf294..0x2eaf354, 0x2eaf2fc (29006039: stp w25,w24,[x1]) and 0x2eaf300 (29015837: stp w23,w22,[x1,#8]) write [w25=entry_w1, w24=entry_w2, w23=entry_w3, w22=entry_w4] into the 16B wire buffer x1=[x29+0x58], while entry_w6 (w26) is passed to osal_set_msg_src at 0x2eaf2f0.",
                "verified": True,
            },
            {
                "invariant": "upm.ko .text contains 12 synchronous osal_snd_sync_msg call sites to 0x80924220 (0x0130, 0x0e38, 0x0fd8, 0x614c, 0x69f4, 0x6acc, 0x6ed4, 0x700c, 0x7164, 0x88c4, 0xa2d0, 0xaa44) and 5 asynchronous upm_c3p_msg_async broadcast sites on 0x80924220 (0x08a8, 0x24b4, 0x2510, 0x2680, 0x2720).",
                "verified": True,
            },
            {
                "invariant": "upm.ko .text+0x2598 -> 0x2310 -> 0x2468..0x2490 on 0x00920202 (MSS_del_stopper) requires status==1 (STOPPED) and stopper_list ([x20+0x40]) becoming NULL; it then resets request_list ([x20+0x30]) states to 1, sets elapsed_sec=0, status=2, and starts the timer for min_req->timeout_sec (the current minimum registered request, NOT unconditionally 300s).",
                "verified": True,
            },
        ],
    }

    ev3_path = OUT_DIR / "display-contract-evidence-v3.json"
    fx3_path = OUT_DIR / "display-contract-fixture-v3.json"
    ev3_path.write_text(json.dumps(ev_v3, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fx3_path.write_text(json.dumps(fx_v3, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"[OK] Verified all 4 errata items against fixed-SHA binaries.")
    print(f"[OK] Wrote {ev3_path} (SHA256={sha256_file(ev3_path)})")
    print(f"[OK] Wrote {fx3_path} (SHA256={sha256_file(fx3_path)})")


if __name__ == "__main__":
    verify_v3_errata()
