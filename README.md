# Python Datetime Footgun Correctness Lab

A tiny, reproducible Python-only lab testing the Hacker News debate around Python datetime pitfalls.

**HN thread:** https://news.ycombinator.com/item?id=39417231
**Linked article:** https://dev.arie.bovenberg.net/blog/python-datetime-pitfalls/
**PEP 495 (fold):** https://peps.python.org/pep-0495/
**PEP 615 (zoneinfo):** https://peps.python.org/pep-0615/

## What HN was debating

- Why datetime has surprising but historically compatible behavior.
- Why naïve and aware datetimes should not be casually mixed.
- Why UTC instants are useful but do not solve every human scheduling problem.
- Why "4pm local time" can mean different things depending on the product requirement.
- Why DST gaps and folds need explicit handling.
- Why the `fold` attribute exists (PEP 495).
- Why fixed offsets are not the same thing as IANA time zones.
- Why adding 24 hours and preserving the same local wall-clock time are different ideas.
- Why date/datetime inheritance and comparison behavior surprise people.
- Why Python stdlib does not support leap seconds.
- Why local system timezone behavior is a caveat.
- Why Arrow/Pendulum conflating Date/Time/Datetime into one type creates bugs.
- Why third-party libraries are out of scope for this lab.

The linked article lists 10 datetime pitfalls: incompatible concepts squeezed into one class (naïve/aware), operators ignoring DST, inconsistent meaning of "naïve", non-existent datetimes passing silently, guessing in the face of ambiguity (fold), disambiguation breaking equality, inconsistent equality within timezone, datetime inheriting from date, datetime.timezone not being enough for timezone support, and the local timezone being DST-unaware.

## What this lab does

Tests 53 deterministic datetime edge cases across 9 stdlib-only methods:

| Method | Description |
|---|---|
| `aware_utc_roundtrip_baseline` | convert aware datetime to UTC and back |
| `zoneinfo_wall_time_baseline` | `zoneinfo.ZoneInfo` IANA timezone handling — skip if zone unavailable |
| `fixed_offset_timezone_baseline` | `datetime.timezone` fixed offsets — documents where this ≠ real zone |
| `isoformat_fromisoformat_roundtrip` | `datetime.isoformat` / `datetime.fromisoformat` round-trip |
| `rfc_email_datetime_parse` | `email.utils` RFC 2822 datetime parsing |
| `timestamp_roundtrip_baseline` | `timestamp()` / `fromtimestamp()` — with fold-loss caveats |
| `timedelta_add_24h_naive` | `timedelta(days=1)` vs `timedelta(hours=24)` across DST |
| `naive_string_sort_baseline` | intentionally unsafe string comparison — expected to fail |
| `naive_strip_timezone_baseline` | intentionally unsafe tzinfo stripping — expected to fail |

**Categories covered:** normal, naive_aware, utc_instant, fixed_offset, zoneinfo, dst_gap, dst_fold, ambiguous, nonexistent, isoformat, rfc_email, timestamp, date_datetime, timedelta_math, local_timezone_caveat, leap_day, leap_second_caveat, naive_negative

No compilers, no package managers, no Docker, no external corpora, no network calls during the benchmark. Python stdlib only.

## Running

```bash
python3 -m py_compile generate_cases.py run_lab.py
python3 generate_cases.py
python3 run_lab.py
```

Output:
- `cases/cases.jsonl` — 53 deterministic cases (seed 42)
- `results/results.jsonl` — per-method results
- `RESULTS.md` — summary table, skip matrix, failure list, conclusions

## Results (CPython 3.12.3)

| Method | Pass | Fail | Skip |
|---|---|---:|---:|
| aware_utc_roundtrip_baseline | 28 | 0 | 25 |
| zoneinfo_wall_time_baseline | 16 | 0 | 37 |
| fixed_offset_timezone_baseline | 28 | 0 | 25 |
| isoformat_fromisoformat_roundtrip | 43 | 0 | 10 |
| rfc_email_datetime_parse | 29 | 0 | 24 |
| timestamp_roundtrip_baseline | 27 | 2 | 24 |
| timedelta_add_24h_naive | 38 | 0 | 15 |
| naive_string_sort_baseline | 6 | 0 | 47 |
| naive_strip_timezone_baseline | 18 | 21 | 14 |

Timestamp roundtrip: 2 expected failures (DST gap / nonexistent times). Naive strip: 21 expected failures (timezone info loss). All correct-method failures are 0.

See [RESULTS.md](RESULTS.md) for full details.

## Key findings

- Naïve and aware datetimes cannot be compared — raises `TypeError`, correct behavior.
- UTC round-trip preserves instants correctly for aware datetimes.
- ZoneInfo correctly handles DST transitions, gaps, and folds — when the IANA zone is available.
- Fixed offsets work but do NOT observe DST — not equivalent to real time zones.
- ISO-8601 round-trip works; `fromisoformat()` may reject `Z` suffix depending on Python version.
- RFC 2822 email datetime parsing works via `email.utils`.
- Timestamp round-trip can lose `fold` information (PEP 495) and breaks on nonexistent DST gap times.
- Adding `timedelta(days=1)` preserves wall-clock time, NOT necessarily 24 elapsed hours across DST.
- Naive string sorting of datetime strings ignores timezone semantics.
- Stripping timezone info changes comparison results — security/correctness footgun.
- Python datetime has **no leap second support**.
- IANA timezone database availability depends on the system — ZoneInfo skips cleanly if zones are missing.

## Scope

This lab is intentionally tiny. It does **not** claim Python datetime is bad, and does **not** claim third-party libraries are better. It tests the HN debate in a reproducible way: naïve/aware mixing surprises people, DST gaps/folds need explicit handling, UTC instants ≠ human local schedules, fixed offsets ≠ real time zones, and 24 hours ≠ "same wall-clock time tomorrow."

No external datetime libraries (arrow, pendulum, dateutil, pytz, whenever, heliclockter, etc.) were used.

## Verify

See [VERIFY.md](VERIFY.md) for a fresh-clone verification transcript.
