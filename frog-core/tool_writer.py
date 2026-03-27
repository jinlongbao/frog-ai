import os
import sys
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List
import traceback
import subprocess
import tempfile
import importlib.util

# Use generated_tools instead of dynamic_tools for consistency
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_TOOLS_DIR = os.path.join(BASE_DIR, "generated_tools")
PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")

if not os.path.exists(GENERATED_TOOLS_DIR):
    os.makedirs(GENERATED_TOOLS_DIR)

class ToolWriter:
    def __init__(self, docker_manager=None):
        self.docker_manager = docker_manager

    def _get_tool_path(self, tool_name: str) -> str:
        return os.path.join(GENERATED_TOOLS_DIR, tool_name)

    def list_tools(self) -> Dict[str, Any]:
        """List all tools from both plugins/ and generated_tools/"""
        tools = []
        
        # Scan built-in plugins
        if os.path.exists(PLUGINS_DIR):
            for item in os.listdir(PLUGINS_DIR):
                item_path = os.path.join(PLUGINS_DIR, item)
                if os.path.isdir(item_path):
                    manifest_path = os.path.join(item_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, "r", encoding="utf-8") as f:
                                manifest = json.load(f)
                                tools.append({
                                    "id": manifest.get("id", item),
                                    "name": manifest.get("name", item),
                                    "description": manifest.get("description", ""),
                                    "parameters": manifest.get("parameters", {}),
                                    "source": "builtin"
                                })
                        except Exception:
                            continue

        # Scan generated tools
        if os.path.exists(GENERATED_TOOLS_DIR):
            for item in os.listdir(GENERATED_TOOLS_DIR):
                item_path = os.path.join(GENERATED_TOOLS_DIR, item)
                if os.path.isdir(item_path):
                    manifest_path = os.path.join(item_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, "r", encoding="utf-8") as f:
                                manifest = json.load(f)
                                tools.append({
                                    "id": manifest.get("id", item),
                                    "name": manifest.get("name", item),
                                    "description": manifest.get("description", ""),
                                    "parameters": manifest.get("parameters", {}),
                                    "source": "generated"
                                })
                        except Exception:
                            continue
        
        return {
            "status": "success",
            "count": len(tools),
            "tools": tools
        }

    def write_tool(self, tool_name: str, description: str, code: str, parameters: Optional[Dict] = None, test_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Write a new tool using folder-based structure: generated_tools/{tool_name}/[index.py, manifest.json]
        """
        # Ensure tool_name is safe for filesystem
        safe_name = tool_name.lower().replace(" ", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in ("_", "-"))
        tool_path = self._get_tool_path(safe_name)
        
        if not os.path.exists(tool_path):
            os.makedirs(tool_path)
            
        # 1. Create manifest.json
        manifest = {
            "id": safe_name,
            "name": tool_name,
            "version": "1.0.0",
            "description": description,
            "entry_point": "index.py",
            "parameters": parameters or {
                "type": "object",
                "properties": {
                    "params": {"type": "object", "description": "Parameters for the tool"}
                },
                "required": []
            },
            "created_at": datetime.now().isoformat()
        }
        
        with open(os.path.join(tool_path, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            
        # 2. Create index.py
        with open(os.path.join(tool_path, "index.py"), "w", encoding="utf-8") as f:
            f.write(code)
            
        # 3. Create tests/test_index.py (Phase 33: TDD)
        test_dir = os.path.join(tool_path, "tests")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "test_index.py"), "w", encoding="utf-8") as f:
            if test_code:
                f.write(test_code)
            else:
                # Fallback minimal template
                f.write(f"import pytest\nimport index\n\ndef test_basic():\n    # Basic sanity check\n    assert hasattr(index, 'execute')\n")
            
        return {
            "status": "success",
            "tool_id": safe_name,
            "tool_name": tool_name,
            "path": tool_path,
            "message": f"Tool '{tool_name}' created successfully in {tool_path}"
        }

    def execute_tool(self, tool_id: str, params: Dict, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a tool. Uses Docker sandbox if available, else falls back to subprocess."""
        if self.docker_manager:
            return self.execute_in_sandbox(tool_id, params, context)
        return self.execute_isolated(tool_id, params, context)

    def execute_in_sandbox(self, tool_id: str, params: Dict, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Runs the tool inside an isolated Docker container."""
        # Check tool exists
        tool_path = os.path.join(GENERATED_TOOLS_DIR, tool_id)
        if not os.path.exists(tool_path):
            tool_path = os.path.join(PLUGINS_DIR, tool_id)
            if not os.path.exists(tool_path):
                return {"status": "error", "message": f"Tool '{tool_id}' not found"}

        try:
            # Transfer tool files to temp dir for Docker mount
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy index.py and manifest.json
                for item in ["index.py", "manifest.json"]:
                    src = os.path.join(tool_path, item)
                    if os.path.exists(src):
                        shutil.copy(src, temp_dir)
                
                # Serialized params/context
                with open(os.path.join(temp_dir, "params.json"), "w", encoding="utf-8") as f:
                    json.dump(params, f)
                with open(os.path.join(temp_dir, "context.json"), "w", encoding="utf-8") as f:
                    json.dump(context or {}, f)
                
                # Run in container via DockerManager
                result = self.docker_manager.run_tool_container(
                    image="python:3.11-slim",
                    command=["python", "index.py"], # This assumes index.py reads params.json
                    volumes={temp_dir: {"bind": "/app", "mode": "rw"}}
                )
                return result
        except Exception as e:
             return {"status": "error", "message": f"Docker sandbox execution failed: {str(e)}"}

    def verify_tool(self, tool_id: str) -> Dict[str, Any]:
        """Runs pytest on the tool's test suite inside the sandbox."""
        if not self.docker_manager:
            return {"status": "error", "message": "Docker Manager not initialized. Cannot verify tool."}

        tool_path = self._get_tool_path(tool_id)
        if not os.path.exists(tool_path):
             return {"status": "error", "message": f"Tool '{tool_id}' not found"}

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy everything to temp dir (including tests/)
                import shutil
                shutil.copytree(tool_path, os.path.join(temp_dir, "app"), dirs_exist_ok=True)
                
                # Run pytest in container
                result = self.docker_manager.run_tool_container(
                    image="python:3.11-slim",
                    command=["sh", "-c", "pip install pytest && pytest /app/tests"],
                    volumes={temp_dir: {"bind": "/app", "mode": "rw"}}
                )
                
                if result.get("status") == "success":
                    return {"status": "success", "message": "All tests passed.", "output": result.get("output")}
                else:
                    return {"status": "error", "message": "Tests failed.", "output": result.get("output")}
        except Exception as e:
            return {"status": "error", "message": f"Verification failed: {str(e)}"}

    def execute_isolated(self, tool_id: str, params: Dict, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Legacy subprocess execution (fallback)"""
        # Check in generated_tools
        tool_path = os.path.join(GENERATED_TOOLS_DIR, tool_id)
        if not os.path.exists(tool_path):
            # Also check in plugins for uniformity (if needed by main.py)
            tool_path = os.path.join(PLUGINS_DIR, tool_id)
            if not os.path.exists(tool_path):
                return {"status": "error", "message": f"Tool '{tool_id}' not found"}

        index_path = os.path.join(tool_path, "index.py")
        if not os.path.exists(index_path):
            return {"status": "error", "message": f"Entry point index.py not found for tool '{tool_id}'"}

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                params_file = os.path.join(temp_dir, "params.json")
                context_file = os.path.join(temp_dir, "context.json")
                out_file = os.path.join(temp_dir, "out.json")
                
                with open(params_file, "w", encoding="utf-8") as f:
                    json.dump(params, f, ensure_ascii=False)
                with open(context_file, "w", encoding="utf-8") as f:
                    json.dump(context or {}, f, ensure_ascii=False)
                    
                runner_code = f"""
import sys
import json
import traceback

sys.path.insert(0, r"{os.path.dirname(index_path)}")

try:
    import index
    
    with open(r"{params_file}", "r", encoding="utf-8") as f:
        params_dict = json.load(f)
    with open(r"{context_file}", "r", encoding="utf-8") as f:
        context_dict = json.load(f)
        
    result = index.execute(params_dict, context_dict)
    
    with open(r"{out_file}", "w", encoding="utf-8") as f:
        json.dump({{"status": "success", "tool_id": "{tool_id}", "result": result}}, f, ensure_ascii=False)
except Exception as e:
    with open(r"{out_file}", "w", encoding="utf-8") as f:
        json.dump({{"status": "error", "tool_id": "{tool_id}", "message": str(e), "traceback": traceback.format_exc()}}, f, ensure_ascii=False)
"""
                runner_file = os.path.join(temp_dir, "runner.py")
                with open(runner_file, "w", encoding="utf-8") as f:
                    f.write(runner_code)
                    
                # Execute isolated
                out_txt = os.path.join(temp_dir, "stdout.txt")
                err_txt = os.path.join(temp_dir, "stderr.txt")
                try:
                    with open(out_txt, "w", encoding="utf-8") as f_out, open(err_txt, "w", encoding="utf-8") as f_err:
                        proc = subprocess.run(
                            [sys.executable, runner_file],
                            cwd=os.path.dirname(index_path),
                            timeout=30,
                            stdout=f_out,
                            stderr=f_err,
                            text=True
                        )
                    
                    if os.path.exists(out_file):
                        with open(out_file, "r", encoding="utf-8") as f:
                            return json.load(f)
                    else:
                        stdout_str, stderr_str = "", ""
                        try:
                            with open(out_txt, "r", encoding="utf-8") as f: stdout_str = f.read()
                            with open(err_txt, "r", encoding="utf-8") as f: stderr_str = f.read()
                        except: pass
                        return {
                            "status": "error", 
                            "message": "Plugin execution crashed silently without generating output JSON.",
                            "stdout": stdout_str,
                            "stderr": stderr_str
                        }
                        
                except subprocess.TimeoutExpired:
                    return {"status": "error", "message": f"Plugin execution timed out after 30 seconds limit."}
                
        except Exception as e:
            return {
                "status": "error",
                "tool_id": tool_id,
                "message": f"Sandbox error: {str(e)}",
                "traceback": traceback.format_exc()
            }

    def fix_tool(self, tool_id: str, error_message: str, new_code: str) -> Dict[str, Any]:
        """Update the index.py of an existing tool"""
        tool_path = self._get_tool_path(tool_id)
        if not os.path.exists(tool_path):
            return {"status": "error", "message": f"Tool '{tool_id}' not found"}

        index_path = os.path.join(tool_path, "index.py")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_code)
            
        return {
            "status": "success",
            "tool_id": tool_id,
            "message": f"Tool '{tool_id}' fixed and updated"
        }

    def delete_tool(self, tool_id: str) -> Dict[str, Any]:
        """Delete a tool folder from generated_tools/"""
        tool_path = self._get_tool_path(tool_id)
        if os.path.exists(tool_path):
            shutil.rmtree(tool_path)
            return {"status": "success", "message": f"Tool '{tool_id}' deleted successfully"}
        return {"status": "error", "message": f"Tool '{tool_id}' not found"}

tool_writer = ToolWriter()
