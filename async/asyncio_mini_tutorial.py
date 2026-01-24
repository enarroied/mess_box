# https://www.youtube.com/watch?v=Qb9s3UiMSTA

import asyncio


async def fetch_data(delay, data):
    print("start fetching")
    await asyncio.sleep(delay)  # Simulate a network delay
    print("done fetching")
    return {"data": data}  # Simulated fetched data


# Coroutine function returning a coroutine object
async def main(i):
    print(f"start of main coroutine - {i}")
    task = fetch_data(5, f"sample data: {i}")  # Create coroutine object
    result = await task  # Await the coroutine object
    print(f"result: {result}")


# run the main coroutine
asyncio.run(main(1))  # main() is a coroutine object
