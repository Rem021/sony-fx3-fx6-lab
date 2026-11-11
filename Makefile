# Unified Sony FX3 / FX6 Lab Verification & Candidate Dry-Run Makefile
PYTHON ?= /usr/bin/python3
PYFLAGS := -B
CLOSURE_PYTHONPATH := outputs/fx3-safety:outputs/fx6-on-fx3-closure

.PHONY: all test test-json dry-run clean-audit verify-storage-ram-budget verify-p1-recovery-bridge verify-stage-a-orchestrator verify-byof

all: test

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(PYFLAGS) scripts/run_all_lab_tests.py

test-json:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(PYFLAGS) scripts/run_all_lab_tests.py --json

dry-run:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure dry-run-candidate

verify-storage-ram-budget:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-storage-ram-budget

verify-p1-recovery-bridge:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-p1-recovery-bridge

verify-stage-a-orchestrator:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CLOSURE_PYTHONPATH)" $(PYTHON) $(PYFLAGS) -m fx6_closure verify-stage-a-orchestrator

verify-byof:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(PYFLAGS) scripts/verify_byof_manifest.py

clean-audit:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(PYFLAGS) scripts/run_all_lab_tests.py --clean-only
