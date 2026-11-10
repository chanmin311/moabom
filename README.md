# 모아봄 — 인턴·알바·대외활동 공고 자동 모음

사람인 · 링커리어 · 알바몬 · 알바천국 공고를 **하루 두 번(06:47, 18:47) 자동으로 모아서**
내 사이트 한 곳에서 보여줘요. 서버 없이 GitHub만으로 돌아가고, 비용은 0원이에요.

```
GitHub Actions(매일 실행) → crawler/ 가 수집 → docs/posts.json 저장 → GitHub Pages 사이트가 읽어서 표시
```

---

## 1. 처음 세팅 (15분)

### ① 저장소 만들기
1. GitHub에서 **New repository** → 이름 예: `moabom` → **Public** 선택 → Create
   (Private 저장소의 Pages는 유료 플랜이 필요해요)
2. **Add file → Upload files**로 이 폴더 안의 파일을 전부 올리기
   - `.github` 폴더가 숨김 폴더라 안 보이면, 폴더째 드래그해서 올리세요
   - 터미널을 쓸 줄 알면: `git init && git add . && git commit -m init && git push`

### ② 사람인 API 키 넣기 (선택, 추천)
1. https://oapi.saramin.co.kr 에서 **이용신청** → 용도: `개인 구직용 공고 모아보기`
2. 승인 메일이 오면 로그인 → **앱 등록** → access-key 복사
3. 내 저장소 **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `SARAMIN_KEY` / Secret: 복사한 키

> 키가 없으면 사람인만 건너뛰고 나머지는 정상으로 돌아가요. 승인되는 동안 먼저 써도 돼요.
> 키는 절대 코드나 config.yaml에 직접 쓰지 마세요 (공개 저장소라 다 보여요).

### ③ 자동 실행 권한 켜기
**Settings → Actions → General → Workflow permissions → "Read and write permissions"** 선택 → Save

### ④ 첫 수집 돌리기
**Actions 탭 → 공고 수집 → Run workflow**. 2~5분 뒤 초록 체크가 뜨면 성공이에요.

### ⑤ 사이트 공개
**Settings → Pages → Branch: `main`, 폴더: `/docs`** → Save
1~2분 뒤 `https://내아이디.github.io/moabom/` 으로 접속하면 끝이에요.
휴대폰에서 열고 **홈 화면에 추가**하면 앱처럼 쓸 수 있어요.

---

## 2. 내 취향대로 바꾸기 → `config.yaml`

| 바꾸고 싶은 것 | 고칠 곳 |
|---|---|
| 사람인에서 찾을 검색어 | `saramin.searches`의 `keywords` |
| 🎬 콘텐츠 태그 기준 | `content_keywords` |
| 보기 싫은 공고 거르기 | `exclude_keywords` |
| 알바몬·알바천국 지역/직종 | 아래 팁 참고 |
| 수집 시간 | `.github/workflows/crawl.yml`의 `cron` (UTC 기준, 한국 시간 −9시간) |

**알바몬·알바천국 팁:** 사이트에서 원하는 조건(지역, 직종, 검색어)을 걸고 검색한 뒤
주소창 URL을 복사해서 `alba.sites.albamon.list_urls`에 넣으세요.
URL 속 페이지 번호 자리를 `{page}`로 바꾸면 여러 페이지를 봐요.
지금 기본값은 전체 목록이라, 키워드 필터를 통과하는 공고가 적을 수 있어요.

GitHub 웹에서 파일을 열고 연필 아이콘으로 고친 뒤 Commit하면, 다음 실행부터 적용돼요.

---

## 3. 뭔가 안 될 때

- **사이트 위에 "⚠ 이번 수집에서 실패"가 떠요** → 그 사이트만 실패한 거예요. 지난번 공고는 남아 있어요.
  Actions 탭에서 빨간 X가 뜬 실행을 열면 자세한 이유가 보여요.
- **링커리어·알바 사이트가 계속 실패해요** → 사이트 구조가 바뀌었을 가능성이 커요.
  Actions 로그의 에러 메시지를 Claude에게 붙여넣고 "고쳐줘"라고 하면 돼요.
- **공고가 0개예요** → `alba.keywords`가 너무 좁은지 확인해보세요.

내 컴퓨터에서 직접 돌려보려면:
```bash
pip install -r requirements.txt
python -m playwright install chromium
SARAMIN_KEY=내키 python -m crawler.main     # 결과: docs/posts.json
python -m pytest -q                          # 파서 테스트
```

---

## 4. 지켜야 할 것

- **개인용으로만 쓰세요.** 사람인 API는 키 공유와, 이 데이터로 돈을 받는 서비스를 금지해요.
  링커리어·알바몬·알바천국도 상업적 재배포는 약관 위반이 될 수 있어요.
- 요청 간격(`delay_seconds`)은 1초 이상, 실행은 하루 몇 번 정도로 유지하세요.
- 사이트에는 제목·마감일·링크만 보여주고, 상세 내용은 원문 링크로 보내는 방식을 유지하세요.

## 폴더 구조
```
config.yaml              ← 수집 설정 (주로 여기만 고치면 됨)
crawler/main.py          ← 전체 실행, 합치기·중복 제거·마감 정리
crawler/sources/         ← 사이트별 수집기 (saramin / linkareer / alba)
docs/index.html          ← 사이트 화면
docs/posts.json          ← 수집 결과 (자동 생성)
.github/workflows/       ← 자동 실행 스케줄
tests/                   ← 파서 테스트
```
