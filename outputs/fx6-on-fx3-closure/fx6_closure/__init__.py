"""FX6-on-FX3 Phase 12 Compatibility Closure, U1-U5 Blueprint Closure, p1 Recovery Bridge, WBI (p5) Safety Redline & Atomic Stage-A Boot Orchestrator Suite."""

from __future__ import annotations

__version__ = "12.0.0"

from .stage_a_boot_orchestrator import (
    BootArtifactDigestRecord,
    CandidateWbiRedlineAudit,
    EXPECTED_STAGE_A_FORWARD_STEP_IDS,
    InitrdBootChainContractAudit,
    ORCHESTRATOR_CPIO_REL_PATH,
    OrchestratorSandboxRunResult,
    OrchestratorScenarioResult,
    OrchestratorStateMachineTrace,
    PINNED_FX6_WBI_NFLASH5_BYTES,
    PINNED_FX6_WBI_NFLASH5_SHA256,
    PINNED_INITRD_AND_BOOT_ARTIFACTS,
    Phase12StageABootOrchestratorReport,
    Wbi2HeaderAudit,
    audit_initrd_boot_chain_and_wbi_contracts,
    generate_stage_a_boot_orchestrator_script,
    parse_wbi2_header_bytes,
    run_stage_a_boot_orchestrator_verification,
    simulate_orchestrator_state_machine,
    validate_candidate_wbi_redline,
)

__all__ = [
    "__version__",
    "BootArtifactDigestRecord",
    "CandidateWbiRedlineAudit",
    "EXPECTED_STAGE_A_FORWARD_STEP_IDS",
    "InitrdBootChainContractAudit",
    "ORCHESTRATOR_CPIO_REL_PATH",
    "OrchestratorSandboxRunResult",
    "OrchestratorScenarioResult",
    "OrchestratorStateMachineTrace",
    "PINNED_FX6_WBI_NFLASH5_BYTES",
    "PINNED_FX6_WBI_NFLASH5_SHA256",
    "PINNED_INITRD_AND_BOOT_ARTIFACTS",
    "Phase12StageABootOrchestratorReport",
    "Wbi2HeaderAudit",
    "audit_initrd_boot_chain_and_wbi_contracts",
    "generate_stage_a_boot_orchestrator_script",
    "parse_wbi2_header_bytes",
    "run_stage_a_boot_orchestrator_verification",
    "simulate_orchestrator_state_machine",
    "validate_candidate_wbi_redline",
]
