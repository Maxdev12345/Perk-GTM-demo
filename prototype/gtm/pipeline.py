"""End-to-end run: source -> enrich -> score -> decide -> brief -> write back.

Run:  python -m gtm.pipeline            (from the prototype folder)
      python -m gtm.pipeline --reset    (forget processed actions)
"""
import argparse
import hashlib
import json
import pathlib
import time

from . import brief, config, enrich, routing, scoring
from .demo_data import ACCOUNTS

OUT = pathlib.Path(__file__).resolve().parent.parent / "out"
STATE = OUT / "processed_actions.json"

# Assumptions for the time-back estimate (minutes of manual work replaced per record)
MANUAL_MINUTES = {"research": 25, "crm_entry": 5, "account_plan": 40}


def action_id(acc: dict, play: str, signals: list) -> str:
    """Stable key: the same account + play + signal set never creates a second task."""
    key = "|".join([acc["id"], play, ",".join(sorted(f"{s['type']}@{s['days_ago']}" for s in signals)),
                    config.CONFIG_VERSION])
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def crm_payload(acc: dict, s: dict, d: dict) -> dict:
    """What gets written to Salesforce (Account object). Custom fields are illustrative."""
    return {
        "object": "Account",
        "match_on": {"Website": acc["domain"]},
        "fields": {
            "GTM_Fit_Travel__c": s["fit_travel"],
            "GTM_Fit_Spend__c": s["fit_spend"],
            "GTM_Timing_Score__c": s["timing"],
            "GTM_Priority_Tier__c": s["tier"],
            "GTM_Top_Signal__c": s["active_signals"][0]["label"] if s["active_signals"] else None,
            "GTM_Play__c": d["play"],
            "GTM_Brief_Confidence__c": d["brief"]["confidence"],
            "GTM_Config_Version__c": config.CONFIG_VERSION,
        },
        "task": None if d["play"] in ("no_action", "hold_cooldown", "marketing_nurture") else {
            "Subject": f"[{s['tier']}] {routing.PLAYS[d['play']]['label']}",
            "Owner": routing.PLAYS[d["play"]]["owner"],
            "External_Id__c": d["action_id"],   # idempotency key used as upsert key
        },
    }


def run(reset: bool = False) -> dict:
    t0 = time.perf_counter()
    OUT.mkdir(exist_ok=True)
    processed = set() if reset or not STATE.exists() else set(json.loads(STATE.read_text()))

    decisions, exceptions = [], []
    for raw in ACCOUNTS:
        acc = enrich.enrich(raw)
        if not acc.get("employees"):
            exceptions.append({"id": acc["id"], "reason": "employees not found after waterfall"})
        s = scoring.score(acc)
        play = routing.choose_play(acc, s)
        decisions.append({"account": acc, "scores": s, "play": play, "routing_notes": []})

    routing.apply_capacity(decisions)

    new_actions = dupes = 0
    for d in decisions:
        acc, s = d["account"], d["scores"]
        d["action_id"] = action_id(acc, d["play"], s["active_signals"])
        d["brief"] = brief.generate(acc, s, d["play"])
        d["duplicate"] = d["action_id"] in processed
        if d["play"] not in ("no_action", "hold_cooldown"):
            if d["duplicate"]:
                dupes += 1
            else:
                new_actions += 1
                processed.add(d["action_id"])
        d["crm_payload"] = crm_payload(acc, s, d)
        d["play_meta"] = routing.PLAYS[d["play"]]

    STATE.write_text(json.dumps(sorted(processed), indent=1))

    # ---- run metrics: commercial + reliability, side by side ----
    prospects = [d for d in decisions if not d["account"].get("is_customer")]
    contacts = [d["account"].get("finance_contact") for d in prospects]
    found = [c for c in contacts if c]
    verified = [c for c in found if c.get("email_status") == "valid"]
    credits = sum(d["account"]["enrichment"]["credits"] for d in decisions)
    actioned = [d for d in decisions if d["play"] not in ("no_action", "hold_cooldown")]
    minutes = 0
    for d in actioned:
        minutes += MANUAL_MINUTES["crm_entry"]
        minutes += MANUAL_MINUTES["account_plan"] if d["account"].get("is_customer") else MANUAL_MINUTES["research"]
    by_play = {}
    for d in decisions:
        by_play[d["play"]] = by_play.get(d["play"], 0) + 1

    metrics = {
        "records_in": len(decisions),
        "contact_coverage_pct": round(100 * len(found) / max(1, len(prospects))),
        "verified_email_pct": round(100 * len(verified) / max(1, len(prospects))),
        "credits_spent": round(credits, 1),
        "credits_per_verified_contact": round(credits / max(1, len(verified)), 1),
        "actions_created": new_actions,
        "duplicates_skipped": dupes,
        "needs_human_review": sum(1 for d in decisions if d["brief"]["needs_review"]),
        "suppressed_signals": sum(len(d["scores"]["suppressed_signals"]) for d in decisions),
        "exceptions": exceptions,
        "manual_minutes_replaced": minutes,
        "by_play": by_play,
        "runtime_ms": round(1000 * (time.perf_counter() - t0)),
    }
    result = {"config_version": config.CONFIG_VERSION, "run_date": config.RUN_DATE.isoformat(),
              "metrics": metrics, "signals_catalog": config.SIGNALS, "plays": routing.PLAYS,
              "decisions": decisions}
    (OUT / "run_output.json").write_text(json.dumps(result, indent=1, default=str))
    return result


def _print(result: dict) -> None:
    m = result["metrics"]
    print(f"GTM run {result['run_date']} | config {result['config_version']}")
    print(f"{'ID':8} {'Account':26} {'FitT':>4} {'FitS':>4} {'Tim':>4} {'Pri':>4} Tier  Play")
    for d in sorted(result["decisions"], key=lambda d: -d["scores"]["priority"]):
        a, s = d["account"], d["scores"]
        flag = " (dup)" if d["duplicate"] else ""
        review = " [review]" if d["brief"]["needs_review"] else ""
        print(f"{a['id']:8} {a['name'][:26]:26} {s['fit_travel']:4} {s['fit_spend']:4} {s['timing']:4} "
              f"{s['priority']:4} {s['tier']:5} {d['play']}{review}{flag}")
    print("\nMetrics:", json.dumps({k: v for k, v in m.items() if k != "by_play"}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="forget processed actions before running")
    _print(run(reset=ap.parse_args().reset))
