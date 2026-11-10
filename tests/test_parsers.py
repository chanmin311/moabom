"""실제 사이트 응답 형식을 흉내 낸 샘플로 파서를 검사해요.  실행: pytest -q"""
import datetime as dt
import time

from crawler import common, main
from crawler.sources import alba, linkareer, saramin

D = lambda n: (common.today() + dt.timedelta(days=n)).isoformat()


def test_saramin_parse():
    exp = int(time.time()) + 5 * 86400
    data = {"jobs": {"count": 2, "job": [
        {"id": "111", "url": "https://www.saramin.co.kr/x?rec_idx=111", "active": 1,
         "company": {"detail": {"name": "(주)가나"}},
         "position": {"title": "콘텐츠 마케팅 인턴", "location": {"name": "서울 &gt; 강남구"},
                      "job-type": {"name": "인턴직"}},
         "salary": {"name": "회사내규에 따름"}, "expiration-timestamp": str(exp)},
        {"id": "222", "active": 0, "position": {"title": "마감된 공고"}},
    ]}}
    posts = saramin.parse(data, "인턴")
    assert len(posts) == 1
    p = posts[0]
    assert p["id"] == "사람인:111" and p["org"] == "(주)가나"
    assert p["location"] == "서울 > 강남구" and p["deadline"] == D(5)


def test_linkareer_parse():
    close_ms = int(time.time() * 1000) + 3 * 86400 * 1000
    data = {"data": {"activities": {"nodes": [
        {"id": "300", "title": " 대학생  SNS 서포터즈 ", "organizationName": "샘플재단",
         "recruitCloseAt": str(close_ms), "jobTypes": None, "categories": []}]}}}
    p = linkareer.parse(data, "서포터즈")[0]
    assert p["title"] == "대학생 SNS 서포터즈"
    assert p["url"] == "https://linkareer.com/activity/300" and p["deadline"] == D(3)


def test_alba_listing_and_detail():
    listing = '<a href="/jobs/detail/123?x=1">A</a><a href="https://www.albamon.com/jobs/detail/456">B</a><a href="/jobs/detail/123">dup</a>'
    assert alba.listing_ids("albamon", listing) == ["123", "456"]
    assert alba.listing_ids("alba", '<a href="/job/Detail?adid=789">x</a>') == ["789"]

    detail = """<html><script type="application/ld+json">
    {"@context":"https://schema.org","@type":"JobPosting","title":"유튜브 영상편집 보조",
     "hiringOrganization":{"name":"예시스튜디오"},"validThrough":"%s",
     "jobLocation":{"address":{"addressRegion":"서울","addressLocality":"마포구"}},
     "baseSalary":{"currency":"KRW","value":{"value":12000,"unitText":"HOUR"}}}
    </script></html>""" % (D(7) + "T23:59:00+09:00")
    p = alba.parse_detail("albamon", "123", detail)
    assert p["title"] == "유튜브 영상편집 보조" and p["org"] == "예시스튜디오"
    assert p["deadline"] == D(7) and p["location"] == "서울 마포구" and p["pay"] == "시급 12,000원"

    # JSON-LD 없이 표만 있는 경우 + '상시모집'
    table = "<title>데모카페 채용정보 : 카드뉴스 디자인 알바 - 알바천국</title><dl><dt>급여</dt><dd>건당 30,000원</dd><dt>모집마감</dt><dd>상시모집</dd></dl>"
    p = alba.parse_detail("alba", "789", table)
    assert p["title"] == "카드뉴스 디자인 알바" and p["org"] == "데모카페"
    assert p["deadline"] is None and p["pay"] == "건당 30,000원"


def test_text_to_date():
    assert common.text_to_date("2026.11.20 23:59") == "2026-11-20"
    assert common.text_to_date("2026년 1월 5일") == "2026-01-05"
    assert common.text_to_date("채용시까지") is None


def mk(id_, title, source="링커리어", deadline=None, org="가나"):
    return common.make_post(source=source, source_id=id_, type="대외활동", title=title,
                            org=org, url=f"https://x/{source}/{id_}", deadline=deadline)


def test_merge_rules():
    cfg = {"exclude_keywords": ["다단계"], "content_keywords": ["영상"]}
    previous = {"posts": [
        dict(mk("1", "영상 서포터즈", deadline=D(3)), first_seen="2026-01-01"),
        dict(mk("9", "사람인 옛 공고", source="사람인", deadline=D(4)), first_seen="2026-01-02"),
        dict(mk("8", "사람인 지난 공고", source="사람인", deadline=D(-1)), first_seen="2026-01-02"),
    ]}
    fresh = {"linkareer": [
        mk("1", "영상 서포터즈", deadline=D(3)),          # 이전에 본 공고 → first_seen 유지
        mk("2", "마감 지난 활동", deadline=D(-1)),        # 제거
        mk("3", "다단계 활동"),                           # 제외어
        mk("4", "영상  서포터즈!", deadline=D(3)),        # 제목 중복 → 제거
        mk("5", "상시 모집 활동"),                        # 마감일 없음 → 맨 뒤
    ]}
    out = main.merge(fresh, failed={"saramin"}, previous=previous, cfg=cfg)
    ids = [p["id"] for p in out]
    assert ids == ["링커리어:1", "사람인:9", "링커리어:5"]
    assert out[0]["first_seen"] == "2026-01-01" and out[0]["content"] is True
    assert out[2]["first_seen"] == common.today().isoformat()


def test_error_hides_api_key():
    e = RuntimeError("Max retries exceeded with url: /job-search?access-key=SECRET123&job_type=4")
    assert "SECRET123" not in main._safe_error(e)
