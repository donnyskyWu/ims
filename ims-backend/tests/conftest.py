"""Pytest hooks for ims-backend (schema reset lives in tests/schema_reset.py)."""

import pytest


@pytest.fixture(autouse=True)
def _reset_schema_before_test(request):
    if request.node.get_closest_marker("l3"):
        return
    from tests.schema_reset import reset_ims_test_schema

    reset_ims_test_schema()
