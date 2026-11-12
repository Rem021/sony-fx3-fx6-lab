#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import subprocess
import sys
from typing import Any, Dict, List

DONOR_ROOT = pathlib.Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

DONOR_BK4_NTSC = pathlib.Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "FX6-donor-assessment-20261103/team/donor/tree/0110_backup/"
    "SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin"
)

TARGET_BINARIES = [
    "bin/im.elf",
    "lib/libIMDB.so",
    "lib/libMWF.so",
    "lib/libgrm.so",
    "lib/libgrm_bmp.so",
    "lib/libgemini-grm.so",
    "lib/libuxengine.so",
    "lib/libosal_uipc.so",
    "lib/libbackup.so",
    "lib/libInfraMediaConfig.so",
    "lib/libInfraAvbbc.so",
    "lib/libInfraInput.so",
    "lib/libCertificateManager.so",
    "lib/libmpr.so",
    "lib/appFw.so",
]


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def disasm_range(path: pathlib.Path, start: int, stop: int) -> str:
    objdump_cmd = ["/usr/bin/objdump"]
    if not pathlib.Path("/usr/bin/objdump").exists():
        objdump_cmd = ["xcrun", "llvm-objdump"]
    return subprocess.check_output(
        objdump_cmd
        + [
            "-d",
            f"--start-address={hex(start)}",
            f"--stop-address={hex(stop)}",
            str(path),
        ],
        text=True,
    )


def parse_imdb_entries(libimdb_path: pathlib.Path) -> List[Dict[str, Any]]:
    data = libimdb_path.read_bytes()
    # In FX6 6.01 libIMDB.so, .data is at file offset 0xdf30 with VMA 0x1df30;
    # imdb_raw starts at VMA 0x1e870 (file offset 0xe870), entries at +0x100 (VMA 0x1e970).
    table_vma = 0x1E970
    vma_to_file = 0x10000
    table_off = table_vma - vma_to_file

    def read_cstr(ptr: int) -> str:
        if ptr == 0:
            return ""
        off = ptr - vma_to_file
        if off < 0 or off >= len(data):
            return f"<va:{hex(ptr)}>"
        end = data.find(b"\x00", off)
        if end < 0:
            return ""
        return data[off:end].decode("ascii", errors="replace")

    entries: List[Dict[str, Any]] = []
    for idx in range(180):
        off = table_off + idx * 72
        if off + 72 > len(data):
            break
        kind, flags, mask = struct.unpack_from("<III", data, off)
        mod_id, sel = struct.unpack_from("<II", data, off + 0x18)
        lib_p, sym_p, arg0_p, arg1_p = struct.unpack_from("<QQQQ", data, off + 0x28)
        entry = {
            "index": idx,
            "vma": hex(table_vma + idx * 72),
            "kind": hex(kind),
            "flags": hex(flags),
            "target_mask": hex(mask),
            "module_id": mod_id,
            "sel": sel,
            "lib": read_cstr(lib_p),
            "init": read_cstr(sym_p),
            "arg0": read_cstr(arg0_p),
            "arg1": read_cstr(arg1_p),
        }
        entries.append(entry)
        if kind == 0x08000009:
            break
    return entries


