.DEFAULT_GOAL := help

.PHONY: help submodules component-status verify-scaffold m01-host-portability m01-image-identity m01-preflight m01-image m01-build m01-compare m01-enroll-golden m01-verify m01-clean m02-preflight m02-clean m02-bundle m02-compare m02-verify m02-enroll-golden m02 m03-preflight m03-clean m03-scan m03-compare m03-enroll-golden m03-verify m03 m04-preflight m04-private-evidence m04-verify m04 m04r1-license-verify m05-preflight m05-clean m05-build m05-compare m05-enroll-golden m05-negative-tests m05-verify m05 m06-preflight m06-prepare-m05 m06-clean m06-build m06-nec98-regression m06-media m06-compare m06-enroll-golden m06-negative-tests m06-verify m06 m07-preflight m07-clean m07-probe m07-variants m07-public-tests m07-public-verify m07-enroll-golden m07-redact m07-public m07r2-tests m07r2-verify m07r2-private-evidence m07r2-public m07r3-tests m07r3-verify m07r3-public m07r4-tests m07r4-verify m07r4-public m07r5-tests m07r5-verify m07r5-public m07r6-tests m07r6-verify m07r6-public verify

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
		'  m04-preflight     Verify the accepted public M04 identity' \
		'  m04-private-evidence  Validate local M04 TXT/Markdown locators' \
		'  m04-verify        Verify the public provisional M04 contract' \
		'  m04               Run the public non-destructive M04 verification' \
		'  m04r1-license-verify  Verify the GPL-2.0-or-later root policy' \
		'  m05-preflight     Verify M05 identities and accepted M02 inputs' \
		'  m05-clean         Remove only generated M05 result paths' \
		'  m05-build         Build and inspect two independent M05 media runs' \
		'  m05-compare       Compare complete M05 result trees byte-for-byte' \
		'  m05-enroll-golden Explicitly enroll a passing M05 textual golden' \
		'  m05-negative-tests  Run M05 fail-closed media tests' \
		'  m05-verify        Verify M05 runs against the committed golden' \
		'  m05               Run the complete deterministic M05 sequence' \
		'  m06-preflight     Verify M06 child, historical identities, M05 bytes, and toolchain' \
		'  m06-prepare-m05   Regenerate accepted M05 prerequisites under the M06 gitlink overlay' \
		'  m06-clean         Remove only generated M06 result paths' \
		'  m06-build         Build two PC-88VA targets and two NEC98 regressions' \
		'  m06-nec98-regression  Verify all accepted fdkernel NEC98 artifact hashes' \
		'  m06-media         Build and inspect two derived compile-only media runs' \
		'  m06-compare       Compare complete M06 result trees byte-for-byte' \
		'  m06-enroll-golden Explicitly enroll a passing M06 textual golden' \
		'  m06-negative-tests  Run M06 fail-closed parent tests' \
		'  m06-verify        Verify M06 runs against the committed golden' \
		'  m06               Run the complete deterministic M06 sequence' \
		'  m07-preflight     Verify accepted identities and public M07 inputs' \
		'  m07-clean         Remove only generated public M07 result paths' \
		'  m07-probe         Build the probe and five variants twice' \
		'  m07-variants      Compare complete public result trees' \
		'  m07-public-tests  Run M07 ROM-free fail-closed tests' \
		'  m07-public-verify Verify public results against the M07 golden' \
		'  m07-public        Run the complete ROM-free M07 public gate' \
		'  m07r2-tests       Run synthetic D88 and abstract-boundary tests' \
		'  m07r2-verify      Verify the redacted M07R2 Class A status' \
		'  m07r2-private-evidence  Check ignored local CONTROL evidence without printing values' \
		'  m07r2-public      Run the complete ROM-free M07R2 public gate' \
		'  m07r3-tests       Run M07R3 public abstract-status tests' \
		'  m07r3-verify      Verify the M07R3 public diagnosis record' \
		'  m07r3-public      Run the ROM-free M07R3 public gate' \
		'  m07r4-tests       Run M07R4 public reconstruction-status tests' \
		'  m07r4-verify      Verify the M07R4 abstract B2 reconstruction record' \
		'  m07r4-public      Run the ROM-free M07R4 public gate' \
		'  m07r5-tests       Run M07R5 abstract request-gate tests' \
		'  m07r5-verify      Verify the M07R5 abstract request-gate record' \
		'  m07r5-public      Run the ROM-free M07R5 public gate' \
		'  m07r6-tests       Run M07R6 subsystem command-gate tests' \
		'  m07r6-verify      Verify the M07R6 abstract command-gate record' \
		'  m07r6-public      Run the ROM-free M07R6 public gate' \
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
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m03/verify_m03.py --enroll-golden --supersede-golden

