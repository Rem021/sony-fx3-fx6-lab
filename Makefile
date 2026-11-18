# Unified Sony FX3 / FX6 Lab Verification & Candidate Dry-Run Makefile
PYTHON ?= /usr/bin/python3
PYFLAGS := -B
CLOSURE_PYTHONPATH := outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure

.PHONY: all test test-json dry-run readiness-packet lifecycle-drill stage-b-lifecycle-drill clean-audit verify-storage-ram-budget verify-p1-recovery-bridge verify-stage-a-orchestrator verify-kmod-userland-abi verify-peripheral-ux verify-ap-cp-imaging verify-stage-b-p10 verify-uipc-cp-shim verify-wireless-guard verify-firmware-lab verify-coemulation verify-byof verify-20-gates verify-24-gates verify-32-gates verify-40-gates verify-44-gates verify-48-gates verify-50-gates verify-52-gates verify-54-gates verify-56-gates verify-58-gates verify-rp2040-fixture verify-init2-escape verify-tier0-backup verify-antirollback-guard verify-10pillar-recovery verify-13pillar-recovery verify-17pillar-recovery verify-22pillar-recovery verify-post-trial-audit verify-milestone-90 verify-milestone-110 verify-milestone-130 verify-sd-stageb-bundle verify-milestone-147 preflight-realhw-bench verify-milestone-175 verify-milestone-193 verify-milestone-209 verify-milestone-221 verify-milestone-233 verify-milestone-254 verify-milestone-264 verify-milestone-295 verify-milestone-311 verify-milestone-324 verify-milestone-349 verify-fast

all: test

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(PYFLAGS) scripts/run_all_lab_tests.py

test-json:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(PYFLAGS) scripts/run_all_lab_tests.py --json

dry-run:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure dry-run-candidate

readiness-packet:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure build-readiness-packet

lifecycle-drill:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure run-h0-h1-h2-drill

stage-b-lifecycle-drill:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure run-stage-b-lifecycle-drill

verify-storage-ram-budget:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-storage-ram-budget

verify-p1-recovery-bridge:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-p1-recovery-bridge

verify-stage-a-orchestrator:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-stage-a-orchestrator

verify-kmod-userland-abi:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-kmod-userland-abi

verify-peripheral-ux:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-peripheral-ux

verify-ap-cp-imaging:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-ap-cp-imaging

verify-stage-b-p10:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-stage-b-p10

verify-uipc-cp-shim:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-uipc-cp-shim

verify-wireless-guard:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-wireless-guard

verify-firmware-lab:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-firmware-lab" $(PYTHON) $(PYFLAGS) -m fx3_firmware_lab audit-all

verify-coemulation:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-vm" $(PYTHON) $(PYFLAGS) outputs/fx3-vm/fx3_vm_coemulation_suite.py

verify-byof:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(PYFLAGS) scripts/verify_byof_manifest.py

verify-20-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-20-gates --dry-run-simulated-backup

verify-24-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-24-gates --dry-run-simulated-backup

verify-32-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-32-gates --dry-run-simulated-backup

verify-40-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-40-gates --dry-run-simulated-backup

verify-44-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-44-gates --dry-run-simulated-backup

verify-48-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-48-gates --dry-run-simulated-backup

verify-50-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-50-gates --dry-run-simulated-backup

verify-52-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-52-gates --dry-run-simulated-backup

verify-54-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-54-gates --dry-run-simulated-backup

verify-56-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-56-gates --dry-run-simulated-backup

verify-58-gates:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-58-gates --dry-run-simulated-backup

verify-rp2040-fixture:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-rp2040-fixture

verify-init2-escape:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-init2-escape

verify-tier0-backup:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-tier0-backup

verify-antirollback-guard:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-antirollback-guard

verify-10pillar-recovery:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106

verify-13pillar-recovery:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124

verify-17pillar-recovery:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138 --with-phase139

verify-22pillar-recovery:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-22pillar-recovery

verify-post-trial-audit:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" $(PYTHON) $(PYFLAGS) -m fx6_closure audit-stage-b-post-trial

verify-milestone-90:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-90

verify-milestone-110:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-110

verify-milestone-130:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-130

verify-sd-stageb-bundle:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-sd-stageb-bundle-uninstaller

verify-milestone-147:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-147

preflight-realhw-bench:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure preflight-realhw-bench --simulate-ready-bench

verify-milestone-175:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-175

verify-milestone-193:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-193
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-193 --force-clean-room

verify-milestone-209:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-209
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-209 --force-clean-room

verify-milestone-221:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-221
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-221 --force-clean-room

verify-milestone-233:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-233
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-233 --force-clean-room

verify-milestone-254:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-254
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-254 --force-clean-room

verify-milestone-264:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-264
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-264 --force-clean-room

verify-milestone-295:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-295
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-295 --force-clean-room

verify-milestone-311:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-311
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-311 --force-clean-room

verify-milestone-324:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-324
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-324 --force-clean-room

verify-milestone-349:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-349
	FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-milestone-349 --force-clean-room

verify-fast: verify-byof verify-40-gates verify-44-gates verify-58-gates verify-13pillar-recovery verify-17pillar-recovery verify-22pillar-recovery verify-firmware-lab verify-coemulation verify-milestone-130 verify-milestone-147 verify-milestone-175 verify-milestone-193 verify-milestone-209 verify-milestone-221 verify-milestone-233 verify-milestone-254 verify-milestone-264 verify-milestone-295 verify-milestone-311 verify-milestone-324 verify-milestone-349

clean-audit:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(PYFLAGS) scripts/run_all_lab_tests.py --clean-only
