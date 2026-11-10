"""여러 수집기가 같이 쓰는 도구: HTTP 요청, 날짜 처리, 공고 형식."""
import atexit
import datetime as dt
import re
import time

import requests

KST = dt.timezone(dt.timedelta(hours=9))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 moabom-personal/1.0")

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
_delay = 1.5


def set_delay(seconds: float) -> None:
    global _delay
    _delay = max(0.5, float(seconds))


def today() -> dt.date:
    return dt.datetime.now(KST).date()


def now_iso() -> str:
    return dt.datetime.now(KST).isoformat(timespec="minutes")


def _polite():
    time.sleep(_delay)


def get_json(url, params=None, headers=None):
    _polite()
    r = _session.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()


def post_json(url, payload):
    _polite()
    r = _session.post(url, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


# ── HTML: 먼저 일반 요청, 막히면 헤드리스 브라우저(Playwright)로 재시도 ──
_browser = None


def _browser_page():
    global _browser
    if _browser is None:
        from playwright.sync_api import sync_playwright  # 설치돼 있을 때만
        pw = sync_playwright().start()
        _browser = pw.chromium.launch()
        atexit.register(lambda: (_browser.close(), pw.stop()))
    return _browser.new_page(user_agent=UA, locale="ko-KR")


def get_html(url: str, must_contain: str | None = None) -> str:
    """must_contain: 정상 페이지라면 들어있어야 할 문자열(없으면 브라우저로 재시도)."""
    _polite()
    try:
        r = _session.get(url, timeout=20)
        if r.ok and (must_contain is None or must_contain in r.text):
            return r.text
    except requests.RequestException:
        pass
    try:
        page = _browser_page()
    except ImportError:
        raise RuntimeError(f"요청 실패, Playwright 없음: {url}")
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        return page.content()
    finally:
        page.close()


# ── 날짜 ──
def ts_to_date(ts, ms=False):
    if ts in (None, "", 0, "0"):
        return None
    try:
        v = int(ts) / (1000 if ms else 1)
        return dt.datetime.fromtimestamp(v, KST).date().isoformat()
    except (ValueError, OverflowError, OSError):
        return None


_DATE_RE = re.compile(r"(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})")


def text_to_date(text):
    """'2026.11.20', '2026-11-20T23:59', '2026년 11월 20일' → '2026-11-20'. 상시모집 등은 None."""
    if not text:
        return None
    m = _DATE_RE.search(str(text))
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    try:
        return dt.date(y, mo, d).isoformat()
    except ValueError:
        return None


def make_post(*, source, source_id, type, title, org, url,
              deadline=None, location="", pay=""):
    clean = lambda s: re.sub(r"\s+", " ", str(s or "")).strip()
    return {
        "id": f"{source}:{source_id}",
        "source": source,
        "type": type,
        "title": clean(title),
        "org": clean(org),
        "url": url,
        "deadline": deadline,      # 'YYYY-MM-DD' 또는 None(상시)
        "location": clean(location),
        "pay": clean(pay),
    }
