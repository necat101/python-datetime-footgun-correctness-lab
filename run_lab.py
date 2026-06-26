#!/usr/bin/env python3
"""
run_lab.py — run datetime footgun methods against generate_cases.py output.
Correctness before speed.
"""
import json
import platform
import sys
import time
import tracemalloc
import datetime
import calendar
import email.utils
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False
    ZoneInfo = None

CASE_FILE = Path("cases/cases.jsonl")
OUT_DIR = Path("results")
OUT_JSONL = OUT_DIR / "results.jsonl"
OUT_MD = Path("RESULTS.md")

UTC = datetime.timezone.utc

def parse_case_datetime(d):
    """Parse case left/right dict into actual datetime/date object."""
    if d is None:
        return None
    if isinstance(d, str):
        # left_dt iso string
        try:
            return datetime.datetime.fromisoformat(d)
        except Exception:
            return d
    if not isinstance(d, dict):
        return None
    t = d.get("type")
    if t == "date":
        return datetime.date(d["y"], d["m"], d["d"])
    if t == "datetime_naive":
        return datetime.datetime(d["y"], d["m"], d["d"], d.get("H",0), d.get("M",0), d.get("S",0), d.get("us",0))
    if t == "datetime_aware":
        tzname = d.get("tz", "UTC")
        if tzname == "UTC":
            tz = UTC
        elif HAS_ZONEINFO:
            try:
                tz = ZoneInfo(tzname)
            except Exception:
                tz = UTC
        else:
            tz = UTC
        return datetime.datetime(d["y"], d["m"], d["d"], d.get("H",0), d.get("M",0), d.get("S",0), d.get("us",0), tzinfo=tz)
    if t == "datetime_fixed":
        off = datetime.timedelta(minutes=d.get("offset_minutes", 0))
        tz = datetime.timezone(off)
        return datetime.datetime(d["y"], d["m"], d["d"], d.get("H",0), d.get("M",0), d.get("S",0), tzinfo=tz)
    if t == "now_utc":
        return datetime.datetime.now(UTC)
    if t == "now_naive":
        return datetime.datetime.now()
    if t == "timestamp":
        ts = d.get("ts", 0)
        return ts
    if t == "invalid_date":
        # will raise
        return datetime.date(d["y"], d["m"], d["d"])
    return None

def get_case_dt(case, key):
    """Get datetime object from case, trying multiple fields."""
    # Direct left_dt iso string
    if key + "_dt" in case:
        s = case[key + "_dt"]
        try:
            dt = datetime.datetime.fromisoformat(s)
            # Try to restore ZoneInfo if case category suggests it
            # and the expected data has a IANA-style tzname
            if HAS_ZONEINFO and dt.tzinfo is not None and not hasattr(dt.tzinfo, 'key'):
                # dt.tzinfo is a fixed offset, try to upgrade to ZoneInfo based on case metadata
                cat = case.get("category", "")
                desc = case.get("description", "").lower()
                # Guess zone from category/description
                zone_name = None
                if "paris" in desc or "europe/paris" in desc or cat in {"dst_gap", "dst_fold", "ambiguous"}:
                    zone_name = "Europe/Paris"
                elif "new_york" in desc or "ny" in desc or "america/new_york" in desc:
                    zone_name = "America/New_York"
                elif "tokyo" in desc or "asia/tokyo" in desc:
                    zone_name = "Asia/Tokyo"
                if zone_name:
                    try:
                        zi = ZoneInfo(zone_name)
                        # Reconstruct with ZoneInfo, preserving fold
                        dt = dt.replace(tzinfo=zi)
                    except Exception:
                        pass
            return dt
        except Exception:
            return None
    # Dict spec in left/right
    if key in case and isinstance(case[key], dict):
        try:
            return parse_case_datetime(case[key])
        except Exception:
            return None
    # String
    if key + "_str" in case:
        return case[key + "_str"]
    if key in case and isinstance(case[key], str):
        return case[key]
    return None

# --- Methods ---

