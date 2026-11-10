"""링커리어: 사이트가 쓰는 GraphQL API(api.linkareer.com/graphql)로 목록을 받아요."""
from ..common import make_post, post_json, ts_to_date

API = "https://api.linkareer.com/graphql"

QUERY = """
{
  activities(
    filterBy: %s,
    orderBy: { direction: DESC, field: RECENT },
    pagination: { pageSize: 50, page: %d }
  ) {
    nodes { id title organizationName recruitCloseAt jobTypes categories { name } }
  }
}
"""


def parse(data: dict, type_: str) -> list[dict]:
    if data.get("errors"):
        raise RuntimeError("링커리어 GraphQL 오류: " + data["errors"][0].get("message", ""))
    nodes = ((data.get("data") or {}).get("activities") or {}).get("nodes") or []
    return [make_post(
        source="링커리어",
        source_id=n["id"],
        type=type_,
        title=n.get("title"),
        org=n.get("organizationName"),
        url=f"https://linkareer.com/activity/{n['id']}",
        deadline=ts_to_date(n.get("recruitCloseAt"), ms=True),
    ) for n in nodes]


def collect(cfg: dict) -> list[dict]:
    posts = []
    for t in cfg.get("types", []):
        f = f'{{ status: OPEN, activityTypeID: "{t["id"]}"'
        f += ", jobTypes: [INTERN] }" if t.get("intern_only") else " }"
        for page in range(1, cfg.get("pages", 2) + 1):
            got = parse(post_json(API, {"query": QUERY % (f, page)}), t["type"])
            posts += got
            if len(got) < 50:
                break
    return posts
