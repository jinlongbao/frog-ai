import os
import re
from datetime import datetime
from typing import Any, List
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# These will be passed in from main.py context or we import from a shared utils
# For now, we'll assume the environment has the necessary dependencies.

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_urls(text: str) -> List[str]:
    url_pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*"
    return re.findall(url_pattern, text)

def execute(params: dict, context: dict) -> dict:
    """
    Standard entry point for Frog Plugins.
    params: parameters from manifest.json
    context: utilities provided by Frog Brain (ingest_web_content, etc.)
    """
    command = params.get("command", "")
    max_results = params.get("max_results", 5)
    max_learn = params.get("max_learn", 3)
    
    # Use helper from context if available, else local (simplified)
    ingest_fn = context.get("ingest_web_content")
    
    input_urls = extract_urls(command)
    # Simple query extraction: remove URLs
    query = command
    for url in input_urls:
        query = query.replace(url, "")
    query = query.strip()
    
    candidates = []
    seen_urls = set()
    
    for url in input_urls:
        if url not in seen_urls:
            candidates.append({"title": "URL from command", "url": url})
            seen_urls.add(url)
            
    if query and len(candidates) < max(max_learn, 1):
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max(max_results, max_learn)):
                    url = r.get("href", "")
                    if not url or url in seen_urls:
                        continue
                    candidates.append({
                        "title": r.get("title", ""),
                        "url": url,
                        "snippet": r.get("body", ""),
                    })
                    seen_urls.add(url)
                    if len(candidates) >= max(max_results, max_learn):
                        break
        except Exception as e:
            print(f"Search failed: {e}")

    learned_items = []
    failed_items = []
    
    for candidate in candidates[: max(max_learn, 1)]:
        url = candidate.get("url", "")
        if not url:
            continue
        try:
            if ingest_fn:
                learned = ingest_fn(url=url, title_hint=candidate.get("title", ""))
                learned_items.append(learned)
            else:
                failed_items.append({"url": url, "reason": "Ingestion service unavailable"})
        except Exception as e:
            failed_items.append({"url": url, "reason": str(e)})

    # Build summary
    summary_lines = [f"Research completed for: {query or 'URL task'}"]
    for idx, item in enumerate(learned_items, start=1):
        summary_lines.append(f"{idx}. {item.get('title', 'Untitled')} ({item.get('url', '')})")
    
    if not learned_items:
        summary = "No pages were learned."
    else:
        summary = "\n".join(summary_lines)

    return {
        "status": "success",
        "triggered": True,
        "query": query,
        "learned_count": len(learned_items),
        "learned_items": learned_items,
        "failed_items": failed_items,
        "summary": summary
    }
