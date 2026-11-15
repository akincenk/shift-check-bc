# shift-check-bc

Check a staff schedule against the hours of work and overtime rules of the British Columbia Employment Standards Act before you post it. It reads the schedule from a CSV file. It lists every shift that breaks a rule or costs extra pay, with the section of the Act it comes from, and shows each person's weekly hours split into regular time, time and a half and double time.

This is a planning aid, not legal advice. See [What it does not cover](#what-it-does-not-cover).

## Who it is for

Store managers, shift supervisors and small business owners in BC who build schedules in a spreadsheet. Most payroll and scheduling tools only total the hours. The rules that are easy to get wrong are things like a meal break after five hours, eight hours off between a closing and an opening shift, a split shift that runs too long, or a sixth day that turns into overtime. This tool finds those before the schedule goes on the wall.

## Rules checked

| Rule | Section | Kind |
| --- | --- | --- |
| no more than 5 consecutive hours without a meal break of at least 30 minutes | s. 32 | violation |
| a split shift is completed within 12 hours of starting work | s. 33 | violation |
| at least 2 hours' pay when an employee reports for work | s. 34 | pay |
| at least 8 consecutive hours free between shifts | s. 36(2) | violation |
| 32 consecutive hours free each week, or time and a half for work in that period | s. 36(1) | pay |
| time and a half over 8 hours a day, double time over 12 | s. 40(1) | hours table |
| time and a half over 40 hours a week, counting only the first 8 hours of each day | s. 40(2), (3) | hours table |
| hourly wage at least the general minimum wage on the day worked (with `--wages`) | s. 16 | violation |

`violation` means the schedule should be changed. `pay` means it is allowed but costs extra or sets a pay floor.

Sources: the [Employment Standards Act](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_96113_01) (RSBC 1996, c. 113) on BC Laws, and the BC government minimum wage announcements ($17.85 from June 1, 2025; $18.25 from June 1, 2026). All numbers are in [`src/shift_check/esa.py`](src/shift_check/esa.py) with the section they come from.

## Install

Python 3.11 or newer. No runtime dependencies.

```sh
git clone https://github.com/akincenk/shift-check-bc
cd shift-check-bc
python3 -m venv .venv && . .venv/bin/activate
pip install -e .            # add '.[dev]' to run the tests
```

## Use

```sh
shift-check check examples/schedule.csv --wages examples/wages.csv
```

```text
16 shifts, 4 violations, 2 pay notes

VIOLATION  E101          2026-11-17  s. 32     09:00-19:00: 6 h 30 min without a meal break of at least 30 min (limit 5 h)
PAY        E102          2026-11-15  s. 34     scheduled for 1 h 30 min; must be paid for at least 2 h
VIOLATION  E102          2026-11-21  s. 36(2)  only 7 h 30 min free between Fri 23:30 and Sat 07:00 (needs 8 h)
VIOLATION  E102          2026-11-21  s. 33     split shift 07:00 to 20:00 spans 13 h (limit 12 h)
VIOLATION  E103          2026-11-15  s. 16     hourly wage 18.00 is below the minimum wage of 18.25 in effect on 2026-11-15
PAY        E103          2026-11-15  s. 36(1)  week of 2026-11-15: longest time off is 22 h, not 32 h; work in the missing rest period is paid at time and a half

employee  week of     total        regular      1.5x        2x   gross pay
E101      2026-11-15  49 h 15 min  40 h         9 h 15 min  0 h  1050.56
E102      2026-11-15  17 h 30 min  16 h 30 min  1 h         0 h  328.50
E103      2026-11-15  45 h         40 h         5 h         0 h  855.00
```

The exit code is `0` when there are no violations, `1` when there are, and `2` for bad input, so it can run in a script or a CI job that checks a schedule file. `--format csv` and `--format json` give machine-readable output. `shift-check hours` prints only the weekly table.

### Schedule file

```csv
employee,date,start,end,breaks
E101,2026-11-17,09:00,19:00,12:00-12:30
E103,2026-11-16,22:00,06:00,01:30-02:00
E102,2026-11-21,07:00,11:00,
E102,2026-11-21,15:00,20:00,
```

- `employee` is any ID. Use IDs, not names, if the file leaves your computer.
- Times are 24-hour local times. An end time that is not after the start ends the next day.
- `breaks` lists unpaid breaks separated by `;`. Breaks of 30 minutes or more are meal breaks.
- Two rows for the same person on the same day, less than 8 hours apart, are one split shift.
- Every bad line is reported with its line number, and overlapping shifts for one person are refused.

`--wages` takes a CSV with `employee,hourly_wage` to add gross pay and the minimum wage check.

## How it reads the Act

Some rules need a choice where the Act does not spell out the detail. The choices are:

- **Day and week.** Hours count towards the day the shift starts, following the definition of "day" for shifts over midnight. Overtime weeks start on Sunday, as the definition of "week" says for overtime. The weekly rest check uses the same Sunday weeks, and time outside the schedule file counts as free.
- **Split shift.** The Act does not define it. Here, parts on the same day with less than 8 hours between them form one split shift. With 8 hours or more between them they are two shifts, and s. 36(2) is met.
- **Short breaks.** A break under 30 minutes is not a meal break, so the 5-hour count does not restart at it. The time is still taken off the hours worked, because the file says it is unpaid.
- **Meal breaks on call.** If staff must stay available during a meal break, s. 32(2) says it counts as time worked. Leave such breaks out of the `breaks` column.

## What it does not cover

- Occupations that are excluded from these rules or have their own rules in the Employment Standards Regulation, and anyone covered by a collective agreement with different terms.
- Averaging agreements (s. 37) and variances granted by the Director.
- Statutory holidays, vacation pay and the emergency exception to s. 36(2).
- Reporting pay when a shift is cut short on the day (s. 34(2), (3)). The tool checks the schedule, not what happened.

Check the [Employment Standards Branch](https://www2.gov.bc.ca/gov/content/employment-business/employment-standards-advice/employment-standards) for anything outside these limits. Several of them are planned in [ROADMAP.md](ROADMAP.md).

## Code layout

| File | Role |
| --- | --- |
| `src/shift_check/esa.py` | the numbers from the Act and the minimum wage table, each with its section |
| `src/shift_check/schedule.py` | `Shift`, CSV loading, night shifts, breaks, overlap check |
| `src/shift_check/hours.py` | daily and weekly overtime split (s. 40) and gross pay with `Decimal` |
| `src/shift_check/checks.py` | one function per rule, each returning `Finding`s |
| `src/shift_check/cli.py` | the `shift-check` command |

A new rule is one function in `checks.py` that takes the shifts and returns findings, plus one line in `check()`.

## Development

```sh
pip install -e '.[dev]'
ruff check . && ruff format --check . && pytest -q
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT, see [LICENSE](LICENSE).
