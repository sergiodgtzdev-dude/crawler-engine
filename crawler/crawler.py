import requests
import pprint
from bs4 import BeautifulSoup
import asyncio
import httpx
import time
import logging
from dotenv import load_dotenv
from urllib.parse import urljoin, urldefrag, urlparse

load_dotenv(".venv/.env")

# Logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Worker %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler()],
)


# Function that cleans url and returns None if the url is not valid or is the same as the current page url
def get_clean_outbound_url(href: str, current_page_url: str) -> str | None:
    # 1. Convert relative URLs to absolute URLs
    absolute_url = urljoin(current_page_url, href)

    # 2. Strip fragment anchors (#comments, #respond, #, etc.)
    clean_url, fragment = urldefrag(absolute_url)

    if (
        "jpg" in clean_url
        or "jpeg" in clean_url
        or "png" in clean_url
        or "gif" in clean_url
        or "svg" in clean_url
    ):
        return None

    # 3. Filter out non-HTTP schemes (mailto:, javascript:, tel:, empty strings)
    parsed = urlparse(clean_url)
    if parsed.scheme not in ("http", "https"):
        return None

    # 4. Normalize trailing slashes for comparison
    normalized_clean = clean_url.rstrip("/")
    normalized_current, _ = urldefrag(current_page_url)
    normalized_current = normalized_current.rstrip("/")

    # 5. Skip if the link points to the exact page you are currently crawling
    if normalized_clean == normalized_current:
        return None
    return clean_url


class Crawler:
    def __init__(
        self,
        queue: asyncio.Queue = None,
        id: int = 0,
        url: str = "",
        visited_urls: set = None,
        processed_urls: list = None,
    ):
        self.id = id
        self.current_page_url = url
        self.queue = queue
        self.visited_urls = visited_urls
        self.processed_urls = processed_urls
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; DistributedSearchBot/1.0; +[https://github.com/sergiodgtzdev-dude/crawler-engine](https://github.com/sergiodgtzdev-dude/crawler-engine))",
            "Accept": "application/json",
        }
        logging.info(f"Worker {self.id} initialized.")

    async def consume(self):
        while True:
            retries = 0
            url, depth = await self.queue.get()
            self.current_page_url = url
            result = None
            try:
                logging.info(f" {self.id} Processing {url} at depth {depth}")
                if depth <= 1:
                    result = await self.process_text()
                else:
                    logging.info(
                        f" {self.id} Skipping {url} at depth {depth} (max depth reached)"
                    )
            except Exception as e:
                logging.error(f"Error processing {url}: {e}")
                logging.error(f"Finished Processing {url} with result: {e}")
                continue
            finally:
                # Handling result
                if result:
                    logging.info(
                        f"Finished Processing {url} with result: {result['status_code']}"
                    )
                    if depth < 1:
                        outbound_links = result.pop("outbound_links", [])
                        outbound_to_enqueue = outbound_links[:10]
                        for link, next_depth in outbound_to_enqueue:
                            if link not in self.visited_urls:
                                self.visited_urls.add(link)
                                await self.queue.put((link, next_depth))
                    self.processed_urls.append(result)

                self.queue.task_done()

    # Method will be async as it will be called in an async context, allowing for concurrent processing of multiple URLs
    async def process_text(self):
        current_page_url = self.current_page_url
        async with httpx.AsyncClient(
            follow_redirects=False, timeout=httpx.Timeout(3.0, connect=3.0)
        ) as client:
            try:
                response = await client.get(
                    url=current_page_url, headers=self.headers, timeout=3.0
                )
            except httpx.HTTPError as e:
                logging.warning(
                    f"Worker {self.id} HTTP error in {current_page_url}: {e}"
                )
                return None
        if response.status_code != 200:
            return None
        else:
            # Extraction of metadata and processed text
            soup = BeautifulSoup(response.content, "html.parser")
            # Filtered elements to avoid noise in the processed text
            for element in soup(
                ["nav", "footer", "aside", "script", "img", "style", "svg"]
            ):
                element.decompose()

            # Building information for final dictionary object
            title = soup.title.string if soup.title else "No title found"
            meta_desc_tag = soup.find(
                "meta", attrs={"name": "description"}
            ) or soup.find("meta", attrs={"property": "og:description"})
            description = (
                meta_desc_tag.get("content", "").strip()
                if meta_desc_tag
                else "No description found"
            )
            lang_tag = soup.find("html")
            lang = lang_tag.get("lang", "")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            h1 = [h1.get_text(strip=True) for h1 in soup.find_all("h1")]
            h2 = [h2.get_text(strip=True) for h2 in soup.find_all("h2")]

            # Creating a list of urls and cleaning them using the get_clean_outbound_url function
            urls = soup.find_all("a", href=True)
            clean_url_list = []

            for anchor in urls:
                raw = anchor["href"].strip()
                clean_url = get_clean_outbound_url(raw, current_page_url)
                if clean_url:
                    clean_url_list.append((clean_url, 1))

            # Creating the clean directory response with the processed information
            clean_text = soup.get_text(separator=" ", strip=True)
            processed_url = {
                "url": response.url,
                "status_code": response.status_code,
                "crawled_at": timestamp,
                "metadata": {
                    "title": title,
                    "description": description,
                    "language": lang,
                },
                "content": {"h1": h1, "h2": h2, "clean_text": clean_text},
                "outbound_links": clean_url_list,
            }
            return processed_url
