"""East Money API helpers."""

import requests

FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Session that bypasses proxy for East Money APIs
_session = requests.Session()
_session.trust_env = False


def em_get(url: str, timeout: int = 15) -> dict | None:
    """GET request to East Money APIs with retry."""
    for attempt in range(3):
        try:
            r = _session.get(url, headers=FETCH_HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return None


def parse_secid(code: str) -> str:
    """Convert stock code to secid format. Shanghai=1.xxx, Shenzhen=0.xxx."""
    code = code.strip()
    if code.startswith("6"):
        return f"1.{code}"
    return f"0.{code}"


def em_prefix(code: str) -> str:
    """Convert stock code to emweb prefix. Shanghai=SH, Shenzhen=SZ."""
    code = code.strip()
    if code.startswith("6"):
        return f"SH{code}"
    return f"SZ{code}"