import json
import uuid
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from tool_writer import tool_writer

class TaskStatus(Enum):
    PENDING = "pending"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING_FOR_HUMAN = "waiting_for_human"
    COMPLETED = "completed"
    FAILED = "failed"

class Task:
    def __init__(self, task_id: str, messages: List[Dict], config: Dict):
        self.task_id = task_id
        self.messages = messages.copy()
        self.config = config
        self.status = TaskStatus.PENDING
        self.steps: List[Dict] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.final_result: Optional[str] = None
        self.error: Optional[str] = None
        self.human_input_pending: Optional[str] = None
        self.human_input_type: Optional[str] = None

    def to_dict(self) -> Dict:
        status_map = {
            TaskStatus.PENDING: "PENDING",
            TaskStatus.THINKING: "THINKING",
            TaskStatus.ACTING: "ACTING",
            TaskStatus.WAITING_FOR_HUMAN: "WAITING_HUMAN_INPUT",
            TaskStatus.COMPLETED: "COMPLETED",
            TaskStatus.FAILED: "FAILED"
        }
        
        return {
            "task_id": self.task_id,
            "status": status_map.get(self.status, self.status.value),
            "messages": self.messages,
            "config": self.config,
            "steps": self.steps,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "final_answer": self.final_result,
            "final_result": self.final_result,
            "error": self.error,
            "human_input_pending": self.human_input_pending,
            "human_input_type": self.human_input_type,
            "human_input_prompt": self.human_input_pending
        }

