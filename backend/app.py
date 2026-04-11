"""
马鞍 Ma'an - Backend Server
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
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

import httpx
import yaml
import uvicorn
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from hermes_bridge import HermesBridge


# ── Configuration ─────────────────────────────────────────────────

def load_config() -> dict:
    """Load config, falling back to defaults."""
    config_paths = [
        Path(__file__).parent.parent / "config" / "maan.yaml",
        Path.home() / ".maan" / "config.yaml",
    ]

    for path in config_paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

    return {}


# ── Personalization ───────────────────────────────────────────────

PERSONA_DIR = Path.home() / ".maan"
PERSONA_FILE = PERSONA_DIR / "persona.json"
AVATAR_DIR = PERSONA_DIR / "avatar"

DEFAULT_PERSONA = {
    "agent_name": "My Agent",
    "user_display_name": "",
    "user_avatar": "",
    "avatar": "logo.png",  # Default avatar image
    "avatar_preset": "",  # robot | face | bolt - used when no custom avatar
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


def load_persona() -> dict:
    """Load user's agent personalization."""
    persona = DEFAULT_PERSONA.copy()
    if PERSONA_FILE.exists():
        try:
            with open(PERSONA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                persona.update(saved)
        except Exception:
            pass
    return persona


def save_persona(persona: dict):
    """Save personalization to disk."""
    PERSONA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PERSONA_FILE, "w", encoding="utf-8") as f:
        json.dump(persona, f, ensure_ascii=False, indent=2)


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

# Conversation history stored in memory (per session)
# Format: { session_id: [ {role, content, timestamp}, ... ] }
conversations: dict = {}
current_session_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")

# Sessions directory for persistence
SESSIONS_DIR = Path.home() / ".maan" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Load all sessions from disk
    load_all_sessions()
    
    persona = load_persona()
    name = persona.get("agent_name") or "Your Agent"
    print("=" * 60)
    print(f"  {name} — 马鞍 Ma'an")
    print("=" * 60)
    print(f"  Hermes home : {bridge.hermes_home}")
    print(f"  Ollama URL  : {bridge.get_ollama_url()}")
    print(f"  Model       : {bridge.get_default_model()}")
    print(f"  Skills      : {len(bridge.get_skills())} installed")
    print(f"  Sessions    : {len(conversations)} loaded")
    print(f"  Setup done  : {persona.get('setup_complete', False)}")
    print("=" * 60)
    yield
    print("\nShutting down...")


# ── FastAPI App ───────────────────────────────────────────────────

app = FastAPI(
    title="马鞍 Ma'an",
    description="WebUI for Hermes Agent — your saddle for the ride",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
async def update_persona(request: Request):
    """Update agent personalization."""
    body = await request.json()
    persona = load_persona()

    # Update allowed fields
    for key in ("agent_name", "agent_subtitle", "user_display_name", "avatar", "user_avatar", "avatar_preset", "setup_complete"):
        if key in body:
            persona[key] = body[key]

    # Handle theme
    if "theme" in body:
        theme = body["theme"]
        preset = theme.get("preset", "")
        if preset in THEME_PRESETS:
            persona["theme"] = {**THEME_PRESETS[preset], "preset": preset}
        elif preset == "custom" and "accent" in theme:
            persona["theme"] = {
                "accent": theme["accent"],
                "accent_dim": theme.get("accent_dim", theme["accent"]),
                "preset": "custom",
            }

    save_persona(persona)
    return {"status": "ok", "persona": persona}


@app.post("/api/persona/avatar")
async def upload_avatar(file: UploadFile = File(...), type: str = "agent"):
    """Upload a custom avatar (agent or user)."""
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)

    # Validate file type
    if file.content_type not in ("image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"):
        raise HTTPException(status_code=400, detail="Unsupported image format")

    # Save file
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"{type}_avatar.{ext}" if type == "user" else f"avatar.{ext}"
    filepath = AVATAR_DIR / filename

    with open(filepath, "wb") as f:
        content = await file.read()
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
    # Check in avatar dir first
    filepath = AVATAR_DIR / filename
    if filepath.exists():
        return FileResponse(filepath)
    # Fallback to frontend directory
    frontend_file = frontend_dir / filename
    if frontend_file.exists():
        return FileResponse(frontend_file)
    # Fallback to project root for default assets like logo.png
    project_root = Path(__file__).parent.parent
    root_file = project_root / filename
    if root_file.exists():
        return FileResponse(root_file)
    raise HTTPException(status_code=404, detail="Avatar not found")

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
async def update_memory(filename: str, request: Request):
    """Update a memory file."""
    if filename not in ("SOUL.md", "MEMORY.md", "USER.md"):
        raise HTTPException(status_code=400, detail="Invalid memory file")

    body = await request.json()
    content = body.get("content", "")

    if bridge.write_memory(filename, content):
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
    temp_dir = Path.home() / ".maan" / "temp_skill"
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
            "created": msgs[0]["timestamp"] if msgs else "",
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
                    "created": messages[0]["timestamp"] if messages else "",
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
async def chat(request: Request):
    """
    Main chat endpoint.
    Injects Hermes memories into the system prompt, sends to Ollama,
    and stores conversation history.
    """
    body = await request.json()
    user_message = body.get("message", "")
    session_id = body.get("session_id", current_session_id)

    # Get model - from request, config, or auto-select first available
    model = body.get("model", "")
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

    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message")

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
    # Try exact file first
    file_path = frontend_dir / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    # Fallback to index.html
    index = frontend_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"error": "Frontend not found"}, status_code=404)


# ── Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="马鞍 Ma'an Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port")
    parser.add_argument("--hermes-home", default=None, help="Hermes home dir")
    args = parser.parse_args()

    if args.hermes_home:
        bridge.hermes_home = Path(args.hermes_home)

    uvicorn.run(app, host=args.host, port=args.port)
