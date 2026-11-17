"""로그아웃 홈에 뜬 롱폼의 기획·구성 연구용 묶음 만들기 (알고리즘 분석 A '연구 갱신' 2단계).

순서: ① python yt_home_loggedout.py <폴더> --scrolls 30 --min-views 1000000   → items.json
      ② python yt_longform_study.py <같은 폴더> [--max-age 31 --min-views 1000000 --min-dur 180]
결과: <폴더>/meta_all.json(후보의 정확한 게시일·길이·구독자), <폴더>/candidates.tsv(포함/제외와 이유),
      <폴더>/pack/<id>.md(메타 + 설명 + 챕터 + 상위 댓글 25개 + 타임스탬프 자막) — 분석 브리프의 입력.
제외: 라이브 다시보기, 음악(20분 미만 음악 분류·재생목록), 기간·조회·길이 기준 밖.
'다시 본 구간' 히트맵은 로그아웃 상태로 받을 수 없어 쓰지 않는다(2026-11 확인).
자막·댓글 원문은 분석용이다. 결과 폴더는 임시 폴더에 두고 공유하지 않는다.
"""
import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

import yt_dlp

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LANGS = ['ko-orig', 'ko', 'en-orig']
PLAYLIST = re.compile(r'playlist|플레이리스트|ᴘʟᴀʏʟɪꜱᴛ|1시간 반복|모음 \|', re.I)


def subs_lines(vdir, i):
    for lang in LANGS:
        f = vdir / f'{i}.{lang}.json3'
        if not f.exists():
            continue
        lines, cur, t0 = [], '', None
        for e in json.load(open(f, encoding='utf-8')).get('events', []):
            txt = ''.join(s.get('utf8', '') for s in e.get('segs') or []).replace('\n', ' ').strip()
            if not txt:
                continue
            t = e['tStartMs'] // 1000
            t0 = t if t0 is None else t0
            cur += ' ' + txt
            if len(cur) > 110 or t - t0 >= 12:
                lines.append(f'[{t0 // 60:02d}:{t0 % 60:02d}] {cur.strip()}')
                cur, t0 = '', None
        if cur:
            lines.append(f'[{t0 // 60:02d}:{t0 % 60:02d}] {cur.strip()}')
        return lang, lines
    return None, []


