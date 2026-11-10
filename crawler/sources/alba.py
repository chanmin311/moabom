"""알바몬·알바천국: 목록 페이지에서 공고 링크를 모은 뒤, 상세 페이지에서 정보를 읽어요.

상세 페이지는 검색엔진용 구조화 데이터(JSON-LD JobPosting)를 우선 읽어서
화면 디자인이 바뀌어도 잘 안 깨지게 했어요. 없으면 표(dt/dd)를 읽어요.
"""
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..common import get_html, make_post, text_to_date

SITES = {
    "albamon": {"name": "알바몬", "host": "https://www.albamon.com",
                "link": re.compile(r"/jobs/detail/(\d+)"),
                "detail": "https://www.albamon.com/jobs/detail/{id}", "marker": "/jobs/detail/"},
    "alba": {"name": "알바천국", "host": "https://www.alba.co.kr",
             "link": re.compile(r"/job/Detail\?adid=(\d+)", re.I),
             "detail": "https://www.alba.co.kr/job/Detail?adid={id}", "marker": "adid="},
}


def listing_ids(site: str, html: str) -> list[str]:
    pat = SITES[site]["link"]
    ids = []
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        m = pat.search(a["href"])
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    if not ids:   # 링크가 스크립트 안에만 있는 경우
        ids = list(dict.fromkeys(pat.findall(html)))
    return ids


def _job_posting(soup) -> dict:
    def walk(v):
        if isinstance(v, list):
            for x in v:
                yield from walk(x)
        elif isinstance(v, dict):
            t = v.get("@type")
            if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                yield v
            yield from walk(v.get("@graph", []))
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            found = next(walk(json.loads(s.string or s.get_text())), None)
        except (ValueError, TypeError):
            continue
        if found:
            return found
    return {}


def _fields(soup) -> dict:
    out = {}
    for dt_ in soup.select("dt"):
        dd = dt_.find_next_sibling("dd")
        if dd:
            out.setdefault(dt_.get_text(" ", strip=True), dd.get_text(" ", strip=True))
    return out


def _location(jp: dict) -> str:
    loc = jp.get("jobLocation") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    addr = loc.get("address", {}) if isinstance(loc, dict) else {}
    if isinstance(addr, str):
        return addr
    return " ".join(str(addr.get(k)) for k in ("addressRegion", "addressLocality") if addr.get(k))


def _pay(jp: dict) -> str:
    sal = jp.get("baseSalary")
    if not isinstance(sal, dict):
        return ""
    val = sal.get("value") or {}
    num, unit = val.get("value"), str(val.get("unitText", "")).upper()
    if not isinstance(num, (int, float)):
        return ""
    label = {"HOUR": "시급", "DAY": "일급", "WEEK": "주급", "MONTH": "월급", "YEAR": "연봉"}.get(unit, "")
    return f"{label} {int(num):,}원".strip()


def parse_detail(site: str, source_id: str, html: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    jp, f = _job_posting(soup), _fields(soup)
    title = jp.get("title")
    org = (jp.get("hiringOrganization") or {}).get("name", "")
    if not title and soup.title:   # 알바천국 예전 형식: "회사 채용정보 : 제목 - 알바천국"
        t = soup.title.get_text(" ", strip=True)
        if "채용정보 :" in t:
            org, title = (x.strip() for x in t.split("채용정보 :", 1))
            title = title.removesuffix("- 알바천국").strip()
    if not title:
        return None
    deadline_text = f.get("모집마감") or f.get("마감일") or jp.get("validThrough")
    return make_post(
        source=SITES[site]["name"], source_id=source_id, type="알바",
        title=title, org=org,
        url=SITES[site]["detail"].format(id=source_id),
        deadline=text_to_date(deadline_text),
        location=f.get("근무지") or f.get("근무지역") or _location(jp),
        pay=f.get("급여") or _pay(jp),
    )


def _matches(post: dict, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text = f"{post['title']} {post['org']}"
    return any(k in text for k in keywords)


def collect(cfg: dict) -> list[dict]:
    posts, errors = [], []
    for site, scfg in (cfg.get("sites") or {}).items():
        try:
            ids = []
            for tmpl in scfg.get("list_urls", []):
                pages = range(1, cfg.get("pages", 1) + 1) if "{page}" in tmpl else [1]
                for p in pages:
                    url = tmpl.replace("{page}", str(p))
                    ids += [i for i in listing_ids(site, get_html(url, must_contain=SITES[site]["marker"])) if i not in ids]
            if not ids:
                raise RuntimeError("목록에서 공고 링크를 못 찾음 (사이트 구조 변경 가능성)")
            for sid in ids[: cfg.get("max_details", 30)]:
                try:
                    html = get_html(SITES[site]["detail"].format(id=sid))
                    p = parse_detail(site, sid, html)
                except Exception:
                    continue
                if p and _matches(p, cfg.get("keywords") or []):
                    posts.append(p)
        except Exception as e:
            errors.append(f"{SITES[site]['name']}: {e}")
    if errors and not posts:
        raise RuntimeError(" / ".join(errors))
    if errors:
        print("  ⚠", " / ".join(errors))
    return posts
