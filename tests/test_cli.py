import csv
import io
import json

from shift_check.cli import main


def test_check_text(examples, capsys):
    code = main(["check", str(examples / "schedule.csv"), "--wages", str(examples / "wages.csv")])
    out = capsys.readouterr().out
    assert code == 1
    assert "16 shifts, 4 violations, 2 pay notes" in out
    assert "not legal advice" in out and "gross pay" in out


def test_check_csv_and_json(examples, capsys):
    main(["check", str(examples / "schedule.csv"), "--format", "csv"])
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert {r["rule"] for r in rows} >= {"meal-break", "split-shift"}
    main(["check", str(examples / "schedule.csv"), "--wages", str(examples / "wages.csv"), "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    e101 = next(w for w in data["weeks"] if w["employee"] == "E101")
    assert e101["pay"] is not None and data["findings"][0]["day"].startswith("2026-")


def test_clean_schedule_exit_0(write, capsys):
    path = write("s.csv", "employee,date,start,end,breaks\nE1,2026-11-16,09:00,17:00,12:00-12:30\n")
    assert main(["check", str(path)]) == 0
    assert main(["hours", str(path)]) == 0
    assert "7 h 30 min" in capsys.readouterr().out


def test_bad_input_exit_2(write, capsys):
    assert main(["check", str(write("s.csv", "employee,date,start,end\nE1,x,09:00,10:00\n"))]) == 2
    assert "not YYYY-MM-DD" in capsys.readouterr().err
