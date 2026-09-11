from datetime import date

from kizashi.dates import (
    add_years,
    due_date,
    last_day_of_month,
    parse_dd_mon_yyyy,
    parse_mm_dd_yyyy,
    parse_yyyymm,
    period_ends_after,
)


def test_due_date_calendar_year():
    assert due_date(date(2023, 12, 31)) == date(2024, 5, 15)


def test_due_date_fiscal_june():
    assert due_date(date(2024, 6, 30)) == date(2024, 11, 15)


def test_due_date_wraps_year():
    assert due_date(date(2024, 9, 30)) == date(2025, 2, 15)


def test_third_missed_due_matches_irs_rule():
    ends = period_ends_after(date(2023, 12, 31), 3)
    assert ends == [date(2024, 12, 31), date(2025, 12, 31), date(2026, 12, 31)]
    assert due_date(ends[2]) == date(2027, 5, 15)


def test_add_years_clamps_leap_day():
    assert add_years(date(2024, 2, 29), 1) == date(2025, 2, 28)


def test_parsers():
    assert parse_mm_dd_yyyy("12-31-2023") == date(2023, 12, 31)
    assert parse_mm_dd_yyyy("") is None
    assert parse_yyyymm("202406") == date(2024, 6, 30)
    assert parse_yyyymm("") is None
    assert parse_yyyymm("000000") is None
    assert parse_dd_mon_yyyy("15-MAY-2023") == date(2023, 5, 15)
    assert last_day_of_month(2024, 2) == date(2024, 2, 29)
