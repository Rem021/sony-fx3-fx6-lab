"""Deterministic Offline Binary Adapter, Boot Snippet Generator & Byte-Exact Rollback Verifier.

Covers the complete FX6-on-FX3 Compatibility Adaptation Matrix:
- P1: User 3D LUT partition path adaptation (`/dev/nflasha20` -> `/dev/cnflasha30` symlink + 4-library `'2'->'3'`)
- P3: Remote panel service thread pruning (`libInfraAppRemoteBoard.so` `0x157c` & `0x1700` -> `mov w0, #0; ret`)
- P4: Electronic Variable ND Clear state lock (`appFw.so` `0x2111358` -> `nop` & `0x21113f0` -> `b 0x211145c`)
- P8: Non-blocking async log wait adaptation (`appFw.so` `0x2159c50` -> `mov w0, #0; ret`)
- P9: Sensor measurement null-callback guard (`upm.ko` `ET_REL` `.text+0x136b8` `blr x2` -> `mov w0, #0`)
- Fan: Thermal curve backup flag compatibility (`libfan.so` `0x1dec` `_Z19fan_i_bkup_is_validv` -> `mov w0, #1; ret`)
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .elf_verify import (
    PF_R,
    PF_X,
    SHF_ALLOC,
    SHF_EXECINSTR,
    ElfMappingError,
    parse_elf64_aarch64,
    parse_elf64_relocatable_aarch64,
    section_offset_to_file_offset,
    vma_to_file_offset,
)


DEFAULT_FX6_DONOR_LIB_DIR = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
)

DEFAULT_FX3_MODULES_DIR = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/"
    "menu-repair-01/original-uipc/original-modules"
)


class PatchVerificationError(ValueError):
    """Raised when pre-patch or rollback context/SHA-256 verification fails."""


def _pack_insns(*words: int) -> bytes:
    return b"".join(struct.pack("<I", w) for w in words)


@dataclass(frozen=True)
class PatchSiteSpec:
    site_id: str
    patch_group: str
    symbol_or_desc: str
    vma: int
    expected_file_offset: int
    required_segment_flags: int
    original_bytes: bytes
    patched_bytes: bytes
    pre_context: bytes = b""
    post_context: bytes = b""
    section_name: Optional[str] = None

    def __post_init__(self) -> None:
        if len(self.original_bytes) == 0 or len(self.original_bytes) != len(self.patched_bytes):
            raise ValueError(f"PatchSiteSpec {self.site_id} must be non-empty and equal-length")
        if self.original_bytes == self.patched_bytes:
            raise ValueError(f"PatchSiteSpec {self.site_id} original_bytes equals patched_bytes")

    @property
    def size(self) -> int:
        return len(self.original_bytes)


@dataclass(frozen=True)
class LibraryPatchSpec:
    spec_id: str
    library_name: str
    expected_size: int
    donor_sha256: str
    sites: Tuple[PatchSiteSpec, ...]
    elf_kind: str = "ET_DYN"
    source_domain: str = "fx6_lib"


@dataclass(frozen=True)
class SiteResolution:
    site_id: str
    patch_group: str
    vma: int
    file_offset: int
    pt_load_index: int
    segment_flags: str
    original_hex: str
    patched_hex: str
    section_name: Optional[str] = None


@dataclass(frozen=True)
class PatchReceipt:
    spec_id: str
    library_name: str
    file_size: int
    before_sha256: str
    after_sha256: str
    changed_byte_count: int
    resolutions: Tuple[SiteResolution, ...]


@dataclass(frozen=True)
class RollbackReceipt:
    spec_id: str
    library_name: str
    file_size: int
    patched_sha256: str
    restored_sha256: str
    donor_sha256_matched: bool
    restored_byte_count: int
    resolutions: Tuple[SiteResolution, ...]


# ============================================================================
# Canonical Compatibility Adaptation Specifications (P1, P3, P4, P8, P9, Fan)
# ============================================================================

# P1: "/dev/nflasha20\x00" -> "/dev/nflasha30\x00" ('2'=0x32 at +12 -> '3'=0x33)
P1_LIB_INFRA_SETUP_FILE_SPEC = LibraryPatchSpec(
    spec_id="P1_libInfraSetupFile",
    library_name="libInfraSetupFile.so",
    expected_size=202664,
    donor_sha256="b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357",
    sites=(
        PatchSiteSpec(
            site_id="P1_setupfile_nflasha20_to_30",
            patch_group="P1",
            symbol_or_desc='InfraSetupFile::SetupFile::DEV_NAME ("/dev/nflasha20" -> "/dev/nflasha30")',
            vma=0x25E9C,
            expected_file_offset=0x25E9C,
            required_segment_flags=PF_R,
            original_bytes=b"2",
            patched_bytes=b"3",
            pre_context=b"_CMP\x00\x00\x00\x00/dev/nflasha",
            post_context=b"0\x00[InfraSetupFile][",
        ),
    ),
)

P1_LIB_INFRA_MEDIA_COMMON_SPEC = LibraryPatchSpec(
    spec_id="P1_libInfraMediaCommon",
    library_name="libInfraMediaCommon.so",
    expected_size=402624,
    donor_sha256="acbabff1ac3595a39f73a24f1384e0c132f69e19bf7a1ca42c9e2621cf5fbedd",
    sites=(
        PatchSiteSpec(
            site_id="P1_mediacommon_nflasha20_to_30",
            patch_group="P1",
            symbol_or_desc='libInfraMediaCommon LUT partition descriptor ("/dev/nflasha20" -> "/dev/nflasha30")',
            vma=0x4DFCB,
            expected_file_offset=0x4DFCB,
            required_segment_flags=PF_R,
            original_bytes=b"2",
            patched_bytes=b"3",
            pre_context=b"nflasha19\x00/dev/nflasha",
            post_context=b"0\x00/image_nflasha20\x00",
        ),
    ),
)

P1_LIB_INFRA_MEDIA_CONFIG_SPEC = LibraryPatchSpec(
    spec_id="P1_libInfraMediaConfig",
    library_name="libInfraMediaConfig.so",
    expected_size=52312,
    donor_sha256="9709656102d582bd0d91d7a612abb076873d533b1e0e2ed042c6b2611d56c1c3",
    sites=(
        PatchSiteSpec(
            site_id="P1_mediaconfig_nflasha20_to_30",
            patch_group="P1",
            symbol_or_desc='libInfraMediaConfig LUT partition table ("/dev/nflasha20" -> "/dev/nflasha30")',
            vma=0x86FE,
            expected_file_offset=0x86FE,
            required_segment_flags=PF_R,
            original_bytes=b"2",
            patched_bytes=b"3",
            pre_context=b"\x06\x00\x00\x00\x14\xd5/dev/nflasha",
            post_context=b"0\x00\x00\x00\x00\x00\x00\x00\x00\x06",
        ),
    ),
)

P1_APPFW_SITE = PatchSiteSpec(
    site_id="P1_appfw_nflasha20_to_30",
    patch_group="P1",
    symbol_or_desc='appFw.so LUT mount device string ("/dev/nflasha20" -> "/dev/nflasha30")',
    vma=0x25896CE,
    expected_file_offset=0x25896CE,
    required_segment_flags=PF_R,
    original_bytes=b"2",
    patched_bytes=b"3",
    pre_context=b"line[%d]\x00/dev/nflasha",
    post_context=b"0\x00model_user_lut_fi",
)

# P3: libInfraAppRemoteBoard.so MainThread (0x1700) & execRcvMsg (0x157c) -> mov w0, #0; ret
P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = LibraryPatchSpec(
    spec_id="P3_libInfraAppRemoteBoard",
    library_name="libInfraAppRemoteBoard.so",
    expected_size=10448,
    donor_sha256="c7d666093b42713eecf601ddacbfa879b255d0f953a9e77929eb12b916e6b0a6",
    sites=(
        PatchSiteSpec(
            site_id="P3_remoteboard_execRcvMsg",
            patch_group="P3",
            symbol_or_desc="InfraAppRemoteBoard::execRcvMsg(void*) -> mov w0, #0; ret",
            vma=0x157C,
            expected_file_offset=0x157C,
            required_segment_flags=PF_R | PF_X,
            original_bytes=_pack_insns(0xA9BE7BFD, 0x12800001),  # stp x29, x30, [sp, #-0x20]!; mov w1, #-1
            patched_bytes=_pack_insns(0x52800000, 0xD65F03C0),   # mov w0, #0; ret
            post_context=_pack_insns(0x910003FD, 0xA90153F3),    # mov x29, sp; stp x19, x20, [sp, #0x10]
        ),
        PatchSiteSpec(
            site_id="P3_remoteboard_MainThread",
            patch_group="P3",
            symbol_or_desc="InfraAppRemoteBoard::MainThread(void*) -> mov w0, #0; ret",
            vma=0x1700,
            expected_file_offset=0x1700,
            required_segment_flags=PF_R | PF_X,
            original_bytes=_pack_insns(0xA9BC7BFD, 0x52803460),  # stp x29, x30, [sp, #-0x40]!; mov w0, #0x1a3
            patched_bytes=_pack_insns(0x52800000, 0xD65F03C0),   # mov w0, #0; ret
            post_context=_pack_insns(0x72A01F40, 0x910003FD),    # movk w0, #0xfa, lsl #16; mov x29, sp
        ),
    ),
)

# P4: appFw.so Electronic Variable ND Filter Clear (Off) Lock
P4_APPFW_MODE_SITE = PatchSiteSpec(
    site_id="P4_appfw_set_nd_filter_mode_clear",
    patch_group="P4",
    symbol_or_desc="infra_wrapper_imaging::detail::set_nd_filter_mode_i @ 0x2111358 (cbnz w1 -> nop)",
    vma=0x2111358,
    expected_file_offset=0x2111358,
    required_segment_flags=PF_R | PF_X,
    original_bytes=_pack_insns(0x35000081),  # cbnz w1, #0x2111368
    patched_bytes=_pack_insns(0xD503201F),   # nop
    post_context=_pack_insns(0x52800080, 0x39002060, 0xD65F03C0),  # mov w0, #4; strb w0, [x3, #8]; ret
)

P4_APPFW_VALUE_SITE = PatchSiteSpec(
    site_id="P4_appfw_set_nd_filter_value_clear",
    patch_group="P4",
    symbol_or_desc="infra_wrapper_imaging::detail::set_nd_filter_value_i @ 0x21113f0 (cbz w1 -> b 0x211145c)",
    vma=0x21113F0,
    expected_file_offset=0x21113F0,
    required_segment_flags=PF_R | PF_X,
    original_bytes=_pack_insns(0x34000361),  # cbz w1, #0x211145c
    patched_bytes=_pack_insns(0x1400001B),   # b #0x211145c
    pre_context=_pack_insns(0xF9403BB3, 0x29012268),  # ldr x19, [x29, #0x70]; stp w8, w8, [x19, #8]
    post_context=_pack_insns(0x6B08003F, 0x54000521),  # cmp w1, w8; b.ne #0x211149c
)

# P8: appFw.so VMA 0x2159c50 Non-Blocking Async Log Wait Adaptation -> mov w0, #0; ret
P8_APPFW_SITE = PatchSiteSpec(
    site_id="P8_appfw_async_log_wait_nonblocking",
    patch_group="P8",
    symbol_or_desc="appFw.so async log wait @ 0x2159c50 -> mov w0, #0; ret",
    vma=0x2159C50,
    expected_file_offset=0x2159C50,
    required_segment_flags=PF_R | PF_X,
    original_bytes=_pack_insns(0xA9BA7BFD, 0x910003FD),  # stp x29, x30, [sp, #-0x60]!; mov x29, sp
    patched_bytes=_pack_insns(0x52800000, 0xD65F03C0),   # mov w0, #0; ret
    pre_context=_pack_insns(0xA8C57BFD, 0xD65F03C0),     # ldp x29, x30, [sp], #0x50; ret
    post_context=_pack_insns(0xA90153F3, 0x910123B4),    # stp x19, x20, [sp, #0x10]; add x20, x29, #0x48
)

# P9: FX3 upm.ko ET_REL .text+0x136b8 Sensor Measurement Callback Null-Pointer Guard
P9_UPM_KO_SPEC = LibraryPatchSpec(
    spec_id="P9_upm_ko",
    library_name="upm.ko",
    expected_size=453896,
    donor_sha256="ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e",
    elf_kind="ET_REL",
    source_domain="fx3_module",
    sites=(
        PatchSiteSpec(
            site_id="P9_upm_sensor_callback_null_guard",
            patch_group="P9",
            symbol_or_desc="upm.ko .text+0x136b8 (blr x2 -> mov w0, #0)",
            vma=0x136B8,
            expected_file_offset=0x13720,
            required_segment_flags=SHF_ALLOC | SHF_EXECINSTR,
            original_bytes=_pack_insns(0xD63F0040),  # blr x2
            patched_bytes=_pack_insns(0x52800000),   # mov w0, #0
            pre_context=_pack_insns(0x91001341, 0xF9400842),   # add x1, x26, #0x4; ldr x2, [x2, #0x10]
            post_context=_pack_insns(0x72001C1F, 0xB9405FB5),  # tst w0, #0xff; ldr w21, [x29, #0x5c]
            section_name=".text",
        ),
    ),
)

# Fan: FX6 libfan.so VMA 0x1dec (_Z19fan_i_bkup_is_validv) Thermal Curve Compatibility -> mov w0, #1; ret
FAN_LIBFAN_SPEC = LibraryPatchSpec(
    spec_id="Fan_libfan",
    library_name="libfan.so",
    expected_size=31176,
    donor_sha256="d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850",
    sites=(
        PatchSiteSpec(
            site_id="Fan_libfan_bkup_is_valid_true",
            patch_group="Fan",
            symbol_or_desc="_Z19fan_i_bkup_is_validv @ 0x1dec -> mov w0, #1; ret",
            vma=0x1DEC,
            expected_file_offset=0x1DEC,
            required_segment_flags=PF_R | PF_X,
            original_bytes=_pack_insns(0xA9BD7BFD, 0x52800120),  # stp x29, x30, [sp, #-0x30]!; mov w0, #0x9
            patched_bytes=_pack_insns(0x52800020, 0xD65F03C0),   # mov w0, #1; ret
            pre_context=_pack_insns(0xA8C37BFD, 0xD65F03C0),     # ldp x29, x30, [sp], #0x30; ret
            post_context=_pack_insns(0x52800081, 0x910003FD),    # mov w1, #0x4; mov x29, sp
        ),
    ),
)

P1_APPFW_ONLY_SPEC = LibraryPatchSpec(
    spec_id="P1_appFw",
    library_name="appFw.so",
    expected_size=50520424,
    donor_sha256="a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
    sites=(P1_APPFW_SITE,),
)

P4_APPFW_ONLY_SPEC = LibraryPatchSpec(
    spec_id="P4_appFw",
    library_name="appFw.so",
    expected_size=50520424,
    donor_sha256="a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
    sites=(P4_APPFW_MODE_SITE, P4_APPFW_VALUE_SITE),
)

P8_APPFW_ONLY_SPEC = LibraryPatchSpec(
    spec_id="P8_appFw",
    library_name="appFw.so",
    expected_size=50520424,
    donor_sha256="a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
    sites=(P8_APPFW_SITE,),
)

P1_AND_P4_APPFW_COMBINED_SPEC = LibraryPatchSpec(
    spec_id="P1_P4_appFw_combined",
    library_name="appFw.so",
    expected_size=50520424,
    donor_sha256="a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
    sites=(P4_APPFW_MODE_SITE, P4_APPFW_VALUE_SITE, P1_APPFW_SITE),
)

P1_P4_P8_APPFW_COMBINED_SPEC = LibraryPatchSpec(
    spec_id="P1_P4_P8_appFw_combined",
    library_name="appFw.so",
    expected_size=50520424,
    donor_sha256="a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
    sites=(P4_APPFW_MODE_SITE, P4_APPFW_VALUE_SITE, P8_APPFW_SITE, P1_APPFW_SITE),
)

ALL_P1_SPECS: Tuple[LibraryPatchSpec, ...] = (
    P1_LIB_INFRA_SETUP_FILE_SPEC,
    P1_APPFW_ONLY_SPEC,
    P1_LIB_INFRA_MEDIA_COMMON_SPEC,
    P1_LIB_INFRA_MEDIA_CONFIG_SPEC,
)

ALL_CANONICAL_LIBRARY_SPECS: Tuple[LibraryPatchSpec, ...] = (
    P1_LIB_INFRA_SETUP_FILE_SPEC,
    P1_LIB_INFRA_MEDIA_COMMON_SPEC,
    P1_LIB_INFRA_MEDIA_CONFIG_SPEC,
    P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC,
    P1_AND_P4_APPFW_COMBINED_SPEC,
)

ALL_PHASE2_TARGET_SPECS: Tuple[LibraryPatchSpec, ...] = (
    P1_LIB_INFRA_SETUP_FILE_SPEC,
    P1_LIB_INFRA_MEDIA_COMMON_SPEC,
    P1_LIB_INFRA_MEDIA_CONFIG_SPEC,
    P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC,
    FAN_LIBFAN_SPEC,
    P1_P4_P8_APPFW_COMBINED_SPEC,
    P9_UPM_KO_SPEC,
)


def resolve_donor_binary_path(
    spec: LibraryPatchSpec,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
) -> Path:
    """Resolve the read-only source file path for a shared library or relocatable kernel module."""
    if spec.source_domain == "fx3_module":
        return fx3_modules_dir / spec.library_name
    return fx6_lib_dir / spec.library_name


def resolve_and_verify_sites(
    raw: bytes,
    spec: LibraryPatchSpec,
    expect_patched_state: bool = False,
    enforce_size: bool = True,
) -> Tuple[SiteResolution, ...]:
    """Resolve every PatchSiteSpec via ELF64 `PT_LOAD` or `ET_REL` section headers and verify context."""
    if enforce_size and len(raw) != spec.expected_size:
        raise PatchVerificationError(
            f"{spec.library_name}: expected size {spec.expected_size} B, got {len(raw)} B"
        )

    is_rel = spec.elf_kind == "ET_REL"
    try:
        elf_dyn = None if is_rel else parse_elf64_aarch64(raw)
        elf_rel = parse_elf64_relocatable_aarch64(raw) if is_rel else None
    except ElfMappingError as exc:
        raise PatchVerificationError(f"{spec.library_name}: ELF64 validation failed: {exc}") from exc

    seen_ranges: List[Tuple[int, int]] = []
    resolutions: List[SiteResolution] = []

    for site in spec.sites:
        if is_rel:
            assert elf_rel is not None
            sec_name = site.section_name or ".text"
            try:
                foff, sec = section_offset_to_file_offset(
                    elf_rel,
                    section_name=sec_name,
                    section_offset=site.vma,
                    size=site.size,
                    required_sh_flags=site.required_segment_flags,
                )
            except ElfMappingError as exc:
                raise PatchVerificationError(f"{spec.library_name} [{site.site_id}]: {exc}") from exc
            region_start = sec.sh_offset
            region_end = sec.sh_offset + sec.sh_size
            idx_val = sec.index
            flags_str = sec.flags_str
        else:
            assert elf_dyn is not None
            try:
                foff, seg = vma_to_file_offset(
                    elf_dyn,
                    vma=site.vma,
                    size=site.size,
                    required_flags=site.required_segment_flags,
                )
            except ElfMappingError as exc:
                raise PatchVerificationError(f"{spec.library_name} [{site.site_id}]: {exc}") from exc
            region_start = seg.p_offset
            region_end = seg.p_offset + seg.p_filesz
            idx_val = seg.index
            flags_str = seg.flags_str

        if foff != site.expected_file_offset:
            raise PatchVerificationError(
                f"{spec.library_name} [{site.site_id}]: translated offset 0x{site.vma:x} -> "
                f"file offset 0x{foff:x}, expected 0x{site.expected_file_offset:x}"
            )

        for prev_start, prev_end in seen_ranges:
            if not (foff + site.size <= prev_start or foff >= prev_end):
                raise PatchVerificationError(
                    f"{spec.library_name} [{site.site_id}]: overlapping patch site at file offset 0x{foff:x}"
                )
        seen_ranges.append((foff, foff + site.size))

        if site.pre_context:
            pre_start = foff - len(site.pre_context)
            if pre_start < region_start or raw[pre_start:foff] != site.pre_context:
                raise PatchVerificationError(
                    f"{spec.library_name} [{site.site_id}]: pre-context mismatch before 0x{foff:x}"
                )

        if site.post_context:
            post_end = foff + site.size + len(site.post_context)
            if post_end > region_end or raw[foff + site.size : post_end] != site.post_context:
                raise PatchVerificationError(
                    f"{spec.library_name} [{site.site_id}]: post-context mismatch after 0x{foff + site.size:x}"
                )

        expected_target = site.patched_bytes if expect_patched_state else site.original_bytes
        actual_target = raw[foff : foff + site.size]
        if actual_target != expected_target:
            state_label = "patched" if expect_patched_state else "original"
            raise PatchVerificationError(
                f"{spec.library_name} [{site.site_id}] @ 0x{site.vma:x} (foff 0x{foff:x}): "
                f"expected {state_label} bytes {expected_target.hex()}, got {actual_target.hex()}"
            )

        resolutions.append(
            SiteResolution(
                site_id=site.site_id,
                patch_group=site.patch_group,
                vma=site.vma,
                file_offset=foff,
                pt_load_index=idx_val,
                segment_flags=flags_str,
                original_hex=site.original_bytes.hex(),
                patched_hex=site.patched_bytes.hex(),
                section_name=site.section_name,
            )
        )

    return tuple(resolutions)


def apply_patch_spec(
    raw: bytes,
    spec: LibraryPatchSpec,
    verify_donor_sha256: bool = True,
) -> Tuple[bytes, PatchReceipt]:
    """Verify ELF64 offsets, context, and donor SHA-256 on an in-memory buffer and return adapted copy."""
    before_sha = hashlib.sha256(raw).hexdigest()
    if verify_donor_sha256 and before_sha != spec.donor_sha256:
        raise PatchVerificationError(
            f"{spec.library_name}: donor SHA-256 mismatch (expected {spec.donor_sha256}, got {before_sha})"
        )

    resolutions = resolve_and_verify_sites(raw, spec, expect_patched_state=False, enforce_size=verify_donor_sha256)
    buf = bytearray(raw)
    changed_bytes = 0
    for site, res in zip(spec.sites, resolutions):
        buf[res.file_offset : res.file_offset + site.size] = site.patched_bytes
        changed_bytes += site.size

    patched = bytes(buf)
    resolve_and_verify_sites(patched, spec, expect_patched_state=True, enforce_size=verify_donor_sha256)
    after_sha = hashlib.sha256(patched).hexdigest()

    return patched, PatchReceipt(
        spec_id=spec.spec_id,
        library_name=spec.library_name,
        file_size=len(patched),
        before_sha256=before_sha,
        after_sha256=after_sha,
        changed_byte_count=changed_bytes,
        resolutions=resolutions,
    )


def rollback_patch_spec(
    patched: bytes,
    spec: LibraryPatchSpec,
    expected_original_sha256: Optional[str] = None,
    enforce_size: bool = True,
) -> Tuple[bytes, RollbackReceipt]:
    """Deterministically roll back an adapted buffer and verify 100% SHA-256 restoration."""
    patched_sha = hashlib.sha256(patched).hexdigest()
    resolutions = resolve_and_verify_sites(
        patched, spec, expect_patched_state=True, enforce_size=enforce_size
    )

    buf = bytearray(patched)
    restored_bytes = 0
    for site, res in zip(spec.sites, resolutions):
        buf[res.file_offset : res.file_offset + site.size] = site.original_bytes
        restored_bytes += site.size

    restored = bytes(buf)
    resolve_and_verify_sites(restored, spec, expect_patched_state=False, enforce_size=enforce_size)
    restored_sha = hashlib.sha256(restored).hexdigest()

    target_sha = spec.donor_sha256 if expected_original_sha256 is None else expected_original_sha256
    matched = restored_sha == target_sha
    if target_sha and not matched:
        raise PatchVerificationError(
            f"{spec.library_name}: rollback SHA-256 {restored_sha} != expected original SHA-256 {target_sha}"
        )

    return restored, RollbackReceipt(
        spec_id=spec.spec_id,
        library_name=spec.library_name,
        file_size=len(restored),
        patched_sha256=patched_sha,
        restored_sha256=restored_sha,
        donor_sha256_matched=matched,
        restored_byte_count=restored_bytes,
        resolutions=resolutions,
    )


def generate_p1_lut_mount_snippet(
    lut_mount_dir: str = "/usr/data/lut",
    decrypted_p30_dev: str = "/dev/cnflasha30",
    physical_p30_dev: str = "/dev/pnflasha30",
) -> str:
    """Generate an idempotent POSIX sh boot snippet mapping FX6 p20 LUT nodes to FX3 48MiB p30."""
    return (
        "#!/bin/sh\n"
        "# FX6-on-FX3 P1 Zero-Repartitioning 3D LUT Partition Adaptation (Idempotent)\n"
        "# Preserves FX3 native Sector 0 ('8246' '2.00') & redirects p20 -> FX3 48MiB p30.\n"
        f'if [ -b "{decrypted_p30_dev}" ] || [ -e "{decrypted_p30_dev}" ]; then\n'
        "    rm -f /dev/nflasha20 /dev/cnflasha20 /dev/pnflasha20\n"
        f'    ln -s "{decrypted_p30_dev}" /dev/nflasha20\n'
        f'    ln -s "{decrypted_p30_dev}" /dev/cnflasha20\n'
        f'    if [ -b "{physical_p30_dev}" ] || [ -e "{physical_p30_dev}" ]; then\n'
        f'        ln -s "{physical_p30_dev}" /dev/pnflasha20\n'
        "    fi\n"
        "fi\n"
        f'mkdir -p "{lut_mount_dir}"\n'
    )
