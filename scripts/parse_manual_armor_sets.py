#!/usr/bin/env python3
"""解析手動存檔的套裝頁 .cache/manual/armor_sets.html → data/reborn/armor_sets.json，圖片複製到 data/reborn/images/。
只讀本地檔，不對官網發請求。用法：python3 scripts/parse_manual_armor_sets.py"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual'
OUT = ROOT / 'data' / 'reborn'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()

h = (SRC / 'armor_sets.html').read_text(encoding='utf-8')
h = re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S)
(OUT / 'images').mkdir(parents=True, exist_ok=True)
sets, missing = [], set()
for c in h[h.index('id="lookup-armor-sets"'):].split('page-surface--sleek-bronze')[1:]:
    name = re.search(r'<div class="text-amber-200 font-semibold">(.*?)</div>', c, re.S)
    sid = re.search(r'>Set (\d+)<', c)
    if not (name and sid): continue  # 套裝區塊之後的 modal 也帶同一個 class
    bonus = re.search(r'<span class="font-semibold text-emerald-200">([^<]*)</span>(.*?)</div>', c, re.S)
    items = []
    for tr in re.findall(r'<tr.*?</tr>', c, re.S):
        a = re.search(r'<a [^>]*item=(\d+)[^>]*>(.*?)</a>(.*?)</td>', tr, re.S)
        src = re.search(r'<img src="([^"]*)"', tr)
        icon = None
        if src:
            f = src.group(1)
            p = SRC / f
            if f.startswith('./') and p.exists():
                icon = p.name; shutil.copy(p, OUT / 'images' / icon)
            else:
                missing.add(f)
        items.append({'id': int(a.group(1)), 'name': txt(a.group(2)), 'blessed': 'Blessed' in a.group(3), 'icon': icon})
    sets.append({'id': int(sid.group(1)), 'name': txt(name.group(1)),
                 'bonus_label': txt(bonus.group(1)) if bonus else None,
                 'bonus': txt(bonus.group(2)) if bonus else None, 'items': items})
assert len({s['id'] for s in sets}) == len(sets), '套裝 id 重複'
(OUT / 'armor_sets.json').write_text(json.dumps(sets, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
n = sum(len(s['items']) for s in sets)
print(f'{len(sets)} 套裝、{n} 件；缺圖 {sum(i["icon"] is None for s in sets for i in s["items"])} 件（{len(missing)} 個圖檔）')
