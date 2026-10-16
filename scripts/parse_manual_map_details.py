#!/usr/bin/env python3
"""解析手動存檔的地圖詳情頁 .cache/manual/map_details/map_<id>.html（?page=guide-map&id=<id>）
→ data/reborn/map_details.json（{地圖ID: 詳情}）。只讀本地檔，不對官網發請求，也不複製圖片
（atlas 的圖磚是動態載入的畫布，頁面存檔本來就不含；怪物圖示見 images/monsters/）。
兩種版型：
- atlas 版（有 <script id="atlas-data"> JSON）：怪物、Boss（含重生週期）、出入口、NPC、狩獵區座標都從這份 JSON 取。
- 舊版（沒有 atlas）：怪物卡片 + 有些頁多一張「同區樓層與傳送」表。"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual' / 'map_details'
OUT = ROOT / 'data' / 'reborn'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()

def parse_atlas(raw, mid):
    d = json.loads(re.search(r'<script[^>]*id="atlas-data"[^>]*>(.*?)</script>', raw, re.S).group(1))
    D = d['data']
    assert d['id'] == mid and D['map']['id'] == mid, f'map_{mid}.html 內的地圖 ID 不符：{d["id"]}/{D["map"]["id"]}'
    h = re.sub(r'<script.*?</script>|<style.*?</style>', '', raw, flags=re.S)
    facts = {txt(k): txt(v) for k, v in re.findall(r'<div class="atlas-fact"><dt>(.*?)</dt><dd>(.*?)</dd>', h, re.S)}
    # 頁面標示的數量要跟 JSON 對得上
    for label, key in (('Monster types', 'monsters'), ('Field bosses', 'bosses'), ('Exits', 'exits'), ('NPCs', 'npcs')):
        if label in facts:
            assert int(facts[label]) == len(D[key]), f'map_{mid}.html {label} 頁面 {facts[label]}、JSON {len(D[key])}'
    return {'id': mid, 'name': D['map']['name'], 'source': 'atlas', 'generated_at': D['generatedAt'], 'facts': facts,
            'size': {'width': d['layout']['width'], 'height': d['layout']['height']}, 'world': d['layout']['world'],
            'escape': D['escape'], 'monsters': D['monsters'], 'bosses': D['bosses'], 'exits': D['exits'],
            'arrivals': D['arrivals'], 'npcs': D['npcs'], 'hunting': D['hunting']}

def parse_legacy(raw, mid):
    h = re.sub(r'<script.*?</script>|<style.*?</style>', '', raw, flags=re.S)
    name = txt(re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S).group(1))
    assert re.search(rf'Map ID {mid}\b', txt(h)), f'map_{mid}.html 不是地圖 {mid}'
    listed = int(re.search(r'Monsters On This Map</h2>.*?(\d+) listed', h, re.S).group(1))
    monsters = []
    for c in h.split('<div id="spawn-')[1:]:
        a = re.search(r'<a href="[^"]*npc=(\d+)[^"]*"[^>]*>(.*?)</a>', c, re.S)
        assert a and int(re.match(r'(\d+)"', c).group(1)) == int(a.group(1)), f'map_{mid}.html 怪物卡片 ID 不符'
        monsters.append({'id': int(a.group(1)), 'name': txt(a.group(2)),
                         'badges': [txt(b) for b in re.findall(r'<span class="px-2 py-0\.5 text-xs rounded[^"]*">(.*?)</span>', c, re.S)],
                         'stats': {txt(k).rstrip(':'): txt(v) for k, v in re.findall(r'<div><span class="text-gray-400">(.*?)</span>(.*?)</div>', c, re.S)},
                         'spawn_note': txt(re.search(r'<div class="text-xs text-gray-300 mt-2">(.*?)</div>', c, re.S).group(1))})
    assert len(monsters) == listed, f'map_{mid}.html 怪物 {len(monsters)} 隻、頁面標示 {listed}'
    rec = {'id': mid, 'name': name, 'source': 'legacy', 'monsters': monsters}
    # 部分舊版頁有「同區樓層與傳送」表：樓層、地圖、可傳到的地圖
    t = re.search(r'<h2[^>]*>(.*?)</h2>\s*</div>\s*<div class="text-sm text-gray-300">(\d+) maps</div>.*?<tbody>(.*?)</tbody>', h, re.S)
    if t:
        floors = []
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t.group(3), re.S):  # 當前地圖那列是 <tr class="is-current">
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
            m = re.search(r'id=(\d+)"[^>]*>(.*?)</a>', tds[1], re.S)  # 當前地圖那列沒有連結，是 <span aria-current>
            cur = 'aria-current' in tds[1]
            assert bool(m) != cur, f'map_{mid}.html 樓層表格式不符：{txt(tds[1])}'
            floors.append({'floor': txt(tds[0]), 'map_id': mid if cur else int(m.group(1)), 'name': txt(tds[1]) if cur else txt(m.group(2)),
                           'portals': [{'map_id': int(i), 'label': txt(l)} for i, l in re.findall(r'id=(\d+)"[^>]*>(.*?)</a>', tds[2], re.S)]})
        assert len(floors) == int(t.group(2)), f'map_{mid}.html 樓層 {len(floors)}、頁面標示 {t.group(2)}'
        rec['area'] = {'name': txt(t.group(1)), 'floors': floors}
    return rec

out = {}
for path in sorted(SRC.glob('map_*.html'), key=lambda p: int(p.stem[4:])):
    mid = int(path.stem[4:])
    raw = path.read_text(encoding='utf-8')
    out[mid] = parse_atlas(raw, mid) if 'id="atlas-data"' in raw else parse_legacy(raw, mid)
ids = json.loads((SRC / 'todo_map_ids.json').read_text())
assert sorted(out) == sorted(ids), f'地圖頁與清單不符：缺 {sorted(set(ids) - set(out))}、多 {sorted(set(out) - set(ids))}'
(OUT / 'map_details.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
a = [m for m in out.values() if m['source'] == 'atlas']
print(f'{len(out)} 張地圖（atlas {len(a)}、舊版 {len(out) - len(a)}）；怪物 {sum(len(m["monsters"]) for m in out.values())}、'
      f'Boss {sum(len(m["bosses"]) for m in a)}、出口 {sum(len(m["exits"]) for m in a)}、NPC {sum(len(m["npcs"]) for m in a)}、狩獵區 {sum(len(m["hunting"]) for m in a)}；'
      f'有樓層表 {sum("area" in m for m in out.values())}')
