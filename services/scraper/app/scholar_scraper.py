import time
from typing import Generator
from scholarly import scholarly, ProxyGenerator
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from app.config import settings


def setup_proxy() -> None:
    if settings.scholar_use_proxy:
        pg = ProxyGenerator()
        pg.Tor_External(tor_sock_port=9050, tor_control_port=9051)
        scholarly.use_proxy(pg)
        logger.info("Proxy configured via Tor")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_articles(query: str) -> Generator[dict, None, None]:
    for result in scholarly.search_pubs(query):
        filled = scholarly.fill(result)
        yield {
            "title": filled.get("bib", {}).get("title"),
            "abstract": filled.get("bib", {}).get("abstract"),
            "authors": filled.get("bib", {}).get("author", []),
            "year": filled.get("bib", {}).get("pub_year"),
            "venue": filled.get("bib", {}).get("venue"),
            "citations": filled.get("num_citations", 0),
            "url": filled.get("pub_url"),
            "scholar_id": filled.get("scholar_id"),
            "doi": filled.get("externalids", {}).get("DOI"),
        }
        time.sleep(settings.scrape_delay_seconds)
