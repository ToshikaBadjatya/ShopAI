import html
import json
import re
import ssl
import time
from dataclasses import dataclass
from typing import Type
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin
from urllib.request import Request, urlopen

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "identity",
}
SSL_CONTEXT = ssl.create_default_context()
RESULT_LIMIT = 5


@dataclass
class ProductResult:
    marketplace: str
    title: str
    url: str
    price: str | None = None
    rating: float | None = None
    rank: int = 1

    def to_dict(self) -> dict:
        return {
            "marketplace": self.marketplace,
            "title": self.title,
            "url": self.url,
            "price": self.price,
            "rating": self.rating,
            "rank": self.rank,
        }


class OutfitScraperInput(BaseModel):
    """Input schema for outfit product scraping."""

    outfit_piece: str = Field(
        ...,
        description=(
            "A specific outfit piece to shop for, e.g. 'women white linen shirt' "
            "or 'men blue denim jacket'."
        ),
    )


class OutfitScraperTool(BaseTool):
    name: str = "outfit_product_scraper"
    description: str = (
        "Searches Amazon, Flipkart, Myntra, and Meesho for a given outfit piece "
        "and returns up to 5 bestseller product links with title, price, and rating. "
        "Use this when you need real product URLs from Indian marketplaces."
    )
    args_schema: Type[BaseModel] = OutfitScraperInput

    def _run(self, outfit_piece: str) -> str:
        query = outfit_piece.strip()
        if not query:
            return json.dumps({"error": "outfit_piece must not be empty", "products": []})

        errors: list[str] = []
        by_marketplace: dict[str, list[ProductResult]] = {
            "amazon": [],
            "flipkart": [],
            "myntra": [],
            "meesho": [],
        }

        scrapers = [
            ("amazon", self._scrape_amazon),
            ("flipkart", self._scrape_flipkart),
            ("myntra", self._scrape_myntra),
            ("meesho", self._scrape_meesho),
        ]

        for marketplace, scraper in scrapers:
            try:
                by_marketplace[marketplace] = scraper(query)
            except (HTTPError, URLError, TimeoutError, ValueError) as error:
                errors.append(f"{marketplace}: {error}")
            time.sleep(0.4)

        products = self._select_top_products(by_marketplace)
        payload = {
            "outfit_piece": query,
            "products": [product.to_dict() for product in products],
            "marketplaces_searched": list(by_marketplace.keys()),
            "errors": errors,
        }
        return json.dumps(payload, indent=2)

    def _fetch(self, url: str) -> str:
        request = Request(url, headers=REQUEST_HEADERS)
        with urlopen(request, timeout=20, context=SSL_CONTEXT) as response:
            return response.read().decode("utf-8", errors="replace")

    def _decode_json_string(self, value: str) -> str:
        return bytes(value, "utf-8").decode("unicode_escape")

    def _title_from_slug(self, url: str) -> str:
        for part in reversed(url.split("?")[0].rstrip("/").split("/")):
            if part in {"p", "buy"} or part.startswith("itm"):
                continue
            if part.startswith("www.") or "." in part:
                continue
            return html.unescape(part.replace("-", " ").replace("+", " ").strip()) or "Product"
        return "Product"

    def _extract_amazon_title(self, card: str, asin: str) -> str:
        patterns = [
            r'<span class="a-size-[^"]*a-color-base[^"]*a-text-normal">([^<]+)</span>',
            r'<h2[^>]*>\s*<a[^>]*>\s*<span[^>]*>([^<]+)</span>',
            r'aria-label="([^"]+)"[^>]*class="a-link-normal[^"]*s-line-clamp',
        ]
        for pattern in patterns:
            match = re.search(pattern, card)
            if match:
                return html.unescape(match.group(1).strip())
        return asin

    def _scrape_amazon(self, query: str) -> list[ProductResult]:
        page = self._fetch(
            "https://www.amazon.in/s?"
            f"k={quote(query)}&s=exact-aware-popularity-rank"
        )
        cards = re.split(r'data-component-type="s-search-result"', page)[1:]
        results: list[ProductResult] = []

        for index, card in enumerate(cards, start=1):
            asin_match = re.search(r'data-asin="([A-Z0-9]{10})"', card)
            if not asin_match:
                continue

            asin = asin_match.group(1)
            if asin == "0000000000":
                continue

            price_match = re.search(r'<span class="a-price-whole">([^<]+)</span>', card)
            rating_match = re.search(r'aria-label="([\d.]+) out of 5 stars"', card)
            title = self._extract_amazon_title(card, asin)
            results.append(
                ProductResult(
                    marketplace="amazon",
                    title=title,
                    url=f"https://www.amazon.in/dp/{asin}",
                    price=f"₹{price_match.group(1).strip()}" if price_match else None,
                    rating=float(rating_match.group(1)) if rating_match else None,
                    rank=index,
                )
            )
            if len(results) >= 2:
                break

        if not results:
            raise ValueError("no Amazon bestseller results found")
        return results

    def _scrape_flipkart(self, query: str) -> list[ProductResult]:
        page = self._fetch(
            "https://www.flipkart.com/search?"
            f"q={quote(query)}&sort=popularity"
        )
        hrefs = re.findall(r'href="(/[^"]+/p/itm[^"]+)"', page)
        results: list[ProductResult] = []
        seen_urls: set[str] = set()

        for href in hrefs:
            clean_href = html.unescape(href.split("&amp;")[0])
            url = urljoin("https://www.flipkart.com", clean_href)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            index = page.find(clean_href)
            snippet = page[max(0, index - 4000) : index + 800]
            title_match = re.search(
                r'class="(?:wjcEIp|KzDlHZ|IRpwTa|_4rR01T)">([^<]+)<',
                snippet,
            )
            price_match = re.search(
                r'class="(?:Nx9bqj|_30jeq3)[^"]*">([^<]+)<',
                snippet,
            )
            rating_match = re.search(
                r'class="(?:XQDdHH|_3LWZlK)[^"]*">([\d.]+)<',
                snippet,
            )

            title = (
                html.unescape(title_match.group(1).strip())
                if title_match
                else self._title_from_slug(url)
            )
            results.append(
                ProductResult(
                    marketplace="flipkart",
                    title=title,
                    url=url,
                    price=price_match.group(1).strip() if price_match else None,
                    rating=float(rating_match.group(1)) if rating_match else None,
                    rank=len(results) + 1,
                )
            )
            if len(results) >= 2:
                break

        if not results:
            raise ValueError("no Flipkart bestseller results found")
        return results

    def _scrape_myntra(self, query: str) -> list[ProductResult]:
        slug_query = quote(query.replace(" ", "-"))
        page = self._fetch(f"https://www.myntra.com/{slug_query}?sort=popularity")
        landing_urls = re.findall(r'"landingPageUrl":"([^"]+)"', page)
        names = re.findall(r'"productName":"([^"]+)"', page)
        prices = re.findall(r'"price":(\d+)', page)
        ratings = re.findall(r'"rating":(\d+\.?\d*)', page)

        if not landing_urls:
            page = self._fetch(
                f"https://www.myntra.com/shirts?rawQuery={quote(query)}&sort=popularity"
            )
            landing_urls = re.findall(r'"landingPageUrl":"([^"]+)"', page)
            names = re.findall(r'"productName":"([^"]+)"', page)
            prices = re.findall(r'"price":(\d+)', page)
            ratings = re.findall(r'"rating":(\d+\.?\d*)', page)

        results: list[ProductResult] = []
        for index in range(min(2, len(landing_urls))):
            path = self._decode_json_string(landing_urls[index])
            title = (
                html.unescape(self._decode_json_string(names[index]).strip())
                if index < len(names)
                else self._title_from_slug(path)
            )
            results.append(
                ProductResult(
                    marketplace="myntra",
                    title=title,
                    url=urljoin("https://www.myntra.com/", path),
                    price=f"₹{prices[index]}" if index < len(prices) else None,
                    rating=float(ratings[index]) if index < len(ratings) else None,
                    rank=index + 1,
                )
            )

        if not results:
            raise ValueError("no Myntra bestseller results found")
        return results

    def _scrape_meesho(self, query: str) -> list[ProductResult]:
        product_links = self._search_meesho_links(query)

        if not product_links:
            raise ValueError("no Meesho bestseller results found")

        return [
            ProductResult(
                marketplace="meesho",
                title=self._title_from_slug(link),
                url=link,
                rank=index + 1,
            )
            for index, link in enumerate(product_links)
        ]

    def _search_meesho_links(self, query: str) -> list[str]:
        search_urls = [
            f"https://search.brave.com/search?q={quote(f'site:meesho.com {query}')}",
            f"https://html.duckduckgo.com/html/?q={quote(f'site:meesho.com {query}')}",
        ]
        product_links: list[str] = []
        seen: set[str] = set()

        for search_url in search_urls:
            try:
                search_page = self._fetch(search_url)
            except (HTTPError, URLError):
                continue

            links = re.findall(
                r'(?:href="|uddg=)(https://www\.meesho\.com/[^"&]+|/[^"&]*meesho\.com[^"&]+)',
                search_page,
            )
            for link in links:
                if link.startswith("/"):
                    link = unquote(link)
                if "meesho.com" not in link or "/p/" not in link:
                    continue
                normalized = link.split("?")[0]
                if normalized in seen:
                    continue
                seen.add(normalized)
                product_links.append(normalized)
                if len(product_links) >= 2:
                    return product_links
            time.sleep(0.8)

        return product_links

    def _select_top_products(
        self, by_marketplace: dict[str, list[ProductResult]]
    ) -> list[ProductResult]:
        selected: list[ProductResult] = []
        marketplaces = ("amazon", "flipkart", "myntra", "meesho")

        for marketplace in marketplaces:
            results = by_marketplace.get(marketplace, [])
            if results:
                selected.append(results[0])

        if len(selected) < RESULT_LIMIT:
            for marketplace in marketplaces:
                for product in by_marketplace.get(marketplace, [])[1:]:
                    if len(selected) >= RESULT_LIMIT:
                        break
                    if all(existing.url != product.url for existing in selected):
                        selected.append(product)

        return selected[:RESULT_LIMIT]
