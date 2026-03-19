# 🦞 GEMINI.md — Instructions & Context for my-claw

Welcome to **my-claw**, a minimalist, self-hosted, and privacy-first personal assistant for Windows. This file serves as the primary instructional context for Gemini CLI when working on this codebase.

## 🏗️ Project Overview

**my-claw** is a hybrid assistant combining a modern web frontend with a powerful Python-based "brain" powered by `smolagents`. It is designed to run locally on Windows, with deep OS integration.

### Core Components
1.  **Gateway (`/gateway`)**:
    - **Tech**: Next.js 16.1, React 19, Tailwind CSS 4, Prisma 7.
    - **Purpose**: Handles the WebChat UI, conversation memory (SQLite/Prisma), and authentication.
    - **API**: `/api/chat` (SSE) manages user interaction and calls the Python Agent.
2.  **Agent (`/agent`)**:
    - **Tech**: Python 3.14 (via `uv`), FastAPI, `smolagents`.
    - **Purpose**: The reasoning engine. Orchestrates tools and specialized sub-agents.
    - **Sub-Agents**:
        - `pc_control`: Windows GUI automation (vision, mouse, keyboard).
        - `browser`: Chrome automation via MCP (Chrome DevTools).
    - **Direct Tools**: `file_system`, `os_exec` (PowerShell), `clipboard`, `web_search` (DuckDuckGo), `visit_webpage`.

## 🚀 Building and Running

### Prerequisites
- **Node.js**: 25.x+
- **Python**: 3.14.x+ (via `uv`)
- **Ollama**: Local LLM server.
- **Windows**: Recommended for native tool support.

### Setup
Run the central setup script from the root:
```powershell
./setup.ps1
```

### Running the Services
1.  **Gateway (Frontend)**:
    ```powershell
    cd gateway
    npm run dev
    ```
2.  **Agent (Backend)**:
    ```powershell
    cd agent
    uv run python main.py
    ```
3.  **Gradio Dev UI (Optional)**:
    ```powershell
    cd agent
    uv run python gradio_app.py
    ```

## 🧠 Model Configuration

- **Default Model**: Managed in `agent/.env` via `DEFAULT_MODEL`.
    - `reason`: GLM-4.7 (requires `ZAI_API_KEY`).
    - `main`: Qwen3:8b (Local fallback).
- **Local Models**: Managed via `agent/models.py` with categories: `fast`, `smart`, `main`, `vision`.
- **Vision**: Uses `qwen3-vl` for image analysis and GUI grounding.

## 🛠️ Development Conventions

### Python (Agent)
- **Tooling**: Use `uv` for package management.
- **Coding Style**:
    - Prefer native Python code over `os_exec` (e.g., use `requests` for HTTP, built-in `open()` for files).
    - Always use `final_answer()` to return results in agent tools.
- **Multi-Agent**: The `Manager` agent automatically delegates tasks to `pc_control` or `browser` based on the user's request.
- **Skills**: Core agent instructions are in `agent/skills.txt`. Always consult this before modifying agent behavior.
- **MCP**: New capabilities should be added as MCP servers (like the current Chrome DevTools integration).

### Next.js (Gateway)
- **Memory**: Conversation history is persisted in SQLite using Prisma.
- **SSE**: The chat API uses Server-Sent Events for a streaming response experience.
- **Styling**: Tailwind CSS 4 with Vanilla CSS preferences.

## 📁 Key File Map
- `agent/main.py`: FastAPI server & Agent initialization.
- `agent/models.py`: LLM configuration and detection logic.
- `agent/skills.txt`: "System prompt" and patterns for the Manager agent.
- `gateway/app/api/chat/route.ts`: Main chat orchestrator.
- `gateway/prisma/schema.prisma`: Database schema for memory.
- `setup.ps1`: Automated environment preparation.

## 📅 Roadmap Highlights
- [ ] Module 4: Nextcloud Talk Integration (Webhooks).
- [ ] Module 5: Proactive Tasks (Cron-based).
- [ ] Module 6: Identity & Persona (Customizable system prompts).
