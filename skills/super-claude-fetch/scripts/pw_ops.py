#!/usr/bin/env python3
"""
Pure Playwright operations for skill usage (no MCP dependency).

Commands:
  - fetch: render page and return text content as JSON
  - screenshot: capture PNG (base64 to stdout or write file)
  - execute: run JS in page context and optionally intercept API responses
"""

import argparse
import asyncio
import base64
import json
from pathlib import Path

from playwright.async_api import async_playwright

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


async def _new_page(playwright):
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=DEFAULT_UA,
    )
    page = await context.new_page()
    return browser, context, page


async def cmd_fetch(args):
    async with async_playwright() as p:
        browser, context, page = await _new_page(p)
        try:
            await page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout)
            if args.wait_for:
                await page.wait_for_selector(args.wait_for, timeout=args.timeout)
            else:
                # Poll for meaningful content for at most 15s.
                for _ in range(15):
                    await page.wait_for_timeout(1000)
                    text = await page.inner_text("body")
                    if len(text.strip()) > 200:
                        break

            title = await page.title()
            text = await page.inner_text("body")
            output = {
                "title": title,
                "url": page.url,
                "text": text[: args.max_chars],
            }
            print(json.dumps(output, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            raise
        finally:
            await context.close()
            await browser.close()


async def cmd_screenshot(args):
    async with async_playwright() as p:
        browser, context, page = await _new_page(p)
        try:
            await page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout)
            if args.wait_for:
                await page.wait_for_selector(args.wait_for, timeout=args.timeout)
            else:
                await page.wait_for_timeout(3000)

            img_bytes = await page.screenshot(full_page=args.full_page)
            if args.out:
                out_path = Path(args.out)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(img_bytes)
                print(json.dumps({"path": str(out_path), "bytes": len(img_bytes)}))
            else:
                print(base64.b64encode(img_bytes).decode("utf-8"))
        except Exception as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            raise
        finally:
            await context.close()
            await browser.close()


async def cmd_execute(args):
    script = args.script
    if args.script_file:
        script = Path(args.script_file).read_text(encoding="utf-8")
    if not script:
        raise ValueError("Provide --script or --script-file")

    api_responses = []

    async with async_playwright() as p:
        browser, context, page = await _new_page(p)
        try:
            if args.intercept_pattern:

                async def on_response(response):
                    if args.intercept_pattern in response.url:
                        try:
                            body = await response.text()
                            api_responses.append(
                                {
                                    "url": response.url,
                                    "status": response.status,
                                    "body": body[: args.max_body_chars],
                                }
                            )
                        except Exception:
                            return

                page.on("response", on_response)

            await page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout)
            if args.wait_for:
                await page.wait_for_selector(args.wait_for, timeout=args.timeout)
            else:
                await page.wait_for_timeout(3000)

            result = await page.evaluate(script)
            output = {"result": result}
            if api_responses:
                output["intercepted_apis"] = api_responses[: args.max_intercepts]
            print(json.dumps(output, ensure_ascii=False, default=str))
        except Exception as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            raise
        finally:
            await context.close()
            await browser.close()


def build_parser():
    parser = argparse.ArgumentParser(description="Playwright operations for pure skills")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch JS-rendered page text")
    fetch_parser.add_argument("--url", required=True, help="Target URL")
    fetch_parser.add_argument("--wait-for", help="Optional CSS selector")
    fetch_parser.add_argument("--timeout", type=int, default=30000, help="Timeout in ms")
    fetch_parser.add_argument(
        "--max-chars",
        type=int,
        default=50000,
        help="Maximum text characters to return",
    )
    fetch_parser.set_defaults(func=cmd_fetch)

    screenshot_parser = subparsers.add_parser("screenshot", help="Take a page screenshot")
    screenshot_parser.add_argument("--url", required=True, help="Target URL")
    screenshot_parser.add_argument("--wait-for", help="Optional CSS selector")
    screenshot_parser.add_argument("--timeout", type=int, default=30000, help="Timeout in ms")
    screenshot_parser.add_argument("--full-page", action="store_true", help="Capture full page")
    screenshot_parser.add_argument(
        "--out",
        help="Optional file path to write PNG. If omitted, prints base64 PNG",
    )
    screenshot_parser.set_defaults(func=cmd_screenshot)

    execute_parser = subparsers.add_parser("execute", help="Execute JS and return result JSON")
    execute_parser.add_argument("--url", required=True, help="Target URL")
    execute_parser.add_argument("--script", help="JavaScript snippet to evaluate")
    execute_parser.add_argument("--script-file", help="Path to JavaScript snippet file")
    execute_parser.add_argument("--wait-for", help="Optional CSS selector")
    execute_parser.add_argument("--timeout", type=int, default=30000, help="Timeout in ms")
    execute_parser.add_argument(
        "--intercept-pattern",
        help="Optional substring to match response URL for API interception",
    )
    execute_parser.add_argument(
        "--max-body-chars",
        type=int,
        default=5000,
        help="Maximum chars to keep per intercepted response body",
    )
    execute_parser.add_argument(
        "--max-intercepts",
        type=int,
        default=20,
        help="Maximum intercepted responses to return",
    )
    execute_parser.set_defaults(func=cmd_execute)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        asyncio.run(args.func(args))
    except Exception:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
