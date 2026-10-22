from pathlib import Path

import polars as pl
import pytest

from grid_worker.portfolio_project_risk_calculator import (
    generate_mock_historical_data,
    run_vectorized_risk_engine,
)


# An empty request should still produce a readable empty Parquet dataset.
def test_generate_mock_data_supports_empty_dataset(tmp_path: Path) -> None:
    parquet_path = tmp_path / "empty.parquet"

    generate_mock_historical_data(parquet_path, num_rows=0)

    assert pl.read_parquet(parquet_path).is_empty()


# Non-multiple row counts should generate exactly the requested number of records.
def test_generate_mock_data_supports_non_multiple_of_node_count(tmp_path: Path) -> None:
    parquet_path = tmp_path / "partial_tick.parquet"

    generate_mock_historical_data(parquet_path, num_rows=51)

    result = pl.read_parquet(parquet_path)
    assert result.height == 51
    assert result.columns == ["timestamp", "node_id", "lmp", "zone"]


# Negative row counts are invalid and should fail with a clear error.
def test_generate_mock_data_rejects_negative_row_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="num_rows must be non-negative"):
        generate_mock_historical_data(tmp_path / "invalid.parquet", num_rows=-1)


# An empty but schema-valid Parquet file should return an empty report with columns.
def test_risk_engine_handles_empty_parquet_input(tmp_path: Path) -> None:
    parquet_path = tmp_path / "empty.parquet"
    pl.DataFrame(
        schema={
            "timestamp": pl.Int64,
            "node_id": pl.Int64,
            "lmp": pl.Float64,
            "zone": pl.String,
        }
    ).write_parquet(parquet_path)

    result = run_vectorized_risk_engine(parquet_path)

    assert result.is_empty()
    assert {
        "node_id",
        "zone",
        "mean_lmp",
        "volatility_lmp",
        "peak_lmp",
        "spike_count",
        "total_ticks",
        "spike_frequency_pct",
    }.issubset(result.columns)


# Validate spike metrics with negative, zero, threshold, and filtered-zone prices.
def test_risk_engine_aggregates_negative_and_zero_prices(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parquet_path = tmp_path / "prices.parquet"
    pl.DataFrame(
        {
            "timestamp": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            "node_id": [1001, 1001, 1001, 1001, 1002, 1002, 1003, 1003, 1004],
            "lmp": [-50.0, 0.0, 200.0, 250.0, -10.0, -20.0, 0.0, 0.0, 0.0],
            "zone": [
                "HB_NORTH",
                "HB_NORTH",
                "HB_NORTH",
                "HB_NORTH",
                "HB_HOUSTON",
                "HB_HOUSTON",
                "HB_HOUSTON",
                "HB_HOUSTON",
                "HB_SOUTH",
            ],
        }
    ).write_parquet(parquet_path)

    result = run_vectorized_risk_engine(parquet_path)
    capsys.readouterr()

    north = result.filter(pl.col("node_id") == 1001).row(0, named=True)
    houston = result.filter(pl.col("node_id") == 1002).row(0, named=True)
    zero_price = result.filter(pl.col("node_id") == 1003).row(0, named=True)

    assert north["total_ticks"] == 4
    assert north["spike_count"] == 1
    assert north["spike_frequency_pct"] == pytest.approx(25.0)
    assert north["mean_lmp"] == pytest.approx(100.0)
    assert north["peak_lmp"] == pytest.approx(250.0)
    assert houston["total_ticks"] == 2
    assert houston["spike_count"] == 0
    assert houston["spike_frequency_pct"] == pytest.approx(0.0)
    assert houston["mean_lmp"] == pytest.approx(-15.0)
    assert zero_price["total_ticks"] == 2
    assert zero_price["spike_count"] == 0
    assert zero_price["spike_frequency_pct"] == pytest.approx(0.0)
    assert result.filter(pl.col("node_id") == 1004).is_empty()
