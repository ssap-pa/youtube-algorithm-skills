# 유튜브 알고리즘 스킬 (Claude Code 플러그인)

로그인 없는 유튜브 홈에 알고리즘이 띄운 **최근 1개월·조회 100만+ 롱폼 39개**를 뜯어 본 기준으로,
**다음 영상 주제를 새로 찾아 주고**(algorithm-topics) **만들고 있는 영상을 점검해 주는**(algorithm-analysis) Claude Code 스킬 2종입니다.

| 스킬 | 언제 | 이렇게 말하면 됩니다 | 결과 |
|---|---|---|---|
| **algorithm-topics** (주제 추천) | 다음 영상 주제가 없을 때 | "알고리즘 주제 추천해줘", "다음 영상 뭐 만들지" | 새 후보 8~10개를 22점으로 채점, 상위 3개 펼치기, 1위 기획서(PLAN) 초안 → `youtube-algorithm/topics/TOPICS-<날짜>.md` |
| **algorithm-analysis** (영상 점검) | 주제를 정했거나 대본·시놉시스가 있을 때 | "이 영상에 알고리즘 분석 적용해줘", "터진 영상 기준으로 점검해줘" | 9개 항목 18점 점검표와 고칠 제안 → 영상 폴더의 `ALGO-CHECK.md`, `PLAN.md` |

순서: **주제 추천으로 고르고 → 제작하면서 분석으로 점검**합니다. 분석 스킬은 근거 연구를 새로 돌리는 모드(A)도 있습니다.

## 무엇이 다른가
- **지난 영상의 후속편을 추천하지 않습니다.** 후보를 다섯 곳 밖에서 찾습니다: 로그아웃 홈 100만+ 영상 패턴 · 최근 24시간 뉴스 · 해외에서 터졌는데 국내엔 없는 사례 · 검색 수요(급상승·댓글 질문·자동완성) · 직접 주는 SNS 인기글.
- **내 채널 데이터는 '내 시청자에게 맞나'를 재는 데만** 씁니다(조회·구독 증가 상위 영상).
- **숫자·인용은 원문으로 확인한 것만** 쓰고, 2차 출처·추정치는 표시합니다.
- 근거 문서가 들어 있습니다: [기획·구성 워크플로](reference/PLANNING-WORKFLOW.md) · [39개 분석 요약](reference/RESEARCH-20261113.md) · [실제 출력 예](examples/TOPICS-EXAMPLE.md)

## 설치 (Claude Code)
Claude Code 안에서:
```
/plugin marketplace add https://github.com/ssap-pa/youtube-algorithm-skills.git
/plugin install youtube-algorithm@youtube-algorithm
```
터미널에서는:
```bash
claude plugin marketplace add https://github.com/ssap-pa/youtube-algorithm-skills.git
```
```bash
claude plugin install youtube-algorithm@youtube-algorithm
```
설치 뒤 Claude Code를 다시 시작하면 스킬 2개가 보입니다. `owner/repo` 짧은 형식이 SSH 오류(Permission denied)로 실패하면 위처럼 `https://…git` 주소를 쓰세요.

## 처음 설정 3단계
1. **파이썬 패키지**(파이썬 3.10+)
   ```bash
   pip install -r requirements.txt
   ```
   플러그인 폴더 위치는 Claude에게 "youtube-algorithm 플러그인 폴더에서 requirements 설치해줘"라고 하면 찾아 줍니다. 로그아웃 홈 수집에는 PC에 크롬이 있어야 합니다.
2. **채널 프로필** — 처음 스킬을 부르면 Claude가 프로젝트에 `youtube-algorithm/CHANNEL.md`를 만들고 4가지를 묻습니다: 채널 주소, 분야 한 줄, 다루지 않을 주제, 꼭 지키는 규칙. 이 파일의 규칙이 스킬 패턴보다 우선합니다.
3. **YouTube API**(둘 중 하나, 무료)
   - **API 키**(가장 쉬움, 공개 데이터만): Google Cloud 콘솔 → 새 프로젝트 → 'YouTube Data API v3' 사용 설정 → 사용자 인증 정보 → API 키 만들기. 그다음 환경 변수 `YOUTUBE_API_KEY`에 넣거나, `~/.config/youtube-algorithm/api_key.txt`에 한 줄로 저장합니다.
   - **OAuth**(내 채널 구독 증가·평균 시청까지): 같은 프로젝트에서 'YouTube Analytics API'도 켜고 OAuth 클라이언트(데스크톱 앱)를 만들어 `~/.config/youtube-algorithm/client_secret.json`으로 저장합니다. 첫 실행 때 브라우저 로그인 창이 한 번 뜹니다.
   - 키·토큰은 프로젝트 폴더나 채팅에 넣지 마세요. 설정 폴더를 바꾸려면 환경 변수 `YTA_CONFIG_DIR`.
   - 하루 기본 할당량은 10,000단위입니다. 수요 스캔은 검색어 1개당 100단위(기본 예시 약 1,800단위)를 씁니다.

API 없이도 웹 검색·로그아웃 홈 수집 갈래는 돌아갑니다. 이 경우 채널 적합도와 검색 수요 점수는 약해집니다.

## 들어 있는 것
```
skills/algorithm-topics/SKILL.md      주제 추천 절차 (0 준비 → 1 제외 목록 → 2 다섯 갈래 수집 → 3 거르기 → 4 22점 채점 → 5 상위 3개·PLAN → 6 문서)
skills/algorithm-analysis/SKILL.md    A 연구 갱신 / B 진행 중 영상 점검(9개 항목)
reference/PLANNING-WORKFLOW.md        소재 → 로그라인 → 패키징 → 뼈대 A~E → 오프닝 60초 → 리듬 → 결말 → PLAN 양식
reference/RESEARCH-20261113.md        로그아웃 홈 100만+ 롱폼 39개 분석 요약(구독 대비 3배 이상 표·공통 패턴·따라 하면 안 되는 것)
reference/ANALYSIS-BRIEF.md           연구 갱신 때 서브 에이전트에게 주는 영상 분석 브리프
reference/FIRST-RUN.md                처음 실행 준비 절차
scripts/yt_auth.py                    API 키·OAuth 확인 (python yt_auth.py 로 상태 보기)
scripts/yt_channel.py                 내 채널 영상 목록·지표 → videos.json
scripts/demand_scan.py                국내·해외 급상승, 댓글 질문, 검색 자동완성 → demand.md
scripts/yt_home_loggedout.py          로그인 없는 홈 수집(시크릿 → Shorts → 로고와 같은 조건)
scripts/yt_longform_study.py          100만+ 롱폼 분석 묶음(메타·챕터·상위 댓글·자막) 만들기
templates/CHANNEL.md                  채널 프로필 양식
templates/demand_keywords.json        수요 스캔 검색어 양식(AI 분야 예시 → 내 분야로 바꾸기)
```

## 한계
- 근거는 2026-11-13 하루치 로그아웃 홈 1회 표본(한국 롱폼 39개)입니다. 분석 스킬 A로 내 시점의 홈을 다시 분석해 갱신하세요.
- 로그아웃 상태로는 '가장 많이 다시 본 구간' 히트맵을 받을 수 없습니다.
- 로그아웃 홈 수집의 조회수 읽기는 한국어·영어 화면 표기만 지원합니다.
- 점수는 기획 판단을 돕는 도구입니다. 최종 결정과 사실 확인은 사람이 합니다.
- 다른 사람 영상의 자막·댓글은 분석용으로만 임시 폴더에 받고, 공유물에는 짧은 인용만 씁니다.

## 만든 사람
[ssapable](https://github.com/ssap-pa) · MIT License
