"""사람인 공식 채용공고 API (https://oapi.saramin.co.kr). 하루 500회까지 호출 가능."""
import os

from ..common import get_json, make_post, ts_to_date

API = "https://oapi.saramin.co.kr/job-search"


def parse(data: dict, type_: str) -> list[dict]:
    jobs = (data.get("jobs") or {}).get("job") or []
    posts = []
    for j in jobs:
        if str(j.get("active", 1)) != "1":
            continue
        pos = j.get("position") or {}
        posts.append(make_post(
            source="사람인",
            source_id=j.get("id"),
            type=type_,
            title=pos.get("title"),
            org=((j.get("company") or {}).get("detail") or {}).get("name"),
            url=j.get("url"),
            deadline=ts_to_date(j.get("expiration-timestamp")),
            location=(pos.get("location") or {}).get("name", "").replace("&gt;", ">"),
            pay=(j.get("salary") or {}).get("name", ""),
        ))
    return posts


def collect(cfg: dict) -> list[dict]:
    key = os.environ.get("SARAMIN_KEY")
    if not key:
        raise RuntimeError("SARAMIN_KEY가 없어서 건너뜀 (README의 'API 키 넣기' 참고)")
    posts = []
    for s in cfg.get("searches", []):
        params = {"access-key": key, "job_type": s["job_type"],
                  "count": cfg.get("count", 110), "sort": "pd"}
        if s.get("keywords"):
            params["keywords"] = s["keywords"]
        data = get_json(API, params=params, headers={"Accept": "application/json"})
        if "code" in data and "jobs" not in data:   # 에러 응답 형식
            raise RuntimeError(f"사람인 API 오류: {data.get('message', data)}")
        posts += parse(data, s["type"])
    return posts
