"""DuckDuckGo search helpers."""

import re
import requests
from ddgs import DDGS
from hermes.api.eastmoney import FETCH_HEADERS

BACKENDS = ["google", "lite"]


def search_text(query: str, max_results: int, backend: str = "google") -> list[dict]:
    """Core text search with fallback."""
    for b in ([backend, "lite"] if backend == "google" else [backend]):
        try:
            with DDGS() as ddgs:
                return [
                    {"title": r.get("title", ""), "url": r.get("href", ""), "description": r.get("body", "")}
                    for r in ddgs.text(query, backend=b, max_results=max_results)
                ]
        except Exception:
            continue
    return []


def search_news(query: str, max_results: int = 10) -> list[dict]:
    """Search news with fallback to text search."""
    max_results = min(max_results, 20)
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""), "url": r.get("url", ""),
                    "description": r.get("body", ""), "source": r.get("source", ""),
                    "date": r.get("date", ""),
                })
    except Exception:
        results = search_text(query, max_results, "google")
    return results


def fetch_page(url: str, keywords: list[str] | None = None, max_length: int = 5000) -> dict:
    """Fetch a web page and extract text content. Returns dict with url, content, length."""
    try:
        r = requests.get(url, headers=FETCH_HEADERS, timeout=15)
        r.raise_for_status()
        clean = re.sub(r"<[^>]+>", " ", r.text)
        clean = re.sub(r"\s+", " ", clean)
    except Exception as e:
        return {"error": f"Fetch failed: {e}", "url": url}

    if keywords:
        snippets = []
        for kw in keywords:
            idx = 0
            while True:
                idx = clean.find(kw, idx)
                if idx < 0:
                    break
                start = max(0, idx - 100)
                end = min(len(clean), idx + 400)
                snippets.append(clean[start:end].strip())
                idx = end
        text = "\n".join(snippets)
    else:
        text = clean

    text = text[:max_length]
    return {"url": url, "length": len(text), "content": text}