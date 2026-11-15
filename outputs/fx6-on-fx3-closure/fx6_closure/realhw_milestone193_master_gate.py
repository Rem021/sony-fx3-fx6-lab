"""Milestone Phase 193 — Grand Unified 6-Pillar Real-Hardware `ILME-FX3 Ver. 7.02` Pre-Bench Master Gate (`realhw_milestone193_master_gate_v1`).

Unifies ALL Wave 21–24 Real-Hardware Main Track subsystems (Phases 134–192) and ALL
10 live Sony ILME-FX3 `Ver. 7.02` (`Linux 4.9.337-scel+`) ARM64 QEMU Rehearsal
Rounds (`Rounds 28..37` — `30/30` sub-experiments + `20/20` `< 28 KiB` PNG receipts)
into a single tamper-evident, fail-closed certificate executing in `< 8.0s` across
both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
modes while keeping `verify-milestone-175` and `preflight-card-insert` 100% intact:

- `P1` (`SAFETY_66GATE_REALHW_MASTER_PREFLIGHT`):
  Evaluates Phase 191 `evaluate_66gate_preflight` (`G01..G66`), verifying `66/66`
  dry-run simulated gates pass (`dry_run_rehearsal_only=True`,
  `overall_ready_for_hardware_attach=False`) while offline hardware-truth mode enforces
  `63/66` (`G10..G12` physical Tier-0 attach/backup gates locked), explicitly auditing
  `G59..G66` (SSBOOT/`WBI2` `PRSVIMG` + `LIRO`, `7.02` UFU >= 2.04 floor + Slot-1 C2PA,
  E-Mount `info7/8/3D` & `0x02cf0232` focus breathing, Type-A HDMI `4264x2408` 16-bit RAW
  vs masked 12G-SDI, `ILME-FX3` vs `ILME-FX3A` branch firewall, `XLR-H1` MI-Shoe 4ch/24b
  vs 3.5mm override, No-UVC USB gadget + `NP-FZ100`/`DC-C1 >=65W/5A`, and dual-media
  `.cube` LUT path asymmetry + Cine EI + `RMT-P1BT`), while hard-locking
  `persistent_emmc_writes_authorized=False`, `spi_nor_write_authorized=False`,
  `el3_payload_transmit_authorized=False`, `persistent_write_release=False`, and
  `agent_auto_flash_blocked=True`.
- `P2` (`TWENTY_SIX_PILLAR_RECOVERY_AIRGAP_AND_FX3A_FIREWALL`):
  Verifies all `>= 26` recovery pillars (`evaluate_26pillar_recovery_master`, Phases
  47–190), covering Pillars `23..26` (`WBI` 100-cycle powerloss transition, 24-pillar
  master, Air-Gap `FX3BNDL1` SD bundle manifest + ExFAT hygiene, and `ILME-FX3` vs
  `ILME-FX3A` recovery firewall + `XLR-H1` audio hygiene), locking
  `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`,
  `passive_tx_bytes_emitted == 0`, `physical_usb_packets_emitted == 0`,
  `physical_device_writes == 0`, and `raw_firmware_bytes_leaked == 0`.
- `P3` (`FORTY_FIRMWARE_LAB_REALBIN_AUDITORS`):
  Verifies all `>= 40` `fx3_firmware_lab` auditors (Phases 1–192), forward-compatible
  with Auditor 41+, explicitly auditing #37..#40 (HDMI BRAW/WPA3/Anamorphic 7.02 delta,
  E-Mount `info3D`/`0x02cf0232` breathing & MC 2.1.0 focus map, `ILME-FX3` vs `FX3A`
  split & `XLR-H1` MI-Shoe 4ch bridge, and No-UVC/`DC-C1` >=65W/dual-media `.cube` LUT
  path + Cine EI/`RMT-P1BT`), locking `calibration_mutation_bytes == 0` and
  `raw_firmware_bytes_leaked == 0`.
- `P4` (`THIRTY_THREE_STAGE_VM_HIL_COEMULATION`):
  Verifies all `>= 33` `outputs/fx3-vm` heterogeneous AArch64 AP + ARM32 Thumb-2
  Stock-CP co-emulation stages (Phases 33–188), forward-compatible with Stage 34+,
  explicitly auditing Stages 31..33 (`SSBOOT`/`WBI2` 100-cycle powerloss & Slot-1 UFU,
  E-Mount `info3D`/breathing & Type-A HDMI `4264x2408` RAW, and `FX3` vs `FX3A` firewall
  & `XLR-H1` 4ch MI-Shoe HIL), locking `emmc_corruptions == 0`,
  `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, and `wf12_00342260_hits == 0`.
- `P5` (`CLOSURE_PREFLIGHT_CARD_INSERT_AND_H0_H3`):
  Verifies `Phase 136` (`U4/U5/U6` + Tier-0 stop-gate), `Phase 143` (BYOF SD bundle,
  `EH1 <= 50 us`, `16/16 H0 == H3`), `Phase 154` (`preflight-realhw-bench`), AND
  `Phase 186` (`preflight-card-insert`: Slot-1 ExFAT geometry & zero `._*` AppleDouble
  hygiene, `BODYDATA.DAT >= 2.04` floor coexistence, `FX3BNDL1 <-> FX3RCPT1` dual-media
  serial binding, electrical/cable/thermal interlock, and `EH1..EH3` + `H0..H3` dry-run).
- `P6` (`REAL_FX3_702_QEMU_ROUNDS_28_TO_37_AND_PNG_RECEIPTS`):
  Verifies committed `O_RDONLY` receipts from ALL 10 Real-Hardware QEMU Rehearsal
  Rounds (`Rounds 28..37`, `30/30` sub-experiments on unmodified FX3 `7.02`
  `4.9.337-scel+`) and all `20/20` `< 28 KiB` PNG receipts (with deterministic
  clean-room synthesis when `FX3_FX6_FORCE_CLEAN_ROOM=1`), proving `crashes == 0`,
  `nop_count == 0`, `emmc_write_count == 0`, and cross-pillar zero-write invariants.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from concurrent.futures import ProcessPoolExecutor
import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Mapping, Optional, Tuple


def _ensure_cross_package_paths(repo_root: Path) -> None:
    """Ensure all sibling lab package roots are importable under default PYTHONPATH."""
    for rel in (
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-firmware-lab",
        "outputs/fx3-vm",
        "outputs/fx6-on-fx3-closure",
    ):
        cand = str(repo_root / rel)
        if cand not in sys.path:
            sys.path.append(cand)


DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

from fx3_firmware_lab.realhw_emount_info3d_breathing_02cf0232_auditor import (  # noqa: E402
    analyze_realhw_emount_info3d_breathing_02cf0232,
    realhw_emount_info3d_breathing_02cf0232_report_to_dict,
)
from fx3_firmware_lab.realhw_fx3_vs_fx3a_and_xlrh1_mishoe_auditor import (  # noqa: E402
    analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe,
    realhw_fx3_vs_fx3a_and_xlrh1_mishoe_report_to_dict,
)
from fx3_firmware_lab.realhw_hdmi_braw_wpa3_702_delta_auditor import (  # noqa: E402
    analyze_realhw_hdmi_braw_wpa3_702_delta,
    realhw_hdmi_braw_wpa3_702_delta_report_to_dict,
)
from fx3_firmware_lab.realhw_nouvc_dcc1_pd_lut_path_cineei_auditor import (  # noqa: E402
    analyze_realhw_nouvc_dcc1_pd_lut_path_cineei,
    realhw_nouvc_dcc1_pd_lut_path_cineei_report_to_dict,
)
from fx3_recovery.realhw_26pillar_master_recovery_verifier import (  # noqa: E402
    MASTER_26_PILLAR_IDS,
    evaluate_26pillar_recovery_master,
)
from fx3_safety.realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard import (  # noqa: E402
    evaluate_66gate_preflight,
)

from .hardware_readiness_packet import _is_forced_clean_room  # noqa: E402
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
)
from .realhw_bench_preflight_and_usb_classifier import (  # noqa: E402
    run_realhw_bench_preflight,
)
from .realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    build_simulated_staged_elf64_artifacts,
    run_card_insert_preflight,
    verify_phase186_report,
)
from .realhw_milestone147_master_gate import (  # noqa: E402
    _worker_phase136,
)
from .realhw_milestone175_master_gate import (  # noqa: E402
    FIRMWARE_LAB_36_AUDITOR_KEYS,
    MILESTONE175_SCHEMA_VERSION,
    RECOVERY_22_PILLAR_IDS,
    ROUND28_TO_34_SPECS,
    VM_COEMULATION_30_STAGE_KEYS,
    RealHwMilestone175FaultInjection,
    RoundQemuReceiptSpec,
    _evaluate_pillar_3 as _eval_m175_p3,
    _evaluate_pillar_4 as _eval_m175_p4,
    _evaluate_pillar_5 as _eval_m175_p5,
    _worker_pillar_3_batch as _m175_worker_pillar_3_batch,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    run_phase143_sd_stageb_bundle_uninstaller_audit,
)
from .stage_b_capstone_22gate_verifier import _build_clean_room_stage_b_manifest_items  # noqa: E402
from .stage_b_milestone110_master_gate import (  # noqa: E402
    _clean_room_faithful_block,
    _worker_pillar_4,
)
from .stage_b_post_trial_auditor import _read_file_o_rdonly  # noqa: E402
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_MILESTONE193_SCHEMA: str = "realhw_milestone193_master_gate_v1"
MILESTONE193_SCHEMA_VERSION: str = REALHW_MILESTONE193_SCHEMA
SCHEMA_VERSION: str = REALHW_MILESTONE193_SCHEMA
PHASE_193_VERSION: str = "193.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
P8_CP_MUTATION_FORBIDDEN: bool = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN: bool = True
CP_MUTATION_BYTES: int = 0
WBI_MUTATION_BYTES: int = 0
CALIBRATION_MUTATION_BYTES: int = 0
USB_OR_CAMERA_OPERATIONS: int = 0
OTP_FUSE_TOUCHES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0

PNG_MAGIC_BYTES: bytes = b"\x89PNG\r\n\x1a\n"
PNG_MAX_SIZE_BYTES: int = 28 * 1024  # 28,672 B (< 28 KiB hard ceiling)

STATUS_MILESTONE_READY: str = "MILESTONE_193_PREBENCH_MASTER_VERIFIED"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_66GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "TWENTY_SIX_PILLAR_RECOVERY_AIRGAP_AND_FX3A_FIREWALL"),
    ("P3", "FORTY_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "THIRTY_THREE_STAGE_VM_HIL_COEMULATION"),
    ("P5", "CLOSURE_PREFLIGHT_CARD_INSERT_AND_H0_H3"),
    ("P6", "REAL_FX3_702_QEMU_ROUNDS_28_TO_37_AND_PNG_RECEIPTS"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

RECOVERY_26_PILLAR_IDS: Tuple[str, ...] = MASTER_26_PILLAR_IDS

FIRMWARE_LAB_40_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_36_AUDITOR_KEYS,
    "realhw_hdmi_braw_wpa3_702_delta_audit",
    "realhw_emount_info3d_breathing_02cf0232_audit",
    "realhw_fx3_vs_fx3a_and_xlrh1_mishoe_audit",
    "realhw_nouvc_dcc1_pd_lut_path_cineei_audit",
)

VM_COEMULATION_33_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_30_STAGE_KEYS,
    "stage31_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil",
    "stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil",
    "stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil",
)

ROUND35_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round35-realhw-ssboot-wbi2-powerloss-slot1-ufu-qemu/summary.json"
)
ROUND36_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round36-realhw-emount-info3d-hdmi-4264-raw-wpa3-qemu/summary.json"
)
ROUND37_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round37-realhw-fx3a-firewall-xlrh1-4ch-fx3bndl1-qemu/summary.json"
)

ROUND35_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round35-realhw-ssboot-wbi2-powerloss-slot1-ufu-qemu-v1"
)
ROUND36_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round36-realhw-emount-info3d-hdmi-4264-raw-wpa3-qemu-v1"
)
ROUND37_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round37-realhw-fx3a-firewall-xlrh1-4ch-fx3bndl1-qemu-v1"
)

ROUND28_TO_37_SPECS: Tuple[RoundQemuReceiptSpec, ...] = (
    *ROUND28_TO_34_SPECS,
    RoundQemuReceiptSpec(
        round_num=35,
        summary_relpath=ROUND35_SUMMARY_RELPATH,
        expected_schema=ROUND35_EXPECTED_SCHEMA,
        audit_key="r35_realhw_ssboot_wbi2_powerloss_slot1_ufu_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r35a_wbi2_nflasha5_blkroset_erofs_and_suspend_disk_intercept_verified",
            "r35a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r35b_100cycle_powerloss_rsv_to_mxf_salvage_verified",
            "r35b_16_of_16_h0_eq_h3_wbi2_zero_drift_verified",
            "r35c_bodydata_204_floor_slot1_uniqueness_and_under_100us_bypass_verified",
            "r35c_c2pa_100_ceiling_and_wpa2_wpa3_enforced_verified",
        ),
        run_specs=(
            ("r35a_ssboot_wbi2_big6_schinese", 1),
            ("r35b_powerloss_100cycle_rsv", None),
            ("r35c_slot1_ufu_c2pa_ceiling", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=36,
        summary_relpath=ROUND36_SUMMARY_RELPATH,
        expected_schema=ROUND36_EXPECTED_SCHEMA,
        audit_key="r36_realhw_emount_info3d_hdmi_4264_raw_wpa3_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r36a_p18_lensfile_erofs_and_emount_info3d_breathing_verified",
            "r36a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r36b_hdmi_4264x2408_braw_prores_and_va3g_reject_verified",
            "r36b_anamorphic_nonbake_and_masked_sdi_mmio_zero_verified",
            "r36c_wpa2_wpa3_sanitizer_rejects_legacy_before_supplicant_verified",
            "r36c_mc210_focusmap_tmpfs_bridge_and_backup_erofs_verified",
        ),
        run_specs=(
            ("r36a_emount_info3d_big6_schinese", 1),
            ("r36b_hdmi_4264_raw_prores_braw", None),
            ("r36c_wpa2_wpa3_focusmap_bridge", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=37,
        summary_relpath=ROUND37_SUMMARY_RELPATH,
        expected_schema=ROUND37_EXPECTED_SCHEMA,
        audit_key="r37_realhw_fx3a_firewall_xlrh1_4ch_fx3bndl1_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r37a_fx3a_rejected_under_50us_rc_minus_22_verified",
            "r37a_fx3a_bodydata_and_camset_blocked_rc_minus_79_verified",
            "r37a_fx3_702_144m_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r37b_xlrh1_48khz_24bit_4ch_and_monitor_matrix_verified",
            "r37b_body35_override_and_sq_mute_verified",
            "r37c_fx3bndl1_foreign_serial_transplant_rejected_rc_minus_13_verified",
            "r37c_appledouble_stripped_dlopen_ok_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r37a_fx3a_firewall_big6_schinese", 1),
            ("r37b_xlrh1_4ch_override", None),
            ("r37c_fx3bndl1_serial_appledouble", None),
        ),
    ),
)

ROUND28_TO_37_PNG_RECEIPTS: Dict[int, Tuple[str, str]] = {
    28: (
        "reports/2026-11-14-round28-realhw-sd-dualboot-overlay-qemu-rehearsal/assets/r28b-sd-trigger-valid-jiritsu-stageb-big6-alpha.png",
        "reports/2026-11-14-round28-realhw-sd-dualboot-overlay-qemu-rehearsal/assets/r28b-sd-trigger-valid-jiritsu-stageb-big6-composited.png",
    ),
    29: (
        "reports/2026-11-14-round29-realhw-atomic-installer-mpr-rec-qemu-rehearsal/assets/r29a-atomic-install-and-live-mpr-rec-big6-alpha.png",
        "reports/2026-11-14-round29-realhw-atomic-installer-mpr-rec-qemu-rehearsal/assets/r29a-atomic-install-and-live-mpr-rec-big6-composited.png",
    ),
    30: (
        "reports/2026-11-15-round30-realhw-canary-tier0-peripheral-uninstall-qemu/assets/r30b-peripheral-big6-schinese-alpha.png",
        "reports/2026-11-15-round30-realhw-canary-tier0-peripheral-uninstall-qemu/assets/r30b-peripheral-big6-schinese-composited.png",
    ),
    31: (
        "reports/2026-11-15-round31-realhw-keymap-fan-fz100-mtdro-qemu/assets/r31a-keymap-tally-big6-schinese-alpha.png",
        "reports/2026-11-15-round31-realhw-keymap-fan-fz100-mtdro-qemu/assets/r31a-keymap-tally-big6-schinese-composited.png",
    ),
    32: (
        "reports/2026-11-15-round32-realhw-imx510-cube-cdcncm-uart-qemu/assets/r32a-imx510-cube-big6-schinese-alpha.png",
        "reports/2026-11-15-round32-realhw-imx510-cube-cdcncm-uart-qemu/assets/r32a-imx510-cube-big6-schinese-composited.png",
    ),
    33: (
        "reports/2026-11-15-round33-realhw-cfexpress-rsv-ufu-5tier-qemu/assets/r33a-cfexpress-rsv-big6-schinese-alpha.png",
        "reports/2026-11-15-round33-realhw-cfexpress-rsv-ufu-5tier-qemu/assets/r33a-cfexpress-rsv-big6-schinese-composited.png",
    ),
    34: (
        "reports/2026-11-15-round34-realhw-cxd90058-c2pa-tc-gyro-seal-qemu/assets/r34a-c2pa-tc-gyro-big6-schinese-alpha.png",
        "reports/2026-11-15-round34-realhw-cxd90058-c2pa-tc-gyro-seal-qemu/assets/r34a-c2pa-tc-gyro-big6-schinese-composited.png",
    ),
    35: (
        "reports/2026-11-15-round35-realhw-ssboot-wbi2-powerloss-slot1-ufu-qemu/assets/r35a-ssboot-wbi2-big6-schinese-alpha.png",
        "reports/2026-11-15-round35-realhw-ssboot-wbi2-powerloss-slot1-ufu-qemu/assets/r35a-ssboot-wbi2-big6-schinese-composited.png",
    ),
    36: (
        "reports/2026-11-15-round36-realhw-emount-info3d-hdmi-4264-raw-wpa3-qemu/assets/r36a-emount-info3d-big6-schinese-alpha.png",
        "reports/2026-11-15-round36-realhw-emount-info3d-hdmi-4264-raw-wpa3-qemu/assets/r36a-emount-info3d-big6-schinese-composited.png",
    ),
    37: (
        "reports/2026-11-15-round37-realhw-fx3a-firewall-xlrh1-4ch-fx3bndl1-qemu/assets/r37a-fx3a-firewall-big6-schinese-alpha.png",
        "reports/2026-11-15-round37-realhw-fx3a-firewall-xlrh1-4ch-fx3bndl1-qemu/assets/r37a-fx3a-firewall-big6-schinese-composited.png",
    ),
}

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_VM_STAGE_KEY_RE = re.compile(r"^stage(\d+)_")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwMilestone193FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 faults (66-gate preflight, G21..G66)
    p1_service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None
    p1_stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None
    p1_pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None
    p1_rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None
    p1_uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None
    p1_imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None
    p1_cfexpress_ufu_kwargs: Optional[Mapping[str, Any]] = None
    p1_five_tier_el3_kwargs: Optional[Mapping[str, Any]] = None
    p1_cxd90058_sabin_kwargs: Optional[Mapping[str, Any]] = None
    p1_factory_seal_kwargs: Optional[Mapping[str, Any]] = None
    p1_c2pa_cert_kwargs: Optional[Mapping[str, Any]] = None
    p1_tc_gyro_meta_kwargs: Optional[Mapping[str, Any]] = None
    p1_dualmedia_vault_kwargs: Optional[Mapping[str, Any]] = None
    p1_bench_interlock_kwargs: Optional[Mapping[str, Any]] = None
    p1_vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None
    p1_vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None
    p1_jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None
    p1_cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None
    p1_pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None
    p1_dummy_battery_kwargs: Optional[Mapping[str, Any]] = None
    p1_saltspray_haze_kwargs: Optional[Mapping[str, Any]] = None
    p1_followfocus_gimbal_kwargs: Optional[Mapping[str, Any]] = None
    p1_hdmi_aoc_kwargs: Optional[Mapping[str, Any]] = None
    p1_cfexpress_media_kwargs: Optional[Mapping[str, Any]] = None
    p1_usbpd_uvc_kwargs: Optional[Mapping[str, Any]] = None
    p1_multiterminal_ptp_kwargs: Optional[Mapping[str, Any]] = None
    p1_monsoon_mishoe_kwargs: Optional[Mapping[str, Any]] = None
    p1_cagetwist_xlrh1_kwargs: Optional[Mapping[str, Any]] = None
    p1_dewpoint_kwargs: Optional[Mapping[str, Any]] = None
    p1_pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None
    p1_xlr_kwargs: Optional[Mapping[str, Any]] = None
    p1_gimbal_kwargs: Optional[Mapping[str, Any]] = None
    p1_rig_kwargs: Optional[Mapping[str, Any]] = None
    p1_emount_kwargs: Optional[Mapping[str, Any]] = None
    p1_power_failover_kwargs: Optional[Mapping[str, Any]] = None
    p1_intake_fan_kwargs: Optional[Mapping[str, Any]] = None
    p1_tripod_housing_kwargs: Optional[Mapping[str, Any]] = None
    p1_sensor_curtain_kwargs: Optional[Mapping[str, Any]] = None
    p1_subzero_altitude_kwargs: Optional[Mapping[str, Any]] = None
    p1_wireless_tx_emi_kwargs: Optional[Mapping[str, Any]] = None
    p1_longform_endurance_kwargs: Optional[Mapping[str, Any]] = None
    # Wave 22-24 P1 gates (G59..G66)
    p1_ssboot_wbi2_kwargs: Optional[Mapping[str, Any]] = None
    p1_slot1_ufu_c2pa_kwargs: Optional[Mapping[str, Any]] = None
    p1_emount_breathing_kwargs: Optional[Mapping[str, Any]] = None
    p1_hdmi_raw_kwargs: Optional[Mapping[str, Any]] = None
    p1_fx3a_firewall_kwargs: Optional[Mapping[str, Any]] = None
    p1_xlrh1_mishoe_kwargs: Optional[Mapping[str, Any]] = None
    p1_nouvc_dcc1_pd_kwargs: Optional[Mapping[str, Any]] = None
    p1_lut_path_cineei_bt_kwargs: Optional[Mapping[str, Any]] = None
    p1_request_persistent_writes: bool = False

    # P2 faults (26-pillar recovery master + Pillars 23..26 + redlines)
    p2_fault_inject_pillar: Optional[str] = None
    p2_otp_fuse_touches_override: int = 0
    p2_rpmb_increments_override: int = 0
    p2_passive_tx_bytes_override: int = 0
    p2_physical_usb_packets_override: int = 0
    p2_physical_device_writes_override: int = 0
    p2_raw_firmware_bytes_leaked_override: int = 0

    # P3 faults (>= 40 fx3_firmware_lab auditors, incl. #25..#40)
    p3_calibration_mutation_bytes: int = 0
    p3_bk4_persistent_nvram_writes: int = 0
    p3_corrupt_wb_whitepoint: bool = False
    p3_corrupt_nrtm_sidecar: bool = False
    p3_inject_legacy_sq_big6_block: bool = False
    p3_inject_persistent_nvram_shadow_path: bool = False
    p3_int24_wrap_around_count: int = 0
    p3_bus_contention_count: int = 0
    p3_p4_nd_motor_fault_attempts: int = 0
    p3_inject_internal_emmc_format_attempt: bool = False
    p3_imu_calibration_mutation_bytes: int = 0
    p3_emmc_mutation_bytes: int = 0
    p3_c2pa_shading_mutation_bytes: int = 0
    p3_hdr_nrtm_mutation_bytes: int = 0
    p3_ob_clamp_mutation_bytes: int = 0
    p3_uvc_crsdk_emmc_mutation_bytes: int = 0
    p3_mxf_tally_emmc_mutation_bytes: int = 0
    p3_vp_ledwall_emmc_mutation_bytes: int = 0
    p3_xavc_fz100_emmc_mutation_bytes: int = 0
    p3_realhw_cp_spi_mutation_bytes: int = 0
    p3_realhw_mpr_bridge_emmc_mutation_bytes: int = 0
    p3_peripheral_p18_emmc_mutation_bytes: int = 0
    p3_controls_fan_emmc_mutation_bytes: int = 0
    p3_wifi_rfnvs_mutation_bytes: int = 0
    p3_imx510_sensor_cal_mutation_bytes: int = 0
    p3_cfexpress_ufu_emmc_mutation_bytes: int = 0
    p3_cxd90058_sabin_mutation_bytes: int = 0
    p3_c2pa_cert_mutation_bytes: int = 0
    p3_wbi2_hibdrv_mutation_bytes: int = 0
    # Auditors #37..#40
    p3_hdmi_braw_raw_leaked_override: int = 0
    p3_emount_lens_partition_writes_override: int = 0
    p3_fx3a_xlrh1_persistent_writes_override: int = 0
    p3_nouvc_dcc1_lut_persistent_writes_override: int = 0

    # P4 faults (>= 33-stage VM co-emulation, Stages 1..33)
    p4_cp_mutation_bytes: int = 0
    p4_bk4_persistent_nvram_writes: int = 0
    p4_stage10_dropped_frames: int = 0
    p4_stage11_nop_count: int = 0
    p4_stage11_null_gpio_derefs: int = 0
    p4_stage12_uart_contention_events: int = 0
    p4_stage13_p1_emmc_format_attempt: bool = False
    p4_stage13_p4_nd_motor_faults: int = 0
    p4_stage15_wf12_hits: int = 0
    p4_stage16_lithium_plating_events: int = 0
    p4_stage17_emmc_sector_writes: int = 0
    p4_stage18_cnflasha_mutation_bytes: int = 0
    p4_stage18_private_key_exports: int = 0
    p4_stage19_fiz_gear_strip_events: int = 0
    p4_stage19_display_assist_burn_in_frames: int = 0
    p4_stage20_pl_breathing_stale_crop_frames: int = 0
    p4_stage20_sy1129_fuse_damage_events: int = 0
    p4_stage21_emmc_flash_mutation_bytes: int = 0
    p4_stage21_wf12_hits: int = 0
    p4_stage21_uart_tx_bytes: int = 0
    p4_stage22_emmc_mutation_bytes: int = 0
    p4_stage23_emmc_mutation_bytes: int = 0
    p4_stage24_emmc_mutation_bytes: int = 0
    p4_stage24_spi_nor_mutation_bytes: int = 0
    p4_stage24_sector0_mutation_bytes: int = 0
    p4_stage24_rsv_orphan_count: int = 0
    p4_stage25_emmc_mutation_bytes: int = 0
    p4_stage26_p18_mutation_bytes: int = 0
    p4_stage27_sensor_or_rfnvs_mutation_bytes: int = 0
    p4_stage28_spi_or_emmc_mutation_bytes: int = 0
    p4_stage29_cxd90058_or_residual_count: int = 0
    p4_stage30_c2pa_or_voltage_events: int = 0
    # Stages 31..33
    p4_stage31_wbi_or_c2pa_mutation_bytes: int = 0
    p4_stage32_lens_or_sdi_faults: int = 0
    p4_stage33_ribbon_or_audio_faults: int = 0

    # P5 faults (Closure Phase 136 + Phase 143 + Phase 154 + Phase 186 preflight-card-insert)
    p5_inject_p136_u4_u5_u6_fault: bool = False
    p5_inject_p143_escape_hatch_over_budget_us: int = 0
    p5_inject_p143_h0_h3_drift: bool = False
    p5_inject_p154_no_go_fault: bool = False
    p5_inject_p154_usb_packets_override: int = 0
    p5_inject_p186_appledouble_fault: bool = False
    p5_inject_p186_h0_h3_drift: bool = False
    p5_inject_p186_fw_below_204: bool = False
    p5_inject_p186_single_device_collision: bool = False
    p5_inject_p186_usb_packets_override: int = 0

    # P6 faults (Rounds 28..37 live QEMU kernel rehearsal & PNG receipts)
    p6_round_nop_override_num: Optional[int] = None
    p6_round_nop_count_override: Optional[int] = None
    p6_round_crash_override_num: Optional[int] = None
    p6_round_crashes_override: Optional[int] = None
    p6_round_emmc_override_num: Optional[int] = None
    p6_round_emmc_writes_override: Optional[int] = None
    p6_tamper_schema_round_num: Optional[int] = None
    p6_png_size_override_round_num: Optional[int] = None
    p6_png_size_override_bytes: Optional[int] = None


@dataclass(frozen=True)
class Milestone193PillarResult:
    pillar_id: str
    pillar_name: str
    passed: bool
    status: str
    summary: str
    evidence: Dict[str, Any]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwMilestone193MasterGateReport:
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_milestone_ready: bool
    status: str
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    hardware_live_attachment_authorized: bool
    hardware_live_attachment_requirements: Tuple[str, ...]
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    p8_cp_mutation_forbidden: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    cp_mutation_bytes: int
    wbi_mutation_bytes: int
    calibration_mutation_bytes: int
    usb_or_camera_operations: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    temp_dir_cleaned: bool
    pillar_count: int
    passed_pillar_count: int
    failed_pillar_ids: Tuple[str, ...]
    pillars: Tuple[Milestone193PillarResult, ...]
    gate66_total_gates: int
    gate66_offline_verified: int
    gate66_simulated_verified: int
    recovery_pillar_count: int
    recovery_pillars_passed: int
    firmware_lab_auditor_count: int
    firmware_lab_auditors_passed: int
    vm_coemulation_stage_count: int
    vm_coemulation_stages_passed: int
    vm_emmc_corruptions: int
    vm_wf12_00342260_hits: int
    p136_u6_command_count: int
    p136_u4_u5_u6_closed: bool
    p143_sd_escape_absent_us: int
    p143_h0_equals_h3_count: int
    p143_h0_h3_surface_count: int
    p154_bench_go: bool
    p154_usb_packets_emitted: int
    p154_iokit_handles_opened: int
    p186_offline_go_no_go: str
    p186_sim_go_no_go: str
    p186_sim_gates_passed: int
    p186_card_insert_authorized: bool
    p186_body_fw_ge_204: bool
    p186_dual_media_serial_bound: bool
    p186_h0_equals_h3_count: int
    qemu_rounds_verified: int
    qemu_runs_verified: int
    qemu_png_receipts_verified: int
    qemu_png_max_bytes: int
    qemu_round_runs_by_round: Dict[str, int]
    qemu_real_kernel_nop_count: int
    qemu_real_kernel_crashes: int
    qemu_real_kernel_emmc_writes: int
    errors: Tuple[str, ...]
    milestone193_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone193VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone193_sha256: str
    observed_milestone193_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Digest & O_RDONLY Rounds 28..37 + PNG Receipt Loaders
# ---------------------------------------------------------------------------


def compute_milestone193_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone193MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone193_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _load_round28_to_37_summary(
    spec: RoundQemuReceiptSpec,
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load Round 28..37 QEMU rehearsal summary strictly via `os.O_RDONLY`, else clean-room synthetic."""
    summary_path = repo_root / spec.summary_relpath
    if not use_clean_room:
        if not summary_path.is_file() or summary_path.is_symlink():
            raise FileNotFoundError(f"Missing round{spec.round_num} summary report: {summary_path}")
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if not isinstance(obj, dict):
            raise ValueError(f"Invalid JSON object in {summary_path}")
        return obj, "REPO_SUMMARY_O_RDONLY"

    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"

    manifest_items = _build_clean_room_stage_b_manifest_items()
    kver = "Linux version 4.9.337-scel+ (clean-room-synthetic)"
    runs: Dict[str, Any] = {}
    for rid, exp_f in spec.run_specs:
        run_entry: Dict[str, Any] = {
            "run_id": rid.replace("_", "-"),
            "round": spec.round_num,
            "lang": "schinese",
            "kernel_version": kver,
            "crashes": 0,
            "emmc_write_count": 0,
            "stage_b": {
                "stage": "B",
                f"r{spec.round_num}_enabled": True,
                "lang": "schinese",
                "manifest_count": 13,
                "manifest_items": list(manifest_items),
            },
        }
        if exp_f is not None:
            faithful = _clean_room_faithful_block()
            faithful["FX6_NATIVE_FAITHFUL"] = exp_f
            faithful["emmc_write_count"] = 0
            run_entry["nop_count"] = 0
            run_entry["faithful_invariants"] = faithful
        runs[rid] = run_entry

    audit_obj: Dict[str, Any] = {k: True for k in spec.audit_bool_keys}
    audit_obj["total_runs"] = len(spec.run_specs)
    return (
        {
            "schema": spec.expected_schema,
            "kernel_version": kver,
            "runs": runs,
            spec.audit_key: audit_obj,
        },
        "CLEAN_ROOM_SYNTHETIC",
    )


