import gzip
import random
import argparse
from datetime import date, timedelta
from pathlib import Path



APPS = ["checkout", "login", "search", "payment", "catalog"]
STATUS_CODES = [200] * 85 + [404] * 8 + [500] * 5 + [503] * 2
MALFORMED_RATE = 0.01  # 1% de linhas corrompidas

def generate_line(ts: str) -> str:
    user_id = random.randint(1, 50000)
    app = random.choice(APPS)
    status = random.choice(STATUS_CODES)
    latency = random.randint(10, 2000)
    ip = f"10.{random.randint(0,5)}.{random.randint(0,255)}.{random.randint(1,254)}"
    return f"{ts} user_id={user_id} app={app} status={status} latency_ms={latency} ip={ip}\n"

def generate_malformed_line() -> str:
    options = [
        "CORRUPTED_ENTRY\n",
        f"2026-99-99T99:99:99Z user_id=abc app= status=XYZ\n",
        "\n",
        f"incomplete user_id=123\n",
    ]
    return random.choice(options)

def generate_day(output_dir: Path, day: date, lines: int) -> None:
    filename = output_dir / f"acesso-{day.isoformat()}.log.gz"
    with gzip.open(filename, "wt", encoding="utf-8") as f:
        for i in range(lines):
            if random.random() < MALFORMED_RATE:
                f.write(generate_malformed_line())
            else:
                hour = random.randint(0, 23)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                ts = f"{day.isoformat()}T{hour:02d}:{minute:02d}:{second:02d}Z"
                f.write(generate_line(ts))


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera logs sintéticos de acesso")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"), help="Diretório de saída")
    parser.add_argument("--start", type=date.fromisoformat, required=True, help="Data inicial YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, required=True, help="Data final YYYY-MM-DD")
    parser.add_argument("--lines-per-day", type=int, default=100000, help="Linhas por arquivo")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    current = args.start
    while current <= args.end:
        print(f"Gerando {current.isoformat()} com {args.lines_per_day} linhas...")
        generate_day(args.output_dir, current, args.lines_per_day)
        current += timedelta(days=1)

    print("Concluído.")


if __name__ == "__main__":
    main(),