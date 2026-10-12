PYTHON ?= python3

.PHONY: api-gen error-codes test check-static

api-gen:
	$(PYTHON) -m tools.api_gen

error-codes:
	$(PYTHON) -m tools.export_error_codes

check-static:
	$(PYTHON) -m tools.static_checks

test:
	$(PYTHON) -m pytest -q
