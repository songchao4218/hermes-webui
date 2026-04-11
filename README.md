<div align="center">

<img src="docs/banner.png" alt="马鞍 Ma'an" width="800">

# 马鞍 Ma'an

**Hermes 的马鞍 — 骑上你的本地 AI Agent**

A customizable, cyber-noir WebUI for [Hermes Agent](https://github.com/hermes-ai/hermes) with full memory sync.

Give your local AI agent an identity — any name, any avatar, any color.

[![License: MIT](https://img.shields.io/badge/License-MIT-cyan.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![Hermes](https://img.shields.io/badge/Hermes-Agent-purple.svg)](https://github.com/hermes-ai/hermes)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-green.svg)](https://ollama.ai)

</div>

---

## Why 马鞍?

Hermes（爱马仕）is a horse. 马鞍 is the saddle. You need a saddle to ride.

Hermes Agent is one of the best open-source AI agents — but it lives in the terminal. 马鞍 gives it a face, **your** face, with **your** name and **your** colors.

- **Shares memory with Hermes CLI** — SOUL.md, MEMORY.md, USER.md are the same files
- **Fully customizable identity** — Name your agent anything (emoji welcome), upload an avatar, pick a color theme
- **Runs 100% locally** — Your data never leaves your machine
- **Works with any Ollama model** — Gemma, Llama, Qwen, DeepSeek, you name it
- **Cyber-noir design** — Deep obsidian theme inspired by Google Stitch

## Personalization

On first launch, a guided onboarding wizard helps you set up your agent's identity:

| Feature | Details |
|---------|---------|
| **Agent Name** | Any characters — English, Chinese, Japanese, emoji, symbols. Max 32 chars. |
| **Avatar** | Upload PNG, JPG, GIF, or WEBP. Stored locally in `~/.maan/avatar/` |
| **Theme Color** | Choose from 5 presets (cyan, purple, green, amber, rose) or pick any custom color |
| **Subtitle** | Optional tagline displayed under the name |

Everything can be changed later in the Settings page. Persona config is stored in `~/.maan/persona.json`.

## Features

- **Full Memory Sync** — WebUI reads and writes the same memory files as Hermes CLI. Edit in one, see it in the other.
- **Customizable Agent Identity** — Name, avatar, and theme color — all yours to define.
- **Onboarding Wizard** — Friendly 4-step setup on first launch.
- **Skill Browser** — View all installed Hermes skills with descriptions.
- **Memory Editor** — View and edit SOUL.md, MEMORY.md, USER.md directly in the browser.
- **Model Switcher** — Switch between Ollama models on the fly.
- **Session Management** — Multiple conversation sessions with history.
- **Dynamic Theming** — CSS custom properties update the entire UI in real-time when you change colors.
- **One-click Start** — Double-click `start.bat` (Windows) or run `./scripts/start.sh` (Linux/Mac).

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser    │────▶│  FastAPI     │────▶│   Ollama    │
│  (Your Agent)│◀────│  Backend     │◀────│   (Local)   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  ~/.hermes/  │  ◀── Shared with Hermes CLI
                    │  ├─ SOUL.md  │
                    │  ├─ memories/│
                    │  ├─ skills/  │
                    │  └─ state.db │
                    └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  ~/.maan/    │  ◀── 马鞍 persona & config
                    │  ├─ persona.json
                    │  ├─ avatar/  │
                    │  └─ config.yaml
                    └──────────────┘
```

The key insight: **马鞍 doesn't replace Hermes — it's the saddle you ride it with.** Both CLI and WebUI read/write the same `~/.hermes/` directory. Your agent's memories, personality, and skills are always in sync.

## Quick Start

### Prerequisites

| Component | Required | Purpose |
|-----------|----------|---------|
| [Python 3.10+](https://www.python.org) | Yes | Backend server |
| [Ollama](https://ollama.ai) | Yes | Local LLM inference |
| [Hermes](https://github.com/hermes-ai/hermes) | Recommended | Agent framework with memory/skills |

### Install

```bash
# 1. Clone
git clone https://github.com/yourname/maan-webui.git
cd maan-webui

# 2. Install (creates venv, installs deps)
# Linux / macOS / WSL:
chmod +x scripts/install.sh && ./scripts/install.sh

# Windows: just double-click start.bat (auto-installs on first run)
```

### Start

```bash
# Linux / macOS / WSL
./scripts/start.sh

# Windows
start.bat

# Then open: http://localhost:8080
```

On first launch, the onboarding wizard will guide you through naming your agent, choosing an avatar, and picking a theme.

### Pull a model (if you haven't)

```bash
# Recommended: Google Gemma 4
ollama pull gemma4:27b-it-q4_K_M

# Alternatives
ollama pull llama3:8b
ollama pull qwen2:7b
ollama pull deepseek-r1:8b
```

## Configuration

马鞍 auto-detects settings from Hermes config. For manual configuration:

```yaml
# config/maan.yaml (or ~/.maan/config.yaml)

hermes_home: ~/.hermes

server:
  host: 0.0.0.0
  port: 8080

# Override Ollama URL (useful for WSL → Windows)
# ollama_url: http://172.18.224.1:11434
```

## Docker Support

### Using Docker Compose

```bash
docker-compose up -d
```

This will start:
- Ma'an WebUI on port 8080
- Ollama on port 11434

### Volumes

- `~/.maan` - Ma'an data (sessions, persona)
- `~/.hermes` - Hermes data (memories, skills)
- `~/.ollama` - Ollama data (models)

### Dockerfile

The project includes a Dockerfile for building the Ma'an image:

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN mkdir -p /root/.maan/avatar /root/.maan/sessions /root/.hermes/memories /root/.hermes/skills
EXPOSE 8080
ENV PYTHONUNBUFFERED=1
CMD ["python", "backend/app.py", "--host", "0.0.0.0", "--port", "8080"]
```

### Persona Data

Agent identity is stored separately from the Hermes config:

```
~/.maan/
├── persona.json    # { agent_name, avatar, theme, ... }
├── avatar/         # Uploaded avatar images
│   └── avatar.png
└── config.yaml     # Optional server config override
```

### WSL Users

If Ollama runs on Windows and Hermes runs in WSL, set the Windows host IP:

```yaml
# ~/.hermes/config.yaml
ollama_base_url: http://<WINDOWS_IP>:11434
```

Find your Windows IP: `cat /etc/resolv.conf | grep nameserver`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/persona` | Get agent personalization (name, avatar, theme) |
| `PUT` | `/api/persona` | Update agent personalization |
| `POST` | `/api/persona/avatar` | Upload avatar image |
| `GET` | `/api/persona/avatar/{file}` | Serve avatar image |
| `POST` | `/api/chat` | Send a message, get a response |
| `GET` | `/api/status` | System status (Ollama, Hermes) |
| `GET` | `/api/models` | List Ollama models |
| `GET` | `/api/memories` | Get all memory files |
| `PUT` | `/api/memories/{file}` | Update a memory file |
| `GET` | `/api/skills` | List installed Hermes skills |
| `POST` | `/api/sessions/new` | Create new session |

## Memory System

The memory files are **the same files** Hermes CLI uses:

| File | Purpose | Location |
|------|---------|----------|
| `SOUL.md` | Agent personality, values, behavior rules | `~/.hermes/SOUL.md` |
| `MEMORY.md` | Accumulated knowledge & context | `~/.hermes/memories/MEMORY.md` |
| `USER.md` | User profile information | `~/.hermes/memories/USER.md` |

Edit these in the WebUI's Memory tab, and Hermes CLI will see the changes immediately. And vice versa.

## Design

The UI follows a **Cyber-noir** philosophy — inspired by [Google Stitch](https://stitch.withgoogle.com):

- **Obsidian base** (#111318) for minimal eye strain
- **Dynamic accent color** — chosen by the user, applied via CSS custom properties
- **Manrope typeface** for tech-efficient readability
- **Scanline overlay** for subtle hardware texture
- **Glassmorphism** on floating elements

See [docs/DESIGN.md](docs/DESIGN.md) for the full design system documentation.

## Project Structure

```
maan-webui/
├── backend/
│   ├── app.py              # FastAPI server + persona API
│   ├── hermes_bridge.py    # Hermes memory/skill bridge
│   └── requirements.txt
├── frontend/
│   ├── index.html          # Single-file WebUI (chat, skills, memory, settings, onboarding)
│   └── assets/
├── config/
│   └── maan.yaml           # Default config
├── scripts/
│   ├── install.sh          # Linux/Mac installer
│   └── start.sh            # Linux/Mac launcher
├── docs/
│   ├── DESIGN.md           # Design system docs
│   └── banner.png          # Repo banner
├── start.bat               # Windows one-click launcher
├── LICENSE
└── README.md
```

## Roadmap

- [x] Chat with memory sync
- [x] Customizable agent identity (name, avatar, theme)
- [x] Onboarding wizard
- [x] Settings page
- [x] Skill browser
- [x] Memory editor
- [x] Model switcher
- [x] Dynamic theming engine
- [x] Conversation history persistence
- [x] Skill invocation cards in chat
- [x] Docker support
- [x] i18n (English / Chinese)
- [ ] Streaming responses (SSE)
- [ ] Voice input/output

## Contributing

Contributions welcome! Some ideas to get started:

- Add SSE streaming for real-time responses
- Implement conversation persistence to SQLite
- Create additional theme presets
- Add i18n support
- Docker compose setup

## Credits

- [Hermes](https://github.com/hermes-ai/hermes) — The agent framework
- [Ollama](https://ollama.ai) — Local LLM inference
- [Google Stitch](https://stitch.withgoogle.com) — UI design inspiration
- [Tailwind CSS](https://tailwindcss.com) — Styling
- [FastAPI](https://fastapi.tiangolo.com) — Backend framework

## License

MIT License. See [LICENSE](LICENSE).

---

<div align="center">

**Hermes 是马，马鞍是你的。**

*Everything stays local. Your agent evolves with you.*

</div>
