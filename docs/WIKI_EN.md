# Frog AI - Technical Wiki (v3.0)

Welcome to the official technical documentation for Frog AI v3.0. This guide provides deep dives into the system architecture, plugin development, and external service integration via the Model Context Protocol (MCP).

---

## 1. System Architecture

Frog AI v3.0 is built on a **Modular Micro-Services** architecture, orchestrated via Docker.

### Core Components
- **`frog-brain` (Python/FastAPI)**: The cognitive engine. Handles task planning (ReAct), tool execution, and LLM orchestration.
- **`frog-memory` (ChromaDB)**: The vectorized long-term memory store. Manages project context, expert knowledge, and MCP discovery markets.
- **`frog-ui` (Nginx/Web)**: The "IDE-Style" frontend. Served as a static web app, it connect to the Brain via REST/SSE.

### The Sandbox Engine
Frog executes AI-generated code in a dedicated **Containerized Sandbox**.
- Tools are written as standalone modules with a `manifest.json` and `index.py`.
- Execution occurs in an isolated Python container to prevent host machine corruption.
- State is synchronized via shared volumes and specialized "Shift" logs.

---

## 2. Model Context Protocol (MCP)

Frog AI v3.0 is an **MCP-Native** agent. It treats external services as first-class citizens.

### MCP Discovery Market
The discovery engine (`mcp_discovery.py`) maintains a vectorized registry of community MCP servers. The AI can:
1. **Search** for tools based on task intent (e.g., "I need to read a SQLite database").
2. **Retrieve** connection metadata (Docker images, capabilities).
3. **Instantiate** a connection on-the-fly via the `mcp_registry` tool.

### Active Connections
Once connected, the AI maintains a persistent JSON-RPC link to the MCP server, allowing it to call external tools as if they were built-in.

---

## 3. Plugin Development (`tool_writer`)

While MCP is for external services, **Skills** (local plugins) are for specific, targeted logic within the project.

### Creating a Skill
A skill folder (in `plugins/` or `generated_tools/`) must contain:
1. `manifest.json`: Metadata and parameter schema.
2. `index.py`: The `execute()` function.

**Manifest Example:**
```json
{
  "id": "project_analyzer",
  "name": "Project Analyzer",
  "description": "Analyzes file structure and provides dependencies.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Absolute path to analyze." }
    },
    "required": ["path"]
  }
}
```

**Implementation Example:**
```python
def execute(params: dict, context: dict) -> dict:
    path = params.get("path")
    # Logic here...
    return {"status": "success", "result": f"Analysis of {path} completed."}
```

---

## 4. Operational Best Practices

### Guardian Mode
Always keep the **Guardian Mode** active. This layer audits every shell command and tool execution against a safety policy before it hits the sandbox.

### Project Memory Integration
Use the `project_memory` tool to "Teach" the AI about your specific workspace. This persists information across Docker restarts in the ChromaDB volume.

---
*End of Technical Wiki (En). For deployment, see [README.md](../README.md).*
