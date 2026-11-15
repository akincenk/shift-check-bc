"""Command line: shift-check check | hours."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict

from .checks import check
from .hours import hm, weeks
from .schedule import ScheduleError, load_schedule, load_wages

NOTICE = "Planning aid only, not legal advice. Exclusions, variances and averaging agreements are not covered."


def _week_rows(week_list) -> list[list[str]]:
    rows = [["employee", "week of", "total", "regular", "1.5x", "2x", "gross pay"]]
    for w in week_list:
        pay = "" if w.pay is None else f"{w.pay}"
        rows.append([w.employee, str(w.start), hm(w.minutes), hm(w.regular), hm(w.time_and_half), hm(w.double), pay])
    return rows


def _table(rows: list[list[str]]) -> str:
    widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]
    return "\n".join("  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)).rstrip() for r in rows)


def cmd_check(args: argparse.Namespace) -> int:
    shifts = load_schedule(args.schedule)
    wages = load_wages(args.wages) if args.wages else None
    findings = check(shifts, wages)
    week_list = weeks(shifts, wages)
    violations = sum(1 for f in findings if f.kind == "violation")
    if args.format == "json":
        data = {
            "findings": [asdict(f) | {"day": str(f.day)} for f in findings],
            "weeks": [
                asdict(w) | {"start": str(w.start), "pay": None if w.pay is None else str(w.pay)} for w in week_list
            ],
        }
        sys.stdout.write(json.dumps(data, indent=2) + "\n")
    elif args.format == "csv":
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(["kind", "rule", "section", "employee", "day", "message"])
        writer.writerows([f.kind, f.rule, f.section, f.employee, f.day, f.message] for f in findings)
    else:
        print(f"{len(shifts)} shifts, {violations} violations, {len(findings) - violations} pay notes\n")
        for f in findings:
            print(f"{f.kind.upper():<9}  {f.employee:<12}  {f.day}  {f.section:<8}  {f.message}")
        print("\n" + _table(_week_rows(week_list)))
        print(f"\n{NOTICE}")
    return 1 if violations else 0


def cmd_hours(args: argparse.Namespace) -> int:
    shifts = load_schedule(args.schedule)
    wages = load_wages(args.wages) if args.wages else None
    print(_table(_week_rows(weeks(shifts, wages))))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shift-check",
        description="Check a staff schedule against the BC Employment Standards Act hours of work rules.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func, text in (
        ("check", cmd_check, "list rule problems and weekly hours"),
        ("hours", cmd_hours, "weekly hours with the overtime split"),
    ):
        p = sub.add_parser(name, help=text)
        p.add_argument("schedule", help="CSV with employee, date, start, end, optional breaks")
        p.add_argument("--wages", help="CSV with employee, hourly_wage (enables pay and minimum wage checks)")
        if name == "check":
            p.add_argument("--format", choices=["text", "csv", "json"], default="text")
        p.set_defaults(func=func)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ScheduleError, OSError) as exc:
        print(f"shift-check: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
