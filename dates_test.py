import pytest

from chrono_stats import edtf_interval
from dates import (
    NEG_INF,
    POS_INF,
    duration_years,
    overlaps,
    parse_ohm_date,
    parse_ohm_range,
    start_of_date,
)


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

    def test_rejects_uncertainty_markers(self):
        assert parse_ohm_date("c. 1900") is None
        assert parse_ohm_date("ca. 1900") is None
        assert parse_ohm_date("~ 1900") is None

    def test_rejects_trailing_junk(self):
        assert parse_ohm_date("1900?") is None
        assert parse_ohm_date("1900 (est.)") is None

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

    def test_invalid_datelike(self):
        assert parse_ohm_date("600 BC") is None
        assert parse_ohm_date("1975..1985") is None
        assert parse_ohm_date("1984-02..2009") is None


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


class TestEdtfInterval:
    def test_exact_day(self):
        assert edtf_interval("1948-05-08") == ((1948, 5, 8), (1948, 5, 8))

    def test_year_month(self):
        assert edtf_interval("1948-05") == ((1948, 5, 1), (1948, 5, 31))

    def test_year_only(self):
        assert edtf_interval("1948") == ((1948, 1, 1), (1948, 12, 31))

    def test_approximate_year(self):
        # 1948~ is uncertain/approximate but still bounded to that year
        lo, hi = edtf_interval("1948~")
        assert lo == (1948, 1, 1)
        assert hi == (1948, 12, 31)

    def test_interval(self):
        assert edtf_interval("1944/1950") == ((1944, 1, 1), (1950, 12, 31))

    def test_open_ended_upper(self):
        lo, hi = edtf_interval("1948/..")
        assert lo == (1948, 1, 1)
        assert hi == (10**12, 1, 1)

    def test_invalid_returns_none(self):
        # Strings that are not valid EDTF at all
        assert edtf_interval("not a date") is None
        assert edtf_interval("unknown") is None

    def test_invalid_ohm_style_qualifiers(self):
        # OHM plain-date qualifiers are not valid EDTF
        assert edtf_interval("c. 1900") is None
        assert edtf_interval("ca. 1900") is None
        assert edtf_interval("1900 (est.)") is None
        assert edtf_interval("600 BC") is None

    def test_invalid_ohm_range_in_edtf_field(self):
        # OHM date ranges written with a dash are not valid EDTF
        assert edtf_interval("1900-1910") is None

    def test_unspecified_month_day_digits(self):
        # Partially-unspecified dates with X in month/day parse successfully
        # but lower_strict()/upper_strict() raise ValueError inside the library.
        # edtf_interval must catch this and return None.
        assert edtf_interval("1X00-1X-1X") is None

    def test_mismatch_day_off_by_one(self):
        """The motivating example from the issue: end_date=1948-05-08, end_date:edtf=1948-05-09."""
        plain = (1948, 5, 8)
        lo, hi = edtf_interval("1948-05-09")
        assert not (lo <= plain <= hi)

    def test_match_day_within_month(self):
        """A day-level plain date is within a month-level EDTF interval."""
        plain = (1948, 5, 8)
        lo, hi = edtf_interval("1948-05")
        assert lo <= plain <= hi

    def test_match_day_within_year(self):
        """A day-level plain date is within a year-level EDTF interval."""
        plain = (1948, 5, 8)
        lo, hi = edtf_interval("1948")
        assert lo <= plain <= hi

    def test_mismatch_wrong_year(self):
        plain = (1949, 1, 1)
        lo, hi = edtf_interval("1948")
        assert not (lo <= plain <= hi)
