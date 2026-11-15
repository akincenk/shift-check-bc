"""Rule checks for a schedule. Each finding names the section of the Act it comes from.

Two kinds of finding:

- ``violation``: the schedule breaks a rule and should be changed (meal breaks, split shifts,
  rest between shifts, minimum wage).
- ``pay``: the schedule is allowed but costs extra or has a pay floor (missing weekly rest is paid
  at time and a half, a short shift is paid at least 2 hours).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from . import esa
from .hours import hm, week_start
from .schedule import Shift, minutes_between


@dataclass(frozen=True)
class Finding:
    kind: str  # violation or pay
    rule: str  # short code, e.g. meal-break
    section: str  # e.g. "s. 32"
    employee: str
    day: date
    message: str


def _groups(shifts: list[Shift]) -> list[list[Shift]]:
    """Split shifts: parts on the same day with less than 8 hours between them form one group.

    The Act does not define a split shift. Here a gap of 8 hours or more makes two separate shifts,
    because s. 36(2) is then met; a shorter gap on the same day makes the parts one split shift.
    """
    groups: list[list[Shift]] = []
    for shift in sorted(shifts, key=lambda s: (s.employee, s.start)):
        prev = groups[-1][-1] if groups else None
        if (
            prev is not None
            and prev.employee == shift.employee
            and prev.day == shift.day
            and minutes_between(prev.end, shift.start) < esa.REST_BETWEEN_SHIFTS_MIN
        ):
            groups[-1].append(shift)
        else:
            groups.append([shift])
    return groups


def meal_breaks(shifts: list[Shift]) -> list[Finding]:
    """s. 32: no more than 5 consecutive hours without a meal break of at least 30 minutes.

    Breaks shorter than 30 minutes are not meal breaks and do not restart the count.
    """
    out = []
    for shift in shifts:
        meals = [b for b in shift.breaks if minutes_between(*b) >= esa.MEAL_BREAK_MIN]
        edges = [shift.start, *[x for b in meals for x in b], shift.end]
        stretches = [minutes_between(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
        longest = max(stretches)
        if longest > esa.MEAL_BREAK_AFTER_MIN:
            out.append(
                Finding(
                    "violation",
                    "meal-break",
                    "s. 32",
                    shift.employee,
                    shift.day,
                    f"{shift.start:%H:%M}-{shift.end:%H:%M}: {hm(longest)} without a meal break "
                    f"of at least {esa.MEAL_BREAK_MIN} min (limit 5 h)",
                )
            )
    return out


def split_shifts(shifts: list[Shift]) -> list[Finding]:
    """s. 33: a split shift must be completed within 12 hours of starting work."""
    out = []
    for group in _groups(shifts):
        if len(group) < 2:
            continue
        span = minutes_between(group[0].start, group[-1].end)
        if span > esa.SPLIT_SHIFT_SPAN_MIN:
            out.append(
                Finding(
                    "violation",
                    "split-shift",
                    "s. 33",
                    group[0].employee,
                    group[0].day,
                    f"split shift {group[0].start:%H:%M} to {group[-1].end:%H:%M} spans {hm(span)} (limit 12 h)",
                )
            )
    return out


def rest_between_shifts(shifts: list[Shift]) -> list[Finding]:
    """s. 36(2): at least 8 consecutive hours free between shifts (not applied in an emergency)."""
    out = []
    groups = _groups(shifts)
    for a, b in zip(groups, groups[1:], strict=False):
        if a[0].employee != b[0].employee:
            continue
        gap = minutes_between(a[-1].end, b[0].start)
        if gap < esa.REST_BETWEEN_SHIFTS_MIN:
            out.append(
                Finding(
                    "violation",
                    "rest-between-shifts",
                    "s. 36(2)",
                    b[0].employee,
                    b[0].day,
                    f"only {hm(gap)} free between {a[-1].end:%a %H:%M} and {b[0].start:%a %H:%M} (needs 8 h)",
                )
            )
    return out


def weekly_rest(shifts: list[Shift]) -> list[Finding]:
    """s. 36(1): 32 consecutive hours free each week, or time and a half for work in that period.

    Weeks are the Sunday-to-Saturday overtime weeks. Time outside the schedule counts as free.
    """
    by_week: dict[tuple[str, date], list[Shift]] = defaultdict(list)
    for shift in shifts:
        by_week[(shift.employee, week_start(shift.day))].append(shift)
    out = []
    for (employee, start), items in sorted(by_week.items()):
        w_start = datetime.combine(start, datetime.min.time())
        w_end = w_start + timedelta(days=7)
        cursor, longest = w_start, 0
        for shift in sorted(items, key=lambda s: s.start):
            longest = max(longest, minutes_between(cursor, max(cursor, shift.start)))
            cursor = max(cursor, shift.end)
        longest = max(longest, minutes_between(cursor, w_end) if cursor < w_end else 0)
        if longest < esa.WEEKLY_REST_MIN:
            out.append(
                Finding(
                    "pay",
                    "weekly-rest",
                    "s. 36(1)",
                    employee,
                    start,
                    f"week of {start}: longest time off is {hm(longest)}, not 32 h; "
                    "work in the missing rest period is paid at time and a half",
                )
            )
    return out


def minimum_daily_pay(shifts: list[Shift]) -> list[Finding]:
    """s. 34(1): an employee who reports for work is paid for at least 2 hours."""
    out = []
    for group in _groups(shifts):
        minutes = sum(s.minutes for s in group)
        if minutes < esa.MIN_DAILY_PAY_MIN:
            out.append(
                Finding(
                    "pay",
                    "minimum-daily-pay",
                    "s. 34",
                    group[0].employee,
                    group[0].day,
                    f"scheduled for {hm(minutes)}; must be paid for at least 2 h",
                )
            )
    return out


def minimum_wage(shifts: list[Shift], wages: dict[str, str]) -> list[Finding]:
    """s. 16: the hourly wage is at least the general minimum wage on the day worked."""
    out = []
    seen: set[tuple[str, Decimal]] = set()
    for shift in shifts:
        if shift.employee not in wages:
            continue
        wage = Decimal(wages[shift.employee])
        floor = esa.minimum_wage(shift.day)
        if floor is not None and wage < floor and (shift.employee, floor) not in seen:
            seen.add((shift.employee, floor))
            out.append(
                Finding(
                    "violation",
                    "minimum-wage",
                    "s. 16",
                    shift.employee,
                    shift.day,
                    f"hourly wage {wage} is below the minimum wage of {floor} in effect on {shift.day}",
                )
            )
    return out


def check(shifts: list[Shift], wages: dict[str, str] | None = None) -> list[Finding]:
    """Run every check and return the findings sorted by employee and day."""
    findings = [
        *meal_breaks(shifts),
        *split_shifts(shifts),
        *rest_between_shifts(shifts),
        *weekly_rest(shifts),
        *minimum_daily_pay(shifts),
        *(minimum_wage(shifts, wages) if wages else []),
    ]
    return sorted(findings, key=lambda f: (f.employee, f.day, f.rule))
