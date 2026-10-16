#!/usr/bin/env python3
"""解析手動存檔的寶箱列表 .cache/manual/treasure_boxes.html → data/reborn/treasure_boxes.json，圖片複製到 data/reborn/images/。
只讀本地檔，不對官網發請求。"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual'
OUT = ROOT / 'data' / 'reborn'
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
(OUT / 'images').mkdir(parents=True, exist_ok=True)

h = re.sub(r'<script.*?</script>|<style.*?</style>', '', (SRC / 'treasure_boxes.html').read_text(encoding='utf-8'), flags=re.S)
assert 'stat=treasure_boxes' in h, 'treasure_boxes.html 不是寶箱頁'
h = h[re.search(r'<h\d[^>]*>\s*Treasure Boxes\s*</h\d>', h).end():]

boxes, seen, missing = [], set(), []
for a in re.finditer(r'<a href="[^"]*[?&;](item|npc)=(\d+)"[^>]*>(.*?)</a>', h, re.S):
    link, iid, body = a.group(1), int(a.group(2)), a.group(3)
    if iid in seen: print('重複', iid); continue
    seen.add(iid)
    label = re.search(r'font-semibold">(.*?)</div>', body, re.S)
    shown = re.search(r'>\s*ID (\d+)\s*<', body)
    assert label and shown and int(shown.group(1)) == iid, f'卡片 {iid} 格式不符'
    img = re.search(r'<img src="([^"]*)"', body)
    icon = None
    if img and img.group(1).startswith('treasure_boxes_files/') and (SRC / img.group(1)).exists():
        p = SRC / img.group(1); icon = p.name; shutil.copy(p, OUT / 'images' / icon)
    else:
        missing.append(iid)
    box = {'id': iid, 'name': txt(label.group(1)), 'link': link, 'icon': icon}
    # lazy-load 佔位圖（src 仍是 data:）且 data-src 的圖檔不存在 → 官網該圖示 404，頁面退回 default.webp
    if icon is None and img and img.group(1).startswith('data:') and 'data-src=' in body:
        box['icon_404'] = True
    boxes.append(box)
(OUT / 'treasure_boxes.json').write_text(json.dumps(boxes, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'{len(boxes)} 個寶箱；缺圖 {len(missing)} 個 {missing}；圖示 404 {[b["id"] for b in boxes if b.get("icon_404")]}')
