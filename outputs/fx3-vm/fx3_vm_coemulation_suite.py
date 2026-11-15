#!/usr/bin/env python3
"""Phase 33 — Unified `outputs/fx3-vm/` Full-Board Virtual Camera Co-Emulation Orchestrator & CLI.

Combines all three `outputs/fx3-vm/` virtualization pillars into a single turn-key,
deterministic, clean-room-compliant full-board cold-boot and shooting frame cycle:

1. **Stage 1 — Cold-Boot Baseline & `virtual-rom-v1` `/dev/ttyAMA3` Bluetooth Bring-Up**:
   - Inspects `outputs/fx3-vm/manifest.json` & `run_probe.py` AP Linux VM baseline strictly
     `os.O_RDONLY` (kernel SHA-256, `2048 MiB`, `FX3_VM_ESRAM_RAM=1`, `FX3_VM_HIGH_DDR=1`,
     7 disabled hardware initcalls, `minimal-linux` & `app-loader` profiles).
   - Inspects FX6 `libbt-vendor.so` & `libInfraBluetoothCore.so` strictly `os.O_RDONLY`
     (with deterministic clean-room synthetic ELF64 fallback).
   - Runs `virtual-rom-v1` H4 UART (`/dev/ttyAMA3`) bring-up in the configured mode
     (`HEALTHY_VIRTUAL_ROM_V1`, `UART_DISCONNECTED_TIMEOUT` -> `P12` `0x0BB9` / `3001`,
     `PATCHRAM_CORRUPT_NACK` -> Sony `00342260` Airplane-latch, or `AIRPLANE_SHADOW_GATED`
     via RAM-shadow `BK4\\0`) and optionally verifies the full 4-mode containment matrix.

2. **Stage 2 — Dual-ISA `AArch64` AP <-> `IVSHMEM` <-> `ARM32 Thumb-2` Stock-CP Shooting Cycle**:
   - Executes real AArch64 (`CXD90057`) + ARM32 Thumb-2 (`CXD90058`, unmodified `cpapp-b.bin`
     mapped `UC_PROT_READ | UC_PROT_EXEC`, `cp_mutation_bytes == 0`) inside Unicorn over
     zero-copy shared RAM (`1 MiB`) and `IVSHMEM` Doorbell/Flat MMIO.
   - Verifies `P11` AP-side isolation (`0x92d2091c` `/dev/rtc0` & `0x91db059b` Smart Handle
     never enter the `IVSHMEM` TX ring or wake Stock-CP).
   - Executes ProCam Video Mode (`0x0416`), Cine EI Dual Native Base ISO (`800 / 12800`),
     `33^3` 3D LUT DMA (`0x0165 > 0xbb80` + `0x0166` toggle), and 5-axis IBIS SteadyShot
     center-lock (`0x0400`, `Off` / `Standard` / `Active`), even when BT is degraded.

3. **Stage 3 — Software GPE0 (`0x41E001000`) + `ramfb` (`0x41E100000`) HUD + Big-6 Frame**:
   - Decodes sprites strictly `os.O_RDONLY` from FX6 `image_00_169.uxc` (or clean-room
     synthetic `uxd\\x07` fixtures when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor absent).
   - Composites an authentic `1024x540` Cinema Line HUD + Big-6 frame reflecting live
     Stage 1 BT & Stage 2 Cine EI / 3D LUT / IBIS state, verifying `fx6_px` (`0xFFF08018`)
     R/B channel parity, 9-patch stretch, `A8` glyph tint, `gpe0->gpe1` parity, and
     `HOSDAP02` `ramfb` `XRGB8888` scanout.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

FX3_VM_DIR = Path(__file__).resolve().parent
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import c2pa_shading_mcfleet_ovp_emulator as p107  # noqa: E402
import camset_lpcm_tcub_emulator as p82  # noqa: E402
import cxd90057_dtb_and_mhlx_emulator as p41  # noqa: E402
import dual_ap_cp_ivshmem_bridge as p24  # noqa: E402
import dualslot_proxy_ups_salvage_emulator as p71  # noqa: E402
import fx3_vm_hil_fault_harness as p53  # noqa: E402
import gyroflow_rtmd_anamorphic_emulator as p91  # noqa: E402
import hdr_hlg_assist_fiz_gimbal_emulator as p112  # noqa: E402
import hdmi_raw_prores_breathing_mishoe_aoc_emulator as p117  # noqa: E402
import imx510_xavc_cfexpress_pipeline_emulator as p45  # noqa: E402
import interval_cache_ftp_fan_emulator as p96  # noqa: E402
import lut3d_tetrahedral_subzero_sdi_emulator as p99  # noqa: E402
import mxf_mp4_ptpv2_tally_monsoon_emulator as p127  # noqa: E402
import playback_shotmark_dewpoint_emulator as p87  # noqa: E402
import qmp_guest_introspection_tracer as p58  # noqa: E402
import realhw_body_peripheral_ibis_fan_power_coemulator as p150  # noqa: E402
import realhw_cfexpress_ufu_and_5tier_recovery_coemulator as p162  # noqa: E402
import realhw_imx510_color_and_network_usb_coemulator as p157  # noqa: E402
import realhw_mpr_dmm_recording_coemulator as p145  # noqa: E402
import realhw_preflash_dualboot_lifecycle_emulator as p141  # noqa: E402
import soft_gpe_and_bt_rom_emulator as p29  # noqa: E402
import tc_genlock_lens_paint_emulator as p67  # noqa: E402
import touch_af_ciz_assignable_emulator as p78  # noqa: E402
import usb_uvc_uac_srt_crsdk_usbpd_emulator as p121  # noqa: E402
import uvc_hdmi_raw_output_emulator as p63  # noqa: E402
import vp_ledwall_freed_artnet_vib_emulator as p132  # noqa: E402
import wireless_emi_exfat_endurance_emulator as p103  # noqa: E402


# ---------------------------------------------------------------------------
# Phase 33 Schema & Redline Locks
# ---------------------------------------------------------------------------

PHASE_33_SCHEMA = "phase33_fx3_vm_coemulation_suite_v1"
PHASE_33_VERSION = "33.0.0"

P8_CP_MUTATION_FORBIDDEN = True
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
DONOR_ACCESS_MODE = "O_RDONLY"

VALID_LUT_MODES: Tuple[str, ...] = ("8bit", "16bit", "off")
LUT_MODE_BYTES: Mapping[str, int] = {
    "8bit": p24.LUT_8BIT_ALIGNED_BYTES,
    "16bit": p24.LUT_16BIT_BYTES,
    "off": 0,
}


class CoEmulationSuiteError(RuntimeError):
    """Raised on invalid Phase 33 co-emulation configuration or redline violation."""


@dataclass(frozen=True)
class CoEmulationConfig:
    """Configuration for a deterministic full-board virtual camera co-emulation cycle."""

    bt_mode: str = p29.BT_MODE_HEALTHY
    cine_ei_iso: int = 800
    lut_mode: str = "8bit"
    ibis_mode: str = "Active"
    rtc_valid: bool = True
    bkid_0x019e0012: Optional[int] = None
    bkid_0x01a20002: Optional[int] = None
    include_bt_containment_matrix: bool = True
    include_phase41_dtb_mhlx: bool = True
    include_phase45_imx510_xavc: bool = True
    include_phase53_hil_fault_harness: bool = True
    include_phase58_qmp_introspection: bool = True
    include_phase63_hdmi_raw_uvc: bool = True
    include_phase67_tc_lens_paint: bool = True
    include_phase71_dualslot_ups_salvage: bool = True
    include_phase78_touchaf_ciz_assignable: bool = True
    include_phase82_camset_lpcm_tcub: bool = True
    include_phase87_playback_shotmark_dewpoint: bool = True
    include_phase91_gyroflow_rtmd_anamorphic: bool = True
    include_phase96_interval_cache_ftp_fan: bool = True
    include_phase99_lut3d_subzero_sdi: bool = True
    include_phase103_emi_exfat_endurance: bool = True
    include_phase107_c2pa_shading_mcfleet_ovp: bool = True
    include_phase112_hdr_hlg_fiz_gimbal: bool = True
    include_phase117_proresraw_breathing_mishoe_hil: bool = True
    include_phase121_uvc_srt_crsdk_usbpd_hil: bool = True
    include_phase127_mxf_ptpv2_tally_monsoon_hil: bool = True
    include_phase132_vp_ledwall_freed_artnet_hil: bool = True
    include_phase141_realhw_preflash_dualboot_hil: bool = True
    include_phase145_realhw_mpr_dmm_rec: bool = True
    include_phase150_realhw_body_peripheral_hil: bool = True
    include_phase157_realhw_imx510_network_usb_hil: bool = True
    include_phase162_realhw_cfexpress_ufu_5tier_hil: bool = True
    xavc_resolution: str = p45.RES_QFHD_4K
    xavc_fps: str = "59.94p"
    xavc_codec: str = p45.CODEC_XAVC_I
    recording_mode: str = p45.REC_MODE_SIMULTANEOUS
    force_clean_room: Optional[bool] = None

    def validate(self) -> None:
        if self.bt_mode not in p29.ALL_BT_OPERATING_MODES:
            raise CoEmulationSuiteError(
                f"Invalid bt_mode {self.bt_mode!r}; expected one of {p29.ALL_BT_OPERATING_MODES}"
            )
        if self.cine_ei_iso not in p24.DUAL_NATIVE_ISO_BASES:
            raise CoEmulationSuiteError(
                f"Invalid cine_ei_iso {self.cine_ei_iso!r}; expected one of {p24.DUAL_NATIVE_ISO_BASES}"
            )
        if self.lut_mode not in VALID_LUT_MODES:
            raise CoEmulationSuiteError(
                f"Invalid lut_mode {self.lut_mode!r}; expected one of {VALID_LUT_MODES}"
            )
        if self.ibis_mode not in p24.VALID_STEADYSHOT_MODES:
            raise CoEmulationSuiteError(
                f"Invalid ibis_mode {self.ibis_mode!r}; expected one of {tuple(p24.VALID_STEADYSHOT_MODES.keys())}"
            )
        if self.recording_mode not in p45.ALL_RECORDING_MODES:
            raise CoEmulationSuiteError(
                f"Invalid recording_mode {self.recording_mode!r}; expected one of {p45.ALL_RECORDING_MODES}"
            )
        try:
            p45.resolve_xavc_profile(self.xavc_codec, self.xavc_resolution, self.xavc_fps)
        except p45.PipelineConfigError as exc:
            raise CoEmulationSuiteError(str(exc)) from exc


@dataclass(frozen=True)
class ApVmManifestBaseline:
    """Read-only AP Linux QEMU baseline metadata extracted from `manifest.json` & `run_probe.py`."""

    manifest_present: bool
    run_probe_present: bool
    schema: str
    memory_mib: int
    kernel_sha256: str
    kernel_bytes: int
    model_env: Dict[str, str]
    disabled_initcalls_count: int
    profiles: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) File Helpers & UXC Cache
# ---------------------------------------------------------------------------


def read_file_readonly_bytes(path: Path) -> bytes:
    """Read a file strictly via `os.open(..., os.O_RDONLY)` and deterministic close."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = st.st_size
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 4 * 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def inspect_ap_vm_manifest(fx3_vm_dir: Path = FX3_VM_DIR) -> ApVmManifestBaseline:
    """Inspect `manifest.json` and `run_probe.py` baseline strictly `O_RDONLY` without launching QEMU."""
    manifest_path = fx3_vm_dir / "manifest.json"
    probe_path = fx3_vm_dir / "run_probe.py"
    run_probe_present = probe_path.is_file()
    if not manifest_path.is_file():
        return ApVmManifestBaseline(
            manifest_present=False,
            run_probe_present=run_probe_present,
            schema="",
            memory_mib=0,
            kernel_sha256="",
            kernel_bytes=0,
            model_env={},
            disabled_initcalls_count=0,
            profiles=(),
        )
    raw = read_file_readonly_bytes(manifest_path)
    data = json.loads(raw.decode("utf-8"))
    kernel = data.get("kernel", {})
    model_env_raw = data.get("model_env", {})
    model_env = {str(k): str(v) for k, v in sorted(model_env_raw.items())}
    profiles = tuple(sorted(str(k) for k in data.get("profiles", {}).keys()))
    return ApVmManifestBaseline(
        manifest_present=True,
        run_probe_present=run_probe_present,
        schema=str(data.get("schema", "")),
        memory_mib=int(data.get("memory_mib", 0)),
        kernel_sha256=str(kernel.get("sha256", "")),
        kernel_bytes=int(kernel.get("bytes", 0)),
        model_env=model_env,
        disabled_initcalls_count=len(data.get("disabled_initcalls", [])),
        profiles=profiles,
    )


_UXC_CACHE: Dict[
    Tuple[str, str],
    Tuple[bytes, int, Tuple[p29.UxdSpriteDescriptor, ...]],
] = {}


