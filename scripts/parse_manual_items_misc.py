#!/usr/bin/env python3
"""解析手動存檔的其他道具列表 .cache/manual/items/<分類>.html、<分類>_p2..pN.html
（?page=lookup-items&cat=<分類>&item_page=N，Standard；分類 runes、materials、consumables、other，另有 stat=trophies 存成 trophies）
＋ 單件頁 .cache/manual/items/item_<id>.html（?page=lookup-items&mode=standard&item=<id>）：寶箱列表（stat=treasure_boxes）只有連結，
  內容要逐件抓；monsters 掉落、擊殺任務獎勵裡出現但列表沒有的道具也都是寶箱（etcitem），一併歸 treasure_boxes 分類。
  單件頁會附同套裝的其他卡片，只取 ID 等於檔名的那張。非 etcitem 的單件頁（armor_sets 引用、列表沒有的 7673614、7673619、7673622）
  歸 single_page 分類。
→ data/reborn/items/misc.json，圖片複製到 data/reborn/items/images/。只讀本地檔，不對官網發請求。
- 同一件道具可屬多個分類（戰利品是旗標，跟材料／其他重疊；符文裡 110 件已在 armors.json 的 pattern_back），所以以 id 合併，categories 記全部。
- 寶箱卡片多一塊「Treasure Box Contents (N rolls)」→ contents（rolls、道具 ID／名稱／數量／機率）；官網沒公開內容的寶箱沒有這個欄位。
  官網隱藏機率的寶箱整箱顯示 0%，chance_pct 存 None；箱內只有部分項目是 0% 時無法分辨是真的 0 還是隱藏，照原值存。
- 不含「Load sources」（掉落／商店來源，需點擊才載入）；有 Craftable 標記、「Used in N recipes」數量（配方內容在 used-in-guide，另外抓）。"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.cache' / 'manual' / 'items'
OUT = ROOT / 'data' / 'reborn' / 'items'
CATS = ('runes', 'trophies', 'materials', 'consumables', 'other')
BOX_CAT = 'treasure_boxes'
SINGLE_CAT = 'single_page'
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
    contents = None
    if 'Treasure Box Contents' in c:
        sec = c[c.index('Treasure Box Contents'):]
        rolls = re.match(r'Treasure Box Contents \((\d+) rolls?\)', txt(sec[:200]))
        rows = re.findall(r'<div class="flex items-center gap-2 border border-amber-700/30 rounded px-2 py-1 bg-black/40">(.*?)</div>\s*</div>\s*</div>', sec, re.S)
        contents = {'rolls': int(rolls.group(1)) if rolls else None, 'items': []}
        for r in rows:
            m = re.search(r'item=(\d+)[^>]*>(.*?)</a>.*?<span class="text-gray-400">x([\d,]+)(?:-([\d,]+))?</span>\s*<span class="text-amber-300/80">([\d.,]+)%</span>', r, re.S)
            assert m, f'{stem} 卡片 {iid} 箱子內容格式不符：{txt(r)}'
            lo = int(m.group(3).replace(',', ''))
            contents['items'].append({'item_id': int(m.group(1)), 'name': txt(m.group(2)), 'qty_min': lo,
                                      'qty_max': int(m.group(4).replace(',', '')) if m.group(4) else lo, 'chance_pct': float(m.group(5).replace(',', ''))})
        assert rolls and contents['items'] and len(rows) == sec.count('border-amber-700/30 rounded px-2 py-1 bg-black/40'), f'{stem} 卡片 {iid} 箱子內容區塊不符'
        if all(i['chance_pct'] == 0 for i in contents['items']):  # 官網對部分寶箱隱藏機率，整箱顯示 0%；別存成 0
            for i in contents['items']: i['chance_pct'] = None
    return {'id': iid, 'name': txt(a.group(3)), 'slug': a.group(2), 'kind': kind.group(1),
            'bless': txt(bless.group(1)) if bless else None, 'stat_tags': [t for t in tags.group(1).split(',') if t] if tags else [],
            'stats': stats, 'craftable': 'page=crafting-guide' in c, 'used_in_recipes': int(used.group(1)) if used else 0,
            'market': market, 'icon': icon, **({'contents': contents} if contents else {})}

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
for path in sorted(SRC.glob('item_[0-9]*.html'), key=lambda p: int(p.stem[5:])):  # 單件頁
    iid = int(path.stem[5:])
    h = re.sub(r'<script.*?</script>|<style.*?</style>', '', path.read_text(encoding='utf-8'), flags=re.S)
    cards = h.split('data-item-card-id="')[1:]  # 單件頁除了該道具，還會附同套裝的其他卡片，只取 ID 等於檔名的那張
    assert len(cards) == h.count('lookup-sources-load'), f'{path.name} 卡片數與 Load sources 按鈕數不符'
    mine = [c for c in cards if int(re.match(r'(\d+)"', c).group(1)) == iid]
    assert len(mine) == 1, f'{path.name} 沒有 ID {iid} 的卡片或有多張'
    it = parse_card(mine[0], path.stem)
    assert it['id'] not in items, f'{path.name} 列表已有 {iid}'
    cat = BOX_CAT if it['kind'] == 'etcitem' else SINGLE_CAT  # 寶箱都是 etcitem；其他（套裝裝備）只有單件頁，不屬於任何列表分類
    items[iid] = {**it, 'categories': [cat]}; per[cat] = per.get(cat, 0) + 1
boxes = {x['id'] for x in json.loads((OUT.parent / 'treasure_boxes.json').read_text(encoding='utf-8')) if x['link'] == 'item'}
for iid in boxes & items.keys():  # 列表裡本來就有的寶箱也標上
    if BOX_CAT not in items[iid]['categories']: items[iid]['categories'].append(BOX_CAT)
out = sorted(items.values(), key=lambda x: x['id'])
(OUT / 'misc.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
known = {x['id'] for f in ('weapons', 'armors') for x in json.loads((OUT / f'{f}.json').read_text(encoding='utf-8'))}
print(f'{len(out)} 件（{sum(per.values())} 張卡片）', per, f'；已在 weapons/armors {sum(i["id"] in known for i in out)} 件；缺圖 {sum(i["icon"] is None for i in out)}；',
      f'可製作 {sum(i["craftable"] for i in out)}；寶箱 {sum(BOX_CAT in i["categories"] for i in out)}（有內容 {sum("contents" in i for i in out)}）；'
      f'寶箱列表 {len(boxes)} 個 item 型，找不到 {sorted(boxes - items.keys() - known)}')
