import sys
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
            token = "{" + k + "}"
            if obj == token:
                return v
            elif token in obj:
                obj = obj.replace(token, str(v))
        return obj
    elif isinstance(obj, dict):
        return {k: _deep_replace(v, params_dict) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_deep_replace(v, params_dict) for v in obj]
    return obj

def execute(params: dict, context: dict) -> dict:
    steps_str = r"""[{"tool_name": "plugin_generator", "params": {"action": "create", "tool_name": "fetch_web_content", "description": "Fetch raw web content from a URL via HTTP GET and return text or parsed JSON when possible.", "code": "import json\\nimport urllib.request\\nimport urllib.error\\n\\ndef execute(params: dict, context: dict) -> dict:\\n    url = params.get('url')\\n    timeout = int(params.get('timeout', 20))\\n    if not url:\\n        return {'status': 'error', 'message': 'Missing required parameter: url'}\\n    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})\\n    try:\\n        with urllib.request.urlopen(req, timeout=timeout) as resp:\\n            raw = resp.read()\\n            content_type = resp.headers.get('Content-Type', '')\\n            text = raw.decode('utf-8', errors='replace')\\n            result = {\\n                'status': 'success',\\n                'url': url,\\n                'http_status': getattr(resp, 'status', 200),\\n                'content_type': content_type,\\n                'text': text\\n            }\\n            try:\\n                result['json'] = json.loads(text)\\n            except Exception:\\n                pass\\n            return result\\n    except urllib.error.HTTPError as e:\\n        return {'status': 'error', 'message': f'HTTPError: {e.code} {e.reason}'}\\n    except Exception as e:\\n        return {'status': 'error', 'message': str(e)}\\n"}}, {"tool_name": "fetch_web_content", "params": {"url": "{url}"}}]"""
    steps = json.loads(steps_str)
    
    history = []
    
    try:
        for i, step in enumerate(steps):
            tool_name = step.get("tool_name")
            raw_params = step.get("params", {})
            
            injected_params = _deep_replace(raw_params, params)
            
            res = tool_writer.execute_tool(tool_name, injected_params, context)
            history.append({"step": i+1, "tool": tool_name, "result": res})
            
            if isinstance(res, dict) and res.get("status") == "error":
                return {"status": "error", "message": f"Macro failed at step {i+1} ({tool_name})", "history": history}
                
        return {"status": "success", "message": "Macro completed successfully", "results": history}
    except Exception as e:
        return {"status": "error", "message": f"Macro execution error: {str(e)}", "traceback": traceback.format_exc(), "history": history}
