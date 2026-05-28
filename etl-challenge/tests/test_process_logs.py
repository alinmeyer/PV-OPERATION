import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from process_logs import parse_line, compute_metrics
import polars as pl

def test_parse_line_valida():
    line = "2026-05-01T10:00:00Z user_id=123 app=checkout status=200 latency_ms=150 ip=10.0.0.1"
    result = parse_line(line)
    assert result is not None
    assert result["user_id"] == 123
    assert result["app"] == "checkout"
    assert result["status"] == 200
    assert result["latency_ms"] == 150


def test_parse_line_vazia():
    assert parse_line("") is None
    assert parse_line("\n") is None
    assert parse_line("   ") is None


def test_parse_line_malformada():
    assert parse_line("CORRUPTED_ENTRY") is None
    assert parse_line("2026-99-99T99:99:99Z user_id=abc app= status=XYZ") is None
    assert parse_line("incomplete user_id=123") is None


def test_parse_line_campos_faltando():
    line = "2026-05-01T10:00:00Z user_id=123 app=checkout status=200"
    assert parse_line(line) is None

def test_compute_metrics_basico():
    df = pl.DataFrame({
        "timestamp": ["2026-05-01T10:00:00Z"] * 4,
        "user_id": [1, 2, 3, 1],
        "app": ["checkout", "checkout", "checkout", "checkout"],
        "status": [200, 200, 500, 503],
        "latency_ms": [100, 200, 300, 400],
    })
    metrics = compute_metrics(df)
    row = metrics.filter(pl.col("app") == "checkout").row(0, named=True)

    assert row["total_requests"] == 4
    assert row["error_count"] == 2
    assert row["unique_users"] == 3
    assert round(row["error_rate"], 2) == 0.50


def test_compute_metrics_sem_erros():
    df = pl.DataFrame({
        "timestamp": ["2026-05-01T10:00:00Z"] * 3,
        "user_id": [1, 2, 3],
        "app": ["login", "login", "login"],
        "status": [200, 200, 200],
        "latency_ms": [100, 200, 300],
    })
    metrics = compute_metrics(df)
    row = metrics.filter(pl.col("app") == "login").row(0, named=True)

    assert row["error_count"] == 0
    assert row["error_rate"] == 0.0


