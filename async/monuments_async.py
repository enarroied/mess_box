import asyncio
import re

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


def extract_monument_ids(html):
    """Extract data-detail IDs from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", attrs={"data-detail": True})
    return [link.get("data-detail") for link in links]


async def scrape_single_page(page_num, base_url):
    """Scrape a single page in its own browser instance. Returns None if page doesn't exist."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            offset = (page_num - 1) * 50
            url = f"{base_url}&arko_default_648970c046073--from={offset}&arko_default_648970c046073--resultSize=50"

            # Shorter timeout and handle errors gracefully
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception as e:
                print(f"Page {page_num}: Timeout/Error - {type(e).__name__}")
                return page_num, None

            if response.status == 404:
                return page_num, None

            try:
                await page.wait_for_selector("a[data-detail]", timeout=5000)
            except:
                return page_num, None

            html = await page.content()
            ids = extract_monument_ids(html)

            if not ids:
                return page_num, None

            return page_num, ids

        except Exception as e:
            print(f"Page {page_num}: Exception - {type(e).__name__}")
            return page_num, None
        finally:
            await browser.close()


async def scrape_batch(start_page, batch_size, base_url):
    """Scrape a batch of pages concurrently. Returns IDs, successful count, and failed pages."""
    tasks = [
        scrape_single_page(page_num, base_url)
        for page_num in range(start_page, start_page + batch_size)
    ]

    results = await asyncio.gather(*tasks)

    all_ids = []
    successful_pages = 0
    failed_pages = []

    for page_num, ids in sorted(results):
        if ids is None:
            print(f"Page {page_num}: No results")
            failed_pages.append(page_num)
        else:
            print(f"Page {page_num}: {len(ids)} IDs")
            all_ids.extend(ids)
            successful_pages += 1

    return all_ids, successful_pages, failed_pages


async def get_total_pages(base_url):
    """Determine total pages by loading first page and checking pagination."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(base_url, wait_until="networkidle")
            await page.wait_for_selector("button", timeout=5000)

            # Find all pagination buttons and get the highest number
            buttons = await page.query_selector_all("button")
            page_numbers = []

            for button in buttons:
                text = await button.inner_text()
                if text.strip().isdigit():
                    page_numbers.append(int(text.strip()))

            # If we found page numbers, return the max
            if page_numbers:
                return max(page_numbers)

            # Fallback: look for total count in the page
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Try to find total results text (e.g., "38926 résultats")
            # Then calculate: total_pages = (total_results + 49) // 50
            text = soup.get_text()
            import re

            match = re.search(r"(\d+)\s*résultats?", text, re.IGNORECASE)
            if match:
                total_results = int(match.group(1))
                return (total_results + 49) // 50

            return None

        finally:
            await browser.close()


async def scrape_all_monuments(concurrent_browsers=5):
    """Scrape all pages using concurrent browser instances until no more results."""
    base_url = "https://www.monuments-aux-morts.fr/monuments?arko_default_648970c046073--ficheFocus=&arko_default_648970c046073--filtreGroupes%5Bmode%5D=simple&arko_default_648970c046073--filtreGroupes%5Bop%5D=AND&arko_default_648970c046073--contenuIds%5B%5D=181917&arko_default_648970c046073--modeRestit=arko_default_648974b6631ac"

    all_ids = []
    page_num = 1
    consecutive_empty_batches = 0
    all_failed_pages = []

    while True:
        print(f"\nBatch: pages {page_num}-{page_num + concurrent_browsers - 1}")

        batch_ids, successful_pages, failed_pages = await scrape_batch(
            page_num, concurrent_browsers, base_url
        )
        all_ids.extend(batch_ids)
        all_failed_pages.extend(failed_pages)

        if successful_pages == 0:
            consecutive_empty_batches += 1
            if consecutive_empty_batches >= 2:
                print("\n✓ Reached the end")
                break
        else:
            consecutive_empty_batches = 0

        page_num += concurrent_browsers
        await asyncio.sleep(1)

    # Retry failed pages once
    if all_failed_pages:
        # Only retry pages that are before the last successful page
        last_successful = max(
            (p for p in range(1, page_num) if p not in all_failed_pages), default=0
        )
        retry_pages = [p for p in all_failed_pages if p <= last_successful]

        if retry_pages:
            print(f"\n⚠️  Retrying {len(retry_pages)} failed pages...")
            for page_n in retry_pages:
                _, ids = await scrape_single_page(page_n, base_url)
                if ids:
                    print(f"Page {page_n}: {len(ids)} IDs (retry success)")
                    all_ids.extend(ids)
                else:
                    print(f"Page {page_n}: Failed again")

    return list(dict.fromkeys(all_ids))


async def main():
    concurrent = 3

    print(f"Scraping all pages with {concurrent} concurrent browsers...")
    print("Will stop automatically when no more results found\n")

    monument_ids = await scrape_all_monuments(concurrent_browsers=concurrent)

    print(f"\n{'=' * 60}")
    print(f"Total unique IDs: {len(monument_ids)}")
    print(f"{'=' * 60}")

    with open("monument_ids.txt", "w") as f:
        for mid in monument_ids:
            f.write(f"{mid}\n")

    print(f"\n✅ Saved to monument_ids.txt")


if __name__ == "__main__":
    asyncio.run(main())
