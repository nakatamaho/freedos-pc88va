.DEFAULT_GOAL := help

.PHONY: help submodules component-status verify-scaffold

help:
	@printf '%s\n' 'Available targets:' '  help              Show this help' '  submodules        Initialize/update locked submodules' '  component-status  Show submodule status' '  verify-scaffold   Validate the M00 scaffold'

submodules:
	@git submodule update --init --recursive

component-status:
	@git submodule status --recursive

verify-scaffold:
	@python3 tools/verify_scaffold.py
