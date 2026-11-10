"""모든 수집기를 돌려서 docs/posts.json 을 만들어요.

실행:  python -m crawler.main
"""
import json
import re
import sys
from pathlib import Path

import yaml

from . import common
from .sources import alba, linkareer, saramin

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "posts.json"
SOURCES = {"saramin": ("사람인", saramin), "linkareer": ("링커리어", linkareer),
           "alba": ("알바몬/알바천국", alba)}
ALBA_NAMES = {"알바몬", "알바천국"}


def _norm(s: str) -> str:
    return re.sub(r"[\W_]+", "", s.lower())


def _safe_error(e: Exception) -> str:
    """posts.json은 공개되니까 API 키를 지우고 짧게 줄여요."""
    msg = re.sub(r"access-key=[^&\s'\"]+", "access-key=***", str(e))
    msg = " / ".join(line.split("Call log:")[0].strip() for line in msg.split(" / "))
    return msg.splitlines()[0][:160] if msg else type(e).__name__


def merge(fresh: dict[str, list], failed: set[str], previous: dict, cfg: dict) -> list[dict]:
    """fresh: 소스키→새 공고, failed: 실패한 소스키, previous: 지난번 posts.json."""
    today = common.today().isoformat()
    prev_posts = previous.get("posts", [])
    first_seen = {p["id"]: p.get("first_seen", today) for p in prev_posts}

    posts = [p for items in fresh.values() for p in items]
    # 이번에 실패한 소스는 지난번 공고를 그대로 유지 (사이트가 갑자기 텅 비지 않게)
    for key in failed:
        name = SOURCES[key][0]
        posts += [p for p in prev_posts
                  if p["source"] == name or (key == "alba" and p["source"] in ALBA_NAMES)]

    exclude = cfg.get("exclude_keywords") or []
    content_kw = cfg.get("content_keywords") or []
    seen_url, seen_key, out = set(), set(), []
    for p in posts:
        if p.get("deadline") and p["deadline"] < today:
            continue                                   # 마감 지남
        text = f"{p['title']} {p['org']}"
        if any(k in text for k in exclude):
            continue
        key = _norm(p["title"]) + "|" + _norm(p["org"])
        if p["url"] in seen_url or key in seen_key:
            continue                                   # 중복
        seen_url.add(p["url"]); seen_key.add(key)
        p = dict(p)
        p["content"] = any(k.lower() in text.lower() for k in content_kw)
        p["first_seen"] = first_seen.get(p["id"], today)
        out.append(p)
    out.sort(key=lambda p: (p["deadline"] is None, p["deadline"] or ""))
    return out


def run(cfg: dict, previous: dict) -> dict:
    common.set_delay(cfg.get("delay_seconds", 1.5))
    fresh, failed, status = {}, set(), {}
    for key, (name, mod) in SOURCES.items():
        scfg = cfg.get(key) or {}
        if not scfg.get("enabled", True):
            continue
        print(f"▶ {name} 수집 중…")
        try:
            items = mod.collect(scfg)
            fresh[key] = items
            status[name] = {"ok": True, "count": len(items)}
            print(f"  ✓ {len(items)}개")
        except Exception as e:
            failed.add(key)
            msg = _safe_error(e)
            status[name] = {"ok": False, "error": msg}
            print(f"  ✗ 실패: {msg}")
    posts = merge(fresh, failed, previous, cfg)
    return {"updated_at": common.now_iso(), "sources": status, "posts": posts}


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    result = run(cfg, previous)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n총 {len(result['posts'])}개 공고 → {OUT.relative_to(ROOT)}")
    if not any(s["ok"] for s in result["sources"].values()):
        sys.exit(1)   # 전부 실패하면 GitHub Actions에서 빨간불로 알려줌


if __name__ == "__main__":
    main()
