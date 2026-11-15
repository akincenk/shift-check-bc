from datetime import datetime

import pytest

from shift_check import ScheduleError, load_schedule, load_wages, make_shift


def test_day_shift_with_breaks():
    s = make_shift("E1", "2026-11-16", "09:00", "17:30", "12:00-12:30; 15:00-15:15")
    assert s.minutes == 8 * 60 + 30 - 45
    assert len(s.work()) == 3


def test_night_shift_ends_next_day_and_belongs_to_start_day():
    s = make_shift("E1", "2026-11-16", "22:00", "06:00", "01:30-02:00")
    assert s.end == datetime(2026, 11, 17, 6, 0)
    assert s.breaks[0][0] == datetime(2026, 11, 17, 1, 30)
    assert s.day.isoformat() == "2026-11-16" and s.minutes == 450


@pytest.mark.parametrize(
    "args,message",
    [
        (("2026-13-01", "09:00", "10:00"), "not YYYY-MM-DD"),
        (("2026-11-16", "9am", "10:00"), "not HH:MM"),
        (("2026-11-16", "24:00", "10:00"), "out of range"),
        (("2026-11-16", "09:00", "09:00"), "same time"),
        (("2026-11-16", "09:00", "17:00", "08:00-08:30"), "not inside"),
        (("2026-11-16", "09:00", "17:00", "12:00-12:30;12:15-12:45"), "overlaps"),
        (("2026-11-16", "09:00", "17:00", "12:00"), "HH:MM-HH:MM"),
    ],
)
def test_make_shift_errors(args, message):
    with pytest.raises(ValueError, match=message):
        make_shift("E1", *args)


def test_load_example(examples):
    shifts = load_schedule(examples / "schedule.csv")
    assert len(shifts) == 16 and shifts[0].employee == "E101"


def test_load_reports_every_line_and_overlaps(write):
    path = write(
        "s.csv",
        "employee,date,start,end\n,2026-11-16,09:00,10:00\nE1,2026-11-16,x,10:00\n"
        "E1,2026-11-16,09:00,17:00\nE1,2026-11-16,16:00,18:00\n",
    )
    with pytest.raises(ScheduleError) as info:
        load_schedule(path)
    assert [e.split(":")[0] for e in info.value.errors] == ["line 2", "line 3", "line 5"]
    assert "overlaps the shift on line 4" in info.value.errors[-1]


def test_missing_columns_and_empty(write):
    with pytest.raises(ScheduleError, match="missing column"):
        load_schedule(write("s.csv", "employee,date,start\nE1,2026-11-16,09:00\n"))
    with pytest.raises(ScheduleError, match="empty"):
        load_schedule(write("s.csv", ""))
    with pytest.raises(ScheduleError, match="no shifts"):
        load_schedule(write("s.csv", "employee,date,start,end\n"))


def test_wages(examples, write):
    assert load_wages(examples / "wages.csv")["E103"] == "18.00"
    with pytest.raises(ScheduleError) as info:
        load_wages(write("w.csv", "employee,hourly_wage\nE1,19.5.0\nE2,20\nE2,21\n"))
    assert len(info.value.errors) == 2
    with pytest.raises(ScheduleError, match="needs columns"):
        load_wages(write("w.csv", "employee,wage\nE1,20\n"))
