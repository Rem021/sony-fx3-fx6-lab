"""Keyless Clean-Room Sony BODYDATA.DAT (UFU / FDAT / UDTRFIRM) & SDM2 Partition Auditor.

Strictly Clean-Room & BYOF Compliant:
- Embeds ZERO proprietary Sony secret AES keys (such as CXD90057_k8) or vendor RSA private keys.
- Uses only public format magic bytes (`\\x89UFU\\r\\n\\x1a\\n`, `FDAT`, `UDTRFIRM`, `SDM2` `8246` `2.00`),
  public mathematical constants (`hashlib.sha256(b"").digest()[:16]` for synthetic test vectors),
  optional caller-supplied BYOF decrypt/verify callbacks, and deterministic structural/checksum checks.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple


# Public container magic bytes & geometry constants
UFU_MAGIC = b"\x89UFU\r\n\x1a\n"
UFU_HEADER_STRUCT = struct.Struct("<8sIII")  # magic, header_version, model_id, block_count
FDAT_MAGIC = b"FDAT"
FDAT_BLOCK_HEADER_STRUCT = struct.Struct("<4sIII")  # tag, payload_size, model_id, flags
FDAT_IV_BYTES = 16
FDAT_RSA2048_SIG_BYTES = 256
FDAT_TRAILER_BYTES = FDAT_IV_BYTES + FDAT_RSA2048_SIG_BYTES  # 0x110 (272 B) at off + size

FDAT_CHUNK_SIZE = 1024
FDAT_CHUNK_HEADER_SIZE = 4
FDAT_CHUNK_PAYLOAD_MAX = FDAT_CHUNK_SIZE - FDAT_CHUNK_HEADER_SIZE  # 1020 B
FDAT_CHUNK_TERMINAL_FLAG = 0x8000

UDTRFIRM_MAGIC = b"UDTRFIRM"
UDTRFIRM_HEADER_STRUCT = struct.Struct("<8sIIII")  # magic, version, entry_count, model_id, flags
UDTRFIRM_ENTRY_STRUCT = struct.Struct("<32sIQQ32s")  # name, part_idx, offset, size, sha256_digest

SDM2_PTBL_MAGIC = b"8246"
SDM2_PTBL_VERSION = b"2.00"
SDM2_ENTRY_COUNT = 30
SDM2_TABLE_BYTES = 512

# Public empty-digest mathematical constant documented in Sony header-wrap specs (no secret keys)
PUBLIC_EMPTY_SHA256_PREFIX16: bytes = hashlib.sha256(b"").digest()[:16]

# Model ID Guard constants (prevents 5L+6S cross-variant update rejection / bricking)
MODEL_ID_FX3 = 0x91030080
MODEL_ID_FX3A = 0x91030082
MODEL_ID_FX6 = 0x91030060
MODEL_ID_A7M4 = 0x91030070

KNOWN_MODEL_IDS: Dict[int, str] = {
    MODEL_ID_FX3: "ILME-FX3 (PRODUCT_MODEL_ALCIN_UUD)",
    MODEL_ID_FX3A: "ILME-FX3A (PRODUCT_MODEL_ALCIN2)",
    MODEL_ID_FX6: "ILME-FX6 (PRODUCT_MODEL_CHAPLIN)",
    MODEL_ID_A7M4: "ILCE-7M4 (PRODUCT_MODEL_LS)",
}


@dataclass(frozen=True)
class FdatChunkAuditResult:
    valid: bool
    chunk_count: int
    total_stream_bytes: int
    reconstructed_bytes: int
    terminal_flag_seen: bool
    checksum_errors: Tuple[str, ...]
    framing_errors: Tuple[str, ...]
    reconstructed_sha256: str


@dataclass(frozen=True)
class UdtRFirmEntry:
    name: str
    partition_index: int
    offset: int
    size: int
    sha256_hex: str


@dataclass(frozen=True)
class UdtRFirmManifest:
    valid: bool
    magic_ok: bool
    version: int
    model_id: int
    entry_count: int
    entries: Tuple[UdtRFirmEntry, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Sdm2PartitionDescriptor:
    index: int
    start_sector: int
    size_sectors: int
    part_type: int
    flag: int
    aes_xts_256_encrypted: bool
    device_node: str

    @property
    def size_bytes(self) -> int:
        return self.size_sectors * 512


@dataclass(frozen=True)
class Sdm2AuditResult:
    valid: bool
    magic_ok: bool
    version_ok: bool
    entry_count: int
    layout_profile: str
    xts_encrypted_partitions: Tuple[int, ...]
    plaintext_partitions: Tuple[int, ...]
    has_overlaps: bool
    emmc_static_boot_sig_required: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    descriptors: Tuple[Sdm2PartitionDescriptor, ...]


@dataclass(frozen=True)
class UfuAuditReport:
    valid: bool
    ufu_magic_ok: bool
    header_version: int
    envelope_model_id: int
    expected_model_id: int
    model_id_match: bool
    brick_guard_code: str
    fdat_found: bool
    fdat_offset: int
    fdat_payload_size: int
    fdat_trailer_offset: int
    fdat_trailer_bytes: int
    fdat_iv_hex: str
    fdat_rsa2048_sig_bytes: int
    fdat_trailer_non_degenerate: bool
    chunk_audit: Optional[FdatChunkAuditResult]
    udtrfirm_manifest: Optional[UdtRFirmManifest]
    byof_callback_invoked: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


def build_fdat_chunk_stream(payload: bytes) -> bytes:
    """Frame raw UDTRFIRM/payload bytes into 1024-byte FDAT chunks (`<HH` u16 sum + len/0x8000)."""
    if not payload:
        # Empty payload still emits a single terminal 1024-byte frame
        chk = 0
        hdr = struct.pack("<HH", chk, FDAT_CHUNK_TERMINAL_FLAG)
        return hdr + bytes(FDAT_CHUNK_PAYLOAD_MAX)

    out = bytearray()
    total = len(payload)
    offset = 0
    while offset < total:
        piece = payload[offset : offset + FDAT_CHUNK_PAYLOAD_MAX]
        offset += len(piece)
        is_last = offset >= total
        len_field = len(piece) | (FDAT_CHUNK_TERMINAL_FLAG if is_last else 0)
        chk = sum(piece) & 0xFFFF
        out.extend(struct.pack("<HH", chk, len_field))
        out.extend(piece)
        if len(piece) < FDAT_CHUNK_PAYLOAD_MAX:
            out.extend(bytes(FDAT_CHUNK_PAYLOAD_MAX - len(piece)))
    return bytes(out)


def verify_fdat_chunk_stream(
    stream_bytes: bytes,
    *,
    return_payload: bool = False,
) -> Tuple[FdatChunkAuditResult, Optional[bytes]]:
    """Verify 1024-byte `<HH` checksum + length/0x8000 terminal-flag chunk framing."""
    checksum_errors: List[str] = []
    framing_errors: List[str] = []

    if len(stream_bytes) == 0 or (len(stream_bytes) % FDAT_CHUNK_SIZE) != 0:
        framing_errors.append(
            f"Stream length {len(stream_bytes)} is not a positive multiple of {FDAT_CHUNK_SIZE} bytes"
        )
        res = FdatChunkAuditResult(
            valid=False,
            chunk_count=0,
            total_stream_bytes=len(stream_bytes),
            reconstructed_bytes=0,
            terminal_flag_seen=False,
            checksum_errors=(),
            framing_errors=tuple(framing_errors),
            reconstructed_sha256="",
        )
        return res, None

    chunk_count = len(stream_bytes) // FDAT_CHUNK_SIZE
    reconstructed = bytearray()
    terminal_seen = False

    for idx in range(chunk_count):
        base = idx * FDAT_CHUNK_SIZE
        expected_chk, raw_len = struct.unpack_from("<HH", stream_bytes, base)
        is_term = bool(raw_len & FDAT_CHUNK_TERMINAL_FLAG)
        payload_len = raw_len & 0x7FFF

        if terminal_seen:
            framing_errors.append(
                f"Chunk {idx}: trailing data found after terminal 0x8000 chunk"
            )
            break

        if payload_len > FDAT_CHUNK_PAYLOAD_MAX:
            framing_errors.append(
                f"Chunk {idx}: payload length {payload_len} exceeds {FDAT_CHUNK_PAYLOAD_MAX}"
            )
            continue

        if not is_term and payload_len != FDAT_CHUNK_PAYLOAD_MAX:
            framing_errors.append(
                f"Chunk {idx}: non-terminal chunk has short payload {payload_len} (< {FDAT_CHUNK_PAYLOAD_MAX})"
            )

        piece = stream_bytes[base + FDAT_CHUNK_HEADER_SIZE : base + FDAT_CHUNK_HEADER_SIZE + payload_len]
        pad = stream_bytes[base + FDAT_CHUNK_HEADER_SIZE + payload_len : base + FDAT_CHUNK_SIZE]
        if any(b != 0 for b in pad):
            framing_errors.append(f"Chunk {idx}: non-zero padding bytes beyond payload_len={payload_len}")

        computed_chk = sum(piece) & 0xFFFF
        if computed_chk != expected_chk:
            checksum_errors.append(
                f"Chunk {idx}: u16 checksum mismatch header={expected_chk:#06x} computed={computed_chk:#06x}"
            )

        reconstructed.extend(piece)
        if is_term:
            terminal_seen = True

    if not terminal_seen:
        framing_errors.append("Missing 0x8000 terminal chunk flag in final 1024-byte frame")

    rec_bytes = bytes(reconstructed)
    valid = len(checksum_errors) == 0 and len(framing_errors) == 0 and terminal_seen
    res = FdatChunkAuditResult(
        valid=valid,
        chunk_count=chunk_count,
        total_stream_bytes=len(stream_bytes),
        reconstructed_bytes=len(rec_bytes),
        terminal_flag_seen=terminal_seen,
        checksum_errors=tuple(checksum_errors),
        framing_errors=tuple(framing_errors),
        reconstructed_sha256=hashlib.sha256(rec_bytes).hexdigest(),
    )
    return res, (rec_bytes if return_payload else None)


def build_udtrfirm_container(
    partitions: Sequence[Tuple[str, int, bytes]],
    *,
    model_id: int = MODEL_ID_FX3,
    version: int = 1,
    flags: int = 0,
) -> bytes:
    """Build a deterministic clean-room UDTRFIRM partition manifest + payload container."""
    header_size = UDTRFIRM_HEADER_STRUCT.size
    table_size = len(partitions) * UDTRFIRM_ENTRY_STRUCT.size
    cursor = header_size + table_size

    entry_blobs = bytearray()
    payload_blobs = bytearray()
    for name, part_idx, data in partitions:
        name_b = name.encode("ascii")
        if len(name_b) > 32:
            raise ValueError(f"UDTRFIRM partition name exceeds 32 bytes: {name!r}")
        digest = hashlib.sha256(data).digest()
        entry_blobs.extend(
            UDTRFIRM_ENTRY_STRUCT.pack(
                name_b.ljust(32, b"\x00"),
                part_idx,
                cursor,
                len(data),
                digest,
            )
        )
        payload_blobs.extend(data)
        cursor += len(data)

    header = UDTRFIRM_HEADER_STRUCT.pack(
        UDTRFIRM_MAGIC,
        version,
        len(partitions),
        model_id,
        flags,
    )
    return header + bytes(entry_blobs) + bytes(payload_blobs)


def parse_udtrfirm_container(data: bytes) -> UdtRFirmManifest:
    """Parse and SHA-256 verify a UDTRFIRM inner partition manifest container."""
    errors: List[str] = []
    if len(data) < UDTRFIRM_HEADER_STRUCT.size:
        return UdtRFirmManifest(
            valid=False,
            magic_ok=False,
            version=0,
            model_id=0,
            entry_count=0,
            entries=(),
            errors=(f"Truncated UDTRFIRM header ({len(data)} bytes)",),
        )

    magic, version, entry_count, model_id, _flags = UDTRFIRM_HEADER_STRUCT.unpack_from(data, 0)
    magic_ok = magic == UDTRFIRM_MAGIC
    if not magic_ok:
        errors.append(f"Invalid UDTRFIRM magic {magic!r} (expected {UDTRFIRM_MAGIC!r})")

    table_end = UDTRFIRM_HEADER_STRUCT.size + entry_count * UDTRFIRM_ENTRY_STRUCT.size
    if table_end > len(data):
        errors.append(
            f"UDTRFIRM entry table ({entry_count} entries -> {table_end} bytes) exceeds buffer {len(data)}"
        )
        return UdtRFirmManifest(
            valid=False,
            magic_ok=magic_ok,
            version=version,
            model_id=model_id,
            entry_count=entry_count,
            entries=(),
            errors=tuple(errors),
        )

    entries: List[UdtRFirmEntry] = []
    for idx in range(entry_count):
        off = UDTRFIRM_HEADER_STRUCT.size + idx * UDTRFIRM_ENTRY_STRUCT.size
        raw_name, part_idx, p_off, p_size, expected_sha = UDTRFIRM_ENTRY_STRUCT.unpack_from(data, off)
        name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="replace")
        if p_off < table_end or p_off + p_size > len(data):
            errors.append(
                f"UDTRFIRM entry {idx} ({name}): span [{p_off:#x}..{p_off + p_size:#x}) out of bounds"
            )
            actual_hex = ""
        else:
            slice_data = data[p_off : p_off + p_size]
            actual_digest = hashlib.sha256(slice_data).digest()
            actual_hex = actual_digest.hex()
            if actual_digest != expected_sha:
                errors.append(
                    f"UDTRFIRM entry {idx} ({name}): SHA-256 mismatch "
                    f"expected={expected_sha.hex()} actual={actual_hex}"
                )
        entries.append(
            UdtRFirmEntry(
                name=name,
                partition_index=part_idx,
                offset=p_off,
                size=p_size,
                sha256_hex=actual_hex or expected_sha.hex(),
            )
        )

    return UdtRFirmManifest(
        valid=magic_ok and len(errors) == 0,
        magic_ok=magic_ok,
        version=version,
        model_id=model_id,
        entry_count=entry_count,
        entries=tuple(entries),
        errors=tuple(errors),
    )


def build_synthetic_ufu_container(
    *,
    model_id: int = MODEL_ID_FX3,
    header_version: int = 1,
    partitions: Optional[Sequence[Tuple[str, int, bytes]]] = None,
    iv: Optional[bytes] = None,
    signature: Optional[bytes] = None,
    chunk_stream_override: Optional[bytes] = None,
) -> bytes:
    """Build a keyless clean-room synthetic BODYDATA.DAT / UFU envelope for structural auditing."""
    if partitions is None:
        partitions = (
            ("/dev/nflasha3", 3, b"SYNTH_VMLINUX_INITRD_FX3_702"),
            ("/dev/nflasha7", 7, b"SYNTH_EXT2_ROOTFS_FX3_0x19000_SECTORS"),
            ("/dev/nflasha15", 15, b"SYNTH_USR_APPFW_50MB_CONTAINER"),
        )
    udtrfirm_raw = build_udtrfirm_container(partitions, model_id=model_id)
    chunk_stream = (
        chunk_stream_override
        if chunk_stream_override is not None
        else build_fdat_chunk_stream(udtrfirm_raw)
    )

    iv_bytes = PUBLIC_EMPTY_SHA256_PREFIX16 if iv is None else iv
    if len(iv_bytes) != FDAT_IV_BYTES:
        raise ValueError(f"IV must be {FDAT_IV_BYTES} bytes, got {len(iv_bytes)}")

    if signature is None:
        # Public deterministic non-secret RSA-2048-sized structural placeholder digest chain
        sig_blocks = bytearray()
        seed = hashlib.sha256(chunk_stream + iv_bytes).digest()
        for idx in range(FDAT_RSA2048_SIG_BYTES // 32):
            sig_blocks.extend(hashlib.sha256(seed + bytes([idx])).digest())
        sig_bytes = bytes(sig_blocks)
    else:
        sig_bytes = signature
    if len(sig_bytes) != FDAT_RSA2048_SIG_BYTES:
        raise ValueError(f"RSA-2048 signature trailer must be {FDAT_RSA2048_SIG_BYTES} bytes")

    ufu_hdr = UFU_HEADER_STRUCT.pack(UFU_MAGIC, header_version, model_id, 1)
    fdat_hdr = FDAT_BLOCK_HEADER_STRUCT.pack(FDAT_MAGIC, len(chunk_stream), model_id, 0)
    return ufu_hdr + fdat_hdr + chunk_stream + iv_bytes + sig_bytes


def audit_ufu_container(
    data: bytes,
    *,
    expected_model_id: int = MODEL_ID_FX3,
    byof_decrypt_callback: Optional[Callable[[bytes, bytes], bytes]] = None,
) -> UfuAuditReport:
    """Audit a UFU / BODYDATA.DAT container structurally (keyless or with caller BYOF callback)."""
    errors: List[str] = []
    warnings: List[str] = []

    if len(data) < UFU_HEADER_STRUCT.size:
        return UfuAuditReport(
            valid=False,
            ufu_magic_ok=False,
            header_version=0,
            envelope_model_id=0,
            expected_model_id=expected_model_id,
            model_id_match=False,
            brick_guard_code="TRUNCATED_UFU_ENVELOPE",
            fdat_found=False,
            fdat_offset=-1,
            fdat_payload_size=0,
            fdat_trailer_offset=-1,
            fdat_trailer_bytes=0,
            fdat_iv_hex="",
            fdat_rsa2048_sig_bytes=0,
            fdat_trailer_non_degenerate=False,
            chunk_audit=None,
            udtrfirm_manifest=None,
            byof_callback_invoked=False,
            errors=(f"Truncated UFU envelope ({len(data)} bytes)",),
            warnings=(),
        )

    magic, hdr_ver, env_model_id, _blk_count = UFU_HEADER_STRUCT.unpack_from(data, 0)
    ufu_magic_ok = magic == UFU_MAGIC
    if not ufu_magic_ok:
        errors.append(f"Invalid UFU envelope magic {magic!r} (expected {UFU_MAGIC!r})")

    model_match = env_model_id == expected_model_id
    brick_code = "OK_MODEL_MATCH"
    if not model_match:
        brick_code = "5L+6S_MODEL_ID_MISMATCH_BRICK_GUARD"
        errors.append(
            f"Model ID mismatch: envelope={env_model_id:#010x} "
            f"({KNOWN_MODEL_IDS.get(env_model_id, 'UNKNOWN')}) != expected={expected_model_id:#010x} "
            f"({KNOWN_MODEL_IDS.get(expected_model_id, 'UNKNOWN')}) -> blocks 5L+6S updater rejection!"
        )

    fdat_off = data.find(FDAT_MAGIC, UFU_HEADER_STRUCT.size)
    if fdat_off < 0 or fdat_off + FDAT_BLOCK_HEADER_STRUCT.size > len(data):
        errors.append("Missing or truncated FDAT block header inside UFU envelope")
        return UfuAuditReport(
            valid=False,
            ufu_magic_ok=ufu_magic_ok,
            header_version=hdr_ver,
            envelope_model_id=env_model_id,
            expected_model_id=expected_model_id,
            model_id_match=model_match,
            brick_guard_code=brick_code,
            fdat_found=False,
            fdat_offset=-1,
            fdat_payload_size=0,
            fdat_trailer_offset=-1,
            fdat_trailer_bytes=0,
            fdat_iv_hex="",
            fdat_rsa2048_sig_bytes=0,
            fdat_trailer_non_degenerate=False,
            chunk_audit=None,
            udtrfirm_manifest=None,
            byof_callback_invoked=False,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    tag, payload_size, fdat_model_id, _fdat_flags = FDAT_BLOCK_HEADER_STRUCT.unpack_from(data, fdat_off)
    if tag != FDAT_MAGIC:
        errors.append(f"Unexpected FDAT tag {tag!r}")
    if fdat_model_id != env_model_id:
        errors.append(
            f"FDAT inner model_id {fdat_model_id:#010x} disagrees with UFU envelope {env_model_id:#010x}"
        )
        if model_match:
            model_match = False
            brick_code = "5L+6S_MODEL_ID_MISMATCH_BRICK_GUARD"

    payload_start = fdat_off + FDAT_BLOCK_HEADER_STRUCT.size
    trailer_off = payload_start + payload_size
    trailer_end = trailer_off + FDAT_TRAILER_BYTES

    if payload_size == 0 or trailer_end > len(data):
        errors.append(
            f"FDAT payload+trailer span [{payload_start:#x}..{trailer_end:#x}) exceeds UFU length {len(data):#x}"
        )
        return UfuAuditReport(
            valid=False,
            ufu_magic_ok=ufu_magic_ok,
            header_version=hdr_ver,
            envelope_model_id=env_model_id,
            expected_model_id=expected_model_id,
            model_id_match=model_match,
            brick_guard_code=brick_code,
            fdat_found=True,
            fdat_offset=fdat_off,
            fdat_payload_size=payload_size,
            fdat_trailer_offset=trailer_off,
            fdat_trailer_bytes=max(0, len(data) - trailer_off),
            fdat_iv_hex="",
            fdat_rsa2048_sig_bytes=0,
            fdat_trailer_non_degenerate=False,
            chunk_audit=None,
            udtrfirm_manifest=None,
            byof_callback_invoked=False,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    iv_bytes = data[trailer_off : trailer_off + FDAT_IV_BYTES]
    sig_bytes = data[trailer_off + FDAT_IV_BYTES : trailer_end]
    non_degenerate = any(b != 0 for b in iv_bytes) and len(set(sig_bytes)) > 1
    if not non_degenerate:
        errors.append("Degenerate all-zero/constant FDAT 16B IV or 256B RSA-2048 signature trailer")

    raw_payload = data[payload_start:trailer_off]
    byof_invoked = False
    if byof_decrypt_callback is not None:
        raw_payload = byof_decrypt_callback(raw_payload, iv_bytes)
        byof_invoked = True

    chunk_audit, reconstructed = verify_fdat_chunk_stream(raw_payload, return_payload=True)
    if not chunk_audit.valid:
        errors.extend(chunk_audit.framing_errors)
        errors.extend(chunk_audit.checksum_errors)

    manifest: Optional[UdtRFirmManifest] = None
    if reconstructed is not None:
        if reconstructed.startswith(UDTRFIRM_MAGIC):
            manifest = parse_udtrfirm_container(reconstructed)
            if not manifest.valid:
                errors.extend(manifest.errors)
        else:
            warnings.append("Reconstructed FDAT payload is encrypted or non-UDTRFIRM (keyless mode)")

    valid = (
        ufu_magic_ok
        and model_match
        and non_degenerate
        and chunk_audit.valid
        and (manifest is None or manifest.valid)
        and len(errors) == 0
    )

    return UfuAuditReport(
        valid=valid,
        ufu_magic_ok=ufu_magic_ok,
        header_version=hdr_ver,
        envelope_model_id=env_model_id,
        expected_model_id=expected_model_id,
        model_id_match=model_match,
        brick_guard_code=brick_code,
        fdat_found=True,
        fdat_offset=fdat_off,
        fdat_payload_size=payload_size,
        fdat_trailer_offset=trailer_off,
        fdat_trailer_bytes=FDAT_TRAILER_BYTES,
        fdat_iv_hex=iv_bytes.hex(),
        fdat_rsa2048_sig_bytes=len(sig_bytes),
        fdat_trailer_non_degenerate=non_degenerate,
        chunk_audit=chunk_audit,
        udtrfirm_manifest=manifest,
        byof_callback_invoked=byof_invoked,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def build_sdm2_partition_table(
    entries: Sequence[Tuple[int, int, int, int]],
) -> bytes:
    """Serialize 30 `(start_sector, size_sectors, part_type, flag)` entries into 512-byte SDM2 Sector 0."""
    if len(entries) != SDM2_ENTRY_COUNT:
        raise ValueError(f"Expected {SDM2_ENTRY_COUNT} SDM2 entries, got {len(entries)}")
    buf = bytearray(SDM2_TABLE_BYTES)
    buf[0:4] = SDM2_PTBL_MAGIC
    buf[4:8] = SDM2_PTBL_VERSION
    struct.pack_into("<I", buf, 8, SDM2_ENTRY_COUNT)
    for idx, (start_s, size_s, ptype, flag) in enumerate(entries):
        struct.pack_into("<IIII", buf, 32 + idx * 16, start_s, size_s, ptype, flag)
    return bytes(buf)


def audit_sdm2_partition_table(data: bytes) -> Sdm2AuditResult:
    """Validate Sony SDM2 (`8246`, `2.00`) 30-entry partition table & AES-XTS-256 (`type=5, flag&1`) flags."""
    errors: List[str] = []
    warnings: List[str] = []
    if len(data) != SDM2_TABLE_BYTES:
        return Sdm2AuditResult(
            valid=False,
            magic_ok=False,
            version_ok=False,
            entry_count=0,
            layout_profile="INVALID_SIZE",
            xts_encrypted_partitions=(),
            plaintext_partitions=(),
            has_overlaps=False,
            emmc_static_boot_sig_required=False,
            errors=(f"Expected {SDM2_TABLE_BYTES} bytes, got {len(data)}",),
            warnings=(),
            descriptors=(),
        )

    magic = data[0:4]
    version = data[4:8]
    count = struct.unpack_from("<I", data, 8)[0]
    magic_ok = magic == SDM2_PTBL_MAGIC
    version_ok = version == SDM2_PTBL_VERSION
    if not magic_ok:
        errors.append(f"Invalid SDM2 magic {magic!r} (expected {SDM2_PTBL_MAGIC!r})")
    if not version_ok:
        errors.append(f"Invalid SDM2 version {version!r} (expected {SDM2_PTBL_VERSION!r})")
    if count != SDM2_ENTRY_COUNT:
        errors.append(f"Invalid SDM2 entry count {count} (expected {SDM2_ENTRY_COUNT})")

    descriptors: List[Sdm2PartitionDescriptor] = []
    xts_parts: List[int] = []
    plain_parts: List[int] = []
    spans: List[Tuple[int, int, int]] = []
    has_overlaps = False

    for idx in range(SDM2_ENTRY_COUNT):
        part_num = idx + 1
        start_s, size_s, ptype, flag = struct.unpack_from("<IIII", data, 32 + idx * 16)
        is_xts = ptype == 5 and bool(flag & 1)
        dev_node = f"/dev/cnflasha{part_num}" if is_xts else f"/dev/pnflasha{part_num}"
        if size_s > 0:
            if is_xts:
                xts_parts.append(part_num)
            else:
                plain_parts.append(part_num)
            if start_s < 0x80:
                errors.append(f"Partition p{part_num} start {start_s:#x} collides with Sector 0 (<0x80)")
                has_overlaps = True
            end_s = start_s + size_s
            for ps, pe, pidx in spans:
                if not (end_s <= ps or start_s >= pe):
                    errors.append(
                        f"Partition p{part_num} [{start_s:#x}..{end_s:#x}) overlaps p{pidx} [{ps:#x}..{pe:#x})"
                    )
                    has_overlaps = True
            spans.append((start_s, end_s, part_num))

        descriptors.append(
            Sdm2PartitionDescriptor(
                index=part_num,
                start_sector=start_s,
                size_sectors=size_s,
                part_type=ptype,
                flag=flag,
                aes_xts_256_encrypted=is_xts,
                device_node=dev_node,
            )
        )

    by_idx = {d.index: d for d in descriptors}
    p7 = by_idx[7]
    p12 = by_idx[12]
    p18 = by_idx[18]
    layout_profile = "CUSTOM_OR_UNKNOWN"
    if p7.size_sectors == 0x00019000 and p12.size_sectors == 0x00014000 and p18.start_sector == 0x0031C000:
        layout_profile = "FX3_702"
    elif p7.size_sectors == 0 and p12.size_sectors == 0x0000A000 and p18.start_sector == 0x00312000:
        layout_profile = "FX6_601"
        warnings.append("FX6_601 layout shifts p18 (/lens) to 0x312000 (-20 MiB vs FX3 0x31C000)")

    return Sdm2AuditResult(
        valid=magic_ok and version_ok and count == SDM2_ENTRY_COUNT and not has_overlaps and len(errors) == 0,
        magic_ok=magic_ok,
        version_ok=version_ok,
        entry_count=count,
        layout_profile=layout_profile,
        xts_encrypted_partitions=tuple(xts_parts),
        plaintext_partitions=tuple(plain_parts),
        has_overlaps=has_overlaps,
        emmc_static_boot_sig_required=False,  # BootROM / eMMC relies on XTS-256 + nflasha1 updater sig
        errors=tuple(errors),
        warnings=tuple(warnings),
        descriptors=tuple(descriptors),
    )


def default_fx3_sdm2_entries() -> List[Tuple[int, int, int, int]]:
    """Return canonical 30-entry FX3 7.02 SDM2 Sector-0 partition descriptors."""
    entries: List[Tuple[int, int, int, int]] = [(0, 0, 0, 0)] * SDM2_ENTRY_COUNT
    entries[0] = (0x00000080, 0x0000BF80, 4, 1)  # p1:/updater plaintext VFAT
    entries[1] = (0x0000C000, 0x0000A000, 4, 1)  # p2:/setting plaintext
    entries[2] = (0x00016000, 0x00025800, 5, 1)  # p3:/system XTS
    entries[4] = (0x00042000, 0x00096000, 6, 1)  # p5:/wbi
    entries[5] = (0x000D8000, 0x0000C800, 4, 1)  # p6:/tmp/jiritsu calibration
    entries[6] = (0x000E4800, 0x00019000, 5, 1)  # p7:/rootfs XTS (0x19000 on FX3)
    entries[7] = (0x000FD800, 0x00032000, 5, 1)  # p8:/cp XTS
    entries[11] = (0x0020C000, 0x00014000, 5, 1)  # p12:/cert XTS
    entries[14] = (0x00222000, 0x000FA000, 5, 1)  # p15:/usr XTS (ends at 0x31C000)
    entries[17] = (0x0031C000, 0x0000A000, 4, 1)  # p18:/lens calibration
    entries[29] = (0x00346000, 0x00018000, 4, 1)  # p30:/usr/data/lut
    return entries


def audit_ufu_suite() -> Dict[str, object]:
    """Run clean-room keyless UFU/FDAT/UDTRFIRM & SDM2 structural verification suite."""
    fx3_ufu = build_synthetic_ufu_container(model_id=MODEL_ID_FX3)
    fx3_rep = audit_ufu_container(fx3_ufu, expected_model_id=MODEL_ID_FX3)

    fx3a_ufu = build_synthetic_ufu_container(model_id=MODEL_ID_FX3A)
    fx3a_mismatch_rep = audit_ufu_container(fx3a_ufu, expected_model_id=MODEL_ID_FX3)

    sdm2_bytes = build_sdm2_partition_table(default_fx3_sdm2_entries())
    sdm2_rep = audit_sdm2_partition_table(sdm2_bytes)

    all_ok = (
        fx3_rep.valid
        and (not fx3a_mismatch_rep.valid)
        and fx3a_mismatch_rep.brick_guard_code == "5L+6S_MODEL_ID_MISMATCH_BRICK_GUARD"
        and sdm2_rep.valid
        and sdm2_rep.layout_profile == "FX3_702"
        and (15 in sdm2_rep.xts_encrypted_partitions)
    )
    return {
        "all_checks_passed": all_ok,
        "keyless_clean_room_mode": True,
        "public_header_vector_sha256_empty_16b": PUBLIC_EMPTY_SHA256_PREFIX16.hex(),
        "fx3_synthetic_ufu": asdict(fx3_rep),
        "fx3a_model_mismatch_guard": asdict(fx3a_mismatch_rep),
        "sdm2_fx3_partition_table": {
            "valid": sdm2_rep.valid,
            "layout_profile": sdm2_rep.layout_profile,
            "xts_encrypted_partitions": list(sdm2_rep.xts_encrypted_partitions),
            "plaintext_partitions": list(sdm2_rep.plaintext_partitions),
            "emmc_static_boot_sig_required": sdm2_rep.emmc_static_boot_sig_required,
        },
    }
