"""Cross-Skill data correlation and intelligent fusion.

Implements the patent's fusion pipeline:
  1. Multi-dimension correlation (time, spatial, business)
  2. Fusion graph construction
  3. Time/Spatial/Business alignment
  4. Conflict detection and resolution

Usage:
    import sys
    sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')
    from fusion import correlate, fuse, detect_conflicts, resolve_conflicts

    correlations = correlate({"rainfall": rows1, "water-situation": rows2})
    fused = fuse({"rainfall": rows1, "water-situation": rows2}, correlations)
"""

from collections import defaultdict
from datetime import datetime

# ── Business correlation rules ──────────────────────────────────────

BUSINESS_RULES = [
    {"skill1": "rainfall",            "skill2": "water-situation",     "strength": 1.0, "desc": "降雨量变化会影响河道水位"},
    {"skill1": "water-situation",     "skill2": "water-warning",      "strength": 1.0, "desc": "水位超过警戒值会触发防洪预警"},
    {"skill1": "water-quality",       "skill2": "water-warning",      "strength": 1.0, "desc": "水质指标决定水质等级"},
    {"skill1": "water-situation",     "skill2": "water-quality",      "strength": 0.7, "desc": "水位变化可能影响水质"},
    {"skill1": "gate-pump-operation", "skill2": "water-situation",    "strength": 0.9, "desc": "闸门启闭会影响上下游水位"},
    {"skill1": "water-forecast",      "skill2": "water-situation",    "strength": 0.9, "desc": "预测水位与实际水位对比"},
]

# ── Station name normalization ──────────────────────────────────────

_SUFFIXES = ("水位站", "水质站", "水文站", "雨量站", "闸站", "泵站")

def normalize_station(name):
    if not isinstance(name, str):
        return str(name)
    for s in _SUFFIXES:
        if name.endswith(s):
            return name[:-len(s)]
    return name

# ── Time field detection ────────────────────────────────────────────

_TIME_FIELDS = ("tm", "time", "时间", "datetime", "timestamp")
_STATION_FIELDS = ("stnm", "station", "测站", "站名", "name")
_VALUE_FIELDS = {
    "水位": 0.05,
    "流量": 1.0,
    "z": 0.05,
    "溶解氧": 0.5,
    "DO": 0.5,
    "氨氮": 0.1,
    "NH3N": 0.1,
    "降雨": 0.5,
    "降雨量": 0.5,
    "DRP": 0.5,
}
DEFAULT_THRESHOLD = 0.01

TIME_FORMATS = {
    "MINUTE": "%Y-%m-%d %H:%M",
    "HOUR":   "%Y-%m-%d %H:00",
    "DAY":    "%Y-%m-%d",
    "MONTH":  "%Y-%m",
}


def _find_field(row, candidates):
    for c in candidates:
        if c in row:
            return c
    return None


def _parse_time(val):
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return None


# ── Step 1: Correlation identification ──────────────────────────────

def correlate(results):
    """Identify multi-dimensional correlations between skill results.

    Args:
        results: Dict[str, List[dict]] - skill_name -> rows

    Returns:
        Dict with "time", "spatial", "business" correlation lists.
    """
    skills = list(results.keys())
    correlations = {"time": [], "spatial": [], "business": []}

    # Extract metadata from each skill's results
    meta = {}
    for skill, rows in results.items():
        if not rows:
            continue
        time_field = _find_field(rows[0], _TIME_FIELDS)
        station_field = _find_field(rows[0], _STATION_FIELDS)

        times = [_parse_time(r[time_field]) for r in rows if time_field and time_field in r]
        times = [t for t in times if t]
        stations = set()
        if station_field:
            stations = {normalize_station(r[station_field]) for r in rows if station_field in r and r[station_field]}

        meta[skill] = {
            "time_field": time_field,
            "station_field": station_field,
            "time_range": (min(times), max(times)) if times else None,
            "stations": stations,
            "row_count": len(rows),
        }

    # Pairwise correlation
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            si, sj = skills[i], skills[j]
            mi, mj = meta.get(si), meta.get(sj)
            if not mi or not mj:
                continue

            # Time correlation
            ri, rj = mi["time_range"], mj["time_range"]
            if ri and rj:
                overlap_start = max(ri[0], rj[0])
                overlap_end = min(ri[1], rj[1])
                if overlap_start < overlap_end:
                    ri_dur = (ri[1] - ri[0]).total_seconds()
                    rj_dur = (rj[1] - rj[0]).total_seconds()
                    overlap_dur = (overlap_end - overlap_start).total_seconds()
                    strength = overlap_dur / min(ri_dur, rj_dur) if min(ri_dur, rj_dur) > 0 else 0
                    # Determine granularity
                    avg = (ri_dur / max(mi["row_count"], 1) + rj_dur / max(mj["row_count"], 1)) / 2
                    if avg < 600:
                        gran = "MINUTE"
                    elif avg < 7200:
                        gran = "HOUR"
                    elif avg < 172800:
                        gran = "DAY"
                    else:
                        gran = "MONTH"
                    correlations["time"].append({
                        "skills": (si, sj), "strength": round(strength, 3),
                        "overlap": (overlap_start, overlap_end), "granularity": gran,
                    })

            # Spatial correlation
            shared = mi["stations"] & mj["stations"]
            if shared:
                min_count = min(len(mi["stations"]), len(mj["stations"]))
                strength = len(shared) / min_count if min_count > 0 else 0
                correlations["spatial"].append({
                    "skills": (si, sj), "strength": round(strength, 3),
                    "shared_stations": sorted(shared),
                })

    # Business correlation
    skill_set = set(skills)
    for rule in BUSINESS_RULES:
        if rule["skill1"] in skill_set and rule["skill2"] in skill_set:
            correlations["business"].append({
                "skills": (rule["skill1"], rule["skill2"]),
                "strength": rule["strength"],
                "desc": rule["desc"],
            })

    return correlations


