---
name: scrapling
description: |
  Use this skill for web scraping tasks using the Scrapling framework.
  Triggers when user mentions "scrapling", "scrape a website", "web scraping with python",
  "bypass Cloudflare", "anti-bot bypass", "adaptive scraping", "StealthyFetcher",
  "DynamicFetcher", "browser automation for scraping", "crawl website", "parse HTML with python",
  "scrape protected website", "Cloudflare Turnstile", "TLS fingerprinting", "spider crawl",
  "extract data from website", "web crawler python", "headless browser scraping",
  "stealth scraping", "proxy rotation scraping", "session-based scraping",
  or asks to extract, crawl, or parse data from websites using Python.
  Also trigger when the user wants to convert web pages to markdown, scrape JS-rendered SPAs,
  handle CAPTCHAs, rotate proxies, or build multi-page crawlers.
  Scrapling is installed locally (v0.4.2, Python 3.14) at
  /Users/stevensanders/Library/Python/3.14/lib/python/site-packages/scrapling/.
tools: Read, Bash, Edit, Write, Glob, Grep
---

# Scrapling Web Scraping Framework

Scrapling is an adaptive Python web scraping framework (v0.4.2, Python 3.10+) that handles everything from parsing static HTML to bypassing Cloudflare with full browser automation. It is **already installed** on this system.

## Quick Decision Matrix

| Scenario | Tool | Import |
|----------|------|--------|
| Parse HTML string | `Selector` | `from scrapling.parser import Selector` |
| Scrape static page | `Fetcher` | `from scrapling.fetchers import Fetcher` |
| Async static page | `AsyncFetcher` | `from scrapling.fetchers import AsyncFetcher` |
| Scrape JS-heavy page | `DynamicFetcher` | `from scrapling.fetchers import DynamicFetcher` |
| Bypass Cloudflare/anti-bot | `StealthyFetcher` | `from scrapling.fetchers import StealthyFetcher` |
| Crawl multiple pages | `Spider` | `from scrapling.spiders import Spider, Response` |
| Reuse HTTP connections | `FetcherSession` | `from scrapling.fetchers import FetcherSession` |
| Reuse browser sessions | `StealthySession` / `DynamicSession` | `from scrapling.fetchers import StealthySession` |
| Async browser session | `AsyncDynamicSession` / `AsyncStealthySession` | `from scrapling.fetchers import AsyncStealthySession` |
| Rotate proxies | `ProxyRotator` | `from scrapling.fetchers import ProxyRotator` |
| Survive site redesigns | Adaptive mode | `Selector(html, adaptive=True, url='...')` |
| CLI quick extract | `scrapling extract` | Shell command, no code needed |

## Choosing the Right Fetcher

Think of it as a ladder — start at the simplest rung and climb only if needed:

1. **Fetcher** — fast HTTP via curl_cffi. Use when the page works without JavaScript. Supports `get`, `post`, `put`, `delete`.
2. **DynamicFetcher** — launches a Playwright browser. Use when the page requires JS rendering (SPAs, lazy-loaded content). Alias: `PlayWrightFetcher`.
3. **StealthyFetcher** — launches a patched Chromium (patchright) with anti-detection. Use when the site actively blocks bots (Cloudflare, DataDome, etc.).

Each level is slower but more capable. Don't reach for StealthyFetcher when Fetcher will do.

---

## Core Patterns

### 1. Parse Existing HTML

```python
from scrapling.parser import Selector

page = Selector(html_content)

# CSS selection (supports pseudo-elements)
titles = page.css('h1::text').getall()
link = page.css('a::attr(href)').get()

# XPath (supports variables via kwargs)
items = page.xpath('//div[@class="item"]')
specific = page.xpath('//div[@id=$myid]', myid='target')

# BeautifulSoup-style
divs = page.find_all('div', class_='product')
first = page.find('span', id='price')

# Text and regex search
el = page.find_by_text('Add to Cart', partial=True, case_sensitive=False)
prices = page.find_by_regex(r'\$[\d\.]+', first_match=False)

# Find similar elements (great for extracting repeated patterns)
similar = element.find_similar(similarity_threshold=0.2)

# Navigation
parent = element.parent
kids = element.children
sibs = element.siblings
nxt = element.next
prev = element.previous
ancestors = element.path  # full ancestry to root

# Rich text extraction
all_text = page.get_all_text(separator="\n", strip=True, ignore_tags=("script", "style"))

# URL handling
full_url = element.urljoin('/relative/path')

# Class checking
if element.has_class('active'):
    ...
```

### 2. Fetch Static Pages (HTTP)

```python
from scrapling.fetchers import Fetcher

# GET with stealth headers and browser fingerprint
page = Fetcher.get('https://example.com', stealthy_headers=True, impersonate='chrome')
data = page.css('.product-title::text').getall()

# POST with JSON body
page = Fetcher.post('https://api.example.com', json={'query': 'test'})

# PUT and DELETE also available
page = Fetcher.put(url, json=payload)
page = Fetcher.delete(url)

# Random browser fingerprint per request (picks one each time)
page = Fetcher.get(url, impersonate=['chrome', 'firefox', 'edge'])
```

