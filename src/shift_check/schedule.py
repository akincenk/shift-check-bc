"""Reading a staff schedule from CSV.

Times are local wall-clock times. A shift whose end time is not after its start time ends the next
day, so ``22:00`` to ``06:00`` is an eight-hour night shift.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

MAX_ERRORS_SHOWN = 10
_TIME = re.compile(r"(\d{1,2}):(\d{2})")


class ScheduleError(ValueError):
    """The schedule cannot be used. ``errors`` holds one message per problem."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        shown = errors[:MAX_ERRORS_SHOWN]
        more = len(errors) - len(shown)
        super().__init__("\n".join(shown) + (f"\n... and {more} more" if more else ""))


Interval = tuple[datetime, datetime]


@dataclass(frozen=True)
class Shift:
    employee: str
    start: datetime
    end: datetime
    breaks: tuple[Interval, ...] = ()  # unpaid breaks, inside the shift, in order
    line: int = 0

    @property
    def day(self) -> date:
        """The day the shift counts towards. A shift over midnight belongs to the day it starts."""
        return self.start.date()

    def work(self) -> list[Interval]:
        """The shift with its breaks cut out."""
        out: list[Interval] = []
        cursor = self.start
        for b_start, b_end in self.breaks:
            if b_start > cursor:
                out.append((cursor, b_start))
            cursor = b_end
        if self.end > cursor:
            out.append((cursor, self.end))
        return out

    @property
    def minutes(self) -> int:
        return sum(minutes_between(a, b) for a, b in self.work())


def minutes_between(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)


def parse_time(text: str) -> time:
    match = _TIME.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"time {text!r} is not HH:MM")
    hour, minute = int(match[1]), int(match[2])
    if hour > 23 or minute > 59:
        raise ValueError(f"time {text!r} is out of range")
    return time(hour, minute)


def make_shift(employee: str, day: str, start: str, end: str, breaks: str = "", line: int = 0) -> Shift:
    """Build a shift from text fields, as they appear in the CSV. Raises ValueError with a readable message."""
    try:
        d = date.fromisoformat(day.strip())
    except ValueError:
        raise ValueError(f"date {day!r} is not YYYY-MM-DD") from None
    s = datetime.combine(d, parse_time(start))
    e = datetime.combine(d, parse_time(end))
    if e == s:
        raise ValueError("start and end are the same time")
    if e < s:
        e += timedelta(days=1)
    parsed: list[Interval] = []
    for part in filter(None, (p.strip() for p in breaks.split(";"))):
        if part.count("-") != 1:
            raise ValueError(f"break {part!r} is not HH:MM-HH:MM")
        a_text, b_text = part.split("-")
        a = datetime.combine(d, parse_time(a_text))
        if a < s:
            a += timedelta(days=1)
        b = datetime.combine(a.date(), parse_time(b_text))
        if b <= a:
            b += timedelta(days=1)
        if not (s < a and b < e):
            raise ValueError(f"break {part} is not inside the shift")
        if parsed and a < parsed[-1][1]:
            raise ValueError(f"break {part} overlaps or comes before the previous break")
        parsed.append((a, b))
    return Shift(employee.strip(), s, e, tuple(parsed), line)


def load_schedule(path: str | Path) -> list[Shift]:
    """Read shifts from a CSV with columns employee, date, start, end and optional breaks."""
    shifts: list[Shift] = []
    errors: list[str] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ScheduleError([f"{path}: file is empty"])
        names = [n.strip().lower() for n in reader.fieldnames]
        missing = [c for c in ("employee", "date", "start", "end") if c not in names]
        if missing:
            raise ScheduleError([f"{path}: missing column(s) {', '.join(missing)}"])
        reader.fieldnames = names
        for row in reader:
            num = reader.line_num
            row = {k: (v or "").strip() for k, v in row.items() if k}
            if not row["employee"]:
                errors.append(f"line {num}: empty employee")
                continue
            try:
                shifts.append(
                    make_shift(row["employee"], row["date"], row["start"], row["end"], row.get("breaks", ""), num)
                )
            except ValueError as exc:
                errors.append(f"line {num}: {exc}")
    errors.extend(_overlaps(shifts))
    if errors:
        raise ScheduleError(errors)
    if not shifts:
        raise ScheduleError([f"{path}: no shifts"])
    return sorted(shifts, key=lambda s: (s.employee, s.start))


def _overlaps(shifts: list[Shift]) -> list[str]:
    errors = []
    ordered = sorted(shifts, key=lambda s: (s.employee, s.start))
    for a, b in zip(ordered, ordered[1:], strict=False):
        if a.employee == b.employee and b.start < a.end:
            errors.append(f"line {b.line}: overlaps the shift on line {a.line} for {a.employee}")
    return errors


def load_wages(path: str | Path) -> dict[str, str]:
    """Read hourly wages (employee, hourly_wage). Values stay text; the caller converts to Decimal."""
    wages: dict[str, str] = {}
    errors: list[str] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        names = [n.strip().lower() for n in reader.fieldnames or []]
        if "employee" not in names or "hourly_wage" not in names:
            raise ScheduleError([f"{path}: needs columns employee and hourly_wage"])
        reader.fieldnames = names
        for row in reader:
            employee, wage = (row.get("employee") or "").strip(), (row.get("hourly_wage") or "").strip()
            if not re.fullmatch(r"\d+(\.\d{1,2})?", wage):
                errors.append(f"{path} line {reader.line_num}: hourly_wage {wage!r} is not an amount like 19.50")
            elif employee in wages:
                errors.append(f"{path} line {reader.line_num}: {employee} is listed twice")
            else:
                wages[employee] = wage
    if errors:
        raise ScheduleError(errors)
    return wages
