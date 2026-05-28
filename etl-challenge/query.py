import duckdb

con = duckdb.connect()
result = con.execute("""
    SELECT 
        app,
        SUM(total_requests) as total_requests,
        ROUND(AVG(error_rate) * 100, 2) as avg_error_rate_pct,
        ROUND(AVG(latency_p50), 0) as avg_p50,
        ROUND(AVG(latency_p95), 0) as avg_p95,
        ROUND(AVG(latency_p99), 0) as avg_p99,
        SUM(unique_users) as total_unique_users
    FROM read_parquet('data/output/metrics-*.parquet')
    GROUP BY app
    ORDER BY avg_error_rate_pct DESC
""").pl()
print(result)