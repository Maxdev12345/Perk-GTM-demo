from gtm import config, enrich, routing, scoring
from gtm.demo_data import ACCOUNTS
from gtm.pipeline import action_id, run


def _acc(id_):
    return enrich.enrich(next(a for a in ACCOUNTS if a["id"] == id_))


def test_decay_halves_at_half_life():
    assert scoring.decayed(40, 30, 30) == 20


def test_fresh_signal_beats_stale_signal():
    fresh = scoring.decayed(20, 1, 7)
    stale = scoring.decayed(20, 30, 7)
    assert fresh > 5 * stale


def test_open_opportunity_suppresses_outbound_signals():
    acc = _acc("ACC-007")
    s = scoring.score(acc)
    assert any(x["type"] == "new_finance_leader" for x in s["suppressed_signals"])
    assert routing.choose_play(acc, s) == "deal_signal_to_ae"


def test_recently_contacted_is_held():
    acc = _acc("ACC-008")
    assert routing.choose_play(acc, scoring.score(acc)) == "hold_cooldown"


def test_demo_request_goes_straight_to_ae():
    acc = _acc("ACC-014")
    assert routing.choose_play(acc, scoring.score(acc)) == "inbound_speed_to_lead"


def test_churn_signal_wins_over_expansion():
    acc = _acc("CUS-102")
    assert routing.choose_play(acc, scoring.score(acc)) == "am_save_play"


def test_waterfall_stops_at_first_hit_and_logs_cost():
    acc = _acc("ACC-002")
    log = acc["enrichment"]["log"]
    hits = [l for l in log if l.startswith("employees: hit")]
    assert len(hits) == 1
    assert acc["enrichment"]["credits"] > 0


def test_action_id_is_stable_and_rerun_creates_no_duplicates():
    acc = _acc("ACC-001")
    s = scoring.score(acc)
    assert action_id(acc, "x", s["active_signals"]) == action_id(acc, "x", s["active_signals"])
    first = run(reset=True)["metrics"]
    second = run()["metrics"]
    assert first["actions_created"] > 0
    assert second["actions_created"] == 0
    assert second["duplicates_skipped"] == first["actions_created"]


def test_tiers_respect_thresholds():
    assert scoring.tier(70, 50) == "P1"
    assert scoring.tier(70, 10) == "P3"
    assert scoring.tier(30, 90) == "P4"


def test_every_signal_has_a_contract():
    for spec in config.SIGNALS.values():
        assert {"strength", "half_life", "motion", "source", "owner", "suppress_if"} <= spec.keys()
