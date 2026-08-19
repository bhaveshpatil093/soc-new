import asyncio
from elasticsearch import AsyncElasticsearch

async def test():
    # DNS Error
    client = AsyncElasticsearch("https://this-does-not-exist.local:9200")
    try:
        await client.info()
    except Exception as e:
        print(f"DNS: {type(e)}")
        print(f"Underlying: {e}")
        
    # Connection Refused
    client = AsyncElasticsearch("https://127.0.0.1:9999")
    try:
        await client.info()
    except Exception as e:
        print(f"Refused: {type(e)}")
        print(f"Underlying: {e}")
        
    await client.close()

if __name__ == "__main__":
    asyncio.run(test())
