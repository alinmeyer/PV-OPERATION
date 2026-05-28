docker run --rm -v "$(pwd)/data:/app/data" etl-logs --start 2026-05-01 --end 2026-05-03 --input-dir data/raw --output-dir data/output

# NOTAS.md

## Decisões técnicas

### Polars em vez de Pandas ou Spark
Escolhi Polars porque o cenário é um servidor Ubuntu único processando um dia de logs por vez.
Pandas seria mais lento e consumiria mais memória para volumes grandes. Spark faz sentido para
clusters distribuídos — adiciona complexidade operacional desnecessária aqui. Polars resolve
com processamento paralelo nativo, uso de Arrow internamente e lazy evaluation.

### Leitura em streaming
O process_logs.py lê os arquivos .log.gz linha por linha com gzip.open + for line in f.
Nunca carrega o arquivo inteiro na memória. Os records são acumulados em lista e o DataFrame
é construído uma única vez ao final — Polars é muito mais eficiente assim do que inserção incremental.

### Idempotência via arquivo temporário
A escrita do Parquet usa um arquivo .tmp.parquet que é renomeado atomicamente para o nome final.
Se o processo morrer no meio da escrita, o arquivo final nunca fica corrompido. Rodar duas vezes
para o mesmo dia sobrescreve com resultado idêntico.
Nota: no Windows, Path.rename() não sobrescreve — foi necessário usar Path.replace().
Em Linux (produção) o comportamento é atômico e correto.

### python:3.12-slim como base Docker
Imagem menor (~150MB) em vez de Ubuntu (~500MB), já inclui Python, menos superfície de ataque.
O slim é Debian sem pacotes desnecessários. Justificativa suficiente para produção.

### Usuário não-root no container
O container roda com usuário etl (uid 1001). Se o container for comprometido, o atacante não
tem privilégios de root no host.

### requirements.txt apenas com dependências de produção
pytest e outras dependências de desenvolvimento foram excluídas. O container de produção não
precisa executar testes.

## O que tentei e descartei

- Tentei usar DuckDB para leitura direta dos .log.gz mas ele não suporta parsing de formato
  customizado linha a linha. Ficou com Python puro para parsing + Polars para agregação.
- Considerei escrever o Parquet particionado por app mas o enunciado pede um arquivo por dia,
  não por app.

## Uso de IA
Usei Claude como par técnico durante todo o desenvolvimento. Cada bloco de código foi explicado
antes de ser escrito — entendo o propósito de cada linha. A IA sugeriu o padrão de arquivo
temporário para idempotência e o uso de Path.replace() para compatibilidade Windows/Linux.

## Limitações conhecidas

- O script bash run_daily.sh usa date -d "yesterday" que é GNU date (Linux). No macOS seria
  date -v-1d. Em produção Ubuntu isso não é problema.
- Não há retry automático por dia com falha — se um dia falhar, precisa rodar manualmente.
- O volume de dados sintéticos é pequeno para testes. Em produção com dezenas de milhões de
  linhas, o acúmulo de records em lista pode pressionar memória — alternativa seria processar
  em chunks e concatenar DataFrames parciais.
- Não implementamos autenticação no registry Docker — em produção a imagem estaria em um
  registry privado.

## Perguntas que faria ao time

- Qual o volume médio real de linhas por dia? Isso define se precisamos de chunking.
- Os logs já estão em /var/log/apps/ ou precisamos de um step de coleta antes?
- Existe um data catalog ou os Parquets ficam só no filesystem?
- Qual a política de retenção dos Parquets de saída?
- O job precisa de alertas ativos (PagerDuty, Slack) ou email é suficiente?