### 3. Fetch Dynamic Pages (JS Rendering)

```python
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch(
    'https://spa-site.com',
    headless=True,
    network_idle=True,             # wait for network to settle (500ms+ quiet)
    wait_selector='div.loaded',    # wait for specific element
    disable_resources=True,        # block fonts/images (~25% speed boost)
    blocked_domains={'ads.com'},   # block specific domains
    locale='en-US',
    timezone_id='America/New_York',
)

# Custom page automation before extraction
async def scroll_and_click(page):
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await page.click('button.load-more')
    await page.wait_for_timeout(2000)

page = DynamicFetcher.fetch(url, page_action=scroll_and_click)
```

### 4. Bypass Anti-Bot Protection

```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch(
    'https://protected-site.com',
    solve_cloudflare=True,      # auto-solve Turnstile/Interstitial challenges
    block_webrtc=True,          # prevent real IP leak via WebRTC
    hide_canvas=True,           # add noise to canvas fingerprinting
    allow_webgl=True,           # keep WebGL enabled (default True)
    real_chrome=True,           # use your installed Chrome instead of Chromium
    timeout=60000,              # Cloudflare needs at least 60s
    google_search=True,         # set Google as referer (looks organic)
    extra_flags=['--disable-gpu', '--window-size=1366,768'],
)

# Inject custom JS that runs on every page load
page = StealthyFetcher.fetch(url, init_script='/path/to/stealth_overrides.js')

# Connect to an already-running Chrome via CDP
page = StealthyFetcher.fetch(url, cdp_url='ws://localhost:9222/devtools/browser/...')

# Persistent browser profile (keeps cookies/localStorage between runs)
page = StealthyFetcher.fetch(url, user_data_dir='/path/to/chrome-profile')
```

### 5. Reuse Sessions (10x Faster)

Sessions keep connections alive and persist cookies automatically.

```python
# HTTP sessions
from scrapling.fetchers import FetcherSession

with FetcherSession(impersonate='chrome') as session:
    page1 = session.get('https://example.com/page1')
    page2 = session.get('https://example.com/page2')  # cookies persist

# Browser sessions (Playwright)
from scrapling.fetchers import DynamicSession

with DynamicSession(headless=True) as session:
    page = session.fetch('https://example.com')

# Stealth browser sessions
from scrapling.fetchers import StealthySession

with StealthySession(real_chrome=True, block_webrtc=True) as session:
    page = session.fetch('https://protected.com')

# Async versions available too
from scrapling.fetchers import AsyncDynamicSession, AsyncStealthySession

async with AsyncStealthySession(solve_cloudflare=True) as session:
    page = await session.fetch('https://protected.com')
```

### 6. Spider (Multi-Page Crawl)

```python
from scrapling.spiders import Spider, Response

class ProductSpider(Spider):
    name = "products"
    start_urls = ["https://example.com/products"]
    allowed_domains = {"example.com"}       # stay on-domain
    concurrent_requests = 4                  # parallel requests
    concurrent_requests_per_domain = 2       # rate limit per domain
    download_delay = 0.5                     # seconds between requests

    async def parse(self, response: Response):
        for item in response.css('.product'):
            yield {
                "name": item.css('.title::text').get(''),
                "price": item.css('.price::text').get(''),
                "url": response.urljoin(item.css('a::attr(href)').get('')),
            }
        # Follow pagination
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

result = ProductSpider().run()

# Export results
result.items.to_json('products.json')
result.items.to_jsonl('products.jsonl')  # newline-delimited JSON

# Crawl statistics
stats = result.stats
print(f"Scraped {stats.items_scraped} items in {stats.elapsed_seconds:.1f}s")
print(f"RPS: {stats.requests_per_second:.1f}")
print(f"Status codes: {stats.response_status_count}")
```

#### Spider with Custom Sessions

Override `configure_sessions` to use browser-based fetchers in your spider:

```python
class StealthSpider(Spider):
    name = "stealth_spider"
    start_urls = ["https://protected-site.com"]

    def configure_sessions(self, manager):
        manager.add(
            'stealth',
            StealthySession(solve_cloudflare=True, real_chrome=True),
            default=True,
            lazy=True,  # only starts when first used
        )

    async def parse(self, response):
        yield {"title": response.css('h1::text').get()}
```

#### Pause & Resume Crawls

Pass `crawldir` to enable checkpointing — the spider saves its state periodically and can resume after interruption:

```python
spider = ProductSpider(crawldir='/tmp/crawl_state', interval=60.0)
result = spider.run()  # resumes from checkpoint if one exists
```

#### Spider Lifecycle Hooks

