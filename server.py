"""
Playwright MCP Server
Headless browser tools for fetching JS-rendered web pages.
"""

import asyncio
import base64
import json
from mcp.server.fastmcp import FastMCP
from browser import new_page, cleanup

mcp = FastMCP(
    "playwright-fetch",
    instructions=(
        "A headless browser that renders pages with full JavaScript support. "
        "WHEN TO USE: Automatically use this tool when:\n"
        "1. A previous fetch/WebFetch returned very short content (< 200 chars), empty body, or just a site title\n"
        "2. A previous fetch returned 'JavaScript is not available/disabled' or similar errors\n"
        "3. The target URL is a known SPA/dynamic site (DeFi apps, Twitter/X, dashboards, web apps)\n"
        "4. The target URL is on a domain known to block simple HTTP requests (x.com, trading platforms, etc.)\n"
        "Do NOT wait for the user to ask — proactively retry with this tool whenever regular fetch fails to get useful content."
    ),
)


@mcp.tool()
async def fetch(
    url: str,
    wait_for: str | None = None,
    timeout: int = 30000,
) -> str:
    """
    Navigate to a URL with a headless browser and return the rendered page text.
    Handles JS-rendered SPAs, dynamic content, and anti-bot pages.

    Use this as a FALLBACK when regular fetch/WebFetch fails or returns
    empty/useless content (e.g., just a title, "JavaScript is disabled", etc.).

    Args:
        url: The URL to navigate to.
        wait_for: Optional CSS selector to wait for before extracting content.
        timeout: Navigation timeout in milliseconds (default 30000).

    Returns:
        JSON string with title, final_url, and text content of the rendered page.
    """
    page = await new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        if wait_for:
            await page.wait_for_selector(wait_for, timeout=timeout)
        else:
            # Smart wait: poll until body has meaningful content or max 15s
            for _ in range(15):
                await page.wait_for_timeout(1000)
                text = await page.inner_text("body")
                if len(text.strip()) > 200:
                    break

        title = await page.title()
        text = await page.inner_text("body")
        final_url = page.url

        return json.dumps(
            {"title": title, "url": final_url, "text": text[:50000]},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await page.context.close()


@mcp.tool()
async def screenshot(
    url: str,
    wait_for: str | None = None,
    timeout: int = 30000,
    full_page: bool = False,
) -> str:
    """
    Take a screenshot of a web page.

    Args:
        url: The URL to navigate to.
        wait_for: Optional CSS selector to wait for before taking screenshot.
        timeout: Navigation timeout in milliseconds (default 30000).
        full_page: Whether to capture the full scrollable page (default False).

    Returns:
        Base64 encoded PNG image data.
    """
    page = await new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        if wait_for:
            await page.wait_for_selector(wait_for, timeout=timeout)
        else:
            await page.wait_for_timeout(3000)

        img_bytes = await page.screenshot(full_page=full_page)
        return base64.b64encode(img_bytes).decode()
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await page.context.close()


@mcp.tool()
async def execute(
    url: str,
    script: str,
    wait_for: str | None = None,
    timeout: int = 30000,
    intercept_pattern: str | None = None,
) -> str:
    """
    Navigate to a URL and execute JavaScript to extract structured data.
    Optionally intercept API responses matching a URL pattern.

    Args:
        url: The URL to navigate to.
        script: JavaScript code to execute in the page context. Must return a value.
        wait_for: Optional CSS selector to wait for before executing script.
        timeout: Navigation timeout in milliseconds (default 30000).
        intercept_pattern: Optional substring to match against response URLs.
            If provided, matching API responses will be captured and included in the result.

    Returns:
        JSON string with the script result and optionally intercepted API responses.
    """
    page = await new_page()
    api_responses = []

    try:
        if intercept_pattern:
            async def on_response(response):
                if intercept_pattern in response.url:
                    try:
                        body = await response.text()
                        api_responses.append({
                            "url": response.url,
                            "status": response.status,
                            "body": body[:5000],
                        })
                    except:
                        pass
            page.on("response", on_response)

        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        if wait_for:
            await page.wait_for_selector(wait_for, timeout=timeout)
        else:
            await page.wait_for_timeout(3000)

        result = await page.evaluate(script)

        output = {"result": result}
        if api_responses:
            output["intercepted_apis"] = api_responses

        return json.dumps(output, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await page.context.close()


if __name__ == "__main__":
    mcp.run()
