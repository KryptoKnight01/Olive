from __future__ import annotations

import json
from datetime import UTC, datetime

from olive.smoke.multistrategy import PAPER_STRATEGIES, make_alert_payload


def test_multistrategy_payloads_are_fresh_unique_and_valid() -> None:
    now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)

    generated = [make_alert_payload(strategy, "s" * 32, now) for strategy in PAPER_STRATEGIES]
    payloads = [json.loads(body) for body, _external_id in generated]

    assert {payload["strategy_id"] for payload in payloads} == {"OLM", "OLB"}
    assert len({payload["signal_id"] for payload in payloads}) == 2
    assert all(payload["timestamp"] == "2026-09-02T12:00:00+00:00" for payload in payloads)
    assert all(payload["environment"] == "staging" for payload in payloads)
    assert all(payload["expiry_seconds"] == 300 for payload in payloads)
    assert all(payload["webhook_secret"] == "s" * 32 for payload in payloads)
