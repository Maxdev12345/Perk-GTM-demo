"""Enrichment waterfall with mocked providers.

Real providers are replaced by deterministic mocks (hash-based coverage) so the
demo is reproducible offline. The waterfall logic is the production logic:
ask the cheapest source first, pay the next one only on a miss, verify every
email before it is used, and record source + cost for every field.
"""
import hashlib

from . import config

# Mock "provider universe": the values a provider would return when it has
# coverage. Only used for fields missing in the CRM.
_TRUE_EMPLOYEES = {"ACC-002": 1150, "ACC-006": 380, "ACC-010": 950}

_FIRST = ["Lucia", "Marco", "Hannah", "Pieter", "Chloe", "Rahul", "Sofia", "Daniel", "Ines", "Oliver",
          "Mei", "Tomas", "Grace", "Jonas", "Amara", "Leo", "Nora", "Felix", "Elena"]
_LAST = ["Ortega", "Bianchi", "Becker", "de Vries", "Martin", "Shah", "Lindqvist", "Brooks", "Navarro",
         "Hughes", "Chen", "Novak", "Okafor", "Keller", "Moreau", "Ricci", "Haugen", "Price", "Silva"]
_TITLES = ["CFO", "VP Finance", "Head of Finance Operations", "Finance Director", "Controller"]

# Coverage by provider and region, in percent (mocked).
_COVERAGE = {
    "provider_a": {"EMEA": 45, "NA": 70},
    "provider_b": {"EMEA": 80, "NA": 45},
    "provider_c": {"EMEA": 85, "NA": 90},
}


def _h(*parts) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest(), 16)


def _provider_has(provider: str, account: dict, field: str) -> bool:
    return _h(provider, account["domain"], field) % 100 < _COVERAGE[provider][account["region"]]


def _contact_for(account: dict) -> dict:
    n = _h(account["domain"], "contact")
    first, last = _FIRST[n % len(_FIRST)], _LAST[(n // 7) % len(_LAST)]
    title = _TITLES[(n // 13) % len(_TITLES)]
    if account["employees"] and account["employees"] < 400 and title == "CFO":
        title = "Head of Finance"
    email = f"{first.lower()}.{last.lower().replace(' ', '')}@{account['domain']}"
    return {"name": f"{first} {last}", "title": title, "email": email}


def _verify_email(email: str) -> str:
    r = _h(email, "verify") % 100
    return "valid" if r < 82 else ("catch_all" if r < 94 else "invalid")


def enrich(account: dict) -> dict:
    """Return enrichment result: fields found, per-field source, cost and a log."""
    acc = dict(account)
    log, cost, sources = [], 0.0, {}

    wanted = []
    if not acc.get("employees"):
        wanted.append("employees")
    if not acc.get("is_customer"):
        wanted.append("finance_contact")

    for field in wanted:
        for step in config.WATERFALL:
            cost += step["cost"]
            if _provider_has(step["name"], acc, field):
                if field == "employees":
                    acc["employees"] = _TRUE_EMPLOYEES.get(acc["id"], 500)
                else:
                    acc["finance_contact"] = _contact_for(acc)
                sources[field] = step["name"]
                log.append(f"{field}: hit on {step['name']} (+{step['cost']} cr)")
                break
            log.append(f"{field}: miss on {step['name']} (+{step['cost']} cr)")
        else:
            sources[field] = None
            log.append(f"{field}: not found after full waterfall -> exception queue")

    if acc.get("finance_contact"):
        cost += config.EMAIL_VERIFY_COST
        status = _verify_email(acc["finance_contact"]["email"])
        acc["finance_contact"]["email_status"] = status
        log.append(f"email verification: {status} (+{config.EMAIL_VERIFY_COST} cr)")

    acc["enrichment"] = {"sources": sources, "credits": round(cost, 2), "log": log}
    return acc
