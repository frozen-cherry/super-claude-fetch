# Super Claude Fetch

[English](README_EN.md)

一个本地 MCP 服务器，让 Claude 拥有**无头浏览器**能力 —— 能访问任何 JavaScript 渲染的网站，包括 SPA 应用、反爬页面和动态 Web App。

普通 HTTP fetch 搞不定的，它来搞定。

基于 [Playwright](https://playwright.dev/) + [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 构建。

## 为什么需要这个？

Claude 内置的 `WebFetch` 走的是普通 HTTP 请求。静态页面没问题，但现代 Web 应用**全靠 JS 渲染**，HTTP 拿到的就是个空壳：

| 网站 | 普通 HTTP Fetch | Super Claude Fetch |
|------|----------------|-------------------|
| **Hyperliquid** | `Hyperliquid`（11 字符，只有标题） | 完整交易界面：实时价格、盘口、24h 成交量（1499 字符） |
| **Lighter DEX** | `Lighter`（7 字符） | 完整页面结构、交易对、市场数据（880 字符） |
| **Twitter/X** | `JavaScript is not available`（报错页） | 推文原文、作者、时间戳、互动数据（610 字符） |
| **小红书** | 空白或登录墙 | 帖子标题、作者、正文内容、点赞收藏数 |

## 三个工具

| 工具 | 用途 |
|------|------|
| `fetch` | 打开网页，等 JS 渲染完，返回页面文本。主力工具。 |
| `screenshot` | 对任意网页截图，返回 PNG。 |
| `execute` | 在页面上执行自定义 JS + 可选拦截 API 响应。进阶玩法。 |

## 安装

### 依赖

```bash
pip install playwright mcp
playwright install chromium
```

### 安装为 Agent Skill（纯 Skill 方式，可选）

当前仓库已包含可直接使用的 skill 目录：

- `skills/super-claude-fetch/`

可安装到 Codex Skills 目录：

```bash
mkdir -p "$CODEX_HOME/skills"
cp -R ./skills/super-claude-fetch "$CODEX_HOME/skills/super-claude-fetch"
```

也可安装到 Claude Skills 目录：

```bash
mkdir -p "$HOME/.claude/skills"
cp -R ./skills/super-claude-fetch "$HOME/.claude/skills/super-claude-fetch"
```

然后在对话中显式调用：

```text
用 $super-claude-fetch 抓取这个 JS 页面内容：https://example.com
```

Skill 内部会直接调用：

- `scripts/pw_ops.py fetch`
- `scripts/pw_ops.py screenshot`
- `scripts/pw_ops.py execute`

无需配置 MCP server。

### 配置 Claude Desktop

编辑配置文件：
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "playwright-fetch": {
      "command": "python",
      "args": ["你的路径/server.py"]
    }
  }
}
```

重启 Claude Desktop，工具自动出现。

### 配置 Claude Code

在 MCP 设置中添加：

```json
{
  "playwright-fetch": {
    "command": "python",
    "args": ["你的路径/server.py"],
    "type": "stdio"
  }
}
```

## 工作原理

1. **懒加载浏览器** — 首次调用时启动 Chromium，之后复用，无重复冷启动。
2. **智能等待** — 轮询页面直到出现有意义的内容（或最多 15 秒），快站秒返，慢站耐心等。
3. **页面隔离** — 每次请求独立 context，无 cookie/状态泄漏。
4. **自动降级** — MCP instructions 告诉 Claude：普通 fetch 拿不到内容时，自动切换到这个工具，不需要用户手动提醒。

## 用法示例

### 基础抓取
```
用户："Hyperliquid 上现在交易什么？"
Claude：[自动调用 playwright-fetch.fetch] → 拿到完整交易页面和实时价格
```

### API 拦截
```python
# 加载页面的同时拦截 DeFi 后端 API 响应
execute(
    url="https://app.lighter.xyz/trade/",
    script="() => document.title",
    intercept_pattern="zklighter.elliot.ai/api"
)
# 返回：orderBookDetails, candles, assetDetails 等原始数据
```

### 截图
```python
screenshot(url="https://app.hyperliquid.xyz/trade/")
# 返回：base64 编码的 PNG 截图
```

## 性能对比

| 指标 | HTTP Fetch | Super Claude Fetch |
|------|-----------|-------------------|
| 速度 | ~0.5-1s | ~3-5s |
| JS 渲染 | 不支持 | 支持 |
| SPA 应用 | 不支持 | 支持 |
| 反爬绕过 | 不支持 | 支持 |
| API 拦截 | 不支持 | 支持 |

3-5 秒的开销是跑真实浏览器的代价。HTTP fetch 能搞定的站不需要用这个，**这个工具专治 HTTP fetch 搞不定的站**。

## License

MIT
