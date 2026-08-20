import duckdb
import pyarrow as pa

data1 = pa.table({"user_name": ["a", "b", "a"], "host_name": ["h1", "h1", "h2"]})
data2 = pa.table({"user_name": ["a", "c"], "host_name": ["h2", "h3"]})

con = duckdb.connect("scratch/test.db")
con.execute("CREATE TABLE IF NOT EXISTS user_host_freq (user_name VARCHAR, host_name VARCHAR, count BIGINT)")

# Fit 1
con.execute("INSERT INTO user_host_freq SELECT user_name, host_name, COUNT(*) FROM data1 GROUP BY user_name, host_name")
# Fit 2
con.execute("INSERT INTO user_host_freq SELECT user_name, host_name, COUNT(*) FROM data2 GROUP BY user_name, host_name")

# Query
print(con.execute("SELECT user_name, host_name, SUM(count) FROM user_host_freq GROUP BY user_name, host_name").df())
