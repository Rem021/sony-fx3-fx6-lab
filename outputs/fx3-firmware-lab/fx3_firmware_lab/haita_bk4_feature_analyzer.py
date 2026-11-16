"""FX3 v7.02 (PRODUCT_MODEL_ALCIN_UUD) vs FX6 v6.01 Cinema Line HAITA & BK4 Differential Analyzer.

Strictly Read-Only (`os.O_RDONLY`) & Clean-Room Dual-Mode:
- Local Donor Mode: opens FX3 v7.02 `appFw.so` and FX6 v6.01 `appFw.so` strictly `O_RDONLY`
  and extracts `PRODUCT_MODEL_*`, `TYPE_MENU_ITEM_*`, `*HAITA*` / `PRM_HAITA_*`,
  `PRM_FEATURE_MANAGER_*`, `STRID_FUNC_*`, `BKID_*`, and Open-Gate / Cinema Line markers
  using fast C-level `bytes.find` / byte regex scans (<0.3s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` or `clean_room=True` or donors absent):
  runs deterministic synthetic clean-room binary fixtures & verified baseline contracts with
  zero proprietary files required.
"""

from __future__ import annotations

import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")

FX3_APPFW_RELPATH = "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
FX6_APPFW_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)

BK4_SYNC_MARKER = 0xAAAAAAAA
BK4_MAGIC = b"BK4\x00"
BK4_HEADER_SIZE = 256

# Canonical Product Model Enum & Hardware Coupling Table
# Reference: leogenot/sony-a7iv-feature-research PRODUCT_CLASS.md & FX3 7.02 appFw.so
PRODUCT_MODEL_CONTRACTS: Dict[str, Dict[str, object]] = {
    "PRODUCT_MODEL_LS": {
        "enum_id": 0,
        "feature_index": 26,
        "camera": "ILCE-7M4 (A7 IV)",
        "sensor": "IMX710",
        "category": "OTHER",
        "mechanical_shutter": True,
        "dual_cfexpress_a": False,
    },
    "PRODUCT_MODEL_LAX": {
        "enum_id": 3,
        "feature_index": 25,
        "camera": "ILME-FX30",
        "sensor": "IMX684",
        "category": "CINEMA_LINE",
        "mechanical_shutter": False,
        "dual_cfexpress_a": False,
    },
    "PRODUCT_MODEL_ALCIN_UUD": {
        "enum_id": 4,
        "feature_index": 24,
        "camera": "ILME-FX3",
        "sensor": "IMX510",
        "category": "CINEMA_LINE",
        "mechanical_shutter": True,
        "dual_cfexpress_a": True,
    },
    "PRODUCT_MODEL_CHAPLIN": {
        "enum_id": None,
        "feature_index": None,
        "camera": "ILME-FX6",
        "sensor": "IMX510-FX6-BASE",
        "category": "CINEMA_LINE_PRO",
        "mechanical_shutter": False,
        "dual_cfexpress_a": True,
    },
}

FX3_EXPECTED_ACTIVE_PRODUCT_MODELS: Tuple[str, ...] = (
    "PRODUCT_MODEL_ALCIN_UUD",
    "PRODUCT_MODEL_DZ",
    "PRODUCT_MODEL_GL",
    "PRODUCT_MODEL_GS",
    "PRODUCT_MODEL_LAX",
    "PRODUCT_MODEL_LS",
    "PRODUCT_MODEL_SA",
    "PRODUCT_MODEL_YS",
    "PRODUCT_MODEL_YT",
)

# Verified BK4 Cinema Line NVRAM Property Contracts
@dataclass(frozen=True)
class BK4PropertyContract:
    prop_id: int
    bkid_name: str
    description: str
    byte_length: int
    value_map: Dict[str, str]
    fx3_nvram_mutation_hazard: str
    stage_a_ram_shadow_safe: bool


