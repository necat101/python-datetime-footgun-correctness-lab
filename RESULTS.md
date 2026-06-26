# Python Datetime Footgun Correctness Lab — Results

**Python:** 3.12.3 (CPython)

**zoneinfo available:** True

**Zones loaded:** Europe/Paris, America/New_York, Asia/Tokyo, UTC

**Platform:** Linux-6.17.0-1009-aws-x86_64-with-glibc2.39

**Cases:** 53 (12884 bytes)

**Seed:** 42 (deterministic)

**Timing:** time.perf_counter()

**Memory:** tracemalloc — current 251.7 KiB, peak 252.3 KiB

**Total wall time:** 0.0369s

**Subprocess count:** 0

## Summary

| Method | Kind | Pass | Fail | Skip | Expected-Fail | Time (ms) |
|---|---|---:|---:|---:|---:|---:|
| aware_utc_roundtrip_baseline | utc-conversion | 28 | 0 | 25 | 0 | 5.153 |
| zoneinfo_wall_time_baseline | zoneinfo-conversion | 16 | 0 | 37 | 0 | 1.060 |
| fixed_offset_timezone_baseline | fixed-offset | 28 | 0 | 25 | 0 | 0.870 |
| isoformat_fromisoformat_roundtrip | iso-roundtrip | 43 | 0 | 10 | 0 | 2.043 |
| rfc_email_datetime_parse | rfc-parse | 29 | 0 | 24 | 0 | 2.314 |
| timestamp_roundtrip_baseline | timestamp | 27 | 2 | 24 | 2 | 1.548 |
| timedelta_add_24h_naive | timedelta-arithmetic | 38 | 0 | 15 | 0 | 3.135 |
| naive_string_sort_baseline | naive-string | 6 | 0 | 47 | 0 | 1.165 |
| naive_strip_timezone_baseline | naive-strip | 18 | 21 | 14 | 21 | 1.446 |

## Skip Matrix

| Method | Total | Passed | Failed | Skipped |
|---|---:|---:|---:|---:|
| aware_utc_roundtrip_baseline | 53 | 28 | 0 | 25 |
| zoneinfo_wall_time_baseline | 53 | 16 | 0 | 37 |
| fixed_offset_timezone_baseline | 53 | 28 | 0 | 25 |
| isoformat_fromisoformat_roundtrip | 53 | 43 | 0 | 10 |
| rfc_email_datetime_parse | 53 | 29 | 0 | 24 |
| timestamp_roundtrip_baseline | 53 | 27 | 2 | 24 |
| timedelta_add_24h_naive | 53 | 38 | 0 | 15 |
| naive_string_sort_baseline | 53 | 6 | 0 | 47 |
| naive_strip_timezone_baseline | 53 | 18 | 21 | 14 |

## Failures (grouped by method)

### timestamp_roundtrip_baseline

- **D007** [dst_gap]  — timestamp roundtrip mismatch (expected)
- **D013** [nonexistent]  — timestamp roundtrip mismatch (expected)

### naive_strip_timezone_baseline

- **D003** [naive_aware]  — naive strip changed comparison result (expected)
- **D004** [utc_instant]  — timezone info stripped (expected)
- **D005** [fixed_offset]  — timezone info stripped (expected)
- **D006** [zoneinfo]  — timezone info stripped (expected)
- **D007** [dst_gap]  — timezone info stripped (expected)
- **D008** [dst_fold]  — timezone info stripped (expected)
- **D009** [dst_fold]  — timezone info stripped (expected)
- **D010** [zoneinfo]  — timezone info stripped (expected)
- **D011** [zoneinfo]  — timezone info stripped (expected)
- **D012** [ambiguous]  — timezone info stripped (expected)
- **D014** [utc_instant]  — timezone info stripped (expected)
- **D015** [utc_instant]  — timezone info stripped (expected)
- **D016** [naive_aware]  — naive strip changed comparison result (expected)
- **D019** [timestamp]  — timezone info stripped (expected)
- **D024** [timestamp]  — timezone info stripped (expected)
- **D028** [fixed_offset]  — timezone info stripped (expected)
- **D039** [dst_fold]  — timezone info stripped (expected)
- **D040** [dst_gap]  — timezone info stripped (expected)
- **D043** [timestamp]  — timezone info stripped (expected)
- **D048** [utc_instant]  — timezone info stripped (expected)
- **D050** [fixed_offset]  — timezone info stripped (expected)

## Notes

- `aware_utc_roundtrip_baseline`: UTC round-trip preserves instant and fold where supported.
- `zoneinfo_wall_time_baseline`: IANA ZoneInfo handles DST transitions; skipped if zone unavailable.
- `fixed_offset_timezone_baseline`: fixed offsets work but are NOT real time zones (no DST).
- `isoformat_fromisoformat_roundtrip`: ISO-8601 round-trip works; `fromisoformat` may reject `Z` suffix depending on Python version.
- `rfc_email_datetime_parse`: email.utils handles RFC 2822 dates.
- `timestamp_roundtrip_baseline`: timestamp round-trip can lose fold information (PEP 495).
- `timedelta_add_24h_naive`: adding `days=1` preserves wall-clock time, not necessarily 24 elapsed hours across DST.
- `naive_string_sort_baseline`: string comparison of datetime strings ignores timezone semantics.
- `naive_strip_timezone_baseline`: stripping tzinfo loses information and changes comparison results.
- No external datetime libraries (arrow, pendulum, dateutil, pytz, etc.) were used — out of scope.
- Python datetime has no leap second support.

## Conclusion

Naïve and aware datetimes have different meanings. DST gaps and folds surprise people. UTC instants and human local schedules are different concepts. Fixed offsets are not full time zones. Adding 24 hours is not always the same as 'same local clock time tomorrow'. Use explicit timezone handling with ZoneInfo, be careful with fold/ambiguity, and never rely on naive string or timestamp handling for datetime semantics.
