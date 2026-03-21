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
    steps_str = r"""[{"tool_name": "plugin_generator", "params": {"action": "create", "tool_name": "duckduckgo_promoter_search", "description": "Search DuckDuckGo for relevant external discussions or technical blog posts about AI agents/open source personal AI, and return structured results with title, URL, and summary.", "code": "def execute(params: dict, context: dict) -> dict:\\n    import importlib\\n    import time\\n    import traceback\\n    import urllib.parse\\n    import urllib.request\\n    import json\\n\\n    keywords = params.get('keywords', 'Open Source AI Agent')\\n    max_results = int(params.get('max_results', 3))\\n\\n    def normalize(items):\\n        out = []\\n        seen = set()\\n        for r in items:\\n            title = (r.get('title') or '').strip()\\n            href = (r.get('url') or r.get('href') or '').strip()\\n            body = (r.get('summary') or r.get('body') or r.get('snippet') or '').strip()\\n            if not href or href in seen:\\n                continue\\n            seen.add(href)\\n            out.append({'title': title, 'url': href, 'summary': body})\\n            if len(out) >= max_results:\\n                break\\n        return out\\n\\n    try:\\n        ddgs_mod = importlib.import_module('duckduckgo_search')\\n        DDGS = getattr(ddgs_mod, 'DDGS', None)\\n        if DDGS is not None:\\n            queries = [keywords, f'{keywords} discussion', f'{keywords} blog']\\n            collected = []\\n            seen = set()\\n            with DDGS() as ddgs:\\n                for q in queries:\\n                    try:\\n                        for r in ddgs.text(q, max_results=max_results * 3):\\n                            title = (r.get('title') or '').strip()\\n                            href = (r.get('href') or r.get('url') or '').strip()\\n                            body = (r.get('body') or r.get('snippet') or '').strip()\\n                            if not href or href in seen:\\n                                continue\\n                            seen.add(href)\\n                            collected.append({'title': title, 'url': href, 'summary': body})\\n                            if len(collected) >= max_results:\\n                                return {'status': 'success', 'keywords': keywords, 'results': collected, 'source': 'duckduckgo_search'}\\n                    except Exception:\\n                        time.sleep(1)\\n                        continue\\n            if collected:\\n                return {'status': 'success', 'keywords': keywords, 'results': collected[:max_results], 'source': 'duckduckgo_search_partial'}\\n    except Exception:\\n        pass\\n\\n    try:\\n        q = urllib.parse.quote(keywords)\\n        url = f'https://api.duckduckgo.com/?q={q}&format=json&no_redirect=1&no_html=1'\\n        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})\\n        with urllib.request.urlopen(req, timeout=20) as resp:\\n            data = json.loads(resp.read().decode('utf-8', errors='ignore'))\\n        items = []\\n        abstract = (data.get('AbstractText') or '').strip()\\n        abstract_url = (data.get('AbstractURL') or '').strip()\\n        heading = (data.get('Heading') or keywords).strip()\\n        if abstract_url:\\n            items.append({'title': heading, 'url': abstract_url, 'summary': abstract})\\n        for topic in data.get('RelatedTopics', []):\\n            if isinstance(topic, dict) and 'Topics' in topic:\\n                for sub in topic.get('Topics', []):\\n                    txt = (sub.get('Text') or '').strip()\\n                    first = txt.split(' - ')[0].strip() if txt else ''\\n                    u = (sub.get('FirstURL') or '').strip()\\n                    if u:\\n                        items.append({'title': first or 'Related Topic', 'url': u, 'summary': txt})\\n            elif isinstance(topic, dict):\\n                txt = (topic.get('Text') or '').strip()\\n                first = txt.split(' - ')[0].strip() if txt else ''\\n                u = (topic.get('FirstURL') or '').strip()\\n                if u:\\n                    items.append({'title': first or 'Related Topic', 'url': u, 'summary': txt})\\n        norm = normalize(items)\\n        if norm:\\n            return {'status': 'success', 'keywords': keywords, 'results': norm, 'source': 'duckduckgo_instant_answer'}\\n    except Exception as e:\\n        return {'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}\\n\\n    return {'status': 'success', 'keywords': keywords, 'results': [], 'source': 'no_results'}"}}, {"tool_name": "duckduckgo_promoter_search", "params": {"keywords": "{keywords}", "max_results": "{max_results}"}}]"""
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
