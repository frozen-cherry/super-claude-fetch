---
name: super-claude-fetch
description: Pure local Playwright skill for fetching JavaScript-rendered pages, taking screenshots, and executing page-context extraction scripts without MCP. Use when normal HTTP/WebFetch returns empty or low-value content, when a target site is a SPA or anti-bot page, when visual evidence is needed, or when structured data must be extracted from rendered DOM/API responses.
---

# Super Claude Fetch Skill

Use this skill to run local Playwright operations directly via `scripts/pw_ops.py` (no MCP layer).

## Resolve Skill Directory

Resolve the absolute path that contains this `SKILL.md` as `$SKILL_DIR`, then run commands from that directory.

## Setup Workflow

1. Check runtime dependencies:
```bash
cd $SKILL_DIR
python3 -m pip install playwright
playwright install chromium
```
2. Verify CLI script is available:
```bash
cd $SKILL_DIR
python3 scripts/pw_ops.py --help
```

## Operating Workflow

1. Prefer normal fetch first for simple static pages.
2. Switch to this skill when content is empty, too short, JS-disabled, or obviously incomplete.
3. Run one command:
- `fetch`: Render page and return JSON (`title`, `url`, `text`).
- `screenshot`: Render page and return base64 PNG, or write PNG to file.
- `execute`: Run JS extractor and optionally capture matching API responses.
4. Return concise, structured results to the user (title, final URL, key content, confidence).

## Command Patterns

### `fetch` command

Use for primary content acquisition on SPA/dynamic pages.

```bash
cd $SKILL_DIR
python3 scripts/pw_ops.py fetch \
  --url "https://example.com" \
  --timeout 30000
```

- Use `--wait-for` only when you know a stable selector.
- If content is thin, retry once with `--wait-for`.
- `text` is truncated by `--max-chars` (default `50000`).

### `screenshot` command

Use when user asks for visual verification or layout checks.

Return base64:
```bash
cd $SKILL_DIR
python3 scripts/pw_ops.py screenshot \
  --url "https://example.com"
```

Write file:
```bash
cd $SKILL_DIR
python3 scripts/pw_ops.py screenshot \
  --url "https://example.com" \
  --full-page \
  --out "/tmp/page.png"
```

- Use `--full-page` for documentation/debug captures.
- For dynamic pages, prefer `--wait-for` over fixed delay behavior.

### `execute` command

Use for structured extraction or API-response sniffing during page load.

Inline script:
```bash
cd $SKILL_DIR
python3 scripts/pw_ops.py execute \
  --url "https://example.com" \
  --script "() => ({title: document.title})"
```

Script file:
```bash
cd $SKILL_DIR
cat > /tmp/extractor.js <<'EOF'
() => {
  const title = document.title;
  const h1 = document.querySelector("h1")?.innerText ?? null;
  return { title, h1 };
}
EOF
python3 scripts/pw_ops.py execute \
  --url "https://example.com" \
  --script-file "/tmp/extractor.js"
```

- Keep scripts read-only and deterministic.
- Return JSON-serializable values.
- Use `--intercept-pattern` only for user-requested API families.

## Local Safety Guardrails

Treat this as a high-privilege local skill.

1. Do not browse sensitive local targets (`localhost`, private subnets, metadata endpoints, `file://`) unless user explicitly asks.
2. Ask for confirmation before executing side-effectful scripts in `execute` (clicking, form submission, wallet actions).
3. Summarize command intent before running broad extraction/interception tasks.
4. Avoid exposing raw internal error details unless user asks for debugging output.

## Repository Map

- `scripts/pw_ops.py`: Pure Playwright CLI for `fetch/screenshot/execute`
- `server.py`: MCP server (fetch/screenshot/execute tools)
- `browser.py`: shared browser lifecycle manager
- `comparison_test.py`: HTTP vs Playwright comparison utility
- `lighter_test.py`: target-site exploratory scraper example

## Maintenance Tasks

1. Keep instructions in `README.md` and `README_EN.md` aligned with script behavior.
2. When changing script parameters (timeouts, truncation, waits), update skill guidance.
3. Re-test at least one dynamic site after behavior changes.
