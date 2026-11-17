"""채널의 업로드 영상 목록과 영상별 지표를 받는다 (주제 추천의 '이미 다룬 주제'·'채널 적합도' 재료).

사용:
  python yt_channel.py <출력폴더>                      # OAuth가 있으면 내 채널 + Analytics(평균 시청·구독 증가)
  python yt_channel.py <출력폴더> --channel @핸들      # API 키만 있을 때(공개 지표만), 또는 다른 채널
결과: <출력폴더>/videos.json (최신순: 제목·업로드일·길이(초)·롱폼/숏츠·조회·좋아요·댓글·하루 평균 조회
      + OAuth일 때 avg_view_sec·avg_view_pct·shares·subs_gained)
할당량: 영상 50개당 약 2단위.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from yt_auth import has_oauth, oauth_credentials, youtube  # noqa: E402


def seconds(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--channel", help="채널 ID(UC…) 또는 @핸들. 없으면 OAuth로 로그인한 내 채널")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    mine = not a.channel
    if mine and not has_oauth():
        sys.exit("--channel @핸들 을 주거나 OAuth(client_secret.json)를 설정하세요.")
    yt = youtube(prefer_key=not mine)
    part = "snippet,statistics,contentDetails"
    if mine:
        r = yt.channels().list(part=part, mine=True).execute()
    elif a.channel.startswith("@"):
        r = yt.channels().list(part=part, forHandle=a.channel).execute()
    else:
        r = yt.channels().list(part=part, id=a.channel).execute()
    if not r.get("items"):
        sys.exit(f"채널을 찾지 못했습니다: {a.channel}")
    channel = r["items"][0]
    uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, token = [], None
    while True:
        page = yt.playlistItems().list(part="contentDetails", playlistId=uploads,
                                       maxResults=50, pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in page["items"]]
        token = page.get("nextPageToken")
        if not token:
            break
    videos = []
    for n in range(0, len(ids), 50):
        videos += yt.videos().list(part="snippet,contentDetails,statistics",
                                   id=",".join(ids[n:n + 50])).execute()["items"]

    stats = {}
    if mine:
        from googleapiclient.discovery import build
        ya = build("youtubeAnalytics", "v2", credentials=oauth_credentials(), cache_discovery=False)
        rows = ya.reports().query(
            ids="channel==MINE", startDate="2005-01-01", endDate=dt.date.today().isoformat(),
            dimensions="video", metrics="views,averageViewDuration,averageViewPercentage,shares,subscribersGained",
            sort="-views", maxResults=200).execute().get("rows", [])
        stats = {row[0]: row[1:] for row in rows}

    today = dt.date.today()
    result = []
    for v in videos:
        sec = seconds(v["contentDetails"]["duration"])
        pub = v["snippet"]["publishedAt"][:10]
        views = int(v["statistics"].get("viewCount", 0))
        item = {
            "id": v["id"], "title": v["snippet"]["title"], "published": pub,
            "duration_sec": sec, "type": "short" if sec <= 180 else "long",
            "views": views, "views_per_day": views // max((today - dt.date.fromisoformat(pub)).days, 1),
            "likes": int(v["statistics"].get("likeCount", 0)),
            "comments": int(v["statistics"].get("commentCount", 0)),
            "description": v["snippet"]["description"][:500],
        }
        if mine:
            s = stats.get(v["id"], [None] * 5)
            item.update(avg_view_sec=s[1], avg_view_pct=s[2], shares=s[3], subs_gained=s[4])
        result.append(item)
    result.sort(key=lambda x: x["published"], reverse=True)
    (out / "channel.json").write_text(json.dumps(channel, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "videos.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(channel["snippet"]["title"], "영상", len(result), "개 →", out / "videos.json",
          "(Analytics 포함)" if mine else "(공개 지표만)")


if __name__ == "__main__":
    main()
