"""Clean-room Sony BIONZ XR firmware container, HAITA/BK4 feature, and .uxc/LDEC asset lab."""

from __future__ import annotations

from .haita_bk4_feature_analyzer import (
    BK4PropertyContract,
    HaitaFeatureAuditReport,
    analyze_haita_and_bk4_features,
    audit_bk4_record_bytes,
    build_clean_room_bk4_record,
    prove_product_model_nvram_hazard,
)
from .ufu_container_auditor import (
    FdatChunkAuditResult,
    Sdm2AuditResult,
    UdtRFirmManifest,
    UfuAuditReport,
    audit_sdm2_partition_table,
    audit_ufu_container,
    audit_ufu_suite,
    build_fdat_chunk_stream,
    build_synthetic_ufu_container,
    build_udtrfirm_container,
    parse_udtrfirm_container,
    verify_fdat_chunk_stream,
)
from .uxc_ldec_inspector import (
    LdecDecodeResult,
    UxcContainerSummary,
    UxcInspectionReport,
    UxcSpriteEntry,
    convert_pixel_buffer_to_argb8888,
    decode_ldec_lz77,
    encode_ldec_lz77_raw_or_match,
    inspect_uxc_and_ldec,
    inspect_uxc_bytes,
    rgba4444_to_argb8888,
)

__all__ = [
    "BK4PropertyContract",
    "FdatChunkAuditResult",
    "HaitaFeatureAuditReport",
    "LdecDecodeResult",
    "Sdm2AuditResult",
    "UdtRFirmManifest",
    "UfuAuditReport",
    "UxcContainerSummary",
    "UxcInspectionReport",
    "UxcSpriteEntry",
    "analyze_haita_and_bk4_features",
    "audit_bk4_record_bytes",
    "audit_sdm2_partition_table",
    "audit_ufu_container",
    "audit_ufu_suite",
    "build_clean_room_bk4_record",
    "build_fdat_chunk_stream",
    "build_synthetic_ufu_container",
    "build_udtrfirm_container",
    "convert_pixel_buffer_to_argb8888",
    "decode_ldec_lz77",
    "encode_ldec_lz77_raw_or_match",
    "inspect_uxc_and_ldec",
    "inspect_uxc_bytes",
    "parse_udtrfirm_container",
    "prove_product_model_nvram_hazard",
    "rgba4444_to_argb8888",
    "verify_fdat_chunk_stream",
]
