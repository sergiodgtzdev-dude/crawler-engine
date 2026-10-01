import redis.exceptions
import requests
import pprint
import asyncio
from crawler import get_clean_outbound_url as get_clean_outbound_url, Crawler
from dotenv import load_dotenv
import math
import logging
import json
import redis.asyncio as aioredis
import uuid
import os
import redis

load_dotenv(".venv/.env")

# Logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Worker %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler()],
)

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))

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

#Returns the cache key for the search term and saves the data to redis with a TTL of 1 hour
async def save_to_redis(search_term: str, data: list, ttl_seconds: int = 3600) -> str:
    cache_key = f"crawl:{search_term.lower().replace(' ', '_')}"

    # Opening redis db connection
    async with aioredis.Redis(host=redis_host, port=redis_port, db=0) as r:
        # Normalizing cache key

        # Serialize and save with expiration time of 1 hour
        await r.set(cache_key, json.dumps(data, ensure_ascii=False,), ex=ttl_seconds)

        # Retrieve the inserted values for testing and debugging purposes
        # value = await r.get(cache_key)
        logging.warning(f"Results saved under key: '{cache_key}' (TTL: {ttl_seconds}s)")

    return cache_key


#Main function that orchestrates the  crawl operation
async def crawl_term(search_term : str, job_id : str) -> list:
    #Initializing the queue and the visited urls set
    visited_urls = set()
    url_queue = []
    queue = asyncio.Queue()
    pool = []
    visited_urls = set()
    processed_urls = []

    searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8080")

    # Getting search info
    initial_url = f"{searxng_url}/search?q={search_term}&format=json"
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

    for url in url_queue:
        queue.put_nowait(url)
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

    logging.warning(f"Finished job with id {job_id} - Exiting. Processed URLs: {len(visited_urls)}")
    # Prints URLs for testing and verification purposes
    # pprint.pp(processed_urls[1:5])

    return processed_urls


#Function that checks the Redis Queue for new terms to crawl and invokes the main function
async def worker():
    async with aioredis.Redis(host=redis_host, port=redis_port, db=0) as r:
        logging.warning("Application listening to Redis Queue 'queue:crawling'")
        while True:
            try:
                #Waiting for tasks to populate the queue and decoding search term to utf-8
                _, raw_term = await r.brpop("queue:crawling", timeout= 5)
                if raw_term is None:
                    continue

                search_term = raw_term.decode("utf-8")
                job_id = str(uuid.uuid4())

                term_slug = search_term.lower().replace(" ", "_")
                cache_key = f"crawl:{term_slug}"
                lock_key = f"processing:{term_slug}"

                #Checking if term already exists in redis DB
                if await r.exists(cache_key):
                    logging.info(
                        f"[SKIP] The term '{search_term}' is already in cache with cache key ({cache_key})."
                    )
                    continue

                logging.warning(f"Job received, assigned ID {job_id}")
                acquired_lock = await r.set(lock_key, job_id, nx=True, ex=120)

                if not acquired_lock:
                    logging.info(
                        f"[SKIP] The term '{search_term}' is being processed. Skipping duplicate work"
                    )
                    continue

                data = await crawl_term(search_term, job_id)
                await save_to_redis(search_term=search_term, data=data, ttl_seconds=3600)

            except redis.exceptions.TimeoutError:
                continue
            except Exception as e:
                logging.error(
                    f"Error inesperado procesando el trabajo: {e}",
                    exc_info=True,
                )
            finally:
                if lock_key:
                    await r.delete(lock_key)

if __name__ == "__main__":
    asyncio.run(worker())
