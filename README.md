# Super Claude Fetch

A local MCP server that gives Claude the ability to access **any** website — even JavaScript-heavy SPAs, anti-bot pages, and dynamic web apps that regular HTTP fetch simply cannot handle.

Built with [Playwright](https://playwright.dev/) headless browser + [MCP (Model Context Protocol)](https://modelcontextprotocol.io/).

## The Problem

Claude's built-in `WebFetch` uses plain HTTP requests. This works fine for static pages, but **completely fails** on modern web apps:

| Website | HTTP Fetch | Super Claude Fetch |
|---------|-----------|-------------------|
| **Hyperliquid DEX** | `Hyperliquid` (11 chars, just a title) | Full trading UI with live prices, order book, 24h volume (1499 chars) |
| **Lighter DEX** | `Lighter` (7 chars) | Complete page structure with market data, trading pairs (880 chars) |
| **Twitter/X** | `JavaScript is not available` (error page) | Full tweet content, author, timestamps, engagement metrics (610 chars) |
| **Xiaohongshu** | Blank or login wall | Post title, author, full text content, engagement stats |

**Why?** Most modern sites are SPAs (Single Page Applications) that render content with JavaScript. A plain HTTP GET only returns an empty HTML shell.

## Tools

| Tool | Description |
|------|-------------|
| `fetch` | Navigate to a URL, render JavaScript, return page text. The primary tool. |
| `screenshot` | Take a PNG screenshot of any page. |
| `execute` | Run custom JavaScript on a page + optionally intercept API responses. |

## Setup

### Prerequisites

```bash
pip install playwright mcp
playwright install chromium
```

### Configure Claude Desktop

Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "playwright-fetch": {
      "command": "python",
      "args": ["C:\\path\\to\\server.py"]
    }
  }
}
```

Restart Claude Desktop. The tools will appear automatically.

### Configure Claude Code

Add to your Claude Code MCP settings:

```json
{
  "playwright-fetch": {
    "command": "python",
    "args": ["C:\\path\\to\\server.py"],
    "type": "stdio"
  }
}
```

## How It Works

1. **Lazy browser init** — A Chromium instance starts on first use and stays alive for subsequent calls. No cold start penalty after the first request.
2. **Smart wait** — Instead of a fixed delay, the server polls the page until meaningful content appears (or 15s max). This handles fast sites quickly while giving slow SPAs enough time.
3. **Page isolation** — Each request gets a fresh browser context. No cookie/state leakage between calls.
4. **Auto-fallback instructions** — The MCP server tells Claude to use it automatically when regular fetch returns empty or useless content. No manual prompting needed.

## Examples

### Basic fetch
```
User: "What's trading on Hyperliquid right now?"
Claude: [uses playwright-fetch.fetch] → gets full trading page with live prices
```

### API interception
```python
# Intercept DeFi API responses while loading a page
execute(
    url="https://app.lighter.xyz/trade/",
    script="() => document.title",
    intercept_pattern="zklighter.elliot.ai/api"
)
# Returns: orderBookDetails, candles, assetDetails, etc.
```

### Screenshot
```python
screenshot(url="https://app.hyperliquid.xyz/trade/")
# Returns: base64 PNG of the rendered page
```

## Performance

| Metric | HTTP Fetch | Super Claude Fetch |
|--------|-----------|-------------------|
| Speed | ~0.5-1s | ~3-5s |
| JS rendering | No | Yes |
| SPA support | No | Yes |
| Anti-bot bypass | No | Yes |
| API interception | No | Yes |

The 3-5s overhead is the cost of running a real browser. For sites where HTTP fetch works fine, keep using it. This tool shines exactly where HTTP fetch fails.

## License

MIT
