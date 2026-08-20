import duckdb
import pyarrow as pa
import numpy as np

# Create skewed data (heavy-tailed)
np.random.seed(42)
data = pa.table({
    "feature_name": ["event_count"] * 100000,
    "value": np.random.pareto(1.5, 100000) * 10
})

con = duckdb.connect(":memory:")
con.execute("CREATE TABLE features (feature_name VARCHAR, value DOUBLE)")
con.execute("INSERT INTO features SELECT * FROM data")

# Compute basic stats
query = """
SELECT 
    feature_name,
    AVG(value) as mean,
    STDDEV(value) as std,
    MEDIAN(value) as median,
    quantile_cont(value, 0.25) as p25,
    quantile_cont(value, 0.75) as p75,
    quantile_cont(value, 0.90) as p90,
    quantile_cont(value, 0.95) as p95,
    quantile_cont(value, 0.99) as p99,
    quantile_cont(value, 0.999) as p99_9
FROM features
GROUP BY feature_name
"""
res = con.execute(query).fetchone()

# MAD
mad_query = """
SELECT 
    MEDIAN(ABS(f.value - stats.median)) as mad
FROM features f
JOIN (
    SELECT feature_name, MEDIAN(value) as median 
    FROM features GROUP BY feature_name
) stats ON f.feature_name = stats.feature_name
WHERE f.feature_name = 'event_count'
"""
mad_res = con.execute(mad_query).fetchone()

print(f"Mean:   {res[1]:.2f}")
print(f"StdDev: {res[2]:.2f}")
print(f"Median: {res[3]:.2f}")
print(f"MAD:    {mad_res[0]:.2f}")
print(f"IQR:    {res[5] - res[4]:.2f}")
print(f"p99:    {res[8]:.2f}")
