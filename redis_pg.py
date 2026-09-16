import requests
import pprint
import asyncio
from crawler import get_clean_outbound_url as get_clean_outbound_url, Crawler
from dotenv import load_dotenv
import math
import logging
import redis.asyncio as redis

import redis.asyncio as redis


async def basic_example():
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    await r.set("foo", "bar")
    value = await r.get("foo")
    print(value)
    # bar
    await r.aclose()


asyncio.run(basic_example())
