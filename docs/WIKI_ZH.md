# Frog AI - 官方技术维基 (v3.0)

欢迎查看 Frog AI v3.0 官方技术文档。本指南深入介绍了系统架构、插件开发以及通过模型上下文协议 (MCP) 进行的外部服务集成。

---

## 1. 系统架构

Frog AI v3.0 基于**模块化微服务**架构，通过 Docker 进行编排。

### 核心组件
- **`frog-brain` (Python/FastAPI)**：认知引擎。负责任务规划 (ReAct)、工具执行和 LLM 编排。
- **`frog-memory` (ChromaDB)**：向量化长期存储。管理项目上下文、专家知识和 MCP 发现市场。
- **`frog-ui` (Nginx/Web)**：IDEA 风格的前端界面。作为静态 Web 应用运行，通过 REST/SSE 连接到 Brain。

### 沙箱引擎 (Sandbox)
Frog 在专用的**容器化沙箱**中执行 AI 生成的代码。
- 工具以独立模块编写，包含 `manifest.json` 和 `index.py`。
- 执行发生在隔离的 Python 容器中，防止破坏主机系统。
- 状态通过共享卷和专门的“偏移量 (Shift)”日志进行同步。

---

## 2. 模型上下文协议 (MCP)

Frog AI v3.0 是一个 **MCP 原生**的智能体。它将外部服务视为“一等公民”。

### MCP 发现市场
发现引擎 (`mcp_discovery.py`) 维护着社区 MCP 服务的向量化注册表。AI 可以：
1. **搜索**：根据任务意图寻找工具（例如：“我需要读取 SQLite 数据库”）。
2. **检索**：获取连接元数据（Docker 镜像、能力）。
3. **实例化**：通过 `mcp_registry` 工具动态建立连接。

### 活跃连接 (Active Connections)
一旦连接，AI 就会维护一个指向 MCP 服务器的持久 JSON-RPC 链接，允许它像调用内置工具一样调用外部工具。

---

## 3. 插件开发规范 (`tool_writer`)

MCP 针对外部服务，而 **Skills**（本地插件）则针对项目内的特定逻辑。

### 创建技能
技能文件夹（位于 `plugins/` 或 `generated_tools/`）必须包含：
1. `manifest.json`：元数据和参数模式。
2. `index.py`：包含 `execute()` 函数。

**Manifest 示例：**
```json
{
  "id": "project_analyzer",
  "name": "项目分析器",
  "description": "分析文件结构并提供依赖。",
  "parameters": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "要分析的绝对路径。" }
    },
    "required": ["path"]
  }
}
```

**代码实现示例：**
```python
def execute(params: dict, context: dict) -> dict:
    path = params.get("path")
    # 业务逻辑...
    return {"status": "success", "result": f"Analysis of {path} completed."}
```

---

## 4. 最佳实践

### 守护者模式 (Guardian Mode)
务必保持 **Guardian Mode** 开启。该层会在 shell 命令和工具执行进入沙箱前，根据安全策略进行审核。

### 项目记忆集成
利用 `project_memory` 工具让 AI “学习”你的特定工作区。这能让信息在 Docker 重启后依然保留在 ChromaDB 卷中。

---
*End of Technical Wiki (Zh). 部署指南请查看 [README.md](../README.md)。*
