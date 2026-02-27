# my-claw — QWEN.md

> Project context file for AI assistants. Read this file first before starting any task.
> Also read: `AGENTS.md`, `LEARNING.md`, `PLAN.md`, `STATUS.md`

---

## Project Overview

**my-claw** is a self-hosted, privacy-first personal assistant running on a dedicated Windows machine. It uses a hybrid architecture with local LLMs (Ollama) for 100% local processing, and optional cloud LLMs (Z.ai GLM-4.7) for advanced tasks.

**Architecture:**
- **Gateway** (`gateway/`): Next.js 16 + Prisma 7 + SQLite — handles webhooks, memory, WebChat UI
- **Agent** (`agent/`): Python smolagents + FastAPI — LLM brain with local tools + MCP Chrome DevTools (26 tools)
- **UI Dev** (`agent/gradio_app.py`): Gradio for development/testing

**Current Status:** **8/10 core tools implemented** (TOOL-1,2,3,4,7,8,9,10,11 DONE / TOOL-5,6 TODO)

---

## Quick Reference

| File | Purpose |
|------|---------|
| `README.md` | Getting started guide |
| `AGENTS.md` | **Critical** — coding rules, architecture, conventions |
| `LEARNING.md` | Technical discoveries & solutions |
| `STATUS.md` | Quick progress overview |
| `PROGRESS.md` | Detailed progress |
| `PLAN.md` | Global architecture & roadmap |
| `IMPLEMENTATION-TOOLS.md` | Tool implementation guide |

---

## Building & Running

### Prerequisites

