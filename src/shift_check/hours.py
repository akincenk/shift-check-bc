"""Daily and weekly hours, overtime split and gross pay under ss. 35 and 40."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from . import esa
from .schedule import Shift


def week_start(day: date) -> date:
    """The Sunday that starts the overtime week containing ``day`` (s. 1, "week" (a))."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


@dataclass
class Week:
    employee: str
    start: date  # a Sunday
    minutes: int = 0
    regular: int = 0
    time_and_half: int = 0  # daily over 8 up to 12, plus weekly over 40
    double: int = 0  # daily over 12
    daily_ot: int = 0  # part of time_and_half that comes from the daily rule
    weekly_ot: int = 0  # part of time_and_half that comes from the weekly rule
    pay: Decimal | None = None


def daily_minutes(shifts: list[Shift]) -> dict[tuple[str, date], int]:
    totals: dict[tuple[str, date], int] = defaultdict(int)
    for shift in shifts:
        totals[(shift.employee, shift.day)] += shift.minutes
    return dict(totals)


def weeks(shifts: list[Shift], wages: dict[str, str] | None = None) -> list[Week]:
    """One summary per employee and overtime week, in employee and date order."""
    result: dict[tuple[str, date], Week] = {}
    counted: dict[tuple[str, date], int] = defaultdict(int)
    for (employee, day), minutes in sorted(daily_minutes(shifts).items()):
        key = (employee, week_start(day))
        week = result.setdefault(key, Week(employee, key[1]))
        week.minutes += minutes
        week.daily_ot += min(max(minutes - esa.DAILY_OT_MIN, 0), esa.DAILY_DOUBLE_MIN - esa.DAILY_OT_MIN)
        week.double += max(minutes - esa.DAILY_DOUBLE_MIN, 0)
        counted[key] += min(minutes, esa.WEEKLY_COUNTED_PER_DAY_MIN)
    for key, week in result.items():
        week.weekly_ot = max(counted[key] - esa.WEEKLY_OT_MIN, 0)
        week.time_and_half = week.daily_ot + week.weekly_ot
        week.regular = week.minutes - week.time_and_half - week.double
        if wages and week.employee in wages:
            week.pay = gross_pay(week, Decimal(wages[week.employee]))
    return [result[k] for k in sorted(result)]


def gross_pay(week: Week, wage: Decimal) -> Decimal:
    hours = (Decimal(week.regular) + Decimal(week.time_and_half) * Decimal("1.5") + Decimal(week.double) * 2) / Decimal(
        60
    )
    return (hours * wage).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def hm(minutes: int) -> str:
    """Minutes as ``7 h 30 min``."""
    h, m = divmod(minutes, 60)
    return f"{h} h {m:02d} min" if m else f"{h} h"
