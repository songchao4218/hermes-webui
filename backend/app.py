"""
Hermes WebUI - Backend Server
WebUI for Hermes Agent with full memory sync and customizable identity.

Architecture:
    Browser <-> FastAPI <-> Hermes Bridge <-> ~/.hermes/ (shared with CLI)
                   |
                   +------> Ollama API (model inference)
"""

import os
import json
import time
import shutil
import asyncio
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

import httpx
import yaml
import uvicorn
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from hermes_bridge import HermesBridge
from wsl_bridge import wsl_bridge
from auth import require_auth, get_or_create_token, set_auth_enabled, is_auth_enabled
from models import ChatRequest, AgentRequest, PersonaUpdate, MemoryUpdate

# ── Logging ──────────────────────────────────────────────────────

logger = logging.getLogger("hermes_webui")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ── Configuration ─────────────────────────────────────────────────

def load_config() -> dict:
    """Load config, falling back to defaults."""
    config_paths = [
        Path(__file__).parent.parent / "config" / "hermes-webui.yaml",
        Path.home() / ".hermes-webui" / "config.yaml",
    ]

    for path in config_paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

    return {}


# ── Personalization ───────────────────────────────────────────────

PERSONA_DIR = Path.home() / ".hermes-webui"
PERSONA_FILE = PERSONA_DIR / "persona.json"
AVATAR_DIR = PERSONA_DIR / "avatar"

DEFAULT_PERSONA = {
    "agent_name": "My Agent",
    "user_display_name": "",
    "user_avatar": "",
    "avatar": "logo.png",        # Default avatar: project logo
    "avatar_preset": "",         # robot | face | bolt - used when no custom avatar
    "theme": {
        "accent": "#e8a849",      # Primary accent color (amber)
        "accent_dim": "#452b00",  # Darker accent for contrast
        "preset": "amber",        # cyan | purple | green | amber | rose | custom
    },
    "setup_complete": False,
}

THEME_PRESETS = {
    "amber":  {"accent": "#e8a849", "accent_dim": "#452b00"},
    "cyan":   {"accent": "#00daf3", "accent_dim": "#005b67"},
    "purple": {"accent": "#d0bcff", "accent_dim": "#571bc1"},
    "green":  {"accent": "#81c784", "accent_dim": "#2e7d32"},
    "rose":   {"accent": "#f48fb1", "accent_dim": "#c2185b"},
}


# ── Rate Limiter ─────────────────────────────────────────────────
# Limits chat/agent requests per IP to prevent accidental Ollama overload.
limiter = Limiter(key_func=get_remote_address)


def load_persona() -> dict:
    """Load user's agent personalization."""
    import copy
    persona = copy.deepcopy(DEFAULT_PERSONA)
    if PERSONA_FILE.exists():
        try:
            with open(PERSONA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                # Deep-merge to preserve nested defaults (e.g. theme keys)
                for key, value in saved.items():
                    if isinstance(value, dict) and isinstance(persona.get(key), dict):
                        persona[key] = {**persona[key], **value}
                    else:
                        persona[key] = value
        except Exception:
            pass
    return persona


def save_persona(persona: dict):
    """Save personalization to disk."""
    PERSONA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PERSONA_FILE, "w", encoding="utf-8") as f:
        json.dump(persona, f, ensure_ascii=False, indent=2)


def _evict_old_sessions():
    """Keep at most 100 sessions in memory; evict oldest by session_id (timestamp-based)."""
    MAX_SESSIONS = 100
    if len(conversations) > MAX_SESSIONS:
        sorted_keys = sorted(conversations.keys())
        for key in sorted_keys[:len(conversations) - MAX_SESSIONS]:
            del conversations[key]


def save_session(session_id: str, messages: list):
    """Save session to disk."""
    try:
        filepath = SESSIONS_DIR / f"{session_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_session(session_id: str) -> list:
    """Load session from disk."""
    try:
        filepath = SESSIONS_DIR / f"{session_id}.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def load_all_sessions():
    """Load all sessions from disk into memory."""
    global conversations
    try:
        for filepath in SESSIONS_DIR.glob("*.json"):
            session_id = filepath.stem
            messages = load_session(session_id)
            if messages:
                conversations[session_id] = messages
    except Exception:
        pass


