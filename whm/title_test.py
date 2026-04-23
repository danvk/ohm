"""Tests for whm/title.py — WHM feature title parsing."""

from title import TitleParts, extract_base_name, parse_whm_title


def T(name, span=None, leader=None, dynasty=None, note=None):
    """Shorthand TitleParts constructor for test assertions."""
    return TitleParts(name=name, span=span, leader=leader, dynasty=dynasty, note=note)


# ── parse_whm_title ────────────────────────────────────────────────────────────


def test_name_and_span_only():
    assert parse_whm_title("Kish, c2900 - 2350BCE.") == T(
        name="Kish", span="c2900 - 2350BCE"
    )


def test_name_only_no_span():
    assert parse_whm_title("East Turks.") == T(name="East Turks")


def test_single_word_name():
    assert parse_whm_title("Wei.") == T(name="Wei")


def test_name_with_qualifier_and_span():
    # "Old Kingdom" is part of the name, not a separate field
    assert parse_whm_title("Egypt, Old Kingdom, 2925 - c2150BCE + -50 years.") == T(
        name="Egypt, Old Kingdom", span="2925 - c2150BCE + -50 years"
    )


def test_vassal_qualifier_in_name():
    # "Assyrian Vassal" has no date range, so it folds into the name
    assert parse_whm_title("Cyprus, Assyrian Vassal, 709 - 612BCE,.") == T(
        name="Cyprus, Assyrian Vassal", span="709 - 612BCE"
    )


def test_dynasty_only():
    assert parse_whm_title("Ghazni, 977 - 1186, Ghaznevid Dynasty 977 - 1186.") == T(
        name="Ghazni", span="977 - 1186", dynasty="Ghaznevid Dynasty 977 - 1186"
    )


def test_leader_and_dynasty_split_across_commas():
    # Standard format: leader personal name in one part, title+date in next part
    assert parse_whm_title(
        "Egypt, 972 - 1169, Al-Mustali Biallah, Emir 1094 - 1102, Fatimid Dynasty 969 - 1171"
    ) == T(
        name="Egypt",
        span="972 - 1169",
        leader="Al-Mustali Biallah, Emir 1094 - 1102",
        dynasty="Fatimid Dynasty 969 - 1171",
    )


def test_full_title_with_qualifier():
    # Both a name qualifier and full leader+dynasty
    assert parse_whm_title(
        "Egypt, Old Kingdom, 2925 - c2150BCE + -50 years, "
        "Snefru, Pharaoh c2575 - c2551BCE, "
        "Fourth Dynasty of Egypt c2575 - c2465BCE."
    ) == T(
        name="Egypt, Old Kingdom",
        span="2925 - c2150BCE + -50 years",
        leader="Snefru, Pharaoh c2575 - c2551BCE",
        dynasty="Fourth Dynasty of Egypt c2575 - c2465BCE",
    )


def test_fused_leader_name_and_title():
    # Leader name and title are in a single comma-part (no comma between them)
    assert parse_whm_title(
        "Calukyas, 973 - 1200, Tailapa Ahavamalla King 973 - 997, Calukya Dynasty 973 - 1200."
    ) == T(
        name="Calukyas",
        span="973 - 1200",
        leader="Tailapa Ahavamalla King 973 - 997",
        dynasty="Calukya Dynasty 973 - 1200",
    )


def test_leader_with_parenthetical():
    # Parenthetical in both the leader name and the title clause
    assert parse_whm_title(
        "Babylonia, c1590BCE - 1225, Nabu-kudurri-usur (Nebuchadnezzar I), King c1126 - c1103BCE."
    ) == T(
        name="Babylonia",
        span="c1590BCE - 1225",
        leader="Nabu-kudurri-usur (Nebuchadnezzar I), King c1126 - c1103BCE",
    )


def test_leader_title_with_parenthetical_caliph():
    # "Emir (Caliph 929)" — parenthetical title keyword inside the leader clause
    assert parse_whm_title(
        "Cordoba, 756 - 1070, Abd-ar-Rahman III, Emir (Caliph 929) 912 - 961, Ummayad Dynasty 756 - 1031."
    ) == T(
        name="Cordoba",
        span="756 - 1070",
        leader="Abd-ar-Rahman III, Emir (Caliph 929) 912 - 961",
        dynasty="Ummayad Dynasty 756 - 1031",
    )


def test_family_keyword_as_dynasty_without_span():
    # "Satomi Family 1467 - 1590" — no explicit span; "Family" triggers dynasty
    assert parse_whm_title("Awa, Satomi Family 1467 - 1590.") == T(
        name="Awa", dynasty="Satomi Family 1467 - 1590"
    )


def test_note_before_leader():
    # Lifestyle description before the leader should go to note; leader is still extracted
    assert parse_whm_title(
        "Huns, c300 - c453, nomadic herders, Rugila, King 432 - 437"
    ) == T(
        name="Huns",
        span="c300 - c453",
        leader="Rugila, King 432 - 437",
        note="nomadic herders",
    )


def test_gained_lost_format():
    # Non-standard "gained/lost" colonial entries: date-range parts go to note
    assert parse_whm_title(
        "Central Africa, French Colonies, gained 1626-1914, lost 1958-1962"
    ) == T(
        name="Central Africa, French Colonies",
        note="gained 1626-1914, lost 1958-1962",
    )


def test_free_text_goes_to_note():
    assert parse_whm_title(
        "Virginia, British Colony, 1607 - 1683, shown as part of America after 1683."
    ) == T(
        name="Virginia, British Colony",
        span="1607 - 1683",
        note="shown as part of America after 1683",
    )


def test_trailing_comma_dot_stripped():
    # Trailing ",." artifacts from the WHM source data are stripped cleanly
    result = parse_whm_title("Chu, c1100 - 223BCE,.")
    assert result.name == "Chu"
    assert result.span == "c1100 - 223BCE"
    assert result.leader is None
    assert result.dynasty is None


def test_bce_span():
    assert parse_whm_title("Argos, c1600 - 1200BCE.") == T(
        name="Argos", span="c1600 - 1200BCE"
    )


def test_present_span():
    assert parse_whm_title("Denmark, 935 - Present.") == T(
        name="Denmark", span="935 - Present"
    )


# ── extract_base_name ──────────────────────────────────────────────────────────


def test_extract_base_name_simple():
    assert extract_base_name("Egypt, Old Kingdom, 2925 - c2150BCE") == "Egypt"


def test_extract_base_name_no_comma():
    assert extract_base_name("Uruk") == "Uruk"


def test_extract_base_name_with_span():
    assert extract_base_name("Uruk, c2900 - 2335BCE.") == "Uruk"
