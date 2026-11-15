from datetime import date, timedelta
from decimal import Decimal

import pytest

from shift_check import make_shift, week_start, weeks
from shift_check.esa import minimum_wage
from shift_check.hours import hm

MONDAY = date(2026, 11, 16)


def days(n, start="09:00", end="17:00", first=MONDAY):
    return [make_shift("E1", str(first + timedelta(days=i)), start, end) for i in range(n)]


def test_week_starts_on_sunday():
    assert week_start(date(2026, 11, 15)) == date(2026, 11, 15)  # a Sunday
    assert week_start(date(2026, 11, 21)) == date(2026, 11, 15)  # Saturday
    assert week_start(date(2026, 11, 22)) == date(2026, 11, 22)


def test_daily_overtime_and_double_time():
    [w] = weeks([make_shift("E1", "2026-11-16", "06:00", "19:30")])  # 13.5 h
    assert (w.regular, w.time_and_half, w.double) == (480, 240, 90)


def test_weekly_overtime_after_40_hours():
    [w] = weeks(days(6))  # six 8-hour days
    assert (w.minutes, w.regular, w.weekly_ot, w.daily_ot) == (2880, 2400, 480, 0)


def test_only_first_8_hours_a_day_count_towards_40():
    # s. 40(3): four 12-hour days are 48 hours, but only 32 count towards the weekly 40.
    [w] = weeks(days(4, "06:00", "18:00"))
    assert (w.daily_ot, w.weekly_ot, w.regular) == (4 * 240, 0, 4 * 480)


def test_mixed_daily_and_weekly():
    shifts = days(5) + [make_shift("E1", "2026-11-21", "08:00", "18:00")]  # 5 x 8 h + 10 h on Saturday
    [w] = weeks(shifts)
    # 50 h in total: 2 h daily overtime on Saturday, 48 counted hours give 8 h weekly overtime
    assert (w.daily_ot, w.weekly_ot, w.regular) == (120, 480, 3000 - 120 - 480)


def test_gross_pay():
    [w] = weeks([make_shift("E1", "2026-11-16", "06:00", "19:30")], {"E1": "20.00"})
    # 8 h x 20 + 4 h x 30 + 1.5 h x 40
    assert w.pay == Decimal("340.00")


def test_weeks_split_by_sunday_and_employee():
    saturday_and_sunday = days(2, first=date(2026, 11, 21))
    shifts = saturday_and_sunday + [make_shift("E2", "2026-11-16", "09:00", "10:00")]
    assert [(w.employee, str(w.start)) for w in weeks(shifts)] == [
        ("E1", "2026-11-15"),
        ("E1", "2026-11-22"),
        ("E2", "2026-11-15"),
    ]


@pytest.mark.parametrize(
    "day,rate", [(date(2025, 5, 31), None), (date(2025, 6, 1), "17.85"), (date(2026, 6, 1), "18.25")]
)
def test_minimum_wage_table(day, rate):
    assert minimum_wage(day) == (None if rate is None else Decimal(rate))


def test_hm():
    assert hm(90) == "1 h 30 min" and hm(120) == "2 h"
