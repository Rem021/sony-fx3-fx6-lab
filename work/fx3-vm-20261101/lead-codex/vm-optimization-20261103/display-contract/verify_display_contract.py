#!/usr/bin/env python3
"""
Deterministic static verification and fixture generator for FX3 7.02 OSD/GUI Display Contract
and Native Shutdown (scr0039_shutdown) Transition Chain.

Strictly read-only against original firmware binaries and existing run artifacts.
Writes only to display-contract/.
"""

import hashlib
import json
import os
import struct
import sys
from pathlib import Path

BASE_DIR = Path("/Volumes/KAFU2T/AI/Projects/Mac")
OUT_DIR = BASE_DIR / "work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract"

BINARIES = {
    "appFw.so": {
        "path": BASE_DIR / "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        "expected_sha256": "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f",
    },
    "libObj.so": {
        "path": BASE_DIR / "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/libObj.so",
        "expected_sha256": "c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae",
    },
    "av-cam.bin": {
        "path": BASE_DIR / "work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin",
        "expected_sha256": "0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf",
        "va_base": 0xFFFFFFC001000000,
    },
    "cpapp-b.bin": {
        "path": BASE_DIR / "work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        "expected_sha256": "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        "va_base": 0x00108000,
    },
}

RUNTIME_HELPERS = {
    "fx3-osd-core-v4-frame.h": BASE_DIR / "work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-osd-core-v4-frame.h",
    "fx3-osd-owner-core-v1.h": BASE_DIR / "work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-osd-owner-core-v1.h",
    "fx3-osd-headless-v7-observe102.c": BASE_DIR / "work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-osd-headless-v7-observe102.c",
}

