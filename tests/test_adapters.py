"""Unit tests for adapter factory / pin floors (S04)."""

from choruscontrol.adapters.factory import build_adapters
from choruscontrol.adapters.nulls import NullCache
from choruscontrol.adapters.pins import PIN_FLOORS, check_pins, version_at_least


def test_version_at_least():
    assert version_at_least("1.3.0", "1.3.0")
    assert version_at_least("1.3.1", "1.3.0")
    assert not version_at_least("1.2.9", "1.3.0")


def test_pin_floors_present():
    assert "chorusgraph" in PIN_FLOORS
    assert "prismguard" in PIN_FLOORS
    report = check_pins()
    assert "pins" in report
    assert len(report["pins"]) == len(PIN_FLOORS)


def test_factory_defaults_to_null_without_siblings():
    bundle = build_adapters(force_demo=True)
    assert isinstance(bundle.cache, NullCache)
    assert all(v == "null" for v in bundle.sources.values())
    assert bundle.pins["pins"]
