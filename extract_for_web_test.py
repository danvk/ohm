"""Unit tests for extract_for_web encoding/decoding helpers."""

import base64

from extract_for_web import (
    build_tag_tables,
    decode_ring_varint,
    decode_tags,
    encode_ring_varint,
    encode_tags,
)

# ---------------------------------------------------------------------------
# encode_ring_varint / decode_ring_varint
# ---------------------------------------------------------------------------


def test_ring_varint_empty():
    assert encode_ring_varint([]) == b""
    assert decode_ring_varint(b"") == []


def test_ring_varint_single_positive():
    ids = [100_000_000]
    assert decode_ring_varint(encode_ring_varint(ids)) == ids


def test_ring_varint_single_negative():
    ids = [-100_000_000]
    assert decode_ring_varint(encode_ring_varint(ids)) == ids


def test_ring_varint_roundtrip_simple():
    ids = [10, 20, -30, 40, -50]
    assert decode_ring_varint(encode_ring_varint(ids)) == ids


def test_ring_varint_roundtrip_realistic():
    """Simulate a ring with OSM-scale IDs that are close together."""
    base = 199_978_000
    ids = [base + 283, -(base + 287), base + 286, base + 370, -(base + 369)]
    assert decode_ring_varint(encode_ring_varint(ids)) == ids


def test_ring_varint_roundtrip_large_ids():
    """Maximum realistic OSM way ID magnitude."""
    ids = [202_045_087, -202_045_000, 202_046_157]
    assert decode_ring_varint(encode_ring_varint(ids)) == ids


def test_ring_varint_sign_changes():
    """Alternating signs are encoded correctly."""
    ids = [1, -1, 2, -2, 3, -3]
    assert decode_ring_varint(encode_ring_varint(ids)) == ids


def test_ring_varint_all_negative():
    ids = [-5, -10, -15, -100_000_000]
    assert decode_ring_varint(encode_ring_varint(ids)) == ids


def test_ring_varint_smaller_than_int32():
    """Encoded bytes should be smaller than the equivalent 4-byte int32 encoding
    when IDs are spatially clustered (close to each other)."""
    base = 150_000_000
    ids = [base + i for i in range(20)]
    encoded = encode_ring_varint(ids)
    int32_size = len(ids) * 4
    assert len(encoded) < int32_size


def test_ring_varint_base64_roundtrip():
    """Verify the base64 encode→decode path used in production."""
    ids = [199_978_283, -199_978_287, 199_978_286]
    b64 = base64.b64encode(encode_ring_varint(ids)).decode()
    decoded = decode_ring_varint(base64.b64decode(b64))
    assert decoded == ids


# ---------------------------------------------------------------------------
# build_tag_tables / encode_tags / decode_tags
# ---------------------------------------------------------------------------

SAMPLE_TAGS = [
    {"boundary": "administrative", "admin_level": "6", "name": "Suffolk County"},
    {"boundary": "administrative", "admin_level": "6", "name": "Norfolk County"},
    {"boundary": "administrative", "admin_level": "6", "name": "Essex County"},
    {"boundary": "administrative", "admin_level": "6", "unique_key": "only_here"},
]


def test_build_tag_tables_pair_threshold():
    """Pairs appearing >1 time go into pair_table; singletons do not."""
    pair_table, key_table, val_table = build_tag_tables(SAMPLE_TAGS)
    pairs_as_tuples = [tuple(p) for p in pair_table]
    assert ("boundary", "administrative") in pairs_as_tuples
    assert ("admin_level", "6") in pairs_as_tuples
    # unique_key only appears once — should not be indexed as a pair
    assert ("unique_key", "only_here") not in pairs_as_tuples


def test_build_tag_tables_key_table_sorted():
    pair_table, key_table, val_table = build_tag_tables(SAMPLE_TAGS)
    assert key_table == sorted(key_table)


def test_build_tag_tables_val_table_threshold():
    """Values appearing >1 time go into val_table."""
    pair_table, key_table, val_table = build_tag_tables(SAMPLE_TAGS)
    assert "administrative" in val_table
    assert "6" in val_table
    # "only_here" appears once — not in val_table
    assert "only_here" not in val_table


def test_encode_decode_tags_roundtrip():
    pair_table, key_table, val_table = build_tag_tables(SAMPLE_TAGS)
    for tags in SAMPLE_TAGS:
        flat = encode_tags(tags, pair_table, key_table, val_table)
        assert decode_tags(flat, pair_table, key_table, val_table) == tags


def test_encode_tags_common_pair_is_single_int():
    """A common pair should be encoded as a single negative integer."""
    pair_table, key_table, val_table = build_tag_tables(SAMPLE_TAGS)
    flat = encode_tags({"boundary": "administrative"}, pair_table, key_table, val_table)
    assert len(flat) == 1
    assert isinstance(flat[0], int)
    assert flat[0] < 0


def test_encode_tags_unique_pair_uses_key_and_literal():
    """A singleton pair falls back to [key_idx, literal_string]."""
    pair_table, key_table, val_table = build_tag_tables(SAMPLE_TAGS)
    flat = encode_tags({"unique_key": "only_here"}, pair_table, key_table, val_table)
    assert len(flat) == 2
    assert isinstance(flat[0], int) and flat[0] >= 0
    assert flat[1] == "only_here"


def test_encode_tags_repeated_value_uses_index():
    """A repeated value (in val_table) should be encoded as an int, not a string."""
    pair_table, key_table, val_table = build_tag_tables(SAMPLE_TAGS)
    # "administrative" is repeated, but here we pair it with a key not in pair_table
    # to force the key+value path.  Craft a scenario where the value is repeated
    # but the pair is unique.
    extra_tags = [
        {"type": "boundary"},
        {"kind": "boundary"},  # "boundary" value used with a different key
    ]
    pt, kt, vt = build_tag_tables(extra_tags)
    # "boundary" appears twice as a value across different keys → in val_table
    assert "boundary" in vt
    flat = encode_tags({"type": "boundary"}, pt, kt, vt)
    # Should be [key_idx, val_idx] — both ints
    assert len(flat) == 2
    assert all(isinstance(x, int) and x >= 0 for x in flat)


def test_encode_decode_tags_empty():
    pair_table, key_table, val_table = build_tag_tables([{}])
    assert encode_tags({}, pair_table, key_table, val_table) == []
    assert decode_tags([], pair_table, key_table, val_table) == {}


def test_encode_decode_tags_single_record():
    """Works correctly with only one record (all pairs are singletons)."""
    tags = {"name": "Test Region", "admin_level": "4"}
    pair_table, key_table, val_table = build_tag_tables([tags])
    flat = encode_tags(tags, pair_table, key_table, val_table)
    assert decode_tags(flat, pair_table, key_table, val_table) == tags


def test_encode_tags_coerced_int_value():
    """Non-string values (e.g. color ints) survive encode→decode as strings."""
    tags_raw = {"name": "Region", "color": 2}
    tags_str = {k: str(v) for k, v in tags_raw.items()}
    pair_table, key_table, val_table = build_tag_tables([tags_str])
    flat = encode_tags(tags_str, pair_table, key_table, val_table)
    assert decode_tags(flat, pair_table, key_table, val_table) == tags_str
