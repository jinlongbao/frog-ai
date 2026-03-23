# Frog AI - Official Wiki

Welcome to the Frog AI official documentation! Frog AI is a deeply autonomous, cross-platform personal AI agent. It acts as a **desktop-native expert** that doesn't just answer questions, but actively **plans, executes, remembers, and self-evolves**.

---

## 📖 Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Plugin System (`tool_writer`)](#2-plugin-system)
3. [Built-in Capabilities](#3-built-in-capabilities)
4. [Remote Control & Integration](#4-remote-control--integration)

---

## 1. Architecture Overview
Frog AI relies on a high-speed decoupled architecture consisting of a Python FastAPI backend (`frog-core`) and an Electron frontend (`frog-shell`).

### Pipeless Subprocess Sandbox
To execute dynamic AI-generated code without corrupting the host machine or freezing the UI, Frog AI uses a sandboxed subprocess engine. 
- Python plugins execute in absolute isolation.
- `stdout.txt` acts as an asynchronous disk-drop messaging queue.
- Hard 30-second thermal timeouts prevent ghost-process deadlocks.

---

## 2. Plugin System
Frog AI natively supports hot-swapping functionality. If the AI detects it lacks a tool, it can self-author one into the `generated_tools/` directory.

### Anatomy of a Plugin
A standard plugin requires exactly two files:
* `manifest.json`: Tells the LLM what the tool is and its parameters.
* `index.py`: The isolated logic.

**Manifest Specification (JSON Schema):**
```json
{
  "id": "my_tool",
  "name": "My Custom Tool",
  "description": "Does something amazing.",
  "version": "1.0.0",
  "entry": "index.py",
  "parameters": {
    "type": "object",
    "properties": {
      "target": { "type": "string", "description": "The processing target." }
    },
    "required": ["target"]
  }
}
```

**Index.py Specification:**
```python
def execute(params: dict, context: dict) -> dict:
    target = params.get("target")
    return {"status": "success", "result": f"Target locked: {target}"}
```

---

## 3. Built-in Capabilities

Frog AI ships with a suite of "expert" level core macros:
- **`fs_expert`**: Safely searches directories, reads files, and moves outputs across OS boundaries.
- **`shell_executor`**: Safely runs bash/powershell commands asynchronously on the host machine.
- **`document_generator`**: Bypasses string building to output rich `.docx` and `.pptx` presentations directly to the desktop.
- **`gui_expert`**: Automates keystrokes, mouse clicks, and bypasses regional clipboard barriers.
- **`eyes_expert`**: Captures screen states natively, turning the local computer into a multi-modal desktop canvas for the AI.

---

## 4. Remote Control & Integration

### Telegram Integration
Frog AI natively connects to the Telegram Bot API structure to serve as your mobile command station.
* Any text message sent to your authorized Bot triggers a background `ReAct` chain locally on your PC.
* **`send_telegram_file`**: If you ask Frog to fetch a desktop file, it locates it natively via `fs_expert` and blasts it back to your phone over the Telegram Bot API.

### WeChat / Messaging Integration
Using standard webhook APIs and the generic `messenger_bot` architecture, Frog can be integrated into enterprise notification chains.

---
*End of Wiki. For deployment instructions, refer to `README.md`.*