m03-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m03/verify_m03.py --verify

m03:
	@$(MAKE) m03-preflight
	@$(MAKE) m03-clean
	@$(MAKE) m03-scan
	@$(MAKE) m03-compare
	@$(MAKE) m03-verify

m04-preflight:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m04/verify_m04.py --verify

m04-private-evidence:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m04/verify_m04.py --private-evidence

m04-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m04/verify_m04.py --verify

m04:
	@$(MAKE) m04-verify

m04r1-license-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/qa/verify_license_policy.py

m05-preflight:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m05/verify_m05.py --preflight

m05-clean:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m05/verify_m05.py --clean

m05-build:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m05/build_media.py --repo-root . --output qa/results/m05/run-1
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m05/inspect_media.py --repo-root . --run-dir qa/results/m05/run-1
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m05/build_media.py --repo-root . --output qa/results/m05/run-2
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m05/inspect_media.py --repo-root . --run-dir qa/results/m05/run-2

m05-compare:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m05/compare_media.py

m05-enroll-golden:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m05/verify_m05.py --enroll-golden

m05-negative-tests:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/m05 -p 'test_*.py'

m05-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m05/verify_m05.py --verify

m05:
	@$(MAKE) m05-preflight
	@$(MAKE) m05-clean
	@$(MAKE) m05-build
	@$(MAKE) m05-compare
	@$(MAKE) m05-negative-tests
	@$(MAKE) m05-verify

m06-preflight:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --preflight

m06-prepare-m05:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --prepare-m05

m06-clean:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --clean

m06-build:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --build

m06-nec98-regression:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --nec98-regression

m06-media:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --media

m06-compare:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --compare

m06-enroll-golden:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --enroll-golden

m06-negative-tests:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --negative-tests

m06-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m06/m06.py --verify

m06:
	@$(MAKE) m06-preflight
	@$(MAKE) m06-clean
	@$(MAKE) m06-build
	@$(MAKE) m06-nec98-regression
	@$(MAKE) m06-media
	@$(MAKE) m06-compare
	@$(MAKE) m06-negative-tests
	@$(MAKE) m06-verify

m07-preflight:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/m07.py --preflight

m07-clean:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/m07.py --clean

m07-probe:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/m07.py --build

m07-variants:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/m07.py --compare

m07-public-tests:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/m07.py --tests

m07-public-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/m07.py --verify

m07-enroll-golden:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/m07.py --enroll-golden

m07-redact:
	@test -n "$(M07_PRIVATE_RESULT)" || { printf '%s\n' 'M07_PRIVATE_RESULT is required'; exit 2; }
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/redact_private_result.py --input "$(M07_PRIVATE_RESULT)" --output config/m07/public-result.json

m07-public:
	@$(MAKE) m07-preflight
	@$(MAKE) m07-clean
	@$(MAKE) m07-probe
	@$(MAKE) m07-variants
	@$(MAKE) m07-public-tests
	@$(MAKE) m07-public-verify

m07r2-tests:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/m07r2 -p 'test_*.py'

m07r2-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07r2/verify_m07r2.py

m07r2-private-evidence:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07r2/verify_m07r2.py --private-evidence

m07r2-public:
	@$(MAKE) m07r2-tests
	@$(MAKE) m07r2-verify

m07r3-tests:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/m07r3 -p 'test_*.py'

m07r3-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07r3/verify_m07r3.py

m07r3-public:
	@$(MAKE) m07r3-tests
	@$(MAKE) m07r3-verify

m07r4-tests:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/m07/test_m07r4.py

m07r4-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/verify_m07r4.py

m07r4-public:
	@$(MAKE) m07r4-tests
	@$(MAKE) m07r4-verify

m07r5-tests:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/m07/test_m07r5.py

m07r5-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/verify_m07r5.py

m07r5-public:
	@$(MAKE) m07r5-tests
	@$(MAKE) m07r5-verify

m07r6-tests:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/m07/test_m07r6.py

m07r6-verify:
	@PYTHONDONTWRITEBYTECODE=1 python3 tools/m07/verify_m07r6.py

m07r6-public:
	@$(MAKE) m07r6-tests
	@$(MAKE) m07r6-verify

verify: verify-scaffold
	@if test -f qa/golden/m01-baseline.json && test -d qa/results/m01/run-1 && test -d qa/results/m01/run-2; then \
		bash tools/m01/build_baseline.sh verify; \
	else \
		printf '%s\n' 'M01 verification is not run: no generated two-run evidence is present.'; \
	fi