CANONICAL_BK4_CONTRACTS: Tuple[BK4PropertyContract, ...] = (
    BK4PropertyContract(
        prop_id=0x02CF1702,
        bkid_name="BKID_APP_SHUTTER_ANGLE_MODE",
        description="Shutter Angle Mode (0x00=Speed / 0x01=Angle)",
        byte_length=1,
        value_map={"0x00": "Speed", "0x01": "Angle"},
        fx3_nvram_mutation_hazard="HUD_ONLY_WITHOUT_CINEMA_DIAL_DISPATCH",
        stage_a_ram_shadow_safe=True,
    ),
    BK4PropertyContract(
        prop_id=0x02CF1704,
        bkid_name="BKID_APP_SHUTTER_ANGLE_VALUE",
        description="Shutter Angle Value (0x10=180 deg, 0x0A..0x1C=360..5.6 deg, 0x00..0x09=64F..2F)",
        byte_length=1,
        value_map={"0x10": "180.0 deg", "0x0a..0x1c": "360..5.6 deg", "0x00..0x09": "64F..2F"},
        fx3_nvram_mutation_hazard="REQUIRES_SHUTTER_MODE_AND_UX_DISPATCH",
        stage_a_ram_shadow_safe=True,
    ),
    BK4PropertyContract(
        prop_id=0x02CF1443,
        bkid_name="BKID_APP_LOG_SHOOTING_MODE",
        description="Log Shooting / Cine EI Mode",
        byte_length=1,
        value_map={"0x00": "Off", "0x01": "Flexible ISO", "0x02": "Cine EI Quick", "0x03": "Cine EI"},
        fx3_nvram_mutation_hazard="HIDDEN_BY_TYPE_MENU_ITEM_AND_HAITA_ON_NON_CINEMA_HOSTS",
        stage_a_ram_shadow_safe=True,
    ),
    BK4PropertyContract(
        prop_id=0x02CF1453,
        bkid_name="BKID_APP_SELECT_LUT",
        description="Select 3D LUT Slot (S709 / R709 / S-Log3 / User1-16)",
        byte_length=1,
        value_map={"0x00": "S709", "0x01": "R709", "0x02": "S-Log3", "0x03..0x12": "User1..16"},
        fx3_nvram_mutation_hazard="USER_LUT_REQUIRES_0x02CF14A4_14B3_PRESENCE_FLAGS",
        stage_a_ram_shadow_safe=True,
    ),
    BK4PropertyContract(
        prop_id=0x02CF1BF2,
        bkid_name="BKID_APP_EXTERN_DE_SQUEEZE_DISP",
        description="Anamorphic De-Squeeze Display Ratio",
        byte_length=1,
        value_map={"0x00": "Off", "0x01": "1.3x", "0x02": "2.0x"},
        fx3_nvram_mutation_hazard="GATED_BY_HAITA_DE_SQUEEZE_DISP",
        stage_a_ram_shadow_safe=True,
    ),
    BK4PropertyContract(
        prop_id=0x02CF00D7,
        bkid_name="BKID_APP_EXTERN_MENU_MOVIE_REC_ASPECT_XAVC",
        description="Movie Rec Aspect Open-Gate Marker (5016x3344 hazard proof)",
        byte_length=1,
        value_map={"0x00": "16:9", "0x01": "17:9 / Open-Gate Candidate"},
        fx3_nvram_mutation_hazard="OPEN_GATE_ENCODER_AND_SDK_0x9203_INCOMPLETE",
        stage_a_ram_shadow_safe=False,
    ),
    BK4PropertyContract(
        prop_id=0x02CF0004,
        bkid_name="BKID_APP_NTSC_PAL_POPUP_CONTROL",
        description="NTSC/PAL Selector Warning Popup Control",
        byte_length=1,
        value_map={"0x00": "Show Warning", "0x01": "Suppress Warning"},
        fx3_nvram_mutation_hazard="LOW_RISK_PERSISTENT_PREFERENCE",
        stage_a_ram_shadow_safe=True,
    ),
)


