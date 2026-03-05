"""
Lighter DEX 市场数据抓取脚本
用 Playwright headless browser 打开 Lighter 交易页面，提取所有标的数据

安装依赖：
  pip install playwright
  playwright install chromium

运行：
  python lighter_scraper.py
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def scrape_lighter():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        # 收集 API 请求（如果能拦截到原始数据更好）
        api_responses = []

        async def handle_response(response):
            url = response.url
            # 拦截可能的市场数据 API
            if any(
                kw in url.lower()
                for kw in ["market", "ticker", "perp", "stat", "info", "orderbook"]
            ):
                try:
                    body = await response.text()
                    api_responses.append({"url": url, "status": response.status, "body": body[:2000]})
                except:
                    pass

        page.on("response", handle_response)

        print("正在打开 Lighter 交易页面...")
        await page.goto("https://app.lighter.xyz/trade/", wait_until="domcontentloaded", timeout=60000)

        # 等待页面 JS 渲染完成（SPA 站点不会达到 networkidle）
        await page.wait_for_timeout(10000)

        print("正在提取页面数据...")

        # 方案 A：从 DOM 提取市场列表
        dom_data = await page.evaluate(
            """
        () => {
            // 尝试提取表格或列表中的市场数据
            const results = [];
            
            // 通用方案：提取所有文本内容中包含市场标识的元素
            const allElements = document.querySelectorAll('*');
            const marketKeywords = ['BTC', 'ETH', 'SOL', 'KRCOMP', 'SAMSUNG', 'SKHYNIX', 'HYUNDAI', 
                                     'SPY', 'QQQ', 'DIA', 'AAPL', 'TSLA', 'NVDA', 'URA', 'IWM', 'BOTZ', 'MAGS'];
            
            // 找所有看起来像市场行的元素
            const rows = document.querySelectorAll('tr, [role="row"], [class*="row"], [class*="market"], [class*="pair"]');
            rows.forEach(row => {
                const text = row.innerText;
                if (text && marketKeywords.some(kw => text.includes(kw))) {
                    results.push(text.replace(/\\n/g, ' | '));
                }
            });
            
            // 如果没找到 row，尝试更宽泛地搜索
            if (results.length === 0) {
                const allText = document.body.innerText;
                return { raw_text: allText.substring(0, 10000), rows: [] };
            }
            
            return { rows: results, raw_text: null };
        }
        """
        )

        # 方案 B：检查拦截到的 API 响应
        print(f"\n拦截到 {len(api_responses)} 个可能的 API 请求:")
        for resp in api_responses:
            print(f"  URL: {resp['url']}")
            print(f"  Status: {resp['status']}")
            print(f"  Body preview: {resp['body'][:200]}")
            print()

        # 输出 DOM 提取结果
        if dom_data.get("rows"):
            print(f"\n从 DOM 提取到 {len(dom_data['rows'])} 个市场:")
            for row in dom_data["rows"]:
                print(f"  {row}")
        elif dom_data.get("raw_text"):
            print("\n未找到结构化行，原始页面文本前 3000 字符:")
            print(dom_data["raw_text"][:3000])

        # 额外尝试：看看页面上一共有多少个可交易标的
        market_count = await page.evaluate(
            """
        () => {
            const text = document.body.innerText;
            // 数一下常见的市场标识符
            const symbols = text.match(/\\b[A-Z]{2,6}\\b/g) || [];
            const unique = [...new Set(symbols)];
            return { total_unique_symbols: unique.length, symbols: unique.slice(0, 100) };
        }
        """
        )
        print(f"\n页面上检测到的唯一符号: {market_count['total_unique_symbols']} 个")
        print(f"前 100 个: {market_count['symbols']}")

        await browser.close()
        print("\n完成！")


if __name__ == "__main__":
    asyncio.run(scrape_lighter())