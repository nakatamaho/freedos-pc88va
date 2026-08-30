.DEFAULT_GOAL := help

.PHONY: help submodules component-status verify-scaffold m01-host-portability m01-image-identity m01-preflight m01-image m01-build m01-compare m01-enroll-golden m01-verify m01-clean verify

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

verify: verify-scaffold
	@if test -f qa/golden/m01-baseline.json && test -d qa/results/m01/run-1 && test -d qa/results/m01/run-2; then \
		bash tools/m01/build_baseline.sh verify; \
	else \
		printf '%s\n' 'M01 verification is not run: no generated two-run evidence is present.'; \
	fi
