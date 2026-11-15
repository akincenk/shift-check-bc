from datetime import date, timedelta

from shift_check import check, make_shift
from shift_check.checks import meal_breaks, minimum_daily_pay, rest_between_shifts, split_shifts, weekly_rest


def rules(findings):
    return [f.rule for f in findings]


def test_meal_break_after_five_hours():
    assert meal_breaks([make_shift("E1", "2026-11-16", "09:00", "14:00")]) == []  # exactly 5 h
    [f] = meal_breaks([make_shift("E1", "2026-11-16", "09:00", "14:01")])
    assert (f.section, f.kind) == ("s. 32", "violation")
    assert meal_breaks([make_shift("E1", "2026-11-16", "09:00", "17:00", "12:00-12:30")]) == []


def test_short_break_is_not_a_meal_break():
    shift = make_shift("E1", "2026-11-16", "09:00", "17:00", "11:00-11:15;14:00-14:20")
    [f] = meal_breaks([shift])
    assert "8 h without a meal break" in f.message


def test_meal_break_on_night_shift():
    assert meal_breaks([make_shift("E1", "2026-11-16", "22:00", "06:00", "01:30-02:00")]) == []
    assert len(meal_breaks([make_shift("E1", "2026-11-16", "22:00", "06:00", "04:00-04:30")])) == 1


def test_split_shift_within_twelve_hours():
    ok = [make_shift("E1", "2026-11-16", "07:00", "11:00"), make_shift("E1", "2026-11-16", "15:00", "19:00")]
    assert split_shifts(ok) == []
    late = [make_shift("E1", "2026-11-16", "07:00", "11:00"), make_shift("E1", "2026-11-16", "15:00", "19:30")]
    [f] = split_shifts(late)
    assert "spans 12 h 30 min" in f.message


def test_parts_eight_hours_apart_are_separate_shifts():
    shifts = [make_shift("E1", "2026-11-16", "05:00", "09:00"), make_shift("E1", "2026-11-16", "17:00", "21:00")]
    assert split_shifts(shifts) == [] and rest_between_shifts(shifts) == []


def test_rest_between_shifts():
    shifts = [make_shift("E1", "2026-11-16", "15:00", "23:00"), make_shift("E1", "2026-11-17", "06:30", "14:30")]
    [f] = rest_between_shifts(shifts)
    assert "only 7 h 30 min free" in f.message and f.section == "s. 36(2)"
    other = [make_shift("E1", "2026-11-16", "15:00", "23:00"), make_shift("E2", "2026-11-17", "06:30", "14:30")]
    assert rest_between_shifts(other) == []


def test_weekly_rest():
    sunday = date(2026, 11, 15)
    five = [make_shift("E1", str(sunday + timedelta(days=i)), "09:00", "17:00") for i in range(1, 6)]
    assert weekly_rest(five) == []  # Friday 17:00 to the end of Saturday is 31 h, Sunday to Monday 33 h
    seven = [make_shift("E1", str(sunday + timedelta(days=i)), "09:00", "17:00") for i in range(7)]
    [f] = weekly_rest(seven)
    assert f.kind == "pay" and "16 h" in f.message


def test_minimum_daily_pay_counts_split_parts_together():
    assert rules(minimum_daily_pay([make_shift("E1", "2026-11-16", "09:00", "10:30")])) == ["minimum-daily-pay"]
    parts = [make_shift("E1", "2026-11-16", "09:00", "10:00"), make_shift("E1", "2026-11-16", "12:00", "13:30")]
    assert minimum_daily_pay(parts) == []


def test_minimum_wage_check():
    shifts = [
        make_shift("E1", "2026-05-29", "09:00", "17:00", "12:00-12:30"),
        make_shift("E1", "2026-06-02", "09:00", "17:00", "12:00-12:30"),
    ]
    found = [f for f in check(shifts, {"E1": "18.00"}) if f.rule == "minimum-wage"]
    assert len(found) == 1 and "18.25" in found[0].message  # 18.00 was fine before June 1, 2026
    assert [f for f in check(shifts, {"E1": "18.25"}) if f.rule == "minimum-wage"] == []


def test_example_schedule(examples):
    from shift_check import load_schedule, load_wages

    findings = check(load_schedule(examples / "schedule.csv"), load_wages(examples / "wages.csv"))
    got = {(f.employee, f.rule) for f in findings}
    assert got == {
        ("E101", "meal-break"),
        ("E102", "minimum-daily-pay"),
        ("E102", "rest-between-shifts"),
        ("E102", "split-shift"),
        ("E103", "minimum-wage"),
        ("E103", "weekly-rest"),
    }
