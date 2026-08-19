import os
import asyncio
from pydantic import ValidationError
from tads.schema.settings import get_settings
from tads.ingestion.client import get_es_client
from elastic_transport import ConnectionError

async def demo():
    print("\n--- Failure Path 1: Missing Password ---")
    os.environ["ELASTIC_HOST"] = "https://es.example.com:9200"
    os.environ["ELASTIC_USERNAME"] = "admin"
    if "ELASTIC_PASSWORD" in os.environ:
        del os.environ["ELASTIC_PASSWORD"]
    try:
        get_settings()
    except Exception as e:
        print(f"Caught Exception: {type(e).__name__}")
        print(e)
        
    print("\n--- Failure Path 2: Malformed Host ---")
    os.environ["ELASTIC_HOST"] = "not-a-valid-url"
    os.environ["ELASTIC_PASSWORD"] = "my_super_secret_value_123"
    try:
        get_settings()
    except Exception as e:
        print(f"Caught Exception: {type(e).__name__}")
        print(e)
        
    print("\n--- Failure Path 3: Unreachable Host ---")
    os.environ["ELASTIC_HOST"] = "https://127.0.0.1:9999" # Nothing listening here
    os.environ["ELASTIC_PASSWORD"] = "my_super_secret_value_123"
    
    # We expect a connection error that does NOT dump the password
    settings = get_settings()
    client = get_es_client(settings)
    try:
        await client.info()
    except Exception as e:
        print(f"Caught Exception: {type(e).__name__}")
        print(e)
    finally:
        await client.close()
        
    print("\n--- Validation Gate Complete ---")

if __name__ == "__main__":
    asyncio.run(demo())
