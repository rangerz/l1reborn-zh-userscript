#!/usr/bin/env python3
"""解析手動存檔的其他道具列表 .cache/manual/items/<分類>.html、<分類>_p2..pN.html
（?page=lookup-items&cat=<分類>&item_page=N，Standard；分類 runes、materials、consumables、other，另有 stat=trophies 存成 trophies）
→ data/reborn/items/misc.json，圖片複製到 data/reborn/items/images/。只讀本地檔，不對官網發請求。
- 同一件道具可屬多個分類（戰利品是旗標，跟材料／其他重疊；符文裡 110 件已在 armors.json 的 pattern_back），所以以 id 合併，categories 記全部。
- 不含「Load sources」（掉落／商店來源，需點擊才載入）；有 Craftable 標記、「Used in N recipes」數量（配方內容在 used-in-guide，另外抓）。"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual' / 'items'
OUT = ROOT / 'data' / 'reborn' / 'items'
CATS = ('runes', 'trophies', 'materials', 'consumables', 'other')
txt = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
(OUT / 'images').mkdir(parents=True, exist_ok=True)

def pages(cat):
    yield 1, cat
    n = 2
    while (SRC / f'{cat}_p{n}.html').exists():
        yield n, f'{cat}_p{n}'; n += 1

def parse_card(c, stem):
    iid = int(re.match(r'(\d+)"', c).group(1))
    a = re.search(r'<a href="/item/(\d+)/([^"]*)"[^>]*>(.*?)</a>', c, re.S)
    assert a and int(a.group(1)) == iid, f'{stem} 卡片 {iid} 連結 ID 不符'
    kind = re.search(r'uppercase text-gray-300[^>]*>\s*(\w+)\s*<span class="text-gray-500">\(ID (\d+)\)', c)
    assert kind and int(kind.group(2)) == iid, f'{stem} 卡片 {iid} 格式不符'
    stats = {}
    for k, v in re.findall(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', c, re.S):
        k = txt(k).rstrip(':')
        if not k: continue  # 排版用的空白格
        stats[k] = [html.unescape(t) for t in re.findall(r'title="([^"]*)"', v)] if k == 'Classes' else txt(v)
    img = re.search(r'<img src="([^"]*)"', c)
    icon = None
    if img and img.group(1).startswith(f'{stem}_files/') and (SRC / img.group(1)).exists():
        p = SRC / img.group(1); icon = p.name
        if icon != 'default.webp': shutil.copy(p, OUT / 'images' / icon)
    bless = re.search(r'item-bless-badge[^>]*>(.*?)</span>', c, re.S)
    tags = re.match(r'\d+"\s+data-item-stats="([^"]*)"', c)
    used = re.search(r'Used in (\d+) recipes?', c)
    # 拍賣場近 90 天成交統計（會隨時間變動的快照）
    market = [{'enchant': int(e), 'label': txt(t), 'summary': html.unescape(ti).replace(' Click for price history.', '')}
              for e, ti, t in re.findall(r'<button[^>]*class="lookup-market__(?:pill|chip)"[^>]*data-graph-item-enchant="(\d+)"[^>]*title="([^"]*)"[^>]*>(.*?)</button>', c, re.S)]
    return {'id': iid, 'name': txt(a.group(3)), 'slug': a.group(2), 'kind': kind.group(1),
            'bless': txt(bless.group(1)) if bless else None, 'stat_tags': [t for t in tags.group(1).split(',') if t] if tags else [],
            'stats': stats, 'craftable': 'page=crafting-guide' in c, 'used_in_recipes': int(used.group(1)) if used else 0,
            'market': market, 'icon': icon}

items, per = {}, {}
for cat in CATS:
    n_cat = 0
    for n, stem in pages(cat):
        h = re.sub(r'<script.*?</script>|<style.*?</style>', '', (SRC / f'{stem}.html').read_text(encoding='utf-8'), flags=re.S)
        showing = re.search(r'([\d,]+) items · showing (\d+)–(\d+) · page (\d+) of (\d+)', h)
        cards = h.split('data-item-card-id="')[1:]
        assert showing and int(showing.group(4)) == n, f'{stem}.html 頁碼不符：{showing and showing.group(0)}'
        assert len(cards) == int(showing.group(3)) - int(showing.group(2)) + 1 == h.count('lookup-sources-load'), f'{stem}.html 卡片數與 Showing／Load sources 按鈕數不符'
        for c in cards:
            it = parse_card(c, stem); n_cat += 1
            if it['id'] in items:
                assert items[it['id']]['name'] == it['name'], f'{it["id"]} 跨分類名稱不同'
                items[it['id']]['categories'].append(cat)
            else:
                items[it['id']] = {**it, 'categories': [cat]}
    assert n_cat == int(showing.group(1).replace(',', '')) and n == int(showing.group(5)), f'{cat} 共 {n_cat} 件、{n} 頁，頁面標示 {showing.group(1)} 件、{showing.group(5)} 頁'
    per[cat] = n_cat
out = sorted(items.values(), key=lambda x: x['id'])
(OUT / 'misc.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
known = {x['id'] for f in ('weapons', 'armors') for x in json.loads((OUT / f'{f}.json').read_text(encoding='utf-8'))}
print(f'{len(out)} 件（{sum(per.values())} 張卡片）', per, f'；已在 weapons/armors {sum(i["id"] in known for i in out)} 件；缺圖 {sum(i["icon"] is None for i in out)}；',
      f'可製作 {sum(i["craftable"] for i in out)}')
