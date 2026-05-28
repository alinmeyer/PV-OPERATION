FROM python:3.12-slim

WORKDIR /app

RUN groupadd --gid 1001 etl && \
    useradd --uid 1001 --gid etl --no-create-home etl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY process_logs.py .

USER etl

ENTRYPOINT ["python", "process_logs.py"]

