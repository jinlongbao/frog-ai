import json
import urllib.request
import urllib.parse
import urllib.error

def execute(params: dict, context: dict) -> dict:
    owner = params.get('owner', 'jinlongbao')
    repo = params.get('repo', 'frog-ai')
    per_page = 5
    url = f'https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/issues?state=open&per_page={per_page}'
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'github_manager_plugin/1.0'
    }
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode('utf-8')
            data = json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode('utf-8')
        except Exception:
            detail = str(e)
        return {
            'success': False,
            'error': f'HTTPError {e.code}: {detail}',
            'owner': owner,
            'repo': repo
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'owner': owner,
            'repo': repo
        }

    issues = []
    for item in data:
        if 'pull_request' in item:
            continue
        issues.append({
            'title': item.get('title', ''),
            'author': (item.get('user') or {}).get('login', ''),
            'body': item.get('body', ''),
            'number': item.get('number'),
            'url': item.get('html_url', '')
        })
        if len(issues) >= 5:
            break

    return {
        'success': True,
        'owner': owner,
        'repo': repo,
        'count': len(issues),
        'issues': issues
    }
