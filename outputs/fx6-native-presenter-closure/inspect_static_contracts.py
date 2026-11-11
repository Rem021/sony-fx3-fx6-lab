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
                "+0x00": "u32 msg_type = 0x020102ff",
                "+0x04": "u32 dev_type = 0 (physical tact key)",
                "+0x08": "u16 infra_key_id",
                "+0x0a": "u16 pad = 0",
                "+0x0c": "u32 action (1 = press, 2 = release)",
                "+0x10..0x1f": "zero-filled payload",
            },
            "verified_keycodes": {
                "0x002f": "UP (app_key=0x0001)",
                "0x0030": "DOWN (app_key=0x0002)",
                "0x0031": "LEFT (app_key=0x0003)",
                "0x0032": "RIGHT (app_key=0x0004)",
                "0x01ab": "MENU (app_key=0x0013; <1000ms -> 0x02010018 SHORT_PRESS, >=1000ms -> 0x02010017 LONG_PRESS -> sid=0x0f)",
                "0x01ac": "ENTER / SET (app_key=0x0014 -> 0x02010010)",
                "0x7052": "STATUS_CHECK (app_key=0x0049 -> 0x02010019)",
                "0x718c": "HOME / UIBIZ_KEY_TACT_HOME (app_key=0x0184 -> 0x020102d1 -> 0x02010208 EVENT_FUNC_HOME_ON -> sid=0x0a Big6)",
                "0x719a": "MENU_CANCEL (app_key=0x0192 -> 0x02010107)",
                "0x71a1": "DISP_SEL (app_key=0x0199 -> 0x020100e6)",
            },
        },
        "screen_transitions_verified": {
            "sid_0x14": "37procam_menu_initial_setting_presenter (r5a)",
            "sid_0x02": "25procam_shooting_presenter (r5b)",
            "sid_0x0a": "31procam_big6_menu_home_presenter via 0x718c HOME (r5c)",
            "sid_0x0f": "31procam_menu_layer_1st_presenter via 0x01ab:1300ms MENU_LONG_PRESS (r5d)",
        },
    }

    return {
        "donor_root": str(DONOR_ROOT),
        "digests": digests,
        "imdb_highlights": interesting_imdb,
        "snippet_line_counts": {k: len(v.splitlines()) for k, v in snippets.items()},
        "round5_contracts": round5_contracts,
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
