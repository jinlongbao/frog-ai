<div align="center">
  <img src="./assets/logo.png" width="250" alt="Frog AI Logo">
  
  <br/>
  
  ![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white)
  ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
  ![Electron](https://img.shields.io/badge/Electron-47848F?style=flat-square&logo=electron&logoColor=white)
  ![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Storage-FF6B6B?style=flat-square)
  ![LLM Based](https://img.shields.io/badge/LLM-OpenAI_/_Gemini-412991?style=flat-square)
</div>

# Frog AI - Highly Autonomous Personal AI Agent

Frog AI is a deeply autonomous, cross-platform personal AI agent. It acts as a desktop-native expert that doesn't just answer questions, but actively **plans, executes, remembers, and self-heals**. 

Built with a modern Electron frontend and a powerful Python FastApi backend, Frog gives AI the power to read your local files, execute shell commands in a sandbox, schedule background tasks, manage long-term goals, and even write its own plugins autonomously.

---

## 🚀 Core Features

- **True Autonomy (ReAct Engine):** Frog writes its own steps, evaluates tool outputs, and automatically retries with corrected logic if a tool fails (Self-Healing).
- **Proactive Intelligence:** Features a background curiosity loop, daily persona generation based on chat history, and long-term generic goal tracking.
- **Multi-Agent Spawning:** Can dispatch multiple parallel sub-agents to research or analyze things concurrently.
- **Dynamic Plugin System:** Adding new skills is as easy as putting a `.py` and `.json` in the `plugins/` directory. Frog can even write new plugins for itself dynamically using the `plugin_generator`.
- **System-level Integration:** Native Windows/macOS/Linux toast notifications (`notify_user`) and shell execution (`shell_executor`) built-in.
- **Persistent Knowledge:** Built-in RAG via ChromaDB. Automatically reads, tags, and categorizes local documents.

---

## 🛠️ Environment Requirements

- **OS:** Windows 10/11, macOS, Linux (Cross-platform)
- **Node.js:** v18.0 or higher
- **Python:** v3.10 or higher
- **LLM Account:** Any OpenAI-compatible API key (OpenAI, Anthropic, DeepSeek, local LM Studio, etc.) or Google Gemini API.

---

## 🏃 Build & Run

### 1. Initialize Python Backend
Navigate to `frog-core` and install dependencies:
```bash
cd frog-core
pip install -r requirements.txt
```

Set your environment variables. Create a `.env` in `frog-core/` or `frog-shell/`:
```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-4o
```

### 2. Initialize Node.js Frontend
Navigate to `frog-shell` and install npm modules:
```bash
cd ../frog-shell
npm install
```

### 3. Start the Application
You can start both the backend and frontend simultaneously using the provided startup script in the root directory:
```bash
python start_frog.py
```
*(Alternatively, you can manually run `uvicorn main:app` in frog-core and `npm start` in frog-shell).*

---

## 🔌 API Documentation (Core REST API)

Frog exposes its agent logic via a standard REST API, allowing you to integrate it into external applications (like Discord bots or CI/CD pipelines).

### `POST /task/create`
Creates a new autonomous task.
**Payload:**
```json
{
  "messages": [{"role": "user", "content": "Analyze my codebase and generate a report."}],
  "model": "gpt-4o",
  "webhook_url": "https://your-server.com/frog-webhook-callback" (Optional)
}
```
**Response:** Returns a `task_id`.

### Webhook Callbacks
If `webhook_url` is provided, Frog will run asynchronously and POST to your URL when the task is `COMPLETED` or `FAILED`:
```json
{
  "task_id": "c8f2-...",
  "status": "completed",
  "result": "The analysis is complete. Here are the findings: ..."
}
```

---

## 🧩 External Plugin Specification

Plugins allow Frog to interact with the real world. Frog dynamically loads all plugins from `frog-core/plugins/`.

A plugin requires exactly 2 files:
1. `manifest.json` (Describes the tool to the LLM)
2. `index.py` (The actual execution logic)

### `manifest.json` Example
```json
{
  "id": "my_custom_tool",
  "name": "My Custom Tool",
  "description": "Does something amazing.",
  "version": "1.0.0",
  "entry": "index.py",
  "parameters": {
    "type": "object",
    "properties": {
      "target": { "type": "string", "description": "The target to process." }
    },
    "required": ["target"]
  }
}
```

### `index.py` Example
*Code must be cross-platform (use `os.path` and `platform.system()`).*
```python
def execute(params: dict, context: dict) -> dict:
    target = params.get("target")
    try:
        # Do work...
        return {"status": "success", "result": f"Processed {target}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

---

## 🏭 Industry Templates
Frog ships with sample JSON templates in `templates/` (e.g., `coder.json`, `researcher.json`). 
You can load these to instantly reconfigure Frog's persona, initial goals, and default allowed plugins for specific specialized jobs!
