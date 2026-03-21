def execute(params: dict, context: dict) -> dict:
    import importlib
    import traceback
    import urllib.parse
    import urllib.request
    import json

    keywords = params.get('keywords', 'Open Source AI Agent')
    max_results = int(params.get('max_results', 3))

    def normalize(items):
        out = []
        seen = set()
        for r in items:
            title = str(r.get('title') or '').strip()
            href = str(r.get('url') or r.get('href') or '').strip()
            body = str(r.get('summary') or r.get('body') or r.get('snippet') or '').strip()
            if not href or href in seen:
                continue
            seen.add(href)
            out.append({'title': title, 'url': href, 'summary': body})
            if len(out) >= max_results:
                break
        return out

    try:
        ddgs_mod = importlib.import_module('duckduckgo_search')
        DDGS = getattr(ddgs_mod, 'DDGS', None)
        if DDGS is None:
            raise ImportError('duckduckgo_search.DDGS not available')
        collected = []
        with DDGS() as ddgs:
            for r in ddgs.text(keywords, max_results=max_results * 3):
                collected.append(r)
                if len(collected) >= max_results * 3:
                    break
        results = normalize(collected)
        return {'status': 'success', 'keywords': keywords, 'results': results, 'count': len(results)}
    except Exception as e:
        fallback = []
        try:
            q = urllib.parse.quote(keywords)
            url = 'https://html.duckduckgo.com/html/?q=' + q
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            parts = html.split('result__a')
            seen = set()
            for chunk in parts[1:]:
                href = ''
                title = ''
                if 'href="' in chunk:
                    href = chunk.split('href="', 1)[1].split('"', 1)[0]
                text_part = chunk.split('>', 1)
                if len(text_part) > 1:
                    title = text_part[1].split('</a>', 1)[0]
                title = title.replace('<b>', '').replace('</b>', '').strip()
                if href and href not in seen:
                    seen.add(href)
                    fallback.append({'title': title, 'url': href, 'summary': ''})
                if len(fallback) >= max_results:
                    break
        except Exception:
            pass
        return {
            'status': 'success' if fallback else 'error',
            'keywords': keywords,
            'results': fallback,
            'count': len(fallback),
            'message': 'fallback_used' if fallback else str(e),
            'traceback': traceback.format_exc() if not fallback else ''
        }