# ── Step 2-3: Fusion execution ──────────────────────────────────────

def fuse(results, correlations, strategy="auto"):
    """Fuse multi-skill results using identified correlations.

    Args:
        results: Dict[str, List[dict]] - skill_name -> rows
        correlations: Output from correlate()
        strategy: "time" | "spatial" | "business" | "auto"

    Returns:
        Dict with "data", "strategy_used", "fusion_points".
    """
    skills = list(results.keys())
    if len(skills) <= 1:
        return {"data": results.get(skills[0], []), "strategy_used": "none", "fusion_points": []}

    # Build fusion graph edge weights
    edge_weights = defaultdict(float)
    for c in correlations["time"]:
        edge_weights[tuple(sorted(c["skills"]))] += c["strength"]
    for c in correlations["spatial"]:
        edge_weights[tuple(sorted(c["skills"]))] += c["strength"]
    for c in correlations["business"]:
        edge_weights[tuple(sorted(c["skills"]))] += c["strength"]

    # Pick best strategy based on strongest correlation dimension
    time_max = max((c["strength"] for c in correlations["time"]), default=0)
    spatial_max = max((c["strength"] for c in correlations["spatial"]), default=0)
    business_max = max((c["strength"] for c in correlations["business"]), default=0)

    if strategy == "auto":
        best = max(("time", time_max), ("spatial", spatial_max), ("business", business_max), key=lambda x: x[1])
        strategy = best[0]

    fusion_points = []
    for c in correlations.get(strategy, []):
        fusion_points.append({
            "skills": c["skills"], "strength": c["strength"],
            "type": strategy,
        })

    # Execute fusion
    if strategy == "time" and correlations["time"]:
        fused_data = _fuse_by_time(results, correlations)
    elif strategy == "spatial" and correlations["spatial"]:
        fused_data = _fuse_by_spatial(results, correlations)
    elif strategy == "business" and correlations["business"]:
        fused_data = _fuse_by_business(results, correlations)
    else:
        # Fallback: simple concatenation with skill label
        fused_data = _concat_results(results)

    return {"data": fused_data, "strategy_used": strategy, "fusion_points": fusion_points}


def _fuse_by_time(results, correlations):
    """Time alignment strategy: group by time key, merge matching records."""
    all_rows = []
    for skill, rows in results.items():
        for r in rows:
            r_copy = dict(r)
            r_copy["_source"] = skill
            all_rows.append(r_copy)

    tc = correlations["time"][0] if correlations["time"] else None
    if not tc:
        return all_rows

    granularity = tc.get("granularity", "DAY")
    fmt = TIME_FORMATS.get(granularity, "%Y-%m-%d")

    # Group by time key
    groups = defaultdict(list)
    time_field_cache = {}
    for r in all_rows:
        skill = r["_source"]
        if skill not in time_field_cache:
            time_field_cache[skill] = _find_field(r, _TIME_FIELDS)
        tf = time_field_cache[skill]
        if tf and tf in r:
            t = _parse_time(r[tf])
            if t:
                key = t.strftime(fmt)
                groups[key].append(r)

    # Merge groups
    fused = []
    for key in sorted(groups.keys()):
        merged = {"时间": key}
        for r in groups[key]:
            for k, v in r.items():
                if k not in merged and k != "_source":
                    if k not in merged:
                        merged[k] = v
                    elif isinstance(v, (int, float)) and isinstance(merged[k], (int, float)):
                        merged[k] = max(merged[k], v)  # keep latest/highest
        merged["_sources"] = list({r["_source"] for r in groups[key]})
        fused.append(merged)
    return fused