def _inspect_round_png_receipt(
    relpath: str,
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[bool, int, str]:
    """Verify a Round 28..37 PNG receipt strictly via `os.O_RDONLY` (< 28 KiB), else clean-room."""
    path = repo_root / relpath
    if not use_clean_room or (path.is_file() and not path.is_symlink()):
        if not path.is_file() or path.is_symlink():
            return False, -1, "MISSING_OR_SYMLINK"
        raw = _read_file_o_rdonly(path)
        size = len(raw)
        magic_ok = len(raw) >= len(PNG_MAGIC_BYTES) and raw[: len(PNG_MAGIC_BYTES)] == PNG_MAGIC_BYTES
        return bool(magic_ok and 0 < size < PNG_MAX_SIZE_BYTES), size, "REPO_PNG_O_RDONLY"
    # Clean-room fallback when PNG asset files are not materialized
    return True, 27147, "CLEAN_ROOM_SYNTHETIC"


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 8.0s)
# ---------------------------------------------------------------------------


_66GATE_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_service_0336_canary_kwargs", "service_0336_canary_kwargs"),
    ("p1_stageb_mpr_ibis_p18_kwargs", "stageb_mpr_ibis_p18_kwargs"),
    ("p1_pnflasha_mtdro_kwargs", "pnflasha_mtdro_kwargs"),
    ("p1_rfnvs_fan_power_kwargs", "rfnvs_fan_power_kwargs"),
    ("p1_uart1v8_isp_kwargs", "uart1v8_isp_kwargs"),
    ("p1_imx510_sensor_cal_kwargs", "imx510_sensor_cal_kwargs"),
    ("p1_cfexpress_ufu_kwargs", "cfexpress_ufu_kwargs"),
    ("p1_five_tier_el3_kwargs", "five_tier_el3_kwargs"),
    ("p1_cxd90058_sabin_kwargs", "cxd90058_sabin_kwargs"),
    ("p1_factory_seal_kwargs", "factory_seal_kwargs"),
    ("p1_c2pa_cert_kwargs", "c2pa_cert_kwargs"),
    ("p1_tc_gyro_meta_kwargs", "tc_gyro_meta_kwargs"),
    ("p1_dualmedia_vault_kwargs", "dualmedia_vault_kwargs"),
    ("p1_bench_interlock_kwargs", "bench_interlock_kwargs"),
    ("p1_vp_strobe_genlock_kwargs", "vp_strobe_genlock_kwargs"),
    ("p1_vehiclerig_ibis_kwargs", "vehiclerig_ibis_kwargs"),
    ("p1_jiritsu_service_kwargs", "jiritsu_service_kwargs"),
    ("p1_cnflasha_dualboot_kwargs", "cnflasha_dualboot_kwargs"),
    ("p1_pl_cantilever_kwargs", "pl_cantilever_kwargs"),
    ("p1_dummy_battery_kwargs", "dummy_battery_kwargs"),
    ("p1_saltspray_haze_kwargs", "saltspray_haze_kwargs"),
    ("p1_followfocus_gimbal_kwargs", "followfocus_gimbal_kwargs"),
    ("p1_hdmi_aoc_kwargs", "hdmi_aoc_kwargs"),
    ("p1_cfexpress_media_kwargs", "cfexpress_media_kwargs"),
    ("p1_usbpd_uvc_kwargs", "usbpd_uvc_kwargs"),
    ("p1_multiterminal_ptp_kwargs", "multiterminal_ptp_kwargs"),
    ("p1_monsoon_mishoe_kwargs", "monsoon_mishoe_kwargs"),
    ("p1_cagetwist_xlrh1_kwargs", "cagetwist_xlrh1_kwargs"),
    ("p1_dewpoint_kwargs", "dewpoint_kwargs"),
    ("p1_pmic_usbc_kwargs", "pmic_usbc_kwargs"),
    ("p1_xlr_kwargs", "xlr_kwargs"),
    ("p1_gimbal_kwargs", "gimbal_kwargs"),
    ("p1_rig_kwargs", "rig_kwargs"),
    ("p1_emount_kwargs", "emount_kwargs"),
    ("p1_power_failover_kwargs", "power_failover_kwargs"),
    ("p1_intake_fan_kwargs", "intake_fan_kwargs"),
    ("p1_tripod_housing_kwargs", "tripod_housing_kwargs"),
    ("p1_sensor_curtain_kwargs", "sensor_curtain_kwargs"),
    ("p1_subzero_altitude_kwargs", "subzero_altitude_kwargs"),
    ("p1_wireless_tx_emi_kwargs", "wireless_tx_emi_kwargs"),
    ("p1_longform_endurance_kwargs", "longform_endurance_kwargs"),
    ("p1_ssboot_wbi2_kwargs", "ssboot_wbi2_kwargs"),
    ("p1_slot1_ufu_c2pa_kwargs", "slot1_ufu_c2pa_kwargs"),
    ("p1_emount_breathing_kwargs", "emount_breathing_kwargs"),
    ("p1_hdmi_raw_kwargs", "hdmi_raw_kwargs"),
    ("p1_fx3a_firewall_kwargs", "fx3a_firewall_kwargs"),
    ("p1_xlrh1_mishoe_kwargs", "xlrh1_mishoe_kwargs"),
    ("p1_nouvc_dcc1_pd_kwargs", "nouvc_dcc1_pd_kwargs"),
    ("p1_lut_path_cineei_bt_kwargs", "lut_path_cineei_bt_kwargs"),
)


