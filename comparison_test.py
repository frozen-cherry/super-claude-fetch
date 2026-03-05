"""
对比测试：普通 HTTP fetch vs Playwright headless browser
"""

import asyncio
import json
import sys
import time
import httpx
from server import fetch as playwright_fetch

# Fix Windows GBK encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

URLS = [
    ("Hyperliquid DEX", "https://app.hyperliquid.xyz/trade/"),
    ("Lighter DEX", "https://app.lighter.xyz/trade/"),
    ("X/Twitter Post", "https://x.com/RobinhoodApp/status/2029365914764742913"),
]

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


async def http_fetch(url: str) -> dict:
    """Plain HTTP GET."""
    start = time.time()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url, headers={"User-Agent": UA})
            elapsed = round(time.time() - start, 2)
            # Extract visible text approximation: strip HTML tags
            from html.parser import HTMLParser
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.parts = []
                    self._skip = False
                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style", "noscript"):
                        self._skip = True
                def handle_endtag(self, tag):
                    if tag in ("script", "style", "noscript"):
                        self._skip = False
                def handle_data(self, data):
                    if not self._skip:
                        t = data.strip()
                        if t:
                            self.parts.append(t)
            ext = TextExtractor()
            ext.feed(resp.text)
            text = "\n".join(ext.parts)
            return {
                "status": resp.status_code,
                "text_len": len(text),
                "text_preview": text[:800],
                "elapsed": elapsed,
            }
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        return {"error": str(e), "elapsed": elapsed}


async def pw_fetch(url: str) -> dict:
    """Playwright headless browser fetch."""
    start = time.time()
    result = await playwright_fetch(url, timeout=60000)
    elapsed = round(time.time() - start, 2)
    data = json.loads(result)
    if "error" in data:
        return {"error": data["error"], "elapsed": elapsed}
    return {
        "title": data.get("title"),
        "text_len": len(data.get("text", "")),
        "text_preview": data.get("text", "")[:800],
        "elapsed": elapsed,
    }


def print_result(label: str, result: dict):
    print(f"  [{label}]")
    if "error" in result:
        print(f"    Error: {result['error']}")
        print(f"    Time: {result['elapsed']}s")
        return
    print(f"    Status: {result.get('status', 'OK')}")
    if result.get("title"):
        print(f"    Title: {result['title']}")
    print(f"    Text length: {result['text_len']} chars")
    print(f"    Time: {result['elapsed']}s")
    print(f"    Preview:")
    preview = result["text_preview"].replace("\n", "\n      ")
    print(f"      {preview}")


async def main():
    print("=" * 70)
    print("  HTTP Fetch vs Playwright Headless Browser - Comparison Test")
    print("=" * 70)

    for name, url in URLS:
        print(f"\n{'─' * 70}")
        print(f"  {name}")
        print(f"  {url}")
        print(f"{'─' * 70}")

        # Run HTTP fetch first
        try:
            http_result = await http_fetch(url)
        except Exception as e:
            http_result = {"error": str(e), "elapsed": 0}
        print_result("HTTP Fetch", http_result)

        print()

        # Then Playwright
        try:
            pw_result = await pw_fetch(url)
        except Exception as e:
            pw_result = {"error": str(e), "elapsed": 0}
        print_result("Playwright", pw_result)

        # Verdict
        print()
        http_len = http_result.get("text_len", 0)
        pw_len = pw_result.get("text_len", 0)
        if "error" in http_result and "error" not in pw_result:
            print(f"    >> Verdict: HTTP failed, Playwright succeeded")
        elif http_len < 100 and pw_len > 100:
            print(f"    >> Verdict: HTTP got no useful content, Playwright got {pw_len} chars")
        elif pw_len > http_len * 2:
            print(f"    >> Verdict: Playwright got {pw_len/http_len:.1f}x more content")
        elif pw_len > 0 and http_len > 0:
            print(f"    >> Verdict: Both got content (HTTP: {http_len}, PW: {pw_len})")
        else:
            print(f"    >> Verdict: Both struggled")

    print(f"\n{'=' * 70}")
    print("  Done")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