@dataclass(frozen=True)
class BinaryFeatureProfile:
    label: str
    source_mode: str  # "LOCAL_DONOR_RDONLY" or "SYNTHETIC_CLEAN_ROOM"
    file_bytes: int
    product_models: Tuple[str, ...]
    type_menu_items: Tuple[str, ...]
    strid_func_count: int
    prm_haita_count: int
    haita_symbol_count: int
    feature_manager_count: int
    bkid_count: int
    bk4_u32_table_hits: Dict[str, int]
    has_open_gate_scanmode: bool
    has_open_gate_5016x3344: bool
    has_x_ocn_lt: bool
    has_alcin_uud: bool
    has_chaplin: bool


@dataclass(frozen=True)
class ProductModelHazardProof:
    verdict: str
    stock_nvram_mutation_allowed: bool
    stage_a_ram_shadow_allowed: bool
    flash_mutation_bytes: int
    coupled_hardware_subsystems: Tuple[str, ...]
    open_gate_nvram_only_feasible: bool
    open_gate_blocker_reason: str
    proof_summary: str


@dataclass(frozen=True)
class BK4RecordAudit:
    valid: bool
    magic_ok: bool
    sync_ok: bool
    checksum_ok: bool
    expected_checksum: int
    computed_checksum: int
    subsystems: int
    properties: int
    found_nvram_ids: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HaitaFeatureAuditReport:
    mode: str
    all_checks_passed: bool
    fx3_profile: BinaryFeatureProfile
    fx6_profile: BinaryFeatureProfile
    fx3_9_active_models_verified: bool
    fx6_chaplin_present: bool
    open_gate_asymmetry_verified: bool
    bk4_contracts: Tuple[BK4PropertyContract, ...]
    bk4_synthetic_audit: BK4RecordAudit
    hazard_proof: ProductModelHazardProof
    errors: Tuple[str, ...]


_RE_PRODUCT_MODEL = re.compile(rb"PRODUCT_MODEL_[A-Z0-9_]+")
_RE_TYPE_MENU_ITEM = re.compile(rb"TYPE_MENU_ITEM_[A-Z0-9_]+")
_RE_STRID_FUNC = re.compile(rb"STRID_FUNC_[A-Z0-9_]+")
_RE_PRM_HAITA = re.compile(rb"PRM_HAITA_[A-Z0-9_]*")
_RE_BKID = re.compile(rb"BKID_[A-Z0-9_]+")

_IDENT_BYTES = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_")


def _extract_ident_tokens_containing(data: bytes, needle: bytes) -> set[bytes]:
    """Fast C-level `bytes.find` scan extracting identifier tokens containing `needle`."""
    tokens: set[bytes] = set()
    n = len(data)
    pos = 0
    while True:
        idx = data.find(needle, pos)
        if idx == -1:
            break
        start = idx
        while start > 0 and data[start - 1] in _IDENT_BYTES:
            start -= 1
        end = idx + len(needle)
        while end < n and data[end] in _IDENT_BYTES:
            end += 1
        tokens.add(data[start:end])
        pos = end
    return tokens


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes")


