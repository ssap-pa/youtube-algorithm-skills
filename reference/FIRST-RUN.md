# 처음 실행 준비 (두 스킬 공통)

`<P>` = 플러그인 폴더(`${CLAUDE_PLUGIN_ROOT}`, 스킬 폴더 기준 `../..`). `<W>` = 사용자 프로젝트의 `youtube-algorithm/` 작업 폴더. `<T>` = 임시 폴더(원본 json·이미지·자막을 두는 곳, 공유하지 않는다).

1. **채널 프로필**: `<W>/CHANNEL.md`가 없으면 `<P>/templates/CHANNEL.md`를 복사하고, 사용자에게 한 번에 묻는다(질문 4개 이하).
   - 채널 주소(@핸들) · 분야 한 줄 · 다루지 않을 주제 · 꼭 지키는 규칙(없으면 양식의 예시 규칙을 제안)
   - 답을 받기 전에도 할 수 있는 일(도구 확인 등)은 먼저 한다.
2. **도구 확인**: `python <P>/scripts/yt_auth.py` → API 키·OAuth 유무를 본다.
   - 둘 다 없으면 README '처음 설정 3단계'를 사용자에게 안내하고, API가 필요 없는 단계(웹 검색·로그아웃 홈 수집)로 먼저 진행한다. 키를 대신 만들거나 비밀값을 채팅에 적게 하지 않는다.
   - 파이썬 패키지가 없으면 `pip install -r <P>/requirements.txt`를 제안한다.
3. **채널 데이터**: `python <P>/scripts/yt_channel.py <T>/channel` (OAuth 있을 때, 구독 증가까지) 또는 `--channel @핸들` (API 키만 있을 때).
   - `videos.json`에서 조회(OAuth면 구독 증가도) 상위 5개를 보고 CHANNEL.md '시청자가 반응한 축'과 '기준 영상'을 채운다. 사용자가 이미 적었으면 덮어쓰지 않고 다르면 제안만 한다.
4. **수요 스캔 키워드**: `<W>/demand_keywords.json`이 없으면 `<P>/templates/demand_keywords.json`을 복사해 **CHANNEL.md 분야에 맞는 검색어로 바꾼다**(국내 8~14개, 해외 5~10개, 자동완성 씨앗 6~12개). 내 채널 ID를 `my_channel_id`에 넣는다.

보안: API 키·client_secret·token은 `~/.config/youtube-algorithm/`(또는 `YTA_CONFIG_DIR`)에만 둔다. 프로젝트 폴더·채팅·커밋에 넣지 않는다.