- **Node.js**: 25.x or higher
- **uv**: [Python package manager](https://docs.astral.sh/uv/)
- **Python**: 3.14.x or higher
- **Ollama**: For local LLM acceleration
  - `ollama pull qwen3:8b` (5.2GB — main model, recommended)
  - `ollama pull qwen3-vl:2b` (2.3GB — local vision for TOOL-7, TOOL-11)
  - `ollama pull gemma3:latest` (3.3GB — fast responses)
- **Windows OS**: Required (for native tool support)

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

0. **Read LEARNING.md** — before every task. Update it after with new discoveries.
1. **STOP at every CHECKPOINT** — wait for explicit user validation before continuing
2. **One module at a time** — never anticipate the next module
3. **Read the corresponding skill** in `.claude/skills/` before coding anything
4. **Never implement V2 modules** — they are intentionally blocked
5. **uv only** for Python — never pip install, never requirements.txt
6. **No console.log** in production (Next.js) — use structured logging only
7. **No secrets in code** — always use process.env or os.environ
8. **Webhooks**: respond HTTP 200 immediately, process async
9. **Validate TypeScript**: `npx tsc --noEmit` must pass before every commit
10. **Never run servers** — ask user to run and report errors
11. **max_steps**: 5 for simple tasks, 10+ for complex PC control (TOOL-9)

### Code Style

**Python:**
- Python 3.14+, type hints everywhere
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
│   ├── models.py            # LLM model management (centralized)
│   ├── skills.txt           # Code patterns for agent guidance
│   ├── SKILLS.md            # Skills documentation
│   ├── tools/               # Local tools
│   │   ├── __init__.py      # TOOLS list
│   │   ├── file_system.py   # TOOL-1
│   │   ├── os_exec.py       # TOOL-2
│   │   ├── clipboard.py     # TOOL-3
│   │   ├── screenshot.py    # TOOL-8
│   │   ├── mouse_keyboard.py# TOOL-9
│   │   ├── vision.py        # TOOL-7
│   │   ├── grounding.py     # TOOL-11
│   │   ├── web_search_tool.py  # TOOL-4 (DuckDuckGo)
│   │   └── web_visit_tool.py   # TOOL-5 (VisitWebpageTool)
│   └── agents/              # Specialized sub-agents
│       ├── pc_control_agent.py
│       ├── vision_agent.py
│       ├── browser_agent.py
│       └── web_agent.py
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
| Runtime JS | Node.js | 25+ | |
| Python Manager | uv | latest | Never pip |
| Agent | smolagents | 1.24+ | CodeAgent |
| API Server | FastAPI | 0.131+ | |
| Dev UI | Gradio | 6+ | |
| Local LLM | Ollama | latest | Port 11434 |
| Cloud LLM | Z.ai GLM-4.7 | optional | OpenAI-compatible |
| Language | TypeScript | 5+ | strict: true |

---

## LLM Models

### Ollama (100% local, 0 data sent out)

| ID | Model | Size | Usage |
|----|-------|------|-------|
| fast | gemma3:latest | 3.3GB | Fast responses |
| smart | qwen3:8b | 5.2GB | Daily use — recommended |
| main | qwen3:8b | 5.2GB | Main model — default without ZAI_API_KEY |
| vision | qwen3-vl:2b | ~2.3GB | Local vision (TOOL-7, TOOL-11) |

### Z.ai (Cloud, optional — data sent to Z.ai)

| ID | Model | Usage |
|----|-------|-------|
| code | glm-4.7-flash | Code, technical tasks |
| reason | glm-4.7 | Deep reasoning — default with ZAI_API_KEY |

**Model Rules:**
- Default model: `get_default_model()` — env `DEFAULT_MODEL` → "reason" if ZAI_API_KEY → "main" fallback
- **Auto-detection**: Agent detects installed Ollama models at startup via `GET /api/tags`
- **Preferences per category**: Each category (fast/smart/main/vision) has preferred models
- **Smart fallback**: If preferred model not installed, use next in list
- If ZAI_API_KEY absent: silent fallback to main
- think: false for agent mode (avoids Qwen3 verbosity)
- num_ctx: 32768 for all Ollama models
- max_steps=5 for simple tasks, 10+ for complex PC control
- Ollama Provider: LiteLLMModel with prefix `ollama_chat/`
- Z.ai Provider: CleanedLiteLLMModel with prefix `openai/` (OpenAI-compatible, auto-cleanup `</code` tags)
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

## Implemented Tools (8/10)

| Tool | Status | Description |
|------|--------|-------------|
| **TOOL-1** | ✅ | Windows Files (read/write/create/delete/list/move/search) |
| **TOOL-2** | ✅ | OS Execution (PowerShell) |
| **TOOL-3** | ✅ | Windows Clipboard |
| **TOOL-4** | ✅ | DuckDuckGoSearchTool (built-in smolagents, unlimited, 0 quota) |
| **TOOL-5** | ✅ | VisitWebpageTool (built-in smolagents, unlimited, 0 quota) |
| **TOOL-7** | ✅ | Local Vision (Ollama qwen3-vl:2b) - 100% local |
| **TOOL-8** | ✅ | Windows Screenshot |
| **TOOL-9** | ✅ | Mouse/Keyboard Control (pyautogui) |
| **TOOL-10** | ✅ | MCP Chrome DevTools (26 Puppeteer tools) - TESTED & VALIDATED |
| **TOOL-11** | ✅ | GUI Grounding (qwen3-vl:2b for UI element localization) |

### Pending Tools

| Tool | Priority | Description |
|------|----------|-------------|
| **TOOL-6** | TODO | MCP Zread GitHub (Z.ai) |

---

## Multi-Agent Architecture

The system uses a **Manager + Specialized Sub-agents** architecture:

### Manager
- **Role:** Main orchestrator that delegates tasks to specialized sub-agents
- **Model:** Default (glm-4.7 with ZAI_API_KEY, otherwise qwen3:8b)
- **Direct Tools:** `file_system`, `os_exec`, `clipboard`, `DuckDuckGoSearchTool`, `VisitWebpageTool`

### Sub-agents

**pc_control_agent:**
- **File:** `agent/agents/pc_control_agent.py`
- **Role:** Windows GUI control
- **Tools:** `screenshot`, `ui_grounding`, `mouse_keyboard`
- **Model:** Default model

**vision_agent:**
- **File:** `agent/agents/vision_agent.py`
- **Role:** Image analysis with coding model
- **Tools:** `analyze_image` (uses qwen3-vl:2b internally)
- **Model:** Default model (coding LLM)

**browser_agent:**
- **File:** `agent/agents/browser_agent.py`
- **Role:** Chrome automation via DevTools MCP
- **Tools:** 26 Chrome DevTools MCP tools
- **Model:** Default model

**web_agent:**
- **File:** `agent/agents/web_agent.py`
- **Role:** Web search and page reading
- **Tools:** `DuckDuckGoSearchTool`, `VisitWebpageTool`
- **Model:** Default model

### Delegation Examples
- "Open Notepad" → Delegated to `pc_control_agent`
- "Analyze this image" → Delegated to `vision_agent`
- "Open https://example.com" → Delegated to `browser_agent`
- "Search for smolagents info" → Manager calls `DuckDuckGoSearchTool` directly

---

## Environment Variables

### gateway/.env.local

```env
DATABASE_URL="file:./prisma/dev.db"
WEBCHAT_TOKEN=""           # min 32 chars (openssl rand -hex 32)
CRON_SECRET=""             # min 32 chars
AGENT_URL="http://localhost:8000"
NEXTCLOUD_BASE_URL=""      # ex: https://nextcloud.example.com
NEXTCLOUD_BOT_SECRET=""    # HMAC-SHA256 shared secret
NEXTCLOUD_BOT_ID=""        # Bot ID in Nextcloud
SCREENSHOT_DIR="C:\tmp\myclawshots"  # Optional, default: C:\tmp\myclawshots
```

### agent/.env

```env
OLLAMA_BASE_URL="http://localhost:11434"
ZAI_API_KEY=""             # Optional, for GLM-4.7 cloud
ZAI_BASE_URL="https://api.z.ai/api/coding/paas/v4"
DEFAULT_MODEL=""           # Optional: "reason", "code", "main", "fast", "vision"
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

### PC Control Architecture (TOOL-7 + TOOL-8 + TOOL-9 + TOOL-11)

```
User: "Open Notepad and write a summary of your day"
         ↓
    Manager (glm-4.7 or qwen3:8b, max_steps=10 for complex tasks)
         ↓
    pc_control_agent:
      TOOL-8 screenshot → C:\tmp\myclawshots\screen_001.png
         ↓
      TOOL-11 grounding → "Notepad icon at [0.3, 0.8]"
         ↓
      TOOL-9 mouse → click(x, y)
         ↓
      TOOL-8 screenshot → screen_002.png
         ↓
      TOOL-11 grounding → "Notepad open, text area at [0.5, 0.5]"
         ↓
      TOOL-9 keyboard → type("Summary of February 20, 2026...")
         ↓
    Done
```

**Note:** This architecture requires a powerful orchestrator model (glm-4.7 recommended). qwen3:8b alone may not be sufficient for this level of complexity.

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
- No PC control without Vision (TOOL-7/TOOL-11 required for TOOL-9)

---

## Recent Improvements (2026-02-23)

- ✅ **TOOL-9 Mouse & Keyboard**: Validated — pyautogui control
- ✅ **TOOL-4 Web Search**: DuckDuckGoSearchTool (built-in smolagents, unlimited)
- ✅ **TOOL-5 Web Reader**: VisitWebpageTool (built-in smolagents, unlimited)
- ✅ **TOOL-11 GUI Grounding**: QwenGroundingTool (qwen3-vl:2b for UI localization)
- ✅ **GLM-4.7 Fix**: Auto-cleanup of `</code` tags (SyntaxError resolved via CleanedLiteLLMModel)
- ✅ **Timeouts Increased**: Gateway 6min, Agent 4min (for GLM-4.7 screenshot+vision)
- ✅ **Agent Guidance**: `instructions` + `additional_authorized_imports` to prefer Python native
- ✅ **TOOL-7 Vision**: Ollama qwen3-vl:2b instead of Z.ai MCP (100% local, 0 data sent out)
- ✅ **Skills Externalized**: `agent/skills.txt` with code patterns + `final_answer()`
- ✅ **TOOL-10 Chrome DevTools**: MCP loaded with 26 Puppeteer tools - Tests validated
- ✅ **Multi-Agent Cache**: Per-model caching in `get_or_build_agent()` for consistency

---

## References

- **smolagents**: https://huggingface.co/docs/smolagents
- **smolagents MCP**: https://huggingface.co/docs/smolagents/tutorials/mcp
- **smolagents built-in tools**: https://huggingface.co/docs/smolagents/reference/default_tools
- **Building good agents**: https://huggingface.co/docs/smolagents/tutorials/building_good_agents
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
- **Chrome DevTools MCP**: https://github.com/ChromeDevTools/chrome-devtools-mcp

---

## Next Task

**TOOL-6**: MCP Zread GitHub (Z.ai) — Read GitHub repositories via Z.ai API

See `IMPLEMENTATION-TOOLS.md` for detailed implementation guide.

---

## Checkpoints

Current checkpoint: **TOOL-11 DONE** (GUI Grounding validated)

Next checkpoint: **TOOL-6** (MCP Zread GitHub) — WAITING FOR USER VALIDATION

**DO NOT proceed to TOOL-6 without explicit user validation.**
