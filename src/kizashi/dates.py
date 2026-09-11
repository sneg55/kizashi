import calendar
from datetime import date

MONTHS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], start=1)}


def last_day_of_month(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def parse_mm_dd_yyyy(s: str) -> date | None:
    s = s.strip()
    if not s:
        return None
    m, d, y = s.split("-")
    return date(int(y), int(m), int(d))


def parse_yyyymm(s: str) -> date | None:
    s = s.strip()
    if len(s) != 6 or not s.isdigit():
        return None
    return last_day_of_month(int(s[:4]), int(s[4:]))


def parse_dd_mon_yyyy(s: str) -> date | None:
    s = s.strip()
    if not s:
        return None
    d, mon, y = s.split("-")
    return date(int(y), MONTHS[mon.upper()], int(d))


def add_years(d: date, n: int) -> date:
    year = d.year + n
    day = min(d.day, calendar.monthrange(year, d.month)[1])
    return date(year, d.month, day)


def due_date(period_end: date) -> date:
    month = period_end.month + 5
    year = period_end.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, 15)


def period_ends_after(last_end: date, n: int) -> list[date]:
    return [add_years(last_end, k) for k in range(1, n + 1)]
