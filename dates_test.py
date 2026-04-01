import pytest

from dates import (
    NEG_INF,
    POS_INF,
    duration_years,
    normalize_ohm_date,
    overlaps,
    parse_ohm_date,
    parse_ohm_range,
    start_of_date,
)


class TestNormalizeOhmDate:
    def test_removes_uncertainty_prefixes(self):
        assert normalize_ohm_date("c. 1900") == "1900"
        assert normalize_ohm_date("ca. 1900") == "1900"
        assert normalize_ohm_date("~ 1900") == "1900"

    def test_removes_trailing_junk(self):
        assert normalize_ohm_date("1900?") == "1900"
        assert normalize_ohm_date("1900 (est.)") == "1900"

    def test_rejects_embedded_ranges(self):
        assert normalize_ohm_date("1900-1910") is None
        assert normalize_ohm_date("2000-2010") is None

    def test_handles_none_and_empty(self):
        assert normalize_ohm_date(None) is None
        assert normalize_ohm_date("") is None
        assert normalize_ohm_date("   ") is None

    def test_strips_and_lowercases(self):
        assert normalize_ohm_date("  1900  ") == "1900"
        assert normalize_ohm_date("C. 1900") == "1900"


class TestParseOhmDate:
    def test_year_only(self):
        assert parse_ohm_date("2026") == (2026, None, None)
        assert parse_ohm_date("1900") == (1900, None, None)

    def test_year_month(self):
        assert parse_ohm_date("2026-1") == (2026, 1, None)
        assert parse_ohm_date("2026-12") == (2026, 12, None)

    def test_year_month_day(self):
        assert parse_ohm_date("2026-01-01") == (2026, 1, 1)
        assert parse_ohm_date("2026-12-31") == (2026, 12, 31)

    def test_negative_years(self):
        assert parse_ohm_date("-1234") == (-1234, None, None)
        assert parse_ohm_date("-1234-5-6") == (-1234, 5, 6)

    def test_with_uncertainty_markers(self):
        assert parse_ohm_date("c. 1900") == (1900, None, None)
        assert parse_ohm_date("ca. 1900") == (1900, None, None)
        assert parse_ohm_date("~ 1900") == (1900, None, None)

    def test_with_trailing_junk(self):
        assert parse_ohm_date("1900?") == (1900, None, None)
        assert parse_ohm_date("1900 (est.)") == (1900, None, None)

    def test_invalid_month(self):
        assert parse_ohm_date("2026-13") is None
        assert parse_ohm_date("2026-0") is None

    def test_invalid_day(self):
        assert parse_ohm_date("2026-01-32") is None
        assert parse_ohm_date("2026-01-0") is None

    def test_embedded_ranges_rejected(self):
        assert parse_ohm_date("1900-1910") is None
        assert parse_ohm_date("2000-2010") is None

    def test_none_and_empty(self):
        assert parse_ohm_date(None) is None
        assert parse_ohm_date("") is None
        assert parse_ohm_date("   ") is None

    def test_invalid_format(self):
        assert parse_ohm_date("not a date") is None
        assert parse_ohm_date("abc-def-ghi") is None


class TestStartOfDate:
    def test_year_only(self):
        assert start_of_date((2026, None, None)) == (2026, 1, 1)

    def test_year_month(self):
        assert start_of_date((2026, 5, None)) == (2026, 5, 1)

    def test_year_month_day(self):
        assert start_of_date((2026, 5, 15)) == (2026, 5, 15)

    def test_negative_year(self):
        assert start_of_date((-1234, None, None)) == (-1234, 1, 1)