class Orchestrator:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.max_steps = 10
        
    def create_task(self, messages: List[Dict], config: Dict) -> str:
        task_id = str(uuid.uuid4())
        task = Task(task_id, messages, config)
        self.tasks[task_id] = task
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def resume_task_with_human_input(self, task_id: str, user_input: str) -> bool:
        task = self.get_task(task_id)
        if not task or task.status != TaskStatus.WAITING_FOR_HUMAN:
            return False
        
        task.messages.append({
            "role": "user",
            "content": f"[Human Input] {user_input}"
        })
        
        task.human_input_pending = None
        task.human_input_type = None
        task.status = TaskStatus.PENDING
        task.updated_at = datetime.now().isoformat()
        
        return True
    
    def _get_dynamic_tools_text(self) -> str:
        """Fetch and format all available tools from tool_writer"""
        try:
            result = tool_writer.list_tools()
            if result.get("status") != "success":
                return "No additional tools found."
            
            tools_list = result.get("tools", [])
            if not tools_list:
                return "No additional tools found."
            
            lines = []
            for i, tool in enumerate(tools_list, 1):
                tool_id = tool.get("id")
                desc = tool.get("description", "No description")
                params = json.dumps(tool.get("parameters", {}), ensure_ascii=False)
                source = tool.get("source", "unknown")
                
                # We skip Meta-Tools and base tools that are already hardcoded below
                if tool_id in ("execute_tool", "list_tools", "request_human_input",
                               "search_browser", "knowledge_manager"):
                    continue
                    
                lines.append(f"- {tool_id} (Source: {source}): {desc}")
                lines.append(f"  Input Schema: {params}")
            
            return "\n".join(lines) if lines else "No custom tools found."
        except Exception as e:
            return f"Error loading dynamic tools: {str(e)}"

    def build_react_prompt(self, task: Task) -> str:
        dynamic_tools = self._get_dynamic_tools_text()
        
        persona = ""
        try:
            from persona_manager import get_persona
            persona = get_persona()
        except Exception:
            pass
            
        persona_clause = f"\n### ADOPTED PERSONA:\n{persona}\n" if persona else ""
        
        macro_suggestion_clause = ""
        if len([s for s in task.steps if s.get("parsed", {}).get("type") == "action"]) >= 2:
            # Get the distinct tools used so far
            tools_used = list(set(
                s.get("parsed", {}).get("action", "")
                for s in task.steps
                if s.get("parsed", {}).get("type") == "action"
                and s.get("parsed", {}).get("action", "") not in (
                    "none", "list_tools", "request_human_input"
                )
            ))
            if len(tools_used) >= 2:
                macro_suggestion_clause = f"""
### 🎯 MACRO SKILL OPPORTUNITY DETECTED:
You have used {len(tools_used)} distinct tools in this task: {', '.join(tools_used)}.
BEFORE writing 'Final Answer:', you MUST call `macro_maker` to compile these steps into a reusable Macro Skill plugin.
This is MANDATORY for all multi-step workflows. Name the macro descriptively (e.g., 'web_summarize_and_save').
"""
        
        system_prompt = f"""You are an AUTONOMOUS AGENT. You solve complex tasks by thinking step-by-step and executing tools.{persona_clause}{macro_suggestion_clause}

### ❌ CRITICAL: NO CONVERSATIONAL DRIFT
- DO NOT say "I will create this tool for you" or "Here is your tool".
- DO NOT explain code in the chat.
- YOUR ENTIRE RESPONSE MUST follow the ReAct format below.
- IF YOU TALK IN NATURAL LANGUAGE INSTEAD OF USING AN ACTION BLOCK, YOU FAIL THE MISSION.
- DO NOT say "I will create this tool for you" or "I am working on it" in natural language. USE AN ACTION.
- NEVER claim you have completed a task (e.g., "File created") unless you have received an 'Observation' from a tool that confirms it.
- IF YOU PROVIDE A FINAL ANSWER WITHOUT HAVING ACCESSED THE SYSTEM VIA A TOOL TO ACTUALLY DO IT, YOU ARE HALLUCINATING AND FAILING.
- **CRITICAL**: NEVER use the 'Final Answer:' keyword if you are also using an 'Action:'. Choose one. If a tool call is needed, ONLY use 'Action:'.

### MANDATORY FORMATTING RULES (必须遵守的格式规则):
1. Every response MUST start with "Thought:".
2. To act (create/run/fix tools), you MUST use ONLY the "Action:" and "Action Input:" lines.
3. Structural keywords MUST be in English: Thought, Action, Action Input, Final Answer.

### EXECUTION LOOP (执行循环):
Thought: <Step-by-step reasoning about the next physical action>
Action: <Tool Name to call>
Action Input: {{ "key": "value" }}
(Observation: The real-world result of your action)

Final Answer: <Your final response ONLY after the task is finished>

### EXAMPLE: TOOL CREATION (示例：创建工具)
User: Create a tool to convert USD to CNY.
Thought: I need to create a tool using plugin_generator. I will define the action, name, description, and python code.
Action: plugin_generator
Action Input: {{ "action": "create", "tool_name": "usd_to_cny", "description": "Convert rate...", "code": "def execute(params, context): ..." }}

### CORE CAPABILITIES (META-TOOLS):
1. execute_tool: Run dynamic tools.
2. list_tools: View all current capabilities.
3. request_human_input: Ask human for help/confirmation when truly stuck.
4. search_browser: Web search for real-time info.
5. knowledge_manager: Permanent knowledge storage (save/retrieve).
6. context_compressor: **CALL THIS at step 8+ to compress old steps and prevent context overflow.**
7. notify_user: Send a desktop notification to alert the user (title, message). Use after completing long background tasks.
8. task_scheduler: Schedule a prompt to run later (delay_seconds, repeat_interval_seconds). Use for recurring or deferred tasks.
9. multi_agent: Spawn 2-8 parallel sub-agents each with their own prompt (tasks: [{{ "label": "name", "prompt": "instruction" }}]). Use for parallel research or multi-workstream tasks.
10. goal_tracker: Manage long-term goals across sessions (actions: add, list, update_progress, complete, delete). Review active goals at the start of complex tasks.

### CUSTOM CAPABILITIES (DYNAMIC):
{dynamic_tools}

### AUTONOMY GUIDELINES:
- 🛠️ PRIORITY RULE (MANDATORY): You MUST ALWAYS use EXISTING built-in tools (like `send_telegram_file` for Telegram tasks, or `fs_expert` for files) first. Do NOT use `plugin_generator` or `macro_maker` to create NEW tools if an existing tool or a combination of them can achieve the goal. Redundant tool creation is a CRITICAL mission failure.
- BE PROACTIVE: ONLY if a built-in tool is genuinely broken or completely missing, fix or create it.
- CONTEXT MANAGEMENT: If you are on step 8 or more, ALWAYS call `context_compressor` before continuing.
- MISSION MEMORY: When you successfully complete a multi-step task that may be repeated, ALWAYS use `macro_maker` to compile your steps into a reusable macro before outputting the Final Answer.
- USER NOTIFICATION: After completing any long-running or background task, call `notify_user` so the user knows it's done.
- CROSS-PLATFORM: When writing plugins or commands, NEVER hardcode Windows paths (use os.path/pathlib). For shell, detect platform.system() instead of assuming cmd/PowerShell or bash.
- NO CONVERSATIONAL DRIFT: Do not just say what you will do. DO IT using an Action block.
- NEVER GIVE UP: If a tool fails (e.g., rate limiting), find a workaround or use `request_human_input` for ONLY that specific missing piece. DO NOT stop the entire task.
"""
        return system_prompt

    def parse_llm_response(self, response: str) -> Dict:
        thought = ""
        action = ""
        action_input = {}
        
        # 1. Action Check (Highest Priority) - If AI wants to do something, we MUST loop.
        if "Action:" in response:
            if "Thought:" in response:
                thought_parts = response.split("Thought:")
                if len(thought_parts) > 1:
                    thought = thought_parts[1].split("Action:")[0].strip()
            
            action_parts = response.split("Action:")
            if len(action_parts) > 1:
                action_content = action_parts[1].split("Action Input:")[0].strip()
                action = action_content
            
            if "Action Input:" in response:
                input_parts = response.split("Action Input:")
                if len(input_parts) > 1:
                    input_str = input_parts[1].strip()
                    # Remove possible Final Answer suffix if AI added it erroneously
                    if "Final Answer:" in input_str:
                        input_str = input_str.split("Final Answer:")[0].strip()
                    
                    # Remove markdown fences
                    if input_str.startswith("```"):
                        lines = input_str.splitlines()
                        if len(lines) > 1 and lines[0].startswith("```"):
                            # Skip the first line (fence) and last line (fence)
                            input_str = "\n".join(lines[1:])
                            if "```" in input_str:
                                input_str = input_str.split("```")[0].strip()
                    
                    try:
                        action_input = json.loads(input_str)
                    except Exception:
                        # Try to extract JSON with regex if raw split fails
                        import re
                        match = re.search(r"\{.*\}", input_str, re.DOTALL)
                        if match:
                            try:
                                action_input = json.loads(match.group())
                            except: pass

            return {
                "type": "action",
                "thought": thought,
                "action": action,
                "action_input": action_input
            }

        # 2. Final Answer Check
        if "Final Answer:" in response:
            parts = response.split("Final Answer:", 1)
            return {
                "type": "final_answer",
                "content": parts[1].strip()
            }
        
        # 3. Fallback (If no action/final answer found, treat as partial thought or failed compliance)
        if "Thought:" in response:
            thought = response.split("Thought:")[1].strip()
            return {
                "type": "action", # Still return as action to force loop if not complete
                "thought": thought,
                "action": "none",
                "action_input": {}
            }
            
        return {
            "type": "final_answer",
            "content": response.strip()
        }
    
    def execute_step(self, task: Task, llm_response: str) -> Dict:
        parsed = self.parse_llm_response(llm_response)
        
        step = {
            "step_number": len(task.steps) + 1,
            "timestamp": datetime.now().isoformat(),
            "llm_response": llm_response,
            "parsed": parsed
        }
        
        if parsed["type"] == "final_answer":
            task.status = TaskStatus.COMPLETED
            task.final_result = parsed["content"]
            step["result"] = "Task completed"
            
            # Log AI final answer for persona inference
            try:
                from persona_manager import append_conversation_turn
                append_conversation_turn("assistant", parsed["content"][:500])
            except Exception:
                pass

            # Fire post-task intelligence hooks (self-eval, knowledge enrichment, quality scoring)
            try:
                from post_task_hooks import run_post_task_hooks
                run_post_task_hooks(task, task.config)
            except Exception:
                pass
                
            # Fire webhook if configured
            webhook_url = task.config.get("webhook_url")
            if webhook_url:
                try:
                    import threading
                    import httpx
                    def send_webhook():
                        try:
                            with httpx.Client(timeout=10) as client:
                                payload = {
                                    "task_id": task.task_id,
                                    "status": task.status.value,
                                    "result": task.final_result
                                }
                                client.post(webhook_url, json=payload)
                        except Exception as e:
                            print(f"[Webhook Failed] {e}")
                    threading.Thread(target=send_webhook, daemon=True).start()
                except Exception as e:
                    print(f"[Webhook Error] {e}")
                
                
        elif parsed.get("action") == "request_human_input":
            task.status = TaskStatus.WAITING_FOR_HUMAN
            task.human_input_pending = parsed["action_input"].get("message", "") or parsed["action_input"].get("prompt", "")
            task.human_input_type = parsed["action_input"].get("input_type", "text")
            step["result"] = "Waiting for human input"
        else:
            step["result"] = "Action to be executed"
        
        task.steps.append(step)
        task.updated_at = datetime.now().isoformat()
        
        return parsed

orchestrator = Orchestrator()
