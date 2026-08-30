.DEFAULT_GOAL := help

.PHONY: help submodules component-status verify-scaffold m01-host-portability m01-image-identity m01-preflight m01-image m01-build m01-compare m01-enroll-golden m01-verify m01-clean m02-preflight m02-clean m02-bundle m02-compare m02-verify m02-enroll-golden m02 m03-preflight m03-clean m03-scan m03-compare m03-enroll-golden m03-verify m03 verify

help:
	@printf '%s\n' \
		'Available targets:' \
		'  help              Show this help' \
		'  submodules        Initialize/update locked submodules' \
		'  component-status  Show submodule status' \
		'  verify-scaffold   Validate the M00 scaffold' \
		'  m01-host-portability  Run host portability regression checks' \
		'  m01-image-identity  Run image identity and cleanup checks' \
		'  m01-preflight     Check the read-only M01 host prerequisites' \
		'  m01-image         Build the pinned M01 toolchain image' \
		'  m01-build         Perform two isolated M01 baseline builds' \
		'  m01-compare       Compare the two M01 build runs' \
		'  m01-enroll-golden Explicitly enroll a passing M01 comparison as golden' \
		'  m01-verify        Run offline M01 verification' \
		'  m01-clean         Remove only ignored M01 build results' \
		'  m02-preflight     Check M02 identity, host, and verified M01 inputs' \
		'  m02-clean         Remove only generated M02 result paths' \
		'  m02-bundle        Assemble independent M02 bundle runs' \
		'  m02-compare       Compare M02 trees, tar archives, and sidecars' \
		'  m02-verify        Verify M02 against its committed golden' \
		'  m02-enroll-golden Enroll an M02 golden after a passing comparison' \
		'  m02               Run the complete non-destructive M02 sequence' \
		'  m03-preflight     Check M03 baseline and component identity' \
		'  m03-clean         Remove only generated M03 result paths' \
		'  m03-scan          Generate two deterministic M03 source censuses' \
		'  m03-compare       Compare the two M03 census outputs' \
		'  m03-enroll-golden Enroll an M03 golden after a passing comparison' \
		'  m03-verify        Verify M03 against its reviewed golden' \
		'  m03               Run the complete non-destructive M03 sequence' \
		'  verify            Run scaffold and available M01 verification'

submodules:
	@git submodule update --init --recursive

component-status:
	@git submodule status --recursive

verify-scaffold:
	@python3 tools/verify_scaffold.py

m01-host-portability:
	@bash tools/m01/test_host_portability.sh

m01-image-identity:
	@python3 tools/m01/test_image_identity.py

m01-preflight:
	@bash tools/m01/build_baseline.sh preflight

m01-image:
	@bash tools/m01/build_baseline.sh image

m01-build:
	@bash tools/m01/build_baseline.sh build

m01-compare:
	@bash tools/m01/build_baseline.sh compare

m01-enroll-golden:
	@bash tools/m01/build_baseline.sh enroll

m01-verify:
	@bash tools/m01/build_baseline.sh verify

m01-clean:
	@bash tools/m01/build_baseline.sh clean

m02-preflight:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m02/assemble_bundle.py --preflight

m02-clean:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m02/assemble_bundle.py --clean

m02-bundle:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m02/assemble_bundle.py --bundle

m02-compare:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m02/compare_bundles.py

m02-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m02/verify_bundle.py

m02-enroll-golden:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m02/verify_bundle.py --enroll-golden --supersede-golden

m02:
	@$(MAKE) m02-preflight
	@$(MAKE) m02-clean
	@$(MAKE) m02-bundle
	@$(MAKE) m02-compare
	@$(MAKE) m02-verify

m03-preflight:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m03/verify_m03.py --baseline

m03-clean:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m03/verify_m03.py --clean

m03-scan:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m03/scan_port_surface.py --repo-root . --output qa/results/m03/run-1/port-surface.json
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m03/scan_port_surface.py --repo-root . --output qa/results/m03/run-2/port-surface.json

m03-compare:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m03/verify_m03.py --compare

m03-enroll-golden:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m03/verify_m03.py --enroll-golden

m03-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m03/verify_m03.py --verify

m03:
	@$(MAKE) m03-preflight
	@$(MAKE) m03-clean
	@$(MAKE) m03-scan
	@$(MAKE) m03-compare
	@$(MAKE) m03-verify

verify: verify-scaffold
	@if test -f qa/golden/m01-baseline.json && test -d qa/results/m01/run-1 && test -d qa/results/m01/run-2; then \
		bash tools/m01/build_baseline.sh verify; \
	else \
		printf '%s\n' 'M01 verification is not run: no generated two-run evidence is present.'; \
	fi
