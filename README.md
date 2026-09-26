# Project Arrakis - local prototype

A reproducible, local-only OpenClaw base for Ishan's agent. This is **not** a VPS deployment or a Telegram bot yet. The baseline uses OpenClaw 2026.9.6 and an OpenRouter free model; quota, latency, availability and terms can change. Only the local CLI and a PDF rendering skill are wired so far. There is no live search, voice, browser automation, or editable PPTX path.

## Setup

Install Node >=24.16 or >=26.1, Python 3, and Google Chrome/Chromium for the PDF skill. Clone the repo. Set `OPENROUTER_API_KEY` in your shell without writing it to this repo. Run:

```bash
bash scripts/setup.sh
npm run check
npm run smoke
```

Setup keeps runtime state in `.openclaw-state/` (ignored by git), binds the gateway to loopback, skips public channels and daemon installation, and sets a minimal tool profile. It does not turn on the gateway; use `./node_modules/.bin/openclaw agent --local --message 'Hello'` for a local session after setup. The optional `OPENCLAW_STATE_DIR` environment variable can point to a separate private state directory.

## Design PDF

`python3 scripts/render_pdf.py example.html outputs/example.pdf` renders an HTML document. Check every page visually before delivery. The skill at `workspace/skills/visual-docs/SKILL.md` describes the design and inspection workflow; a PDF is not an editable PPTX.

## What to build next

Connect Telegram only after its bot token is collected securely and its recipients and permissions are agreed. Add model fallbacks and budgets, test 3-5 user session isolation, then add grounded search and richer document workflows. Keep Chrome jobs at one at a time. VPS deployment waits for host access and measured RAM/CPU; do not copy local secrets or expose the gateway.

The OpenClaw decision and feature options were recorded in the [build note](https://files.instinct.com/file-01M3DYYBFK11Q11KJ4Y6P3CGFH) and [earlier blueprint](https://files.instinct.com/file-01M3CZC08GRQVJ4T9HRR6GC7TP). Official [OpenClaw setup](https://docs.openclaw.ai/start/getting-started) and [provider guide](https://docs.openclaw.ai/providers/openrouter) should be rechecked when deploying.
