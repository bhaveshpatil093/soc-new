import os
import sys
import subprocess
from unittest.mock import patch
import asyncio

def run_cli(env_vars):
    env = os.environ.copy()
    env.update(env_vars)
    # Using tads instead of anomaly_system to match our implementation,
    # though python -m anomaly_system would also work since we created the wrapper.
    cmd = [sys.executable, "-m", "anomaly_system", "ingest", "test-connection"]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result

def print_result(name, result):
    print(f"\n{'='*50}")
    print(f"SCENARIO: {name}")
    print(f"EXIT CODE: {result.returncode}")
    print(f"OUTPUT:\n{result.stdout}{result.stderr}")
    print(f"{'='*50}")

def main():
    # Scenario 1: Wrong Password (401)
    # We can't actually get a 401 unless there's a real server responding with 401.
    # We'll get a connection refused if nothing is running on 9200.
    # To demonstrate 401, 403, 404, we need to mock the client OR we can demonstrate
    # DNS failure, Connection Refused, and Timeout without a server.
    
    print_result("DNS Failure (Wrong Host)", run_cli({
        "ELASTIC_HOST": "https://this-does-not-exist.local:9200",
        "ELASTIC_USERNAME": "admin",
        "ELASTIC_PASSWORD": "password"
    }))
    
    print_result("Connection Refused (Blocked Port)", run_cli({
        "ELASTIC_HOST": "https://127.0.0.1:9999",
        "ELASTIC_USERNAME": "admin",
        "ELASTIC_PASSWORD": "password"
    }))
    
    # We will write a small python script to mock the ES client to simulate 401, 403, 404 and Success.
    pass

if __name__ == "__main__":
    main()
