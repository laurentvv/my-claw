# my-claw — QWEN.md

> Project context file for AI assistants. Read this file first before starting any task.
> Also read: `AGENTS.md`, `LEARNING.md`, `PLAN.md`, `STATUS.md`

---

## Project Overview

**my-claw** is a self-hosted, privacy-first personal assistant running on a dedicated Windows machine. It uses a hybrid architecture with local LLMs (Ollama) for 100% local processing, and optional cloud LLMs (Z.ai GLM-4.7) for advanced tasks.

**Architecture:**
- **Gateway** (`gateway/`): Next.js 16 + Prisma 7 + SQLite — handles webhooks, memory, WebChat UI
- **Agent** (`agent/`): Python smolagents + FastAPI — LLM brain with 7 local tools + MCP Chrome DevTools (26 tools)
- **UI Dev** (`agent/gradio_app.py`): Gradio for development/testing

**Current Status:** 7/10 tools implémentés ou en cours (TOOL-1,2,3,7,8,10 DONE / TOOL-9 EN COURS)

---

## Quick Reference

| File | Purpose |
|------|---------|
| `README.md` | Getting started guide |
| `AGENTS.md` | **Critical** — coding rules, architecture, conventions |
| `STATUS.md` | Quick progress overview |
| `PROGRESS.md` | Detailed progress |
| `PLAN.md` | Global architecture & roadmap |
| `LEARNING.md` | Technical discoveries & solutions |
| `IMPLEMENTATION-TOOLS.md` | Tool implementation guide |

---

## Building & Running

### Prerequisites