def collect_contracts() -> Dict[str, Any]:
    digests: Dict[str, Dict[str, Any]] = {}
    for rel in TARGET_BINARIES:
        p = DONOR_ROOT / rel
        digests[rel] = {
            "size_bytes": p.stat().st_size,
            "sha256": sha256_file(p),
        }
    if DONOR_BK4_NTSC.exists():
        digests["tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin"] = {
            "size_bytes": DONOR_BK4_NTSC.stat().st_size,
            "sha256": sha256_file(DONOR_BK4_NTSC),
        }

    imdb_entries = parse_imdb_entries(DONOR_ROOT / "lib/libIMDB.so")
    interesting_imdb = [
        e
        for e in imdb_entries
        if e["kind"].startswith("0x800000")
        or e["lib"]
        in (
            "libMWF.so",
            "libkiki.so",
            "appFw.so",
            "libgrm.so",
            "libInfraMediaConfig.so",
            "libInfraAvbbc.so",
            "libInfraInput.so",
            "libCertificateManager.so",
        )
        or e["init"]
        in (
            "MWF_Init",
            "InfraMediaConfig_Init",
            "Application_System_Init",
            "BIZ_Init",
        )
    ]

    snippets = {
        "im_elf_plt_401cd0": disasm_range(DONOR_ROOT / "bin/im.elf", 0x401CD0, 0x401DC0),
        "im_elf_main_phases": disasm_range(DONOR_ROOT / "bin/im.elf", 0x402490, 0x402750),
        "im_elf_kind_dispatch": disasm_range(DONOR_ROOT / "bin/im.elf", 0x405E24, 0x4062A0),
        "mwf_init_thunk": disasm_range(DONOR_ROOT / "lib/libMWF.so", 0x27D68, 0x27E78),
        "mwf_rsrc_dp_init": disasm_range(DONOR_ROOT / "lib/libMWF.so", 0x38CB0, 0x38DF4),
        "mwf_rsrc_relation_init": disasm_range(DONOR_ROOT / "lib/libMWF.so", 0x3A57C, 0x3A658),
        "mwf_objshlock_ctor_and_lock": disasm_range(DONOR_ROOT / "lib/libMWF.so", 0x3B300, 0x3B498),
        "grm_register_trigger_cb": disasm_range(DONOR_ROOT / "lib/libgrm.so", 0x22C78, 0x22D20),
        "grm_c_api_trigger_cb": disasm_range(DONOR_ROOT / "lib/libgrm.so", 0x236A8, 0x236D0),
        "grm_bmp_bytes_per_pixel": disasm_range(
            DONOR_ROOT / "lib/libgrm_bmp.so", 0x2350, 0x2410
        ),
        "gemini_grm_image_pixel_format": disasm_range(
            DONOR_ROOT / "lib/libgemini-grm.so", 0x71B0, 0x7330
        ),
        "gemini_grm_renderer_fill_blit": disasm_range(
            DONOR_ROOT / "lib/libgemini-grm.so", 0x7700, 0x7E80
        ),
        "uxengine_rgba4444_sw_compositor": disasm_range(
            DONOR_ROOT / "lib/libuxengine.so", 0x8F400, 0x8FF80
        ),
        "infra_mediaconfig_init": disasm_range(
            DONOR_ROOT / "lib/libInfraMediaConfig.so", 0x6538, 0x6790
        ),
        "infra_mediaconfig_create_tbl": disasm_range(
            DONOR_ROOT / "lib/libInfraMediaConfig.so", 0x5B50, 0x60A0
        ),
        "infra_input_send_key_event": disasm_range(
            DONOR_ROOT / "lib/libInfraInput.so", 0xB05C, 0xB390
        ),
        "mpr_slot_type_from_media_id": disasm_range(
            DONOR_ROOT / "lib/libmpr.so", 0x53C850, 0x53C8D0
        ),
        "mpr_set_movie_rec_param": disasm_range(
            DONOR_ROOT / "lib/libmpr.so", 0x16C5E0, 0x16C760
        ),
        "appfw_app_initialize": disasm_range(DONOR_ROOT / "lib/appFw.so", 0xC09DA0, 0xC09E88),
        "appfw_trigger_cb_body": disasm_range(DONOR_ROOT / "lib/appFw.so", 0xC091D0, 0xC091EC),
        "appfw_frame_gate_helpers": disasm_range(DONOR_ROOT / "lib/appFw.so", 0xDE4240, 0xDE42AC),
        "appfw_start_utimer": disasm_range(DONOR_ROOT / "lib/appFw.so", 0xC09C14, 0xC09D9C),
        "appfw_rep_boot_power_on_comp": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0x1009B90, 0x100AB50
        ),
        "appfw_shooting_ctrl_compact_dispatch": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xC69390, 0xC6947C
        ),
        "appfw_func_home_on_forwarder": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xC89AF8, 0xC89B20
        ),
        "appfw_menu_layer_1st_resolver": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xCB317C, 0xCB3200
        ),
        "appfw_shooting_ctrl_open_big6_home": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xFB3D24, 0xFB3E18
        ),
        "appfw_shooting_ctrl_menu_long_press": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xFB31A4, 0xFB321C
        ),
        "appfw_infra_input_msg_receiver": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0x2159DF4, 0x2159FA0
        ),
        "appfw_cold_boot_tail": disasm_range(DONOR_ROOT / "lib/appFw.so", 0x1CD8604, 0x1CD86B4),
        "appfw_init_hdmi": disasm_range(DONOR_ROOT / "lib/appFw.so", 0x1CD80DC, 0x1CD81C4),
        "appfw_media_slot_sync": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0x2125930, 0x2125BB0
        ),
        "appfw_network_rpc_helper": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0x215C6D0, 0x215C900
        ),
        "appfw_big6_home_ctrl_dispatch": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xC69F8C, 0xC6A078
        ),
        "appfw_big6_home_open_subdialog": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xF2E3F0, 0xF2E698
        ),
        "appfw_big6_home_kuru_pon_cursor": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xF2F130, 0xF2F3F0
        ),
        "appfw_menu_layer_1st_ctrl_dispatch": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xC6A720, 0xC6A810
        ),
        "appfw_menu_layer_2nd_ctrl_dispatch": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xC6A8A4, 0xC6A990
        ),
        "appfw_apr_cancel_to_sid_0xc9": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xF77BC0, 0xF77CF0
        ),
        "appfw_msg_2label_ctrl_factory": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xDD0700, 0xDD0810
        ),
        "libbackup_write_family": disasm_range(
            DONOR_ROOT / "lib/libbackup.so", 0x2030, 0x21EC
        ),
        "appfw_big6_look_middle_open": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xDCAD70, 0xDCAE10
        ),
        "appfw_big6_setting_commit_and_enter": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xF414F0, 0xF42330
        ),
        "appfw_menu_layer_3rd_open": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xDC4430, 0xDC44D0
        ),
        "appfw_msg_execute_confirm_ctrl": disasm_range(
            DONOR_ROOT / "lib/appFw.so", 0xF80598, 0xF80860
        ),
    }

    round4_contracts = {
        "uipc_queues": {
            "0x92840747": {
                "service": "SeqQueueCommon",
                "cmd_0x032d_reply": "8-byte status=0 completion to reply_qid",
            },
            "0x80cf016d": {
                "service": "SeqQueueNetwork",
                "caller": "appFw.so+0x215c740",
                "contract": "Non-blocking async completion (+0x04=req_type|1, +0x08=0, +0x10=+0x0c) back to reply_qid (+0x18)",
            },
            "0x80900516": {
                "service": "DMM / MediaSlotState",
                "contract": "Empty media slot completion (slot A/B absent) allowing libXavcMxf.so initialization",
            },
        },
        "nvram_backup": {
            "donor_bk4": "CX95898_NTSC.bin",
            "size_bytes": 2253333,
            "initial_setting_bkid": "0x00010079",
        },
        "pre_appfw_singletons": [
            "MWF_Init (libMWF.so)",
            "InfraMediaConfig_Init (libInfraMediaConfig.so +0x1c470)",
            "InfraInput::GetInstance (libInfraInput.so)",
        ],
    }

    round5_contracts = {
        "bmp_pixel_formats": {
            "1": {
                "grm_image_fmt": 4,
                "stella_gpe_fmt": 7,
                "bpp": 2,
                "layout": "RGBA4444 (u16 LE: [15:12]=R, [11:8]=G, [7:4]=B, [3:0]=A; 4-bit -> 8-bit * 17)",
            },
            "2": {
                "grm_image_fmt": 1,
                "stella_gpe_fmt": 1,
                "bpp": 4,
                "layout": "RGBA8888 byte-order [R, G, B, A] (u32 LE = 0xAABBGGRR) for resource bitmaps; GPE surfaces tracked as 0xAARRGGBB",
            },
            "4": {
                "grm_image_fmt": 8,
                "stella_gpe_fmt": 14,
                "bpp": 1,
                "layout": "A8 8-bit FreeType coverage mask tinted by rectblit +0x3c..+0x3f",
            },
        },
        "infra_input_key_msg_32b": {
            "src_qid": "0x007a804c",
            "dest_qid": "0x005503e0",
            "size_bytes": 32,
            "fields": {
                "+0x00": "u32 infra_key_id",
                "+0x04": "s16 sub_id1 = 0, s16 sub_id2 = 0",
                "+0x08": "u32 status (1 = PRESS, 0 = RELEASE)",
                "+0x0c..0x1f": "zero-filled flags / repeat / reserved",
            },
            "verified_keycodes": {
                "0x0003": "UP (app_key=0x0002 -> 0x02010000 EVENT_INPUT_KEY_TACT_UP_ON)",
                "0x0030": "DOWN (app_key=0x0006 -> 0x02010003 EVENT_INPUT_KEY_TACT_DOWN_ON)",
                "0x0015": "LEFT (app_key=0x0004 -> 0x02010006 EVENT_INPUT_KEY_TACT_LEFT_ON)",
                "0x01af": "RIGHT (app_key=0x0016 -> 0x0201000b EVENT_INPUT_KEY_TACT_RIGHT_ON)",
                "0x01ab": "MENU (app_key=0x0013; <1000ms -> 0x02010018 SHORT_PRESS, >=1000ms -> 0x02010017 LONG_PRESS -> sid=0x0f)",
                "0x01ac": "ENTER / SET (app_key=0x0014 -> 0x02010010 EVENT_INPUT_KEY_TACT_ENTER_ON)",
                "0x7023": "KURU_PON / Multi-Function Dial Push (app_key=0x0029 -> 0x02010157 EVENT_INPUT_KEY_OTHER_KURU_PON_ON -> Big6 cursor ON)",
                "0x704d": "IRIS (app_key=0x0044 -> 0x020100ad..0x020100b0 EVENT_INPUT_KEY_TACT_IRIS_*)",
                "0x704f": "ISO / GAIN (app_key=0x0046 -> 0x020100b1..0x020100b4 EVENT_INPUT_KEY_TACT_ISO_*)",
                "0x7098": "WHT_BAL (app_key=0x0090 -> 0x020100cf..0x020100d2 EVENT_INPUT_KEY_TACT_WB_*)",
                "0x7177": "SHUTTER_MODE (app_key=0x016f -> 0x0201010f..0x02010112 EVENT_INPUT_KEY_TACT_SHUTTER_MODE_*)",
                "0x7180": "ND_FILTER (app_key=0x0178 -> 0x0201011d/0x0201011e EVENT_INPUT_KEY_TACT_ND_FILTER_*)",
                "0x718c": "HOME / UIBIZ_KEY_TACT_HOME (app_key=0x0184 -> 0x020102d1 -> 0x02010208 EVENT_FUNC_HOME_ON -> sid=0x0a Big6 toggle)",
                "0x719a": "MENU_CANCEL / BACK (app_key=0x0192 -> 0x02010107 EVENT_INPUT_KEY_TACT_MENU_CANCEL_ON)",
            },
        },
        "screen_transitions_verified": {
            "sid_0x14": "37procam_menu_initial_setting_presenter (r5a)",
            "sid_0x02": "25procam_shooting_presenter (r5b)",
            "sid_0x0a": "31procam_big6_menu_home_presenter via 0x718c HOME (r5c)",
            "sid_0x0f": "31procam_menu_layer_1st_presenter via 0x01ab:1300ms MENU_LONG_PRESS (r5d)",
        },
    }

    round6_contracts = {
        "key_tables": {
            "infra_to_app_table_off": "0x2245a10",
            "infra_to_app_entry_count": 449,
            "infra_to_app_entry_format": "<II (u32 infra_key_id, u32 app_key)",
            "app_to_ds_table_off": "0x2ee2c08",
            "hold_short_long_table_off": "0x224e468",
            "hold_entry_format": "<6I (on_ev, off_ev, short_ev, long_ev, hold_ms, immediate_flag)",
        },
        "sid_0xc9_notice_origin": {
            "sid": "0xc9",
            "presenter_rtti": "27procam_msg_2label_presenter",
            "presenter_vptr_off": "0x2e8e760",
            "controller_rtti": "28procam_msg_2label_controller",
            "controller_factory_off": "0xdd0af4 -> 0xdd0700",
            "trigger_site_off": "0xf77c38 (41procam_msg_confirm_execute_apr_controller::process_ENTER on button 5 [Cancel])",
            "meaning": "APR Canceled 2-label confirmation toast after declining cold-boot APR execution (sid=0x23a -> sid=0x231 -> sid=0xc9)",
            "clean_dismissal": "Self-dismisses natively via 0x03010000 controller timer (~3s) with zero instruction patches (destructor ~procam_msg_2label_controller at +0xf72910 resets base subobject RTTI to 12i_controller until slots[2] is reused)",
        },
        "presenters_verified": {
            "0x14": {
                "presenter_rtti": "37procam_menu_initial_setting_presenter",
                "controller_rtti": "38procam_menu_initial_setting_controller",
                "vptr_off": "0x2e8df80",
                "slot": 0,
            },
            "0x02": {
                "presenter_rtti": "25procam_shooting_presenter",
                "controller_rtti": "26procam_shooting_controller",
                "vptr_off": "0x2e8d9e0",
                "slot": 0,
            },
            "0x0a": {
                "presenter_rtti": "31procam_big6_menu_home_presenter",
                "controller_rtti": "32procam_big6_menu_home_controller",
                "vptr_off": "0x2e8f7b0",
                "slot": 1,
            },
            "0x0c": {
                "presenter_rtti": "34procam_big6_menu_setting_presenter",
                "controller_rtti": "35procam_big6_menu_setting_controller",
                "vptr_off": "0x2e8f840",
                "slot": 2,
            },
            "0x0f": {
                "presenter_rtti": "31procam_menu_layer_1st_presenter",
                "controller_rtti": "32procam_menu_layer_1st_controller",
                "vptr_off": "0x2e8db00",
                "slot": 2,
            },
            "0x10": {
                "presenter_rtti": "31procam_menu_layer_2nd_presenter",
                "controller_rtti": "32procam_menu_layer_2nd_controller",
                "vptr_off": "0x2e8dbd8",
                "slot": 2,
            },
            "0xc9": {
                "presenter_rtti": "27procam_msg_2label_presenter",
                "controller_rtti": "28procam_msg_2label_controller",
                "vptr_off": "0x2e8e760",
                "slot": 2,
            },
        },
        "interactive_flows_verified": {
            "r6a_big6_subdialog": "0x718c (HOME -> sid=0x0a) -> 0x7023 (KURU_PON -> HOME_SCREEN_STATE=2 cursor ON) -> 0x01ac (ENTER -> sid=0x0c 34procam_big6_menu_setting_presenter)",
            "r6b_menu_layer_2nd": "0x01ab:1300 (MENU_LONG_PRESS -> sid=0x0f) -> 0x0030 (DOWN -> Shooting row 1) -> 0x01af (RIGHT -> sid=0x10 31procam_menu_layer_2nd_presenter)",
            "r6c_back_to_shooting": "0x718c (HOME -> sid=0x0a Big6 Home) -> 0x718c (HOME -> Presenter::close on slots[1] -> returns cleanly to slots[0]=25procam_shooting_presenter sid=0x02)",
        },
    }

    round7_contracts = {
        "libbackup_write_abi": {
            "Backup_write": {
                "lib_off": "0x2030..0x2074",
                "signature": "int Backup_write(uint16_t subsystem, uint32_t id, const void *buf)",
                "ipc_cmd": 9,
                "argc": 3,
                "size_resolution": "Resolved from donor BK4 entry byte length for (subsystem, id)",
            },
            "Backup_write_vsize": {
                "lib_off": "0x2074..0x20bc",
                "signature": "int Backup_write_vsize(uint16_t subsystem, uint32_t id, const void *buf, int32_t size)",
                "ipc_cmd": 10,
                "argc": 4,
            },
            "Backup_write_multi": {
                "lib_off": "0x2104..0x2148",
                "signature": "int Backup_write_multi(uint16_t subsystem, const uint32_t *ids, const void *const *ptrs)",
                "ipc_cmd": 11,
                "argc": 3,
            },
        },
        "big6_grid_cells": {
            "layout": "3x2 card grid framing central viewfinder (top row y=80..185: cell[0..2]; bottom row y=395..500: cell[3..5])",
            "cells": {
                "0": "Top-Left: FPS (S&Q Frame Rate, e.g. 60 / 59.94p -> sid=0x0c)",
                "1": "Top-Middle: ISO / Gain / Base ISO (-> sid=0x0c)",
                "2": "Top-Right: Shutter Speed / Angle (-> sid=0x0c)",
                "3": "Bottom-Left: ND Filter (-> sid=0x0c)",
                "4": "Bottom-Middle: Scene File (Custom mode -> sid=0x0c prop 0x7cb / bkid 0x02cf0546) OR Base Look / LUT (Cine EI mode -> sid=0x0b 38procam_big6_menu_look_middle_presenter)",
                "5": "Bottom-Right: White Balance (-> sid=0x0c)",
            },
        },
        "cine_ei_nvram_gating": {
            "shooting_mode_bkid": "0x02cf0482 (u8: 0x01=Custom, 0x02=Cine EI, 0x03=Cine EI Quick)",
            "cine_ei_submode_bkid": "0x02cf1373 (u32 LE: {1,0,0,0} enables Cine EI Base Look cell[4] routing at +0xf2e464 -> sid=0x0b)",
        },
        "presenters_verified": {
            "0x0b": {
                "presenter_rtti": "38procam_big6_menu_look_middle_presenter",
                "controller_rtti": "39procam_big6_menu_look_middle_controller",
                "vptr_off": "0x2e8f7f8",
                "open_off": "0xdcad70",
                "close_off": "0xdc381c",
                "ctrl_vptr_off": "0x2ebacf8",
                "slot": 2,
            },
            "0x11": {
                "presenter_rtti": "31procam_menu_layer_3rd_presenter",
                "controller_rtti": "32procam_menu_layer_3rd_controller",
                "vptr_off": "0x2e8dcf8",
                "open_off": "0xdc4430",
                "close_off": "0xdc37ec",
                "ctrl_vptr_off": "0x2ebb3f8",
                "slot": 2,
            },
            "0x17": {
                "presenter_rtti": "34procam_select_value_list_presenter",
                "controller_rtti": "35procam_select_value_list_controller",
                "vptr_off": "0x2e8de18",
                "open_off": "0xdc48ac",
                "ctrl_vptr_off": "0x2ebef18",
                "slot": 3,
            },
            "0x5a": {
                "presenter_rtti": "43procam_msg_execute_confirm_common_presenter",
                "controller_rtti": "44procam_msg_execute_confirm_common_controller",
                "vptr_off": "0x2e8e838",
                "open_off": "0xdc6fc8",
                "ctrl_vptr_off": "0x2ebcbb0",
                "slot": 2,
            },
        },
        "interactive_flows_verified": {
            "r7a_big6_base_look": "Cine EI mode (0x02cf0482=0x02, 0x02cf1373=1): 0x718c (HOME -> sid=0x0a) -> 0x7023 (KURU_PON) -> 0x01af (RIGHT -> cell[1]) -> 0x0030 (DOWN -> cell[4] Base Look/LUT) -> 0x01ac (ENTER -> sid=0x0b 38procam_big6_menu_look_middle_presenter)",
            "r7b_menu_layer_3rd": "0x01ab:1300 (MENU_LONG_PRESS -> sid=0x0f) -> 0x0030 (DOWN -> Shooting) -> 0x01af (RIGHT -> sid=0x10 2nd-layer) -> 0x01af (RIGHT -> sid=0x11 31procam_menu_layer_3rd_presenter ISO/Gain/EI)",
            "r7c_param_mutation_roundtrip": "Custom mode: 0x718c (HOME -> sid=0x0a) -> 0x7023 -> 0x01af -> 0x0030 (cell[4] Scene File) -> 0x01ac (sid=0x0c) -> 0x0030 (DOWN -> S-Cinetone) -> 0x01ac (focus [Set]) -> 0x01ac (commit Backup_write id=0x02cf0546=0x01 -> toast sid=0xc7 -> sid=0x0a) -> 0x718c (Shooting sid=0x02) -> 0x718c (re-open Big6 sid=0x0a rendering crisp 'S-Cinetone' glyphs in cell[4], 1,928-px diff bbox=(378,413)..(572,440) vs r5c)",
        },
    }

    return {
        "donor_root": str(DONOR_ROOT),
        "digests": digests,
        "imdb_highlights": interesting_imdb,
        "snippet_line_counts": {k: len(v.splitlines()) for k, v in snippets.items()},
        "round4_contracts": round4_contracts,
        "round5_contracts": round5_contracts,
        "round6_contracts": round6_contracts,
        "round7_contracts": round7_contracts,
    }


def main() -> int:
    summary = collect_contracts()
    out_path = pathlib.Path(__file__).resolve().parent / "static-contracts-summary.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes)")
    for rel, info in summary["digests"].items():
        print(f"  {rel}: {info['size_bytes']} B  sha256={info['sha256']}")
    print(f"  imdb_highlights: {len(summary['imdb_highlights'])} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
