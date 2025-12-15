from app.core.cache.keys import canonical_json, canonical_query_string, hash_bytes, hash_text


def test_canonical_json_is_stable() -> None:
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert canonical_json(a) == canonical_json(b)


def test_canonical_query_string_is_sorted_and_skips_none() -> None:
    qs = canonical_query_string({"b": 2, "a": 1, "c": None})
    assert qs == "a=1&b=2"


def test_hash_helpers_are_consistent() -> None:
    assert hash_text("hello") == hash_bytes(b"hello")