# ── App Lifecycle ─────────────────────────────────────────────────

config = load_config()
bridge = HermesBridge(config.get("hermes_home"))

def find_hermes_cmd() -> Optional[str]:
    """
    Find the hermes executable, checking multiple locations:
    1. Standard PATH via shutil.which
    2. Common install locations (venv, pipx, local)
    3. WSL2 paths (for Windows users)
    4. ~/start-hermes.sh wrapper script (common custom install)
    """
    # 1. Standard PATH
    cmd = shutil.which("hermes")
    if cmd:
        return cmd

    # 2. Common install locations (Unix/Linux)
    candidates = [
        Path.home() / "hermes-agent" / "venv" / "bin" / "hermes",
        Path.home() / ".local" / "bin" / "hermes",
        Path.home() / ".venv" / "bin" / "hermes",
        Path("/usr/local/bin/hermes"),
    ]
    for p in candidates:
        if p.exists() and os.access(p, os.X_OK):
            return str(p)

    # 3. WSL2 paths (Windows users with WSL)
    # Check if we're in WSL or Windows with WSL
    wsl_candidates = [
        # WSL2 mounted Windows home
        Path("/mnt/c/Users") / os.getenv("USERNAME", "") / ".hermes" / "hermes-agent" / "venv" / "bin" / "hermes",
        Path("/mnt/c/Users") / os.getenv("USER", "") / ".hermes" / "hermes-agent" / "venv" / "bin" / "hermes",
        # Direct WSL paths (when running in WSL)
        Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "hermes",
        Path("/home") / os.getenv("USER", "") / ".hermes" / "hermes-agent" / "venv" / "bin" / "hermes",
        # Common Ubuntu WSL usernames (auto-detected via USER env var above)
    ]
    for p in wsl_candidates:
        if p.exists() and os.access(p, os.X_OK):
            return str(p)
    
    # 4. Windows native Python paths
    windows_candidates = [
        Path.home() / ".hermes" / "hermes-agent" / "venv" / "Scripts" / "hermes.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python311" / "Scripts" / "hermes.exe",
        Path("C:") / "Users" / os.getenv("USERNAME", "") / "AppData" / "Roaming" / "Python" / "Python311" / "Scripts" / "hermes.exe",
    ]
    for p in windows_candidates:
        if p.exists():
            return str(p)
    
    # 5. WSL wrapper script (for Windows users with WSL Hermes)
    # Only use if WSL is actually available on this machine
    wrapper = Path(__file__).parent / "hermes_wrapper.bat"
    if wrapper.exists():
        try:
            result = subprocess.run(
                ["wsl", "--status"], capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return str(wrapper)
        except Exception:
            pass

    # 6. Wrapper script (e.g. ~/start-hermes.sh)
    wrapper = Path.home() / "start-hermes.sh"
    if wrapper.exists() and os.access(wrapper, os.X_OK):
        return str(wrapper)

    return None

# Detect local Hermes CLI
HERMES_CMD = find_hermes_cmd()

# ── WSL / Windows path detection ─────────────────────────────────
# Use the new WSLBridge for enhanced WSL2 support

WINDOWS_HOME = wsl_bridge.windows_home  # e.g. "/mnt/c/Users/47291" or None

# Conversation history stored in memory (per session)
# Format: { session_id: [ {role, content, timestamp}, ... ] }
conversations: dict = {}
current_session_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")

# Session locks to prevent concurrent write races
_session_locks: dict[str, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()


async def get_session_lock(session_id: str) -> asyncio.Lock:
    """Get or create a lock for a specific session."""
    async with _locks_lock:
        if session_id not in _session_locks:
            _session_locks[session_id] = asyncio.Lock()
        return _session_locks[session_id]

# Sessions directory for persistence
SESSIONS_DIR = Path.home() / ".hermes-webui" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Load all sessions from disk
    load_all_sessions()

    persona = load_persona()
    logger.info("=" * 60)
    logger.info("  马鞍 Saddle — The Saddle for Hermes")
    logger.info("=" * 60)
    logger.info(f"  Hermes home : {bridge.hermes_home}")
    logger.info(f"  Hermes CLI  : {HERMES_CMD or 'NOT FOUND — install hermes-agent'}")
    if wsl_bridge.is_wsl:
        logger.info(f"  WSL2 env    : {wsl_bridge.wsl_distro} (Windows home: {WINDOWS_HOME})")
    logger.info(f"  Ollama URL  : {bridge.get_ollama_url()}")
    logger.info(f"  Model       : {bridge.get_default_model()}")
    logger.info(f"  Skills      : {len(bridge.get_skills())} installed")
    logger.info(f"  Sessions    : {len(conversations)} loaded")
    logger.info(f"  Auth        : {'disabled (--no-auth)' if not is_auth_enabled() else 'enabled'}")
    if is_auth_enabled():
        token = get_or_create_token()
        logger.info(f"  Token       : {token}")
    logger.info(f"  Setup done  : {persona.get('setup_complete', False)}")
    logger.info("=" * 60)
    yield
    # Graceful shutdown: persist all sessions
    logger.info("Shutting down — saving all sessions...")
    for sid, msgs in conversations.items():
        save_session(sid, msgs)
    logger.info(f"Saved {len(conversations)} sessions. Goodbye.")


# ── FastAPI App ───────────────────────────────────────────────────

# ── CORS Configuration ───────────────────────────────────────────

def _get_cors_origins() -> list[str]:
    """Build allowed CORS origins from config and environment."""
    origins = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:8082",
        "http://127.0.0.1:8082",
        "http://localhost:8083",
        "http://127.0.0.1:8083",
    ]
    # Allow custom origins from environment
    env_origins = os.environ.get("HERMES_CORS_ORIGINS", "")
    if env_origins:
        origins.extend(o.strip() for o in env_origins.split(",") if o.strip())
    # Allow custom origins from config
    config_origins = config.get("allowed_origins", [])
    if isinstance(config_origins, list):
        origins.extend(config_origins)
    return origins


app = FastAPI(
    title="马鞍 Saddle",
    description="The Saddle for Hermes — WebUI for Hermes Agent",
    version="0.5.1",
    lifespan=lifespan,
    dependencies=[Depends(require_auth)],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Routes ────────────────────────────────────────────────────

# ── Persona (Agent Customization) ─────────────────────────────────

@app.get("/api/persona")
async def get_persona():
    """Get current agent personalization (name, avatar, theme)."""
    persona = load_persona()
    persona["theme_presets"] = THEME_PRESETS
    return persona


@app.put("/api/persona")
async def update_persona(body: PersonaUpdate):
    """Update agent personalization."""
    persona = load_persona()

    # Update allowed fields from validated model
    updates = body.model_dump(exclude_none=True, exclude={"theme"})
    for key, value in updates.items():
        persona[key] = value

    # Handle theme
    if body.theme:
        theme = body.theme
        preset = theme.preset or ""
        if preset in THEME_PRESETS:
            persona["theme"] = {**THEME_PRESETS[preset], "preset": preset}
        elif preset == "custom" and theme.accent:
            persona["theme"] = {
                "accent": theme.accent,
                "accent_dim": theme.accent_dim or theme.accent,
                "preset": "custom",
            }

    save_persona(persona)
    return {"status": "ok", "persona": persona}


@app.post("/api/persona/avatar")
async def upload_avatar(file: UploadFile = File(...), type: str = Form(default="agent")):
    """Upload a custom avatar (agent or user)."""
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)

    # Validate file type
    ALLOWED_TYPES = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/svg+xml": "svg",
    }
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    # Use extension derived from content_type, not filename (prevents extension spoofing)
    ext = ALLOWED_TYPES[file.content_type]
    filename = f"{type}_avatar.{ext}" if type == "user" else f"avatar.{ext}"
    filepath = AVATAR_DIR / filename

    # Enforce 5 MB file size limit
    MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Avatar file too large. Maximum size is 5 MB.",
        )

    with open(filepath, "wb") as f:
        f.write(content)

    # Update persona
    persona = load_persona()
    if type == "user":
        persona["user_avatar"] = filename
    else:
        persona["avatar"] = filename
    save_persona(persona)

    return {"status": "ok", "avatar": filename}