def _iter_work_roots(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    cands: List[Path] = []
    for k in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        raw = source.get(k, "").strip()
        if raw:
            cands.append(Path(os.path.expanduser(raw)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        mr = Path(os.path.expanduser(mac_root))
        cands.append(mr / "work")
        cands.append(mr / "outputs" / "sony-fx3-fx6-lab" / "work")
    cands.append(repo_root / "work")
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    cands.append(internal / "outputs" / "sony-fx3-fx6-lab" / "work")
    cands.append(internal / "work")
    cands.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")
    cands.append(LEGACY_MAC_ROOT / "work")
    seen = set()
    uniq: List[Path] = []
    for c in cands:
        s = str(c)
        if s not in seen:
            seen.add(s)
            uniq.append(c)
    return tuple(uniq)


def resolve_donor_file(
    relpath: str,
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    clean_room: bool = False,
) -> Optional[Path]:
    """Resolve an optional local donor file without ever crossing into forbidden clean-room mode."""
    if clean_room or is_forced_clean_room(env):
        return None
    for root in _iter_work_roots(repo_root=repo_root, env=env):
        cand = root / relpath
        if cand.is_file():
            return cand
    return None


def read_bytes_rdonly(path: Path) -> bytes:
    """Strictly open and read a donor binary using `os.O_RDONLY`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def build_synthetic_appfw_bytes(variant: str) -> bytes:
    """Build deterministic clean-room synthetic ELF/rodata fixture representing FX3 or FX6 appFw.so."""
    if variant == "fx3_702":
        tokens: List[bytes] = [
            *(m.encode("ascii") for m in FX3_EXPECTED_ACTIVE_PRODUCT_MODELS),
            b"TYPE_MENU_ITEM_ALCIN_UUD",
            b"TYPE_MENU_ITEM_LAX",
            b"TYPE_MENU_ITEM_LS",
            b"PRM_HAITA_FEATURE_MANAGER_menu_item_setting_base_sensitivity_general_shooting_mode",
            b"PRM_HAITA_FEATURE_MANAGER_model_diff_exposure_mode",
            b"PRM_HAITA_FEATURE_MANAGER_model_diff_setting_log_shooting",
            b"PRM_FEATURE_MANAGER_menu_item",
            b"PRM_FEATURE_MANAGER_camera_parameters",
            b"BKID_APP_EXTERN_DE_SQUEEZE_DISP",
            b"BKID_APP_EXTERN_MENU_MOVIE_REC_ASPECT_XAVC",
            b"STRID_FUNC_SHUTTER_ANGLE",
            b"STRID_FUNC_LOG_SHOOTING",
            struct.pack("<I", 0x02CF00D7),
        ]
    elif variant == "fx6_601":
        tokens = [
            *(m.encode("ascii") for m in FX3_EXPECTED_ACTIVE_PRODUCT_MODELS),
            b"PRODUCT_MODEL_CHAPLIN",
            b"PRODUCT_MODEL_ALCIN2",
            b"PRODUCT_MODEL_OT_UUD",
            b"PRODUCT_MODEL_TK_UUD",
            b"PRM_HAITA_CINEMA_LINE_BASE",
            b"HAITA_DE_SQUEEZE_DISP_ON_MOVIE_MODE",
            b"PRM_FEATURE_MANAGER_product_concept",
            b"PRM_FEATURE_MANAGER_sdi_output",
            b"BKID_APP_EXTERN_MENU_MOVIE_REC_ASPECT_XAVC",
            b"BKID_APP_LOG_SHOOTING_MODE",
            b"BKID_APP_SELECT_LUT",
            b"IMAGER_SCANMODE_FF_5K_3_2",
            b"VIDEO_FORMAT_5016x3344P",
            b"SELECT_CODEC_X_OCN_LT",
            b"STRID_FUNC_CINE_EI",
            struct.pack("<I", 0x02CF1443),
            struct.pack("<I", 0x02CF1453),
            struct.pack("<I", 0x02CF00D7),
        ]
    else:
        raise ValueError(f"Unknown synthetic variant: {variant!r}")

    elf_stub = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    return elf_stub + b"\x00".join(tokens) + b"\x00"


def scan_appfw_features(
    data: bytes,
    *,
    label: str,
    source_mode: str,
) -> BinaryFeatureProfile:
    """Scan an ELF/rodata buffer using fast C-level `bytes.find` and byte regexes."""
    pms = tuple(sorted({m.group(0).decode("ascii") for m in _RE_PRODUCT_MODEL.finditer(data)}))
    tmis = tuple(sorted({m.group(0).decode("ascii") for m in _RE_TYPE_MENU_ITEM.finditer(data)}))
    strid_funcs = {m.group(0) for m in _RE_STRID_FUNC.finditer(data)}
    prm_haitas = {m.group(0) for m in _RE_PRM_HAITA.finditer(data)}
    all_haitas = _extract_ident_tokens_containing(data, b"HAITA")
    fms = _extract_ident_tokens_containing(data, b"FEATURE_MANAGER")
    bkids = {m.group(0) for m in _RE_BKID.finditer(data)}

    bk4_hits = {
        hex(c.prop_id): data.count(struct.pack("<I", c.prop_id))
        for c in CANONICAL_BK4_CONTRACTS
    }

    return BinaryFeatureProfile(
        label=label,
        source_mode=source_mode,
        file_bytes=len(data),
        product_models=pms,
        type_menu_items=tmis,
        strid_func_count=len(strid_funcs),
        prm_haita_count=len(prm_haitas),
        haita_symbol_count=len(all_haitas),
        feature_manager_count=len(fms),
        bkid_count=len(bkids),
        bk4_u32_table_hits=bk4_hits,
        has_open_gate_scanmode=data.find(b"IMAGER_SCANMODE_FF_5K_3_2") != -1,
        has_open_gate_5016x3344=data.find(b"VIDEO_FORMAT_5016x3344P") != -1,
        has_x_ocn_lt=data.find(b"SELECT_CODEC_X_OCN_LT") != -1,
        has_alcin_uud="PRODUCT_MODEL_ALCIN_UUD" in pms,
        has_chaplin="PRODUCT_MODEL_CHAPLIN" in pms,
    )


def build_clean_room_bk4_record(
    properties: Optional[Sequence[Tuple[int, bytes]]] = None,
    *,
    subsystems: int = 1,
    active_byte8: int = 1,
) -> bytes:
    """Build a valid 256B-header + payload `BK4\\0` record matching loader_nor.bin checksum rules."""
    if properties is None:
        properties = (
            (0x02CF1702, b"\x01"),  # Shutter Angle Mode = Angle
            (0x02CF1704, b"\x10"),  # Shutter Angle Value = 180 deg
            (0x02CF1443, b"\x03"),  # Log Shooting = Cine EI
            (0x02CF1453, b"\x02"),  # Select LUT = S-Log3
            (0x02CF1BF2, b"\x01"),  # De-Squeeze = 1.3x
        )

    payload = bytearray()
    for pid, val in properties:
        payload.extend(struct.pack("<IH", pid, len(val)))
        payload.extend(val)

    total_bytes = BK4_HEADER_SIZE + len(payload)
    buf = bytearray(total_bytes)
    struct.pack_into("<I", buf, 0x04, BK4_SYNC_MARKER)
    buf[0x08] = active_byte8 & 0xFF
    buf[0x0C:0x10] = BK4_MAGIC
    struct.pack_into("<IIII", buf, 0x10, subsystems, len(properties), BK4_HEADER_SIZE, len(payload))
    struct.pack_into("<i", buf, 0x2C, 1)
    buf[BK4_HEADER_SIZE:] = payload

    # 32-bit byte sum over [0 : total_bytes] skipping [0x20 : 0x24]
    checksum = (sum(buf[0:0x20]) + sum(buf[0x24:total_bytes])) & 0xFFFFFFFF
    struct.pack_into("<I", buf, 0x20, checksum)
    return bytes(buf)


def audit_bk4_record_bytes(buf: bytes) -> BK4RecordAudit:
    """Validate a `BK4\\0` record and scan for canonical Cinema Line NVRAM IDs."""
    errors: List[str] = []
    if len(buf) < BK4_HEADER_SIZE:
        return BK4RecordAudit(
            valid=False,
            magic_ok=False,
            sync_ok=False,
            checksum_ok=False,
            expected_checksum=0,
            computed_checksum=0,
            subsystems=0,
            properties=0,
            found_nvram_ids=(),
            errors=(f"Buffer {len(buf)} bytes smaller than {BK4_HEADER_SIZE}-byte BK4 header",),
        )

    sync_word = struct.unpack_from("<I", buf, 0x04)[0]
    magic = buf[0x0C:0x10]
    subs, props, data_off, data_size, expected_sum = struct.unpack_from("<IIIII", buf, 0x10)

    sync_ok = sync_word == BK4_SYNC_MARKER
    magic_ok = magic == BK4_MAGIC
    if not sync_ok:
        errors.append(f"Invalid sync marker {sync_word:#010x} (expected {BK4_SYNC_MARKER:#010x})")
    if not magic_ok:
        errors.append(f"Invalid magic {magic!r} (expected {BK4_MAGIC!r})")

    total_bytes = data_off + data_size
    if data_off < BK4_HEADER_SIZE or total_bytes > len(buf):
        errors.append(f"BK4 payload span {total_bytes} exceeds buffer {len(buf)}")
        return BK4RecordAudit(
            valid=False,
            magic_ok=magic_ok,
            sync_ok=sync_ok,
            checksum_ok=False,
            expected_checksum=expected_sum,
            computed_checksum=0,
            subsystems=subs,
            properties=props,
            found_nvram_ids=(),
            errors=tuple(errors),
        )

    computed_sum = (sum(buf[0:0x20]) + sum(buf[0x24:total_bytes])) & 0xFFFFFFFF
    checksum_ok = computed_sum == expected_sum
    if not checksum_ok:
        errors.append(f"BK4 checksum mismatch header={expected_sum:#010x} computed={computed_sum:#010x}")

    payload = buf[data_off:total_bytes]
    found_ids: List[str] = []
    for c in CANONICAL_BK4_CONTRACTS:
        if payload.find(struct.pack("<I", c.prop_id)) != -1:
            found_ids.append(hex(c.prop_id))

    return BK4RecordAudit(
        valid=sync_ok and magic_ok and checksum_ok and len(errors) == 0,
        magic_ok=magic_ok,
        sync_ok=sync_ok,
        checksum_ok=checksum_ok,
        expected_checksum=expected_sum,
        computed_checksum=computed_sum,
        subsystems=subs,
        properties=props,
        found_nvram_ids=tuple(found_ids),
        errors=tuple(errors),
    )


def prove_product_model_nvram_hazard(
    fx3_profile: BinaryFeatureProfile,
    fx6_profile: BinaryFeatureProfile,
) -> ProductModelHazardProof:
    """Prove why mutating PRODUCT_MODEL in stock Backup.bin is forbidden vs RAM-shadow BK4."""
    coupled = (
        "IMX510_sensor_timing_table (enum 4 -> idx 24 vs LAX IMX684 / LS IMX710)",
        "mechanical_shutter_driver_table (FX3 has shutter vs FX30/FX6 shutterless)",
        "evf_lcd_panel_and_fan_thermal_curve (ALCIN_UUD vs CHAPLIN)",
        "dual_cfexpress_type_a_slot_topology",
        "type_menu_item_per_model_pruning (PRM_FEATURE_MANAGER_menu_item id 119)",
    )
    open_gate_feasible = False
    open_gate_reason = (
        "Even though FX6 appFw.so contains IMAGER_SCANMODE_FF_5K_3_2 / VIDEO_FORMAT_5016x3344P / "
        "SELECT_CODEC_X_OCN_LT strings, AVC/HEVC encoder profiles and Remote SDK 0x9203 descriptors "
        "lack 5016x3344 capability, so mutating 0x02cf00d7 in Backup.bin cannot activate Open Gate."
    )
    summary = (
        f"In {fx3_profile.label}, feature_manager::update_product_model() writes PRODUCT_MODEL_ALCIN_UUD "
        f"(enum 4, idx 24) and indexes {len(coupled)} hardware-coupled tables via `ldr w0, [x0, x1, lsl #2]`. "
        f"Mutating PRODUCT_MODEL in stock FX3 Backup.bin switches all coupled sensor/shutter/EVF/fan tables "
        f"simultaneously (brick hazard -> BLOCKED_PRODUCT_MODEL_NVRAM_HAZARD). Conversely, running "
        f"{fx6_profile.label} Cinema Line appFw.so over Stage-A/B tmpfs with a RAM-shadow BK4\\0 "
        f"(flash_mutation_bytes=0) preserves stock Backup.bin and 100% hardware calibration safety."
    )
    return ProductModelHazardProof(
        verdict="BLOCKED_PRODUCT_MODEL_NVRAM_HAZARD",
        stock_nvram_mutation_allowed=False,
        stage_a_ram_shadow_allowed=True,
        flash_mutation_bytes=0,
        coupled_hardware_subsystems=coupled,
        open_gate_nvram_only_feasible=open_gate_feasible,
        open_gate_blocker_reason=open_gate_reason,
        proof_summary=summary,
    )


def analyze_haita_and_bk4_features(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
) -> HaitaFeatureAuditReport:
    """Analyze FX3 v7.02 vs FX6 v6.01 PRODUCT_MODEL, HAITA, and BK4 contracts."""
    errors: List[str] = []
    fx3_path = resolve_donor_file(FX3_APPFW_RELPATH, repo_root=repo_root, env=env, clean_room=clean_room)
    fx6_path = resolve_donor_file(FX6_APPFW_RELPATH, repo_root=repo_root, env=env, clean_room=clean_room)

    if fx3_path is not None and fx6_path is not None:
        mode = "LOCAL_DONOR_VERIFIED"
        fx3_bytes = read_bytes_rdonly(fx3_path)
        fx6_bytes = read_bytes_rdonly(fx6_path)
        fx3_prof = scan_appfw_features(fx3_bytes, label="FX3_v7.02_appFw.so", source_mode="LOCAL_DONOR_RDONLY")
        fx6_prof = scan_appfw_features(fx6_bytes, label="FX6_v6.01_appFw.so", source_mode="LOCAL_DONOR_RDONLY")
    else:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        fx3_bytes = build_synthetic_appfw_bytes("fx3_702")
        fx6_bytes = build_synthetic_appfw_bytes("fx6_601")
        fx3_prof = scan_appfw_features(fx3_bytes, label="FX3_v7.02_appFw.so", source_mode="SYNTHETIC_CLEAN_ROOM")
        fx6_prof = scan_appfw_features(fx6_bytes, label="FX6_v6.01_appFw.so", source_mode="SYNTHETIC_CLEAN_ROOM")

    fx3_9_ok = set(FX3_EXPECTED_ACTIVE_PRODUCT_MODELS).issubset(set(fx3_prof.product_models))
    if fx3_prof.source_mode == "LOCAL_DONOR_RDONLY":
        fx3_9_ok = fx3_prof.product_models == FX3_EXPECTED_ACTIVE_PRODUCT_MODELS
    if not fx3_9_ok:
        errors.append(
            f"FX3 active PRODUCT_MODEL set mismatch: got {fx3_prof.product_models}"
        )

    fx6_chaplin_ok = fx6_prof.has_chaplin and fx6_prof.has_alcin_uud
    if not fx6_chaplin_ok:
        errors.append("FX6 appFw.so missing PRODUCT_MODEL_CHAPLIN or PRODUCT_MODEL_ALCIN_UUD")

    open_gate_asym_ok = (
        (not fx3_prof.has_open_gate_5016x3344)
        and fx6_prof.has_open_gate_scanmode
        and fx6_prof.has_open_gate_5016x3344
        and fx6_prof.has_x_ocn_lt
    )
    if not open_gate_asym_ok:
        errors.append("Unexpected Open-Gate string asymmetry between FX3 7.02 and FX6 6.01")

    bk4_bytes = build_clean_room_bk4_record()
    bk4_audit = audit_bk4_record_bytes(bk4_bytes)
    if not bk4_audit.valid:
        errors.extend(bk4_audit.errors)

    hazard = prove_product_model_nvram_hazard(fx3_prof, fx6_prof)
    all_ok = (
        len(errors) == 0
        and fx3_9_ok
        and fx6_chaplin_ok
        and open_gate_asym_ok
        and bk4_audit.valid
        and hazard.verdict == "BLOCKED_PRODUCT_MODEL_NVRAM_HAZARD"
    )

    return HaitaFeatureAuditReport(
        mode=mode,
        all_checks_passed=all_ok,
        fx3_profile=fx3_prof,
        fx6_profile=fx6_prof,
        fx3_9_active_models_verified=fx3_9_ok,
        fx6_chaplin_present=fx6_chaplin_ok,
        open_gate_asymmetry_verified=open_gate_asym_ok,
        bk4_contracts=CANONICAL_BK4_CONTRACTS,
        bk4_synthetic_audit=bk4_audit,
        hazard_proof=hazard,
        errors=tuple(errors),
    )


def haita_report_to_dict(report: HaitaFeatureAuditReport) -> Dict[str, object]:
    return asdict(report)
