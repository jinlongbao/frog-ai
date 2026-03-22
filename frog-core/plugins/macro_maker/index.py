import sys
import os
import traceback
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from tool_writer import tool_writer

def execute(params: dict, context: dict) -> dict:
    """
    Macro compilation.
    """
    macro_name = params.get("macro_name", "")
    description = params.get("description", f"Macro Skill: {macro_name}")
    parameters_schema = params.get("macro_parameters", {"type": "object", "properties": {}})
    steps = params.get("steps", [])
    
    if not macro_name or not steps:
        return {"status": "error", "message": "Missing macro_name or steps"}
    
    steps_json = json.dumps(steps, ensure_ascii=False).replace('\\', '\\\\')
    
    # Generate the python file string
    code = f'''import sys
import os
import traceback
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from tool_writer import tool_writer

def _deep_replace(obj, params_dict):
    if isinstance(obj, str):
        for k, v in params_dict.items():
            token = "{{" + k + "}}"
            if obj == token:
                return v
            elif token in obj:
                obj = obj.replace(token, str(v))
        return obj
    elif isinstance(obj, dict):
        return {{k: _deep_replace(v, params_dict) for k, v in obj.items()}}
    elif isinstance(obj, list):
        return [_deep_replace(v, params_dict) for v in obj]
    return obj

def execute(params: dict, context: dict) -> dict:
    steps_str = r"""{steps_json}"""
    steps = json.loads(steps_str)
    
    history = []
    
    try:
        for i, step in enumerate(steps):
            tool_name = step.get("tool_name")
            raw_params = step.get("params", {{}})
            
            injected_params = _deep_replace(raw_params, params)
            
            res = tool_writer.execute_tool(tool_name, injected_params, context)
            history.append({{"step": i+1, "tool": tool_name, "result": res}})
            
            if isinstance(res, dict) and res.get("status") == "error":
                return {{"status": "error", "message": f"Macro failed at step {{i+1}} ({{tool_name}})", "history": history}}
                
        return {{"status": "success", "message": "Macro completed successfully", "results": history}}
    except Exception as e:
        return {{"status": "error", "message": f"Macro execution error: {{str(e)}}", "traceback": traceback.format_exc(), "history": history}}
'''

    try:
        result = tool_writer.write_tool(
            tool_name=macro_name,
            description=description,
            code=code,
            parameters=parameters_schema
        )
        result["installed"] = True
        result["message"] = f"Successfully compiled and saved Macro Skill: {macro_name}"
        return result
    except Exception as e:
        return {"status": "error", "message": f"Macro Generator failed: {str(e)}", "traceback": traceback.format_exc()}