def _fuse_by_spatial(results, correlations):
    """Spatial alignment: group by normalized station, then by time."""
    all_rows = []
    for skill, rows in results.items():
        for r in rows:
            r_copy = dict(r)
            r_copy["_source"] = skill
            all_rows.append(r_copy)

    station_field_cache = {}
    normalized = []
    for r in all_rows:
        skill = r["_source"]
        if skill not in station_field_cache:
            station_field_cache[skill] = _find_field(r, _STATION_FIELDS)
        sf = station_field_cache[skill]
        r["_station"] = normalize_station(r[sf]) if sf and sf in r else None
        normalized.append(r)

    # Group by station
    by_station = defaultdict(list)
    for r in normalized:
        if r["_station"]:
            by_station[r["_station"]].append(r)

    fused = []
    for station, rows in sorted(by_station.items()):
        merged = {"测站": station, "data_count": len(rows)}
        for r in rows:
            for k, v in r.items():
                if k not in ("_source", "_station") and k not in merged:
                    merged[k] = v
        merged["_sources"] = list({r["_source"] for r in rows})
        fused.append(merged)
    return fused


def _fuse_by_business(results, correlations):
    """Business logic fusion: apply causal rules and annotate."""
    fused_data = _concat_results(results)
    annotations = []
    for bc in correlations["business"]:
        annotations.append(f"[业务关联] {bc['desc']} (关联强度: {bc['strength']})")
    if fused_data and annotations:
        fused_data[0]["_business_annotations"] = annotations
    return fused_data


def _concat_results(results):
    """Simple concatenation with skill label."""
    all_rows = []
    for skill, rows in results.items():
        for r in rows:
            r_copy = dict(r)
            r_copy["_source"] = skill
            all_rows.append(r_copy)
    return all_rows


# ── Step 4: Conflict detection and resolution ───────────────────────

def detect_conflicts(fused_data):
    """Detect value conflicts in fused data.

    Returns list of conflicts with field, values, difference, threshold.
    """
    if not fused_data:
        return []

    conflicts = []
    # Group by time+station to find overlapping records
    groups = defaultdict(list)
    for r in fused_data:
        key = (r.get("时间", ""), r.get("测站", r.get("_station", "")))
        groups[key].append(r)

    for key, records in groups.items():
        if len(records) < 2:
            continue
        all_fields = set()
        for r in records:
            all_fields.update(k for k in r if not k.startswith("_"))

        for field in all_fields:
            values = [r[field] for r in records if field in r and isinstance(r[field], (int, float))]
            if len(values) < 2:
                continue
            diff = max(values) - min(values)
            threshold = _VALUE_FIELDS.get(field, DEFAULT_THRESHOLD)
            for name, thresh in _VALUE_FIELDS.items():
                if name in field:
                    threshold = thresh
                    break
            if diff > threshold:
                conflicts.append({
                    "field": field, "values": values,
                    "difference": round(diff, 4), "threshold": threshold,
                    "severity": "HIGH" if diff > threshold * 3 else "MEDIUM",
                })
    return conflicts


def resolve_conflicts(fused_data, conflicts, strategy="latest"):
    """Resolve detected conflicts in fused data.

    Args:
        fused_data: List of dicts from fuse()
        conflicts: List from detect_conflicts()
        strategy: "latest" | "average" | "priority"

    Returns:
        Tuple of (resolved_data, resolution_log).
    """
    if not conflicts:
        return fused_data, []

    log = []
    for conflict in conflicts:
        field = conflict["field"]
        values = conflict["values"]

        if strategy == "average":
            resolved = round(sum(values) / len(values), 2)
        elif strategy == "max":
            resolved = max(values)
        elif strategy == "min":
            resolved = min(values)
        else:  # latest
            resolved = values[-1]

        log.append({
            "field": field, "strategy": strategy,
            "original": values, "resolved": resolved,
            "reason": f"{strategy}: {values} -> {resolved}",
        })

        # Apply resolution
        for r in fused_data:
            if field in r and isinstance(r[field], (int, float)):
                if r[field] in values:
                    r[field] = resolved

    return fused_data, log