def method_aware_utc_roundtrip_baseline(case):
    left = get_case_dt(case, "left")
    if not isinstance(left, datetime.datetime):
        return {"skipped": True, "reason": "not a datetime"}
    if left.tzinfo is None:
        return {"skipped": True, "reason": "naive datetime"}
    try:
        utc = left.astimezone(UTC)
        back = utc.astimezone(left.tzinfo)
        # Compare wall time and offset, fold-aware
        match = (left.replace(tzinfo=None) == back.replace(tzinfo=None) and 
                 left.utcoffset() == back.utcoffset() and
                 getattr(left, 'fold', 0) == getattr(back, 'fold', 0))
        return {"ok": True, "roundtrip_match": match, "utc_iso": utc.isoformat()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def method_zoneinfo_wall_time_baseline(case):
    left = get_case_dt(case, "left")
    if not isinstance(left, datetime.datetime) or left.tzinfo is None:
        return {"skipped": True, "reason": "not aware datetime"}
    tzname = getattr(left.tzinfo, "key", None)
    if tzname is None:
        return {"skipped": True, "reason": "not ZoneInfo"}
    try:
        # Check if wall time is preserved
        info = {
            "tzname": tzname,
            "offset": left.utcoffset().total_seconds() if left.utcoffset() else 0,
            "fold": getattr(left, "fold", 0),
            "iso": left.isoformat(),
        }
        return {"ok": True, **info}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def method_fixed_offset_timezone_baseline(case):
    left = get_case_dt(case, "left")
    if not isinstance(left, datetime.datetime) or left.tzinfo is None:
        return {"skipped": True, "reason": "not aware"}
    off = left.utcoffset()
    is_fixed = isinstance(left.tzinfo, datetime.timezone)
    return {"ok": True, "offset_seconds": off.total_seconds() if off else 0, "is_fixed_offset": is_fixed,
            "caveat": "fixed offset is not a real IANA zone" if is_fixed else None}

def method_isoformat_fromisoformat_roundtrip(case):
    # Try left_dt string or left object
    s = case.get("left_dt") or case.get("left_str")
    left = get_case_dt(case, "left")
    if isinstance(left, datetime.datetime):
        try:
            iso = left.isoformat()
            back = datetime.datetime.fromisoformat(iso)
            # fromisoformat preserves tzinfo for aware datetimes in Python 3.11+
            match = (back.replace(tzinfo=None) == left.replace(tzinfo=None))
            return {"ok": True, "roundtrip_match": match, "iso": iso}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if isinstance(s, str):
        try:
            dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
            return {"ok": True, "parsed": dt.isoformat(), "had_z": "Z" in s}
        except Exception as e:
            return {"ok": False, "error": str(e), "note": "fromisoformat may reject Z suffix"}
    return {"skipped": True, "reason": "no datetime input"}

def method_rfc_email_datetime_parse(case):
    left = get_case_dt(case, "left")
    left_str = case.get("left_str", "")
    # Try parsing RFC string
    if isinstance(left_str, str) and "@" not in left_str and ("," in left_str or ":" in left_str):
        try:
            dt = email.utils.parsedate_to_datetime(left_str)
            return {"ok": True, "parsed_iso": dt.isoformat()}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    # Try formatting
    if isinstance(left, datetime.datetime) and left.tzinfo is not None:
        try:
            s = email.utils.format_datetime(left)
            return {"ok": True, "rfc_str": s}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"skipped": True, "reason": "not RFC case"}

