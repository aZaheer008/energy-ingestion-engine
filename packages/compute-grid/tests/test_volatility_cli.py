from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pytest

from grid_worker import volatility_cli


# An explicit worker count should bypass automatic container CPU discovery.
def test_explicit_worker_count_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_cpu_limit_is_checked() -> None:
        pytest.fail("explicit worker count should bypass automatic sizing")

    monkeypatch.setattr(volatility_cli, "get_container_cpu_limit", fail_if_cpu_limit_is_checked)

    assert volatility_cli.resolve_optimal_workers(3) == 3


# Container quotas determine the automatic worker count, with at least one worker.
@pytest.mark.parametrize(
    ("container_limit", "expected"),
    [(4.0, 3), (1.0, 1), (0.5, 1)],
)
def test_worker_count_respects_container_limit(
    monkeypatch: pytest.MonkeyPatch, container_limit: float, expected: int
) -> None:
    monkeypatch.setattr(volatility_cli, "get_container_cpu_limit", lambda: container_limit)

    assert volatility_cli.resolve_optimal_workers(None) == expected


# When no container quota is found, worker sizing falls back to host CPU count.
def test_worker_count_falls_back_to_host_cpu_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(volatility_cli, "get_container_cpu_limit", lambda: None)
    monkeypatch.setattr(volatility_cli.os, "cpu_count", lambda: 8)

    assert volatility_cli.resolve_optimal_workers(None) == 7


# Empty chunks should return an empty array without attempting calculations.
def test_empty_price_chunk_returns_empty_result() -> None:
    result = volatility_cli.compute_node_chunk_volatility(0, np.array([], dtype=np.float64), 5)

    assert result.shape == (0,)
    assert result.dtype == np.float64


# Negative prices should not produce NaN or negative volatility proxy values.
def test_negative_prices_produce_finite_nonnegative_proxy() -> None:
    prices = np.array([-100.0, -25.0, 0.0, 25.0], dtype=np.float64)

    result = volatility_cli.compute_node_chunk_volatility(0, prices, 5)

    assert result.shape == prices.shape
    assert np.isfinite(result).all()
    assert (result >= 0).all()


# Reject invalid negative iteration counts instead of silently skipping the loop.
def test_negative_iteration_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="iterations must be non-negative"):
        volatility_cli.compute_node_chunk_volatility(
            0, np.array([10.0], dtype=np.float64), -1
        )


# The worker function should accept inputs and return finite results in child processes.
def test_worker_function_runs_in_process_pool() -> None:
    chunks = [
        np.array([10.0, 20.0], dtype=np.float64),
        np.array([-10.0, -20.0], dtype=np.float64),
    ]

    with ProcessPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                volatility_cli.compute_node_chunk_volatility,
                range(len(chunks)),
                chunks,
                [5, 5],
            )
        )

    assert [result.shape for result in results] == [(2,), (2,)]
    assert all(np.isfinite(result).all() for result in results)