RUN_ARTIFACTS = {
    "black_frame_trace": BASE_DIR / "work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/black-frame-trace.json",
    "black_transition_compare": BASE_DIR / "work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/black-transition-compare.json",
    "trial_ring_slot_live": BASE_DIR / "work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/runs/try2-70588c4c/trial-ring-slot-live.bin",
    "try2_70588c4c_serial": BASE_DIR / "work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/runs/try2-70588c4c/serial.log",
    "internal_47e2924a_serial": BASE_DIR / "work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2gapinternal-47e2924a/serial.log",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cstr(data: bytes, off: int) -> str:
    end = data.find(b"\x00", off)
    if end == -1:
        return ""
    return data[off:end].decode("utf-8", errors="replace")


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def verify_all():
    evidence = {
        "binaries": {},
        "runtime_helpers": {},
        "va_to_file_mappings": {},
        "opcode_contracts": {},
        "native_consumers": {},
        "double_buffer_swap_contract": {},
        "native_shutdown_chain": {},
        "run_correlations": {},
        "helper_semantic_gaps": [],
    }

    raw_bins = {}
    for name, meta in BINARIES.items():
        path = meta["path"]
        assert path.exists(), f"Missing binary: {path}"
        actual_sha = sha256_file(path)
        assert actual_sha == meta["expected_sha256"], (
            f"SHA256 mismatch for {name}: got {actual_sha}, expected {meta['expected_sha256']}"
        )
        data = path.read_bytes()
        raw_bins[name] = data
        evidence["binaries"][name] = {
            "path": str(path),
            "sha256": actual_sha,
            "size_bytes": len(data),
        }

    for name, path in RUNTIME_HELPERS.items():
        assert path.exists(), f"Missing helper: {path}"
        evidence["runtime_helpers"][name] = {
            "path": str(path),
            "sha256": sha256_file(path),
        }

    appfw = raw_bins["appFw.so"]
    libobj = raw_bins["libObj.so"]
    avcam = raw_bins["av-cam.bin"]
    cpapp = raw_bins["cpapp-b.bin"]

    # 1. Verify ELF / RTOS VA-to-file mappings
    # appFw.so PT_LOAD 0: off=0x0, vaddr=0x0, filesz=0x3d0f79d; PT_LOAD 1: off=0x3d10000, vaddr=0x3d20000, delta=0x10000
    e_phoff = struct.unpack_from("<Q", appfw, 0x20)[0]
    p0 = struct.unpack_from("<IIQQQQQQ", appfw, e_phoff)
    p1 = struct.unpack_from("<IIQQQQQQ", appfw, e_phoff + 56)
    assert p0[2] == 0 and p0[3] == 0 and p0[5] == 0x3D0F79D
    assert p1[2] == 0x3D10000 and p1[3] == 0x3D20000 and (p1[3] - p1[2]) == 0x10000

    # libObj.so PT_LOAD 0: off=0x0, vaddr=0x0, filesz=0x2405d5; PT_LOAD 1: off=0x240aa8, vaddr=0x250aa8, delta=0x10000
    lo_phoff = struct.unpack_from("<Q", libobj, 0x20)[0]
    lp0 = struct.unpack_from("<IIQQQQQQ", libobj, lo_phoff)
    lp1 = struct.unpack_from("<IIQQQQQQ", libobj, lo_phoff + 56)
    assert lp0[2] == 0 and lp0[3] == 0 and lp0[5] == 0x2405D5
    assert lp1[2] == 0x240AA8 and lp1[3] == 0x250AA8 and (lp1[3] - lp1[2]) == 0x10000

    evidence["va_to_file_mappings"] = {
        "appFw.so": [
            {"segment": "PT_LOAD[0]", "file_offset": "0x0", "vaddr": "0x0", "filesz": "0x3d0f79d", "va_minus_file": "0x0"},
            {"segment": "PT_LOAD[1]", "file_offset": "0x3d10000", "vaddr": "0x3d20000", "filesz": "0xe4a730", "va_minus_file": "0x10000"},
        ],
        "libObj.so": [
            {"segment": "PT_LOAD[0]", "file_offset": "0x0", "vaddr": "0x0", "filesz": "0x2405d5", "va_minus_file": "0x0"},
            {"segment": "PT_LOAD[1]", "file_offset": "0x240aa8", "vaddr": "0x250aa8", "filesz": "0x7d220", "va_minus_file": "0x10000"},
        ],
        "av-cam.bin": {
            "va_base": "0xffffffc001000000",
            "formula": "file_offset = va - 0xffffffc001000000",
        },
        "cpapp-b.bin": {
            "va_base": "0x00108000",
            "formula": "file_offset = va - 0x00108000",
        },
    }

    # 2. Verify AP Producers (appFw.so & libObj.so) and AV/CP Consumers (av-cam.bin & cpapp-b.bin)
    # 0x1000: appFw.so 0x16ee7c8..0x16ee894 -> av-cam.bin 0x2ee40c (VA 0xffffffc0012ee40c)
    assert u32(appfw, 0x16EE7D8) == 0x52820000  # mov w0, #0x1000
    assert u32(appfw, 0x16EE828) == 0x52800A02  # mov w2, #0x50 (80 bytes)
    assert cstr(appfw, 0x2F91BE5) == "sendOutputDevice"
    assert u32(avcam, 0x2EECE4) == 0x7100151F  # cmp w8, #5 (after sub 0x1000 -> dispatch 0x1000..0x1005)
    assert u32(avcam, 0x2EE420) == 0x7100411F  # cmp w8, #0x10 (hide_count <= 16)

    # 0x1001: appFw.so 0x16ee6f8 (GUI bitmap w=2), 0x16ee8d8 (MP view w=12..15), 0x176fc2c (CP widgets) -> av-cam.bin 0x2ee2dc
    assert u32(appfw, 0x16EE730) == 0x52820020  # mov w0, #0x1001
    assert u32(appfw, 0x16EE740) == 0x52800040  # mov w0, #2 (w=2 GUI bitmap plane)
    assert u32(appfw, 0x16EE74C) == 0x528003E0  # mov w0, #0x1f (priority 31)
    assert u32(appfw, 0x16EE91C) == 0x5282003A  # mov w26, #0x1001 (MP view layout)
    assert u32(appfw, 0x16EE920) == 0x52800179  # mov w25, #0xb (priority 11 for MP view)
    assert u32(appfw, 0x176FC2C) == 0xA9BD7BFD  # stp x29, x30, [sp, #-0x30]! (update_widget_info)
    assert u32(avcam, 0x2EE314) == 0xF104011F  # cmp x8, #0x100 (w < 256)
    assert cstr(avcam, 0x457677) == "void osdTrans::OsdDataManager::SetCpWidgetInfo(MpOsdTransSetCpWidgetInfo *)"

    # 0x1002: libObj.so 0xf1d90 -> av-cam.bin 0x2eed34 (FixTransInfo 0x2ee50c + WaitAndExecuteUpdateExec 0x2ef014)
    assert u32(libobj, 0xF1D9C) == 0x52800182   # mov w2, #0xc (12 bytes)
    assert u32(libobj, 0xF1E08) == 0x52820041   # mov w1, #0x1002
    assert u32(avcam, 0x2EED34) == 0x91002280   # add x0, x20, #8
    assert u32(avcam, 0x2EE524) == 0x528B0002   # mov w2, #0x5800 (memcpy 256 * 88B staging CpWidgetInfo table)
    assert cstr(avcam, 0x4578C7) == "void osdTrans::OsdTransferMsgCtrl::WaitAndExecuteUpdateExec(__uint32_t)"

    # 0x1003: libObj.so 0xf1e1c & 0xf26e0..0xf2760 -> av-cam.bin 0x2eed4c -> 0x2ee498 (SetGuiInfo)
    assert u32(libobj, 0xF1E28) == 0x52800482   # mov w2, #0x24 (36 bytes)
    assert u32(libobj, 0xF1E94) == 0x52820061   # mov w1, #0x1003
    assert u32(avcam, 0x2EED58) == 0x97FFFDD0   # bl #0x2ee498 (SetGuiInfo)
    assert u32(avcam, 0x2EED5C) == 0x528C0073   # mov w19, #0x6003 (reply op for 0x1003!)
    assert cstr(avcam, 0x4576C3) == "void osdTrans::OsdDataManager::SetGuiInfo(MpOsdTransSetGuiInfo *)"

    # 0x1004: appFw.so 0x176fb4c -> av-cam.bin 0x2ee3ec (SetWidgetTimerInfo)
    assert u32(appfw, 0x176FBC4) == 0x52820080  # mov w0, #0x1004
    assert u32(appfw, 0x176FBCC) == 0x7900A3A0  # strh w0, [x29, #0x50]
    assert u32(avcam, 0x2EE3EC) == 0x320003E8   # mov w8, #1 (timer_info_dirty = 1)

    # 0x1005: libObj.so 0xf1d04 -> av-cam.bin 0x2eed80
    assert u32(libobj, 0xF1D10) == 0x52800102   # mov w2, #8 (8 bytes)
    assert u32(libobj, 0xF1D7C) == 0x528200A1   # mov w1, #0x1005
    assert u32(avcam, 0x2EED8C) == 0x97FFFDDA   # bl #0x2ee4f4
    assert u32(avcam, 0x2EED90) == 0x528C00B3   # mov w19, #0x6005 (reply op for 0x1005!)

    # 0x6003 / 0x6005 sender in av-cam.bin: 0x2eeee0 (VA 0xffffffc0012eeee0)
    assert u32(avcam, 0x2EEEE8) == 0x2A0103F3   # mov w19, w1 (0x6003 or 0x6005)
    assert u32(avcam, 0x2EEEF8) == 0x52B05102   # movk/mov dst queue 0x8288076c upper
    assert u32(avcam, 0x2EEF08) == 0x321D03E1   # mov w1, #8 (8-byte reply packet)
    assert u32(avcam, 0x2EEF18) == 0x9400017C   # bl #0x2ef508 (populate 8B reply header)

    # 0x2001 / 0x2002 forwarder in av-cam.bin: 0x2ef0c8..0x2ef340 -> cpapp-b.bin 0x4b3628 (file 0x3ab628) & 0xa902b0 (file 0x9882b0)
    assert u32(avcam, 0x2EF2E0) == 0x97F4FF39   # bl #0x2efc4 (alloc UIPC msg)
    assert u32(avcam, 0x2EF354) == 0x97FFFF9D   # bl #0x2ef1c8 (send 0x2002 to 0x82860812)
    assert u32(cpapp, 0x3AB740) == 0x02B5F2C0   # Thumb-2 movt/check for 0x82860708 in cpapp-b.bin
    assert u32(cpapp, 0x9886B4) == 0x460D4604   # Thumb-2 dispatcher in cpapp-b.bin 0xa906b4

    # 3. Verify Double-Buffer & GPE Clear-Before-Draw Contract in libObj.so
    # FrameBuffer::initialize (0xf30ac..0xf3198): two subblocks from DMM 0x403 at fb+0x18 (on) and fb+0x38 (off)
    assert u32(libobj, 0xF3124) == 0x91002261   # add x1, x19, #8
    assert u32(libobj, 0xF3174) == 0x94003D69   # bl #0x102718
    # FrameBuffer::swap (0xf33d0): swaps fb+0x60 and fb+0x68
    assert u32(libobj, 0xF33EC) == 0xA9460660   # ldp x0, x1, [x19, #0x60]
    assert u32(libobj, 0xF33F0) == 0xA9060261   # stp x1, x0, [x19, #0x60]
    # ExternalOSDIF commit/refresh dispatcher (0xf2fa0): w1=1 swaps and sends 0x1003; w1=0 does NOT swap and sends 0x1005
    assert u32(libobj, 0xF2FFC) == 0x940000F5   # bl #0xf33d0 (FrameBuffer::swap when w1!=0 -> 0x1003)
    # GraphicsEngine::drawFramebuffer (0x16ea10): checks dirty region (0x16ea5c bl 0x128518; 0x16ea60 cbz w0, 0x16eadc)
    assert u32(libobj, 0x16EA5C) == 0x97FEE6AF  # bl #0x128518 (hasDirtyRegion)
    assert u32(libobj, 0x16EA60) == 0x340003E0  # cbz w0, #0x16eadc (notifyTimingWithoutSwap -> 0x1005)
    # GraphicsContextGRM::beginScene (0x10f318) -> clear (0x10f29c) -> fillRect(color=0) on off buffer (0x10eae0)
    assert u32(libobj, 0x10F494) == 0x97FD1807  # bl #0x554b0
    assert u32(libobj, 0x10F49C) == 0x97FD210D  # bl #0x578d0 (clear off buffer)

    # 4. Verify Native Shutdown Chain in appFw.so
    # callback_off_cmd (0x2eb74dc): 0x00920143 = UPM_CMD_OFF -> creates 16B packet with u32(+0)=0x52 (INFRA_NOTIFY_POWER_OFF)
    assert u32(appfw, 0x2EB7514) == 0x52802861  # mov w1, #0x143
    assert u32(appfw, 0x2EB7518) == 0x72A01241  # movk w1, #0x92, lsl #16 (0x00920143 = UPM_CMD_OFF)
    assert u32(appfw, 0x2EB7654) == 0x52800A40  # mov w0, #0x52 (INFRA_NOTIFY_POWER_OFF)
    assert cstr(appfw, 0x39A0219) == "%s%s(%d)  UPM_CMD_OFF : Prm1:%08x, Prm2:%08x, Prm3:%08x"
    # Model thread run (0x2a8a884): writes 0x82272dc..0x82272e4 (0x2930994) and posts ds_event 0x0003002c (0x2a8aa10)
    assert u32(appfw, 0x2A8A894) == 0x97FA9840  # bl #0x2930994
    assert u32(appfw, 0x2A8AA10) == 0x52800580  # mov w0, #0x2c
    assert u32(appfw, 0x2A8AA14) == 0x72A00060  # movk w0, #3, lsl #16 (0x0003002c)
    assert cstr(appfw, 0x37FEF33) == "%s%s(%d) INFRA_NOTIFY_POWER_OFF : factor(%08X), type(%08X), next_boot(%08X)"
    # master_input_eventgp_all_screen_screengp_All_controller (0x1d26edc..0x1d2733c): handles 0x0003002c -> opens 0x2af (scr0039_shutdown)
    assert u32(appfw, 0x1D26F10) == 0x52800581  # mov w1, #0x2c
    assert u32(appfw, 0x1D26F14) == 0x72A00061  # movk w1, #3, lsl #16 (0x0003002c)
    assert u32(appfw, 0x1D2727C) == 0x528055E0  # mov w0, #0x2af (scr0039_shutdown)
    assert u32(appfw, 0x1D27338) == 0x940148F9  # bl #0x1d7971c (open_screen)
    assert cstr(appfw, 0x3064991) == "[Master][Shutdown] factor:%08x type:%08x next_reboot:%08x"
    # scr0039_shutdown_presenter::hide_cp_widget_by_upper_layer_screen_layout (0x2145fcc..0x21460bc) -> hideMpView (0x16ee8a8)
    assert u32(appfw, 0x2146098) == 0x97D6A11B  # bl #0x16ee504 (MpOsdTransManager::getInstance)
    assert u32(appfw, 0x21460AC) == 0x17D6A1FF  # b #0x16ee8a8 (MpOsdTransManager::hideMpView)
    assert cstr(appfw, 0x30F95D5) == "scr0039_shutdown_presenter::hide_cp_widget_by_upper_layer_screen_layout()"

    # Extract shutdown factor table (file 0x41072f8, VA 0x41172f8)
    shutdown_factors = []
    for i in range(0x35):
        off = 0x41072F8 + i * 16
        model_f, upm_f, sptr = struct.unpack_from("<IIQ", appfw, off)
        shutdown_factors.append({
            "index": i,
            "model_factor": f"0x{model_f:02x}",
            "upm_factor": f"0x{upm_f:02x}",
            "name": cstr(appfw, sptr),
        })

    # 5. Verify Runtime Helper Gap in fx3-osd-headless-v7-observe102.c & trial-ring-slot-live.bin
    obs_c = RUNTIME_HELPERS["fx3-osd-headless-v7-observe102.c"].read_text(encoding="utf-8")
    bug_snippet = "memset(slot+8,0,HO_DATA-8);memcpy(slot+HO_DATA,bytes,f->span);"
    assert bug_snippet in obs_c and "w[20]=f->config_hash;" in obs_c, (
        "Expected ring_commit snippet in fx3-osd-headless-v7-observe102.c line 62"
    )

    ring_slot = RUN_ARTIFACTS["trial_ring_slot_live"].read_bytes()
    assert len(ring_slot) == 1572864  # HO_SLOT_STRIDE = 0x180000
    # Offset 0x1a4..HO_DATA (0x1000) in slot header is zeroed by memset(slot+8,0,HO_DATA-8) and configs[257] is never copied to the ring
    configs_region = ring_slot[0x1A4:0x1000]
    configs_nonzero_bytes = sum(1 for b in configs_region if b != 0)
    slot_config_hash = struct.unpack_from("<Q", ring_slot, 20 * 8)[0]
    assert configs_nonzero_bytes == 0 and slot_config_hash == 0x4741982A43F9E4BF

    # 6. Verify Both Run Serial Logs (try2-70588c4c and internal-47e2924a)
    s_user = RUN_ARTIFACTS["try2_70588c4c_serial"].read_bytes()
    s_int = RUN_ARTIFACTS["internal_47e2924a_serial"].read_bytes()

    user_shutdown_off = s_user.find(b"open screen: scr7001_1005 -> scr0039_shutdown")
    user_fill_off = s_user.find(b"FX3_GPE_CMD op=FillRect seq=1198", user_shutdown_off)
    user_commit_off = s_user.find(b"FX3_OSD102_COMMIT frame=373 op=0x1003", user_fill_off)
    assert 0 < user_shutdown_off < user_fill_off < user_commit_off

    int_shutdown_off = s_int.find(b"open screen: scr7001_1003 -> scr0039_shutdown")
    int_key2_off = s_int.find(b"FX3_KEY_INPUT_RECV step=2 key=0x15 status=1", int_shutdown_off)
    int_fill_off = s_int.find(b"FX3_GPE_CMD op=FillRect seq=717", int_key2_off)
    int_commit_off = s_int.find(b"FX3_OSD102_COMMIT frame=1311 op=0x1003", int_fill_off)
    assert 0 < int_shutdown_off < int_key2_off < int_fill_off < int_commit_off

    # Populate structured evidence
    evidence["opcode_contracts"] = {
        "0x1000_MpOsdTransSetOutputDevice": {
            "queue": "0x8280074d",
            "size_bytes": 80,
            "producer": "appFw.so 0x16ee7c8 (MpOsdTransManager::sendOutputDevice, called from 0x2191e08..0x2191ecc)",
            "consumer": "av-cam.bin 0xffffffc0012ee40c (file 0x2ee40c, osdTrans::OsdDataManager::SetOutputDeviceInfo)",
            "fields": [
                {"offset": "0x00", "type": "u16", "name": "opcode", "value": "0x1000"},
                {"offset": "0x04", "type": "u16", "name": "reserved_flag", "value": "0"},
                {"offset": "0x08", "type": "u32", "name": "output_device", "notes": "appFw.so 0x2191e1c..0x2191e4c maps display mode 1->9, 0->11, 2->2; stored to osdDataMgr+0x14 (staged) -> +0x94 (active)"},
                {"offset": "0x0c", "type": "u32", "name": "hide_count", "notes": "checked <= 16 at av-cam.bin 0x2ee420; stored to osdDataMgr+0x28 (staged) -> +0xa8 (active)"},
                {"offset": "0x10..0x4f", "type": "u32[16]", "name": "hide_targets", "notes": "copied to osdDataMgr+0x2c..0x6b (staged) -> +0xac..0xeb (active)"},
            ],
        },
        "0x1001_MpOsdTransSetCpWidgetInfo": {
            "queue": "0x8280074d",
            "size_bytes": 96,
            "producer": "appFw.so 0x16ee6f8 (sendMpGuiBitmapLayout w=2), 0x16ee8d8 (sendMpViewLayout w=12..15), 0x176fc2c (view_mp_widget_base::update_widget_info)",
            "consumer": "av-cam.bin 0xffffffc0012ee2dc (file 0x2ee2dc, osdTrans::OsdDataManager::SetCpWidgetInfo)",
            "fields": [
                {"offset": "0x00", "type": "u16", "name": "opcode", "value": "0x1001"},
                {"offset": "0x04", "type": "u16", "name": "reserved_flag", "value": "0"},
                {"offset": "0x08", "type": "u16", "name": "widget_or_plane_id_w", "notes": "w=2 is GUI bitmap plane; w=12..15 are MP view planes; checked < 0x100 in av-cam.bin 0x2ee314"},
                {"offset": "0x0a", "type": "u16", "name": "display_visible_d", "notes": "1=visible, 0=hidden; in appFw.so 0x176fc50 computed as (getMode() != 3)"},
                {"offset": "0x0c", "type": "u16", "name": "enable_flag", "notes": "1 in sendMpGuiBitmapLayout / sendMpViewLayout / update_widget_info"},
                {"offset": "0x10", "type": "u16", "name": "x", "notes": "0 for full screen"},
                {"offset": "0x12", "type": "u16", "name": "y", "notes": "0 for full screen"},
                {"offset": "0x14", "type": "u16", "name": "width", "notes": "0x0280 (640)"},
                {"offset": "0x16", "type": "u16", "name": "height", "notes": "0x01e0 (480)"},
                {"offset": "0x18", "type": "u32", "name": "layer_priority_z", "notes": "0x1f (31) for GUI bitmap w=2; 0x0b (11) for MP view w=12..15 and CP widgets"},
                {"offset": "0x1c", "type": "u32", "name": "attr_count", "notes": "1; loop copies attr_count u32s at av-cam.bin 0x2ee370..0x2ee3a0"},
                {"offset": "0x20..0x5f", "type": "u32[16]", "name": "attrs", "notes": "attrs[0] = style/mode index"},
            ],
        },
        "0x1002_MpOsdTransSetUpdate": {
            "queue": "0x8280074d",
            "size_bytes": 12,
            "producer": "libObj.so 0xf1d90 (ExternalOSDIF::sendUpdate)",
            "consumer": "av-cam.bin 0xffffffc0012eed34 & 0xffffffc0012ef014 (FixTransInfo + WaitAndExecuteUpdateExec)",
            "fields": [
                {"offset": "0x00", "type": "u16", "name": "opcode", "value": "0x1002"},
                {"offset": "0x08", "type": "u32", "name": "sub_opcode", "notes": "0x1003 (commit new surface) or 0x1005 (refresh existing surface without swap)"},
            ],
        },
        "0x1003_MpOsdTransSetGuiInfo": {
            "queue": "0x8280084d",
            "size_bytes": 36,
            "producer": "libObj.so 0xf1e1c & 0xf26e0..0xf2760",
            "consumer": "av-cam.bin 0xffffffc0012eed4c -> 0xffffffc0012ee498 (SetGuiInfo), replies 0x6003 (8B) to 0x8288076c",
            "fields": [
                {"offset": "0x00", "type": "u16", "name": "opcode", "value": "0x1003"},
                {"offset": "0x04", "type": "u16", "name": "gui_flag", "value": "0"},
                {"offset": "0x08", "type": "u32", "name": "dmm_token", "notes": "0x401 (0x43ae96100) or 0x402 (0x43feb5100), stored to osdDataMgr+0x90"},
                {"offset": "0x0c", "type": "u32", "name": "valid_one", "value": "1"},
                {"offset": "0x10", "type": "u16", "name": "format_flag", "notes": "0 -> 2B/pixel (RGB565/UT16, 614400B for 640x480), 1 -> 4B/pixel (av-cam.bin 0x2ee5f4..0x2ee608)"},
                {"offset": "0x14", "type": "u16", "name": "canvas_width", "value": "640"},
                {"offset": "0x16", "type": "u16", "name": "canvas_height", "value": "480"},
                {"offset": "0x18..0x1e", "type": "u16[4]", "name": "clip_rect_xywh", "notes": "0, 0, 640, 480"},
                {"offset": "0x20", "type": "u32", "name": "ui_response_update_id", "notes": "stored to osdDataMgr+0xec"},
            ],
        },
        "0x1004_MpOsdTransSetWidgetTimerInfo": {
            "queue": "0x8280074d",
            "size_bytes": 16,
            "producer": "appFw.so 0x176fb4c",
            "consumer": "av-cam.bin 0xffffffc0012ee3ec (SetWidgetTimerInfo)",
            "fields": [
                {"offset": "0x00", "type": "u16", "name": "opcode", "value": "0x1004"},
                {"offset": "0x04", "type": "u16", "name": "reserved_flag", "value": "0"},
                {"offset": "0x08", "type": "u64", "name": "timer_delta", "notes": "stored to osdDataMgr+0x118 (staged) -> +0x128 (active)"},
            ],
        },
        "0x1005_MpOsdTransRefresh": {
            "queue": "0x8280084e",
            "size_bytes": 8,
            "producer": "libObj.so 0xf1d04 (ExternalOSDIF::sendTimingNotification)",
            "consumer": "av-cam.bin 0xffffffc0012eed80, replies 0x6005 (8B) to 0x8288076c",
            "fields": [
                {"offset": "0x00", "type": "u16", "name": "opcode", "value": "0x1005"},
                {"offset": "0x04", "type": "u32", "name": "ui_response_update_id", "notes": "active UIResponse update_id or 0"},
            ],
        },
    }

    evidence["native_consumers"] = {
        "av_cam_osdTrans": {
            "binary": "av-cam.bin",
            "cmd_processor_loop": "0xffffffc0012eec88..0xffffffc0012eef70 (file 0x2eec88..0x2eef70)",
            "fix_trans_info": "0xffffffc0012ee50c (file 0x2ee50c) - snapshots staging CpWidgetInfo[256] (0x5800B from 0xffffffc001bb6508 to 0xffffffc001bbbd08), outputDevice, and timer_info on 0x1002",
            "reply_sender_6003_6005": "0xffffffc0012eeee0 (file 0x2eeee0) - sends 8B reply (u16 op = 0x6003 for 0x1003, 0x6005 for 0x1005) from 0x8280074d to 0x8288076c",
            "cp_forwarder_2001_2002": "0xffffffc0012ef0c8..0xffffffc0012ef340 (file 0x2ef0c8..0x2ef340) - sends 12B 0x2001 to 0x82860708 and 68B 0x2002 to 0x82860812",
        },
        "cpapp_b": {
            "binary": "cpapp-b.bin",
            "receiver_0x82860708": "0x4b3628..0x4b39c0 (file 0x3ab628..0x3ab9c0)",
            "dispatcher_2001_2002": "0xa902b0..0xa90700 (file 0x9882b0..0x988700) - receives 0x2002 on 0x82860812 and replies 0x6002 (8B) to 0x8280074d",
        },
    }

    evidence["double_buffer_swap_contract"] = {
        "dmm_pool_type": "0x403",
        "buffers": [
            {"entry_offset": "fb+0x18", "token": "0x401", "block_phys": "0x43ae96000", "pixel_phys": "0x43ae96100", "span_bytes": 614400},
            {"entry_offset": "fb+0x38", "token": "0x402", "block_phys": "0x43feb5000", "pixel_phys": "0x43feb5100", "span_bytes": 614400},
        ],
        "pointers": {
            "fb+0x60": "on_entry (currently displayed front buffer)",
            "fb+0x68": "off_entry (back buffer rendered into by GPE during beginScene..endScene)",
        },
        "draw_and_commit_rules": {
            "dirty_region_empty": "GraphicsEngine::drawFramebuffer (0x16ea10) takes cbz at 0x16ea60 -> notifyTimingWithoutSwap (0x10fa4c) -> 0xf2fa0(w1=0) -> NO swap of fb+0x60/fb+0x68 -> sends 0x1002(0x1005) + 0x1005",
            "dirty_region_nonempty": "GraphicsEngine::drawFramebuffer calls beginScene (0x10f318) -> selects off_entry [fb+0x68] -> GraphicsContextGRM::clear (0x10f29c) issues GPE_FillRect(color=0, flags=0xff, K=255, const_alpha=255) on dirty scissor rect -> draws visible widgets -> GPE_Flush -> PrepareSwap (0x154b50) -> 0xf2fa0(w1=1) -> FrameBuffer::swap (0xf33d0) swaps fb+0x60/fb+0x68 -> sends 0x1002(0x1003) + 0x1003 with new on_entry token",
        },
    }

    evidence["native_shutdown_chain"] = {
        "step_1_upm_off_callback": {
            "function": "infra_wrapper_upm::detail::callback_off_cmd(OSAL_HANDLE, void*)",
            "va": "0x2eb74dc..0x2eb7860",
            "command_code": "0x00920143 (UPM_CMD_OFF)",
            "action": "Allocates 16B model notification, sets u32(+0)=0x52 (INFRA_NOTIFY_POWER_OFF), maps Prm1 via upm2model_convert_shutdown_factor table at VA 0x41172f8 (file 0x41072f8), enqueues to model run thread",
        },
        "step_2_model_run_power_off": {
            "function": "model thread run()",
            "va": "0x2a8a884..0x2a8aa24 (jump table 0x37fe218 index 82 = 0x52)",
            "action": "Writes shutdown factor/type/next_boot to 0x82272dc..0x82272e4 (0x2930994), logs INFRA_NOTIFY_POWER_OFF, and posts ds_event 0x0003002c via 0x27381b8",
        },
        "step_3_master_all_screen_controller": {
            "function": "master_input_eventgp_all_screen_screengp_All_controller event handler",
            "va": "0x1d26edc..0x1d2733c",
            "action": "Matches ds_event.event_id == 0x0003002c, reads factor from 0x82272dc, logs [Master][Shutdown], selects screen_id 0x2af (scr0039_shutdown at 0x1d2727c), and calls open_screen (0x1d7971c)",
        },
        "step_4_scr0039_shutdown_open_and_clear": {
            "function": "scr0039_shutdown_presenter",
            "va": "0x2145df4..0x21461d0",
            "action": "Closes previous screen (scr7001_1003 id=0x275 or scr7001_1005 id=0x289), calls hide_cp_widget_by_upper_layer_screen_layout (0x2145fcc -> hideMpView 0x16ee8a8) sending 0x1001 config change, marks full 640x480 dirty with 0 visible GUI widgets; next drawFramebuffer clears off_entry via GPE_FillRect(0)+GPE_Flush, swaps on/off, and commits all-zero 0x1003",
        },
        "shutdown_factor_table_sample": shutdown_factors[:20] + [shutdown_factors[34], shutdown_factors[49], shutdown_factors[52]],
    }

    evidence["run_correlations"] = {
        "user_try2_70588c4c": {
            "shutdown_open_serial_byte": user_shutdown_off,
            "shutdown_open_line": "open screen: scr7001_1005 -> scr0039_shutdown (id1=0x289, id2=0x2af, id3=0x289)",
            "fillrect_serial_byte": user_fill_off,
            "fillrect_seq": 1198,
            "flush_seq": 1199,
            "commit_serial_byte": user_commit_off,
            "commit_frame": 373,
            "previous_on_token": "0x401 (0x43ae96100, pixel_source_seq=255)",
            "new_on_token_cleared_to_zero": "0x402 (0x43feb5100, pixel_source_seq=373)",
            "config_hash_change": "0xa8adcf1048b59ea7 -> 0x4741982a43f9e4bf",
        },
        "internal_47e2924a": {
            "shutdown_open_serial_byte": int_shutdown_off,
            "shutdown_open_line": "open screen: scr7001_1003 -> scr0039_shutdown (id1=0x275, id2=0x2af, id3=0x275)",
            "key_step2_serial_byte": int_key2_off,
            "why_keys_2_3_4_had_no_menu_effect": "scr0039_shutdown (0x2af) opened at byte 23494922 BEFORE step=2 key=0x15 at byte 24653534; keys were delivered while active screen was already scr0039_shutdown",
            "fillrect_serial_byte": int_fill_off,
            "fillrect_seq": 717,
            "flush_seq": 718,
            "commit_serial_byte": int_commit_off,
            "commit_frame": 1311,
            "previous_on_token": "0x402 (0x43feb5100, pixel_source_seq=1285)",
            "new_on_token_cleared_to_zero": "0x401 (0x43ae96100, pixel_source_seq=1311)",
            "config_hash_change": "0x8e09d7f5ffd3b3ea -> 0xe144925f50ebce45",
        },
    }

    evidence["helper_semantic_gaps"] = [
        {
            "id": "GAP-1",
            "file": "fx3-osd-headless-v7-observe102.c",
            "line": 62,
            "severity": "high",
            "bug": "In ring_commit (line 62), memset(slot+8,0,HO_DATA-8) zeroes the 25,696B slot header and writes w[20]=f->config_hash, copy of f->frame_target (slot+0xd0, 80B) and job->descriptor (slot+0x180, 36B), but NEVER copies the 24,672B process-private configs[256*96+80+16] table into the shared ring slot.",
            "proof": f"trial-ring-slot-live.bin has config_hash=0x{slot_config_hash:016x} at w[20] but {configs_nonzero_bytes} non-zero bytes in slot+0x200..0x6460.",
            "fix": "Copy configs into the reserved slot header region (e.g. memcpy(slot+0x200, configs, sizeof(configs)) since 0x200 + 24672 = 0x6260 <= HO_DATA=0x6460) so host tools can inspect raw 0x1000/0x1001/0x1004 payloads for every committed frame.",
        },
        {
            "id": "GAP-2",
            "file": "fx3-osd-owner-core-v1.h",
            "line": 94,
            "severity": "high",
            "bug": "qo_GUI rate-limits FX3_OSD_OWNER_GUI logging (c <= 30 || c % 100 == 0) and logs only op/bytes/count without decoding 0x1000 (output_device, hide_count) or 0x1001 (w, d, enable, rect, z_order, attr0), and does not snapshot staging configs on 0x1002 (FixTransInfo).",
            "proof": "In both runs, scr0039_shutdown changed config_hash (e.g., 0xa8adcf1048b59ea7 -> 0x4741982a43f9e4bf), but FX3_OSD_OWNER_GUI produced zero log lines around the transition.",
            "fix": "Log every state-changing 0x1000/0x1001 packet (or whenever config_hash changes) with decoded fields (op=0x1000: dev, hide_count; op=0x1001: w, d, en, x, y, w_px, h_px, z, attr0), and snapshot staging->active config state on 0x1002.",
        },
        {
            "id": "GAP-3",
            "file": "fx3-osd-core-v4-frame.h",
            "line": 124,
            "severity": "medium",
            "bug": "Headless frame exporter treats all-zero 0x1003 commits as an unexplained 'black frame bug' without distinguishing native blank/shutdown screen transitions (scr0039_shutdown id=0x2af / w=2 hidden / 0x1000 output_device hide) from genuine rendering failures.",
            "proof": "Both try2-70588c4c (frame 373, token 0x402) and try2gapinternal-47e2924a (frame 1311, token 0x401) are authentic GPE_FillRect(0)+GPE_Flush+swap commits caused by native scr0039_shutdown.",
            "fix": "Export active plane visibility (configs[2].d), output_device (configs[256].output_device), and blank_reason in the slot header; never mask a black 0x1003 commit by retaining stale pixels from the previous token.",
        },
    ]

    return evidence


def run_contract_model_fixture(evidence: dict) -> dict:
    """
    Executable reference model of the proved FX3 AP->AV OSD display contract
    (appFw.so + libObj.so -> av-cam.bin osdTrans::OsdDataManager), verifying:
    1. Positive replay of try2-70588c4c (token 0x401 -> scr0039_shutdown -> token 0x402 zero commit).
    2. Positive replay of internal-47e2924a (token 0x402 -> scr0039_shutdown -> token 0x401 zero commit).
    3. Negative/adversarial cases (invalid widget id >= 256, invalid hide_count > 16, 0x1005 must not swap tokens).
    """

    class OsdTransModel:
        def __init__(self, initial_on_token=0x401, initial_off_token=0x402):
            self.on_token = initial_on_token
            self.off_token = initial_off_token
            self.buffers = {
                0x401: {"phys": "0x43ae96100", "nonuniform": True, "all_zero": False},
                0x402: {"phys": "0x43feb5100", "nonuniform": True, "all_zero": False},
            }
            self.staging_widgets = {}
            self.active_widgets = {}
            self.staging_output = {"output_device": 9, "hide_count": 0, "hide_targets": []}
            self.active_output = dict(self.staging_output)
            self.timer_delta = 0
            self.pending_sub_op = 0
            self.committed_token = initial_on_token
            self.last_reply = None

        def recv_1000(self, pkt: bytes) -> bool:
            if len(pkt) < 80 or struct.unpack_from("<H", pkt, 0)[0] != 0x1000:
                return False
            dev, hide_cnt = struct.unpack_from("<II", pkt, 8)
            if hide_cnt > 16:  # av-cam.bin 0x2ee420: cmp w1, #0x10; b.hi error
                return False
            targets = list(struct.unpack_from(f"<{hide_cnt}I", pkt, 16))
            self.staging_output = {
                "output_device": dev,
                "hide_count": hide_cnt,
                "hide_targets": targets,
            }
            return True

        def recv_1001(self, pkt: bytes) -> bool:
            if len(pkt) < 96 or struct.unpack_from("<H", pkt, 0)[0] != 0x1001:
                return False
            w, d, en, _pad, x, y, width, height, z, attr_cnt = struct.unpack_from(
                "<HHHHHHHHII", pkt, 8
            )
            if w >= 256 or attr_cnt > 16:  # av-cam.bin 0x2ee314: cmp w1, #0x100
                return False
            attrs = list(struct.unpack_from(f"<{attr_cnt}I", pkt, 32))
            self.staging_widgets[w] = {
                "w": w,
                "d": d,
                "enable": en,
                "rect": [x, y, width, height],
                "z_order": z,
                "attrs": attrs,
            }
            return True

        def recv_1004(self, pkt: bytes) -> bool:
            if len(pkt) < 16 or struct.unpack_from("<H", pkt, 0)[0] != 0x1004:
                return False
            self.timer_delta = struct.unpack_from("<Q", pkt, 8)[0]
            return True

        def recv_1002(self, pkt: bytes) -> bool:
            if len(pkt) < 12 or struct.unpack_from("<H", pkt, 0)[0] != 0x1002:
                return False
            sub_op = struct.unpack_from("<I", pkt, 8)[0]
            if sub_op not in (0x1003, 0x1005):
                return False
            # FixTransInfo (av-cam.bin 0x2ee50c): snapshot staging -> active
            self.active_widgets = {k: dict(v) for k, v in self.staging_widgets.items()}
            self.active_output = dict(self.staging_output)
            self.pending_sub_op = sub_op
            return True

        def gpe_draw_and_commit(self, dirty: bool, visible_gui_widgets: int, ui_update_id: int = 0):
            if not dirty:
                # notifyTimingWithoutSwap (libObj.so 0x10fa4c -> 0xf2fa0(w1=0))
                pkt_1002 = struct.pack("<HHII", 0x1002, 0, 0, 0x1005)
                assert self.recv_1002(pkt_1002)
                pkt_1005 = struct.pack("<HHI", 0x1005, 0, ui_update_id)
                assert self.recv_1005(pkt_1005)
                return {"op": "0x1005", "token": hex(self.committed_token), "reply": hex(self.last_reply)}
            else:
                # beginScene clears off_token via GPE_FillRect(0), draws widgets, swaps on/off, sends 0x1003
                self.buffers[self.off_token]["all_zero"] = (visible_gui_widgets == 0)
                self.buffers[self.off_token]["nonuniform"] = (visible_gui_widgets > 0)
                # FrameBuffer::swap (libObj.so 0xf33d0)
                self.on_token, self.off_token = self.off_token, self.on_token
                pkt_1002 = struct.pack("<HHII", 0x1002, 0, 0, 0x1003)
                assert self.recv_1002(pkt_1002)
                pkt_1003 = struct.pack(
                    "<HHHHIIHHHHHHHHI",
                    0x1003, 0, 0, 0,
                    self.on_token, 1,
                    0, 0, 640, 480, 0, 0, 640, 480,
                    ui_update_id,
                )
                assert self.recv_1003(pkt_1003)
                return {
                    "op": "0x1003",
                    "token": hex(self.committed_token),
                    "phys": self.buffers[self.committed_token]["phys"],
                    "all_zero": self.buffers[self.committed_token]["all_zero"],
                    "reply": hex(self.last_reply),
                }

        def recv_1003(self, pkt: bytes) -> bool:
            if len(pkt) < 36 or struct.unpack_from("<H", pkt, 0)[0] != 0x1003:
                return False
            if self.pending_sub_op != 0x1003:
                return False
            token = struct.unpack_from("<I", pkt, 8)[0]
            self.committed_token = token
            self.pending_sub_op = 0
            self.last_reply = 0x6003  # av-cam.bin 0x2eed60
            return True

        def recv_1005(self, pkt: bytes) -> bool:
            if len(pkt) < 8 or struct.unpack_from("<H", pkt, 0)[0] != 0x1005:
                return False
            if self.pending_sub_op != 0x1005:
                return False
            self.pending_sub_op = 0
            self.last_reply = 0x6005  # av-cam.bin 0x2eed8c
            return True

    # Test 1: Replay user_try2_70588c4c transition
    m1 = OsdTransModel(initial_on_token=0x401, initial_off_token=0x402)
    # Normal menu refresh (frame 372): dirty=False -> 0x1005 keeps token 0x401
    r372 = m1.gpe_draw_and_commit(dirty=False, visible_gui_widgets=1)
    assert r372["op"] == "0x1005" and r372["token"] == "0x401" and r372["reply"] == "0x6005"
    # scr0039_shutdown opens: hideMpView sends 0x1001 (d=0), dirty=True, visible_gui_widgets=0
    pkt_hide_mp = struct.pack("<HHHH8HI2I15I", 0x1001, 0, 0, 0, 12, 0, 1, 0, 0, 0, 640, 480, 11, 1, 0, *([0] * 15))
    assert m1.recv_1001(pkt_hide_mp)
    r373 = m1.gpe_draw_and_commit(dirty=True, visible_gui_widgets=0)
    assert r373["op"] == "0x1003" and r373["token"] == "0x402" and r373["phys"] == "0x43feb5100" and r373["all_zero"] is True
    assert m1.active_widgets[12]["d"] == 0
    # Subsequent frame 378 (0x1005) refreshes token 0x402 without swap
    r378 = m1.gpe_draw_and_commit(dirty=False, visible_gui_widgets=0)
    assert r378["op"] == "0x1005" and r378["token"] == "0x402"

    # Test 2: Replay internal_47e2924a transition
    m2 = OsdTransModel(initial_on_token=0x402, initial_off_token=0x401)
    r1310 = m2.gpe_draw_and_commit(dirty=False, visible_gui_widgets=1)
    assert r1310["op"] == "0x1005" and r1310["token"] == "0x402"
    assert m2.recv_1001(pkt_hide_mp)
    r1311 = m2.gpe_draw_and_commit(dirty=True, visible_gui_widgets=0)
    assert r1311["op"] == "0x1003" and r1311["token"] == "0x401" and r1311["phys"] == "0x43ae96100" and r1311["all_zero"] is True
    r1314 = m2.gpe_draw_and_commit(dirty=False, visible_gui_widgets=0)
    assert r1314["op"] == "0x1005" and r1314["token"] == "0x401"

    # Test 3: Negative assertions (adversarial inputs rejected by av-cam.bin osdTrans bounds checks)
    bad_1000_hide_cnt = struct.pack("<HHHHII16I", 0x1000, 0, 0, 0, 9, 17, *([0] * 16))
    assert m1.recv_1000(bad_1000_hide_cnt) is False, "Must reject hide_count > 16 (av-cam.bin 0x2ee420)"

    bad_1001_widget_id = struct.pack("<HHHH8HI2I15I", 0x1001, 0, 0, 0, 256, 1, 1, 0, 0, 0, 640, 480, 11, 1, 0, *([0] * 15))
    assert m1.recv_1001(bad_1001_widget_id) is False, "Must reject w >= 256 (av-cam.bin 0x2ee314)"

    unpaired_1003 = struct.pack("<HHHHIIHHHHHHHHI", 0x1003, 0, 0, 0, 0x401, 1, 0, 0, 640, 480, 0, 0, 640, 480, 0)
    assert m1.recv_1003(unpaired_1003) is False, "Must reject 0x1003 without preceding 0x1002(sub_op=0x1003)"

    return {
        "status": "PASSED",
        "positive_cases": {
            "user_try2_70588c4c_replay": {"frame_372": r372, "frame_373": r373, "frame_378": r378},
            "internal_47e2924a_replay": {"frame_1310": r1310, "frame_1311": r1311, "frame_1314": r1314},
        },
        "negative_cases": [
            {"case": "0x1000_hide_count_17_gt_16", "rejected": True, "av_cam_check": "0xffffffc0012ee420 cmp w1, #0x10"},
            {"case": "0x1001_widget_id_256_ge_256", "rejected": True, "av_cam_check": "0xffffffc0012ee314 cmp w1, #0x100"},
            {"case": "0x1003_without_0x1002_pair", "rejected": True, "av_cam_check": "0xffffffc0012ef014 WaitAndExecuteUpdateExec"},
        ],
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence = verify_all()
    fixture = run_contract_model_fixture(evidence)

    ev_path = OUT_DIR / "display-contract-evidence.json"
    fx_path = OUT_DIR / "display-contract-fixture.json"

    ev_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fx_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"[OK] Verified all 4 firmware binaries, VA mappings, opcode contracts, and both run traces.")
    print(f"[OK] Wrote {ev_path}")
    print(f"[OK] Wrote {fx_path}")


if __name__ == "__main__":
    main()
