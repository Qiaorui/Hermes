"""East Money API helpers with rate limiting and availability detection.

push2.eastmoney.com enforces a ~30-second rate limit — requests faster than
1 per 30s trigger anti-scraping (empty reply / connection drop). All push2
requests are gated through a global cooldown timer.

If push2 fails on first attempt, the domain is marked "down" for this session
and all subsequent push2 requests are skipped immediately (no wasted cooldown).
This prevents 60+ second timeouts when push2 is unreachable.

datacenter-web.eastmoney.com and emweb.securities.eastmoney.com have no
such restriction and can be called freely.
"""

import time
import logging
import requests

log = logging.getLogger(__name__)

FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "http://quote.eastmoney.com/",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# ── Global rate limiter for push2.eastmoney.com ──
_PUSH2_MIN_INTERVAL = 31  # seconds between push2 requests (30s limit + 1s buffer)
_push2_last_request = 0.0

# ── Availability flag: once push2 fails, skip all subsequent requests this session ──
_push2_down = False


def _push2_cooldown():
    """Wait until at least 31s since the last push2 request."""
    global _push2_last_request
    elapsed = time.time() - _push2_last_request
    if elapsed < _PUSH2_MIN_INTERVAL:
        wait = _PUSH2_MIN_INTERVAL - elapsed
        log.info(f"push2 cooldown: waiting {wait:.1f}s")
        time.sleep(wait)
    _push2_last_request = time.time()


def _is_push2_url(url: str) -> bool:
    return "push2.eastmoney.com" in url or "push2his.eastmoney.com" in url


# ── Sessions ──

_session = requests.Session()
_session.trust_env = False

_session_push2 = requests.Session()
_session_push2.trust_env = False
_session_push2.headers.update(FETCH_HEADERS)


def em_get(url: str, timeout: int = 15) -> dict | None:
    """GET request to East Money APIs with rate limiting, retry, and availability check."""
    global _push2_down, _push2_last_request

    is_push2 = _is_push2_url(url)

    # Skip push2 immediately if domain is down this session
    if is_push2 and _push2_down:
        log.debug(f"push2 down — skipping: {url[:80]}...")
        return None

    session = _session_push2 if is_push2 else _session
    max_attempts = 2 if is_push2 else 3

    for attempt in range(max_attempts):
        if is_push2:
            _push2_cooldown()

        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError):
            if is_push2:
                _push2_last_request = time.time()
                _push2_down = True
                log.warning("push2.eastmoney.com unreachable — marking down for this session")
                return None  # don't retry, save time
            continue
        except Exception:
            continue

    return None


def parse_secid(code: str) -> str:
    code = code.strip()
    if code.startswith("6"):
        return f"1.{code}"
    return f"0.{code}"


def em_prefix(code: str) -> str:
    code = code.strip()
    if code.startswith("6"):
        return f"SH{code}"
    return f"SZ{code}"


def emweb_get(url: str, timeout: int = 15) -> dict | None:
    """GET request to emweb.securities.eastmoney.com (no rate limit)."""
    try:
        r = _session.get(url, headers=FETCH_HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def push2_status() -> str:
    """Return push2 availability status for display."""
    if _push2_down:
        return "down — all push2 requests skipped this session"
    return "available"


def reset_push2():
    """Reset push2 availability flag (e.g. after network switch)."""
    global _push2_down, _push2_last_request
    _push2_down = False
    _push2_last_request = 0.0
    log.info("push2 status reset — will retry on next request")