```python
class MySpider(Spider):
    async def on_start(self, resuming=False):
        """Called before crawl. resuming=True if loading checkpoint."""
        if resuming:
            print("Resuming previous crawl...")

    async def on_close(self):
        """Called after crawl finishes."""

    async def on_error(self, request, error):
        """Handle request errors."""
        print(f"Error on {request.url}: {error}")

    async def on_scraped_item(self, item):
        """Post-process each scraped item. Return None to drop it."""
        if not item.get('price'):
            return None  # drop items without price
        return item
```

### 7. Proxy Rotation

```python
from scrapling.fetchers import ProxyRotator, FetcherSession

rotator = ProxyRotator([
    'http://proxy1:8080',
    'http://user:pass@proxy2:8080',
    'socks5://proxy3:1080',
    {"server": "http://proxy4:8080", "username": "u", "password": "p"},
])

# Works with any session type
with FetcherSession(proxy_rotator=rotator) as session:
    page = session.get(url)  # auto-rotates through proxies

# Custom rotation strategy
def random_rotation(proxies, current_index):
    import random
    idx = random.randint(0, len(proxies) - 1)
    return proxies[idx], idx

rotator = ProxyRotator(proxies, strategy=random_rotation)
```

### 8. Adaptive Mode (Survive Redesigns)

Adaptive mode saves element fingerprints so scrapers keep working even after a site redesign changes class names or restructure.

```python
# First run — save element locations
page = Selector(html, adaptive=True, url='https://example.com')
price = page.css('#price', auto_save=True)  # fingerprint saved to SQLite

# Later, after site redesign — relocate elements
page = Selector(new_html, adaptive=True, url='https://example.com')
price = page.css('#price')  # finds element even if ID changed

# Manual save/retrieve
page.save(element, 'my_price_element')
data = page.retrieve('my_price_element')

# Custom storage backend (default: SQLite at elements_storage.db)
from scrapling.core.storage import SQLiteStorageSystem
page = Selector(html, adaptive=True, url=url,
    storage=SQLiteStorageSystem,
    storage_args={'storage_file': 'my_elements.db'})
```

---

## Response Object Reference

Every fetcher returns a Response that extends Selector, so all parsing methods work directly on it. Additional properties:

| Property | Type | Description |
|----------|------|-------------|
| `status` | int | HTTP status code |
| `reason` | str | Status reason phrase |
| `cookies` | dict | Response cookies |
| `headers` | dict | Response headers |
| `request_headers` | dict | Headers that were sent |
| `history` | list | Redirect chain |
| `body` | bytes | Raw response body |
| `meta` | dict | Custom metadata from Request |

---

## CLI Quick Reference

No code needed for simple extractions:

```bash
# Static HTTP GET → save as markdown, HTML, or text
scrapling extract get 'https://example.com' output.md
scrapling extract get 'https://example.com' output.html --css-selector '.main-content'

# POST with JSON
scrapling extract post 'https://api.com/data' result.json --json '{"q":"test"}'

# Browser-rendered fetch
scrapling extract fetch 'https://spa-site.com' output.md --headless --network-idle

# Stealth fetch (bypasses protection)
scrapling extract stealthy 'https://protected.com' output.md --real-chrome --timeout 60000

# With custom headers and cookies
scrapling extract get URL output.md -H 'Authorization: Bearer token' --cookies 'session=abc123'

# Interactive IPython shell
scrapling shell

# Install browser dependencies
scrapling install
```

---

## Advanced Features

| Feature | Usage |
|---------|-------|
| Random browser per request | `impersonate=['chrome', 'firefox', 'edge']` |
| Inject JS on every page | `init_script='/absolute/path/to/script.js'` |
| Remote browser via CDP | `cdp_url='ws://host:9222/...'` |
| Custom Chromium flags | `extra_flags=['--disable-gpu', '--window-size=1366,768']` |
| Persistent browser profile | `user_data_dir='/path/to/profile'` |
| Adaptive element tracking | `page.css('#price', auto_save=True)` then `adaptive=True` |
| Lazy sessions in Spider | `manager.add('id', session, lazy=True)` |
| XPath variables | `page.xpath('//div[@id=$x]', x='myid')` |
| Large HTML documents | `Selector(html, huge_tree=True)` (default) |
| Preserve HTML comments | `Selector(html, keep_comments=True)` |
| Dedup fingerprint tuning | `fp_include_kwargs=True`, `fp_keep_fragments=True` on Spider |
| Blocked request detection | Status codes 401, 403, 407, 429, 444, 500-504 auto-detected |
| MCP server mode | `scrapling mcp --http --port 8080` |

## Key Constraints

- Python 3.10+ required (installed: 3.14)
- StealthyFetcher uses **patchright** (patched Playwright fork), not standard Playwright
- Cloudflare solving requires `timeout >= 60000`
- `disable_resources=True` blocks fonts, images, and media — don't use if you need those
- Adaptive mode stores fingerprints in SQLite — first run must succeed to build the database
- Spider's `parse()` method must be async and yield dicts (items) or Requests (follow links)

## Common Patterns Reference

For detailed parameter signatures, async patterns, custom type methods (TextHandler, AttributesHandler), storage backends, and the full Spider API, read `references/api-reference.md`.