def main(a):
    global LANGS
    LANGS = a.sub_langs.split(',')
    root = Path(a.folder)
    vdir, pdir = root / 'vids', root / 'pack'
    vdir.mkdir(exist_ok=True)
    pdir.mkdir(exist_ok=True)
    today = dt.date.today()
    items = json.load(open(root / 'items.json', encoding='utf-8'))
    # 홈 표시 '2개월 전·년 전'은 미리 뺀다(정확한 날짜는 아래에서 다시 잰다)
    cand = [x for x in items if x['views'] >= a.min_views and not re.search(r'([2-9]|1[0-9])개월 전|년 전', x['text'])]
    print('후보', len(cand), flush=True)
    opts = {'skip_download': True, 'quiet': True, 'no_warnings': True, 'noprogress': True,
            'writesubtitles': True, 'writeautomaticsub': True, 'subtitleslangs': LANGS,
            'subtitlesformat': 'json3', 'outtmpl': str(vdir / '%(id)s.%(ext)s'), 'getcomments': True,
            'extractor_args': {'youtube': {'max_comments': ['40', '40', '0', '0'], 'comment_sort': ['top']}}}
    rows, tsv = [], ['id\t포함\t이유\t조회\t구독\t게시\t길이분\t제목']
    with yt_dlp.YoutubeDL(opts) as y:
        for x in cand:
            try:
                info = y.extract_info('https://www.youtube.com/watch?v=' + x['id'], download=False)
            except Exception as e:  # 연령 제한·삭제 등
                print('ERR', x['id'], str(e)[:80])
                continue
            up = info.get('upload_date') or info.get('release_date') or '19700101'
            d = dt.date(int(up[:4]), int(up[4:6]), int(up[6:8]))
            r = {'id': x['id'], 'title': info.get('title'), 'home_title': x['text'].split(' | ')[1] if ' | ' in x['text'] else '',
                 'channel': info.get('channel'), 'subs': info.get('channel_follower_count'),
                 'views': info.get('view_count'), 'likes': info.get('like_count'), 'comments': info.get('comment_count'),
                 'date': str(d), 'age_days': (today - d).days, 'dur': info.get('duration') or 0,
                 'live': info.get('live_status'), 'cats': info.get('categories') or [],
                 'chapters': [(c['start_time'], c['title']) for c in (info.get('chapters') or [])],
                 'desc': (info.get('description') or '')[:1500], 'tags': (info.get('tags') or [])[:15]}
            title = unicodedata.normalize('NFKC', r['title'] or '')
            why = ('기간' if r['age_days'] > a.max_age else '길이' if r['dur'] < a.min_dur
                   else '라이브' if r['live'] in ('was_live', 'is_live', 'post_live') else
                   '음악' if ('Music' in r['cats'] and r['dur'] < 1200) or PLAYLIST.search(title) else '')
            tsv.append('\t'.join(map(str, [r['id'], 'X' if why else 'O', why, r['views'], r['subs'], r['date'], r['dur'] // 60, title[:60]])))
            rows.append(r)
            print(r['id'], 'O' if not why else 'X ' + why, r['date'], r['dur'] // 60, '분', r['views'], title[:40], flush=True)
            if why:
                continue
            y.process_info(info)  # 자막 저장
            cm = sorted(info.get('comments') or [], key=lambda c: -(c.get('like_count') or 0))[:25]
            lang, lines = subs_lines(vdir, r['id'])
            ratio = round(r['views'] / r['subs'], 2) if r['subs'] else None
            md = [f"# {r['title']}", f"- 홈에 뜬 제목: {r['home_title']}",
                  f"- id {r['id']} · 채널 {r['channel']} (구독 {r['subs']}) · 조회 {r['views']} · 조회/구독 {ratio}",
                  f"- 게시 {r['date']} ({r['age_days']}일 전) · 길이 {r['dur'] // 60}분 {r['dur'] % 60}초 · 좋아요 {r['likes']} · 댓글(받아 온 수) {r['comments']} · 분류 {r['cats']}",
                  f"- 썸네일 https://i.ytimg.com/vi/{r['id']}/maxresdefault.jpg (빈 이미지면 hqdefault) · 태그 {r['tags']}",
                  '## 설명', r['desc'], '## 챕터', *[f"- {int(t) // 60:02d}:{int(t) % 60:02d} {n}" for t, n in r['chapters']],
                  '## 상위 댓글(좋아요순)', *[f"- ({c.get('like_count')}) {(c.get('text') or '').replace(chr(10), ' ')[:220]}" for c in cm],
                  f'## 자막 ({lang or "없음"})', *lines]
            (pdir / f"{r['id']}.md").write_text('\n'.join(md), encoding='utf-8')
    json.dump(rows, open(root / 'meta_all.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    (root / 'candidates.tsv').write_text('\n'.join(tsv), encoding='utf-8')
    print('분석 묶음', len(list(pdir.glob('*.md'))), '개 →', pdir, flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', help='yt_home_loggedout.py 결과 폴더(items.json이 있는 곳)')
    ap.add_argument('--max-age', type=int, default=31, help='게시 후 최대 일수')
    ap.add_argument('--min-views', type=int, default=1_000_000)
    ap.add_argument('--min-dur', type=int, default=180, help='최소 길이(초) — 롱폼만')
    ap.add_argument('--sub-langs', default='ko-orig,ko,en-orig', help='받을 자막 언어(앞쪽 우선)')
    main(ap.parse_args())
