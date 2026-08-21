from __future__ import annotations

import json
import logging

from olive.logging import JsonFormatter


def test_json_formatter_emits_machine_readable_context() -> None:
    record = logging.LogRecord(
        name="olive.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="health_checked",
        args=(),
        exc_info=None,
    )
    record.environment = "testing"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "health_checked"
    assert payload["context"]["environment"] == "testing"