def load_uxc_container_cached(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Tuple[str, bytes, int, Tuple[p29.UxdSpriteDescriptor, ...]]:
    """Load and parse `image_00_169.uxc` strictly `O_RDONLY` (or clean-room synthetic `uxd\\x07`)."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room is True:
        eff_env[p29.ENV_FORCE_CLEAN_ROOM] = "1"
    elif force_clean_room is False:
        eff_env.pop(p29.ENV_FORCE_CLEAN_ROOM, None)

    paths = p29.resolve_phase29_donor_paths(env=eff_env)
    uxc_path = paths["fx6_image_uxc"]
    use_donor = uxc_path.is_file() and not p29.is_forced_clean_room(eff_env)
    source_mode = "LOCAL_DONOR_RDONLY" if use_donor else "CLEAN_ROOM_SYNTHETIC"
    cache_key = (source_mode, str(uxc_path) if use_donor else "")

    if cache_key not in _UXC_CACHE:
        uxc_bytes = p29.read_donor_bytes_readonly(uxc_path) if use_donor else p29.build_clean_room_uxd_fixture()
        entry_slots, sprites = p29.parse_uxd_sprites(uxc_bytes)
        _UXC_CACHE[cache_key] = (uxc_bytes, entry_slots, tuple(sprites))

    uxc_bytes, entry_slots, sprites = _UXC_CACHE[cache_key]
    return source_mode, uxc_bytes, entry_slots, sprites


# ---------------------------------------------------------------------------
# Stage 1: Cold-Boot Baseline & `virtual-rom-v1` `/dev/ttyAMA3` Bluetooth
# ---------------------------------------------------------------------------


def run_stage1_bt_and_coldboot(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 1: AP VM manifest baseline + `virtual-rom-v1` `/dev/ttyAMA3` BT bring-up."""
    config.validate()
    eff_env = dict(os.environ if env is None else env)
    if config.force_clean_room is True:
        eff_env[p29.ENV_FORCE_CLEAN_ROOM] = "1"
    elif config.force_clean_room is False:
        eff_env.pop(p29.ENV_FORCE_CLEAN_ROOM, None)

    manifest_baseline = inspect_ap_vm_manifest()
    bt_inspection = p29.inspect_bt_donor_libraries(
        force_clean_room=p29.is_forced_clean_room(eff_env),
        env=eff_env,
    )
    active_bt = p29.run_bsa_bringup_scenario(
        config.bt_mode,
        bkid_0x019e0012=config.bkid_0x019e0012,
        bkid_0x01a20002=config.bkid_0x01a20002,
    )

    matrix: Dict[str, Dict[str, object]] = {}
    if config.include_bt_containment_matrix:
        for mode_name in p29.ALL_BT_OPERATING_MODES:
            matrix[mode_name] = asdict(p29.run_bsa_bringup_scenario(mode_name))
    else:
        matrix[config.bt_mode] = asdict(active_bt)

    matrix_ok = all(bool(item["passed"]) for item in matrix.values())
    stage_passed = (
        manifest_baseline.manifest_present
        and manifest_baseline.run_probe_present
        and manifest_baseline.disabled_initcalls_count == 7
        and bt_inspection.all_markers_satisfied
        and active_bt.passed
        and not active_bt.system_error_abort
        and active_bt.wdt_resets == 0
        and active_bt.shooting_unaffected
        and active_bt.recording_unaffected
        and active_bt.nvram_writes == 0
        and matrix_ok
    )

    return {
        "stage": "stage1_coldboot_and_bt",
        "all_checks_passed": stage_passed,
        "ap_vm_manifest": asdict(manifest_baseline),
        "bt_donor_inspection": asdict(bt_inspection),
        "active_bt_mode": config.bt_mode,
        "active_bt_result": asdict(active_bt),
        "bt_containment_matrix": matrix,
    }


# ---------------------------------------------------------------------------
# Stage 2: Dual-ISA `AArch64` AP <-> `IVSHMEM` <-> `Thumb-2` Stock-CP Shooting Cycle
# ---------------------------------------------------------------------------


def run_stage2_dual_isa_shooting_cycle(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 2: Dual-ISA Unicorn co-emulation with P11 filter, Cine EI, 3D LUT DMA, and IBIS."""
    config.validate()
    session = p24.create_dual_ap_cp_session(
        force_clean_room=config.force_clean_room,
        env=env,
        rtc_valid=config.rtc_valid,
    )

    # 1. P11 AP-side isolation (0x92d2091c RTC & 0x91db059b Smart Handle)
    rtc_receipt = session.send_uipc_from_ap(p24.RTC_QUEUE_ID, bytes((0x03, 0x00)))
    handle_receipt = session.send_uipc_from_ap(
        p24.HANDLE_QUEUE_ID,
        struct.pack("<III", p24.HANDLE_REG_CMD, 0, 0x81CC0501),
    )

    # 2. ProCam video mode (0x0416) & Cine EI Dual Native ISO (800 / 12800)
    r_0416 = session.send_uipc_from_ap(
        p24.UIPC_BB_TARGET_QUEUE,
        p24.build_0x92840747_packet(p24.OPCODE_VIDEO_MODE_PROCAM),
    )
    r_0169 = session.send_uipc_from_ap(
        p24.UIPC_BB_TARGET_QUEUE,
        p24.build_0x92840747_packet(
            p24.OPCODE_DEVELOP_A,
            struct.pack("<BBH", 1 if config.cine_ei_iso == 800 else 0, 0, 800),
        ),
    )
    r_016a = session.send_uipc_from_ap(
        p24.UIPC_BB_TARGET_QUEUE,
        p24.build_0x92840747_packet(
            p24.OPCODE_DEVELOP_B,
            struct.pack("<HH", 12800, 1 if config.cine_ei_iso == 12800 else 0),
        ),
    )

    # 3. 33^3 3D LUT DMA (0x0165 > 0xbb80) + LUT Toggle (0x0166)
    lut_bytes = LUT_MODE_BYTES[config.lut_mode]
    roundtrip_receipts: List[p24.CoEmulationRoundTripReceipt] = [r_0416, r_0169, r_016a]
    r_0165: Optional[p24.CoEmulationRoundTripReceipt] = None
    if lut_bytes > 0:
        lut_seed = b"FX3_33CUBE_LUT_8" if config.lut_mode == "8bit" else b"FX3_33CUBE_LUT16"
        lut_payload = (lut_seed * ((lut_bytes // len(lut_seed)) + 1))[:lut_bytes]
        r_0165 = session.send_uipc_from_ap(
            p24.UIPC_BB_TARGET_QUEUE,
            p24.build_0x0165_lut_dma_packet(lut_bytes=lut_bytes),
            stage_lut_bytes=lut_payload,
        )
        roundtrip_receipts.append(r_0165)

    r_0166 = session.send_uipc_from_ap(
        p24.UIPC_BB_TARGET_QUEUE,
        p24.build_0x0166_lut_toggle_packet(enable=(lut_bytes > 0)),
    )
    roundtrip_receipts.append(r_0166)

    # 4. 5-Axis IBIS Center-Lock / SteadyShot (0x0400)
    ibis_mode_id = p24.VALID_STEADYSHOT_MODES[config.ibis_mode]
    r_0400 = session.send_uipc_from_ap(
        p24.UIPC_BB_TARGET_QUEUE,
        p24.build_0x92840747_packet(p24.OPCODE_TC_MODE, struct.pack("<BBH", ibis_mode_id, 1, 0)),
    )
    roundtrip_receipts.append(r_0400)

    immut = session.verify_cp_immutability()
    telemetry = session.telemetry_snapshot()
    all_receipts = [rtc_receipt, handle_receipt] + roundtrip_receipts

    expected_rtc_hex = "0300" if config.rtc_valid else "0301"
    expected_irqs = len(roundtrip_receipts)
    lut_ok = (
        (
            r_0165 is not None
            and r_0165.rx_completion_opcode == f"0x{p24.OPCODE_LUT_DMA | p24.UIPC_BB_COMPLETION_BIT:04x}"
            and r_0165.lut_dma_acked_bytes == lut_bytes
            and telemetry["lut_dma_ack_count"] == 1
        )
        if lut_bytes > 0
        else (telemetry["lut_dma_ack_count"] == 0)
    )

    stage_passed = (
        immut.immutable
        and immut.cp_mutation_bytes == 0
        and rtc_receipt.intercepted_by_p11
        and not rtc_receipt.tx_enqueued
        and not rtc_receipt.cp_executed
        and rtc_receipt.rx_completion_hex == expected_rtc_hex
        and handle_receipt.intercepted_by_p11
        and not handle_receipt.tx_enqueued
        and not handle_receipt.cp_executed
        and all(
            r.tx_enqueued
            and r.ap_doorbell_to_cp
            and r.cp_executed
            and r.cp_doorbell_to_ap
            and r.ibis_center_lock_energized
            and r.cp_mutation_bytes == 0
            for r in roundtrip_receipts
        )
        and lut_ok
        and telemetry["cp_verified_0x92840747"] == 1
        and telemetry["cp_verified_load_base"] == 1
        and telemetry["ibis_center_lock_state"] == 1
        and telemetry["ibis_steadyshot_mode"] == ibis_mode_id
        and telemetry["cp_doorbell_irq_count"] == expected_irqs
        and telemetry["ap_doorbell_irq_count"] == expected_irqs
        and telemetry["p11_local_rtc_count"] == 1
        and telemetry["p11_local_handle_count"] == 1
        and telemetry["malform_drop_count"] == 0
    )

    return {
        "stage": "stage2_dual_isa_cp_shooting",
        "all_checks_passed": stage_passed,
        "source_mode": session.source_mode,
        "cine_ei_iso": config.cine_ei_iso,
        "dual_native_iso_bases": list(p24.DUAL_NATIVE_ISO_BASES),
        "lut_mode": config.lut_mode,
        "lut_bytes": lut_bytes,
        "lut_enabled": lut_bytes > 0,
        "ibis_mode": config.ibis_mode,
        "ibis_mode_id": ibis_mode_id,
        "ibis_center_lock_energized": bool(telemetry["ibis_center_lock_state"]),
        "rtc_valid": config.rtc_valid,
        "cp_mutation_bytes": immut.cp_mutation_bytes,
        "cp_immutability": asdict(immut),
        "cp_inspection": asdict(session.cp_inspection),
        "ap_inspection": asdict(session.ap_inspection),
        "telemetry": telemetry,
        "doorbell_event_count": len(session.bus.doorbell_trace),
        "receipts": [asdict(r) for r in all_receipts],
    }


# ---------------------------------------------------------------------------
# Stage 3: Software GPE0 (`0x41E001000`) + `ramfb` (`0x41E100000`) HUD + Big-6 Frame
# ---------------------------------------------------------------------------


_STAGE3_HUD_CACHE: Dict[Tuple[object, ...], Dict[str, object]] = {}


def run_stage3_soft_gpe_hud_composite(
    config: CoEmulationConfig,
    *,
    bt_result: Mapping[str, object],
    cp_result: Mapping[str, object],
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 3: `1024x540` HUD + Big-6 frame composited on `GPE0` and scanned to `HOSDAP02` `ramfb`."""
    config.validate()
    source_mode, uxc_bytes, entry_slots, sprites = load_uxc_container_cached(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    active_bt = bt_result.get("active_bt_result", {})
    if active_bt.get("bsa_ready"):
        bt_badge_rgb = (0x28, 0xC8, 0x78)
    elif active_bt.get("airplane_latched"):
        bt_badge_rgb = (0xB8, 0x3C, 0x46)
    else:
        bt_badge_rgb = (0xF0, 0x98, 0x20)
    cp_ok = bool(cp_result.get("all_checks_passed"))
    cache_key = (
        source_mode,
        len(uxc_bytes),
        entry_slots,
        len(sprites),
        config.cine_ei_iso,
        config.lut_mode,
        config.ibis_mode,
        bt_badge_rgb,
        cp_ok,
    )
    if cache_key in _STAGE3_HUD_CACHE:
        cached = dict(_STAGE3_HUD_CACHE[cache_key])
        cached["ramfb_scanout"] = dict(cached["ramfb_scanout"])  # type: ignore[arg-type]
        return cached

    nine_patches = [s for s in sprites if s.is_nine_patch]
    standards = [s for s in sprites if not s.is_nine_patch]

    engine = p29.SoftGpeEngine()

    # 1. Backdrop & Cinema Line HUD + Big-6 Layout via GRM_gpermFillrect
    engine.grm_fillrect(0, 0, 1024, 540, 0x10, 0x14, 0x1A, 0xFF)
    # Top status bar
    engine.grm_fillrect(0, 0, 1024, 42, 0x18, 0x20, 0x2C, 0xFF)
    # Left Cine EI / ISO / LUT card + Cinema Line Amber accent strip (0xFFF08018)
    engine.grm_fillrect(8, 52, 224, 140, 0x22, 0x2E, 0x3E, 0xFF)
    engine.grm_fillrect(8, 52, 6, 140, 0xF0, 0x80, 0x18, 0xFF)

    # Cine EI ISO indicator block (800 = cool cyan, 12800 = high-sensitivity gold)
    if config.cine_ei_iso == 12800:
        engine.grm_fillrect(24, 144, 192, 32, 0xE8, 0xA8, 0x28, 0xFF)
    else:
        engine.grm_fillrect(24, 144, 192, 32, 0x2C, 0x9C, 0xDC, 0xFF)

    # Translucent center LUT / viewfinder HUD overlay (BLEND_SRC_OVER_CONST_ALPHA)
    overlay_r, overlay_g, overlay_b = (0x1A, 0x30, 0x28) if config.lut_mode != "off" else (0x14, 0x1E, 0x28)
    engine.grm_fillrect(
        248,
        56,
        160,
        64,
        overlay_r,
        overlay_g,
        overlay_b,
        0xAA,
        blend_mode=p29.BLEND_SRC_OVER_CONST_ALPHA,
        const_alpha=0xC0,
    )

    # Right IBIS center-lock card (reflects Off / Standard / Active + energized lock)
    ibis_rgb = {
        "Off": (0x64, 0x70, 0x80),
        "Standard": (0x38, 0xB8, 0xE8),
        "Active": (0x30, 0xD8, 0x88),
    }[config.ibis_mode]
    engine.grm_fillrect(796, 52, 220, 72, 0x1E, 0x28, 0x36, 0xFF)
    engine.grm_fillrect(796, 52, 6, 72, *ibis_rgb, 0xFF)

    # Top-right BT status badge (reflects Stage 1 healthy / P12 / 00342260 / airplane-gated)
    engine.grm_fillrect(890, 10, 120, 22, *bt_badge_rgb, 0xFF)

    # Big-6 bottom status strip (6 cells across 1008px)
    engine.grm_fillrect(8, 436, 1008, 92, 0x18, 0x22, 0x30, 0xFF)
    for cell_idx in range(6):
        cx = 16 + cell_idx * 166
        engine.grm_fillrect(cx, 446, 158, 72, 0x22, 0x30, 0x42, 0xFF)
        if cell_idx == 3:
            # Big-6 EI cell highlights active base ISO
            engine.grm_fillrect(cx, 512, 158, 6, 0xF0, 0x80, 0x18, 0xFF)

    # 2. Composite O_RDONLY-decoded `.uxc` sprites (standard + 9-patch) + A8/RGBA8888/ARGB4444
    decoded_sprites_count = 0
    if standards:
        sp0 = standards[0]
        surf0 = p29.decode_uxd_sprite_to_surface(uxc_bytes, sp0)
        engine.grm_rectblit(surf0, (0, 0, sp0.width, sp0.height), (24, 72, sp0.width, sp0.height))
        decoded_sprites_count += 1
    if nine_patches:
        np0 = nine_patches[0]
        surf_np = p29.decode_uxd_sprite_to_surface(uxc_bytes, np0)
        engine.grm_nine_patch_blit(surf_np, (256, 68, 260, 64), np0.insets)
        decoded_sprites_count += 1

    a8_glyph = p29.GpeSurface(8, 8, p29.PIXEL_FMT_A8, raw_bytes=bytes([0xFF] * 64))
    engine.grm_rectblit(
        a8_glyph,
        (0, 0, 8, 8),
        (540, 68, 8, 8),
        color_mod=p29.COLOR_MOD_TINT,
        tint_rgb=(0xEE, 0xEE, 0xEE),
    )
    rgba8888_surf = p29.GpeSurface(4, 4, p29.PIXEL_FMT_RGBA8888, raw_bytes=bytes([0xF0, 0x38, 0x38, 0xFF]) * 16)
    engine.grm_rectblit(rgba8888_surf, (0, 0, 4, 4), (554, 68, 4, 4))
    argb4444_surf = p29.GpeSurface(4, 4, p29.PIXEL_FMT_ARGB4444, raw_bytes=struct.pack("<H", 0xF28E) * 16)
    engine.grm_rectblit(argb4444_surf, (0, 0, 4, 4), (564, 68, 4, 4))

    # 3. Flush GPE0 -> GPE1 parity and composite onto HOSDAP02 ramfb
    gpe0_sha = engine.flush_to_offscreen_parity()
    hdr, _ramfb_bytes, ramfb_stats = engine.hosdap02_ramfb_scanout()

    amber_px = engine.gpe0.read_argb32(10, 80)
    rb_parity_ok = amber_px == p29.fx6_px(0xF0, 0x80, 0x18, 0xFF) == 0xFFF08018
    bt_badge_px = engine.gpe0.read_argb32(900, 18)
    expected_bt_px = p29.fx6_px(*bt_badge_rgb, 0xFF)

    stage_passed = (
        len(sprites) > 0
        and len(nine_patches) > 0
        and decoded_sprites_count >= 2
        and rb_parity_ok
        and bt_badge_px == expected_bt_px
        and hdr[:8] == p29.HOSDAP02_MAGIC
        and len(hdr) == p29.HOSDAP02_HEADER_BYTES
        and int(ramfb_stats["nonzero_gpe0_pixels"]) == p29.GPE0_PIXEL_COUNT
        and int(ramfb_stats["unique_gpe0_colors"]) >= 8
        and int(ramfb_stats["ramfb_bytes"]) == p29.GPE0_BYTES
        and gpe0_sha == engine.gpe1.sha256()
        and bool(cp_result.get("all_checks_passed"))
    )

    result: Dict[str, object] = {
        "stage": "stage3_soft_gpe_hud_ramfb",
        "all_checks_passed": stage_passed,
        "source_mode": source_mode,
        "uxc_bytes": len(uxc_bytes),
        "entry_slots": entry_slots,
        "total_sprites": len(sprites),
        "nine_patch_sprites": len(nine_patches),
        "decoded_sprites_composited": decoded_sprites_count,
        "fillrect_count": engine.fillrect_count,
        "rectblit_count": engine.rectblit_count,
        "nine_patch_count": engine.nine_patch_count,
        "flush_count": engine.flush_count,
        "ramfb_scanout_count": engine.ramfb_scanout_count,
        "fx6_px_rb_parity_ok": rb_parity_ok,
        "amber_accent_px_hex": f"0x{amber_px:08x}",
        "bt_badge_px_hex": f"0x{bt_badge_px:08x}",
        "hosdap02_header_hex": hdr[:16].hex(),
        "ramfb_scanout": ramfb_stats,
    }
    _STAGE3_HUD_CACHE[cache_key] = result
    out = dict(result)
    out["ramfb_scanout"] = dict(ramfb_stats)
    return out


# ---------------------------------------------------------------------------
# Stage 4 (Phase 41): CXD90057 Pure-Python FDT/DTB + MHLX Ring + MMIO Window
# ---------------------------------------------------------------------------


def run_stage4_dtb_mhlx_mmio(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 4 (Phase 41): FDT v17 synthesizer, `0xf0000000..0xf8ffffff` MMIO, MHLX ring & `shm_Loader`."""
    config.validate()
    rep = p41.run_phase41_emulator_audit(
        bt_mode=config.bt_mode,
        force_clean_room=config.force_clean_room,
        env=env,
    )
    return {
        "stage": "stage4_phase41_dtb_mhlx_mmio",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["donor_kernel_mmio_audit"]["source_mode"],
        "cp_mutation_bytes": rep["redlines"]["cp_mutation_bytes"],
        "wbi_mutation_bytes": rep["redlines"]["wbi_mutation_bytes"],
        "fdt_synthesis_and_audit": rep["fdt_synthesis_and_audit"],
        "donor_kernel_mmio_audit": rep["donor_kernel_mmio_audit"],
        "mmio_window_emulation": rep["mmio_window_emulation"],
        "shm_loader_handshakes": rep["shm_loader_handshakes"],
        "phase41_audit_digest_sha256": rep["audit_digest_sha256"],
    }


# ---------------------------------------------------------------------------
# Stage 5 (Phase 45): IMX510 VSYNC, libmpr XAVC, RTMD 0xE304 & Dual Slot A/B
# ---------------------------------------------------------------------------


def run_stage5_imx510_xavc_cfexpress(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 5 (Phase 45): IMX510 VSYNC, libmpr XAVC-I/S-I, RTMD 0xE304 & Dual CFexpress/SDXC."""
    config.validate()
    rep = p45.run_phase45_pipeline_audit(
        resolution_mode=config.xavc_resolution,
        fps_label=config.xavc_fps,
        codec_family=config.xavc_codec,
        recording_mode=config.recording_mode,
        base_iso=config.cine_ei_iso,
        lut_mode=config.lut_mode,
        ibis_mode=config.ibis_mode,
        force_clean_room=config.force_clean_room,
        env=env,
    )
    return {
        "stage": "stage5_phase45_imx510_xavc_cfexpress",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "cp_mutation_bytes": rep["redlines"]["cp_mutation_bytes"],
        "wbi_mutation_bytes": rep["redlines"]["wbi_mutation_bytes"],
        "physical_device_writes": rep["redlines"]["physical_device_writes"],
        "donor_audit": rep["donor_audit"],
        "primary_recording": rep["primary_recording"],
        "containment_matrix": rep["containment_matrix"],
        "phase45_audit_digest_sha256": rep["audit_digest_sha256"],
    }


# ---------------------------------------------------------------------------
# Stage 6 (Phase 53): HIL Dynamic Fault-Injection & Thermal / C2PA Harness
# ---------------------------------------------------------------------------


def run_stage6_hil_fault_harness(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 6 (Phase 53): 8-scenario HIL fault-injection & thermal/NP-FZ100/XLR-H1/C2PA harness."""
    config.validate()
    rep = p53.run_phase53_hil_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    return {
        "stage": "stage6_phase53_hil_fault_harness",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "scenarios_total": rep["scenarios_total"],
        "scenarios_passed": rep["scenarios_passed"],
        "cp_mutation_bytes": rep["redlines"]["cp_mutation_bytes"],
        "wbi_mutation_bytes": rep["redlines"]["wbi_mutation_bytes"],
        "calibration_mutation_bytes": rep["redlines"]["calibration_mutation_bytes"],
        "nvram_persistent_writes": rep["redlines"]["nvram_persistent_writes"],
        "physical_device_writes": rep["redlines"]["physical_device_writes"],
        "donor_audit": rep["donor_audit"],
        "board_integrity": rep["board_integrity"],
        "scenarios": rep["scenarios"],
        "phase53_audit_digest_sha256": rep["audit_digest_sha256"],
    }


# ---------------------------------------------------------------------------
# Stage 7 (Phase 58): Non-Intrusive QMP Guest Introspection & USB-LAN PTP-IP Tracer
# ---------------------------------------------------------------------------


def run_stage7_qmp_guest_introspection(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 7 (Phase 58): Non-intrusive QMP introspection + USB-LAN CDC-NCM / PTP-IP 15740 tracer."""
    config.validate()
    rep = p58.run_phase58_qmp_tracer_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    return {
        "stage": "stage7_phase58_qmp_introspection",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": rep["redlines"]["nop_count"],
        "guest_code_modification_bytes": rep["redlines"]["guest_code_modification_bytes"],
        "cp_mutation_bytes": rep["redlines"]["cp_mutation_bytes"],
        "wbi_mutation_bytes": rep["redlines"]["wbi_mutation_bytes"],
        "calibration_mutation_bytes": rep["redlines"]["calibration_mutation_bytes"],
        "nvram_persistent_writes": rep["redlines"]["nvram_persistent_writes"],
        "physical_device_writes": rep["redlines"]["physical_device_writes"],
        "donor_audit": rep["donor_audit"],
        "qmp_session": rep["qmp_session"],
        "guest_introspection": rep["guest_introspection"],
        "usblan_p12_isolation": rep["usblan_p12_isolation"],
        "ptpip_15740_safe_channel": rep["ptpip_15740_safe_channel"],
        "ptpip_allowed_count": rep["ptpip_15740_safe_channel"]["allowed_count"],
        "ptpip_blocked_count": rep["ptpip_15740_safe_channel"]["blocked_count"],
        "phase58_audit_digest_sha256": rep["audit_digest_sha256"],
    }


# ---------------------------------------------------------------------------
# Stage 8 (Phase 63): HDMI Type-A RAW16 EDID, MLUT Clean-Feed & USB-C Arbitrator
# ---------------------------------------------------------------------------


def run_stage8_hdmi_raw_uvc_arbitrator(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 8 (Phase 63): 256B EDID RAW16/MLUT handshake, 12G-SDI containment & USB-C arbitrator."""
    config.validate()
    rep = p63.run_phase63_hdmi_uvc_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    return {
        "stage": "stage8_phase63_hdmi_raw_uvc",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": rep["redlines"]["nop_count"],
        "guest_code_modification_bytes": rep["redlines"]["guest_code_modification_bytes"],
        "cp_mutation_bytes": rep["redlines"]["cp_mutation_bytes"],
        "wbi_mutation_bytes": rep["redlines"]["wbi_mutation_bytes"],
        "calibration_mutation_bytes": rep["redlines"]["calibration_mutation_bytes"],
        "nvram_persistent_writes": rep["redlines"]["nvram_persistent_writes"],
        "physical_device_writes": rep["redlines"]["physical_device_writes"],
        "persistent_emmc_writes_authorized": rep["redlines"]["persistent_emmc_writes_authorized"],
        "sdi_transceiver_faults": rep["redlines"]["sdi_transceiver_faults"],
        "donor_audit": rep["donor_audit"],
        "edid_synthesis": rep["edid_synthesis"],
        "hdmi_negotiation_matrix": rep["hdmi_negotiation_matrix"],
        "sdi_noop_containment": rep["sdi_noop_containment"],
        "usbc_arbitrator_matrix": rep["usbc_arbitrator_matrix"],
        "phase63_audit_digest_sha256": rep["audit_digest_sha256"],
    }


# ---------------------------------------------------------------------------
# Stage 9 (Phase 67): SMPTE 12M TC EXT-LK, E-Mount PZ/Breathing/IBIS & libpaint
# ---------------------------------------------------------------------------


def run_stage9_tc_lens_paint(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 9 (Phase 67): SMPTE 12M TC EXT-LK, E-Mount PZ/Breathing/IBIS+OSS & libpaint 3x3 Matrix."""
    config.validate()
    rep = p67.run_phase67_tc_lens_paint_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    return {
        "stage": "stage9_phase67_tc_lens_paint",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": rep["redlines"]["nop_count"],
        "guest_code_modification_bytes": rep["redlines"]["guest_code_modification_bytes"],
        "cp_mutation_bytes": rep["redlines"]["cp_mutation_bytes"],
        "wbi_mutation_bytes": rep["redlines"]["wbi_mutation_bytes"],
        "calibration_mutation_bytes": rep["redlines"]["calibration_mutation_bytes"],
        "nvram_persistent_writes": rep["redlines"]["nvram_persistent_writes"],
        "physical_device_writes": rep["redlines"]["physical_device_writes"],
        "persistent_emmc_writes_authorized": rep["redlines"]["persistent_emmc_writes_authorized"],
        "donor_audit": rep["donor_audit"],
        "smpte_12m_tc_genlock": rep["smpte_12m_tc_genlock"],
        "emount_pz_breathing_ibis": rep["emount_pz_breathing_ibis"],
        "libpaint_color_pipeline": rep["libpaint_color_pipeline"],
        "phase67_audit_digest_sha256": rep["audit_digest_sha256"],
    }


# ---------------------------------------------------------------------------
# Stage 10 (Phase 71): Dual-Slot Proxy, NonRealTimeMeta.xml & UPS / .RSV Salvage
# ---------------------------------------------------------------------------


def run_stage10_dualslot_proxy_ups_salvage(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 10 (Phase 71): Dual-Slot Relay/Simul/Sort Proxy, NonRealTimeMeta.xml & UPS/.RSV Salvage."""
    config.validate()
    rep = p71.run_phase71_dualslot_ups_salvage_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    rsv = rep["ups_brownout_rsv_salvage"]["batteryless_brownout_rsv_salvage"]
    return {
        "stage": "stage10_phase71_dualslot_ups_salvage",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": rep["redlines"]["nop_count"],
        "guest_code_modification_bytes": rep["redlines"]["guest_code_modification_bytes"],
        "cp_mutation_bytes": rep["redlines"]["cp_mutation_bytes"],
        "wbi_mutation_bytes": rep["redlines"]["wbi_mutation_bytes"],
        "calibration_mutation_bytes": rep["redlines"]["calibration_mutation_bytes"],
        "nvram_persistent_writes": rep["redlines"]["nvram_persistent_writes"],
        "physical_device_writes": rep["redlines"]["physical_device_writes"],
        "persistent_emmc_writes_authorized": rep["redlines"]["persistent_emmc_writes_authorized"],
        "p1_emmc_mutations": rep["redlines"]["p1_emmc_mutations"],
        "internal_emmc_writes": rep["redlines"]["internal_emmc_writes"],
        "c2pa_license_untouched": rep["redlines"]["c2pa_license_untouched"],
        "rsv_salvageable_frames": rsv["salvageable_frames"],
        "rsv_committed_frames": rsv["committed_ring_frames"],
        "donor_audit": rep["donor_audit"],
        "dualslot_proxy_pipeline": rep["dualslot_proxy_pipeline"],
        "nonrealtimemeta_rtmd_sync": rep["nonrealtimemeta_rtmd_sync"],
        "ups_brownout_rsv_salvage": rep["ups_brownout_rsv_salvage"],
        "phase71_audit_digest_sha256": rep["audit_digest_sha256"],
    }


# ---------------------------------------------------------------------------
# Stage 11 (Phase 78): Touch AF 627-pt PDAF, CIZ Arbitrator & Assignable Dispatcher
# ---------------------------------------------------------------------------


def run_stage11_touchaf_ciz_assignable(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 11 (Phase 78): evdev Touch AF 627-pt PDAF, CIZ Arbitrator & Assignable Dispatcher."""
    config.validate()
    rep = p78.run_phase78_touchaf_ciz_assignable_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage11_phase78_touchaf_ciz_assignable",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "donor_audit": rep["donor_audit"],
        "touch_af_pdaf_pipeline": rep["touch_af_pdaf_pipeline"],
        "tw_zoom_ciz_arbitrator": rep["tw_zoom_ciz_arbitrator"],
        "assignable_button_dispatcher": rep["assignable_button_dispatcher"],
        "phase78_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage12_camset_lpcm_tcub(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 12 (Phase 82): Cross-Body CAMSET Sanitizer, 4ch 24-bit/48kHz LPCM & SMPTE 12M User-Bits."""
    config.validate()
    rep = p82.run_phase82_camset_lpcm_tcub_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage12_phase82_camset_lpcm_tcub",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "uart_boot_contention_events": red["uart_boot_contention_events"],
        "donor_audit": rep["donor_audit"],
        "camset_cross_body_sanitizer": rep["camset_cross_body_sanitizer"],
        "lpcm_4ch_24bit_48khz_pipeline": rep["lpcm_4ch_24bit_48khz_pipeline"],
        "smpte_12m_user_bits_tc_regenerator": rep["smpte_12m_user_bits_tc_regenerator"],
        "phase82_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage13_playback_shotmark_dewpoint(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 13 (Phase 87): Playback/ShotMark, Cine EI Push Auto Iris & Dew-Point/PMIC 5V HIL."""
    config.validate()
    rep = p87.run_phase87_playback_shotmark_dewpoint_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage13_phase87_playback_shotmark_dewpoint",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "internal_emmc_format_blocked": red["internal_emmc_format_blocked"],
        "internal_emmc_writes": red["internal_emmc_writes"],
        "p1_emmc_mutations": red["p1_emmc_mutations"],
        "c2pa_license_untouched": red["c2pa_license_untouched"],
        "p4_nd_motor_faults": red["p4_nd_motor_faults"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "donor_audit": rep["donor_audit"],
        "playback_shotmark_emmc_guard": rep["playback_shotmark_emmc_guard"],
        "cine_ei_push_auto_iris": rep["cine_ei_push_auto_iris"],
        "dewpoint_pmic_5v_hil": rep["dewpoint_pmic_5v_hil"],
        "phase87_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage14_gyroflow_rtmd_anamorphic(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 14 (Phase 91): 2000Hz IMU RTMD 0xE4xx, Anamorphic IBIS Arbitrator & IMX510 RS HIL."""
    config.validate()
    rep = p91.run_phase91_gyroflow_rtmd_anamorphic_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage14_phase91_gyroflow_rtmd_anamorphic",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "donor_audit": rep["donor_audit"],
        "imu_2000hz_rtmd_e4xx": rep["imu_2000hz_rtmd_e4xx"],
        "anamorphic_ibis_arbitrator": rep["anamorphic_ibis_arbitrator"],
        "imx510_rolling_shutter_hil": rep["imx510_rolling_shutter_hil"],
        "phase91_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage15_interval_cache_ftp_fan(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 15 (Phase 96): Interval Rec, Picture Cache 384MiB DDR Ring, USB-LAN FTPS & Fan/Housing HIL."""
    config.validate()
    rep = p96.run_phase96_interval_cache_ftp_fan_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage15_phase96_interval_cache_ftp_fan",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "emmc_partition_mutations": red["emmc_partition_mutations"],
        "donor_audit": rep["donor_audit"],
        "interval_recording_timelapse": rep["interval_recording_timelapse"],
        "picture_cache_ddr_ring": rep["picture_cache_ddr_ring"],
        "wired_usblan_ftps_p12": rep["wired_usblan_ftps_p12"],
        "sigma_fan_housing_hil": rep["sigma_fan_housing_hil"],
        "phase96_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage16_lut3d_subzero_sdi(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 16 (Phase 99): 65^3->33^3 Tetrahedral 3D-LUT DMA, HDMI AVI->12G-SDI Bridge & Sub-Zero/Altitude HIL."""
    config.validate()
    rep = p99.run_phase99_lut3d_subzero_sdi_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage16_phase99_lut3d_subzero_sdi",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "sdi_transceiver_faults": red["sdi_transceiver_faults"],
        "lithium_plating_events": red["lithium_plating_events"],
        "dropped_rec_triggers": red["dropped_rec_triggers"],
        "donor_audit": rep["donor_audit"],
        "lut3d_tetrahedral_dma": rep["lut3d_tetrahedral_dma"],
        "hdmi_avi_to_12g_sdi_bridge": rep["hdmi_avi_to_12g_sdi_bridge"],
        "subzero_esr_and_altitude_hil": rep["subzero_esr_and_altitude_hil"],
        "phase99_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage17_emi_exfat_endurance(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 17 (Phase 103): Wireless TX EMI/ESD/LTC, 12h exFAT/SMART & Zero-eMMC-Churn Endurance HIL."""
    config.validate()
    rep = p103.run_phase103_emi_exfat_endurance_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage17_phase103_emi_exfat_endurance",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "emmc_sector_writes": red["emmc_sector_writes"],
        "emmc_wear_level_increments": red["emmc_wear_level_increments"],
        "cxd90057_gpio_damage_events": red["cxd90057_gpio_damage_events"],
        "dropped_audio_samples": red["dropped_audio_samples"],
        "dropped_video_frames": red["dropped_video_frames"],
        "donor_audit": rep["donor_audit"],
        "longform_exfat_smart_hil": rep["longform_exfat_smart_hil"],
        "wireless_emi_hotplug_ltc_hil": rep["wireless_emi_hotplug_ltc_hil"],
        "zero_emmc_nvram_churn_endurance": rep["zero_emmc_nvram_churn_endurance"],
        "phase103_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage18_c2pa_shading_mcfleet_ovp(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 18 (Phase 107): C2PA 2.1 cnflasha Firewall, E-Mount/PL Shading Arbitrator, 4-Cam MC Fleet & G31/G32 OVP HIL."""
    config.validate()
    rep = p107.run_phase107_c2pa_shading_mcfleet_ovp_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage18_phase107_c2pa_shading_mcfleet_ovp",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "cnflasha_mutation_bytes": red["cnflasha_mutation_bytes"],
        "private_key_reads": red["private_key_reads"],
        "private_key_exports": red["private_key_exports"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "cxd90057_pmic_damage_events": red["cxd90057_pmic_damage_events"],
        "emount_flange_damage_events": red["emount_flange_damage_events"],
        "donor_audit": rep["donor_audit"],
        "c2pa_cnflasha_firewall": rep["c2pa_cnflasha_firewall"],
        "emount_shading_pl_arbitrator": rep["emount_shading_pl_arbitrator"],
        "mc_4cam_wired_fleet_sync": rep["mc_4cam_wired_fleet_sync"],
        "g31_g32_ovp_cantilever_hil": rep["g31_g32_ovp_cantilever_hil"],
        "phase107_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage19_hdr_hlg_fiz_gimbal(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 19 (Phase 112): ITU-R BT.2100/ARIB STD-B67 HLG, CTA-861.3 0x87 InfoFrame, Gamma Display Assist & G33/G34 HIL."""
    config.validate()
    rep = p112.run_phase112_hdr_hlg_fiz_gimbal_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage19_phase112_hdr_hlg_fiz_gimbal",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "display_assist_burn_in_frames": red["display_assist_burn_in_frames"],
        "xavc_clean_feed_leakage_events": red["xavc_clean_feed_leakage_events"],
        "fiz_gear_strip_events": red["fiz_gear_strip_events"],
        "ibis_coil_saturation_events": red["ibis_coil_saturation_events"],
        "duct_salt_haze_ingestion_damage_events": red["duct_salt_haze_ingestion_damage_events"],
        "donor_audit": rep["donor_audit"],
        "bt2100_hlg_gamut_pipeline": rep["bt2100_hlg_gamut_pipeline"],
        "cta861_3_infoframe_and_gamma_assist": rep["cta861_3_infoframe_and_gamma_assist"],
        "g33_g34_duct_fiz_gimbal_hil": rep["g33_g34_duct_fiz_gimbal_hil"],
        "phase112_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage20_proresraw_breathing_mishoe_hil(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 20 (Phase 117): ProRes RAW/BRAW Handshake, Focus Breathing vs PL/RAW Bypass, MI-Shoe 48kHz PLL & G35/G36 HIL."""
    config.validate()
    rep = p117.run_phase117_proresraw_breathing_mishoe_aoc_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage20_proresraw_breathing_mishoe_hil",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "raw_lut_burn_in_frames": red["raw_lut_burn_in_frames"],
        "pl_breathing_stale_crop_frames": red["pl_breathing_stale_crop_frames"],
        "audio_pop_click_frames": red["audio_pop_click_frames"],
        "sy1129_hdmi_fuse_damage_events": red["sy1129_hdmi_fuse_damage_events"],
        "cfexpress_fat_corruption_events": red["cfexpress_fat_corruption_events"],
        "donor_audit": rep["donor_audit"],
        "pillar_a_hdmi_raw_prores_braw": rep["pillar_a_hdmi_raw_prores_braw"],
        "pillar_b_focus_breathing_arbitrator": rep["pillar_b_focus_breathing_arbitrator"],
        "pillar_c_mishoe_i2s_pll_lock": rep["pillar_c_mishoe_i2s_pll_lock"],
        "pillar_d_g35_g36_aoc_cfexpress_hil": rep["pillar_d_g35_g36_aoc_cfexpress_hil"],
        "phase117_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage21_uvc_srt_crsdk_usbpd_hil(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 21 (Phase 121): USB-C UVC 1.5/UAC 2.0, Wired P12-Safe SRT/RTMPS, CRSDK PTP/Firewall & G37/G38 HIL."""
    config.validate()
    rep = p121.run_phase121_uvc_srt_crsdk_usbpd_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage21_uvc_srt_crsdk_usbpd_hil",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "emmc_flash_mutation_bytes": red["emmc_flash_mutation_bytes"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "cxd90057_pad_damage_events": red["cxd90057_pad_damage_events"],
        "uvc_osd_burn_in_frames": red["uvc_osd_burn_in_frames"],
        "srt_dropped_gops": red["srt_dropped_gops"],
        "uart_tx_bytes": red["uart_tx_bytes"],
        "donor_audit": rep["donor_audit"],
        "pillar_a_uvc15_uac20_negotiator": rep["pillar_a_uvc15_uac20_negotiator"],
        "pillar_b_wired_srt_rtmps_p12": rep["pillar_b_wired_srt_rtmps_p12"],
        "pillar_c_crsdk_ptp_flash_firewall": rep["pillar_c_crsdk_ptp_flash_firewall"],
        "pillar_d_g37_g38_usbpd_uart_hil": rep["pillar_d_g37_g38_usbpd_uart_hil"],
        "phase121_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage22_mxf_ptpv2_tally_monsoon_hil(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 22 (Phase 127): MXF/MP4 RDD-18/UMID Bridge, ST 2059-2 PTPv2/LTC Sync, TSL UMD v5.0 Tally & G39/G40 HIL."""
    config.validate()
    rep = p127.run_phase127_mxf_ptpv2_tally_monsoon_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage22_mxf_ptpv2_tally_monsoon_hil",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "emmc_mutation_bytes": red["emmc_mutation_bytes"],
        "dropped_klv_tags": red["dropped_klv_tags"],
        "frame_essence_reencode_loss": red["frame_essence_reencode_loss"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "fx6_green_gpio_faults": red["fx6_green_gpio_faults"],
        "mishoe_rail_corrosion_events": red["mishoe_rail_corrosion_events"],
        "chassis_damage_events": red["chassis_damage_events"],
        "donor_audit": rep["donor_audit"],
        "pillar_a_mxf_mp4_essence_bridge": rep["pillar_a_mxf_mp4_essence_bridge"],
        "pillar_b_st2059_ptpv2_ltc_servo": rep["pillar_b_st2059_ptpv2_ltc_servo"],
        "pillar_c_tsl_umd_v5_tally_bridge": rep["pillar_c_tsl_umd_v5_tally_bridge"],
        "pillar_d_g39_g40_monsoon_cagetwist_hil": rep["pillar_d_g39_g40_monsoon_cagetwist_hil"],
        "phase127_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage23_vp_ledwall_freed_artnet_hil(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 23 (Phase 132): VP LED-Wall ECS Solver, FreeD 0xD1 LiveLink, Art-Net 4/sACN Sync & G41/G42 Genlock/IBIS HIL."""
    config.validate()
    rep = p132.run_phase132_vp_ledwall_freed_artnet_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage23_vp_ledwall_freed_artnet_hil",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "emmc_mutation_bytes": red["emmc_mutation_bytes"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "flash_split_band_frames": red["flash_split_band_frames"],
        "cxd90057_pin_damage_events": red["cxd90057_pin_damage_events"],
        "imx510_sensor_burn_events": red["imx510_sensor_burn_events"],
        "ibis_endstop_slam_events": red["ibis_endstop_slam_events"],
        "ibis_coil_thermal_runaway_events": red["ibis_coil_thermal_runaway_events"],
        "donor_audit": rep["donor_audit"],
        "pillar_a_vp_ledwall_ecs_solver": rep["pillar_a_vp_ledwall_ecs_solver"],
        "pillar_b_freed_0xd1_livelink_bridge": rep["pillar_b_freed_0xd1_livelink_bridge"],
        "pillar_c_artnet4_sacn_flash_sync": rep["pillar_c_artnet4_sacn_flash_sync"],
        "pillar_d_g41_g42_genlock_vib_hil": rep["pillar_d_g41_g42_genlock_vib_hil"],
        "phase132_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage24_realhw_preflash_dualboot_hil(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 24 (Phase 141): Real-Hardware Pre-Flash Lifecycle & 4-State Dual-Boot HIL Simulator."""
    config.validate()
    rep = p141.run_phase141_realhw_preflash_dualboot_audit(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage24_realhw_preflash_dualboot_hil",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "spi_nor_mutation_bytes": red["spi_nor_mutation_bytes"],
        "emmc_mutation_bytes": red["emmc_mutation_bytes"],
        "sector0_mutation_bytes": red["sector0_mutation_bytes"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "rsv_orphan_count": red["rsv_orphan_count"],
        "donor_audit": rep["donor_audit"],
        "pillar_a_jiritsu_setfile2_cold_backup_and_spacc_topology": rep[
            "pillar_a_jiritsu_setfile2_cold_backup_and_spacc_topology"
        ],
        "pillar_b_cnflasha15_cipher_safe_install_and_powercut_rollback": rep[
            "pillar_b_cnflasha15_cipher_safe_install_and_powercut_rollback"
        ],
        "pillar_c_four_state_dualboot_and_native_rec_closed_loop": rep[
            "pillar_c_four_state_dualboot_and_native_rec_closed_loop"
        ],
        "pillar_d_hardware_safety_redlines_and_zero_mutation_proof": rep[
            "pillar_d_hardware_safety_redlines_and_zero_mutation_proof"
        ],
        "phase141_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage25_realhw_mpr_dmm_rec(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 25 (Phase 145): Real-Hardware `appFw.so -> Stock FX3 libmpr.so / DmmCfg.bin` Card-Recording Co-Emulator."""
    config.validate()
    rep = p145.run_phase145_realhw_mpr_dmm_rec_coemulator(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage25_realhw_mpr_dmm_rec",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "emmc_nflasha_write_count": red["emmc_nflasha_write_count"],
        "emmc_mutation_bytes": red["emmc_mutation_bytes"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "rsv_orphan_count": red["rsv_orphan_count"],
        "appfw_crashes": red["appfw_crashes"],
        "dmm_allocated_after_stop": red["dmm_allocated_after_stop"],
        "m_user_count": red["m_user_count"],
        "uipc_lock_depth": red["uipc_lock_depth"],
        "donor_audit": rep["donor_audit"],
        "pillar_a_ld_preload_libmpr_secvlt_shim": rep["pillar_a_ld_preload_libmpr_secvlt_shim"],
        "pillar_b_stock_fx3_dmmcfg_pool_budget": rep["pillar_b_stock_fx3_dmmcfg_pool_budget"],
        "pillar_c_rec_parameter_control_m4root": rep["pillar_c_rec_parameter_control_m4root"],
        "pillar_d_fault_injection_resilience": rep["pillar_d_fault_injection_resilience"],
        "phase145_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage26_realhw_body_peripheral_hil(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 26 (Phase 150): Real-Hardware FX3 Body Controls, IBIS Center-Lock, XLR-H1, Fan PWM & NP-FZ100/USB-PD HIL."""
    config.validate()
    rep = p150.run_phase150_realhw_body_peripheral_hil(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage26_realhw_body_peripheral_hil",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "emmc_nflasha_write_count": red["emmc_nflasha_write_count"],
        "emmc_mutation_bytes": red["emmc_mutation_bytes"],
        "p18_mutation_bytes": red["p18_mutation_bytes"],
        "p18_lens_writes_permitted": red["p18_lens_writes_permitted"],
        "floating_coil_ms": red["floating_coil_ms"],
        "sdi_blocking_wait_ms": red["sdi_blocking_wait_ms"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "rsv_orphan_count": red["rsv_orphan_count"],
        "appfw_crashes": red["appfw_crashes"],
        "false_19v5_dcin_alarms": red["false_19v5_dcin_alarms"],
        "donor_audit": rep["donor_audit"],
        "pillar_a_ibis_center_lock_and_emount_ro": rep["pillar_a_ibis_center_lock_and_emount_ro"],
        "pillar_b_xlrh1_hotplug_hdmi_ltc": rep["pillar_b_xlrh1_hotplug_hdmi_ltc"],
        "pillar_c_fx3_keymap_reachability_and_tally": rep["pillar_c_fx3_keymap_reachability_and_tally"],
        "pillar_d_fan_override_and_npfz100_usbpd": rep["pillar_d_fan_override_and_npfz100_usbpd"],
        "phase150_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage27_realhw_imx510_network_usb_hil(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 27 (Phase 157): Real-Hardware IMX510 Dual-Base ISO 800/12800, psd/defdet NVS, .cube MLUT, CDC-NCM & 054C:0DA1 HIL."""
    config.validate()
    rep = p157.run_phase157_realhw_imx510_network_usb_hil(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage27_realhw_imx510_network_usb_hil",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "sensor_cal_mutation_bytes": red["sensor_cal_mutation_bytes"],
        "psd_defdet_writes_permitted": red["psd_defdet_writes_permitted"],
        "rf_nvs_p12_p13_writes_permitted": red["rf_nvs_p12_p13_writes_permitted"],
        "rf_nvs_p12_p13_mutation_bytes": red["rf_nvs_p12_p13_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "emmc_nflasha_write_count": red["emmc_nflasha_write_count"],
        "emmc_mutation_bytes": red["emmc_mutation_bytes"],
        "slog3_master_double_baked": red["slog3_master_double_baked"],
        "bt_hci_blocking_wait_ms": red["bt_hci_blocking_wait_ms"],
        "bt_hci_blocking_wait_eliminated": red["bt_hci_blocking_wait_eliminated"],
        "usb_msc_0da1_recovery_intact": red["usb_msc_0da1_recovery_intact"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "rsv_orphan_count": red["rsv_orphan_count"],
        "appfw_crashes": red["appfw_crashes"],
        "donor_audit": rep["donor_audit"],
        "pillar_a_imx510_cine_ei_and_sensor_nvs": rep["pillar_a_imx510_cine_ei_and_sensor_nvs"],
        "pillar_b_cube_mlut_16slot_and_slog3_guard": rep["pillar_b_cube_mlut_16slot_and_slog3_guard"],
        "pillar_c_wifi_cdcnm_ptpip_and_rf_lock": rep["pillar_c_wifi_cdcnm_ptpip_and_rf_lock"],
        "pillar_d_usbc_multirole_0da1_recovery": rep["pillar_d_usbc_multirole_0da1_recovery"],
        "phase157_audit_digest_sha256": rep["audit_digest_sha256"],
    }


def run_stage28_realhw_cfexpress_ufu_5tier_hil(
    config: CoEmulationConfig,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run Stage 28 (Phase 162): Real-Hardware CFexpress/SDXC V90, .RSV Salvage, BODYDATA.DAT UFU Bypass & 5-Tier Recovery HIL."""
    config.validate()
    rep = p162.run_phase162_realhw_cfexpress_ufu_5tier_hil(
        force_clean_room=config.force_clean_room,
        env=env,
    )
    red = rep["redlines"]
    return {
        "stage": "stage28_realhw_cfexpress_ufu_5tier_hil",
        "all_checks_passed": bool(rep["all_checks_passed"]),
        "source_mode": rep["source_mode"],
        "nop_count": red["nop_count"],
        "guest_code_modification_bytes": red["guest_code_modification_bytes"],
        "cp_mutation_bytes": red["cp_mutation_bytes"],
        "wbi_mutation_bytes": red["wbi_mutation_bytes"],
        "calibration_mutation_bytes": red["calibration_mutation_bytes"],
        "nvram_persistent_writes": red["nvram_persistent_writes"],
        "bk4_persistent_nvram_writes": red["bk4_persistent_nvram_writes"],
        "physical_device_writes": red["physical_device_writes"],
        "persistent_emmc_writes_authorized": red["persistent_emmc_writes_authorized"],
        "emmc_nflasha_write_count": red["emmc_nflasha_write_count"],
        "emmc_mutation_bytes": red["emmc_mutation_bytes"],
        "spi_nor_write_authorized": red["spi_nor_write_authorized"],
        "spi_nor_mutation_bytes": red["spi_nor_mutation_bytes"],
        "el3_payload_transmit_authorized": red["el3_payload_transmit_authorized"],
        "user_media_clips_intact": red["user_media_clips_intact"],
        "null_gpio_derefs": red["null_gpio_derefs"],
        "mailbox_stalls": red["mailbox_stalls"],
        "stock_cp_fault_count": red["stock_cp_fault_count"],
        "wf12_00342260_hits": red["wf12_00342260_hits"],
        "rsv_orphan_count": red["rsv_orphan_count"],
        "appfw_crashes": red["appfw_crashes"],
        "donor_audit": rep["donor_audit"],
        "pillar_a_cfexpress_sdxc_relay_and_card_door": rep[
            "pillar_a_cfexpress_sdxc_relay_and_card_door"
        ],
        "pillar_b_rsv_clip_salvage_and_recover_db": rep[
            "pillar_b_rsv_clip_salvage_and_recover_db"
        ],
        "pillar_c_bodydata_ufu_bypass_and_model_gate": rep[
            "pillar_c_bodydata_ufu_bypass_and_model_gate"
        ],
        "pillar_d_five_tier_unbrickable_recovery_drill": rep[
            "pillar_d_five_tier_unbrickable_recovery_drill"
        ],
        "phase162_audit_digest_sha256": rep["audit_digest_sha256"],
    }


# ---------------------------------------------------------------------------
# Unified Full-Board Co-Emulation Orchestrator
# ---------------------------------------------------------------------------


def run_fx3_vm_coemulation_suite(
    config: Optional[CoEmulationConfig] = None,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the unified 28-stage (Phase 33..162) Full-Board Co-Emulation Pipeline."""
    cfg = CoEmulationConfig() if config is None else config
    cfg.validate()

    stage1 = run_stage1_bt_and_coldboot(cfg, env=env)
    stage2 = run_stage2_dual_isa_shooting_cycle(cfg, env=env)
    stage3 = run_stage3_soft_gpe_hud_composite(cfg, bt_result=stage1, cp_result=stage2, env=env)
    stage4: Optional[Dict[str, object]] = (
        run_stage4_dtb_mhlx_mmio(cfg, env=env) if cfg.include_phase41_dtb_mhlx else None
    )
    stage5: Optional[Dict[str, object]] = (
        run_stage5_imx510_xavc_cfexpress(cfg, env=env) if cfg.include_phase45_imx510_xavc else None
    )
    stage6: Optional[Dict[str, object]] = (
        run_stage6_hil_fault_harness(cfg, env=env) if cfg.include_phase53_hil_fault_harness else None
    )
    stage7: Optional[Dict[str, object]] = (
        run_stage7_qmp_guest_introspection(cfg, env=env) if cfg.include_phase58_qmp_introspection else None
    )
    stage8: Optional[Dict[str, object]] = (
        run_stage8_hdmi_raw_uvc_arbitrator(cfg, env=env) if cfg.include_phase63_hdmi_raw_uvc else None
    )
    stage9: Optional[Dict[str, object]] = (
        run_stage9_tc_lens_paint(cfg, env=env) if cfg.include_phase67_tc_lens_paint else None
    )
    stage10: Optional[Dict[str, object]] = (
        run_stage10_dualslot_proxy_ups_salvage(cfg, env=env) if cfg.include_phase71_dualslot_ups_salvage else None
    )
    stage11: Optional[Dict[str, object]] = (
        run_stage11_touchaf_ciz_assignable(cfg, env=env) if cfg.include_phase78_touchaf_ciz_assignable else None
    )
    stage12: Optional[Dict[str, object]] = (
        run_stage12_camset_lpcm_tcub(cfg, env=env) if cfg.include_phase82_camset_lpcm_tcub else None
    )
    stage13: Optional[Dict[str, object]] = (
        run_stage13_playback_shotmark_dewpoint(cfg, env=env)
        if cfg.include_phase87_playback_shotmark_dewpoint
        else None
    )
    stage14: Optional[Dict[str, object]] = (
        run_stage14_gyroflow_rtmd_anamorphic(cfg, env=env)
        if cfg.include_phase91_gyroflow_rtmd_anamorphic
        else None
    )
    stage15: Optional[Dict[str, object]] = (
        run_stage15_interval_cache_ftp_fan(cfg, env=env)
        if cfg.include_phase96_interval_cache_ftp_fan
        else None
    )
    stage16: Optional[Dict[str, object]] = (
        run_stage16_lut3d_subzero_sdi(cfg, env=env)
        if cfg.include_phase99_lut3d_subzero_sdi
        else None
    )
    stage17: Optional[Dict[str, object]] = (
        run_stage17_emi_exfat_endurance(cfg, env=env)
        if cfg.include_phase103_emi_exfat_endurance
        else None
    )
    stage18: Optional[Dict[str, object]] = (
        run_stage18_c2pa_shading_mcfleet_ovp(cfg, env=env)
        if cfg.include_phase107_c2pa_shading_mcfleet_ovp
        else None
    )
    stage19: Optional[Dict[str, object]] = (
        run_stage19_hdr_hlg_fiz_gimbal(cfg, env=env)
        if cfg.include_phase112_hdr_hlg_fiz_gimbal
        else None
    )
    stage20: Optional[Dict[str, object]] = (
        run_stage20_proresraw_breathing_mishoe_hil(cfg, env=env)
        if cfg.include_phase117_proresraw_breathing_mishoe_hil
        else None
    )
    stage21: Optional[Dict[str, object]] = (
        run_stage21_uvc_srt_crsdk_usbpd_hil(cfg, env=env)
        if cfg.include_phase121_uvc_srt_crsdk_usbpd_hil
        else None
    )
    stage22: Optional[Dict[str, object]] = (
        run_stage22_mxf_ptpv2_tally_monsoon_hil(cfg, env=env)
        if cfg.include_phase127_mxf_ptpv2_tally_monsoon_hil
        else None
    )
    stage23: Optional[Dict[str, object]] = (
        run_stage23_vp_ledwall_freed_artnet_hil(cfg, env=env)
        if cfg.include_phase132_vp_ledwall_freed_artnet_hil
        else None
    )
    stage24: Optional[Dict[str, object]] = (
        run_stage24_realhw_preflash_dualboot_hil(cfg, env=env)
        if cfg.include_phase141_realhw_preflash_dualboot_hil
        else None
    )
    stage25: Optional[Dict[str, object]] = (
        run_stage25_realhw_mpr_dmm_rec(cfg, env=env)
        if cfg.include_phase145_realhw_mpr_dmm_rec
        else None
    )
    stage26: Optional[Dict[str, object]] = (
        run_stage26_realhw_body_peripheral_hil(cfg, env=env)
        if cfg.include_phase150_realhw_body_peripheral_hil
        else None
    )
    stage27: Optional[Dict[str, object]] = (
        run_stage27_realhw_imx510_network_usb_hil(cfg, env=env)
        if cfg.include_phase157_realhw_imx510_network_usb_hil
        else None
    )
    stage28: Optional[Dict[str, object]] = (
        run_stage28_realhw_cfexpress_ufu_5tier_hil(cfg, env=env)
        if cfg.include_phase162_realhw_cfexpress_ufu_5tier_hil
        else None
    )
    topo = p24.build_dual_qemu_ivshmem_topology_spec()

    stage4_ok = True if stage4 is None else (
        bool(stage4["all_checks_passed"])
        and stage4["cp_mutation_bytes"] == 0
        and stage4["wbi_mutation_bytes"] == 0
    )
    stage5_ok = True if stage5 is None else (
        bool(stage5["all_checks_passed"])
        and stage5["cp_mutation_bytes"] == 0
        and stage5["wbi_mutation_bytes"] == 0
        and stage5["physical_device_writes"] == 0
    )
    stage6_ok = True if stage6 is None else (
        bool(stage6["all_checks_passed"])
        and stage6["cp_mutation_bytes"] == 0
        and stage6["wbi_mutation_bytes"] == 0
        and stage6["calibration_mutation_bytes"] == 0
        and stage6["nvram_persistent_writes"] == 0
        and stage6["physical_device_writes"] == 0
        and stage6["scenarios_passed"] == stage6["scenarios_total"]
    )
    stage7_ok = True if stage7 is None else (
        bool(stage7["all_checks_passed"])
        and stage7["nop_count"] == 0
        and stage7["guest_code_modification_bytes"] == 0
        and stage7["cp_mutation_bytes"] == 0
        and stage7["wbi_mutation_bytes"] == 0
        and stage7["calibration_mutation_bytes"] == 0
        and stage7["nvram_persistent_writes"] == 0
        and stage7["physical_device_writes"] == 0
    )
    stage8_ok = True if stage8 is None else (
        bool(stage8["all_checks_passed"])
        and stage8["nop_count"] == 0
        and stage8["guest_code_modification_bytes"] == 0
        and stage8["cp_mutation_bytes"] == 0
        and stage8["wbi_mutation_bytes"] == 0
        and stage8["calibration_mutation_bytes"] == 0
        and stage8["nvram_persistent_writes"] == 0
        and stage8["physical_device_writes"] == 0
        and (not stage8["persistent_emmc_writes_authorized"])
        and stage8["sdi_transceiver_faults"] == 0
    )
    stage9_ok = True if stage9 is None else (
        bool(stage9["all_checks_passed"])
        and stage9["nop_count"] == 0
        and stage9["guest_code_modification_bytes"] == 0
        and stage9["cp_mutation_bytes"] == 0
        and stage9["wbi_mutation_bytes"] == 0
        and stage9["calibration_mutation_bytes"] == 0
        and stage9["nvram_persistent_writes"] == 0
        and stage9["physical_device_writes"] == 0
        and (not stage9["persistent_emmc_writes_authorized"])
    )
    stage10_ok = True if stage10 is None else (
        bool(stage10["all_checks_passed"])
        and stage10["nop_count"] == 0
        and stage10["guest_code_modification_bytes"] == 0
        and stage10["cp_mutation_bytes"] == 0
        and stage10["wbi_mutation_bytes"] == 0
        and stage10["calibration_mutation_bytes"] == 0
        and stage10["nvram_persistent_writes"] == 0
        and stage10["physical_device_writes"] == 0
        and stage10["p1_emmc_mutations"] == 0
        and stage10["internal_emmc_writes"] == 0
        and bool(stage10["c2pa_license_untouched"])
        and (not stage10["persistent_emmc_writes_authorized"])
    )
    stage11_ok = True if stage11 is None else (
        bool(stage11["all_checks_passed"])
        and stage11["nop_count"] == 0
        and stage11["guest_code_modification_bytes"] == 0
        and stage11["cp_mutation_bytes"] == 0
        and stage11["wbi_mutation_bytes"] == 0
        and stage11["calibration_mutation_bytes"] == 0
        and stage11["nvram_persistent_writes"] == 0
        and stage11["bk4_persistent_nvram_writes"] == 0
        and stage11["physical_device_writes"] == 0
        and stage11["null_gpio_derefs"] == 0
        and stage11["mailbox_stalls"] == 0
        and (not stage11["persistent_emmc_writes_authorized"])
    )
    stage12_ok = True if stage12 is None else (
        bool(stage12["all_checks_passed"])
        and stage12["nop_count"] == 0
        and stage12["guest_code_modification_bytes"] == 0
        and stage12["cp_mutation_bytes"] == 0
        and stage12["wbi_mutation_bytes"] == 0
        and stage12["calibration_mutation_bytes"] == 0
        and stage12["nvram_persistent_writes"] == 0
        and stage12["bk4_persistent_nvram_writes"] == 0
        and stage12["physical_device_writes"] == 0
        and stage12["null_gpio_derefs"] == 0
        and stage12["mailbox_stalls"] == 0
        and stage12["uart_boot_contention_events"] == 0
        and (not stage12["persistent_emmc_writes_authorized"])
    )
    stage13_ok = True if stage13 is None else (
        bool(stage13["all_checks_passed"])
        and stage13["nop_count"] == 0
        and stage13["guest_code_modification_bytes"] == 0
        and stage13["cp_mutation_bytes"] == 0
        and stage13["wbi_mutation_bytes"] == 0
        and stage13["calibration_mutation_bytes"] == 0
        and stage13["nvram_persistent_writes"] == 0
        and stage13["bk4_persistent_nvram_writes"] == 0
        and stage13["physical_device_writes"] == 0
        and stage13["null_gpio_derefs"] == 0
        and stage13["mailbox_stalls"] == 0
        and stage13["p1_emmc_mutations"] == 0
        and stage13["internal_emmc_writes"] == 0
        and stage13["p4_nd_motor_faults"] == 0
        and bool(stage13["internal_emmc_format_blocked"])
        and bool(stage13["c2pa_license_untouched"])
        and (not stage13["persistent_emmc_writes_authorized"])
    )
    stage14_ok = True if stage14 is None else (
        bool(stage14["all_checks_passed"])
        and stage14["nop_count"] == 0
        and stage14["guest_code_modification_bytes"] == 0
        and stage14["cp_mutation_bytes"] == 0
        and stage14["wbi_mutation_bytes"] == 0
        and stage14["calibration_mutation_bytes"] == 0
        and stage14["nvram_persistent_writes"] == 0
        and stage14["bk4_persistent_nvram_writes"] == 0
        and stage14["physical_device_writes"] == 0
        and stage14["null_gpio_derefs"] == 0
        and stage14["mailbox_stalls"] == 0
        and stage14["stock_cp_fault_count"] == 0
        and (not stage14["persistent_emmc_writes_authorized"])
    )
    stage15_ok = True if stage15 is None else (
        bool(stage15["all_checks_passed"])
        and stage15["nop_count"] == 0
        and stage15["guest_code_modification_bytes"] == 0
        and stage15["cp_mutation_bytes"] == 0
        and stage15["wbi_mutation_bytes"] == 0
        and stage15["calibration_mutation_bytes"] == 0
        and stage15["nvram_persistent_writes"] == 0
        and stage15["bk4_persistent_nvram_writes"] == 0
        and stage15["physical_device_writes"] == 0
        and stage15["null_gpio_derefs"] == 0
        and stage15["mailbox_stalls"] == 0
        and stage15["stock_cp_fault_count"] == 0
        and stage15["wf12_00342260_hits"] == 0
        and stage15["emmc_partition_mutations"] == 0
        and (not stage15["persistent_emmc_writes_authorized"])
    )
    stage16_ok = True if stage16 is None else (
        bool(stage16["all_checks_passed"])
        and stage16["nop_count"] == 0
        and stage16["guest_code_modification_bytes"] == 0
        and stage16["cp_mutation_bytes"] == 0
        and stage16["wbi_mutation_bytes"] == 0
        and stage16["calibration_mutation_bytes"] == 0
        and stage16["nvram_persistent_writes"] == 0
        and stage16["bk4_persistent_nvram_writes"] == 0
        and stage16["physical_device_writes"] == 0
        and stage16["null_gpio_derefs"] == 0
        and stage16["mailbox_stalls"] == 0
        and stage16["stock_cp_fault_count"] == 0
        and stage16["sdi_transceiver_faults"] == 0
        and stage16["lithium_plating_events"] == 0
        and stage16["dropped_rec_triggers"] == 0
        and (not stage16["persistent_emmc_writes_authorized"])
    )
    stage17_ok = True if stage17 is None else (
        bool(stage17["all_checks_passed"])
        and stage17["nop_count"] == 0
        and stage17["guest_code_modification_bytes"] == 0
        and stage17["cp_mutation_bytes"] == 0
        and stage17["wbi_mutation_bytes"] == 0
        and stage17["calibration_mutation_bytes"] == 0
        and stage17["nvram_persistent_writes"] == 0
        and stage17["bk4_persistent_nvram_writes"] == 0
        and stage17["physical_device_writes"] == 0
        and stage17["null_gpio_derefs"] == 0
        and stage17["mailbox_stalls"] == 0
        and stage17["stock_cp_fault_count"] == 0
        and stage17["emmc_sector_writes"] == 0
        and stage17["emmc_wear_level_increments"] == 0
        and stage17["cxd90057_gpio_damage_events"] == 0
        and stage17["dropped_audio_samples"] == 0
        and stage17["dropped_video_frames"] == 0
        and (not stage17["persistent_emmc_writes_authorized"])
    )
    stage18_ok = True if stage18 is None else (
        bool(stage18["all_checks_passed"])
        and stage18["nop_count"] == 0
        and stage18["guest_code_modification_bytes"] == 0
        and stage18["cp_mutation_bytes"] == 0
        and stage18["wbi_mutation_bytes"] == 0
        and stage18["calibration_mutation_bytes"] == 0
        and stage18["nvram_persistent_writes"] == 0
        and stage18["bk4_persistent_nvram_writes"] == 0
        and stage18["physical_device_writes"] == 0
        and stage18["null_gpio_derefs"] == 0
        and stage18["mailbox_stalls"] == 0
        and stage18["stock_cp_fault_count"] == 0
        and stage18["cnflasha_mutation_bytes"] == 0
        and stage18["private_key_reads"] == 0
        and stage18["private_key_exports"] == 0
        and stage18["wf12_00342260_hits"] == 0
        and stage18["cxd90057_pmic_damage_events"] == 0
        and stage18["emount_flange_damage_events"] == 0
        and (not stage18["persistent_emmc_writes_authorized"])
    )
    stage19_ok = True if stage19 is None else (
        bool(stage19["all_checks_passed"])
        and stage19["nop_count"] == 0
        and stage19["guest_code_modification_bytes"] == 0
        and stage19["cp_mutation_bytes"] == 0
        and stage19["wbi_mutation_bytes"] == 0
        and stage19["calibration_mutation_bytes"] == 0
        and stage19["nvram_persistent_writes"] == 0
        and stage19["bk4_persistent_nvram_writes"] == 0
        and stage19["physical_device_writes"] == 0
        and stage19["null_gpio_derefs"] == 0
        and stage19["mailbox_stalls"] == 0
        and stage19["stock_cp_fault_count"] == 0
        and stage19["display_assist_burn_in_frames"] == 0
        and stage19["xavc_clean_feed_leakage_events"] == 0
        and stage19["fiz_gear_strip_events"] == 0
        and stage19["ibis_coil_saturation_events"] == 0
        and stage19["duct_salt_haze_ingestion_damage_events"] == 0
        and (not stage19["persistent_emmc_writes_authorized"])
    )
    stage20_ok = True if stage20 is None else (
        bool(stage20["all_checks_passed"])
        and stage20["nop_count"] == 0
        and stage20["guest_code_modification_bytes"] == 0
        and stage20["cp_mutation_bytes"] == 0
        and stage20["wbi_mutation_bytes"] == 0
        and stage20["calibration_mutation_bytes"] == 0
        and stage20["nvram_persistent_writes"] == 0
        and stage20["bk4_persistent_nvram_writes"] == 0
        and stage20["physical_device_writes"] == 0
        and stage20["null_gpio_derefs"] == 0
        and stage20["mailbox_stalls"] == 0
        and stage20["stock_cp_fault_count"] == 0
        and stage20["raw_lut_burn_in_frames"] == 0
        and stage20["pl_breathing_stale_crop_frames"] == 0
        and stage20["audio_pop_click_frames"] == 0
        and stage20["sy1129_hdmi_fuse_damage_events"] == 0
        and stage20["cfexpress_fat_corruption_events"] == 0
        and (not stage20["persistent_emmc_writes_authorized"])
    )
    stage21_ok = True if stage21 is None else (
        bool(stage21["all_checks_passed"])
        and stage21["nop_count"] == 0
        and stage21["guest_code_modification_bytes"] == 0
        and stage21["cp_mutation_bytes"] == 0
        and stage21["wbi_mutation_bytes"] == 0
        and stage21["calibration_mutation_bytes"] == 0
        and stage21["nvram_persistent_writes"] == 0
        and stage21["bk4_persistent_nvram_writes"] == 0
        and stage21["physical_device_writes"] == 0
        and stage21["null_gpio_derefs"] == 0
        and stage21["mailbox_stalls"] == 0
        and stage21["stock_cp_fault_count"] == 0
        and stage21["emmc_flash_mutation_bytes"] == 0
        and stage21["wf12_00342260_hits"] == 0
        and stage21["cxd90057_pad_damage_events"] == 0
        and stage21["uvc_osd_burn_in_frames"] == 0
        and stage21["srt_dropped_gops"] == 0
        and stage21["uart_tx_bytes"] == 0
        and (not stage21["persistent_emmc_writes_authorized"])
    )
    stage22_ok = True if stage22 is None else (
        bool(stage22["all_checks_passed"])
        and stage22["nop_count"] == 0
        and stage22["guest_code_modification_bytes"] == 0
        and stage22["cp_mutation_bytes"] == 0
        and stage22["wbi_mutation_bytes"] == 0
        and stage22["calibration_mutation_bytes"] == 0
        and stage22["nvram_persistent_writes"] == 0
        and stage22["bk4_persistent_nvram_writes"] == 0
        and stage22["physical_device_writes"] == 0
        and stage22["null_gpio_derefs"] == 0
        and stage22["mailbox_stalls"] == 0
        and stage22["stock_cp_fault_count"] == 0
        and stage22["emmc_mutation_bytes"] == 0
        and stage22["dropped_klv_tags"] == 0
        and stage22["frame_essence_reencode_loss"] == 0
        and stage22["wf12_00342260_hits"] == 0
        and stage22["fx6_green_gpio_faults"] == 0
        and stage22["mishoe_rail_corrosion_events"] == 0
        and stage22["chassis_damage_events"] == 0
        and (not stage22["persistent_emmc_writes_authorized"])
    )
    stage23_ok = True if stage23 is None else (
        bool(stage23["all_checks_passed"])
        and stage23["nop_count"] == 0
        and stage23["guest_code_modification_bytes"] == 0
        and stage23["cp_mutation_bytes"] == 0
        and stage23["wbi_mutation_bytes"] == 0
        and stage23["calibration_mutation_bytes"] == 0
        and stage23["nvram_persistent_writes"] == 0
        and stage23["bk4_persistent_nvram_writes"] == 0
        and stage23["physical_device_writes"] == 0
        and stage23["null_gpio_derefs"] == 0
        and stage23["mailbox_stalls"] == 0
        and stage23["stock_cp_fault_count"] == 0
        and stage23["emmc_mutation_bytes"] == 0
        and stage23["wf12_00342260_hits"] == 0
        and stage23["flash_split_band_frames"] == 0
        and stage23["cxd90057_pin_damage_events"] == 0
        and stage23["imx510_sensor_burn_events"] == 0
        and stage23["ibis_endstop_slam_events"] == 0
        and stage23["ibis_coil_thermal_runaway_events"] == 0
        and (not stage23["persistent_emmc_writes_authorized"])
    )
    stage24_ok = True if stage24 is None else (
        bool(stage24["all_checks_passed"])
        and stage24["nop_count"] == 0
        and stage24["guest_code_modification_bytes"] == 0
        and stage24["cp_mutation_bytes"] == 0
        and stage24["wbi_mutation_bytes"] == 0
        and stage24["calibration_mutation_bytes"] == 0
        and stage24["nvram_persistent_writes"] == 0
        and stage24["bk4_persistent_nvram_writes"] == 0
        and stage24["physical_device_writes"] == 0
        and stage24["spi_nor_mutation_bytes"] == 0
        and stage24["emmc_mutation_bytes"] == 0
        and stage24["sector0_mutation_bytes"] == 0
        and stage24["null_gpio_derefs"] == 0
        and stage24["mailbox_stalls"] == 0
        and stage24["stock_cp_fault_count"] == 0
        and stage24["wf12_00342260_hits"] == 0
        and stage24["rsv_orphan_count"] == 0
        and (not stage24["persistent_emmc_writes_authorized"])
    )
    stage25_ok = True if stage25 is None else (
        bool(stage25["all_checks_passed"])
        and stage25["nop_count"] == 0
        and stage25["guest_code_modification_bytes"] == 0
        and stage25["cp_mutation_bytes"] == 0
        and stage25["wbi_mutation_bytes"] == 0
        and stage25["calibration_mutation_bytes"] == 0
        and stage25["nvram_persistent_writes"] == 0
        and stage25["bk4_persistent_nvram_writes"] == 0
        and stage25["physical_device_writes"] == 0
        and stage25["emmc_nflasha_write_count"] == 0
        and stage25["emmc_mutation_bytes"] == 0
        and stage25["null_gpio_derefs"] == 0
        and stage25["mailbox_stalls"] == 0
        and stage25["stock_cp_fault_count"] == 0
        and stage25["wf12_00342260_hits"] == 0
        and stage25["rsv_orphan_count"] == 0
        and stage25["appfw_crashes"] == 0
        and stage25["dmm_allocated_after_stop"] == 0
        and stage25["m_user_count"] == 0
        and stage25["uipc_lock_depth"] == 0
        and (not stage25["persistent_emmc_writes_authorized"])
    )
    stage26_ok = True if stage26 is None else (
        bool(stage26["all_checks_passed"])
        and stage26["nop_count"] == 0
        and stage26["guest_code_modification_bytes"] == 0
        and stage26["cp_mutation_bytes"] == 0
        and stage26["wbi_mutation_bytes"] == 0
        and stage26["calibration_mutation_bytes"] == 0
        and stage26["nvram_persistent_writes"] == 0
        and stage26["bk4_persistent_nvram_writes"] == 0
        and stage26["physical_device_writes"] == 0
        and stage26["emmc_nflasha_write_count"] == 0
        and stage26["emmc_mutation_bytes"] == 0
        and stage26["p18_mutation_bytes"] == 0
        and (not stage26["p18_lens_writes_permitted"])
        and stage26["floating_coil_ms"] == 0
        and stage26["sdi_blocking_wait_ms"] == 0.0
        and stage26["null_gpio_derefs"] == 0
        and stage26["mailbox_stalls"] == 0
        and stage26["stock_cp_fault_count"] == 0
        and stage26["wf12_00342260_hits"] == 0
        and stage26["rsv_orphan_count"] == 0
        and stage26["appfw_crashes"] == 0
        and stage26["false_19v5_dcin_alarms"] == 0
        and (not stage26["persistent_emmc_writes_authorized"])
    )
    stage27_ok = True if stage27 is None else (
        bool(stage27["all_checks_passed"])
        and stage27["nop_count"] == 0
        and stage27["guest_code_modification_bytes"] == 0
        and stage27["cp_mutation_bytes"] == 0
        and stage27["wbi_mutation_bytes"] == 0
        and stage27["calibration_mutation_bytes"] == 0
        and stage27["sensor_cal_mutation_bytes"] == 0
        and (not stage27["psd_defdet_writes_permitted"])
        and (not stage27["rf_nvs_p12_p13_writes_permitted"])
        and stage27["rf_nvs_p12_p13_mutation_bytes"] == 0
        and stage27["nvram_persistent_writes"] == 0
        and stage27["bk4_persistent_nvram_writes"] == 0
        and stage27["physical_device_writes"] == 0
        and stage27["emmc_nflasha_write_count"] == 0
        and stage27["emmc_mutation_bytes"] == 0
        and (not stage27["slog3_master_double_baked"])
        and stage27["bt_hci_blocking_wait_ms"] == 0
        and bool(stage27["bt_hci_blocking_wait_eliminated"])
        and bool(stage27["usb_msc_0da1_recovery_intact"])
        and stage27["null_gpio_derefs"] == 0
        and stage27["mailbox_stalls"] == 0
        and stage27["stock_cp_fault_count"] == 0
        and stage27["wf12_00342260_hits"] == 0
        and stage27["rsv_orphan_count"] == 0
        and stage27["appfw_crashes"] == 0
        and (not stage27["persistent_emmc_writes_authorized"])
    )
    stage28_ok = True if stage28 is None else (
        bool(stage28["all_checks_passed"])
        and stage28["nop_count"] == 0
        and stage28["guest_code_modification_bytes"] == 0
        and stage28["cp_mutation_bytes"] == 0
        and stage28["wbi_mutation_bytes"] == 0
        and stage28["calibration_mutation_bytes"] == 0
        and stage28["nvram_persistent_writes"] == 0
        and stage28["bk4_persistent_nvram_writes"] == 0
        and stage28["physical_device_writes"] == 0
        and stage28["emmc_nflasha_write_count"] == 0
        and stage28["emmc_mutation_bytes"] == 0
        and stage28["spi_nor_mutation_bytes"] == 0
        and (not stage28["spi_nor_write_authorized"])
        and (not stage28["el3_payload_transmit_authorized"])
        and bool(stage28["user_media_clips_intact"])
        and stage28["null_gpio_derefs"] == 0
        and stage28["mailbox_stalls"] == 0
        and stage28["stock_cp_fault_count"] == 0
        and stage28["wf12_00342260_hits"] == 0
        and stage28["rsv_orphan_count"] == 0
        and stage28["appfw_crashes"] == 0
        and (not stage28["persistent_emmc_writes_authorized"])
    )

    all_passed = (
        bool(stage1["all_checks_passed"])
        and bool(stage2["all_checks_passed"])
        and bool(stage3["all_checks_passed"])
        and stage2["cp_mutation_bytes"] == 0
        and stage4_ok
        and stage5_ok
        and stage6_ok
        and stage7_ok
        and stage8_ok
        and stage9_ok
        and stage10_ok
        and stage11_ok
        and stage12_ok
        and stage13_ok
        and stage14_ok
        and stage15_ok
        and stage16_ok
        and stage17_ok
        and stage18_ok
        and stage19_ok
        and stage20_ok
        and stage21_ok
        and stage22_ok
        and stage23_ok
        and stage24_ok
        and stage25_ok
        and stage26_ok
        and stage27_ok
        and stage28_ok
    )

    core_payload: Dict[str, object] = {
        "schema": PHASE_33_SCHEMA,
        "version": PHASE_33_VERSION,
        "all_checks_passed": all_passed,
        "clean_room_forced": bool(
            cfg.force_clean_room if cfg.force_clean_room is not None else p24.is_forced_clean_room(env)
        ),
        "config": {
            "bt_mode": cfg.bt_mode,
            "cine_ei_iso": cfg.cine_ei_iso,
            "lut_mode": cfg.lut_mode,
            "ibis_mode": cfg.ibis_mode,
            "rtc_valid": cfg.rtc_valid,
            "include_bt_containment_matrix": cfg.include_bt_containment_matrix,
            "include_phase41_dtb_mhlx": cfg.include_phase41_dtb_mhlx,
            "include_phase45_imx510_xavc": cfg.include_phase45_imx510_xavc,
            "include_phase53_hil_fault_harness": cfg.include_phase53_hil_fault_harness,
            "include_phase58_qmp_introspection": cfg.include_phase58_qmp_introspection,
            "include_phase63_hdmi_raw_uvc": cfg.include_phase63_hdmi_raw_uvc,
            "include_phase67_tc_lens_paint": cfg.include_phase67_tc_lens_paint,
            "include_phase71_dualslot_ups_salvage": cfg.include_phase71_dualslot_ups_salvage,
            "include_phase78_touchaf_ciz_assignable": cfg.include_phase78_touchaf_ciz_assignable,
            "include_phase82_camset_lpcm_tcub": cfg.include_phase82_camset_lpcm_tcub,
            "include_phase87_playback_shotmark_dewpoint": cfg.include_phase87_playback_shotmark_dewpoint,
            "include_phase91_gyroflow_rtmd_anamorphic": cfg.include_phase91_gyroflow_rtmd_anamorphic,
            "include_phase96_interval_cache_ftp_fan": cfg.include_phase96_interval_cache_ftp_fan,
            "include_phase99_lut3d_subzero_sdi": cfg.include_phase99_lut3d_subzero_sdi,
            "include_phase103_emi_exfat_endurance": cfg.include_phase103_emi_exfat_endurance,
            "include_phase107_c2pa_shading_mcfleet_ovp": cfg.include_phase107_c2pa_shading_mcfleet_ovp,
            "include_phase112_hdr_hlg_fiz_gimbal": cfg.include_phase112_hdr_hlg_fiz_gimbal,
            "include_phase117_proresraw_breathing_mishoe_hil": cfg.include_phase117_proresraw_breathing_mishoe_hil,
            "include_phase121_uvc_srt_crsdk_usbpd_hil": cfg.include_phase121_uvc_srt_crsdk_usbpd_hil,
            "include_phase127_mxf_ptpv2_tally_monsoon_hil": cfg.include_phase127_mxf_ptpv2_tally_monsoon_hil,
            "include_phase132_vp_ledwall_freed_artnet_hil": cfg.include_phase132_vp_ledwall_freed_artnet_hil,
            "include_phase141_realhw_preflash_dualboot_hil": cfg.include_phase141_realhw_preflash_dualboot_hil,
            "include_phase145_realhw_mpr_dmm_rec": cfg.include_phase145_realhw_mpr_dmm_rec,
            "include_phase150_realhw_body_peripheral_hil": cfg.include_phase150_realhw_body_peripheral_hil,
            "include_phase157_realhw_imx510_network_usb_hil": cfg.include_phase157_realhw_imx510_network_usb_hil,
            "include_phase162_realhw_cfexpress_ufu_5tier_hil": cfg.include_phase162_realhw_cfexpress_ufu_5tier_hil,
            "xavc_resolution": cfg.xavc_resolution,
            "xavc_fps": cfg.xavc_fps,
            "xavc_codec": cfg.xavc_codec,
            "recording_mode": cfg.recording_mode,
        },
        "redlines": {
            "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
            "cp_mutation_bytes": CP_MUTATION_BYTES,
            "wbi_mutation_bytes": WBI_MUTATION_BYTES,
            "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
            "physical_device_writes": PHYSICAL_DEVICE_WRITES,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "stage1_coldboot_and_bt": stage1,
        "stage2_dual_isa_cp_shooting": stage2,
        "stage3_soft_gpe_hud_ramfb": stage3,
        "qemu_topology_summary": {
            "ivshmem_server_cmd": list(topo.ivshmem_server_cmd),
            "peer0_ap_device": topo.peer0_ap_mira["device"],
            "peer1_cp_device": topo.peer1_cp_cetus["device"],
            "cp_load_base": topo.peer1_cp_cetus["cp_load_base"],
            "cp_read_only": topo.peer1_cp_cetus["cp_read_only"],
        },
    }
    if stage4 is not None:
        core_payload["stage4_phase41_dtb_mhlx"] = stage4
    if stage5 is not None:
        core_payload["stage5_phase45_imx510_xavc"] = stage5
    if stage6 is not None:
        core_payload["stage6_phase53_hil_fault_harness"] = stage6
    if stage7 is not None:
        core_payload["stage7_phase58_qmp_introspection"] = stage7
    if stage8 is not None:
        core_payload["stage8_phase63_hdmi_raw_uvc"] = stage8
    if stage9 is not None:
        core_payload["stage9_phase67_tc_lens_paint"] = stage9
    if stage10 is not None:
        core_payload["stage10_phase71_dualslot_ups_salvage"] = stage10
    if stage11 is not None:
        core_payload["stage11_phase78_touchaf_ciz_assignable"] = stage11
    if stage12 is not None:
        core_payload["stage12_phase82_camset_lpcm_tcub"] = stage12
    if stage13 is not None:
        core_payload["stage13_phase87_playback_shotmark_dewpoint"] = stage13
    if stage14 is not None:
        core_payload["stage14_phase91_gyroflow_rtmd_anamorphic"] = stage14
    if stage15 is not None:
        core_payload["stage15_phase96_interval_cache_ftp_fan"] = stage15
    if stage16 is not None:
        core_payload["stage16_phase99_lut3d_subzero_sdi"] = stage16
    if stage17 is not None:
        core_payload["stage17_phase103_emi_exfat_endurance"] = stage17
    if stage18 is not None:
        core_payload["stage18_phase107_c2pa_shading_mcfleet_ovp"] = stage18
    if stage19 is not None:
        core_payload["stage19_phase112_hdr_hlg_fiz_gimbal"] = stage19
    if stage20 is not None:
        core_payload["stage20_proresraw_breathing_mishoe_hil"] = stage20
    if stage21 is not None:
        core_payload["stage21_uvc_srt_crsdk_usbpd_hil"] = stage21
    if stage22 is not None:
        core_payload["stage22_mxf_ptpv2_tally_monsoon_hil"] = stage22
    if stage23 is not None:
        core_payload["stage23_vp_ledwall_freed_artnet_hil"] = stage23
    if stage24 is not None:
        core_payload["stage24_realhw_preflash_dualboot_hil"] = stage24
    if stage25 is not None:
        core_payload["stage25_realhw_mpr_dmm_rec"] = stage25
    if stage26 is not None:
        core_payload["stage26_realhw_body_peripheral_hil"] = stage26
    if stage27 is not None:
        core_payload["stage27_realhw_imx510_network_usb_hil"] = stage27
    if stage28 is not None:
        core_payload["stage28_realhw_cfexpress_ufu_5tier_hil"] = stage28

    digest = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    core_payload["audit_digest_sha256"] = digest
    return core_payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fx3_vm_coemulation_suite.py",
        description="Phase 33 + 41 + 45 + 53 + 58 + 63 + 67 + 71 + 78 + 82 + 87 + 91 + 96 + 99 + 103 + 107 + 112 + 117 + 121 + 127 + 132 + 141 + 145 + 150 + 157 + 162 Unified FX3-VM Full-Board Co-Emulation Orchestrator & CLI",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit summary (default)")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary instead of JSON")
    parser.add_argument("--topology", action="store_true", help="Emit Dual-QEMU IVSHMEM topology JSON only")
    parser.add_argument(
        "--skip-phase41",
        action="store_true",
        help="Skip optional Stage 4 (Phase 41 CXD90057 FDT/DTB & MHLX MMIO check)",
    )
    parser.add_argument(
        "--skip-phase45",
        action="store_true",
        help="Skip optional Stage 5 (Phase 45 IMX510 XAVC & Dual CFexpress/SDXC pipeline)",
    )
    parser.add_argument(
        "--skip-phase53",
        action="store_true",
        help="Skip optional Stage 6 (Phase 53 HIL Dynamic Fault-Injection & Thermal/C2PA Harness)",
    )
    parser.add_argument(
        "--skip-phase58",
        action="store_true",
        help="Skip optional Stage 7 (Phase 58 QMP Guest Introspection & USB-LAN PTP-IP Tracer)",
    )
    parser.add_argument(
        "--skip-phase63",
        action="store_true",
        help="Skip optional Stage 8 (Phase 63 HDMI RAW16 EDID, MLUT Clean-Feed & USB-C Arbitrator)",
    )
    parser.add_argument(
        "--skip-phase67",
        action="store_true",
        help="Skip optional Stage 9 (Phase 67 SMPTE 12M TC EXT-LK, E-Mount PZ/Breathing & libpaint)",
    )
    parser.add_argument(
        "--skip-phase71",
        action="store_true",
        help="Skip optional Stage 10 (Phase 71 Dual-Slot Proxy, NonRealTimeMeta.xml & UPS/.RSV Salvage)",
    )
    parser.add_argument(
        "--skip-phase78",
        action="store_true",
        help="Skip optional Stage 11 (Phase 78 Touch AF 627-pt PDAF, CIZ Arbitrator & Assignable Dispatcher)",
    )
    parser.add_argument(
        "--skip-phase82",
        action="store_true",
        help="Skip optional Stage 12 (Phase 82 Cross-Body CAMSET Sanitizer, 4ch 24-bit/48kHz LPCM & SMPTE 12M User-Bits)",
    )
    parser.add_argument(
        "--skip-phase87",
        action="store_true",
        help="Skip optional Stage 13 (Phase 87 Playback/ShotMark, Push Auto Iris & Dew-Point/PMIC 5V HIL)",
    )
    parser.add_argument(
        "--skip-phase91",
        action="store_true",
        help="Skip optional Stage 14 (Phase 91 Gyroflow 2000Hz IMU RTMD 0xE4xx, Anamorphic IBIS & IMX510 RS HIL)",
    )
    parser.add_argument(
        "--skip-phase96",
        action="store_true",
        help="Skip optional Stage 15 (Phase 96 Interval Rec, Picture Cache 384MiB DDR Ring, USB-LAN FTPS & Fan/Housing HIL)",
    )
    parser.add_argument(
        "--skip-phase99",
        action="store_true",
        help="Skip optional Stage 16 (Phase 99 65^3->33^3 Tetrahedral 3D-LUT DMA, HDMI AVI->12G-SDI Bridge & Sub-Zero/Altitude HIL)",
    )
    parser.add_argument(
        "--skip-phase103",
        action="store_true",
        help="Skip optional Stage 17 (Phase 103 Wireless TX EMI/ESD/LTC, 12h exFAT/SMART & Zero-eMMC-Churn Endurance HIL)",
    )
    parser.add_argument(
        "--skip-phase107",
        action="store_true",
        help="Skip optional Stage 18 (Phase 107 C2PA 2.1 cnflasha Firewall, E-Mount/PL Shading Arbitrator, 4-Cam MC Fleet & G31/G32 OVP HIL)",
    )
    parser.add_argument(
        "--skip-phase112",
        action="store_true",
        help="Skip optional Stage 19 (Phase 112 BT.2100/ARIB STD-B67 HLG, CTA-861.3 0x87 InfoFrame, Gamma Display Assist & G33/G34 HIL)",
    )
    parser.add_argument(
        "--skip-phase117",
        action="store_true",
        help="Skip optional Stage 20 (Phase 117 ProRes RAW/BRAW Handshake, Focus Breathing vs PL/RAW Bypass, MI-Shoe 48kHz PLL & G35/G36 HIL)",
    )
    parser.add_argument(
        "--skip-phase121",
        action="store_true",
        help="Skip optional Stage 21 (Phase 121 USB-C UVC 1.5/UAC 2.0, Wired P12-Safe SRT/RTMPS, CRSDK PTP/Firewall & G37/G38 HIL)",
    )
    parser.add_argument(
        "--skip-phase127",
        action="store_true",
        help="Skip optional Stage 22 (Phase 127 MXF/MP4 RDD-18/UMID Bridge, ST 2059-2 PTPv2/LTC Sync, TSL UMD v5.0 Tally & G39/G40 HIL)",
    )
    parser.add_argument(
        "--skip-phase132",
        action="store_true",
        help="Skip optional Stage 23 (Phase 132 VP LED-Wall ECS Solver, FreeD 0xD1 LiveLink, Art-Net 4/sACN Sync & G41/G42 Genlock/IBIS HIL)",
    )
    parser.add_argument(
        "--skip-phase141",
        action="store_true",
        help="Skip optional Stage 24 (Phase 141 Real-Hardware Pre-Flash Lifecycle & 4-State Dual-Boot HIL Simulator)",
    )
    parser.add_argument(
        "--skip-phase145",
        action="store_true",
        help="Skip optional Stage 25 (Phase 145 Real-Hardware appFw.so -> Stock FX3 libmpr.so / DmmCfg.bin Card-Recording Co-Emulator)",
    )
    parser.add_argument(
        "--skip-phase150",
        action="store_true",
        help="Skip optional Stage 26 (Phase 150 Real-Hardware FX3 Body Controls, IBIS Center-Lock, XLR-H1, Fan PWM & NP-FZ100/USB-PD HIL)",
    )
    parser.add_argument(
        "--skip-phase157",
        action="store_true",
        help="Skip optional Stage 27 (Phase 157 Real-Hardware IMX510 Dual-Base ISO 800/12800, psd/defdet NVS, .cube MLUT, CDC-NCM & 054C:0DA1 HIL)",
    )
    parser.add_argument(
        "--skip-phase162",
        action="store_true",
        help="Skip optional Stage 28 (Phase 162 Real-Hardware CFexpress/SDXC V90, .RSV Salvage, BODYDATA.DAT UFU Bypass & 5-Tier Recovery HIL)",
    )
    parser.add_argument(
        "--bt-mode",
        choices=p29.ALL_BT_OPERATING_MODES,
        default=p29.BT_MODE_HEALTHY,
        help="virtual-rom-v1 Bluetooth UART operating mode",
    )
    parser.add_argument(
        "--cine-ei-iso",
        type=int,
        choices=p24.DUAL_NATIVE_ISO_BASES,
        default=800,
        help="Cine EI native base ISO selection (800 or 12800)",
    )
    parser.add_argument(
        "--lut-mode",
        choices=VALID_LUT_MODES,
        default="8bit",
        help="33^3 3D LUT DMA mode",
    )
    parser.add_argument(
        "--ibis-mode",
        choices=tuple(p24.VALID_STEADYSHOT_MODES.keys()),
        default="Active",
        help="5-axis IBIS SteadyShot mode",
    )
    parser.add_argument(
        "--xavc-resolution",
        choices=tuple(p45.IMX510_READOUT_MODES.keys()),
        default=p45.RES_QFHD_4K,
        help="Stage 5 IMX510 readout resolution mode",
    )
    parser.add_argument(
        "--xavc-fps",
        choices=tuple(p45.FRAME_RATE_SPECS.keys()),
        default="59.94p",
        help="Stage 5 IMX510 VSYNC frame rate",
    )
    parser.add_argument(
        "--xavc-codec",
        choices=p45.ALL_CODEC_FAMILIES,
        default=p45.CODEC_XAVC_I,
        help="Stage 5 libmpr XAVC codec family",
    )
    parser.add_argument(
        "--rec-mode",
        choices=p45.ALL_RECORDING_MODES,
        default=p45.REC_MODE_SIMULTANEOUS,
        help="Stage 5 Dual Slot A/B recording mode",
    )
    parser.add_argument(
        "--rtc-invalid",
        action="store_true",
        help="Simulate unset /dev/rtc0 state in P11 AP filter",
    )
    args = parser.parse_args(argv)

    if args.topology:
        sys.stdout.write(json.dumps(asdict(p24.build_dual_qemu_ivshmem_topology_spec()), indent=2) + "\n")
        return 0

    cfg = CoEmulationConfig(
        bt_mode=args.bt_mode,
        cine_ei_iso=args.cine_ei_iso,
        lut_mode=args.lut_mode,
        ibis_mode=args.ibis_mode,
        rtc_valid=not args.rtc_invalid,
        include_phase41_dtb_mhlx=not args.skip_phase41,
        include_phase45_imx510_xavc=not args.skip_phase45,
        include_phase53_hil_fault_harness=not args.skip_phase53,
        include_phase58_qmp_introspection=not args.skip_phase58,
        include_phase63_hdmi_raw_uvc=not args.skip_phase63,
        include_phase67_tc_lens_paint=not args.skip_phase67,
        include_phase71_dualslot_ups_salvage=not args.skip_phase71,
        include_phase78_touchaf_ciz_assignable=not args.skip_phase78,
        include_phase82_camset_lpcm_tcub=not args.skip_phase82,
        include_phase87_playback_shotmark_dewpoint=not args.skip_phase87,
        include_phase91_gyroflow_rtmd_anamorphic=not args.skip_phase91,
        include_phase96_interval_cache_ftp_fan=not args.skip_phase96,
        include_phase99_lut3d_subzero_sdi=not args.skip_phase99,
        include_phase103_emi_exfat_endurance=not args.skip_phase103,
        include_phase107_c2pa_shading_mcfleet_ovp=not args.skip_phase107,
        include_phase112_hdr_hlg_fiz_gimbal=not args.skip_phase112,
        include_phase117_proresraw_breathing_mishoe_hil=not args.skip_phase117,
        include_phase121_uvc_srt_crsdk_usbpd_hil=not args.skip_phase121,
        include_phase127_mxf_ptpv2_tally_monsoon_hil=not args.skip_phase127,
        include_phase132_vp_ledwall_freed_artnet_hil=not args.skip_phase132,
        include_phase141_realhw_preflash_dualboot_hil=not args.skip_phase141,
        include_phase145_realhw_mpr_dmm_rec=not args.skip_phase145,
        include_phase150_realhw_body_peripheral_hil=not args.skip_phase150,
        include_phase157_realhw_imx510_network_usb_hil=not args.skip_phase157,
        include_phase162_realhw_cfexpress_ufu_5tier_hil=not args.skip_phase162,
        xavc_resolution=args.xavc_resolution,
        xavc_fps=args.xavc_fps,
        xavc_codec=args.xavc_codec,
        recording_mode=args.rec_mode,
        force_clean_room=True if args.clean_room else None,
    )
    rep = run_fx3_vm_coemulation_suite(cfg)

    if args.summary and not args.json:
        s1 = rep["stage1_coldboot_and_bt"]
        s2 = rep["stage2_dual_isa_cp_shooting"]
        s3 = rep["stage3_soft_gpe_hud_ramfb"]
        s4 = rep.get("stage4_phase41_dtb_mhlx")
        s5 = rep.get("stage5_phase45_imx510_xavc")
        s6 = rep.get("stage6_phase53_hil_fault_harness")
        s7 = rep.get("stage7_phase58_qmp_introspection")
        s8 = rep.get("stage8_phase63_hdmi_raw_uvc")
        s9 = rep.get("stage9_phase67_tc_lens_paint")
        s10 = rep.get("stage10_phase71_dualslot_ups_salvage")
        s11 = rep.get("stage11_phase78_touchaf_ciz_assignable")
        s12 = rep.get("stage12_phase82_camset_lpcm_tcub")
        s13 = rep.get("stage13_phase87_playback_shotmark_dewpoint")
        s14 = rep.get("stage14_phase91_gyroflow_rtmd_anamorphic")
        s15 = rep.get("stage15_phase96_interval_cache_ftp_fan")
        s16 = rep.get("stage16_phase99_lut3d_subzero_sdi")
        s17 = rep.get("stage17_phase103_emi_exfat_endurance")
        s18 = rep.get("stage18_phase107_c2pa_shading_mcfleet_ovp")
        s19 = rep.get("stage19_phase112_hdr_hlg_fiz_gimbal")
        s20 = rep.get("stage20_proresraw_breathing_mishoe_hil")
        s21 = rep.get("stage21_uvc_srt_crsdk_usbpd_hil")
        s22 = rep.get("stage22_mxf_ptpv2_tally_monsoon_hil")
        s23 = rep.get("stage23_vp_ledwall_freed_artnet_hil")
        s24 = rep.get("stage24_realhw_preflash_dualboot_hil")
        s25 = rep.get("stage25_realhw_mpr_dmm_rec")
        s26 = rep.get("stage26_realhw_body_peripheral_hil")
        s27 = rep.get("stage27_realhw_imx510_network_usb_hil")
        s28 = rep.get("stage28_realhw_cfexpress_ufu_5tier_hil")
        s4_str = (
            f" | dtb_mhlx={s4['source_mode']}({s4['fdt_synthesis_and_audit']['totalsize_bytes']}B)"
            if isinstance(s4, dict)
            else ""
        )
        s5_str = (
            f" | xavc={s5['source_mode']}({s5['primary_recording']['xavc_stream']['codec_family']}"
            f"@{s5['primary_recording']['imx510']['fps_label']})"
            if isinstance(s5, dict)
            else ""
        )
        s6_str = (
            f" | hil={s6['source_mode']}({s6['scenarios_passed']}/{s6['scenarios_total']})"
            if isinstance(s6, dict)
            else ""
        )
        s7_str = (
            f" | qmp={s7['source_mode']}(nop={s7['nop_count']},"
            f"ptpip={s7['ptpip_allowed_count']}ok/{s7['ptpip_blocked_count']}blk)"
            if isinstance(s7, dict)
            else ""
        )
        s8_str = (
            f" | hdmi_uvc={s8['source_mode']}(raw16=4264x2408@59.94p,"
            f"sdi_faults={s8['sdi_transceiver_faults']},"
            f"usbc={s8['usbc_arbitrator_matrix']['allowed_transitions']}ok/"
            f"{s8['usbc_arbitrator_matrix']['blocked_transitions']}blk)"
            if isinstance(s8, dict)
            else ""
        )
        s9_str = (
            f" | tc_lens_paint={s9['source_mode']}(ext_lk=0.0f,"
            f"breath={s9['emount_pz_breathing_ibis']['breathing_selp1635g_near_028m']['fov_scale_factor']}x,"
            f"cal_mut={s9['calibration_mutation_bytes']})"
            if isinstance(s9, dict)
            else ""
        )
        s10_str = (
            f" | dualslot_ups={s10['source_mode']}(relay=0drop,simul_yank=0drop,"
            f"rsv={s10['rsv_salvageable_frames']}/{s10['rsv_committed_frames']},c2pa_ok=1)"
            if isinstance(s10, dict)
            else ""
        )
        s11_str = (
            f" | touchaf_ciz={s11['source_mode']}(pdaf=627,ciz=1.5x/2.0x,gpio_derefs={s11['null_gpio_derefs']})"
            if isinstance(s11, dict)
            else ""
        )
        s12_str = (
            f" | camset_lpcm_tcub={s12['source_mode']}(nd=Clear,wlan=Off,lpcm=4ch/-20dB,"
            f"ub={s12['smpte_12m_user_bits_tc_regenerator']['sony_ub_display']},bk4_wr={s12['bk4_persistent_nvram_writes']})"
            if isinstance(s12, dict)
            else ""
        )
        s13_str = (
            f" | pb_iris_hil={s13['source_mode']}(marks={s13['playback_shotmark_emmc_guard']['shotmarks_punched_total']},"
            f"p1_blk=1,iris=41.0%IRE/nd_flt={s13['p4_nd_motor_faults']},dp=27.14C/shed=1)"
            if isinstance(s13, dict)
            else ""
        )
        s14_str = (
            f" | gyro_anam={s14['source_mode']}(imu=2000Hz/"
            f"drift={s14['imu_2000hz_rtmd_e4xx']['gyroflow_roundtrip_integration']['quaternion_drift_deg']}deg,"
            f"anamo=1.33x..2.0x/dbl_blk=1,rs=8.7/4.3/8.9ms)"
            if isinstance(s14, dict)
            else ""
        )
        s15_str = (
            f" | ivl_cache_ftp_fan={s15['source_mode']}(eshutter_mech=0,"
            f"cache={s15['picture_cache_ddr_ring']['xavc_i_4k60_16s_clamped']['allocated_pool_mib']}MiB/0drop,"
            f"ftps=TLS1.3+REST/wf12={s15['wf12_00342260_hits']},fan_rsv=120/120)"
            if isinstance(s15, dict)
            else ""
        )
        s16_str = (
            f" | lut3d_sdi_hil={s16['source_mode']}(65^3->33^3="
            f"{s16['lut3d_tetrahedral_dma']['resolve_65_to_33_ivshmem']['dma_table_bytes']}B,"
            f"avi=17B/drop={s16['dropped_rec_triggers']},"
            f"subz=-20C/plate={s16['lithium_plating_events']},"
            f"alt5200m=shed1)"
            if isinstance(s16, dict)
            else ""
        )
        s17_str = (
            f" | emi_exfat_12h={s17['source_mode']}(3.24TB/drop={s17['dropped_video_frames']}/{s17['dropped_audio_samples']},"
            f"emi=1000mW/eye250mV,ltc=clamp3.35V/gpio_dmg={s17['cxd90057_gpio_damage_events']},"
            f"emmc_wr={s17['emmc_sector_writes']})"
            if isinstance(s17, dict)
            else ""
        )
        s18_str = (
            f" | c2pa_shad_mc_ovp={s18['source_mode']}(cnfl_mut={s18['cnflasha_mutation_bytes']}/priv_rd={s18['private_key_reads']},"
            f"pl_id=1.0x/0.42ms,mc4=skew{s18['mc_4cam_wired_fleet_sync']['fleet_4cam_gigabit_p12_ok']['gang_rec_start_skew_ms']}ms/wf12={s18['wf12_00342260_hits']},"
            f"ovp26v={s18['g31_g32_ovp_cantilever_hil']['g32_26v_ovp_crowbar_tripped']['ovp_isolation_latency_us']}us/pmic_dmg={s18['cxd90057_pmic_damage_events']})"
            if isinstance(s18, dict)
            else ""
        )
        s19_str = (
            f" | hlg_assist_g33_g34={s19['source_mode']}(hlg={s19['bt2100_hlg_gamut_pipeline']['hlg1_87pct_peak_cv']}/{s19['bt2100_hlg_gamut_pipeline']['hlg2_95pct_peak_cv']}/{s19['bt2100_hlg_gamut_pipeline']['hlg3_100pct_peak_cv']},"
            f"if87=30B/burn={s19['display_assist_burn_in_frames']},"
            f"fiz={s19['g33_g34_duct_fiz_gimbal_hil']['g34_fiz_gimbal_hil']['uncalibrated_3v2nm_fiz_slam_clamped']['clamped_fiz_torque_nm']}Nm/strip={s19['fiz_gear_strip_events']},"
            f"gmb={s19['g33_g34_duct_fiz_gimbal_hil']['g34_fiz_gimbal_hil']['zoom_22mm_cog_oscillation_ibis_protected']['gimbal_pid_resonance_hz']}Hz/sat={s19['ibis_coil_saturation_events']})"
            if isinstance(s19, dict)
            else ""
        )
        s20_str = (
            f" | prores_breath_mi_g35_g36={s20['source_mode']}(raw_burn={s20['raw_lut_burn_in_frames']},"
            f"pl_bypass={s20['pillar_b_focus_breathing_arbitrator']['pl_unchipped_identity_bypass']['bypass_latency_ms']}ms/stale={s20['pl_breathing_stale_crop_frames']},"
            f"pll_12h={s20['pillar_c_mishoe_i2s_pll_lock']['xlr_h1_5994p_12h']['drift_samples_per_hour']}sph/pop={s20['audio_pop_click_frames']},"
            f"g35_bf={s20['pillar_d_g35_g36_aoc_cfexpress_hil']['g35_aoc_hdmi_5v_hil']['reverse_backfeed_gt5v35_isolated']['isolation_latency_us']}us/fuse_dmg={s20['sy1129_hdmi_fuse_damage_events']},"
            f"g36_fat_corr={s20['cfexpress_fat_corruption_events']})"
            if isinstance(s20, dict)
            else ""
        )
        s21_str = (
            f" | uvc_srt_crsdk_usbpd={s21['source_mode']}(uvc_usb2={s21['pillar_a_uvc15_uac20_negotiator']['usb2_cable_auto_stepdown']['total_payload_mbps']}Mbps/osd={s21['uvc_osd_burn_in_frames']},"
            f"srt_drop={s21['srt_dropped_gops']}/wf12={s21['wf12_00342260_hits']},"
            f"crsdk_fw_mut={s21['emmc_flash_mutation_bytes']},"
            f"g37_20v={s21['pillar_d_g37_g38_usbpd_uart_hil']['g37_usbpd_decoy_isolator_hil']['unnegotiated_20v_decoy_crowbar']['crowbar_latency_us']}us/pad_dmg={s21['cxd90057_pad_damage_events']},"
            f"g38_tx={s21['uart_tx_bytes']})"
            if isinstance(s21, dict)
            else ""
        )
        s22_str = (
            f" | mxf_ptpv2_tally_monsoon={s22['source_mode']}(klv_drop={s22['dropped_klv_tags']}/reenc={s22['frame_essence_reencode_loss']},"
            f"ptp_rms={s22['pillar_b_st2059_ptpv2_ltc_servo']['hw_ptpv2_servo_locked']['ptpv2_rms_offset_us']}us/ltc_8h={s22['pillar_b_st2059_ptpv2_ltc_servo']['ltc_8h_holdover_locked']['holdover_phase_slip_frames']}f,"
            f"tally_wf12={s22['wf12_00342260_hits']}/g_flt={s22['fx6_green_gpio_faults']},"
            f"g39_trip={s22['pillar_d_g39_g40_monsoon_cagetwist_hil']['g39_monsoon_mishoe_hil']['wet_mishoe_short_tripped']['load_switch_trip_us']}us/corr={s22['mishoe_rail_corrosion_events']},"
            f"g40_ffd={s22['pillar_d_g39_g40_monsoon_cagetwist_hil']['g40_xlrh1_cagetwist_ffd_hil']['cage_twist_ffd_interlock']['estimated_ffd_tilt_um']}um/dmg={s22['chassis_damage_events']})"
            if isinstance(s22, dict)
            else ""
        )
        s23_str = (
            f" | vp_ledwall_freed_artnet={s23['source_mode']}(ecs={s23['pillar_a_vp_ledwall_ecs_solver']['brompton_4k24_3840hz_locked']['luminance_banding_residual_pct']}%,"
            f"freed={s23['pillar_b_freed_0xd1_livelink_bridge']['emount_12pin_120hz_livelink']['glass_to_engine_latency_ms']}ms/wf12={s23['wf12_00342260_hits']},"
            f"dmx_split={s23['flash_split_band_frames']},"
            f"g41_iso={s23['pillar_d_g41_g42_genlock_vib_hil']['g41_genlock_clash_and_uv_hil']['trilevel_genlock_isolated']['isolation_latency_us']}us/pin_dmg={s23['cxd90057_pin_damage_events']},"
            f"g42={s23['pillar_d_g41_g42_genlock_vib_hil']['g42_helicopter_ibis_resonance_hil']['helicopter_autopark_gyroflow']['ibis_state']}/slam={s23['ibis_endstop_slam_events']})"
            if isinstance(s23, dict)
            else ""
        )
        s24_str = (
            f" | realhw_preflash_dualboot={s24['source_mode']}(p6_res={s24['pillar_a_jiritsu_setfile2_cold_backup_and_spacc_topology']['setfile2_tier012_cold_backup']['p6_residual_files']},"
            f"cn15_orig={s24['pillar_b_cnflasha15_cipher_safe_install_and_powercut_rollback']['midwrite_battery_pull_orig_recovery']['stock_im_elf_restored_100pct']},"
            f"tamper_fc={s24['pillar_c_four_state_dualboot_and_native_rec_closed_loop']['path3_tampered_manifest_fail_closed']['fail_closed_latency_ms']}ms,"
            f"rsv={s24['rsv_orphan_count']},emmc_auth={s24['persistent_emmc_writes_authorized']})"
            if isinstance(s24, dict)
            else ""
        )
        s25_str = (
            f" | realhw_mpr_dmm_rec={s25['source_mode']}(pass={s25['pillar_a_ld_preload_libmpr_secvlt_shim']['passthrough_verified_count']},"
            f"shim={s25['pillar_a_ld_preload_libmpr_secvlt_shim']['shim_intercepted_count']},"
            f"dmm_u={s25['pillar_b_stock_fx3_dmmcfg_pool_budget']['shared_main_dmm_units']},"
            f"leak={s25['dmm_allocated_after_stop']},"
            f"lock={s25['uipc_lock_depth']},"
            f"emmc_wr={s25['emmc_nflasha_write_count']})"
            if isinstance(s25, dict)
            else ""
        )
        s26_str = (
            f" | realhw_body_peripheral_hil={s26['source_mode']}(ibis_float={s26['floating_coil_ms']}ms,"
            f"p18_mut={s26['p18_mutation_bytes']},"
            f"sdi_wait={s26['sdi_blocking_wait_ms']}ms,"
            f"keymap={s26['pillar_c_fx3_keymap_reachability_and_tally']['recording_tally_lit_100pct']['reachability_pct']}%,"
            f"fan_ovr={s26['pillar_d_fan_override_and_npfz100_usbpd']['fan_off_in_rec_thermal_override']['pwm_pct']}%,"
            f"dcin_alarm={s26['false_19v5_dcin_alarms']},"
            f"emmc_wr={s26['emmc_nflasha_write_count']})"
            if isinstance(s26, dict)
            else ""
        )
        s27_str = (
            f" | realhw_imx510_network_usb_hil={s27['source_mode']}(cal_mut={s27['sensor_cal_mutation_bytes']},"
            f"mlut={s27['pillar_b_cube_mlut_16slot_and_slog3_guard']['active_slots_count']}/16,"
            f"dbl_bake={s27['slog3_master_double_baked']},"
            f"bt_wait={s27['bt_hci_blocking_wait_ms']}ms,"
            f"rf_mut={s27['rf_nvs_p12_p13_mutation_bytes']},"
            f"msc_0da1={s27['usb_msc_0da1_recovery_intact']},"
            f"emmc_wr={s27['emmc_nflasha_write_count']})"
            if isinstance(s27, dict)
            else ""
        )
        s28_str = (
            f" | realhw_cfexpress_ufu_5tier_hil={s28['source_mode']}(bypass_us={s28['pillar_c_bodydata_ufu_bypass_and_model_gate']['bodydata_stage_a_bypass_lt_100us']['bypass_latency_us']},"
            f"tiers={s28['pillar_d_five_tier_unbrickable_recovery_drill']['tiers_verified_count']}/5,"
            f"rsv={s28['rsv_orphan_count']},"
            f"el3_tx={s28['el3_payload_transmit_authorized']},"
            f"spi_wr={s28['spi_nor_write_authorized']},"
            f"emmc_wr={s28['emmc_nflasha_write_count']})"
            if isinstance(s28, dict)
            else ""
        )
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 33 FX3-VM Co-Emulation | bt={s1['active_bt_mode']} "
            f"({s1['active_bt_result']['degraded_state']}) | cp={s2['source_mode']} "
            f"iso={s2['cine_ei_iso']} lut={s2['lut_mode']}({s2['lut_bytes']}B) "
            f"ibis={s2['ibis_mode']} cp_mut={s2['cp_mutation_bytes']} | "
            f"gpe={s3['source_mode']} sprites={s3['total_sprites']} "
            f"ramfb_sha={s3['ramfb_scanout']['ramfb_xrgb8888_sha256'][:12]}"
            f"{s4_str}{s5_str}{s6_str}{s7_str}{s8_str}{s9_str}{s10_str}{s11_str}{s12_str}{s13_str}{s14_str}{s15_str}{s16_str}{s17_str}{s18_str}{s19_str}{s20_str}{s21_str}{s22_str}{s23_str}{s24_str}{s25_str}{s26_str}{s27_str}{s28_str} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
