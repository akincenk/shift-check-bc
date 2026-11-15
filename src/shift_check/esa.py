"""Numbers from the BC Employment Standards Act, Part 4 (hours of work and overtime).

Source: Employment Standards Act, RSBC 1996, c. 113, ss. 1, 32-36 and 40, on bclaws.gov.bc.ca.
Minimum wage: BC government news releases 2025LBR0017-000500 and 2026LBR0021-000581.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

MEAL_BREAK_AFTER_MIN = 5 * 60  # s. 32(1)(a): no more than 5 consecutive hours without a meal break
MEAL_BREAK_MIN = 30  # s. 32(1)(b): a meal break lasts at least half an hour
SPLIT_SHIFT_SPAN_MIN = 12 * 60  # s. 33: a split shift is completed within 12 hours of starting work
MIN_DAILY_PAY_MIN = 2 * 60  # s. 34(1): at least 2 hours' pay when an employee reports for work
WEEKLY_REST_MIN = 32 * 60  # s. 36(1): 32 consecutive hours free from work each week
REST_BETWEEN_SHIFTS_MIN = 8 * 60  # s. 36(2): 8 consecutive hours free between shifts
DAILY_OT_MIN = 8 * 60  # s. 40(1)(a): time and a half over 8 hours a day
DAILY_DOUBLE_MIN = 12 * 60  # s. 40(1)(b): double time over 12 hours a day
WEEKLY_OT_MIN = 40 * 60  # s. 40(2): time and a half over 40 hours a week
WEEKLY_COUNTED_PER_DAY_MIN = 8 * 60  # s. 40(3): only the first 8 hours of each day count towards the 40

# General minimum wage per hour, by the date it took effect. Add new rates at the end.
MINIMUM_WAGE: list[tuple[date, Decimal]] = [
    (date(2025, 6, 1), Decimal("17.85")),
    (date(2026, 6, 1), Decimal("18.25")),
]


def minimum_wage(on: date) -> Decimal | None:
    """The general minimum wage on a date, or None if the date is before the first known rate."""
    rate = None
    for start, value in MINIMUM_WAGE:
        if on >= start:
            rate = value
    return rate