class TestParseOhmRange:
    def test_both_dates_specified(self):
        result = parse_ohm_range("1991", "2000")
        assert result == ((1991, 1, 1), (2000, 1, 1))

    def test_open_ended_range(self):
        result = parse_ohm_range("2000", None)
        assert result == ((2000, 1, 1), POS_INF)

    def test_start_unbounded(self):
        result = parse_ohm_range(None, "2000")
        assert result == (NEG_INF, (2000, 1, 1))

    def test_both_unbounded(self):
        result = parse_ohm_range(None, None)
        assert result == (NEG_INF, POS_INF)

    def test_partial_dates(self):
        result = parse_ohm_range("2000-05", "2001")
        assert result == ((2000, 5, 1), (2001, 1, 1))

    def test_negative_years(self):
        result = parse_ohm_range("-1234", "-1200")
        assert result == ((-1234, 1, 1), (-1200, 1, 1))

    def test_messy_input(self):
        result = parse_ohm_range("c. 1900?", "1910 (est.)")
        assert result == ((1900, 1, 1), (1910, 1, 1))


class TestDurationYears:
    def test_whole_years(self):
        r = parse_ohm_range("2021", "2026")
        assert duration_years(r) == 5.0

    def test_months_only(self):
        # 2020-01 to 2020-10 is 9 months = 0.75 years
        r = parse_ohm_range("2020-01", "2020-10")
        assert duration_years(r) == pytest.approx(0.75)

    def test_cross_year_months(self):
        # 2019-07 to 2020-01 is 6 months = 0.5 years
        r = parse_ohm_range("2019-07", "2020-01")
        assert duration_years(r) == pytest.approx(0.5)

    def test_single_year(self):
        r = parse_ohm_range("2000", "2001")
        assert duration_years(r) == pytest.approx(1.0)

    def test_open_end_is_inf(self):
        r = parse_ohm_range("2000", None)
        assert duration_years(r) == float("inf")

    def test_open_start_is_inf(self):
        r = parse_ohm_range(None, "2000")
        assert duration_years(r) == float("inf")

    def test_both_open_is_inf(self):
        r = parse_ohm_range(None, None)
        assert duration_years(r) == float("inf")

    def test_century(self):
        r = parse_ohm_range("1900", "2000")
        assert duration_years(r) == pytest.approx(100.0)


class TestOverlaps:
    def test_no_overlap_consecutive_years(self):
        """1991-2000 and 2000-inf should not overlap"""
        A = parse_ohm_range("1991", "2000")
        B = parse_ohm_range("2000", None)
        assert not overlaps(A, B)

    def test_overlap_partial_dates(self):
        """2000-05 to 2001 and 2000 to 2000-06 should overlap"""
        C = parse_ohm_range("2000-05", "2001")
        D = parse_ohm_range("2000", "2000-06")
        assert overlaps(C, D)

    def test_no_overlap_negative_years(self):
        """-1234 to -1200 and -1200 to inf should not overlap"""
        E = parse_ohm_range("-1234", "-1200")
        F = parse_ohm_range("-1200", None)
        assert not overlaps(E, F)

    def test_overlap_messy_input(self):
        """c. 1900 to 1910 (est.) and 1905 to inf should overlap"""
        G = parse_ohm_range("c. 1900?", "1910 (est.)")
        H = parse_ohm_range("1905", None)
        assert overlaps(G, H)

    def test_complete_overlap(self):
        """One range completely contains another"""
        A = parse_ohm_range("1900", "2000")
        B = parse_ohm_range("1950", "1960")
        assert overlaps(A, B)
        assert overlaps(B, A)

    def test_no_overlap_separated_ranges(self):
        """Ranges are clearly separated"""
        A = parse_ohm_range("1900", "1950")
        B = parse_ohm_range("2000", "2050")
        assert not overlaps(A, B)
        assert not overlaps(B, A)

    def test_overlap_with_unbounded_ranges(self):
        """Any bounded range overlaps with (-inf, +inf)"""
        A = parse_ohm_range("1900", "2000")
        B = parse_ohm_range(None, None)
        assert overlaps(A, B)
        assert overlaps(B, A)

    def test_partial_overlap(self):
        """Ranges partially overlap"""
        A = parse_ohm_range("1900", "1950")
        B = parse_ohm_range("1925", "1975")
        assert overlaps(A, B)
        assert overlaps(B, A)
