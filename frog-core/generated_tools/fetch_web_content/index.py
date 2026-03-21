import json
import urllib.request
import urllib.error

def execute(params: dict, context: dict) -> dict:
    url = params.get('url')
    timeout = int(params.get('timeout', 20))
    if not url:
        return {'status': 'error', 'message': 'Missing required parameter: url'}
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            content_type = resp.headers.get('Content-Type', '')
            text = raw.decode('utf-8', errors='replace')
            result = {
                'status': 'success',
                'url': url,
                'http_status': getattr(resp, 'status', 200),
                'content_type': content_type,
                'text': text
            }
            try:
                result['json'] = json.loads(text)
            except Exception:
                pass
            return result
    except urllib.error.HTTPError as e:
        return {'status': 'error', 'message': f'HTTPError: {e.code} {e.reason}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
