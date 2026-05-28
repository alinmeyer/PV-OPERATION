#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/etl/run_daily.log"
INPUT_DIR="/var/log/apps"
OUTPUT_DIR="/opt/etl/output"
IMAGE="etl-logs"

mkdir -p "$(dirname "$LOG_FILE")" "$OUTPUT_DIR"

YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
START_TIME=$(date +%s)

log() {
    echo "[$(date -d "yesterday" +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"
}

log "INFO Iniciando processamento para $YESTERDAY"

docker run --rm \
    -v "$INPUT_DIR:/app/data/raw:ro" \
    -v "$OUTPUT_DIR:/app/data/output" \
    "$IMAGE" \
    --start "$YESTERDAY" \
    --end "$YESTERDAY" \
    --input-dir data/raw \
    --output-dir data/output

EXPECTED_FILE="$OUTPUT_DIR/metrics-${YESTERDAY}.parquet"
if [[ ! -f "$EXPECTED_FILE" ]]; then
    log "ERROR Parquet não gerado: $EXPECTED_FILE"
    exit 1
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
log "INFO Concluído em ${DURATION}s. Arquivo: $EXPECTED_FILE"