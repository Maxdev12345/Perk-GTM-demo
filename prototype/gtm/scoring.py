"""Fit, timing and priority scoring.

Fit (slow-moving, who should buy) and timing (fast-decaying, why now) are
computed separately and stored in separate CRM fields. Priority combines them.
"""
from . import config



def _employee_points(n):
    w = config.FIT_WEIGHTS
    if n is None:
        return 0
    if 200 <= n <= 1500:
        return w["employees_core"]
    if 100 <= n < 200 or 1500 < n <= 2500:
        return w["employees_edge"]
    if 50 <= n < 100 or 2500 < n <= 10000:
        return w["employees_ok"]
    return 0


def _country_points(c):
    w = config.FIT_WEIGHTS
    return w["multi_country_5plus"] if c >= 5 else (w["multi_country_3plus"] if c >= 3 else 0)


def fit_travel(acc: dict) -> int:
    w = config.FIT_WEIGHTS
    pts = _employee_points(acc.get("employees"))
    if acc["industry"] in config.TRAVEL_INTENSIVE:
        pts += w["travel_industry"]
    elif acc["industry"] not in config.LOW_TRAVEL:
        pts += w["travel_industry"] // 2
    pts += _country_points(acc.get("countries", 1))
    tool = acc.get("current_tool", "").lower()
    if any(t in tool for t in ("excel", "none", "paper")):
        pts += w["no_tool"]
    elif any(t in tool for t in ("concur", "expensify")):
        pts += w["legacy_tool"]
    elif "navan" in tool:
        pts += w["modern_competitor"]
    return min(100, pts)


def fit_spend(acc: dict) -> int:
    w = config.FIT_WEIGHTS
    pts = _employee_points(acc.get("employees"))
    tool = acc.get("current_tool", "").lower()
    if any(t in tool for t in ("excel", "none", "paper")):
        pts += w["spend_no_tool"]       # no formal spend tool: biggest pain
    elif any(t in tool for t in ("concur", "expensify")):
        pts += w["spend_legacy_tool"]   # legacy expense tool: switch candidate
    elif "ramp" in tool:
        pts += w["modern_competitor"]
    pts += _country_points(acc.get("countries", 1))  # multi-entity, multi-currency
    if acc["industry"] in config.TRAVEL_INTENSIVE:
        pts += w["spend_field_industry"]  # field spend, per diems
    return min(100, pts)


def decayed(strength: float, days_ago: float, half_life: float) -> float:
    return strength * 0.5 ** (days_ago / half_life)


def timing(acc: dict, motion_filter=None):
    """Return (timing score 0-100, list of active signals with decayed weight, suppressed list)."""
    active, suppressed, total = [], [], 0.0
    for s in acc.get("signals", []):
        spec = config.SIGNALS[s["type"]]
        if motion_filter and spec["motion"] not in motion_filter:
            continue
        if acc.get("open_opportunity") and "open_opportunity" in spec["suppress_if"]:
            suppressed.append({**s, "reason": "open opportunity already exists"})
            continue
        w = decayed(spec["strength"], s["days_ago"], spec["half_life"])
        total += w
        active.append({**s, "label": spec["label"], "source": spec["source"],
                       "weight": round(w, 1), "strength": spec["strength"]})
    active.sort(key=lambda x: -x["weight"])
    return min(100, round(total)), active, suppressed


def tier(fit: float, timing_score: float) -> str:
    for name, rule in config.TIERS:
        if fit >= rule["min_fit"] and timing_score >= rule["min_timing"]:
            return name
    return "P4"


def score(acc: dict) -> dict:
    ft, fs = fit_travel(acc), fit_spend(acc)
    if acc.get("is_customer"):
        motions = {"expansion", "retention", "any"}
    else:
        motions = {"new_logo", "inbound", "any"}
    t, active, suppressed = timing(acc, motions)
    fit = max(ft, fs)
    pw = config.PRIORITY_WEIGHTS
    priority = round(pw["fit"] * fit + pw["timing"] * t)
    if ft >= 60 and fs >= 60:
        angle = "Travel + Spend bundle"
    elif ft >= fs:
        angle = "Travel-led"
    else:
        angle = "Spend-led"
    return {"fit_travel": ft, "fit_spend": fs, "fit": fit, "timing": t, "priority": priority,
            "tier": tier(fit, t), "product_angle": angle,
            "active_signals": active, "suppressed_signals": suppressed}
