import asyncio


async def fetch_data(n):
    print("hi")
    await asyncio.sleep(1)
    return f"Result {n}"


async def main():
    results = await asyncio.gather(fetch_data(1), fetch_data(2), fetch_data(3))
    print(results)  # ['Result 1', 'Result 2', 'Result 3']


asyncio.run(main())
