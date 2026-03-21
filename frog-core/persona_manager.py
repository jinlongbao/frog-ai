import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
PERSONA_FILE = os.path.join(KNOWLEDGE_DIR, "persona.json")
MEMORY_FILE = os.path.join(KNOWLEDGE_DIR, "project_memory.json")
CONVERSATION_LOG_FILE = os.path.join(KNOWLEDGE_DIR, "conversation_log.jsonl")

PERSONA_TTL_HOURS = 24  # Regenerate persona every 24 hours


def append_conversation_turn(role: str, content: str):
    """Append a conversation turn to the rolling log for persona inference."""
    try:
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        entry = {
            "role": role,
            "content": content[:500],
            "ts": datetime.now().isoformat()
        }
        with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _get_recent_conversation_snippet(max_turns: int = 20) -> str:
    """Read the last N turns from the conversation log."""
    if not os.path.exists(CONVERSATION_LOG_FILE):
        return ""
    try:
        with open(CONVERSATION_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        recent = lines[-max_turns:] if len(lines) > max_turns else lines
        turns = []
        for line in recent:
            try:
                entry = json.loads(line.strip())
                role = entry.get("role", "unknown")
                content = entry.get("content", "")
                turns.append(f"{role.upper()}: {content}")
            except Exception:
                pass
        return "\n".join(turns)
    except Exception:
        return ""


def _is_stale() -> bool:
    """Returns True if the persona file needs regeneration."""
    if not os.path.exists(PERSONA_FILE):
        return True
    try:
        with open(PERSONA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        last_updated = datetime.fromisoformat(data.get("last_updated", "2000-01-01"))
        return datetime.now() - last_updated > timedelta(hours=PERSONA_TTL_HOURS)
    except Exception:
        return True


def generate_persona(force: bool = False) -> dict:
    """Generate or refresh a data-driven persona from memory + recent conversations."""
    if not force and not _is_stale():
        return {"status": "skipped", "message": "Persona still fresh (< 24h old)"}

    try:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"status": "error", "message": "API key missing"}

        memory_content = ""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    memory_content = f.read(3000)
            except Exception:
                pass

        conversation_snippet = _get_recent_conversation_snippet(max_turns=30)

        if not memory_content.strip() and not conversation_snippet.strip():
            return {"status": "skipped", "message": "No data available to generate persona"}

        prompt = """You are building a dynamic AI persona based on the user's project memory and recent conversations.
Analyze the data below and extract the user's communication style, primary domain, and clear preferences.
Output ONLY a 2-3 sentence persona description in English that the AI should adopt.
Start with "You are a" or "As an AI assistant, you".

=== PROJECT MEMORY ===
{memory}

=== RECENT CONVERSATION HISTORY ===
{conversation}
""".format(memory=memory_content or "(none)", conversation=conversation_snippet or "(none)")

        from openai import OpenAI
        import httpx
        base_url = os.getenv("OPENAI_BASE_URL", "")
        http_client = httpx.Client(follow_redirects=True, timeout=60.0)
        client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None,
            http_client=http_client
        )

        response = client.chat.completions.create(
            model=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.4
        )

        persona_text = response.choices[0].message.content.strip()

        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        with open(PERSONA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "persona": persona_text,
                "last_updated": datetime.now().isoformat(),
                "evidence_memory_chars": len(memory_content),
                "evidence_conversation_turns": conversation_snippet.count("\n") + 1
            }, f, ensure_ascii=False, indent=2)

        print(f"[Persona] Updated: {persona_text[:80]}...")
        return {"status": "success", "persona": persona_text}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_persona() -> str:
    """Returns the current persona string, triggering a background refresh if stale."""
    if _is_stale():
        try:
            import threading
            threading.Thread(target=generate_persona, daemon=True).start()
        except Exception:
            pass

    if os.path.exists(PERSONA_FILE):
        try:
            with open(PERSONA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("persona", "")
        except Exception:
            return ""
    return ""
