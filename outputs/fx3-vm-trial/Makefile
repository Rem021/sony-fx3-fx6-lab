PYTHON ?= python3

.PHONY: all shim clean-cache

all:
	$(PYTHON) -B build_live700.py

shim:
	$(PYTHON) -B build_live700.py --compile-only

clean-cache:
	rm -rf /private/tmp/fx6-live700-zig-cache /private/tmp/fx6_gpe0_scanline_*