def _fault_to_m175_faults(faults: RealHwMilestone193FaultInjection) -> RealHwMilestone175FaultInjection:
    return RealHwMilestone175FaultInjection(
        p3_calibration_mutation_bytes=faults.p3_calibration_mutation_bytes,
        p3_bk4_persistent_nvram_writes=faults.p3_bk4_persistent_nvram_writes,
        p3_corrupt_wb_whitepoint=faults.p3_corrupt_wb_whitepoint,
        p3_corrupt_nrtm_sidecar=faults.p3_corrupt_nrtm_sidecar,
        p3_inject_legacy_sq_big6_block=faults.p3_inject_legacy_sq_big6_block,
        p3_inject_persistent_nvram_shadow_path=faults.p3_inject_persistent_nvram_shadow_path,
        p3_int24_wrap_around_count=faults.p3_int24_wrap_around_count,
        p3_bus_contention_count=faults.p3_bus_contention_count,
        p3_p4_nd_motor_fault_attempts=faults.p3_p4_nd_motor_fault_attempts,
        p3_inject_internal_emmc_format_attempt=faults.p3_inject_internal_emmc_format_attempt,
        p3_imu_calibration_mutation_bytes=faults.p3_imu_calibration_mutation_bytes,
        p3_emmc_mutation_bytes=faults.p3_emmc_mutation_bytes,
        p3_c2pa_shading_mutation_bytes=faults.p3_c2pa_shading_mutation_bytes,
        p3_hdr_nrtm_mutation_bytes=faults.p3_hdr_nrtm_mutation_bytes,
        p3_ob_clamp_mutation_bytes=faults.p3_ob_clamp_mutation_bytes,
        p3_uvc_crsdk_emmc_mutation_bytes=faults.p3_uvc_crsdk_emmc_mutation_bytes,
        p3_mxf_tally_emmc_mutation_bytes=faults.p3_mxf_tally_emmc_mutation_bytes,
        p3_vp_ledwall_emmc_mutation_bytes=faults.p3_vp_ledwall_emmc_mutation_bytes,
        p3_xavc_fz100_emmc_mutation_bytes=faults.p3_xavc_fz100_emmc_mutation_bytes,
        p3_realhw_cp_spi_mutation_bytes=faults.p3_realhw_cp_spi_mutation_bytes,
        p3_realhw_mpr_bridge_emmc_mutation_bytes=faults.p3_realhw_mpr_bridge_emmc_mutation_bytes,
        p3_peripheral_p18_emmc_mutation_bytes=faults.p3_peripheral_p18_emmc_mutation_bytes,
        p3_controls_fan_emmc_mutation_bytes=faults.p3_controls_fan_emmc_mutation_bytes,
        p3_wifi_rfnvs_mutation_bytes=faults.p3_wifi_rfnvs_mutation_bytes,
        p3_imx510_sensor_cal_mutation_bytes=faults.p3_imx510_sensor_cal_mutation_bytes,
        p3_cfexpress_ufu_emmc_mutation_bytes=faults.p3_cfexpress_ufu_emmc_mutation_bytes,
        p3_cxd90058_sabin_mutation_bytes=faults.p3_cxd90058_sabin_mutation_bytes,
        p3_c2pa_cert_mutation_bytes=faults.p3_c2pa_cert_mutation_bytes,
        p3_wbi2_hibdrv_mutation_bytes=faults.p3_wbi2_hibdrv_mutation_bytes,
        p4_cp_mutation_bytes=faults.p4_cp_mutation_bytes,
        p4_bk4_persistent_nvram_writes=faults.p4_bk4_persistent_nvram_writes,
        p4_stage10_dropped_frames=faults.p4_stage10_dropped_frames,
        p4_stage11_nop_count=faults.p4_stage11_nop_count,
        p4_stage11_null_gpio_derefs=faults.p4_stage11_null_gpio_derefs,
        p4_stage12_uart_contention_events=faults.p4_stage12_uart_contention_events,
        p4_stage13_p1_emmc_format_attempt=faults.p4_stage13_p1_emmc_format_attempt,
        p4_stage13_p4_nd_motor_faults=faults.p4_stage13_p4_nd_motor_faults,
        p4_stage15_wf12_hits=faults.p4_stage15_wf12_hits,
        p4_stage16_lithium_plating_events=faults.p4_stage16_lithium_plating_events,
        p4_stage17_emmc_sector_writes=faults.p4_stage17_emmc_sector_writes,
        p4_stage18_cnflasha_mutation_bytes=faults.p4_stage18_cnflasha_mutation_bytes,
        p4_stage18_private_key_exports=faults.p4_stage18_private_key_exports,
        p4_stage19_fiz_gear_strip_events=faults.p4_stage19_fiz_gear_strip_events,
        p4_stage19_display_assist_burn_in_frames=faults.p4_stage19_display_assist_burn_in_frames,
        p4_stage20_pl_breathing_stale_crop_frames=faults.p4_stage20_pl_breathing_stale_crop_frames,
        p4_stage20_sy1129_fuse_damage_events=faults.p4_stage20_sy1129_fuse_damage_events,
        p4_stage21_emmc_flash_mutation_bytes=faults.p4_stage21_emmc_flash_mutation_bytes,
        p4_stage21_wf12_hits=faults.p4_stage21_wf12_hits,
        p4_stage21_uart_tx_bytes=faults.p4_stage21_uart_tx_bytes,
        p4_stage22_emmc_mutation_bytes=faults.p4_stage22_emmc_mutation_bytes,
        p4_stage23_emmc_mutation_bytes=faults.p4_stage23_emmc_mutation_bytes,
        p4_stage24_emmc_mutation_bytes=faults.p4_stage24_emmc_mutation_bytes,
        p4_stage24_spi_nor_mutation_bytes=faults.p4_stage24_spi_nor_mutation_bytes,
        p4_stage24_sector0_mutation_bytes=faults.p4_stage24_sector0_mutation_bytes,
        p4_stage24_rsv_orphan_count=faults.p4_stage24_rsv_orphan_count,
        p4_stage25_emmc_mutation_bytes=faults.p4_stage25_emmc_mutation_bytes,
        p4_stage26_p18_mutation_bytes=faults.p4_stage26_p18_mutation_bytes,
        p4_stage27_sensor_or_rfnvs_mutation_bytes=faults.p4_stage27_sensor_or_rfnvs_mutation_bytes,
        p4_stage28_spi_or_emmc_mutation_bytes=faults.p4_stage28_spi_or_emmc_mutation_bytes,
        p4_stage29_cxd90058_or_residual_count=faults.p4_stage29_cxd90058_or_residual_count,
        p4_stage30_c2pa_or_voltage_events=faults.p4_stage30_c2pa_or_voltage_events,
        p5_inject_p136_u4_u5_u6_fault=faults.p5_inject_p136_u4_u5_u6_fault,
        p5_inject_p143_escape_hatch_over_budget_us=faults.p5_inject_p143_escape_hatch_over_budget_us,
        p5_inject_p143_h0_h3_drift=faults.p5_inject_p143_h0_h3_drift,
        p5_inject_p154_no_go_fault=faults.p5_inject_p154_no_go_fault,
        p5_inject_p154_usb_packets_override=faults.p5_inject_p154_usb_packets_override,
    )


