# Unified Sony FX3 / FX6 Lab Verification & Candidate Dry-Run Makefile
PYTHON ?= /usr/bin/python3
PYFLAGS := -B
CLOSURE_PYTHONPATH := outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure

.PHONY: all test test-json dry-run readiness-packet lifecycle-drill stage-b-lifecycle-drill clean-audit verify-storage-ram-budget verify-p1-recovery-bridge verify-stage-a-orchestrator verify-kmod-userland-abi verify-peripheral-ux verify-ap-cp-imaging verify-stage-b-p10 verify-uipc-cp-shim verify-wireless-guard verify-firmware-lab verify-coemulation verify-byof

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

clean-audit:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(PYFLAGS) scripts/run_all_lab_tests.py --clean-only
