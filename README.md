# my-claw 🦞

A minimalist, self-hosted, and privacy-first personal assistant designed for Windows.

**my-claw** is a powerful hybrid assistant that combines a modern Next.js 16 frontend with a Python-based "brain" powered by `smolagents`. It is built to run entirely on your own hardware, ensuring your data never leaves your machine unless you explicitly choose to use optional cloud models.

---

## ✨ Key Features

- 🛡️ **Privacy-First**: Designed to run 100% locally with Ollama.
- 🪟 **Deep Windows Integration**: Full access to the file system, PowerShell, clipboard, and screen.
- 🧠 **Hybrid Brain**: Uses `smolagents` for intelligent tool use and code execution.
- 🌐 **Modern Web Interface**: Clean, responsive UI built with Next.js 16 and Tailwind CSS.
- 🔌 **Extensible Tools**: Supports custom Python tools and Model Context Protocol (MCP) integrations.
- 🤖 **Multi-Model Support**: Native support for Qwen3, Gemma3, and GLM-4.7 (via Z.ai).

---

## 🚀 Quick Start

### Prerequisites

- **Node.js**: 24.x or higher
- **uv**: [Python package manager](https://docs.astral.sh/uv/)
- **Ollama**: For local LLM acceleration
- **Windows OS**: Recommended (for native tool support)

### Installation

The project includes an automatic setup script for convenience:

```powershell
./setup.ps1
```

This script will:
1. Initialize the Gateway (Next.js) environment and dependencies.
2. Setup the Agent (Python) environment using `uv`.
3. Configure the Prisma 7 SQLite database.
4. Prepare your `.env` files.

---

## 🏗️ Architecture

The system is split into two main components: the **Gateway** (handling UI and memory) and the **Agent** (handling reasoning and tools).

```mermaid
graph TD
    User([User])
    WebChat[Next.js 16 WebChat]
    NCTalk[Nextcloud Talk]

    subgraph "Gateway (Node.js/Next.js)"
        API_Chat[API /api/chat]
        API_Webhook[API /api/webhook]
        Prisma[Prisma 7 + SQLite]
    end

    subgraph "Agent (Python)"
        FastAPI[FastAPI Server]
        Smolagents[smolagents CodeAgent]
        Tools[Windows & MCP Tools]
    end

    subgraph "Local Services"
        Ollama[Ollama - Qwen3/Gemma3]
    end

    subgraph "External (Optional)"
        ZAI[Z.ai GLM-4.7]
    end

    User --> WebChat
    User --> NCTalk
    WebChat --> API_Chat
    NCTalk --> API_Webhook
    API_Chat --> Prisma
    API_Chat --> FastAPI
    API_Webhook --> FastAPI
    FastAPI --> Smolagents
    Smolagents --> Tools
    Smolagents --> Ollama
    Smolagents --> ZAI
    Tools --> Windows[Windows OS]
    Tools --> Chrome[Chrome DevTools]
```

---

## 🛠️ Tool Capabilities

Current status: **6/10 core tools implemented**

| Tool | Status | Description |
|------|--------|-------------|
| **File System** | ✅ | Read, write, move, delete, and search files on Windows. |
| **OS Exec** | ✅ | Execute PowerShell commands and scripts. |
| **Clipboard** | ✅ | Access and modify the Windows clipboard. |
| **Vision** | ✅ | Local image analysis and OCR via `qwen3-vl:2b`. |
| **Screenshot** | ✅ | Capture full screen or specific regions. |
| **Chrome DevTools**| ✅ | Full browser automation via MCP (Playwright). |
| **Mouse & Keyboard**| 🔄 | Direct OS input control (In Progress). |
| **Web Search** | ⏳ | Real-time web search (Roadmap). |
| **Web Reader** | ⏳ | Content extraction from URLs (Roadmap). |
| **GitHub** | ⏳ | Repository analysis and file reading (Roadmap). |

---

## 📅 Roadmap

### Module 0: Foundation ✅
- Project structure, Next.js 16, Python `uv`, and Ollama integration.

### Module 1: Python Brain ✅
- `smolagents` integration, FastAPI server, and Gradio development UI.

### Module 2: Memory (Prisma 7) ✅
- SQLite persistence for conversations and settings.

### Module 3: WebChat ✅
- Streaming UI, SSE, and secure authentication.

### Module 4: Nextcloud Talk Integration ⏳
- Bot support via HMAC-SHA256 webhooks for mobile interaction.

### Module 5: Proactive Tasks ⏳
- Cron-based job execution and proactive notifications.

### Module 6: Identity & Persona ⏳
- Customizable system prompts and assistant personality settings.

---

## 📚 Documentation

For more detailed information, please refer to the following files:

- 📊 [STATUS.md](STATUS.md) — Quick project overview.
- 📋 [PROGRESS.md](PROGRESS.md) — Detailed development checkpoints.
- 🗺️ [PLAN.md](PLAN.md) — Long-term architecture and goals.
- 🏗️ [AGENTS.md](AGENTS.md) — Technical guide for developers and agents.
- 🎯 [agent/SKILLS.md](agent/SKILLS.md) — Agent-specific code patterns.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 16, React, Tailwind CSS
- **Database**: SQLite with Prisma 7
- **Agent Framework**: [smolagents](https://github.com/huggingface/smolagents)
- **API**: FastAPI (Python)
- **Environment**: Node.js 24+, Python 3.11+ (via `uv`)
- **LLM**: Ollama (Local), Z.ai (Cloud/Optional)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Built with 🦞 and 🐍 for a better personal AI experience.