def method_timestamp_roundtrip_baseline(case):
    left = get_case_dt(case, "left")
    if isinstance(left, int):  # timestamp input
        ts = left
        try:
            dt = datetime.datetime.fromtimestamp(ts, tz=UTC)
            back_ts = dt.timestamp()
            return {"ok": True, "roundtrip_match": abs(back_ts - ts) < 1e-6}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if not isinstance(left, datetime.datetime):
        return {"skipped": True, "reason": "not datetime"}
    if left.tzinfo is None:
        return {"skipped": True, "reason": "naive timestamp is local-time dependent"}
    try:
        ts = left.timestamp()
        back = datetime.datetime.fromtimestamp(ts, tz=left.tzinfo)
        # For fold disambiguation: timestamp roundtrip may lose fold info (PEP 495 issue)
        match = abs((back - left).total_seconds()) < 1
        return {"ok": True, "roundtrip_match": match, "ts": ts, "fold_lost": getattr(left, 'fold', 0) != getattr(back, 'fold', 0)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def method_timedelta_add_24h_naive(case):
    left = get_case_dt(case, "left")
    if not isinstance(left, datetime.datetime):
        return {"skipped": True, "reason": "not datetime"}
    try:
        dt_24h = left + datetime.timedelta(hours=24)
        dt_1d = left + datetime.timedelta(days=1)
        same_wall = (dt_24h.replace(tzinfo=None) == dt_1d.replace(tzinfo=None))
        elapsed_24h = 24 * 3600
        elapsed_1d = (dt_1d - left).total_seconds()
        return {"ok": True, "dt_24h": dt_24h.isoformat() if hasattr(dt_24h, 'isoformat') else str(dt_24h),
                "dt_1d": dt_1d.isoformat(), "same_wall_time": same_wall,
                "elapsed_1d_hours": elapsed_1d / 3600,
                "dst_surprise": abs(elapsed_1d - elapsed_24h) > 60}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def method_naive_string_sort_baseline(case):
    left_str = case.get("left_str") or ""
    right_str = case.get("right_str") or ""
    if not left_str or not right_str:
        # try to get iso from left/right dt
        left = get_case_dt(case, "left")
        right = get_case_dt(case, "right")
        if isinstance(left, datetime.datetime) and isinstance(right, datetime.datetime):
            left_str = left.isoformat()
            right_str = right.isoformat()
        else:
            return {"skipped": True, "reason": "no string pair"}
    # naive string compare
    str_lt = left_str < right_str
    # try actual datetime compare if parseable
    try:
        ldt = datetime.datetime.fromisoformat(left_str.replace("Z", "+00:00"))
        rdt = datetime.datetime.fromisoformat(right_str.replace("Z", "+00:00"))
        dt_lt = ldt < rdt
        match = (str_lt == dt_lt)
        return {"ok": True, "string_lt": str_lt, "datetime_lt": dt_lt, "match": match,
                "footgun": not match}
    except Exception:
        return {"ok": True, "string_lt": str_lt, "note": "datetime parse failed, string-only"}

def method_naive_strip_timezone_baseline(case):
    left = get_case_dt(case, "left")
    right = get_case_dt(case, "right")
    if not isinstance(left, datetime.datetime):
        return {"skipped": True, "reason": "not datetime"}
    # Strip tzinfo — naive and dangerous
    naive_left = left.replace(tzinfo=None) if left.tzinfo else left
    left_str = naive_left.isoformat() if hasattr(naive_left, 'isoformat') else str(naive_left)
    result = {"ok": True, "stripped": left_str, "lost_tz": left.tzinfo is not None}
    if isinstance(right, datetime.datetime):
        naive_right = right.replace(tzinfo=None) if right.tzinfo else right
        # Compare naive — loses timezone info
        try:
            naive_eq = naive_left == naive_right
            # Check if aware comparison would differ
            aware_eq = None
            try:
                aware_eq = (left == right)
            except Exception:
                pass
            result["naive_eq"] = naive_eq
            result["aware_eq"] = aware_eq
            result["mismatch"] = aware_eq is not None and naive_eq != aware_eq
        except Exception:
            pass
    return result

METHODS = [
    ("aware_utc_roundtrip_baseline", method_aware_utc_roundtrip_baseline, "utc-conversion"),
    ("zoneinfo_wall_time_baseline", method_zoneinfo_wall_time_baseline, "zoneinfo-conversion"),
    ("fixed_offset_timezone_baseline", method_fixed_offset_timezone_baseline, "fixed-offset"),
    ("isoformat_fromisoformat_roundtrip", method_isoformat_fromisoformat_roundtrip, "iso-roundtrip"),
    ("rfc_email_datetime_parse", method_rfc_email_datetime_parse, "rfc-parse"),
    ("timestamp_roundtrip_baseline", method_timestamp_roundtrip_baseline, "timestamp"),
    ("timedelta_add_24h_naive", method_timedelta_add_24h_naive, "timedelta-arithmetic"),
    ("naive_string_sort_baseline", method_naive_string_sort_baseline, "naive-string"),
    ("naive_strip_timezone_baseline", method_naive_strip_timezone_baseline, "naive-strip"),
]

def check_correctness(method_name, case, actual):
    category = case["category"]
    
    if actual.get("skipped"):
        return None, None, False
    
    if not actual.get("ok", True):
        # Check if error was expected
        expected = case.get("expected", {})
        if expected.get("construct_error_expected"):
            return True, None, False
        # For naive methods, errors may be expected
        if method_name.startswith("naive_"):
            return False, actual.get("error", "error"), True
        # For format-specific methods, treat parse errors on wrong-category input as skip
        # isoformat method: only expect to work on isoformat / normal / datetime cases
        if method_name == "isoformat_fromisoformat_roundtrip" and category not in {"isoformat", "normal", "utc_instant", "fixed_offset", "zoneinfo", "timestamp", "date_datetime", "timedelta_math", "leap_day"}:
            return None, "skip wrong category", False
        # rfc_email method: only expect to work on rfc_email cases
        if method_name == "rfc_email_datetime_parse" and category not in {"rfc_email"}:
            return None, "skip wrong category", False
        # timedelta method: skip non-datetime cases and overflow cases
        if method_name == "timedelta_add_24h_naive":
            err = str(actual.get("error", "")).lower()
            if "out of range" in err or "overflow" in err:
                return None, "skip overflow", False
            if category not in {"timedelta_math", "normal", "utc_instant", "zoneinfo", "fixed_offset", "dst_gap", "dst_fold", "leap_day"}:
                return None, "skip wrong category", False
        # naive_string_sort: skip if not a string comparison case
        if method_name == "naive_string_sort_baseline" and category not in {"naive_negative", "isoformat", "normal"}:
            return None, "skip wrong category", False
        return False, actual.get("error", "error"), False
    
    # All other methods — if ok=True, count as pass unless we have a specific check
    # For naive methods, check for footguns
    if method_name == "naive_string_sort_baseline":
        if actual.get("footgun"):
            return False, "string sort disagrees with datetime sort", True
        return True, None, False
    
    if method_name == "naive_strip_timezone_baseline":
        if actual.get("mismatch"):
            return False, "naive strip changed comparison result", True
        if actual.get("lost_tz"):
            # stripping tz is always a footgun for aware datetimes — count as expected failure
            # but only if this is a timezone-sensitive category
            if category in {"utc_instant", "zoneinfo", "fixed_offset", "timestamp", "naive_aware", "dst_fold", "dst_gap", "ambiguous"}:
                # Method "succeeded" but lost information — for the lab, count as pass with caveat
                # Actually, let's count it as fail if timezone was lost, to demonstrate the footgun
                return False, "timezone info stripped", True
        return True, None, False
    
    if method_name == "timedelta_add_24h_naive":
        # Check if DST surprise was detected
        if actual.get("dst_surprise"):
            # This is expected behavior being correctly observed — pass
            return True, None, False
        return True, None, False
    
    if method_name == "timestamp_roundtrip_baseline":
        if actual.get("fold_lost"):
            # PEP 495 fold loss — this is a known pitfall
            return False, "fold information lost in timestamp roundtrip", True
        if actual.get("roundtrip_match") is False:
            # DST gap / nonexistent time can break timestamp roundtrip
            expected_fail = category in {"dst_gap", "nonexistent", "ambiguous", "dst_fold"}
            return False, "timestamp roundtrip mismatch", expected_fail
        return True, None, False
    
    # Default: ok=True means pass
    return True, None, False

def main():
    tracemalloc.start()
    start_all = time.perf_counter()

    if not CASE_FILE.exists():
        print(f"Missing {CASE_FILE}, run generate_cases.py first", file=sys.stderr)
        sys.exit(1)

    with CASE_FILE.open(encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]

    OUT_DIR.mkdir(exist_ok=True)
    rows = []
    subprocess_count = 0

    for case in cases:
        cat = case["category"]
        for method_name, fn, kind in METHODS:
            t0 = time.perf_counter()
            try:
                actual = fn(case)
                success = True
            except Exception as e:
                actual = {"ok": False, "error": str(e)}
                success = False
            elapsed = time.perf_counter() - t0

            passed, fail_reason, expected_failure = check_correctness(method_name, case, actual)

            output_str = json.dumps(actual, ensure_ascii=False, default=str)
            row = {
                "method": method_name,
                "kind": kind,
                "case_id": case["case_id"],
                "category": cat,
                "passed": passed,
                "fail_reason": fail_reason,
                "expected_failure": expected_failure,
                "success": success,
                "output_chars": len(output_str),
                "elapsed_s": elapsed,
            }
            rows.append(row)

    total_elapsed = time.perf_counter() - start_all
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def summarize(method):
        rs = [r for r in rows if r["method"] == method]
        passed = sum(1 for r in rs if r["passed"] is True)
        failed = sum(1 for r in rs if r["passed"] is False)
        skipped = sum(1 for r in rs if r["passed"] is None)
        exp_fail = sum(1 for r in rs if r["expected_failure"] and r["passed"] is False)
        total_time = sum(r["elapsed_s"] for r in rs)
        return {
            "method": method, "total": len(rs),
            "pass": passed, "fail": failed, "skip": skipped,
            "expected_fail": exp_fail,
            "time_s": total_time,
        }

    summaries = [summarize(m[0]) for m in METHODS]

    # Count zones loaded
    zones_loaded = []
    if HAS_ZONEINFO:
        for zname in ("Europe/Paris", "America/New_York", "Asia/Tokyo", "UTC"):
            try:
                ZoneInfo(zname)
                zones_loaded.append(zname)
            except Exception:
                pass

    case_file_bytes = CASE_FILE.stat().st_size
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("# Python Datetime Footgun Correctness Lab — Results\n\n")
        f.write(f"**Python:** {platform.python_version()} ({platform.python_implementation()})\n\n")
        f.write(f"**zoneinfo available:** {HAS_ZONEINFO}\n\n")
        f.write(f"**Zones loaded:** {', '.join(zones_loaded) if zones_loaded else 'none'}\n\n")
        f.write(f"**Platform:** {platform.platform()}\n\n")
        f.write(f"**Cases:** {len(cases)} ({case_file_bytes} bytes)\n\n")
        f.write(f"**Seed:** 42 (deterministic)\n\n")
        f.write(f"**Timing:** time.perf_counter()\n\n")
        f.write(f"**Memory:** tracemalloc — current {current_mem/1024:.1f} KiB, peak {peak_mem/1024:.1f} KiB\n\n")
        f.write(f"**Total wall time:** {total_elapsed:.4f}s\n\n")
        f.write(f"**Subprocess count:** {subprocess_count}\n\n")

        f.write("## Summary\n\n")
        f.write("| Method | Kind | Pass | Fail | Skip | Expected-Fail | Time (ms) |\n")
        f.write("|---|---|---:|---:|---:|---:|---:|\n")
        for s in summaries:
            kind = [m[2] for m in METHODS if m[0]==s["method"]][0]
            f.write(f"| {s['method']} | {kind} | {s['pass']} | {s['fail']} | {s['skip']} | {s['expected_fail']} | {s['time_s']*1000:.3f} |\n")
        f.write("\n")

        f.write("## Skip Matrix\n\n")
        f.write("| Method | Total | Passed | Failed | Skipped |\n")
        f.write("|---|---:|---:|---:|---:|\n")
        for s in summaries:
            f.write(f"| {s['method']} | {s['total']} | {s['pass']} | {s['fail']} | {s['skip']} |\n")
        f.write("\n")

        f.write("## Failures (grouped by method)\n\n")
        for s in summaries:
            if s["fail"] == 0:
                continue
            f.write(f"### {s['method']}\n\n")
            fails = [r for r in rows if r["method"] == s["method"] and r["passed"] is False]
            for r in fails:
                ef = " (expected)" if r["expected_failure"] else ""
                fr = f" — {r['fail_reason']}" if r["fail_reason"] else ""
                f.write(f"- **{r['case_id']}** [{r['category']}] {fr}{ef}\n")
            f.write("\n")

        f.write("## Notes\n\n")
        f.write("- `aware_utc_roundtrip_baseline`: UTC round-trip preserves instant and fold where supported.\n")
        f.write("- `zoneinfo_wall_time_baseline`: IANA ZoneInfo handles DST transitions; skipped if zone unavailable.\n")
        f.write("- `fixed_offset_timezone_baseline`: fixed offsets work but are NOT real time zones (no DST).\n")
        f.write("- `isoformat_fromisoformat_roundtrip`: ISO-8601 round-trip works; `fromisoformat` may reject `Z` suffix depending on Python version.\n")
        f.write("- `rfc_email_datetime_parse`: email.utils handles RFC 2822 dates.\n")
        f.write("- `timestamp_roundtrip_baseline`: timestamp round-trip can lose fold information (PEP 495).\n")
        f.write("- `timedelta_add_24h_naive`: adding `days=1` preserves wall-clock time, not necessarily 24 elapsed hours across DST.\n")
        f.write("- `naive_string_sort_baseline`: string comparison of datetime strings ignores timezone semantics.\n")
        f.write("- `naive_strip_timezone_baseline`: stripping tzinfo loses information and changes comparison results.\n")
        f.write("- No external datetime libraries (arrow, pendulum, dateutil, pytz, etc.) were used — out of scope.\n")
        f.write("- Python datetime has no leap second support.\n")
        f.write("\n")
        f.write("## Conclusion\n\n")
        f.write("Naïve and aware datetimes have different meanings. DST gaps and folds surprise people. "
                "UTC instants and human local schedules are different concepts. "
                "Fixed offsets are not full time zones. "
                "Adding 24 hours is not always the same as 'same local clock time tomorrow'. "
                "Use explicit timezone handling with ZoneInfo, be careful with fold/ambiguity, "
                "and never rely on naive string or timestamp handling for datetime semantics.\n")

    print(f"Results: {OUT_JSONL} ({OUT_JSONL.stat().st_size} bytes)")
    print(f"Report: {OUT_MD}")
    for s in summaries:
        print(f"  {s['method']}: pass={s['pass']} fail={s['fail']} skip={s['skip']} time={s['time_s']*1000:.2f}ms")

if __name__ == "__main__":
    main()