@app.get("/api/persona/avatar/{filename}")
async def serve_avatar(filename: str):
    """Serve the uploaded avatar file."""
    # Prevent path traversal: reject any filename containing path separators
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Check in avatar dir first
    filepath = (AVATAR_DIR / filename).resolve()
    if not str(filepath).startswith(str(AVATAR_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if filepath.exists():
        return FileResponse(filepath)
    # Fallback to frontend directory
    frontend_file = (frontend_dir / filename).resolve()
    if frontend_file.exists() and str(frontend_file).startswith(str(frontend_dir.resolve())):
        return FileResponse(frontend_file)
    # Fallback to project root for default assets like logo.png
    project_root = Path(__file__).parent.parent
    root_file = (project_root / filename).resolve()
    if root_file.exists() and str(root_file).startswith(str(project_root.resolve())):
        return FileResponse(root_file)
    raise HTTPException(status_code=404, detail="Avatar not found")


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker / monitoring."""
    return {"status": "ok", "version": app.version}


# ── Self-update ───────────────────────────────────────────────────

REPO_API = "https://api.github.com/repos/songchao4218/hermes-webui/commits/main"
PROJECT_ROOT = Path(__file__).parent.parent

def get_local_commit() -> str:
    """Get the current local git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()[:7] if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"

def is_git_repo() -> bool:
    """Check if the project is a git repository."""
    return (PROJECT_ROOT / ".git").exists()


@app.get("/api/update/check")
async def check_update():
    """Check if a newer version is available on GitHub."""
    if not is_git_repo():
        return {"has_update": False, "error": "Not a git repository"}

    local_commit = get_local_commit()

    try:
        # Use system proxy if available
        proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or \
                os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")
        client_kwargs = {"timeout": 10}
        if proxy:
            client_kwargs["proxy"] = proxy

        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.get(
                REPO_API,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if resp.status_code != 200:
                return {"has_update": False, "error": f"GitHub API error: {resp.status_code}"}

            data = resp.json()
            remote_sha = data.get("sha", "")[:7]
            remote_message = data.get("commit", {}).get("message", "").split("\n")[0]
            remote_date = data.get("commit", {}).get("author", {}).get("date", "")[:10]

            has_update = remote_sha != local_commit and local_commit != "unknown"

            return {
                "has_update": has_update,
                "local_commit": local_commit,
                "remote_commit": remote_sha,
                "remote_message": remote_message,
                "remote_date": remote_date,
            }
    except Exception as e:
        return {"has_update": False, "error": str(e)}


@app.post("/api/update/apply")
async def apply_update():
    """Pull latest changes from GitHub and restart."""
    if not is_git_repo():
        raise HTTPException(status_code=400, detail="Not a git repository")

    async def stream_update():
        try:
            # git pull
            proc = await asyncio.create_subprocess_exec(
                "git", "pull", "--ff-only",
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            async for line in proc.stdout:
                yield f"data: {json.dumps({'log': line.decode('utf-8', errors='replace').rstrip()})}\n\n"
            await proc.wait()

            if proc.returncode != 0:
                yield f"data: {json.dumps({'error': 'git pull failed'})}\n\n"
                return

            # pip install -r requirements.txt (in case deps changed)
            pip_cmd = "pip3" if shutil.which("pip3") else "pip"
            req_file = str(PROJECT_ROOT / "backend" / "requirements.txt")
            proc2 = await asyncio.create_subprocess_exec(
                pip_cmd, "install", "-r", req_file, "-q",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            async for line in proc2.stdout:
                yield f"data: {json.dumps({'log': line.decode('utf-8', errors='replace').rstrip()})}\n\n"
            await proc2.wait()

            yield f"data: {json.dumps({'done': True, 'message': 'Update complete. Please refresh the page.'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_update(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/status")
async def get_status():
    """System status: Ollama connection, Hermes state, model info."""
    ollama_url = bridge.get_ollama_url()
    ollama_ok = False
    available_models = []

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            ollama_ok = resp.status_code == 200
            if ollama_ok:
                data = resp.json()
                available_models = [m["name"] for m in data.get("models", [])]
    except Exception:
        pass

    # Use first available model if none configured
    default_model = bridge.get_default_model()
    if not default_model and available_models:
        default_model = available_models[0]

    return {
        "ollama": {
            "url": ollama_url,
            "connected": ollama_ok,
        },
        "hermes": {
            "home": str(bridge.hermes_home),
            "gateway": bridge.get_gateway_status(),
            "cli_available": bool(HERMES_CMD),
            "cli_path": HERMES_CMD,
            "windows_home": WINDOWS_HOME,
        },
        "wsl": {
            "is_wsl": wsl_bridge.is_wsl,
            "is_wsl2": wsl_bridge.is_wsl2,
            "distro": wsl_bridge.wsl_distro,
            "windows_home": wsl_bridge.windows_home,
        },
        "model": default_model,
        "session_id": current_session_id,
    }


@app.get("/api/models")
async def get_models():
    """List available Ollama models."""
    ollama_url = bridge.get_ollama_url()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            data = resp.json()
            models = [
                {
                    "name": m["name"],
                    "size": m.get("size", 0),
                    "modified": m.get("modified_at", ""),
                }
                for m in data.get("models", [])
            ]
            # Use first model as default if none configured
            default_model = bridge.get_default_model()
            if not default_model and models:
                default_model = models[0]["name"]
            return {
                "models": models,
                "default": default_model,
            }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama unreachable: {e}")


@app.get("/api/memories")
async def get_memories():
    """Get all memory files."""
    return bridge.get_all_memories()


@app.put("/api/memories/{filename}")
async def update_memory(filename: str, body: MemoryUpdate):
    """Update a memory file."""
    if filename not in ("SOUL.md", "MEMORY.md", "USER.md"):
        raise HTTPException(status_code=400, detail="Invalid memory file")

    if bridge.write_memory(filename, body.content):
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=500, detail="Failed to write memory")


@app.get("/api/skills")
async def get_skills():
    """List all installed Hermes skills."""
    return {"skills": bridge.get_skills()}


@app.post("/api/skills/import")
async def import_skill(file: UploadFile = File(...)):
    """Import a skill from a zip file."""
    import zipfile
    import shutil

    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    # Create temp directory for extraction
    temp_dir = Path.home() / ".hermes-webui" / "temp_skill"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Save and extract zip
    zip_path = temp_dir / "skill.zip"
    with open(zip_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Find the skill directory (should contain SKILL.md or hermes_skill.json)
        skill_dir = None
        for item in temp_dir.iterdir():
            if item.is_dir():
                if (item / "SKILL.md").exists() or (item / "hermes_skill.json").exists():
                    skill_dir = item
                    break

        if not skill_dir:
            # Check if files were extracted directly to temp_dir
            if (temp_dir / "SKILL.md").exists() or (temp_dir / "hermes_skill.json").exists():
                skill_dir = temp_dir
            else:
                raise HTTPException(status_code=400, detail="Invalid skill package: missing SKILL.md or hermes_skill.json")

        # Get skill id and name from hermes_skill.json or directory
        skill_id = skill_dir.name
        skill_name = skill_dir.name
        skill_desc = ""
        if (skill_dir / "hermes_skill.json").exists():
            import json
            with open(skill_dir / "hermes_skill.json", encoding="utf-8") as f:
                skill_data = json.load(f)
                skill_id = skill_data.get("id", skill_data.get("name", skill_id))
                skill_name = skill_data.get("name", skill_name)
                skill_desc = skill_data.get("description", "")
                print(f"[Import Skill] Found hermes_skill.json: id={skill_id}, name={skill_name}")

        # Copy to Hermes skills directory (use id as directory name)
        target_dir = bridge.skills_dir / skill_id
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(skill_dir, target_dir)

        # Cleanup
        shutil.rmtree(temp_dir)

        return {"status": "ok", "skill": skill_id, "name": skill_name}
    except HTTPException:
        raise
    except Exception as e:
        # Cleanup on error
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")


@app.get("/api/sessions")
async def get_sessions():
    """List conversation sessions."""
    # Combine in-memory sessions with Hermes sessions
    sessions = []
    for sid, msgs in conversations.items():
        sessions.append({
            "id": sid,
            "name": msgs[0]["content"][:50] if msgs else "New Session",
            "message_count": len(msgs),
            "created": msgs[0].get("timestamp", "") if msgs else "",
        })
    
    # Also load sessions from disk that might not be in memory
    for filepath in SESSIONS_DIR.glob("*.json"):
        session_id = filepath.stem
        if session_id not in conversations:
            messages = load_session(session_id)
            if messages:
                sessions.append({
                    "id": session_id,
                    "name": messages[0]["content"][:50] if messages else "New Session",
                    "message_count": len(messages),
                    "created": messages[0].get("timestamp", "") if messages else "",
                })
    
    # Sort sessions by created time (newest first)
    sessions.sort(key=lambda x: x["created"] or "", reverse=True)
    
    return {"sessions": sessions, "current": current_session_id}


@app.post("/api/sessions/new")
async def new_session():
    """Create a new conversation session."""
    global current_session_id
    current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    conversations[current_session_id] = []
    _evict_old_sessions()
    return {"session_id": current_session_id}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    global current_session_id
    # Remove from memory
    if session_id in conversations:
        del conversations[session_id]
    # Remove from disk
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if filepath.exists():
        filepath.unlink()
    # Reset current session if it was the deleted one
    if current_session_id == session_id:
        current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        conversations[current_session_id] = []
    return {"status": "ok"}


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get messages for a session."""
    # Try to get from memory first
    if session_id in conversations:
        return {"messages": conversations[session_id]}
    # Fallback to disk
    messages = load_session(session_id)
    # Load into memory for future use
    conversations[session_id] = messages
    return {"messages": messages}


@app.post("/api/chat")
@limiter.limit("60/minute")
async def chat(request: Request, body: ChatRequest):
    """
    Main chat endpoint.
    Injects Hermes memories into the system prompt, sends to Ollama,
    and stores conversation history.
    """
    user_message = body.message
    session_id = body.session_id or current_session_id

    # Get model - from request, config, or auto-select first available
    model = body.model or ""
    if not model:
        model = bridge.get_default_model()
    if not model:
        # Auto-select first available model from Ollama
        try:
            ollama_url = bridge.get_ollama_url()
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    if models:
                        model = models[0]["name"]
        except Exception:
            pass

    if not model:
        raise HTTPException(status_code=400, detail="No model available")

    lock = await get_session_lock(session_id)
    async with lock:
        # Initialize session if needed
        if session_id not in conversations:
            conversations[session_id] = []

        # Record user message
        conversations[session_id].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
        })

        # Build system prompt from Hermes memories
        system_prompt = bridge.build_system_prompt()

        # Build message history for context
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Include recent conversation history (last 20 messages for context)
        recent = conversations[session_id][-20:]
        for msg in recent:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Call Ollama
        ollama_url = bridge.get_ollama_url()
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{ollama_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                    },
                )
                data = resp.json()
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Ollama request failed: {e}",
            )

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract response
        assistant_content = ""
        if "choices" in data and data["choices"]:
            assistant_content = data["choices"][0].get("message", {}).get(
                "content", ""
            )
        elif "message" in data:
            assistant_content = data["message"].get("content", "")

        if not assistant_content:
            assistant_content = "No response received."

        # Record assistant message
        conversations[session_id].append({
            "role": "assistant",
            "content": assistant_content,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "latency_ms": latency_ms,
        })

        # Save session to disk
        save_session(session_id, conversations[session_id])

    return {
        "content": assistant_content,
        "model": model,
        "latency_ms": latency_ms,
        "session_id": session_id,
    }


@app.post("/api/chat/stream")
@limiter.limit("60/minute")
async def chat_stream(request: Request, body: ChatRequest):
    """
    Streaming chat endpoint using SSE.
    Sends tokens as they arrive from Ollama, then a final [DONE] event
    with metadata (model, latency_ms, session_id).
    """
    user_message = body.message
    session_id = body.session_id or current_session_id

    model = body.model or ""
    if not model:
        model = bridge.get_default_model()
    if not model:
        try:
            ollama_url = bridge.get_ollama_url()
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    if models:
                        model = models[0]["name"]
        except Exception:
            pass

    if not model:
        raise HTTPException(status_code=400, detail="No model available")
    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message")

    if session_id not in conversations:
        conversations[session_id] = []

    conversations[session_id].append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat(),
    })

    system_prompt = bridge.build_system_prompt()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    recent = conversations[session_id][-20:]
    for msg in recent:
        messages.append({"role": msg["role"], "content": msg["content"]})

    ollama_url = bridge.get_ollama_url()
    start_time = time.time()

    async def generate():
        full_content = ""
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    f"{ollama_url}/v1/chat/completions",
                    json={"model": model, "messages": messages, "stream": True},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                full_content += token
                                yield f"data: {json.dumps({'token': token})}\n\n"
                        except Exception:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        latency_ms = int((time.time() - start_time) * 1000)
        if not full_content:
            full_content = "No response received."

        conversations[session_id].append({
            "role": "assistant",
            "content": full_content,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "latency_ms": latency_ms,
        })
        save_session(session_id, conversations[session_id])

        yield f"data: {json.dumps({'done': True, 'model': model, 'latency_ms': latency_ms, 'session_id': session_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Agent Mode (Hermes CLI proxy) ────────────────────────────────

@app.post("/api/agent/run")
@limiter.limit("20/minute")
async def agent_run(request: Request, body: AgentRequest):
    """
    Agent endpoint: proxies the user message to the local Hermes CLI
    and streams back its output line by line as SSE.

    Requires `hermes` to be installed and on PATH.
    Uses: hermes chat -Q --yolo -q "<message>"

    Enhanced for WSL2: Automatically converts Windows paths to WSL paths
    and provides context to the LLM about the Windows file system.
    """
    if not HERMES_CMD:
        raise HTTPException(
            status_code=503,
            detail="Hermes CLI not found. Install it with: pip install hermes-agent",
        )

    user_message = body.message.strip()
    session_id = body.session_id or current_session_id

    # Record user message
    if session_id not in conversations:
        conversations[session_id] = []
    conversations[session_id].append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat(),
    })

    async def generate():
        full_output = []
        start_time = time.time()

        # Convert user input: Windows paths → WSL paths
        query = wsl_bridge.convert_user_input(user_message)

        # Inject Windows path context
        username = os.environ.get("USERNAME", "")
        windows_home = wsl_bridge.windows_home or (f"/mnt/c/Users/{username}" if username else "")
        if windows_home:
            context_prompt = (
                f"[System: Running via WSL2. Windows home is at {windows_home}. "
                f"Desktop={windows_home}/Desktop, Downloads={windows_home}/Downloads, "
                f"Documents={windows_home}/Documents. "
                f"Always use /mnt/c/... paths to access Windows files. "
                f"Execute tasks directly without asking for clarification.]"
            )
            query = f"{context_prompt}\n\n{query}"

        # Build command — on Windows use wsl.exe directly to avoid shell quoting issues
        hermes_bin = "/home/songchao/hermes-agent/venv/bin/hermes"
        # Try to find hermes path in WSL
        try:
            r = await asyncio.create_subprocess_exec(
                "wsl.exe", "-d", "Ubuntu", "which", "hermes",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            out, _ = await asyncio.wait_for(r.communicate(), timeout=5)
            found = out.decode("utf-8", errors="replace").strip()
            if found:
                hermes_bin = found
        except Exception:
            pass

        cmd = [
            "wsl.exe", "-d", "Ubuntu",
            hermes_bin, "chat",
            "-Q", "--yolo", "--source", "tool",
            "-q", query,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=None,
            )

            # Hard timeout: kill Hermes if it takes more than 120s
            try:
                async with asyncio.timeout(120):
                    async for raw_line in proc.stdout:
                        # Try multiple encodings to handle WSL output
                        line = None
                        for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
                            try:
                                line = raw_line.decode(encoding)
                                break
                            except UnicodeDecodeError:
                                continue
                        if line is None:
                            line = raw_line.decode("utf-8", errors="replace")

                        # Strip ANSI escape codes
                        import re as _re
                        line = _re.sub(r'\x1b\[[0-9;]*[mGKHFJA-Za-z]', '', line)
                        line = _re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)', '', line)
                        line = _re.sub(r'\x1b[()][AB012]', '', line)
                        line = _re.sub(r'\r', '', line)
                        # Strip spinner/progress characters
                        line = _re.sub(r'[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏✓✗⠿]', '', line)
                        # Strip box-drawing and other non-printable chars
                        line = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', line)

                        # Filter WSL warning messages
                        line_lower = line.lower()
                        if ('wsl' in line_lower and 'localhost' in line_lower) or \
                           line.strip().startswith('wsl:'):
                            continue

                        # Skip blank lines
                        if not line.strip():
                            continue

                        # Convert WSL paths back to Windows paths for display
                        if wsl_bridge.is_wsl:
                            line = wsl_bridge.convert_output(line)

                        # Filter done/error JSON events and session_id lines
                        stripped = line.strip()
                        if (stripped.startswith('{"done":') or
                                stripped.startswith('{"error":') or
                                stripped.startswith('session_id:') or
                                _re.match(r'^session_id:\s*\S+', stripped)):
                            continue

                        full_output.append(line)
                        yield f"data: {json.dumps({'token': line})}\n\n"

            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                yield f"data: {json.dumps({'error': 'Agent timed out after 120s'})}\n\n"
                return

            await proc.wait()

        except Exception as e:
            err = f"Agent error: {e}"
            yield f"data: {json.dumps({'error': err})}\n\n"
            return

        latency_ms = int((time.time() - start_time) * 1000)
        full_text = "".join(full_output).strip()

        # Save to session history
        conversations[session_id].append({
            "role": "assistant",
            "content": full_text,
            "timestamp": datetime.now().isoformat(),
            "latency_ms": latency_ms,
            "source": "hermes_agent",
        })
        save_session(session_id, conversations[session_id])

        yield f"data: {json.dumps({'done': True, 'latency_ms': latency_ms, 'session_id': session_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Static Files (Frontend) ──────────────────────────────────────

frontend_dir = Path(__file__).parent.parent / "frontend"

# Mount assets
if (frontend_dir / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(frontend_dir / "assets")),
        name="assets",
    )

# Serve index.html for all non-API routes (SPA fallback)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # Try exact file first — must stay within frontend_dir
    file_path = (frontend_dir / full_path).resolve()
    if file_path.is_file() and str(file_path).startswith(str(frontend_dir.resolve())):
        return FileResponse(file_path)
    # Fallback to index.html
    index = frontend_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"error": "Frontend not found"}, status_code=404)


# ── Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hermes WebUI Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port")
    parser.add_argument("--hermes-home", default=None, help="Hermes home dir")
    parser.add_argument("--no-auth", action="store_true", help="Disable API token authentication")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level (default: INFO)")
    parser.add_argument("--cors-origin", action="append", default=[], help="Additional CORS origins")
    args = parser.parse_args()

    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Configure auth
    if args.no_auth:
        set_auth_enabled(False)

    if args.hermes_home:
        bridge.hermes_home = Path(args.hermes_home)

    uvicorn.run(app, host=args.host, port=args.port)
