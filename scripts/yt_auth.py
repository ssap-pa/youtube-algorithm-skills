"""YouTube API 인증 도우미 (다른 스크립트가 불러 쓴다).

두 가지 방법 중 하나만 있어도 된다.
  1. API 키 (공개 데이터: 검색·영상·채널·댓글)  → 환경 변수 YOUTUBE_API_KEY
     또는 <설정 폴더>/api_key.txt 에 키 한 줄
  2. OAuth (내 채널 Analytics: 평균 시청·구독 증가까지) → <설정 폴더>/client_secret.json
     (Google Cloud '데스크톱 앱' OAuth 클라이언트). 첫 실행 때 브라우저로 로그인하면 token.json이 생긴다.

설정 폴더: 환경 변수 YTA_CONFIG_DIR, 없으면 ~/.config/youtube-algorithm
비밀값은 프로젝트(저장소) 안에 두지 않는다.
"""
import os
import sys
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def config_dir():
    return Path(os.environ.get("YTA_CONFIG_DIR") or Path.home() / ".config" / "youtube-algorithm")


def api_key():
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    f = config_dir() / "api_key.txt"
    if not key and f.exists():
        key = f.read_text(encoding="utf-8").strip()
    return key or None


def has_oauth():
    d = config_dir()
    return (d / "token.json").exists() or (d / "client_secret.json").exists()


def oauth_credentials():
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    d = config_dir()
    token = d / "token.json"
    # 토큰에 저장된 권한 범위를 그대로 쓴다(더 넓은 범위로 받아 둔 기존 토큰도 재사용 가능)
    creds = Credentials.from_authorized_user_file(str(token)) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None  # 만료·취소된 토큰 → 다시 로그인
    if not creds or not creds.valid:
        secret = d / "client_secret.json"
        if not secret.exists():
            sys.exit(f"OAuth 클라이언트 파일이 없습니다: {secret}")
        creds = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES).run_local_server(port=0)
    d.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json(), encoding="utf-8")
    return creds


def youtube(prefer_key=True):
    """YouTube Data API 클라이언트. 공개 데이터는 API 키를 먼저 쓴다(로그인 창이 뜨지 않게)."""
    from googleapiclient.discovery import build

    key = api_key()
    if prefer_key and key:
        return build("youtube", "v3", developerKey=key, cache_discovery=False)
    if has_oauth():
        return build("youtube", "v3", credentials=oauth_credentials(), cache_discovery=False)
    if key:
        return build("youtube", "v3", developerKey=key, cache_discovery=False)
    sys.exit("유튜브 API 인증이 없습니다. README의 '처음 설정 3단계'를 보세요 "
             "(환경 변수 YOUTUBE_API_KEY 또는 설정 폴더의 client_secret.json).")


if __name__ == "__main__":
    print("설정 폴더:", config_dir())
    print("API 키:", "있음" if api_key() else "없음")
    print("OAuth:", "있음" if has_oauth() else "없음")
