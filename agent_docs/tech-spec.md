# Technical Specifications — my-claw 🦞

This document provides detailed technical information for the `my-claw` project, intended for deep-dive reference by agents and developers.

## Technical Stack

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| Gateway | Next.js | 16+ | App Router required |
| ORM | Prisma | 7+ | SQLite local |
| JS Runtime | Node.js | 25+ | |
| Python Manager | uv | latest | Never use pip |
| LLM Agent | smolagents | 1.24+ | CodeAgent |
| Python API | FastAPI | 0.131+ | |
| Dev UI | Gradio | 6+ | |
| Local LLM | Ollama | latest | Port 11434 |
| Cloud LLM | Z.ai GLM-4.7 | — | OpenAI-compatible |
| Language | TypeScript | 5+ | strict: true |

## LLM Models Configuration

### Model Categories (Ollama)
- **main**: `qwen3:8b` (default fallback)
- **smart**: `qwen3:8b`
- **fast**: `gemma3:latest`
- **vision**: `qwen3-vl:2b` (TOOL-7, internal use)
- **grounding**: `qwen3-vl:2b` (TOOL-11)

### Model Selection Logic
See `agent/models.py` for implementation details.
1. `DEFAULT_MODEL` env var.
2. `reason` (`glm-4.7`) if `ZAI_API_KEY` is present.
3. `main` (`qwen3:8b`) as local fallback.

## Database Schema (Prisma 7)

Refer to `gateway/prisma/schema.prisma` for the source of truth.

### Key Models:
- **Conversation**: Stores session data per channel. Unique on `[channel, channelId]`.
- **Message**: Stores chat history.
- **CronJob**: Proactive tasks configuration.
- **Settings**: Global assistant settings (persona, system prompt).

**Note**: Prisma 7 in this project uses `gateway/prisma.config.ts` for connection strings, not the `url` field in `schema.prisma`.

## Multi-Agent Architecture

- **Manager**: Orchestrates tasks and delegates to sub-agents. Default `max_steps=10`.
- **pc_control_agent**: Handles Windows GUI interaction (screenshot -> grounding -> action). Default `max_steps=15`.
- **vision_agent**: Specialized in image analysis.
- **browser_agent**: Automates Chrome via MCP tools.
- **web_agent**: Real-time search via DuckDuckGo.

## Tools Summary

Complete list of tools available to the agents:
- **TOOL-1**: File System (read, write, move, delete, list, search)
- **TOOL-2**: OS Exec (PowerShell, CP1252 encoding)
- **TOOL-3**: Clipboard
- **TOOL-4**: Web Search (DuckDuckGo)
- **TOOL-5**: Web Reader (VisitWebpage)
- **TOOL-7**: Local Vision (qwen3-vl)
- **TOOL-8**: Screenshot
- **TOOL-9**: Mouse & Keyboard (pyautogui)
- **TOOL-10**: Chrome DevTools MCP (26 tools)
- **TOOL-11**: GUI Grounding (qwen3-vl)

## Webhooks & Channels

### WebChat
- Bearer token authentication.
- SSE Streaming.

### Nextcloud Talk
- HMAC-SHA256 signature verification required.
- Uses `NEXTCLOUD_BOT_SECRET`.
- **Async Pattern**: Always respond HTTP 200 immediately; process message logic asynchronously.

## Environment Variables

Refer to `.env.example` in both `gateway/` and `agent/` directories for the full list of required variables.
