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
    """Fetch a web page and extract text content. Returns dict with url, content, length.

    For PDF URLs, returns metadata only (PDF cannot be converted to text by this function).
    """
    # PDF URLs cannot be parsed to text — return metadata instead
    if url.lower().endswith(".pdf") or "/pdf/" in url.lower():
        return {"url": url, "length": 0, "content": "", "is_pdf": True, "note": "PDF file — use dedicated PDF reader or AI to extract content"}

    try:
        r = requests.get(url, headers=FETCH_HEADERS, timeout=15)
        r.raise_for_status()
        # Auto-detect encoding — many Chinese sites use gb2312/gbk instead of utf-8
        r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        # Remove script/style blocks first (they contain no useful text)
        html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S)
        html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.S)
        # Strip all remaining HTML tags
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean).strip()
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


def fetch_pdf(url: str, keywords: list[str] | None = None, max_length: int = 5000) -> dict:
    """Fetch a PDF file and extract text content. Uses pypdf for extraction.

    Args:
        url: PDF URL to fetch.
        keywords: Optional keywords to filter relevant text snippets.
        max_length: Maximum text length to return.

    Returns dict with url, content, length, page_count.
    """
    import io
    try:
        r = requests.get(url, headers=FETCH_HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        return {"error": f"PDF fetch failed: {e}", "url": url}

    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(r.content))
        pages_text = []
        page_count = len(reader.pages)
        for page in reader.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
        full_text = "\n".join(pages_text)
    except ImportError:
        # pypdf not installed — try pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                page_count = len(pdf.pages)
                full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        except ImportError:
            return {"error": "PDF extraction requires pypdf or pdfplumber package", "url": url, "is_pdf": True}
    except Exception as e:
        return {"error": f"PDF parsing failed: {e}", "url": url, "is_pdf": True}

    # Clean and filter
    full_text = re.sub(r"\s+", " ", full_text).strip()

    if keywords:
        snippets = []
        for kw in keywords:
            idx = 0
            while True:
                idx = full_text.find(kw, idx)
                if idx < 0:
                    break
                start = max(0, idx - 100)
                end = min(len(full_text), idx + 400)
                snippets.append(full_text[start:end].strip())
                idx = end
        text = "\n".join(snippets)
    else:
        text = full_text

    text = text[:max_length]
    return {"url": url, "length": len(text), "content": text, "page_count": page_count, "is_pdf": True}