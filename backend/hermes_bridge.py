"""
马鞍 Ma'an - Hermes Bridge
Bridges the WebUI to Hermes Agent's memory, session, and skill systems.
Ensures CLI and WebUI share the same brain.
"""

import os
import yaml
import sqlite3
import json
import glob
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


class HermesBridge:
    """
    Core bridge between WebUI and Hermes Agent.
    Reads/writes the same files Hermes uses, ensuring full memory sync.
    """

    def __init__(self, hermes_home: Optional[str] = None):
        self.hermes_home = Path(hermes_home or os.path.expanduser("~/.hermes"))
        self.memories_dir = self.hermes_home / "memories"
        self.sessions_dir = self.hermes_home / "sessions"
        self.skills_dir = self.hermes_home / "skills"
        self.state_db = self.hermes_home / "state.db"
        self.config_path = self.hermes_home / "config.yaml"
        self.soul_path = self.hermes_home / "SOUL.md"

    # ── Configuration ─────────────────────────────────────────────

    def get_config(self) -> dict:
        """Read Hermes config.yaml"""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_ollama_url(self) -> str:
        """Extract Ollama base URL from Hermes config"""
        config = self.get_config()
        # Try multiple config paths
        url = config.get("ollama_base_url", "")
        if not url:
            model_cfg = config.get("model", {})
            base_url = model_cfg.get("base_url", "")
            if base_url:
                # Remove /v1 suffix for Ollama native API
                url = re.sub(r"/v1/?$", "", base_url)
        return url or "http://localhost:11434"

    def get_default_model(self) -> str:
        """Get default model from Hermes config"""
        config = self.get_config()
        return config.get("model", {}).get("default", "")

    # ── Memory System ─────────────────────────────────────────────

    def read_memory(self, filename: str) -> str:
        """Read a memory file (SOUL.md, MEMORY.md, USER.md)"""
        # SOUL.md is in hermes root, others in memories/
        if filename == "SOUL.md":
            path = self.soul_path
        else:
            path = self.memories_dir / filename

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def write_memory(self, filename: str, content: str) -> bool:
        """Write to a memory file"""
        if filename == "SOUL.md":
            path = self.soul_path
        else:
            self.memories_dir.mkdir(parents=True, exist_ok=True)
            path = self.memories_dir / filename

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False

    def get_all_memories(self) -> dict:
        """Get all memory files as a dict"""
        return {
            "SOUL.md": self.read_memory("SOUL.md"),
            "MEMORY.md": self.read_memory("MEMORY.md"),
            "USER.md": self.read_memory("USER.md"),
        }

    def build_system_prompt(self) -> str:
        """
        Build the system prompt by combining all memory files.
        This is the key to memory continuity between CLI and WebUI.
        """
        memories = self.get_all_memories()
        parts = []

        if memories["SOUL.md"]:
            parts.append(memories["SOUL.md"])

        if memories["MEMORY.md"]:
            parts.append(
                "# Current Memory\n\n"
                "The following is your accumulated knowledge and context:\n\n"
                + memories["MEMORY.md"]
            )

        if memories["USER.md"]:
            parts.append(
                "# User Profile\n\n"
                "Information about the user you are assisting:\n\n"
                + memories["USER.md"]
            )

        return "\n\n---\n\n".join(parts)

    # ── Session Management ────────────────────────────────────────

    def get_sessions(self) -> list:
        """List all conversation sessions"""
        sessions = []
        if self.sessions_dir.exists():
            for f in sorted(self.sessions_dir.iterdir(), reverse=True):
                if f.suffix == ".json" or f.is_dir():
                    sessions.append({
                        "id": f.stem,
                        "name": f.stem,
                        "modified": datetime.fromtimestamp(
                            f.stat().st_mtime
                        ).isoformat(),
                    })
        return sessions

    def get_history_from_db(self, limit: int = 50) -> list:
        """Read conversation history from Hermes state.db"""
        if not self.state_db.exists():
            return []

        try:
            conn = sqlite3.connect(str(self.state_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Try to find the messages table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row["name"] for row in cursor.fetchall()]

            history = []

            # Hermes uses different table structures depending on version
            if "messages" in tables:
                cursor.execute(
                    "SELECT * FROM messages ORDER BY rowid DESC LIMIT ?",
                    (limit,),
                )
                for row in cursor.fetchall():
                    history.append(dict(row))
            elif "conversation" in tables:
                cursor.execute(
                    "SELECT * FROM conversation ORDER BY rowid DESC LIMIT ?",
                    (limit,),
                )
                for row in cursor.fetchall():
                    history.append(dict(row))

            conn.close()
            return list(reversed(history))
        except Exception as e:
            print(f"Error reading state.db: {e}")
            return []

    # ── Skills ────────────────────────────────────────────────────

    def get_skills(self) -> list:
        """List all installed Hermes skills with metadata"""
        skills = []
        if not self.skills_dir.exists():
            return skills

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            skill_info = {
                "id": skill_dir.name,
                "name": skill_dir.name,
                "description": "",
                "type": "official",
                "installed": True,
            }

            # Try reading SKILL.md for description
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    # Extract first line or description
                    lines = content.strip().split("\n")
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            skill_info["description"] = line[:200]
                            break
                        elif line.startswith("# "):
                            skill_info["name"] = line[2:].strip()
                except Exception:
                    pass

            # Try reading hermes_skill.json
            skill_json = skill_dir / "hermes_skill.json"
            if skill_json.exists():
                try:
                    data = json.loads(skill_json.read_text(encoding="utf-8"))
                    skill_info["name"] = data.get("name", skill_info["name"])
                    skill_info["description"] = data.get(
                        "description", skill_info["description"]
                    )
                except Exception:
                    pass

            skills.append(skill_info)

        return skills

    # ── Status ────────────────────────────────────────────────────

    def get_gateway_status(self) -> dict:
        """Check if Hermes Gateway is running"""
        pid_file = self.hermes_home / "gateway.pid"
        state_file = self.hermes_home / "gateway_state.json"

        status = {"running": False, "pid": None, "port": 8642}

        if pid_file.exists():
            try:
                pid_data = json.loads(pid_file.read_text(encoding="utf-8"))
                status["pid"] = pid_data.get("pid")
                status["running"] = True
            except Exception:
                pass

        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                status.update(state)
            except Exception:
                pass

        return status
