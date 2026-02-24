# AGENTS.md — my-claw 🦞
Technical guidance for coding agents (Kilo, Claude, Cursor, Codex, Windsurf...)

## WHAT & WHY
**my-claw** is a privacy-first, hybrid personal assistant for Windows. It bridges a **Next.js 16 gateway** (memory/UI) with a **Python smolagents brain** (reasoning/tools).
**Objective**: Provide a local-first, extensible AI capable of OS control, web automation, and proactive tasks.

## HOW TO WORK
### Essential Commands
- **Initialization**: Run `./setup.ps1` to sync environments and dependencies.
- **Python Management**: Use `uv` exclusively (e.g., `uv add <pkg>`). **No pip, no requirements.txt.**
- **Verification**: `npx tsc --noEmit` must pass in `gateway/` before any commit.
- **Execution**: Do not start dev servers yourself. Ask the user to run them and report errors.

### Critical Rules
- **Behavior**: **STOP at each CHECKPOINT** and wait for explicit user approval.
- **Focus**: Work on **one module at a time**. Never implement "V2" modules (blocked).
- **Security**: No secrets in source code. Use `process.env` or `os.environ`.
- **OS Control**: `pyautogui.FAILSAFE=False` is set. Use `time.sleep(0.5)` after actions to let the OS react.
- **Reliability**: Check [`LEARNING.md`](LEARNING.md) before starting and update it with new discoveries after.

## ARCHITECTURE & NAVIGATION
The system uses a Manager + Specialized Sub-agents pattern.
- **Project Index**: See [`STATUS.md`](STATUS.md) for current progress and active tools.
- **Technical Specs**: [`agent_docs/tech-spec.md`](agent_docs/tech-spec.md) (Stack, DB Schema, Models, Webhooks).
- **Code Patterns**: Use [`agent/SKILLS.md`](agent/SKILLS.md) to copy-paste validated tool usage patterns.
- **Database**: Defined in `gateway/prisma/schema.prisma`. Uses Prisma 7 local SQLite.
- **Brain**: Rooted in `agent/main.py`. Tools are in `agent/tools/`.

---
*Write deliberately. Less is more. Trust the pointers.*
