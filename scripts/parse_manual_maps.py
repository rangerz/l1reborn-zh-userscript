#!/usr/bin/env python3
"""解析手動存檔的地圖列表 .cache/manual/maps.html、maps_p2..pN.html
→ data/reborn/maps.json，圖片複製到 data/reborn/images/maps/。只讀本地檔，不對官網發請求。"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual'
OUT = ROOT / 'data' / 'reborn'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
(OUT / 'images' / 'maps').mkdir(parents=True, exist_ok=True)

def pages():
    yield 1, 'maps'
    n = 2
    while (SRC / f'maps_p{n}.html').exists():
        yield n, f'maps_p{n}'; n += 1

maps, seen = [], set()
for n, stem in pages():
    h = re.sub(r'<script.*?</script>|<style.*?</style>', '', (SRC / f'{stem}.html').read_text(encoding='utf-8'), flags=re.S)
    total = re.search(r'Page (\d+) of (\d+)', h)
    assert total and int(total.group(1)) == n, f'{stem}.html 頁碼不符：{total and total.group(0)}'
    showing = re.search(r'Showing (\d+)-(\d+) of (\d+) maps', h)
    cards = h.split('<article')[1:]
    assert showing and len(cards) == int(showing.group(2)) - int(showing.group(1)) + 1, f'{stem}.html 卡片數與 Showing 不符'
    for c in cards:
        mid = int(re.search(r'href="[^"]*page=guide-map&amp;id=(\d+)"', c).group(1))
        if mid in seen: print('重複', mid); continue
        seen.add(mid)
        name = txt(re.search(r'text-lg font-semibold[^>]*>(.*?)</div>', c, re.S).group(1))
        shown = re.search(r'>\s*Map (\d+)\s*<', c)
        assert shown and int(shown.group(1)) == mid, f'地圖 {mid} 格式不符'
        img = re.search(r'<img src="([^"]*)"', c)
        icon = None
        if img and img.group(1).startswith(f'{stem}_files/') and (SRC / img.group(1)).exists():
            p = SRC / img.group(1); icon = p.name; shutil.copy(p, OUT / 'images' / 'maps' / icon)
        maps.append({'id': mid, 'name': name, 'image': icon})
assert len(maps) == int(showing.group(3)), f'共 {len(maps)} 張，頁面標示 {showing.group(3)} 張'
(OUT / 'maps.json').write_text(json.dumps(maps, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'{len(maps)} 張地圖，{n} 頁（共 {total.group(2)} 頁），缺圖 {sum(m["image"] is None for m in maps)} 張')
