import time
import duckdb

con = duckdb.connect("scratch/test_perf.db")
con.execute("CREATE TABLE IF NOT EXISTS test_freq (k1 VARCHAR, k2 VARCHAR, count BIGINT)")
con.execute("INSERT INTO test_freq SELECT 'u' || (i%1000)::VARCHAR, 'h' || (i%500)::VARCHAR, 1 FROM range(1000000) tbl(i)")
con.execute("CREATE TABLE final_freq AS SELECT k1, k2, SUM(count) as c FROM test_freq GROUP BY k1, k2")
con.execute("CREATE INDEX idx ON final_freq(k1, k2)")

start = time.perf_counter()
for _ in range(10000):
    res = con.execute("SELECT c FROM final_freq WHERE k1 = 'u500' AND k2 = 'h0'").fetchone()
end = time.perf_counter()

print(f"Time for 10,000 lookups: {end - start:.4f}s")
