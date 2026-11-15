# Roadmap

Planned work after the first version, roughly in order. Estimates are for one person and include tests and docs. Each item has a GitHub issue. Any new rule must cite the section of the Employment Standards Act or Regulation it comes from, checked on BC Laws. Total: about 29 hours.

## 1. Statutory holidays (4 h)

Add the statutory holidays listed in s. 1 of the Act (New Year's Day through Christmas Day) with their dates per year, and flag work on them. Implement eligibility and pay from Part 5 of the Act, quoting each section from BC Laws in the code. Eligibility depends on past shifts, so accept an optional history file.

## 2. Averaging agreements (4 h)

Support s. 37 averaging agreements: per-employee settings in a TOML file, overtime computed over the averaging period instead of daily and weekly, and the limits in s. 37 checked. Read s. 37 on BC Laws first and quote the limits in the code.

## 3. Rest period week start (1.5 h)

For s. 36(1) the Act allows a week to start on any day. Let the employer choose the start day for the weekly rest check, and add a rolling 7-day mode that reports the worst window.

## 4. Spreadsheet-style input (3 h)

Many schedules are a grid: one row per person, one column per day, cells like `9-5:30` or `22-6 (30)`. Read that format from CSV, with a clear error per cell that cannot be read.

## 5. Shift cut short on the day (2 h)

Given actual start and end times next to the scheduled ones, compute the minimum daily pay under s. 34(2) and (3): 4 hours when the person was scheduled for more than 8, 2 hours when work stopped for reasons beyond the employer's control.

## 6. Paid and on-call meal breaks (1.5 h)

A `paid_breaks` column for breaks where staff must stay available. They count as time worked (s. 32(2)) and do not restart the 5-hour count.

## 7. Excluded occupations and other rules (3 h)

Let a person be marked with a profile (for example manager) that turns specific checks off, and document each profile with the section of the Employment Standards Regulation that excludes it. No profile is added without a citation.

## 8. iCalendar export of a clean schedule (2 h)

`shift-check ical` writes one `.ics` file per employee so staff can add their shifts to a phone calendar. Only after `check` finds no violations, unless `--force`.

## 9. Suggested fixes (3 h)

For each violation, suggest the smallest change that fixes it: move a break earlier, end a split shift sooner, push the next start time later. Show the fix and the new overtime cost; never change the file without `--write`.

## 10. Cost summary per week (1.5 h)

Total overtime hours and cost per week and per person, and what it would cost if the overtime were given to someone under 40 hours.

## 11. HTML report (2 h)

A self-contained HTML page with one row per person and one column per day, violations in red, for printing next to the posted schedule.

## 12. Minimum wage updates check (1.5 h)

A small test that fails when the minimum wage table is more than a year old after June 1, as a reminder to check the yearly BC announcement and add the new rate with its source.
