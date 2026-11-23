"""Orchestration: which record enters which play, owned by whom, on what criteria.

This is the decision layer. It is plain, testable code on purpose: the rules a
Sales VP will challenge must be readable, versioned and explainable per record.
"""
from . import config

PLAYS = {
    "inbound_speed_to_lead": dict(label="Inbound speed-to-lead", owner="AE (round-robin, region)", sla="5 min",
                                  human_in_loop=False),
    "signal_outbound_sdr": dict(label="Signal-based outbound (human SDR)", owner="SDR pod", sla="24 h",
                                human_in_loop=True),
    "ai_sdr_supervised": dict(label="AI SDR sequence, human-approved", owner="AI SDR agent + SDR reviewer",
                              sla="48 h", human_in_loop=True),
    "deal_signal_to_ae": dict(label="Live-deal signal to AE owner", owner="Opportunity owner (AE)", sla="24 h",
                              human_in_loop=False),
    "marketing_nurture": dict(label="Marketing nurture", owner="Marketing automation", sla="weekly",
                              human_in_loop=False),
    "am_cross_sell_spend": dict(label="Cross-sell Spend to Travel customer", owner="Account Manager", sla="5 days",
                                human_in_loop=True),
    "am_save_play": dict(label="Churn-risk save play", owner="Account Manager + CSM", sla="48 h",
                         human_in_loop=True),
    "am_expansion_watch": dict(label="Expansion watch (seat growth)", owner="Account Manager", sla="next QBR",
                               human_in_loop=False),
    "hold_cooldown": dict(label="Hold: contacted recently", owner="None", sla="-", human_in_loop=False),
    "no_action": dict(label="No action (low fit and no timing)", owner="None", sla="-", human_in_loop=False),
}


def choose_play(acc: dict, s: dict) -> str:
    types = {x["type"] for x in s["active_signals"]}
    if acc.get("is_customer"):
        if types & {"bookings_drop", "champion_left", "support_escalations"}:
            return "am_save_play"
        if "travel_only_high_spend" in types and "Spend" not in acc.get("products", []):
            return "am_cross_sell_spend"
        if types:
            return "am_expansion_watch"
        return "no_action"
    if "demo_request" in types:
        return "inbound_speed_to_lead"
    if acc.get("open_opportunity"):
        return "deal_signal_to_ae"
    if acc.get("last_contacted_days") is not None and acc["last_contacted_days"] < config.RECONTACT_COOLDOWN_DAYS:
        return "hold_cooldown"
    if s["tier"] == "P1":
        return "signal_outbound_sdr"
    if s["tier"] == "P2":
        return "ai_sdr_supervised"
    if s["tier"] == "P3":
        return "marketing_nurture"
    return "no_action"


def apply_capacity(decisions: list) -> list:
    """SDR capacity guard: overflow P1 accounts go to the supervised AI SDR
    instead of sitting unworked in a rep's queue (which shows up later as 'low
    conversion' rather than 'unworked')."""
    by_region = {}
    for d in sorted(decisions, key=lambda d: -d["scores"]["priority"]):
        if d["play"] != "signal_outbound_sdr":
            continue
        region = d["account"]["region"]
        by_region[region] = by_region.get(region, 0) + 1
        if by_region[region] > config.SDR_CAPACITY_PER_RUN:
            d["play"] = "ai_sdr_supervised"
            d["routing_notes"].append(f"SDR pod {region} at capacity -> overflow to supervised AI SDR")
    return decisions
