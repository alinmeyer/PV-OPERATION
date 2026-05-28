import gzip
import logging
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import polars as pl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    try:
        parts = line.split(" ")
        if len(parts) < 6:
            return None
        ts = parts[0]
        fields = {}
        for part in parts[1:]:
            if "=" in part:
                key, _, value = part.partition("=")
                fields[key] = value

        required = {"user_id", "app", "status", "latency_ms"}
        if not required.issubset(fields.keys()):
            return None

        return {
            "timestamp": ts,
            "user_id": int(fields["user_id"]),
            "app": fields["app"],
            "status": int(fields["status"]),
            "latency_ms": int(fields["latency_ms"]),
        }
    except (ValueError, KeyError):
        return None
    
def process_file(filepath: Path) -> pl.DataFrame | None:
    records = []
    skipped = 0

    with gzip.open(filepath, "rt", encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if parsed is None:
                skipped += 1
            else:
                records.append(parsed)

    if skipped > 0:
        logger.warning(f"{filepath.name}: {skipped} linhas ignoradas")

    if not records:
        logger.error(f"{filepath.name}: nenhuma linha válida encontrada")
        return None

    return pl.DataFrame(records)


def compute_metrics(df: pl.DataFrame) -> pl.DataFrame:
    return (
        df.group_by("app")
        .agg([
            pl.len().alias("total_requests"),
            (pl.col("status") >= 500).sum().alias("error_count"),
            pl.col("latency_ms").quantile(0.50).alias("latency_p50"),
            pl.col("latency_ms").quantile(0.95).alias("latency_p95"),
            pl.col("latency_ms").quantile(0.99).alias("latency_p99"),
            pl.col("user_id").n_unique().alias("unique_users"),
        ])
        .with_columns([
            (pl.col("error_count") / pl.col("total_requests")).alias("error_rate"),
        ])
    )

def save_parquet(df: pl.DataFrame, output_dir: Path, day: date) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"metrics-{day.isoformat()}.parquet"
    tmp_path = output_path.with_suffix(".tmp.parquet")

    df.write_parquet(tmp_path)
    tmp_path.replace(output_path)

    logger.info(f"Salvo: {output_path}")
    return output_path

def main() -> None:
    parser = argparse.ArgumentParser(description="Processa logs de acesso e gera métricas diárias")
    parser.add_argument("--start", type=date.fromisoformat, required=True, help="Data inicial YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, required=True, help="Data final YYYY-MM-DD")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"), help="Diretório com os .log.gz")
    parser.add_argument("--output-dir", type=Path, default=Path("data/output"), help="Diretório de saída Parquet")
    args = parser.parse_args()

    current = args.start
    errors = []

    while current <= args.end:
        filepath = args.input_dir / f"acesso-{current.isoformat()}.log.gz"

        if not filepath.exists():
            logger.warning(f"Arquivo não encontrado: {filepath}")
            current += timedelta(days=1)
            continue

        logger.info(f"Processando {filepath.name}...")
        df = process_file(filepath)

        if df is None:
            logger.error(f"Falha ao processar {filepath.name}")
            errors.append(current.isoformat())
            current += timedelta(days=1)
            continue

        metrics = compute_metrics(df)
        save_parquet(metrics, args.output_dir, current)
        current += timedelta(days=1)

    if errors:
        logger.error(f"Dias com falha: {errors}")
        sys.exit(1)

    logger.info("Processamento concluído com sucesso.")


if __name__ == "__main__":
    main()



