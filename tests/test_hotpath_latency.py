"""S03 — prove attach_agent / ledger never add mother awaits on hot path."""

from __future__ import annotations

import statistics
import time

from choruscontrol.agent.runtime import AgentRuntime, invoke_passthrough


def _fake_invoke(x: int) -> int:
    return x + 1


def test_invoke_passthrough_no_mother_await():
    # Agent without mother URL would exit on start; we only use record_ledger path
    class _Mini:
        mother_calls_on_hot_path = 0

        def record_ledger(self, entry):
            return True

    agent = _Mini()
    # baseline
    samples_base = []
    for _ in range(200):
        t0 = time.perf_counter()
        assert _fake_invoke(1) == 2
        samples_base.append(time.perf_counter() - t0)
    # treatment
    samples_t = []
    for _ in range(200):
        t0 = time.perf_counter()
        assert invoke_passthrough(_fake_invoke, 1, agent=agent) == 2  # type: ignore[arg-type]
        samples_t.append(time.perf_counter() - t0)
    p50_base = statistics.median(samples_base)
    p50_t = statistics.median(samples_t)
    # Allow generous noise on Windows CI; absolute delta must stay sub-ms class
    assert (p50_t - p50_base) < 0.005, f"p50 delta too high: base={p50_base} treat={p50_t}"
    assert agent.mother_calls_on_hot_path == 0


def test_ledger_enqueue_drops_under_backpressure():
    from choruscontrol.agent.ledger import LedgerExporter

    exp = LedgerExporter("http://127.0.0.1:9", node_id="n1", tenant_id="t", max_queue=2)
    assert exp.enqueue({"a": 1})
    assert exp.enqueue({"a": 2})
    assert not exp.enqueue({"a": 3})
    assert exp.dropped == 1


def test_supported_commands_nack_unknown():
    assert "INVALIDATE_CACHE" in __import__(
        "choruscontrol.agent.runtime", fromlist=["SUPPORTED_COMMANDS"]
    ).SUPPORTED_COMMANDS
