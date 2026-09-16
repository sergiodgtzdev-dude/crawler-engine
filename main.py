import requests
import pprint
import asyncio
from crawler import get_clean_outbound_url as get_clean_outbound_url, Crawler
from dotenv import load_dotenv
import math
import logging

load_dotenv(".venv/.env")

# Logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Worker %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler()],
)

# Headers for the request following Best Practices as a crawler bot project
headers = {
    "User-Agent": "Mozilla/5.0 (compatible; DistributedSearchBot/1.0; +[https://github.com/sergiodgtzdev-dude/crawler-engine](https://github.com/sergiodgtzdev-dude/crawler-engine))",
    "Accept": "application/json",
}
BLOCKED_DOMAINS = {
    "amazon.com",
    "tiktok.com",
    "elpalaciodehierro.com",
    "ebay.com",
    "mercadolibre.com",
    "aliexpress.com",
    "youtube.com",
    "walmart.com",
    "bestbuy.com",
    "newegg.com",
    "target.com",
    "overstock.com",
    "homedepot.com",
    "costco.com",
    "bhphotovideo.com",
    "staples.com",
    "officeDepot.com",
    "wayfair.com",
    "zappos.com",
    "instagram.com",
}

# Batch size that each worker will process at a time, and the maximum number of workers that can run concurrently
batch_size = 2
max_workers = 50

# pprint.pp(response["results"][0])


async def main():

    # Initializing the queue and the visited urls set
    visited_urls = set()
    url_queue = []
    queue = asyncio.Queue()
    pool = []
    search_term = "laptop origins"
    visited_urls = set()
    processed_urls = []

    # Getting search info
    initial_url = f"http://localhost:8080/search?q={search_term}&format=json"
    response = requests.get(initial_url, headers=headers)
    response = response.json()

    # Collect the initial url list
    for item in response["results"]:
        url_queue.append(item["url"])

    # pprint.pp("Initial URL Queue:")
    # pprint.pp(url_queue)

    # filter out the list
    for blocked in BLOCKED_DOMAINS:
        url_queue = [url for url in url_queue if blocked not in url]

    # Adds the depth of each url
    url_queue = [(url, 0) for url in url_queue]

    # Using a tuple to store the url and its depth
    # print("\n\nFiltered URL Queue:")
    # pprint.pp(url_queue)

    for url in url_queue:
        queue.put_nowait(url)
    pprint.pp(f"Queue: {queue}")
    logging.info(f"Starting crawler with {len(url_queue)} URLs to process.")
    active_workers = min(max_workers, math.ceil(len(url_queue) / batch_size))
    logging.info(f"Active workers are: {active_workers} ")
    active_workers = max(1, active_workers)
    tasks = []
    # print(f"\n\nFiltered URL Queue: Active workers {active_workers}")

    # Starting all workers
    for i in range(active_workers):
        worker = Crawler(
            queue=queue,
            id=i + 1,
            visited_urls=visited_urls,
            processed_urls=processed_urls,
        )
        pool.append(worker)
        task = asyncio.create_task(worker.consume())
        tasks.append(task)

    await queue.join()  # Wait for all tasks to be processed

    for task in tasks:
        task.cancel()  # Cancel any remaining tasks

    logging.info(f"All tasks completed. Exiting. Processed URLs: {len(visited_urls)}")
    # Prints URLs for validation purposes
    # pprint.pp(processed_urls[1:5])


if __name__ == "__main__":
    asyncio.run(main())
