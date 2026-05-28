# ETL de Logs de Acesso

Pipeline que transforma logs de acesso comprimidos em métricas diárias por aplicação,
armazenadas em Parquet.

## Fluxo

```
/var/log/apps/acesso-YYYY-MM-DD.log.gz
        |
        v
process_logs.py (streaming, linha a linha)
        |
        +-- parse_line() -> descarta malformadas
        +-- compute_metrics() -> agrega por app
        +-- save_parquet() -> escrita atomica
        |
        v
/opt/etl/output/metrics-YYYY-MM-DD.parquet
        |
        v
  DuckDB / Polars (consulta)
```

## Pre-requisitos

- Python 3.12+
- Docker
- (opcional) DuckDB para consultar os Parquets

## 1. Gerar dados de exemplo

```bash
pip install -r requirements.txt
python generate_sample.py --start 2026-05-01 --end 2026-05-07 --lines-per-day 100000
```

Os arquivos serao criados em data/raw/.

## 2. Rodar o script localmente

```bash
python process_logs.py --start 2026-05-01 --end 2026-05-07
```

Saida em data/output/.

## 3. Buildar e rodar o container

```bash
docker build -t etl-logs .
```

Linux e macOS:

```bash
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  etl-logs \
  --start 2026-05-01 --end 2026-05-07 \
  --input-dir data/raw \
  --output-dir data/output
```

Windows Git Bash:

```bash
docker run --rm \
  -v "C:/caminho/completo/etl-challenge/data:/app/data" \
  etl-logs \
  --start 2026-05-01 --end 2026-05-07 \
  --input-dir data/raw \
  --output-dir data/output
```

## 4. Instalar o systemd timer no servidor Ubuntu

```bash
sudo cp infra/run_daily.sh /opt/etl/run_daily.sh
sudo chmod +x /opt/etl/run_daily.sh
sudo cp infra/etl.service /etc/systemd/system/etl.service
sudo cp infra/etl.timer /etc/systemd/system/etl.timer
sudo cp infra/etl-logrotate /etc/logrotate.d/etl

sudo useradd --system --no-create-home etl
sudo mkdir -p /var/log/etl /opt/etl/output
sudo chown etl:etl /var/log/etl /opt/etl/output

sudo systemctl daemon-reload
sudo systemctl enable etl.timer
sudo systemctl start etl.timer

sudo systemctl status etl.timer
sudo journalctl -u etl.service -f
```

## 5. Consultar a saida

Com Polars:

```python
python3 -c "
import polars as pl
df = pl.read_parquet('data/output/metrics-2026-05-01.parquet')
print(df)
"
```

Com DuckDB:

```bash
pip install duckdb
python query.py
```

O arquivo query.py agrega todos os dias disponíveis por app, mostrando
total de requests, taxa de erro média, latências p50/p95/p99 e usuários únicos.

## 6. Rodar os testes

```bash
pip install pytest
python -m pytest tests/ -v
```

## Observabilidade

### Métricas a coletar

**Métricas técnicas do job:**
- `etl_duration_seconds` duração do job. Alerta se > 1800s (30min): indica degradação.
- `etl_lines_skipped_total` linhas malformadas por dia. Alerta se > 5%: indica mudança no formato do log.
- `etl_lines_processed_total` total de linhas processadas. Alerta se cair > 30% em relação à média dos últimos 7 dias: indica problema na geração dos logs.
- `etl_exit_code` código de saída do job. Alerta se != 0: falha no processamento.

**Métricas de negócio (dentro do Parquet):**
- `error_rate` por app alerta se > 10% em qualquer app: indica problema na aplicação.
- `latency_p99` por app alerta se > 5000ms: degradação de performance.
- `unique_users` por dia alerta se cair > 40% vs média: pode indicar problema de coleta ou queda real de uso.
- `total_requests` por dia alerta se zero em qualquer app: app pode estar fora do ar.

### Onde coletar

- O `run_daily.sh` já registra duração e status em `/var/log/etl/run_daily.log`
- O systemd journal captura stdout/stderr do job, consultável com `journalctl -u etl.service`
- As métricas de negócio vivem nos Parquets, um job secundário pode ler e exportar para Prometheus ou DataDog

### Como ser notificado

- Falha do job: o systemd pode chamar um `OnFailure=etl-notify.service` que envia alerta via email ou webhook Slack
- Anomalias de negócio: script Python agendado que lê o Parquet do dia e compara com limites, enviando alerta se violado

### Critério para dia suspeito

Um dia é suspeito mesmo com job bem-sucedido quando:
- Total de linhas processadas cai mais de 30% vs média dos 7 dias anteriores
- Taxa de erro de qualquer app aumenta mais de 3x vs dia anterior
- Nenhum usuário único registrado em qualquer app
- Latência p99 dobra vs dia anterior sem mudança de volume

Esses casos indicam problema silencioso, o job rodou, mas os dados estão errados ou incompletos.
