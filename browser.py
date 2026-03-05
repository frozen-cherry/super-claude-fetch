"""
Browser lifecycle manager.
Lazy-init singleton browser, per-call pages.
"""

from playwright.async_api import async_playwright, Browser, Page

_playwright = None
_browser: Browser | None = None

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


async def get_browser() -> Browser:
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
    return _browser


async def new_page() -> Page:
    browser = await get_browser()
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=DEFAULT_UA,
    )
    return await context.new_page()


async def cleanup():
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None
