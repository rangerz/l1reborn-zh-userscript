#!/usr/bin/env python3
"""解析手動存檔的可馴服怪物列表 .cache/manual/tamable.html、tamable_p2..pN.html
→ data/reborn/tamable.json，圖片複製到 data/reborn/images/monsters/。只讀本地檔，不對官網發請求。"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual'
OUT = ROOT / 'data' / 'reborn'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
(OUT / 'images' / 'monsters').mkdir(parents=True, exist_ok=True)

def pages():
    yield 1, 'tamable'
    n = 2
    while (SRC / f'tamable_p{n}.html').exists():
        yield n, f'tamable_p{n}'; n += 1

mons, seen = [], set()
for n, stem in pages():
    h = re.sub(r'<script.*?</script>|<style.*?</style>', '', (SRC / f'{stem}.html').read_text(encoding='utf-8'), flags=re.S)
    total = re.search(r'Page (\d+) of (\d+)', h)
    assert total and int(total.group(1)) == n, f'{stem}.html 頁碼不符：{total and total.group(0)}'
    h = h[h.index('id="lookup-monsters"'):]
    for c in h.split('lookup-monster-summary')[1:]:
        a = re.search(r'<a href="[^"]*npc=(\d+)[^"]*"[^>]*>(.*?)</a>', c, re.S)
        mid = int(a.group(1))
        if mid in seen: print('重複', mid); continue
        seen.add(mid)
        badges = [txt(b) for b in re.findall(r'<span class="px-2 py-0\.5 text-xs rounded[^"]*">(.*?)</span>', c, re.S)]
        assert 'Tameable' in badges, f'{mid} 不是可馴服'
        stats = {txt(k).rstrip(':'): txt(v) for k, v in re.findall(r'<div><span class="text-gray-400">(.*?)</span>(.*?)</div>', c, re.S)}
        loc = re.search(r'Locations:</span>(.*?)</div>', c, re.S)
        locations = [{'map_id': int(i), 'name': txt(t)} for i, t in re.findall(r'guide-map&amp;id=(\d+)"[^>]*>(.*?)</a>', loc.group(1), re.S)] if loc else []
        img = re.search(r'<img src="([^"]*)"', c)
        icon = None
        if img and img.group(1).startswith(f'{stem}_files/') and (SRC / img.group(1)).exists():
            p = SRC / img.group(1); icon = p.name; shutil.copy(p, OUT / 'images' / 'monsters' / icon)
        mons.append({'id': mid, 'name': txt(a.group(2)), 'badges': badges, 'stats': stats, 'locations': locations, 'icon': icon})
(OUT / 'tamable.json').write_text(json.dumps(mons, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'{len(mons)} 隻可馴服怪物，{n} 頁（共 {total.group(2)} 頁），缺圖 {sum(m["icon"] is None for m in mons)} 隻')
