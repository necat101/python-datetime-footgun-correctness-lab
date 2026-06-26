# VERIFY.md — Fresh-clone verification

## Commit 980af49 (HEAD)

Verified 2026-06-26.

```bash
$ git clone https://github.com/necat101/python-datetime-footgun-correctness-lab.git datetime-verify
Cloning into 'datetime-verify'...

$ cd datetime-verify
$ python3 -m py_compile generate_cases.py run_lab.py
$ python3 generate_cases.py
Wrote 53 cases to cases/cases.jsonl (12884 bytes), zoneinfo=True, paris=True, ny=True, tokyo=True

$ python3 run_lab.py
Results: results/results.jsonl (120072 bytes)
Report: RESULTS.md
  aware_utc_roundtrip_baseline: pass=28 fail=0 skip=25 time=6.79ms
  zoneinfo_wall_time_baseline: pass=16 fail=0 skip=37 time=1.27ms
  fixed_offset_timezone_baseline: pass=28 fail=0 skip=25 time=0.97ms
  isoformat_fromisoformat_roundtrip: pass=43 fail=0 skip=10 time=2.33ms
  rfc_email_datetime_parse: pass=29 fail=0 skip=24 time=2.44ms
  timestamp_roundtrip_baseline: pass=27 fail=2 skip=24 time=1.76ms
  timedelta_add_24h_naive: pass=38 fail=0 skip=15 time=3.35ms
  naive_string_sort_baseline: pass=6 fail=0 skip=47 time=1.15ms
  naive_strip_timezone_baseline: pass=18 fail=21 skip=14 time=1.48ms
```

All 53 cases generated deterministically (seed 42).
- `aware_utc_roundtrip_baseline`: 28 pass, 0 fail, 25 skip
- `zoneinfo_wall_time_baseline`: 16 pass, 0 fail, 37 skip (ZoneInfo cases only; skipped when zone unavailable or input not ZoneInfo)
- `fixed_offset_timezone_baseline`: 28 pass, 0 fail, 25 skip
- `isoformat_fromisoformat_roundtrip`: 43 pass, 0 fail, 10 skip
- `rfc_email_datetime_parse`: 29 pass, 0 fail, 24 skip
- `timestamp_roundtrip_baseline`: 27 pass, **2 fail**, 24 skip — 2 expected failures (DST gap / nonexistent times)
- `timedelta_add_24h_naive`: 38 pass, 0 fail, 15 skip
- `naive_string_sort_baseline`: 6 pass, 0 fail, 47 skip
- `naive_strip_timezone_baseline`: 18 pass, **21 fail**, 14 skip — all 21 failures expected (timezone info loss)

Python: CPython 3.12.3 on Linux-6.17.0-1009-aws-x86_64-with-glibc2.39
zoneinfo available: True
Zones loaded: Europe/Paris, America/New_York, Asia/Tokyo, UTC
