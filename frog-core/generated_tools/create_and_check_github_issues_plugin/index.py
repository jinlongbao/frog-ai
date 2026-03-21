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
    steps_str = r"""[{"tool_name": "plugin_generator", "params": {"action": "create", "tool_name": "github_manager", "description": "Fetch the latest 5 open GitHub issues for a public repository using the GitHub API. Accepts owner and repo parameters with defaults owner=jinlongbao and repo=frog-ai, and returns clear structured issue data including title, author, and body.", "code": "import json\\nimport urllib.request\\nimport urllib.parse\\nimport urllib.error\\n\\ndef execute(params: dict, context: dict) -> dict:\\n    owner = params.get('owner', 'jinlongbao')\\n    repo = params.get('repo', 'frog-ai')\\n    per_page = 5\\n    url = f'https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/issues?state=open&per_page={per_page}'\\n    headers = {\\n        'Accept': 'application/vnd.github+json',\\n        'User-Agent': 'github_manager_plugin/1.0'\\n    }\\n    req = urllib.request.Request(url, headers=headers, method='GET')\\n    try:\\n        with urllib.request.urlopen(req, timeout=20) as resp:\\n            raw = resp.read().decode('utf-8')\\n            data = json.loads(raw)\\n    except urllib.error.HTTPError as e:\\n        try:\\n            detail = e.read().decode('utf-8')\\n        except Exception:\\n            detail = str(e)\\n        return {\\n            'success': False,\\n            'error': f'HTTPError {e.code}: {detail}',\\n            'owner': owner,\\n            'repo': repo\\n        }\\n    except Exception as e:\\n        return {\\n            'success': False,\\n            'error': str(e),\\n            'owner': owner,\\n            'repo': repo\\n        }\\n\\n    issues = []\\n    for item in data:\\n        if 'pull_request' in item:\\n            continue\\n        issues.append({\\n            'title': item.get('title', ''),\\n            'author': (item.get('user') or {}).get('login', ''),\\n            'body': item.get('body', ''),\\n            'number': item.get('number'),\\n            'url': item.get('html_url', '')\\n        })\\n        if len(issues) >= 5:\\n            break\\n\\n    return {\\n        'success': True,\\n        'owner': owner,\\n        'repo': repo,\\n        'count': len(issues),\\n        'issues': issues\\n    }\\n"}}, {"tool_name": "github_manager", "params": {"owner": "{owner}", "repo": "{repo}"}}]"""
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
