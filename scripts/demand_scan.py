"""주제 수요 스캔: 사람들이 지금 실제로 보고·묻고·치는 것을 한 번에 모은다.

신호 4가지
  1. 국내 급상승: 최근 N일 업로드, 하루 평균 조회와 구독자 대비 배수
  2. 댓글 수요: 국내 급상승 영상의 최근 N일 댓글 중 질문·요청형
  3. 검색 자동완성: 유튜브 검색창 추천어
  4. 해외 급상승: 같은 기간 해외 상위 영상(국내 빈칸 찾기용)

사용: python demand_scan.py <출력폴더> --config <키워드 JSON> [--days 14]
키워드 JSON 양식은 플러그인 templates/demand_keywords.json (내 분야 검색어로 바꿔 쓴다).
인증: API 키(YOUTUBE_API_KEY)면 충분하다.
할당량: 검색어 1개당 100단위. 검색어 24개면 약 2,600단위(하루 기본 한도 10,000).
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from yt_auth import youtube  # noqa: E402

ASK = re.compile(r"\?|궁금|어떻게|가능할까|가능한가|알려|해주세요|부탁|하고 ?싶|원해요|다뤄|만들어 ?주|how|can you|please", re.I)
NON_LATIN = re.compile("[가-힣ぁ-んァ-ン一-龥ऀ-ॿа-яА-Я]")


def search(yt, q, region, lang, since, n=25):
    r = yt.search().list(part="id", q=q, type="video", order="viewCount", regionCode=region,
                         relevanceLanguage=lang, publishedAfter=since, maxResults=n).execute()
    return [i["id"]["videoId"] for i in r["items"]]


def details(yt, ids, today, me):
    vids, ids = [], list(dict.fromkeys(ids))
    for k in range(0, len(ids), 50):
        for v in yt.videos().list(part="snippet,statistics,contentDetails",
                                  id=",".join(ids[k:k + 50])).execute()["items"]:
            s = v["snippet"]
            if s["channelId"] == me:
                continue
            age = max((today - dt.date.fromisoformat(s["publishedAt"][:10])).days, 1)
            views = int(v["statistics"].get("viewCount", 0))
            vids.append({"id": v["id"], "title": s["title"], "ch": s["channelTitle"], "cid": s["channelId"],
                         "date": s["publishedAt"][:10], "dur": v["contentDetails"]["duration"],
                         "views": views, "per_day": views // age,
                         "comments": int(v["statistics"].get("commentCount", 0))})
    cids, subs = list({v["cid"] for v in vids}), {}
    for k in range(0, len(cids), 50):
        for c in yt.channels().list(part="statistics", id=",".join(cids[k:k + 50])).execute()["items"]:
            subs[c["id"]] = int(c["statistics"].get("subscriberCount", 0) or 0)
    for v in vids:
        v["subs"] = subs.get(v["cid"], 0)
        v["ratio"] = round(v["views"] / max(v["subs"], 1), 2)
    return sorted(vids, key=lambda v: -v["per_day"])


def comments(yt, vid, since, limit=300):
    out, tok = [], None
    while len(out) < limit:
        try:
            r = yt.commentThreads().list(part="snippet", videoId=vid, order="relevance", maxResults=100,
                                         pageToken=tok, textFormat="plainText").execute()
        except Exception:  # 댓글 꺼짐 등
            break
        for t in r["items"]:
            s = t["snippet"]["topLevelComment"]["snippet"]
            if s["publishedAt"][:10] >= since[:10]:
                out.append({"vid": vid, "likes": s["likeCount"], "text": s["textOriginal"]})
        tok = r.get("nextPageToken")
        if not tok:
            break
    return out


def suggest(seed, hl):
    url = ("https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&hl=" + hl
           + "&q=" + urllib.parse.quote(seed))
    try:
        return json.loads(urllib.request.urlopen(url, timeout=10).read().decode("utf-8"))[1]
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--config", required=True, help="키워드 JSON (templates/demand_keywords.json 참고)")
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    since = (today - dt.timedelta(days=a.days)).isoformat() + "T00:00:00Z"
    me = cfg.get("my_channel_id", "")
    noise = re.compile(cfg["noise_title_regex"], re.I) if cfg.get("noise_title_regex") else None
    noise_ch = set(cfg.get("noise_channels", []))
    loc, glo, sug = cfg["local"], cfg.get("global") or {}, cfg.get("suggest") or {}
    n_search = len(loc["queries"]) + len(glo.get("queries", []))
    print(f"검색어 {n_search}개 → 할당량 약 {n_search * 100 + 200:,}단위", flush=True)
    yt = youtube(prefer_key=True)

    def clean(v):
        return not (noise and noise.search(v["title"])) and v["ch"] not in noise_ch

    kr = details(yt, [i for q in loc["queries"] for i in search(yt, q, loc["region"], loc["lang"], since)], today, me)
    kr = [v for v in kr if clean(v) and (loc["lang"] != "ko" or re.search("[가-힣]", v["title"]))]
    gl = []
    if glo.get("queries"):
        gl = details(yt, [i for q in glo["queries"] for i in search(yt, q, glo["region"], glo["lang"], since)], today, me)
        gl = [v for v in gl if clean(v) and not NON_LATIN.search(v["title"])]

    cm = []
    for v in [v for v in kr if v["comments"] >= 15][:20]:
        for c in comments(yt, v["id"], since):
            if ASK.search(c["text"]) and len(c["text"]) > 12:
                c["ch"], c["title"] = v["ch"], v["title"]
                cm.append(c)
    cm.sort(key=lambda c: -c["likes"])
    sg = {s: suggest(s, sug.get("hl", "ko")) for s in sug.get("seeds", [])}

    json.dump({"date": today.isoformat(), "days": a.days, "local": kr, "global": gl, "asks": cm, "suggest": sg},
              open(out / "demand.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    L = [f"# 수요 스캔 {today} (최근 {a.days}일)", "", "## 국내 급상승 (하루 평균 조회순)"]
    L += [f"- {v['per_day']:,}/일 · {v['views']:,} · 구독 대비 ×{v['ratio']} · {v['ch']} | {v['title']} (youtu.be/{v['id']})" for v in kr[:30]]
    L += ["", "## 해외 급상승"]
    L += [f"- {v['per_day']:,}/일 · {v['views']:,} · ×{v['ratio']} · {v['ch']} | {v['title']} (youtu.be/{v['id']})" for v in gl[:30]]
    L += ["", f"## 댓글 질문·요청 ({len(cm)}개 중 좋아요순 80)"]
    L += [f"- [{c['ch']}|♥{c['likes']}] {c['text'][:160].replace(chr(10), ' ')}" for c in cm[:80]]
    L += ["", "## 검색 자동완성"]
    L += [f"- {s}: {', '.join(x)}" for s, x in sg.items()]
    (out / "demand.md").write_text("\n".join(L), encoding="utf-8")
    print(out / "demand.md", "국내", len(kr), "해외", len(gl), "질문 댓글", len(cm))


if __name__ == "__main__":
    main()
