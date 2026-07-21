import pytest

from app.services.registry import ServiceRegistry


def test_register_and_get():
    registry = ServiceRegistry()
    handler = object()
    registry.register("foo", handler)

    assert registry.get("foo") is handler


def test_get_unknown_raises_key_error():
    registry = ServiceRegistry()

    with pytest.raises(KeyError):
        registry.get("missing")