- Node.js 24+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- [Ollama](https://ollama.ai) with models:
  - `ollama pull qwen3:8b` (5.2GB — main model, recommended)
  - `ollama pull qwen3-vl:2b` (2.3GB — local vision for TOOL-7)
  - `ollama pull gemma3:latest` (3.3GB — fast responses)
- Python 3.11+ (managed by uv)
- Optional: Z.ai API key for GLM-4.7 cloud (code/reasoning tasks)

### Startup Commands

Run the automatic setup script:

```powershell
./setup.ps1
```

> **Important:** Never run `npm run dev` or `uv run uvicorn` without asking the user first. Ask the user to run and report any errors.

### Adding Dependencies

```bash
# Python (NEVER use pip)
cd agent
uv add <package>

# Node.js
cd gateway
npm install <package>
```

---

## Development Conventions

### Critical Rules (from AGENTS.md)

0. **Read LEARNING.md** before any task. Update it after with new discoveries.
1. **STOP at every CHECKPOINT** — wait for explicit user validation before continuing
2. **One module at a time** — never anticipate the next module
3. **Read the corresponding skill** in `.claude/skills/` before coding anything
4. **Never implement V2 modules** — they are intentionally blocked
5. **uv only** for Python — never pip install, never requirements.txt
6. **No console.log** in production (Next.js) — use structured logging only
7. **No secrets in code** — always use process.env or os.environ
8. **Webhooks**: respond HTTP 200 immediately, process async
9. **Validate TypeScript**: `npx tsc --noEmit` must pass before every commit
10. **max_steps**: 5 for simple tasks, 10 for complex PC control (TOOL-9)

### Code Style

**Python:**
- Python 3.11+, type hints everywhere
- `pyproject.toml` + `uv.lock` — never `requirements.txt`
- Logging via `logging` module, never `print()`
- Imports in `forward()` for external libraries (not stdlib)

**TypeScript:**
- `strict: true` in tsconfig
- Named exports, no default except Next.js pages
- `unknown` + type guard, never `any`

**Security:**
- Never log message content
- Log only: channel, timestamp, duration, model
- Validate signature/token on all webhooks

---

## Project Structure

```
my-claw/
├── gateway/                 # Next.js 16 + Prisma 7
│   ├── app/                 # App Router (API routes, WebChat UI)
│   ├── components/          # React components
│   ├── lib/                 # Utilities (DB, agent client)
│   ├── prisma/              # Schema + migrations
│   └── prisma.config.ts     # Prisma 7 config (no URL in schema.prisma)
│
├── agent/                   # Python smolagents
│   ├── main.py              # FastAPI server (+400 lines)
│   ├── gradio_app.py        # Dev UI
│   ├── skills.txt           # Code patterns for agent guidance
│   ├── tools/               # 6 local tools
│   │   ├── __init__.py      # TOOLS list
│   │   ├── file_system.py   # TOOL-1
│   │   ├── os_exec.py       # TOOL-2
│   │   ├── clipboard.py     # TOOL-3
│   │   ├── screenshot.py    # TOOL-8
│   │   ├── mouse_keyboard.py# TOOL-9
│   │   └── vision.py        # TOOL-7
│   └── pyproject.toml       # Python dependencies
│
├── .claude/                 # Skills documentation
├── .crush/                  # Agent config
└── *.md                     # Documentation files
```

---

## Technology Stack

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| Gateway | Next.js | 16+ | App Router required |
| ORM | Prisma | 7+ | SQLite local, config in `prisma.config.ts` |
| Runtime JS | Node.js | 24+ | |
| Python Manager | uv | latest | Never pip |
| Agent | smolagents | 1.9+ | CodeAgent |
| API Server | FastAPI | 0.115+ | |
| Dev UI | Gradio | 5+ | |
| Local LLM | Ollama | latest | Port 11434 |
| Cloud LLM | Z.ai GLM-4.7 | optional | OpenAI-compatible |
| Language | TypeScript | 5+ | strict: true |

---

## LLM Models

### Ollama (100% local, 0 data sent out)

| ID | Model | Size | Usage |
|----|-------|------|-------|
| fast | gemma3:latest | 3.3GB | Fast responses |
| smart | qwen3:latest (8b) | 5.2GB | Daily use — recommended |
| main | qwen3:latest (8b) | 5.2GB | Main model — default |
| vision | qwen3-vl:2b | ~2GB | Local vision (TOOL-7) |

### Z.ai (Cloud, optional — data sent to Z.ai)

| ID | Model | Usage |
|----|-------|-------|
| code | glm-4.7-flash | Code, technical tasks |
| reason | glm-4.7 | Deep reasoning |

**Model Rules:**
- Default model: main (qwen3:8b)
- **Auto-detection**: Agent detects installed Ollama models at startup via `GET /api/tags`
- **Preferences per category**: Each category (fast/smart/main/vision) has preferred models
- **Smart fallback**: If preferred model not installed, use next in list
- If ZAI_API_KEY absent: silent fallback to main
- think: false for agent mode (avoids Qwen3 verbosity)
- num_ctx: 32768 for all Ollama models
- max_steps=5 for simple tasks, 10 for complex PC control
- Ollama Provider: LiteLLMModel with prefix `ollama_chat/`
- Z.ai Provider: LiteLLMModel with prefix `openai/` (OpenAI-compatible)
- **API `/models`**: Endpoint to get available models

---

## Database Schema (Prisma 7)

**Important:** `url` in schema.prisma no longer exists. Connection configured in `gateway/prisma.config.ts` via `datasource.url`. `adapter`, `earlyAccess`, `engine` removed in v7.

### Tables

**Conversation:**
- id: cuid, PK
- channel: "webchat" | "nextcloud"
- channelId: unique identifier per channel
- title: auto-summary, optional
- model: default model "main"
- createdAt, updatedAt
- Unique index on [channel, channelId]

**Message:**
- id: cuid, PK
- conversationId: FK to Conversation (cascade delete)
- role: "user" | "assistant"
- content: text
- model: used model, optional
- createdAt
- Index on [conversationId, createdAt]

**CronJob:**
- id: cuid, PK
- name: unique
- schedule: cron expression ex "0 9 * * 1-5"
- prompt: instruction to execute
- channel + channelId: recipient
- model: default "main"
- enabled: boolean
- lastRun: datetime optional

**Settings:**
- key: PK string
- value: string
- updatedAt
- Used for: system_prompt, persona_name, persona_lang

---

## Implemented Tools (7/10)

| Tool | Status | Description |
|------|--------|-------------|
| **TOOL-1** | ✅ | Windows Files (read/write/create/delete/list/move/search) |
| **TOOL-2** | ✅ | OS Execution (PowerShell + curl alias fix) |
| **TOOL-3** | ✅ | Windows Clipboard |
| **TOOL-7** | ✅ | Local Vision (Ollama qwen3-vl:2b) - 100% local |
| **TOOL-8** | ✅ | Windows Screenshot |
| **TOOL-9** | 🔄 | Mouse/Keyboard Control (en cours - nécessite orchestration) |
| **TOOL-10** | ✅ | MCP Chrome DevTools (26 Puppeteer tools) - TESTÉ & VALIDÉ |

### Pending Tools

| Tool | Priority | Description |
|------|----------|-------------|
| **TOOL-4** | TODO | MCP Web Search Z.ai |
| **TOOL-5** | TODO | MCP Web Reader Z.ai |
| **TOOL-6** | TODO | MCP Zread GitHub |

---

## Environment Variables

### gateway/.env.local

```env
DATABASE_URL="file:./prisma/dev.db"
WEBCHAT_TOKEN=""           # min 32 chars (openssl rand -hex 32)
CRON_SECRET=""             # min 32 chars
AGENT_URL="http://localhost:8000"
NEXTCLOUD_BASE_URL=""      # ex: https://nextcloud.mondomaine.fr
NEXTCLOUD_BOT_SECRET=""    # HMAC-SHA256 shared secret
NEXTCLOUD_BOT_ID=""        # Bot ID in Nextcloud
SCREENSHOT_DIR="C:\tmp\myclawshots"  # Optional, default: C:\tmp\myclawshots
```

### agent/.env

```env
OLLAMA_BASE_URL="http://localhost:11434"
ZAI_API_KEY=""             # Optional, for GLM-4.7 cloud
ZAI_BASE_URL="https://api.z.ai/api/coding/paas/v4"
SCREENSHOT_DIR="C:\tmp\myclawshots"  # Default
```

---

## Key Workflows

### /api/chat Flow

1. Receive { message, conversationId?, model?, channel, channelId }
2. Create or retrieve Conversation (Prisma)
3. Save user message to DB
4. Get last 20 messages (sliding context)
5. Get system prompt from Settings
6. Call agent Python POST /run with { message, history, model }
7. Save assistant response to DB
8. Return response (SSE streaming for webchat, JSON for others)

### PC Control Architecture (TOOL-7 + TOOL-8 + TOOL-9)

```
User: "Open Notepad and write a summary of your day"
         ↓
    glm-4.7 (orchestrator, max_steps=10 for complex tasks)
         ↓
    TOOL-8 screenshot → C:\tmp\myclawshots\screen_001.png
         ↓
    TOOL-7 vision → "Windows desktop visible, Notepad not open"
         ↓
    TOOL-9 keyboard → hotkey("win") → type("notepad") → hotkey("enter")
         ↓
    TOOL-8 screenshot → screen_002.png
         ↓
    TOOL-7 vision → "Notepad open, empty text area, cursor active"
         ↓
    TOOL-9 keyboard → type("Summary of February 20, 2026...")
         ↓
    Done
```

**Note:** This architecture requires a powerful orchestrator model (glm-4.7 recommended). qwen3:8b alone is not sufficient for this level of complexity.

---

## Channels

### WebChat

- Auth: header `Authorization: Bearer {WEBCHAT_TOKEN}`
- Streaming via Server-Sent Events (ReadableStream)
- Token minimum 32 chars

### Nextcloud Talk Bot

- POST `/api/webhook/nextcloud`: verify HMAC-SHA256 signature mandatory
- Headers to verify: `X-Nextcloud-Talk-Random` + `X-Nextcloud-Talk-Signature`
- Shared secret: `NEXTCLOUD_BOT_SECRET`
- Send: POST `{NC_BASE_URL}/ocs/v2.php/apps/spreed/api/v1/bot/{BOT_ID}/message`
- Header send: `OCS-APIRequest: true`
- Use `crypto.timingSafeEqual` to compare signatures

---

## What We DON'T Do

- No multi-users
- No Docker for main app
- No Redis or message queue
- No pip install or requirements.txt
- No V2 features without explicit validation
- No Telegram, Discord, Slack, Signal
- No PC control without Vision (TOOL-7 required for TOOL-9)

---

## Recent Improvements (2026-02-20)

- ✅ **GLM-4.7 Fix**: Auto-cleanup of `</code` tags generated by GLM-4.7 (SyntaxError resolved)
- ✅ **Timeouts Increased**: Gateway 6min, Agent 4min (for GLM-4.7 screenshot+vision)
- ✅ **Agent Guidance**: `instructions` + `additional_authorized_imports` to prefer Python native (requests, urllib, json, etc.)
- ✅ **TOOL-7 Vision**: Ollama qwen3-vl:2b instead of Z.ai MCP (100% local, 0 data sent out)
- ✅ **Skills Externalized**: `agent/skills.txt` with code patterns + `final_answer()`
- ✅ **TOOL-10 Chrome DevTools**: MCP loaded with 26 Puppeteer tools - Tests validated

---

## References

- **smolagents**: https://huggingface.co/docs/smolagents
- **smolagents MCP**: https://huggingface.co/docs/smolagents/tutorials/mcp
- **Prisma 7 Config**: https://pris.ly/d/config-datasource
- **Z.ai GLM-4.7**: https://open.bigmodel.cn/dev/api
- **Ollama API**: https://github.com/ollama/ollama/blob/main/docs/api.md
- **Nextcloud Talk Bot**: https://nextcloud-talk.readthedocs.io/en/latest/bot-list/
- **Prisma 7 Docs**: https://www.prisma.io/docs
- **Next.js 16**: https://nextjs.org/docs/app
- **Gradio**: https://www.gradio.app/docs
- **FastAPI**: https://fastapi.tiangolo.com
- **pyautogui**: https://pyautogui.readthedocs.io
- **Pillow**: https://pillow.readthedocs.io

---

## Next Task

**TOOL-4**: MCP Web Search Z.ai (web search via Z.ai API)

See `IMPLEMENTATION-TOOLS.md` for detailed implementation guide.

---

## Checkpoints

Current checkpoint: **TOOL-10 DONE** (MCP Chrome DevTools validé)

Next checkpoint: **TOOL-4** (MCP Web Search Z.ai) — WAITING FOR USER VALIDATION

**DO NOT proceed to TOOL-4 without explicit user validation.**