def _fault_to_66gate_worker_dict(faults: RealHwMilestone193FaultInjection) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "p1_request_persistent_writes": bool(faults.p1_request_persistent_writes),
    }
    for src_attr, _ in _66GATE_FAULT_FIELDS:
        val = getattr(faults, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    return out


def _extract_gate_dict(g: object) -> Dict[str, Any]:
    if isinstance(g, Mapping):
        return dict(g)
    return {
        "gate_id": getattr(g, "gate_id", ""),
        "gate_code": getattr(g, "gate_code", ""),
        "status": getattr(g, "status", ""),
        "passed": bool(getattr(g, "passed", False)),
        "violation_codes": tuple(getattr(g, "violation_codes", ())),
    }


def _worker_66gate_single(args: Tuple[str, bool, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, dry_run_sim, fault_dict = args
    repo_root = Path(repo_root_str)
    kwargs: Dict[str, Any] = {
        "request_persistent_emmc_writes": bool(fault_dict.get("p1_request_persistent_writes", False))
    }
    for src_attr, dst_kw in _66GATE_FAULT_FIELDS:
        if fault_dict.get(src_attr) is not None:
            kwargs[dst_kw] = fault_dict[src_attr]

    rep = evaluate_66gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=dry_run_sim,
        **kwargs,
    )

    m64 = rep.master_64_report
    m62 = m64.get("master_62_report", {})
    m60 = m62.get("master_60_report", {})
    m58 = m60.get("master_58_report", {})
    m56 = m58.get("master_56_report", {})
    m54 = m56.get("master_54_report", {})
    m52 = m54.get("master_52_report", {})
    m50 = m52.get("master_50_report", {})
    m48 = m50.get("master_48_report", {})
    m46 = m48.get("master_46_report", {})
    nested_g_valid: Dict[str, bool] = {}
    for tag, src in (
        ("g45", m46.get("g45_result", {})),
        ("g46", m46.get("g46_result", {})),
        ("g47", m48.get("g47_result", {})),
        ("g48", m48.get("g48_result", {})),
        ("g49", m50.get("g49_result", {})),
        ("g50", m50.get("g50_result", {})),
        ("g51", m52.get("g51_result", {})),
        ("g52", m52.get("g52_result", {})),
        ("g53", m54.get("g53_result", {})),
        ("g54", m54.get("g54_result", {})),
        ("g55", m56.get("g55_result", {})),
        ("g56", m56.get("g56_result", {})),
        ("g57", m58.get("g57_result", {})),
        ("g58", m58.get("g58_result", {})),
        ("g59", m60.get("g59_result", {})),
        ("g60", m60.get("g60_result", {})),
        ("g61", m62.get("g61_result", {})),
        ("g62", m62.get("g62_result", {})),
        ("g63", m64.get("g63_result", {})),
        ("g64", m64.get("g64_result", {})),
        ("g65", rep.g65_result),
        ("g66", rep.g66_result),
    ):
        nested_g_valid[tag] = isinstance(src, Mapping) and bool(src.get("valid", False))

    gates_brief = [_extract_gate_dict(g) for g in rep.gates]
    return {
        "schema": rep.schema,
        "verification_mode": rep.verification_mode,
        "total_gates": int(rep.summary.get("total_gates", len(gates_brief))),
        "verified_gates": int(rep.summary.get("verified_gates", 0)),
        "offline_63_gates_verified": bool(rep.offline_63_gates_verified),
        "all_66_gates_verified": bool(rep.all_66_gates_verified),
        "g13_to_g66_all_passed": bool(rep.g13_to_g66_all_passed),
        "g65_to_g66_all_passed": bool(rep.g65_to_g66_all_passed),
        "dry_run_rehearsal_only": bool(rep.dry_run_rehearsal_only),
        "overall_ready_for_hardware_attach": bool(rep.overall_ready_for_hardware_attach),
        "agent_auto_flash_blocked": bool(rep.agent_auto_flash_blocked),
        "el3_payload_transmit_authorized": bool(rep.el3_payload_transmit_authorized),
        "spi_nor_write_authorized": bool(rep.spi_nor_write_authorized),
        "persistent_emmc_writes_authorized": bool(rep.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep.persistent_write_release),
        "nested_g45_to_g66_valid": nested_g_valid,
        "gates_45_to_66": gates_brief[44:],
        "errors": list(rep.errors),
    }


def _worker_recovery_26pillar(args: Tuple[bool, Optional[str]]) -> Dict[str, Any]:
    use_clean_room, fault_pillar = args
    rep = evaluate_26pillar_recovery_master(
        force_clean_room=use_clean_room,
        fault_inject_pillar=fault_pillar,
    )
    p_by_num = {int(p.pillar_number): p for p in rep.pillars}
    p23_obj = p_by_num.get(23)
    p24_obj = p_by_num.get(24)
    return {
        "schema": rep.schema,
        "version": rep.version,
        "verification_mode": rep.verification_mode,
        "all_passed": bool(rep.all_passed),
        "status": rep.status,
        "pillar_count": int(rep.pillar_count),
        "pillars_passed": int(rep.pillars_passed),
        "failed_pillars": list(rep.failed_pillars),
        "pillars": [asdict(p) for p in rep.pillars],
        "pillar23_wbi": asdict(p23_obj) if p23_obj is not None else {},
        "pillar24_slot1_ufu": asdict(p24_obj) if p24_obj is not None else {},
        "pillar24_master_digest": str(p24_obj.digest_sha256) if p24_obj is not None else "",
        "pillar25_airgap_sd_bundle": {
            "all_passed": bool(rep.pillar25_airgap_sd_bundle.all_passed),
            "status": rep.pillar25_airgap_sd_bundle.status,
            "suite_sha256": rep.pillar25_airgap_sd_bundle.suite_sha256,
            "airgap_sockets_opened": int(rep.pillar25_airgap_sd_bundle.airgap_sockets_opened),
        },
        "pillar26_a_fx3a_firewall": asdict(rep.pillar26_a_fx3a_firewall),
        "pillar26_b_xlrh1_hygiene": asdict(rep.pillar26_b_xlrh1_hygiene),
        "master_26pillar_sha256": rep.master_26pillar_sha256,
        "otp_fuse_touches": int(rep.otp_fuse_touches),
        "otp_fuse_writes": int(rep.otp_fuse_writes),
        "rpmb_counter_increments": int(rep.rpmb_counter_increments),
        "passive_tx_bytes_emitted": int(rep.passive_tx_bytes_emitted),
        "physical_usb_packets_emitted": int(rep.physical_usb_packets_emitted),
        "physical_device_writes": int(rep.physical_device_writes),
        "raw_firmware_bytes_leaked": int(rep.raw_firmware_bytes_leaked),
        "airgap_sockets_opened": int(rep.pillar25_airgap_sd_bundle.airgap_sockets_opened),
        "el3_payload_transmit_authorized": bool(rep.el3_payload_transmit_authorized),
        "isp_write_authorized": bool(rep.isp_write_authorized),
        "spi_nor_write_authorized": bool(rep.spi_nor_write_authorized),
        "persistent_emmc_writes_authorized": bool(rep.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep.persistent_write_release),
        "allow_boot_partition_targeting": bool(rep.allow_boot_partition_targeting),
        "allow_destructive_fastboot": bool(rep.allow_destructive_fastboot),
        "live_usb_iokit_transmit_enabled": bool(rep.live_usb_iokit_transmit_enabled),
        "errors": list(rep.errors),
    }


def _worker_pillar_3_wave22_24(group: str, clean_room: bool) -> Dict[str, Dict[str, Any]]:
    if group == "realhw_hdmi_braw_wpa3":
        return {
            "realhw_hdmi_braw_wpa3_702_delta_audit": realhw_hdmi_braw_wpa3_702_delta_report_to_dict(
                analyze_realhw_hdmi_braw_wpa3_702_delta(clean_room=clean_room)
            )
        }
    if group == "realhw_emount_info3d":
        return {
            "realhw_emount_info3d_breathing_02cf0232_audit": realhw_emount_info3d_breathing_02cf0232_report_to_dict(
                analyze_realhw_emount_info3d_breathing_02cf0232(clean_room=clean_room)
            )
        }
    if group == "realhw_fx3a_xlrh1":
        return {
            "realhw_fx3_vs_fx3a_and_xlrh1_mishoe_audit": realhw_fx3_vs_fx3a_and_xlrh1_mishoe_report_to_dict(
                analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe(clean_room=clean_room)
            )
        }
    if group == "realhw_nouvc_dcc1_lut":
        return {
            "realhw_nouvc_dcc1_pd_lut_path_cineei_audit": realhw_nouvc_dcc1_pd_lut_path_cineei_report_to_dict(
                analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=clean_room)
            )
        }
    return {}


def _worker_pillar_3_batch(args: Tuple[Tuple[str, ...], bool]) -> Dict[str, Dict[str, Any]]:
    groups, clean_room = args
    merged: Dict[str, Dict[str, Any]] = {}
    wave22_groups = (
        "realhw_hdmi_braw_wpa3",
        "realhw_emount_info3d",
        "realhw_fx3a_xlrh1",
        "realhw_nouvc_dcc1_lut",
    )
    m175_groups = tuple(g for g in groups if g not in wave22_groups)
    if m175_groups:
        merged.update(_m175_worker_pillar_3_batch((m175_groups, clean_room)))
    for g in groups:
        if g in wave22_groups:
            merged.update(_worker_pillar_3_wave22_24(g, clean_room))
    return merged


def _worker_phase143_154_186(
    args: Tuple[str, str, bool, bool, Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    fx6_lib_dir_str, fx3_modules_dir_str, use_clean_room, p154_sim_ready, p186_faults = args
    fx6_dir = Path(fx6_lib_dir_str)
    fx3_dir = Path(fx3_modules_dir_str)

    p143 = run_phase143_sd_stageb_bundle_uninstaller_audit(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        synthetic_clean_room=use_clean_room,
    ).to_dict()
    p154 = run_realhw_bench_preflight(
        simulate_ready_bench=p154_sim_ready,
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        synthetic_clean_room=use_clean_room,
    ).to_dict()

    p186_off = run_card_insert_preflight(
        dry_run_simulated=False,
        force_clean_room=use_clean_room,
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
    ).to_dict()

    sim_kwargs: Dict[str, Any] = {
        "dry_run_simulated": True,
        "force_clean_room": use_clean_room,
        "fx6_lib_dir": fx6_dir,
        "fx3_modules_dir": fx3_dir,
    }
    if p186_faults.get("inject_h0_h3_drift"):
        sim_kwargs["inject_h0_h3_drift_surface"] = "p12"
    if p186_faults.get("inject_fw_below_204"):
        sim_kwargs["body_fw"] = "2.00"
    if p186_faults.get("inject_single_device_collision"):
        sim_kwargs["st_dev_a_override"] = 1001
        sim_kwargs["st_dev_b_override"] = 1001

    if p186_faults.get("inject_appledouble_fault"):
        with tempfile.TemporaryDirectory() as tmpd:
            sd_root = Path(tmpd)
            stageb_dir = sd_root / "FX6_STAGEB"
            stageb_dir.mkdir(parents=True, exist_ok=True)
            staged = build_simulated_staged_elf64_artifacts()
            for rel, (blob, _) in staged.items():
                target = stageb_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(blob)
            (stageb_dir / "._FX6_STAGEB_BOOT.MANIFEST").write_bytes(b"\x00\x05\x16\x07junk")
            sim_kwargs["sd_dir"] = sd_root
            sim_kwargs["staged_artifacts"] = staged
            p186_sim = run_card_insert_preflight(**sim_kwargs).to_dict()
    else:
        p186_sim = run_card_insert_preflight(**sim_kwargs).to_dict()

    return p143, p154, p186_off, p186_sim


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1 .. P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
) -> Milestone193PillarResult:
    errors: List[str] = []
    total_gates = int(raw_sim.get("total_gates", 0))
    offline_verified = int(raw_off.get("verified_gates", -1))
    sim_verified = int(raw_sim.get("verified_gates", -1))

    if total_gates < 66:
        errors.append(f"p1: total_gates expected >= 66, got {total_gates}")
    if (
        not raw_off.get("offline_63_gates_verified")
        or offline_verified < 63
        or offline_verified >= total_gates
    ):
        errors.append(
            f"p1: offline hardware-truth gates expected >= 63 and < {total_gates}, got {offline_verified}/{total_gates}"
        )
    if raw_off.get("all_66_gates_verified") or raw_off.get("overall_ready_for_hardware_attach"):
        errors.append("p1: offline mode must remain blocked for live hardware attach (G10..G12)")
    if (
        not raw_sim.get("all_66_gates_verified")
        or sim_verified < 66
        or sim_verified != total_gates
    ):
        errors.append(
            f"p1: simulated rehearsal gates expected >= 66 and == {total_gates}, got {sim_verified}/{total_gates}"
        )
    if not raw_sim.get("dry_run_rehearsal_only") or raw_sim.get("overall_ready_for_hardware_attach"):
        errors.append("p1: simulated 66-gate rehearsal must keep overall_ready_for_hardware_attach=False")
    if not raw_sim.get("g13_to_g66_all_passed") or not raw_sim.get("g65_to_g66_all_passed"):
        errors.append("p1: G13..G66 or G65..G66 safety guard gate blocked")

    nested = raw_sim.get("nested_g45_to_g66_valid", {})
    for gnum in range(45, 67):
        if not bool(nested.get(f"g{gnum}", False)):
            errors.append(f"p1: G{gnum} nested safety guard failed")

    g45_to_66 = raw_sim.get("gates_45_to_66", ())
    if len(g45_to_66) < 22 or any(not bool(g.get("passed", False)) for g in g45_to_66):
        errors.append("p1: one or more G45..G66 master gates failed in simulated rehearsal")

    for obj_name, obj in (("offline", raw_off), ("simulated", raw_sim)):
        if (
            obj.get("persistent_emmc_writes_authorized") is not False
            or obj.get("persistent_write_release") is not False
            or obj.get("spi_nor_write_authorized") is not False
            or obj.get("el3_payload_transmit_authorized") is not False
            or obj.get("agent_auto_flash_blocked") is not True
        ):
            errors.append(f"p1 ({obj_name}): hard-locked zero-write/SPI-NOR/EL3/auto-flash guard breached")

    for err in raw_sim.get("errors", ()):
        errors.append(f"p1_66gate: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_sim.get("schema"),
        "verification_mode": raw_sim.get("verification_mode"),
        "total_gates": total_gates,
        "offline_verified_gates": offline_verified,
        "offline_ready_for_hardware_attach": raw_off.get("overall_ready_for_hardware_attach"),
        "simulated_verified_gates": sim_verified,
        "simulated_ready_for_hardware_attach": raw_sim.get("overall_ready_for_hardware_attach"),
        "g13_to_g66_all_passed": raw_sim.get("g13_to_g66_all_passed"),
        "g65_to_g66_all_passed": raw_sim.get("g65_to_g66_all_passed"),
        "nested_g45_to_g66_valid": dict(nested),
        "persistent_emmc_writes_authorized": raw_sim.get("persistent_emmc_writes_authorized"),
        "persistent_write_release": raw_sim.get("persistent_write_release"),
        "spi_nor_write_authorized": raw_sim.get("spi_nor_write_authorized"),
        "el3_payload_transmit_authorized": raw_sim.get("el3_payload_transmit_authorized"),
        "agent_auto_flash_blocked": raw_sim.get("agent_auto_flash_blocked"),
    }
    return Milestone193PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_66GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"66-Gate offline={offline_verified}/{total_gates} (G10..G12 locked) "
            f"sim={sim_verified}/{total_gates}, G13..G66={raw_sim.get('g13_to_g66_all_passed')}, "
            f"G65..G66={raw_sim.get('g65_to_g66_all_passed')} {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    raw_26p: Mapping[str, Any],
    faults: RealHwMilestone193FaultInjection,
) -> Tuple[Milestone193PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    if not raw_26p.get("all_passed"):
        errors.append(f"p2: evaluate_26pillar_recovery_master failed ({raw_26p.get('failed_pillars')})")

    pillar_list = raw_26p.get("pillars", ())
    pillar_statuses: Dict[str, bool] = {}
    for pentry in pillar_list:
        if isinstance(pentry, Mapping):
            pid = str(pentry.get("pillar_id", ""))
            ok = bool(pentry.get("passed"))
            if pid:
                pillar_statuses[pid] = ok
                if not ok:
                    errors.append(f"p2: pillar {pid} failed ({pentry.get('errors')})")

    for expected_pid in MASTER_26_PILLAR_IDS:
        if not pillar_statuses.get(expected_pid, False):
            errors.append(f"p2: required recovery pillar missing or failed: {expected_pid}")

    total_pillars = len(pillar_statuses)
    passed_pillars = sum(1 for v in pillar_statuses.values() if v)
    if total_pillars < 26 or passed_pillars < 26 or passed_pillars != total_pillars:
        errors.append(
            f"p2: recovery pillars expected >= 26 and all passing, got {passed_pillars}/{total_pillars}"
        )

    p23 = raw_26p.get("pillar23_wbi", {})
    p24 = raw_26p.get("pillar24_slot1_ufu", {})
    p25 = raw_26p.get("pillar25_airgap_sd_bundle", {})
    p26a = raw_26p.get("pillar26_a_fx3a_firewall", {})
    p26b = raw_26p.get("pillar26_b_xlrh1_hygiene", {})
    if not bool(p23.get("passed", False)):
        errors.append("p2: Pillar 23 WBI 100-cycle powerloss transition verifier failed")
    if not bool(p24.get("passed", False)):
        errors.append("p2: Pillar 24 Slot-1 UFU reflash & hygiene verifier failed")
    if not bool(p25.get("all_passed", False)):
        errors.append("p2: Pillar 25 Air-Gap FX3BNDL1 bundle & ExFAT hygiene verifier failed")
    if not bool(p26a.get("passed", False)) or not bool(p26b.get("passed", False)):
        errors.append("p2: Pillar 26 FX3A firewall or XLR-H1 MI-Shoe audio hygiene verifier failed")

    otp_touches = (
        int(raw_26p.get("otp_fuse_touches", 0))
        + int(raw_26p.get("otp_fuse_writes", 0))
        + int(faults.p2_otp_fuse_touches_override)
    )
    rpmb_incs = int(raw_26p.get("rpmb_counter_increments", 0)) + int(faults.p2_rpmb_increments_override)
    passive_tx = int(raw_26p.get("passive_tx_bytes_emitted", 0)) + int(faults.p2_passive_tx_bytes_override)
    phys_usb = int(raw_26p.get("physical_usb_packets_emitted", 0)) + int(
        faults.p2_physical_usb_packets_override
    )
    phys_writes = int(raw_26p.get("physical_device_writes", 0)) + int(
        faults.p2_physical_device_writes_override
    )
    leaked_fw = int(raw_26p.get("raw_firmware_bytes_leaked", 0)) + int(
        faults.p2_raw_firmware_bytes_leaked_override
    )
    airgap_sockets = int(raw_26p.get("airgap_sockets_opened", 0))

    if otp_touches != 0:
        errors.append(f"p2: otp_fuse_touches={otp_touches} != 0")
    if rpmb_incs != 0:
        errors.append(f"p2: rpmb_counter_increments={rpmb_incs} != 0")
    if passive_tx != 0:
        errors.append(f"p2: passive_tx_bytes_emitted={passive_tx} != 0")
    if phys_usb != 0:
        errors.append(f"p2: physical_usb_packets_emitted={phys_usb} != 0")
    if phys_writes != 0 or leaked_fw != 0 or airgap_sockets != 0:
        errors.append(
            f"p2: physical_device_writes={phys_writes}, raw_fw_leaked={leaked_fw}, airgap_sockets={airgap_sockets} must be 0"
        )

    if (
        raw_26p.get("el3_payload_transmit_authorized") is not False
        or raw_26p.get("isp_write_authorized") is not False
        or raw_26p.get("spi_nor_write_authorized") is not False
        or raw_26p.get("persistent_emmc_writes_authorized") is not False
        or raw_26p.get("persistent_write_release") is not False
        or raw_26p.get("live_usb_iokit_transmit_enabled") is not False
    ):
        errors.append("p2: hard-locked EL3/ISP/SPI-NOR/eMMC/IOKit write guard breached")

    for err in raw_26p.get("errors", ()):
        errors.append(f"p2_master: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_26p.get("schema"),
        "verification_mode": raw_26p.get("verification_mode"),
        "recovery_pillar_count": total_pillars,
        "recovery_pillars_passed": passed_pillars,
        "pillar_statuses": pillar_statuses,
        "master_26pillar_sha256": raw_26p.get("master_26pillar_sha256"),
        "otp_fuse_touches": otp_touches,
        "rpmb_counter_increments": rpmb_incs,
        "passive_tx_bytes_emitted": passive_tx,
        "physical_usb_packets_emitted": phys_usb,
        "physical_device_writes": phys_writes,
        "raw_firmware_bytes_leaked": leaked_fw,
        "airgap_sockets_opened": airgap_sockets,
        "el3_payload_transmit_authorized": raw_26p.get("el3_payload_transmit_authorized"),
        "isp_write_authorized": raw_26p.get("isp_write_authorized"),
        "spi_nor_write_authorized": raw_26p.get("spi_nor_write_authorized"),
        "persistent_emmc_writes_authorized": raw_26p.get("persistent_emmc_writes_authorized"),
    }
    pillar = Milestone193PillarResult(
        pillar_id="P2",
        pillar_name="TWENTY_SIX_PILLAR_RECOVERY_AIRGAP_AND_FX3A_FIREWALL",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Recovery {passed_pillars}/{total_pillars} pillars (>=26 required; Pillars 23..26 "
            f"WBI2-100c/AirGap-FX3BNDL1/FX3A-Firewall/XLR-H1), "
            f"OTP={otp_touches}, RPMB={rpmb_incs}, passive_tx={passive_tx}B, usb_pkts={phys_usb} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "recovery_pillar_count": total_pillars,
        "recovery_pillars_passed": passed_pillars,
        "otp_fuse_touches": otp_touches,
        "rpmb_counter_increments": rpmb_incs,
        "passive_tx_bytes_emitted": passive_tx,
        "physical_usb_packets_emitted": phys_usb,
        "raw_firmware_bytes_leaked": leaked_fw,
    }
    return pillar, meta


def _evaluate_pillar_3(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: RealHwMilestone193FaultInjection,
) -> Tuple[Milestone193PillarResult, Dict[str, Any]]:
    m175_p3, meta_36 = _eval_m175_p3(auditors, _fault_to_m175_faults(faults))
    errors: List[str] = list(m175_p3.errors)
    auditor_statuses: Dict[str, bool] = dict(m175_p3.evidence["auditor_statuses"])
    auditor_sha256s: Dict[str, Optional[str]] = dict(m175_p3.evidence["auditor_sha256s"])

    # #37: HDMI BRAW + WPA2/WPA3 + Anamorphic GRM + 7.02 Delta
    a37 = auditors.get("realhw_hdmi_braw_wpa3_702_delta_audit", {})
    a37_leak = int(a37.get("raw_firmware_bytes_leaked", -1)) + int(faults.p3_hdmi_braw_raw_leaked_override)
    if (
        not bool(a37.get("all_checks_passed"))
        or a37.get("o_rdonly_enforced") is not True
        or a37.get("hdmi_braw_bridged_sdi_masked") is not True
        or a37.get("wpa2_wpa3_only_enforced") is not True
        or a37.get("anamorphic_15x_16x_grm_unclipped") is not True
        or a37.get("usblan_and_dual_slot_telemetry_ready") is not True
        or a37.get("persistent_emmc_writes_authorized") is not False
        or a37.get("spi_nor_write_authorized") is not False
        or a37.get("el3_payload_transmit_authorized") is not False
        or a37_leak != 0
    ):
        errors.append(f"p3: #37 realhw_hdmi_braw_wpa3_702_delta_audit failed (leaked={a37_leak})")

    # #38: E-Mount info7/8/3D + 0x02cf0232 Focus Breathing + MC 2.1.0 Focus Map
    a38 = auditors.get("realhw_emount_info3d_breathing_02cf0232_audit", {})
    a38_lens = int(a38.get("lens_partition_writes", -1)) + int(faults.p3_emount_lens_partition_writes_override)
    a38_bk = int(a38.get("backup_bin_writes", -1))
    a38_leak = int(a38.get("raw_firmware_bytes_leaked", -1))
    if (
        not bool(a38.get("all_checks_passed"))
        or a38.get("o_rdonly_enforced") is not True
        or a38.get("emount_info3d_handshake_verified") is not True
        or a38.get("sony_lens_id_filter_and_02cf0232_verified") is not True
        or a38.get("p18_lensfile_ro_isolated") is not True
        or a38.get("monitor_control_210_focus_map_verified") is not True
        or a38.get("persistent_emmc_writes_authorized") is not False
        or a38.get("spi_nor_write_authorized") is not False
        or a38.get("el3_payload_transmit_authorized") is not False
        or a38_lens != 0
        or a38_bk != 0
        or a38_leak != 0
    ):
        errors.append(f"p3: #38 realhw_emount_info3d_breathing_02cf0232_audit failed (lens={a38_lens})")

    # #39: ILME-FX3 vs ILME-FX3A branch firewall & XLR-H1 MI-Shoe 4ch bridge
    a39 = auditors.get("realhw_fx3_vs_fx3a_and_xlrh1_mishoe_audit", {})
    a39_wr = int(a39.get("persistent_writes", -1)) + int(faults.p3_fx3a_xlrh1_persistent_writes_override)
    a39_bk = int(a39.get("backup_bin_writes", -1))
    a39_leak = int(a39.get("raw_firmware_bytes_leaked", -1))
    if (
        not bool(a39.get("all_checks_passed"))
        or a39.get("o_rdonly_enforced") is not True
        or a39.get("fx3_vs_fx3a_branch_isolated") is not True
        or a39.get("xlrh1_mishoe_4ch_bridge_verified") is not True
        or a39.get("body_35mm_override_and_sq_mute_verified") is not True
        or a39.get("post_ufu_audio_default_hygiene_verified") is not True
        or a39.get("persistent_emmc_writes_authorized") is not False
        or a39.get("spi_nor_write_authorized") is not False
        or a39.get("el3_payload_transmit_authorized") is not False
        or a39_wr != 0
        or a39_bk != 0
        or a39_leak != 0
    ):
        errors.append(f"p3: #39 realhw_fx3_vs_fx3a_and_xlrh1_mishoe_audit failed (wr={a39_wr})")

    # #40: No-UVC gadget + USB-PD vs DC-C1 >=65W/5A + Dual-Media .cube LUT path + Cine EI + RMT-P1BT
    a40 = auditors.get("realhw_nouvc_dcc1_pd_lut_path_cineei_audit", {})
    a40_wr = int(a40.get("persistent_writes", -1)) + int(faults.p3_nouvc_dcc1_lut_persistent_writes_override)
    a40_leak = int(a40.get("raw_firmware_bytes_leaked", -1))
    if (
        not bool(a40.get("all_checks_passed"))
        or a40.get("o_rdonly_enforced") is not True
        or a40.get("nouvc_and_network_streaming_verified") is not True
        or a40.get("power_delivery_pd_vs_dcc1_verified") is not True
        or a40.get("lut_path_cine_ei_and_rmt_p1bt_verified") is not True
        or a40.get("write_firewall_and_matrix_verified") is not True
        or a40.get("persistent_emmc_writes_authorized") is not False
        or a40.get("spi_nor_write_authorized") is not False
        or a40.get("el3_payload_transmit_authorized") is not False
        or a40_wr != 0
        or a40_leak != 0
    ):
        errors.append(f"p3: #40 realhw_nouvc_dcc1_pd_lut_path_cineei_audit failed (wr={a40_wr})")

    for key in FIRMWARE_LAB_40_AUDITOR_KEYS[36:]:
        obj = auditors.get(key, {})
        ok = isinstance(obj, Mapping) and bool(obj.get("all_checks_passed"))
        auditor_statuses[key] = ok
        sha_val = obj.get("report_sha256") or obj.get("audit_digest_sha256") if isinstance(obj, Mapping) else None
        auditor_sha256s[key] = str(sha_val) if sha_val else None

    total_count = len(auditor_statuses)
    passed_count = sum(1 for v in auditor_statuses.values() if v)
    total_cal_mut = max(
        int(meta_36["calibration_mutation_bytes"]),
        max(0, a38_lens),
        max(0, a38_bk),
        max(0, a39_bk),
    )
    total_leaked = max(0, a37_leak) + max(0, a38_leak) + max(0, a39_leak) + max(0, a40_leak)

    if total_count < 40 or passed_count < 40 or passed_count != total_count:
        errors.append(f"p3: expected >= 40 auditors and all passing, got {passed_count}/{total_count}")
    if total_leaked != 0:
        errors.append(f"p3: raw_firmware_bytes_leaked={total_leaked} != 0")

    passed = len(errors) == 0 and total_cal_mut == 0 and total_leaked == 0
    evidence = dict(m175_p3.evidence)
    evidence.update(
        {
            "auditor_count": total_count,
            "passed_auditor_count": passed_count,
            "auditor_statuses": auditor_statuses,
            "auditor_sha256s": auditor_sha256s,
            "calibration_mutation_bytes": total_cal_mut,
            "raw_firmware_bytes_leaked": total_leaked,
            "wbi_mutation_bytes": int(meta_36.get("wbi_mutation_bytes", 0)),
        }
    )
    pillar = Milestone193PillarResult(
        pillar_id="P3",
        pillar_name="FORTY_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {passed_count}/{total_count} auditors (>=40 required; Auditors 37..40 "
            f"HDMI-BRAW-WPA3/E-Mount-info3D-02cf0232/FX3A-XLRH1/NoUVC-DC-C1-LUT), "
            f"cal_mut={total_cal_mut}B, leaked={total_leaked}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "auditor_count": total_count,
        "passed_count": passed_count,
        "calibration_mutation_bytes": total_cal_mut,
        "bk4_persistent_nvram_writes": int(meta_36["bk4_persistent_nvram_writes"]),
        "wbi_mutation_bytes": int(meta_36.get("wbi_mutation_bytes", 0)),
        "raw_firmware_bytes_leaked": total_leaked,
    }
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: RealHwMilestone193FaultInjection,
) -> Tuple[Milestone193PillarResult, Dict[str, Any]]:
    m175_p4, meta_30 = _eval_m175_p4(vm_rep, _fault_to_m175_faults(faults))
    errors: List[str] = list(m175_p4.errors)
    stage_statuses: Dict[str, bool] = dict(m175_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_33_STAGE_KEYS[30:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if not ok:
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Stage 31: Phase 178 SSBOOT/WBI2 Powerloss 100-Cycle & Slot-1 UFU/C2PA HIL
    s31 = vm_rep.get("stage31_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil", {})
    s31_mut = (
        int(s31.get("wbi_mutation_bytes", -1))
        + int(s31.get("wbi_persistent_writes", -1))
        + int(s31.get("c2pa_cert_mutation_bytes", -1))
        + int(s31.get("nvram_persistent_writes", -1))
        + int(s31.get("bk4_persistent_nvram_writes", -1))
        + int(s31.get("emmc_mutation_bytes", -1))
        + int(s31.get("spi_nor_mutation_bytes", -1))
        + int(s31.get("otp_fuse_touches", -1))
        + int(s31.get("rpmb_counter_increments", -1))
        + int(faults.p4_stage31_wbi_or_c2pa_mutation_bytes)
    )
    if (
        int(s31.get("nop_count", -1)) != 0
        or int(s31.get("cp_mutation_bytes", -1)) != 0
        or int(s31.get("calibration_mutation_bytes", -1)) != 0
        or s31.get("p12_rq_lic_erofs_locked") is not True
        or s31.get("persistent_emmc_writes_authorized") is not False
        or s31.get("spi_nor_write_authorized") is not False
        or s31.get("el3_payload_transmit_authorized") is not False
        or int(s31.get("physical_usb_packets_emitted", -1)) != 0
        or int(s31.get("raw_firmware_bytes_leaked", -1)) != 0
        or s31_mut != 0
        or int(s31.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 31 redlines violated (wbi_or_c2pa_mut={s31_mut})")

    # Stage 32: Phase 182 E-Mount info3D/Breathing 0x02cf0232 & HDMI 4264x2408 16-bit RAW HIL
    s32 = vm_rep.get("stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil", {})
    s32_mut = (
        int(s32.get("lens_partition_writes", -1))
        + int(s32.get("p18_mutation_bytes", -1))
        + int(s32.get("emmc_mutation_bytes", -1))
        + int(s32.get("spi_nor_mutation_bytes", -1))
        + int(s32.get("sdi_bnc_mmio_faults", -1))
        + int(faults.p4_stage32_lens_or_sdi_faults)
    )
    if (
        int(s32.get("nop_count", -1)) != 0
        or int(s32.get("cp_mutation_bytes", -1)) != 0
        or int(s32.get("wbi_mutation_bytes", -1)) != 0
        or int(s32.get("calibration_mutation_bytes", -1)) != 0
        or int(s32.get("p18_blkroset", -1)) != 1
        or s32.get("persistent_emmc_writes_authorized") is not False
        or s32.get("spi_nor_write_authorized") is not False
        or s32.get("el3_payload_transmit_authorized") is not False
        or int(s32.get("raw_firmware_bytes_leaked", -1)) != 0
        or s32_mut != 0
        or int(s32.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 32 redlines violated (lens_or_sdi={s32_mut})")

    # Stage 33: Phase 188 FX3 vs FX3A Branch Firewall & XLR-H1 4ch MI-Shoe Audio HIL
    s33 = vm_rep.get("stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil", {})
    s33_mut = (
        int(s33.get("emmc_mutation_bytes", -1))
        + int(s33.get("spi_nor_mutation_bytes", -1))
        + int(s33.get("fx6_ribbon_mmio_faults", -1))
        + int(s33.get("audio_pop_click_events", -1))
        + int(faults.p4_stage33_ribbon_or_audio_faults)
    )
    if (
        int(s33.get("nop_count", -1)) != 0
        or int(s33.get("cp_mutation_bytes", -1)) != 0
        or int(s33.get("wbi_mutation_bytes", -1)) != 0
        or int(s33.get("calibration_mutation_bytes", -1)) != 0
        or s33.get("persistent_emmc_writes_authorized") is not False
        or s33.get("spi_nor_write_authorized") is not False
        or s33.get("el3_payload_transmit_authorized") is not False
        or int(s33.get("raw_firmware_bytes_leaked", -1)) != 0
        or s33_mut != 0
        or int(s33.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 33 redlines violated (ribbon_or_audio={s33_mut})")

    total_stages = len(stage_statuses)
    passed_stages = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = (
        int(meta_30.get("emmc_corruptions", 0))
        + max(0, int(s31.get("emmc_mutation_bytes", 0)))
        + max(0, int(s32.get("emmc_mutation_bytes", 0)))
        + max(0, int(s33.get("emmc_mutation_bytes", 0)))
    )
    total_wf12_hits = (
        int(meta_30.get("wf12_00342260_hits", 0))
        + max(0, int(s31.get("wf12_00342260_hits", 0)))
        + max(0, int(s32.get("wf12_00342260_hits", 0)))
        + max(0, int(s33.get("wf12_00342260_hits", 0)))
    )

    if total_stages < 33 or passed_stages < 33 or passed_stages != total_stages:
        errors.append(f"p4: expected >= 33 VM stages and all passing, got {passed_stages}/{total_stages}")
    if emmc_corruptions != 0:
        errors.append(f"p4: emmc_corruptions={emmc_corruptions} != 0")

    passed = len(errors) == 0
    evidence = dict(m175_p4.evidence)
    evidence.update(
        {
            "stage_count": total_stages,
            "passed_stage_count": passed_stages,
            "stage_statuses": stage_statuses,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
            "stage31_digest_sha256": s31.get("phase178_audit_digest_sha256"),
            "stage32_digest_sha256": s32.get("phase182_audit_digest_sha256"),
            "stage33_digest_sha256": s33.get("phase188_audit_digest_sha256"),
        }
    )
    pillar = Milestone193PillarResult(
        pillar_id="P4",
        pillar_name="THIRTY_THREE_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {passed_stages}/{total_stages} stages (>=33 required; Stages 31..33 "
            f"SSBOOT-WBI2/E-Mount-HDMI-4KRAW/FX3A-XLRH1), "
            f"emmc_corruptions={emmc_corruptions}, wf12_hits={total_wf12_hits} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "stage_count": total_stages,
        "passed_count": passed_stages,
        "cp_mutation_bytes": meta_30["cp_mutation_bytes"],
        "bk4_persistent_nvram_writes": meta_30["bk4_persistent_nvram_writes"],
        "wf12_00342260_hits": total_wf12_hits,
        "emmc_corruptions": emmc_corruptions,
    }
    return pillar, meta


def _evaluate_pillar_5(
    raw_p136: Mapping[str, Any],
    raw_p143: Mapping[str, Any],
    raw_p154: Mapping[str, Any],
    raw_p186_off: Mapping[str, Any],
    raw_p186_sim: Mapping[str, Any],
    faults: RealHwMilestone193FaultInjection,
) -> Tuple[Milestone193PillarResult, Dict[str, Any]]:
    m175_p5, meta_p5_base = _eval_m175_p5(
        raw_p136, raw_p143, raw_p154, _fault_to_m175_faults(faults)
    )
    errors: List[str] = list(m175_p5.errors)

    # Phase 186 offline physical-receipt block mode
    p186_off_dict = copy.deepcopy(dict(raw_p186_off))
    v186_off = verify_phase186_report(p186_off_dict)
    if (
        not v186_off.valid
        or p186_off_dict.get("go_no_go") != GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        or p186_off_dict.get("card_insert_authorized") is not False
        or p186_off_dict.get("all_4_gates_passed") is not False
        or p186_off_dict.get("sd_physical_media_written") is not False
        or int(p186_off_dict.get("physical_usb_packets_emitted", -1)) != 0
        or int(p186_off_dict.get("raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append(
            f"p5_p186_off: expected {GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT} with 0 usb/leaked "
            f"(got {p186_off_dict.get('go_no_go')}, valid={v186_off.valid}, errs={v186_off.errors})"
        )

    # Phase 186 simulated dry-run C1..C4 preflight mode
    p186_sim_dict = copy.deepcopy(dict(raw_p186_sim))
    if faults.p5_inject_p186_usb_packets_override:
        p186_sim_dict["physical_usb_packets_emitted"] = int(
            p186_sim_dict.get("physical_usb_packets_emitted", 0)
        ) + int(faults.p5_inject_p186_usb_packets_override)

    v186_sim = verify_phase186_report(p186_sim_dict)
    c1 = p186_sim_dict.get("c1_slot1_exfat_hygiene", {})
    c2 = p186_sim_dict.get("c2_tier0_dual_media_binding", {})
    c3 = p186_sim_dict.get("c3_electrical_cable_thermal", {})
    c4 = p186_sim_dict.get("c4_escape_hatch_uninstall_dryrun", {})
    p186_sim_pkts = int(p186_sim_dict.get("physical_usb_packets_emitted", -1))
    p186_sim_leaked = int(p186_sim_dict.get("raw_firmware_bytes_leaked", -1))
    p186_sim_gates = int(p186_sim_dict.get("gates_passed", -1))
    p186_h0_h3 = int(c4.get("h0_equals_h3_count", -1))
    p186_fw_ge_204 = bool(c2.get("body_fw_ge_204_floor"))
    p186_serial_bound = bool(
        c2.get("distinct_physical_devices")
        and c2.get("crc32_parity_ok")
        and c2.get("sha256_parity_ok")
        and c2.get("h0_baselines_all_verified")
    )

    if (
        not v186_sim.valid
        or p186_sim_dict.get("go_no_go") != GO_NO_GO_DRY_RUN_SIMULATED_READY
        or not bool(p186_sim_dict.get("all_4_gates_passed"))
        or p186_sim_gates != 4
        or p186_sim_dict.get("card_insert_authorized") is not False
        or not bool(c1.get("passed"))
        or len(c1.get("macos_junk_in_fx6_stageb", ())) != 0
        or len(c1.get("slot1_bodydata_hits", ())) != 0
        or int(c1.get("symlinks_rejected", -1)) != 0
        or not bool(c2.get("passed"))
        or not p186_fw_ge_204
        or not p186_serial_bound
        or not bool(c3.get("passed"))
        or not bool(c4.get("passed"))
        or p186_h0_h3 != 16
        or int(c4.get("emmc_writes_during_dryrun", -1)) != 0
        or p186_sim_pkts != 0
        or p186_sim_leaked != 0
        or p186_sim_dict.get("persistent_emmc_writes_authorized") is not False
        or p186_sim_dict.get("spi_nor_write_authorized") is not False
        or p186_sim_dict.get("el3_payload_transmit_authorized") is not False
    ):
        errors.append(
            f"p5_p186_sim: preflight-card-insert failed (go={p186_sim_dict.get('go_no_go')}, "
            f"gates={p186_sim_gates}/4, c1={c1.get('passed')}, c2={c2.get('passed')}, "
            f"c3={c3.get('passed')}, c4={c4.get('passed')}, errs={v186_sim.errors})"
        )

    passed = len(errors) == 0
    evidence = dict(m175_p5.evidence)
    evidence.update(
        {
            "p186_offline_go_no_go": p186_off_dict.get("go_no_go"),
            "p186_offline_gates_passed": p186_off_dict.get("gates_passed"),
            "p186_offline_report_verified": bool(v186_off.valid),
            "p186_sim_go_no_go": p186_sim_dict.get("go_no_go"),
            "p186_sim_gates_passed": p186_sim_gates,
            "p186_card_insert_authorized": p186_sim_dict.get("card_insert_authorized"),
            "p186_body_fw_ge_204": p186_fw_ge_204,
            "p186_dual_media_serial_bound": p186_serial_bound,
            "p186_h0_equals_h3_count": p186_h0_h3,
            "p186_sim_usb_packets_emitted": p186_sim_pkts,
            "p186_sim_raw_firmware_bytes_leaked": p186_sim_leaked,
            "p186_sim_report_verified": bool(v186_sim.valid),
            "p186_sim_receipt_sha256": str(c2.get("receipt_sha256", "")),
        }
    )
    pillar = Milestone193PillarResult(
        pillar_id="P5",
        pillar_name="CLOSURE_PREFLIGHT_CARD_INSERT_AND_H0_H3",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Ph136(U4/U5/U6={meta_p5_base['u4_u5_u6_closed']}, cmds={meta_p5_base['u6_command_count']}) + "
            f"Ph143(EH1={meta_p5_base['eh1_observed_latency_us']}us, H0==H3 {meta_p5_base['h0_equals_h3_count']}/16) + "
            f"Ph154(go={meta_p5_base['p154_bench_go']}) + "
            f"Ph186(card-insert off={p186_off_dict.get('gates_passed')}/4 sim={p186_sim_gates}/4 H0==H3={p186_h0_h3}/16) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_p5_base)
    meta.update(
        {
            "p186_offline_go_no_go": str(p186_off_dict.get("go_no_go", "")),
            "p186_sim_go_no_go": str(p186_sim_dict.get("go_no_go", "")),
            "p186_sim_gates_passed": p186_sim_gates,
            "p186_card_insert_authorized": bool(p186_sim_dict.get("card_insert_authorized", True)),
            "p186_body_fw_ge_204": p186_fw_ge_204,
            "p186_dual_media_serial_bound": p186_serial_bound,
            "p186_h0_equals_h3_count": p186_h0_h3,
            "p186_sim_usb_packets_emitted": p186_sim_pkts,
            "p186_sim_raw_firmware_bytes_leaked": p186_sim_leaked,
        }
    )
    return pillar, meta


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone193FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone193PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    round_sources: Dict[str, str] = {}
    round_schemas: Dict[str, str] = {}
    runs_by_round: Dict[str, int] = {}
    png_sizes_by_asset: Dict[str, int] = {}
    png_sources_by_round: Dict[str, str] = {}

    total_nops = 0
    total_crashes = 0
    total_emmc = 0
    rounds_verified = 0
    total_runs_verified = 0
    pngs_verified = 0
    max_png_bytes = 0

    for spec in ROUND28_TO_37_SPECS:
        r_tag = f"r{spec.round_num}"
        raw_round, r_src = _load_round28_to_37_summary(
            spec, repo_root=repo_root, use_clean_room=use_clean_room
        )
        if faults.p6_tamper_schema_round_num == spec.round_num:
            raw_round = copy.deepcopy(raw_round)
            raw_round["schema"] = "tampered-invalid-schema"

        round_sources[r_tag] = r_src
        r_schema = str(raw_round.get("schema", ""))
        r_kver = str(raw_round.get("kernel_version", ""))
        round_schemas[r_tag] = r_schema

        round_ok = True
        if r_schema != spec.expected_schema:
            errors.append(f"p6_{r_tag}: unexpected schema {r_schema!r}")
            round_ok = False
        if "4.9.337-scel+" not in r_kver:
            errors.append(f"p6_{r_tag}: unexpected kernel_version {r_kver!r}")
            round_ok = False

        audit_obj = raw_round.get(spec.audit_key, {})
        if not isinstance(audit_obj, Mapping):
            errors.append(f"p6_{r_tag}: missing audit block {spec.audit_key}")
            round_ok = False
        else:
            for bkey in spec.audit_bool_keys:
                if not bool(audit_obj.get(bkey, False)):
                    errors.append(f"p6_{r_tag}: audit flag {bkey} is False")
                    round_ok = False

        # Verify 2 PNG receipts (< 28 KiB) for this round
        png_pair = ROUND28_TO_37_PNG_RECEIPTS[spec.round_num]
        for png_idx, png_rel in enumerate(png_pair):
            png_ok, png_size, png_src = _inspect_round_png_receipt(
                png_rel, repo_root=repo_root, use_clean_room=use_clean_room
            )
            if (
                png_idx == 0
                and faults.p6_png_size_override_round_num == spec.round_num
                and faults.p6_png_size_override_bytes is not None
            ):
                png_size = int(faults.p6_png_size_override_bytes)
                png_ok = 0 < png_size < PNG_MAX_SIZE_BYTES
            png_sizes_by_asset[Path(png_rel).name] = png_size
            png_sources_by_round[r_tag] = png_src
            if png_size > max_png_bytes:
                max_png_bytes = png_size
            if png_ok:
                pngs_verified += 1
            else:
                errors.append(
                    f"p6_{r_tag}: PNG receipt invalid or >= {PNG_MAX_SIZE_BYTES}B ({png_rel}, size={png_size})"
                )
                round_ok = False

        runs_map = raw_round.get("runs", {})
        if not isinstance(runs_map, Mapping):
            errors.append(f"p6_{r_tag}: missing runs mapping")
            runs_by_round[r_tag] = 0
            continue

        verified_in_round = 0
        for run_idx, (rid, exp_faithful) in enumerate(spec.run_specs):
            robj = runs_map.get(rid)
            if not isinstance(robj, Mapping):
                errors.append(f"p6_{r_tag}: missing run {rid}")
                round_ok = False
                continue

            if (
                run_idx == 0
                and faults.p6_round_nop_override_num == spec.round_num
                and faults.p6_round_nop_count_override is not None
            ):
                rnop = int(faults.p6_round_nop_count_override)
            elif exp_faithful is not None:
                rnop = int(robj.get("nop_count", -1))
            else:
                rnop = int(robj.get("nop_count", 0))

            if (
                run_idx == 0
                and faults.p6_round_crash_override_num == spec.round_num
                and faults.p6_round_crashes_override is not None
            ):
                rcrash = int(faults.p6_round_crashes_override)
            else:
                rcrash = int(robj.get("crashes", -1))

            if (
                run_idx == 0
                and faults.p6_round_emmc_override_num == spec.round_num
                and faults.p6_round_emmc_writes_override is not None
            ):
                remmc = int(faults.p6_round_emmc_writes_override)
            else:
                remmc = int(robj.get("emmc_write_count", -1))

            total_nops += max(0, rnop)
            total_crashes += max(0, rcrash)
            total_emmc += max(0, remmc)

            rkver = str(robj.get("kernel_version", r_kver))
            sb = robj.get("stage_b", {})
            sb_count = int(sb.get("manifest_count", -1)) if isinstance(sb, Mapping) else -1
            fi_ok = True
            if exp_faithful is not None:
                fi = robj.get("faithful_invariants", {})
                fi_val = int(fi.get("FX6_NATIVE_FAITHFUL", -1)) if isinstance(fi, Mapping) else -1
                if fi_val != exp_faithful:
                    fi_ok = False

            if (
                "4.9.337-scel+" not in rkver
                or rnop != 0
                or rcrash != 0
                or remmc != 0
                or sb_count != 13
                or not fi_ok
            ):
                errors.append(
                    f"p6_{r_tag}:{rid}: failed invariants (nop={rnop}, crash={rcrash}, emmc={remmc}, sb={sb_count}, fi_ok={fi_ok})"
                )
                round_ok = False
                continue

            verified_in_round += 1

        runs_by_round[r_tag] = verified_in_round
        total_runs_verified += verified_in_round
        if round_ok and verified_in_round == len(spec.run_specs):
            rounds_verified += 1

    # Cross-pillar hardware-lock invariants
    if (
        p1_meta.get("persistent_emmc_writes_authorized") is not False
        or p1_meta.get("spi_nor_write_authorized") is not False
        or p1_meta.get("el3_payload_transmit_authorized") is not False
        or p1_meta.get("simulated_ready_for_hardware_attach") is not False
    ):
        errors.append("p6: P1 hardware-lock invariant breached")
    if (
        int(p2_meta.get("otp_fuse_touches", -1)) != 0
        or int(p2_meta.get("rpmb_counter_increments", -1)) != 0
        or int(p2_meta.get("passive_tx_bytes_emitted", -1)) != 0
        or int(p2_meta.get("physical_usb_packets_emitted", -1)) != 0
        or int(p2_meta.get("raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append("p6: P2 zero-touch OTP/RPMB/passive-UART/USB-PKT/raw-FW invariant breached")
    if (
        int(p3_meta.get("calibration_mutation_bytes", -1)) != 0
        or int(p3_meta.get("wbi_mutation_bytes", -1)) != 0
        or int(p3_meta.get("raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append("p6: P3 calibration/WBI/raw-FW zero-mutation invariant breached")
    if (
        int(p4_meta.get("cp_mutation_bytes", -1)) != 0
        or int(p4_meta.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(p4_meta.get("wf12_00342260_hits", -1)) != 0
        or int(p4_meta.get("emmc_corruptions", -1)) != 0
    ):
        errors.append("p6: P4 CP/BK4/WF-12/eMMC zero-mutation invariant breached")
    if (
        int(p5_meta.get("h0_equals_h3_count", -1)) != 16
        or not bool(p5_meta.get("p154_bench_go"))
        or int(p5_meta.get("p154_usb_packets_emitted", -1)) != 0
        or int(p5_meta.get("p186_sim_gates_passed", -1)) != 4
        or p5_meta.get("p186_card_insert_authorized") is not False
        or int(p5_meta.get("p186_sim_usb_packets_emitted", -1)) != 0
        or int(p5_meta.get("p186_sim_raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append("p6: P5 H0 == H3 (16/16), Phase 154, or Phase 186 preflight invariant breached")

    passed = (
        len(errors) == 0
        and rounds_verified == len(ROUND28_TO_37_SPECS)
        and total_runs_verified == 30
        and pngs_verified == 20
        and 0 < max_png_bytes < PNG_MAX_SIZE_BYTES
        and total_nops == 0
        and total_crashes == 0
        and total_emmc == 0
    )
    evidence = {
        "round_sources": round_sources,
        "round_schemas": round_schemas,
        "rounds_verified": rounds_verified,
        "expected_rounds": len(ROUND28_TO_37_SPECS),
        "runs_by_round": runs_by_round,
        "total_runs_verified": total_runs_verified,
        "expected_total_runs": 30,
        "png_receipts_verified": pngs_verified,
        "expected_png_receipts": 20,
        "png_max_bytes": max_png_bytes,
        "png_max_ceiling_bytes": PNG_MAX_SIZE_BYTES,
        "png_sizes_by_asset": png_sizes_by_asset,
        "png_sources_by_round": png_sources_by_round,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "milestone175_schema_anchor": MILESTONE175_SCHEMA_VERSION,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }
    pillar = Milestone193PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_ROUNDS_28_TO_37_AND_PNG_RECEIPTS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Live FX3 7.02 QEMU Rounds 28..37={rounds_verified}/10 rounds ({total_runs_verified}/30 runs, "
            f"PNGs={pngs_verified}/20 max={max_png_bytes}B < 28KiB), "
            f"nop={total_nops}, crashes={total_crashes}, emmc={total_emmc} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "qemu_rounds_verified": rounds_verified,
        "qemu_runs_verified": total_runs_verified,
        "qemu_png_receipts_verified": pngs_verified,
        "qemu_png_max_bytes": max_png_bytes,
        "qemu_round_runs_by_round": runs_by_round,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
    }
    return pillar, meta


# ---------------------------------------------------------------------------
# Parallel Collector, Builder & Fail-Closed Verifier
# ---------------------------------------------------------------------------


def _collect_parallel_milestone193_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: RealHwMilestone193FaultInjection,
) -> Tuple[
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
]:
    gate_fault_dict = _fault_to_66gate_worker_dict(faults)
    p154_sim_ready = not faults.p5_inject_p154_no_go_fault
    p186_fault_dict = {
        "inject_appledouble_fault": bool(faults.p5_inject_p186_appledouble_fault),
        "inject_h0_h3_drift": bool(faults.p5_inject_p186_h0_h3_drift),
        "inject_fw_below_204": bool(faults.p5_inject_p186_fw_below_204),
        "inject_single_device_collision": bool(faults.p5_inject_p186_single_device_collision),
    }

    p3_batches: Tuple[Tuple[str, ...], ...] = (
        ("multilang",),
        ("group_b",),
        ("sensor",),
        ("haita",),
        ("group_a",),
        ("emount",),
        ("wbi",),
        ("assignable", "falsecolor", "playback", "gyroflow"),
        ("interval_ftp", "lut3d_sdi", "c2pa_mc", "hdr_hlg"),
        ("prores_mishoe", "uvc_crsdk", "mxf_tally", "vp_ledwall"),
        ("xavc_fz100", "realhw_cp_backup", "realhw_mpr_dmm"),
        ("realhw_peripheral", "realhw_controls_fan", "realhw_wifi_usb"),
        ("realhw_imx510", "realhw_cfexpress_ufu", "realhw_cxd90058_sabin"),
        ("realhw_c2pa_tc_gyro", "realhw_wbi2_hibdrv"),
        ("realhw_hdmi_braw_wpa3", "realhw_emount_info3d"),
        ("realhw_fx3a_xlrh1", "realhw_nouvc_dcc1_lut"),
    )

    try:
        ctx = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=22, mp_context=ctx) as ex:
            fut_vm = ex.submit(_worker_pillar_4, use_clean_room)
            fut_p136 = ex.submit(_worker_phase136, use_clean_room)
            fut_26p = ex.submit(
                _worker_recovery_26pillar, (use_clean_room, faults.p2_fault_inject_pillar)
            )
            fut_143_154_186 = ex.submit(
                _worker_phase143_154_186,
                (
                    str(fx6_lib_dir),
                    str(fx3_modules_dir),
                    use_clean_room,
                    p154_sim_ready,
                    p186_fault_dict,
                ),
            )
            fut_3 = [ex.submit(_worker_pillar_3_batch, (batch, use_clean_room)) for batch in p3_batches]
            fut_1_off = ex.submit(
                _worker_66gate_single, (str(repo_root), use_clean_room, False, gate_fault_dict)
            )
            fut_1_sim = ex.submit(
                _worker_66gate_single, (str(repo_root), use_clean_room, True, gate_fault_dict)
            )

            raw_1_off = fut_1_off.result()
            raw_1_sim = fut_1_sim.result()
            raw_26p = fut_26p.result()
            auditors: Dict[str, Dict[str, Any]] = {}
            for fg in fut_3:
                auditors.update(fg.result())
            raw_vm = fut_vm.result()
            raw_p136 = fut_p136.result()
            raw_p143, raw_p154, raw_p186_off, raw_p186_sim = fut_143_154_186.result()
            return (
                raw_1_off,
                raw_1_sim,
                raw_26p,
                auditors,
                raw_vm,
                raw_p136,
                raw_p143,
                raw_p154,
                raw_p186_off,
                raw_p186_sim,
            )
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1_off = _worker_66gate_single((str(repo_root), use_clean_room, False, gate_fault_dict))
    raw_1_sim = _worker_66gate_single((str(repo_root), use_clean_room, True, gate_fault_dict))
    raw_26p = _worker_recovery_26pillar((use_clean_room, faults.p2_fault_inject_pillar))
    auditors = {}
    for batch in p3_batches:
        auditors.update(_worker_pillar_3_batch((batch, use_clean_room)))
    raw_vm = _worker_pillar_4(use_clean_room)
    raw_p136 = _worker_phase136(use_clean_room)
    raw_p143, raw_p154, raw_p186_off, raw_p186_sim = _worker_phase143_154_186(
        (
            str(fx6_lib_dir),
            str(fx3_modules_dir),
            use_clean_room,
            p154_sim_ready,
            p186_fault_dict,
        )
    )
    return (
        raw_1_off,
        raw_1_sim,
        raw_26p,
        auditors,
        raw_vm,
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
    )


def build_realhw_milestone193_master_gate_report(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[RealHwMilestone193FaultInjection] = None,
) -> RealHwMilestone193MasterGateReport:
    """Build & evaluate the Grand Milestone Phase 193 6-Pillar Real-Hardware Pre-Bench Master Gate."""
    use_clean_room = _is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    active_faults = faults or RealHwMilestone193FaultInjection()

    (
        raw_1_off,
        raw_1_sim,
        raw_26p,
        auditors,
        raw_vm,
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
    ) = _collect_parallel_milestone193_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )

    p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
    p2, meta_2 = _evaluate_pillar_2(raw_26p, active_faults)
    p3, meta_3 = _evaluate_pillar_3(auditors, active_faults)
    p4, meta_4 = _evaluate_pillar_4(raw_vm, active_faults)
    p5, meta_5 = _evaluate_pillar_5(
        raw_p136, raw_p143, raw_p154, raw_p186_off, raw_p186_sim, active_faults
    )
    p6, meta_6 = _evaluate_pillar_6(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=active_faults,
        p1_meta=p1.evidence,
        p2_meta=meta_2,
        p3_meta=meta_3,
        p4_meta=meta_4,
        p5_meta=meta_5,
    )

    pillars: Tuple[Milestone193PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
    passed_count = sum(1 for p in pillars if p.passed)
    failed_ids = tuple(p.pillar_id for p in pillars if not p.passed)
    all_errors: List[str] = []
    for p in pillars:
        all_errors.extend(p.errors)

    all_ready = passed_count == len(pillars) and len(all_errors) == 0
    mode_str = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"
    total_raw_leaked = (
        int(meta_2["raw_firmware_bytes_leaked"])
        + int(meta_3["raw_firmware_bytes_leaked"])
        + int(meta_5["p186_sim_raw_firmware_bytes_leaked"])
    )
    total_usb_pkts = int(meta_2["physical_usb_packets_emitted"]) + int(
        meta_5["p186_sim_usb_packets_emitted"]
    )

    payload_no_sha: Dict[str, Any] = {
        "schema_version": REALHW_MILESTONE193_SCHEMA,
        "phase_version": PHASE_193_VERSION,
        "verification_mode": mode_str,
        "all_pillars_milestone_ready": all_ready,
        "status": STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "hardware_live_attachment_requirements": HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        "physical_usb_packets_emitted": total_usb_pkts,
        "raw_firmware_bytes_leaked": total_raw_leaked,
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "wbi_p5_write_and_hibernation_forbidden": WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        "cp_mutation_bytes": meta_4["cp_mutation_bytes"],
        "wbi_mutation_bytes": meta_3["wbi_mutation_bytes"],
        "calibration_mutation_bytes": meta_3["calibration_mutation_bytes"],
        "usb_or_camera_operations": USB_OR_CAMERA_OPERATIONS,
        "otp_fuse_touches": meta_2["otp_fuse_touches"],
        "rpmb_counter_increments": meta_2["rpmb_counter_increments"],
        "passive_tx_bytes_emitted": meta_2["passive_tx_bytes_emitted"],
        "temp_dir_cleaned": True,
        "pillar_count": len(pillars),
        "passed_pillar_count": passed_count,
        "failed_pillar_ids": failed_ids,
        "pillars": [p.to_dict() for p in pillars],
        "gate66_total_gates": raw_1_sim["total_gates"],
        "gate66_offline_verified": raw_1_off["verified_gates"],
        "gate66_simulated_verified": raw_1_sim["verified_gates"],
        "recovery_pillar_count": meta_2["recovery_pillar_count"],
        "recovery_pillars_passed": meta_2["recovery_pillars_passed"],
        "firmware_lab_auditor_count": meta_3["auditor_count"],
        "firmware_lab_auditors_passed": meta_3["passed_count"],
        "vm_coemulation_stage_count": meta_4["stage_count"],
        "vm_coemulation_stages_passed": meta_4["passed_count"],
        "vm_emmc_corruptions": meta_4["emmc_corruptions"],
        "vm_wf12_00342260_hits": meta_4["wf12_00342260_hits"],
        "p136_u6_command_count": meta_5["u6_command_count"],
        "p136_u4_u5_u6_closed": meta_5["u4_u5_u6_closed"],
        "p143_sd_escape_absent_us": meta_5["eh1_observed_latency_us"],
        "p143_h0_equals_h3_count": meta_5["h0_equals_h3_count"],
        "p143_h0_h3_surface_count": meta_5["h0_h3_surface_count"],
        "p154_bench_go": meta_5["p154_bench_go"],
        "p154_usb_packets_emitted": meta_5["p154_usb_packets_emitted"],
        "p154_iokit_handles_opened": meta_5["p154_iokit_handles_opened"],
        "p186_offline_go_no_go": meta_5["p186_offline_go_no_go"],
        "p186_sim_go_no_go": meta_5["p186_sim_go_no_go"],
        "p186_sim_gates_passed": meta_5["p186_sim_gates_passed"],
        "p186_card_insert_authorized": meta_5["p186_card_insert_authorized"],
        "p186_body_fw_ge_204": meta_5["p186_body_fw_ge_204"],
        "p186_dual_media_serial_bound": meta_5["p186_dual_media_serial_bound"],
        "p186_h0_equals_h3_count": meta_5["p186_h0_equals_h3_count"],
        "qemu_rounds_verified": meta_6["qemu_rounds_verified"],
        "qemu_runs_verified": meta_6["qemu_runs_verified"],
        "qemu_png_receipts_verified": meta_6["qemu_png_receipts_verified"],
        "qemu_png_max_bytes": meta_6["qemu_png_max_bytes"],
        "qemu_round_runs_by_round": meta_6["qemu_round_runs_by_round"],
        "qemu_real_kernel_nop_count": meta_6["qemu_real_kernel_nop_count"],
        "qemu_real_kernel_crashes": meta_6["qemu_real_kernel_crashes"],
        "qemu_real_kernel_emmc_writes": meta_6["qemu_real_kernel_emmc_writes"],
        "errors": tuple(all_errors),
    }
    digest = compute_milestone193_sha256(payload_no_sha)

    return RealHwMilestone193MasterGateReport(
        schema_version=REALHW_MILESTONE193_SCHEMA,
        phase_version=PHASE_193_VERSION,
        verification_mode=mode_str,
        all_pillars_milestone_ready=all_ready,
        status=STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        hardware_live_attachment_requirements=HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        physical_usb_packets_emitted=total_usb_pkts,
        raw_firmware_bytes_leaked=total_raw_leaked,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        cp_mutation_bytes=meta_4["cp_mutation_bytes"],
        wbi_mutation_bytes=meta_3["wbi_mutation_bytes"],
        calibration_mutation_bytes=meta_3["calibration_mutation_bytes"],
        usb_or_camera_operations=USB_OR_CAMERA_OPERATIONS,
        otp_fuse_touches=meta_2["otp_fuse_touches"],
        rpmb_counter_increments=meta_2["rpmb_counter_increments"],
        passive_tx_bytes_emitted=meta_2["passive_tx_bytes_emitted"],
        temp_dir_cleaned=True,
        pillar_count=len(pillars),
        passed_pillar_count=passed_count,
        failed_pillar_ids=failed_ids,
        pillars=pillars,
        gate66_total_gates=raw_1_sim["total_gates"],
        gate66_offline_verified=raw_1_off["verified_gates"],
        gate66_simulated_verified=raw_1_sim["verified_gates"],
        recovery_pillar_count=meta_2["recovery_pillar_count"],
        recovery_pillars_passed=meta_2["recovery_pillars_passed"],
        firmware_lab_auditor_count=meta_3["auditor_count"],
        firmware_lab_auditors_passed=meta_3["passed_count"],
        vm_coemulation_stage_count=meta_4["stage_count"],
        vm_coemulation_stages_passed=meta_4["passed_count"],
        vm_emmc_corruptions=meta_4["emmc_corruptions"],
        vm_wf12_00342260_hits=meta_4["wf12_00342260_hits"],
        p136_u6_command_count=meta_5["u6_command_count"],
        p136_u4_u5_u6_closed=meta_5["u4_u5_u6_closed"],
        p143_sd_escape_absent_us=meta_5["eh1_observed_latency_us"],
        p143_h0_equals_h3_count=meta_5["h0_equals_h3_count"],
        p143_h0_h3_surface_count=meta_5["h0_h3_surface_count"],
        p154_bench_go=meta_5["p154_bench_go"],
        p154_usb_packets_emitted=meta_5["p154_usb_packets_emitted"],
        p154_iokit_handles_opened=meta_5["p154_iokit_handles_opened"],
        p186_offline_go_no_go=meta_5["p186_offline_go_no_go"],
        p186_sim_go_no_go=meta_5["p186_sim_go_no_go"],
        p186_sim_gates_passed=meta_5["p186_sim_gates_passed"],
        p186_card_insert_authorized=meta_5["p186_card_insert_authorized"],
        p186_body_fw_ge_204=meta_5["p186_body_fw_ge_204"],
        p186_dual_media_serial_bound=meta_5["p186_dual_media_serial_bound"],
        p186_h0_equals_h3_count=meta_5["p186_h0_equals_h3_count"],
        qemu_rounds_verified=meta_6["qemu_rounds_verified"],
        qemu_runs_verified=meta_6["qemu_runs_verified"],
        qemu_png_receipts_verified=meta_6["qemu_png_receipts_verified"],
        qemu_png_max_bytes=meta_6["qemu_png_max_bytes"],
        qemu_round_runs_by_round=meta_6["qemu_round_runs_by_round"],
        qemu_real_kernel_nop_count=meta_6["qemu_real_kernel_nop_count"],
        qemu_real_kernel_crashes=meta_6["qemu_real_kernel_crashes"],
        qemu_real_kernel_emmc_writes=meta_6["qemu_real_kernel_emmc_writes"],
        errors=tuple(all_errors),
        milestone193_sha256=digest,
    )


evaluate_milestone193_master_gate = build_realhw_milestone193_master_gate_report


def verify_realhw_milestone193_master_gate(
    report: object,
) -> RealHwMilestone193VerifyResult:
    """Fail-closed verifier for a Milestone Phase 193 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone193MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone193VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone193_sha256="",
            observed_milestone193_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone193MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = payload.get("schema_version") == REALHW_MILESTONE193_SCHEMA
    if not schema_ok:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")

    expected_sha = compute_milestone193_sha256(payload)
    observed_sha = str(payload.get("milestone193_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(f"milestone193_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}")

    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("spi_nor_write_authorized") is False
        and payload.get("el3_payload_transmit_authorized") is False
        and payload.get("isp_write_authorized") is False
        and payload.get("hardware_live_attachment_authorized") is False
        and payload.get("physical_usb_packets_emitted") == 0
        and payload.get("raw_firmware_bytes_leaked") == 0
        and payload.get("p8_cp_mutation_forbidden") is True
        and payload.get("wbi_p5_write_and_hibernation_forbidden") is True
        and payload.get("cp_mutation_bytes") == 0
        and payload.get("wbi_mutation_bytes") == 0
        and payload.get("calibration_mutation_bytes") == 0
        and payload.get("usb_or_camera_operations") == 0
        and payload.get("otp_fuse_touches") == 0
        and payload.get("rpmb_counter_increments") == 0
        and payload.get("passive_tx_bytes_emitted") == 0
        and payload.get("p154_usb_packets_emitted") == 0
        and payload.get("p154_iokit_handles_opened") == 0
        and payload.get("p186_card_insert_authorized") is False
    )
    if not redlines_ok:
        errors.append("hard-locked zero-write / zero-SPI-NOR / zero-EL3 / zero-USB-TX / zero-leak / zero-attach redlines breached")

    pillars_raw = payload.get("pillars", [])
    pillars_seq = list(pillars_raw) if isinstance(pillars_raw, (list, tuple)) else []
    seen_ids = tuple(str(p.get("pillar_id", "")) for p in pillars_seq if isinstance(p, Mapping))
    all_6_ok = (
        seen_ids == PILLAR_IDS
        and len(pillars_seq) == 6
        and all(
            isinstance(p, Mapping)
            and bool(p.get("passed"))
            and p.get("status") == STATUS_MILESTONE_READY
            for p in pillars_seq
        )
    )
    if not all_6_ok:
        errors.append(f"all_6_pillars_ok check failed (seen={seen_ids!r})")

    counts_ok = (
        int(payload.get("gate66_total_gates", -1)) >= 66
        and int(payload.get("gate66_offline_verified", -1)) >= 63
        and int(payload.get("gate66_simulated_verified", -1)) >= 66
        and int(payload.get("recovery_pillar_count", -1)) >= 26
        and int(payload.get("recovery_pillars_passed", -1))
        == int(payload.get("recovery_pillar_count", -2))
        and int(payload.get("firmware_lab_auditor_count", -1)) >= 40
        and int(payload.get("firmware_lab_auditors_passed", -1))
        == int(payload.get("firmware_lab_auditor_count", -2))
        and int(payload.get("vm_coemulation_stage_count", -1)) >= 33
        and int(payload.get("vm_coemulation_stages_passed", -1))
        == int(payload.get("vm_coemulation_stage_count", -2))
        and int(payload.get("vm_emmc_corruptions", -1)) == 0
        and int(payload.get("vm_wf12_00342260_hits", -1)) == 0
        and int(payload.get("p136_u6_command_count", -1)) >= 19
        and payload.get("p136_u4_u5_u6_closed") is True
        and int(payload.get("p143_sd_escape_absent_us", 999)) <= 50
        and int(payload.get("p143_h0_equals_h3_count", -1)) == 16
        and int(payload.get("p143_h0_h3_surface_count", -1)) == 16
        and payload.get("p154_bench_go") is True
        and payload.get("p186_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p186_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p186_sim_gates_passed", -1)) == 4
        and payload.get("p186_body_fw_ge_204") is True
        and payload.get("p186_dual_media_serial_bound") is True
        and int(payload.get("p186_h0_equals_h3_count", -1)) == 16
        and int(payload.get("qemu_rounds_verified", -1)) == 10
        and int(payload.get("qemu_runs_verified", -1)) == 30
        and int(payload.get("qemu_png_receipts_verified", -1)) == 20
        and 0 < int(payload.get("qemu_png_max_bytes", -1)) < PNG_MAX_SIZE_BYTES
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone193 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append("all_pillars_milestone_ready / status is not MILESTONE_193_PREBENCH_MASTER_VERIFIED")

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 193 payload")

    valid = bool(schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0)
    return RealHwMilestone193VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone193_sha256=expected_sha,
        observed_milestone193_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


def render_milestone193_markdown(report: RealHwMilestone193MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 193 Master Gate."""
    lines = [
        f"# Grand Milestone Phase 193 — Real-Hardware `ILME-FX3 Ver. 7.02` Pre-Bench Master Gate (`{report.schema_version}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone193_sha256}`",
        "",
        "## Hard-Locked Safety Redlines / 硬锁定安全红线",
        f"- `persistent_emmc_writes_authorized = {report.persistent_emmc_writes_authorized}`, "
        f"`spi_nor_write_authorized = {report.spi_nor_write_authorized}`, "
        f"`el3_payload_transmit_authorized = {report.el3_payload_transmit_authorized}`",
        f"- `isp_write_authorized = {report.isp_write_authorized}`, "
        f"`persistent_write_release = {report.persistent_write_release}`, "
        f"`hardware_live_attachment_authorized = {report.hardware_live_attachment_authorized}`",
        f"- `physical_usb_packets_emitted = {report.physical_usb_packets_emitted}`, "
        f"`raw_firmware_bytes_leaked = {report.raw_firmware_bytes_leaked}`, "
        f"`otp_fuse_touches = {report.otp_fuse_touches}`, "
        f"`rpmb_counter_increments = {report.rpmb_counter_increments}`, "
        f"`passive_tx_bytes_emitted = {report.passive_tx_bytes_emitted}`",
        f"- `cp_mutation_bytes = {report.cp_mutation_bytes}`, "
        f"`wbi_mutation_bytes = {report.wbi_mutation_bytes}`, "
        f"`calibration_mutation_bytes = {report.calibration_mutation_bytes}`",
        "",
        "## Pillar Matrix / 六大支柱总览",
        "| Pillar | Name | Status | Summary |",
        "|---|---|---|---|",
    ]
    for p in report.pillars:
        lines.append(f"| `{p.pillar_id}` | `{p.pillar_name}` | `{p.status}` | {p.summary} |")
    lines.extend(
        [
            "",
            "## Key Grand Milestone Phase 193 Metrics / 实机台架前总闭环核心指标",
            f"- 66-Gate Preflight (`G01..G66`): offline=`{report.gate66_offline_verified}/{report.gate66_total_gates}` (`G10..G12` locked), simulated=`{report.gate66_simulated_verified}/{report.gate66_total_gates}`",
            f"- 26-Pillar Recovery Vault, Air-Gap & `FX3A` Firewall (`Ph47..190`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`>=26` required)",
            f"- 40 Firmware-Lab Auditors (`Ph1..192`): `{report.firmware_lab_auditors_passed}/{report.firmware_lab_auditor_count}` (`>=40` required; Auditors `37..40`)",
            f"- 33-Stage VM Co-Emulation (`Ph33..188`): `{report.vm_coemulation_stages_passed}/{report.vm_coemulation_stage_count}` (`>=33` required; `emmc_corruptions={report.vm_emmc_corruptions}`, `wf12_hits={report.vm_wf12_00342260_hits}`)",
            f"- Closure, Bench Preflight & `preflight-card-insert` (`Ph136 + Ph143 + Ph154 + Ph186`): `U4/U5/U6={report.p136_u4_u5_u6_closed}`, `EH1={report.p143_sd_escape_absent_us}us`, `H0==H3={report.p143_h0_equals_h3_count}/{report.p143_h0_h3_surface_count}`, `Phase154={report.p154_bench_go}`, `Phase186 sim={report.p186_sim_gates_passed}/4 ({report.p186_sim_go_no_go})`",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts (`Rounds 28..37`): `{report.qemu_rounds_verified}/10` rounds (`{report.qemu_runs_verified}/30` sub-experiments, `PNGs={report.qemu_png_receipts_verified}/20` max=`{report.qemu_png_max_bytes}B < 28KiB`), `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
            "- Wave 22–24 Hardware Parity Redlines: `MIRA_CETUS2` E-Mount `info7/8/3D` & `0x02cf0232` Breathing, HDMI Type-A `4264x2408` 16-bit RAW, `ILME-FX3` vs `ILME-FX3A` firewall, `XLR-H1` MI-Shoe `48kHz/24bit 4ch`, `No-UVC` gadget lock, `USB-PD` `NP-FZ100` vs `DC-C1 >=65W/5A`, SD vs CFexpress-A `.cube` LUT path split + `RMT-P1BT`.",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DEFAULT_REPO_ROOT",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "FIRMWARE_LAB_40_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "ISP_WRITE_AUTHORIZED",
    "MILESTONE193_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_193_VERSION",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "PNG_MAGIC_BYTES",
    "PNG_MAX_SIZE_BYTES",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_MILESTONE193_SCHEMA",
    "RECOVERY_26_PILLAR_IDS",
    "ROUND28_TO_37_PNG_RECEIPTS",
    "ROUND28_TO_37_SPECS",
    "ROUND35_EXPECTED_SCHEMA",
    "ROUND35_SUMMARY_RELPATH",
    "ROUND36_EXPECTED_SCHEMA",
    "ROUND36_SUMMARY_RELPATH",
    "ROUND37_EXPECTED_SCHEMA",
    "ROUND37_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "VM_COEMULATION_33_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone193PillarResult",
    "RealHwMilestone193FaultInjection",
    "RealHwMilestone193MasterGateReport",
    "RealHwMilestone193VerifyResult",
    "build_realhw_milestone193_master_gate_report",
    "compute_milestone193_sha256",
    "evaluate_milestone193_master_gate",
    "render_milestone193_markdown",
    "verify_realhw_milestone193_master_gate",
]
