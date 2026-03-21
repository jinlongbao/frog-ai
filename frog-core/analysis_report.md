# [REPORT] Frog Brain (main.py) Architectural Improvements

## Current Status Analysis
`main.py` has grown into a "God Object" (887 lines), encompassing:
- Configuration & Environment management.
- Data Models (Pydantic).
- Infrastructure (CORS, Middlewares).
- Business Logic (Agent learning, Knowledge retrieval).
- Orchestration (ReAct loops, Prompt construction).
- Provider Bridges (OpenAI, Gemini).
- Local Tool implementations.

## Proposed Improvements (FastAPI Best Practices)

### 1. Module Decoupling (The Router Pattern)
**Issue**: All endpoints are in one file.
**Fix**: Use `APIRouter` to split functionality.
- `routers/tasks.py`: Orchestration endpoints.
- `routers/knowledge.py`: Ingestion & Retrieval.
- `routers/tools.py`: Tool registry & execution.

### 2. Dependency Injection (DI)
**Issue**: Global `tool_writer` and `orchestrator` instances.
**Fix**: Use `Annotated[ToolWriter, Depends(get_tool_writer)]`. This allows easier mocking during unit tests.

### 3. Service Layer Extraction
**Issue**: Complex logic like `chat_with_llm` and `execute_task_step` resides directly in route handlers.
**Fix**: Create a `services/` directory to handle the AI logic, keeping route handlers clean and focused only on HTTP semantics.

### 4. Custom Middleware for Traceability
**Issue**: Error handling is reactive (try/except).
**Fix**: Use an `ExceptionMiddleware` to capture all internal errors and format them into a standardized "Frog Protocol" JSON response.

---

## Autonomous Tool: Code Quality Scanner
I will now create the `code_quality_scanner` tool to automate this process.
