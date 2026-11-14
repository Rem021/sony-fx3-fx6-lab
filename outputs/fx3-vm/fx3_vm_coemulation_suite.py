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

import cxd90057_dtb_and_mhlx_emulator as p41  # noqa: E402
import dual_ap_cp_ivshmem_bridge as p24  # noqa: E402
import soft_gpe_and_bt_rom_emulator as p29  # noqa: E402


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
    active_bt = bt_result.get("active_bt_result", {})
    if active_bt.get("bsa_ready"):
        bt_badge_rgb = (0x28, 0xC8, 0x78)
    elif active_bt.get("airplane_latched"):
        bt_badge_rgb = (0xB8, 0x3C, 0x46)
    else:
        bt_badge_rgb = (0xF0, 0x98, 0x20)
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

    return {
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
# Unified Full-Board Co-Emulation Orchestrator
# ---------------------------------------------------------------------------


def run_fx3_vm_coemulation_suite(
    config: Optional[CoEmulationConfig] = None,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the unified Phase 33 + Phase 41 Full-Board Virtual Camera Co-Emulation Pipeline."""
    cfg = CoEmulationConfig() if config is None else config
    cfg.validate()

    stage1 = run_stage1_bt_and_coldboot(cfg, env=env)
    stage2 = run_stage2_dual_isa_shooting_cycle(cfg, env=env)
    stage3 = run_stage3_soft_gpe_hud_composite(cfg, bt_result=stage1, cp_result=stage2, env=env)
    stage4: Optional[Dict[str, object]] = (
        run_stage4_dtb_mhlx_mmio(cfg, env=env) if cfg.include_phase41_dtb_mhlx else None
    )
    topo = p24.build_dual_qemu_ivshmem_topology_spec()

    stage4_ok = True if stage4 is None else (
        bool(stage4["all_checks_passed"])
        and stage4["cp_mutation_bytes"] == 0
        and stage4["wbi_mutation_bytes"] == 0
    )

    all_passed = (
        bool(stage1["all_checks_passed"])
        and bool(stage2["all_checks_passed"])
        and bool(stage3["all_checks_passed"])
        and stage2["cp_mutation_bytes"] == 0
        and stage4_ok
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

    digest = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    core_payload["audit_digest_sha256"] = digest
    return core_payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fx3_vm_coemulation_suite.py",
        description="Phase 33 + Phase 41 Unified FX3-VM Full-Board Co-Emulation Orchestrator & CLI",
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
        force_clean_room=True if args.clean_room else None,
    )
    rep = run_fx3_vm_coemulation_suite(cfg)

    if args.summary and not args.json:
        s1 = rep["stage1_coldboot_and_bt"]
        s2 = rep["stage2_dual_isa_cp_shooting"]
        s3 = rep["stage3_soft_gpe_hud_ramfb"]
        s4 = rep.get("stage4_phase41_dtb_mhlx")
        s4_str = (
            f" | dtb_mhlx={s4['source_mode']}({s4['fdt_synthesis_and_audit']['totalsize_bytes']}B)"
            if isinstance(s4, dict)
            else ""
        )
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 33 FX3-VM Co-Emulation | bt={s1['active_bt_mode']} "
            f"({s1['active_bt_result']['degraded_state']}) | cp={s2['source_mode']} "
            f"iso={s2['cine_ei_iso']} lut={s2['lut_mode']}({s2['lut_bytes']}B) "
            f"ibis={s2['ibis_mode']} cp_mut={s2['cp_mutation_bytes']} | "
            f"gpe={s3['source_mode']} sprites={s3['total_sprites']} "
            f"ramfb_sha={s3['ramfb_scanout']['ramfb_xrgb8888_sha256'][:12]}{s4_str} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
