"""로그인 없는 유튜브 홈(시크릿 창과 같은 조건)에 알고리즘이 띄운 영상을 모은다.

사람이 할 때: 크롬 시크릿 창 → 유튜브 → 왼쪽 'Shorts' 누름 → 유튜브 로고 누름 → 로그인 없이 알고리즘이 고른 홈이 뜬다.
처음 들어간 홈은 비어 있고, 쇼츠를 한 번 거친 뒤에야 채워진다(2026-11 실측: 처음 0개 → 쇼츠 뒤 359개).
이 스크립트는 쿠키·시청 이력 없는 새 크롬을 띄워 같은 순서로 누른다.

사용: python yt_home_loggedout.py <결과 폴더> [--scrolls 30] [--min-views 1000000] [--locale ko-KR] [--show]
결과: items.json(영상 id·홈 표시 글자·조회수), t_<id>.jpg(썸네일), sheet<N>.jpg(9장 비교 시트), 0~3_*.png(화면)
준비: pip install playwright pillow  (크롬이 설치돼 있어야 한다)
결과 폴더는 임시 폴더에 둔다(이미지·원문은 공유하지 않는다).
"""
import argparse
import io
import json
import re
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

JS = r"""
() => [...document.querySelectorAll('ytd-rich-item-renderer')].map(e => {
  const a = e.querySelector('a[href*="/watch?v="]');
  if (!a) return null;
  return {id: new URL(a.href).searchParams.get('v'), text: e.innerText.replace(/\n+/g, ' | ').slice(0, 400)};
}).filter(Boolean)
"""


def views(text):
    """'208만 | 3일 전' 또는 '2.1M views | 3 days ago' → 숫자. 광고·라이브 시청 중은 0."""
    if re.search(r'스폰서|시청 중|Sponsored|watching', text):
        return 0
    m = re.search(r'\| ([\d.]+)(천|만|억)? \| [^|]*전', text)
    if m:
        return int(float(m.group(1)) * {'천': 1e3, '만': 1e4, '억': 1e8, None: 1}[m.group(2)])
    m = re.search(r'([\d.,]+)\s*([KMB])?\s*views', text, re.I)
    if m:
        unit = (m.group(2) or '').upper()
        return int(float(m.group(1).replace(',', '')) * {'K': 1e3, 'M': 1e6, 'B': 1e9, '': 1}[unit])
    return 0


def collect(out, scrolls, headless, locale):
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', headless=headless, args=['--window-size=1500,1000'])
        pg = b.new_context(locale=locale, viewport={'width': 1480, 'height': 920}).new_page()
        pg.goto('https://www.youtube.com/', wait_until='domcontentloaded')
        time.sleep(4)
        pg.screenshot(path=str(out / '0_home_first.png'))
        print('처음 홈 영상 수', len(pg.evaluate(JS)), flush=True)
        pg.locator('a[title="Shorts"]').first.click()      # 왼쪽 Shorts
        time.sleep(8)
        pg.screenshot(path=str(out / '1_shorts.png'))
        pg.locator('a#logo').first.click(timeout=5000)      # 유튜브 로고
        time.sleep(6)
        pg.screenshot(path=str(out / '2_home_after.png'))
        seen = {}
        for i in range(scrolls):
            for it in pg.evaluate(JS):
                seen.setdefault(it['id'], it)
            if i % 3 == 0:
                pg.screenshot(path=str(out / f'3_scroll_{i:02d}.png'))
            pg.mouse.wheel(0, 1700)
            time.sleep(1.6)
        b.close()
    items = list(seen.values())
    for it in items:
        it['views'] = views(it['text'])
    (out / 'items.json').write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding='utf-8')
    print('모은 영상', len(items), flush=True)
    return items


def sheets(out, items, min_views):
    pick = [it for it in items if it['views'] >= min_views and not re.search(r'Playlist|플레이리스트|𝐏𝐥𝐚𝐲𝐥𝐢𝐬𝐭|MV|M/V', it['text'])]
    ims = []
    for it in pick:
        im = None
        for q in ['maxresdefault', 'hq720', 'hqdefault']:
            try:
                im = Image.open(io.BytesIO(urllib.request.urlopen(f"https://i.ytimg.com/vi/{it['id']}/{q}.jpg", timeout=15).read())).convert('RGB')
                if im.width >= 400:
                    break
            except Exception:
                im = None
        if im is None:
            continue
        if im.height * 16 != im.width * 9:
            h = im.width * 9 // 16
            t = (im.height - h) // 2
            im = im.crop((0, t, im.width, t + h))
        im.resize((1280, 720), Image.LANCZOS).save(out / f"t_{it['id']}.jpg", quality=88)
        ims.append((it, im.resize((640, 360), Image.LANCZOS)))
    for s in range(0, len(ims), 9):
        c = Image.new('RGB', (1920, 1080), 'black')
        d = ImageDraw.Draw(c)
        for k, (it, im) in enumerate(ims[s:s + 9]):
            x, y = (k % 3) * 640, (k // 3) * 360
            c.paste(im, (x, y))
            d.rectangle((x, y, x + 150, y + 20), fill='black')
            d.text((x + 4, y + 4), f"{it['id']} {it['views']:,}", fill='yellow')
        c.save(out / f'sheet{s // 9}.jpg', quality=85)
    print('썸네일', len(ims), '장, 시트', (len(ims) + 8) // 9, flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--scrolls', type=int, default=30)
    ap.add_argument('--min-views', type=int, default=1000000)
    ap.add_argument('--locale', default='ko-KR', help='홈 언어·지역 (조회수 표기는 한국어·영어만 읽음)')
    ap.add_argument('--show', action='store_true', help='창을 띄워서 실행')
    a = ap.parse_args()
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    sheets(o, collect(o, a.scrolls, not a.show, a.locale), a.min_views)
