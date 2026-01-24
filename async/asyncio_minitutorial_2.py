import asyncio


async def fetch_data(x):
    print(f"Fetching data for {x}...")
    await asyncio.sleep(x)  # Simulate an I/O-bound operation
    print(f"Data for {x} fetched.")
    return f"data_{x}"


async def main():
    tasks = []
    async with asyncio.TaskGroup() as tg:
        for i in range(5):
            tasks.append(tg.create_task(fetch_data(i)))

    results = [task.result() for task in tasks]
    print("All data fetched:", results)
    return results


asyncio.run(main())
