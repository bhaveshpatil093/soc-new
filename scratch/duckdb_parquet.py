import duckdb
import pyarrow as pa
import tempfile
from pathlib import Path

# Train
db_path = tempfile.mktemp(suffix=".db")
con = duckdb.connect(db_path)
con.execute("CREATE TABLE freq (k1 VARCHAR, k2 VARCHAR, count BIGINT)")
data = pa.table({"k1": ["u1", "u2", "u1"], "k2": ["h1", "h1", "h2"]})
con.execute("INSERT INTO freq SELECT k1, k2, COUNT(*) FROM data GROUP BY k1, k2")
con.execute("CREATE TABLE final AS SELECT k1, k2, SUM(count) as c FROM freq GROUP BY k1, k2")
con.execute("COPY final TO 'scratch/test.parquet' (FORMAT PARQUET)")
con.close()

# Infer
infer_con = duckdb.connect(":memory:")
infer_con.execute("CREATE VIEW final AS SELECT * FROM read_parquet('scratch/test.parquet')")
res = infer_con.execute("SELECT c FROM final WHERE k1='u1' AND k2='h1'").fetchone()
print(f"Count for u1, h1: {res[0] if res else 0}")
