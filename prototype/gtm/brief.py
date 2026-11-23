"""Account brief generation: the artefact a rep actually sees.

Two engines with one output contract (BRIEF_SCHEMA):
  * "template": deterministic, free, used offline and as the fallback
  * "claude":   an LLM call with structured output, used when an API key and
                the anthropic SDK are available (set GTM_BRIEF_ENGINE=claude)

Every brief carries a confidence score. Below config.AI_CONFIDENCE_FLOOR it is
routed to a human review queue instead of straight to the rep or sequence.
"""
import json
import os

from . import config

BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "why_now": {"type": "string"},
        "angle": {"type": "string"},
        "opener": {"type": "string"},
        "discovery_questions": {"type": "array", "items": {"type": "string"}},
        "next_step": {"type": "string"},
    },
    "required": ["why_now", "angle", "opener", "discovery_questions", "next_step"],
    "additionalProperties": False,
}

_PROOF = {
    "Travel-led": "teams like yours cut booking time and keep every trip in policy without chasing approvals",
    "Spend-led": "finance teams close expenses with 90% of reports processed with zero human touch",
    "Travel + Spend bundle": "one policy layer and one data layer across trips, cards and expenses",
}


def confidence(acc: dict, s: dict) -> float:
    c = 0.45
    c += min(0.25, 0.1 * len(s["active_signals"]))
    contact = acc.get("finance_contact")
    if acc.get("is_customer"):
        c += 0.2
    elif contact:
        c += {"valid": 0.2, "catch_all": 0.05, "invalid": -0.1}.get(contact.get("email_status"), 0)
    if acc["enrichment"]["sources"].get("employees", "crm") is None:
        c -= 0.1
    return round(max(0.0, min(0.95, c)), 2)


def template_brief(acc: dict, s: dict, play: str) -> dict:
    top = s["active_signals"][:2]
    why = "; ".join(f"{x['label']} ({x['days_ago']}d ago): {x['evidence']}" for x in top) or "No active signal"
    contact = acc.get("finance_contact") or {"name": "the account owner", "title": ""}
    first = contact["name"].split()[0]
    if play == "am_save_play":
        return dict(
            why_now=why,
            angle="Retention risk: re-establish an owner and show value delivered",
            opener=f"Book a value review with {acc['name']}: savings, policy compliance and hours saved this year.",
            discovery_questions=["Who now owns travel admin after the change?",
                                 "What changed in your travel volume this quarter?",
                                 "Which reconciliation issues are still open?"],
            next_step="AM + CSM call within 48h; CSM fixes open escalations first",
        )
    if play == "am_cross_sell_spend":
        return dict(
            why_now=why,
            angle="Bring expenses onto the same platform their travel already runs on",
            opener=(f"{acc['name']} already books ~EUR {acc.get('annual_travel_spend_eur', 0):,.0f} of travel on Perk; "
                    "the receipts, per diems and card spend behind those trips are still handled elsewhere."),
            discovery_questions=["How do you reconcile travel invoices with expenses today?",
                                 "How many hours a month does finance spend on expense reports?",
                                 "When does your current expense tool renew?"],
            next_step="AM sends a 1-page ROI estimate built from their own Perk booking data",
        )
    return dict(
        why_now=why,
        angle=f"{s['product_angle']}: {_PROOF[s['product_angle']]}",
        opener=(f"Hi {first}, I noticed: {top[0]['evidence'] if top else 'your team is growing'}. "
                f"Companies at {acc['name']}'s stage usually hit the point where travel and expenses outgrow "
                f"{acc.get('current_tool', 'spreadsheets')}. Worth 20 minutes?"),
        discovery_questions=["How are trips booked and approved today?",
                             "How long does month-end expense close take?",
                             "Who owns travel policy, and how is it enforced?"],
        next_step="Discovery call; SDR attaches this brief to the meeting invite",
    )


def claude_brief(acc: dict, s: dict, play: str) -> dict:
    import anthropic  # optional dependency

    client = anthropic.Anthropic()
    context = {
        "account": {k: acc.get(k) for k in ("name", "industry", "employees", "countries", "region",
                                            "current_tool", "products", "annual_travel_spend_eur")},
        "contact": acc.get("finance_contact"),
        "signals": s["active_signals"],
        "product_angle": s["product_angle"],
        "play": play,
    }
    response = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=2000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": BRIEF_SCHEMA}},
        system=("You write account briefs for Perk sellers (travel + spend management). Use only the facts "
                "in the context. No invented numbers or names. Opener under 60 words, plain and specific."),
        messages=[{"role": "user", "content": json.dumps(context)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("model declined")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def generate(acc: dict, s: dict, play: str) -> dict:
    engine = os.getenv("GTM_BRIEF_ENGINE", "template")
    used = "template"
    if engine == "claude":
        try:
            brief = claude_brief(acc, s, play)
            used = "claude"
        except Exception as exc:  # fall back, never block the run
            brief = template_brief(acc, s, play)
            brief["engine_error"] = str(exc)[:120]
    else:
        brief = template_brief(acc, s, play)
    conf = confidence(acc, s)
    brief.update(engine=used, confidence=conf, needs_review=conf < config.AI_CONFIDENCE_FLOOR)
    return brief
