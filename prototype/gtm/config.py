"""Versioned GTM configuration: signal contracts, scoring weights, routing rules.

Everything a revenue leader might want to change lives here, not in code.
In production this file is reviewed like code (PR + changelog) and every run
stamps the CONFIG_VERSION on the records it writes.
"""
from datetime import date

CONFIG_VERSION = "2026.11.0"
RUN_DATE = date(2026, 11, 23)  # fixed so the demo is reproducible

# --------------------------------------------------------------------------
# Signal contracts. Each signal states what it is, how strong it is on its
# own, how fast it decays (half-life in days), which motion may use it and
# when it must NOT trigger action.
# --------------------------------------------------------------------------
SIGNALS = {
    # Prospect timing signals (third party)
    "new_finance_leader": dict(label="New CFO / VP Finance", strength=30, half_life=90,
                               motion="new_logo", source="UserGems / job-change feed",
                               owner="GTM Eng", suppress_if=["open_opportunity"]),
    "hiring_travel_or_ap": dict(label="Hiring travel manager or AP clerk", strength=25, half_life=45,
                                motion="new_logo", source="PredictLeads job postings",
                                owner="GTM Eng", suppress_if=["open_opportunity"]),
    "funding_round": dict(label="Raised a funding round", strength=20, half_life=60,
                          motion="new_logo", source="Funding news feed",
                          owner="GTM Eng", suppress_if=[]),
    "new_office_or_country": dict(label="New office or country entry", strength=22, half_life=120,
                                  motion="new_logo", source="Claygent web research",
                                  owner="GTM Eng", suppress_if=[]),
    "competitor_renewal_window": dict(label="Incumbent T&E contract renews < 6 months", strength=35, half_life=60,
                                      motion="new_logo", source="Tech-stack data + rep notes",
                                      owner="RevOps", suppress_if=["open_opportunity"]),
    "intent_spend_mgmt": dict(label="Third-party intent: spend management", strength=15, half_life=21,
                              motion="new_logo", source="Bombora / 6sense",
                              owner="Marketing Ops", suppress_if=[]),
    # First-party signals (Perk owns these, competitors don't)
    "pricing_page_visit": dict(label="Visited pricing page (known account)", strength=18, half_life=7,
                               motion="any", source="Website reverse-IP",
                               owner="Marketing Ops", suppress_if=[]),
    "demo_request": dict(label="Requested a demo", strength=60, half_life=3,
                         motion="inbound", source="Web form",
                         owner="Marketing Ops", suppress_if=[]),
    # Customer signals for Account Management
    "travel_only_high_spend": dict(label="Travel customer, no Spend module, high T&E volume", strength=30, half_life=180,
                                   motion="expansion", source="Perk product data (Snowflake)",
                                   owner="AM leadership", suppress_if=["open_opportunity"]),
    "headcount_growth": dict(label="Headcount +20% in 12 months", strength=15, half_life=120,
                             motion="expansion", source="Enrichment",
                             owner="GTM Eng", suppress_if=[]),
    "bookings_drop": dict(label="Bookings down > 30% vs prior 90 days", strength=35, half_life=45,
                          motion="retention", source="Perk product data (Snowflake)",
                          owner="AM leadership", suppress_if=[]),
    "champion_left": dict(label="Champion / admin left the company", strength=30, half_life=60,
                          motion="retention", source="UserGems / job-change feed",
                          owner="AM leadership", suppress_if=[]),
    "support_escalations": dict(label="3+ support escalations in 30 days", strength=20, half_life=30,
                                motion="retention", source="Zendesk",
                                owner="CX Ops", suppress_if=[]),
}

# --------------------------------------------------------------------------
# Fit model. Two products, two fit scores. Fit and timing stay in separate
# fields: fit changes slowly, timing decays in weeks.
# --------------------------------------------------------------------------
TRAVEL_INTENSIVE = {"Consulting", "Construction", "Engineering", "Pharma", "Media & Events",
                    "Software", "Energy", "Logistics"}
LOW_TRAVEL = {"Retail", "Hospitality"}

FIT_WEIGHTS = {
    # Company size: Perk's SMB / mid-market core
    "employees_core": 30,        # 200-1,500
    "employees_edge": 22,        # 100-200 or 1,500-2,500
    "employees_ok": 10,          # 50-100 or 2,500-10,000
    # Travel fit
    "travel_industry": 25,       # half for neutral industries, 0 for low-travel ones
    "multi_country_3plus": 8,
    "multi_country_5plus": 15,
    "no_tool": 20,               # Excel / paper / nothing: pain is obvious
    "legacy_tool": 12,           # Concur, Expensify: switch story
    "modern_competitor": 4,      # Navan, Ramp: hard displacement
    # Spend fit
    "spend_no_tool": 30,
    "spend_legacy_tool": 20,
    "spend_field_industry": 10,
}

PRIORITY_WEIGHTS = {"fit": 0.55, "timing": 0.45}

TIERS = [  # evaluated top-down
    ("P1", dict(min_fit=65, min_timing=40)),
    ("P2", dict(min_fit=55, min_timing=25)),
    ("P3", dict(min_fit=40, min_timing=0)),
]

# Rules of Engagement: who owns an account.
# Global accounts (large or multi-country) go to the Global pod, the rest to the regional pod.
GLOBAL_ACCOUNT_RULE = dict(min_employees=2000, min_countries=6)

# Routing
SDR_CAPACITY_PER_RUN = 2        # new accounts a single SDR pod can absorb per run
AI_CONFIDENCE_FLOOR = 0.70      # below this, the brief goes to a human review queue
RECONTACT_COOLDOWN_DAYS = 14

# Enrichment waterfall: cheapest good source first. Costs are in credits.
WATERFALL = [
    dict(name="provider_a", label="Provider A (low-cost, Apollo-like)", cost=1),
    dict(name="provider_b", label="Provider B (EU-strong, Cognism-like)", cost=3),
    dict(name="provider_c", label="Provider C (premium, ZoomInfo-like)", cost=6),
]
EMAIL_VERIFY_COST = 0.5
